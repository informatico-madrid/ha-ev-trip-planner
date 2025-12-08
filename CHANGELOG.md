# Changelog - EV Trip Planner

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Milestone 3 Preparation**: Complete architectural redesign for EMHASS integration
  - New documentation: `docs/MILESTONE_3_ARCHITECTURE_ANALYSIS.md` (375 lines)
  - New documentation: `docs/MILESTONE_3_REFINEMENT.md` (888 lines)
  - Updated `ROADMAP.md` with 5-phase Milestone 3 plan (3A-3E)
  - Updated `TODO.md` with detailed implementation tasks

### Fixed
- **Validación de formato de hora**: Se añadió validación estricta en `async_add_recurring_trip()` para rechazar formatos de hora inválidos (ej: "16:400") antes de almacenarlos. Implementado con TDD: 3 tests añadidos y pasando, previniendo datos corruptos en el storage.

## [0.3.0-dev] - Target: Q1 2026

### Added
- **EMHASS Integration**: Full support for EMHASS day-ahead optimization
  - Automatic publication of trips as deferrable loads
  - Dynamic parameter calculation (power, duration, deadline)
  - Real-time schedule monitoring and execution
- **Smart Presence Detection**: Prevent charging activation when vehicle not available
  - Home detection via sensor or coordinates
  - Plugged status verification
  - Intelligent notifications when charging needed but not possible
- **Vehicle Control Abstraction**: Support for multiple control mechanisms
  - Switch entity control
  - Custom service calls
  - Script execution
- **Migration Tool**: Import existing slider-based configuration
  - Service: `ev_trip_planner.import_from_sliders`
  - Preview mode to validate before migration

### Changed
- **Architecture**: Complete redesign based on production EMHASS analysis
  - Moved from hybrid sensor approach to deferrable load interface
  - Numeric index mapping (0,1,2...) instead of wildcard entities
  - Agnostic optimizer design (EMHASS now, others later)
- **Configuration**: Extended config flow with 2 new steps
  - Step 4: EMHASS index and planning horizon
  - Step 5: Presence detection setup (optional)

### Technical Details
- **New Components**: `emhass_adapter.py`, `vehicle_controller.py`, `schedule_monitor.py`, `presence_monitor.py`
- **New Constants**: `CONF_EMHASS_INDEX`, `CONF_PLANNING_HORIZON`, `CONF_HOME_SENSOR`, `CONF_PLUGGED_SENSOR`
- **Safety Features**: Presence verification before any charging action
- **Testing**: 3-level testing strategy (unit, integration, E2E)

### Known Limitations
- Manual EMHASS configuration required (user must add config snippet for each potential index)
- Fixed planning horizon (does not dynamically adapt to EMHASS changes)
- Maximum 50 simultaneous trips (configurable, but EMHASS has practical limits)

### Architectural Corrections (2025-12-08)
- **CRITICAL FIX**: Changed from "one index per vehicle" to "one index per trip"
  - Each trip gets its own unique EMHASS index (0, 1, 2, 3...)
  - Enables multiple simultaneous trips per vehicle
  - Dynamic index assignment with reuse when trips are deleted
  - Persistent mapping: `trip_id → emhass_index` stored in HA storage
  - Updated all documentation (ROADMAP, MILESTONE_3_REFINEMENT, TODO, IMPLEMENTATION_PLAN)

## [0.2.0-dev] - 2025-11-22

### Added
- 4 sensores de cálculo: next_trip, next_deadline, kwh_today, hours_today
- Lógica de expansión de viajes recurrentes para 7 días
- Combinación de viajes recurrentes y puntuales
- Manejo completo de timezone con zoneinfo
- Cobertura de tests: 84% (60/60 tests pasando)

### Changed
- Actualizado ROADMAP.md para reflejar Milestone 2 completado
- Versión en manifest.json: 0.1.0-dev → 0.2.0-dev

### Fixed
- Timezone mismatch en cálculos de viajes
- Issues con async/threadsafe en sensores

## [0.1.0-dev] - 2025-11-18

### Added
- Estructura inicial del proyecto
- Config flow para configuración de vehículos
- Sistema de gestión de viajes (recurrentes y puntuales)
- 3 sensores básicos (trips_list, recurring_count, punctual_count)
- Dashboard Lovelace de ejemplo

### Changed
- Migración de input_text a Storage API

### Fixed
- Issues iniciales de setup y configuración
