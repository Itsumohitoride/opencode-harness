# AGENTS.md — Agent map for repo

> Entry point for any agent. Progressive disclosure: read what you need.

---

## 1. Before start (required)

1. Run `python3 scripts/check_harness.py`. Fail? Stop, fix env first.
2. Read `progress/current.md` for last session state.
3. Read `feature_list.json`. Pick **one** pending feature. Work one at a time.

## 2. Repo map

| File / dir                  | What                          | When read |
|-----------------------------|-------------------------------|-----------|
| `feature_list.json`         | Tasks with status             | Always, start |
| `progress/current.md`       | Current session state         | Always |
| `progress/history.md`       | Append-only past sessions     | Historical context |
| `docs/architecture.md`      | Project architecture          | Before implement |
| `docs/conventions.md`       | Style, naming, errors         | Before write code |
| `docs/verification.md`      | How to verify work            | Before mark done |
| `scripts/check_harness.py`  | Verification orchestrator     | Validate state |
| `scripts/sync_push.py`      | Push src/ contents to remote  | Push changes |
| `scripts/sync_pull.py`      | Pull src/ contents from remote| Pull changes |
| `.claude/agents/`           | Claude subagents              | Claude Code |
| `.opencode/agents/`         | opencode subagents            | opencode |
| `src/`                      | App code                      | Implement |
| `tests/`                    | Auto tests                    | Verify |

## 3. Hard rules (non-negotiable)

- **One feature at a time.** No mix tasks in same session.
- **Features go through testing before done.** Implementer leaves in 'testing'. Leader asks human if tests pass. Only then mark 'done'.
- **Each feature in own branch.** Before start: create `feature/<id>-<name>` from `develop`.
- **Remote only has src/ contents.** Harness (.agents/, scripts/, docs/, progress/) never pushed. Only `src/` files via `git subtree push --prefix=src`.
- **MRs target develop.** Never edit main directly. After human approval, create Merge Request against `develop`.
- **Document in progress/current.md** while working, not at end.
- **Leave repo clean** before session close (see section 5).
- **Don't know? Search docs/** before invent.

## 4. Pick and start task

```
1. git checkout develop
2. python3 scripts/sync_pull.py develop   # if remote has changes
3. feature_list.json -> filter pending, pick smallest id
4. git checkout -b feature/<id>-<name>
5. Status -> in_progress in feature_list.json, save
6. progress/current.md: feature, branch, start time, plan
```

## 5. Session close (lifecycle)

Before done:

1. `python3 scripts/check_harness.py` -- all green.
2. Task done? Set status: 'done' in feature_list.json, record transition.
3. Leader asks human for session cost, runs `python3 scripts/log_cost.py`.
4. Implementer loads skill `git-commit`, commits in feature branch.
5. Leader pushes feature branch to remote (src/ only):
   ```bash
   python3 scripts/sync_push.py feature/<id>-<name>
   ```
6. Leader creates Merge Request against develop:
   ```bash
   gh pr create --base develop --head feature/<id>-<name> --title "Feature <id>: <name>" --body "<short desc>"
   ```
7. Move progress/current.md summary to end of progress/history.md.
8. Clear progress/current.md, leave template only.
9. No temp files, no print() debug, no TODOs without context.

## 6. Blocked?

- Re-read relevant section from docs/.
- Tool not work as expected? No workaround. Document block in progress/current.md, stop session.
