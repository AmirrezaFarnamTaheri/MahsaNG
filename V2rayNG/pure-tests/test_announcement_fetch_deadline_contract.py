"""Announcement retrieval must remain bounded and Android 21 compatible."""
from pathlib import Path
import unittest

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "app/src/main/kotlin/com/v2ray/ang/gfwknocker/wget_module.kt"
)


class AnnouncementFetchSafetyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_total_deadline_applies_to_redirects_and_body(self):
        self.assertIn("TOTAL_FETCH_MS = 20_000L", self.source)
        self.assertIn("fun remainingMillis()", self.source)
        self.assertIn("if (remainingMillis() <= 0) return null", self.source)
        self.assertIn("connection.readTimeout = minOf(10_000L, left)", self.source)

    def test_no_api24_only_content_length_accessor(self):
        self.assertNotIn("connection.contentLengthLong", self.source)
        self.assertIn("connection.contentLength > MAX_ANNOUNCEMENT_BYTES", self.source)

    def test_https_redirect_and_content_bounds_remain(self):
        self.assertIn("uri.scheme.equals(\"https\"", self.source)
        self.assertIn("MAX_ANNOUNCEMENT_BYTES", self.source)
        self.assertIn("if (redirectCount == 3) return null", self.source)


if __name__ == "__main__":
    unittest.main()
