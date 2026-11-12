"""PR #10 CodeRabbit regression contracts; full Android compile remains mandatory."""
from pathlib import Path
import re
import unittest

APP = Path(__file__).resolve().parents[1] / "app/src/main"
KT = APP / "kotlin/com/v2ray/ang"
JAVA = APP / "java/com/v2ray/ang/GFW_psiphonSettings_Activity.java"


class CodeRabbitPr10RegressionTest(unittest.TestCase):
    def test_no_duplicate_kotlin_validation_delegates(self):
        text = (KT / "util/Utils.kt").read_text(encoding="utf-8")
        self.assertEqual(1, len(re.findall(r"fun validate_port\(port: Int\)", text)))
        self.assertEqual(1, len(re.findall(r"fun fragment_param_check\(value: String\?\)", text)))

    def test_psiphon_defaults_are_savable_without_overwriting_other_choices(self):
        activity = JAVA.read_text(encoding="utf-8")
        self.assertIn("PsiphonProxyPortRules.isValid(socks_port, http_port)", activity)
        self.assertNotIn("n_socks <= 0", activity)
        self.assertNotIn("n_http <= 0", activity)
        for option in ("psiphon_country_code", "psiphon_protocol", "psiphon_aggressive"):
            self.assertIn('mystrg.put_value("' + option + '"', activity)
        app_config = (KT / "AppConfig.kt").read_text(encoding="utf-8")
        self.assertIn('const val PSIPHON_SOCKS = "0"', app_config)
        self.assertIn('const val PSIPHON_HTTP = "0"', app_config)

    def test_ech_tls_fields_are_shared_and_read_by_both_link_formats(self):
        dto = (KT / "dto/V2rayConfig.kt").read_text(encoding="utf-8")
        for field in ("echConfigList", "echServerKeys", "echForceQuery"):
            self.assertIn("var " + field + ":", dto)
        for format_name in ("VlessFmt", "TrojanFmt"):
            with self.subTest(format_name=format_name):
                source = (KT / "util/fmt" / (format_name + ".kt")).read_text(encoding="utf-8")
                self.assertIn("EchLinkParameters.toQuery(", source)
                self.assertIn("EchLinkParameters.fromQuery(", source)
                for field in ("echConfigList", "echServerKeys", "echForceQuery"):
                    self.assertIn("tlsSetting." + field, source)
                self.assertIn("echForceQuery = ech.forceQuery", source)

    def test_legacy_mux_enabled_flag_restores_mode_and_concurrency(self):
        source = (KT / "ui/ServerActivity.kt").read_text(encoding="utf-8")
        self.assertIn("MuxModeRestoration.restore(mux?.status, mux?.enabled)", source)
        self.assertIn("et_mux_concurrency?.text = Utils.getEditable(cun.toString())", source)
        self.assertNotIn("mux?.status.orEmpty()", source)

    def test_permission_result_cannot_swap_append_and_replace_on_recreation(self):
        source = (KT / "ui/RoutingSettingsFragment.kt").read_text(encoding="utf-8")
        self.assertIn("private val replaceCameraPermission", source)
        self.assertIn("private val appendCameraPermission", source)
        self.assertIn("replaceCameraPermission.launch(Manifest.permission.CAMERA)", source)
        self.assertIn("appendCameraPermission.launch(Manifest.permission.CAMERA)", source)
        self.assertIn("scanQRCodeForReplace.launch(", source)
        self.assertIn("scanQRCodeForAppend.launch(", source)
        self.assertNotIn("scanReplaceRequested", source)


if __name__ == "__main__":
    unittest.main()
