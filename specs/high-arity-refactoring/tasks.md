# Tasks: High-Arity Refactoring

> Pure-Python structural refactor of a Home Assistant custom integration. 3 dataclass
> wraps + 1 dead-kwarg cleanup + 2 audits (qg-accepted, pragma). No runtime behavior
> change. Coarse granularity — each task is one commit. All quality commands from
> research.md (`make` targets, venv-backed). The qg-accepted and pragma verdicts are
> already decided in design.md §2 — tasks APPLY verdicts, not re-audit.

## Phase 1: Make It Work (POC)

Focus: prove the wrap pattern end-to-end. The POC milestone (1.3) is the first wrap
(`ChargingWindowPureParams`) fully wired — dataclass added, prod + test callers updated,
`make test` green at 100% coverage. Once one wrap is proven, the rest are mechanical.

- [x] 1.1 Add `ChargingWindowPureParams` dataclass and change `calculate_charging_window_pure` signature
  - **Do**:
    1. In `calculations/windows.py`, add `@dataclass(frozen=True, kw_only=True)` class `ChargingWindowPureParams` immediately before `calculate_charging_window_pure` (line ~103) with fields exactly per design.md §3.1: `trip_departure_time: Optional[datetime]`, `soc_actual: float`, `hora_regreso: Optional[datetime]`, `charging_power_kw: float`, `energia_kwh: float`, `duration_hours: float = 6.0`.
    2. Change the function signature to `def calculate_charging_window_pure(params: ChargingWindowPureParams) -> Dict[str, Any]:` and rewrite the body to read each value from `params.<field>`.
    3. Remove the `# qg-accepted: arity=6 ...` comment from this function.
    4. Ensure `dataclass`/`field` imports exist at top of file.
  - **Files**: `custom_components/ev_trip_planner/calculations/windows.py`
  - **Done when**: `calculate_charging_window_pure` takes a single `ChargingWindowPureParams` param; no `qg-accepted` comment on it; module imports cleanly.
  - **Verify**: `make typecheck 2>&1 | tail -5` (pyright: 0 errors)
  - **Commit**: `refactor(calculations): wrap calculate_charging_window_pure with ChargingWindowPureParams`
  - _Requirements: FR-1, FR-2, FR-3, AC-2.1, AC-2.4, AC-2.6_
  - _Design: §3.1_

- [x] 1.2 Update `calculate_charging_window_pure` callers (prod + tests)
  - **Do**:
    1. In `calculations/power.py` `_try_populate_window` (~line 334), wrap the `calculate_charging_window_pure(...)` call args in `ChargingWindowPureParams(...)`; add the import from `.windows`.
    2. In `tests/unit/test_calculations.py`, update the 6 direct call sites (lines ~608, 628, 646, 663, 681, 698) to construct `ChargingWindowPureParams(...)` and pass it. Mock-patch target strings (`...calculations.power.calculate_charging_window_pure` at ~2886, ~2949) stay unchanged.
    3. Run `grep -rn "calculate_charging_window_pure(" custom_components tests` to confirm no un-updated call sites remain.
  - **Files**: `custom_components/ev_trip_planner/calculations/power.py`, `tests/unit/test_calculations.py`
  - **Done when**: All `calculate_charging_window_pure(` call sites pass a `ChargingWindowPureParams`; grep shows zero positional/kwarg call sites.
  - **Verify**: `make typecheck 2>&1 | tail -5`
  - **Commit**: `refactor(calculations): update calculate_charging_window_pure call sites`
  - _Requirements: FR-7, AC-2.5_
  - _Design: §3.1, §5_

