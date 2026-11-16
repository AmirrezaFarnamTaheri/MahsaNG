"""Regression: failed or stale tun2socks FD handoffs cannot strand the VPN."""
from pathlib import Path
import unittest

SERVICE = Path(__file__).resolve().parents[1] / (
    "app/src/main/kotlin/com/v2ray/ang/service/V2RayVpnService.kt"
)


class TunFdHandoffContractTest(unittest.TestCase):
    def test_handoff_is_bound_to_adopted_child_not_just_session(self):
        code = SERVICE.read_text(encoding="utf-8")
        self.assertIn("sendFd(generation, child)", code)
        self.assertIn("private fun sendFd(generation: Long, child: Process)", code)
        handoff = code.split("private fun sendFd(", 1)[1].split(
            "override fun onStartCommand(", 1
        )[0]
        self.assertIn("tunProcesses.owns(generation, child)", handoff)
        self.assertNotIn("tunProcesses.isCurrent(generation)", handoff)

    def test_exhausted_fd_delivery_stops_only_the_still_owned_vpn(self):
        code = SERVICE.read_text(encoding="utf-8")
        handoff = code.split("private fun sendFd(", 1)[1].split(
            "override fun onStartCommand(", 1
        )[0]
        self.assertIn("for (tries in 0..5)", handoff)
        self.assertIn("withContext(Dispatchers.Main)", handoff)
        self.assertIn("if (tunProcesses.owns(generation, child)) stopV2Ray()", handoff)
        self.assertGreater(handoff.index("stopV2Ray()"), handoff.index("for (tries in 0..5)"))
        # Successful sends still finish without requesting a stop.
        self.assertIn("socket.outputStream.write(42)", handoff)
        self.assertIn("return@launch", handoff)


if __name__ == "__main__":
    unittest.main()
