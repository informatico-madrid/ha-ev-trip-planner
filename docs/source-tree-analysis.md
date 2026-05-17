# Source Tree Analysis: HA EV Trip Planner

> Generated: 2026-05-14 | Scan Level: Deep | Architecture: SOLID Package Decomposition
> **Note:** Post-spec-3-solid-refactor structure. 9 god-class modules were decomposed into
> 8 SOLID-compliant packages (dashboard/ package removed in commit 8924d98).
> See [_ai/SOLID_REFACTORING_CASE_STUDY.md](../_ai/SOLID_REFACTORING_CASE_STUDY.md).

---

## Annotated Directory Tree

```
ha-ev-trip-planner/
├── custom_components/
│   └── ev_trip_planner/                    # ⭐ ENTRY POINT — HA Custom Component
│       │
│       ├── __init__.py                     # 🔵 Integration setup, config entry lifecycle
│       │                                    #    Creates TripManager (trip/), EMHASSAdapter (emhass/), TripPlannerCoordinator
│       │
│       ├── coordinator.py                  # 🔵 DataUpdateCoordinator (30s polling)
│       │
│       ├── const.py                        # Constants — config keys, defaults, enums, trip types, error messages
│       │                                    #    DRY canonical: consolidated error message strings
│       │
│       ├── definitions.py                  # Sensor definitions — TripSensorEntityDescription + TRIP_SENSORS
│       │
│       ├── utils.py                        # Utilities — Trip ID generation, DRY canonical for validate_hora, is_trip_today
│       │
│       ├── yaml_trip_storage.py            # YAML-based trip storage fallback
│       │
│       ├── diagnostics.py                  # HA diagnostics support
│       │
│       ├── panel.py                        # 🔵 Native HA sidebar panel registration (Lit web component)
│       │
│       ├── services.yaml                   # HA service definitions for UI
│       │
│       ├── manifest.json                   # HA integration manifest
│       │
│       ├── quality_scale.yaml              # HA quality scale metadata
│       │
│       ├── strings.json                    # Config flow + options flow strings
│       │
│       ├── trip_manager.py                 # 🔵 Transitional shim (5 lines) — re-exports from trip/ package
│       │                                    #    Backward compatibility: existing imports continue to work
│       │
│       ├── emhass_adapter.py               # ❌ ELIMINATED — replaced by emhass/ package
│       ├── services.py                     # ❌ ELIMINATED — replaced by services/ package
│       ├── dashboard.py                    # ❌ ELIMINATED — replaced by dashboard/ package
│       ├── vehicle_controller.py          # ❌ ELIMINATED — replaced by vehicle/ package
│       ├── calculations.py                 # ❌ ELIMINATED — replaced by calculations/ package
│       ├── config_flow.py                  # ❌ ELIMINATED — replaced by config_flow/ package
│       ├── sensor.py                       # ❌ ELIMINATED — replaced by sensor/ package
│       ├── presence_monitor.py             # ❌ ELIMINATED — replaced by presence_monitor/ package
│       │
│       ├── trip/                           # 📦 Package: Trip Management — Facade + Mixins
│       │   ├── __init__.py                 #    Re-exports: TripManager, CargaVentana, SOCMilestoneResult
│       │   ├── manager.py                   #    Facade: TripManager (31→3 public methods, delegates to mixins)
│       │   ├── _crud.py                     #    TripCRUD mixin (9 verbs: add/update/delete/get/save/pause/resume/complete/cancel)
│       │   ├── _soc_helpers.py              #    SOCHelpers mixin
│       │   ├── _soc_window.py               #    SOCWindowMixin (includes BUG-001 fix: ventana_horas consistency)
│       │   ├── _soc_query.py                 #    SOCQueryMixin
│       │   ├── _power_profile.py            #    PowerProfileMixin
│       │   ├── _schedule.py                #    ScheduleMixin
│       │   ├── _sensor_callbacks.py         #    SensorCallbackRegistry (DI for trip→sensor cycle elimination)
│       │   ├── _trip_lifecycle.py            #    TripLifecycle mixin
│       │   ├── _trip_navigator.py           #    TripNavigator mixin
│       │   ├── _persistence.py               #    PersistenceMixin
│       │   ├── _emhass_sync.py               #    EMHASSMixin
│       │   ├── _types.py                     #    TypedDict definitions (Trip data types)
│       │   └── state.py                      #    TripState — shared state management
│       │
│       ├── emhass/                         # 📦 Package: EMHASS Adapter — Facade + Composition
│       │   ├── __init__.py                  #    Re-exports: EMHASSAdapter, ErrorHandler, IndexManager, LoadPublisher
│       │   ├── adapter.py                   #    Facade: EMHASSAdapter (19 public methods, 1-line delegations)
│       │   ├── error_handler.py              #    ErrorHandler: notification routing, error state tracking, recovery
│       │   ├── index_manager.py             #    IndexManager: trip→deferrable index lifecycle (assign/release/get/cleanup)
│       │   └── load_publisher.py            #    LoadPublisher: deferrable load payloads, publish/update/remove, cache results
│       │
│       ├── calculations/                    # 📦 Package: Pure Functions — Functional Decomposition
│       │   ├── __init__.py                  #    Re-exports: all 20 public names (17 functions + 2 classes + 1 constant)
│       │   ├── core.py                      #    calculate_trip_time, calculate_day_index (DRY canonical)
│       │   ├── windows.py                   #    calculate_multi_trip_charging_windows (BUG-001 + BUG-002 fixed)
│       │   ├── power.py                     #    calculate_power_profile, calculate_power_profile_from_trips (CC refactored)
│       │   ├── schedule.py                  #    generate_deferrable_schedule_from_trips, calculate_deferrable_parameters
│       │   ├── deficit.py                    #    calculate_deficit_propagation (CC refactored D→B)
│       │   ├── _helpers.py                   #    _ensure_aware, private helpers
│       │   └── __all__                       #    20 public names declared
│       │
│       ├── services/                        # 📦 Package: Service Handlers — Module Facade + Handler Factories
│       │   ├── __init__.py                  #    Re-exports: register_services (shrunk from 688 LOC → ~80 LOC)
│       │   ├── _handler_factories.py         #    make_<service_id>_handler() closures (≤80 LOC each, CC ≤10)
│       │   ├── handlers.py                   #    Service handler registration
│       │   ├── dashboard_helpers.py          #    Dashboard I/O helpers
│       │   ├── cleanup.py                    #    Orphaned sensor cleanup
│       │   ├── presence.py                   #    Presence configuration helpers
│       │   ├── _lookup.py                    #    Entity lookup utilities
│       │   └── _utils.py                     #    Internal utilities
│       │                                    #    10 public functions preserved: async_cleanup_orphaned_emhass_sensors,
│       │                                    #    async_cleanup_stale_storage, async_import_dashboard_for_entry,
│       │                                    #    async_register_panel_for_entry, async_register_static_paths,
│       │                                    #    async_remove_entry_cleanup, async_unload_entry_cleanup,
│       │                                    #    build_presence_config, create_dashboard_input_helpers, register_services
│       │
│       ├── dashboard/                       # 📦 Package: Dashboard — Facade + Builder
│       │   ├── __init__.py                  #    Re-exports: import_dashboard, is_lovelace_available, DashboardImportResult
│       │   │                                    + 4 exception classes
│       │   ├── builder.py                   #    DashboardBuilder (fluent interface)
│       │   ├── importer.py                  #    import_dashboard (delegated from old dashboard.py)
│       │   ├── template_manager.py          #    Template I/O
│       │   └── templates/                    #    📊 11 YAML/JS dashboard templates
│       │       ├── dashboard.yaml
│       │       ├── dashboard-create.yaml
│       │       ├── dashboard-edit.yaml
│       │       ├── dashboard-delete.yaml
│       │       ├── dashboard-list.yaml
│       │       ├── ev-trip-planner-{vehicle_id}.yaml
│       │       ├── ev-trip-planner-full.yaml
│       │       ├── ev-trip-planner-simple.yaml
│       │       ├── dashboard.js
│       │       ├── ev-trip-planner-simple.js
│       │       ├── dashboard_chispitas_test.yaml
│       │       ├── dashboard_chispitas_test.yaml
│       │       └── ... (additional templates)
│       │
│       ├── vehicle/                         # 📦 Package: Vehicle Control — Strategy Pattern
│       │   ├── __init__.py                  #    Re-exports: VehicleController, VehicleControlStrategy, create_control_strategy
│       │   ├── controller.py                #    VehicleController facade
│       │   ├── strategy.py                  #    VehicleControlStrategy ABC (3 methods: async_activate/deactivate/get_status)
│       │   └── external.py                  #    ExternalStrategy (no-op for external control)
│       │                                    #    4 strategies: SwitchStrategy, ServiceStrategy, ScriptStrategy, ExternalStrategy
│       │
│       ├── sensor/                          # 📦 Package: Sensor Platform — Platform Decomposition
│       │   ├── __init__.py                  #    HA platform entry: PLATFORMS = ["sensor"]
│       │   ├── _async_setup.py              #    async_setup_entry orchestration
│       │   ├── entity_trip_planner.py        #    TripPlannerSensor (base: CoordinatorEntity + RestoreSensor)
│       │   ├── entity_trip.py                #    TripSensor, TripsListSensor, RecurringTripsCountSensor, etc.
│       │   ├── entity_trip_emhass.py         #    TripEmhassSensor (per-trip EMHASS sensor, 9 attributes)
│       │   └── entity_emhass_deferrable.py    #    EmhassDeferrableLoadSensor (aggregated)
│       │
│       ├── config_flow/                     # 📦 Package: Config Flow — Flow Type Decomposition
│       │   ├── __init__.py                  #    Re-exports: EVTripPlannerFlowHandler, async_step_user, async_step_init
│       │   ├── main.py                      #    EVTripPlannerFlowHandler (5-step setup wizard)
│       │   ├── options.py                    #    Options flow handler
│       │   ├── _emhass.py                    #    EMHASS-specific config steps
│       │   └── _entities.py                   #    Entity selection helpers
│       │
│       ├── presence_monitor/                 # 📦 Package: Presence Detection — Package Re-export
│       │   ├── __init__.py                  #    Re-exports: PresenceMonitor, build_presence_config
│       │   │                                    #    Dual detection: sensor-based + GPS coordinate-based
│       │   │                                    #    Haversine distance (30m threshold), SOC tracking, home/away events
│       │
│       ├── frontend/                         # 🎨 Lit Web Component Panel
│       │   ├── panel.js                      #    Main panel JS (Lit component)
│       │   ├── panel.css                     #    Panel styles
│       │   └── lit-bundle.js                 #    Lit framework bundle
│       │
│       └── translations/                     # 🌐 Localization
│           ├── en.json                      #    English translations
│           └── es.json                      #    Spanish translations
│
├── tests/                                   # 🧪 Python Unit Tests
│   ├── conftest.py                          #    Shared fixtures (hass, config_entry, trip_manager)
│   │
│   ├── unit/                               #    Unit tests (100% coverage target)
│   │   ├── test_trip_*.py                   #    Trip package tests (168 tests)
│   │   ├── test_emhass_*.py                  #    EMHASS package tests (124 tests)
│   │   ├── test_calculations.py              #    Calculations package tests
│   │   ├── test_coordinator.py               #    Coordinator tests
│   │   ├── test_services_*.py               #    Services package tests
│   │   ├── test_dashboard_*.py               #    Dashboard package tests
│   │   ├── test_vehicle_*.py                 #    Vehicle package tests
│   │   ├── test_sensor*.py                   #    Sensor package tests
│   │   ├── test_config_flow*.py              #    Config flow tests
│   │   ├── test_presence_monitor.py           #    Presence monitor tests
│   │   ├── test_utils.py                     #    Utils tests
│   │   ├── test_definitions.py               #    Definitions tests
│   │   ├── test_diagnostics.py               #    Diagnostics tests
│   │   └── test_dynamic_soc_capping.py        #    Dynamic SOC capping tests
│   │
│   ├── integration/                          #    Integration tests
│   │   ├── test_config_entry_not_ready.py
│   │   └── test_coordinator.py
│   │
│   ├── e2e/                                 # 🎭 Playwright E2E Tests (30 specs)
│   │   ├── create-trip.spec.ts
│   │   ├── edit-trip.spec.ts
│   │   ├── delete-trip.spec.ts
│   │   ├── form-validation.spec.ts
│   │   ├── trip-list-view.spec.ts
│   │   ├── emhass-sensor-updates.spec.ts
│   │   ├── panel-emhass-sensor-entity-id.spec.ts
│   │   ├── trips-helpers.ts
│   │   └── zzz-integration-deletion-cleanup.spec.ts
│   │
│   ├── e2e-dynamic-soc/                    #    SOC-specific E2E (10 specs)
│   │   ├── test-dynamic-soc-capping.spec.ts
│   │   └── test-config-flow-soh.spec.ts
│   │
│   ├── helpers/                             #    Test helpers
│   │   ├── constants.py
│   │   ├── factories.py
│   │   └── fakes.py
│   │
│   └── setup_entry.py                       #    HA setup test utilities
│
├── docs/                                    # 📖 Project Documentation
│   ├── index.md                             #    Documentation index
│   ├── architecture.md                      #    ⭐ Architecture (updated: SOLID package decomposition)
│   ├── source-tree-analysis.md              #    This file (updated: post-decomposition structure)
│   ├── project-overview.md                  #    Project overview
│   ├── development-guide.md                 #    Development guide
│   ├── api-contracts.md                     #    Service API contracts
│   ├── data-models.md                       #    Data models
│   ├── emhass-setup.md                      #    EMHASS setup guide
│   ├── VEHICLE_CONTROL.md                   #    Vehicle control strategies
│   ├── DASHBOARD.md                         #    Dashboard documentation
│   ├── staging-vs-e2e-separation.md          #    Environment separation rules
│   ├── staging-qa-results.md                 #    Staging QA results
│   ├── staging-manual-verification.md        #    Staging verification guide
│   └── ...                                  #    Additional docs
│
├── _ai/                                     # 🤖 AI Context Documentation
│   ├── index.md                            #    AI context index
│   ├── PORTFOLIO.md                        #    ⭐ Portfolio (includes Arc 5: SOLID Refactoring)
│   ├── ai-development-lab.md                #    AI development methodology (Phase 8)
│   ├── RALPH_METHODOLOGY.md                 #    Smart Ralph fork methodology
│   ├── TDD_METHODOLOGY.md                   #    TDD methodology
│   ├── TESTING_E2E.md                       #    E2E testing framework
│   ├── CODEGUIDELINESia.md                  #    AI coding standards
│   ├── SPECKIT_SDD_FLOW_INTEGRATION_MAP.md  #    Speckit integration
│   ├── SOLID_REFACTORING_CASE_STUDY.md       #    ⭐ NEW: Transformation case study
│   └── ...                                  #    Additional AI docs
│
├── specs/                                   # 📋 Specification Documents
│   ├── _epics/                             #    Epic-level specs
│   │   └── tech-debt-cleanup/              #    Tech Debt Cleanup Epic
│   │       ├── epic.md
│   │       └── specs/                      #    Specs in dependency order
│   │           ├── 1-solid-refactor/        #    Spec 1: Initial SOLID (definitions.py refactor)
│   │           ├── 2-test-reorg/           #    Spec 2: Test reorganization (✅ merged PR #46)
│   │           ├── 3-solid-refactor/         #    ⭐ Spec 3: FULL SOLID Decomposition (✅ completed PR #47)
│   │           ├── 4-dispatcher/            #    Spec 4: Dispatcher pattern (pending)
│   │           └── 5-mutation-config/       #    Spec 5: Mutation config (pending)
│   │
│   ├── m401-emhass-hotfixes/               #    M4.0.1: EMHASS hotfixes (✅ completed)
│   ├── m403-dynamic-soc-capping/          #    M4.0.3: Dynamic SOC capping (✅ completed)
│   │   └── task_review.md                   #    1100+ lines of external review
│   ├── 3-solid-refactor/                   #    ⭐ The spec that transformed the architecture
│   │   ├── chat.md                         #    731 lines: execution history
│   │   ├── task_review.md                  #    2084 lines: external reviewer interventions
│   │   ├── .progress.md                    #    731 lines: task progress + metrics
│   │   ├── requirements.md                 #    Spec requirements (522 lines)
│   │   ├── design.md                       #    Architectural design (1194 lines)
│   │   ├── tasks.md                        #    156 tasks for decomposition
│   │   └── DRY_ANALYSIS_REPORT.md          #    False positive analysis
│   │
│   └── [30+ other spec folders]            #    Historical specs
│
├── scripts/                                 # 🔧 Development Scripts
│   ├── run-e2e.sh                          #    E2E test runner (hass direct, NO Docker)
│   ├── run-e2e-soc.sh                      #    SOC E2E test runner
│   ├── ha-onboard.sh                       #    HA setup script
│   ├── staging-init.sh                     #    Staging init (Docker)
│   ├── staging-reset.sh                    #    Staging reset (Docker)
│   ├── install-tools.sh                    #    Tool installation
│   ├── quality-baseline.sh                  #    Quality baseline capture
│   ├── quick-e2e-check.sh                  #    Quick E2E check
│   └── extract_report.js                   #    Coverage report extractor
│
├── automations/                             # 🤖 HA Automation Templates
│   └── emhass_charge_control_template.yaml  #    Charging control automation
│
├── _bmad/                                   # 🔧 BMad Method Configuration
├── bmalph/                                  # 🔧 BMad + Ralph Integration
├── .github/                                 # 📦 GitHub Actions CI/CD
├── playwright/                              # 🎭 Playwright configuration
├── qa/                                      # 📊 QA reports
├── report/                                  # 📊 Test coverage reports
├── coverage_html_report/                    # 📊 HTML coverage report
├── gito-report/                             # 📊 Gito lint report
├── plans/                                   # 📋 Implementation Plans
│   └── spec3-doc-update-plan.md             #    ⭐ This documentation update plan
│
├── Makefile                                 # 🔨 Build automation (quality gates, tests, E2E)
├── pyproject.toml                           # 📦 Python project config + quality gates
├── requirements_dev.txt                     # 📦 Development dependencies
├── package.json                            # 📦 Node.js dependencies
├── playwright.config.ts                    # 🎭 Playwright config
├── jest.config.js                           # 🎭 Jest config
├── Dockerfile.custom                        # 🐳 Custom Docker for staging
├── docker-compose.staging.yml              # 🐳 Staging Docker compose
├── .pre-commit-config.yaml                 # 🪝 Pre-commit hooks
├── .pylintrc                               # 🔍 Pylint config
├── .ruff.toml                              # 🔍 Ruff config
├── .semgrep.yml                            # 🔍 Semgrep config
├── .jscpd.json                             # 🔍 Copy-paste detection config
├── .gitleaks.toml                          # 🔍 Secret detection config
├── CLAUDE.md                                # 🤖 AI agent instructions
├── CLAUDE.es.md                            # 🤖 AI agent instructions (Spanish)
├── ROADMAP.md                              # 🗺️ Roadmap (updated: Spec 3 completion)
├── CHANGELOG.md                            # 📝 Changelog (pending: v0.5.24 entry)
└── README.md                                # 📖 Project README
```

