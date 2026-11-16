"""Proxy candidate validation must be explicit, bounded and fail closed."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "app/src/main"
UI = ROOT / "kotlin/com/v2ray/ang/ui/TargetDiscoveryActivity.kt"
PROXY = ROOT / "kotlin/com/v2ray/ang/util/ProxyCandidateProbe.kt"

class ProxyCandidateValidationContractTest(unittest.TestCase):
    def test_explicit_proxy_route_reads_existing_local_http_port(self):
        ui = UI.read_text()
        self.assertIn("Utils.getConfiguredHttpPortOrNull()", ui)
        self.assertIn("localProxyCheckbox.isChecked", ui)
        self.assertIn("TargetProbeRoute.LOCAL_HTTP_CONNECT", ui)
        self.assertIn("ProxyCandidateProbe.inspect(", ui)
        self.assertIn("TargetDiscoveryProbe.inspect(", ui)
        self.assertIn("requireNotNull(proxyPort)", ui)

    def test_no_transport_or_subscription_mutation(self):
        ui = UI.read_text()
        for forbidden in ("V2RayServiceManager.startV2Ray", "V2RayServiceManager.stopV2rayPoint",
                          "MmkvManager.encodeServerConfig", "startV2Ray("):
            self.assertNotIn(forbidden, ui)

    def test_http_connect_does_not_open_socket_to_target_ip(self):
        src = PROXY.read_text()
        self.assertIn('InetSocketAddress("127.0.0.1", localHttpPort)', src)
        self.assertIn('CONNECT $authority HTTP/1.1', src)
        self.assertIn('parameters.endpointIdentificationAlgorithm = "HTTPS"', src)
        self.assertIn('tls.startHandshake()', src)
        self.assertNotIn("Socket().connect(InetSocketAddress(target.host", src)
        self.assertNotIn("Proxy.NO_PROXY", src)

    def test_attempts_use_one_bounded_queue_and_current_network_lease(self):
        ui = UI.read_text()
        self.assertIn("CandidateProbeRunPlan.create(", ui)
        # One worker owns a target through all passes; never scan its repeats concurrently.
        self.assertIn("BoundedProbeQueue(baseAttempts, concurrency = 6)", ui)
        self.assertIn("for (passIndex in 1..passes)", ui)
        self.assertIn("RunNetworkObserver.register(this)", ui)
        self.assertIn("observer.isCurrent()", ui)
        self.assertIn("owner.stop()", ui)
        self.assertIn("lease?.stop()", ui)
        self.assertIn("CandidateStability.summarize(", ui)

if __name__ == "__main__":
    unittest.main()
