# Source Tree Analysis: HA EV Trip Planner

> Generated: 2026-04-16 | Scan Level: Deep

## Annotated Directory Tree

```
ha-ev-trip-planner/
├── custom_components/
│   └── ev_trip_planner/                    # ⭐ ENTRY POINT - HA Custom Component
│       ├── __init__.py                     # 🔵 Integration setup, config entry lifecycle
│       ├── config_flow.py                  # 🔵 Multi-step config flow (vehicle + sensors + EMHASS + presence)
│       ├── const.py                        # Constants, config keys, defaults, enums
│       ├── coordinator.py                  # DataUpdateCoordinator (30s polling cycle)
│       ├── definitions.py                  # Sensor entity descriptions (TRIP_SENSORS tuple)
│       ├── sensor.py                       # Sensor entities (TripPlannerSensor, TripEmhassSensor)
│       ├── services.py                     # 🔵 9+ HA service handlers (trip CRUD, dashboard import)
│       ├── services.yaml                   # Service definitions for HA UI
│   ├── trip_manager.py # ⭐ CORE: Trip CRUD, energy calc, EMHASS sync (2244 LOC)
│       ├── calculations.py                 # Pure calculation functions (extracted for testability)
│       ├── emhass_adapter.py               # EMHASS integration adapter (deferrable loads, power profiles)
│       ├── vehicle_controller.py           # 4 charging control strategies (switch, service, script, external)
│       ├── presence_monitor.py             # GPS + sensor-based presence detection
│       ├── schedule_monitor.py             # EMHASS schedule monitoring + vehicle control execution
│       ├── panel.py                        # Native HA sidebar panel registration
│       ├── dashboard.py                    # Auto-deploy Lovelace dashboards (storage + YAML modes)
│       ├── utils.py                        # Utility functions (trip ID generation, validation)
│       ├── diagnostics.py                  # HA diagnostics support
│       ├── yaml_trip_storage.py            # YAML-based trip storage fallback
│       ├── manifest.json                   # HA integration manifest
│       ├── quality_scale.yaml              # HA quality scale metadata
│       ├── strings.json                    # Config flow + options flow strings
│       │
│       ├── frontend/                       # 🎨 Lit Web Component Panel
│       │   ├── panel.js                    # Main panel JS (Lit component)
│       │   ├── panel.css                   # Panel styles
│       │   └── lit-bundle.js               # Lit framework bundle
│       │
│       ├── dashboard/                      # 📊 Lovelace Dashboard Templates
│       │   ├── dashboard.yaml              # Main dashboard template
│       │   ├── dashboard.js                # Dashboard JS helpers
│       │   ├── dashboard-create.yaml       # Trip creation view
│       │   ├── dashboard-edit.yaml         # Trip editing view
│       │   ├── dashboard-delete.yaml       # Trip deletion view
│       │   ├── dashboard-list.yaml         # Trip list view
│       │   ├── ev-trip-planner-simple.yaml # Simplified dashboard variant
│       │   └── ev-trip-planner-full.yaml   # Full dashboard variant
│       │
│       └── translations/                   # 🌐 Localization
│           ├── en.json                     # English translations
│           └── es.json                     # Spanish translations
│
├── tests/ # 🧪 Python Unit Tests (90 test files)
│   ├── conftest.py                         # Shared fixtures (hass, config_entry, trip_manager)
│   ├── test_trip_manager.py                # Core trip manager tests
│   ├── test_calculations.py                # Pure calculation tests
│   ├── test_coordinator.py                 # Coordinator tests
│   ├── test_sensor*.py                     # Sensor entity tests (multiple files)
│   ├── test_config_flow*.py                # Config flow tests (multiple files)
│   ├── test_services*.py                   # Service handler tests
│   ├── test_emhass_adapter.py              # EMHASS adapter tests
│   ├── test_dashboard*.py                  # Dashboard tests
│   ├── test_presence_monitor.py            # Presence monitor tests
│   ├── test_schedule_monitor.py            # Schedule monitor tests
│   ├── test_vehicle_controller*.py         # Vehicle controller tests
│   ├── test_utils.py # Utility function tests
│   ├── fixtures/                           # Test fixtures (JSON trip/vehicle data)
│   │   ├── trips/                          # Trip fixture data
│   │   └── vehicles/                       # Vehicle fixture data
│   │
│   └── e2e/                                # 🎭 Playwright E2E Tests
│       ├── create-trip.spec.ts             # Trip creation E2E
│       ├── edit-trip.spec.ts               # Trip editing E2E
│       ├── delete-trip.spec.ts             # Trip deletion E2E
│       ├── form-validation.spec.ts         # Form validation E2E
│       ├── trip-list-view.spec.ts          # Trip list view E2E
│       ├── emhass-sensor-updates.spec.ts   # EMHASS sensor E2E
│       ├── panel-emhass-sensor-entity-id.spec.ts # Panel EMHASS E2E
│       └── trips-helpers.ts                # Shared E2E helpers
│
├── docs/                                   # 📖 Project Documentation
│   ├── DASHBOARD.md                        # Dashboard documentation
│   ├── VEHICLE_CONTROL.md                  # Vehicle control strategies
│   ├── emhass-setup.md                     # EMHASS setup guide
│   ├── TESTING_E2E.md                      # E2E testing guide
│   ├── TDD_METHODOLOGY.md                  # TDD methodology
docs/source-tree-analysis.md
│   └── ...                                 # Additional docs
│
├── specs/                                  # 📋 Specification Documents
│   ├── _epics/                             # Epic-level specs
│   └── [30+ spec folders]                  # Individual feature specs
│
├── automations/                            # 🤖 HA Automation Templates
│   └── emhass_charge_control_template.yaml
│
├── scripts/                                # 🔧 Development Scripts
│   ├── run-e2e.sh                          # E2E test runner
│   ├── ha-onboard.sh                       # HA setup script
│   └── extract_report.js                   # Coverage report extractor
│
├── docker-compose.yml                      # 📦 Docker config (DEPRECATED for E2E — historical residue, not referenced by E2E runner)
├── Dockerfile.custom                       # Custom HA Docker image
├── package.json                            # Node.js dependencies (Playwright, Jest, Lit)
├── pyproject.toml                          # Python tooling config (black, ruff, mypy, pytest)
├── Makefile                                # 🎯 Development commands (test, lint, format, e2e)
├── hacs.json                               # HACS repository metadata
├── README.md                               # Main project README (Spanish)
├── CONTRIBUTING.md                         # Contribution guidelines
├── CHANGELOG.md                            # Version changelog
└── ROADMAP.md                              # Project roadmap
```

