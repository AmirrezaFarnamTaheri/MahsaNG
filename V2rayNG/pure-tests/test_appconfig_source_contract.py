"""Imported AppConfig fields must exist and carry conservative defaults."""
from pathlib import Path
import re
import unittest

SRC = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang"
APP_CONFIG = SRC / "AppConfig.kt"

FILES = [
    SRC / "ui/ServerActivity.kt",
    SRC / "util/AngConfigManager.kt",
    SRC / "util/fmt/WireguardFmt.kt",
]


class AppConfigSourceContractTests(unittest.TestCase):
    def test_imported_static_app_config_constants_exist(self):
        text = APP_CONFIG.read_text(encoding="utf-8")
        defined = set(re.findall(r"\\b(?:const\\s+val|val)\\s+([A-Za-z_][A-Za-z_0-9]*)", text))
        for file in FILES:
            if not file.is_file():
                continue
            contents = file.read_text(encoding="utf-8")
            imports = re.findall(r"import com\\.v2ray\\.ang\\.AppConfig\\.([A-Za-z_][A-Za-z_0-9]*)", contents)
            with self.subTest(file=file.name):
                self.assertFalse(set(imports) - defined, "Undefined AppConfig imports: " + str(set(imports) - defined))

    def test_wireguard_defaults_are_source_backed_or_disabled(self):
        text = APP_CONFIG.read_text(encoding="utf-8")
        self.assertIn('const val WIREGUARD_LOCAL_ADDRESS_V4 = "172.16.0.2/32"', text)
        self.assertIn('const val WIREGUARD_LOCAL_MTU = "1420"', text)
        self.assertIn('const val WIREGUARD_wnoise = ""', text)
        self.assertIn('const val WIREGUARD_wnoisecount = ""', text)


if __name__ == "__main__":
    unittest.main()
