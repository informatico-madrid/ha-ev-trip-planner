# Tasks: Dead Code Elimination

> Granularity: COARSE — larger tasks, one commit each. Verification at phase boundaries (BALANCED priority).
> Workflow: POC-first 5-phase structure, adapted for a removal spec (no feature to prototype).
> Phase gate is `make test` (per design.md — NOT `make lint`). Full quality gate runs in the final phase.

## Phase 1: Zero-Risk Removals (proves build survives bulk dead-code removal)

Focus: remove dead code with zero production consumers. EMHASSAdapter/IndexManager
method removals land ATOMICALLY with their 11 test deletions in the same commit.

- [x] 1.1 Remove trivial artifacts (backups + empty dashboard dir)
  - **Do**:
    1. `rm -f custom_components/ev_trip_planner/panel.js.bak custom_components/ev_trip_planner/panel.js.old custom_components/ev_trip_planner/panel.js.fixed` (idempotent — files already absent on this branch)
    2. `rm -rf custom_components/ev_trip_planner/dashboard/__pycache__`
    3. `rmdir custom_components/ev_trip_planner/dashboard` (directory contains only `__pycache__/`)
  - **Files**: `custom_components/ev_trip_planner/panel.js.*`, `custom_components/ev_trip_planner/dashboard/`
  - **Done when**: `panel.js.*` absent AND `dashboard/` directory no longer exists
  - **Verify**: `! ls custom_components/ev_trip_planner/panel.js.* 2>/dev/null && ! test -d custom_components/ev_trip_planner/dashboard && echo PASS`
  - **Commit**: `chore(cleanup): remove stale frontend backups and empty dashboard dir`
  - _Requirements: FR-8, US-8, AC-8.1, AC-8.2_
  - _Design: Component 8_

- [x] 1.2 Remove 4 dead attributes from EMHASSAdapter — 22e663a
  - **Do**:
    1. In `emhass/adapter.py`, remove line 133 assignment `self._stored_battery_capacity_kwh = battery_capacity_kwh`
    2. Remove line 146 declaration `self._stored_t_base: float | None = None`
    3. Remove line 147 declaration `self._stored_soh_sensor: str | None = None`
    4. Remove the DUPLICATE declaration of `_stored_charging_power_kw` at line 145 ONLY — keep the live assignment at line 132 (it is read/written at lines 283, 306; the line-145 dup overwrites it with None — this is a bug fix)
  - **Files**: `custom_components/ev_trip_planner/emhass/adapter.py`
  - **Done when**: 3 dead attrs gone AND `_stored_charging_power_kw` appears only once (line ~132)
  - **Verify**: `grep -c '_stored_charging_power_kw' custom_components/ev_trip_planner/emhass/adapter.py | grep -qx 2 && ! grep -q '_stored_battery_capacity_kwh\|_stored_t_base\|_stored_soh_sensor' custom_components/ev_trip_planner/emhass/adapter.py && echo PASS`
  - **Commit**: `refactor(emhass): remove dead adapter attributes, fix duplicate declaration`
  - _Requirements: FR-2, US-2, AC-2.1, AC-2.2, AC-2.3, AC-2.4_
  - _Design: Component 1_

- [x] 1.3 [ATOMIC] Remove 8 dead methods (7 adapter + IndexManager) AND delete their 11 tests — 3d5a7de
  - **Do** (source + test removal MUST land together in ONE commit — reviewed-and-fixed defect, do not split):
    1. From `emhass/adapter.py` remove 7 dead methods: `async_notify_error` (~222-230), `calculate_deferrable_parameters` (~610-621, returns `{}`), `get_assigned_index` (~207-209), `get_all_assigned_indices` (~211-213), `async_release_trip_index` (~176-186), `async_save` (~164-166), `async_save_trips` EMHASS version (~606-608). Do NOT touch `get_available_indices` (live, used by diagnostics.py) or `state.async_save_trips` (different scope).
    2. From `emhass/index_manager.py` remove `async_release_index` (~63-69). KEEP `async_load_index` and `async_save_index` — no-op stubs called from adapter.py.
    3. From `tests/unit/test_emhass_package.py` delete the 11 tests for the removed methods: `test_async_release_index_*` (2), `test_async_save_*` (1), `test_async_release_trip_index_*` (2), `test_get_assigned_index*` (2), `test_get_all_assigned_indices` (1), `test_async_notify_error_logs` (1), `test_calculate_deferrable_parameters_returns_empty` (1), `test_async_save_trips_delegates` (1).
  - **Files**: `custom_components/ev_trip_planner/emhass/adapter.py`, `custom_components/ev_trip_planner/emhass/index_manager.py`, `tests/unit/test_emhass_package.py`
  - **Done when**: 8 methods removed; 11 tests deleted; `async_load_index`/`async_save_index` still present
  - **Verify**: `! grep -qE 'def (async_notify_error|get_assigned_index|get_all_assigned_indices|async_release_trip_index|async_release_index)\b' custom_components/ev_trip_planner/emhass/adapter.py custom_components/ev_trip_planner/emhass/index_manager.py && grep -q 'def async_load_index' custom_components/ev_trip_planner/emhass/index_manager.py && grep -q 'def async_save_index' custom_components/ev_trip_planner/emhass/index_manager.py && echo PASS`
  - **Commit**: `refactor(emhass): remove 8 dead methods and their 11 tests`
  - _Requirements: FR-1, FR-3, US-1, US-3, AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5, AC-1.6, AC-1.7, AC-3.1, AC-3.2_
  - _Design: Component 1, Component 2_

