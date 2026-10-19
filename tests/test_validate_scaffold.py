"""Unit tests for the hackathon scaffold's active CI check."""

import tempfile
import unittest
from pathlib import Path

from scripts.validate_scaffold import check_required_files, valid_pr_title


class ValidateScaffoldTests(unittest.TestCase):
    def test_accepted_pr_titles(self):
        titles = (
            "feat: add demo flow",
            "fix(api): handle not found",
            "docs: clarify setup",
            "ci(workflows)!: replace legacy job",
            "refactor(frontend/ui): extract components",
        )
        for title in titles:
            with self.subTest(title=title):
                self.assertTrue(valid_pr_title(title))

    def test_rejected_pr_titles(self):
        titles = (
            "WIP add demo flow",
            "Fix(api): handle not found",
            "update",
            "feat:",
            "feat: ",
            "feat(scope):",
            "feat(Has Spaces): add thing",
        )
        for title in titles:
            with self.subTest(title=title):
                self.assertFalse(valid_pr_title(title))

    def test_missing_files_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = check_required_files(root)
            self.assertIn("AGENTS.md", missing)
            self.assertIn("docs/ARCHITECTURE.md", missing)

    def test_all_required_files_can_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in check_required_files(root):
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text("placeholder", encoding="utf-8")
            self.assertEqual([], check_required_files(root))


if __name__ == "__main__":
    unittest.main()

