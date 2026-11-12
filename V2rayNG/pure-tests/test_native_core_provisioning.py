"""Never green-light a VPN APK without the authentic native V2Ray core."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/mahsa-safety.yml"
PIN = "48f35be868ee247e53a8036e284a8c2f97c80068"

class NativeCoreCIContractTest(unittest.TestCase):
    def test_rebuilds_authentic_pinned_mahsa_core_from_source(self):
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("https://github.com/GFW-knocker/AndroidLibXrayLite.git", yml)
        self.assertIn(PIN, yml)
        self.assertIn('git -C "$NATIVE_DIR" rev-parse HEAD', yml)
        self.assertIn("go mod verify", yml)
        self.assertIn("gomobile bind", yml)
        self.assertIn("V2rayNG/app/libs/libv2ray.aar", yml)
        self.assertIn("libv2ray/V2RayPoint.class", yml)
        self.assertIn("libv2ray/V2RayVPNServiceSupportsSet.class", yml)

    def test_native_core_step_precedes_apk_assembly(self):
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertLess(yml.index("Build pinned Mahsa native Xray AAR"),
                        yml.index("Assemble Android application"))

if __name__ == "__main__":
    unittest.main()
