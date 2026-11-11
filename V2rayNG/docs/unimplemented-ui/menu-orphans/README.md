# Archived navigation/UI menus

The original `menu_drawer_original.xml` includes roughly two dozen entries.
The current `MainActivity.onNavigationItemSelected` handles only four routes:
subscriptions, settings, user assets, and logcat. The compiled menu was
replaced with those four actions and standard Android icons so users cannot
select controls that do nothing or route to unpublished features.

`menu_telegram_proxy.xml` and `menu_warp_setting.xml` are also preserved
byte-for-byte because their corresponding screens and resource definitions
are absent from the public repository. Do not re-enable an item simply to
satisfy resource linking. Restore each complete feature and tests first.

`V2rayNG/pure-tests/test_navigation_drawer_contract.py` protects both the
working destinations and the source archive. The mobile layouts for main and
logcat remain active and become TV fallbacks until feature-complete TV
variants are provided.
