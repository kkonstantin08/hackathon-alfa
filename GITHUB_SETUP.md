# GitHub repository setup (manual actions by a human)

This repository is intended to be **public on GitHub Free**. The ZIP cannot grant collaborators access, create branch rulesets, configure Actions permissions, provision external hosting, or install workstation plugins. An administrator must perform these steps once in the GitHub web interface.

## 1. Access, branches, PRs

1. Create one public repository; use `main` as default branch. Add all five human participants as collaborators with **Write** or an appropriate organization role. Verify they can open and review PRs.
2. In repository Settings, enable **Issues** and **Actions**. Prefer **Squash merge** (Conventional Commit-style PR title becomes squash commit title). Disable force pushes and branch deletions for protected `main`.
3. In Settings → Rules → Rulesets, use **two separate active branch rulesets** targeting `main`. Rulesets can be configured on public GitHub Free repositories; actual UI labels may vary.

### Ruleset A — PR and review gate (controlled bypass)

- Name: `main-review-gate`; enforcement: **Active**; target: default branch / `main`.
- Require a pull request before merging; require **1 approving review**.
- Set bypass for the **Write/Maintain role** (or the team's specific non-secret GitHub organization team as appropriate), with bypass mode **For pull requests only**. Verify *all five* humans have the intended bypass capability, not anonymous users or bots.
- Do **not** use a silent `Exempt` mode. No habitual bypass: it is only for documented Emergency Merge with an explicit human command.

**Limitation:** GitHub permissions cannot enforce that bypass is used only for genuine emergencies or after a verbal human command. This is a team rule backed by PR history and accountability.

### Ruleset B — non-bypassable CI gate

- Name: `main-ci-gate`; enforcement: **Active**; target: `main`.
- Require status checks before merge. Select required job **`foundation`** from workflow **`CI`** after CI has run at least once; choose the GitHub Actions source if requested.
- **Do not add participants, roles, admins or apps to this ruleset's bypass list**. Otherwise an Emergency Merge could accidentally bypass the checks.
- Disallow force pushes/deletion of `main`. Keep updates through PRs. Do not grant general direct-push exemptions.
- Once stack checks are added, require their stable job names here too (e.g. `frontend-checks`, `backend-checks`, `integration-checks`).

> Initial setup order: push/import the scaffold to the brand-new repository, open a small test PR, wait for `CI / foundation` to appear, then select that check and activate both rulesets. Make a second test PR to verify enforcement. Initial bootstrap of an empty repo necessarily precedes these protections.

**Test the emergency path once:** open a harmless PR with green CI, have one authorized human explicitly direct a bypass merge, confirm GitHub offers **review-only** bypass and still blocks red/missing CI. Write the reason in the PR. If the interface does not offer the exact combination on your account, **stop and adjust the ruleset with the team**; do not weaken the CI gate silently.

## 2. Issues and team cadence

- Use `.github/ISSUE_TEMPLATE/feature.yml` / `bug.yml`. Assign each Issue to a human; label `priority:must` / `priority:should` and relevant function. Create labels in GitHub UI if they do not already exist.
- Keep one Issue per coherent deliverable and link PRs using `Closes #<issue-number>`.
- Update `docs/STATUS.md` on agreed checkpoints (roughly daily and pre-demo), ideally by Team Lead / Integration to avoid concurrent edits.
- Set a short integration sync: blockers, shared interface changes, CI health, next demo slice.

## 3. CI — active from first PR

- `.github/workflows/ci.yml` is active once pushed. It runs Python standard-library validation and validator unit tests on PRs and `main` pushes.
- The `foundation` job verifies template file presence, untracked private role conventions, and Conventional Commit PR titles. It is a **scaffold check only**, not a substitute for application tests.
- After the case/stack is chosen, create real jobs that perform dependency install, formatting/lint, type checking, unit/integration tests and build for every applicable app. Make those job names required in Ruleset B. Keep CI deterministic and do not put deploy credentials in PR jobs.
- The validator can be tested locally by the agent with `python3 -m unittest discover -s tests -v` and `python3 scripts/validate_scaffold.py --root .`.

## 4. CD — enable after hosting is selected

`templates/deploy.github-actions.example.yml` is an **inactive, deliberately failing** example; it is not in `.github/workflows/` and does not deploy anything. To activate actual automatic demo deployment:

1. Choose a host and public demo URL at kickoff (e.g. one provider for web UI and backend or a monolithic host). Confirm account/quota, regions, secrets and rollback route.
2. Add required credentials in Settings → Secrets and variables → Actions, preferably via a protected `demo` environment. Never commit tokens or `.env`.
3. Copy/adapt the template to `.github/workflows/deploy.yml`. **Replace the explicit failure placeholder** with a tested provider-specific build/deploy step, and add a real smoke test against the deployed URL. If provider offers GitHub app auto-deploy, document it and avoid double deployment from Actions.
4. Verify deploy on a controlled merge to `main` and record demo URL in `docs/STATUS.md` and `docs/ARCHITECTURE.md`.
5. Keep `on: push` to `main`: every completed human-authorized merge then triggers automatic deployment. Set concurrency to avoid overlapping deployments.

Until steps 1–4 are done, **automatic deployment is not configured**. Do not report green CD from a workflow that merely prints success.

## 5. Security and permissions

- Use Actions `permissions: contents: read` for CI; provide deployments only permissions actually required by the hosting provider.
- Do not run untrusted PR code with write tokens or deploy secrets; deployment triggers only from protected `main`.
- Review marketplace plugins and Ponytail's two lifecycle hooks before trusting them on each human's machine.
- Do not share personal agent settings, `ROLE.local.md`, API keys, production data or credentials in the public repository.

## References

- GitHub rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository
- Available rules: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
- GitHub Actions: https://docs.github.com/en/actions

