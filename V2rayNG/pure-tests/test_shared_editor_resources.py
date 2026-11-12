"""Structural regression for the Hysteria2 editor's shared address/port block."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / 'app/src/main/res'
ANDROID = '{http://schemas.android.com/apk/res/android}'

class SharedEditorResourceTests(unittest.TestCase):
    def test_shared_editor_has_required_address_port_and_remark_fields(self):
        path = ROOT / 'layout/layout_address_port.xml'
        self.assertTrue(path.is_file(), 'Hysteria2 includes this layout and needs editor fields')
        root = ET.parse(path).getroot()
        fields = {}
        for field in root.iter('EditText'):
            identifier = field.get(ANDROID + 'id', '')
            fields[identifier] = field
        for name in ('et_remarks', 'et_address', 'et_port'):
            self.assertIn('@+id/' + name, fields)
        self.assertEqual('number', fields['@+id/et_port'].get(ANDROID + 'inputType'))

    def test_missing_critical_labels_have_meaningful_text(self):
        path = ROOT / 'values/active_screen_compat.xml'
        self.assertTrue(path.is_file())
        root = ET.parse(path).getroot()
        values = {node.get('name'): ''.join(node.itertext()).strip() for node in root}
        for key in ('server_lab_bandwidth_down', 'server_lab_bandwidth_up', 'server_lab_finalmask_hysteria2'):
            self.assertTrue(values.get(key), key + ' is missing')

if __name__ == '__main__':
    unittest.main()