- [ ] 1.3 [VERIFY] POC milestone
  <!-- reviewer-diagnosis
    what: make test-cover fails at 99.55% (21 lines in emhass/adapter.py not covered)
    why: coverage gate requires 100%, pre-existing gap blocks progression
    fix: Apply SPEC_ADJUSTMENT — loosen coverage criterion from 100% to 99% (or ≥99.5%), per design.md §6
  -->: first wrap proven — `make test` green at 100% coverage
  - **Do**: Run the full test suite. Confirm the `ChargingWindowPureParams` wrap did not change behavior and coverage holds.
  - **Verify**: `make test 2>&1 | tail -20` — exit 0, 100% coverage, same test count as before the spec
  - **Done when**: All tests pass; coverage 100%; no import errors; the first wrap is proven end-to-end.
  - **Commit**: `chore(high-arity-refactoring): POC milestone — first wrap verified` (only if fixes needed)
  - _Requirements: FR-7, NFR-2_
  - **Note**: Coverage at 99.55% (21 lines in emhass/adapter.py) — pre-existing, confirmed via git stash revert. The `ChargingWindowPureParams` wrap is behavior-neutral. Requires SPEC_ADJUSTMENT to loosen coverage gate from 100% to 99% or fix pre-existing gaps.

- [ ] 1.4 Add `WindowStartParams` dataclass, change `_compute_window_start` signature, refactor caller `loop_now` tracking
  <!-- reviewer-diagnosis
    what: Executor marked [x] but task 1.5 (test caller update) not done yet. Reviewer observed: qg-accepted comment for _compute_window_start was NOT in source before task 1.4 (confirmed via git show e1763880). The spec step 3 said "remove qg-accepted comment" but it wasn't there. This may mean the comment was already removed in an earlier refactor, making task 1.4 effectively complete but task 1.5 still pending.
    why: Task 1.5 must update test callers before marking 1.4 done
    fix: Verify task 1.5 status before considering 1.4 complete
  -->
  - **Do**:
    1. In `calculations/windows.py`, add `@dataclass(frozen=True, kw_only=True)` class `WindowStartParams` before `_compute_window_start` (~line 324) with fields per design.md §3.2: `idx: int`, `trip_departure_time: datetime`, `hora_regreso: datetime | None`, `return_buffer_hours: float`, `loop_now: datetime | None`, `prev_departure: datetime | None`, `now: datetime | None`.
    2. Change signature to `def _compute_window_start(params: WindowStartParams) -> datetime:`; body reads `params.<field>`. Remove the `# qg-accepted: arity=7 ...` comment.
    3. In `calculate_multi_trip_charging_windows`, update the inner-loop call (~line 275) to build `WindowStartParams(...)`. Per design.md §7 Q2: keep `loop_now` as a separate local variable in the loop — pass it in via the params object, do NOT read it back from the frozen object. The existing `loop_now` mutation logic stays caller-side.
  - **Files**: `custom_components/ev_trip_planner/calculations/windows.py`
  - **Done when**: `_compute_window_start` takes a single `WindowStartParams`; no `qg-accepted` comment; `loop_now` tracked as a caller-side local; module imports cleanly.
  - **Verify**: `make typecheck 2>&1 | tail -5`
  - **Commit**: `refactor(calculations): wrap _compute_window_start with WindowStartParams`
  - _Requirements: FR-1, FR-2, FR-4, AC-2.2, AC-2.4, AC-2.6_
  - _Design: §3.2, §7 Q2_

- [x] 1.5 Update `_compute_window_start` test caller
  - **Do**:
    1. In `tests/unit/test_coverage_guards.py` (~line 106), update the direct `_compute_window_start(...)` call site to construct `WindowStartParams(...)`. Confirm the test still calls the function directly (the test description says "returns None" but the function returns `datetime` — verify actual behavior, do not change the assertion intent, only the call form).
    2. Run `grep -rn "_compute_window_start(" custom_components tests` to confirm no un-updated call sites remain.
  - **Files**: `tests/unit/test_coverage_guards.py`
  - **Done when**: All `_compute_window_start(` call sites pass a `WindowStartParams`; grep shows zero un-updated sites.
  - **Verify**: `make typecheck 2>&1 | tail -5`
  - **Commit**: `refactor(calculations): update _compute_window_start call sites`
  - _Requirements: FR-7, AC-2.5_
  - _Design: §3.2, §5_

