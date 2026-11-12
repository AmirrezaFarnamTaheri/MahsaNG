"""Regression contracts for Psiphon auto ports and fail-closed JNI cleanup."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "app/src/main"
JAVA = ROOT / "java/com/v2ray/ang/GFW_psiphonSettings_Activity.java"
SERVICE = ROOT / "kotlin/com/v2ray/ang/service/PsiphonVpnService.kt"


class PsiphonSettingsAndRoutingSafetyContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.java = JAVA.read_text(encoding="utf-8")
        cls.service = SERVICE.read_text(encoding="utf-8")

    def test_settings_accept_auto_ports_via_shared_parser(self):
        self.assertIn("PsiphonProxyPortRules.isValid(socks_port, http_port)", self.java)
        self.assertNotIn("n_socks <= 0", self.java)
        self.assertNotIn("n_http <= 0", self.java)

    def test_config_validates_saved_ports_and_fails_back_to_auto(self):
        self.assertIn("PsiphonProxyPortRules.parse(", self.service)
        self.assertIn("PsiphonProxyPorts(0, 0)", self.service)

    def test_native_jni_exit_invalidates_vpn(self):
        worker = self.service.split("private fun startTun2socks(socksPort: Int)", 1)[1].split(
            "private fun startForegroundNotification()", 1
        )[0]
        self.assertIn("catch (error: LinkageError)", worker)
        self.assertIn("finally {", worker)
        self.assertIn("Thread { stopAll() }.start()", worker)

    def test_cleanup_cannot_skip_vpn_close_if_native_unavailable(self):
        cleanup = self.service.split("private fun stopAll(", 1)[1].split(
            "override fun loadLibrary(", 1
        )[0]
        self.assertIn("runCatching { Tun2SocksJniLoader.terminateTun2Socks() }", cleanup)
        self.assertIn("mInterface?.close()", cleanup)
        self.assertIn("stopService(Intent(this, V2RayProxyOnlyService::class.java))", cleanup)

    def test_native_psiphon_start_catches_linkage_error(self):
        startup = self.service.split("private fun startPsiphonTunnelAsync(", 1)[1].split(
            "private fun waitForPort(", 1
        )[0]
        self.assertIn("catch (e: LinkageError)", startup)


if __name__ == "__main__":
    unittest.main()
