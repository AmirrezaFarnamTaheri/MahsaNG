#!/usr/bin/env bash
set -euo pipefail

# This source returns full JSON including hostnames, user IDs and passwords.
# The config generator must not make Android log calls with this content.
file="V2rayNG/app/src/main/kotlin/com/v2ray/ang/util/V2rayConfigUtil.kt"
if grep -nE 'Log\.[[:alpha:]]+\(' "$file"; then
  printf '%s\n' 'ERROR: Generated proxy configurations must never be written to Android logs.' >&2
  exit 1
fi
echo "PASS: No Android log calls in the core configuration generator"
