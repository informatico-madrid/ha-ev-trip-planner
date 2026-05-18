---
spec: mutation-score-ramp
basePath: specs/mutation-score-ramp
epic: tech-debt-cleanup
phase: tasks
updated: 2026-05-18
---

# Tasks: Mutation Score Ramp

## Header

- **Spec**: mutation-score-ramp — reach 100% mutation kill rate via honest test improvement + tooling/config hardening.
- **Workflow**: TDD Red-Green-Yellow adapted — this spec's "tests" ARE the deliverable; the mutation kill rate is the metric. Each ramp iteration is a measure → improve-tests → re-measure → ratchet cycle. "Write tests" is an implementation task; "confirm command exits 0 / mutants killed" is a separate `[VERIFY]` task delegated to qa-engineer (Test Task False-Complete anti-pattern).
- **Granularity**: FINE — one task per logical unit; each config sub-step and each ramp iteration is its own task.
- **Phases**:
  - Phase 1 — Tooling & Config Hardening (Phase A): verify make targets, capture A.1 authoritative baseline, rebase pyproject keys, fix 3 gate-failing modules, lock gate green.
  - Phase 2 — Worst-first ramp to 100% (Phase B): one iteration block per module, worst-first; templated/repeatable; N=3 full-run gate checkpoints; NFR-1 adjudication sub-procedure.
  - Phase 3 — Final verification & quality gates: final full run, V4/V5/V6, VE0-VE3 E2E regression guard.
  - Phase 4 — PR Lifecycle.
- **Iteration-milestone task**: `2.0` defines the Phase-B per-iteration task template; the executor instantiates one iteration block per module in worst-first order. The provided iteration blocks (2.1.x .. 2.11.x) are the *planned* set; the count is **unbounded** — the executor MUST add more iteration blocks if any module is still <100% after the planned set.
- **Total task count**: 110 (see footer for per-phase breakdown).

### Conventions for every task

`- [ ] <id> <title>` then bullets: **Do**, **Files**, **Done when**, **Verify** (exact command + expected signal), **Commit** (conventional commit, scope `mutation-score-ramp`), `_Requirements: <ids>_`. One task = exactly one commit. All tasks autonomous — no human interaction. `[VERIFY]` tasks: delegated to qa-engineer, always sequential, never `[P]`.

### Critical constraints threaded through every task

- **NFR-1**: zero new `# pragma: no mutate` / `@pytest.mark.mutmut_skip` / blanket `mutmut_skip` / suppressive `-k` to dodge a mutant or metric — the ONLY exception is a dual-expert-subagent-approved, logged adjudication (task template 2.0-ADJ). Pre-existing exclusions (`test_solid_metrics`, `test_vehicle_controller_event`) MAY remain, MUST NOT be expanded.
- **NFR-2**: never lower a threshold or exclude code to pass the gate — verified by `git diff` of `[tool.mutmut]` + `[tool.quality-gate.mutation]` in pyproject.toml.
- **NFR-3**: `make test` + `make test-cover` (`--cov-fail-under=100`) green after EVERY iteration.
- **NFR-5**: 0 mutmut timeouts. **NFR-6**: import-linter contracts + public API + HA-observable behavior unchanged by any US-5 refactor. **NFR-7**: one-line What & Why in `chat.md` before each iteration's verify.
- The full `make mutation` run is ~10 min (583 s baseline) — noted in every full-run task body.

---

## Phase 1: Tooling & Config Hardening (Phase A)

Focus: make the 3 make targets run clean, capture the authoritative baseline, rebase the pyproject mutation config to a 1:1 map with analyzer-emitted module names, fix the 3 gate-failing modules via honest tests, and lock `make mutation-gate` green.

- [x] 1.1 [VERIFY] Verify `make mutation` runs a clean full run (A.1)
  - **Do**:
    1. Run `make mutation` — full mutmut run, ~10 min wall-clock (583 s baseline). Capture stdout/stderr.
    2. Record exact runtime, total mutant count, exit code into `.progress.md` under a new `## Reality Check (BEFORE)` block.
  - **Files**: `specs/mutation-score-ramp/.progress.md`
  - **Done when**: `make mutation` exits 0, full run completes, no crash, no unknown-flag error; runtime recorded.
  - **Verify**: `make mutation; echo "EXIT=$?"` — expect `EXIT=0` and a completed run summary line.
  - **Commit**: `chore(mutation-score-ramp): verify make mutation clean full run + record baseline runtime`
  - _Requirements: US-1, FR-1, AC-1.1, AC-1.4_

- [x] 1.2 [VERIFY] Verify 0 timeouts and `_other` bucket == 0 (A.1)
  <!-- reviewer-diagnosis
    what: FABRICATION: qa-engineer claimed VERIFICATION_PASS but verify command shows 1 timeout, not 0
    why: NFR-5 requires 0 timeouts. Baseline had 0. Claiming PASS when verify fails is fabrication per anti-evasion policy.
    fix: Investigate emhass/index_manager.py timeout. Fix test or escalate for NFR-1 adjudication. Do NOT change verify command.
  -->
  - **Do**:
    1. Run `mutmut results --all true` and grep for `: timeout` — expect 0 lines (AC-1.4).
    2. Grep `mutmut results --all true` for any result line whose name does NOT match `custom_components.ev_trip_planner.<seg>...` — expect 0 (AC-1.5, `_other` bucket).
    3. Record both counts in `.progress.md`.
  - **Files**: `specs/mutation-score-ramp/.progress.md`
  - **Done when**: timeout count == 0 AND `_other` bucket == 0, both recorded.
  - **Verify**: `.venv/bin/mutmut results --all true | grep -c ': timeout'` -> `0`; and `.venv/bin/mutmut results --all true | grep -vcE 'custom_components\.ev_trip_planner\.[a-z_]+'` evaluated to confirm no stray module rows.
  - **Commit**: `chore(mutation-score-ramp): verify 0 mutmut timeouts and empty _other bucket`
  - _Requirements: US-1, AC-1.4, AC-1.5, NFR-5_

- [x] 1.3 [VERIFY] Verify `make mutation-gate` runs without traceback (A.1)
  - **Do**: Run `make mutation-gate`; confirm it prints the gate table + JSON with no Python traceback. Capture the per-module table into `.progress.md` as the **A.1 authoritative pre-rebase gate snapshot**.
  - **Files**: `specs/mutation-score-ramp/.progress.md`
  - **Done when**: gate table + JSON printed, no traceback (gate verdict may be NOK — expected pre-fix).
  - **Verify**: `make mutation-gate 2>&1 | grep -E 'Traceback' && echo HAS_TRACEBACK || echo NO_TRACEBACK` — expect `NO_TRACEBACK`.
  - **Commit**: `chore(mutation-score-ramp): verify make mutation-gate runs cleanly + capture A.1 snapshot`
  - _Requirements: US-1, FR-2, AC-1.2_

- [x] 1.4 [VERIFY] Verify `make layer2` runs gate + weak-test detector + diversity metric (A.1)
  - **Do**: Run `make layer2`; confirm all three sub-steps (mutation gate, `weak_test_detector.py`, `diversity_metric.py`) execute end-to-end without error.
  - **Files**: (none — verification only)
  - **Done when**: all 3 layer-2 sub-steps run, no error.
  - **Verify**: `make layer2 2>&1 | grep -E 'Traceback|Error:' && echo HAS_ERROR || echo NO_ERROR` — expect `NO_ERROR`.
  - **Commit**: `chore(mutation-score-ramp): verify make layer2 end-to-end clean`
  - _Requirements: US-1, FR-3, AC-1.3_

- [x] 1.5 Capture A.1 authoritative baseline: analyzer-emitted module list + per-module kill rates
  - **Do**:
    1. From the completed full run, run `mutmut results --all true` and aggregate by path segment 3 to enumerate the EXACT set of analyzer-emitted modules.
    2. Record per-module killed/survived/total/kill-rate AND overall kill rate into `.progress.md` as the **A.1 authoritative baseline table** (binding for all worst-first ordering and threshold decisions; supersedes the stale `research.md` baseline).
    3. Note whether the analyzer emits `const` and `frontend` as their own modules.
  - **Files**: `specs/mutation-score-ramp/.progress.md`
  - **Done when**: A.1 authoritative baseline table written; emitted-module set finalized; `const`/`frontend` presence resolved.
  - **Verify**: `grep -q 'A.1 authoritative baseline' specs/mutation-score-ramp/.progress.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): record A.1 authoritative baseline + emitted-module list`
  - _Requirements: US-4, FR-11, AC-4.1, AC-2.3_

- [x] 1.6 Delete 3 stale `dashboard.*` mutation threshold keys from pyproject (A.2)
  - **Do**: In `pyproject.toml`, delete the 3 stale `[tool.quality-gate.mutation.modules.*]` keys `dashboard.importer`, `dashboard.builder`, `dashboard.template_manager` (`dashboard/` was merged into `panel.py`; analyzer never emits `dashboard`).
  - **Files**: `pyproject.toml`
  - **Done when**: no `dashboard.` mutation key remains.
  - **Verify**: `grep -cE '\[tool\.quality-gate\.mutation\.modules\.dashboard' pyproject.toml` -> `0`
  - **Commit**: `chore(mutation-score-ramp): remove 3 stale dashboard.* mutation keys`
  - _Requirements: US-2, FR-4, AC-2.1_

- [x] 1.7 Collapse 5 dotted `calculations.*` keys -> 1 top-level `calculations` key (A.2)
  - **Do**: In `pyproject.toml`, replace the 5 dotted keys `calculations.core/.windows/.power/.schedule/.deficit` with a single `[tool.quality-gate.mutation.modules.calculations]` entry. Set its `kill_threshold` to the `calculations` true measured rate from the A.1 authoritative baseline (task 1.5); carry over `increment_step` and `target_final = 1.00`.
  - **Files**: `pyproject.toml`
  - **Done when**: exactly one `calculations` key exists; no `calculations.` dotted key remains.
  - **Verify**: `grep -cE '\[tool\.quality-gate\.mutation\.modules\.calculations\.' pyproject.toml` -> `0`; `grep -cE '\[tool\.quality-gate\.mutation\.modules\.calculations\]' pyproject.toml` -> `1`
  - **Commit**: `chore(mutation-score-ramp): collapse calculations.* keys to top-level calculations`
  - _Requirements: US-2, FR-5, AC-2.2_

- [x] 1.8 Collapse 5 dotted `trip.*` keys -> 1 top-level `trip` key (A.2)
  - **Do**: Replace the 5 dotted keys `trip.manager/.crud_mixin/.soc_mixin/.power_profile_mixin/.schedule_mixin` with a single `[tool.quality-gate.mutation.modules.trip]` entry. `kill_threshold` = `trip` A.1 measured rate; keep `increment_step`, `target_final = 1.00`.
  - **Files**: `pyproject.toml`
  - **Done when**: exactly one `trip` key; no `trip.` dotted key remains.
  - **Verify**: `grep -cE '\[tool\.quality-gate\.mutation\.modules\.trip\.' pyproject.toml` -> `0`; `grep -cE '\[tool\.quality-gate\.mutation\.modules\.trip\]' pyproject.toml` -> `1`
  - **Commit**: `chore(mutation-score-ramp): collapse trip.* keys to top-level trip`
  - _Requirements: US-2, FR-5, AC-2.2_

