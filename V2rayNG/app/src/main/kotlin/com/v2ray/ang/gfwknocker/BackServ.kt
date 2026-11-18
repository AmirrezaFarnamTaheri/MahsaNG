package com.v2ray.ang.gfwknocker

import android.app.Service
import android.content.Context
import com.v2ray.ang.service.FragmentorListenerExit


class backServ(ctx1 : Context , svc1 : Service , target_ip : String , target_port : Int , nfrag : Int , sleepfrag : Double , is_youtube : Boolean ){
    private var DoH_service: DoH_over_Fragment? = null
    private var HTTPS_serv: HTTPS_Fragmentor? = null
    private var TLS_serv: TLS_Fragmentor? = null
    private var ctx = ctx1
    private var svc = svc1

    // constructor
    init {

        // The public source does not contain config_pkg_reader or its DNS rules.
        // Do not guess DoH targets or silently start a partially configured proxy.
        require(!is_youtube) { "YouTube/DoH mode has no published config parser" }

        TLS_serv = TLS_Fragmentor(
            "127.0.0.1", 2500,
            target_ip , target_port, true,
            nfrag, sleepfrag
        )



        // No optional DoH listener is constructed until its source and rules are restored.

//        DoH_service!!.query("instagram.com")
//        DoH_service!!.query("youtube.com")
//        DoH_service!!.query("youtu.be")
//        DoH_service!!.query("fb.com")
//        DoH_service!!.query("twitter.com")
//        DoH_service!!.query("google.com")
//        DoH_service!!.query("google.com")
//        DoH_service!!.query("fb.com")
//        DoH_service!!.query("google.com")

    }


    fun start_HTTPS_service() {
        // YouTube/DoH forwarding is optional; it is not created for normal profiles.
        HTTPS_serv?.let { if (it.state == Thread.State.NEW) it.start() }
    }

    fun stop_HTTPS_service() {
        runCatching { HTTPS_serv?.safely_stop_server() }
        runCatching { DoH_service?.safely_stop_DoH() }
    }

    fun start_TLS_service() {
        TLS_serv?.let { if (it.state == Thread.State.NEW) it.start() }
    }

    fun stop_TLS_service() {
        runCatching { TLS_serv?.safely_stop_server() }
    }

    /**
     * Ask both optional local listeners to stop, then observe actual listener
     * thread exit. A stop request alone is not exit evidence.
     * This does not await active per-client handler threads or the VPN TUN.
     */
    fun stopAndAwaitListeners(timeoutMillis: Long = 3_000L): Boolean {
        // Always attempt both stops even if either request fails.
        val httpsStopReturned = runCatching { stop_HTTPS_service() }.isSuccess
        val tlsStopReturned = runCatching { stop_TLS_service() }.isSuccess
        val listenersExited = FragmentorListenerExit.allExitedWithin(
            timeoutMillis, HTTPS_serv, TLS_serv
        )
        return httpsStopReturned && tlsStopReturned && listenersExited
    }
}

