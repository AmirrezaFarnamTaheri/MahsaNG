"""Psiphon defaults must match its real local-proxy port configuration."""
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang"
PSIPHON = SRC / "service/PsiphonVpnService.kt"


class PsiphonSourceContractTests(unittest.TestCase):
    def test_auto_assigned_default_ports_do_not_collide_with_v2ray(self):
        config = (SRC / "AppConfig.kt").read_text(encoding="utf-8")
        self.assertIn('const val PSIPHON_SOCKS = "0"', config)
        self.assertIn('const val PSIPHON_HTTP = "0"', config)
        source = PSIPHON.read_text(encoding="utf-8")
        # Settings are now validated through a shared port parser; keep both
        # persisted automatic-port defaults and native notice callbacks covered.
        self.assertIn("PsiphonProxyPortRules.parse(", source)
        self.assertIn('mystrg.get_value("psiphon_socks_port", AppConfig.PSIPHON_SOCKS)', source)
        self.assertIn('mystrg.get_value("psiphon_http_port", AppConfig.PSIPHON_HTTP)', source)
        self.assertIn("PsiphonProxyPorts(0, 0)", source)
        self.assertIn('config.put("LocalSocksProxyPort", ports.socks)', source)
        self.assertIn('config.put("LocalHttpProxyPort", ports.http)', source)
        self.assertIn("override fun onListeningSocksProxyPort(port: Int)", source)
        self.assertIn("override fun onListeningHttpProxyPort(port: Int)", source)

    def test_compiler_references_only_real_psiphon_assets_and_imports(self):
        source = PSIPHON.read_text(encoding="utf-8")
        self.assertNotIn("import com.v2ray.ang.gfwknocker.GFW_sutil", source)
        self.assertNotIn("import com.v2ray.ang.gfwknocker.GFW_txt_crypt", source)
        self.assertNotIn("R.drawable.ic_stat_name_m2", source)
        self.assertIn("R.drawable.ic_stat_name", source)


if __name__ == "__main__":
    unittest.main()
