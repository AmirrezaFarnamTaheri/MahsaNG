"""Regression: probe exceptions must not echo attacker-controlled credentials."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "app" / "src" / "main"
SPEED = ROOT / "kotlin" / "com" / "v2ray" / "ang" / "util" / "SpeedtestUtil.kt"

class SafeProbeErrorContract(unittest.TestCase):
    def test_full_stacktraces_and_exception_messages_are_never_shown(self):
        source = SPEED.read_text(encoding="utf-8")
        self.assertNotIn("printStackTrace()", source)
        self.assertNotIn("Log.getStackTraceString", source)
        self.assertNotIn("e.message", source)
        self.assertNotIn('"realPing: $e"', source)
        self.assertNotIn('"socketConnectTime IOException: $e"', source)
        self.assertIn("SafeProbeFailure.safeReason(e)", source)
        self.assertIn("SafeProbeFailure.classify(e)", source)

    def test_english_persian_failure_labels_match(self):
        names = []
        for locale in ("values", "values-fa"):
            xml = ET.parse(ROOT / "res" / locale / "safe_probe_failures.xml")
            labels = {n.attrib["name"]: (n.text or "") for n in xml.findall(".//string")}
            self.assertEqual(6, len(labels))
            self.assertTrue(all(x.strip() for x in labels.values()))
            names.append(set(labels))
        self.assertEqual(names[0], names[1])

if __name__ == "__main__":
    unittest.main()
