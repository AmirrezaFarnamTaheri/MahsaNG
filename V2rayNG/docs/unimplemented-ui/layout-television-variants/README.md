# Television layout overrides awaiting complete resource sets

The original `activity_main.xml` and `activity_logcat.xml` television
overrides are preserved here. They referenced dozens of missing TV-specific
assets and strings. Their underlying Activities are registered and have
complete default layout files, so the app temporarily uses the default
layout on TV rather than dropping an Activity or inventing controls.

`V2rayNG/pure-tests/test_television_layout_fallback.py` asserts that the
default layouts remain available and the archived TV variants are not
included in Android resource linking. Restore each TV layout only after
its referenced resources and behavior are reviewed and device-tested.
