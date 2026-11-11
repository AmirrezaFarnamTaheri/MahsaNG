"""TLS-only ECH editor controls must have compiled, reachable resource IDs."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "app/src/main"
RES = ROOT / "res"
KOTLIN = ROOT / "kotlin/com/v2ray/ang"
ANDROID = "{http://schemas.android.com/apk/res/android}"


class EchEditorContractTests(unittest.TestCase):
    def test_source_resource_has_real_controls_for_existing_activity_fields(self):
        tls = (RES / "layout/tls_layout.xml").read_text(encoding="utf-8")
        self.assertEqual(1, tls.count('layout="@layout/gfw_ech_layout"'))
        root = ET.parse(RES / "layout/gfw_ech_layout.xml").getroot()
        ids = {node.attrib.get(ANDROID + "id", "").removeprefix("@+id/"): node
               for node in root.iter() if node.attrib.get(ANDROID + "id")}
        self.assertEqual("LinearLayout", ids["l_ech"].tag)
        self.assertNotIn('android:id="@+id/l_ech"', tls)
        self.assertEqual("gone", ids["l_ech"].get(ANDROID + "visibility"))
        for name in ("et_echConfigList", "et_echServerKeys", "et_echForceQuery"):
            self.assertEqual("EditText", ids[name].tag)

    def test_ech_visibility_follows_tls_not_reality(self):
        source = (KOTLIN / "ui/ServerActivity.kt").read_text(encoding="utf-8")
        self.assertIn("container_ech?.visibility = if (streamSecuritys[position] == TLS)", source)
        dto = (KOTLIN / "dto/V2rayConfig.kt").read_text(encoding="utf-8")
        self.assertIn("echConfigList = echConfigList", dto)
        self.assertIn("echServerKeys = echServerKeys", dto)
        self.assertIn("echForceQuery = echForceQuery", dto)


if __name__ == "__main__":
    unittest.main()
