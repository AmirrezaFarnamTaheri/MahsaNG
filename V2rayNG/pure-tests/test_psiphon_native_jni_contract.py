"""A routed Psiphon VPN must package the real official tun2socks JNI module.

The existing libtun2socks.so is a V2Ray executable, not this Java JNI bridge.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github/workflows/mahsa-safety.yml").read_text(encoding="utf-8")
LOADER = (ROOT / "V2rayNG/app/src/main/java/ca/psiphon/Tun2SocksJniLoader.java").read_text(encoding="utf-8")


class PsiphonNativeJniContractTest(unittest.TestCase):
    def test_loader_requires_distinct_native_module(self):
        self.assertIn('System.loadLibrary("tun2socks_psiphon")', LOADER)
        self.assertIn("native static void runTun2Socks(", LOADER)
        self.assertIn("native static void terminateTun2Socks()", LOADER)

    def test_builds_pinned_upstream_source_and_checks_native_jni_symbol(self):
        self.assertIn("https://github.com/Psiphon-Inc/psiphon-android.git", WORKFLOW)
        self.assertIn("c2c043da1208b34d28c3fdeef72b43dcd470dacb", WORKFLOW)
        self.assertIn("ndk-build", WORKFLOW)
        self.assertIn("LOCAL_MODULE := tun2socks_psiphon", WORKFLOW)
        self.assertIn("JNI_OnLoad", WORKFLOW)
        self.assertIn("libtun2socks_psiphon.so", WORKFLOW)

    def test_universal_apk_is_audited_for_all_supported_abis(self):
        self.assertIn("unzip -Z1", WORKFLOW)
        self.assertIn('"lib/$abi/libtun2socks_psiphon.so"', WORKFLOW)
        self.assertIn("armeabi-v7a arm64-v8a x86 x86_64", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