- [ ] 1.4 Remove dead re-exports from sensor/__init__.py
  - **Do**:
    1. In `sensor/__init__.py` remove `TRIP_SENSORS` from the import block (line ~14) and from `__all__` (line ~31)
    2. Remove `_async_create_trip_sensors` from the import block (line ~15) — it is not in `__all__`
    3. Do NOT touch `async_setup_entry`, `TripSensor`, `TripPlannerSensor`, `EmhassDeferrableLoadSensor`, `TripEmhassSensor` — HA platform entry points
  - **Files**: `custom_components/ev_trip_planner/sensor/__init__.py`
  - **Done when**: `TRIP_SENSORS` and `_async_create_trip_sensors` gone from imports and `__all__`
  - **Verify**: `! grep -qE 'TRIP_SENSORS|_async_create_trip_sensors' custom_components/ev_trip_planner/sensor/__init__.py && grep -q 'async_setup_entry' custom_components/ev_trip_planner/sensor/__init__.py && echo PASS`
  - **Commit**: `refactor(sensor): remove dead TRIP_SENSORS and _async_create_trip_sensors re-exports`
  - _Requirements: FR-6, US-6, AC-6.1, AC-6.2_
  - _Design: Component 5_

- [ ] 1.5 [VERIFY] Phase 1 gate: make test passes
  - **Do**: Run `make test` (runs `pytest tests/unit tests/integration`). Confirm zero failures and zero new warnings after the bulk zero-risk removals.
  - **Verify**: `make test` exits 0
  - **Done when**: All tests green; no AttributeError/NameError for removed names
  - **Commit**: `chore(dead-code-elimination): pass Phase 1 test gate` (only if fixes needed)

## Phase 2: Service Shim Removal (low risk — test-only consumers)

Focus: delete the 3 service shim files and clean their integration test consumers.

- [ ] 2.1 Delete 3 service shim files and clean their test consumers
  - **Do**:
    1. `rm custom_components/ev_trip_planner/services/handlers.py custom_components/ev_trip_planner/services/_lookup.py custom_components/ev_trip_planner/services/presence.py`
    2. In `tests/integration/test_services_shims.py` remove all 3 test methods for the dead shims (remove the file if it becomes empty)
    3. In `tests/integration/test_services_pkg.py` remove the `TestServicesLookupShim`, `TestServicesPresenceShim`, `TestServicesHandlersShim` classes (~52 lines)
    4. These shims only re-exported from `_utils.py`, which remains intact — no production import path is affected
  - **Files**: `custom_components/ev_trip_planner/services/handlers.py`, `custom_components/ev_trip_planner/services/_lookup.py`, `custom_components/ev_trip_planner/services/presence.py`, `tests/integration/test_services_shims.py`, `tests/integration/test_services_pkg.py`
  - **Done when**: 3 shim files removed; shim test classes/methods removed from both integration test files
  - **Verify**: `! ls custom_components/ev_trip_planner/services/handlers.py custom_components/ev_trip_planner/services/_lookup.py custom_components/ev_trip_planner/services/presence.py 2>/dev/null && ! grep -qE 'TestServicesLookupShim|TestServicesPresenceShim|TestServicesHandlersShim' tests/integration/test_services_pkg.py && echo PASS`
  - **Commit**: `refactor(services): delete dead shim files and their tests`
  - _Requirements: FR-7, US-7, AC-7.1, AC-7.2, AC-7.3, AC-7.4_
  - _Design: Component 6_

