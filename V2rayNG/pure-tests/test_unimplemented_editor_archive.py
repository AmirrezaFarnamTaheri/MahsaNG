"""Fail CI if unsupported protocol editor layouts enter the Android resource graph.

The Android source in this tree has no backed EConfigType or ServerActivity route
for these editor screens. Keep their source XML for a future implementation.
"""
from pathlib import Path
import unittest
import re

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app/src/main'
ARCHIVE = ROOT / 'docs/unimplemented-ui/layout-orphans'
ORPHANS = (
    'activity_server_dnstt',
    'activity_server_gooserelay',
    'activity_server_masterdns',
    'activity_server_psiphon',
    'activity_server_skirk',
)

class UnimplementedEditorArchiveTest(unittest.TestCase):
    def test_source_is_preserved_but_unimplemented_layouts_are_not_compiled(self):
        for name in ORPHANS:
            with self.subTest(layout=name):
                self.assertTrue((ARCHIVE / (name + '.xml')).is_file(),
                                'Preserve original XML before removing it from resources')
                self.assertFalse((APP / 'res/layout' / (name + '.xml')).exists(),
                                 'Unimplemented editor cannot compile without its backing feature')

    def test_no_source_compiles_against_missing_editor_layouts(self):
        pattern = re.compile(r'R\\.layout\\.(' + '|'.join(ORPHANS) + r')\\b')
        for location in (APP / 'java', APP / 'kotlin'):
            for file in location.rglob('*'):
                if file.suffix in ('.kt', '.java'):
                    with self.subTest(file=file.name):
                        self.assertIsNone(pattern.search(file.read_text(encoding='utf-8')),
                                          'Restore editor implementation and resources together')

if __name__ == '__main__':
    unittest.main()
