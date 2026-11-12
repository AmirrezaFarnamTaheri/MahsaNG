import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from audit_native_aar_compatibility import examine


def write_aar(path, classes, libraries):
    class_bytes = io.BytesIO()
    with zipfile.ZipFile(class_bytes, 'w') as jar:
        for klass in classes:
            jar.writestr(klass, b'dummy')
    with zipfile.ZipFile(path, 'w') as aar:
        aar.writestr('classes.jar', class_bytes.getvalue())
        for name, value in libraries.items():
            aar.writestr(name, value)


class NativeCompatibilityTests(unittest.TestCase):
    def test_shared_go_seq_and_native_library_are_release_blockers(self):
        with tempfile.TemporaryDirectory() as temp:
            xray, psi = Path(temp) / 'xray.aar', Path(temp) / 'psi.aar'
            write_aar(xray, ['go/Seq.class', 'libv2ray/Libv2ray.class'],
                      {'jni/arm64-v8a/libgojni.so': b'xray'})
            write_aar(psi, ['go/Seq.class', 'psi/Psi.class', 'ca/psiphon/PsiphonTunnel.class'],
                      {'jni/arm64-v8a/libgojni.so': b'psi'})
            result = examine(xray, psi, local_tunnel_source=True)
            self.assertFalse(result['safe_to_combine'])
            self.assertIn('go/Seq.class', result['duplicate_classes'])
            self.assertIn('arm64-v8a/libgojni.so', result['native_collisions'])
            self.assertTrue(result['duplicate_local_psiphon_tunnel'])

    def test_distinct_bindings_with_full_abis_are_not_reported_as_collisions(self):
        with tempfile.TemporaryDirectory() as temp:
            xray, psi = Path(temp) / 'xray.aar', Path(temp) / 'psi.aar'
            write_aar(xray, ['libv2ray/Libv2ray.class'],
                      {'jni/' + abi + '/libxray.so': b'xray'
                       for abi in ('armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64')})
            write_aar(psi, [
                'psi/Psi.class', 'psi/PsiphonProvider.class',
                'psi/PsiphonProviderFeedbackHandler.class',
                'psi/PsiphonProviderNetwork.class',
                'psi/PsiphonProviderNoticeHandler.class',
            ], {'jni/' + abi + '/libpsiphon.so': b'psi'
                for abi in ('armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64')})
            result = examine(xray, psi, local_tunnel_source=False)
            self.assertTrue(result['safe_to_combine'])
            self.assertFalse(result['duplicate_classes'])
            self.assertFalse(result['native_collisions'])

    def test_missing_native_psi_api_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            xray, psi = Path(temp) / 'xray.aar', Path(temp) / 'psi.aar'
            write_aar(xray, ['libv2ray/Libv2ray.class'], {})
            write_aar(psi, ['ca/psiphon/PsiphonTunnel.class'], {})
            result = examine(xray, psi, local_tunnel_source=False)
            self.assertFalse(result['safe_to_combine'])
            self.assertFalse(result['contains_required_psi_api'])

    def test_missing_named_psiphon_native_library_is_a_blocker(self):
        with tempfile.TemporaryDirectory() as temp:
            xray, psi = Path(temp) / 'xray.aar', Path(temp) / 'psi.aar'
            write_aar(xray, ['libv2ray/Libv2ray.class'],
                      {'jni/arm64-v8a/libgojni.so': b'xray'})
            write_aar(psi, ['psi/Psi.class'],
                      {'jni/arm64-v8a/libunrelated.so': b'unknown'})
            result = examine(xray, psi, local_tunnel_source=False)
            self.assertIn('arm64-v8a/libpsiphon.so', result['missing_psiphon_native_libraries'])
            self.assertFalse(result['safe_to_combine'])

    def test_missing_provider_interface_is_a_blocker(self):
        with tempfile.TemporaryDirectory() as temp:
            xray, psi = Path(temp) / 'xray.aar', Path(temp) / 'psi.aar'
            write_aar(xray, ['libv2ray/Libv2ray.class'],
                      {'jni/arm64-v8a/libgojni.so': b'xray'})
            write_aar(psi, ['psi/Psi.class'],
                      {'jni/arm64-v8a/libpsiphon.so': b'psi'})
            result = examine(xray, psi, local_tunnel_source=False)
            self.assertIn('psi/PsiphonProvider.class', result['missing_psi_classes'])
            self.assertFalse(result['safe_to_combine'])

    def test_missing_abi_in_one_library_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            xray, psi = Path(temp) / 'xray.aar', Path(temp) / 'psi.aar'
            write_aar(xray, ['libv2ray/Libv2ray.class'], {
                'jni/arm64-v8a/libxray.so': b'xray',
                'jni/x86_64/libxray.so': b'xray',
            })
            write_aar(psi, ['psi/Psi.class', 'psi/PsiphonProvider.class',
                            'psi/PsiphonProviderFeedbackHandler.class',
                            'psi/PsiphonProviderNetwork.class',
                            'psi/PsiphonProviderNoticeHandler.class'],
                      {'jni/arm64-v8a/libpsiphon.so': b'psi'})
            result = examine(xray, psi, local_tunnel_source=False)
            self.assertIn('x86_64', result['missing_psiphon_abis'])
            self.assertFalse(result['safe_to_combine'])


    def test_empty_xray_native_inventory_never_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            xray, psi = Path(temp) / 'xray.aar', Path(temp) / 'psi.aar'
            providers = [
                'psi/Psi.class', 'psi/PsiphonProvider.class',
                'psi/PsiphonProviderFeedbackHandler.class',
                'psi/PsiphonProviderNetwork.class',
                'psi/PsiphonProviderNoticeHandler.class',
            ]
            write_aar(xray, ['libv2ray/Libv2ray.class'], {})
            write_aar(psi, providers, {
                'jni/' + abi + '/libpsiphon.so': b'psi'
                for abi in ('armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64')
            })
            result = examine(xray, psi, local_tunnel_source=False)
            self.assertFalse(result['safe_to_combine'])
            self.assertEqual(4, len(result['missing_xray_abis']))

    def test_incomplete_xray_abi_inventory_never_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            xray, psi = Path(temp) / 'xray.aar', Path(temp) / 'psi.aar'
            write_aar(xray, ['libv2ray/Libv2ray.class'],
                      {'jni/arm64-v8a/libgojni.so': b'xray'})
            write_aar(psi, ['psi/Psi.class'],
                      {'jni/arm64-v8a/libpsiphon.so': b'psi'})
            result = examine(xray, psi, local_tunnel_source=False)
            self.assertFalse(result['safe_to_combine'])
            self.assertIn('x86_64', result['missing_xray_abis'])

    def test_so_in_aar_libs_is_not_a_packaged_jni_library(self):
        with tempfile.TemporaryDirectory() as temp:
            xray, psi = Path(temp) / 'xray.aar', Path(temp) / 'psi.aar'
            write_aar(xray, ['libv2ray/Libv2ray.class'], {
                'jni/' + abi + '/libgojni.so': b'xray'
                for abi in ('armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64')
            })
            write_aar(psi, [
                'psi/Psi.class', 'psi/PsiphonProvider.class',
                'psi/PsiphonProviderFeedbackHandler.class',
                'psi/PsiphonProviderNetwork.class',
                'psi/PsiphonProviderNoticeHandler.class',
            ], {'libs/' + abi + '/libpsiphon.so': b'not packaged'
                for abi in ('armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64')})
            result = examine(xray, psi, local_tunnel_source=False)
            self.assertFalse(result['safe_to_combine'])
            self.assertIn('arm64-v8a/libpsiphon.so', result['missing_psiphon_native_libraries'])


if __name__ == '__main__':
    unittest.main()
