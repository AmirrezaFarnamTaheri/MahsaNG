#!/usr/bin/env bash
# Stop-envelope/ack simulation in TWO Android QA processes. NO live VPN/JNI.
set -euo pipefail

package_id="${1:-com.MahsaNG.EMS.dev}"
owner="$package_id/com.v2ray.ang.qa.VpnSessionQaOwnerReceiver"
contender="$package_id/com.v2ray.ang.qa.VpnSessionQaContenderReceiver"
tag="MahsaSessionFenceQA"
token="STOPCMDQA$(date +%s)$$"
first="$(python3 -c 'import uuid; print(uuid.uuid4())')"
second="$(python3 -c 'import uuid; print(uuid.uuid4())')"
current_wire="v1|$first|1"
wrong_wire="v1|$second|1"

on_error() {
  local code=$?
  if ((code != 0)); then
    echo "Two-process Stop command QA failed (status $code)" >&2
    # Receiver logs status only, never credentials or raw session IDs.
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
  echo "Missing expected Stop command QA status: $expected" >&2
  return 1
}

send_owner() {
  adb shell am broadcast -n "$owner" --es token "$token" "$@" >/dev/null
}
send_contender() {
  adb shell am broadcast -n "$contender" --es token "$token" "$@" >/dev/null
}

# Deliberate reset of the disposable debug-QA record ONLY. Production
# migration must never silently initialize missing session ownership state.
adb logcat -c
send_owner --es op SEED
wait_for "OWNER SEED ACCEPTED"
send_owner --es op BEGIN --es id "$first" --es mode PSIPHON_VIA_XRAY
wait_for "OWNER BEGIN ACCEPTED"
send_owner --es op ATTACH --es id "$first" --el gen 1 --es role XRAY
wait_for "OWNER ATTACH ACCEPTED"
send_contender --es op ATTACH --es id "$first" --el gen 1 --es role PSIPHON
wait_for "CONTENDER ATTACH ACCEPTED"
owner_pid="$(adb shell pidof "$package_id:qa_lock_owner" | tr -d '\r[:space:]')"
contender_pid="$(adb shell pidof "$package_id:qa_lock_contender" | tr -d '\r[:space:]')"
if [[ -z "$owner_pid" || -z "$contender_pid" || "$owner_pid" == "$contender_pid" ]]; then
  echo "Expected two distinct Android QA processes for Stop delivery" >&2
  exit 1
fi

# A stale/wrong-ID controller command cannot transition the current session.
send_owner --es op CMD_REQUEST --es wire "$wrong_wire"
wait_for "OWNER CMD_REQUEST REJECTED"
send_owner --es op CMD_REQUEST --es wire "$current_wire"
wait_for "OWNER CMD_REQUEST ACCEPTED"

# Each separate process verifies the persisted STOPPING generation before
# it would be allowed to initiate native shutdown.
send_owner --es op CMD_CHECK --es wire "$current_wire" --es role XRAY
wait_for "OWNER CMD_CHECK ACCEPTED"
send_contender --es op CMD_CHECK --es wire "$current_wire" --es role PSIPHON
wait_for "CONTENDER CMD_CHECK ACCEPTED"

# False completion cannot release either owner or permit a replacement.
send_contender --es op CMD_SIM_ACK --es wire "$current_wire" --es role PSIPHON --ez complete false
wait_for "CONTENDER CMD_SIM_ACK REJECTED"
send_contender --es op BEGIN --es id "$second" --es mode XRAY_VPN
wait_for "CONTENDER BEGIN REJECTED"
send_owner --es op CHECK --el gen 1 --es phase STOPPING
wait_for "OWNER CHECK STOPPING PASS"

# First simulated completion cannot free the other process.
send_owner --es op CMD_SIM_ACK --es wire "$current_wire" --es role XRAY --ez complete true
wait_for "OWNER CMD_SIM_ACK ACCEPTED"
send_contender --es op CMD_ROLE_LEFT --es wire "$current_wire" --es role PSIPHON
wait_for "CONTENDER CMD_ROLE_LEFT ACCEPTED"
send_owner --es op BEGIN_NEXT --es id "$second" --es mode XRAY_VPN
wait_for "OWNER BEGIN_NEXT REJECTED"

# Both simulated completions permit a successor generation. Old commands
# and old acknowledgements remain rejected after generation changes.
send_contender --es op CMD_SIM_ACK --es wire "$current_wire" --es role PSIPHON --ez complete true
wait_for "CONTENDER CMD_SIM_ACK ACCEPTED"
send_owner --es op BEGIN_NEXT --es id "$second" --es mode XRAY_VPN
wait_for "OWNER BEGIN_NEXT ACCEPTED"
send_owner --es op CMD_CHECK --es wire "$current_wire" --es role XRAY
wait_for "OWNER CMD_CHECK REJECTED"
send_contender --es op CMD_REQUEST --es wire "$current_wire"
wait_for "CONTENDER CMD_REQUEST REJECTED"
send_owner --es op CMD_SIM_ACK --es wire "$current_wire" --es role XRAY --ez complete true
wait_for "OWNER CMD_SIM_ACK REJECTED"
send_contender --es op CHECK --el gen 2 --es phase STARTING
wait_for "CONTENDER CHECK STARTING PASS"

echo "Android Stop command QA passed: two processes, stale request rejection, role fencing and simulated ack"
