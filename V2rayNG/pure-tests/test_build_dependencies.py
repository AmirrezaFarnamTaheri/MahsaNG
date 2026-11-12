"""Old RxPermissions was JCenter-only; ensure modern permission flow is used."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "app/src/main/kotlin/com/v2ray/ang/ui"

class BuildDependenciesTest(unittest.TestCase):
    def test_legacy_rxpermissions_dependency_is_not_required(self):
        gradle = (ROOT / "app/build.gradle").read_text(encoding="utf-8")
        self.assertNotIn("com.tbruyelle.rxpermissions", gradle)
        for name in ("ScannerActivity", "ScScannerActivity",
                     "RoutingSettingsFragment", "UserAssetActivity"):
            source = (UI / (name + ".kt")).read_text(encoding="utf-8")
            self.assertNotIn("com.tbruyelle.rxpermissions", source)
            self.assertNotIn("RxPermissions(", source)

if __name__ == "__main__":
    unittest.main()
