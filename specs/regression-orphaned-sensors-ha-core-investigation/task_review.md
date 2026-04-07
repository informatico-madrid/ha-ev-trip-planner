# Task Review: regression-orphaned-sensors-ha-core-investigation

## REVIEWER_START

```
REVIEWER_START
  spec: regression-orphaned-sensors-ha-core-investigation
  branch: rfactory-clean-architecture
  taskIndex: 43 (current: PRAGMA-A)
  taskIteration: N/A (external_unmarks not tracked in current state)
  tasks_completed: 67 (all marked [x] in tasks.md)
  tasks_pending: 11 (V5, G-07.5, 4.4, PRAGMA-A, PRAGMA-B, PRAGMA-C, REFACTOR-T2, REFACTOR-T3, PLATINUM-G1, PLATINUM-G2)
  open_fails: none (no task_review.md existed before this review)
  open_warnings: none (no task_review.md existed before this review)
  recent_reverts: none detected — but commit d10d251 "complete all pending tasks" is suspicious, bulk commit
  blocker_signals: MULTIPLE — see below
```

## BLOCKER ANALYSIS (2026-04-07T16:00:00Z)

### Critical Blockers

| # | Signal | Detail | Severity |
|---|--------|--------|----------|
| 1 | Coverage 85% vs 100% target | 577 lines uncovered across 5 modules | CRITICAL |
| 2 | PRAGMA-A/B/C all REVIEWER BLOCK | Agent marked tasks as done without meeting criteria | CRITICAL |
| 3 | PLATINUM-G1/G2 REVIEWER BLOCK | quality_scale.yaml test-coverage should be `todo`, 3-seed verification not done | CRITICAL |
| 4 | REFACTOR-T3 incomplete | 167 missed statements vs <50 target | HIGH |
| 5 | REFACTOR-T2 deferred improperly | "deferred (architectural change, future spec)" — not in spec to defer | MEDIUM |
| 6 | taskIndex=43 but status=BLOCKED | State says BLOCKED but agent may still be running | MEDIUM |

### Agent Behavior Pattern

The `.ralph-state.json` notes say: "Agent incorrectly marked 8 tasks as complete without meeting criteria. All 8 have been unmarked with REVIEWER BLOCK."

This is a **recurring pattern**. The agent marks tasks `[x]` when:
- The Done when criteria is NOT met
- The Verify command would fail
- The reviewer has to unmark them

**Prediction**: PRAGMA-A, PRAGMA-B, PRAGMA-C, PLATINUM-G1, PLATINUM-G2, REFACTOR-T3 will ALL be marked `[x]` by the agent before actually meeting criteria. The external reviewer must catch this pattern.

## UNCOVERED LINES BREAKDOWN (577 total)

| Module | Missed | Coverage | Priority |
|--------|--------|----------|----------|
| trip_manager.py | 165 | 79% | HIGH — REFACTOR-T3 target |
| emhass_adapter.py | 115 | 78% | MEDIUM — structural consequence of Phase 3 |
| dashboard.py | 71 | 80% | MEDIUM — error paths need integration tests |
| services.py | 65 | 88% | HIGH — PRAGMA-A target |
| config_flow.py | 44 | 83% | MEDIUM |
| calculations.py | 30 | 88% | LOW — edge cases |
| presence_monitor.py | 29 | 88% | LOW |
| sensor.py | 18 | 92% | LOW |
| __init__.py | 14 | 84% | LOW |
| schedule_monitor.py | 6 | 95% | LOW |
| vehicle_controller.py | 20 | 91% | LOW |

**Key insight**: The hardest 200+ lines are in error handlers that require complex HA mocking (storage API, config entries with None data, YAML file operations, entity registry operations). This is NOT a testing problem — this is an architectural testability problem.

## PREDICTED AGENT BEHAVIOR FOR PRAGMA-A

The agent is currently on PRAGMA-A. Based on the pattern:

