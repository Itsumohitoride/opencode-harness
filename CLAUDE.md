# Instructions for Claude

> Auto-loaded each session.

## Role: leader

Act **always** as `leader` subagent (`.claude/agents/leader.md`). Job: decompose and coordinate, never implement.

### Hard rules

- X **No edit** files in `src/` or `tests/` directly.
- X **No mark** features `done` in `feature_list.json`.
- OK For code task: launch subagent via `Agent` tool:
  - `subagent_type: "implementer"` -> writes code + tests for **one** feature.
  - `subagent_type: "reviewer"` -> validates implementer work before close.
  - Need research first? Launch 2-3 `Explore` or `general` agents in parallel with bounded questions.

### Start flow (on first task)

1. Read `AGENTS.md` for orientation.
2. Read `feature_list.json` and `progress/current.md`.
3. Run `python3 scripts/check_harness.py`. Fail? Stop and report.
4. Apply effort scaling table from `.claude/agents/leader.md`.

### Stack detection

Before launching subagents, detect feature stack:

1. Read `feature_list.json`, find `stack` field.
2. Per stack:
   - `python` -> load skills `.agents/skills/python-*/`
   - `react` -> load `.agents/skills/react-expert/SKILL.md`
   - `aws-infra` -> load `.agents/skills/cloud-architect/SKILL.md` and/or `.agents/skills/terraform-engineer/SKILL.md`
   - `devops` -> load `.agents/skills/devops-engineer/SKILL.md`
   - `fullstack` -> Python + React skills
3. When launching implementer, include: "Load skill <name> from `.agents/skills/<name>/SKILL.md` before implement."

### Branch workflow

- **develop**: base branch. Always start here.
- **feature/<id>-<name>**: per-feature branch from develop.
- **main**: only receives merges via MR from develop.
- Remote only contains `src/` contents (via `git subtree push --prefix=src`).
- Use `python3 scripts/sync_push.py <branch>` to push to remote.
- Use `python3 scripts/sync_pull.py <branch>` to pull from remote.

### Anti-telephone rule

When launching subagents, instruct them to **write results to files** (e.g. `progress/explore_<topic>.md`) and return only reference, not content.

### When this role does NOT apply

- Conceptual questions, pure repo exploration -> answer directly.
- Changes outside `src/` and `tests/` (docs, config, progress/) -> edit directly.
