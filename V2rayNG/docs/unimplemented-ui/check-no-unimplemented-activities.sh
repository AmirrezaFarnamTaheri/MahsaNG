#!/usr/bin/env bash
set -euo pipefail

# Quarantine can only be safe while the missing Activities are genuinely absent.
if grep -REn 'AddMasqueActivity|AddWarpActivity|R\\.layout\\.activity_add_(masque|warp)' \
    V2rayNG/app/src/main/java V2rayNG/app/src/main/kotlin V2rayNG/app/src/main/AndroidManifest.xml; then
  echo "ERROR: MASQUE/WARP screen implementation now exists; restore and review archived layouts." >&2
  exit 1
fi
for path in \
  V2rayNG/app/src/main/res/layout/activity_add_masque.xml \
  V2rayNG/app/src/main/res/layout/activity_add_warp.xml \
  V2rayNG/app/src/main/res/layout-television/activity_add_masque.xml \
  V2rayNG/app/src/main/res/layout-television/activity_add_warp.xml; do
  if test -f "$path"; then
    echo "ERROR: Unimplemented MASQUE/WARP layout unexpectedly compiles: $path" >&2
    exit 1
  fi
done
echo "PASS: Unimplemented MASQUE/WARP layouts remain safely archived"
