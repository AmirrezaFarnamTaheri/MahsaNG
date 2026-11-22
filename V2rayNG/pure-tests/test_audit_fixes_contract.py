"""Regression contracts for audit fixes across VPN lifecycle, ECH, FGS, and storage."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "app/src/main"
KOTLIN = MAIN / "kotlin/com/v2ray/ang"
ANDROID = "{http://schemas.android.com/apk/res/android}"


class AuditFixesContractTest(unittest.TestCase):
    def test_vpn_deferred_restart_resets_trackers_and_fails_closed_when_blocked(self):
        vpn = (KOTLIN / "service/V2RayVpnService.kt").read_text(encoding="utf-8")
        manager = (KOTLIN / "service/V2RayServiceManager.kt").read_text(encoding="utf-8")
        self.assertIn("internal fun prepareForVerifiedRestart(): Boolean", vpn)
        self.assertIn("tunCloseTracker.resetForNewSession()", vpn)
        self.assertIn("tunExitTracker.resetForNewSession()", vpn)
        self.assertIn('throw IllegalStateException("Xray VPN TUN establishment blocked by Stop")', vpn)
        self.assertIn("service.prepareForVerifiedRestart()", manager)
        self.assertIn("coreStopGate.isQuarantined()", manager)
        self.assertIn("private var activeServiceRef: Service? = null", manager)

    def test_foreground_services_satisfy_android_o_and_target_sdk_34_requirements(self):
        manifest = ET.parse(MAIN / "AndroidManifest.xml").getroot()
        for name in (".service.PsiphonVpnService", ".service.V2RayVpnService", ".service.V2RayProxyOnlyService"):
            services = [s for s in manifest.findall(".//service") if s.attrib.get(ANDROID + "name") == name]
            self.assertEqual(1, len(services), name)
            self.assertEqual("specialUse", services[0].attrib.get(ANDROID + "foregroundServiceType"), name)
            prop = services[0].find("./property")
            self.assertIsNotNone(prop, name)
            self.assertEqual("android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE", prop.get(ANDROID + "name"))
        vpn = (KOTLIN / "service/V2RayVpnService.kt").read_text(encoding="utf-8")
        proxy = (KOTLIN / "service/V2RayProxyOnlyService.kt").read_text(encoding="utf-8")
        self.assertIn("V2RayServiceManager.ensureForeground(this)", vpn)
        self.assertIn("V2RayServiceManager.ensureForeground(this)", proxy)
        tile = (KOTLIN / "service/QSTileService.kt").read_text(encoding="utf-8")
        self.assertIn("Context.RECEIVER_NOT_EXPORTED", tile)

    def test_fragmentor_sockets_are_tracked_before_bounded_connect(self):
        for name in ("TLS_Fragmentor.kt", "HTTPS_Fragmentor.kt"):
            src = (KOTLIN / "gfwknocker" / name).read_text(encoding="utf-8")
            self.assertIn("InetSocketAddress(", src)
            self.assertIn(".connect(InetSocketAddress(", src)
            self.assertLess(src.index("forwarders.track(this,"), src.index(".connect(InetSocketAddress("))

    def test_psiphon_notification_update_preserves_session_stop_action_and_register_reply(self):
        psiphon = (KOTLIN / "service/PsiphonVpnService.kt").read_text(encoding="utf-8")
        update = psiphon.split("private fun updateNotification(", 1)[1].split("private fun closeTrackedTunDescriptor(", 1)[0]
        self.assertIn('builder.addAction(R.drawable.ic_close_grey_800_24dp, "Stop", stopPendingIntent)', update)
        self.assertIn("AppConfig.MSG_REGISTER_CLIENT", psiphon)

    def test_ang_config_manager_wires_ech_parameters_and_guards_blank_addresses(self):
        mgr = (KOTLIN / "util/AngConfigManager.kt").read_text(encoding="utf-8")
        self.assertGreaterEqual(mgr.count("EchLinkParameters.fromQuery("), 4)
        self.assertIn("EchLinkParameters.toQuery(", mgr)
        self.assertNotIn("outbound.getServerAddress()!!", mgr)
        for fmt in ("VlessFmt.kt", "TrojanFmt.kt"):
            src = (KOTLIN / "util/fmt" / fmt).read_text(encoding="utf-8")
            self.assertIn("TlsCertificatePolicy.forImport(", src)
            self.assertNotIn('queryParam["allowInsecure"]', src)

    def test_mmkv_callers_check_write_and_selection_results(self):
        vm = (KOTLIN / "viewmodel/MainViewModel.kt").read_text(encoding="utf-8")
        self.assertIn("if (!MmkvManager.removeServer(guid))", vm)
        self.assertIn("if (key.isBlank()) {", vm)
        tasker = (KOTLIN / "receiver/TaskerReceiver.kt").read_text(encoding="utf-8")
        self.assertIn("MmkvManager.selectExistingServer(guid)", tasker)
        self.assertNotIn("mainStorage?.encode(MmkvManager.KEY_SELECTED_SERVER", tasker)
        server = (KOTLIN / "ui/ServerActivity.kt").read_text(encoding="utf-8")
        custom = (KOTLIN / "ui/ServerCustomConfigActivity.kt").read_text(encoding="utf-8")
        self.assertIn("if (savedGuid.isBlank())", server)
        self.assertIn("if (savedGuid.isBlank())", custom)


if __name__ == "__main__":
    unittest.main()
