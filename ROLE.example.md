# Local agent role — COPY TO `ROLE.local.md` (never commit)

> Personal configuration. Ask the human to fill every `<...>` field before product implementation. This file is read by both Codex and Claude agents operating on this person's workstation.

## Identity

- Human participant: `<name>`
- GitHub handle: `<@github-handle>`
- Agent host(s): `<Codex Desktop | Claude Code Desktop | both>`
- Functions (one or more): `<Backend | Frontend | UI/UX | Team Lead / Integration | DevOps | Fullstack>`
- Primary ownership / paths once architecture is chosen: `<module(s), directories, components>`
- Integration contact / reviewer for own modules: `<@github-handle>`

## My responsibilities

- Own delivery of: `<Issue types or components>`
- Internal technology decisions I can make autonomously: `<module-local choices>`
- Interfaces I provide/consume: `<docs/CONTRACTS.md section or links>`
- Out-of-scope areas that normally require the responsible owner's review: `<areas>`

## Working agreement

- I can modify other areas when an Issue requires it; my normal PR needs review from the responsible human for the affected area.
- Before modifying a shared API, schema, event, URL contract, component library contract, or deploy interface, I notify consumers in the linked Issue/PR and update `docs/CONTRACTS.md`.
- Architecture details inside my area are my responsibility once high-level team decisions are made; I record impactful cross-team decisions in `docs/DECISIONS.md`.
- I never merge a PR unless this human explicitly commands the merge. Emergency Merge still requires this command, a reason, and green CI.
- Follow `AGENTS.md`, `docs/AGENT_WORKFLOW.md`, `docs/GIT_WORKFLOW.md` and `docs/DEFINITION_OF_DONE.md`.

