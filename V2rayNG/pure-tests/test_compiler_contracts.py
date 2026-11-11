"""Regression coverage for source-level defects diagnosed by the full Android build.

These fast checks complement, and never replace, the mandatory Kotlin compiler.
"""
from pathlib import Path
import re
import unittest

APP = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang"


class KotlinSourceContractTests(unittest.TestCase):
    def test_share_config_explicitly_rejects_unsupported_http_and_hysteria_cases(self):
        source = (APP / "util/AngConfigManager.kt").read_text(encoding="utf-8")
        start = source.index("return config.configType.protocolScheme + when (config.configType)")
        end = source.index("} catch (e: Exception)", start)
        branches = source[start:end]
        self.assertRegex(branches, r"EConfigType\\.HTTP\\s*,\\s*EConfigType\\.HYSTERIA2\\s*->\\s*\"\"")

    def test_uri_exports_reject_missing_endpoint_without_crashing(self):
        for name in ("ShadowsocksFmt", "SocksFmt", "TrojanFmt", "VlessFmt", "WireguardFmt"):
            with self.subTest(name=name):
                source = (APP / "util/fmt" / (name + ".kt")).read_text(encoding="utf-8")
                start = source.index("fun toUri(config: ServerConfig)")
                body = source[start:]
                self.assertIn("val address = outbound.getServerAddress() ?: return \"\"", body)
                self.assertIn("Utils.getIpv6Address(address)", body)

    def test_plugin_package_lookup_and_registration_are_defined(self):
        manager = (APP / "plugin/PluginManager.kt").read_text(encoding="utf-8")
        resolved = (APP / "plugin/ResolvedPlugin.kt").read_text(encoding="utf-8")
        helper = APP / "extension/PluginPackageChange.kt"
        self.assertTrue(helper.is_file())
        code = helper.read_text(encoding="utf-8")
        self.assertIn("fun Context.listenForPackageChanges(", code)
        self.assertIn("fun Context.getPackageInfo(", code)
        self.assertIn("Intent.ACTION_PACKAGE_REPLACED", code)
        self.assertIn("Intent.ACTION_PACKAGE_REMOVED", code)
        self.assertIn('filter.addDataScheme("package")', code)
        self.assertIn("cachedPlugins = null", manager)
        # Repeated invalidation must not leak another registered receiver each time.
        self.assertNotIn("receiver = null", manager)
        self.assertIn("getPackageInfo(componentInfo.packageName)", resolved)


if __name__ == "__main__":
    unittest.main()
