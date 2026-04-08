# Requirements: SOLID Refactor via Protocol DI

## Goal

Refactor `trip_manager.py` (~1346L) and `emhass_adapter.py` (~1536L) applying SOLID principles via Protocol Dependency Injection — without rewriting classes into new subclasses. Achieve 100% coverage as a consequence of good design, not as a direct objective.

## User Stories

### US-A1: Extract Pure Functions from TripManager
**As a** developer
**I want to** extract pure functions from TripManager to `calculations.py`/`utils.py`
**So that** they are 100% testable without any test doubles

**Acceptance Criteria:**
- [ ] AC-A1.1: `_validate_hora()` moved to `utils.py` with full unit tests
- [ ] AC-A1.2: `_sanitize_recurring_trips()` moved to `utils.py` with full unit tests
- [ ] AC-A1.3: `_is_trip_today()` moved to `utils.py` with full unit tests
- [ ] AC-A1.4: `_get_trip_time()` moved to `utils.py` with full unit tests
- [ ] AC-A1.5: `_get_day_index()` moved to `utils.py` with full unit tests
- [ ] AC-A1.6: `_calcular_tasa_carga_soc()` moved to `calculations.py` with full unit tests
- [ ] AC-A1.7: `_calcular_soc_objetivo_base()` moved to `calculations.py` with full unit tests
- [ ] AC-A1.8: `_get_charging_power()` moved to `calculations.py` with full unit tests
- [ ] AC-A1.9: TripManager imports and calls extracted functions (no logic duplication)
- [ ] AC-A1.10: All existing tests pass after extraction

### US-A2: Extract Pure Functions from EMHASSAdapter
**As a** developer
**I want to** extract pure functions from EMHASSAdapter to `calculations.py`
**So that** they are 100% testable without any test doubles

**Acceptance Criteria:**
- [ ] AC-A2.1: `calculate_deferrable_parameters()` moved to `calculations.py` with full unit tests
- [ ] AC-A2.2: `_calculate_power_profile_from_trips()` moved to `calculations.py` with full unit tests
- [ ] AC-A2.3: `_generate_schedule_from_trips()` moved to `calculations.py` with full unit tests
- [ ] AC-A2.4: EMHASSAdapter imports and calls extracted functions (no logic duplication)
- [ ] AC-A2.5: All existing tests pass after extraction

### US-B1: Define TripStorageProtocol
**As a** developer
**I want to** define `TripStorageProtocol` in `protocols.py`
**So that** TripManager can receive storage via DI without knowing the implementation

**Acceptance Criteria:**
- [ ] AC-B1.1: `TripStorageProtocol` defined with `async_load()` and `async_save()` methods
- [ ] AC-B1.2: Protocol uses `typing.Protocol` (structural subtyping, no inheritance required)
- [ ] AC-B1.3: Protocol methods have proper type signatures using `...` (ellipsis) for stubs
- [ ] AC-B1.4: Existing `YamlTripStorage` class is compatible with the protocol (no modification needed)

### US-B2: Define EMHASSPublisherProtocol
**As a** developer
**I want to** define `EMHASSPublisherProtocol` in `protocols.py`
**So that** TripManager can receive EMHASS adapter via DI without knowing the implementation

**Acceptance Criteria:**
- [ ] AC-B2.1: `EMHASSPublisherProtocol` defined with `async_publish_deferrable_load()` and `async_remove_deferrable_load()` methods
- [ ] AC-B2.2: Protocol uses `typing.Protocol` (structural subtyping, no inheritance required)
- [ ] AC-B2.3: Protocol methods have proper type signatures using `...` (ellipsis) for stubs
- [ ] AC-B2.4: Existing `EMHASSAdapter` class is compatible with the protocol (no modification needed)

### US-C1: Inject Protocols into TripManager via Constructor
**As a** developer
**I want to** TripManager accept storage and emhass via constructor with defaults
**So that** tests can inject fake implementations while production code uses real ones

