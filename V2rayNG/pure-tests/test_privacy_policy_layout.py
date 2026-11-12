"""The compiled privacy-policy Activity must have the matching accessible layout."""
from pathlib import Path
from xml.etree import ElementTree
import unittest

ROOT = Path(__file__).resolve().parents[1]
ANDROID_NS = "http://schemas.android.com/apk/res/android"


class PrivacyPolicyLayoutTest(unittest.TestCase):
    def test_existing_local_privacy_policy_asset_has_a_readable_screen(self):
        policy = ROOT / "app/src/main/assets/privacy_policy.txt"
        layout = ROOT / "app/src/main/res/layout/activity_gfw_privacy_policy.xml"
        self.assertTrue(policy.is_file(), "The source-backed local privacy policy must remain available")
        self.assertTrue(layout.is_file(), "Restore the privacy Activity's actual referenced layout")
        root = ElementTree.parse(layout).getroot()
        views = root.iter()
        texts = [node for node in views if node.tag.endswith("TextView")]
        self.assertTrue(any(node.attrib.get(f"{{{ANDROID_NS}}}id") == "@+id/textView_privacy_policy"
                            for node in texts))
        self.assertTrue(any(node.attrib.get(f"{{{ANDROID_NS}}}textIsSelectable") == "true"
                            for node in texts))


if __name__ == "__main__":
    unittest.main()
