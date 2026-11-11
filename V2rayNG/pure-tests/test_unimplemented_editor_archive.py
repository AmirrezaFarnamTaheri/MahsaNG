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
    'activity_gfw_update',
    'activity_terms_service',
    'activity_tunnel_config',
    'activity_update',
    'activity_warp_setting',
    'activity_youtube_config',
    'bottom_sheet_result',
    'gfw_permit_layout',
    'activity_donate_config',
)

class UnimplementedEditorArchiveTest(unittest.TestCase):
    def test_source_is_preserved_but_unimplemented_layouts_are_not_compiled(self):
        for name in ORPHANS:
            with self.subTest(layout=name):
                self.assertTrue((ARCHIVE / (name + '.xml')).is_file(),
                                'Preserve original XML before removing it from resources')
                for resource_dir in (APP / 'res').glob('layout*'):
                    self.assertFalse((resource_dir / (name + '.xml')).exists(),
                                     'Unimplemented editor must not compile in any resource qualifier')

    def test_archived_layouts_have_no_live_xml_includes(self):
        for path in (APP / 'res').rglob('*.xml'):
            content = path.read_text(encoding='utf-8')
            for name in ORPHANS:
                with self.subTest(path=path.name, layout=name):
                    self.assertNotIn('@layout/' + name, content,
                                     'Restore the complete feature instead of archiving a referenced layout')

    def test_referenced_psiphon_settings_layout_remains_compiled(self):
        activity = APP / 'java/com/v2ray/ang/GFW_psiphonSettings_Activity.java'
        self.assertIn('R.layout.activity_gfw_psiphon_settings',
                      activity.read_text(encoding='utf-8'))
        self.assertTrue((APP / 'res/layout/activity_gfw_psiphon_settings.xml').is_file())

    def test_no_source_compiles_against_missing_editor_layouts(self):
        bindings = tuple(''.join(part.title() for part in name.split('_')) + 'Binding'
                         for name in ORPHANS)
        pattern = re.compile(r'R\.layout\.(' + '|'.join(ORPHANS) + r')\b|'
                             + r'\b(' + '|'.join(bindings) + r')\b')
        for location in (APP / 'java', APP / 'kotlin'):
            for file in location.rglob('*'):
                if file.suffix in ('.kt', '.java'):
                    with self.subTest(file=file.name):
                        self.assertIsNone(pattern.search(file.read_text(encoding='utf-8')),
                                          'Restore editor implementation and resources together')

if __name__ == '__main__':
    unittest.main()
