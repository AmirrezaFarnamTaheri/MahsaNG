"""Keep registered activities usable when their TV overrides need missing assets."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "app/src/main/res"
ARCHIVE = ROOT / "docs/unimplemented-ui/layout-television-variants"


class TelevisionFallbackTests(unittest.TestCase):
    def test_registered_activities_use_existing_compilable_mobile_fallback(self):
        for name in ("activity_main", "activity_logcat"):
            with self.subTest(screen=name):
                fallback = RES / "layout" / (name + ".xml")
                television = RES / "layout-television" / (name + ".xml")
                original = ARCHIVE / (name + ".xml")
                self.assertTrue(fallback.is_file())
                self.assertFalse(television.exists())
                self.assertTrue(original.is_file())
                ET.parse(fallback)
                ET.parse(original)


if __name__ == "__main__":
    unittest.main()
