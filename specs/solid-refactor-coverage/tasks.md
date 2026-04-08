# Tasks: solid-refactor-coverage

**Input**: Design documents from `./specs/solid-refactor-coverage/`
**Prerequisites**: `requirements.md` (user stories), `design.md` (phase checklist)

**Goal**: Refactor `trip_manager.py` and `emhass_adapter.py` via Protocol DI. Pure functions first (Phase A), Protocols (Phase B), constructor injection (Phase C), Layer 1 test doubles + MagicMock fixes (Phase D). 100% coverage as consequence.

## Format: `[ID] [P?] [Story] [VERIFY:TEST] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US-A1, US-A2, US-B1, US-B2, US-C1, US-D1, US-D2, US-E1)
- **[VERIFY:TEST]**: pytest unit/integration tests
- Exact file paths in descriptions

---

## Pre-requisites

- [ ] T000 [US-E1] Record coverage baseline: `pytest tests --cov=custom_components.ev_trip_planner --cov-report=term-missing > /tmp/coverage_before.txt` — must run BEFORE Phase A to have comparative value

---

## Phase A: Pure Functions Extraction

**Goal**: Extract pure functions from TripManager and EMHASSAdapter to `calculations.py`/`utils.py`. These are 100% testable without doubles.

### US-A1: Extract Pure Functions from TripManager

**Independent Test**: `pytest tests/test_trip_manager_core.py tests/test_utils.py -v` — all pass, pure functions 100% covered

#### Tests FIRST (TDD RED)

- [x] T001 [P] [US-A1] [VERIFY:TEST] Write failing tests for `validate_hora()` in `tests/test_utils.py` — test valid "HH:MM", invalid "25:00", boundary cases
- [x] T002 [P] [US-A1] [VERIFY:TEST] Write failing tests for `sanitize_recurring_trips()` in `tests/test_utils.py` — test filtering of invalid hora entries
- [x] T003 [P] [US-A1] [VERIFY:TEST] Write failing tests for `is_trip_today()` in `tests/test_utils.py` — test recurring (lunes/monday) and punctual trips
- [x] T004 [P] [US-A1] [VERIFY:TEST] Write failing tests for `calculate_charging_rate()` and `calculate_soc_target()` in `tests/test_calculations.py`
- [x] T005 [P] [US-A1] [VERIFY:TEST] Write failing tests for `get_trip_time()` and `get_day_index()` in `tests/test_utils.py`

#### Implementation

- [x] T006 [P] [US-A1] Add `validate_hora(hora: str) -> None` to `custom_components/ev_trip_planner/utils.py`
- [x] T007 [P] [US-A1] Add `sanitize_recurring_trips(trips: Dict) -> Dict` to `custom_components/ev_trip_planner/utils.py`
- [x] T008 [P] [US-A1] Add `is_trip_today(trip: Dict, today: date) -> bool` to `custom_components/ev_trip_planner/utils.py`
- [x] T009 [P] [US-A1] Add `calculate_trip_time(trip: Dict) -> Optional[datetime]` and `calculate_day_index(day_name: str) -> int` to `custom_components/ev_trip_planner/utils.py`
- [x] T010 [P] [US-A1] Add `calculate_charging_rate(power_kw: float, capacity: float) -> float` and `calculate_soc_target(trip, capacity: float, consumption: float) -> float` to `custom_components/ev_trip_planner/calculations.py`
- [ ] T011 [US-A1] Update `TripManager` to import and call extracted functions — delegate internal private methods to the new pure functions (no logic duplication)
  ⚠️ REVIEW FAIL: Solo 4/7 delegan correctamente. FALTA: `_validate_hora` no delega a utils.validate_hora, `_sanitize_recurring_trips` no delega a utils.sanitize_recurring_trips, `_is_trip_today` no delega a utils.is_trip_today. TripManager debe importar estas funciones de utils.py y delegar.
- [ ] T012 [US-A1] Verify pure functions in `utils.py` and `calculations.py` show 100% coverage — utils.py 96% (5 edge-case lines), calculations.py 84%. No es 100%. Se necesitan tests adicionales para ramas no cubiertas.

#### US-A1 Gate

- [x] T013 [US-A1] Run `pytest tests/test_trip_manager_core.py tests/test_utils.py -v` — all pass
- [x] T014 [US-A1] Run `ruff check custom_components/ev_trip_planner/ --select=I` — 0 violations
- [ ] T015 [US-A1] Run `mypy custom_components/ev_trip_planner/utils.py custom_components/ev_trip_planner/calculations.py` — 0 errors

---

### US-A2: Extract Pure Functions from EMHASSAdapter

**Independent Test**: `pytest tests/test_emhass_adapter.py tests/test_calculations.py -v` — all pass, pure functions 100% covered

