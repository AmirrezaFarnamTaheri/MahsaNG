"""Android Storage Access Framework does not require legacy storage permissions."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "app"
SOURCES = ROOT / "src/main/kotlin/com/v2ray/ang/ui"

class AndroidPermissionContractTests(unittest.TestCase):
    def test_unsupported_rxpermissions_dependency_is_gone(self):
        gradle = (ROOT / "build.gradle").read_text(encoding="utf-8")
        self.assertNotIn("com.tbruyelle.rxpermissions", gradle)
        for name in ("ScannerActivity", "ScScannerActivity",
                     "RoutingSettingsFragment", "UserAssetActivity"):
            with self.subTest(name=name):
                source = (SOURCES / (name + ".kt")).read_text(encoding="utf-8")
                self.assertNotIn("RxPermissions", source)

    def test_file_pickers_do_not_request_gallery_storage_permission(self):
        for name in ("ScannerActivity", "UserAssetActivity"):
            with self.subTest(name=name):
                source = (SOURCES / (name + ".kt")).read_text(encoding="utf-8")
                self.assertIn("Intent.ACTION_GET_CONTENT", source)
                self.assertNotIn("READ_MEDIA_IMAGES", source)
                self.assertNotIn("READ_EXTERNAL_STORAGE", source)

    def test_camera_uses_lifecycle_owned_activity_result_contract(self):
        for name in ("ScScannerActivity", "RoutingSettingsFragment"):
            with self.subTest(name=name):
                source = (SOURCES / (name + ".kt")).read_text(encoding="utf-8")
                self.assertIn("ActivityResultContracts.RequestPermission()", source)
                self.assertIn("Manifest.permission.CAMERA", source)

if __name__ == "__main__":
    unittest.main()