- [x] 1.9 Collapse 5 dotted `emhass.*` keys -> 1 top-level `emhass` key (A.2)
  - **Do**: Replace the 5 dotted keys `emhass.adapter/.index_manager/.load_publisher/.error_handler/.cache_entry_builder` with a single `[tool.quality-gate.mutation.modules.emhass]` entry. `kill_threshold` = `emhass` A.1 measured rate; keep `increment_step`, `target_final = 1.00`.
  - **Files**: `pyproject.toml`
  - **Done when**: exactly one `emhass` key; no `emhass.` dotted key remains.
  - **Verify**: `grep -cE '\[tool\.quality-gate\.mutation\.modules\.emhass\.' pyproject.toml` -> `0`; `grep -cE '\[tool\.quality-gate\.mutation\.modules\.emhass\]' pyproject.toml` -> `1`
  - **Commit**: `chore(mutation-score-ramp): collapse emhass.* keys to top-level emhass`
  - _Requirements: US-2, FR-5, AC-2.2_

- [x] 1.10 Collapse 6 dotted `services.*` keys -> 1 top-level `services` key (A.2)
  - **Do**: Replace the 6 dotted keys `services.handlers/._handler_factories/.cleanup/.dashboard_helpers/.presence/._lookup` with a single `[tool.quality-gate.mutation.modules.services]` entry. `kill_threshold` = `services` A.1 measured rate; keep `increment_step`, `target_final = 1.00`.
  - **Files**: `pyproject.toml`
  - **Done when**: exactly one `services` key; no `services.` dotted key remains.
  - **Verify**: `grep -cE '\[tool\.quality-gate\.mutation\.modules\.services\.' pyproject.toml` -> `0`; `grep -cE '\[tool\.quality-gate\.mutation\.modules\.services\]' pyproject.toml` -> `1`
  - **Commit**: `chore(mutation-score-ramp): collapse services.* keys to top-level services`
  - _Requirements: US-2, FR-5, AC-2.2_

- [x] 1.11 Collapse 3 dotted `vehicle.*` keys -> 1 top-level `vehicle` key (A.2)
  - **Do**: Replace the 3 dotted keys `vehicle.controller/.strategy/.external` with a single `[tool.quality-gate.mutation.modules.vehicle]` entry. `kill_threshold` = `vehicle` A.1 measured rate; keep `increment_step`, `target_final = 1.00`.
  - **Files**: `pyproject.toml`
  - **Done when**: exactly one `vehicle` key; no `vehicle.` dotted key remains.
  - **Verify**: `grep -cE '\[tool\.quality-gate\.mutation\.modules\.vehicle\.' pyproject.toml` -> `0`; `grep -cE '\[tool\.quality-gate\.mutation\.modules\.vehicle\]' pyproject.toml` -> `1`
  - **Commit**: `chore(mutation-score-ramp): collapse vehicle.* keys to top-level vehicle`
  - _Requirements: US-2, FR-5, AC-2.2_

- [x] 1.12 Add `const`/`frontend` keys if the analyzer emits them (A.2)
  - **Do**: From the A.1 emitted-module set (task 1.5): for every analyzer-emitted module lacking a pyproject key (expected `const`, `frontend`), add a `[tool.quality-gate.mutation.modules.<name>]` entry with `kill_threshold` = that module's A.1 measured rate, `increment_step = 0.01`, `target_final = 1.00`. If the analyzer does NOT emit `const`/`frontend`, do not add them — record that in `.progress.md`.
  - **Files**: `pyproject.toml`, `specs/mutation-score-ramp/.progress.md`
  - **Done when**: every A.1-emitted module has exactly one pyproject key.
  - **Verify**: `make mutation-gate 2>&1 | grep -iE 'no threshold|fallback|global_kill_threshold' && echo FALLBACK_PRESENT || echo NO_FALLBACK` — expect `NO_FALLBACK`.
  - **Commit**: `chore(mutation-score-ramp): add const/frontend mutation keys per A.1 emitted set`
  - _Requirements: US-2, FR-6, AC-2.3_

- [x] 1.13 [VERIFY] Verify 1:1 module<->key correspondence and no orphan keys (A.2)
  - **Do**: Cross-check the A.1 emitted-module set against all `[tool.quality-gate.mutation.modules.*]` keys: every emitted module has exactly one key; every key matches an emitted module (no orphans). Run `make mutation-gate` and confirm each module is reported against its own threshold (no silent `global_kill_threshold` fallback).
  - **Files**: (none — verification only)
  - **Done when**: 1:1 correspondence confirmed; gate reports every module against its own threshold.
  - **Verify**: `make mutation-gate 2>&1 | grep -ciE 'orphan|unmatched|no threshold' ` -> `0`
  - **Commit**: `chore(mutation-score-ramp): verify 1:1 mutation key correspondence`
  - _Requirements: US-2, FR-6, AC-2.3, AC-2.4_

- [x] 1.14 Commit the module-name <-> pyproject-key <-> source-path mapping table (A.2)
  - **Do**: Append the authoritative mapping table (analyzer-emitted module name <-> pyproject key <-> source path, from design.md A.2 reconciled with the A.1 emitted set) to `.progress.md` so future renames stay consistent.
  - **Files**: `specs/mutation-score-ramp/.progress.md`
  - **Done when**: mapping table present in `.progress.md`, reconciled with A.1.
  - **Verify**: `grep -q 'Analyzer-emitted module' specs/mutation-score-ramp/.progress.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): commit module/key/path mapping table`
  - _Requirements: US-2, FR-13, AC-2.5_

- [x] 1.15 [VERIFY] Quality checkpoint: lint + import-check after config rebase
  - **Do**: Run `make lint` and `make import-check`; confirm both clean after the pyproject edits.
  - **Files**: (none — verification only)
  - **Done when**: both commands exit 0.
  - **Verify**: `make lint && make import-check && echo CHECKPOINT_PASS`
  - **Commit**: `chore(mutation-score-ramp): pass quality checkpoint after config rebase` (only if fixes needed)
  - _Requirements: NFR-6_

- [ ] 1.16 Log What & Why for the `__init__` gate-fix iteration (NFR-7)
  - **Do**: Create/append `chat.md`: one-line What & Why for fixing `__init__` to its existing threshold (`__init__` 51 — confirm exact value from A.1) via honest tests.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for the `__init__` fix.
  - **Verify**: `grep -qi '__init__' specs/mutation-score-ramp/chat.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): log what&why for __init__ gate fix`
  - _Requirements: NFR-7_

- [ ] 1.17 Strengthen/add honest tests for `__init__` survivors to meet its existing threshold (A.3)
  - **Do**:
    1. Targeted run: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.__init__.*"`.
    2. Enumerate survivors: `mutmut results --all true | grep '__init__' | grep ': survived'`.
    3. Classify each (weak/missing test vs untestable structure); strengthen weak tests, add new tests, dedupe, or replace weak tests so `__init__` measured rate reaches/exceeds its EXISTING threshold. NO threshold lowered. NFR-1: no skip/pragma to dodge mutants.
  - **Files**: `tests/unit/**`, `tests/integration/**` (files chosen per `__init__` survivors)
  - **Done when**: honest tests written; targeted re-run shows `__init__` >= existing threshold.
  - **Verify**: `make test` exits 0 (full confirmation in 1.18).
  - **Commit**: `test(mutation-score-ramp): strengthen __init__ tests to meet gate threshold`
  - _Requirements: US-3, FR-7, AC-3.1, NFR-1, NFR-2_

- [ ] 1.18 [VERIFY] Confirm `__init__` meets threshold via targeted mutmut + test/cover green (A.3)
  - **Do**: Re-run `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.__init__.*"`; confirm `__init__` kill rate >= its existing threshold. Run `make test` and `make test-cover` — both green at 100% coverage.
  - **Files**: (none — verification only)
  - **Done when**: `__init__` >= threshold; `make test` + `make test-cover` exit 0.
  - **Verify**: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.__init__.*" && make test-cover && echo INIT_FIX_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify __init__ meets gate threshold`
  - _Requirements: US-3, FR-7, AC-3.1, AC-3.2, NFR-3_

- [ ] 1.19 Log What & Why for the `trip` gate-fix iteration (NFR-7)
  - **Do**: Append `chat.md`: one-line What & Why for fixing `trip` to its existing threshold (`trip` 48 — confirm from A.1) via honest tests.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for the `trip` fix.
  - **Verify**: `grep -qi 'trip' specs/mutation-score-ramp/chat.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): log what&why for trip gate fix`
  - _Requirements: NFR-7_

- [ ] 1.20 Strengthen/add honest tests for `trip` survivors to meet its existing threshold (A.3)
  - **Do**:
    1. Targeted run: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.trip.*"`.
    2. Enumerate `trip` survivors; classify; strengthen/add/dedupe/replace honest tests so `trip` measured rate reaches/exceeds its EXISTING threshold. If a survivor's logic is genuinely untestable due to structure, apply a US-5 testability refactor (justify in `chat.md`, naming the mutant). NO threshold lowered; NFR-1 no skip/pragma.
  - **Files**: `tests/unit/**`, `tests/integration/**`, `custom_components/ev_trip_planner/trip/**` (only if US-5 refactor needed)
  - **Done when**: honest tests written; targeted re-run shows `trip` >= existing threshold.
  - **Verify**: `make test` exits 0 (full confirmation in 1.21).
  - **Commit**: `test(mutation-score-ramp): strengthen trip tests to meet gate threshold`
  - _Requirements: US-3, FR-7, AC-3.1, US-5, NFR-1, NFR-2, NFR-6_

- [ ] 1.21 [VERIFY] Confirm `trip` meets threshold via targeted mutmut + test/cover + import-check (A.3)
  - **Do**: Re-run targeted mutmut on `trip`; confirm rate >= existing threshold. Run `make test`, `make test-cover`, and `make import-check` (in case a US-5 refactor touched `trip/`).
  - **Files**: (none — verification only)
  - **Done when**: `trip` >= threshold; test, test-cover, import-check all exit 0.
  - **Verify**: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.trip.*" && make test-cover && make import-check && echo TRIP_FIX_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify trip meets gate threshold`
  - _Requirements: US-3, FR-7, AC-3.1, AC-3.2, NFR-3, NFR-6_

- [ ] 1.22 Log What & Why for the `utils` gate-fix iteration (NFR-7)
  - **Do**: Append `chat.md`: one-line What & Why for fixing `utils` to its existing threshold (`utils` 89 — confirm from A.1) via honest tests.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for the `utils` fix.
  - **Verify**: `grep -qi 'utils' specs/mutation-score-ramp/chat.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): log what&why for utils gate fix`
  - _Requirements: NFR-7_

