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
        callback_start = block.index('testRuns.publishIfCurrent(runId, guid) {')
        brace = block.index('{', callback_start)
        depth = 0
        callback_end = None
        for i in range(brace, len(block)):
            if block[i] == '{':
                depth += 1
            elif block[i] == '}':
                depth -= 1
                if depth == 0:
                    callback_end = i
                    break
        self.assertIsNotNone(callback_end)
        callback = block[brace:callback_end]
        self.assertIn('MmkvManager.encodeServerTestDelayMillis(guid, delay)', callback)
        self.assertIn('queueTcpDisplayUpdate(runId, guid)', callback)
        self.assertLess(callback.index('MmkvManager.encodeServerTestDelayMillis(guid, delay)'),
                        callback.index('queueTcpDisplayUpdate(runId, guid)'))
        self.assertNotIn('updateListAction.value = getPosition(guid)', block)

    def test_filtered_updates_rebuild_membership_instead_of_just_rebinding(self):
        source = VIEWMODEL.read_text()
        self.assertIn('if (probeFilterActive()) updateCache()', source)
        self.assertIn('tcpEvidenceRevisions[guid] = profileDigest(current)', source)
        self.assertIn('tcpEvidenceByGuid.remove(guid)', source)
        self.assertIn('if (probeFilterActive()) {', source)
        self.assertIn('updateListAction.value = -1', source)

    def test_batched_rows_are_rendered_as_ranges(self):
        source = ACTIVITY.read_text()
        self.assertIn('updateListBatchAction.observe(this)', source)
        self.assertIn('TcpRowBatch.ranges(indices, adapter.itemCount)', source)
        self.assertIn('adapter.notifyItemRangeChanged', source)

if __name__ == '__main__': unittest.main()
