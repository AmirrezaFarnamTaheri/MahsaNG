"""Source-level checks for legacy server editor layout completeness.

The real Android resource linker / Kotlin compiler remains mandatory.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "app/src/main"
LAYOUT = ROOT / "res/layout"


class ServerEditorLayoutContractTests(unittest.TestCase):
    def test_ech_controls_exist_in_real_included_tls_layout(self):
        tls = (LAYOUT / "tls_layout.xml").read_text(encoding="utf-8")
        self.assertIn('@layout/gfw_ech_layout', tls)
        ech = (LAYOUT / "gfw_ech_layout.xml").read_text(encoding="utf-8")
        for view_id in ("l_ech", "et_echConfigList", "et_echServerKeys", "et_echForceQuery"):
            with self.subTest(view_id=view_id):
                self.assertIn('android:id="@+id/' + view_id + '"', ech)
        editor = (ROOT / "kotlin/com/v2ray/ang/ui/ServerActivity.kt").read_text(encoding="utf-8")
        self.assertIn("container_ech?.visibility", editor)

    def test_no_ech_editor_for_reality_or_non_tls_modes(self):
        editor = (ROOT / "kotlin/com/v2ray/ang/ui/ServerActivity.kt").read_text(encoding="utf-8")
        self.assertIn("container_ech?.visibility = if (streamSecuritys[position] == TLS)", editor)


if __name__ == "__main__":
    unittest.main()
