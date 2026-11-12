"""Exercise the actual Bash emulator gate with a controlled fake ADB."""
import os
import pathlib
import subprocess
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).with_name("smoke-android-emulator.sh")


class EmulatorForegroundSmokeTest(unittest.TestCase):
    def run_smoke(self, mode):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            binaries = root / "bin"
            binaries.mkdir()
            apk_dir = root / "V2rayNG/app/build/outputs/apk/dev/debug"
            apk_dir.mkdir(parents=True)
            (apk_dir / "v2rayNG-dev_x86_64.apk").write_bytes(b"test APK")
            adb = binaries / "adb"
            adb.write_text("""#!/usr/bin/env python3
import os
import pathlib
import sys
args = sys.argv[1:]
marker = pathlib.Path(os.environ["FAKE_MARKER"])
mode = os.environ["FAKE_MODE"]
if args[:3] == ["shell", "dumpsys", "activity"]:
    if mode == "wrong":
        print("topResumedActivity=ActivityRecord{u0 com.example.other/.OtherActivity t1}")
    elif mode == "permission" and not marker.exists():
        print("topResumedActivity=ActivityRecord{u0 com.google.android.permissioncontroller/com.android.permissioncontroller.GrantPermissionsActivity t1}")
    else:
        print("topResumedActivity=ActivityRecord{u0 com.MahsaNG.EMS.dev/com.v2ray.ang.ui.MainActivity t1}")
elif args[:3] == ["shell", "input", "keyevent"]:
    marker.touch()
elif args[:3] == ["shell", "pm", "path"]:
    print("package:/data/app/base.apk")
elif args[:3] == ["shell", "pidof", "com.MahsaNG.EMS.dev"]:
    print("2456")
elif args[:3] == ["shell", "dumpsys", "package"]:
    print("com.v2ray.ang.service.PsiphonVpnService")
elif args[:2] == ["install", "-r"]:
    print("Success")
elif args[:3] == ["shell", "am", "start"]:
    print("Status: ok")
sys.exit(0)
""", encoding="utf-8")
            adb.chmod(0o755)
            fast_sleep = binaries / "sleep"
            fast_sleep.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fast_sleep.chmod(0o755)
            environment = os.environ.copy()
            marker = root / "permission-denied"
            environment.update(
                FAKE_MARKER=str(marker),
                FAKE_MODE=mode,
                GITHUB_WORKSPACE=str(root),
                PATH=str(binaries) + os.pathsep + environment.get("PATH", ""),
            )
            result = subprocess.run(
                ["bash", str(SCRIPT)],
                capture_output=True,
                text=True,
                env=environment,
                timeout=25,
            )
            return result, marker.exists()

    def test_success_requires_actual_main_activity_in_foreground(self):
        result, denied = self.run_smoke("normal")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(denied)
        self.assertIn("Emulator smoke passed", result.stdout)

    def test_initial_android_permission_dialog_is_denied_and_main_resumes(self):
        result, denied = self.run_smoke("permission")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(denied)

    def test_live_process_but_wrong_foreground_activity_fails(self):
        result, denied = self.run_smoke("wrong")
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(denied)
        self.assertIn("MainActivity was not resumed", result.stderr)


if __name__ == "__main__":
    unittest.main()
