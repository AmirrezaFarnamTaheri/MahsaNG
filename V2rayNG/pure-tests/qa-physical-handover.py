#!/usr/bin/env python3
"""Operator-attested Wi-Fi/cellular VPN handover check for a physical Android device.

This opt-in tool does not alter Android network settings, read profile/config
contents, inspect logcat, or claim to measure the routed tunnel packet path.
It checks only package installation and daemon process-ID continuity via ADB.
"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

PACKAGE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+")
SERIAL_RE = re.compile(r"[A-Za-z0-9._:-]{1,128}")
STAGES = (
    ("wifi", "Enable Wi-Fi and connect the chosen VPN mode. Keep mobile data available."),
    ("cellular", "Turn Wi-Fi OFF, leave mobile data ON, and keep the VPN connected."),
    ("wifi-restored", "Turn Wi-Fi ON again and keep the same VPN session connected."),
)


class QaFailure(Exception):
    """A prerequisite or operator-attestation step could not be verified."""


def adb(serial, *arguments):
    try:
        result = subprocess.run(
            ["adb", "-s", serial, *arguments],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as error:
        raise QaFailure("ADB unavailable or timed out") from error
    if result.returncode != 0:
        # Deliberately do not echo device-side errors, endpoints, or config data.
        raise QaFailure("ADB prerequisite or process query failed")
    return result.stdout.strip()


def processes(serial, package, mode):
    required = [f"{package}:RunSoLibV2RayDaemon"]
    if mode == "psiphon-via-xray":
        required.append(f"{package}:PsiphonDaemon")
    observed = []
    for process in required:
        output = adb(serial, "shell", "pidof", process)
        pids = output.split()
        if len(pids) != 1 or not pids[0].isdigit():
            raise QaFailure("Expected exactly one live VPN daemon process")
        observed.append(pids[0])
    if len(set(observed)) != len(observed):
        raise QaFailure("Expected distinct Xray and Psiphon daemon processes")
    return tuple(observed)


def attest(instruction, confirmation):
    print(instruction, flush=True)
    try:
        answer = input(f"Type {confirmation} to attest this step (anything else aborts): ")
    except EOFError as error:
        raise QaFailure("Operator confirmation unavailable") from error
    if answer.strip() != confirmation:
        raise QaFailure("Operator did not confirm the required check")


def write_report(path, record):
    if path is None:
        return
    try:
        # No raw ADB output, host/device serial, SSID, endpoint, or profile data.
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(record, output, indent=2, sort_keys=True)
            output.write("\n")
    except OSError as error:
        raise QaFailure("Unable to write sanitized QA report") from error


def run(args):
    if not SERIAL_RE.fullmatch(args.serial):
        raise QaFailure("Invalid explicit Android device serial")
    if not PACKAGE_RE.fullmatch(args.package):
        raise QaFailure("Invalid Android package identifier")

    record = {
        "schema_version": 1,
        "mode": args.mode,
        "result": "INCOMPLETE",
        "network_transport_device_verified": False,
        "tunnel_packet_path_device_verified": False,
        "stages": [],
    }
    try:
        if adb(args.serial, "get-state") != "device":
            raise QaFailure("Selected Android device is not online")
        if not adb(args.serial, "shell", "pm", "path", args.package).startswith("package:"):
            raise QaFailure("Selected Android application is not installed")

        baseline = None
        for phase, instruction in STAGES:
            attest(f"[{phase}] {instruction}", "READY")
            before = processes(args.serial, args.package, args.mode)
            if baseline is None:
                baseline = before
            elif before != baseline:
                raise QaFailure("VPN process changed during handover")

            attest(
                "Open a separate, VPN-routed browser app, load a fresh page, "
                "and check that it works without disabling the VPN. "
                "Do not include the URL or any credentials in this report.",
                "PASS",
            )
            after = processes(args.serial, args.package, args.mode)
            if after != baseline:
                raise QaFailure("VPN process changed during handover")
            record["stages"].append({
                "phase": phase,
                "pid_stable": True,
                "browser_confirmed": True,
            })

        record["result"] = "OPERATOR_ATTESTED"
        write_report(args.report, record)
        print(
            "Operator-attested handover passed: daemon PIDs stayed stable. "
            "Neither actual transport changes nor VPN packet routing were "
            "automatically verified.",
            flush=True,
        )
        return 0
    except QaFailure:
        # Preserve only sanitized, partial evidence; never claim success.
        write_report(args.report, record)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="Explicit ADB device serial")
    parser.add_argument("--mode", required=True, choices=("xray-vpn", "psiphon-via-xray"))
    parser.add_argument("--package", default="com.MahsaNG.EMS.dev", help="Installed app ID")
    parser.add_argument("--report", type=Path, help="Optional sanitized JSON output path")
    args = parser.parse_args()
    try:
        return run(args)
    except (QaFailure, KeyboardInterrupt) as error:
        print(f"QA INCOMPLETE: {error or 'Interrupted by operator'}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
