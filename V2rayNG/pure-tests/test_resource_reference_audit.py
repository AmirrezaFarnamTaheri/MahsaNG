"""Regression tests for the pre-Android-link missing-resource inventory."""
import tempfile
from pathlib import Path
import unittest
from resource_reference_audit import audit_resources


class ResourceReferenceAuditTests(unittest.TestCase):
    def test_reports_missing_references_across_qualified_layouts(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = Path(tmp)
            (res / "values").mkdir()
            (res / "layout-television").mkdir()
            (res / "drawable").mkdir()
            (res / "values/strings.xml").write_text(
                '<resources><string name="known">Known</string>'
                '<string-array name="known_array"><item>Auto</item></string-array></resources>'
            )
            (res / "drawable/icon.xml").write_text('<vector/>')
            (res / "layout-television/main.xml").write_text(
                '<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android" '
                'android:contentDescription="@string/known" '
                'android:background="@drawable/icon">'
                '<TextView android:text="@string/absent"/>'
                '<Spinner android:entries="@array/missing"/>'
                '<ImageView android:src="@android:drawable/ic_menu_help"/>'
                '</LinearLayout>'
            )
            missing = audit_resources(res)
            self.assertEqual({"array/missing", "string/absent"}, set(missing))
            self.assertIn("layout-television/main.xml", missing["array/missing"])

    def test_does_not_count_library_styles_and_local_new_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = Path(tmp)
            (res / "layout").mkdir()
            (res / "layout/main.xml").write_text(
                '<View xmlns:android="http://schemas.android.com/apk/res/android" '
                'android:id="@+id/new_local_id" style="@style/TextAppearance.AppCompat" />'
            )
            self.assertEqual({}, audit_resources(res))


if __name__ == "__main__":
    unittest.main()
