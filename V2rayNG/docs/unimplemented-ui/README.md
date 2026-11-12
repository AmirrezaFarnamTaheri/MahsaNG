# Unimplemented MASQUE/WARP editor layouts — preserved for source restoration

These archived XML layouts were checked into the public MahsaNG tree, but their declared
Activity classes (`.feature.masqueGenerator.AddMasqueActivity`,
`.feature.warpGenerator.AddWarpActivity`, `.feature.dnsScanner.DnsScannerActivity`, and
`.feature.proxy.TelegramProxyActivity`) **are absent**, as are their companion
styles, drawables, strings, and related feature implementation.

They are preserved **byte-for-byte** in this directory, outside Android's
`src/main/res` folder. The archived resources are not compiled or presented
to users, so they cannot pretend to provide a working key-generation feature.

The original upstream source added the app layouts in
[GFW-knocker/MahsaNG commit b049f70](https://github.com/GFW-knocker/MahsaNG/commit/b049f70296b95ee8d4e9e1af7f6f0e368aa98902)
without the referenced supporting resources.

### Restore only when the feature is real
1. Obtain/author reviewed Activities for the corresponding missing features,
   including MASQUE/WARP generation, DNS scanning, and Telegram proxy configuration, with secure
   key handling and protocol integration, with verified licensing and source.
2. Restore all portrait/television layout files that belong to the restored Activities, plus referenced
   string, drawable and color resources with accessibility and Persian RTL QA.
3. Register the activities and test both the generated profile and actual
   tunneled connection in an instrumented Android device build.
4. Remove the archive guard after the replacement feature and resources
   have been verified.

This quarantine is not a substitute for implementation and does not disable
any working Activity in the public source because neither Activity exists.

The unused DNS scanner layout was the first resource-linking failure after
archiving the MASQUE/WARP layouts in CI run
[42919339923](https://github.com/AmirrezaFarnamTaheri/MahsaNG/actions/runs/42919339923).
It references `ic_check`, `ping_ok`, `dns_scan_stat_elapsed`,
`layout_error_state` and further resources that do not exist in the repository.