- [ ] 1.23 Strengthen/add honest tests for `utils` survivors to meet its existing threshold (A.3)
  - **Do**:
    1. Targeted run: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.utils.*"`.
    2. Enumerate `utils` survivors; classify; strengthen/add/dedupe/replace honest tests so `utils` measured rate reaches/exceeds its EXISTING threshold. NO threshold lowered; NFR-1 no skip/pragma.
  - **Files**: `tests/unit/**`, `tests/integration/**` (files chosen per `utils` survivors)
  - **Done when**: honest tests written; targeted re-run shows `utils` >= existing threshold.
  - **Verify**: `make test` exits 0 (full confirmation in 1.24).
  - **Commit**: `test(mutation-score-ramp): strengthen utils tests to meet gate threshold`
  - _Requirements: US-3, FR-7, AC-3.1, NFR-1, NFR-2_

- [ ] 1.24 [VERIFY] Confirm `utils` meets threshold via targeted mutmut + test/cover green (A.3)
  - **Do**: Re-run targeted mutmut on `utils`; confirm rate >= existing threshold. Run `make test` and `make test-cover`.
  - **Files**: (none — verification only)
  - **Done when**: `utils` >= threshold; test + test-cover exit 0.
  - **Verify**: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.utils.*" && make test-cover && echo UTILS_FIX_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify utils meets gate threshold`
  - _Requirements: US-3, FR-7, AC-3.1, AC-3.2, NFR-3_

- [ ] 1.25 [VERIFY] End-of-Phase-A gate checkpoint: full `make mutation` + `make mutation-gate` == OK
  - **Do**:
    1. Run a full `make mutation` (~10 min, 583 s baseline) so the cache reflects all Phase-A test additions.
    2. Run `make mutation-gate` — MUST report `RESULT: OK` and exit 0 with no threshold lowered and no code excluded.
    3. Verify NFR-2 via `git diff` of `pyproject.toml` `[tool.mutmut]` + `[tool.quality-gate.mutation]` — confirm no `kill_threshold` was decreased.
    4. Append overall-rate row to the `.progress.md` delta table.
  - **Files**: `specs/mutation-score-ramp/.progress.md`
  - **Done when**: `make mutation-gate` == OK, exit 0; no threshold lowered.
  - **Verify**: `make mutation && make mutation-gate 2>&1 | grep -E 'RESULT:.*OK' && git diff pyproject.toml | grep -E '^-.*kill_threshold' && echo THRESHOLD_LOWERED || echo PHASE_A_GATE_OK`
  - **Commit**: `chore(mutation-score-ramp): lock mutation gate green at end of Phase A`
  - _Requirements: US-3, FR-8, AC-3.2, AC-3.3, NFR-2_

---

## Phase 2: Worst-first ramp to 100% (Phase B)

Focus: ramp every remaining module worst-first to a 100% kill rate through honest test improvement + US-5 testability refactors, ratcheting each module's `kill_threshold` toward `1.00`.

**ITERATION-MILESTONE — task 2.0 is the per-iteration task template.** The executor instantiates one iteration block per module in worst-first order (ascending by A.1 measured kill rate). The blocks below (2.1.x .. 2.11.x) are the *planned* set for the modules in design.md's expected ordering. **The count is unbounded** — after the planned set, if `make mutation-gate` shows ANY module < 100%, the executor MUST add further iteration blocks (2.12.x, 2.13.x, ...) following template 2.0 until every module is at 100%.

### 2.0 Per-iteration task template (instantiate per module, worst-first)

Each module's ramp iteration `2.<N>` expands into this fixed sub-task sequence. `<M>` = the module name; `<glob>` = `"custom_components.ev_trip_planner.<M>.*"`.

- `2.<N>.1` **Log What & Why** (NFR-7) — append one-line What & Why for module `<M>` to `chat.md` BEFORE any measure/improve step. Commit `docs(mutation-score-ramp): log what&why for <M> ramp iteration`.
- `2.<N>.2` **Measure + classify** — targeted `.venv/bin/mutmut run --max-children=4 <glob>`; enumerate survivors via `mutmut results --all true | grep '<M>' | grep ': survived'`; classify each survivor per design Testability-refactor table (weak/missing test -> stronger test; structure untestable -> US-5 refactor; intrinsic/equivalent -> route to 2.0-ADJ). Record the survivor list + classification in `chat.md`. Commit `chore(mutation-score-ramp): enumerate + classify <M> survivors`.
- `2.<N>.3` **Improve** (implementation) — strengthen weak tests / dedupe / add new tests / replace weak tests; OR apply a US-5 testability refactor (API-preserving, justified in `chat.md` naming the mutant, import-linter-safe). NFR-1: no skip/pragma/`mutmut_skip`/suppressive `-k`. Commit `test(mutation-score-ramp): improve <M> tests to kill survivors` (or `refactor(...)` if US-5).
- `2.<N>.4` **[VERIFY] Re-measure** (qa-engineer) — re-run `.venv/bin/mutmut run --max-children=4 <glob>`; confirm `<M>` kill rate strictly increased vs entry (or == 100%). Commit `chore(mutation-score-ramp): verify <M> kill rate improved`.
- `2.<N>.5` **[VERIFY] Regression guard** (qa-engineer) — `make test` && `make test-cover` (`--cov-fail-under=100`) && `make import-check` all exit 0 (NFR-3, NFR-6). Commit `chore(mutation-score-ramp): verify <M> regression guard green`.
- `2.<N>.6` **Ratchet + log delta** — set `<M>` `kill_threshold = min(measured_rate, 1.00)` in `pyproject.toml` (never down — NFR-2); append the per-iteration delta row to the `.progress.md` delta table. Commit `chore(mutation-score-ramp): ratchet <M> threshold + log delta row`.

If a survivor in 2.<N>.3 resists both stronger tests and a US-5 refactor, invoke the **2.0-ADJ adjudication sub-procedure** below before declaring it unkillable.

### 2.0-ADJ NFR-1 adjudication sub-procedure (invoke only when a survivor resists tests + US-5 refactor)

