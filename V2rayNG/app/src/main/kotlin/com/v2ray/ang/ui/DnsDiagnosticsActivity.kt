package com.v2ray.ang.ui

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.text.InputType
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.lifecycle.lifecycleScope
import com.v2ray.ang.R
import com.v2ray.ang.util.Utils
import com.v2ray.ang.util.dns.DnsResolverDefaults
import com.v2ray.ang.util.dns.DnsProbe
import com.v2ray.ang.util.dns.DnsProbeResult
import com.v2ray.ang.util.dns.DnsResolverInput
import com.v2ray.ang.util.dns.DnsType
import com.v2ray.ang.util.dns.DnsWire
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.Locale
import java.util.concurrent.atomic.AtomicInteger

/** User-initiated read-only queries: packets follow the app's current VPN/network route. */
class DnsDiagnosticsActivity : BaseActivity() {
    private lateinit var domains: EditText
    private lateinit var resolvers: EditText
    private lateinit var types: EditText
    private lateinit var timeout: EditText
    private lateinit var diagnose: Button
    private lateinit var scan: Button
    private lateinit var cancel: Button
    private lateinit var filterButton: Button
    private lateinit var sortButton: Button
    private lateinit var status: TextView
    private lateinit var resultsText: TextView
    private lateinit var routeInfo: TextView
    private val results = mutableListOf<DnsProbeResult>()
    private var filter = 0
    private var fastestFirst = false
    private var generation = 0L
    private var job: Job? = null
    private var completed = 0
    private var total = 0
    private var runNetwork: Network? = null
    private var runRouteHint: Int? = null
    private var observedNetworkChange = false
    private var lastRender = 0L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = getString(R.string.dns_diagnostics_title)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        val scale = resources.displayMetrics.density
        fun dp(value: Int) = (value * scale + 0.5f).toInt()
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(12), dp(20), dp(24))
        }
        fun label(res: Int) {
            column.addView(TextView(this).apply {
                setText(res)
                textSize = 16f
                setPadding(0, dp(12), 0, dp(4))
                textDirection = View.TEXT_DIRECTION_FIRST_STRONG
            })
        }
        fun input(labelId: Int, initial: String, multiline: Boolean = true): EditText {
            label(labelId)
            return EditText(this).also { field ->
                field.setText(initial)
                field.setSingleLine(!multiline)
                field.inputType = if (multiline) InputType.TYPE_CLASS_TEXT or
                    InputType.TYPE_TEXT_FLAG_MULTI_LINE else InputType.TYPE_CLASS_NUMBER
                field.contentDescription = getString(labelId)
                column.addView(field)
            }
        }
        label(R.string.dns_diagnostics_route_warning)
        domains = input(R.string.dns_diagnostics_domains, "example.com")
        // Read existing Xray settings without interpreting them as the active DNS path.
        // Credential-bearing DoH/DoQ URLs must never be echoed into this UI.
        val configuredResolvers = DnsResolverDefaults.fromConfiguredEntries(Utils.getRemoteDnsServers())
        resolvers = input(R.string.dns_diagnostics_resolvers, configuredResolvers.suggestedInput)
        val visibleConfigured = configuredResolvers.numericResolvers.take(4).joinToString(", ")
            .ifBlank { getString(R.string.dns_diagnostics_no_plain_resolver) }
        column.addView(TextView(this).apply {
            text = getString(R.string.dns_diagnostics_configured, visibleConfigured,
                configuredResolvers.unsupportedCount + configuredResolvers.additionalNumericCount)
            textSize = 13f
            textDirection = View.TEXT_DIRECTION_FIRST_STRONG
        })
        types = input(R.string.dns_diagnostics_types, "A,AAAA")
        timeout = input(R.string.dns_diagnostics_timeout, "1500", multiline = false)
        diagnose = Button(this).apply {
            setText(R.string.dns_diagnostics_one)
            setOnClickListener { begin(single = true) }
        }
        scan = Button(this).apply {
            setText(R.string.dns_diagnostics_scan)
            setOnClickListener { begin(single = false) }
        }
        cancel = Button(this).apply {
            setText(R.string.dns_diagnostics_stop)
            visibility = View.GONE
            setOnClickListener { stopRun() }
        }
        filterButton = Button(this).apply { setOnClickListener { filter = (filter + 1) % 3; render() } }
        sortButton = Button(this).apply { setOnClickListener { fastestFirst = !fastestFirst; render() } }
        routeInfo = TextView(this).apply {
            textSize = 13f
            setPadding(0, dp(10), 0, dp(8))
            textDirection = View.TEXT_DIRECTION_FIRST_STRONG
        }
        status = TextView(this).apply {
            textSize = 16f
            setPadding(0, dp(10), 0, dp(8))
            setTextIsSelectable(true)
        }
        resultsText = TextView(this).apply {
            textSize = 14f
            setTextIsSelectable(true)
            textDirection = View.TEXT_DIRECTION_FIRST_STRONG
        }
        listOf(diagnose, scan, cancel, filterButton, sortButton, routeInfo, status, resultsText).forEach(column::addView)
        setContentView(ScrollView(this).apply { addView(column) })
        render()
    }

    // Android 5 cannot provide activeNetwork. A transport hint is not packet-route
    // proof; a separate Xray-routed DNS test must not be inferred from this field.
    private fun defaultNetwork(): Network? = runCatching {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) null
        else (getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager).activeNetwork
    }.getOrNull()

    private fun appRouteHint(): Int {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return R.string.dns_diagnostics_route_unknown
        return runCatching {
            val manager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            val capabilities = defaultNetwork()?.let { manager.getNetworkCapabilities(it) }
            when {
                capabilities == null -> R.string.dns_diagnostics_route_unknown
                capabilities.hasTransport(NetworkCapabilities.TRANSPORT_VPN) ->
                    R.string.dns_diagnostics_route_vpn_reported
                else -> R.string.dns_diagnostics_route_vpn_not_reported
            }
        }.getOrDefault(R.string.dns_diagnostics_route_unknown)
    }

    private data class Query(val resolver: String, val domain: String, val type: DnsType)

    private fun begin(single: Boolean) {
        if (job?.isActive == true) return
        val selected = runCatching { selections(single) }.getOrNull()
        if (selected.isNullOrEmpty()) {
            AlertDialog.Builder(this).setMessage(R.string.dns_diagnostics_invalid)
                .setPositiveButton(android.R.string.ok, null).show()
            return
        }
        val timeoutMs = timeout.text.toString().toIntOrNull() ?: return
        AlertDialog.Builder(this)
            .setTitle(R.string.dns_diagnostics_confirm_title)
            .setMessage(getString(R.string.dns_diagnostics_budget, selected.size))
            .setPositiveButton(R.string.dns_diagnostics_run) { _, _ -> execute(selected, timeoutMs) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun selections(single: Boolean): List<Query> {
        val timeoutMs = timeout.text.toString().toIntOrNull()
        require(timeoutMs != null && timeoutMs in 300..10_000)
        fun entries(raw: String) = raw.split(Regex("[,;\\s]+"))
            .map { it.trim() }.filter(String::isNotBlank).distinct()
        val allDomains = entries(domains.text.toString())
        val allResolvers = entries(resolvers.text.toString())
        val allTypes = entries(types.text.toString()).map { name ->
            DnsType.values().firstOrNull { it.name == name.uppercase(Locale.ROOT) }
                ?: throw IllegalArgumentException("INVALID_TYPE")
        }.distinct()
        require(allDomains.isNotEmpty() && allResolvers.isNotEmpty() && allTypes.isNotEmpty())
        require(allDomains.size <= 12 && allResolvers.size <= 4 && allTypes.size <= 7)
        allResolvers.forEach(DnsResolverInput::parse)
        allDomains.forEach { DnsWire.query(it, allTypes.first(), 1) }
        val chosenDomains = if (single) allDomains.take(1) else allDomains
        val chosenResolvers = if (single) allResolvers.take(1) else allResolvers
        val chosenTypes = if (single) allTypes.take(1) else allTypes
        val combinations = chosenDomains.size * chosenResolvers.size * chosenTypes.size
        require(combinations <= 144)
        return chosenResolvers.flatMap { resolver ->
            chosenDomains.flatMap { domain -> chosenTypes.map { type -> Query(resolver, domain, type) } }
        }
    }

    private fun execute(queries: List<Query>, timeoutMs: Int) {
        val token = ++generation
        runNetwork = defaultNetwork()
        runRouteHint = appRouteHint()
        observedNetworkChange = false
        results.clear()
        completed = 0
        total = queries.size
        lastRender = 0L
        diagnose.isEnabled = false
        scan.isEnabled = false
        cancel.visibility = View.VISIBLE
        render()
        job = lifecycleScope.launch {
            try {
                // Fixed-sized workers, not one coroutine per query or a new global scheduler.
                coroutineScope {
                    val index = AtomicInteger(0)
                    repeat(minOf(6, queries.size)) {
                        launch(Dispatchers.IO) {
                            val probe = DnsProbe()
                            while (isActive) {
                                val position = index.getAndIncrement()
                                if (position >= queries.size) break
                                val query = queries[position]
                                val observation = probe.query(query.resolver, query.domain, query.type, timeoutMs)
                                withContext(Dispatchers.Main) {
                                    if (token == generation) {
                                        if (defaultNetwork() != runNetwork) observedNetworkChange = true
                                        results.add(observation)
                                        completed++
                                        val now = SystemClock.elapsedRealtime()
                                        if (now - lastRender > 120L || completed == total) {
                                            lastRender = now
                                            render()
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            } catch (_: CancellationException) {
                // Cancellation is normal; never report skipped queries as failures.
            } finally {
                if (token == generation) {
                    if (defaultNetwork() != runNetwork) observedNetworkChange = true
                    diagnose.isEnabled = true
                    scan.isEnabled = true
                    cancel.visibility = View.GONE
                    render()
                }
            }
        }
    }

    private fun stopRun() {
        generation++ // Results from blocked sockets may not re-enter this screen.
        job?.cancel()
        job = null
        diagnose.isEnabled = true
        scan.isEnabled = true
        cancel.visibility = View.GONE
        status.setText(R.string.dns_diagnostics_stopped)
        renderResults()
    }

    private fun render() {
        filterButton.text = getString(when (filter) {
            1 -> R.string.dns_diagnostics_filter_ok
            2 -> R.string.dns_diagnostics_filter_errors
            else -> R.string.dns_diagnostics_filter_all
        })
        sortButton.text = getString(if (fastestFirst)
            R.string.dns_diagnostics_sort_fastest else R.string.dns_diagnostics_sort_original)
        routeInfo.text = getString(R.string.dns_diagnostics_test_route,
            getString(runRouteHint ?: appRouteHint())) +
            if (observedNetworkChange) "\n" + getString(R.string.dns_diagnostics_route_changed) else ""
        status.text = getString(R.string.dns_diagnostics_progress, completed, total)
        renderResults()
    }

    private fun renderResults() {
        val visible = results.filter {
            when (filter) {
                1 -> it.succeeded
                2 -> !it.succeeded
                else -> true
            }
        }
        val selected = if (fastestFirst) visible.sortedWith(compareBy<DnsProbeResult> { !it.succeeded }
            .thenBy { it.elapsedMs }) else visible
        resultsText.text = if (selected.isEmpty()) getString(R.string.dns_diagnostics_empty) else buildString {
            for (res in selected) {
                append(res.domain).append("  ").append(res.qtype.name)
                    .append("  @ ").append(res.resolver)
                    .append("\n").append(res.status).append("  ").append(res.elapsedMs).append(" ms")
                append("  ").append(res.attempts.joinToString(" → ") { "${it.transport}: ${it.status} (${it.elapsedMs} ms)" })
                res.answer?.let { reply ->
                    append("\nRCODE=").append(reply.rcode)
                        .append("  RA=").append(reply.recursionAvailable)
                        .append("  AD bit=").append(reply.authenticatedData)
                        .append("  EDNS=").append(reply.edns)
                    reply.records.forEach { record ->
                        append("\n").append(record.type.name)
                            .append("  TTL ").append(record.ttl).append("s: ")
                            .append(record.value.replace(Regex("[\\p{Cntrl}]"), " ").take(256))
                    }
                }
                append("\n\n")
            }
        }
    }

    override fun onDestroy() {
        generation++
        job?.cancel()
        super.onDestroy()
    }
    override fun onSupportNavigateUp(): Boolean { finish(); return true }
}
