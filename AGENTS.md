# Agent entry point

This is a five-person, 4–7-day hackathon monorepo. Follow the linked source files; keep this index short.

1. Read `ROLE.local.md` (create from `ROLE.example.md` with the human before implementation; it is intentionally gitignored) and `docs/AGENT_WORKFLOW.md` to identify your human's responsibilities and boundaries.
2. Read `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, and `docs/CONTRACTS.md` before proposing or changing implementation. Do not invent case details or override settled shared decisions.
3. Follow `docs/GIT_WORKFLOW.md` and `docs/DEFINITION_OF_DONE.md` for every Issue and PR. You may create branches, commit, push, and open PRs autonomously. **Never merge without an explicit human instruction**, even in emergencies.
4. Treat GitHub Issues as the task source of truth; see `docs/STATUS.md` for the snapshot. Notify affected developers in the Issue/PR **before changing shared interfaces**.
5. Follow `docs/AGENT_SETUP.md`: verify Superpowers, Ponytail (with approved hooks), and Matt Pocock Skills are installed for the current agent host. Ask the human to finish setup if unavailable.
6. Codex only: orchestrator `gpt-6.1-sol` at `medium`; default executor/subagent `gpt-6-luna` at `high`; **no more than two active subagents per main session**. See `config/codex.config.toml.example`. This model/concurrency rule does not apply to Claude.

Keep changes scoped to an Issue, document meaningful trade-offs, test before claiming success, and request a human decision whenever authority or a shared contract is unclear.