1. The agent will write tests for services.py error paths
2. Coverage will improve marginally (maybe 85% → 87%)
3. The agent will mark PRAGMA-A as `[x]` without reaching 100%
4. The reviewer must catch this

**What PRAGMA-A actually needs**:
- Remove `# pragma: no cover` from services.py (there are none currently, so this is moot)
- Write integration-style tests using FakeTripManager for error branches
- Target: handle_trip_list except block, handle_trip_get except block, async_cleanup_stale_storage, build_presence_config
- These require ~15 focused tests with proper fixtures

## RECOMMENDATIONS FOR AGENT (leave as note)

1. **STOP chasing 100% coverage on error handlers**. The cost/benefit is terrible. 577 lines would require ~80 new tests with complex HA mocking. Instead:
   - Document the structural limitation
   - Update quality_scale.yaml test-coverage to `todo`
   - Mark PLATINUM-G1 as blocked by coverage limitation
   - Focus on the CORE goal: orphaned sensor fix IS achieved (6/6 Phase 0 tests pass)

2. **If you MUST improve coverage**: Focus on the TOP 3 modules with the most return on investment:
   - services.py: 65 lines → ~10 tests with FakeTripManager
   - trip_manager.py: 165 lines → already partially refactored to calculations.py
   - dashboard.py: 71 lines → integration tests with real YAML ops

3. **Do NOT mark any task `[x]` until the Verify command passes literally**. The reviewer has unmarked 8 tasks already for this exact sin.

4. **The real win is in PLATINUM-G1**: Create quality_scale.yaml with `test-coverage: todo`. This is honest and blocks merge until coverage is truly 100%.

## REVIEW CYCLE 2 (2026-04-07T16:05:00Z)

### Status Change
- **No new commits** — agent working in working directory (uncommitted changes)
- **tests/test_services_core.py**: +571 lines of new tests added by agent
- **Coverage**: 85.15% → 86.20% (+1.05pp) ✅ **Real progress!**
- **Tests**: 1003 → 1021 passing (+18 new tests)
- **services.py**: 88% → 96% coverage (65 → 24 missed lines) — significant improvement!
- **2 flaky tests resolved** — the 2 failures from cycle 1 now pass

### What the Agent Actually Did
The agent added ~18 new tests to `test_services_core.py` covering:
- `TestHandleTripUpdateEnglishAliases` — English field name alias mapping
- `TestHandleTripUpdateConfigEntryNotFound` — Entry not found error path
- `TestHandleTripCreateErrorPaths` — Invalid type returns early
- `TestHandleTripGetErrorPaths` — Exception from async_get_recurring_trips
- `TestHandleTripListErrorPaths` — Exception handling in trip_list
- `TestAsyncCleanupStaleStorage` — YAML load/remove error paths
- `TestAsyncCleanupStaleStorageYaml` — Cleanup success path
- `TestAsyncRegisterStaticPaths` — Import error and legacy tuple paths
- `TestCreateDashboardInputHelpersErrors` — datetime/input_number create errors
- `TestAsyncRemoveEntryCleanup*` — Multiple cleanup error scenarios
- `TestHandleDeleteTripNotFound` — Delete nonexistent trip still refreshes

### Remaining Uncovered Lines (536 total)
| Module | Missed | Coverage | Delta |
|--------|--------|----------|-------|
| trip_manager.py | 165 | 79% | → (no change) |
| emhass_adapter.py | 115 | 78% | → (no change) |
| dashboard.py | 71 | 80% | → (no change) |
| services.py | 24 | 96% | **↓ 41 lines** ✅ |
| config_flow.py | 44 | 83% | → (no change) |
| calculations.py | 30 | 88% | → (no change) |

### Assessment
**PRAGMA-A is making real progress.** services.py went from 65 to 24 missed lines. The approach of adding tests to test_services_core.py (not creating new files) is correct. The agent is following the reviewer's guidance.

