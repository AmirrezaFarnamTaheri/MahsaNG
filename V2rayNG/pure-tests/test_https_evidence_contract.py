"""HTTPS/TLS evidence must remain explicit, safe and method-attributed."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / 'app' / 'src' / 'main'
ANDROID = '{http://schemas.android.com/apk/res/android}'

class HttpsEvidenceContract(unittest.TestCase):
    def test_internal_activity_and_explicit_one_shot_buttons(self):
        manifest = ET.parse(ROOT / 'AndroidManifest.xml')
        found = [x for x in manifest.iter('activity') if x.get(ANDROID+'name') == '.ui.HttpsEvidenceActivity']
        self.assertEqual(1, len(found))
        self.assertEqual('false', found[0].get(ANDROID+'exported'))
        code = (ROOT / 'kotlin/com/v2ray/ang/ui/HttpsEvidenceActivity.kt').read_text()
        self.assertIn('setOnClickListener { runEvidence(viaLocalProxy = false) }', code)
        self.assertIn('setOnClickListener { runEvidence(viaLocalProxy = true) }', code)
        self.assertIn('generation++', code)
        self.assertNotIn('MmkvManager', code)

    def test_default_platform_tls_verification_and_safe_codes(self):
        code = (ROOT / 'kotlin/com/v2ray/ang/util/HttpsEvidence.kt').read_text()
        self.assertIn('HttpsURLConnection', code)
        self.assertIn('Proxy.NO_PROXY', code)
        self.assertIn('Proxy.Type.HTTP', code)
        self.assertNotIn('HostnameVerifier {', code)
        self.assertNotIn('X509TrustManager', code)
        self.assertNotIn('e.message', code)
        self.assertNotIn('printStackTrace()', code)
        # Kotlin maps HttpsURLConnection.getServerCertificates() to this property.
        self.assertIn('connection.serverCertificates', code)
        self.assertIn('connection.cipherSuite', code)

    def test_local_http_port_is_read_from_saved_setting_without_writes(self):
        ui = (ROOT / 'kotlin/com/v2ray/ang/ui/HttpsEvidenceActivity.kt').read_text()
        utils = (ROOT / 'kotlin/com/v2ray/ang/util/Utils.kt').read_text()
        self.assertIn('Utils.getConfiguredHttpPortOrNull()', ui)
        self.assertNotIn('AppConfig.PORT_HTTP', ui)
        self.assertIn('AppConfig.PREF_HTTP_PORT', utils)
        self.assertIn('configured.toIntOrNull()?.takeIf { it in 1..65535 }', utils)

    def test_english_persian_parity(self):
        names=[]
        for dir in ('values','values-fa'):
            tree = ET.parse(ROOT / 'res' / dir / 'https_evidence.xml')
            names.append({x.attrib['name'] for x in tree.findall('string')})
        self.assertEqual(names[0], names[1])
        self.assertGreaterEqual(len(names[0]), 20)
        # Android AAPT string resources reject unescaped ASCII apostrophes.
        for locale in ('values', 'values-fa'):
            text = (ROOT / 'res' / locale / 'https_evidence.xml').read_text()
            self.assertNotRegex(text, r"(?<!\\)'", locale)

if __name__ == '__main__': unittest.main()
