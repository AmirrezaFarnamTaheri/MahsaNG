"""Unsupported export schemes fail closed; MVLESS shares normal VLESS wire URIs."""
from pathlib import Path
import unittest

FILE = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang/util/AngConfigManager.kt"

class ShareProtocolContractTests(unittest.TestCase):
    def test_unimplemented_http_hysteria2_share_schemes_do_not_emit_empty_urls(self):
        code = FILE.read_text(encoding="utf-8")
        share = code[code.index("private fun shareConfig("):code.index("fun share2Clipboard(")]
        self.assertIn("config.configType == EConfigType.HTTP", share)
        self.assertIn("config.configType == EConfigType.HYSTERIA2", share)
        self.assertIn("return \"\"", share)
        self.assertIn("EConfigType.VLESS, EConfigType.MVLESS,", share)

if __name__ == "__main__":
    unittest.main()
