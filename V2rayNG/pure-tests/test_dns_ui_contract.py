"""Source-contract regression for user-triggered read-only DNS diagnostics."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / 'app' / 'src' / 'main'
UI = ROOT / 'kotlin' / 'com' / 'v2ray' / 'ang' / 'ui'
ANDROID = '{http://schemas.android.com/apk/res/android}'

class DnsUiContract(unittest.TestCase):
    def test_scan_requires_click_and_bounds_parallelism(self):
        code = (UI / 'DnsDiagnosticsActivity.kt').read_text()
        self.assertIn('setOnClickListener { begin(single = false) }', code)
        self.assertIn('repeat(minOf(6, queries.size))', code)
        self.assertIn('require(combinations <= 144)', code)
        self.assertIn('AlertDialog.Builder(this)', code)
        self.assertIn('generation++', code)

    def test_no_saved_profiles_mutation_or_false_proxy_attribution(self):
        code = (UI / 'DnsDiagnosticsActivity.kt').read_text()
        self.assertNotIn('MmkvManager', code)
        self.assertNotIn('removeAllServer', code)
        self.assertNotIn('V2RayServiceManager', code)
        resources = ET.parse(ROOT / 'res' / 'values' / 'dns_diagnostics.xml')
        label = next(x.text for x in resources.findall('string') if x.attrib['name']=='dns_diagnostics_route_warning')
        self.assertIn('may use the active VPN', label)
        self.assertIn('do not prove an Xray through-proxy path', label)

    def test_persian_parity_and_manifest_internal_only(self):
        en = {s.attrib['name'] for s in ET.parse(ROOT / 'res' / 'values' / 'dns_diagnostics.xml').findall('string')}
        fa = {s.attrib['name'] for s in ET.parse(ROOT / 'res' / 'values-fa' / 'dns_diagnostics.xml').findall('string')}
        self.assertEqual(en, fa)
        manifest = ET.parse(ROOT / 'AndroidManifest.xml')
        acts = [a for a in manifest.iter('activity') if a.get(ANDROID+'name') == '.ui.DnsDiagnosticsActivity']
        self.assertEqual(len(acts),1)
        self.assertEqual(acts[0].get(ANDROID+'exported'),'false')

    def test_main_menu_is_wired_explicitly(self):
        menu = ET.parse(ROOT / 'res' / 'menu' / 'menu_main.xml')
        self.assertTrue(any(node.get(ANDROID+'id')=='@+id/dns_diagnostics' for node in menu.iter('item')))
        main = (UI / 'MainActivity.kt').read_text()
        self.assertIn('R.id.dns_diagnostics ->', main)
        self.assertIn('DnsDiagnosticsActivity::class.java', main)

if __name__ == '__main__': unittest.main()