- [ ] 2.2 [VERIFY] Phase 2 gate: make test passes
  - **Do**: Run `make test`. Confirm no ImportError from the deleted shim files and all tests green.
  - **Verify**: `make test` exits 0
  - **Done when**: All tests pass; no ImportError for `services.handlers`/`services._lookup`/`services.presence`
  - **Commit**: `chore(dead-code-elimination): pass Phase 2 test gate` (only if fixes needed)

## Phase 3: trip_manager Shim + _emhass_sync Removal (medium risk — import ordering critical)

Focus: redirect all `trip_manager` imports BEFORE deleting the shim; remove test
consumers of `_get_all_active_trips` BEFORE deleting the method.

- [ ] 3.1 Redirect all trip_manager imports, then delete the shim
  - **Do** (import updates MUST precede the shim deletion — dependency-ordering constraint):
    1. Update `vehicle/controller.py:26` TYPE_CHECKING import: `from ..trip_manager import TripManager` → `from ..trip import TripManager`
    2. Update `tests/unit/conftest.py` lines ~11 and ~867: `from custom_components.ev_trip_planner.trip_manager import TripManager` → `from custom_components.ev_trip_planner.trip import TripManager`
    3. Update `tests/integration/conftest.py` lines ~635 and ~658: same redirect `trip_manager` → `trip`
    4. After ALL imports are redirected, `rm custom_components/ev_trip_planner/trip_manager.py`
    5. Do NOT touch `test_trip_imports.py` — it imports from `trip.manager` directly, no change needed
  - **Files**: `custom_components/ev_trip_planner/vehicle/controller.py`, `tests/unit/conftest.py`, `tests/integration/conftest.py`, `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: shim file deleted; no remaining `trip_manager` import anywhere; `from ...trip import TripManager` resolves
  - **Verify**: `! test -f custom_components/ev_trip_planner/trip_manager.py && ! grep -rqE 'ev_trip_planner\.trip_manager|\.\.trip_manager' custom_components/ev_trip_planner tests && echo PASS`
  - **Commit**: `refactor(trip): redirect imports and remove trip_manager.py shim`
  - _Requirements: FR-5, US-5, AC-5.1, AC-5.2, AC-5.3_
  - _Design: Component 4, Component 7_

- [ ] 3.2 Remove _get_all_active_trips test consumers, then delete the method
  - **Do** (test consumers MUST be removed before/with the source method — dependency-ordering constraint):
    1. From `tests/unit/test_trip_crud_execution.py` remove the `TestGetAllActiveTrips` class and all 4 of its test methods
    2. From `tests/unit/test_trip_manager_properties.py` remove `test_get_all_active_trips_via_emhass_sync`
    3. From `trip/_emhass_sync.py` remove `_get_all_active_trips` (~lines 117-127). Do NOT touch `_async_sync_trip_to_emhass`, `_async_remove_trip_from_emhass`, `_async_publish_new_trip_to_emhass`.
  - **Files**: `tests/unit/test_trip_crud_execution.py`, `tests/unit/test_trip_manager_properties.py`, `custom_components/ev_trip_planner/trip/_emhass_sync.py`
  - **Done when**: `_get_all_active_trips` removed; `TestGetAllActiveTrips` and `test_get_all_active_trips_via_emhass_sync` removed
  - **Verify**: `! grep -q 'def _get_all_active_trips' custom_components/ev_trip_planner/trip/_emhass_sync.py && ! grep -qE 'TestGetAllActiveTrips|test_get_all_active_trips_via_emhass_sync' tests/unit/test_trip_crud_execution.py tests/unit/test_trip_manager_properties.py && echo PASS`
  - **Commit**: `refactor(trip): remove dead _get_all_active_trips method and its tests`
  - _Requirements: FR-4, US-4, AC-4.1_
  - _Design: Component 3_

- [ ] 3.3 [VERIFY] Phase 3 gate: make test passes
  - **Do**: Run `make test`. Confirm conftest fixtures (`trip_manager_with_entry_id`, `mock_hass_manager_setup_error`, `mock_hass_manager_setup_ok`) still resolve after import redirects and no ImportError/AttributeError for removed code.
  - **Verify**: `make test` exits 0
  - **Done when**: All tests pass; conftest fixtures construct cleanly
  - **Commit**: `chore(dead-code-elimination): pass Phase 3 test gate` (only if fixes needed)

## Phase 4: Quality Gates + Hard-Invariant Verification

Focus: full quality suite, dead-code audit, hard-invariant import checks, PR.

- [ ] 4.1 [VERIFY] Verify hard invariants (preserved API surface)
  - **Do**: Run import + presence checks for everything that MUST survive the removals:
    1. `python3 -c "from custom_components.ev_trip_planner.sensor import async_setup_entry, TripSensor, TripPlannerSensor, EmhassDeferrableLoadSensor, TripEmhassSensor"`
    2. `python3 -c "from custom_components.ev_trip_planner.trip import TripManager"`
    3. `grep -q 'def async_load_index' custom_components/ev_trip_planner/emhass/index_manager.py && grep -q 'def async_save_index' custom_components/ev_trip_planner/emhass/index_manager.py`
    4. `grep -rq 'class ErrorHandler' custom_components/ev_trip_planner/emhass/error_handler.py`
    5. `grep -q 'def calculate_deferrable_parameters' custom_components/ev_trip_planner/calculations/schedule.py`
  - **Verify**: All 5 commands exit 0
  - **Done when**: Sensor + trip imports resolve; IndexManager stubs, ErrorHandler, and calculations/schedule.py replacement all still present
  - **Commit**: None

- [ ] 4.2 [VERIFY] Dead-code audit: vulture reports zero findings for removed names
  - **Do**: Run `make dead-code` (vulture, >=80% confidence). Confirm none of the removed names still appear as live, and no NEW in-scope findings were introduced. New findings beyond scoped items are expected — log them in .progress.md for a future pass, do not fix here.
  - **Verify**: `make dead-code` runs; output contains zero findings for: `async_notify_error`, `calculate_deferrable_parameters` (adapter), `get_assigned_index`, `get_all_assigned_indices`, `async_release_trip_index`, `async_save` (adapter), `async_save_trips` (adapter), `async_release_index`, `_get_all_active_trips`, `TRIP_SENSORS`, `_async_create_trip_sensors`, `handlers`, `_lookup`, `presence`
  - **Done when**: No vulture findings for any removed name
  - **Commit**: None

- [ ] V4 [VERIFY] Full local quality gate: lint, typecheck, dead-code, test, quality-gate-ci
  - **Do**: Run the complete local quality suite in order:
    1. `make lint` — ruff + pylint clean
    2. `make typecheck` — pyright clean (no type errors outside removal scope)
    3. `make dead-code` — vulture clean for removed names
    4. `make test` — all unit + integration tests pass
    5. `make quality-gate-ci` — CI quality gate passes
  - **Verify**: All 5 commands exit 0
  - **Done when**: lint, typecheck, dead-code, test, and quality-gate-ci all pass
  - **Commit**: `chore(dead-code-elimination): pass full local quality gate` (only if fixes needed)

- [ ] V5 [VERIFY] PR opened correctly
  - **Do**: Verify current branch is a feature branch (`git branch --show-current`), push with `git push -u origin <branch>`, then create the PR with `gh pr create` (HEREDOC body summarizing the ~30 removed dead-code items) if it does not already exist.
  - **Verify**: `gh pr view --json url,state | jq -r '.state'` returns `OPEN`
  - **Done when**: PR exists on GitHub with a valid URL and state OPEN
  - **Commit**: None
  - **Output**: `PR_OPENED #<N> → <url>`

  > PR Lifecycle Rule: the local agent's responsibility ends when the PR exists on GitHub. Do NOT wait for CI or run `gh pr checks --watch`.

