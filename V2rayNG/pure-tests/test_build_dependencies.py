"""Regressions introduced by removing dependencies still imported in Kotlin."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/src/main/kotlin/com/v2ray/ang/ui"
BUILD = ROOT / "app/build.gradle"

class BuildDependenciesTest(unittest.TestCase):
    def test_rxpermissions_is_declared_if_production_imports_it(self):
        imports = [p for p in SOURCE.glob("*.kt")
                   if "com.tbruyelle.rxpermissions.RxPermissions" in p.read_text(encoding="utf-8")]
        self.assertGreaterEqual(len(imports), 1, "Test assumes there is an RxPermissions consumer")
        self.assertIn("com.tbruyelle.rxpermissions:rxpermissions:0.9.4@aar",
                      BUILD.read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
