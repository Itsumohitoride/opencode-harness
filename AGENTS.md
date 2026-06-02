# AGENTS.md — Agent map for repo (dual-repo setup)

> Entry point for any agent. Progressive disclosure: read what you need.

---

## 1. Before start (required)

1. Run python3 scripts/check_harness.py. Fail? Stop, fix env first.
2. Read progress/current.md for last session state.
3. Read eature_list.json. Pick **one** pending feature. Work one at a time.

## 2. Repo structure — TWO repos

This root = **harness repo** (opencode-harness.git).
Project code lives in **separate repo** (src/ has its own .git → Rafear.git).

| Location | Remote | Contents |
|----------|--------|----------|
| Root ./ | origin → opencode-harness.git | AGENTS.md, scripts/, docs/, progress/, .agents/, feature_list.json |
| src/ | origin → Rafear.git | App code (hrtf_engine.py, ealtime_processor.py) + 	ests/ |

## 3. Repo map

| File / dir                  | What                          | When read |
|-----------------------------|-------------------------------|-----------|
| eature_list.json         | Tasks with status             | Always, start |
| progress/current.md       | Current session state         | Always |
| progress/history.md       | Append-only past sessions     | Historical context |
| docs/architecture.md      | Project architecture          | Before implement |
| docs/conventions.md       | Style, naming, errors         | Before write code |
| docs/verification.md      | How to verify work            | Before mark done |
| scripts/check_harness.py  | Verification orchestrator     | Validate state |
| .claude/agents/           | Claude subagents              | Claude Code |
| .opencode/agents/         | opencode subagents            | opencode |
| src/                      | App code (separate repo)      | Implement |
| src/tests/                | Auto tests (in src/ repo)     | Verify |

## 4. Hard rules (non-negotiable)

- **One feature at a time.** No mix tasks in same session.
- **Features go through testing before done.** Implementer leaves in 'testing'. Leader asks human if tests pass. Only then mark 'done'.
- **Each feature in own branch.** Before start: create eature/<id>-<name> from develop.
- **Two repos, two remotes:**
  - Root (harness): origin → opencode-harness.git
  - src/ (project): origin → Rafear.git
- **Harness backed up to opencode-harness.git.** Push harness changes separately.
- **MRs target develop.** Never edit main directly.
- **Document in progress/current.md** while working, not at end.
- **Leave repo clean** before session close (see section 5).
- **Don't know? Search docs/** before invent.

## 5. Working with two repos

### Push project code (src/)
`ash
cd src
git push origin feature/<id>-<name>
`

### Pull project code (src/)
`ash
cd src
git fetch origin develop
`

### Push harness changes
`ash
# From root
git push origin develop
`

### Create project PR
`ash
cd src
gh pr create --base develop --head feature/<id>-<name> --title "Feature <id>: <name>" --body "<short desc>"
`

## 6. Pick and start task

`
1. cd src && git checkout develop && cd ..
2. feature_list.json -> filter pending, pick smallest id
3. cd src && git checkout -b feature/<id>-<name> && cd ..
4. Status -> in_progress in feature_list.json, save
5. progress/current.md: feature, branch, start time, plan
`

## 7. Session close (lifecycle)

Before done:

1. python3 scripts/check_harness.py -- all green.
2. Task done? Set status: 'done' in feature_list.json, record transition.
3. Leader asks human for session cost, runs python3 scripts/log_cost.py.
4. Implementer loads skill git-commit, commits in feature branch.
5. Leader pushes feature branch to project remote:
   `ash
   cd src && git push origin feature/<id>-<name>
   `
6. Leader creates Merge Request against develop:
   `ash
   cd src && gh pr create --base develop --head feature/<id>-<name> --title "Feature <id>: <name>" --body "<short desc>"
   `
7. Move progress/current.md summary to end of progress/history.md.
8. Clear progress/current.md, leave template only.
9. No temp files, no print() debug, no TODOs without context.

## 8. Blocked?

- Re-read relevant section from docs/.
- Tool not work as expected? No workaround. Document block in progress/current.md, stop session.