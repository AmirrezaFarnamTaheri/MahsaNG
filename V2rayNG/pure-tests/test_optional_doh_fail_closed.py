"""Prove optional YouTube/DoH stays disabled without its unpublished parser."""
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'app/src/main/kotlin/com/v2ray/ang/gfwknocker/BackServ.kt'

class OptionalDohGuardTests(unittest.TestCase):
    def test_missing_config_parser_is_not_called_by_running_tunnel(self):
        source = SOURCE.read_text(encoding='utf-8')
        self.assertNotIn('config_pkg_reader(', source)
        self.assertIn('require(!is_youtube)', source)
        self.assertLess(source.index('require(!is_youtube)'), source.index('TLS_serv = TLS_Fragmentor('))

if __name__ == '__main__':
    unittest.main()