**Acceptance Criteria:**
- [ ] AC-C1.1: `TripManager.__init__` accepts `storage: TripStorageProtocol` parameter (no `| None`)
- [ ] AC-C1.2: `TripManager.__init__` accepts `emhass_adapter: EMHASSPublisherProtocol` parameter (no `| None`)
- [ ] AC-C1.3: Constructor defaults to real `YamlTripStorage` and `EMHASSAdapter` instances (instance created directly, no `if None` branching)
- [ ] AC-C1.4: `set_emhass_adapter()` and `get_emhass_adapter()` remain functional for backward compatibility
- [ ] AC-C1.5: All existing tests pass with default real implementations
- [ ] AC-C1.6: `ruff check` passes with no new violations
- [ ] AC-C1.7: `mypy` passes with no new errors

### US-D1: Populate tests/__init__.py with Layer 1 Test Doubles
**As a** developer
**I want to** populate `tests/__init__.py` with TEST_*, create_mock_*(), setup_mock_*()
**So that** Layered Test Doubles Strategy is correctly implemented

**Acceptance Criteria:**
- [ ] AC-D1.1: `TEST_VEHICLE_ID`, `TEST_ENTRY_ID`, `TEST_CONFIG`, `TEST_TRIPS`, `TEST_COORDINATOR_DATA` constants defined
- [ ] AC-D1.2: `create_mock_trip_manager()` returns `MagicMock(spec=TripManager)` with async methods configured individually
- [ ] AC-D1.3: `create_mock_coordinator(hass, entry, trip_manager)` returns MagicMock with spec
- [ ] AC-D1.4: `create_mock_ev_config_entry(hass, data, entry_id)` returns MockConfigEntry
- [ ] AC-D1.5: `setup_mock_ev_config_entry(hass, config_entry, trip_manager)` includes `patch()` at HA boundary
- [ ] AC-D1.6: `FakeTripStorage` class defined for synchronous in-memory storage
- [ ] AC-D1.7: `FakeEMHASSPublisher` class defined for in-memory EMHASS publishing
- [ ] AC-D1.8: All Layer 1 doubles use `MagicMock(spec=RealClass)` for classes own to project

### US-D2: Fix MagicMock() Without Spec Violations Incrementally
**As a** developer
**I want to** fix MagicMock() without spec for own classes across test files
**So that** Layered Test Doubles Strategy is correctly applied

**Acceptance Criteria:**
- [ ] AC-D2.1: All `MagicMock()` calls for `TripManager`, `EMHASSAdapter`, `TripPlannerCoordinator` use `spec=`
- [ ] AC-D2.2: `MagicMock()` without spec is only used for HA external classes (acceptable)
- [ ] AC-D2.3: Each fix verified by running relevant test file
- [ ] AC-D2.4: No new violations introduced in files not being refactored

### US-D3: Achieve Consequent 100% Coverage
**As a** developer
**I want to** reach 100% coverage on refactored modules
**So that** coverage is a consequence of good design, not a forced target

**Acceptance Criteria:**
- [ ] AC-D3.1: trip_manager.py coverage increases measurably after phases A-C (baseline recorded before Phase A)
- [ ] AC-D3.2: emhass_adapter.py coverage increases measurably after phases A-C (baseline recorded before Phase A)
- [ ] AC-D3.3: Pure functions in `calculations.py` and `utils.py` achieve 100% coverage
- [ ] AC-D3.4: No `# pragma: no cover` added without documented reason
- [ ] AC-D3.5: All new tests follow Layered Test Doubles Strategy

### US-E1: Checkpoint Verification
**As a** developer
**I want to** verify all checkpoints pass before advancing phases
**So that** the refactor is incremental and stable