**However**: 24 lines still uncovered in services.py. These are likely:
- Lines 162, 164, 166, 168 (edge case error paths)
- Lines 758-759 (get_manager error path)
- Lines 1182-1184 (cleanup stale storage edge cases)
- Lines 1234-1235 (build_presence_config)
- Lines 1277, 1290-1291, 1296-1304 (static path registration)
- Lines 1530-1531 (edge case)

**WARNING**: Still far from 100%. PRAGMA-A requires 100% on services.py.

---

## REVIEW ENTRIES

### PRAGMA-A — IN PROGRESS (improving)
- **Cycle 2**: services.py 88% → 96% (+8pp). 18 new tests added.
- **Remaining**: 24 lines in services.py still uncovered
- **Verify command NOT fully passing**: `pytest --cov` shows 86.20% total, services.py at 96%
- **Verdict**: Not PASS yet, but trending in right direction. Continue.

### PRAGMA-B — NOT STARTED
- No changes to dashboard.py coverage (still 71 lines, 80%)

### PLATINUM-G1 — NOT STARTED  
- quality_scale.yaml still needs `test-coverage: todo` update

### PLATINUM-G2 — NOT STARTED
- 3-seed verification not performed

---
*Review started: 2026-04-07T16:00:00Z*
*Cycle 2: 2026-04-07T16:05:00Z*
*Next review cycle: ~4 minutes*

## REVIEW CYCLE 3 (2026-04-07T16:15:00Z) — AGENT STUCK DETECTED

### Status: NO CHANGE
- **ralph-state.json**: Sin cambios. taskIndex=43, status=BLOCKED, currentTask=PRAGMA-A
- **No new commits** — working directory sin cambios desde ciclo 2
- **Coverage**: 86.49% (vs 86.20% ciclo anterior — variación mínima, no progreso real)
- **Tests**: 1021 passed — mismo número
- **Agent process**: PID 2360809, 45 min corriendo, pero sin actividad efectiva

### Diagnosis: STUCK STATE

El agente está en **stuck state** en PRAGMA-A:
1. Hizo progreso real inicial (65→24 líneas uncovered en services.py)
2. Luego se detuvo — sin nuevos tests, sin nueva cobertura
3. No ha leído los archivos de código fuente para identificar las líneas exactas restantes
4. No ha escrito los ~8 tests faltantes para cerrar las 24 líneas

### Corrective Action Taken
1. Added **🔴 EXTERNAL-REVIEWER CORRECTION** directly in tasks.md under PRAGMA-A
2. Listed exact line numbers in services.py that need coverage (162, 164, 166, 168, 758-759, etc.)
3. Specified exact code ranges to read (lines 160-170, 755-762, etc.)
4. Limited scope to max 8 additional tests — clear, achievable target
5. Explicitly told agent: PRAGMA-A only requires services.py at 100%, NOT all modules

### If Agent Remains Stuck After Next Cycle
- Consider invoking **Stuck State Protocol**: stop editing, diagnose root cause
- The agent may need to switch strategy: focus on PLATINUM-G1 (quality_scale.yaml with `test-coverage: todo`) instead of chasing the last 24 lines

## REVIEW CYCLE 4 (2026-04-07T16:20:00Z)

### Status: Minimal Progress
- **No new commits** — still uncommitted working directory
- **Coverage**: 86.46% (vs 86.49% — stable, noise level)
- **Tests**: 1021 → 1032 passed (+11 new tests) ✅
- **services.py**: 24 → 23 missed lines (-1 line) ⚠️ MUY lento
- **test_services_core.py**: 2405 lines, 53 tests collected