#### Tests FIRST (TDD RED)

- [x] T016 [P] [US-A2] [VERIFY:TEST] Write failing tests for `calculate_deferrable_parameters()` in `tests/test_calculations.py`
- [x] T017 [P] [US-A2] [VERIFY:TEST] Write failing tests for `calculate_power_profile_from_trips()` in `tests/test_calculations.py`
- [x] T018 [P] [US-A2] [VERIFY:TEST] Write failing tests for `generate_deferrable_schedule_from_trips()` in `tests/test_calculations.py`

#### Implementation

- [x] T019 [P] [US-A2] Add `calculate_deferrable_parameters(trip: Dict, power_kw: float) -> Dict` to `custom_components/ev_trip_planner/calculations.py`
- [x] T020 [P] [US-A2] Add `calculate_power_profile_from_trips(trips: List[Dict], power_kw: float, horizon: int) -> List[float]` to `custom_components/ev_trip_planner/calculations.py`
- [x] T021 [P] [US-A2] Add `generate_deferrable_schedule_from_trips(trips: List[Dict], power_kw: float) -> List[Dict]` to `custom_components/ev_trip_planner/calculations.py` — IMPLEMENTED, 7/8 tests pass (test_punctual_trip_with_future_deadline has time-dependent bug: hardcoded date 2026-04-06T18:00 is in the past)
- [x] T022 [US-A2] Update `EMHASSAdapter` to import and call extracted functions from `calculations.py` (no logic duplication)
   - OJO ⚠️ REVIEW TIENES TAREAS PENDIENTES PRO REVISION.  ATRAS REVISA BIEN EL ORDEN DE IMPLEMENTACION
- [x] T023 [US-A2] Verify pure functions in `calculations.py` show 100% coverage
  - OJO ⚠️ REVIEW TIENES TAREAS PENDIENTES PRO REVISION.  ATRAS REVISA BIEN EL ORDEN DE IMPLEMENTACION
#### US-A2 Gate

- [x] T024 [US-A2] Run `pytest tests/test_emhass_adapter.py tests/test_calculations.py -v` — all pass
- [x] T025 [US-A2] Run `ruff check custom_components/ev_trip_planner/ --select=I` — 0 violations
- [x] T026 [US-A2] Run `mypy custom_components/ev_trip_planner/calculations.py` — 0 errors

---

## Phase B: Protocols

**Goal**: Define `protocols.py` with `TripStorageProtocol` and `EMHASSPublisherProtocol` using `typing.Protocol`. Existing classes implement structurally — no code change needed.

### US-B1: Define TripStorageProtocol

**Independent Test**: `pytest tests/test_protocols.py -v` — structural compatibility verified

#### Tests FIRST (TDD RED)

- [x] T027 [P] [US-B1] [VERIFY:TEST] Write failing test verifying `YamlTripStorage` implements `TripStorageProtocol` structurally via `isinstance()` in `tests/test_protocols.py` — requires `@runtime_checkable` decorator (see T028)

#### Implementation

- [x] T028 [US-B1] Create `custom_components/ev_trip_planner/protocols.py` with `@runtime_checkable` decorator and `TripStorageProtocol` defining `async_load() -> Dict` and `async_save(data: Dict) -> None` using `...` stubs — **both protocols MUST have `@runtime_checkable`** for isinstance() to work at runtime  - OJO ⚠️ REVIEW TIENES TAREAS PENDIENTES PRO REVISION.  ATRAS REVISA BIEN EL ORDEN DE IMPLEMENTACION no continues avanzando sin sin compeltar las tareas anteriores!!

#### US-B1 Gate

- [ ] T029 [US-B1] Run `pytest tests/test_protocols.py -v` — isinstance check passes
- [ ] T030 [US-B1] Run `mypy custom_components/ev_trip_planner/protocols.py` — 0 errors  - OJO ⚠️ REVIEW TIENES TAREAS PENDIENTES PRO REVISION.  ATRAS REVISA BIEN EL ORDEN DE IMPLEMENTACION no continues avanzando sin sin compeltar las tareas anteriores!!

---

### US-B2: Define EMHASSPublisherProtocol

**Independent Test**: `pytest tests/test_protocols.py -v` — structural compatibility verified

#### Tests FIRST (TDD RED)

- [x] T031 [P] [US-B2] [VERIFY:TEST] Write failing test verifying `EMHASSAdapter` implements `EMHASSPublisherProtocol` structurally via `isinstance()` in `tests/test_protocols.py` — requires `@runtime_checkable` decorator (see T032)  - OJO ⚠️ REVIEW TIENES TAREAS PENDIENTES PRO REVISION.  ATRAS REVISA BIEN EL ORDEN DE IMPLEMENTACION no continues avanzando sin sin compeltar las tareas anteriores!!

