---
project_name: ha-ev-trip-planner
user_name: Malka
date: '2026-04-16'
sections_completed:
  - technology_stack
  - critical_implementation_rules
  - architecture_patterns
  - testing_rules
  - development_workflow
  - existing_documentation_map
existing_patterns_found: 42
---

# Project Context for AI Agents — ha-ev-trip-planner

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

### Core Runtime
- **Python**: 3.11+ (target 3.14 in mypy config)
- **Home Assistant**: >= 2024.1.0 (custom component integration)
- **Component Domain**: `ev_trip_planner` (v0.5.1)
- **Installation Type**: Home Assistant Container (NO Supervisor, NO OS)
- **HACS**: Default integration category

### Testing & Quality
- **pytest**: >= 7.4.0 with `pytest-homeassistant-custom-component` >= 0.13.0
- **pytest-cov**: >= 4.1.0
- **Coverage target**: 100% (`fail_under = 100` in pyproject.toml)
- **asyncio_mode**: `auto` (all test functions can be `async def`)
- **Test count**: 793+ Python unit tests + 10 E2E Playwright tests
- **E2E Framework**: Playwright with TypeScript

### Linting & Formatting
- **black**: >= 23.0.0 (line-length: 88)
- **ruff**: line-length 88, ignore E501
- **pylint**: >= 2.17.0 (py-version: 3.11, ignores: too-few-public-methods, too-many-instance-attributes, too-many-arguments)
- **mypy**: >= 1.5.0 (strict mode: strict_optional, disallow_any_generics, check_untyped_defs, no_implicit_reexport)
- **isort**: >= 5.12.0 (profile: black, line_length: 88)

### Frontend
- **Panel**: Custom panel via `panel_custom` (not Lovelace-dependent)
- **Frontend JS**: Vanilla JS + Lit HTML bundle (`frontend/panel.js`, `frontend/lit-bundle.js`)
- **Dashboard**: Lovelace YAML dashboards (auto-generated)

---

## Critical Implementation Rules

### Rule 0: Implementation is Source of Truth

> **The codebase is the authoritative source. Documentation may be outdated, contradictory, or aspirational.**

- When documentation conflicts with code, **trust the code**
- Specs in `specs/` may describe intended behavior that was never implemented or was changed during implementation
- `ROADMAP.md`, `README.md`, and `docs/` may contain stale information — verify against actual code
- Use file modification dates to resolve contradictions — most recent wins
- `tasks.md` in each spec folder is the implementation order source of truth
- If a spec says X but the code does Y, the code is correct unless explicitly flagged as a bug
- ALWAYS verify claims against the actual codebase before making changes
- This project is in a documentation-unstable state — documentation migration to BMad is in progress

### Rule 1: Home Assistant Container — No Supervisor

> This project runs on **Home Assistant Container**. There is NO Supervisor, NO Add-on Store, NO `hassio` API.

- NEVER assume `supervisor` is available
- NEVER use `homeassistant.helpers.storage` with `hass.helpers.storage` — use `homeassistant.helpers.storage` directly
- Shell commands require manual setup (documented in `docs/SHELL_COMMAND_SETUP.md`)
- Lovelace storage mode may NOT be available — use YAML dashboards or `panel_custom`
- `config_entries` flow works normally but there is no backup/restore via Supervisor

### Rule 2: Entity Identity — Prevent Duplicate Sensors

> Gap G-01 from CODEGUIDELINESia.md: Sensors MUST have stable, unique `unique_id` to prevent duplicates on reinstall.

- ALWAYS set `_attr_unique_id = f"{vehicle_id}_{description.key}"` in sensor constructors
- NEVER create sensors without `unique_id` — they will duplicate on reinstall
- Use `entry.entry_id` or `vehicle_id` as prefix for all entity unique IDs
- EMHASS sensor format: `emhass_trip_{vehicle_id}_{trip_id}`

### Rule 3: SensorEntityDescription Pattern — definitions.py

> Gap G-07: Use ONE base class + definitions file, NOT separate classes per sensor.

