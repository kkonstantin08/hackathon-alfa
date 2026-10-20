# Multi-agent, multi-human operating agreement

## Scope and decision rights

- One public GitHub Free monorepo, four humans, each with their own local agent role file, Codex Desktop and/or Claude Code Desktop.
- GitHub Issues are canonical tasks; every code PR links to an Issue. `docs/STATUS.md` is only a compact overview.
- At the case kickoff, assign the four independent data tasks in `docs/ROLES.md`. After the four independent tasks are complete, discuss architecture, the application stack and interfaces before integrating them. Select the deployment environment after evaluating the integrated prototype. The implementer decides their own module's libraries, patterns and internal architecture without mandatory lead approval. Revisit only when necessary.
- Before a shared interface changes (API request/response, shared type, DB contract depended on by another area, event, design-system public component, environment variable, or deploy interface), notify affected owners in Issue/PR and update `docs/CONTRACTS.md`. Agreement is useful, but formal approval of internal decisions is not a blocker.

## Functional boundaries, not hard walls

| Function | Leads on | Normally reviews changes to |
| --- | --- | --- |
| Backend | Services, persistence, API implementation | Backend-owned areas and APIs |
| Frontend | Application UI behavior and integration | Frontend-owned areas |
| UI/UX | User flows, prototypes, design guidance | User-facing layout, design system |
| Team Lead / Integration | Roadmap, merges coordination, integration testing | Cross-module wiring and shared agreements |
| DevOps | CI, environments, deployment, observability | Infrastructure and CI/CD |
| Fullstack | Assigned vertical feature | The assigned feature's frontend + backend code |

Four people may cover six functions after the first integrated prototype. Start with the four independent tasks in `docs/ROLES.md`, regardless of questionnaire specializations. Keep personal task boundaries in `ROLE.local.md`.

**Normal PR:** contributor may touch any code required by its Issue, but ask the responsible human to review modifications in that area. **Emergency Merge:** any team participant with appropriate GitHub access may merge a green-checked PR without a reviewer only on explicit human instruction, with an explanation in PR. No autonomous merge.

## For either agent host

1. Read `AGENTS.md`, the human's `ROLE.local.md`, the Issue, `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, and relevant contracts.
2. Ask only for missing decisions that change interfaces, scope or safety. Propose the smallest deliverable and, if needed, a short Issue-level plan.
3. Create `type/issue-number-short-topic` branch; implement and test; commit with Conventional Commits; push; open a PR. Never directly push to `main`.
4. Explain changed areas, tests, affected dependencies and reviewers in PR. Ask for human merge command only after checks/review or a declared emergency.
5. Let a human confirm merge; CI deploy follows on `main` after a provider has been configured.

## Skill precedence

- **Superpowers:** intent, planning, TDD, debugging, code review and verification workflow where applicable.
- **Ponytail:** minimize unnecessary complexity, but **never** use minimalism to omit agreed acceptance criteria, tests, security, accessible UI or required communication.
- **Matt Pocock Skills:** specialized engineering, issue triage and documentation; configure its issue tracker to GitHub Issues.
- When skills conflict, project requirements, safety and explicit human decisions win. Explain the conflict; do not silently bypass workflow checks.

## Codex-specific orchestration

- Desired main model: `gpt-6.1-sol`, reasoning `medium`.
- Desired default child model: `gpt-6-luna`, reasoning `high`.
- At most **2 active subagents at a time in a single Codex main session** (not an aggregate limit across four humans).
- Run dependent tasks sequentially; use subagents only where supported and genuinely independent. Child agents inherit the same workspace rules.
- This cap and model policy apply to Codex, **not Claude**.

## Coordination etiquette

- Claim/assign an Issue before coding; record dependent Issues and affected people there.
- Avoid editing `docs/STATUS.md` from four simultaneous feature branches. Update at checkpoints, coordinated by Team Lead / Integration, via PR.
- Resolve PR conflicts by communicating with the owner; never overwrite their work without checking.
- Keep API and UI implementations synchronized through `docs/CONTRACTS.md`, not parallel guesses.

