"""Guard app startup and package-list null handling across Android versions."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang"

class ApplicationSourceGuardsTests(unittest.TestCase):
    def test_plugin_application_reference_is_initialized_before_first_use(self):
        application = (ROOT / "AngApplication.kt").read_text(encoding="utf-8")
        manager = (ROOT / "plugin/PluginManager.kt").read_text(encoding="utf-8")
        self.assertIn("AngApplication.application", manager)
        self.assertIn("lateinit var application: AngApplication", application)
        self.assertIn("application = this", application)
        self.assertLess(application.index("application = this"), application.index("MMKV.initialize(this)"))

    def test_apps_with_no_applicationinfo_are_skipped_not_dereferenced(self):
        manager = (ROOT / "util/AppManagerUtil.kt").read_text(encoding="utf-8")
        self.assertIn("val applicationInfo = pkg.applicationInfo ?: continue", manager)

if __name__ == "__main__":
    unittest.main()
