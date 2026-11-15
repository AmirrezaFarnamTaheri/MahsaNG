"""Regression: subscription update never writes a credential-bearing URL to Logcat."""
import pathlib
import re

URL_INTERPOLATION = re.compile(r'Log\.\w+\s*\([^)]*\$(?:\{url\}|url\b)')
THROWABLE_LOG = re.compile(r'Log\.\w+\s*\(\s*ANG_PACKAGE\s*,\s*(?:"(?:\\.|[^"\\])*"|[^,()]+)\s*,\s*[^)\n]+\)')
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
        self.assertNotRegex(refresh, URL_INTERPOLATION)
        self.assertNotRegex(refresh, THROWABLE_LOG)

    def test_guards_reject_interpolated_urls_and_throwables(self):
        for unsafe in (
            'Log.w(ANG_PACKAGE, "Subscription failed: $url")',
            'Log.w(ANG_PACKAGE, "Subscription failed: ${url}")',
        ):
            self.assertRegex(unsafe, URL_INTERPOLATION)
        for unsafe in (
            'Log.w(ANG_PACKAGE, "request failed", e)',
            'Log.e(ANG_PACKAGE, "request failed", error)',
            'Log.w(ANG_PACKAGE, "request failed", e.cause)',
            'Log.w(ANG_PACKAGE, "request failed", cause)',
            'Log.w(ANG_PACKAGE, "request failed", exception.cause)',
        ):
            self.assertRegex(unsafe, THROWABLE_LOG)


if __name__ == "__main__":
    unittest.main()
