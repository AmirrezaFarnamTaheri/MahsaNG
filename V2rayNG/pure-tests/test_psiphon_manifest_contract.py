"""Keep the dedicated Psiphon VPN process non-exported and properly declared.

Source contract only; working VPN and native lifecycle need Android device tests.
"""
from pathlib import Path
from xml.etree import ElementTree as ET
import unittest

APP = Path(__file__).resolve().parents[1] / 'app'
MANIFEST = APP / 'src/main/AndroidManifest.xml'
ANDROID = '{http://schemas.android.com/apk/res/android}'


class PsiphonManifestContractTest(unittest.TestCase):
    def test_psiphon_service_is_isolated_and_not_externally_launchable(self):
        manifest = ET.parse(MANIFEST).getroot()
        services = [s for s in manifest.findall('.//service') if
                    s.attrib.get(ANDROID + 'name') == '.service.PsiphonVpnService']
        self.assertEqual(1, len(services), 'PsiphonVpnService must be declared exactly once')
        svc = services[0]
        self.assertEqual('false', svc.attrib.get(ANDROID + 'exported'))
        self.assertEqual(':PsiphonDaemon', svc.attrib.get(ANDROID + 'process'))
        self.assertEqual('android.permission.BIND_VPN_SERVICE', svc.attrib.get(ANDROID + 'permission'))
        self.assertEqual('specialUse', svc.attrib.get(ANDROID + 'foregroundServiceType'))
        actions = [a.attrib.get(ANDROID + 'name') for a in svc.findall('./intent-filter/action')]
        self.assertIn('android.net.VpnService', actions)
        special_use = svc.find('./property')
        self.assertIsNotNone(special_use)
        self.assertEqual('android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE', special_use.get(ANDROID + 'name'))
        self.assertTrue(special_use.get(ANDROID + 'value'))

    def test_special_use_foreground_service_permission_is_declared(self):
        manifest = ET.parse(MANIFEST).getroot()
        permissions = {p.attrib.get(ANDROID + 'name') for p in manifest.findall('./uses-permission')}
        self.assertIn('android.permission.FOREGROUND_SERVICE_SPECIAL_USE', permissions)


if __name__ == '__main__':
    unittest.main()
