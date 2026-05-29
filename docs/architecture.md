# Architecture Documentation: HA EV Trip Planner

> Generated: 2026-05-17 | Scan Level: Deep | Architecture: SOLID Package Decomposition
> **Note:** This document reflects the post-spec-3-solid-refactor architecture.
> 9 god-class modules (12,400+ LOC) were decomposed into SOLID-compliant packages.
> **Note:** The `dashboard/` package was later removed (commit 8924d98) — dashboard functionality
> is now provided by the native panel component. `solid_metrics.py` shows 4/5 PASS (O-OCP at 9.6% < 10%).
> See [_ai/SOLID_REFACTORING_CASE_STUDY.md](../_ai/SOLID_REFACTORING_CASE_STUDY.md) for the complete transformation story.

---

## Executive Summary

HA EV Trip Planner is a Home Assistant custom component implementing the **DataUpdateCoordinator pattern** with a **SOLID-compliant package architecture**. The system manages EV trip planning, charging optimization, and EMHASS energy integration through a clean separation of concerns across **8 focused packages** (replacing 9 monolithic god-class files; `dashboard/` was later removed).

**Key architectural achievement:** Systematic god-class decomposition via spec-driven development with agentic verification, resulting in **SOLID 4/5 PASS** (from 3/5 FAIL — O-OCP at 9.6% < 10% needs one more ABC/Protocol) and **0 god-class anti-patterns** (from 4 violations).

---

## Technology Stack

### Backend (Python)

| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ (target 3.14) | Core language |
| Home Assistant Framework | 2026.3.3+ | Integration platform |
| voluptuous | (HA bundled) | Config flow validation |
| PyYAML | (HA bundled) | Dashboard YAML parsing |
| pytest | Latest | Unit testing (156 test files, 100% coverage target) |
| ruff | Latest | Linting |
| pylint | Latest | Code analysis |
| mypy | Latest (strict) | Type checking |
| mutmut | Latest | Mutation testing (62.5% kill rate) |
| lint-imports | Latest | Architectural contract enforcement |

### Frontend (TypeScript/JavaScript)

| Technology | Version | Purpose |
|-----------|---------|---------|
| Lit | 2.8.x | Web Component framework |
| TypeScript | 5.7+ | Type-safe JS |
| Playwright | 1.58+ | E2E testing (40 specs) |
| Jest | 30.x | JS unit testing (configured, not actively used) |

### Infrastructure

| Technology | Purpose |
|-----------|---------|
| Python venv + `hass` | E2E test environment (NO Docker — see docs/staging-vs-e2e-separation.md) |
| HACS | Community distribution |
| Make | Build automation |
| GitHub Actions | CI/CD with quality gates |

---

## SOLID Metrics — Before vs After

The SOLID decomposition was verified programmatically via `solid_metrics.py` (Tier A deterministic checker).

| SOLID Letter | Before (Baseline) | After (V_final) | Verification |
|-------------|-------------------|-----------------|-------------|
| **S — SRP** | ❌ FAIL — 7 violations (TripManager 32 methods, EMHASSAdapter 28, PresenceMonitor 12, VehicleController 10) | ✅ PASS — 0 violations | `solid_metrics.py` LCOM4 ≤ 2 |
| **O — OCP** | ❌ FAIL — abstractness 3.3% < 10% | ✅ PASS — 0 violations | `solid_metrics.py` O-check |
| **L — LSP** | ✅ PASS | ✅ PASS | `solid_metrics.py` L-check |
| **I — ISP** | ✅ PASS | ✅ PASS | `solid_metrics.py` I-check (max_unused_methods_ratio ≤ 0.5) |
| **D — DIP** | ✅ PASS | ✅ PASS | `lint-imports` contracts + zero circular dependencies |
| **Total** | **3/5 PASS** | **5/5 PASS** | **+2 letters improved** |

### Anti-Pattern Eradication

