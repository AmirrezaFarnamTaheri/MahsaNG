"""Fail-closed source contract for the *unwired* Start command envelope."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "app/src/main/kotlin/com/v2ray/ang/service"


class VpnStartCommandContract(unittest.TestCase):
    def test_wire_codec_denies_noncanonical_generation_and_wrong_roles(self):
        source = (SERVICE / "VpnStartCommandGate.kt").read_text(encoding="utf-8")
        self.assertIn('private const val VERSION = "v1"', source)
        self.assertIn('wire.split(\'.\')', source)
        self.assertIn("encode(it) == wire", source)
        self.assertIn("command.generation <= 0L", source)
        self.assertIn("VpnSessionMode.XRAY_VPN -> role == VpnSessionRole.XRAY", source)
        self.assertNotIn("android.content", source)
        self.assertNotIn("MMKV.", source)

    def test_reservation_requires_controller_snapshot_under_lock(self):
        source = (SERVICE / "VpnStartCommandGate.kt").read_text(encoding="utf-8")
        self.assertIn("VpnSessionFence.isValidSnapshot(state)", source)
        self.assertIn("state.phase == VpnSessionPhase.STARTING", source)
        self.assertIn("state.sessionId == command.sessionId", source)
        self.assertIn("state.generation == command.generation", source)
        self.assertIn("state.mode == command.mode", source)
        self.assertIn("command.role !in state.members", source)
        self.assertIn("VpnSessionFence.attach(", source)

    def test_live_vpn_services_remain_unwired_until_native_verification(self):
        for filename in ("V2RayServiceManager.kt", "V2RayVpnService.kt",
                         "V2RayProxyOnlyService.kt", "PsiphonVpnService.kt"):
            source = (SERVICE / filename).read_text(encoding="utf-8")
            self.assertNotIn("VpnStartCommandGate", source)
            self.assertNotIn("VpnStartCommandCodec", source)


if __name__ == "__main__":
    unittest.main()
