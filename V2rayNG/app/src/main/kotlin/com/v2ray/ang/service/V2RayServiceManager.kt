package com.v2ray.ang.service
import com.v2ray.ang.gfwknocker.*

import android.app.*
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.VpnService
import android.graphics.Color
import android.os.Build
import android.util.Log
import androidx.annotation.RequiresApi
import androidx.core.app.NotificationCompat
import com.tencent.mmkv.MMKV
import com.v2ray.ang.AppConfig
import com.v2ray.ang.AppConfig.ANG_PACKAGE
import com.v2ray.ang.AppConfig.TAG_DIRECT
import com.v2ray.ang.R
import com.v2ray.ang.dto.ServerConfig
import com.v2ray.ang.extension.toSpeedString
import com.v2ray.ang.extension.toast
import com.v2ray.ang.ui.MainActivity
import com.v2ray.ang.util.MessageUtil
import com.v2ray.ang.util.MmkvManager
import com.v2ray.ang.util.TestRunTracker
import com.v2ray.ang.util.Utils
import com.v2ray.ang.util.V2rayConfigUtil
import go.Seq
import kotlinx.coroutines.*
import libv2ray.Libv2ray
import libv2ray.V2RayPoint
import libv2ray.V2RayVPNServiceSupportsSet
import rx.Observable
import rx.Subscription
import java.lang.ref.SoftReference
import kotlin.math.min

object V2RayServiceManager {
    private const val NOTIFICATION_ID = 1
    private const val NOTIFICATION_PENDING_INTENT_CONTENT = 0
    private const val NOTIFICATION_PENDING_INTENT_STOP_V2RAY = 1
    private const val NOTIFICATION_ICON_THRESHOLD = 3000

    @Volatile
    var TLS_serv: backServ? = null

    private val coreStopGate = CoreStopGate()
    // Native cleanup must finish even after an Android Service has been stopped.
    private val nativeCleanupScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    // Live delay JNI is blocking: invalidating the owner drops old results even
    // if the native call cannot be physically interrupted.
    private val liveDelayScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val liveDelayTracker = TestRunTracker()
    private var liveDelayJob: Job? = null

    // Called only while holding V2RayServiceManager's monitor (start/stop/measure).
    private fun invalidateLiveDelay() {
        liveDelayTracker.invalidate()
        liveDelayJob?.cancel()
        liveDelayJob = null
    }

    val v2rayPoint: V2RayPoint = Libv2ray.newV2RayPoint(V2RayCallback(), Build.VERSION.SDK_INT >= Build.VERSION_CODES.N_MR1)
    private val mMsgReceive = ReceiveMessageHandler()
    private val mainStorage by lazy { MMKV.mmkvWithID(MmkvManager.ID_MAIN, MMKV.MULTI_PROCESS_MODE) }
    private val settingsStorage by lazy { MMKV.mmkvWithID(MmkvManager.ID_SETTING, MMKV.MULTI_PROCESS_MODE) }

    @Volatile
    var serviceControl: SoftReference<ServiceControl>? = null
        set(value) {
            field = value
            Seq.setContext(value?.get()?.getService()?.applicationContext)
            Libv2ray.initV2Env(Utils.userAssetPath(value?.get()?.getService()), "")
        }
    @Volatile
    var currentConfig: ServerConfig? = null

    private var lastQueryTime = 0L
    private var mBuilder: NotificationCompat.Builder? = null
    private var mSubscription: Subscription? = null
    private var mNotificationManager: NotificationManager? = null

