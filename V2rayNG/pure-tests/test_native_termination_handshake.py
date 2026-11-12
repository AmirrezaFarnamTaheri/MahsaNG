"""Native startup cannot erase a preceding termination signal."""
import unittest
from patch_psiphon_tun2socks import harden_tun2socks

UPSTREAM = '''
static void terminateTun2SocksNative(
        JNIEnv *env,
        jclass cls);

    static JNINativeMethod method_table[] = {
        {"terminateTun2Socks", "()V", (void *) terminateTun2SocksNative},
    };

    BLog_InitPsiphon();

    __sync_bool_compare_and_swap(&g_terminate, 1, 0);

    run();

void terminateTun2SocksNative(
        JNIEnv *env,
        jclass cls) {
    __sync_bool_compare_and_swap(&g_terminate, 0, 1);
}
'''


class NativeTerminationHandshakeTest(unittest.TestCase):
    def test_native_start_does_not_reset_sticky_stop(self):
        result = harden_tun2socks(UPSTREAM)
        worker_start = result.split("BLog_InitPsiphon();", 1)[1].split("run();", 1)[0]
        self.assertNotIn("compare_and_swap(&g_terminate, 1, 0)", worker_start)
        self.assertIn('{"prepareTun2Socks", "()V", (void *) prepareTun2SocksNative}', result)
        self.assertEqual(result.count("__sync_bool_compare_and_swap(&g_terminate, 1, 0)"), 1)

    def test_mismatched_pinned_source_fails_closed(self):
        with self.assertRaises(ValueError):
            harden_tun2socks(UPSTREAM.replace("BLog_InitPsiphon();", "BLog_InitOther();"))

    def test_reapplication_fails_closed(self):
        with self.assertRaises(ValueError):
            harden_tun2socks(harden_tun2socks(UPSTREAM))


if __name__ == "__main__":
    unittest.main()