- [ ] V6 [VERIFY] AC checklist
  - **Do**: Read requirements.md and programmatically verify each AC is satisfied:
    - AC-1.1..1.7: grep adapter.py confirms the 7 methods are gone
    - AC-2.1..2.4: grep adapter.py confirms 3 dead attrs gone, `_stored_charging_power_kw` declared once
    - AC-3.1/3.2: `async_release_index` gone, `async_load_index`/`async_save_index` present
    - AC-4.1: `_get_all_active_trips` gone from `_emhass_sync.py`
    - AC-5.1..5.3: controller.py import redirected, `trip_manager.py` gone, no `trip_manager` test imports
    - AC-6.1/6.2: `TRIP_SENSORS`/`_async_create_trip_sensors` gone from sensor/__init__.py
    - AC-7.1..7.4: 3 service shims gone, shim test classes removed
    - AC-8.1/8.2: `panel.js.*` and `dashboard/` gone
  - **Verify**: Grep checks for every AC + relevant `make test` results all confirm satisfied
  - **Done when**: All acceptance criteria across US-1..US-8 confirmed met via automated checks
  - **Commit**: None

- [ ] VE1 [VERIFY] E2E startup: boot Home Assistant via make e2e harness
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session, home-assistant-best-practices
  - **Do**:
    1. The project runs E2E via `make e2e`, which auto-starts HA (`hass` direct, port 8123, ephemeral `/tmp/ha-e2e-config/`, NO Docker) and then runs Playwright. There is no separate dev-server step — `make e2e` owns startup.
    2. This VE1 task confirms the E2E harness can boot HA cleanly after the dead-code removals (especially the `sensor/__init__.py` re-export removal must not break HA entity-platform loading).
    3. Run `make e2e` (it boots HA, waits for ready, runs the Playwright suite).
  - **Verify**: `make e2e` reaches the test-run phase without an HA startup/import error (HA loads `sensor` platform via manifest `platforms` key)
  - **Done when**: HA boots under the E2E harness; no ImportError/AttributeError during component load
  - **Commit**: None
  - Note: Browser Automation — qa-engineer runs `make e2e` only; never `npx playwright test` directly (project rule).

