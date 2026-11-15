"""Integration regression: DNS, TCP row batching and HTTPS coexist in one APK."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
MAIN = BASE / 'app/src/main'
KOTLIN = MAIN / 'kotlin/com/v2ray/ang'
ANDROID = '{http://schemas.android.com/apk/res/android}'

class DiagnosticIntegrationContract(unittest.TestCase):
    def test_both_diagnostic_activities_are_internal_and_reachable(self):
        manifest = ET.parse(MAIN / 'AndroidManifest.xml')
        activities = {a.get(ANDROID+'name'): a.get(ANDROID+'exported')
                      for a in manifest.iter('activity')}
        self.assertEqual('false', activities.get('.ui.DnsDiagnosticsActivity'))
        self.assertEqual('false', activities.get('.ui.HttpsEvidenceActivity'))
        menu = ET.parse(MAIN / 'res/menu/menu_main.xml')
        ids = {x.get(ANDROID+'id') for x in menu.iter('item')}
        self.assertIn('@+id/dns_diagnostics', ids)
        self.assertIn('@+id/https_evidence', ids)
        main = (KOTLIN / 'ui/MainActivity.kt').read_text()
        self.assertIn('R.id.dns_diagnostics ->', main)
        self.assertIn('R.id.https_evidence ->', main)
        self.assertIn('DnsDiagnosticsActivity::class.java', main)
        self.assertIn('HttpsEvidenceActivity::class.java', main)

    def test_tcp_display_updates_remain_owned_and_bounded(self):
        main = (KOTLIN / 'ui/MainActivity.kt').read_text()
        viewmodel = (KOTLIN / 'viewmodel/MainViewModel.kt').read_text()
        batch = (KOTLIN / 'util/TcpRowBatch.kt').read_text()
        self.assertIn('updateListBatchAction.observe(this)', main)
        self.assertIn('TcpRowBatch.ranges(indices, adapter.itemCount)', main)
        self.assertIn('testRuns.publishIfCurrent(runId, guid)', viewmodel)
        self.assertIn('queueTcpDisplayUpdate(runId, guid)', viewmodel)
        self.assertIn('it < rowCount', batch)

    def test_existing_proxy_port_configuration_works_for_both_diagnostics(self):
        utils = (KOTLIN / 'util/Utils.kt').read_text()
        dns = (KOTLIN / 'ui/DnsDiagnosticsActivity.kt').read_text()
        https = (KOTLIN / 'ui/HttpsEvidenceActivity.kt').read_text()
        self.assertIn('fun getConfiguredSocksPortOrNull()', utils)
        self.assertIn('fun getConfiguredHttpPortOrNull()', utils)
        self.assertIn('Utils.getConfiguredSocksPortOrNull()', dns)
        self.assertIn('Utils.getConfiguredHttpPortOrNull()', https)
        self.assertIn('DnsRoute.LOCAL_SOCKS5_TCP', dns)
        self.assertIn('HttpsEvidenceRoute.LOCAL_HTTP_PROXY', https)

    def test_legacy_proxy_probes_keep_credential_safe_error_messages(self):
        speed = (KOTLIN / 'util/SpeedtestUtil.kt').read_text()
        safe = (KOTLIN / 'util/SafeProbeFailure.kt').read_text()
        self.assertIn('SafeProbeFailure.safeReason(e)', speed)
        self.assertIn('SafeProbeFailure.classify(e)', speed)
        self.assertNotIn('printStackTrace()', speed)
        self.assertNotIn('Log.getStackTraceString', speed)
        self.assertNotIn('error.toString()', safe)
        self.assertNotIn('error.message', safe)

    def test_pure_kotlin_test_suite_carries_all_production_helpers(self):
        build = (BASE / 'pure-tests/build.gradle.kts').read_text()
        for helper in ('DnsWire', 'DnsProbe', 'DnsResolverDefaults',
                       'DnsSocks5Tcp', 'TcpRowBatch', 'HttpsEvidence', 'SafeProbeFailure'):
            with self.subTest(helper=helper):
                self.assertIn('"'+helper+'"', build)

if __name__ == '__main__':
    unittest.main()