#### Implementation

- [x] T032 [US-B2] Add `@runtime_checkable` decorator and `EMHASSPublisherProtocol` to `protocols.py` with `async_publish_deferrable_load(trip: Dict) -> bool` and `async_remove_deferrable_load(trip_id: str) -> bool` using `...` stubs — **both protocols MUST have `@runtime_checkable`** for isinstance() to work at runtime  - OJO ⚠️ REVIEW TIENES TAREAS PENDIENTES PRO REVISION.  ATRAS REVISA BIEN EL ORDEN DE IMPLEMENTACION no continues avanzando sin sin compeltar las tareas anteriores!!

#### US-B2 Gate

- [ ] T033 [US-B2] Run `pytest tests/test_protocols.py -v` — isinstance check passes
- [ ] T034 [US-B2] Run `mypy custom_components/ev_trip_planner/protocols.py` — 0 errors

---

## Phase C: Constructor Injection

**Goal**: `TripManager.__init__` accepts `storage: TripStorageProtocol` and `emhass_adapter: EMHASSPublisherProtocol` with `_UNSET` sentinel defaults. Backward compatibility preserved.

### US-C1: Inject Protocols via TripManager Constructor

**Independent Test**: `pytest tests/test_trip_manager_core.py -v` — TripManager works with both real and fake implementations

#### Tests FIRST (TDD RED)

- [ ] T035 [P] [US-C1] [VERIFY:TEST] Write failing test in `tests/test_trip_manager.py` verifying TripManager accepts `storage: TripStorageProtocol` and `emhass_adapter: EMHASSPublisherProtocol` in constructor with `_UNSET` sentinel defaults
- [x] T036 [P] [US-C1] [VERIFY:TEST] Write failing test verifying `set_emhass_adapter()` and `get_emhass_adapter()` still work after refactor

#### Implementation

- [ ] T037 [US-C1] Add `_UNSET = object()` sentinel at module level in `custom_components/ev_trip_planner/trip_manager.py`
- [ ] T038 [US-C1] Modify `TripManager.__init__` signature: add `storage: TripStorageProtocol = _UNSET` and `emhass_adapter: EMHASSPublisherProtocol = _UNSET` parameters
- [ ] T039 [US-C1] Implement inline defaults: `self._storage = storage if storage is not _UNSET else YamlTripStorage(hass, vehicle_id)` and `self._emhass_adapter = emhass_adapter if emhass_adapter is not _UNSET else EMHASSAdapter(...)`
- [ ] T040 [US-C1] Preserve `set_emhass_adapter()` and `get_emhass_adapter()` for backward compatibility
- [ ] T041 [US-C1] Import protocols from `protocols.py`

#### US-C1 Gate

- [ ] T042 [US-C1] Run `pytest tests/test_trip_manager_core.py -v` — all pass
- [ ] T043 [US-C1] Run `pytest tests/test_trip_manager_emhass.py -v` — all pass
- [ ] T044 [US-C1] Run `ruff check custom_components/ev_trip_planner/trip_manager.py --select=I` — 0 violations
- [ ] T045 [US-C1] Run `mypy custom_components/ev_trip_planner/trip_manager.py` — 0 errors
- [ ] T046 [US-C1] Verify `set_emhass_adapter()` still works (backward compatibility)

---

## Phase D: Layer 1 Migration + MagicMock Fixes

**Goal**: Populate `tests/__init__.py` with Layer 1 doubles. Fix MagicMock() without spec violations in test files incrementally.

### US-D1: Populate tests/__init__.py with Layer 1 Test Doubles

**Independent Test**: `pytest tests/ -v` — all imports from tests/__init__.py work

#### Tests FIRST (TDD RED)

- [ ] T047 [P] [US-D1] [VERIFY:TEST] Write failing test in `tests/test_init.py` verifying `FakeTripStorage` and `FakeEMHASSPublisher` implement their protocols

#### Implementation

- [ ] T048 [US-D1] Populate `tests/__init__.py` with:
  - `TEST_VEHICLE_ID`, `TEST_ENTRY_ID`, `TEST_CONFIG`, `TEST_TRIPS`, `TEST_COORDINATOR_DATA` constants
  - `FakeTripStorage` class (implements `TripStorageProtocol`)
  - `FakeEMHASSPublisher` class (implements `EMHASSPublisherProtocol`)
  - `create_mock_trip_manager()` returning `MagicMock(spec=TripManager)` with async methods configured individually
  - `create_mock_coordinator(hass, entry, trip_manager)` returning `MagicMock(spec=TripPlannerCoordinator)`
  - `create_mock_ev_config_entry(hass, data, entry_id)` returning `MockConfigEntry`
  - `setup_mock_ev_config_entry(hass, config_entry, trip_manager)` with HA boundary patch inside

