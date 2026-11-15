"""Preserve TCP socket route and run ownership while showing safe attempt evidence."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1] / "app/src/main"
SPEED = ROOT / "kotlin/com/v2ray/ang/util/SpeedtestUtil.kt"
VM = ROOT / "kotlin/com/v2ray/ang/viewmodel/MainViewModel.kt"
ADAPTER = ROOT / "kotlin/com/v2ray/ang/ui/MainRecyclerAdapter.kt"

class TcpEvidenceContract(unittest.TestCase):
    def test_existing_tcp_socket_probe_and_persistent_ownership_are_preserved(self):
        speed = SPEED.read_text()
        vm = VM.read_text()
        self.assertIn("SocketConnectTimer.measure(", speed)
        self.assertIn("TcpProbePreset.fromStored(", speed)
        self.assertIn("SpeedtestUtil.tcpingEvidence(address, port)", vm)
        self.assertIn("testRuns.publishIfCurrent(runId, guid)", vm)
        self.assertIn("MmkvManager.encodeServerTestDelayMillis(guid, delay)", vm)
        self.assertIn("tcpEvidenceByGuid[guid] = evidence", vm)

    def test_displays_safe_failure_reasons_without_sensitive_exception_content(self):
        adapter = ADAPTER.read_text()
        self.assertIn("showTcpEvidence(tcpEvidence)", adapter)
        self.assertIn("SafeProbeFailure.Kind.TIMEOUT", adapter)
        self.assertIn("SafeProbeFailure.Kind.DNS", adapter)
        self.assertNotIn("error.message", adapter)
        self.assertNotIn("printStackTrace()", (ROOT / "kotlin/com/v2ray/ang/util/TcpProbeEvidence.kt").read_text())

    def test_profile_edits_invalidate_only_matching_stale_evidence(self):
        vm = VM.read_text()
        self.assertIn('tcpEvidenceRevisions[guid] != profileDigest(config)', vm)
        self.assertIn('tcpEvidenceByGuid.remove(guid)', vm)
        self.assertIn('tcpEvidenceRevisions.remove(guid)', vm)

    def test_english_persian_labels_match(self):
        labels = []
        for lang in ("values", "values-fa"):
            xml = ET.parse(ROOT / "res" / lang / "tcp_probe_evidence.xml")
            labels.append({x.attrib["name"] for x in xml.findall("string")})
        self.assertEqual(labels[0], labels[1])

if __name__ == "__main__": unittest.main()
