"""Prevent invalid two-argument Android string formatting from returning."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

RES = Path(__file__).resolve().parents[1] / 'app/src/main/res'
LOCALES = ('values', 'values-fa', 'values-ru', 'values-zh-rCN')

class LocalizedStringTests(unittest.TestCase):
    def test_connection_test_two_pings_use_positional_format_specifiers(self):
        for locale in LOCALES:
            with self.subTest(locale=locale):
                root = ET.parse(RES / locale / 'strings.xml').getroot()
                text = next((node.text or '') for node in root.iter('string')
                            if node.get('name') == 'connection_test_available')
                self.assertIn('%1$d', text)
                self.assertIn('%2$d', text)
                self.assertNotIn(' %d ', text)

if __name__ == '__main__':
    unittest.main()