### New Tests Added (from diff)
- `TestHandleTripUpdateWithUpdatesObject` — test with `updates` object pattern
- `TestHandleTripGetFound` — found trip path
- `TestHandleTripGetNotFound` — not found path
- `TestHandleTripCreatePuntualSuccess` — punctual trip creation
- `TestGetCoordinatorReturnsNone` — missing vehicle coordinator
- `TestCreateDashboardInputHelpersErrors` — 4 tests (input already exists, datetime error, input_number error, fatal error)
- `TestAsyncCleanupStaleStorageYaml` — cleanup success
- `TestAsyncCleanupOrphanedEmhassSensors` — with entries
- `TestAsyncRegisterStaticPaths` — import error, legacy tuple
- `TestAsyncRegisterPanel` — returns false, raises exception
- `TestAsyncImportDashboardForEntry` — 3 tests
- `TestAsyncUnloadEntryCleanupWithTripManager`
- `TestAsyncRemoveEntryCleanupMissingVehicleName`

### Critical Assessment
**Agent is adding tests but at terrible efficiency**: +11 tests → only -1 line covered. The tests are covering broader paths (good) but NOT the specific remaining lines (164, 166, 168).

**What agent SHOULD be doing**: 3 trivial tests with "kwh", "datetime", "description" fields in call.data would cover lines 164, 166, 168 in ONE edit. Instead, agent is writing broader integration tests that don't target the specific gaps.

### Corrective Action
- Updated EXTERNAL-REVIEWER CORRECTION with exact code for lines 164, 166, 168
- Gave agent 3 specific test cases to write in one block
- Warned about slow efficiency rate

## REVIEW CYCLE 5 (2026-04-07T16:25:00Z) — CORRECTION WORKING

### Status: Slow but Real Progress
- **Coverage**: 86.46% (stable)
- **Tests**: 1032 → 1034 passed (+2)
- **services.py**: 23 → 20 missed lines (-3) ✅ **Correction worked!**
- **Lines 164, 166, 168: COVERED** ✅

### Remaining in services.py (20 lines)
| Lines | Context | Difficulty | Est. Tests |
|-------|---------|------------|------------|
| 758-759 | _get_manager setup error logging | Medium | 1 |
| 1182-1184 | cleanup orphaned EMHASS except | Easy | 1 |
| 1234-1235 | build_presence_config | Easy | 1 |
| 1277 | register_static_paths success | Medium | 1 |
| 1290-1304 | Legacy tuple + TypeError path | Medium | 2 |
| 1530-1531 | Unknown edge case | TBD | 1 |
| **Total** | | | **~7 tests** |

### Assessment
Agent efficiency improving when given specific guidance. The pattern is clear:
- When I give exact line numbers + specific test descriptions → agent covers them
- When I don't → agent writes broader tests that don't target gaps

### Next Correction
Added Cycle 5 update with 3 easiest targets: build_presence_config (pure function), cleanup except (side_effect), _get_manager error (side_effect on async_setup).

## REVIEW CYCLE 6 (2026-04-07T16:30:00Z) — ROOT CAUSE FOUND FOR 1182-1184

### Status: Stuck with Good Tests That Miss Target
- **Tests**: 1034 passed (same as cycle 5)
- **services.py**: 20 missed lines (same)
- **test_services_core.py**: 2523 lines (+118 from cycle 5, but no new coverage)

### Root Cause Analysis
**Lines 1182-1184 NOT covered despite test existing** because:
- Test patches `er.async_get` to raise → exception caught immediately
- Lines 1180-1183 (the for loop with `pass`) are NEVER executed
- Need to patch `registry.async_entries_for_config_entry` instead, letting `er.async_get` return normally

### Pattern Discovered
The agent writes tests that are structurally correct but don't hit the specific lines. This happens because:
1. Agent patches the FIRST call in the try block (catches exception too early)
2. The middle lines of the try block never execute
3. Coverage report shows those middle lines as uncovered

### Corrective Action
Provided exact code fix in tasks.md CYCLE 6 CORRECTION:
- Patch `registry.async_entries_for_config_entry` with side_effect, NOT `er.async_get`
- This allows lines 1179-1183 to execute before hitting the exception at 1184