- ALL sensor definitions go in `definitions.py` as `TripSensorEntityDescription` instances
- `TripSensorEntityDescription` extends `SensorEntityDescription` with: `value_fn`, `attrs_fn`, `restore`, `exists_fn`
- Sensors are defined as DATA in `TRIP_SENSORS` tuple, not as separate classes
- `sensor.py` has ONE `TripSensor` class that handles all sensor types via `entity_description`
- NEVER create a new Sensor class for a new sensor — add a `TripSensorEntityDescription` entry instead

### Rule 4: Runtime Data — entry.runtime_data with @dataclass

> Gap G-05: Use `entry.runtime_data` with typed dataclass, NOT `hass.data[DOMAIN]`.

- `EVTripRuntimeData` dataclass in `__init__.py` holds: `coordinator`, `trip_manager`, `emhass_adapter`, etc.
- Set in `async_setup_entry`: `entry.runtime_data = EVTripRuntimeData(...)`
- Access via `entry.runtime_data` in all platforms (sensor, services, etc.)
- TypeAlias: `CoordinatorType = DataUpdateCoordinator[dict[str, Any]]`
- NEVER use `hass.data[DOMAIN][entry.entry_id]` for runtime data — use `entry.runtime_data`

### Rule 5: Protocol Dependency Injection

> SOLID refactor (April 2026): Use `typing.Protocol` for DI, not inheritance.

- `protocols.py` defines: `TripStorageProtocol`, `EMHASSPublisherProtocol`
- Both use `@runtime_checkable` decorator
- `TripManager.__init__` accepts `storage: TripStorageProtocol` and `emhass_adapter: EMHASSPublisherProtocol`
- Constructor defaults to real implementations (no `if None` branching)
- `set_emhass_adapter()` / `get_emhass_adapter()` remain for backward compatibility
- Tests inject fakes via constructor parameters

### Rule 6: Pure Functions in calculations.py and utils.py

> SOLID refactor: Extract pure functions from TripManager and EMHASSAdapter.

- `calculations.py`: `_calcular_tasa_carga_soc()`, `_calcular_soc_objetivo_base()`, `_get_charging_power()`, `calculate_deferrable_parameters()`, `_calculate_power_profile_from_trips()`, `_generate_schedule_from_trips()`, `calculate_multi_trip_charging_windows()`
- `utils.py`: `_validate_hora()`, `_sanitize_recurring_trips()`, `_is_trip_today()`, `_get_trip_time()`, `_get_day_index()`
- Pure functions are 100% testable without test doubles
- TripManager/EMHASSAdapter import and call extracted functions

### Rule 7: RestoreEntity for Sensor Persistence

> Gap G-08: Sensors MUST restore state after HA restart.

- Set `restore=True` in `TripSensorEntityDescription` for sensors that need persistence
- Sensors with `restore=True`: `kwh_needed_today`, `hours_needed_today`, `next_trip`, `next_deadline`
- Implement `async_get_last_sensor_data` if using custom restore logic
- NEVER rely solely on coordinator refresh for initial state — restore first

### Rule 8: Config Entry Lifecycle

> Gap G-04: Complete lifecycle management prevents zombie sensors.

- `async_setup_entry`: Create coordinator, trip_manager, emhass_adapter, register services, forward setups, register panel
- `async_unload_entry`: Unload platforms, unregister panel (remove `if unload_ok:` guard — always unregister)
- `async_migrate_entry`: Handle version migrations (CONFIG_VERSION = 2)
- `async_remove_entry`: Cleanup orphaned EMHASS sensors from both state machine AND entity registry
- ALWAYS call `async_unregister_panel()` regardless of platform unload status

### Rule 9: EMHASS Integration Architecture

> Gap G-08 from ROADMAP: Per-trip EMHASS sensors, NOT aggregated.

