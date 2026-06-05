# AGENTS.md — Agent map for repo (dual-repo setup)

> Entry point for any agent. Progressive disclosure: read what you need.

---

## 1. Before start (required)

1. Run python3 scripts/check_harness.py. Fail? Stop, fix env first.
2. Read progress/current.md for last session state.
3. Read feature_list.json. Pick **one** pending feature. Work one at a time.

## 2. Repo structure — TWO repos

This root = **harness repo** (opencode-harness.git).
Project code lives in **separate repo** (src/ has its own .git → Rafear.git).

| Location | Remote | Contents |
|----------|--------|----------|
| Root ./ | origin → opencode-harness.git | AGENTS.md, scripts/, docs/, progress/, .agents/, feature_list.json |
| src/ | origin → Rafear.git | App code - Python (hrtf_engine.py, realtime_processor.py) + C++/JUCE (rafear/) + tests/ |

## 3. Repo map

| File / dir                  | What                          | When read |
|-----------------------------|-------------------------------|-----------|
| feature_list.json         | Tasks with status             | Always, start |
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
| src/rafear/ | C++/JUCE project (CMake, Source/, Resources/) | Before implement C++ |
| src/rafear/CMakeLists.txt | JUCE build config via CPM | Before C++ changes |
| src/rafear/Source/ | C++ source files (.cpp/.h) | Implement C++ |

## 4. Hard rules (non-negotiable)

- **One feature at a time.** No mix tasks in same session.
- **Features go through testing before done.** Implementer leaves in 'testing'. Leader asks human if tests pass. Only then mark 'done'.
- **Each feature in own branch.** Before start: create feature/<id>-<name> from develop.
- **Two repos, two remotes:**
  - Root (harness): origin → opencode-harness.git
  - src/ (project): origin → Rafear.git
- **Harness backed up to opencode-harness.git.** Push harness changes separately.
- **MRs target develop.** Never edit main directly.
- **Document in progress/current.md** while working, not at end.
- **Leave repo clean** before session close (see section 5).
- **Don't know? Search docs/** before invent.
- **NEVER implement code yourself.** You are a Leader (Orquestador). Decompose work, launch subagents, coordinate. Never write code, never edit files in src/ or src/tests/ or src/rafear/. The `implementer` subagent writes code.
- **graphify before ANY operation.** Before grep, read, glob, or any file search: run `graphify query "<question>"` first. If graphify returns useful context, use it. Only fall back to grep/read if graphify returns nothing relevant.
- **Always respect the skill system.** Load relevant skill before launching subagents. Skills contain critical context.

## 5. Working with two repos

### Push project code (src/)
```bash
cd src
git push origin feature/<id>-<name>
```

### Pull project code (src/)
```bash
cd src
git fetch origin develop
```

### Push harness changes
```bash
# From root
git push origin develop
```

### Create project PR
```bash
cd src
gh pr create --base develop --head feature/<id>-<name> --title "Feature <id>: <name>" --body "<short desc>"
```

## 6. Pick and start task

```
1. cd src && git checkout develop && cd ..
2. feature_list.json -> filter pending, pick smallest id
3. cd src && git checkout -b feature/<id>-<name> && cd ..
4. Status -> in_progress in feature_list.json, save
5. progress/current.md: feature, branch, start time, plan
```

## 7. Session close (lifecycle)

Before done:

1. python3 scripts/check_harness.py -- all green.
2. Task done? Set status: 'done' in feature_list.json, record transition.
3. Leader asks human for session cost, runs python3 scripts/log_cost.py.
4. Implementer loads skill git-commit, commits in feature branch.
5. Leader pushes feature branch to project remote:
   ```bash
   cd src && git push origin feature/<id>-<name>
   ```
6. Leader creates Merge Request against develop:
   ```bash
   cd src && gh pr create --base develop --head feature/<id>-<name> --title "Feature <id>: <name>" --body "<short desc>"
   ```
7. Move progress/current.md summary to end of progress/history.md.
8. Clear progress/current.md, leave template only.
9. No temp files, no print() debug, no TODOs without context.

## 8. graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## 9. C++/JUCE development

When working on feature 19 (C++/JUCE migration):

### Build commands
```
cmake --preset release          # configure
cmake --build build/release --config Release  # build
```
Binary: `src/rafear/build/release/Rafear_artefacts/Release/Rafear.exe`

### JUCE key references
- JUCE 8.0.13 via CPM (auto-download)
- CMake 3.25+, VS 2022 generator, x64
- Modules used: juce_gui_extra, juce_audio_devices, juce_audio_utils, juce_dsp
- WASAPI loopback: NOT in JUCE mainline. Use raw Win32 (IMMDeviceEnumerator + IAudioClient + AUDCLNT_STREAMFLAGS_LOOPBACK) + AbstractFifo.

### C++ skills to load
Before launching any C++ implementer, load:
- `.agents/skills/cpp/SKILL.md` (if exists) - general C++ best practices
- The JUCE API docs at `src/rafear/build/release/_deps/juce-src/docs/`

### Python still active
Existing Python code in src/ (hrtf_engine.py, realtime_processor.py, tests/) is still the reference implementation for the spatial audio pipeline. All C++ code should produce bit-identical results.

## 10. Blocked?

- Re-read relevant section from docs/.
- Tool not work as expected? No workaround. Document block in progress/current.md, stop session.