---

## Package Summary Table

| Package | LOC (approx) | Sub-modules | Pattern | Public API Preserved |
|---------|---------------|-------------|---------|---------------------|
| `trip/` | ~2,500 | 14 | Facade + Mixins | ✅ TripManager constructor unchanged |
| `emhass/` | ~2,700 | 4 | Facade + Composition | ✅ EMHASSAdapter constructor unchanged |
| `calculations/` | ~1,700 | 7 | Functional Decomp | ✅ 20 public names re-exported |
| `services/` | ~1,600 | 8 | Module Facade | ✅ 10 public functions unchanged |
| `dashboard/` | ~1,300 | 4 + templates | Facade + Builder | ✅ import_dashboard + exceptions preserved |
| `vehicle/` | ~500 | 3 | Strategy | ✅ VehicleController constructor unchanged |
| `sensor/` | ~1,000 | 5 | Platform Decomp | ✅ HA platform contract preserved |
| `config_flow/` | ~1,000 | 4 | Flow Type Decomp | ✅ Config flow steps preserved |
| `presence_monitor/` | ~800 | 1 | Package Re-export | ✅ PresenceMonitor class preserved |
| **Total** | **~12,100** | **45+** | — | **All public APIs preserved** |

---

## SOLID Compliance Verification

| Package | S (LCOM4 ≤ 2) | O | L | I | D | Notes |
|---------|---------------|---|---|---|---|-------|
| `calculations/` | ✅ | ✅ | ✅ | ✅ | ✅ | Pure functions, no classes |
| `trip/` | ✅* | ✅ | ✅ | ✅ | ✅ | *LCOM4 exceptions documented |
| `emhass/` | ✅* | ✅ | ✅ | ✅ | ✅ | *Facade + Composition |
| `services/` | ✅ | ✅ | ✅ | ✅ | ✅ | Module-level |
| `dashboard/` | ✅ | ✅ | ✅ | ✅ | ✅ | Builder pattern |
| `vehicle/` | ✅ | ✅ | ✅ | ✅ | ✅ | Strategy pattern |
| `sensor/` | ✅ | ✅ | ✅ | ✅ | ✅ | Platform decomposition |
| `config_flow/` | ✅ | ✅ | ✅ | ✅ | ✅ | Flow type decomposition |
| `presence_monitor/` | ✅ | ✅ | ✅ | ✅ | ✅ | Package re-export |

**Overall: SOLID 4/5 PASS** — verified by `solid_metrics.py` Tier A deterministic checker.

---

## Architectural Contracts (lint-imports)

| Contract | Rule | Packages Affected |
|----------|------|-------------------|
| **No cycles** | Zero circular dependencies | All |
| **No trip → sensor** | SensorCallbackRegistry DI | `trip/` → `sensor/` |
| **No dashboard → trip/emhass/services** | Independence | `dashboard/` |
| **Calculations leaf** | Only imports `utils/`, `const/` | `calculations/` |
| **Layered: services top** | Services may import packages, not vice versa | `services/` |
| **7 contracts total** | Enforced by lint-imports | All |

---

## Related Documentation

- [architecture.md](architecture.md) — Complete architecture documentation (SOLID packages, metrics, patterns)
- [_ai/SOLID_REFACTORING_CASE_STUDY.md](../_ai/SOLID_REFACTORING_CASE_STUDY.md) — Transformation story with before/after
- [_ai/PORTFOLIO.md](../_ai/PORTFOLIO.md) — Portfolio with Arc 5 metrics
- [development-guide.md](development-guide.md) — Development setup