- [ ] VE2 [VERIFY] E2E check: dead-code removal did not break HA entity loading or UI
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session, home-assistant-best-practices
  - **Do**:
    1. Within the same `make e2e` run started in VE1, confirm the Playwright E2E suite (`tests/e2e/*.spec.ts`) passes end-to-end.
    2. Verify the critical user-facing flow still works: HA loads the `ev_trip_planner` integration, the sensor entities (`async_setup_entry`, `TripSensor`, `TripPlannerSensor`, `EmhassDeferrableLoadSensor`, `TripEmhassSensor`) register, and the integration UI renders without console errors.
    3. Confirm no entity-platform load failure traces in the HA log caused by the `sensor/__init__.py` re-export removal or the `trip_manager.py` shim deletion.
  - **Done when**:
    - [ ] `make e2e` Playwright suite exits 0 (all `.spec.ts` pass)
    - [ ] HA registered the `ev_trip_planner` sensor entities (no missing-platform error)
    - [ ] No ImportError/AttributeError for any removed name in the HA E2E log
    - [ ] No 404, crash, or unexpected console error during the integration UI flow
  - **Verify**: `make e2e 2>&1 | tail -30` shows the Playwright suite passing and no HA component-load error
  - **Commit**: None

- [ ] VE3 [VERIFY] E2E cleanup: tear down E2E HA instance
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session
  - **Do**:
    1. Stop any HA process started by the E2E harness on port 8123: `lsof -ti :8123 | xargs -r kill 2>/dev/null || true`; wait 2s; escalate survivors `lsof -ti :8123 | xargs -r kill -9 2>/dev/null || true`
    2. Remove the ephemeral E2E config dir: `rm -rf /tmp/ha-e2e-config`
    3. Run `make e2e`'s own teardown if it exposes one; otherwise the port-kill above is the fallback
    4. Verify port 8123 is free
  - **Verify**: `! lsof -ti :8123 && echo VE3_PASS`
  - **Done when**: No process listening on 8123; ephemeral E2E config removed
  - **Commit**: None
  - Note: VE3 MUST run even if VE1/VE2 fail — orphaned HA processes block port 8123.

## Notes

- **Removal-spec adaptation**: There is no POC feature to build. Phase 1 = zero-risk removals (proves the build/tests survive the bulk of dead-code gone). Phases 2-3 = riskier shim/import work. Phase 4 = full quality + E2E verification. The "POC Checkpoint" role is filled by the 1.5 `make test` gate.
- **Atomic constraint (1.3)**: Removing the 8 dead methods and deleting the 11 `test_emhass_package.py` tests land in ONE commit — splitting source removal from test cleanup was a reviewed-and-fixed defect; do not reintroduce it.
- **Dependency ordering (3.1, 3.2)**: `controller.py` + conftest import redirects precede `trip_manager.py` deletion; `_get_all_active_trips` test consumers are removed before/with the source method.
- **Phase gate is `make test`** (per design.md), not `make lint`. The full quality gate (`make lint`, `make typecheck`, `make dead-code`, `make test`, `make quality-gate-ci`) runs once in Phase 4 (V4).
- **Idempotent removals**: `panel.js.*` files confirmed absent on this branch — `rm -f` handles this without error.
- **Preserved (do NOT touch)**: `ErrorHandler`, `IndexManager.async_load_index`/`async_save_index` no-op stubs, ABC markers (`IndexManagerBase`/`LoadPublisherBase`), `calculations/schedule.py.calculate_deferrable_parameters`, `get_available_indices`, `state.async_save_trips` (TripPersistence).
- **vulture new findings**: any dead code flagged beyond the ~30 scoped items is expected — log for a future pass, do not fix in this spec.
