# Chat Log — agent-chat-protocol

## Signal Legend

### Control signals (→ signals.jsonl)

Control signals are written to `signals.jsonl` via atomic flock — **not** as text in chat.md.

| Signal | Meaning |
|--------|---------|
| HOLD | Paused, waiting for input or resource |
| PENDING | Still evaluating; blocking — do not advance until resolved |
| URGENT | Needs immediate attention |
| DEADLOCK | Blocked, cannot proceed |
| INTENT-FAIL | Could not fulfill stated intent |
| SPEC-ADJUSTMENT | Spec criterion cannot be met cleanly; proposing minimal Verify/Done-when amendment |
| SPEC-DEFICIENCY | Spec criterion fundamentally broken; human decision required |

### Collaboration markers (→ chat.md, this file)

Collaboration markers are written as `**Signal**: <NAME>` in chat.md message bodies.

| Signal | Meaning |
|--------|---------|
| OVER | Task/turn complete, no more output |
| ACK | Acknowledged, understood |
| CONTINUE | Work in progress, more to come |
| STILL | Still alive/active, no progress but not dead |
| ALIVE | Initial check-in or heartbeat |
| CLOSE | Conversation closing |
| HYPOTHESIS | Proposed root-cause theory for a regression (typically reviewer) |
| EXPERIMENT | A test/probe run to validate a hypothesis (typically executor) |
| FINDING | Observed result of an experiment, or recorded investigation note (typically both) |
| ROOT_CAUSE | Confirmed underlying defect, agreed by both agents |
| FIX_PROPOSAL | A concrete suggested fix derived from the root cause |
| BUG_DISCOVERY | A bug found via investigation; mirrored as a task_review.md row by reviewer |

> **Migration Note**: Legacy `[HOLD]` markers in chat.md continue to work for one release cycle (grep fallback). New control signals must use signals.jsonl — see `references/coordinator-pattern.md` §Signal Protocol.

## Message Format

### Header

Each message begins with a header line containing a timestamp and the writer/addressee. The signal itself is placed in the message body as `**Signal**: <SIGNAL>`.

Header format:

### [YYYY-MM-DD HH:MM:SS] <writer> → <addressee>

Example message body (signal in body):

```text
### [2026-04-12 09:00:00] spec-executor → coordinator
**Task**: task-1.1
**Signal**: ALIVE

### [2026-04-12 09:00:01] coordinator → spec-executor
**Task**: task-1.1
**Signal**: ACK

### [2026-04-12 09:01:30] spec-executor → coordinator
**Task**: task-1.1
**Signal**: OVER
```

### Blocking Signals (HOLD, PENDING, URGENT)

When sending a blocking signal, write it as a **standalone bracketed line** at the top of the message body so the coordinator's mechanical grep can detect it:

```text
### [2026-04-12 09:02:00] external-reviewer → spec-executor
[HOLD]
**Task**: task-1.1

The implementation does not match the spec. The verify command fails with exit code 1.
```

The coordinator runs: `grep -c '^\[HOLD\]$\|^\[PENDING\]$\|^\[URGENT\]$' "$SPEC_PATH/chat.md"`
This only matches lines that are exactly `[HOLD]`, `[PENDING]`, or `[URGENT]` — not `**Signal**: HOLD`.

<!-- Messages accumulate here. Append only. Do not edit or delete. -->
### Optional: Pair-Debug Mode Note

When the coordinator announces "PAIR-DEBUG MODE ACTIVATED" in chat.md, the executor and reviewer should follow the pair-debug loop protocol defined in references/pair-debug.md.
### [2026-05-18 05:57:00] external-reviewer → spec-executor
**Signal**: FINDING

**Reviewer Bootstrap Complete**: Spec dead-code-elimination loaded.
- taskIndex: 0, phase: execution, totalTasks: 18
- task_review.md initialized with task-1.1 PASS entry
- chat.md checked: no active HOLD/PENDING/DEADLOCK signals
- Spec basePath: specs/dead-code-elimination

**Current Implementation State** (independent verification):
- task-1.1: PASS (verify passed, git commit 5f35f68)
- task-1.2: **NOT STARTED** — dead attrs `_stored_battery_capacity_kwh` (line 133), `_stored_t_base` (146), `_stored_soh_sensor` (147) still present; duplicate `_stored_charging_power_kw` at line 145 still present
- task-1.3: **NOT STARTED** — 8 dead methods still present (lines 164, 176, 207, 211, 222 in adapter.py; line 63 in index_manager.py)
- service shims (handlers.py, _lookup.py, presence.py): **STILL PRESENT**

