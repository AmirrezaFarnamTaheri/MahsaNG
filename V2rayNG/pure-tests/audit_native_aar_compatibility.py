"""Report binary-class, native-library and ABI conflicts between two Android AARs.

Fail closed: a passing Gradle dependency resolution is not proof that two gomobile
runtimes can be safely packaged or loaded in an Android process.
"""

import argparse
import io
import json
import sys
from pathlib import Path
from zipfile import ZipFile


def _inventory(path):
    with ZipFile(path) as aar:
        names = set(aar.namelist())
        if 'classes.jar' not in names:
            raise ValueError(f'{path}: missing classes.jar')
        with ZipFile(io.BytesIO(aar.read('classes.jar'))) as classes:
            classnames = {n for n in classes.namelist() if n.endswith('.class')}
        binaries = {}
        for name in names:
            pieces = name.split('/')
            if len(pieces) == 3 and pieces[0] in ('jni', 'libs') and name.endswith('.so'):
                binaries[pieces[1] + '/' + pieces[2]] = name
        return classnames, binaries


def examine(xray, psiphon, local_tunnel_source=True):
    x_classes, x_natives = _inventory(xray)
    p_classes, p_natives = _inventory(psiphon)
    x_abis = {p.split('/')[0] for p in x_natives}
    p_abis = {p.split('/')[0] for p in p_natives}
    duplicates = sorted(x_classes & p_classes)
    collisions = sorted(set(x_natives) & set(p_natives))
    local_conflict = local_tunnel_source and 'ca/psiphon/PsiphonTunnel.class' in p_classes
    contains_psi = 'psi/Psi.class' in p_classes
    missing_abis = sorted(x_abis - p_abis)
    return {
        'safe_to_combine': not (duplicates or collisions or local_conflict or not contains_psi or missing_abis),
        'contains_required_psi_api': contains_psi,
        'duplicate_local_psiphon_tunnel': bool(local_conflict),
        'duplicate_classes': duplicates,
        'native_collisions': collisions,
        'xray_native_abis': sorted(x_abis),
        'psiphon_native_abis': sorted(p_abis),
        'missing_psiphon_abis': missing_abis,
        'xray_class_count': len(x_classes),
        'psiphon_class_count': len(p_classes),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xray', type=Path, required=True)
    parser.add_argument('--psiphon', type=Path, required=True)
    parser.add_argument('--local-tunnel-source', type=Path, required=True)
    args = parser.parse_args(argv)
    result = examine(args.xray, args.psiphon, args.local_tunnel_source.exists())
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result['safe_to_combine']:
        print('BLOCKED: cannot combine these AARs without resolving all class/JNI collisions', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
