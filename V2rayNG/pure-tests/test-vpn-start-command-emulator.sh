#!/usr/bin/env bash
# Debug-only QA: session-scoped Start reservation in two Android processes.
# Does NOT call JNI, establish a VPN, or claim native tunnel readiness.
set -euo pipefail

package_id="${1:-com.MahsaNG.EMS.dev}"
owner="$package_id/com.v2ray.ang.qa.VpnSessionQaOwnerReceiver"
contender="$package_id/com.v2ray.ang.qa.VpnSessionQaContenderReceiver"
tag="MahsaSessionFenceQA"
qa_wait_attempts="${QA_WAIT_ATTEMPTS:-80}"
qa_wait_delay="${QA_WAIT_DELAY:-0.15}"
base="STARTQA$(date +%s)${BASHPID}"
step=0
first="$(python3 -c 'import uuid; print(uuid.uuid4())')"
second="$(python3 -c 'import uuid; print(uuid.uuid4())')"
xray="v1.$first.1.PSIPHON_VIA_XRAY.XRAY"
psiphon="v1.$first.1.PSIPHON_VIA_XRAY.PSIPHON"
wrong_id="v1.$second.1.PSIPHON_VIA_XRAY.XRAY"
wrong_generation="v1.$first.2.PSIPHON_VIA_XRAY.XRAY"
old_generation="v1.$first.1.XRAY_VPN.XRAY"
new_generation="v1.$first.2.XRAY_VPN.XRAY"
stop_wire="v1.$first.1"

report_error() {
  local exit_status=$?
  if ((exit_status != 0)); then
    echo "Two-process Start QA failed (exit ${exit_status})" >&2
    # Only the dedicated status-only QA tag is read, not app logs or profiles.
    adb logcat -d -v raw -s "$tag:I" | tail -n 50 >&2 || true
  fi
}
trap report_error EXIT

wait_for() {
  local token="$1" expected="$2" attempt
  for ((attempt=0;attempt<qa_wait_attempts;attempt++)); do
    if adb logcat -d -v raw -s "$tag:I" 2>/dev/null |
      grep -F -- "$token $expected" >/dev/null; then
      return 0
    fi
    sleep "$qa_wait_delay"
  done
  echo "Missing Start QA status: $expected" >&2
  return 1
}

# Each invocation uses a new valid token. An old log line can never satisfy
# an assertion for a later action, even if its operation/result match.
send_expect() {
  local receiver="$1" actor="$2" expected="$3"
  shift 3
  step=$((step+1))
  local token="${base}N${step}"
  adb shell am broadcast -n "$receiver" --es token "$token" "$@" >/dev/null
  wait_for "$token" "$actor $expected"
}

adb logcat -c
send_expect "$owner" OWNER "SEED ACCEPTED" --es op SEED
send_expect "$owner" OWNER "BEGIN ACCEPTED" --es op BEGIN --es id "$first" --es mode PSIPHON_VIA_XRAY
owner_pid="$(adb shell pidof "$package_id:qa_lock_owner" | tr -d '\r[:space:]')"
contender_pid="$(adb shell pidof "$package_id:qa_lock_contender" 2>/dev/null | tr -d '\r[:space:]' || true)"
# Contender process is lazy: an initial rejected Start command must start it.
send_expect "$contender" CONTENDER "START_RESERVE REJECTED" --es op START_RESERVE --es wire "$wrong_id"
contender_pid="$(adb shell pidof "$package_id:qa_lock_contender" | tr -d '\r[:space:]')"
if [[ -z "$owner_pid" || -z "$contender_pid" || "$owner_pid" == "$contender_pid" ]]; then
  echo "Expected distinct Android QA processes" >&2
  exit 1
fi

send_expect "$owner" OWNER "START_RESERVE REJECTED" --es op START_RESERVE --es wire "$wrong_generation"
send_expect "$contender" CONTENDER "START_RESERVE REJECTED" --es op START_RESERVE --es wire "invalid-start"
send_expect "$owner" OWNER "START_RESERVE ACCEPTED" --es op START_RESERVE --es wire "$xray"
send_expect "$contender" CONTENDER "START_RESERVE REJECTED" --es op START_RESERVE --es wire "$xray"
send_expect "$contender" CONTENDER "START_CHECK ACCEPTED" --es op START_CHECK --es wire "$xray"
send_expect "$contender" CONTENDER "START_RESERVE ACCEPTED" --es op START_RESERVE --es wire "$psiphon"
send_expect "$owner" OWNER "START_CHECK ACCEPTED" --es op START_CHECK --es wire "$psiphon"
send_expect "$owner" OWNER "CHECK ACTIVE PASS" --es op CHECK --el gen 1 --es phase ACTIVE

# Persist STOPPING before receiving a late Start command. The old lease is
# still occupied, including after one participant simulates a stopped worker.
send_expect "$owner" OWNER "CMD_REQUEST ACCEPTED" --es op CMD_REQUEST --es wire "$stop_wire"
send_expect "$contender" CONTENDER "START_RESERVE REJECTED" --es op START_RESERVE --es wire "$psiphon"
send_expect "$owner" OWNER "START_CHECK REJECTED" --es op START_CHECK --es wire "$xray"
send_expect "$owner" OWNER "CMD_SIM_ACK ACCEPTED" --es op CMD_SIM_ACK --es wire "$stop_wire" --es role XRAY --ez complete true
send_expect "$contender" CONTENDER "BEGIN_NEXT REJECTED" --es op BEGIN_NEXT --es id "$first" --es mode XRAY_VPN
send_expect "$contender" CONTENDER "CMD_SIM_ACK ACCEPTED" --es op CMD_SIM_ACK --es wire "$stop_wire" --es role PSIPHON --ez complete true

# Reuse the opaque ID deliberately to verify generation (ABA) fencing.
send_expect "$owner" OWNER "BEGIN_NEXT ACCEPTED" --es op BEGIN_NEXT --es id "$first" --es mode XRAY_VPN
send_expect "$contender" CONTENDER "START_RESERVE REJECTED" --es op START_RESERVE --es wire "$old_generation"
send_expect "$contender" CONTENDER "START_RESERVE ACCEPTED" --es op START_RESERVE --es wire "$new_generation"
send_expect "$owner" OWNER "CHECK ACTIVE PASS" --es op CHECK --el gen 2 --es phase ACTIVE

# Native start and JNI readiness were never invoked; this is a policy-only QA.
echo "Android Start command QA passed: two Android processes, stale/duplicate/ABA rejection, STOPPING exclusion"