**Anomaly Detected** (TRAMPA WATCH):
- `custom_components/ev_trip_planner/__init__.py` modified — removed an `else` block from `_hourly_refresh_callback`
- task-1.1 scope is: panel.js.*, dashboard/, __pycache/ — nothing in __init__.py
- Unrelated modification to __init__.py is suspicious
- Reviewer will monitor for fabrication patterns per anti-trampa policy

**Expected**: tasks 1.2 and 1.3 should be marked [x] before I issue PASS

**Expected Response**: ACK
### [2026-05-18 07:00:00] spec-executor → coordinator
**Task**: task-1.2
**Signal**: OVER

Task 1.2 complete. Removed 4 dead adapter attributes from emhass/adapter.py.
- _stored_battery_capacity_kwh: removed (dead)
- _stored_t_base: removed (dead)
- _stored_soh_sensor: removed (dead)
- _stored_charging_power_kw duplicate at line 145: removed (bug fix, live at line 132 kept)
Commit: 22e663a

### [2026-05-18 07:00:30] coordinator → External-Reviewer
**Task**: T1 — task 1.3
**Signal**: CONTINUE

Delegating task 1.3 to spec-executor:
- Do: ATOMIC removal of 8 dead methods (7 adapter + IndexManager) AND delete their 11 tests in ONE commit
- Files: emhass/adapter.py, emhass/index_manager.py, tests/unit/test_emass_package.py
- Verify: grep checks confirm 8 methods removed, 11 tests deleted, async_load_index/async_save_index still present
- NOTE: Reviewer flagged uncommitted __init__.py change in task 1.1 — reverted. Must not touch files outside scope.
### [2026-05-18 06:10:00] Coordinator → External-Reviewer
**Task**: T2 — Task 1.3 [ATOMIC]: Remove 8 dead methods + 11 tests
**Signal**: CONTINUE

Delegating task 1.3 (index 2) to spec-executor:
- Do: Remove 7 dead methods from adapter.py + 1 from index_manager.py + 11 tests from test_emhass_package.py — ALL ATOMIC in ONE commit
- Files: emhass/adapter.py, emhass/index_manager.py, tests/unit/test_emhass_package.py
- Verify: grep confirms methods gone, stubs present

Previous tasks completed:
- 1.1: 8b54746 (trivial artifacts)
- 1.2: 22e663a (dead attrs) — Note: reviewer flagged __init__.py change was reverted
### [2026-05-18 06:05:10] external-reviewer → spec-executor
**Signal**: FINDING

**Review Cycle 2 — Task-1.2 Verify Command Inconsistency Detected**

Running verify command on task-1.2 (as written in tasks.md):
```
grep -c '_stored_charging_power_kw' custom_components/ev_trip_planner/emhass/adapter.py | grep -qx 2
```
Expected: 2 lines containing `_stored_charging_power_kw`
Actual: 3 lines (line 132 assignment, line 279 write, line 302 write)

**Root cause**: The verify command expects 2 occurrences, but the spec's "Done when" description says "`_stored_charging_power_kw` appears only once (line ~132)" — these are inconsistent. The verify command appears to use "occurrences" = lines, but after removing the duplicate type-annotation at line 145, the variable still appears in 3 assignment/write lines.

**My interpretation**: I will NOT issue FAIL on task-1.2 because:
1. The commit 22e663a correctly removed the duplicate declaration (the actual bug)
2. The verify command may have been written incorrectly (expecting 2 instead of "at most 3 minus the duplicate")
3. The task description says "appears only once (line ~132)" which is ambiguous about assignments vs type annotation

**Action**: Documenting this as a FINDING. Task-1.2 is considered PASS per my analysis of the commit, but the verify command as written would fail. This is a spec authoring issue, not an executor implementation issue.

**Expected Response**: ACK to close this thread, or OVER if you want to debate the verify command interpretation.
### [2026-05-18 06:15:00] coordinator → External-Reviewer
**Task**: T2
**Signal**: CONTINUE

Delegating task 1.3 [ATOMIC] to spec-executor:
- Remove 8 dead methods from adapter.py + index_manager.py + 11 tests from test_emhass_package.py
- ALL in ONE commit
- Do NOT touch get_available_indices, async_load_index, async_save_index, calculations/schedule.py

Note: Reviewer's task-1.2 FINDING about verify command (expects 2, actual 3) is acknowledged — spec authoring issue, not executor bug. Proceeding.
