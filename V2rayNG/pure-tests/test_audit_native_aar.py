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
                      {'jni/arm64-v8a/libxray.so': b'xray'})
            write_aar(psi, ['psi/Psi.class'],
                      {'jni/arm64-v8a/libpsiphon.so': b'psi'})
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

    def test_missing_abi_in_one_library_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            xray, psi = Path(temp) / 'xray.aar', Path(temp) / 'psi.aar'
            write_aar(xray, ['libv2ray/Libv2ray.class'], {
                'jni/arm64-v8a/libxray.so': b'xray',
                'jni/x86_64/libxray.so': b'xray',
            })
            write_aar(psi, ['psi/Psi.class'], {'jni/arm64-v8a/libpsiphon.so': b'psi'})
            result = examine(xray, psi, local_tunnel_source=False)
            self.assertEqual(['x86_64'], result['missing_psiphon_abis'])
            self.assertFalse(result['safe_to_combine'])


if __name__ == '__main__':
    unittest.main()
