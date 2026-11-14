"""Regression: subscription update never writes a credential-bearing URL to Logcat."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1] / "app" / "src" / "main"
ACTIVITY = ROOT / "kotlin" / "com" / "v2ray" / "ang" / "ui" / "MainActivity.kt"

class SubscriptionUrlLoggingContractTest(unittest.TestCase):
    def test_subscription_url_is_not_logged_during_refresh(self):
        source = ACTIVITY.read_text(encoding="utf-8")
        self.assertIn("val url = Utils.idnToASCII(it.second.url)", source)
        self.assertNotRegex(source, r"Log\.[a-z]+\(ANG_PACKAGE,\s*url\s*\)")
        self.assertIn("// Subscription URLs may contain access tokens.", source)
        refresh = source.split("fun importConfigViaSub()", 1)[1].split("show file chooser", 1)[0]
        self.assertNotIn("printStackTrace()", refresh)
        self.assertNotRegex(refresh, r"Log\.[a-z]+\(ANG_PACKAGE,\s*(?:url|e)\s*\)")


if __name__ == "__main__":
    unittest.main()
