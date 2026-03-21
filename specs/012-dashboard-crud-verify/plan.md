# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implementar dashboard CRUD completo para EV Trip Planner en Home Assistant. Basado en el análisis de la spec 011, el problema raíz fue que los fixes no se implementaron completamente antes de intentar el dashboard. Este plan incluye:

**Fase 1**: Fixes críticos P001-P004 (state_class, coordinator, entry_id, YAML fallback)

**Fase 2**: Dashboard CRUD completo con:
- Vehicle setup con configflow
- Dashboard auto-deploy en Lovelace
- CRUD operations: create, read, update, delete trips
- Tests unitarios e integración con >=80% coverage
- Playwright E2E tests para flujo web completo
- Validación: 100% tests passing, 0 critical errors

**CRÍTICO**: Todo el CRUD está en una sola User Story (US1). No hay stories separadas para create/read/update/delete.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**:
- Home Assistant 2026.x (custom_components)
- pytest-homeassistant-custom-component (testing framework)
- pytest-cov (test coverage)

**Storage**: YAML files en config directory (fallback para Container sin Storage API)

**Testing**: pytest con pytest-cov, >80% coverage requirement

**Target Platform**: Home Assistant Container (sin Supervisor API, sin Storage API)

**Project Type**: Home Assistant Custom Component (Integration)

**Performance Goals**:
- Tests completados en <5 minutos
- Dashboard disponible inmediatamente tras configuración
- Sin errores CRÍTICOS en logs

**Constraints**:
- Home Assistant Container no tiene hass.storage API
- Device class 'energy' requiere state_class 'total' o 'total_increasing' (no 'measurement')
- Config entry lookup usa entry_id, no vehicle_id
- Dashboard debe ser auto-generado o instrucciones claras para import manual

**Scale/Scope**:
- Múltiples vehículos (dashboards independientes por vehicle_id)
- CRUD completo para viajes (create, read, update, delete)
- Sensores HA para cada viaje

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Style Compliance
- [x] Line length: 88 characters (using black-compatible formatting)
- [x] Type hints: Required for all public functions
- [x] Docstrings: Google style, required for all public functions
- [x] Imports: Standard lib → Third party → HA → Local (isort)
- [x] Async: Always use `async`/`await`, no blocking calls

### Testing Compliance
- [x] >80% test coverage for production code
- [x] Tests written using pytest: `pytest tests/ -v --cov=custom_components/ev_trip_planner`

### Documentation Compliance
- [x] Conventional Commits format: `feat:`, `fix:`, `docs:`

### Gates Verified: PASS

**Gates from Constitution 011-fix-production-errors:**
- No critical errors in logs: Will verify during testing
- All sensors functional without warnings: Will verify with unit tests
- Dashboard deployable: Will verify with integration tests
- CRUD operations working: Will verify with BDD tests

**No violations detected. Proceeding to Phase 0.**

## Available Tools for Verification

*Skills and MCPs installed and available for task verification*

| Tool | Type | Status | Purpose |
|------|------|--------|---------|
| homeassistant-best-practices | skill | installed | Best practices para automations, helpers, scripts, device controls, Lovelace dashboard |
| homeassistant-ops | skill | installed | Operar Home Assistant via REST/WebSocket APIs, backups, bulk changes |
| homeassistant-config | skill | installed | Crear y manejar YAML config files, automations, scripts, blueprints |
| homeassistant-dashboard-designer | skill | installed | Design y refactor de Lovelace dashboards (YAML views/partials) |
| homeassistant-skill | skill | installed | Control de dispositivos y automations via REST API |
| python-testing-patterns | skill | installed | Testing con pytest, fixtures, mocking, TDD |
| e2e-testing-patterns | skill | installed | E2E testing con Playwright y Cypress |
| python-performance-optimization | skill | installed | Profile y optimizar Python code con cProfile, memory profilers |
| python-security-scanner | skill | installed | Detectar vulnerabilidades Python (SQL injection, unsafe deserialization, hardcoded secrets) |
| gis | skill | installed | CRS reference, data formats, Blender/QGIS integration |
| docker-essentials | skill | installed | Docker commands y workflows para container management |
| linux-administration | skill | installed | System administration para Linux servers |