    fun startV2Ray(context: Context) {
        val mode = settingsStorage?.decodeString(AppConfig.PREF_MODE)
        if (VpnModeSelection.requiresVpnPermission(mode) && VpnService.prepare(context) != null) {
            context.toast(R.string.toast_permission_denied)
            return
        }
        if (settingsStorage?.decodeBool(AppConfig.PREF_PROXY_SHARING) == true) {
            context.toast(R.string.toast_warning_pref_proxysharing_short)
        } else {
            context.toast(R.string.toast_services_start)
        }
        val primary = Intent(context.applicationContext, if (VpnModeSelection.startsProxyProcess(mode)) {
            V2RayProxyOnlyService::class.java
        } else {
            V2RayVpnService::class.java
        })
        val psiphon = if (VpnModeSelection.usesPsiphon(mode)) {
            Intent(context.applicationContext, PsiphonVpnService::class.java)
        } else null
        fun launch(intent: Intent) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent)
            else context.startService(intent)
        }
        try {
            launch(primary)
            if (psiphon != null) launch(psiphon)
        } catch (error: Exception) {
            Log.e(ANG_PACKAGE, "Unable to start selected VPN service mode", error)
            if (psiphon != null) runCatching { context.stopService(psiphon) }
            runCatching { context.stopService(primary) }
            MessageUtil.sendMsg2UI(context, AppConfig.MSG_STATE_START_FAILURE, "")
        }
    }

    private class V2RayCallback : V2RayVPNServiceSupportsSet {
        override fun shutdown(): Long {
            val serviceControl = serviceControl?.get() ?: return -1
            // called by go
            return try {
                serviceControl.stopService()
                0
            } catch (e: Exception) {
                Log.d(ANG_PACKAGE, e.toString())
                -1
            }
        }

        override fun prepare(): Long {
            return 0
        }

        override fun protect(l: Long): Boolean {
            val serviceControl = serviceControl?.get() ?: return true
            return serviceControl.vpnProtect(l.toInt())
        }

        override fun onEmitStatus(l: Long, s: String?): Long {
            //Logger.d(s)
            return 0
        }

        override fun setup(s: String): Long {
            val serviceControl = serviceControl?.get() ?: return -1
            //Logger.d(s)
            return try {
                serviceControl.startService()
                lastQueryTime = System.currentTimeMillis()
                startSpeedNotification()
                0
            } catch (e: Exception) {
                Log.d(ANG_PACKAGE, e.toString())
                -1
            }
        }
    }

    // Serialize native startup with stop's resource snapshot; onRevoke cannot
    // observe an unstarted core and then leave a concurrently started core alive.
    @Synchronized
    fun startV2rayPoint() {
        // If stopLoop is still executing, coalesce starts into one deferred retry.
        if (!coreStopGate.requestStart()) return

        val service = serviceControl?.get()?.getService() ?: return
        val guid = mainStorage?.decodeString(MmkvManager.KEY_SELECTED_SERVER)
            ?.takeIf { it.isNotBlank() } ?: return
        val config = MmkvManager.decodeServerConfig(guid) ?: return
        if (v2rayPoint.isRunning) return
        invalidateLiveDelay()
        val result = V2rayConfigUtil.getV2rayConfig(service, guid)
        if (!result.status) {
            MessageUtil.sendMsg2UI(service, AppConfig.MSG_STATE_START_FAILURE, "")
            return
        }

        var receiverRegistered = false
        var fragmentor: backServ? = null
        try {
            // Configuration must be valid before allocating optional local listeners.
            // Read the exact keys used by the existing GFW settings screen.
            val outbound = config.getProxyOutbound()
            val options = runCatching {
                val preferences = my_preference_storage(service)
                FragmentorOptions.fromSettings(
                    outbound?.getServerAddress(), outbound?.getServerPort()
                ) { key, fallback -> preferences.get_value(key, fallback) }
            }.getOrNull()
            if (options != null) {
                fragmentor = backServ(
                    service.applicationContext, service, options.targetHost,
                    options.targetPort, options.fragments, options.delaySeconds,
                    false // HTTPS/DoH is optional; no public setting identifies YouTube mode.
                )
                fragmentor.start_TLS_service()
                fragmentor.start_HTTPS_service()
                TLS_serv = fragmentor
            }

            val filter = IntentFilter(AppConfig.BROADCAST_ACTION_SERVICE)
            filter.addAction(Intent.ACTION_SCREEN_ON)
            filter.addAction(Intent.ACTION_SCREEN_OFF)
            filter.addAction(Intent.ACTION_USER_PRESENT)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                service.registerReceiver(mMsgReceive, filter, Context.RECEIVER_NOT_EXPORTED)
            } else service.registerReceiver(mMsgReceive, filter)
            receiverRegistered = true

            v2rayPoint.configureFileContent = result.content
            v2rayPoint.domainName = config.getV2rayPointDomainAndPort()
            currentConfig = config
            v2rayPoint.runLoop(settingsStorage?.decodeBool(AppConfig.PREF_PREFER_IPV6) ?: false)
            if (!v2rayPoint.isRunning) error("Native core failed to enter running state")

            // Xray's SOCKS listener is ready; Psiphon VPN routing may still be connecting.
            val state = if (VpnModeSelection.usesPsiphon(settingsStorage?.decodeString(AppConfig.PREF_MODE))) {
                AppConfig.MSG_STATE_RUNNING
            } else AppConfig.MSG_STATE_START_SUCCESS
            MessageUtil.sendMsg2UI(service, state, "")
            runCatching { showNotification() }.onFailure { Log.d(ANG_PACKAGE, "Notification: $it") }
        } catch (failure: Exception) {
            Log.d(ANG_PACKAGE, "Native core start failed: $failure")
            runCatching { fragmentor?.stop_HTTPS_service() }
            runCatching { fragmentor?.stop_TLS_service() }
            if (TLS_serv === fragmentor) TLS_serv = null
            if (receiverRegistered) {
                runCatching { service.unregisterReceiver(mMsgReceive) }
            }
            currentConfig = null
            MessageUtil.sendMsg2UI(service, AppConfig.MSG_STATE_START_FAILURE, "")
        }
    }

    @Synchronized
    fun stopV2rayPoint() {
        invalidateLiveDelay()
        // Idempotent while an earlier stopLoop remains in flight.
        val stopToken = coreStopGate.beginStop() ?: return
        val service = serviceControl?.get()?.getService()
        val fragmentor = TLS_serv
        TLS_serv = null

        nativeCleanupScope.launch {
            var stopped = false
            try {
                if (v2rayPoint.isRunning) v2rayPoint.stopLoop()
                stopped = !v2rayPoint.isRunning
            } catch (failure: Exception) {
                Log.d(ANG_PACKAGE, "Native stopLoop failed: $failure")
            } finally {
                runCatching { fragmentor?.stop_HTTPS_service() }
                runCatching { fragmentor?.stop_TLS_service() }
            }

            // A successful stop broadcast must follow native socket cleanup,
            // not precede it as it did with unowned GlobalScope.
            withContext(Dispatchers.Main) {
                if (stopped) {
                    cancelNotificationFor(service)
                    if (service != null) {
                        runCatching { service.unregisterReceiver(mMsgReceive) }
                        MessageUtil.sendMsg2UI(service, AppConfig.MSG_STATE_STOP_SUCCESS, "")
                    }
                    currentConfig = null
                } else if (service != null) {
                    // Do not claim the core stopped if stopLoop failed or is still running.
                    val actualState = if (v2rayPoint.isRunning) {
                        AppConfig.MSG_STATE_RUNNING
                    } else {
                        AppConfig.MSG_STATE_NOT_RUNNING
                    }
                    MessageUtil.sendMsg2UI(service, actualState, "")
                }

                val restartToken = coreStopGate.completeStop(stopToken, stopped)
                if (restartToken != null && coreStopGate.canResume(restartToken)) {
                    startV2rayPoint()
                }
            }
        }
    }

    private class ReceiveMessageHandler : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            val serviceControl = serviceControl?.get() ?: return
            when (intent?.getIntExtra("key", 0)) {
                AppConfig.MSG_REGISTER_CLIENT -> {
                    //Logger.e("ReceiveMessageHandler", intent?.getIntExtra("key", 0).toString())
                    if (v2rayPoint.isRunning) {
                        MessageUtil.sendMsg2UI(serviceControl.getService(), AppConfig.MSG_STATE_RUNNING, "")
                    } else {
                        MessageUtil.sendMsg2UI(serviceControl.getService(), AppConfig.MSG_STATE_NOT_RUNNING, "")
                    }
                }
                AppConfig.MSG_UNREGISTER_CLIENT -> {
                    // nothing to do
                }
                AppConfig.MSG_STATE_START -> {
                    // nothing to do
                }
                AppConfig.MSG_STATE_STOP -> {
                    serviceControl.stopService()
                }
                AppConfig.MSG_STATE_RESTART -> {
                    startV2rayPoint()
                }
                AppConfig.MSG_MEASURE_DELAY -> {
                    measureV2rayDelay()
                }
            }

            when (intent?.action) {
                Intent.ACTION_SCREEN_OFF -> {
                    Log.d(ANG_PACKAGE, "SCREEN_OFF, stop querying stats")
                    stopSpeedNotification()
                }
                Intent.ACTION_SCREEN_ON -> {
                    Log.d(ANG_PACKAGE, "SCREEN_ON, start querying stats")
                    startSpeedNotification()
                }
            }
        }
    }

    @Synchronized
    private fun measureV2rayDelay() {
        // Only the most recent request for this selected profile can publish.
        invalidateLiveDelay()
        val service = serviceControl?.get()?.getService() ?: return
        val guid = mainStorage?.decodeString(MmkvManager.KEY_SELECTED_SERVER)
            ?.takeIf { it.isNotBlank() } ?: return
        if (!v2rayPoint.isRunning) return

        val runId = liveDelayTracker.begin(listOf(guid))
        liveDelayJob = liveDelayScope.launch {
            var time = -1L
            var errstr = ""
            try {
                time = v2rayPoint.measureDelay(AppConfig.DelayTestUrl)
            } catch (cancelled: CancellationException) {
                return@launch
            } catch (e: Exception) {
                Log.d(ANG_PACKAGE, "measureV2rayDelay: $e")
                errstr = e.message?.substringAfter("\":") ?: "empty message"
            }

            // Serialize this short publish gate with core start/stop so an
            // obsolete JNI completion cannot emit a success after disconnect.
            synchronized(V2RayServiceManager) {
                if (!isActive || !v2rayPoint.isRunning ||
                    serviceControl?.get()?.getService() !== service ||
                    mainStorage?.decodeString(MmkvManager.KEY_SELECTED_SERVER) != guid ||
                    !liveDelayTracker.accepts(runId, guid)
                ) return@synchronized
                val result = if (time == -1L) {
                    service.getString(R.string.connection_test_error, errstr)
                } else {
                    service.getString(R.string.connection_test_available, time)
                }
                MessageUtil.sendMsg2UI(service, AppConfig.MSG_MEASURE_DELAY_SUCCESS, result)
            }
        }
    }

    private fun showNotification() {
        val service = serviceControl?.get()?.getService() ?: return
        val startMainIntent = Intent(service, MainActivity::class.java)
        val contentPendingIntent = PendingIntent.getActivity(service,
                NOTIFICATION_PENDING_INTENT_CONTENT, startMainIntent,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            } else {
                PendingIntent.FLAG_UPDATE_CURRENT
            })

        val stopV2RayIntent = Intent(AppConfig.BROADCAST_ACTION_SERVICE)
        stopV2RayIntent.`package` = ANG_PACKAGE
        stopV2RayIntent.putExtra("key", AppConfig.MSG_STATE_STOP)

        val stopV2RayPendingIntent = PendingIntent.getBroadcast(service,
                NOTIFICATION_PENDING_INTENT_STOP_V2RAY, stopV2RayIntent,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            } else {
                PendingIntent.FLAG_UPDATE_CURRENT
            })

        val channelId =
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    createNotificationChannel()
                } else {
                    // If earlier version channel ID is not used
                    // https://developer.android.com/reference/android/support/v4/app/NotificationCompat.Builder.html#NotificationCompat.Builder(android.content.Context)
                    ""
                }

        mBuilder = NotificationCompat.Builder(service, channelId)
                .setSmallIcon(R.drawable.ic_stat_name)
            // ------- GFW-knocker  ----------------------