## Critical Folders Summary

| Folder | Purpose | Key Files |
|--------|---------|-----------|
| `custom_components/ev_trip_planner/` | Core integration code | All `.py` files, `manifest.json` |
| `custom_components/ev_trip_planner/frontend/` | Lit web component panel | `panel.js`, `panel.css` |
| `custom_components/ev_trip_planner/dashboard/` | Lovelace YAML templates | `dashboard*.yaml`, `ev-trip-planner-*.yaml` |
| `custom_components/ev_trip_planner/translations/` | i18n strings | `en.json`, `es.json` |
| `tests/` | Python unit tests (90+ files) | `conftest.py`, `test_*.py` |
| `tests/e2e/` | Playwright E2E tests | `*.spec.ts`, `trips-helpers.ts` |
| `docs/` | Project documentation | 15+ markdown files |
| `specs/` | Feature specifications | 30+ spec folders |
| `scripts/` | Dev automation scripts | `run-e2e.sh`, `ha-onboard.sh` |

## Entry Points

| Entry Point | File | Description |
|-------------|------|-------------|
| **Integration Setup** | `__init__.py::async_setup_entry` | HA calls this when config entry is added |
| **Config Flow** | `config_flow.py::EVTripPlannerConfigFlow` | Multi-step vehicle setup wizard |
| **Sensor Platform** | `sensor.py::async_setup_entry` | Registers sensor entities |
| **Service Registration** | `services.py::register_services` | Registers 9+ HA services |
| **Panel Registration** | `panel.py::async_register_panel` | Registers native sidebar panel |
| **Dashboard Import** | `dashboard.py::import_dashboard` | Auto-deploys Lovelace dashboard |
| **Frontend Panel** | `frontend/panel.js` | Lit web component loaded in HA sidebar |
| **E2E Tests** | `tests/e2e/*.spec.ts` | Playwright test suite |
| **Docker** | `docker-compose.yml` | DEPRECATED — historical residue. NOT used for E2E. E2E uses `hass` directly via `scripts/run-e2e.sh`. May be repurposed for staging. |
