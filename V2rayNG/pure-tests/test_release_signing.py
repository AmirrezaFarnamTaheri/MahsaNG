"""A release APK must never be signed with the shared Android debug key."""
from pathlib import Path
import re
import unittest

GRADLE = Path(__file__).resolve().parents[1] / "app/build.gradle"


class ReleaseSigningTest(unittest.TestCase):
    def test_release_variant_does_not_use_debug_signing(self):
        source = GRADLE.read_text(encoding="utf-8")
        release = re.search(
            r"buildTypes\s*\{[\s\S]*?\brelease\s*\{(?P<release>[\s\S]*?)\n\s*\}\s*\n\s*debug\s*\{",
            source,
        )
        self.assertIsNotNone(release, "cannot locate release build type")
        self.assertNotRegex(release.group("release"), r"signingConfig\s+signingConfigs\.debug\b")


if __name__ == "__main__":
    unittest.main()