**Acceptance Criteria:**
- [ ] AC-E1.1: `pytest tests/` passes completely after each phase
- [ ] AC-E1.2: `ruff check` produces no errors
- [ ] AC-E1.3: `mypy` produces no new errors
- [ ] AC-E1.4: `pytest --randomly-seed=1` produces same result as seed=2 and seed=3 (no flaky tests)
- [ ] AC-E1.5: E2E tests via `make e2e` pass after final phase

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-A1 | Extract `_validate_hora()` to utils.py | High | Function is pure (no side effects), 100% testable without doubles |
| FR-A2 | Extract `_sanitize_recurring_trips()` to utils.py | High | Function is pure, tests pass |
| FR-A3 | Extract `_is_trip_today()` to utils.py | High | Function is pure, tests pass |
| FR-A4 | Extract `_get_trip_time()` to utils.py | High | Function is pure, tests pass |
| FR-A5 | Extract `_get_day_index()` to utils.py | High | Function is pure, tests pass |
| FR-A6 | Extract `_calcular_tasa_carga_soc()` to calculations.py | High | Function is pure, tests pass |
| FR-A7 | Extract `_calcular_soc_objetivo_base()` to calculations.py | High | Function is pure, tests pass |
| FR-A8 | Extract `_get_charging_power()` to calculations.py | High | Function is pure, tests pass |
| FR-A9 | Extract `calculate_deferrable_parameters()` to calculations.py | High | Function is pure, tests pass |
| FR-A10 | Extract `_calculate_power_profile_from_trips()` to calculations.py | Medium | Function is pure, tests pass |
| FR-A11 | Extract `_generate_schedule_from_trips()` to calculations.py | Medium | Function is pure, tests pass |
| FR-B1 | Define `TripStorageProtocol` in protocols.py | High | Uses typing.Protocol, methods have ... stubs |
| FR-B2 | Define `EMHASSPublisherProtocol` in protocols.py | High | Uses typing.Protocol, methods have ... stubs |
| FR-C1 | Inject protocols via TripManager constructor | High | Default to real impl, backward compatible |
| FR-D1 | Populate tests/__init__.py with Layer 1 doubles | High | Contains TEST_*, create_mock_*(), Fake* classes |
| FR-D2 | Fix MagicMock() without spec violations | High | spec=ClaseReal for own classes |
| FR-D3 | Pure functions 100% covered after Phase A | High | Pure funcs in calculations.py/utils.py — 100% by definition |
| FR-D4 | I/O-bound paths covered in Phase D | Medium | Coverage of I/O-bound paths deferred to Phase D when DI enables simple fakes |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Existing tests pass | Test pass rate | 100% after each phase |
| NFR-2 | Coverage after Phase A | Module coverage | Refactored modules >= 90% |
| NFR-3 | Code quality | ruff check | 0 violations |
| NFR-4 | Type checking | mypy | 0 new errors |
| NFR-5 | Test stability | pytest --randomly-seed=1/2/3 | Same result all 3 runs |
| NFR-6 | Backward compatibility | Public API unchanged | TripManager and EMHASSAdapter interface preserved |

## Glossary

- **Pure Function**: Function with no side effects — same input always produces same output, no I/O, no state mutation
- **Protocol**: Python `typing.Protocol` defining structural subtyping — classes implement implicitly by having matching methods
- **Test Double**: Generic term for fake, stub, mock, spy, fixture, patch used to replace real dependencies in tests
- **Layer 1**: Shared test doubles in `tests/__init__.py` — constants, factory functions, Fake classes
- **Layer 2**: Per-test stubs that override specific methods from Layer 1 factories
- **Layer 3**: Pytest fixtures in `conftest.py` that set up HA infrastructure (hass, store, registry). **Patches at the HA boundary go inside Capa 1 factory functions in `tests/__init__.py`, not in Capa 3 directly.**
- **MagicMock(spec=ClaseReal)**: Mock with spec set to real class — catches errors on wrong API usage
- **DIP**: Dependency Inversion Principle — high-level modules depend on abstractions, not concretions
- **YamlTripStorage**: Existing storage implementation that persists trips to YAML files
- **EMHASSPublisherProtocol**: Protocol for publishing deferrable loads to EMHASS

## Out of Scope

- Splitting TripManager or EMHASSAdapter into new subclasses (not the objective)
- Changing storage format (YAML format must remain backward compatible)
- Modifying public interface of TripManager or EMHASSAdapter
- Creating `*_coverage.py` or `*_coverage2.py` files
- Adding `# pragma: no cover` except for structurally unreachable code with documented reason
- Moving pytest fixtures from `conftest.py` to other locations

## Dependencies

