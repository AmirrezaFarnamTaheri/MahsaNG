"""Regression for emulator runner's per-line shell process semantics."""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/mahsa-safety.yml'
SMOKE = ROOT / 'V2rayNG/pure-tests/smoke-android-emulator.sh'


class EmulatorSmokeContractTest(unittest.TestCase):
    def test_emulator_action_invokes_single_stateful_bash_process(self):
        workflow = WORKFLOW.read_text(encoding='utf-8')
        step = workflow.split('name: Install and launch real devDebug APK on Android 35 emulator', 1)[1]
        self.assertIn('uses: reactivecircus/android-emulator-runner@v2', step)
        self.assertRegex(step, r'(?m)^\s*script: bash V2rayNG/pure-tests/smoke-android-emulator\.sh\s*$')
        self.assertNotIn('script: |', step, 'Multiple script lines lose shell local variables in this action')

    def test_smoke_script_has_valid_bash_syntax_and_checks_real_app(self):
        self.assertTrue(SMOKE.is_file())
        result = subprocess.run(['bash', '-n', str(SMOKE)], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        script = SMOKE.read_text(encoding='utf-8')
        for required in (
            'set -euo pipefail', 'adb install -r', 'adb shell pm path',
            'adb shell am start -W', 'adb shell pidof', 'PsiphonVpnService',
            '*_x86_64.apk',
        ):
            with self.subTest(required=required):
                self.assertIn(required, script)


if __name__ == '__main__':
    unittest.main()
