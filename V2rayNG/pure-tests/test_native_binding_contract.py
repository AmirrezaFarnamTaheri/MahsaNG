"""Pinned GFW-knocker AndroidLibXrayLite JNI call contract.

Go source at 48f35be defines:
  InitV2Env(envPath string, key string)
  MeasureOutboundDelay(config string, url string)
  (*V2RayPoint).MeasureDelay(url string)
The second init key is optional in the Go implementation (empty disables it).
"""
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang"


class NativeBindingContractTests(unittest.TestCase):
    def test_native_initialization_uses_explicit_optional_empty_key(self):
        service = (SRC / "service/V2RayServiceManager.kt").read_text(encoding="utf-8")
        tester = (SRC / "service/V2RayTestService.kt").read_text(encoding="utf-8")
        self.assertIn("Libv2ray.initV2Env(Utils.userAssetPath(value?.get()?.getService()), \"\" )".replace(' \"' , '\"'), service)
        self.assertIn('Libv2ray.initV2Env(Utils.userAssetPath(this), "")', tester)

    def test_delay_measurements_supply_http_204_url(self):
        service = (SRC / "service/V2RayServiceManager.kt").read_text(encoding="utf-8")
        speed = (SRC / "util/SpeedtestUtil.kt").read_text(encoding="utf-8")
        self.assertIn("v2rayPoint.measureDelay(AppConfig.DelayTestUrl)", service)
        self.assertIn("Libv2ray.measureOutboundDelay(config, AppConfig.DelayTestUrl)", speed)


if __name__ == "__main__":
    unittest.main()
