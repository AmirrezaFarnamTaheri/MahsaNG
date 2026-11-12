# Release signing and device QA

The Android `release` build type **must not** use the standard Android debug
keystore. Release APKs without an approved production signing configuration
are intentionally unsigned and **not distributable as app updates**.
Inject release signing through a reviewed, private CI/signing setup before
any production publishing step; never commit signing keys or credentials.

The `MahsaNG-devDebug-QA-<commit>` Actions artifact is uploaded **only after**
source/native compatibility, APK assembly, Android module unit tests and
Android 35 emulator smoke pass. This artifact is for isolated device QA, uses
debug signing, is not a production build, and expires after seven days.

QA must still exercise actual VPN lifecycle, Xray/Psiphon start, stop and
reconnect, DNS/IPv6, network handoff, configuration/profile redaction, and
leak protection on physical devices. Passing emulator startup or APK assembly
alone does not satisfy these gates.

To protect VPN credentials, app backup is disabled and both legacy and Android
12+ cloud/device-transfer extraction rules exclude the app data tree. This
intentionally sacrifices automatic device-migration recovery. Existing backups
cannot be retroactively removed by changing the manifest.
