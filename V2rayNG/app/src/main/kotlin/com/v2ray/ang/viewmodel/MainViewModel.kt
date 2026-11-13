package com.v2ray.ang.viewmodel

import android.app.Application
import android.content.*
import android.os.Build
import android.util.Log
import android.view.LayoutInflater
import android.widget.ArrayAdapter
import androidx.appcompat.app.AlertDialog
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import com.tencent.mmkv.MMKV
import com.v2ray.ang.AngApplication
import com.v2ray.ang.AppConfig
import com.v2ray.ang.AppConfig.ANG_PACKAGE
import com.v2ray.ang.R
import com.v2ray.ang.databinding.DialogConfigFilterBinding
import com.v2ray.ang.dto.*
import com.v2ray.ang.extension.toast
import com.v2ray.ang.util.*
import com.v2ray.ang.util.MmkvManager.KEY_ANG_CONFIGS
import kotlinx.coroutines.*
import java.util.*

class MainViewModel(application: Application) : AndroidViewModel(application) {
    private val mainStorage by lazy { MMKV.mmkvWithID(MmkvManager.ID_MAIN, MMKV.MULTI_PROCESS_MODE) }
    private val serverRawStorage by lazy { MMKV.mmkvWithID(MmkvManager.ID_SERVER_RAW, MMKV.MULTI_PROCESS_MODE) }
    private val settingsStorage by lazy { MMKV.mmkvWithID(MmkvManager.ID_SETTING, MMKV.MULTI_PROCESS_MODE) }

    var serverList = MmkvManager.decodeServerList()
    var subscriptionId: String = ""
    var keywordFilter: String = ""
        private set
    val serversCache = mutableListOf<ServersCache>()
    val isRunning by lazy { MutableLiveData<Boolean>() }
    val updateListAction by lazy { MutableLiveData<Int>() }
    val updateTestResultAction by lazy { MutableLiveData<String>() }

    private val tcpingTestScope by lazy { CoroutineScope(SupervisorJob() + Dispatchers.IO) }
    private val testRuns = TestRunTracker()
    private var realPingScheduleJob: Job? = null
    private var nativeTestRunPending = false
    private var broadcastRegistered = false

    /**
     * Called on the UI thread. Snapshot identifiers before scheduling any background work.
     * A new run invalidates both previous TCP callbacks and in-flight native callbacks.
     */
    private fun beginTestRun(visibleGuids: List<String>, native: Boolean): String {
        tcpingTestScope.coroutineContext[Job]?.cancelChildren()
        realPingScheduleJob?.cancel()
        SpeedtestUtil.closeAllTcpSockets()
        val runId = testRuns.begin(visibleGuids)
        // Starting a TCP-only run must not launch a native service unnecessarily.
        // If a real-ping run preceded it, this command cancels that native run.
        if (native || nativeTestRunPending) {
            MessageUtil.sendMsg2TestService(getApplication(), AppConfig.MSG_MEASURE_CONFIG_CANCEL, runId)
        }
        nativeTestRunPending = native
        MmkvManager.clearTestDelayResults(visibleGuids)
        updateListAction.value = -1
        return runId
    }

