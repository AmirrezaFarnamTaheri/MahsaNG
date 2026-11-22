"""Behavioral tests for manual physical Android VPN handover QA gate.

The fake ADB only returns coarse package and PID information. No real device or
private VPN profiles are accessed by these tests.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("qa-physical-handover.py")

FAKE_ADB = '''#!/usr/bin/env python3
import os
from pathlib import Path
import sys
args = sys.argv[1:]
scenario = os.environ.get("FAKE_SCENARIO", "normal")
root = Path(os.environ["FAKE_ADB_DIR"])
with (root / "calls").open("a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\\n")
if args[:2] != ["-s", "QA-DEVICE"]:
    sys.exit(80)
command = args[2:]
if command == ["get-state"]:
    print("offline" if scenario == "offline" else "device")
elif command == ["shell", "pm", "path", "com.MahsaNG.EMS.dev"]:
    print("package:/data/app/base.apk")
elif command[:3] == ["shell", "pidof", "com.MahsaNG.EMS.dev:RunSoLibV2RayDaemon"]:
    marker = root / "xray_count"
    count = int(marker.read_text()) + 1 if marker.exists() else 1
    marker.write_text(str(count))
    print("555" if scenario != "replacement" or count < 3 else "888")
elif command[:3] == ["shell", "pidof", "com.MahsaNG.EMS.dev:PsiphonDaemon"]:
    if scenario != "missing_psiphon":
        print("777")
    else:
        sys.exit(1)
else:
    sys.exit(81)
'''


class PhysicalHandoverQaTest(unittest.TestCase):
    def execute(self, *, scenario="normal", mode="xray-vpn", operator_input=None,
                extra_args=()):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            fake = bin_dir / "adb"
            fake.write_text(FAKE_ADB, encoding="utf-8", newline="\n")
            fake.chmod(0o755)
            if os.name == "nt":
                fake_bat = bin_dir / "adb.cmd"
                fake_bat.write_text(f'@"{sys.executable}" "{fake}" %*\r\n', encoding="utf-8")
            report = root / "report.json"
            env = os.environ.copy()
            env.update(
                PATH=str(bin_dir) + os.pathsep + env.get("PATH", ""),
                FAKE_SCENARIO=scenario,
                FAKE_ADB_DIR=str(root),
            )
            args = [sys.executable, str(SCRIPT), "--serial", "QA-DEVICE",
                    "--mode", mode, "--report", str(report), *extra_args]
            result = subprocess.run(
                args, input=operator_input if operator_input is not None
                else "READY\nPASS\n" * 3,
                text=True, capture_output=True, env=env, timeout=20,
            )
            evidence = json.loads(report.read_text(encoding="utf-8")) if report.exists() else None
            calls = (root / "calls").read_text(encoding="utf-8") if (root / "calls").exists() else ""
            return result, evidence, calls

    def test_pass_requires_three_operator_confirmations_and_stable_xray_process(self):
        result, report, calls = self.execute()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("OPERATOR_ATTESTED", report["result"])
        self.assertEqual(["wifi", "cellular", "wifi-restored"],
                         [stage["phase"] for stage in report["stages"]])
        self.assertTrue(all(stage["pid_stable"] and stage["browser_confirmed"]
                            for stage in report["stages"]))
        self.assertIn("shell pidof com.MahsaNG.EMS.dev:RunSoLibV2RayDaemon", calls)
        self.assertNotIn("PsiphonDaemon", calls)
        self.assertNotIn("logcat", calls)
        self.assertNotIn("dumpsys", calls)
        self.assertNotIn("QA-DEVICE", json.dumps(report))
        self.assertFalse(report["network_transport_device_verified"])
        self.assertFalse(report["tunnel_packet_path_device_verified"])

    def test_psiphon_chained_mode_requires_both_distinct_daemons(self):
        result, report, calls = self.execute(mode="psiphon-via-xray")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("OPERATOR_ATTESTED", report["result"])
        self.assertIn("shell pidof com.MahsaNG.EMS.dev:PsiphonDaemon", calls)
        self.assertIn("shell pidof com.MahsaNG.EMS.dev:RunSoLibV2RayDaemon", calls)

    def test_missing_psiphon_process_fails_closed(self):
        result, report, _ = self.execute(mode="psiphon-via-xray", scenario="missing_psiphon")
        self.assertNotEqual(0, result.returncode)
        self.assertNotEqual("OPERATOR_ATTESTED", (report or {}).get("result"))

    def test_process_replacement_during_handover_fails_closed(self):
        result, report, _ = self.execute(scenario="replacement")
        self.assertNotEqual(0, result.returncode)
        self.assertNotEqual("OPERATOR_ATTESTED", (report or {}).get("result"))
        self.assertIn("process changed", result.stderr.lower())

    def test_operator_rejects_browser_confirmation(self):
        result, report, _ = self.execute(operator_input="READY\nNO\n")
        self.assertNotEqual(0, result.returncode)
        self.assertNotEqual("OPERATOR_ATTESTED", (report or {}).get("result"))
        self.assertNotIn("handover passed", result.stdout.lower())

    def test_offline_adb_fails_without_claiming_success(self):
        result, report, _ = self.execute(scenario="offline")
        self.assertNotEqual(0, result.returncode)
        self.assertNotEqual("OPERATOR_ATTESTED", (report or {}).get("result"))

    def test_serial_is_required_to_prevent_wrong_device_selection(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--mode", "xray-vpn"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("--serial", result.stderr)

    def test_report_writes_only_coarse_attestations(self):
        result, report, _ = self.execute()
        self.assertEqual(0, result.returncode, result.stderr)
        encoded = json.dumps(report)
        for unsafe in ("QA-DEVICE", "https://", "ssid", "credential", "networkId", "555"):
            with self.subTest(unsafe=unsafe):
                self.assertNotIn(unsafe, encoded)


if __name__ == "__main__":
    unittest.main()
