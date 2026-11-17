#!/usr/bin/env bash
# Real two-process MMKV state transitions on Android 35, NOT a live VPN tunnel.
# Both probes are debug-only and Android DUMP-permission-restricted.
set -euo pipefail

package_id="${1:-com.MahsaNG.EMS.dev}"
owner="$package_id/com.v2ray.ang.qa.VpnSessionQaOwnerReceiver"
contender="$package_id/com.v2ray.ang.qa.VpnSessionQaContenderReceiver"
tag="MahsaSessionFenceQA"
token="SESSIONQA$(date +%s)$$"
first="$(python3 -c 'import uuid; print(uuid.uuid4())')"
second="$(python3 -c 'import uuid; print(uuid.uuid4())')"

on_error() {
  local code=$?
  if ((code != 0)); then
    echo "Two-process session fencing QA failed (exit $code)" >&2
    # Only role/event/boolean result and a generated correlation tag are logged.
    adb logcat -d -v raw -s "$tag:I" | tail -n 65 >&2 || true
  fi
}
trap on_error EXIT

wait_for() {
  local expected="$1"
  local attempt
  for ((attempt=0; attempt<80; attempt++)); do
    if adb logcat -d -v raw -s "$tag:I" 2>/dev/null |
      grep -F -- "$token $expected" >/dev/null; then
      return 0
    fi
    sleep 0.15
  done
  echo "Missing expected native session event: $expected" >&2
  return 1
}

send_owner() {
  adb shell am broadcast -n "$owner" --es token "$token" "$@" >/dev/null
}

send_contender() {
  adb shell am broadcast -n "$contender" --es token "$token" "$@" >/dev/null
}

adb logcat -c

# Initialization is a destructive step on a dedicated DEBUG QA-only
# record; production transactions must never bootstrap a missing record.
send_owner --es op SEED
wait_for "OWNER SEED ACCEPTED"

send_owner --es op BEGIN --es id "$first" --es mode PSIPHON_VIA_XRAY
wait_for "OWNER BEGIN ACCEPTED"
send_owner --es op ATTACH --es id "$first" --el gen 1 --es role XRAY
wait_for "OWNER ATTACH ACCEPTED"
send_contender --es op ATTACH --es id "$first" --el gen 1 --es role PSIPHON
wait_for "CONTENDER ATTACH ACCEPTED"

# Verify the two processes have different Android process IDs.
owner_pid="$(adb shell pidof "$package_id:qa_lock_owner" | tr -d '\r[:space:]')"
contender_pid="$(adb shell pidof "$package_id:qa_lock_contender" | tr -d '\r[:space:]')"
if [[ -z "$owner_pid" || -z "$contender_pid" || "$owner_pid" == "$contender_pid" ]]; then
  echo "Missing distinct Android process IDs for session participants" >&2
  exit 1
fi
send_contender --es op CHECK --el gen 1 --es phase ACTIVE
wait_for "CONTENDER CHECK PASS"
send_contender --es op STOP --es id "$second" --el gen 1
wait_for "CONTENDER STOP REJECTED"

send_owner --es op STOP --es id "$first" --el gen 1
wait_for "OWNER STOP ACCEPTED"
send_contender --es op RELEASE --es id "$first" --el gen 1 --es role PSIPHON
wait_for "CONTENDER RELEASE ACCEPTED"
send_owner --es op CHECK --el gen 1 --es phase STOPPING
wait_for "OWNER CHECK PASS"
send_contender --es op BEGIN --es id "$second" --es mode XRAY_VPN
wait_for "CONTENDER BEGIN REJECTED"
send_owner --es op RELEASE --es id "$first" --el gen 1 --es role XRAY
wait_for "OWNER RELEASE ACCEPTED"

# Generation-1 stop must not affect generation 2.
send_contender --es op BEGIN --es id "$second" --es mode XRAY_VPN
wait_for "CONTENDER BEGIN ACCEPTED"
send_owner --es op STOP --es id "$first" --el gen 1
wait_for "OWNER STOP REJECTED"
send_contender --es op CHECK --el gen 2 --es phase STARTING
wait_for "CONTENDER CHECK PASS"

# Real native lease exclusion from a different Android process.
send_owner --es op HOLD >/dev/null &
owner_shell=$!
wait_for "OWNER HOLD LOCKED"
send_contender --es op PROBE
wait_for "CONTENDER PROBE UNAVAILABLE"
wait_for "OWNER HOLD RELEASED"
wait "$owner_shell"
send_contender --es op PROBE
wait_for "CONTENDER PROBE ACCEPTED"

# A malformed QA record must never become an implicit empty session.
send_owner --es op CORRUPT
wait_for "OWNER CORRUPT ACCEPTED"
send_contender --es op PROBE
wait_for "CONTENDER PROBE UNAVAILABLE"

echo "Android session fencing QA passed: two processes, native exclusion, stale token and corruption refusal"