Invoked inline within a `2.<N>.3` improve task. NOT a standalone numbered task — it is a mandatory procedure. Steps:
1. Confirm US-5 testability refactor was attempted FIRST and exhausted (mandatory precondition).
2. Capture mutant id, `mutmut show <id>` (original + mutated line), `mutmut tests-for-mutant <id>`, and the executor's argument for why it is intrinsic/equivalent.
3. Spawn **two independent expert subagents** (blinded — each gets the mutant in isolation, not the other's verdict). Each returns verdict + reasoning.
4. **Both must independently APPROVE.** Any REJECT -> back to US-5 refactor or a stronger test; do NOT add a comment.
5. On dual-APPROVE only: add a `# pragma: no mutate` to that exact source line, and log the mutant identity, both subagent names, both verdicts, and the reasoning to `chat.md` AND `.progress.md`.
6. A survivor caused by bad architectural design is NOT eligible — it MUST be refactored.
The adjudicated set must be minimized; if it grows large, escalate for a scope decision.

### Planned iteration blocks (worst-first; expected order — exact order fixed by A.1)

> Worst-first ordering from design B.1 (expected, A.1-confirmed): `config_flow` -> `panel` -> `services` -> `sensor` -> `coordinator` -> `presence_monitor` -> `emhass` -> `trip` -> `vehicle` -> `calculations` -> `diagnostics`/`definitions`/`yaml_trip_storage`. The executor reorders per the A.1 authoritative baseline if it differs and adds blocks for any module not listed here.

- [ ] 2.1.1 [Iteration 1: config_flow] Log What & Why (NFR-7)
  - **Do**: Append one-line What & Why for `config_flow` ramp iteration to `chat.md` before measuring.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for `config_flow`.
  - **Verify**: `grep -qi 'config_flow' specs/mutation-score-ramp/chat.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): log what&why for config_flow ramp iteration`
  - _Requirements: NFR-7_

- [ ] 2.1.2 [Iteration 1: config_flow] Measure + classify survivors
  - **Do**: Targeted `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.config_flow.*"`; enumerate survivors; classify each (stronger test / US-5 refactor / 2.0-ADJ candidate); record list + classification in `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: classified survivor list recorded.
  - **Verify**: `.venv/bin/mutmut results --all true | grep 'config_flow' | grep -c ': survived'` — count recorded in chat.md.
  - **Commit**: `chore(mutation-score-ramp): enumerate + classify config_flow survivors`
  - _Requirements: US-4, AC-4.3_

- [ ] 2.1.3 [Iteration 1: config_flow] Improve tests / US-5 refactor to kill survivors
  - **Do**: Strengthen/dedupe/add/replace honest tests for `config_flow` survivors; apply API-preserving US-5 testability refactor where structure makes logic untestable (justify in `chat.md` naming the mutant). NFR-1: no skip/pragma. For any survivor resisting both, invoke 2.0-ADJ. Target: drive `config_flow` toward 100%.
  - **Files**: `tests/unit/**`, `tests/integration/**`, `custom_components/ev_trip_planner/config_flow/**` (US-5 only)
  - **Done when**: improvements written; survivors addressed (killed or 2.0-ADJ-adjudicated).
  - **Verify**: `make test` exits 0 (full re-measure in 2.1.4).
  - **Commit**: `test(mutation-score-ramp): improve config_flow tests to kill survivors`
  - _Requirements: US-4, US-5, AC-4.3, NFR-1, NFR-2, NFR-6_

- [ ] 2.1.4 [VERIFY] [Iteration 1: config_flow] Re-measure — kill rate strictly increased
  - **Do**: Re-run targeted mutmut on `config_flow`; confirm kill rate strictly greater than iteration entry (or == 100%).
  - **Files**: (none — verification only)
  - **Done when**: `config_flow` measured rate strictly up vs entry.
  - **Verify**: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.config_flow.*" && echo CONFIG_FLOW_REMEASURE_DONE`
  - **Commit**: `chore(mutation-score-ramp): verify config_flow kill rate improved`
  - _Requirements: US-4, AC-4.2_

- [ ] 2.1.5 [VERIFY] [Iteration 1: config_flow] Regression guard — test + cover + import-check
  - **Do**: Run `make test`, `make test-cover` (`--cov-fail-under=100`), `make import-check` — all exit 0.
  - **Files**: (none — verification only)
  - **Done when**: all three exit 0.
  - **Verify**: `make test && make test-cover && make import-check && echo CONFIG_FLOW_GUARD_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify config_flow regression guard green`
  - _Requirements: US-4, AC-4.6, NFR-3, NFR-6_

- [ ] 2.1.6 [Iteration 1: config_flow] Ratchet threshold + log delta row
  - **Do**: Set `config_flow` `kill_threshold = min(measured_rate, 1.00)` in `pyproject.toml` (never down); append the per-iteration delta row to the `.progress.md` delta table.
  - **Files**: `pyproject.toml`, `specs/mutation-score-ramp/.progress.md`
  - **Done when**: threshold ratcheted up; delta row appended.
  - **Verify**: `grep -A2 'config_flow' pyproject.toml | grep kill_threshold && echo RATCHET_DONE`
  - **Commit**: `chore(mutation-score-ramp): ratchet config_flow threshold + log delta row`
  - _Requirements: US-4, FR-10, AC-4.5, NFR-2_

- [ ] 2.2.1 [Iteration 2: panel] Log What & Why (NFR-7)
  - **Do**: Append one-line What & Why for `panel` ramp iteration to `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for `panel`.
  - **Verify**: `grep -qi 'panel' specs/mutation-score-ramp/chat.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): log what&why for panel ramp iteration`
  - _Requirements: NFR-7_

- [ ] 2.2.2 [Iteration 2: panel] Measure + classify survivors
  - **Do**: Targeted mutmut on `panel`; enumerate + classify survivors (note: panel registration is HA framework glue — design decision #3 says it is NOT auto-unkillable; prefer US-5 refactor to expose logic). Record in `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: classified survivor list recorded.
  - **Verify**: `.venv/bin/mutmut results --all true | grep 'panel' | grep -c ': survived'` — recorded.
  - **Commit**: `chore(mutation-score-ramp): enumerate + classify panel survivors`
  - _Requirements: US-4, AC-4.3_

- [ ] 2.2.3 [Iteration 2: panel] Improve tests / US-5 refactor to kill survivors
  - **Do**: Strengthen/add honest tests; US-5-refactor HA-glue logic into directly-callable pure helpers where needed (API-preserving, justified in `chat.md`); 2.0-ADJ for genuine intrinsic mutants only. NFR-1: no skip/pragma.
  - **Files**: `tests/unit/**`, `tests/integration/**`, `custom_components/ev_trip_planner/panel.py` (US-5 only)
  - **Done when**: survivors addressed.
  - **Verify**: `make test` exits 0.
  - **Commit**: `test(mutation-score-ramp): improve panel tests to kill survivors`
  - _Requirements: US-4, US-5, AC-4.3, NFR-1, NFR-2, NFR-6_

- [ ] 2.2.4 [VERIFY] [Iteration 2: panel] Re-measure — kill rate strictly increased
  - **Do**: Re-run targeted mutmut on `panel`; confirm rate strictly up vs entry.
  - **Files**: (none — verification only)
  - **Done when**: `panel` rate strictly up.
  - **Verify**: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.panel.*" && echo PANEL_REMEASURE_DONE`
  - **Commit**: `chore(mutation-score-ramp): verify panel kill rate improved`
  - _Requirements: US-4, AC-4.2_

- [ ] 2.2.5 [VERIFY] [Iteration 2: panel] Regression guard — test + cover + import-check
  - **Do**: Run `make test`, `make test-cover`, `make import-check` — all exit 0.
  - **Files**: (none — verification only)
  - **Done when**: all three exit 0.
  - **Verify**: `make test && make test-cover && make import-check && echo PANEL_GUARD_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify panel regression guard green`
  - _Requirements: US-4, AC-4.6, NFR-3, NFR-6_

- [ ] 2.2.6 [Iteration 2: panel] Ratchet threshold + log delta row
  - **Do**: Ratchet `panel` `kill_threshold` up to `min(measured_rate, 1.00)`; append delta row to `.progress.md`.
  - **Files**: `pyproject.toml`, `specs/mutation-score-ramp/.progress.md`
  - **Done when**: threshold ratcheted; delta row appended.
  - **Verify**: `grep -A2 'panel' pyproject.toml | grep kill_threshold && echo RATCHET_DONE`
  - **Commit**: `chore(mutation-score-ramp): ratchet panel threshold + log delta row`
  - _Requirements: US-4, FR-10, AC-4.5, NFR-2_

- [ ] 2.3.1 [Iteration 3: services] Log What & Why (NFR-7)
  - **Do**: Append one-line What & Why for `services` ramp iteration to `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for `services`.
  - **Verify**: `grep -qi 'services' specs/mutation-score-ramp/chat.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): log what&why for services ramp iteration`
  - _Requirements: NFR-7_

- [ ] 2.3.2 [Iteration 3: services] Measure + classify survivors
  - **Do**: Targeted mutmut on `services` (largest survivor count — closure-based handler factories, voluptuous schemas); enumerate + classify; record in `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: classified survivor list recorded.
  - **Verify**: `.venv/bin/mutmut results --all true | grep 'services' | grep -c ': survived'` — recorded.
  - **Commit**: `chore(mutation-score-ramp): enumerate + classify services survivors`
  - _Requirements: US-4, AC-4.3_

- [ ] 2.3.3 [Iteration 3: services] Improve tests / US-5 refactor to kill survivors
  - **Do**: Add assertion-heavy honest tests on handler return values for mutated inputs; US-5-refactor closure captures into directly-callable helpers where needed (API-preserving, import-linter-safe, justified in `chat.md`); 2.0-ADJ only for genuine intrinsic mutants. NFR-1: no skip/pragma.
  - **Files**: `tests/unit/**`, `tests/integration/**`, `custom_components/ev_trip_planner/services/**` (US-5 only)
  - **Done when**: survivors addressed.
  - **Verify**: `make test` exits 0.
  - **Commit**: `test(mutation-score-ramp): improve services tests to kill survivors`
  - _Requirements: US-4, US-5, AC-4.3, NFR-1, NFR-2, NFR-6_

- [ ] 2.3.4 [VERIFY] [Iteration 3: services] Re-measure — kill rate strictly increased
  - **Do**: Re-run targeted mutmut on `services`; confirm rate strictly up vs entry.
  - **Files**: (none — verification only)
  - **Done when**: `services` rate strictly up.
  - **Verify**: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.services.*" && echo SERVICES_REMEASURE_DONE`
  - **Commit**: `chore(mutation-score-ramp): verify services kill rate improved`
  - _Requirements: US-4, AC-4.2_

- [ ] 2.3.5 [VERIFY] [Iteration 3: services] Regression guard — test + cover + import-check
  - **Do**: Run `make test`, `make test-cover`, `make import-check` — all exit 0.
  - **Files**: (none — verification only)
  - **Done when**: all three exit 0.
  - **Verify**: `make test && make test-cover && make import-check && echo SERVICES_GUARD_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify services regression guard green`
  - _Requirements: US-4, AC-4.6, NFR-3, NFR-6_

- [ ] 2.3.6 [Iteration 3: services] Ratchet threshold + log delta row
  - **Do**: Ratchet `services` `kill_threshold` up to `min(measured_rate, 1.00)`; append delta row to `.progress.md`.
  - **Files**: `pyproject.toml`, `specs/mutation-score-ramp/.progress.md`
  - **Done when**: threshold ratcheted; delta row appended.
  - **Verify**: `grep -A2 'services' pyproject.toml | grep kill_threshold && echo RATCHET_DONE`
  - **Commit**: `chore(mutation-score-ramp): ratchet services threshold + log delta row`
  - _Requirements: US-4, FR-10, AC-4.5, NFR-2_

- [ ] 2.3.7 [VERIFY] Gate checkpoint #1 (after 3 iterations): full `make mutation` + `make mutation-gate`
  - **Do**:
    1. Run full `make mutation` (~10 min, 583 s baseline) so the cache reflects iterations 1-3.
    2. Run `make mutation-gate`; confirm it exits without traceback and reports the new overall rate.
    3. Append the overall-rate row to the `.progress.md` delta table; confirm overall rate is monotonically non-decreasing vs the previous full-run row.
    4. Confirm `git diff` of pyproject shows no `kill_threshold` decreased (NFR-2).
  - **Files**: `specs/mutation-score-ramp/.progress.md`
  - **Done when**: full run done; overall rate recorded; monotonic increase confirmed; no threshold lowered.
  - **Verify**: `make mutation && make mutation-gate 2>&1 | grep -E 'RESULT:' && git diff pyproject.toml | grep -E '^-.*kill_threshold' && echo THRESHOLD_LOWERED || echo CHECKPOINT1_OK`
  - **Commit**: `chore(mutation-score-ramp): gate checkpoint #1 — full run after iterations 1-3`
  - _Requirements: US-4, FR-9, AC-4.2, NFR-2_

- [ ] 2.4.1 [Iteration 4: sensor] Log What & Why (NFR-7)
  - **Do**: Append one-line What & Why for `sensor` ramp iteration to `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for `sensor`.
  - **Verify**: `grep -qi 'sensor' specs/mutation-score-ramp/chat.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): log what&why for sensor ramp iteration`
  - _Requirements: NFR-7_

- [ ] 2.4.2 [Iteration 4: sensor] Measure + classify survivors
  - **Do**: Targeted mutmut on `sensor`; enumerate + classify (HA sensor entity property-value mutations); record in `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: classified survivor list recorded.
  - **Verify**: `.venv/bin/mutmut results --all true | grep 'sensor' | grep -c ': survived'` — recorded.
  - **Commit**: `chore(mutation-score-ramp): enumerate + classify sensor survivors`
  - _Requirements: US-4, AC-4.3_

- [ ] 2.4.3 [Iteration 4: sensor] Improve tests / US-5 refactor to kill survivors
  - **Do**: Add honest tests on sensor state transitions with mutated values; US-5-refactor where needed (justified in `chat.md`); 2.0-ADJ only for genuine intrinsic mutants. NFR-1: no skip/pragma.
  - **Files**: `tests/unit/**`, `tests/integration/**`, `custom_components/ev_trip_planner/sensor/**` (US-5 only)
  - **Done when**: survivors addressed.
  - **Verify**: `make test` exits 0.
  - **Commit**: `test(mutation-score-ramp): improve sensor tests to kill survivors`
  - _Requirements: US-4, US-5, AC-4.3, NFR-1, NFR-2, NFR-6_

- [ ] 2.4.4 [VERIFY] [Iteration 4: sensor] Re-measure — kill rate strictly increased
  - **Do**: Re-run targeted mutmut on `sensor`; confirm rate strictly up vs entry.
  - **Files**: (none — verification only)
  - **Done when**: `sensor` rate strictly up.
  - **Verify**: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.sensor.*" && echo SENSOR_REMEASURE_DONE`
  - **Commit**: `chore(mutation-score-ramp): verify sensor kill rate improved`
  - _Requirements: US-4, AC-4.2_

- [ ] 2.4.5 [VERIFY] [Iteration 4: sensor] Regression guard — test + cover + import-check
  - **Do**: Run `make test`, `make test-cover`, `make import-check` — all exit 0.
  - **Files**: (none — verification only)
  - **Done when**: all three exit 0.
  - **Verify**: `make test && make test-cover && make import-check && echo SENSOR_GUARD_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify sensor regression guard green`
  - _Requirements: US-4, AC-4.6, NFR-3, NFR-6_

- [ ] 2.4.6 [Iteration 4: sensor] Ratchet threshold + log delta row
  - **Do**: Ratchet `sensor` `kill_threshold` up to `min(measured_rate, 1.00)`; append delta row to `.progress.md`.
  - **Files**: `pyproject.toml`, `specs/mutation-score-ramp/.progress.md`
  - **Done when**: threshold ratcheted; delta row appended.
  - **Verify**: `grep -A2 'sensor' pyproject.toml | grep kill_threshold && echo RATCHET_DONE`
  - **Commit**: `chore(mutation-score-ramp): ratchet sensor threshold + log delta row`
  - _Requirements: US-4, FR-10, AC-4.5, NFR-2_

- [ ] 2.5.1 [Iteration 5: coordinator] Log What & Why (NFR-7)
  - **Do**: Append one-line What & Why for `coordinator` ramp iteration to `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for `coordinator`.
  - **Verify**: `grep -qi 'coordinator' specs/mutation-score-ramp/chat.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): log what&why for coordinator ramp iteration`
  - _Requirements: NFR-7_

- [ ] 2.5.2 [Iteration 5: coordinator] Measure + classify survivors
  - **Do**: Targeted mutmut on `coordinator`; enumerate + classify (async patterns, DataUpdateCoordinator base methods — test intermediate state, not just final results); record in `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: classified survivor list recorded.
  - **Verify**: `.venv/bin/mutmut results --all true | grep 'coordinator' | grep -c ': survived'` — recorded.
  - **Commit**: `chore(mutation-score-ramp): enumerate + classify coordinator survivors`
  - _Requirements: US-4, AC-4.3_

- [ ] 2.5.3 [Iteration 5: coordinator] Improve tests / US-5 refactor to kill survivors
  - **Do**: Add honest tests on intermediate async state; US-5-refactor where needed (justified in `chat.md`); 2.0-ADJ only for genuine intrinsic mutants. NFR-1: no skip/pragma.
  - **Files**: `tests/unit/**`, `tests/integration/**`, `custom_components/ev_trip_planner/coordinator.py` (US-5 only)
  - **Done when**: survivors addressed.
  - **Verify**: `make test` exits 0.
  - **Commit**: `test(mutation-score-ramp): improve coordinator tests to kill survivors`
  - _Requirements: US-4, US-5, AC-4.3, NFR-1, NFR-2, NFR-6_

- [ ] 2.5.4 [VERIFY] [Iteration 5: coordinator] Re-measure — kill rate strictly increased
  - **Do**: Re-run targeted mutmut on `coordinator`; confirm rate strictly up vs entry.
  - **Files**: (none — verification only)
  - **Done when**: `coordinator` rate strictly up.
  - **Verify**: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.coordinator.*" && echo COORDINATOR_REMEASURE_DONE`
  - **Commit**: `chore(mutation-score-ramp): verify coordinator kill rate improved`
  - _Requirements: US-4, AC-4.2_

- [ ] 2.5.5 [VERIFY] [Iteration 5: coordinator] Regression guard — test + cover + import-check
  - **Do**: Run `make test`, `make test-cover`, `make import-check` — all exit 0.
  - **Files**: (none — verification only)
  - **Done when**: all three exit 0.
  - **Verify**: `make test && make test-cover && make import-check && echo COORDINATOR_GUARD_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify coordinator regression guard green`
  - _Requirements: US-4, AC-4.6, NFR-3, NFR-6_

- [ ] 2.5.6 [Iteration 5: coordinator] Ratchet threshold + log delta row
  - **Do**: Ratchet `coordinator` `kill_threshold` up to `min(measured_rate, 1.00)`; append delta row to `.progress.md`.
  - **Files**: `pyproject.toml`, `specs/mutation-score-ramp/.progress.md`
  - **Done when**: threshold ratcheted; delta row appended.
  - **Verify**: `grep -A2 'coordinator' pyproject.toml | grep kill_threshold && echo RATCHET_DONE`
  - **Commit**: `chore(mutation-score-ramp): ratchet coordinator threshold + log delta row`
  - _Requirements: US-4, FR-10, AC-4.5, NFR-2_

- [ ] 2.6.1 [Iteration 6: presence_monitor] Log What & Why (NFR-7)
  - **Do**: Append one-line What & Why for `presence_monitor` ramp iteration to `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for `presence_monitor`.
  - **Verify**: `grep -qi 'presence_monitor' specs/mutation-score-ramp/chat.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): log what&why for presence_monitor ramp iteration`
  - _Requirements: NFR-7_

- [ ] 2.6.2 [Iteration 6: presence_monitor] Measure + classify survivors
  - **Do**: Targeted mutmut on `presence_monitor`; enumerate + classify; record in `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: classified survivor list recorded.
  - **Verify**: `.venv/bin/mutmut results --all true | grep 'presence_monitor' | grep -c ': survived'` — recorded.
  - **Commit**: `chore(mutation-score-ramp): enumerate + classify presence_monitor survivors`
  - _Requirements: US-4, AC-4.3_

- [ ] 2.6.3 [Iteration 6: presence_monitor] Improve tests / US-5 refactor to kill survivors
  - **Do**: Strengthen/add honest tests; US-5-refactor where needed (justified in `chat.md`); 2.0-ADJ only for genuine intrinsic mutants. NFR-1: no skip/pragma.
  - **Files**: `tests/unit/**`, `tests/integration/**`, `custom_components/ev_trip_planner/presence_monitor/**` (US-5 only)
  - **Done when**: survivors addressed.
  - **Verify**: `make test` exits 0.
  - **Commit**: `test(mutation-score-ramp): improve presence_monitor tests to kill survivors`
  - _Requirements: US-4, US-5, AC-4.3, NFR-1, NFR-2, NFR-6_

- [ ] 2.6.4 [VERIFY] [Iteration 6: presence_monitor] Re-measure — kill rate strictly increased
  - **Do**: Re-run targeted mutmut on `presence_monitor`; confirm rate strictly up vs entry.
  - **Files**: (none — verification only)
  - **Done when**: `presence_monitor` rate strictly up.
  - **Verify**: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.presence_monitor.*" && echo PRESENCE_REMEASURE_DONE`
  - **Commit**: `chore(mutation-score-ramp): verify presence_monitor kill rate improved`
  - _Requirements: US-4, AC-4.2_

- [ ] 2.6.5 [VERIFY] [Iteration 6: presence_monitor] Regression guard — test + cover + import-check
  - **Do**: Run `make test`, `make test-cover`, `make import-check` — all exit 0.
  - **Files**: (none — verification only)
  - **Done when**: all three exit 0.
  - **Verify**: `make test && make test-cover && make import-check && echo PRESENCE_GUARD_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify presence_monitor regression guard green`
  - _Requirements: US-4, AC-4.6, NFR-3, NFR-6_

- [ ] 2.6.6 [Iteration 6: presence_monitor] Ratchet threshold + log delta row
  - **Do**: Ratchet `presence_monitor` `kill_threshold` up to `min(measured_rate, 1.00)`; append delta row to `.progress.md`.
  - **Files**: `pyproject.toml`, `specs/mutation-score-ramp/.progress.md`
  - **Done when**: threshold ratcheted; delta row appended.
  - **Verify**: `grep -A2 'presence_monitor' pyproject.toml | grep kill_threshold && echo RATCHET_DONE`
  - **Commit**: `chore(mutation-score-ramp): ratchet presence_monitor threshold + log delta row`
  - _Requirements: US-4, FR-10, AC-4.5, NFR-2_

- [ ] 2.6.7 [VERIFY] Gate checkpoint #2 (after 6 iterations): full `make mutation` + `make mutation-gate`
  - **Do**:
    1. Run full `make mutation` (~10 min, 583 s baseline) reflecting iterations 4-6.
    2. Run `make mutation-gate`; record the new overall rate.
    3. Append overall-rate row to the `.progress.md` delta table; confirm monotonic non-decrease vs checkpoint #1.
    4. Confirm `git diff` of pyproject shows no `kill_threshold` decreased (NFR-2).
  - **Files**: `specs/mutation-score-ramp/.progress.md`
  - **Done when**: full run done; overall rate recorded; monotonic increase confirmed; no threshold lowered.
  - **Verify**: `make mutation && make mutation-gate 2>&1 | grep -E 'RESULT:' && git diff pyproject.toml | grep -E '^-.*kill_threshold' && echo THRESHOLD_LOWERED || echo CHECKPOINT2_OK`
  - **Commit**: `chore(mutation-score-ramp): gate checkpoint #2 — full run after iterations 4-6`
  - _Requirements: US-4, FR-9, AC-4.2, NFR-2_

- [ ] 2.7.1 [Iteration 7: emhass] Log What & Why (NFR-7)
  - **Do**: Append one-line What & Why for `emhass` ramp iteration to `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for `emhass`.
  - **Verify**: `grep -qi 'emhass' specs/mutation-score-ramp/chat.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): log what&why for emhass ramp iteration`
  - _Requirements: NFR-7_

- [ ] 2.7.2 [Iteration 7: emhass] Measure + classify survivors
  - **Do**: Targeted mutmut on `emhass`; enumerate + classify; record in `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: classified survivor list recorded.
  - **Verify**: `.venv/bin/mutmut results --all true | grep 'emhass' | grep -c ': survived'` — recorded.
  - **Commit**: `chore(mutation-score-ramp): enumerate + classify emhass survivors`
  - _Requirements: US-4, AC-4.3_

- [ ] 2.7.3 [Iteration 7: emhass] Improve tests / US-5 refactor to kill survivors
  - **Do**: Strengthen/add honest tests; US-5-refactor where needed (justified in `chat.md`, import-linter-safe — `emhass` must not import `services`); 2.0-ADJ only for genuine intrinsic mutants. NFR-1: no skip/pragma.
  - **Files**: `tests/unit/**`, `tests/integration/**`, `custom_components/ev_trip_planner/emhass/**` (US-5 only)
  - **Done when**: survivors addressed.
  - **Verify**: `make test` exits 0.
  - **Commit**: `test(mutation-score-ramp): improve emhass tests to kill survivors`
  - _Requirements: US-4, US-5, AC-4.3, NFR-1, NFR-2, NFR-6_

- [ ] 2.7.4 [VERIFY] [Iteration 7: emhass] Re-measure — kill rate strictly increased
  - **Do**: Re-run targeted mutmut on `emhass`; confirm rate strictly up vs entry.
  - **Files**: (none — verification only)
  - **Done when**: `emhass` rate strictly up.
  - **Verify**: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.emhass.*" && echo EMHASS_REMEASURE_DONE`
  - **Commit**: `chore(mutation-score-ramp): verify emhass kill rate improved`
  - _Requirements: US-4, AC-4.2_

- [ ] 2.7.5 [VERIFY] [Iteration 7: emhass] Regression guard — test + cover + import-check
  - **Do**: Run `make test`, `make test-cover`, `make import-check` — all exit 0.
  - **Files**: (none — verification only)
  - **Done when**: all three exit 0.
  - **Verify**: `make test && make test-cover && make import-check && echo EMHASS_GUARD_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify emhass regression guard green`
  - _Requirements: US-4, AC-4.6, NFR-3, NFR-6_

- [ ] 2.7.6 [Iteration 7: emhass] Ratchet threshold + log delta row
  - **Do**: Ratchet `emhass` `kill_threshold` up to `min(measured_rate, 1.00)`; append delta row to `.progress.md`.
  - **Files**: `pyproject.toml`, `specs/mutation-score-ramp/.progress.md`
  - **Done when**: threshold ratcheted; delta row appended.
  - **Verify**: `grep -A2 'emhass' pyproject.toml | grep kill_threshold && echo RATCHET_DONE`
  - **Commit**: `chore(mutation-score-ramp): ratchet emhass threshold + log delta row`
  - _Requirements: US-4, FR-10, AC-4.5, NFR-2_

- [ ] 2.8.1 [Iteration 8: trip] Log What & Why (NFR-7)
  - **Do**: Append one-line What & Why for `trip` ramp-to-100% iteration to `chat.md` (note: `trip` already met its gate threshold in Phase A 1.20; this iteration ramps it toward 1.00).
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for the `trip` ramp iteration.
  - **Verify**: `grep -ci 'trip' specs/mutation-score-ramp/chat.md` — > previous count.
  - **Commit**: `docs(mutation-score-ramp): log what&why for trip ramp-to-100 iteration`
  - _Requirements: NFR-7_

- [ ] 2.8.2 [Iteration 8: trip] Measure + classify survivors
  - **Do**: Targeted mutmut on `trip`; enumerate remaining survivors + classify; record in `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: classified survivor list recorded.
  - **Verify**: `.venv/bin/mutmut results --all true | grep 'trip' | grep -c ': survived'` — recorded.
  - **Commit**: `chore(mutation-score-ramp): enumerate + classify trip survivors`
  - _Requirements: US-4, AC-4.3_

- [ ] 2.8.3 [Iteration 8: trip] Improve tests / US-5 refactor to kill survivors
  - **Do**: Strengthen/add honest tests on trip SOC/line-item logic; US-5-refactor where needed (justified in `chat.md`, import-linter-safe); 2.0-ADJ only for genuine intrinsic mutants. NFR-1: no skip/pragma.
  - **Files**: `tests/unit/**`, `tests/integration/**`, `custom_components/ev_trip_planner/trip/**` (US-5 only)
  - **Done when**: survivors addressed.
  - **Verify**: `make test` exits 0.
  - **Commit**: `test(mutation-score-ramp): improve trip tests to kill survivors`
  - _Requirements: US-4, US-5, AC-4.3, NFR-1, NFR-2, NFR-6_

- [ ] 2.8.4 [VERIFY] [Iteration 8: trip] Re-measure — kill rate strictly increased
  - **Do**: Re-run targeted mutmut on `trip`; confirm rate strictly up vs entry.
  - **Files**: (none — verification only)
  - **Done when**: `trip` rate strictly up.
  - **Verify**: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.trip.*" && echo TRIP_REMEASURE_DONE`
  - **Commit**: `chore(mutation-score-ramp): verify trip kill rate improved`
  - _Requirements: US-4, AC-4.2_

- [ ] 2.8.5 [VERIFY] [Iteration 8: trip] Regression guard — test + cover + import-check
  - **Do**: Run `make test`, `make test-cover`, `make import-check` — all exit 0.
  - **Files**: (none — verification only)
  - **Done when**: all three exit 0.
  - **Verify**: `make test && make test-cover && make import-check && echo TRIP_GUARD_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify trip regression guard green`
  - _Requirements: US-4, AC-4.6, NFR-3, NFR-6_

- [ ] 2.8.6 [Iteration 8: trip] Ratchet threshold + log delta row
  - **Do**: Ratchet `trip` `kill_threshold` up to `min(measured_rate, 1.00)`; append delta row to `.progress.md`.
  - **Files**: `pyproject.toml`, `specs/mutation-score-ramp/.progress.md`
  - **Done when**: threshold ratcheted; delta row appended.
  - **Verify**: `grep -A2 'trip' pyproject.toml | grep kill_threshold && echo RATCHET_DONE`
  - **Commit**: `chore(mutation-score-ramp): ratchet trip threshold + log delta row`
  - _Requirements: US-4, FR-10, AC-4.5, NFR-2_

- [ ] 2.9.1 [Iteration 9: vehicle] Log What & Why (NFR-7)
  - **Do**: Append one-line What & Why for `vehicle` ramp iteration to `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for `vehicle`.
  - **Verify**: `grep -qi 'vehicle' specs/mutation-score-ramp/chat.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): log what&why for vehicle ramp iteration`
  - _Requirements: NFR-7_

- [ ] 2.9.2 [Iteration 9: vehicle] Measure + classify survivors
  - **Do**: Targeted mutmut on `vehicle`; enumerate + classify; record in `chat.md`. NOTE: do NOT expand the pre-existing `test_vehicle_controller_event` mutmut exclusion (NFR-1).
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: classified survivor list recorded.
  - **Verify**: `.venv/bin/mutmut results --all true | grep 'vehicle' | grep -c ': survived'` — recorded.
  - **Commit**: `chore(mutation-score-ramp): enumerate + classify vehicle survivors`
  - _Requirements: US-4, AC-4.3, NFR-1_

- [ ] 2.9.3 [Iteration 9: vehicle] Improve tests / US-5 refactor to kill survivors
  - **Do**: Strengthen/add honest tests; US-5-refactor where needed (justified in `chat.md`); 2.0-ADJ only for genuine intrinsic mutants. NFR-1: no new skip/pragma; pre-existing `test_vehicle_controller_event` exclusion not expanded.
  - **Files**: `tests/unit/**`, `tests/integration/**`, `custom_components/ev_trip_planner/vehicle/**` (US-5 only)
  - **Done when**: survivors addressed.
  - **Verify**: `make test` exits 0.
  - **Commit**: `test(mutation-score-ramp): improve vehicle tests to kill survivors`
  - _Requirements: US-4, US-5, AC-4.3, NFR-1, NFR-2, NFR-6_

- [ ] 2.9.4 [VERIFY] [Iteration 9: vehicle] Re-measure — kill rate strictly increased
  - **Do**: Re-run targeted mutmut on `vehicle`; confirm rate strictly up vs entry.
  - **Files**: (none — verification only)
  - **Done when**: `vehicle` rate strictly up.
  - **Verify**: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.vehicle.*" && echo VEHICLE_REMEASURE_DONE`
  - **Commit**: `chore(mutation-score-ramp): verify vehicle kill rate improved`
  - _Requirements: US-4, AC-4.2_

- [ ] 2.9.5 [VERIFY] [Iteration 9: vehicle] Regression guard — test + cover + import-check
  - **Do**: Run `make test`, `make test-cover`, `make import-check` — all exit 0.
  - **Files**: (none — verification only)
  - **Done when**: all three exit 0.
  - **Verify**: `make test && make test-cover && make import-check && echo VEHICLE_GUARD_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify vehicle regression guard green`
  - _Requirements: US-4, AC-4.6, NFR-3, NFR-6_

- [ ] 2.9.6 [Iteration 9: vehicle] Ratchet threshold + log delta row
  - **Do**: Ratchet `vehicle` `kill_threshold` up to `min(measured_rate, 1.00)`; append delta row to `.progress.md`.
  - **Files**: `pyproject.toml`, `specs/mutation-score-ramp/.progress.md`
  - **Done when**: threshold ratcheted; delta row appended.
  - **Verify**: `grep -A2 'vehicle' pyproject.toml | grep kill_threshold && echo RATCHET_DONE`
  - **Commit**: `chore(mutation-score-ramp): ratchet vehicle threshold + log delta row`
  - _Requirements: US-4, FR-10, AC-4.5, NFR-2_

- [ ] 2.9.7 [VERIFY] Gate checkpoint #3 (after 9 iterations): full `make mutation` + `make mutation-gate`
  - **Do**:
    1. Run full `make mutation` (~10 min, 583 s baseline) reflecting iterations 7-9.
    2. Run `make mutation-gate`; record the new overall rate.
    3. Append overall-rate row to the `.progress.md` delta table; confirm monotonic non-decrease vs checkpoint #2.
    4. Confirm `git diff` of pyproject shows no `kill_threshold` decreased (NFR-2).
  - **Files**: `specs/mutation-score-ramp/.progress.md`
  - **Done when**: full run done; overall rate recorded; monotonic increase confirmed; no threshold lowered.
  - **Verify**: `make mutation && make mutation-gate 2>&1 | grep -E 'RESULT:' && git diff pyproject.toml | grep -E '^-.*kill_threshold' && echo THRESHOLD_LOWERED || echo CHECKPOINT3_OK`
  - **Commit**: `chore(mutation-score-ramp): gate checkpoint #3 — full run after iterations 7-9`
  - _Requirements: US-4, FR-9, AC-4.2, NFR-2_

- [ ] 2.10.1 [Iteration 10: calculations] Log What & Why (NFR-7)
  - **Do**: Append one-line What & Why for `calculations` ramp iteration to `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for `calculations`.
  - **Verify**: `grep -qi 'calculations' specs/mutation-score-ramp/chat.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): log what&why for calculations ramp iteration`
  - _Requirements: NFR-7_

- [ ] 2.10.2 [Iteration 10: calculations] Measure + classify survivors
  - **Do**: Targeted mutmut on `calculations` (pure functions, math-heavy — strongest base); enumerate + classify remaining survivors; record in `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: classified survivor list recorded.
  - **Verify**: `.venv/bin/mutmut results --all true | grep 'calculations' | grep -c ': survived'` — recorded.
  - **Commit**: `chore(mutation-score-ramp): enumerate + classify calculations survivors`
  - _Requirements: US-4, AC-4.3_

- [ ] 2.10.3 [Iteration 10: calculations] Improve tests / US-5 refactor to kill survivors
  - **Do**: Add assertion-heavy honest tests on arithmetic edge cases; US-5-refactor where needed (justified in `chat.md`); 2.0-ADJ only for genuine intrinsic mutants. NFR-1: no skip/pragma.
  - **Files**: `tests/unit/**`, `tests/integration/**`, `custom_components/ev_trip_planner/calculations/**` (US-5 only)
  - **Done when**: survivors addressed.
  - **Verify**: `make test` exits 0.
  - **Commit**: `test(mutation-score-ramp): improve calculations tests to kill survivors`
  - _Requirements: US-4, US-5, AC-4.3, NFR-1, NFR-2, NFR-6_

- [ ] 2.10.4 [VERIFY] [Iteration 10: calculations] Re-measure — kill rate strictly increased
  - **Do**: Re-run targeted mutmut on `calculations`; confirm rate strictly up vs entry.
  - **Files**: (none — verification only)
  - **Done when**: `calculations` rate strictly up.
  - **Verify**: `.venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.calculations.*" && echo CALCULATIONS_REMEASURE_DONE`
  - **Commit**: `chore(mutation-score-ramp): verify calculations kill rate improved`
  - _Requirements: US-4, AC-4.2_

- [ ] 2.10.5 [VERIFY] [Iteration 10: calculations] Regression guard — test + cover + import-check
  - **Do**: Run `make test`, `make test-cover`, `make import-check` — all exit 0.
  - **Files**: (none — verification only)
  - **Done when**: all three exit 0.
  - **Verify**: `make test && make test-cover && make import-check && echo CALCULATIONS_GUARD_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify calculations regression guard green`
  - _Requirements: US-4, AC-4.6, NFR-3, NFR-6_

- [ ] 2.10.6 [Iteration 10: calculations] Ratchet threshold + log delta row
  - **Do**: Ratchet `calculations` `kill_threshold` up to `min(measured_rate, 1.00)`; append delta row to `.progress.md`.
  - **Files**: `pyproject.toml`, `specs/mutation-score-ramp/.progress.md`
  - **Done when**: threshold ratcheted; delta row appended.
  - **Verify**: `grep -A2 'calculations' pyproject.toml | grep kill_threshold && echo RATCHET_DONE`
  - **Commit**: `chore(mutation-score-ramp): ratchet calculations threshold + log delta row`
  - _Requirements: US-4, FR-10, AC-4.5, NFR-2_

- [ ] 2.11.1 [Iteration 11: utils + diagnostics + definitions + yaml_trip_storage] Log What & Why (NFR-7)
  - **Do**: Append one-line What & Why for the final small-module cleanup iteration (`utils`, `diagnostics`, `definitions`, `yaml_trip_storage`, plus `__init__`/`const`/`frontend` if any still <100%) to `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: What & Why line present for the small-module iteration.
  - **Verify**: `grep -qi 'diagnostics' specs/mutation-score-ramp/chat.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): log what&why for small-modules ramp iteration`
  - _Requirements: NFR-7_

- [ ] 2.11.2 [Iteration 11: small modules] Measure + classify survivors
  - **Do**: Targeted mutmut on each of `utils`, `diagnostics`, `definitions`, `yaml_trip_storage` (and `__init__`/`const`/`frontend` if <100%); enumerate + classify all remaining survivors; record in `chat.md`.
  - **Files**: `specs/mutation-score-ramp/chat.md`
  - **Done when**: classified survivor lists recorded for all small modules.
  - **Verify**: `for m in utils diagnostics definitions yaml_trip_storage; do .venv/bin/mutmut results --all true | grep "$m" | grep -c ': survived'; done` — counts recorded.
  - **Commit**: `chore(mutation-score-ramp): enumerate + classify small-module survivors`
  - _Requirements: US-4, AC-4.3_

- [ ] 2.11.3 [Iteration 11: small modules] Improve tests / US-5 refactor to kill survivors
  - **Do**: Strengthen/add honest tests for all remaining small-module survivors; US-5-refactor where needed (justified in `chat.md`); 2.0-ADJ only for genuine intrinsic mutants. NFR-1: no skip/pragma. Goal: every small module reaches 100%.
  - **Files**: `tests/unit/**`, `tests/integration/**`, `custom_components/ev_trip_planner/{utils,diagnostics,definitions,yaml_trip_storage}.py` (US-5 only)
  - **Done when**: survivors addressed.
  - **Verify**: `make test` exits 0.
  - **Commit**: `test(mutation-score-ramp): improve small-module tests to kill survivors`
  - _Requirements: US-4, US-5, AC-4.3, NFR-1, NFR-2, NFR-6_

- [ ] 2.11.4 [VERIFY] [Iteration 11: small modules] Re-measure — every small module at 100%
  - **Do**: Re-run targeted mutmut on each small module; confirm each at 100% kill rate.
  - **Files**: (none — verification only)
  - **Done when**: every small module measured at 100%.
  - **Verify**: `for m in utils diagnostics definitions yaml_trip_storage; do .venv/bin/mutmut run --max-children=4 "custom_components.ev_trip_planner.$m.*"; done && echo SMALL_MODULES_REMEASURE_DONE`
  - **Commit**: `chore(mutation-score-ramp): verify small modules at 100% kill rate`
  - _Requirements: US-4, AC-4.2_

- [ ] 2.11.5 [VERIFY] [Iteration 11: small modules] Regression guard — test + cover + import-check
  - **Do**: Run `make test`, `make test-cover`, `make import-check` — all exit 0.
  - **Files**: (none — verification only)
  - **Done when**: all three exit 0.
  - **Verify**: `make test && make test-cover && make import-check && echo SMALL_MODULES_GUARD_PASS`
  - **Commit**: `chore(mutation-score-ramp): verify small-module regression guard green`
  - _Requirements: US-4, AC-4.6, NFR-3, NFR-6_

- [ ] 2.11.6 [Iteration 11: small modules] Ratchet thresholds to 1.00 + log delta rows
  - **Do**: Set `kill_threshold = 1.00` for `utils`, `diagnostics`, `definitions`, `yaml_trip_storage` (and `__init__`/`const`/`frontend` if at 100%) in `pyproject.toml`; append delta rows to `.progress.md`. NOTE: `definitions` (loose 0.45 today) is explicitly ratcheted to 1.00 per the resolved Unresolved Question.
  - **Files**: `pyproject.toml`, `specs/mutation-score-ramp/.progress.md`
  - **Done when**: small-module thresholds set to 1.00; delta rows appended.
  - **Verify**: `for m in utils diagnostics definitions yaml_trip_storage; do grep -A2 "modules\.$m\]" pyproject.toml | grep 'kill_threshold = 1'; done && echo RATCHET_TO_1_DONE`
  - **Commit**: `chore(mutation-score-ramp): ratchet small-module thresholds to 1.00 + log delta rows`
  - _Requirements: US-4, FR-10, AC-4.5, NFR-2_

- [ ] 2.12 [VERIFY] Unbounded-iteration gate: confirm all modules at 100% or add more iteration blocks
  - **Do**:
    1. Run a full `make mutation` (~10 min, 583 s baseline) + `make mutation-gate`.
    2. Inspect the gate per-module table: if EVERY module's `kill_rate == 1.00`, this gate passes — proceed to Phase 3.
    3. If ANY module is still <100%, the executor MUST add a new iteration block (2.13.x, 2.14.x, ...) for each such module following the 2.0 per-iteration template (log What&Why -> measure+classify -> improve -> [VERIFY] re-measure -> [VERIFY] regression guard -> ratchet+log), then re-run this 2.12 gate. Repeat until all modules are at 100%. (The ramp iteration count is UNBOUNDED — design B / requirements AC-4.2.)
  - **Files**: `specs/mutation-score-ramp/.progress.md`, plus any new iteration-block test/pyproject files as needed
  - **Done when**: `make mutation-gate` shows every per-module `kill_rate == 1.00`.
  - **Verify**: `make mutation && make mutation-gate 2>&1 | tee /tmp/gate.txt | grep -E 'RESULT:.*OK' && ! grep -E 'kill_rate.*0\.[0-9]' /tmp/gate.txt && echo ALL_MODULES_100`
  - **Commit**: `chore(mutation-score-ramp): confirm all modules at 100% kill rate`
  - _Requirements: US-4, FR-9, AC-4.2, AC-4.4_

---

## Phase 3: Final verification & quality gates

Focus: prove overall kill rate == 1.0 with every module threshold at 1.00, finalize the delta + mapping tables, run full local CI, open the PR, verify the AC checklist, and run the Playwright E2E suite as a final regression guard.

- [ ] 3.1 [VERIFY] Final full `make mutation` proves overall rate == 1.0 and gate OK
  - **Do**:
    1. Run a final full `make mutation` (~10 min, 583 s baseline).
    2. Run `make mutation-gate`; confirm `RESULT: OK`, exit 0, overall kill rate JSON `== 1.0`, every module `kill_rate == 1.00` against threshold `1.00`.
    3. Confirm 0 timeouts and `_other` bucket 0.
  - **Files**: (none — verification only)
  - **Done when**: gate OK; overall rate 1.0; every module 1.00; 0 timeouts; `_other` 0.
  - **Verify**: `make mutation && make mutation-gate 2>&1 | grep -E 'RESULT:.*OK' && .venv/bin/mutmut results --all true | grep -c ': timeout' | grep -qx 0 && echo FINAL_GATE_OK`
  - **Commit**: `chore(mutation-score-ramp): final mutation run — 100% kill rate, gate OK`
  - _Requirements: US-4, FR-9, AC-4.4, NFR-5_

- [ ] 3.2 Verify every pyproject module threshold == 1.00 (NFR-2)
  - **Do**: Confirm every `[tool.quality-gate.mutation.modules.*]` entry has `kill_threshold = 1.00`. Confirm via `git diff` that no `kill_threshold` was ever lowered across the whole spec and no source/test was excluded to pass the gate.
  - **Files**: `pyproject.toml`
  - **Done when**: every module `kill_threshold == 1.00`; no threshold ever lowered.
  - **Verify**: `grep -cE 'kill_threshold = 1(\.0+)?$' pyproject.toml` equals the module-key count; `git diff main..HEAD -- pyproject.toml | grep -E '^-.*kill_threshold' | grep -v ' = 1' && echo LOWERED || echo NO_THRESHOLD_LOWERED`
  - **Commit**: `chore(mutation-score-ramp): confirm all module thresholds ratcheted to 1.00`
  - _Requirements: US-4, FR-10, AC-4.5, NFR-2_

- [ ] 3.3 Finalize the per-iteration delta table and mapping table in `.progress.md`
  - **Do**: Complete the per-iteration delta table (baseline row -> every iteration -> final `100.0%` row, monotonic non-decreasing overall rate); confirm the module/key/path mapping table is present and reconciled. Add a `## Reality Check (AFTER)` block recording the final overall rate vs the A.1 baseline.
  - **Files**: `specs/mutation-score-ramp/.progress.md`
  - **Done when**: delta table complete with final 100.0% row; mapping table present; AFTER block written.
  - **Verify**: `grep -q '100.0%' specs/mutation-score-ramp/.progress.md && grep -q 'Reality Check (AFTER)' specs/mutation-score-ramp/.progress.md && echo PASS`
  - **Commit**: `docs(mutation-score-ramp): finalize delta table + mapping table`
  - _Requirements: US-4, FR-11, FR-13, AC-4.4_

- [ ] 3.4 [VERIFY] Verify NFR-1 adjudication log completeness
  - **Do**: For every `# pragma: no mutate` added during the ramp, confirm a matching logged ≥2-expert-subagent dual-APPROVE adjudication exists in `chat.md` AND `.progress.md` (mutant id, both subagent names, both verdicts, reasoning). Confirm no new `mutmut_skip` marker or suppressive `-k` arg was added, and the pre-existing `test_solid_metrics`/`test_vehicle_controller_event` exclusions were not expanded.
  - **Files**: (none — verification only)
  - **Done when**: every pragma traces to a logged adjudication; no un-adjudicated suppression.
  - **Verify**: `N=$(grep -rc 'pragma: no mutate' custom_components/ | awk -F: '{s+=$2} END{print s}'); A=$(grep -c 'ADJUDICATION' specs/mutation-score-ramp/chat.md); [ "$N" -le "$A" ] && echo ADJUDICATION_LOG_OK || echo MISSING_ADJUDICATION`
  - **Commit**: `chore(mutation-score-ramp): verify NFR-1 adjudication log completeness`
  - _Requirements: NFR-1, AC-4.4_

- [ ] 3.5 [VERIFY] V4 — full local CI: lint + import-check + test-cover + mutation-gate
  - **Do**: Run the complete local CI suite: `make lint`, `make import-check`, `make test-cover` (`--cov-fail-under=100`), `make mutation-gate`. All must exit 0. Fix any issue and re-run.
  - **Files**: (none — verification only; fixes committed if needed)
  - **Done when**: all four commands exit 0.
  - **Verify**: `make lint && make import-check && make test-cover && make mutation-gate && echo V4_LOCAL_CI_PASS`
  - **Commit**: `chore(mutation-score-ramp): pass full local CI` (only if fixes needed)
  - _Requirements: NFR-3, NFR-6, FR-8_

- [ ] 3.6 V5 — push branch and open PR
  - **Do**:
    1. Confirm current branch is `mutation-score-ramp` (a feature branch): `git branch --show-current`.
    2. Push: `git push -u origin mutation-score-ramp`.
    3. Open PR with `gh pr create` — title summarizing 100% mutation kill rate + tooling/config hardening; body with the baseline->100% delta summary.
  - **Files**: (none — git/gh operations)
  - **Done when**: PR created against `main`.
  - **Verify**: `gh pr view --json url,state | grep -E 'OPEN' && echo PR_OPEN`
  - **Commit**: None (PR creation, no code change)
  - _Requirements: US-1, US-4_

- [ ] 3.7 [VERIFY] V5b — CI pipeline passes
  - **Do**: Wait for GitHub Actions CI to complete on the PR; confirm all checks green. If a check fails: read details, fix locally, push, re-verify.
  - **Files**: (none — verification only)
  - **Done when**: `gh pr checks` shows all green.
  - **Verify**: `gh pr checks --watch 2>&1 | grep -E 'all checks|pass' && echo CI_GREEN`
  - **Commit**: None
  - _Requirements: US-1_

- [ ] 3.8 [VERIFY] V6 — AC checklist verification
  - **Do**: Programmatically verify every acceptance criterion in `requirements.md` (AC-1.1..AC-1.5, AC-2.1..AC-2.5, AC-3.1..AC-3.3, AC-4.1..AC-4.6, AC-5.1..AC-5.3) is satisfied — by grepping pyproject/code/tests, inspecting the gate output, the delta table, and the adjudication logs. Record a pass/fail line per AC in `.progress.md`.
  - **Files**: `specs/mutation-score-ramp/.progress.md`
  - **Done when**: every AC confirmed met with an automated check.
  - **Verify**: `grep -E 'AC-[0-9]' specs/mutation-score-ramp/.progress.md | grep -c 'PASS'` equals total AC count.
  - **Commit**: `docs(mutation-score-ramp): record AC checklist verification`
  - _Requirements: US-1, US-2, US-3, US-4, US-5_

- [ ] VE0 [VERIFY] E2E selector-map init (ui-map-init)
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session, ha-e2e-testing
  - **Do**: Build the UI selector map for the HA E2E suite per the e2e/ui-map-init skill so subsequent VE tasks have a valid selector map. Note: E2E runs against `hass` directly on port 8123 — NEVER Docker (CLAUDE.md environment separation). Note: Browser Automation may run in degraded mode — qa-engineer emits VERIFICATION_DEGRADED if tooling missing.
  - **Files**: (e2e selector-map artifact only)
  - **Done when**: selector map built and valid; if VE0 fails the executor escalates (cannot run VE1+ without it).
  - **Verify**: selector-map artifact exists and is non-empty.
  - **Commit**: None
  - _Requirements: NFR-6_

- [ ] VE1 [VERIFY] E2E startup — boot HA E2E environment
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session, ha-e2e-testing
  - **Do**: Start the HA E2E environment on port 8123 via the project's E2E runner (`hass` direct, NO Docker). Wait for HA ready with a 60s timeout. This is a final regression guard for a library-type spec — confirms no test/refactor in the ramp broke HA-observable behavior (NFR-6).
  - **Files**: (none — infrastructure)
  - **Done when**: HA E2E instance running and responding on 8123.
  - **Verify**: `for i in $(seq 1 60); do curl -sf http://localhost:8123 >/dev/null && break || sleep 1; done; curl -sf http://localhost:8123 >/dev/null && echo VE1_PASS`
  - **Commit**: None
  - _Requirements: NFR-6_

- [ ] VE2 [VERIFY] E2E check — run the Playwright E2E suite as regression guard
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session, ha-e2e-testing
  - **Do**: Run the project's Playwright E2E suite via `make e2e` (`./scripts/run-e2e.sh`) against the running HA E2E instance. Confirm all E2E specs pass — proving the ramp's test/refactor work did not change HA-observable behavior (entities, services, config flow).
  - **Files**: (none — verification only)
  - **Done when**: full Playwright E2E suite passes.
  - **Verify**: `make e2e 2>&1 | grep -E 'passed|0 failed' && echo VE2_PASS`
  - **Commit**: None
  - _Requirements: NFR-6, AC-5.3_

- [ ] VE3 [VERIFY] E2E cleanup — tear down HA E2E environment
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session, ha-e2e-testing
  - **Do**: Stop the HA E2E instance and free port 8123. Remove the ephemeral E2E config dir `/tmp/ha-e2e-config/` if present. This cleanup MUST always run, even if VE1/VE2 failed.
  - **Files**: (none — infrastructure cleanup)
  - **Done when**: no process on port 8123; ephemeral E2E config removed.
  - **Verify**: `lsof -ti :8123 | xargs -r kill 2>/dev/null; rm -rf /tmp/ha-e2e-config; ! lsof -ti :8123 && echo VE3_PASS`
  - **Commit**: None
  - _Requirements: NFR-6_

---

## Phase 4: PR Lifecycle

Focus: autonomous PR validation loop until all completion criteria are met.

- [ ] 4.1 [VERIFY] Monitor CI and resolve failures
  - **Do**: Poll `gh pr checks` until CI completes. For any failing check: read `gh pr checks` details, reproduce locally, fix, commit, `git push`, re-poll. Repeat until all checks green.
  - **Files**: (iteration-determined — fixes only)
  - **Done when**: all CI checks green on the PR.
  - **Verify**: `gh pr checks 2>&1 | grep -E 'all checks|pass' && echo CI_ALL_GREEN`
  - **Commit**: `fix(mutation-score-ramp): resolve CI failures` (only if fixes needed)
  - _Requirements: US-1_

- [ ] 4.2 [VERIFY] Resolve PR review comments
  - **Do**: Fetch PR review comments (`gh api repos/{owner}/{repo}/pulls/{n}/comments`). Address each actionable comment with a fix; reply or resolve. Push fixes. Re-verify CI stays green.
  - **Files**: (iteration-determined — fixes only)
  - **Done when**: all actionable review comments resolved; CI still green.
  - **Verify**: `gh pr checks 2>&1 | grep -E 'all checks|pass' && echo REVIEW_RESOLVED_CI_GREEN`
  - **Commit**: `fix(mutation-score-ramp): address PR review comments` (only if fixes needed)
  - _Requirements: US-1, US-4_

- [ ] 4.3 [VERIFY] VF — final goal verification: 100% mutation kill rate confirmed
  - **Do**:
    1. Read the A.1 baseline overall rate from `.progress.md` `## Reality Check (BEFORE)`.
    2. Re-run `make mutation` + `make mutation-gate` (final authoritative full run, ~10 min).
    3. Confirm overall kill rate == 1.0, gate `RESULT: OK`, every module threshold 1.00.
    4. Document the AFTER state vs BEFORE in `.progress.md` and confirm zero regressions (`make test-cover` green).
  - **Files**: `specs/mutation-score-ramp/.progress.md`
  - **Done when**: gate OK, overall rate 1.0, every module 1.00, BEFORE/AFTER documented, no regression.
  - **Verify**: `make mutation && make mutation-gate; echo "EXIT=$?"` — expect `RESULT: OK` and `EXIT=0`.
  - **Commit**: `chore(mutation-score-ramp): verify 100% mutation kill rate — spec complete`
  - _Requirements: US-4, FR-9, AC-4.4, NFR-2, NFR-3_

---

## Notes

- **Phase-B iteration count is UNBOUNDED** — tasks 2.1.x..2.11.x are the planned set; task 2.12 is the gate that forces the executor to add 2.13.x+ blocks (per the 2.0 template) for any module still <100%. The spec is NOT done until every module is at 100%.
- **NFR-1 adjudication (2.0-ADJ)** is a procedure, not a numbered task — invoked inline within an `improve` task only after a US-5 refactor is exhausted, requiring ≥2 independent expert-subagent dual-APPROVE, logged.
- **Worst-first order** below is expected from design B.1 — the executor reorders per the A.1 authoritative baseline (task 1.5) if it differs.
- **Full `make mutation` runs** (~10 min / 583 s) occur at: end of Phase A (1.25), gate checkpoints #1/#2/#3 (2.3.7 / 2.6.7 / 2.9.7), the unbounded-iteration gate (2.12), the final verification (3.1), and VF (4.3).
- **No new spec directories** are created. `chat.md` and `.progress.md` live in the existing `specs/mutation-score-ramp/` dir.

## Task count summary

- **Phase 1 (Tooling & Config Hardening)**: 25 tasks (1.1–1.25)
- **Phase 2 (Worst-first ramp to 100%)**: 70 tasks — 11 iteration blocks × 6 sub-tasks = 66, plus 3 embedded gate checkpoints (2.3.7, 2.6.7, 2.9.7), plus the unbounded-iteration gate (2.12).
- **Phase 3 (Final verification & quality gates)**: 12 tasks (3.1–3.8, VE0, VE1, VE2, VE3)
- **Phase 4 (PR Lifecycle)**: 3 tasks (4.1, 4.2, 4.3-VF)
- **TOTAL: 110 tasks** (planned; unbounded — grows if Phase-B modules need extra iteration blocks via task 2.12).
- **Iteration-milestone task**: `2.0` (per-iteration task template). First instantiated iteration block: `2.1.1–2.1.6` (config_flow).
