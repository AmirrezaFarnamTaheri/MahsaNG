"""Keep persistent test ownership while reducing RecyclerView invalidations."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'app' / 'src' / 'main'
VIEWMODEL = ROOT / 'kotlin' / 'com' / 'v2ray' / 'ang' / 'viewmodel' / 'MainViewModel.kt'
ACTIVITY = ROOT / 'kotlin' / 'com' / 'v2ray' / 'ang' / 'ui' / 'MainActivity.kt'

class TcpUiBatchContract(unittest.TestCase):
    def test_tcp_results_still_require_ownership_before_persistent_write(self):
        source = VIEWMODEL.read_text()
        block = source.split('fun testAllTcping()', 1)[1].split('fun testAllRealPing()', 1)[0]
        self.assertIn('testRuns.publishIfCurrent(runId, guid)', block)
        self.assertIn('MmkvManager.encodeServerTestDelayMillis(guid, delay)', block)
        self.assertIn('queueTcpDisplayUpdate(runId, guid)', block)
        self.assertNotIn('updateListAction.value = getPosition(guid)', block)

    def test_batched_rows_are_rendered_as_ranges(self):
        source = ACTIVITY.read_text()
        self.assertIn('updateListBatchAction.observe(this)', source)
        self.assertIn('TcpRowBatch.ranges(indices, adapter.itemCount)', source)
        self.assertIn('adapter.notifyItemRangeChanged', source)

if __name__ == '__main__': unittest.main()
