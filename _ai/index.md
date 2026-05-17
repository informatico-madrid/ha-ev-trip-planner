# AI Context - EV Trip Planner

> Updated: 2026-05-14 | Architecture: SOLID Package Decomposition (Spec 3 completed)
> **Note:** 9 god-class modules were decomposed into SOLID-compliant packages.
> See [_ai/SOLID_REFACTORING_CASE_STUDY.md](./SOLID_REFACTORING_CASE_STUDY.md).

Documentation for AI agents working on this codebase.

---

## Project Status

| Metric | Value | Note |
|--------|-------|------|
| **Version** | 0.5.24 | After spec 3-solid-refactor completion |
| **SOLID Compliance** | **5/5 PASS** | From 3/5 FAIL (before) |
| **God Classes** | **0 violations** | From 4 violations (before) |
| **Test Count** | 1,802 | 100% coverage |
| **E2E Tests** | 40 specs | 30 main + 10 SOC |
| **Mutation Kill Rate** | 62.5% | +13.6 pp from baseline |
| **Quality Gate** | ✅ PASS | CI green (PR #47) |

---

## Structure

- `_ai/` - AI-dense documentation (complex, technical, context-heavy)
- `docs/` - Human-readable documentation (concise, explanatory)
- `plans/` - Active development plans and proposals
- `specs/` - Implemented specifications

---

## AI Documents

| Document | Purpose | Updated |
|----------|---------|---------|
| [`ai-development-lab.md`](./ai-development-lab.md) | AI development methodology and workflow (Phase 8: SOLID Refactoring) | ✅ |
| [`PORTFOLIO.md`](./PORTFOLIO.md) | AI orchestration portfolio (Arc 5: Architectural Redemption) | ✅ |
| [`RALPH_METHODOLOGY.md`](./RALPH_METHODOLOGY.md) | Smart Ralph AI-assisted workflow | ✅ |
| [`TDD_METHODOLOGY.md`](./TDD_METHODOLOGY.md) | Test-driven development approach | — |
| [`TESTING_E2E.md`](./TESTING_E2E.md) | End-to-end testing framework | — |
| [`CODEGUIDELINESia.md`](./CODEGUIDELINESia.md) | Coding standards for AI generation | — |
| [`IMPLEMENTATION_REVIEW.md`](./IMPLEMENTATION_REVIEW.md) | Comprehensive implementation analysis | — |
| [`SPECKIT_SDD_FLOW_INTEGRATION_MAP.md`](./SPECKIT_SDD_FLOW_INTEGRATION_MAP.md) | Speckit integration architecture | — |
| [`charging-planning-functional-analysis.md`](./charging-planning-functional-analysis.md) | SOC-aware charging analysis | — |
| **`SOLID_REFACTORING_CASE_STUDY.md`** | **NEW:** Transformation case study (before/after metrics) | ✅ |

---

## Critical Paths — Post-Decomposition

The architecture has been transformed from monolithic god-classes to SOLID packages:

### Entry Points

| Path | Purpose |
|------|---------|
| `custom_components/ev_trip_planner/__init__.py` | Integration setup, config entry lifecycle |
| `custom_components/ev_trip_planner/coordinator.py` | DataUpdateCoordinator (30s polling) |

### 9 SOLID Packages (Replacing 9 God-Class Modules)

| Old Monolith | New Package | Pattern | LOC |
|-------------|-------------|---------|-----|
| `emhass_adapter.py` (2,733 LOC) | `emhass/` | Facade + Composition | 4 sub-modules |
| `trip_manager.py` (2,503 LOC) | `trip/` | Facade + Mixins | 14 sub-modules |
| `services.py` (1,635 LOC) | `services/` | Module Facade + Factories | 8 sub-modules |
| `dashboard.py` (1,285 LOC) | `dashboard/` | Facade + Builder | 4 sub-modules + templates/ |
| `calculations.py` (1,690 LOC) | `calculations/` | Functional Decomposition | 7 sub-modules |
| `vehicle_controller.py` (537 LOC) | `vehicle/` | Strategy Pattern | 3 sub-modules |
| `sensor.py` (1,041 LOC) | `sensor/` | Platform Decomposition | 5 sub-modules |
| `config_flow.py` (1,038 LOC) | `config_flow/` | Flow Type Decomposition | 4 sub-modules |
| `presence_monitor.py` (806 LOC) | `presence_monitor/` | Package Re-export | 1 module |

**Backward Compatibility**: `trip_manager.py` exists as a 5-line transitional shim re-exporting from `trip/` package. Other old module names have been removed.

### Critical Import Paths

| Package | Critical Imports |
|---------|------------------|
| `trip/` | `from custom_components.ev_trip_planner.trip import TripManager` |
| `emhass/` | `from custom_components.ev_trip_planner.emhass import EMHASSAdapter` |
| `services/` | `from custom_components.ev_trip_planner.services import register_services` |
| `calculations/` | `from custom_components.ev_trip_planner.calculations import calculate_power_profile_from_trips` |
| `dashboard/` | `from custom_components.ev_trip_planner.dashboard import import_dashboard` |
| `vehicle/` | `from custom_components.ev_trip_planner.vehicle import VehicleController` |
| `sensor/` | `from custom_components.ev_trip_planner.sensor import async_setup_entry` |
| `config_flow/` | `from custom_components.ev_trip_planner.config_flow import EVTripPlannerFlowHandler` |
| `presence_monitor/` | `from custom_components.ev_trip_planner.presence_monitor import PresenceMonitor` |

### DRY Canonical Locations

| Function | Canonical Location |
|----------|-------------------|
| `validate_hora` | `utils.py:247` |
| `is_trip_today` | `utils.py:243` |
| `calculate_day_index` | `calculations/core.py:164` |

---

## SOLID Metrics Verification

**Programmatic verification** via `solid_metrics.py` Tier A deterministic checker:

| Letter | Status | Details |
|--------|--------|---------|
| **S (SRP)** | ✅ PASS | LCOM4 ≤ 2 for all classes; TripManager (3 public methods from 31), EMHASSAdapter (19 from 28) |
| **O (OCP)** | ✅ PASS | Abstractness above 10% threshold; VehicleControlStrategy ABC with 3 methods |
| **L (LSP)** | ✅ PASS | All ABC implementations honor contracts |
| **I (ISP)** | ✅ PASS | max_unused_methods_ratio ≤ 0.5; VehicleControlStrategy narrowed to 3 methods |
| **D (DIP)** | ✅ PASS | Zero circular dependencies; 7 lint-imports contracts enforced |

**Overall: SOLID 5/5 PASS** — verified programmatically.

---

## Quality Assurance

### Quality Gate Commands

```bash
make quality-gate     # Full gate: lint + typecheck + tests + e2e + import-check
make quality-gate-ci  # CI version (non-fatal mutation)
make lint             # ruff + pylint (0 errors)
make typecheck        # pyright (0 errors)
make test-cover       # pytest (1802 tests, 100% coverage)
make e2e              # Playwright (30 specs)
make e2e-soc          # SOC E2E (10 specs)
make import-check     # lint-imports (7 contracts)
```

### CI/CD Pipeline

- **Rooview**: ✅ PASS (2m56s)
- **CodeRabbit**: ✅ PASS
- **GitHub Actions test**: ✅ PASS (16m36s)
- **Mutation**: 62.5% kill rate
- **Staging VE1/VE2**: ✅ PASS

---

## Spec History (Key Specs)

| Spec | Status | Description |
|------|--------|-------------|
| `trip-creation` | ✅ | Base trip creation and management system |
| `charging-window-calculation` | ✅ | Charging window algorithm and binary profile |
| `soc-integration-baseline` | ✅ | Baseline SOC integration |
| `soc-milestone-algorithm` | ✅ | SOC-aware algorithm with safety margin |
| `emhass-integration-with-fixes` | ✅ | EMHASS integration with compatibility fixes |
| `m401-emhass-per-trip-sensors` | ✅ | Per-trip EMHASS sensors (PR #26) |
| `m403-dynamic-soc-capping` | ✅ | Dynamic SOC capping, 136 tasks, 1822 tests |
| **`3-solid-refactor`** | ✅ | **9 god-classes decomposed, SOLID 5/5, PR #47** |

---

## Known Gaps (Updated)

The SOLID decomposition resolved several original gaps:

| Gap | Status | Note |
|-----|--------|------|
| `schedule_monitor.py` never imported | ⚠️ Still exists | Not connected to config flow |
| Vehicle control not wired to UI | ⚠️ Still exists | Control strategy not exposed in config flow |
| SOH (State of Health) not in UI | ⚠️ Still exists | Code infrastructure exists, no UI selector |

**Resolved by Spec 3**:
- BUG-001: `ventana_horas` inflated by away time → Fixed in `calculations/windows.py`
- BUG-002: `return_buffer_hours` double-count → Fixed (unused after fix)
- 3 DRY violations → Consolidated to canonical locations
- God-class antipatterns (4 violations) → Eliminated via decomposition

---

## Quick Reference for AI Agents

1. **Don't reference old monolith paths** — e.g., `emhass_adapter.py`, `trip_manager.py`, `services.py` no longer exist
2. **Use package imports** — e.g., `from custom_components.ev_trip_planner.emhass import EMHASSAdapter`
3. **DRY canonicals exist** — `validate_hora` → `utils.py`, `is_trip_today` → `utils.py`, `calculate_day_index` → `calculations/core.py`
4. **SOLID metrics are verified** — `solid_metrics.py` runs in quality gate; don't add code that violates LCOM4 ≤ 2
5. **lint-imports contracts enforced** — don't create circular dependencies or import across contract boundaries

---

## Contributing to Documentation

This project is an **AI development laboratory**. Documentation is maintained via spec-driven development:

1. Create a spec for documentation changes
2. Use `/ralph-specum:start` to begin
3. Follow the spec-driven loop (Research → Requirements → Design → Tasks → Implement)
4. External reviewer validates changes before merge

See [`_ai/RALPH_METHODOLOGY.md`](./RALPH_METHODOLOGY.md) for the complete workflow.

---

*Last updated: 2026-05-14 — After spec 3-solid-refactor completion (SOLID 5/5, 9 packages, PR #47)*