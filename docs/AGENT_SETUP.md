# Agent workstation setup (each of four participants)

These instructions are for Codex Desktop and Claude Code Desktop Code tab. Install plugins **independently for every agent host each person uses**; cloning this repo does not install plugins. Only install from official publishers and review permissions/hooks before trusting them. The agent may run installer commands on the human's behalf within its approved environment; a human does not need a daily CLI workflow.

## Mandatory skills / provenance

| Skill system | Trusted upstream | Intended role |
| --- | --- | --- |
| Superpowers | https://github.com/obra/superpowers | Planning, TDD, review, verification |
| Ponytail | https://github.com/DietrichGebert/ponytail | Simpler implementation, hooks |
| Matt Pocock Skills | https://github.com/mattpocock/skills | Engineering practices and issue workflow |

Install plugins once per *host*; do not also install duplicate copies of the same skills through `skills.sh` unless troubleshooting requires it. Plugins are not vendored into this template.

## Codex Desktop

1. **Superpowers:** In Codex Desktop's sidebar open **Plugins**, find **Superpowers** in **Coding** and click `+` to install.
2. **Ponytail:** Ask your agent to run the publisher's installer in an approved environment (these are setup commands, not a requirement to use CLI day to day):

   ```text
   codex plugin marketplace add DietrichGebert/ponytail
   codex plugin add ponytail@ponytail
   ```

   Confirm **Node.js** is on the PATH visible to non-interactive hooks. Review the two lifecycle hooks in Codex's `/hooks` interface and explicitly **trust both**. Restart Codex Desktop and open a **new conversation**. Do not silently accept unreviewed hook code. If desktop installation or `/hooks` isn't exposed in your version, use the supported installer/hook approval flow with the agent's assistance and confirm that hooks really run; do not mark the setup complete prematurely.
3. **Matt Pocock Skills:** Ask your agent to install from the publisher's marketplace:

   ```text
   codex plugin marketplace add mattpocock/skills
   codex plugin add mattpocock-skills@mattpocock
   ```

4. **Model policy:** Merge the contents of `config/codex.config.toml.example` into your personal Codex `config.toml` (usually `~/.codex/config.toml`). Preserve unrelated settings, restart as needed and ask Codex to report active model / subagent settings. This is a **personal** config, not a tracked repo config.
5. Start a new thread and verify Superpowers skills, Ponytail activation via lifecycle hooks, and Matt Pocock Skills are available.

## Claude Code Desktop (Code tab)

Enter these as separate commands in the Code tab's agent prompt. No terminal setup is required if the app supports plugin commands.

1. **Superpowers:**

   ```text
   /plugin install superpowers@claude-plugins-official
   ```

2. **Ponytail** — send as **two distinct prompts**:

   ```text
   /plugin marketplace add DietrichGebert/ponytail
   ```

   ```text
   /plugin install ponytail@ponytail
   ```

   Ensure Node.js works for lifecycle hooks, review permissions, then start a new conversation. The plugin supplies its own hooks; do not paste made-up hook JSON into this project.

3. **Matt Pocock Skills:**

   ```text
   /plugin install mattpocock-skills@claude-plugins-official
   ```

4. Confirm the agent actually reads this repo's `AGENTS.md` and its local `ROLE.local.md`. Do not create a competing root `CLAUDE.md`; if your installed Claude version does not load `AGENTS.md`, explicitly tell the agent to read it at session start and update the app before relying on automatic behavior.
5. No Codex-specific model defaults or subagent limit are imposed on Claude.

## Repository-level initialization (once per repo)

In an agent that has Matt Pocock Skills installed, run `/setup-matt-pocock-skills` **once for this repository**. Select:

- Issue tracker: **GitHub Issues**.
- Triage labels: suggested `type:feature`, `type:bug`, `type:docs`, `priority:must`, `priority:should`, `status:blocked`; adjust in GitHub UI to match actual choices.
- Documentation path: **`docs/`**.

If the skill proposes tracked configuration files, review its diff so it does not overwrite `AGENTS.md` or this template's agreements. Commit relevant **shared** setup through a PR; do not commit personal plugin credentials/state.

## Four-person sign-off checklist

| Check (each human, for each host used) | Done? |
| --- | --- |
| `ROLE.local.md` exists with human's functions and ownership | ☐ |
| Superpowers is installed and usable | ☐ |
| Ponytail is installed from official repo | ☐ |
| Node.js available to Ponytail's lifecycle hooks | ☐ |
| Both Ponytail lifecycle hooks reviewed and trusted where the host requires it | ☐ |
| Fresh agent session confirms hook/skill activation | ☐ |
| Matt Pocock Skills is installed and visible | ☐ |
| Codex-only local config models and max-two-children verified (if Codex is used) | ☐ |
| `AGENTS.md` and local role read by agent | ☐ |

Do not claim these as automatically completed by importing the ZIP; they require installation and human authorization on individual machines.

## Official setup references

- Superpowers: https://github.com/obra/superpowers#installation
- Ponytail (including hook requirements): https://github.com/DietrichGebert/ponytail/blob/main/INSTALL.md
- Matt Pocock Skills: https://github.com/mattpocock/skills#installation-30-second-setup

