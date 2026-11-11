"""Keep the compiled main screen's report and status image references valid."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

RES = Path(__file__).resolve().parents[1] / 'app/src/main/res'
ANDROID = '{http://schemas.android.com/apk/res/android}'
APP = '{http://schemas.android.com/apk/res-auto}'

class MainScreenResourcesTest(unittest.TestCase):
    def test_report_button_has_authored_vector_flag(self):
        target = RES / 'drawable/report_flag1.xml'
        self.assertTrue(target.is_file(), 'Main screen report flag is missing')
        root = ET.parse(target).getroot()
        self.assertEqual('vector', root.tag)
        self.assertTrue(root.findall('path'), 'Flag vector must render visible paths')

    def test_main_screen_uses_existing_status_icon(self):
        root = ET.parse(RES / 'layout/activity_main.xml').getroot()
        nodes = [n for n in root.iter() if n.get(ANDROID+'id') == '@+id/report_flag_button']
        self.assertEqual(1, len(nodes))
        self.assertEqual('@drawable/report_flag1', nodes[0].get(ANDROID+'src'))
        xml = (RES / 'layout/activity_main.xml').read_text(encoding='utf-8')
        self.assertNotIn('@drawable/ic_stat_name_m2', xml)

if __name__ == '__main__':
    unittest.main()
