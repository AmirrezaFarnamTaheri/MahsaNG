#!/usr/bin/env bash
# Validate MMKV's actual native cross-process tryLock/unlock on Android 35.
# Only debug-only DUMP-protected receivers are used. No profile contents read.
set -euo pipefail

package_id="${1:-com.MahsaNG.EMS.dev}"
owner="$package_id/com.v2ray.ang.qa.IndexLeaseOwnerReceiver"
contender="$package_id/com.v2ray.ang.qa.IndexLeaseContenderReceiver"
tag="MahsaIndexLeaseQA"
token="MMKVLOCK$(date +%s)$$"

on_error() {
    local status=$?
    if (( status != 0 )); then
        echo "Native cross-process MMKV contention failed (exit $status)" >&2
        # This tag logs only a generated token, roles and status; no user data.
        adb logcat -d -v raw -s "$tag:I" | tail -n 50 >&2 || true
    fi
}
trap on_error EXIT

wait_for() {
    local expected="$1"
    local count
    for ((count=0; count<55; count++)); do
        if adb logcat -d -v raw -s "$tag:I" 2>/dev/null |
            grep -F -- "$token $expected" >/dev/null; then
            return 0
        fi
        sleep 0.15
    done
    echo "Missing native lock event: $expected" >&2
    return 1
}

# Prime both app processes and MMKV handles before timing a real lock.
adb logcat -c
adb shell am broadcast -n "$owner" --es token "$token" --ez prime true
wait_for "OWNER READY"
adb shell am broadcast -n "$contender" --es token "$token" --ez prime true
wait_for "CONTENDER READY"

# Explicitly verify different Android processes, not two in-process lock objects.
owner_pid="$(adb shell pidof "$package_id:qa_lock_owner" | tr -d '\r[:space:]')"
contender_pid="$(adb shell pidof "$package_id:qa_lock_contender" | tr -d '\r[:space:]')"
if [[ -z "$owner_pid" || -z "$contender_pid" || "$owner_pid" == "$contender_pid" ]]; then
    echo "Missing two distinct Android QA receiver PIDs" >&2
    exit 1
fi

# Some Android shell builds wait for goAsync BroadcastReceiver.finish().
# Run the holder's adb command in the background to avoid serializing probes.
adb shell am broadcast -n "$owner" --es token "$token" --ei hold_ms 6500 >/dev/null &
owner_shell=$!
wait_for "OWNER LOCKED"

# This MUST be denied while the owner holds the real native MMKV file lock.
adb shell am broadcast -n "$contender" --es token "$token"
wait_for "CONTENDER DENIED"
wait_for "OWNER RELEASED"
wait "$owner_shell"

# After release, the same contender process MUST be able to acquire the lock.
adb shell am broadcast -n "$contender" --es token "$token"
wait_for "CONTENDER GRANTED"
echo "Android native MMKV cross-process contention passed: two PIDs, denial during lease, acquisition after release"