- `docs/TDD_METHODOLOGY.md` — Layered Test Doubles Strategy is the source of truth for test doubles
- `doc/promptspecrfactor.md` — Original refactor specification and phase recommendations
- `custom_components/ev_trip_planner/calculations.py` — Destination for extracted pure calculation functions
- `custom_components/ev_trip_planner/utils.py` — Destination for extracted pure utility functions
- `custom_components/ev_trip_planner/trip_manager.py` — Source class for Phase A extraction
- `custom_components/ev_trip_planner/emhass_adapter.py` — Source class for Phase A extraction
- `custom_components/ev_trip_planner/services.py` — Already 100% covered (533 lines, 0 misses via test_services_core.py) — no additional work needed

## Success Criteria

- TripManager and EMHASSAdapter maintain backward compatibility (public API unchanged)
- All existing tests pass after each phase checkpoint
- 100% coverage achievable as a consequence of good design (pure functions + proper DI)
- Layered Test Doubles Strategy correctly implemented with `MagicMock(spec=ClaseReal)` for own classes
- `ruff check` and `mypy` pass with no new violations or errors
- `pytest --randomly-seed=1/2/3` produces identical results across 3 runs (no flakiness)

## Verification Contract

**Project type**: `fullstack` (Home Assistant integration with both UI panel and HTTP API calls to EMHASS)

**Entry points**:
- `custom_components/ev_trip_planner/trip_manager.py` — TripManager class
- `custom_components/ev_trip_planner/emhass_adapter.py` — EMHASSAdapter class
- `tests/test_trip_manager.py` — TripManager tests
- `tests/test_emhass_adapter.py` — EMHASSAdapter tests
- `tests/__init__.py` — Layer 1 test doubles

**Observable signals**:
- PASS looks like: `pytest tests/test_trip_manager.py tests/test_emhass_adapter.py -v` all green, `ruff check custom_components/ev_trip_planner/ --select=I` clean, `mypy custom_components/ev_trip_planner/` zero errors
- FAIL looks like: Test failures with `MagicMock` error messages like "Specification mismatch", coverage report showing uncovered lines in `trip_manager.py` or `emhass_adapter.py`

**Hard invariants**:
- TripManager's `set_emhass_adapter()` / `get_emhass_adapter()` must remain functional
- YAML storage format must remain backward compatible
- All existing service calls must continue to work

**Seed data**:
- Existing test data in `tests/` directory
- TEST_VEHICLE_ID = "coche1", TEST_ENTRY_ID = "test_entry_id_abc123"
- TEST_CONFIG, TEST_TRIPS, TEST_COORDINATOR_DATA in tests/__init__.py

**Dependency map**:
- `trip_manager.py` imports from `calculations.py`, `utils.py`, `emhass_adapter.py`
- `emhass_adapter.py` imports from `calculations.py`
- `services.py` — **100% covered** — delegates to TripManager, not a refactor target

**Escalate if**:
- Storage format needs to change to achieve refactor goals
- Public interface modification required to enable DI
- Tests reveal fundamental design issues not addressable via Protocol DI

## Unresolved Questions

All three questions resolved — no blocking open questions remain:

1. **VehicleController Protocol**: No — out of scope. No coverage gaps identified that require VehicleController DI.
2. **YAML schema migration**: No — AC-C1.3 backward compatibility already covers this. Storage format does not change.
3. **YamlStorageAdapter explicit implementation**: No — `typing.Protocol` structural compatibility means existing `YamlTripStorage` implements `TripStorageProtocol` without modification. No wrapper needed.

## Next Steps

1. Review and approve these requirements
2. Execute Phase A: Extract pure functions from trip_manager.py
3. Execute Phase A: Extract pure functions from emhass_adapter.py
4. Execute Phase B: Define protocols.py with TripStorageProtocol and EMHASSPublisherProtocol
5. Execute Phase C: Inject protocols into TripManager via constructor with defaults
6. Execute Phase D: Populate tests/__init__.py and fix MagicMock() violations
7. Run final checkpoint: ruff, mypy, pytest --randomly-seed=1/2/3, make e2e
