package com.v2ray.ang.ui

import android.os.Bundle
import android.text.InputType
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.lifecycle.lifecycleScope
import com.v2ray.ang.util.Utils
import com.v2ray.ang.R
import com.v2ray.ang.util.HttpsEvidence
import com.v2ray.ang.util.HttpsEvidenceRoute
import com.v2ray.ang.util.HttpsObservation
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.DateFormat
import java.util.Date

/** Explicit single-request TLS/HTTPS evidence; no scan plan, health advice or saved-profile writes. */
class HttpsEvidenceActivity : BaseActivity() {
    private lateinit var host: EditText
    private lateinit var tlsPort: EditText
    private lateinit var proxyPort: EditText
    private lateinit var timeout: EditText
    private lateinit var direct: Button
    private lateinit var viaProxy: Button
    private lateinit var stop: Button
    private lateinit var output: TextView
    private var generation = 0L
    private var job: Job? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = getString(R.string.https_evidence_title)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        val scale = resources.displayMetrics.density
        fun dp(value: Int) = (scale * value + 0.5f).toInt()
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(14), dp(20), dp(24))
        }
        fun label(textRes: Int) {
            column.addView(TextView(this).apply {
                setText(textRes)
                textSize = 16f
                textDirection = View.TEXT_DIRECTION_FIRST_STRONG
                setPadding(0, dp(10), 0, dp(4))
            })
        }
        fun field(labelRes: Int, defaultText: String, number: Boolean = false): EditText {
            label(labelRes)
            return EditText(this).also {
                it.setText(defaultText)
                it.setSingleLine(true)
                if (number) it.inputType = InputType.TYPE_CLASS_NUMBER
                it.contentDescription = getString(labelRes)
                column.addView(it)
            }
        }
        label(R.string.https_evidence_route_warning)
        host = field(R.string.https_evidence_host, "example.com")
        tlsPort = field(R.string.https_evidence_tls_port, "443", true)
        proxyPort = field(R.string.https_evidence_proxy_port,
            Utils.getConfiguredHttpPortOrNull()?.toString() ?: "", true)
        timeout = field(R.string.https_evidence_timeout, "4000", true)
        direct = Button(this).apply {
            setText(R.string.https_evidence_direct)
            setOnClickListener { runEvidence(viaLocalProxy = false) }
        }
        viaProxy = Button(this).apply {
            setText(R.string.https_evidence_via_proxy)
            setOnClickListener { runEvidence(viaLocalProxy = true) }
        }
        stop = Button(this).apply {
            setText(R.string.https_evidence_stop)
            visibility = View.GONE
            setOnClickListener { stopRun() }
        }
        output = TextView(this).apply {
            setText(R.string.https_evidence_ready)
            textSize = 15f
            setTextIsSelectable(true)
            textDirection = View.TEXT_DIRECTION_FIRST_STRONG
            setPadding(0, dp(14), 0, dp(24))
        }
        listOf(direct, viaProxy, stop, output).forEach(column::addView)
        setContentView(ScrollView(this).apply { addView(column) })
    }

    private fun runEvidence(viaLocalProxy: Boolean) {
        if (job?.isActive == true) return
        val deadline = timeout.text.toString().toIntOrNull()
        val port = (if (viaLocalProxy) proxyPort else tlsPort).text.toString().toIntOrNull()
        if (deadline == null || deadline !in 300..10_000 || port == null || port !in 1..65535) {
            output.setText(R.string.https_evidence_invalid)
            return
        }
        val endpoint = host.text.toString()
        val token = ++generation
        direct.isEnabled = false
        viaProxy.isEnabled = false
        stop.visibility = View.VISIBLE
        output.setText(R.string.https_evidence_running)
        job = lifecycleScope.launch {
            try {
                val observation = withContext(Dispatchers.IO) {
                    if (viaLocalProxy) HttpsEvidence.throughLocalHttpProxy(port, deadline)
                    else HttpsEvidence.directEndpoint(endpoint, port, deadline)
                }
                if (token == generation && isActive) render(observation)
            } catch (_: Exception) {
                if (token == generation) output.setText(R.string.https_evidence_invalid)
            } finally {
                if (token == generation) {
                    direct.isEnabled = true
                    viaProxy.isEnabled = true
                    stop.visibility = View.GONE
                }
            }
        }
    }

    private fun render(result: HttpsObservation) {
        fun clean(value: String?): String = value?.replace(Regex("[\\p{Cntrl}]"), " ")?.take(140) ?: "—"
        fun line(key: Int, value: String) = "${getString(key)}: $value\n"
        output.text = buildString {
            append(line(R.string.https_evidence_route, getString(if (result.route == HttpsEvidenceRoute.LOCAL_HTTP_PROXY)
                R.string.https_evidence_route_proxy else R.string.https_evidence_route_app)))
            append(line(R.string.https_evidence_result, result.status))
            append(line(R.string.https_evidence_elapsed, "${result.elapsedMs} ms"))
            result.responseCode?.let { append(line(R.string.https_evidence_http_code, it.toString())) }
            result.cipherSuite?.let { append(line(R.string.https_evidence_cipher, clean(it))) }
            result.certificateSubject?.let { append(line(R.string.https_evidence_cert, clean(it))) }
            result.certificateSha256?.let { append(line(R.string.https_evidence_fingerprint, clean(it))) }
            result.certificateExpiresAt?.let {
                append(line(R.string.https_evidence_expiry, DateFormat.getDateInstance().format(Date(it))))
            }
            result.serverHeader?.let { append(line(R.string.https_evidence_server, clean(it))) }
            result.altSvcHeader?.let { append(line(R.string.https_evidence_alt_svc, clean(it))) }
            result.contentType?.let { append(line(R.string.https_evidence_type, clean(it))) }
            result.contentLength?.let { append(line(R.string.https_evidence_length, it.toString())) }
            if (result.route == HttpsEvidenceRoute.LOCAL_HTTP_PROXY) {
                append(line(R.string.https_evidence_connectivity, result.connectivity204.toString()))
            }
        }
    }

    private fun stopRun() {
        generation++
        job?.cancel()
        job = null
        direct.isEnabled = true
        viaProxy.isEnabled = true
        stop.visibility = View.GONE
        output.setText(R.string.https_evidence_stopped)
    }

    override fun onDestroy() {
        generation++
        job?.cancel()
        super.onDestroy()
    }
    override fun onSupportNavigateUp(): Boolean { finish(); return true }
}