## Project Structure

### Documentation (this feature)

```text
specs/012-dashboard-crud-verify/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
├── checklists/          # Quality checklists
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
custom_components/ev_trip_planner/
├── __init__.py          # Config flow, setup, coordinator
├── manifest.json        # Metadata, dependencies
├── sensor.py            # Sensor definitions (FR-001, FR-004)
├── trip_manager.py      # Trip CRUD operations (FR-005)
├── dashboard/           # Dashboard templates
│   ├── ev-trip-planner-full.yaml
│   ├── ev-trip-planner-simple.yaml
│   └── __init__.py      # Dashboard deployment logic
├── dashboard.py         # Dashboard CRUD UI (FR-003)
├── config_flow.py       # Config flow (FR-001)
├── constants.py         # Constants, enums
├── translations/        # Multi-language support
└── tests/
    ├── __init__.py
    ├── test_sensor.py           # Unit tests for sensors
    ├── test_trip_manager.py     # Unit tests for CRUD
    ├── test_dashboard.py        # Dashboard deployment tests
    ├── test_config_flow.py      # Config flow tests
    └── conftest.py              # Fixtures, helpers

tests/
├── test_dashboard.py        # Dashboard CRUD tests
└── test_integration.py      # Integration tests
```

**Structure Decision**: Existing structure from spec 011 is preserved. The dashboard
CRUD functionality will be added as a new module `dashboard.py` and templates in
`dashboard/` directory.

## State Verification Plan

### ⚠️ IMPORTANT: Only 3 Verification Types (CLOSED set)

| Verification Type | When to Use | Example Command |
|------------------|-------------|----------------|
| `[VERIFY:TEST]` | Unit/integration tests (pytest) | `pytest tests/ -v --cov` |
| `[VERIFY:API]` | REST API verification (curl/MCP to HA) | `curl http://HA/api/states/sensor.xxx` |
| `[VERIFY:BROWSER]` | Playwright/Selenium UI automation | `npx playwright test` |

**RULES:**
- ✅ ONLY these 3 types are valid in tasks
- ✅ Details of HOW to verify (services, logs, dashboard, etc.) are decided per-task in the task description
- ❌ DO NOT add more verification types like `[VERIFY:SERVICES]`, `[VERIFY:LOGS]`, `[VERIFY:LOVELACE]`

### Existence Check
- [ ] Component desplegado: `ls /config/custom_components/ev_trip_planner/`
- [ ] Sensores creados: `curl http://localhost:8123/api/states | jq '.[] | select(.entity_id | contains("sensor."))'`
- [ ] Dashboard disponible: `curl http://localhost:8123/api/lovelace/dashboard`
- [ ] Servicios disponibles: `curl http://localhost:8123/api/services | jq '.[] | select(.domain == "ev_trip_planner")'`
- [ ] Config entries existentes: `curl http://localhost:8123/api/config_entries/entry | jq '.[] | select(.domain == "ev_trip_planner")'`

### Effect Check
- [ ] Estado de entidad ≠ unavailable/unknown: `curl http://localhost:8123/api/states/sensor.{vehicle_id}_trips_count`
- [ ] Log de HA muestra inicialización exitosa: `grep "EV Trip Planner" /config/home-assistant.log`
- [ ] CRUD operaciones funcionan:
  - Create: POST `/api/services/ev_trip_planner/create_trip`
  - Read: GET `/api/services/ev_trip_planner/get_trips`
  - Update: POST `/api/services/ev_trip_planner/update_trip`
  - Delete: POST `/api/services/ev_trip_planner/delete_trip`
- [ ] Dashboard visible: Verificar en UI de Home Assistant → Dashboard → EV Trip Planner
- [ ] Sin errores CRÍTICOS: `grep -i "critical\|error" /config/home-assistant.log | grep -i "ev_trip_planner"`

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