//                .setContentTitle("فعلا فقط یوتیوب")
                .setContentTitle(currentConfig?.remarks)
            // ------- GFW-knocker  ----------------------
                .setPriority(NotificationCompat.PRIORITY_MIN)
                .setOngoing(true)
                .setShowWhen(false)
                .setOnlyAlertOnce(true)
                .setContentIntent(contentPendingIntent)
                .addAction(R.drawable.ic_close_grey_800_24dp,
                        service.getString(R.string.notification_action_stop_v2ray),
                        stopV2RayPendingIntent)
        //.build()

        //mBuilder?.setDefaults(NotificationCompat.FLAG_ONLY_ALERT_ONCE)  //取消震动,铃声其他都不好使

        service.startForeground(NOTIFICATION_ID, mBuilder?.build())
    }

    @RequiresApi(Build.VERSION_CODES.O)
    private fun createNotificationChannel(): String {
        val channelId = "RAY_NG_M_CH_ID"
        val channelName = "V2rayNG Background Service"
        val chan = NotificationChannel(channelId,
                channelName, NotificationManager.IMPORTANCE_HIGH)
        chan.lightColor = Color.DKGRAY
        chan.importance = NotificationManager.IMPORTANCE_NONE
        chan.lockscreenVisibility = Notification.VISIBILITY_PRIVATE
        getNotificationManager()?.createNotificationChannel(chan)
        return channelId
    }

    fun cancelNotification() {
        cancelNotificationFor(serviceControl?.get()?.getService())
    }

    private fun cancelNotificationFor(service: Service?) {
        runCatching { service?.stopForeground(true) }
        mBuilder = null
        mSubscription?.unsubscribe()
        mSubscription = null
    }

    private fun updateNotification(contentText: String?, proxyTraffic: Long, directTraffic: Long) {
        if (mBuilder != null) {
            if (proxyTraffic < NOTIFICATION_ICON_THRESHOLD && directTraffic < NOTIFICATION_ICON_THRESHOLD) {
                mBuilder?.setSmallIcon(R.drawable.ic_stat_name)
            } else if (proxyTraffic > directTraffic) {
                mBuilder?.setSmallIcon(R.drawable.ic_stat_proxy)
            } else {
                mBuilder?.setSmallIcon(R.drawable.ic_stat_direct)
            }
            mBuilder?.setStyle(NotificationCompat.BigTextStyle().bigText(contentText))
            mBuilder?.setContentText(contentText) // Emui4.1 need content text even if style is set as BigTextStyle
            getNotificationManager()?.notify(NOTIFICATION_ID, mBuilder?.build())
        }
    }

    private fun getNotificationManager(): NotificationManager? {
        if (mNotificationManager == null) {
            val service = serviceControl?.get()?.getService() ?: return null
            mNotificationManager = service.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        }
        return mNotificationManager
    }

    private fun startSpeedNotification() {
        if (mSubscription == null &&
                v2rayPoint.isRunning &&
                settingsStorage?.decodeBool(AppConfig.PREF_SPEED_ENABLED) == true) {
            var lastZeroSpeed = false
            val outboundTags = currentConfig?.getAllOutboundTags()
            outboundTags?.remove(TAG_DIRECT)

            mSubscription = Observable.interval(3, java.util.concurrent.TimeUnit.SECONDS)
                    .subscribe {
                        val queryTime = System.currentTimeMillis()
                        val sinceLastQueryInSeconds = (queryTime - lastQueryTime) / 1000.0
                        var proxyTotal = 0L
                        val text = StringBuilder()
                        outboundTags?.forEach {
                            val up = v2rayPoint.queryStats(it, "uplink")
                            val down = v2rayPoint.queryStats(it, "downlink")
                            if (up + down > 0) {
                                appendSpeedString(text, it, up / sinceLastQueryInSeconds, down / sinceLastQueryInSeconds)
                                proxyTotal += up + down
                            }
                        }
                        val directUplink = v2rayPoint.queryStats(TAG_DIRECT, "uplink")
                        val directDownlink = v2rayPoint.queryStats(TAG_DIRECT, "downlink")
                        val zeroSpeed = (proxyTotal == 0L && directUplink == 0L && directDownlink == 0L)
                        if (!zeroSpeed || !lastZeroSpeed) {
                            if (proxyTotal == 0L) {
                                appendSpeedString(text, outboundTags?.firstOrNull(), 0.0, 0.0)
                            }
                            appendSpeedString(text, TAG_DIRECT, directUplink / sinceLastQueryInSeconds,
                                    directDownlink / sinceLastQueryInSeconds)
                            updateNotification(text.toString(), proxyTotal, directDownlink + directUplink)
                        }
                        lastZeroSpeed = zeroSpeed
                        lastQueryTime = queryTime
                    }
        }
    }

    private fun appendSpeedString(text: StringBuilder, name: String?, up: Double, down: Double) {
        var n = name ?: "no tag"
        n = n.substring(0, min(n.length, 6))
        text.append(n)
        for (i in n.length..6 step 2) {
            text.append("\t")
        }
        text.append("•  ${up.toLong().toSpeedString()}↑  ${down.toLong().toSpeedString()}↓\n")
    }

    private fun stopSpeedNotification() {
        if (mSubscription != null) {
            mSubscription?.unsubscribe() //stop queryStats
            mSubscription = null
            updateNotification(currentConfig?.remarks, 0, 0)
        }
    }
}
