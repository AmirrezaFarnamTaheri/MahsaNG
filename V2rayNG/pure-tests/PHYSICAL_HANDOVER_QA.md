# Physical Wi-Fi/cellular VPN handover QA

This is an **opt-in, operator-attested physical-device test**, not an
automated connectivity proof or a CI emulator test. No private profile, SSID,
endpoint, device serial, raw ADB output or logcat is written to its report.

## Requirements

- A **non-production Android test handset** with USB debugging enabled.
- Working Wi-Fi and mobile data, with enough data allowance for the test.
- A trusted MahsaNG APK installed, Android VPN authorization granted, and a
  test profile known to connect on both networks.
- A separate browser that **is routed through the VPN**: check per-app bypass
  settings before testing. Choose a harmless, independently accessible HTTPS
  test page and make a fresh request at each stage (not a cached page).
- ADB and Python 3 installed on your computer. Explicitly choose the handset
  serial shown by `adb devices`; never use an implicit/default device.

## Run the two modes separately

Start the intended VPN mode from MahsaNG's UI and verify it initially connects.
The script does **not** start/stop the VPN, toggle Wi-Fi/mobile data, change app
settings or request any network permissions.

For ordinary Xray VPN:

```sh
python3 V2rayNG/pure-tests/qa-physical-handover.py \
  --serial YOUR_ADB_SERIAL --mode xray-vpn \
  --report ./xray-physical-handover.json
```

For the existing, separately authorized experimental Psiphon-via-Xray mode:

```sh
python3 V2rayNG/pure-tests/qa-physical-handover.py \
  --serial YOUR_ADB_SERIAL --mode psiphon-via-xray \
  --report ./psiphon-physical-handover.json
```

If testing a non-dev build, supply its **actual installed** package name with
`--package` (the default is `com.MahsaNG.EMS.dev`).

At each stage the script first asks for `READY` after you make the requested
manual change, then for `PASS` **only after** an independent browser has loaded
a fresh page while the same VPN remains enabled. Any other answer aborts, as
do a missing daemon, an ADB failure, or a changed process ID. In chained
mode **both** Xray and Psiphon must stay in distinct processes throughout.

Stages: **Wi-Fi baseline → cellular with Wi-Fi off → restored Wi-Fi**.
The actual transport selection is an **operator claim**, not inferred from ADB.

## What the report means

`OPERATOR_ATTESTED` means that the operator confirmed fresh browser requests at
all three stages and ADB observed the required daemon process IDs remain
stable. It does **not** mean the tool measured packet forwarding, proven
network transport handover, checked DNS/IP leaks, validated a kill switch,
proved Android VPN ownership or established zero dropped packets.
A true release claim requires additional instrumented testing with a known
VPN-routed test client, direct underlay observation and device traces reviewed
for credentials before sharing.

A non-zero exit produces `INCOMPLETE` evidence (if `--report` is supplied);
do not count it as success. Reports contain only the test mode and coarse
boolean stage results. Keep the report locally, review it before attaching
to an issue, and do not attach traffic captures, personal browser history,
proxy configuration, or full `dumpsys` / logcat output.

## How the logic is tested in CI

```sh
python3 -m unittest discover -s V2rayNG/pure-tests -p 'test_physical_handover_qa.py'
```

These automated tests run the **actual Python runner** against a fake ADB. They
check fail-closed behavior, explicit device selection, both daemon processes,
process replacement, operator refusal and redaction. No CI emulator or fake ADB
can substitute for the physical operator workflow.

Use separate QA runs for VPN revoke, app force-stop, process death and
cross-process ownership handoff. This script deliberately **does not** issue
destructive stop/start commands or attempt to prove those behaviors.
