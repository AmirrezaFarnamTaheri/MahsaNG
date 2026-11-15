"""Parsed GitHub Actions policy checks: ignore comments and YAML quoting."""
from pathlib import Path
import re
import unittest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "mahsa-safety.yml"

# GitHub Actions uses YAML 1.2 semantics: `on` is a key, not YAML 1.1 boolean.
class GithubActionsLoader(yaml.SafeLoader):
    pass

GithubActionsLoader.yaml_implicit_resolvers = {
    char: [(tag, regex) for tag, regex in resolvers
           if tag != 'tag:yaml.org,2002:bool']
    for char, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
yaml.add_implicit_resolver(
    'tag:yaml.org,2002:bool',
    re.compile(r'^(?:true|false|True|False|TRUE|FALSE)$'),
    list('tTfF'),
    Loader=GithubActionsLoader,
)

def actions_config(text: str) -> dict:
    return yaml.load(text, Loader=GithubActionsLoader)

class StackedFeaturePrCiTest(unittest.TestCase):
    def test_feature_base_branches_are_eligible_for_pr_checks(self):
        config = actions_config(WORKFLOW.read_text(encoding="utf-8"))
        pull_branches = config["on"]["pull_request"]["branches"]
        self.assertIn("master", pull_branches)
        self.assertIn("feat/**", pull_branches)
        self.assertIn("roadmap/**", pull_branches)
        self.assertIn("fix/**", pull_branches)

    def test_feature_pushes_do_not_duplicate_pr_workflows(self):
        config = actions_config(WORKFLOW.read_text(encoding="utf-8"))
        push_branches = config["on"]["push"]["branches"]
        self.assertNotIn("feat/**", push_branches)
        self.assertNotIn("integration/**", push_branches)
        self.assertIs(config["concurrency"]["cancel-in-progress"], True)

    def test_comments_and_quoted_branch_rules_cannot_fool_policy(self):
        sample = """
on:
  pull_request:
    branches: [master] # 'feat/**' must not count
  push:
    branches: ["feat/**"]
concurrency:
  cancel-in-progress: false # true is not a boolean
"""
        config = actions_config(sample)
        self.assertNotIn("feat/**", config["on"]["pull_request"]["branches"])
        self.assertIn("feat/**", config["on"]["push"]["branches"])
        self.assertIs(config["concurrency"]["cancel-in-progress"], False)

if __name__ == "__main__":
    unittest.main()