- `EMHASSAdapter` manages index pool (0-49) with soft delete and cooldown
- Each active trip gets a `TripEmhassSensor` with full EMHASS parameters
- Aggregated sensor `sensor.emhass_perfil_diferible_{vehicle_id}` exposes `p_deferrable_matrix` as `list[list[float]]`
- Matrix rows are 168-element per-trip power profiles ordered by `emhass_index`
- `number_of_deferrable_loads` attribute = number of active trips in matrix
- Charging power updates MUST trigger republish (Gap #5 fix)
- Sequential trips: `def_start_timestep_array[i]` must account for previous trip completion + RETURN_BUFFER_HOURS (4h)

### Rule 10: TDD is MANDATORY

> From docs/TDD_METHODOLOGY.md: RED → GREEN → REFACTOR cycle is NON-NEGOTIABLE.

1. **RED**: Write failing test first
2. **GREEN**: Write minimum code to pass
3. **REFACTOR**: Improve while keeping tests green
4. **Commit**: Atomic commit with test + implementation together
- Test files: `tests/test_{module}.py`
- Test functions: `async def test_{scenario}_{condition}()`
- Shared test doubles: `tests/__init__.py` (NOT conftest.py)
- Coverage must remain at 100% — no regressions allowed

### Rule 11: Config Flow Structure

- 4-step config flow (simplified from original 5):
  1. User: vehicle name, SOC sensor, battery capacity
  2. Sensors: range sensor, charging status, consumption
  3. EMHASS: planning horizon, max deferrable loads, control type
  4. Presence & Notifications: home/plugged sensors, notification config
- Entity filters: SOC → % sensors, Plugged → binary_sensor
- Translations: `strings.json` + `translations/en.json`, `translations/es.json`
- ALWAYS use `entry.options` with `entry.data` fallback for config values

### Rule 12: Charging Window Calculation

- `calculate_multi_trip_charging_windows()`: Batch process ALL trips, not one-by-one
- `RETURN_BUFFER_HOURS = 4.0`: Fixed gap between trip end and next charging window start
- `def_start_timestep[i]` for i > 0 uses batch-computed `inicio_ventana`
- Single trip: `def_start_timestep = 0` (unchanged)
- `def_end_timestep_array` values must NOT change after fix
- `p_deferrable_matrix` values must NOT change (already correct)

---

## Architecture Patterns

### Module Responsibilities

| Module | Responsibility | Lines |
|--------|---------------|-------|
| `__init__.py` | Entry point, runtime data, setup/unload | ~163 |
| `const.py` | Constants, config keys, defaults, enums | ~96 |
| `definitions.py` | SensorEntityDescription definitions | ~86 |
| `protocols.py` | Protocol interfaces for DI | ~27 |
| `calculations.py` | Pure calculation functions | extracted |
| `utils.py` | Pure utility functions | extracted |
| `coordinator.py` | DataUpdateCoordinator | ~refactored |
| `trip_manager.py` | Core business logic, CRUD, EMHASS publishing | ~1346 |
| `emhass_adapter.py` | EMHASS API, index management, deferrable loads | ~1536 |
| `sensor.py` | Sensor entities (TripSensor + EMHASS sensors) | varies |
| `config_flow.py` | Config flow with 4 steps | varies |
| `services.py` | HA service registration | varies |
| `panel.py` | Native panel registration/unregistration | varies |
| `dashboard.py` | Lovelace dashboard CRUD | varies |
| `vehicle_controller.py` | 4 charging control strategies | varies |
| `presence_monitor.py` | Vehicle presence detection | varies |
| `schedule_monitor.py` | EMHASS schedule monitoring | varies |
| `yaml_trip_storage.py` | YAML-based trip persistence | varies |
| `diagnostics.py` | HA diagnostics for debugging | varies |

### Data Flow

```
Config Entry → Coordinator → TripManager → EMHASSAdapter
                    ↓              ↓              ↓
              Sensor Update   Trip CRUD    Deferrable Load Publish
                    ↓              ↓              ↓
              HA State Machine  YAML Storage  EMHASS API
```

### Key Design Decisions

1. **Protocol DI over inheritance**: `typing.Protocol` for loose coupling
2. **Dataclass runtime data**: `entry.runtime_data` over `hass.data`
3. **SensorEntityDescription**: Data-driven sensors over class-per-sensor
4. **Pure functions**: Extracted to `calculations.py` / `utils.py` for testability
5. **Panel Custom**: Native sidebar panel over Lovelace-only dashboard
6. **YAML storage**: Trip data stored in YAML files under HA config dir
7. **Soft delete with cooldown**: EMHASS indices have 24h cooldown before reuse

---

## Testing Rules

### Test Structure
- **Unit tests**: `tests/test_{module}.py` — test pure functions and isolated logic
- **Integration tests**: Tests involving HA framework (coordinator, config entry setup)
- **E2E tests**: `tests/e2e/*.spec.ts` — Playwright tests against running HA instance

### Test Conventions
- File naming: `test_{module}.py`
- Function naming: `async def test_{scenario}_{condition}()`
- Fixtures: `@pytest.fixture` in `conftest.py`
- Shared test doubles: `tests/__init__.py` with `TEST_*` constants, `create_mock_*()`, `setup_mock_*()`
- Coverage: 100% required (`fail_under = 100`)

### Test Execution
```bash
# Unit tests
pytest tests/ -v --cov=custom_components/ev_trip_planner

# E2E tests
npx playwright test

# Specific test
pytest tests/test_calculations.py -v
```

### E2E Test Infrastructure
- Playwright with TypeScript
- Tests: create-trip, delete-trip, edit-trip, form-validation, trip-list-view, emhass-sensor-updates, panel-emhass-sensor-entity-id
- Helpers: `tests/e2e/trips-helpers.ts`

---

## Development Workflow

### Branch Strategy
- Feature branches: `feat/{feature-name}` or `specs/{NNN}-{feature-name}`
- Main branch: `main`
- Current active: `feat/fix-sequential-trip-charging`

### Commit Convention
- Format: `feat: [description] - TDD cycle complete`
- Atomic commits: test + implementation together

### Priority Resolution
- `tasks.md` is the source of truth for implementation order
- `CODEGUIDELINESia.md` is architectural reference
- If conflict: apply `tasks.md` but verify no CODEGUIDELINES requirement is lost
- Use file dates to resolve contradictions — most recent wins

### Documentation Sources (Priority Order)
1. `ROADMAP.md` — Project milestones and current status
2. `docs/CODEGUIDELINESia.md` — Architecture rules and gaps
3. `docs/TDD_METHODOLOGY.md` — Testing methodology
4. `specs/` — Feature specifications (Smart Ralph/Speckit)
5. `docs/` — General documentation

---

## Existing Documentation Map

### Specs (Smart Ralph / Speckit) — 30+ Feature Specs

Located in `specs/` directory. Each spec may contain: `spec.md`, `requirements.md`, `design.md`, `research.md`, `plan.md`, `tasks.md`, `chat.md`.

**Completed Milestones:**
- `001-milestone-3-2-complete/` — EMHASS Integration & Vehicle Control (M3.1 + M3.2)
- `007-complete-milestone-3-verify-1-2/` — Production Validation M3 + M1-M2 Compatibility

**Bug Fixes & Enhancements:**
- `008-fix-config-flow-dashboard-sensors/` — Config Flow & Dashboard Sensor Fixes
- `009-fix-vehicle-creation-dashboard-notifications/` — Vehicle Creation & Notification Fixes
- `010-fix-sensor-errors-dashboard-issues/` — Sensor Errors & Dashboard Issues
- `011-fix-production-errors/` — Production Error Fixes
- `012-dashboard-crud-verify/` — Dashboard CRUD Verification
- `013-fix-emhass-attribute-size/` — EMHASS Attribute Size Fix
- `020-fix-panel-trips-sensors/` — Panel Trips & Sensors Fix

**Feature Development:**
- `017-native-panel-core/` — Native Panel via panel_custom
- `trip-creation/` — Trip CRUD in Panel
- `trip-card-enhancement/` — Trip Card UI Improvements
- `automation-template/` — Automation Template for Charging Control

**EMHASS Integration:**
- `emhass-sensor-enhancement/` — EMHASS Sensor Improvements
- `emhass-sensor-entity-lifecycle/` — EMHASS Sensor Entity Lifecycle Fix
- `emhass-integration-with-fixes/` — EMHASS Integration with Fixes
- `fix-emhass-aggregated-sensor/` — Aggregated EMHASS Sensor Fix
- `fix-emhass-sensor-attributes/` — EMHASS Sensor Attributes Fix
- `fix-sequential-trip-charging/` — Sequential Trip Charging Window Fix
- `m401-emhass-hotfixes/` — M4.0.1 EMHASS Critical Hotfixes
- `duplicate-emhass-sensor-fix/` — Duplicate EMHASS Sensor Fix

**Architecture:**
- `solid-refactor-coverage/` — SOLID Refactor via Protocol DI
- `soc-integration-baseline/` — SOC Integration Baseline
- `soc-milestone-algorithm/` — SOC Milestone Algorithm
- `charging-window-calculation/` — Charging Window Calculation
- `regression-orphaned-sensors-ha-core-investigation/` — Orphaned Sensors Investigation

**Epic:**
- `specs/_epics/emhass-deferrable-integration/` — Epic with dependency graph of 7 specs

### Documentation Files (docs/)
- `CODEGUIDELINESia.md` — 12 critical gaps, architecture rules (593 lines)
- `TDD_METHODOLOGY.md` — Mandatory TDD methodology (531 lines)
- `RALPH_METHODOLOGY.md` — Smart Ralph development methodology (264 lines)
- `SPECKIT_SDD_FLOW_INTEGRATION_MAP.md` — Speckit SDD flow integration (419 lines)
- `COMPLETE_USER_JOURNEY_BDD.md` — BDD approach for HA testing (365 lines)
- `TESTING_E2E.md` — E2E testing guide
- `DASHBOARD.md` — Dashboard documentation
- `emhass-setup.md` — EMHASS setup guide
- `VEHICLE_CONTROL.md` — Vehicle control strategies
- `IMPLEMENTATION_REVIEW.md` — Implementation review
- `MILESTONE_4_POWER_PROFILE.md` — M4 power profile spec
- `MILESTONE_4_1_PLANNING.md` — M4.1 planning
- `SHELL_COMMAND_SETUP.md` — Shell command setup for Container installs
- `configuration_examples.yaml` — Configuration examples

### Key Project Files
- `ROADMAP.md` — Milestones, current status, next steps (325 lines)
- `CLAUDE.md` — Claude Code instructions (references CODEGUIDELINESia.md)
- `README.md` — User-facing documentation (549 lines)
- `CHANGELOG.md` — Version history
- `docker-compose.yml` — HA Container setup
- `Dockerfile.custom` — Custom HA Docker image

---

## Project Milestones Status

| Milestone | Status | Tests | Key Deliverable |
|-----------|--------|-------|-----------------|
| M0: Foundation | ✅ Complete | — | Repo skeleton, HACS metadata |
| M1: Core Infrastructure | ✅ Complete | 29 | Trip CRUD, 3 sensors, dashboard |
| M2: Trip Calculations | ✅ Complete | 60 | 7 sensors, timezone handling |
| M3: EMHASS Integration | ✅ Complete | 156 | EMHASS adapter, vehicle control, presence |
| M3.1: UX Improvements | ✅ Complete | — | Config flow UX, translations |
| M3.2: Advanced Options | ✅ Complete | — | Dynamic battery, consumption profiles |
| M4: Smart Charging | ✅ Complete | 398 | Power profile, SOC-aware, 168h planning |
| SOLID Refactor | ✅ Complete | 793+ | Protocol DI, definitions.py, pure functions |
| M4.0.1: Hotfixes | 📋 Planned | — | Per-trip EMHASS sensors, power update fix |
| M4.1: Enhancements | 📋 Planned | — | Distributed charging, multi-vehicle, weather |

---

## Glossary

- **EMHASS**: Energy Management and Optimization of Home Energy Storage Systems
- **SOC**: State of Charge — battery percentage
- **SOH**: State of Health — battery degradation factor
- **Deferrable Load**: A load that can be shifted in time by the optimizer (EMHASS)
- **p_deferrable_matrix**: 2D array of per-trip power profiles (168 hours × N trips)
- **def_start_timestep**: Zero-based timestep when charging can begin
- **def_end_timestep**: Zero-based timestep when charging must complete
- **RETURN_BUFFER_HOURS**: Fixed 4h gap between trip end and next charging window
- **hora_regreso**: Actual return time (dynamic, from presence_monitor)
- **Soft delete**: EMHASS index marked as deleted but not reusable for 24h cooldown
- **panel_custom**: HA core component for native sidebar panels
- **TripStorageProtocol**: Protocol interface for trip data persistence
- **EMHASSPublisherProtocol**: Protocol interface for EMHASS publishing