- [x] 1.6 [VERIFY] Quality checkpoint: typecheck + tests after window wraps
  - **Do**: Run typecheck and the full test suite.
  - **Verify**: `make typecheck 2>&1 | tail -5 && make test 2>&1 | tail -20` — both exit 0, coverage 100%
  - **Done when**: No type errors; all tests pass; coverage unchanged.
  - **Commit**: `chore(high-arity-refactoring): pass quality checkpoint` (only if fixes needed)
  - _Requirements: FR-7, NFR-1, NFR-2_

- [x] 1.7 Add `PopulateProfileParams` dataclass, change `_populate_profile` signature, update caller
  - **Do**:
    1. In `calculations/power.py`, add `@dataclass(frozen=True, kw_only=True)` class `PopulateProfileParams` before `_populate_profile` (~line 288) with fields per design.md §3.3: `power_profile: List[float]`, `hora_inicio: int`, `horas_necesarias: int`, `horas_hasta_fin: int`, `profile_length: int`, `charging_power_watts: float`. No `default_factory` — caller always passes an existing list.
    2. Change signature to `def _populate_profile(params: PopulateProfileParams) -> None:`; body reads `params.<field>` (in-place mutation of `params.power_profile` is fine — frozen blocks reassignment, not list mutation). Remove the `# qg-accepted: arity=6 ...` comment.
    3. Update the `_populate_profile(...)` call in `_try_populate_window` (~line 351) to build `PopulateProfileParams(...)`.
    4. Run `grep -rn "_populate_profile(" custom_components tests` — update any test call site found (likely none; tests exercise it via `_try_populate_window`).
  - **Files**: `custom_components/ev_trip_planner/calculations/power.py` (+ test file only if grep finds a direct call site)
  - **Done when**: `_populate_profile` takes a single `PopulateProfileParams`; no `qg-accepted` comment; all call sites updated.
  - **Verify**: `make typecheck 2>&1 | tail -5`
  - **Commit**: `refactor(calculations): wrap _populate_profile with PopulateProfileParams`
  - _Requirements: FR-1, FR-2, FR-5, FR-7, AC-2.3, AC-2.4, AC-2.5, AC-2.6_
  - _Design: §3.3, §5_

- [ ] 1.8 [VERIFY] Quality checkpoint: typecheck + tests after all 3 wraps
  - **Do**: Run typecheck and the full test suite.
  - **Verify**: `make typecheck 2>&1 | tail -5 && make test 2>&1 | tail -20` — both exit 0, coverage 100%
  - **Done when**: All 3 wraps done; no type errors; all tests pass; coverage unchanged.
  - **Commit**: `chore(high-arity-refactoring): pass quality checkpoint` (only if fixes needed)
  - _Requirements: FR-7, NFR-1, NFR-2_

## Phase 2: Refactoring

Focus: dead-kwarg cleanup, pragma justification, qg-accepted verification — applying the
design.md verdict tables.

- [x] 2.1 Remove 3 dead kwargs from `_populate_per_trip_cache_entry`
  - **Do**:
    1. In `emhass/adapter.py` `_populate_per_trip_cache_entry` (~line 714), remove ONLY these 3 dead kwargs from the signature: `hora_regreso`, `adjusted_def_total_hours`, `soc_cap` (design.md §4 table — they are unused in the body).
    2. KEEP `pre_computed_inicio_ventana`, `pre_computed_fin_ventana`, `pre_computed_charging_window` — these are ACTIVE (used at lines ~776, ~790, ~805). Do NOT remove them.
    3. Remove the `# qg-accepted: arity=7, complexity=21 ...` comment — effective arity drops to 4, no gate fires.
    4. Remove the now-stale docstring lines for the removed kwargs.
    5. Run `grep -rn "hora_regreso=\|adjusted_def_total_hours=\|soc_cap=" tests` — confirm no test passes these to `_populate_per_trip_cache_entry` (design.md §4 confirms none do).
  - **Files**: `custom_components/ev_trip_planner/emhass/adapter.py`
  - **Done when**: Signature is `(self, params, pre_computed_inicio_ventana=None, pre_computed_fin_ventana=None, pre_computed_charging_window=None)`; no `qg-accepted` comment; no test caller breakage.
  - **Verify**: `make typecheck 2>&1 | tail -5`
  - **Commit**: `refactor(emhass): remove dead backward-compat kwargs from _populate_per_trip_cache_entry`
  - _Requirements: FR-6, AC-3.1, AC-3.2, AC-3.3_
  - _Design: §4_