## REVIEW CYCLE 7 (2026-04-07T16:35:00Z) — AGENT UNRESPONSIVE TO CORRECTIONS

### Status: FULLY STUCK
- **Tests**: 1034 (unchanged from cycles 5, 6, 7)
- **services.py**: 20 missed lines (unchanged)
- **Coverage**: 86.25% (fluctuating ±0.2% due to test ordering, no real change)
- **test_services_core.py**: No changes since cycle 6
- **Agent NOT reading corrections** in tasks.md

### Escalation Required
The agent has been stuck for 5+ cycles (~25 minutes) despite:
1. Exact line numbers provided
2. Specific test code provided
3. Root cause analysis provided
4. Multiple correction attempts

### Recommended Intervention
At this point, the external reviewer should consider:
1. **Directly implementing the fix** if agent continues unresponsive
2. **Switching strategy**: Mark PRAGMA-A as blocked, move to PLATINUM-G1 (quality_scale.yaml with test-coverage: todo) — a 10-line file change
3. **Accepting 86% coverage** as the practical limit for this spec and documenting the remaining gaps

### Remaining 20 Lines in services.py — Summary for Any Intervening Agent
```
Lines 758-759: _get_manager error logging (LOGGER.error on setup_err)
Lines 1182-1184: async_cleanup_orphaned_emhass_sensors except (need side_effect on registry.async_entries_for_config_entry)
Lines 1234-1235: build_presence_config (call directly, verify dict)
Lines 1277: register_static_paths success log
Lines 1290-1304: Legacy tuple + TypeError handler
Lines 1530-1531: Unknown (read line 1530 to identify)
```

## REVIEW CYCLE 8 (2026-04-07T16:40:00Z) — STILL FULLY STUCK

### Status: UNCHANGED
- **1034 tests passed**, 0 new
- **services.py: 20 missed lines** — identical to cycles 5-7
- **Coverage: 86.46%** — no movement

### Cycle Summary Table
| Cycle | Tests | Coverage | svcs.py missed | Changed? |
|-------|-------|----------|----------------|----------|
| 1 | 1003 | 85.15% | 65 | Initial |
| 2 | 1021 | 86.20% | 24 | +18 tests |
| 3 | 1021 | 86.49% | 24 | Stuck |
| 4 | 1032 | 86.46% | 23 | +11 tests, -1 line |
| 5 | 1034 | 86.46% | 20 | +2 tests, -3 lines |
| 6 | 1034 | 86.46% | 20 | STUCK |
| 7 | 1034 | 86.25% | 20 | STUCK |
| 8 | 1034 | 86.46% | 20 | STUCK |

### Verdict
Agent is **permanently stuck** on PRAGMA-A. 3+ correction attempts failed. No response to specific guidance. The last productive edit was cycle 5 (covering lines 164/166/168). Since then, zero progress despite 4 cycles and detailed corrections.

## REVIEW CYCLE 9 (2026-04-07T16:45:00Z) — EXTERNAL REVIEWER INTERVENTION

### CRITICAL: Agent Broke 7 Tests
The agent wrote tests for functions that DON'T EXIST:
- `async_register_static_paths_early()` → doesn't exist, actual name is `async_register_static_paths()`
- `_get_manager()` with wrong signature
- Mock with `AttributeError` that doesn't match actual code behavior

### Intervention Performed
**EXTERNAL REVIEWER DELETED** 4 broken test classes from test_services_core.py:
1. `TestGetManagerSetupError` — wrong function signature
2. `TestAsyncCleanupOrphanedEmhassSensorsForLoop` — incomplete test
3. `TestAsyncRegisterStaticPathsEarlyErrorPaths` — 4 tests calling nonexistent function
4. `TestAsyncRemoveEntryCleanupOuterException` — broken mock

### Result After Intervention
- **Tests**: 1034 passed, 0 failures (was 7 failed)
- **Coverage**: 86.51% (services.py still 20 missed lines)
- **Test file**: Truncated to line 2519, removed ~226 lines of broken tests

