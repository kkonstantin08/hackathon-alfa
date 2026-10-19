#!/usr/bin/env python3
"""Check invariant repository scaffold files and Conventional Commit PR titles."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_FILES = (
    ".gitignore",
    "AGENTS.md",
    "GITHUB_SETUP.md",
    "README.md",
    "ROLE.example.md",
    ".github/ISSUE_TEMPLATE/feature.yml",
    ".github/ISSUE_TEMPLATE/bug.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/ci.yml",
    "config/codex.config.toml.example",
    "docs/AGENT_SETUP.md",
    "docs/AGENT_WORKFLOW.md",
    "docs/ARCHITECTURE.md",
    "docs/CONTRACTS.md",
    "docs/DECISIONS.md",
    "docs/DEFINITION_OF_DONE.md",
    "docs/GIT_WORKFLOW.md",
    "docs/PROPOSAL_TEMPLATE.md",
    "docs/REQUIREMENTS.md",
    "docs/ROLES.md",
    "docs/STATUS.md",
    "scripts/validate_scaffold.py",
    "templates/deploy.github-actions.example.yml",
    "tests/test_validate_scaffold.py",
)

PR_TITLE_PATTERN = re.compile(
    r"(?:feat|fix|docs|refactor|test|chore|ci|build|perf|style)"
    r"(?:\([a-z0-9._/-]+\))?!?: \S.*",
)


def check_required_files(root: Path) -> list[str]:
    """Return missing paths, suitable for readable CI errors."""
    return [relative for relative in REQUIRED_FILES if not (root / relative).is_file()]


def valid_pr_title(title: str) -> bool:
    """Enforce same header convention for PRs and squash-merge commits."""
    return PR_TITLE_PATTERN.fullmatch(title) is not None


def tracked_private_files(root: Path) -> list[str]:
    """Only report *tracked* files; local ROLE.local.md must be allowed to exist."""
    if not (root / ".git").exists():
        return []
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--", "ROLE.local.md", "CLAUDE.md", "CLAUDE.local.md"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--pr-title", default="", help="Title, checked when nonempty")
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []

    errors.extend(f"Missing required file: {name}" for name in check_required_files(root))
    errors.extend(f"Do not commit personal/legacy agent file: {name}" for name in tracked_private_files(root))
    if args.pr_title and not valid_pr_title(args.pr_title):
        errors.append(f"Invalid PR title (see docs/GIT_WORKFLOW.md): {args.pr_title!r}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Foundation validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