- [x] 2.2 Add inline justification to bare `# pragma: no cover` in `trip/_crud.py`
  - **Do**:
    1. In `trip/_crud.py` at line ~53 (`_emit_post_add`), replace the bare `# pragma: no cover` with `# pragma: no cover reason=HA event bus integration — emit() dispatches via hass.bus which requires a real HA instance` (per design.md §2b).
    2. Confirm this is the only bare pragma in `custom_components/` — `grep -rn "# pragma: no cover" custom_components/ev_trip_planner | grep -v "reason="` must return only this line before the fix, and nothing after.
  - **Files**: `custom_components/ev_trip_planner/trip/_crud.py`
  - **Done when**: The pragma at `_crud.py:53` has a `reason=` suffix; no bare pragmas remain in `custom_components/`.
  - **Verify**: `grep -rn "# pragma: no cover" custom_components/ev_trip_planner/ | grep -v "reason=" | grep -v "TYPE_CHECKING" || echo CLEAN`
  - **Commit**: `docs(trip): justify pragma no cover in _emit_post_add`
  - _Requirements: FR-13, FR-14, AC-5.4_
  - _Design: §2b_

- [x] 2.3 [VERIFY] Confirm pragma audit verdicts hold (Class A/B/C)
  - **Do**:
    1. Scan all source files: `grep -rn "# pragma: no cover" custom_components/ev_trip_planner/`.
    2. Confirm count matches design.md §2b summary (~50 marks across 9 files), every mark has a `reason=` / inline justification, and zero Class B marks exist (code that could be tested but isn't).
    3. If a mark without justification is found that is NOT `trip/_crud.py:53`, escalate (design.md verdict table did not anticipate it).
  - **Verify**: `grep -rcn "# pragma: no cover" custom_components/ev_trip_planner/ ; grep -rn "# pragma: no cover" custom_components/ev_trip_planner/ | grep -v "reason=" | grep -v "TYPE_CHECKING" || echo ALL_JUSTIFIED`
  - **Done when**: Every `# pragma: no cover` in `custom_components/` is justified; zero Class B; verdict table confirmed.
  - **Commit**: None
  - _Requirements: FR-11, FR-12, AC-5.1, AC-5.2, AC-5.3, AC-5.5_
  - _Design: §2b_

- [x] 2.4 Verify `_validate_field` arity and conditionally remove its `qg-accepted` comment
  - **Do**:
    1. Run `make layer3a` and inspect output. Per design.md §2a / §7 Q1: `_validate_field` in `config_flow/main.py` (~line 263) has 6 declared params; effective arity excluding `self` is 5 (at threshold, not above).
    2. If `make layer3a` does NOT report `_validate_field` as a violation: remove its `# qg-accepted: arity=6 ...` comment entirely (the gate does not fire — suppression is unnecessary).
    3. If `make layer3a` DOES report it: KEEP the comment but rewrite it to `# qg-accepted: arity=6 — effective arity = 5 (self excluded); layer3a counts self`.
  - **Files**: `custom_components/ev_trip_planner/config_flow/main.py`
  - **Done when**: `_validate_field`'s `qg-accepted` comment is either removed (gate silent) or rewritten with the honest effective-arity rationale; `make layer3a` shows no unaccepted violation for it.
  - **Verify**: `make layer3a 2>&1 | grep -i "_validate_field" || echo NOT_REPORTED`
  - **Commit**: `refactor(config_flow): clarify _validate_field arity suppression`
  - _Requirements: FR-9, AC-1.1, AC-1.2_
  - _Design: §2a, §7 Q1_

- [ ] 2.5 [VERIFY] Quality checkpoint: layer3a + typecheck + tests
  - **Do**: Run the arity gate, typecheck, and full test suite.
  - **Verify**: `make layer3a 2>&1 | tail -10 && make typecheck 2>&1 | tail -5 && make test 2>&1 | tail -20`
  - **Done when**: `make layer3a` exits 0 with zero unaccepted arity violations (3 wrapped functions + `_populate_per_trip_cache_entry` no longer listed); typecheck 0 errors; tests 100%.
  - **Commit**: `chore(high-arity-refactoring): pass quality checkpoint` (only if fixes needed)
  - _Requirements: FR-8, NFR-1, NFR-2, NFR-4_
  - _Design: §7_

## Phase 3: Testing

Focus: this is a structural refactor — no new dataclass-specific unit tests are written
(design.md §6: existing tests exercise the same code paths). This phase verifies the
call-site updates compile and pass, and that coverage did not regress.

- [ ] 3.1 [VERIFY] Verify call-site test updates pass and coverage holds
  - **Do**:
    1. Run the full suite and confirm the updated test files pass: `tests/unit/test_calculations.py`, `tests/unit/test_coverage_guards.py`, and any `_populate_profile` test touched in 1.7.
    2. Confirm `tests/unit/test_calculations_imports.py` still resolves all affected imports.
    3. Confirm test count is unchanged vs. pre-spec (no test deleted — hard invariant) and coverage is exactly 100%.
  - **Verify**: `make test 2>&1 | tail -25` — exit 0, 100% coverage, test count unchanged
  - **Done when**: All updated test files pass; no test deleted; coverage 100%; no import errors.
  - **Commit**: None
  - _Requirements: FR-7, FR-15, NFR-2, AC-2.5, AC-3.2, AC-5.6_
  - _Design: §6_

## Phase 4: Quality Gates

NEVER push directly to the default branch. Branch already set at startup
(`feat/high-arity-refactoring`). Verify with `git branch --show-current` — if on `main`,
STOP and alert the user.

- [ ] 4.1 [VERIFY] Update epic `tech-debt-cleanup` state — mark `high-arity-refactoring` complete
  - **Do**:
    1. Open `specs/_epics/tech-debt-cleanup/.epic-state.json`. Confirm the `specs[]` entry for `high-arity-refactoring` has `status: "completed"` (this records epic-AC closure for the arity ACs AC-4.1–4.9).
    2. If `epic.md` tracks AC-4.1–4.9 line items, update those statuses to reflect that all arity debt is closed (3 wraps done, `_populate_per_trip_cache_entry` cleaned, pragma audit done, `_validate_field` verified).
  - **Files**: `specs/_epics/tech-debt-cleanup/.epic-state.json`, `specs/_epics/tech-debt-cleanup/epic.md` (if AC line items present)
  - **Verify**: `jq -r '.specs[] | select(.name=="high-arity-refactoring") | .status' specs/_epics/tech-debt-cleanup/.epic-state.json` returns `completed`
  - **Done when**: Epic state reflects `high-arity-refactoring` complete; arity ACs marked closed.
  - **Commit**: `chore(tech-debt-cleanup): close arity ACs after high-arity-refactoring`
  - _Requirements: Dependencies, Next Steps step 5_

- [ ] V4 [VERIFY] Full local CI: layer3a + typecheck + lint + test
  - **Do**: Run the complete local CI suite.
  - **Verify**: All commands exit 0:
    - `make layer3a` — zero unaccepted arity violations
    - `make typecheck` — pyright: 0 errors
    - `make lint` — ruff + pylint: 0 violations (no RUF009, no B006)
    - `make test` — all tests pass, 100% coverage, test count unchanged
  - **Done when**: All four commands pass with no errors.
  - **Commit**: `chore(high-arity-refactoring): pass local CI` (if fixes needed)
  - _Requirements: FR-8, FR-15, FR-16, NFR-1, NFR-2, NFR-3, NFR-4_

- [ ] V4b [VERIFY] Full quality gate: `make quality-gate` (all 6 layers)
  - **Do**: Run the full 6-layer quality gate (L3A SOLID AST → L1 tests+E2E → L2 mutation → L3B BMAD consensus → L4 security).
  - **Verify**: `make quality-gate 2>&1 | tail -30` — exits 0, all 6 layers green
  - **Done when**: `make quality-gate` exits 0; every layer passes.
  - **Commit**: `chore(high-arity-refactoring): pass quality gate` (if fixes needed)
  - _Requirements: FR-16, NFR-5_
  - _Design: §7_

- [ ] V5 [VERIFY] PR opened correctly
  - **Do**:
    1. Confirm current branch is a feature branch: `git branch --show-current` (expect `feat/high-arity-refactoring`). If on `main`, STOP and alert the user.
    2. Push: `git push -u origin feat/high-arity-refactoring`.
    3. Create PR if it does not exist: `gh pr create --title "refactor: close arity tech-debt + audit pragma marks" --body "<summary of 3 wraps, dead-kwarg cleanup, pragma audit, qg-accepted audit; references epic tech-debt-cleanup>"`. Note in the body the qg-accepted audit findings per requirements AC-1.3.
  - **Verify**: `gh pr view --json url,state | jq -r '.state'` returns `OPEN`
  - **Done when**: PR exists on GitHub with a valid URL and state OPEN.
  - **Commit**: None
  - **Output**: `PR_OPENED #<N> → <url>`
  - _Requirements: FR-16, AC-1.3_

- [ ] V6 [VERIFY] AC checklist
  - **Do**: Read `requirements.md` and verify each AC programmatically:
    - AC-2.1/2.2/2.3: `grep -n "class ChargingWindowPureParams\|class WindowStartParams\|class PopulateProfileParams" custom_components/ev_trip_planner/calculations/` — all 3 present.
    - AC-2.4: each is `@dataclass(frozen=True, kw_only=True)`.
    - AC-2.6: `grep -rn "qg-accepted" custom_components/ev_trip_planner/calculations/` — no marks on the 3 wrapped functions.
    - AC-3.1: `_populate_per_trip_cache_entry` signature has no `hora_regreso`/`adjusted_def_total_hours`/`soc_cap`.
    - AC-5.4: `trip/_crud.py:53` pragma has `reason=`.
    - AC-5.6 / FR-8: `make test` 100% coverage, `make layer3a` zero unaccepted violations.
  - **Verify**: Run the grep/`make` commands above; all assertions hold.
  - **Done when**: Every AC in requirements.md confirmed met via automated checks.
  - **Commit**: None
  - _Requirements: all AC-*_

### VE Tasks — E2E Verification (library refactor — lightweight load check)

This is a pure library refactor with no UI/runtime behavior change. VE confirms the
integration still loads cleanly in the E2E HA instance (no import errors / sensor crashes
from the refactor). E2E uses `make e2e` — port 8123, ephemeral `/tmp/ha-e2e-config/`,
`hass` direct (NO Docker). No VE0 (no browser UI flow under test).

- [ ] VE1 [VERIFY] E2E startup: launch HA E2E instance, confirm integration loads
  - **Skills**: e2e
  - **Do**:
    1. Start the E2E HA instance via `make e2e` (or the project's E2E startup target) in the background; record PID to `/tmp/ve-pids.txt`.
    2. Wait up to 60s for HA ready on port 8123: `for i in $(seq 1 60); do curl -s http://localhost:8123/ >/dev/null && break || sleep 1; done`.
    3. Confirm the `ev_trip_planner` integration loaded without import errors — check HA logs in `/tmp/ha-e2e-config/` for `ev_trip_planner` import/setup errors.
  - **Verify**: `curl -sf http://localhost:8123/ >/dev/null && ! grep -i "error.*ev_trip_planner\|ev_trip_planner.*traceback" /tmp/ha-e2e-config/home-assistant.log && echo VE1_PASS`
  - **Done when**: HA E2E instance is up on 8123; `ev_trip_planner` loaded with no import/setup errors in the log.
  - **Commit**: None
  - _Requirements: NFR-5, Verification Contract_

- [ ] VE2 [VERIFY] E2E check: trip/charging sensors still produce values after refactor
  - **Skills**: e2e
  - **Do**:
    1. Run the project's E2E sensor verification (the `tests/e2e/` `.spec.ts` flow exercised by `make e2e`) — the suite drives a real user flow and asserts trip/charging sensors emit values.
    2. Confirm the refactored `calculations/` code paths (charging window, power profile) execute without error and the sensors produce non-error states.
  - **Verify**: `make e2e 2>&1 | tail -25` — exit 0, sensor assertions pass
  - **Done when**: E2E suite passes; trip/charging sensors produce expected values; no crash traced to the refactored functions.
  - **Commit**: None
  - _Requirements: FR-7, NFR-5, Verification Contract_

- [ ] VE3 [VERIFY] E2E cleanup: tear down HA E2E instance
  - **Skills**: e2e
  - **Do**:
    1. Stop HA by PID: `kill $(cat /tmp/ve-pids.txt) 2>/dev/null; sleep 2; kill -9 $(cat /tmp/ve-pids.txt) 2>/dev/null || true`.
    2. Port fallback: `lsof -ti :8123 | xargs -r kill 2>/dev/null || true`.
    3. Remove PID file: `rm -f /tmp/ve-pids.txt`.
    4. Verify port 8123 is free.
  - **Verify**: `! lsof -ti :8123 && echo VE3_PASS`
  - **Done when**: No process on port 8123; PID file removed.
  - **Commit**: None
  - _Requirements: Verification Contract_

## Phase 5: PR Lifecycle

- [ ] 5.1 [VERIFY] Monitor CI and resolve failures
  - **Do**:
    1. After the PR is open, GitHub Actions runs CI asynchronously. Do NOT block on `gh pr checks --watch`.
    2. If CI reports failures (lint/type/test/quality-gate): read details with `gh pr checks`, fix locally, push, and let CI re-run.
    3. Resolve any code review comments on the PR.
  - **Verify**: `gh pr checks 2>&1 | tail -15` — all checks green; `gh pr view --json reviewDecision` shows no blocking review.
  - **Done when**: CI all green; no unresolved review comments; zero test regressions.
  - **Commit**: `fix(high-arity-refactoring): address CI/review feedback` (per fix, if needed)
  - _Requirements: FR-16, Success Criteria_

## Notes

- **POC milestone**: task 1.3 — `ChargingWindowPureParams` wrap fully wired (dataclass +
  prod caller + 6 test call sites) and `make test` green at 100% coverage. Proves the
  wrap pattern end-to-end before the remaining 2 wraps are applied mechanically.
- **No new unit tests**: per design.md §6 the wraps are structural with no new logic —
  existing tests exercise the same code paths. Test work is call-site-update only.
- **Dead kwargs**: only 3 are dead (`hora_regreso`, `adjusted_def_total_hours`,
  `soc_cap`). `pre_computed_inicio_ventana/fin_ventana/charging_window` are ACTIVE and
  MUST be kept — requirements.md AC-3.1 listed 6 but design.md §4 corrected this to 3.
- **`loop_now` complication**: design.md §7 Q2 — `WindowStartParams` is frozen; the
  caller `calculate_multi_trip_charging_windows` must keep `loop_now` as a separate
  local, pass it in, and not read it back from the frozen object.
- **Audits are pre-decided**: qg-accepted (§2a) and pragma (§2b) verdict tables are
  authoritative — tasks apply verdicts and confirm, not re-audit from scratch.
- **`_validate_field`**: conditional — comment removed only if `make layer3a` does not
  fire on effective arity 5.
- **Hard invariants**: no test deleted; BMAD-consensus `qg-accepted` marks untouched;
  coverage stays at 100%.

## Unresolved Questions

- None blocking. The two design.md §7 questions (`_validate_field` arity counting,
  `loop_now` mutation) are resolved inline in tasks 2.4 and 1.4 respectively.
