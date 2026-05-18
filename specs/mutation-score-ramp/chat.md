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
| STILL | Still alive/active, no progress but not dead — also the executor liveness **heartbeat** emitted to `signals.jsonl` |
| ALIVE | Initial check-in or liveness **heartbeat** — also the executor heartbeat emitted to `signals.jsonl` with `reason: "step N/M: <activity>"` |
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
### [2026-05-18 17:36:00] Coordinator → External-Reviewer
**Task**: T0 — 1.1 [VERIFY] Verify `make mutation` runs a clean full run (A.1)
**Signal**: CONTINUE

Delegating task 0 to qa-engineer:
- Do: Run `make mutation` full run (~10 min), capture stdout/stderr, record baseline runtime in .progress.md
- Files: specs/mutation-score-ramp/.progress.md
- Verify: `make mutation; echo "EXIT=$?"` — expect EXIT=0 and completed run summary
### [2026-05-18 17:59:30] qa-engineer → Coordinator
**Task**: 1.1 [VERIFY] Verify `make mutation` runs a clean full run (A.1)
**Signal**: OVER

VERIFICATION_PASS

Results:
- Exit code: 0
- Runtime: 456s (~7.6 min)
- Throughput: 25.01 mutations/second
- Total mutants: 11571
- Killed: 6581, Survived: 4989, Timeout: 1
- Kill rate: 56.9% (up from 48.9% baseline — tests added since baseline run)
- No crash, no unknown-flag error, full run completed
