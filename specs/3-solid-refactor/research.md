---
spec: 3-solid-refactor
phase: research
created: 2026-05-10
epic: tech-debt-cleanup
branch: spec/3-solid-refactor (from epic/tech-debt-cleanup)
pr_target: epic/tech-debt-cleanup
depends_on: [tooling-foundation, spec1-dead-code (PR #45), 2-test-reorg (PR #46)]
---

# Research: 3-solid-refactor

## Executive Summary

Decompose 6 god modules (10,383 LOC total) into focused packages with `__init__.py` re-exports preserving the public API. Numbers reconfirmed against current `epic/tech-debt-cleanup` head (commit `e7cf020b`): `emhass_adapter.py` 2,733 LOC / 27 public methods, `trip_manager.py` 2,503 LOC / 31 public methods, `services.py` 1,635 LOC / 10 public functions, `dashboard.py` 1,285 LOC / 2 public functions + 4 public classes, `vehicle_controller.py` 537 LOC / 6 public ABC strategies + 7 public methods on `VehicleController`, `calculations.py` 1,690 LOC / 17 public functions + 2 public classes. Of the "3 cycles" listed in epic.md, two are already broken at module-load time via TYPE_CHECKING (`vehicle_controller→trip_manager`, `presence_monitor→trip_manager`), and the third (`trip_manager→sensor→coordinator→trip_manager`) is broken via in-function lazy imports — `lint-imports` is installed but unconfigured (no contracts in `pyproject.toml`), so there are likely 0 module-load cycles right now and the refactor's job is to make that explicit via contracts and remove the lazy imports.

## 1. Current State (measured)

Source: `wc -l` and `grep -cE "^    (async )?def [a-zA-Z]"` on commit `e7cf020b` of `epic/tech-debt-cleanup`.

| Module | LOC | All `def`/`async def` (top + indented) | Public class methods (`    def [a-z]` not `_`) | Public top-level fns (`def [a-z]` not `_`) |
|---|---:|---:|---:|---:|
| [`emhass_adapter.py`](../../custom_components/ev_trip_planner/emhass_adapter.py) | 2,733 | 41 | 27 | 0 |
| [`trip_manager.py`](../../custom_components/ev_trip_planner/trip_manager.py) | 2,503 | 49 | 31 | 0 |
| [`services.py`](../../custom_components/ev_trip_planner/services.py) | 1,635 | 13 | — | 10 |
| [`dashboard.py`](../../custom_components/ev_trip_planner/dashboard.py) | 1,285 | 14 | — | 2 (+ 4 public classes) |
| [`vehicle_controller.py`](../../custom_components/ev_trip_planner/vehicle_controller.py) | 537 | 30 (multi-class) | 7 (`VehicleController`) | 1 (`create_control_strategy`) |
| [`calculations.py`](../../custom_components/ev_trip_planner/calculations.py) | 1,690 | 17 (top-level) | — | 17 (+ 2 public classes) |
| **Total** | **10,383** | — | — | — |

**Notes**
- `emhass_adapter.py` is now 2,733 LOC (epic.md said 2,730 — within rounding).
- `trip_manager.py` confirmed 2,503 LOC / 49 declared methods (49 in epic.md). 31 are public (no leading `_`); the public count drops below epic.md's 49 because epic.md counted private + dunder.
- `vehicle_controller.py` epic.md says "40 public methods" — ACTUAL count is 30 across all 6 classes in the file (5 strategies + `VehicleController` + `RetryState` + `HomeAssistantWrapper`). Of these, only 7 are on `VehicleController` itself; ARN-002 (≤20 methods/class) is **not violated** by `VehicleController` alone — the violation is the file's total breadth.
- Per-file ARN-001 (≤500 LOC): all 6 modules fail. Only `vehicle_controller.py` is close to threshold (537).
- ARN-002 (≤20 public methods/class): `EMHASSAdapter` (27) and `TripManager` (31) violate.

## 2. Import graph

### 2.1 What each god module imports from inside `custom_components/ev_trip_planner/`

| Source | Internal imports |
|---|---|
| `calculations.py` | `.const` (constants), `.utils.calcular_energia_kwh` |
| `emhass_adapter.py` | `.calculations` (`DEFAULT_T_BASE`, `BatteryCapacity`, `calculate_deferrable_parameters as calc_deferrable_parameters`, `calculate_dynamic_soc_limit`, `calculate_hours_deficit_propagation`, `calculate_multi_trip_charging_windows`, `calculate_power_profile_from_trips`, `calculate_trip_time`, `determine_charging_need`, `generate_deferrable_schedule_from_trips`); `.const` (16 constants); also 2 inline lazy imports `.calculations.calculate_energy_needed` (line 446) and a 3-name lazy import (line 551) |
| `trip_manager.py` | `.calculations` (`BatteryCapacity`, `calculate_day_index`, `calculate_next_recurring_datetime`); `.const`; `.emhass_adapter.EMHASSAdapter`; `.utils` (`calcular_energia_kwh`, `generate_trip_id`, `is_trip_today as pure_is_trip_today`, `sanitize_recurring_trips as pure_sanitize_recurring_trips`, `validate_hora as pure_validate_hora`); `.vehicle_controller.VehicleController`; `.yaml_trip_storage.YamlTripStorage`; **6 lazy imports inside methods**: `.calculations.calculate_charging_rate` (1432), `calculate_soc_target` (1454), `calculate_trip_time` (1553), `calculate_day_index` (1573), 3-name lazy block (2091), `calculate_power_profile` (2228); **7 lazy imports of `.sensor`** (lines 732, 741, 794, 803, 893, 931, 938) — explicitly comment "Local import to avoid circular dependency" |
| `services.py` | `.const.DOMAIN`; `.coordinator.TripPlannerCoordinator`; `.dashboard.DashboardImportResult`; `.trip_manager.TripManager`; `.utils.normalize_vehicle_id`; **2 lazy imports** `from custom_components.ev_trip_planner.dashboard import DashboardImportResult` (1096, 1108); **1 lazy import** `from .dashboard import import_dashboard as import_dashboard` (1372) |
| `dashboard.py` | (none from sibling modules — only stdlib + HA core) |
| `vehicle_controller.py` | `.const.CONF_CHARGING_SENSOR`; `.presence_monitor.PresenceMonitor`; `TYPE_CHECKING: from .trip_manager import TripManager` (line 15) |

### 2.2 What other modules import FROM each god module

Computed via `grep -rn "from .X import\|from custom_components.ev_trip_planner.X import"` across `custom_components/` and `tests/`.

#### From `emhass_adapter.py`
- Source: `__init__.py:27` (`EMHASSAdapter`); `coordinator.py:29` (`EMHASSAdapter`); `trip_manager.py:37` (`EMHASSAdapter`).
- Tests (unit): `test_emhass_deferrable_end.py`, `test_dashboard.py:2090` (lazy), `test_propagate_charge_integration.py:24`, `test_init_full_coverage.py:10`, `test_emhass_adapter_trip_id.py:13`, `test_vehicle_id_vs_entry_id_cleanup.py:21`, `test_emhass_index_persistence.py:16`, `test_soc_100_propagation.py:15`, `test_emhass_integration_dynamic_soc.py:26`, `test_emhass_index_rotation.py:20`, `test_sensor_aggregation.py:26`, `test_array_rotation_consistency.py:15`, `test_three_trips_charging_positions.py:21`, `test_deferrable_start_boundary.py:37`, `test_soc_cap_aggregation_ceil.py:31`, `test_charging_window.py:28`, `test_deferrable_hours_window.py:22`, `test_emhass_array_ordering.py:19`, `test_deferrable_hours_calculation.py:19`, `test_power_profile_positions.py:24`, `test_edge_case_guards.py:13`, `test_deferrable_end_boundary.py:22`, `test_soc_100_deferrable_nominal.py:18`.
- Tests (integration): `test_emhass_adapter.py`, `test_functional_emhass_sensor_updates.py`, `test_emhass_integration_edge_cases.py`, `test_emhass_soft_delete.py`.
- **Public name to preserve via re-export: `EMHASSAdapter`.**

#### From `trip_manager.py`
- Source: `__init__.py:41` (`TripManager`); `coordinator.py:30` (`TripManager`); `services.py:20` (`TripManager`); `presence_monitor.py:24` (TYPE_CHECKING `TripManager`); `vehicle_controller.py:15` (TYPE_CHECKING `TripManager`).
- Tests (unit): `conftest.py:8,844,851`; `test_trip_crud.py:18`, `test_emhass_publish_edge_cases.py:18`, `test_trip_manager_emhass_sensors.py:21`, `test_charging_window.py:29`, `test_init_full_coverage.py:11`, `test_deferrables_schedule.py` (3 lazy), `test_soc_milestone.py:8`.
- Tests (integration): `test_trip_manager_core.py`, `test_trip_manager_power_profile.py`, `test_trip_calculations.py`, `test_post_restart_persistence.py`, `test_renault_integration_issues.py`, `test_user_real_data_simple.py`, `test_power_profile_tdd.py`, `test_trip_emhass_sensor.py`.
- **Public name to preserve via re-export: `TripManager`.**
- Also: `CargaVentana` (TypedDict) and `SOCMilestoneResult` (TypedDict) are defined as public — verify whether external callers import them (grep result: only inside `trip_manager.py`; safe to keep internal in `trip/__init__.py`).

#### From `services.py`
- Source: `__init__.py:29` re-imports the **10 public functions** listed in epic.md table (`async_cleanup_orphaned_emhass_sensors`, `async_cleanup_stale_storage`, `async_import_dashboard_for_entry`, `async_register_panel_for_entry`, `async_register_static_paths`, `async_remove_entry_cleanup`, `async_unload_entry_cleanup`, `build_presence_config`, `create_dashboard_input_helpers`, `register_services`).
- Tests (unit): `test_trip_create_branches.py` (3 lazy imports of `register_services`).
- Tests (integration): `test_services_core.py`, `test_integration_uninstall.py`.
- **Public names to preserve: 10 functions above.** No private helpers (`_find_entry_by_vehicle`, `_get_manager`, `_ensure_setup`, `_get_coordinator`) need re-export.

#### From `dashboard.py`
- Source: `config_flow.py:52` (`import_dashboard`, `is_lovelace_available`); `services.py:19` (`DashboardImportResult`).
- Tests (unit): `test_dashboard.py` (~50+ lazy imports — see import surface below); `test_dashboard_validation.py` (~30+ lazy imports).
- **Public names to preserve from external callers**: `import_dashboard`, `is_lovelace_available`, `DashboardImportResult`.
- **Test-internal names also imported (not consumed by source code, but tests import them — must remain accessible after split)**: `_load_dashboard_template`, `_save_lovelace_dashboard`, `_save_dashboard_yaml_fallback`, `_validate_dashboard_config`, `_verify_storage_permissions`, `_await_executor_result`, `_call_async_executor_sync`, `DashboardError`, `DashboardNotFoundError`, `DashboardValidationError`, `DashboardStorageError`. **Implication**: tests need to be updated to import from the new sub-module locations OR those private names must be re-exported. Recommended: update test imports — these are private helpers (single underscore) and reaching into them from tests was always fragile.

#### From `vehicle_controller.py`
- Source: `trip_manager.py:42` (`VehicleController`).
- Tests (unit): `test_vehicle_controller_event.py`.
- Tests (integration): `test_vehicle_controller.py`.
- **Public name to preserve: `VehicleController`.** Also `VehicleControlStrategy`, `SwitchStrategy`, `ServiceStrategy`, `ScriptStrategy`, `ExternalStrategy`, `RetryState`, `HomeAssistantWrapper`, `create_control_strategy` — verify whether tests reach in. (Found: `test_vehicle_controller.py` and `test_vehicle_controller_event.py` should be inspected for direct strategy imports during requirements/design — likely all imports via `VehicleController` only.)

#### From `calculations.py`
- Source: `emhass_adapter.py` (10 names, see §2.1); `trip_manager.py` (3 module-level names + 6 lazy single-name imports).
- Tests (unit): `test_propagate_charge_integration.py`, `test_edge_case_guards.py`, `test_deferrable_end_boundary.py`, `test_soc_100_deferrable_nominal.py`, `test_recurring_day_offset.py`, `test_dynamic_soc_capping.py`, `test_charging_window.py`, `test_calculations.py`, `test_single_trip_hora_regreso_past.py`, `test_timezone_utc_vs_local.py`, `test_deferrable_hours_calculation.py`, `test_soc_100_propagation.py`.
- **Names imported by external sites (must all be re-exported by `calculations/__init__.py`)**:
  - Classes: `BatteryCapacity`, `ChargingDecision`
  - Constants: `DEFAULT_T_BASE`
  - Functions: `calculate_dynamic_soc_limit`, `calculate_day_index`, `calculate_trip_time`, `calculate_charging_rate`, `calculate_soc_target`, `determine_charging_need`, `calculate_energy_needed`, `calculate_charging_window_pure`, `calculate_multi_trip_charging_windows`, `calculate_hours_deficit_propagation`, `calculate_soc_at_trip_starts`, `calculate_deficit_propagation`, `calculate_next_recurring_datetime`, `calculate_power_profile_from_trips`, `calculate_power_profile`, `generate_deferrable_schedule_from_trips`, `calculate_deferrable_parameters`.
  - **17 functions + 2 classes + 1 constant = 20 names total.** This list defines the `calculations/__init__.py` re-export contract verbatim.

## 3. Public API surface (per god module)

### 3.1 `EMHASSAdapter` (27 public methods, line numbers)
[`emhass_adapter.py`](../../custom_components/ev_trip_planner/emhass_adapter.py)

`__init__` (63), `async_load` (163), `get_cached_optimization_results` (230), `async_save` (259), `async_assign_index_to_trip` (281), `async_release_trip_index` (321), `async_publish_deferrable_load` (355), `async_remove_deferrable_load` (852), `async_update_deferrable_load` (887), `async_publish_all_deferrable_loads` (891), `get_assigned_index` (1345), `get_all_assigned_indices` (1349), `get_available_indices` (1353), `calculate_deferrable_parameters` (1377), `publish_deferrable_loads` (1401), `async_verify_shell_command_integration` (1582), `async_check_emhass_response_sensors` (1673), `async_get_integration_status` (1766), `async_notify_error` (1811), `async_handle_emhass_unavailable` (1997), `async_handle_sensor_error` (2035), `async_handle_shell_command_failure` (2060), `get_last_error` (2094), `async_clear_error` (2112), `async_cleanup_vehicle_indices` (2138), `verify_cleanup` (2390), `setup_config_entry_listener` (2451), `update_charging_power` (2562).

Consumed-from-outside (grep on `<obj>.<method>` patterns and direct imports):
- Direct on adapter instance: `async_load`, `async_save`, `async_assign_index_to_trip`, `async_release_trip_index`, `async_publish_deferrable_load`, `async_remove_deferrable_load`, `async_update_deferrable_load`, `async_publish_all_deferrable_loads`, `publish_deferrable_loads`, `update_charging_power`, `setup_config_entry_listener`, `get_cached_optimization_results`, `async_cleanup_vehicle_indices`, `verify_cleanup`, `get_assigned_index`, `get_all_assigned_indices`, `get_available_indices`, `async_notify_error` (and its dispatched variants), `async_handle_*`, `get_last_error`, `async_clear_error`, `async_get_integration_status`.

The public surface is too large to slim aggressively without behavior changes; the split keeps all 27 methods by mounting them on `EMHASSAdapter` (which becomes a façade aggregating the new sub-classes) — see §5.

### 3.2 `TripManager` (31 public methods)
[`trip_manager.py`](../../custom_components/ev_trip_planner/trip_manager.py)

`__init__` (98), `set_emhass_adapter` (130), `get_emhass_adapter` (135), `publish_deferrable_loads` (217), `async_setup` (388), `async_get_recurring_trips` (675), `async_get_punctual_trips` (679), `get_all_trips` (683), `async_add_recurring_trip` (694), `async_add_punctual_trip` (757), `async_update_trip` (819), `async_delete_trip` (907), `async_delete_all_trips` (948), `async_pause_recurring_trip` (1038), `async_resume_recurring_trip` (1056), `async_update_trip_sensor` (1074), `async_complete_punctual_trip` (1164), `async_cancel_punctual_trip` (1182), `async_get_kwh_needed_today` (1362), `async_get_hours_needed_today` (1374), `get_charging_power` (1401), `async_get_next_trip` (1458), `async_get_next_trip_after` (1476), `async_get_vehicle_soc` (1577), `async_calcular_energia_necesaria` (1600), `calcular_ventana_carga` (1717), `calcular_ventana_carga_multitrip` (1848), `calcular_soc_inicio_trips` (1977), `calcular_hitos_soc` (2055), `async_generate_power_profile` (2208), `async_generate_deferrables_schedule` (2323), and `async_save_trips` (584).

Plus internals callable from outside today (consumed by tests): `_load_trips`, `_load_trips_yaml`, `_save_trips_yaml`, `_async_sync_trip_to_emhass`, `_async_publish_new_trip_to_emhass`. These are touched by integration tests only — should remain in `trip/crud.py` (the refactor must not break test access; tests will be updated).

### 3.3 `services.py` (10 public functions)
See §2.2 for the canonical list.

### 3.4 `dashboard.py` (2 + 4 classes public)
Public functions: `is_lovelace_available` (261), `import_dashboard` (281).
Public classes: `DashboardError` (121), `DashboardNotFoundError` (136), `DashboardValidationError` (157), `DashboardStorageError` (177), `DashboardImportResult` (198).
**Re-export contract**: at minimum the 3 names listed in epic.md (`import_dashboard`, `is_lovelace_available`, `DashboardImportResult`) — recommend re-exporting all 5 exception classes too because tests assert on them.

### 3.5 `vehicle_controller.py` (1 + ABC public + factory)
Public class on `VehicleController`: `__init__`, `async_setup`, `set_strategy`, `update_config`, `async_check_presence_status`, `async_activate_charging`, `reset_retry_state`, `get_retry_state`, `async_deactivate_charging`, `async_get_charging_status` (10 public methods).
ABC + 4 strategies (`VehicleControlStrategy`, `SwitchStrategy`, `ServiceStrategy`, `ScriptStrategy`, `ExternalStrategy`), and helper classes `RetryState`, `HomeAssistantWrapper`, plus `create_control_strategy()`.
**Re-export contract**: only `VehicleController` is required (per epic). However, to be safe re-export `create_control_strategy` and the abstract `VehicleControlStrategy` (allows future subclassing in HA tests).

### 3.6 `calculations.py` (17 + 2 classes public)
Full list in §2.2. All 20 names must be re-exported by `calculations/__init__.py`.

## 4. Circular-cycle analysis

### 4.1 Current state
`pyproject.toml` declares `[tool.import-linter]` with `root_package = "custom_components"` but **no contracts** are configured (verified — only the root_package line). Running `lint-imports` returns "Could not read any configuration." — there's no `[[tool.import-linter.contracts]]` block.

### 4.2 Cycle 1: `coordinator → trip_manager → sensor → coordinator`
- `coordinator.py:30` real import: `from .trip_manager import TripManager`.
- `trip_manager.py` does NOT import `sensor` at module level — it has **7 in-function lazy imports** (lines 732, 741, 794, 803, 893, 931, 938): `from .sensor import async_create_trip_sensor, async_remove_trip_sensor, async_update_trip_sensor, async_create_trip_emhass_sensor, async_remove_trip_emhass_sensor`. Each is wrapped in a comment `# Local import to avoid circular dependency`.
- `sensor.py:38` real import: `from .coordinator import TripPlannerCoordinator`.
- **Module-load cycle status**: BROKEN at runtime by lazy imports. **Logical cycle status**: PRESENT (`sensor` is invoked from `trip_manager` to create/remove HA entities). This is a SRP violation: `TripManager` reaches into the sensor module.
- **Recommended fix**: Use a callback/event injected into `TripManager` constructor (DI) — `trip_manager` should emit "trip created/updated/deleted" events; the sensor platform subscribes. Alternative: move sensor manipulation into `coordinator.async_refresh_trips()` (which already exists) so `trip_manager` only mutates state. Cheapest fix that satisfies ARN-004: keep lazy imports but add an explicit `[[tool.import-linter.contracts]]` "forbidden" rule banning `trip → sensor` at module-load. This documents the intent without major refactor.

### 4.3 Cycle 2: `trip_manager → vehicle_controller → presence_monitor → trip_manager`
- `trip_manager.py:42` real import: `from .vehicle_controller import VehicleController`.
- `vehicle_controller.py:12` real import: `from .presence_monitor import PresenceMonitor`.
- `presence_monitor.py:23-24`: `if TYPE_CHECKING: from .trip_manager import TripManager` — type-only.
- **Module-load cycle status**: BROKEN (presence_monitor uses TYPE_CHECKING).
- **Recommended fix**: nothing required at runtime; add an `import-linter` contract documenting that `presence_monitor` must not import `trip_manager` at module-load (only `TYPE_CHECKING`).

### 4.4 Cycle 3: `trip_manager → vehicle_controller → trip_manager`
- `trip_manager.py:42` real import: `from .vehicle_controller import VehicleController`.
- `vehicle_controller.py:14-15`: `if TYPE_CHECKING: from .trip_manager import TripManager` — type-only.
- **Module-load cycle status**: BROKEN (TYPE_CHECKING).
- **Recommended fix**: same as 4.3 — add a contract documenting it; no runtime change.

### 4.5 Recommendation
Two of three cycles are already broken at module-load via `TYPE_CHECKING`. Cycle 1 is broken via lazy imports (less ideal — it's a runtime escape hatch, not a clean architectural separation). The acceptance for ARN-004 should be: **`make import-check` runs with import-linter contracts that forbid `trip ↔ sensor` and `presence ↔ trip` cycles, and passes with 0 violations.** A cleaner fix for cycle 1 (DI callback) is out-of-scope for "preserve public API" but within scope if added without changing observable behavior. Recommend deferring deep DI to Spec 4 or a future spec; this spec only needs to land contracts + (optionally) replace lazy imports with TYPE_CHECKING + an injected callback for the 7 sensor calls.

## 5. Splitting strategy per module

Naming follows epic.md AC-3.0 through AC-3.3. Function/method counts use the line number tables in §3.

### 5.1 `emhass_adapter.py` → `emhass/`
- `emhass/__init__.py` — re-exports `EMHASSAdapter` (and constants currently re-imported from `.calculations` if any).
- `emhass/index_manager.py` (≤ 500 LOC) — `async_assign_index_to_trip`, `async_release_trip_index`, `get_assigned_index`, `get_all_assigned_indices`, `get_available_indices`, `async_cleanup_vehicle_indices`, `verify_cleanup`, `_get_config_sensor_id`. ~7-8 methods. Persistence to `Store` belongs here.
- `emhass/load_publisher.py` — `async_publish_deferrable_load`, `async_update_deferrable_load`, `async_publish_all_deferrable_loads`, `async_remove_deferrable_load`, `_calculate_deadline_from_trip`, `_populate_per_trip_cache_entry`, `calculate_deferrable_parameters` (façade), `publish_deferrable_loads`, `get_cached_optimization_results`, `update_charging_power`, `setup_config_entry_listener`, `_handle_config_entry_update`, `_calculate_power_profile_from_trips`, `_generate_schedule_from_trips`, `_get_current_soc`, `_get_hora_regreso`, `_get_coordinator`. **WARNING: this concentrates ~17 methods including `_populate_per_trip_cache_entry` (266 LOC, lines 586-852)** — likely overflows 500-LOC budget. Either further-split (e.g., `cache_builder.py`) or accept >500 LOC and document a deviation in design.
- `emhass/error_handler.py` — `async_notify_error`, `_async_update_error_status`, `_async_send_error_notification`, `_async_call_notification_service`, `async_handle_emhass_unavailable`, `async_handle_sensor_error`, `async_handle_shell_command_failure`, `get_last_error`, `async_clear_error`, `async_verify_shell_command_integration`, `async_check_emhass_response_sensors`, `async_get_integration_status`. ~12 methods.
- `emhass/adapter.py` (or remain inside `__init__.py`) — `EMHASSAdapter` façade class that aggregates the three sub-objects via composition. `async_load`, `async_save`, `__init__` stay here.
- **Doesn't fit cleanly**: `_populate_per_trip_cache_entry` (266 LOC) — should be moved to a private `cache_entry_builder.py` to stay under ARN-001.

### 5.2 `trip_manager.py` → `trip/`
- `trip/__init__.py` — re-exports `TripManager`.
- `trip/crud.py` — `async_setup`, `_load_trips`, `_load_trips_yaml`, `_reset_trips`, `async_save_trips`, `_save_trips_yaml`, `_sanitize_recurring_trips`, `_validate_hora`, `_parse_trip_datetime`, `async_get_recurring_trips`, `async_get_punctual_trips`, `get_all_trips`, `async_add_recurring_trip`, `async_add_punctual_trip`, `async_update_trip`, `async_delete_trip`, `async_delete_all_trips`, `async_pause_recurring_trip`, `async_resume_recurring_trip`, `async_complete_punctual_trip`, `async_cancel_punctual_trip`, `_async_sync_trip_to_emhass`, `_async_remove_trip_from_emhass`, `_async_publish_new_trip_to_emhass`, `async_update_trip_sensor`. **Risk: ~24 methods + 7 lazy `from .sensor import` calls. Probably > 500 LOC** — split CRUD-write (`_async_sync_trip_to_emhass` family) into `trip/emhass_sync.py` if needed.
- `trip/soc_calculator.py` — `_get_charging_power`, `get_charging_power`, `_calcular_tasa_carga_soc`, `_calcular_soc_objetivo_base`, `async_get_vehicle_soc`, `async_calcular_energia_necesaria`, `calcular_ventana_carga`, `calcular_ventana_carga_multitrip`, `calcular_soc_inicio_trips`, `calcular_hitos_soc`, `async_get_kwh_needed_today`, `async_get_hours_needed_today`, `async_get_next_trip`, `async_get_next_trip_after`, `_is_trip_today`, `_get_trip_time`, `_get_day_index`. ~17 methods.
- `trip/power_profile.py` — `async_generate_power_profile` and the helpers it calls. ~1-3 methods. Small.
- `trip/schedule_generator.py` — `async_generate_deferrables_schedule`, `_get_all_active_trips`, `publish_deferrable_loads`. ~3 methods.
- `TripManager` is a façade in `__init__.py` (or `trip/manager.py` re-exported) holding shared state and delegating to mixin/composition. Recommendation: **composition over inheritance** — sub-classes don't share `self` cleanly otherwise. But if the methods are tightly bound to `self.hass`, `self._trips`, `self._storage`, splitting via mixins (multiple inheritance) is more pragmatic and what HA core does in many places.
- **Doesn't fit cleanly**: `_async_sync_trip_to_emhass` (79 LOC) and `async_update_trip_sensor` (90 LOC) bridge CRUD ↔ EMHASS ↔ sensor. They should stay in `crud.py` but the lazy `from .sensor import …` calls should be replaced with constructor-injected callbacks (clean architecture) or kept as-is (pragmatic).

### 5.3 `services.py` → `services/`
- `services/__init__.py` — re-exports the 10 public functions.
- `services/handlers.py` — `register_services` (the ~688-line registration function with all inner service handlers). **Risk**: this single function is the bulk of the file. Likely needs to be split further: `services/trip_handlers.py`, `services/dashboard_handlers.py`. Alternative: keep `register_services` as the dispatcher and move each `_handle_*` into thematic files.
- `services/dashboard_helpers.py` — `create_dashboard_input_helpers` (lines 813-1119, ~307 LOC), `async_register_panel_for_entry` (1318), `async_register_static_paths` (1219), `async_import_dashboard_for_entry` (1360).
- `services/cleanup.py` — `async_cleanup_stale_storage` (1120), `async_cleanup_orphaned_emhass_sensors` (1167), `async_unload_entry_cleanup` (1396), `async_remove_entry_cleanup` (1502), `build_presence_config` (1187).
- **Doesn't fit cleanly**: `register_services` is 688 LOC (lines 31-688). Either accept it overflows 500 and add a `# noqa: ARN-001` comment with rationale, or break inner handlers into a `services/trip_handlers.py` with `register_services` calling them.

### 5.4 `dashboard.py` → `dashboard/`
- **Naming conflict**: `custom_components/ev_trip_planner/dashboard/` already exists with 11 template files (`dashboard.yaml`, `ev-trip-planner-full.yaml`, etc.). It currently has NO `__init__.py` (verified — the directory is a templates folder loaded via `pathlib`). **Plan**: introduce `dashboard/__init__.py`, move all 11 files into `dashboard/templates/`, update template-loading code paths to read from `dashboard/templates/` instead of `dashboard/`.
- `dashboard/__init__.py` — re-exports `import_dashboard`, `is_lovelace_available`, `DashboardImportResult`, `DashboardError`, `DashboardNotFoundError`, `DashboardValidationError`, `DashboardStorageError`.
- `dashboard/importer.py` — `import_dashboard`, `is_lovelace_available`, `DashboardImportResult`, `DashboardError` family.
- `dashboard/template_manager.py` — `_load_dashboard_template`, `_save_lovelace_dashboard`, `_save_dashboard_yaml_fallback`, `_validate_dashboard_config`, `_verify_storage_permissions`, `_call_async_executor_sync`, `_await_executor_result`, `_read_file_content`, `_write_file_content`, `_check_path_exists`, `_create_directory`.
- `dashboard/templates/` — all 11 YAML/JS files moved here.
- **Test impact**: `test_dashboard.py` and `test_dashboard_validation.py` use ~80 lazy imports of private helpers — these need to be redirected. Recommendation: keep helper names re-exported in `dashboard/__init__.py` for compatibility OR (cleaner) update tests to import from `dashboard.template_manager`. Choose during requirements phase based on diff size.
- **Path-loading impact**: any code that reads `dashboard/foo.yaml` (e.g., loading templates by `Path(__file__).parent / "dashboard" / "foo.yaml"`) needs path update to `dashboard/templates/foo.yaml`.

### 5.5 `vehicle_controller.py` → `vehicle/`
- `vehicle/__init__.py` — re-exports `VehicleController`, `VehicleControlStrategy`, `create_control_strategy`.
- `vehicle/strategy.py` — `VehicleControlStrategy` (ABC), `SwitchStrategy`, `ServiceStrategy`, `RetryState`, `HomeAssistantWrapper`. ~250-300 LOC.
- `vehicle/external.py` — `ScriptStrategy`, `ExternalStrategy`. ~100 LOC.
- `vehicle/controller.py` — `VehicleController`, `create_control_strategy`. ~250-300 LOC.
- All sub-modules safely under 500 LOC.

### 5.6 `calculations.py` → `calculations/`
- `calculations/__init__.py` — re-exports the 20 names listed in §2.2.
- `calculations/windows.py` — `calculate_charging_window_pure` (520-602), `calculate_multi_trip_charging_windows` (610-737), `calculate_hours_deficit_propagation` (740-802), `calculate_soc_at_trip_starts` (804-869), `_ensure_aware`, helpers. ~350 LOC.
- `calculations/power.py` — `calculate_power_profile_from_trips` (1148-1356), `calculate_power_profile` (1357-1500), `generate_deferrable_schedule_from_trips` (1501-1610), `calculate_deferrable_parameters` (1611+ to EOF). ~540 LOC — **overflows 500 LOC; further-split into `power_profile.py` + `deferrable_schedule.py`** (deferrable schedule is logically separate).
- `calculations/deficit.py` — `calculate_deficit_propagation` (870-1046), `calculate_next_recurring_datetime` (1047-1147), `determine_charging_need` (378-431), `ChargingDecision` (364), `calculate_energy_needed` (432-519). ~370 LOC.
- `calculations/core.py` — `BatteryCapacity` (54), `calculate_dynamic_soc_limit` (116), `calculate_day_index` (177), `calculate_trip_time` (220), `calculate_charging_rate` (307), `calculate_soc_target` (326), `DEFAULT_T_BASE`, etc. ~300 LOC.
- **Doesn't fit cleanly**: `_ensure_aware` is a private helper used in multiple files — keep in `calculations/_helpers.py` and import internally.

#### 5.6.1 `ventana_horas` bug fix during the calculations split
- Location: [`calculations.py:698-699`](../../custom_components/ev_trip_planner/calculations.py#L698) inside `calculate_multi_trip_charging_windows`.
- Current code: `delta = trip_arrival_aware - window_start_aware; ventana_horas = max(0.0, delta.total_seconds() / 3600)`. `trip_arrival = trip_departure_time + duration_hours(6h)`. So `ventana_horas` is inflated by the 6h "away" period.
- **Fix per ROADMAP.md:218-221**: change to `delta = trip_departure_time - window_start_aware`. The window legitimately ends at `trip_departure_time` (line 726 confirms `fin_ventana = trip_departure_time`).
- **Test impact**: `tests/unit/test_single_trip_hora_regreso_past.py` asserts `ventana_horas == pytest.approx(102.0, abs=0.02)` and `ventana_horas == 98.0` and `ventana_horas == pytest.approx(...)`. The 102 vs 98 difference is **~4h delta** — this looks like the test was authored to match the buggy behavior (102 = 96 + 6 buffer; 98 = 92 + 6 buffer? — needs careful inspection during implementation). **Action for design phase**: re-derive expected ventana_horas with the corrected formula; update assertions; record the rationale in the test docstring. `tests/unit/test_soc_milestone.py` uses ventana_horas as **input** (passes it into a fixture), not as an assertion target — those tests are unaffected.

## 6. SOLID Detection Methods — Beyond LOC and Method Count

ARN-001 (≤500 LOC) and ARN-002 (≤20 methods/class) are **screens for god classes**, not SOLID definitions. Each SOLID letter has a distinct, testable meaning. This section defines per-letter detection methods that replace LOC/count as actual quality gates.

### 6.1 S — Single Responsibility

**Detection metrics beyond LOC:**

| Metric | What it measures | Tool/Method | Threshold | Current State |
|--------|-----------------|-------------|-----------|---------------|
| **LCOM4** (Lack of Cohesion of Methods) | Number of method pairs sharing no instance attributes | Custom AST analysis | ≤ 25 per class; ≤ 0.40 ratio | TripManager=212 (FAIL), EMHASSAdapter=113 (FAIL) |
| **LCOM-HS** (Henderson-Sellers) | Sharedness of instance attributes across methods | `cohesion` PyPI package or AST | ≤ 5 | FlowHandler=8 (moderate) |
| **Cohesion ratio** | `shared_pairs / total_pairs` | AST method-attribute matrix | ≥ 0.75 | TripManager=0.573 (borderline) |
| **Verb diversity** | Unique action verbs in method names (e.g. `save_`, `calc_`, `notify_`) | String parsing of names | ≤ 5 unique verbs | TripManager=14 (FAIL), EMHASSAdapter=15 (FAIL) |
| **Fan-out** | Number of internal classes a class imports/uses | AST import analysis | ≤ 5 internal imports | TripManager imports calculations, const, emhass_adapter, utils, vehicle_controller, yaml_trip_storage, sensor |

**5-minute SRP reviewer checklist:**
- [ ] Can you summarize the class purpose in one sentence **without "and"**?
- [ ] If you imagine 3 different stakeholders, do their requested changes hit **disjoint method sets**?
- [ ] LCOM4 ≤ 25?
- [ ] Method names share a verb family (all `save_*` OR all `calc_*`, not mixed)?
- [ ] No method calls more attributes of `self` than the class median (Feature Envy = AP09)?

### 6.2 O — Open/Closed

**Detection metrics:**

| Metric | What it measures | Tool/Method | Threshold | Current State |
|--------|-----------------|-------------|-----------|---------------|
| **ABC/Protocol usage ratio** | Fraction of classes that are abstract/extensible | AST + class map | ≥ 15% | 1% (only VehicleControlStrategy) |
| **Type-switch chain length** | `isinstance()` / `if-elif` over discriminators | AST traversal | ≤ 2 branches | 3 minor chains in sensor.py, utils.py |
| **Discriminator chain length** | `if x == "A": elif x == "B":` chains | AST traversal | ≤ 2 | 2 found in emhass_adapter.py, vehicle_controller.py |

### 6.3 L — Liskov Substitution

**Detection metrics:**

| Metric | What it measures | Tool/Method | Threshold | Current State |
|--------|-----------------|-------------|-----------|---------------|
| **Type hint coverage** | % of functions with typed params and returns | AST analysis | ≥ 90% | Already tracked by solid_metrics.py |
| **Abstract method override compliance** | Subclasses implementing all ABC abstract methods | AST + class map | 0 missing | All 5 strategies override correctly |
| **Return type covariance** | Subclass returns narrower type than parent | pyright/mypy | 0 violations | N/A (only 1 ABC) |

### 6.4 I — Interface Segregation

**Detection metrics:**

| Metric | What it measures | Tool/Method | Threshold | Current State |
|--------|-----------------|-------------|-----------|---------------|
| **Unused public method ratio** | % of public methods never called outside class/module | Call-site analysis | ≤ 15% | Needs HA callback exclusion list |
| **Interface size** | Methods per Protocol/ABC | AST method count | ≤ 5 | VehicleControlStrategy=3 (good) |

### 6.5 D — Dependency Inversion

**Detection metrics:**

| Metric | What it measures | Tool/Method | Threshold | Current State |
|--------|-----------------|-------------|-----------|---------------|
| **Import cycles** | Circular module imports | `lint-imports` | 0 cycles | 0 module-load cycles (lazy imports present) |
| **Import chain depth** | Max depth of import DAG | AST dependency traversal | ≤ 3 | 1 (shallow) |
| **Concrete constructor deps** | Direct concrete class constructor params vs abstractions | AST `__init__` analysis | 0 concrete deps | 4 found (HomeAssistantWrapper used in ABC) |
| **Inline instantiation ratio** | `self.x = SomeClass()` vs DI injection in `__init__` | AST in `__init__` | 0 inline | 4 found (BatteryCapacity, VehicleController, RetryState, PresenceMonitor) |
| **Lazy import escape hatches** | `from .module import ...` inside methods to avoid cycles | grep | 0 | 7 in trip_manager.py + 3 in services.py |

### 6.6 Proposed ARN Rules (replacement for ARN-001/ARN-002)

| Rule | Current | Target | Detection |
|------|---------|--------|-----------|
| ARN-001: LOC per module | ≤ 500 | ≤ 500 (keep as screen) | wc -l |
| ARN-002: Public methods per class | ≤ 20 | **Superseded** by LCOM4 + verb diversity | Custom AST |
| **ARN-003: LCOM4** | — | ≤ 25 per class; ≤ 0.40 ratio | Custom AST |
| **ARN-004: Verb diversity** | — | ≤ 5 unique action verbs | String parsing |
| **ARN-005: Zero import cycles** | Already tracked | 0 cycles + no lazy imports | lint-imports + grep |
| **ARN-006: 0 inline instantiation in `__init__`** | — | All collaborators DI-injected | AST in `__init__` |
| **ARN-007: Type hint coverage ≥ 90%** | Already tracked | ≥ 90% | solid_metrics.py |

**Why supersede ARN-002:** A class with 8 methods can still violate SRP if they have 8 different verbs (`save`, `load`, `calc`, `publish`, `notify`, `cleanup`, `sync`, `validate`). A class with 15 methods can be SRP-clean if they all share the same verb (`save_*`, `load_*`). ARN-002 catches the symptom (too many methods); ARN-003/ARN-004 catch the cause (multiple responsibilities).

### 6.7 Tooling Implementation

| Tool | Installed | Role | Action Needed |
|------|-----------|------|---------------|
| `solid_metrics.py` | Yes | LOC, public methods, arity, ABC ratio, type hints, import depth/cycles | Add LCOM4, verb diversity, composition ratio modules |
| `principles_checker.py` | Yes | DRY, KISS, YAGNI, LoD, CoI | No change |
| `antipattern_checker.py` | Yes | 25 Tier A patterns (AP01–AP39, AP39) | No change |
| `import-linter` | Yes | Import cycle detection | **Configure contracts in pyproject.toml** |
| `lint-imports` | Yes | Import ordering | **Configure contracts in pyproject.toml** |
| `radon` | **NO** | Cyclomatic complexity, maintainability index | **Install: `pip install radon`** |
| `cohesion` | **NO** | LCOM-HS calculation | **Install: `pip install cohesion`** (optional — AST alternative exists) |

---

## 7. Risk inventory

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| 1 | Public-API breakage (callers in `__init__.py`, `services.py`, `coordinator.py`, `sensor.py`, `config_flow.py`, `panel.py`) | HA integration won't load; CI red | `__init__.py` re-export contract per package; pyright + integration tests as gate; checkpoint commit per module |
| 2 | `mutmut` config (`paths_to_mutate = ["custom_components/ev_trip_planner"]`, `tests_dir = ["tests/unit/", "tests/integration/"]`) — paths are at package level so they auto-include sub-packages. Per-module quality-gate config (`[tool.quality-gate.mutation.modules.<name>]`) lists 8 modules: calculations, utils, definitions, sensor, presence_monitor, trip_manager, emhass_adapter, config_flow. After split, `trip_manager` and `emhass_adapter` and `calculations` entries become invalid. | Mutation gate fails post-merge | Update `pyproject.toml`: replace `[tool.quality-gate.mutation.modules.trip_manager]` with entries for each new sub-module (`trip.crud`, `trip.soc_calculator`, ...). Same for `emhass.*` and `calculations.*`. AC-3.9 in epic.md addresses this. |
| 3 | `services.yaml` references stable service IDs (`add_recurring_trip`, `add_punctual_trip`, `edit_trip`, `delete_trip`, `pause_recurring_trip`, `resume_recurring_trip`, `complete_punctual_trip`, `cancel_punctual_trip`, `trip_list`). Service handler **names** are internal but their **registration via `register_services()`** must stay intact. | HA service calls would 404 | `register_services` re-exported as-is; service IDs registered with same string keys; no change needed in `services.yaml` |
| 4 | Test imports — many tests use `from custom_components.ev_trip_planner.<module> import X`. After split, that import path still works (re-exports), but tests that reach into private helpers (`_load_dashboard_template`, etc.) need updating | Test failures | Re-export private dashboard helpers in `dashboard/__init__.py` as a transitional measure; update tests in a follow-up commit |
| 5 | HA entry-point in `__init__.py` — currently imports `EMHASSAdapter`, `TripManager`, and 9 functions from `services` | Integration setup_entry fails on first call | Re-export contract preserves all 11 names; pyright + `make test` cover this |
| 6 | `dashboard/` naming conflict — existing templates dir | Python ImportError if `__init__.py` is added to a non-package | Move 11 template files to `dashboard/templates/` BEFORE creating `dashboard/__init__.py`; update path-loading code in `dashboard.py` accordingly |
| 7 | `ventana_horas` bug fix breaks `test_single_trip_hora_regreso_past.py` | Test failure (intentional during fix) | Update assertions in the SAME commit as the fix; tag both as `[ARN-bug]` so the diff is reviewable; document recomputed expected values in test docstrings |
| 8 | `register_services()` is 688 LOC of nested service handlers — splitting it is invasive | Massive diff in services/ split | Keep `register_services` in `services/handlers.py` and accept ARN-001 deviation OR break each inner handler out (risk: handler closures over `hass` and `entry` make extraction non-trivial) |
| 9 | `_populate_per_trip_cache_entry` (266 LOC) is one method | Sub-module overflows 500 LOC | Move to a private `_cache_entry_builder.py` inside `emhass/` |
| 10 | `lint-imports` has no contracts configured — no automated cycle check today | Cycles re-introduced silently | Add explicit contracts in `pyproject.toml` and wire to `make import-check`; this is part of AC-3.4 |
| 11 | Lazy imports in `trip_manager.py` (`from .sensor import …` 7 times) preserve runtime behavior but smell of architectural debt | Future cycles | Keep them but add a `# TODO(ARN-004 cleanup)` comment; deeper DI deferred to Spec 4 or future spec |

## 8. Existing related work

`specs/solid-refactor-coverage/` is **completed** (closed) and is a different scope (Protocol DI for `TripManager` + `EMHASSAdapter`, populated `tests/__init__.py` Layer 1 doubles, and the `protocols.py` module). Reusable decisions:

| Decision | Source | Reuse here |
|---|---|---|
| Pure functions extracted from `TripManager` to `utils.py` (`validate_hora`, `sanitize_recurring_trips`, `is_trip_today`, `get_trip_time`, `get_day_index`) | [`design.md`](../solid-refactor-coverage/design.md) §"Pure Functions to Extract" | Already in `utils.py` — `trip/crud.py` imports them via the existing `from .utils import …` pattern |
| Pure functions extracted from `EMHASSAdapter` to `calculations.py` (`calculate_deferrable_parameters`, `calculate_power_profile_from_trips`, `generate_deferrable_schedule_from_trips`) | same | Already in `calculations.py` — `emhass/load_publisher.py` imports them |
| `_UNSET = object()` sentinel for DI defaults instead of `\| None = None` (AC-C1.3) | same | Out-of-scope here; existing code already uses this pattern |
| `protocols.py` with `@runtime_checkable TripStorageProtocol` and `EMHASSPublisherProtocol` | same, Phase B | Existing — no change |
| Layered Test Doubles Strategy (Layer 1 fakes in `tests/__init__.py`, Layer 3 fixtures in conftest) | same, Phase D | Reuse: tests after split keep the same Layer 1/Layer 3 strategy |

Do NOT copy that spec's task structure here — its scope was DI + pure-function extraction, not module splitting.

### 8.1 Tools that need config update for this spec

| Tool | What changes | Where |
|---|---|---|
| `mutmut` (per-module quality-gate config) | `[tool.quality-gate.mutation.modules.trip_manager]` → split into `trip.crud`, `trip.soc_calculator`, `trip.power_profile`, `trip.schedule_generator` entries. Same for `emhass_adapter` → `emhass.*`. Same for `calculations` → `calculations.*`. | `pyproject.toml` |
| `import-linter` | Add `[[tool.import-linter.contracts]]` blocks: forbid `trip → sensor` cycle, forbid `presence_monitor → trip` runtime cycle, define layered contracts for new packages (e.g., `dashboard` cannot import from `trip`) | `pyproject.toml` |
| `make import-check` target | Currently runs `ruff --select I` (import sort). Should ALSO run `lint-imports` to catch cycles | `Makefile` |
| `coverage` | `source = ["custom_components/ev_trip_planner"]` is package-level — no change needed; sub-packages auto-discovered | `pyproject.toml` |
| `[tool.coverage.report]` | If `pragma: no cover` lines move during split, coverage may regress — check `make test-cover` after each sub-module commit | `pyproject.toml` |
| `pytest` `testpaths` | `tests/unit`, `tests/integration` — no change | `pyproject.toml` |

## 9. Tooling

Verified available in `.venv` (path: `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/.venv/bin/`):
- `pyright` ✅ — primary type checker (mypy is broken/skipped per AC-0.5)
- `lint-imports` ✅ — installed but **no contracts configured**; running it returns "Could not read any configuration"
- `deptry` ✅
- `vulture` ✅
- `mutmut` ✅

Makefile targets (verified in `Makefile`):
- `make test`, `make test-cover`, `make test-verbose`, `make test-dashboard`
- `make lint`, `make format`, `make typecheck`
- `make e2e` (`scripts/run-e2e.sh`), `make e2e-soc` (`scripts/run-e2e-soc.sh`), `make e2e-headed`, `make e2e-debug`
- `make mutation`, `make mutation-gate`
- `make quality-gate`, `make quality-gate-ci`
- `make security-bandit`, `make security-audit`, `make security-gitleaks`, `make security-semgrep`
- `make import-check` ✅ (currently runs `ruff --select I`, NOT `lint-imports`)
- `make dead-code` (vulture), `make unused-deps` (deptry)
- `make refurb`, `make pre-commit-install`, `make pre-commit-run`

## 10. Process constraints (HARD REQUIREMENTS — task-planner MUST respect)

**Verbatim from `.progress.md` §"Process Constraints" — these are non-negotiable.**

1. **No CodeRabbit auto-wait task.** The PR creation step is the LAST automated step. Human (joao) triggers `@coderabbitai review` manually after PR creation. Do NOT include any `wait-for-coderabbit` or `poll-for-review` task. The closing message of the loop is "PR created and ready for human review".

2. **Gito reviews via `/gito-review-with-spec` ONLY.** Before invoking, verify:
   - Spec context paths: `specs/3-solid-refactor/research.md`, `specs/3-solid-refactor/requirements.md`, `specs/3-solid-refactor/design.md`.
   - Explicit branches: head=`spec/3-solid-refactor`, base=`epic/tech-debt-cleanup`.
   - `.gito/config.toml` `exclude_files` list is adequate for this spec (must include any moved/renamed paths).

3. **Every task updates `chat.md` BEFORE its verify step.** Format: `[<task-id>] DOING: <what> — REASON: <why>`. Tasks lacking this update are rejected by the coordinator.

## 11. Recommended Approach

### 11.1 Order (lowest-risk first)
1. **`vehicle_controller.py` → `vehicle/`** — smallest (537 LOC), 1 external consumer (`trip_manager`), strategies are already independent classes. Lowest blast radius.
2. **`calculations.py` → `calculations/`** — large but pure-function module, 100% deterministic, easy to split by topic (windows / power / deficit / core). Includes the `ventana_horas` bug fix as a separate commit.
3. **`dashboard.py` → `dashboard/`** — must FIRST move 11 template files to `dashboard/templates/`, THEN add `__init__.py`. 2 source consumers (`config_flow`, `services`); ~80 test imports of private helpers — re-export them.
4. **`services.py` → `services/`** — single source consumer (`__init__.py`), but `register_services` is 688 LOC of inner handlers. Largest individual function in the codebase. Likely needs its own deviation from ARN-001.
5. **`emhass_adapter.py` → `emhass/`** — 27 public methods, 24 test files import from it. Large, but boundaries are clear (index / publish / error). The `_populate_per_trip_cache_entry` (266 LOC) needs its own private file.
6. **`trip_manager.py` → `trip/`** — 31 public methods, ~10 test files. The most-coupled (imports `EMHASSAdapter` and `VehicleController` from sibling packages, lazy imports `sensor`). Save for last so all dependencies are settled.

### 11.2 Checkpoint commits per split
For each module M:
1. **Pre-commit (skip if not applicable)**: move templates / static files to new sub-folder.
2. **Skeleton commit**: create new package directory + empty `__init__.py` + sub-modules. Old `M.py` still exists. `make test` passes.
3. **Move-and-re-export commit**: move methods/functions into sub-modules. `M.py` becomes a 1-line re-export `from .M_pkg import *` (transitional). `make test` passes.
4. **Caller-update commit**: update internal callers (`coordinator`, `services`, `__init__`, etc.) to import from new package directly. Old `M.py` stub deleted. `make test` passes.
5. **Mutation-config commit**: update `pyproject.toml` `[tool.quality-gate.mutation.modules]` entries.
6. **Lint-imports commit**: add `[[tool.import-linter.contracts]]` for the new package (after all 6 are done OR per-module).

### 11.3 Rollback strategy
- Each checkpoint is an atomic git commit. A failing `make test` after step 3 of any module = revert step 3 only, re-attempt with smaller batches (e.g., split the methods into multiple commits).
- The branch is `spec/3-solid-refactor` (PR target = `epic/tech-debt-cleanup`). Catastrophic failure = `git reset --hard <last-good-sha>`. Recommend tagging each module's "module M complete" SHA in commit message: `refactor(spec3): vehicle/ split complete — checkpoint`.
- Final verification before PR: `make quality-gate` end-to-end; `pyright` zero-error; `lint-imports` (with new contracts) zero violations; `make e2e` and `make e2e-soc` both pass.

## 12. Open Questions

1. **`register_services` (688 LOC) — split or `# noqa: ARN-001`?** Inner handlers close over `hass` and `entry` and use lots of validation logic. Splitting is non-trivial. Recommend: **document an exception** for this single function in the spec's design doc, OR mandate a split (significantly enlarging this spec). **Decision needed before requirements.**
2. **`_populate_per_trip_cache_entry` (266 LOC) — separate file inside `emhass/`?** The function builds the cache entry for one trip; pulling it out is clean but adds a file. Recommend: yes, put it in `emhass/_cache_entry_builder.py`. **Confirm.**
3. **Cycle 1 (`trip → sensor`) — clean fix or just lint-imports contract?** Cleanest fix (DI callback) involves redesigning `TripManager.__init__` and how `sensor` registers callbacks; that's potentially Spec-4-sized. Pragmatic fix: add `[[tool.import-linter.contracts]]` rule "forbidden", keep lazy imports, document `TODO(spec-4)`. **Recommend the pragmatic fix here; flag for future spec.**
4. **Re-export private dashboard helpers (`_load_dashboard_template` etc.) from `dashboard/__init__.py` for transitional test compatibility?** OR update ~80 test import statements to point to `dashboard/template_manager.py`? **Recommend: re-export with a `# transitional` comment, plan test cleanup as a separate small commit at the end.**
5. **`ventana_horas` test recompute** — `test_single_trip_hora_regreso_past.py` asserts 102.0 and 98.0. With the bug fix, expected values are different (likely 96.0 and 92.0 if the buffer was the inflated component). **Need a quick sanity check during design phase to recompute exact expected values from the trip definitions in the test setup.**
6. **Composition vs. mixins for the new `TripManager` façade?** Mixins (multiple inheritance) preserve `self` semantics naturally but are stylistically heavy. Composition is cleaner architecturally but requires plumbing `self.hass`, `self._trips`, `self._storage`, `self._emhass_adapter` into each sub-object. **Recommend mixins for `TripManager` (pragmatic; HA core uses this pattern); composition for `EMHASSAdapter` (already separable).**
7. **Should this spec eliminate the 7 lazy `from .sensor import` calls in `trip_manager.py`, or defer?** Eliminating them = clean architecture; deferring = smaller diff. **Recommend defer with explicit `TODO(spec-4)` markers.**

## 13. Design Patterns for Each Package

This section answers: **which patterns to use and WHY** for each of the 6 packages. Not "which files" — that's §5. This is about architecture of the split.

### 13.1 `emhass/` — Facade + Composition

**Primary pattern: Facade (Wr Facade)**
**Secondary: Dependency Injection (constructor-based)**

The `EMHASSAdapter` class aggregates 4 distinct concerns:
- **Index management** (assign/release/cool-down indices, Store persistence)
- **Load publishing** (publish/update/remove deferrable loads, schedule generation, SOC calculation)
- **Error handling** (notify, handle-unavailable, handle-sensor-error, track errors)
- **Config entry lifecycle** (listener setup, charging-power updates, cleanup)

These are orthogonally changeable — you might swap the index storage backend without touching publishing logic. Composition cleanly separates them.

**File structure:**
```
emhass/
  __init__.py        # re-exports EMHASSAdapter (the facade)
  index_manager.py   # IndexManager class — index assignment, release, cooldown, cleanup, Store persistence
  load_publisher.py  # LoadPublisher class — publish/update/remove deferrable loads, schedule generation, cache
  error_handler.py   # ErrorHandler class — notifications, error tracking, sensor error handling
  _cache_entry_builder.py  # _populate_per_trip_cache_entry (266 LOC) — extracted as a private module
```

**What the facade looks like:**

```python
# emhass/__init__.py
class EMHASSAdapter:
    """Facade: aggregates sub-objects via composition. Preserves the original 27-method public API."""

    def __init__(self, hass, entry):
        self.hass = hass
        self._entry = entry
        self._index_manager = IndexManager(hass, entry, self)  # DI: parent reference for _get_coordinator
        self._load_publisher = LoadPublisher(hass, entry, self)
        self._error_handler = ErrorHandler(hass, entry, self)
        # ... shared state that all sub-objects need

    # Delegate pattern — thin pass-through to sub-objects
    async def async_assign_index_to_trip(self, trip_id):
        return await self._index_manager.async_assign(trip_id)

    async def async_release_trip_index(self, trip_id):
        return await self._index_manager.async_release(trip_id)

    async def async_publish_deferrable_load(self, trip):
        return await self._load_publisher.publish(trip)

    async def async_notify_error(self, message):
        return await self._error_handler.notify(message)

    # ... all 27 methods become 1-line delegations
```

**Why NOT mixins here:** Mixins share `self` by inheritance, which works for `TripManager` (where `self.hass`/`self._trips`/`self._storage` are the core state). For `EMHASSAdapter`, the concerns (index, publish, error) don't share a common state object — each sub-object has its own Store or in-memory dicts. Composition is cleaner.

**Why NOT the Service Locator anti-pattern:** Don't inject `hass` into every sub-object and have them look things up. Pass only what each sub-object needs (`hass`, `entry`, optionally a reference to the parent adapter).

**Code example — IndexManager:**

```python
# emhass/index_manager.py
class IndexManager:
    """Manages trip_id → EMHASS deferrable index mapping with Store persistence and cooldown."""

    def __init__(self, hass, entry, adapter_ref):
        self._hass = hass
        self._adapter = adapter_ref
        store_key = f"ev_trip_planner_{entry.data.get(CONF_VEHICLE_NAME)}_emhass_indices"
        self._store: Store[Dict[str, Any]] = Store(hass, version=1, key=store_key)
        self._index_map: Dict[str, int] = {}
        self._available_indices: List[int] = list(range(entry.data.get(CONF_MAX_DEFERRABLE_LOADS, 50)))
        self._released_indices: Dict[int, datetime] = {}

    async def async_load(self):
        data = await self._store.async_load()
        if data:
            self._index_map = data.get("index_map", {})
            self._released_indices = {
                int(k): v for k, v in data.get("released_indices", {}).items()
            }

    async def async_assign(self, trip_id: str) -> Optional[int]:
        # ... logic that uses self._index_map, self._available_indices, etc.

    def get_assigned_index(self, trip_id: str) -> Optional[int]:
        return self._index_map.get(trip_id)
```

**Anti-patterns to avoid:**
- **God Facade** — the facade MUST be thin (1-line delegations). No business logic in `EMHASSAdapter` itself.
- **Leaky Abstraction** — sub-objects should not expose internal state dicts to callers. Only expose through the facade.
- **Circular DI** — `IndexManager` needs a reference to `EMHASSAdapter` for `_get_coordinator()` calls. This is fine (unidirectional: sub → facade). Avoid bidirectional sub ↔ sub references.

### 13.2 `trip/` — Facade + Mixins

**Primary pattern: Facade with Mixin-based composition**
**Secondary: Event/Callback (for sensor decoupling)**

`TripManager` has a unique challenge: **all methods share the same state** (`self.hass`, `self.vehicle_id`, `self._trips`, `self._storage`, `self._emhass_adapter`). Splitting via inheritance (mixins) is the most pragmatic approach because it preserves `self` semantics without verbose plumbing.

HA core uses this pattern extensively. For example, `homeassistant/components/number/__init__.py` uses mixin classes (`NumberEntityDescription`, etc.) that share `self` state.

**File structure:**
```
trip/
  __init__.py       # re-exports TripManager
  crud.py           # CRUD operations — add/update/delete trips, save/load, trip lifecycle
  soc_calculator.py # SOC calculations — ventada_carga, hitos_soc, energy_needed, window_carga
  power_profile.py  # Power profile generation — async_generate_power_profile
  schedule_gen.py   # Schedule generation — deferrables schedule, publish_deferrable_loads
  manager.py        # TripManager facade class + mixin definitions
  _sensor_callbacks.py  # DI callbacks for sensor updates (replaces lazy from .sensor imports)
```

**What mixins look like (pragmatic approach):**

```python
# trip/manager.py
from .crud import _CRUDMixin
from .soc_calculator import _SOCCalculatorMixin
from .power_profile import _PowerProfileMixin
from .schedule_gen import _ScheduleGenMixin

class TripManager(_CRUDMixin, _SOCCalculatorMixin, _PowerProfileMixin, _ScheduleGenMixin):
    """Facade + multiple inheritance from mixin classes.

    Each mixin receives shared state in __init__ via a common base,
    avoiding the need to re-pass self.hass/self._trips to every call.
    """

    def __init__(self, hass, vehicle_id, entry_id, presence_config, storage, emhass_adapter=None):
        self.hass = hass
        self.vehicle_id = vehicle_id
        self._entry_id = entry_id
        self._presence_config = presence_config
        self._storage = storage
        self._emhass_adapter = emhass_adapter
        self._trips: Dict[str, Any] = {"recurring": {}, "punctual": {}}

        # Initialize each mixin, passing shared state
        _CRUDMixin.__init__(self, self._storage)
        _SOCCalculatorMixin.__init__(self, self.hass, self._get_charging_power)
        _PowerProfileMixin.__init__(self, self.hass, self._storage)
        _ScheduleGenMixin.__init__(self, self.hass, self._storage, self._emhass_adapter)

    # Public API delegates to the appropriate mixin
    async def async_add_recurring_trip(self, **kwargs):
        return await _CRUDMixin._async_add_recurring_trip(self, **kwargs)
```

**Alternative: Composition (cleaner but more plumbing)**

If the team prefers composition over multiple inheritance:

```python
class TripManager:
    """Facade with composition. Sub-objects receive shared state explicitly."""

    def __init__(self, hass, vehicle_id, entry_id, presence_config, storage, emhass_adapter=None):
        self.hass = hass
        self._crud = _CRUDState(hass, storage)  # manages self._trips + storage
        self._soc_calc = _SOCCalculator(hass, lambda: self._get_charging_power())
        self._profile = _PowerProfileGenerator(hass, storage)
        self._schedule = _ScheduleGenerator(hass, storage, emhass_adapter)
        # ... shared state that the facade owns
```

Composition is architecturally cleaner (no diamond-inheritance ambiguity) but requires every sub-method to accept `self._trips` or `self.hass` as an explicit argument. **Update 2026-05-12:** After W0231/R0901 analysis, mixin inheritance was replaced by **pure composition** — see plan `estabamos-ejecutando-el-plan-hazy-iverson.md`. Pure composition eliminates pylint W0231/R0901 without any disables.

**Event/Callback pattern for sensor decoupling:**

```python
# trip/_sensor_callbacks.py
from typing import Callable, Optional

class SensorCallbackRegistry:
    """Replacement for lazy `from .sensor import ...` calls.

    TripManager registers callbacks on construction; sensor platform
    sets them. This eliminates the circular dependency cleanly.
    """

    def __init__(self):
        self._callbacks: dict[str, Callable] = {}

    def register(self, name: str, callback: Callable) -> None:
        self._callbacks[name] = callback

    def emit(self, name: str, *args, **kwargs):
        cb = self._callbacks.get(name)
        if cb:
            return cb(*args, **kwargs)

# In trip_manager.py:
# self._sensor_emitter = SensorCallbackRegistry()
# await self._sensor_emitter.emit("update_trip_sensor", trip_data)
# # Sensor platform registers:
# from .services import register_sensor_callbacks
# register_sensor_callbacks(trip_manager._sensor_emitter)
```

**Anti-patterns to avoid:**
- **Fragile Base Class** — mixins must not have hidden dependencies on each other. If `_SOCCalculatorMixin` calls `_CRUDMixin._load_trips()`, the inheritance order matters and is fragile. Keep mixins independent (each has its own responsibility, doesn't call other mixins directly).
- **State Sharing Leak** — don't expose `self._trips` dict directly to mixin callers. Use accessor methods.
- **Mixins with their own __init__ without super()** — each mixin's `__init__` must accept **only the state it needs**, not the whole `self`. Example: `_CRUDMixin.__init__(self, storage)` not `_CRUDMixin.__init__(self, hass, vehicle_id, entry_id, ...)` — the latter duplicates state.

### 13.3 `services/` — Facade (at module level)

**Primary pattern: Module-level facade (register_services as dispatcher)**
**Secondary: Strategy (for service schemas)**

`services.py` is not a class — it's a module with a single large function (`register_services`, 688 LOC) containing nested async handlers. The pattern here is different: it's a **module-level dispatcher** that maps service IDs to handler functions.

**File structure:**
```
services/
  __init__.py        # re-exports the 10 public functions
  handlers.py        # register_services() + all inner _handle_* functions (~688 LOC)
  trip_handlers.py   # TripServiceHandler class — extract the 688 LOC into a class for testability
  cleanup.py         # async_cleanup_stale_storage, async_cleanup_orphaned_emhass_sensors, etc.
  dashboard_helpers.py  # create_dashboard_input_helpers, async_register_panel_for_entry, etc.
```

**Recommended approach for register_services:**

The 688-LOC function with nested handlers is the hardest to split because each handler closes over `hass` and `entry`. The cleanest pragmatic solution:

```python
# services/handlers.py

def register_services(hass: HomeAssistant) -> None:
    """Register all EV Trip Planner services.

    This is a controlled ARN-001 deviation (688 LOC). Each inner handler
    delegates to the appropriate TripServiceHandler method.
    """

    async def handle_add_recurring(call: ServiceCall) -> None:
        vehicle_id = call.data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await mgr.async_add_recurring_trip(
            dia_semana=call.data["dia_semana"],
            hora=call.data["hora"],
            km=float(call.data["km"]),
            kwh=float(call.data["kwh"]),
            descripcion=str(call.data.get("descripcion", "")),
        )
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            await coordinator.async_refresh_trips()

    # ... all handlers remain as inner functions (they close over hass/entry)

    # Registration calls
    hass.services.async_register(DOMAIN, "add_recurring_trip", handle_add_recurring, schema=...)
    # ...
```

**The real value add** for `services/` isn't splitting `register_services` — it's moving the **helper functions** (`_find_entry_by_vehicle`, `_get_manager`, `_ensure_setup`, `_get_coordinator`, `build_presence_config`, cleanup functions, dashboard helpers) into separate files.

```python
# services/__init__.py (thin — just the re-exports)
from .handlers import register_services
from .cleanup import (
    async_cleanup_stale_storage,
    async_cleanup_orphaned_emhass_sensors,
    async_unload_entry_cleanup,
    async_remove_entry_cleanup,
)
from .dashboard_helpers import (
    create_dashboard_input_helpers,
    async_register_panel_for_entry,
    async_register_static_paths,
    async_import_dashboard_for_entry,
)
```

**Anti-patterns to avoid:**
- **Transaction Script anti-pattern** — don't have each service handler contain the full workflow (get manager → mutate → refresh coordinator → update sensors). Instead, handlers should be thin, delegating to `TripManager` methods that already do sensor/coordinator updates (the coordinator already handles sensor updates internally).

### 13.4 `dashboard/` — Facade + Builder

**Primary pattern: Facade (at module level)**
**Secondary: Builder (for dashboard config construction)**

`dashboard.py` has a clear separation: (a) template loading/YAML manipulation, (b) dashboard import/validation, (c) exception types. The templates (11 YAML files) are static assets that should live in `templates/`.

**File structure:**
```
dashboard/
  __init__.py        # re-exports import_dashboard, is_lovelace_available, exception classes
  importer.py        # import_dashboard, DashboardImportResult, is_lovelace_available, exception classes
  template_manager.py  # _load_dashboard_template, _save_lovelace_dashboard, _save_dashboard_yaml_fallback,
                        # _validate_dashboard_config, _verify_storage_permissions, executor helpers
  templates/          # 11 YAML/JS template files (moved from dashboard/)
```

**Builder pattern for complex dashboard config construction:**

The `import_dashboard` function constructs a complex YAML structure from templates. A Builder pattern makes this explicit:

```python
# dashboard/importer.py

class DashboardBuilder:
    """Builds a complete Lovelace dashboard configuration from templates and trip data."""

    def __init__(self, vehicle_id: str, trips: Dict[str, Any], soc: float):
        self._vehicle_id = vehicle_id
        self._trips = trips
        self._soc = soc
        self._panels: list[dict] = []
        self._views: list[dict] = []

    def add_status_view(self) -> "DashboardBuilder":
        """Add the vehicle status view (SOC, range, charging)."""
        # ... builds the status panel configuration
        return self  # fluent interface

    def add_trip_list_view(self) -> "DashboardBuilder":
        """Add the trip list view."""
        return self

    def build(self) -> dict[str, Any]:
        """Return the complete dashboard configuration."""
        return {
            "title": f"EV Trip Planner - {self._vehicle_id}",
            "panels": self._panels,
            "views": self._views,
        }

async def import_dashboard(
    hass: HomeAssistant,
    vehicle_id: str,
    trips: Dict[str, Any],
    soc: float,
) -> DashboardImportResult:
    builder = (
        DashboardBuilder(vehicle_id, trips, soc)
        .add_status_view()
        .add_trip_list_view()
    )
    dashboard_config = builder.build()
    # ... save to Lovelace
    return DashboardImportResult(success=True, path=...)
```

**Anti-patterns to avoid:**
- **God Function (import_dashboard)** — the 286-LOC `import_dashboard` function does template loading, validation, YAML parsing, storage writing, and result construction. Split each concern.
- **Magic Path Strings** — don't hardcode `"dashboard/ev-trip-planner-full.yaml"` as string paths everywhere. Use a `TEMPLATES_DIR` constant.

### 13.5 `vehicle/` — Strategy (already partially in place)

**Primary pattern: Strategy (already in use — refactor to complete it)**
**Secondary: Factory**

`vehicle_controller.py` already uses the Strategy pattern correctly. The refactoring here is about **cleaning up the package boundaries** and completing the pattern:

**File structure:**
```
vehicle/
  __init__.py        # re-exports VehicleController, VehicleControlStrategy, create_control_strategy
  strategy.py        # VehicleControlStrategy (ABC), SwitchStrategy, ServiceStrategy, RetryState, HomeAssistantWrapper
  external.py        # ScriptStrategy, ExternalStrategy
  controller.py      # VehicleController class, create_control_strategy factory
```

The Strategy pattern is already working well. The key improvement:

```python
# vehicle/controller.py

class VehicleController:
    """Controls vehicle charging via pluggable strategies."""

    def __init__(self, hass: HomeAssistant, strategy: VehicleControlStrategy):
        self._hass = hass
        self._strategy = strategy  # Strategy injected, not chosen by if/elif
        self._retry_state = RetryState()

    async def async_activate_charging(self) -> bool:
        if not self._retry_state.should_retry():
            _LOGGER.error("Max retry attempts exceeded")
            return False
        result = await self._strategy.async_activate()
        if result:
            self._retry_state.reset()
        else:
            self._retry_state.add_attempt()
        return result

# vehicle/strategy.py (factory)

def create_control_strategy(
    strategy_type: str,
    hass: HomeAssistant,
    config: dict[str, Any],
) -> VehicleControlStrategy:
    """Factory — open for extension: add new strategy by adding a new class + this function."""
    wrappers = {
        "switch": SwitchStrategy,
        "service": ServiceStrategy,
        "script": ScriptStrategy,
        "external": ExternalStrategy,
    }
    strategy_class = wrappers.get(strategy_type)
    if strategy_class is None:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    return strategy_class(HomeAssistantWrapper(hass), config)
```

**What to improve (beyond what exists):**
- Extract `RetryState` and `HomeAssistantWrapper` into `strategy.py` (they belong with the strategies, not the controller)
- Keep `create_control_strategy` in `controller.py` (it's the factory)
- Add `Protocol`-based testing: define `VehicleControlStrategy` as a `Protocol` instead of an ABC if you want duck-typed strategies (optional, for testing)

**Anti-patterns to avoid:**
- **Strategy with type-switch instead of DI** — `create_control_strategy` uses a dict lookup (good). Don't revert to `if/elif/elif` in the controller.
- **Tight coupling to Strategy internals** — `VehicleController` should only call `async_activate()`/`async_deactivate()`/`async_get_status()`. Don't let it inspect strategy internals.

### 13.6 `calculations/` — Functional decomposition (pure functions)

**Primary pattern: Functional decomposition by domain**
**Secondary: Module-level namespace (no class wrapper needed)**

`calculations.py` is already the cleanest module — pure functions, no state, deterministic. The split is purely organizational by domain.

**File structure:**
```
calculations/
  __init__.py        # re-exports all 20 names (BatteryCapacity, calculate_*, etc.)
  core.py            # BatteryCapacity, calculate_dynamic_soc_limit, calculate_day_index,
                      # calculate_trip_time, calculate_charging_rate, calculate_soc_target, DEFAULT_T_BASE
  windows.py         # calculate_charging_window_pure, calculate_multi_trip_charging_windows (with ventana_horas fix),
                      # calculate_hours_deficit_propagation, calculate_soc_at_trip_starts
  power.py           # calculate_power_profile_from_trips, calculate_power_profile
  schedule.py        # generate_deferrable_schedule_from_trips, calculate_deferrable_parameters
  deficit.py         # calculate_deficit_propagation, calculate_next_recurring_datetime,
                      # determine_charging_need, ChargingDecision, calculate_energy_needed
  _helpers.py        # _ensure_aware (private helper used across modules)
```

**Code example — windows.py with the ventana_horas fix:**

```python
# calculations/windows.py

def calculate_multi_trip_charging_windows(
    trips: list[dict],
    battery_capacity_kwh: float,
    t_base: float,
    soc_post_trip: float,
) -> list[CargaVentana]:
    """Calculate charging windows for multiple trips.

    Bug fix [ARN-bug]: ventana_horas now uses trip_departure_time (not trip_arrival).
    Previously used trip_arrival which added 6h of "away" time, inflating the window.
    The charging window legitimately ends at trip_departure_time (when the vehicle leaves).
    """
    results: list[CargaVentana] = []
    for trip in trips:
        trip_departure = trip["departure_time"]
        window_start = _compute_window_start(trip, t_base)

        # FIX: use trip_departure, not trip_arrival (was + 6h)
        delta = trip_departure - window_start
        ventana_horas = max(0.0, delta.total_seconds() / 3600)

        results.append(CargaVentana(
            ventana_horas=ventana_horas,
            kwh_necesarios=trip.get("kwh", 0.0),
            horas_carga_necesarias=ventana_horas,
            inicio_ventana=window_start,
            fin_ventana=trip_departure,
            es_suficiente=ventana_horas >= 2.0,
        ))
    return results
```

**Anti-patterns to avoid:**
- **Class wrapper** — don't wrap pure functions in a `Calculations` class. Pure functions at module level are the Pythonic pattern (and this is how HA core's calculation helpers are organized).
- **Circular domain imports** — `windows.py` should not import from `schedule.py`. If a function in `windows.py` calls one in `schedule.py`, it means the functions should be co-located or extracted to `core.py`.

## 14. Pattern Decision Summary

| Package | Primary Pattern | Rationale | Pattern to Avoid |
|---------|----------------|-----------|-----------------|
| `emhass/` | **Facade + Composition** | 4 orthogonal concerns (index/publish/error/config) with different state lifecycles | God Facade (logic in facade), Service Locator |
| `trip/` | **Facade + Mixins** | All methods share `self.hass`/`self._trips`/`self._storage`; mixins preserve `self` semantics | Fragile Base Class (mixins must be independent), State Sharing Leak |
| `services/` | **Module Facade** | Not a class — module-level dispatcher mapping service IDs to handlers | Transaction Script (handlers should be thin) |
| `dashboard/` | **Facade + Builder** | Template assembly is a construction process; exception hierarchy already exists | God Function (import_dashboard) |
| `vehicle/` | **Strategy (complete it)** | Already partially implemented; extract sub-classes into files | Type-switch in controller (dict lookup is correct) |
| `calculations/` | **Functional decomposition** | Pure functions, no state, deterministic — classes add nothing | Class wrapper (anti-pattern for pure functions) |

## 15. HA Integration Patterns Used Here

This integration already follows several HA core patterns correctly:

1. **DataUpdateCoordinator** — `TripPlannerCoordinator` extends `DataUpdateCoordinator` (HA core pattern for sensor data)
2. **CoordinatorEntity** — `TripSensor` extends `CoordinatorEntity[TripPlannerCoordinator]` (HA core pattern)
3. **Platform forwarding** — `async_forward_entry_setups(entry, PLATFORMS)` in `__init__.py` (HA core pattern)
4. **ConfigEntry.runtime_data** — storing `EVTripRuntimeData` on `entry.runtime_data` (HA 2024+ recommended)
5. **Service registration** — `hass.services.async_register(DOMAIN, name, handler, schema=...)` (HA core pattern)
6. **from __future__ import annotations** — used in 9/17 files (HA 2024+ requirement for forward refs)

The patterns we're ADDING are all **Python design patterns** (Facade, Mixins, Strategy, Builder) that are independent of HA but complement HA's built-in patterns.

## 16. Anti-Pattern Catalog (what NOT to do)

| Anti-Pattern | How it manifests | How to detect |
|-------------|-----------------|---------------|
| **God Facade** | `EMHASSAdapter` methods contain business logic instead of delegating to sub-objects | Methods > 30 LOC in the facade class |
| **Leaky Abstraction** | Sub-objects expose internal dicts to callers (e.g., `adapter._index_map`) | Tests accessing `_`-prefixed attributes outside the package |
| **Fragile Base Class** | Mixin A calls methods of Mixin B, making inheritance order significant | Code reviews showing `_CRUDMixin` → `_SOCCalculatorMixin` calls |
| **Transaction Script** | Service handlers contain full workflow (get manager → mutate → refresh → update sensors) | Handlers > 20 LOC |
| **Type Switch** | `if strategy_type == "switch": ... elif ...` instead of strategy factory | AST check for `if/elif` chains with string comparison |
| **Shotgun Surgery** | A single logical change touches `trip/crud.py`, `trip/soc_calculator.py`, AND `emhass/load_publisher.py` | Code review flag; git blame showing co-modified lines |
| **Lazy Import Escape Hatch** | `from .sensor import X` inside methods to avoid cycles (7 occurrences) | `grep -n "from \.sensor import" trip_manager.py` |

## 17. DRY and KISS Principles — Beyond SOLID

SOLID is not enough. Two additional clean-code principles are equally critical for this refactor:

### 17.1 DRY — Don't Repeat Yourself

**Definition:** Every piece of knowledge must have a single, authoritative representation. Not "don't copy-paste code lines" — don't duplicate *logic*, *state*, or *rules*.

**Detection metrics:**

| Metric | What it measures | Tool/Method | Threshold |
|--------|-----------------|-------------|-----------|
| **Sliding-window code similarity** | Duplicate code blocks ≥ 5 consecutive lines across files | `simian` or `jscpd` | 0 duplications ≥ 5 lines |
| **Duplicate logic detection** | Same algorithm implemented differently in 2 places | AST-based AST-isomorphic matching (e.g., `croc` or manual review) | 0 |
| **Duplicate constant/value sets** | Same list of values hardcoded in 2 places (e.g., days of week, sensor names) | grep + manual | 0 |
| **Divergent implementation** | Same concept modified in 2 places without synchronization | Code review + git blame | 0 |

**Concrete DRY violations in current codebase:**

| Violation | Locations | Fix |
|-----------|-----------|-----|
| `validate_hora` logic duplicated in `trip_manager.py` and `utils.py` — `utils.py` has `pure_validate_hora` which is the *same function*. One should be the canonical version. | `trip_manager.py:900+` vs `utils.py` | Keep `pure_validate_hora` in `utils.py`; remove the internal copy from `trip_manager.py` and import |
| `is_trip_today` duplicated — `pure_is_trip_today` in `utils.py` + inline logic in `trip_manager.py` | `trip_manager.py` vs `utils.py` | Same as above: use the pure version |
| `calculate_day_index` duplicated — `pure` version in `utils.py` + internal in `trip_manager.py` | `trip_manager.py` vs `utils.py` | Same |
| `calcular_energia_kwh` called from both `trip_manager.py` and `calculations.py` | Two call sites | OK if they're *using* the same utility (not duplicating). Confirm signatures match. |
| Error message strings for HA services repeated across `services.py` handlers | `services.py` multiple handlers | Move to `const.py` constants |
| Dashboard template paths built in `dashboard.py` using `os.path.join(comp_dir, "dashboard", ...)` | `dashboard.py:679` | See GAP-1 (§20.1) |

**DRY for this spec:** Extract shared logic to the `utils/` package. The `utils.py` module is already the right home for pure functions. After split, move shared utils to `utils/` package with sub-modules if needed.

### 17.2 KISS — Keep It Simple, Stupid

**Definition:** Systems work best with simple (not simplistic) designs. Complexity should be introduced only when there's a demonstrable benefit.

**Detection metrics:**

| Metric | What it measures | Tool/Method | Threshold |
|--------|-----------------|-------------|-----------|
| **Cyclomatic complexity** | Number of independent paths through a function | `radon cc` (install: `pip install radon`) | ≤ 10 per function; ≤ 5 recommended |
| **Maximum nesting depth** | Deepest `if/for/while/with/try` nesting | `radon nc` or AST | ≤ 4 levels |
| **Method arity** | Number of parameters | AST | ≤ 5 (mandatory); ≤ 3 recommended |
| **Cognitive complexity** | How hard is the function to *understand* (not execute) | `radon hg` or `pylint --enable cognitive-complexity` | ≤ 15 per function |

**Concrete KISS violations in current codebase:**

| Violation | Location | Severity | Fix |
|-----------|----------|----------|-----|
| `register_services()` — 688 LOC, ~15 nesting levels | `services.py` | Critical | Split into handler class (services/trip_handlers.py) |
| `_populate_per_trip_cache_entry` — 266 LOC, complex branching | `emhass_adapter.py` | High | Extract to `_cache_entry_builder.py` |
| `calculate_multi_trip_charging_windows` — 118 LOC, deep nesting | `calculations.py:610-737` | Medium | Extract helper `_compute_window_start` (already partially done) |
| `async_generate_power_profile` — multiple nested `if` chains | `trip_manager.py` | Medium | Extract to `_schedule_gen.py` mixin |

**KISS for this spec:** The *splitting strategy itself* should be KISS. Each file in the new packages should be immediately understandable without tracing imports across 5 files. If a developer can't understand `trip/crud.py` in one reading, it's too complex.

### 17.3 How DRY and KISS integrate with SOLID

| Principle | Overlap | Distinction |
|-----------|---------|-------------|
| DRY + S (SRP) | DRY violations often indicate SRP violations (duplicated logic across classes = shared responsibility) | DRY = don't repeat *code/logic*. SRP = don't combine *responsibilities* |
| KISS + O (OCP) | OCP can add complexity (e.g., adding 3 new Strategy subclasses). KISS asks: "is a simpler approach possible?" | OCP = open for extension, closed for modification. KISS = simplest design that works |
| DRY + D (DIP) | DIP (depend on abstractions) is a DRY technique — define the abstraction once, depend on it everywhere | DRY = general principle. DIP = specific technique under DIP |

**Rule of thumb:** SOLID tells you *what* is wrong (which principle is violated). DRY/KISS tell you *how* to recognize it in code (concrete metrics). The 7 ARN rules from §6.6 now cover all 5 principles.

## 18. BMAD Consensus Party for SOLID Validation

### 18.1 What is the BMAD Consensus Party?

The Consensus Party is a multi-agent adversarial review process that replaces mechanical metric-checking with **semantic understanding** of whether SOLID principles are truly applied. Three specialized agents review each proposed split:

| Agent | Role | Expertise |
|-------|------|-----------|
| **Winston** (Architect) | Validates architectural soundness | Design patterns, package boundaries, dependency direction, facade/mixin correctness |
| **Murat** (Test Architect) | Validates testability and behavior preservation | Public API compatibility, test import paths, behavioral equivalence |
| **Adversarial Reviewer** | Finds flaws in the design | Seeks violations, looks for hidden coupling, identifies silent failures |

### 18.2 Consensus Party Workflow

For each of the 6 packages being split, the Consensus Party executes:

```
Phase 1: Winston (Architect)
  - Reviews proposed package structure
  - Validates pattern selection (Facade/Mixins/Strategy/Builder)
  - Checks: Are sub-objects truly orthogonal? Are mixins independent?
  - Checks: Does the facade expose only what's necessary?
  - Outputs: Architectural assessment (PASS/FAIL + issues)

Phase 2: Murat (Test Architect)
  - Reviews public API re-exports
  - Validates: Do all existing imports still resolve?
  - Checks: Are test fixtures compatible with new structure?
  - Checks: Are behavioral contracts preserved?
  - Outputs: Test compatibility assessment (PASS/FAIL + issues)

Phase 3: Adversarial Review
  - Actively searches for SOLID violations in the proposal
  - Tests: "What if I add a new EMHASS concern? Does the facade need changes?"
  - Tests: "What if TripManager needs a new state? Do mixins conflict?"
  - Tests: "Can I swap the strategy at runtime without changes?"
  - Outputs: Vulnerability report (list of potential failure modes)

Phase 4: Consensus Decision
  - If ALL three PASS → approved
  - If any FAIL → revision requested with specific feedback
  - If 2/3 PASS + Adversarial finds minor issues → approved with notes
```

### 18.3 Per-Package Consensus Focus

| Package | Winston Focus | Murat Focus | Adversarial Attack Vector |
|---------|--------------|-------------|--------------------------|
| `emhass/` (Facade+Composition) | Are IndexManager/LoadPublisher/ErrorHandler truly orthogonal? | Does `EMHASSAdapter` re-export all 27 public methods? | Can I break the facade by modifying IndexManager internals? |
| `trip/` (Facade+Mixins) | Are mixins independent (no cross-mixin calls)? | Does `TripManager` constructor signature stay compatible? | Diamond inheritance: does `_CRUDMixin.__init__` conflict with `_SOCCalculatorMixin.__init__`? |
| `services/` (Module Facade) | Is `register_services` a proper dispatcher or a God Function? | Do all service IDs register correctly? | What if `hass.services.async_register` is called twice with same ID? |
| `dashboard/` (Facade+Builder) | Is `DashboardBuilder` a fluent interface or a data structure? | Are imported template paths stable? | What if `__file__` changes after split? (GAP-1) |
| `vehicle/` (Strategy) | Are strategy interfaces stable ABCs? | Does `create_control_strategy` factory return compatible objects? | Can a strategy replace another at runtime without breaking `VehicleController`? |
| `calculations/` (Functional) | Are pure functions truly pure (no HA state leakage)? | Do function signatures match callers? | What if a "pure" function silently reads global state? |

### 18.4 Consensus Party Integration into Quality Gates

The Consensus Party is a **Tier B** quality gate (after Tier A deterministic checks):

| Gate | Level | What it checks | When |
|------|-------|---------------|------|
| Tier A | Deterministic, < 1 min | LOC, method count, import cycles, type hints (ARN-001 through ARN-007) | Every commit |
| Tier B | BMAD Consensus Party | Semantic SOLID validation, pattern correctness, adversarial stress tests | Per package, before merging each package split |

**Implementation:** The Consensus Party runs as part of the task execution pipeline. When a task completes a package split, the executor invokes the three agents sequentially. Results are logged to `chat.md` and gate the next task.

## 19. GAP Analysis — Independent Review Cross-Reference

This section cross-references an independent gap analysis (15 identified gaps) against our research. Each gap is marked as:
- **COVERED**: Already in our research
- **PARTIALLY**: Addressed in principle but missing detail
- **GAP**: Not covered — new finding

### 19.1 GAP-1: `__file__` path bug in dashboard — PRODUCTION BREAKING

**Status: GAP**

**The bug:** `dashboard.py:679` uses `os.path.dirname(__file__)` to compute template paths. When `dashboard.py` is split into `dashboard/__init__.py`, `__file__` changes from:

```
/mnt/.../custom_components/ev_trip_planner/dashboard.py
→ /mnt/.../custom_components/ev_trip_planner/dashboard/__init__.py
```

The path in `comp_dir` gains an extra `/dashboard` segment. Template lookup code that does:

```python
comp_dir = os.path.dirname(__file__)
possible_paths = [os.path.join(comp_dir, "dashboard", template_file)]
```

will look for `.../ev_trip_planner/dashboard/dashboard/my_template.yaml` (double-nested) instead of `.../ev_trip_planner/dashboard/templates/my_template.yaml`.

**Impact:** Silent failure — templates fail to load, dashboard import fails, but no exception is raised (YAML/JS files just "not found").

**Fix:** Move templates to `dashboard/templates/` AND change the path construction:

```python
# dashboard/__init__.py
comp_dir = os.path.dirname(__file__)
possible_paths = [
    os.path.join(comp_dir, "templates", template_file),  # "templates/" not "dashboard/"
]
```

**Mitigation for this spec:** Add a dedicated commit *before* the split that updates `dashboard.py` to use a resolved absolute path (e.g., `import pkg_resources; pkg_resources.resource_filename(__name__, "templates/...")`), then do the split in a subsequent commit. This is a **pre-condition** for the dashboard split, not optional.

### 19.2 GAP-2: Test import quantification and migration strategy

**Status: PARTIALLY COVERED**

Our research mentions "~80 test imports of private helpers" for dashboard and "24 test files import from emhass_adapter". The independent analysis quantifies **300+ total test imports** across all modules.

**New finding — 3-phase migration strategy:**

```
Phase 1: Skeleton + re-exports
  - Create new package with __init__.py that re-exports ALL public names
  - Private names: re-export from __init__.py with `# transitional` comment
  - All 300+ test imports continue to work without change
  - `make test` passes 100%

Phase 2: Update direct private imports
  - Tests that import `_load_dashboard_template` from dashboard.py
    → update to import from dashboard/template_manager.py
  - Tests that import private names from god modules
    → update to import from new sub-modules
  - `make test` still passes 100%

Phase 3: Cleanup re-exports
  - Remove `# transitional` re-exports from __init__.py
  - Only re-export public API going forward
```

**Action for design phase:** Add this 3-phase migration as a formal process constraint (similar to §10 Process Constraints).

### 19.3 GAP-3: `__init__` constructor signature preservation

**Status: GAP**

**The constraint:** When splitting `TripManager` or `EMHASSAdapter`, the **constructor signature must remain identical** because HA's `setup_entry()` calls `TripManager(hass, vehicle_id, entry_id, presence_config, storage, emhass_adapter)` from `__init__.py`.

For TripManager with mixins, this means:

```python
# BEFORE split — one class
class TripManager:
    def __init__(self, hass, vehicle_id, entry_id, presence_config, storage, emhass_adapter=None):
        ...

# AFTER split — facade + mixins, SAME SIGNATURE
class TripManager(_CRUDMixin, _SOCCalculatorMixin, _PowerProfileMixin, _ScheduleGenMixin):
    def __init__(self, hass, vehicle_id, entry_id, presence_config, storage, emhass_adapter=None):
        # Set shared state FIRST (before calling mixin __init__)
        self.hass = hass
        self.vehicle_id = vehicle_id
        self._entry_id = entry_id
        self._presence_config = presence_config
        self._storage = storage
        self._emhass_adapter = emhass_adapter
        self._trips = {"recurring": {}, "punctual": {}}
        # Then initialize each mixin with only the state it needs
        _CRUDMixin.__init__(self, self._storage)
        _SOCCalculatorMixin.__init__(self, self.hass, lambda: self._get_charging_power())
        ...
```

**Critical detail:** The shared state (`self.hass`, `self._trips`, etc.) is set on `self` **before** calling mixin `__init__`. This is the standard Python pattern for mixins that need shared state.

**Action for design phase:** Document this constraint explicitly. If the constructor signature changes, ALL callers (in `__init__.py`, `coordinator.py`, `services.py`, `config_flow.py`) must update. This is a guaranteed breaking change.

### 19.4 GAP-4: Test naming convention

**Status: GAP (low priority for this spec)**

The independent analysis found that tests use the pattern `<module>_<scenario>.py`. After split, test files for sub-modules should follow `<package>_<submodule>_<scenario>.py` (e.g., `trip_crud_add_recurring.py`).

**Action:** Defer to design phase — this is a cosmetic convention, not a technical risk.

### 19.5 GAP-5: `__all__` declarations for PEP 8 compliance

**Status: GAP**

**The finding:** `calculations.py` is the only module with `__all__`. After split, each `__init__.py` should declare `__all__` listing all re-exported names:

```python
# trip/__init__.py
__all__ = [
    "TripManager",
    # ... all public names
]
```

**Why it matters:** `from custom_components.ev_trip_planner.trip import *` (if used anywhere) requires `__all__`. Even if not used, `__all__` documents the public API and tools like `pyright` use it for import resolution.

**Action:** Require `__all__` on every new `__init__.py`. This is a one-line addition per file.

### 19.6 GAP-6: Mutmut config transition

**Status: PARTIALLY COVERED**

Our §7 Risk #2 mentions mutmut config update. The independent analysis adds detail: `paths_to_mutate = ["custom_components/ev_trip_planner"]` is already package-level and will auto-include sub-packages. The **only** change needed is the per-module quality-gate entries in `pyproject.toml`.

**No new action** beyond what's already in our §7 Risk #2.

### 19.7 GAP-7: Coverage reporting after split

**Status: GAP**

**The finding:** When files move from single-file modules to sub-packages, coverage report paths change:

```
# Before:
custom_components/ev_trip_planner/dashboard.py               1285     21    98%

# After:
custom_components/ev_trip_planner/dashboard/__init__.py       150      5    97%
custom_components/ev_trip_planner/dashboard/template_manager.py  450     10    98%
custom_components/ev_trip_planner/dashboard/importer.py       300      5    98%
```

The total coverage percentage may shift slightly due to new `__init__.py` files (they have import-only LOC that are always "covered" by a single import). This is cosmetic but may affect CI thresholds.

**Action for design phase:** Add a verification step in §10 Process Constraints: "After each package split, run `make test-cover` and verify total coverage doesn't drop below existing threshold."

### 19.8 GAP-8: Mixin `__init__` chain with MRO resolution

**Status: GAP**

**The detail:** When TripManager inherits from 4 mixins, Python's MRO (Method Resolution Order) determines which `__init__` runs first. The correct pattern:

```python
# MRO for TripManager(_CRUDMixin, _SOCCalculatorMixin, _PowerProfileMixin, _ScheduleGenMixin):
# TripManager → _CRUDMixin → _SOCCalculatorMixin → _PowerProfileMixin → _ScheduleGenMixin → object

# Each mixin's __init__ should NOT call super().__init__() unless using cooperative multiple inheritance.
# Since this is the "pragmatic" pattern (not cooperative), each mixin.__init__ is called explicitly
# from TripManager.__init__ as shown in §13.2.

# The shared state (self.hass, self._trips) must be set BEFORE any mixin.__init__() call,
# because mixins may access self.hass in their __init__.
```

**Critical:** If any mixin uses `super().__init__()` AND the next class in MRO also uses `super().__init__()`, you get cooperative multiple inheritance — which requires ALL classes to use it consistently. This is complex and error-prone. **Recommendation: use explicit calls** (as shown in §13.2) rather than `super()` chains.

**Action for design phase:** Add a note in the design doc about `super()` vs explicit mixin `__init__` calls. Explicit calls are safer for this refactor.

### 19.9 GAP-9: Dispatcher scope creep — Spec 4 contradiction

**Status: COVERED**

Our §5.5.2 (§11.3 in the research) already defers the `trip → sensor` circular dependency to Spec 4. The independent analysis confirms this is the right call — but flags a contradiction: **this spec promises to "eliminate circular imports" in the epic.md requirements, but the clean fix requires Spec 4 scope.**

**Resolution:** The spec should state explicitly: "This spec eliminates module-load cycles via TYPE_CHECKING (already done) and configures lint-imports contracts. The `from .sensor import` lazy imports in trip_manager.py are deferred to Spec 4 as a semantic re-architecture (dispatcher pattern). This does NOT violate ARN-005 (zero import cycles) because lazy imports don't create module-load cycles."

### 19.10 GAP-10: Exception narrowing

**Status: GAP**

**The finding:** `dashboard.py` uses bare `except Exception` in `import_dashboard()`. After split into `DashboardBuilder`, exceptions should be narrowed:

```python
# Before:
except Exception as e:
    return DashboardImportResult(success=False, error=str(e))

# After:
except (FileNotFoundError, yaml.YAMLError, json.JSONDecodeError) as e:
    return DashboardImportResult(success=False, error=str(e))
except Exception as e:
    _logger.exception("Unexpected error importing dashboard: %s", e)
    return DashboardImportResult(success=False, error=f"Unexpected: {e}")
```

**Action:** Add to design phase — this is a code quality improvement, not a blocking risk.

### 19.11 GAP-11: Pyright re-export warnings

**Status: GAP**

**The finding:** Pyright warns about names imported and re-exported from sub-modules without explicit type annotations:

```python
# pyright may warn: "Re-export" without explicit type
from .crud import TripManager  # pyright: "TripManager" is not defined

# Fix:
from .crud import TripManager as TripManager  # explicit alias
# OR:
from .crud import TripManager  # with pyright config: "reportUnnecessaryTypeImport" = false
```

**Action:** Add pyright configuration for re-exports to `pyproject.toml` or use explicit aliases. Check before PR.

### 19.12 GAP-12: E2E test impact

**Status: GAP**

**The finding:** E2E tests navigate the HA UI (not import code), so they test the *observable behavior* of the integration. After the refactor:

- E2E tests should continue to pass IF the public API behaves identically
- However, if the split changes import order (e.g., `vehicle/` loaded before `trip/`), timing-sensitive behavior could change
- **Action:** Run `make e2e` and `make e2e-soc` after EACH package split, not just at the end

**Action for process constraints:** Add "After each package split: `make e2e` pass required" to §10 Process Constraints.

### 19.13 GAP-13: Pylint R09xx rules still disabled

**Status: GAP**

**The finding:** Pylint's `R09xx` rules (design metrics: too many arguments, too many branches, too many local variables, too many statements) are disabled in `pyproject.toml`. These directly measure KISS violations (complexity). After installing `radon`, consider:

```toml
# pyproject.toml
[tool.pylint."messages control"]
disable = [
    # ... existing disables ...
    # R0901 (inheritance), R0903 (too few methods), R0904 (too many),
    # R0911 (too many return statements), R0912 (too many branches) = R09xx
]
```

These are already acknowledged as disabled. The `radon` installation (§6.7) is a better replacement for R09xx.

**Action:** In design phase, confirm that `radon` coverage subsumes the R09xx rules before re-enabling pylint.

### 19.14 GAP-14: ISP not implemented in `solid_metrics.py`

**Status: COVERED**

Our §6.4 (ISP detection) already documents that ISP is currently a stub (`PASS`). The independent analysis confirms: `solid_metrics.py` has no ISP implementation. After implementing the ARN rules (§6.6), ISP detection should be added to `solid_metrics.py` as part of the same PR.

**Action:** Add to implementation: "Implement ISP detection in solid_metrics.py — check for unused public methods and interface size."

### 19.15 GAP-15: `radon` not installed

**Status: COVERED**

Our §6.7 explicitly notes `radon` is NOT installed and recommends `pip install radon`. The independent analysis confirms this.

**Action:** Pre-requisite before implementation: `pip install radon` in the `.venv`.

### 19.16 GAP Analysis Summary

| # | Gap | Status | Action Item |
|---|-----|--------|-------------|
| 1 | `__file__` path bug | **GAP** | Pre-condition for dashboard split — add commit instruction |
| 2 | Test import migration | **PARTIALLY** | Add 3-phase migration to process constraints |
| 3 | `__init__` signature | **GAP** | Document constructor signature constraint in design |
| 4 | Test naming convention | **GAP** | Low priority, defer to design |
| 5 | `__all__` declarations | **GAP** | Require on every new `__init__.py` |
| 6 | Mutmut config | **COVERED** | No new action |
| 7 | Coverage reporting | **GAP** | Add verification step in §10 |
| 8 | Mixin `__init__` MRO | **GAP** | Document explicit vs super() pattern in design |
| 9 | Dispatcher scope | **COVERED** | Add clarification to §11.3 |
| 10 | Exception narrowing | **GAP** | Design phase improvement |
| 11 | Pyright re-export | **GAP** | Add to pre-PR checklist |
| 12 | E2E test impact | **GAP** | Add E2E verification after each split to §10 |
| 13 | Pylint R09xx | **GAP** | Confirm radon subsumes R09xx in design phase |
| 14 | ISP in solid_metrics | **COVERED** | Add to implementation tasks |
| 15 | radon not installed | **COVERED** | Pre-requisite for implementation |

**Total new action items from gap analysis: 9** (gaps 1, 3, 4, 5, 7, 8, 10, 11, 12, 13)

## 20. Sources

- [`specs/_epics/tech-debt-cleanup/epic.md`](../_epics/tech-debt-cleanup/epic.md) §4 "Spec 3"
- [`ROADMAP.md`](../../ROADMAP.md):218-221 (`ventana_horas` bug)
- [`specs/solid-refactor-coverage/design.md`](../solid-refactor-coverage/design.md), [`specs/solid-refactor-coverage/tasks.md`](../solid-refactor-coverage/tasks.md)
- [`pyproject.toml`](../../pyproject.toml) — `[tool.import-linter]`, `[tool.mutmut]`, `[tool.quality-gate.mutation.modules.*]`, `[tool.coverage.run]`, `[tool.pytest.ini_options]`
- [`Makefile`](../../Makefile) — verified targets
- [`custom_components/ev_trip_planner/__init__.py`](../../custom_components/ev_trip_planner/__init__.py) — entry-point imports
- [`services.yaml`](../../custom_components/ev_trip_planner/services.yaml) — service IDs frozen
- HA integration package layout reference: HA core uses sub-package re-export pattern in many integrations (e.g., `homeassistant/components/<domain>/__init__.py` re-exports core symbols; sub-modules: `sensor.py`, `binary_sensor.py`, `config_flow.py`). Pattern is well-supported by HA's loader; verified via the existing `sensor.py`/`config_flow.py` files in this integration.
- Python community pattern for splitting god classes while preserving public API: package + `__init__.py` re-exports is the canonical approach (PEP 8 §"Public and internal interfaces"; Fluent Python ch.21; HA dev docs).
- [Design Patterns (Gamma et al.) — Facade, Strategy, Builder patterns](https://refactoring.guru/design-patterns)
- [Fluent Python (2nd ed.) — Luciano Ramalho, ch.21 "Classes in Python" (composition vs mixins)](https://www.oreilly.com/library/view/fluent-python-2nd/9781492056348/)
- [HA Core: DataUpdateCoordinator pattern](https://developers.home-assistant.io/docs/api_lib_index/#data-update-coordinator)
- [HA Core: Platform entities with CoordinatorEntity](https://developers.home-assistant.io/docs/coordinator_index/#coordinatorentity)
- [Python SOLID — Real Python](https://realpython.com/python-solid-principles/)
