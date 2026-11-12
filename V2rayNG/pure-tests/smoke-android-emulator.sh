#!/usr/bin/env bash
# One process is essential: android-emulator-runner executes every script line separately.
set -euo pipefail

package_id="com.MahsaNG.EMS.dev"
activity="com.v2ray.ang.ui.MainActivity"
apk_dir="${GITHUB_WORKSPACE:-.}/V2rayNG/app/build/outputs/apk/dev/debug"
apk="$(find "$apk_dir" -maxdepth 1 -type f -name '*_x86_64.apk' -print -quit)"

if [[ -z "$apk" || ! -s "$apk" ]]; then
  echo "No nonempty x86_64 devDebug APK at $apk_dir" >&2
  exit 1
fi

# Limit diagnostics to Android runtime failures; do not dump app preferences/configs.
on_exit() {
  local code=$?
  if (( code != 0 )); then
    echo "Emulator smoke failed (status $code); AndroidRuntime errors:" >&2
    adb logcat -d -s AndroidRuntime:E -t 160 || true
  fi
}
trap on_exit EXIT

adb install -r "$apk"
adb shell pm path "$package_id" | grep -F 'package:'
adb logcat -c
adb shell am start -W -n "$package_id/$activity"
sleep 8

pid="$(adb shell pidof "$package_id" | tr -d '\r\n[:space:]')"
if [[ -z "$pid" ]]; then
  echo "$package_id stopped after launch" >&2
  exit 1
fi

# Check the *installed* manifest, not merely the source file.
adb shell dumpsys package "$package_id" | grep -F 'PsiphonVpnService'
echo "Emulator smoke passed: $package_id running with PID $pid"
