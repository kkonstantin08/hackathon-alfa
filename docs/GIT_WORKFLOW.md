# Git and pull request convention

## Branches

`<type>/<issue-number>-<short-kebab-topic>` from current `main`.

Examples:

- `feat/42-auth-form`
- `fix/51-api-timeout`
- `docs/12-demo-guide`
- `ci/18-add-backend-tests`

Prefer one Issue and one PR per coherent task. Never commit directly to `main`. Rebase or merge the latest `main` into long-running branches after coordinating conflicts.

## Conventional Commits

Format: `<type>(<optional-scope>)!: <imperative summary>`.

Allowed types:

| Type | Use |
| --- | --- |
| `feat` | User-visible feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Behavior-preserving code cleanup |
| `test` | Add or repair tests |
| `chore` | Maintenance, dependency management |
| `ci` | CI/CD config |
| `build` | Build system, packaging |
| `perf` | Performance improvements |
| `style` | Formatting only |

Use `!` or a `BREAKING CHANGE:` commit footer for intentionally incompatible changes. Such changes still require consumer notification, contract updates and a migration plan.

Examples:

```text
feat(frontend): add onboarding view
fix(api): handle expired sessions
docs: describe local demo setup
ci: run backend tests in pull requests
feat(api)!: rename session response field
```

No vague `update`, `wip`, `fix stuff`, and no noisy AI co-author boilerplate unless your team specifically requests it.

## PR process

1. Agent claims the Issue, creates a branch, implements and tests.
2. Agent commits, pushes and opens a PR using `.github/PULL_REQUEST_TEMPLATE.md`; use a Conventional Commit style **PR title**, too (validated by CI; compatible with squash merge).
3. Request review from a human responsible for the changed area. At least one approval is required under normal rules; authors cannot approve their own PR.
4. GitHub Actions CI must pass. Ask for explicit human merge instruction, then merge only when authorized. Squash merge preferred for a clear `main` history.
5. If a PR modifies a shared interface, list affected people, notification link and compatibility plan.

## Emergency Merge

- Any of the five team participants with repository write access may initiate it on an explicit human command (including a human using GitHub UI directly).
- A reviewer can be bypassed if unavailable; **required CI checks remain non-bypassable**.
- Record in the PR: `Emergency Merge: <reason>; authorized by <human>; follow-up Issue #<id>`.
- Do not force-push `main` or skip required checks. If checks are red, fix or revert first.
- Review skipped in an emergency should be performed after merge when practical.

`GITHUB_SETUP.md` explains how to configure *two* separate rulesets to implement this review-only bypass safely.

