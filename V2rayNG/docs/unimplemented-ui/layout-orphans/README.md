# Archived protocol and utility screens awaiting backing Android source

The seventeen XML files here are **original layout sources**, preserved outside the
Android resource graph until their backing Activities, protocol implementations,
and option-list resources can be restored and reviewed.

The checked-in Android manifest does not register the named GFW utility
screens, and `ui/ServerActivity.kt` only selects the implemented VMESS,
Shadowsocks, SOCKS, HTTP, VLESS, MVLESS, Trojan, WireGuard, and Hysteria2
editors. In particular, the five archived protocol editors (DNSTT, GooseRelay,
MasterDNS, Psiphon, Skirk) are not routed to by `ServerActivity`, while
their original protocol-specific array definitions are not present. The
remaining seven GFW utility/legacy layouts also reference assets or labels
absent from the published repository.

Original XML files are preserved by name:

- `activity_server_dnstt.xml`
- `activity_server_gooserelay.xml`
- `activity_server_masterdns.xml`
- `activity_server_psiphon.xml`
- `activity_server_skirk.xml`
- `activity_gfw_update.xml`
- `activity_terms_service.xml`
- `activity_tunnel_config.xml`
- `activity_update.xml`
- `activity_warp_setting.xml`
- `activity_youtube_config.xml`
- `bottom_sheet_result.xml`
- `gfw_permit_layout.xml`
- `activity_donate_config.xml`
- `activity_gfw_tunnel_config.xml`
- `activity_github_config.xml`
- `activity_ip_scanner.xml`

`V2rayNG/pure-tests/test_unimplemented_editor_archive.py` fails CI if an
archived file is missing, if the layout is placed back into the active
resources without reimplementation, or if a compiled Java/Kotlin source starts
referring to one of these layouts (by R.layout or generated ViewBinding) without restoring the whole feature.

**This does not implement the missing protocols or validate their behavior.**
Restoration requires original/reviewed data model and Activity code, exact
protocol option mappings, complete resources, security review, and Android
device tests before moving files back under `src/main/res`. These archives
must not be treated as dummy working screens or a replacement for complete
source code.

`activity_gfw_psiphon_settings.xml` is intentionally **not** archived:
`GFW_psiphonSettings_Activity.java` still directly references it.
Its missing original Psiphon option arrays must be restored from documented
protocol choices before Android resource linking can succeed; do not invent
or silently replace its selector values.

The archived `activity_update.xml` declares `.feature.update.UpdateActivity`,
which is missing from the published source and manifest. Its former compiled
layout referenced missing animation, theme, drawable, and content resources.

The archived `activity_warp_setting.xml` depends on original WARP UI assets
and strings (including `warp_description`, `ic_internal_warp` and the button
styles), none present in the published source. Restore it only with the
corresponding reviewed and registered WARP settings Activity and resources.

The YouTube configuration layout references absent original help/feature
resources. The result bottom-sheet layout references absent specialized
background/drag-handle resources. The CI guard checks for code references
before allowing these UI resources to stay quarantined; if a real usage is
discovered, the entire backing screen must be restored instead.

`gfw_permit_layout.xml` is preserved because the published DNSTT permit enum
or list is absent. The compile guard now rejects both Java/Kotlin references
and active resource-XML includes to archived layouts, so any discovered
consumer requires restoring the real implementation rather than inventing
selector values.

The original television-only `activity_donate_config.xml` was present in
`res/layout-television` but no compiled or registered donation configuration
Activity could be located. It references unpublished TV donation action labels
and icons. Its original XML is preserved here verbatim; the archive guard
checks all `layout*` resource qualifiers to prevent compiling an unsupported
variant. Restore it with its working Activity and complete resources.

The three television-only layouts `activity_gfw_tunnel_config.xml`,
`activity_github_config.xml` and `activity_ip_scanner.xml` have no default
layout implementations in the published fork and reference strings/drawables
that were not included in its resources. They are preserved byte-for-byte
until their feature code and assets are available. The XML/source-reference
guard runs on all layout qualifiers and must succeed before this can be merged.