    fun startListenBroadcast() {
        if (broadcastRegistered) return
        isRunning.value = false
        val app = getApplication<AngApplication>()
        val filter = IntentFilter(AppConfig.BROADCAST_ACTION_ACTIVITY)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            app.registerReceiver(mMsgReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else app.registerReceiver(mMsgReceiver, filter)
        broadcastRegistered = true
        MessageUtil.sendMsg2Service(app, AppConfig.MSG_REGISTER_CLIENT, "")
    }

    override fun onCleared() {
        if (broadcastRegistered) {
            getApplication<AngApplication>().unregisterReceiver(mMsgReceiver)
            broadcastRegistered = false
        }
        testRuns.invalidate()
        realPingScheduleJob?.cancel()
        // Do not send a global native Cancel from an obsolete ViewModel: a new
        // activity may already own the native service with a newer run token.
        tcpingTestScope.cancel()
        SpeedtestUtil.closeAllTcpSockets()
        Log.i(ANG_PACKAGE, "Main ViewModel is cleared")
        super.onCleared()
    }

    fun reloadServerList() {
        serverList = MmkvManager.decodeServerList()
        updateCache()
        updateListAction.value = -1
    }

    fun removeServer(guid: String) {
        serverList.remove(guid)
        MmkvManager.removeServer(guid)
        val index = getPosition(guid)
        if(index >= 0){
            serversCache.removeAt(index)
        }
    }

    fun appendCustomConfigServer(server: String) {
        val config = ServerConfig.create(EConfigType.CUSTOM)
        config.remarks = System.currentTimeMillis().toString()
        config.subscriptionId = subscriptionId
        config.fullConfig = Gson().fromJson(server, V2rayConfig::class.java)
        val key = MmkvManager.encodeServerConfig("", config)
        serverRawStorage?.encode(key, server)
        serverList.add(0, key)
        serversCache.add(0, ServersCache(key,config))
    }

    fun swapServer(fromPosition: Int, toPosition: Int) {
        val firstGuid = serversCache.getOrNull(fromPosition)?.guid ?: return
        val secondGuid = serversCache.getOrNull(toPosition)?.guid ?: return
        if (MmkvManager.swapServerPositions(firstGuid, secondGuid)) {
            serverList = MmkvManager.decodeServerList()
            Collections.swap(serversCache, fromPosition, toPosition)
        } else {
            // Another writer may have replaced one of the profiles.
            reloadServerList()
        }
    }

    @Synchronized
    fun updateCache() {
        serversCache.clear()
        for (guid in serverList) {
            val config = MmkvManager.decodeServerConfig(guid) ?: continue
            if (subscriptionId.isNotEmpty() && subscriptionId != config.subscriptionId) {
                continue
            }

            if (keywordFilter.isEmpty() || config.remarks.contains(keywordFilter)) {
                serversCache.add(ServersCache(guid, config))
            }
        }
    }

    fun testAllTcping() {
        val snapshot = synchronized(this) { serversCache.toList() }
        val runId = beginTestRun(snapshot.map { it.guid }, native = false)
        getApplication<AngApplication>().toast(R.string.connection_test_testing)

        // Make an immutable, transport-eligible target list before any worker
        // launches. UDP/custom profiles remain UNKNOWN, not false TCP failures.
        val targets = snapshot.mapNotNull { item ->
            val outbound = item.config.getProxyOutbound() ?: return@mapNotNull null
            if (!TcpProbeEligibility.supportsTcpConnect(
                    item.config.configType.name, outbound.protocol, outbound.streamSettings?.network
                )) return@mapNotNull null
            val address = outbound.getServerAddress() ?: return@mapNotNull null
            val port = outbound.getServerPort() ?: return@mapNotNull null
            Triple(item.guid, address, port)
        }
        // A new run snapshots its concurrency: preferences cannot change active
        // scheduling. At most 16 workers exist, even for thousands of targets.
        val concurrency = BoundedProbeQueue.concurrencyFromStored(
            settingsStorage?.decodeString(AppConfig.PREF_TCP_PROBE_CONCURRENCY)
        )
        val queue = BoundedProbeQueue(targets, concurrency)
        repeat(queue.workerCount) {
            tcpingTestScope.launch {
                while (isActive) {
                    val (guid, address, port) = queue.claim() ?: break
                    if (!testRuns.accepts(runId, guid)) continue
                    val delay = SpeedtestUtil.tcping(address, port)
                    withContext(Dispatchers.Main) {
                        // Share forgetGuid's lock through the final persistent write.
                        val published = testRuns.publishIfCurrent(runId, guid) {
                            if (MmkvManager.decodeServerConfig(guid) == null) false
                            else {
                                MmkvManager.encodeServerTestDelayMillis(guid, delay)
                                true
                            }
                        }
                        if (published) updateListAction.value = getPosition(guid)
                    }
                }
            }
        }
    }

    fun testAllRealPing() {
        // Never iterate serversCache on Dispatchers.Default; reloading clears the mutable list.
        val guids = synchronized(this) { serversCache.map { it.guid } }
        val runId = beginTestRun(guids, native = true)
        getApplication<AngApplication>().toast(R.string.connection_test_testing)

        realPingScheduleJob = viewModelScope.launch(Dispatchers.Default) {
            for (guid in guids) {
                if (!isActive || !testRuns.accepts(runId, guid)) break
                val config = V2rayConfigUtil.getV2rayConfig(getApplication(), guid)
                if (config.status && isActive && testRuns.accepts(runId, guid)) {
                    MessageUtil.sendMsg2TestService(
                        getApplication(),
                        AppConfig.MSG_MEASURE_CONFIG,
                        ConfigTestRequest(guid, config.content, runId),
                    )
                }
            }
        }
    }

    fun testCurrentServerRealPing() {
        MessageUtil.sendMsg2Service(getApplication(), AppConfig.MSG_MEASURE_DELAY, "")
    }

    fun filterConfig(context :Context) {
        val subscriptions = MmkvManager.decodeSubscriptions()
        val listId = subscriptions.map { it.first }.toList().toMutableList()
        val listRemarks = subscriptions.map { it.second.remarks }.toList().toMutableList()
        listRemarks += context.getString(R.string.filter_config_all)
        val checkedItem = if (subscriptionId.isNotEmpty()) {
            listId.indexOf(subscriptionId)
        } else {
            listRemarks.count() - 1
        }

        val ivBinding = DialogConfigFilterBinding.inflate(LayoutInflater.from(context))
        ivBinding.spSubscriptionId.adapter = ArrayAdapter<String>( context, android.R.layout.simple_spinner_dropdown_item, listRemarks)
        ivBinding.spSubscriptionId.setSelection(checkedItem)
        ivBinding.etKeyword.text = Utils.getEditable(keywordFilter)
        val builder = AlertDialog.Builder(context).setView(ivBinding.root)
        builder.setTitle(R.string.title_filter_config)
        builder.setPositiveButton(R.string.tasker_setting_confirm) { dialogInterface: DialogInterface?, _: Int ->
            try {
                val position = ivBinding.spSubscriptionId.selectedItemPosition
                subscriptionId = if (listRemarks.count() - 1 == position) {
                    ""
                } else {
                    subscriptions[position].first
                }
                keywordFilter = ivBinding.etKeyword.text.toString()
                reloadServerList()

                dialogInterface?.dismiss()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
        builder.show()
//        AlertDialog.Builder(context)
//            .setSingleChoiceItems(listRemarks.toTypedArray(), checkedItem) { dialog, i ->
//                try {
//                    subscriptionId = if (listRemarks.count() - 1 == i) {
//                        ""
//                    } else {
//                        subscriptions[i].first
//                    }
//                    reloadServerList()
//                    dialog.dismiss()
//                } catch (e: Exception) {
//                    e.printStackTrace()
//                }
//            }.show()
    }

    fun getPosition(guid: String) : Int {
        serversCache.forEachIndexed { index, it ->
            if (it.guid == guid)
                return index
        }
        return -1
    }

    private val mMsgReceiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            when (intent?.getIntExtra("key", 0)) {
                AppConfig.MSG_STATE_RUNNING -> {
                    isRunning.value = true
                }
                AppConfig.MSG_STATE_NOT_RUNNING -> {
                    isRunning.value = false
                }
                AppConfig.MSG_STATE_START_SUCCESS -> {
                    getApplication<AngApplication>().toast(R.string.toast_services_success)
                    isRunning.value = true
                }
                AppConfig.MSG_STATE_START_FAILURE -> {
                    getApplication<AngApplication>().toast(R.string.toast_services_failure)
                    isRunning.value = false
                }
                AppConfig.MSG_STATE_STOP_SUCCESS -> {
                    isRunning.value = false
                }
                AppConfig.MSG_MEASURE_DELAY_SUCCESS -> {
                    updateTestResultAction.value = intent.getStringExtra("content")
                }
                AppConfig.MSG_MEASURE_CONFIG_SUCCESS -> {
                    val result = intent.getSerializableExtra("content") as? ConfigTestResult ?: return
                    val published = testRuns.publishIfCurrent(result.runId, result.guid) {
                        if (MmkvManager.decodeServerConfig(result.guid) == null) false
                        else {
                            MmkvManager.encodeServerTestDelayMillis(result.guid, result.delayMillis)
                            true
                        }
                    }
                    if (published) updateListAction.value = getPosition(result.guid)
                }
            }
        }
    }
}