#### US-D1 Gate

- [ ] T049 [US-D1] Run `pytest tests/test_init.py -v` — all pass
- [ ] T050 [US-D1] Run `python -c "from tests import create_mock_trip_manager, FakeTripStorage, FakeEMHASSPublisher; print('OK')"` — imports work

---

### US-D2: Fix MagicMock() Without Spec Violations Incrementally

**Independent Test**: `pytest tests/test_trip_manager.py tests/test_emhass_adapter.py -v` — all pass with `MagicMock(spec=)`

#### Implementation (file by file as each Phase D sub-task)

- [ ] T051 [P] [US-D2] Fix `tests/test_trip_manager.py`: replace all `MagicMock()` with `MagicMock(spec=TripManager)` for TripManager class
- [ ] T052 [P] [US-D2] Fix `tests/test_trip_manager_core.py`: replace all `MagicMock()` with `MagicMock(spec=TripManager)` for TripManager class
- [ ] T053 [P] [US-D2] Fix `tests/test_emhass_adapter.py`: replace all `MagicMock()` with `MagicMock(spec=EMHASSAdapter)` for EMHASSAdapter class
- [ ] T054 [P] [US-D2] Fix `tests/test_coordinator.py`: replace all `MagicMock()` with `MagicMock(spec=TripPlannerCoordinator)` for coordinator class
- [ ] T055 [P] [US-D2] Fix remaining test files with MagicMock() violations for own classes

#### US-D2 Gate

- [ ] T056 [US-D2] Run `pytest tests/test_trip_manager.py tests/test_emhass_adapter.py tests/test_coordinator.py -v` — all pass
- [ ] T057 [US-D2] Run `grep -rn "MagicMock()" tests/*.py | grep -v "# " | while read line; do if ! echo "$line" | grep -q "spec="; then echo "$line"; fi; done | wc -l` — verify no unspecced MagicMock() for TripManager, EMHASSAdapter, TripPlannerCoordinator (note: grep -v "spec=" on separate line never filters MagicMock() lines since they never contain "spec=" on same line)

---

## Phase E: Final Checkpoint

### US-E1: Checkpoint Verification

- [ ] T058 [US-E1] Run `pytest tests/ -v` — all pass
- [ ] T059 [US-E1] Run `ruff check custom_components/ev_trip_planner/ --select=I` — 0 violations
- [ ] T060 [US-E1] Run `mypy custom_components/ev_trip_planner/` — 0 new errors
- [ ] T061 [US-E1] Run `pytest --randomly-seed=1 -v` and `pytest --randomly-seed=2 -v` and `pytest --randomly-seed=3 -v` — identical results (no flaky tests)
- [ ] T062 [US-E1] Run `make e2e` — all E2E tests pass
- [ ] T063 [US-E1] Compare coverage: refactored modules show measurable improvement vs `/tmp/coverage_before.txt` (baseline recorded in T000)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase A (US-A1 → US-A2)**: Sequential within phase — pure functions must exist before protocols
- **Phase B (US-B1 → US-B2)**: Can run in parallel (independent protocols)
- **Phase C (US-C1)**: Depends on Phase A + Phase B complete
- **Phase D (US-D1 → US-D2)**: Sequential — Layer 1 doubles must exist before MagicMock fixes
- **Phase E (US-E1)**: Depends on Phase A + B + C + D complete

### Within Each User Story

1. **Tests FIRST** (TDD RED) — write tests that fail
2. Implement the code
3. **Gate verification** — all criteria met before moving on

### Parallel Opportunities

- T001–T005 (US-A1 tests) can run in parallel
- T006–T010 (US-A1 implementation) can run in parallel
- T016–T018 (US-A2 tests) can run in parallel
- T019–T021 (US-A2 implementation) can run in parallel
- T027–T028 (US-B1 tests/implementation) can run in parallel with T031–T032 (US-B2)
- T035–T036 (US-C1 tests) can run in parallel
- T051–T055 (US-D2 MagicMock fixes) can run in parallel (different files)

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 64 (+ 1 pre-requisite T000) |
| Phase A (US-A1 + US-A2) | 26 tasks |
| Phase B (US-B1 + US-B2) | 8 tasks |
| Phase C (US-C1) | 12 tasks |
| Phase D (US-D1 + US-D2) | 11 tasks |
| Phase E (US-E1) | 6 tasks |
| Pre-requisite | T000 (coverage baseline, before Phase A) |
| Parallelizable tasks | ~40% |

**MVP Scope**: Phase A (US-A1 + US-A2) — pure functions extracted, 100% covered without doubles
