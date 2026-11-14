"""Ensure GitHub Actions validates stacked feature PRs without duplicate push runs."""
from pathlib import Path
import unittest

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "mahsa-safety.yml"

class StackedFeaturePrCiTest(unittest.TestCase):
    def test_feature_base_branches_are_eligible_for_pr_checks(self):
        contents = WORKFLOW.read_text(encoding="utf-8")
        pr_filter = contents.split("  pull_request:", 1)[1].split("  push:", 1)[0]
        self.assertIn("master", pr_filter)
        self.assertIn("'feat/**'", pr_filter)
        self.assertIn("'roadmap/**'", pr_filter)

    def test_feature_pushes_do_not_duplicate_pr_workflows(self):
        contents = WORKFLOW.read_text(encoding="utf-8")
        push_filter = contents.split("  push:", 1)[1].split("  workflow_dispatch:", 1)[0]
        self.assertNotIn("'feat/**'", push_filter)
        self.assertNotIn("'integration/**'", push_filter)
        self.assertIn("cancel-in-progress: true", contents)

if __name__ == "__main__":
    unittest.main()