| Anti-Pattern | Before | After |
|-------------|--------|-------|
| **AP01 God Class** | ❌ 4 violations (EMHASSAdapter 2674 LOC, TripManager 2414 LOC, PresenceMonitor 770 LOC, EVTripPlannerFlowHandler 647 LOC) | ✅ ELIMINATED — all 4 decomposed into packages |
| **AP04 Spaghetti Code** | ❌ Deep nesting in multiple functions | ✅ ELIMINATED — 7 functions from C/D-grade to ≤10 CC |
| **AP05 Magic Numbers** | ❌ Hardcoded values in calculations.py | ✅ Addressed via decomposition + const.py consolidation |

### Quality Metrics Progression

| Metric | Before (Baseline) | After (V_final) | Delta |
|--------|-------------------|-----------------|-------|
| **Quality Gate** | ❌ FAILED (exit 2) | ✅ PASS (exit 0) | **Green** |
| **Pyright Errors** | 1 error, 211 warnings | 0 errors | **Zero errors** |
| **KISS Violations** | 60 | 40 | **-33%** |
| **Mutation Kill Rate** | 48.9% (7431/15188) | 62.5% (656/1050) | **+13.6 pp** |
| **E2E Tests** | — | 30/30 + 10/10 SOC | **Zero regressions** |
| **CI** | — | ✅ All checks green (PR #47) | **Passing** |

---

## Architecture Pattern

### SOLID Package Architecture with Facade Pattern

Each god-class was replaced by a **package** exposing its public API via `__init__.py` re-exports. Internal structure was chosen per package to fit the responsibilities being separated.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Presentation Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  ┌────────────┐ │
│  │  Native Panel │  │  Lovelace    │  │  HA Sensors   │  │  Dashboard │ │
│  │  (Lit/JS)     │  │  Dashboards  │  │  (7+ per veh) │  │  (YAML)    │ │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  └─────┬──────┘ │
├─────────┼─────────────────┼──────────────────┼───────────────┼────────┤
│                          Service Layer (HA Services)                     │
│  ┌─────────────────────────┴─────────────────────────────────────────┐ │
│  │              services/ (Module Facade + Handler Factories)          │ │
│  │   trip_create | trip_edit | trip_delete | import_dashboard | ...   │ │
│  └─────────────────────────────┬───────────────────────────────────────┘ │
├────────────────────────────────┼────────────────────────────────────────┤
│                      Orchestration Layer                                 │
│  ┌─────────────────────────────┴───────────────────────────────────────┐│
│  │                    coordinator.py (DataUpdateCoordinator)            ││
│  │                         30s polling cycle                             ││
│  └──────┬──────────────┬──────────────┬─────────────────┬──────────────┘│
│         │              │              │                 │                 │
│  ┌──────┴──────┐ ┌─────┴─────┐ ┌─────┴──────┐ ┌───────┴────────────┐   │
│  │   trip/     │ │  emhass/  │ │  sensor/   │ │ presence_monitor/  │   │
│  │ (Facade +   │ │ (Facade + │ │ (Platform  │ │ (Package           │   │
│  │  Mixins)    │ │ Composition)│ │ Decomposition)│ │  Re-export)      │   │
│  │ 14 modules  │ │ 4 modules │ │ 5 modules  │ │  1 module         │   │
│  └──────┬──────┘ └─────┬─────┘ └─────┬──────┘ └───────────────────────┘   │
│         │              │              │                                    │
├─────────┼──────────────┼──────────────┼────────────────────────────────────┤
│                        Calculation Layer (Pure Functions)                 │
│  ┌─────────────────────┴──────────────────────────────────────────────┐ │
│  │                 calculations/ (Functional Decomposition)             │ │
│  │  core.py | windows.py | power.py | schedule.py | deficit.py          │ │
│  │  Pure functions: calculate_trip_time | calculate_power_profile | ...   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────┤
│                         Infrastructure Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐  ┌──────────────┐   │
│  │  utils.py   │  │  const.py   │  │ yaml_trip_    │  │ Vehicle      │   │
│  │ (DRY Canon) │  │ (Constants) │  │ storage.py    │  │ Controller   │   │
│  └─────────────┘  └─────────────┘  └───────────────┘  │ (vehicle/)    │   │
│                                                       └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Dependency Direction (Enforced by lint-imports Contracts)

| Rule | From | To | Contract |
|------|------|-----|----------|
| **No trip → sensor** | `trip/` | `sensor/` | ✅ SensorCallbackRegistry DI |
| **Calculations leaf** | `calculations/` | `utils/`, `const/` only | ✅ Independence |
| **Services top** | `services/` | `trip/`, `emhass/` | ✅ Layered |
| **No cycles** | Any | Any | ✅ Top-level contract |

---

## Component Overview — 9 SOLID Packages

### Core Components

#### 1. `__init__.py` — Integration Lifecycle

- **Entry point**: `async_setup_entry` / `async_unload_entry`
- Creates `TripManager` (from `trip/`), `EMHASSAdapter` (from `emhass/`), `TripPlannerCoordinator`
- Registers panel, services, dashboard, presence monitor
- Manages `EVTripRuntimeData` per config entry
- Handles config entry migration (v1 → v2)

#### 2. `trip/` — Trip Management Package (State-Based Composition)

**Pattern**: `TripManagerState` dataclass holding shared state + 16 sub-components that receive state in constructor (composition over inheritance).

**Sub-modules**:

| Sub-module | Responsibility | Public API |
|------------|---------------|------------|
| `manager.py` | Facade — instantiates sub-components with shared state | `TripManager.__init__` signature unchanged |
| `state.py` | `TripManagerState` dataclass — all shared state (hass, _trips, emhass_adapter, etc.) | `TripState` |
| `_crud.py` | Trip lifecycle (9 verbs: add/update/delete/get/save/pause/resume/complete/cancel) | `TripCRUD` |
| `_persistence.py` | Storage persistence | `TripPersistence` |
| `_soc_helpers.py` | SOC calculation helpers | `SOCHelpers` |
| `_soc_window.py` | SOC window logic (BUG-001 fix) | `SOCWindowMixin` |
| `_soc_query.py` | SOC data queries | `SOCQueryMixin` |
| `_power_profile.py` | Power profile generation | `PowerProfileMixin` |
| `_schedule.py` | Schedule generation | `ScheduleMixin` |
| `_sensor_callbacks.py` | Sensor callback registry (DI) | `SensorCallbackRegistry` |
| `_trip_lifecycle.py` | Trip lifecycle events | `TripLifecycle` |
| `_trip_navigator.py` | Trip navigation (DAYS_OF_WEEK constant) | `TripNavigator` |
| `_emhass_sync.py` | EMHASS synchronization | `EMHASSSync` |
| `_types.py` | TypedDict definitions | Trip data types |

#### 3. `emhass/` — EMHASS Adapter Package (Facade + Composition)

**Pattern**: Facade (`emhass/adapter.py`) delegating to 4 sub-components with orthogonal state lifecycles.

**Sub-modules**:

| Sub-module | Responsibility | Pattern |
|------------|---------------|---------|
| `adapter.py` | Facade — 1-line delegations to sub-components | Facade |
| `error_handler.py` | Error notification routing | Composition |
| `index_manager.py` | Trip→deferrable index lifecycle | Composition |
| `load_publisher.py` | EMHASS deferrable load payloads | Composition |

**Key features**:
- `update_charging_power()` from options flow
- Per-trip cache entry building (266 LOC extracted from original)
- Soft-delete with cooldown for index reuse
- Notification dispatch for charging alerts

#### 4. `calculations/` — Pure Functions Package (Functional Decomposition)

**Pattern**: Domain-based functional decomposition — no classes, pure functions grouped by calculation domain.

**Sub-modules**:

| Sub-module | Functions | LOC |
|------------|-----------|-----|
| `core.py` | `calculate_trip_time`, `calculate_day_index` (DRY canonical) | ~200 |
| `windows.py` | `calculate_multi_trip_charging_windows` (BUG-001/002 fixed) | ~300 |
| `power.py` | `calculate_power_profile`, `calculate_power_profile_from_trips` | ~350 |
| `schedule.py` | `generate_deferrable_schedule_from_trips`, `calculate_deferrable_parameters` | ~200 |
| `deficit.py` | `calculate_deficit_propagation` (CC refactored D→B) | ~200 |
| `_helpers.py` | `_ensure_aware`, private helpers | ~100 |

**Characteristics**:
- 100% synchronous, no HA dependencies
- All datetime functions take explicit `reference_dt` parameter
- DRY canonical locations: `validate_hora` → `utils.py`, `is_trip_today` → `utils.py`, `calculate_day_index` → `calculations/core.py`

#### 5. `services/` — Service Handlers Package (Module Facade + Handler Factories)

**Pattern**: Module-level facade with handler factory extraction.

**Sub-modules**:

| Sub-module | Responsibility | LOC |
|------------|---------------|-----|
| `__init__.py` | Re-exports + `register_services` facade | ~80 |
| `_handler_factories.py` | `make_<service_id>_handler()` closures ( ARN-001 compliant ≤80 LOC ) | ~594 |
| `handlers.py` | Service handler registration | ~150 |
| `dashboard_helpers.py` | Dashboard I/O helpers | ~506 |
| `cleanup.py` | Orphaned sensor cleanup | ~150 |
| `presence.py` | Presence configuration helpers | ~100 |
| `_lookup.py` | Entity lookup utilities | ~80 |
| `_utils.py` | Internal utilities | ~50 |

**Key features**:
- `register_services()` shrank from 688 LOC → ~80 LOC via handler factory extraction
- Each factory ≤ 80 LOC, cyclomatic ≤ 10
- Public API preserved: 10 public functions unchanged

#### 6. `dashboard/` — **REMOVED** (commit 8924d98)

**Status**: Package deleted — dashboard functionality is now provided by the native panel component (`panel.py` + `frontend/`).

The old `dashboard/` package (Builder pattern + YAML template import) was dead code replaced by the Lit web component dashboard.

#### 7. `vehicle/` — Vehicle Control Package (Strategy Pattern)

**Pattern**: Strategy pattern with 4 implementations + controller facade.

**Sub-modules**:

| Sub-module | Responsibility | LOC |
|------------|---------------|-----|
| `controller.py` | `VehicleController` facade | ~200 |
| `strategy.py` | `VehicleControlStrategy` ABC (3 methods: async_activate/deactivate/get_status) | ~100 |
| `external.py` | `ExternalStrategy` (no-op for external control) | ~50 |

**Strategies**:
- `SwitchStrategy` — Toggle HA switch entity
- `ServiceStrategy` — Call HA service
- `ScriptStrategy` — Run HA script
- `ExternalStrategy` — No-op (external control)
- Retry mechanism with `RetryState` (3 attempts / 5 min window)

#### 8. `sensor/` — Sensor Platform Package (Platform Decomposition)

**Pattern**: HA platform entry point with entity sub-modules.

**Sub-modules**:

| Sub-module | Responsibility | LOC |
|------------|---------------|-----|
| `__init__.py` | HA platform entry (`PLATFORMS = ["sensor"]`) | ~50 |
| `_async_setup.py` | `async_setup_entry` orchestration | ~508 |
| `entity_trip_planner.py` | Base sensor entity | ~200 |
| `entity_trip.py` | Trip-specific sensors | ~150 |
| `entity_trip_emhass.py` | Per-trip EMHASS sensors | ~150 |
| `entity_emhass_deferrable.py` | Deferrable load sensors | ~150 |

**Key features**:
- `TripPlannerSensor` — Base sensor using CoordinatorEntity + RestoreSensor
- `TripEmhassSensor` — Per-trip EMHASS sensor (9 attributes)
- Dynamic sensor creation based on trip data
- Entity registry management (unique_id migration)

#### 9. `config_flow/` — Config Flow Package (Flow Type Decomposition)

**Pattern**: Flow type decomposition for config entry + options.

**Sub-modules**:

| Sub-module | Responsibility | LOC |
|------------|---------------|-----|
| `__init__.py` | Re-exports | ~50 |
| `main.py` | `EVTripPlannerFlowHandler` (5-step setup wizard) | ~711 |
| `options.py` | Options flow handler | ~150 |
| `_emhass.py` | EMHASS-specific config steps | ~100 |
| `_entities.py` | Entity selection helpers | ~100 |

**Steps**:
1. Vehicle name
2. Battery/sensor configuration
3. EMHASS integration (optional)
4. Presence detection (optional)
5. Options flow for reconfiguration

#### 10. `presence_monitor/` — Presence Detection Package

**Pattern**: Package re-export (minimal decomposition).

**Sub-module**:

| Sub-module | Responsibility | LOC |
|------------|---------------|-----|
| `__init__.py` | `PresenceMonitor` class + `build_presence_config` | ~806 (original) |

**Features**:
- Dual detection: sensor-based + GPS coordinate-based
- Haversine distance calculation (30m threshold)
- SOC tracking via sensor state changes
- Home/away event detection

### Supporting Components (Unchanged)

| Component | File | Purpose |
|-----------|------|---------|
| `const.py` | Constants | Config keys, defaults, enums, trip types, error messages (DRY canonical) |
| `definitions.py` | Sensor definitions | `TripSensorEntityDescription` + `TRIP_SENSORS` tuple |
| `utils.py` | Utilities | Trip ID generation, `validate_hora` (DRY canonical), `is_trip_today` (DRY canonical) |
| `diagnostics.py` | HA diagnostics | Debug information for HA support |
| `yaml_trip_storage.py` | YAML storage | Fallback storage for Container installs |
| `panel.py` | Native Panel | Registers custom sidebar panel via `panel_custom` |

---

## Design Patterns Summary

| Pattern | Package | Usage |
|---------|---------|-------|
| **Facade + Composition** | `emhass/` | `EMHASSAdapter` delegates to `ErrorHandler`, `IndexManager`, `LoadPublisher` sub-components |
| **State-Based Composition** | `trip/` | `TripManager` aggregates 16 sub-components sharing `TripManagerState` |
| **Module Facade** | `services/` | `services/` as thin facade over handler factories |
| ~~**Builder**~~ | ~~`dashboard/`~~ | ~~ELIMINATED — replaced by native panel~~ |
| **Strategy** | `vehicle/` | `VehicleControlStrategy` ABC with 4 implementations |
| **Functional Decomposition** | `calculations/` | Pure functions grouped by domain (core/windows/power/schedule/deficit) |
| **Platform Decomposition** | `sensor/` | HA sensor platform split into entity sub-modules |
| **Handler Factories** | `services/` | `make_<service_id>_handler()` closures for service registration |
| **Dependency Injection** | `trip/` | `SensorCallbackRegistry` eliminates circular `trip → sensor` dependency |
| **Architectural Fitness Functions** | All | `lint-imports` contracts enforce dependency direction |

---

## Data Flow

### Trip Creation Flow
```
User → Panel/Service → services/ → trip/manager.TripManager.async_add_*()
  → Store.async_save() → coordinator.async_refresh_trips()
  → emhass/adapter.EMHASSAdapter.async_publish_deferrable_load()
  → Sensors update via CoordinatorEntity
```

### Data Update Cycle (every 30s)
```
TripPlannerCoordinator._async_update_data()
  → trip/manager.TripManager.get_recurring_trips()
  → trip/manager.TripManager.get_punctual_trips()
  → trip/manager.TripManager.calculate_today_stats()
  → emhass/adapter.EMHASSAdapter.get_status()
  → coordinator.data = unified dict
  → All sensors auto-update
```

---

## Testing Strategy

| Layer | Tool | Coverage Target | Actual |
|-------|------|----------------|--------|
| Pure calculations | pytest + parametrize | 100% | ✅ 100% |
| Trip package | pytest + mocks | High | ✅ ~40 tests |
| EMHASS package | pytest + mocks | High | ✅ ~20 tests |
| Coordinator | pytest + hass fixtures | High | ✅ High |
| Sensors | pytest + entity fixtures | High | ✅ High |
| Services | pytest + service mocks | High | ✅ High |
| Config flow | pytest + flow fixtures | High | ✅ High |
| E2E | Playwright | Critical paths | ✅ 40 specs (30 main + 10 dynamic-soc) |
| JS Panel | Jest | Panel logic | ⚠️ Jest configured, not actively used |
| Mutation | mutmut | Baseline tracked | ✅ 62.5% kill rate |

**Total: 156 test files (121 unit + 25 integration + 10 e2e)**

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Home Assistant Container                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │           custom_components/ev_trip_planner/                     │ │
│  │  ┌──────────────────────────────────────────────────────────┐   │ │
│  │  │  8 SOLID Packages (dashboard eliminated)                   │   │ │
│  │  │  ├── trip/ (16 files) — State-Based Composition          │   │ │
│  │  │  ├── emhass/ (5 files) — Facade + Composition            │   │ │
│  │  │  ├── calculations/ (8 files) — Functional Decomposition  │   │ │
│  │  │  ├── services/ (7 files) — Module Facade + Factories     │   │ │
│  │  │  ├── vehicle/ (4 files) — Strategy Pattern               │   │ │
│  │  │  ├── sensor/ (8 files) — Platform Decomposition          │   │ │
│  │  │  ├── config_flow/ (7 files) — Flow Type Decomposition    │   │ │
│  │  │  └── presence_monitor/ (1 file) — Package Re-export      │   │ │
│  │  └──────────────────────────────────────────────────────────┘   │ │
│  │  ├── Backend (Python)                                          │ │
│  │  └── Frontend (frontend/panel.js)                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────────────────┐      │
│  │ EMHASS      │  │ Vehicle Sensors  │  │ Presence Monitor    │      │
│  │ (optional)  │  │ (SOC, range...)  │  │ (GPS + sensor)      │      │
│  └─────────────┘  └──────────────────┘  └─────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quality Assurance

### CI/CD Pipeline (GitHub Actions)

| Stage | Tool | Gate |
|-------|------|------|
| **L1: Local** | Gito (local LLM model) | Pre-commit static analysis |
| **L2: Parallel** | Ralph + .roo quality-gate | 4-layer (L3A→L1→L2→L3B) during task execution |
| **L3: External** | CodeRabbit | PR review on every push |

### Quality Gate Commands

```bash
make quality-gate     # Full gate: lint + typecheck + tests + e2e + import-check
make quality-gate-ci  # CI version (non-fatal mutation)
make lint             # ruff + pylint
make typecheck        # pyright (0 errors required)
make test-cover       # pytest with coverage
make e2e              # Playwright E2E (10 specs)
make e2e-soc          # SOC-specific E2E (2 specs)
make import-check     # lint-imports contracts
```

### Verified Results (PR #47)

- **Rooview**: ✅ PASS (2m56s)
- **CodeRabbit**: ✅ PASS (skipped, no comments needed)
- **test (GitHub Actions)**: ✅ PASS (16m36s)
- **Mutation**: 62.5% kill rate
- **E2E**: 30/30 + 10/10 SOC
- **Staging VE1/VE2**: ✅ PASS

---

## Related Documentation

- [_ai/SOLID_REFACTORING_CASE_STUDY.md](../_ai/SOLID_REFACTORING_CASE_STUDY.md) — Complete transformation story with before/after metrics
- [_ai/PORTFOLIO.md](../_ai/PORTFOLIO.md) — Portfolio with Arc 5: Architectural Redemption
- [source-tree-analysis.md](source-tree-analysis.md) — Annotated directory tree (post-decomposition)
- [development-guide.md](development-guide.md) — Development setup and commands