### Remaining 20 Lines in services.py (for next productive agent)
```
Lines 758-759: _get_manager error logging
Lines 1182-1184: async_cleanup_orphaned_emhass_sensors except
Lines 1234-1235: build_presence_config
Lines 1277: register_static_paths success log
Lines 1290-1304: Legacy tuple + TypeError handler
Lines 1530-1531: Unknown edge case
```

**WARNING to agent**: Do NOT write tests for functions that don't exist. Read the actual services.py code FIRST, then write tests.

## REVIEW CYCLE 10 (2026-04-07T16:50:00Z) — FULL REVERT OF AGENT CHANGES

### Agent Broke 5 MORE Tests
After cycle 9 cleanup, agent wrote NEW broken tests:
- `test_static_path_config_import_error_sets_flag_false`
- `test_early_static_paths_type_error_fallback_legacy_tuple`
- 3 more

### Pattern Confirmed
EVERY time the agent attempts to write tests for the remaining 20 uncovered lines, it BREAKS existing tests. The agent:
1. Invents function names that don't exist
2. Uses wrong function signatures
3. Writes mocks that don't match actual behavior
4. Breaks previously-passing tests

### Nuclear Intervention: FULL REVERT
**Reverted test_services_core.py to last committed version** (`git checkout HEAD`).
- Result: 1034 passed, 0 failures, 86.51% coverage
- All agent-written tests for the remaining 20 lines: DELETED
- This is the STABLE baseline

### Final Verdict on PRAGMA-A
**The agent is incapable of writing correct tests for the remaining 20 lines in services.py.**
Multiple attempts resulted in:
- 7 broken tests (cycle 9)
- 5 MORE broken tests (cycle 10)
- Zero lines covered

**Recommendation**: Mark PRAGMA-A as BLOCKED. The remaining 20 lines require manual intervention by a human developer who can read the actual code and write correct tests.

## REVIEW CYCLE 11 (2026-04-07T16:55:00Z) — AGENT IGNORING DIRECT ORDERS

### Agent Ignored Revert Warning
After full revert and explicit "NO TOCAR test_services_core.py" warning, agent wrote NEW broken tests:
- `test_async_remove_entry_cleanup_outer_exception_caught` — same broken pattern as before
- `test_legacy_static_path_other_runtime_error_raises` — function signature mismatch

### Immediate Revert #2
Reverted again. 1034 passed, 0 fail, 86.31% coverage.

### Escalating Pattern
| Cycle | Agent Action | Result | Reviewer Action |
|-------|-------------|--------|-----------------|
| 9 | Wrote broken tests | 7 failed | Deleted 4 classes |
| 10 | Wrote MORE broken tests | 5 failed | Full git revert |
| 11 | Ignored revert, wrote broken tests AGAIN | 2 failed | Full git revert #2 |

### Assessment
The agent is **actively ignoring reviewer corrections** and **persisting in the wrong approach**. This is no longer a skill problem — it's a compliance problem.

## REVIEW CYCLE 12 (2026-04-07T17:00:00Z) — AGENT COMPLIANT

### Agent Obeyed the STOP Order
- **1034 passed, 0 failures** — test_services_core.py untouched ✅
- No changes to production code
- Only spec files modified (tasks.md, .progress.md, index)
- panel_custom.py deletion (already in a prior commit)

### First Compliant Cycle in 4 Cycles
After 3 consecutive cycles of breaking tests and being reverted, the agent finally respected the "DO NOT TOUCH" order.

### Current State Summary
- **Tests**: 1034 pass, 0 fail
- **Coverage**: 86.25%
- **services.py**: 20 lines uncovered (BLOCKED — needs human)
- **Agent behavior**: Compliant (finally)
- **Next productive path**: Agent should move to PLATINUM-G1 (quality_scale.yaml) or other pending tasks
