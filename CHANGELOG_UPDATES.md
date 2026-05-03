# Updates to CHANGELOG.md - April 26, 2026

## [0.5.21] - 2026-04-26 - EMHASS Per-Trip Sensors & Hotfixes (Spec M401 COMPLETED)

### Added
- **TripEmhassSensor**: Per-trip EMHASS sensors with 9 documented attributes
  - Individual `def_total_hours`, `P_deferrable_nom` per trip
  - `def_start_timestep`, `def_end_timestep` per trip
  - `power_profile_watts` per trip (168h matrix)
  - `deadline` (ISO 8601), `soc_target` per trip
  - `vehicle_id`, `trip_id`, `emhass_index` attributes
  - Device grouping under vehicle (not per-trip device)
  - Lifecycle tied to trip (create/delete with trip)
- **EMHASS aggregated sensor enhanced**: `p_deferrable_matrix` attribute
  - Complete P_deferrable matrix for all trips in JSON format
  - `number_of_deferrable_loads` attribute (trip count)
  - Array attributes: `def_total_hours_array`, `p_deferrable_nom_array`, `def_start_timestep_array`, `def_end_timestep_array`
  - Automatic template generation via `| tojson` for EMHASS
- **Charging power update from options**: Fixed Gap #5
  - `entry.options.get("charging_power_kw")` now works correctly
  - `setup_config_entry_listener()` activated in `__init__.py`
  - Profile updates propagate immediately on options change
- **Hours deficit propagation algorithm**: `calculate_hours_deficit_propagation()`
  - Backward propagation across trips when trip #3 has deficit
  - Missing hours propagate to trip #2, then trip #1 (if spare capacity exists)
  - Metadata tracking: `deficit_hours_propagated`, `deficit_hours_to_propagate`, `adjusted_def_total_hours`
  - Integrated in `emhass_adapter.py` per-trip cache
- **82 TDD tasks completed**: Full Red-Green-Refactor cycles
  - Phase 1: Gap #5 fixes (8 tasks) - all passing
  - Phase 2: Per-trip cache (14 tasks) - all passing
  - Phase 3: TripEmhassSensor (8 tasks) - all passing
  - Phase 4: Sensor CRUD (8 tasks) - all passing
  - Phase 5: Aggregated sensor (8 tasks) - all passing
  - Phase 6: TripManager refactor (11 tasks) - all passing
  - Phases 7-8: Frontend/docs/quality (19 tasks) - all passing

### Fixed
- **7 EMHASS integration bugs** (fix-emhass-aggregated-sensor spec)
  - `datetime.now()` → `datetime.now(timezone.utc)` in 5 critical locations
  - `math.ceil()` for `def_total_hours` (prevents truncation)
  - Panel entity ID: `includes('emhass_perfil_diferible_')` instead of `startsWith()`
  - Template keys: removed `_array` suffix (EMHASS API expects singular keys)
  - CSS path: hyphens instead of underscores
  - Warning message clarity: EMHASS status always visible
  - Modal trip type: 3-field fallback (`tipo`, `type`, `recurring`)
- **Gap #8 architecture**: EMHASS now receives per-trip profiles
  - Old aggregated sensor maintained (useful for weekly charts)
  - New per-trip sensors provide individual optimization
  - Automatic Jinja2 template: `P_deferrable: {{ todas_las_cargas_aplazables_concatenadas_en_json }}`
  - No manual EMHASS reconfiguration needed when trips change

### Technical Details
- **New Files**:
  - `tests/test_trip_emhass_sensor.py` - Per-trip sensor tests (8 tests)
  - `tests/test_propagate_charge_deficit.py` - Deficit propagation tests
- **Modified Files**:
  - `sensor.py` - TripEmhassSensor class (9 attributes, device_info)
  - `sensor.py` - Enhanced EmhassDeferrableLoadSensor (p_deferrable_matrix)
  - `emhass_adapter.py` - Per-trip cache, Gap #5 fixes, deficit propagation
  - `trip_manager.py` - Sensor CRUD integration, entry_id parameter
  - `__init__.py` - setup_config_entry_listener() activated
  - `frontend/panel.js` - EMHASS config section with copy button
  - `docs/emhass-setup.md` - Complete configuration guide with templates
- **Test Coverage**: 1470 tests passing, 100% coverage on new code
- **Quality**: Mypy clean (19 source files, 0 errors)
- **PR**: #26 merged (M401-emhass-per-trip-sensors branch)

### Breaking Changes
- None - fully backward compatible
- Old aggregated sensor maintains same entity_id and attributes
- New per-trip sensors use new entity_id pattern: `sensor.ev_trip_planner_{vehicle_id}_emhass_trip_{trip_id}`

### Documentation
- EMHASS setup guide with Jinja2 templates for `optimize.yaml`
- Panel shows ready-to-copy YAML/Jinja2 configuration
- Complete attribute documentation for TripEmhassSensor

---

## [0.5.20] - 2026-04-23 - Datetime Fix & Sequential Charging (Specs Completed)

### Added
- **Sequential trip charging algorithm**: Fixed multi-trip charging windows
  - Correctly handles Trip 1 → Trip 2 → Trip 3 charging sequence
  - Fixed watt calculation for trip #2 and beyond
  - Safety margin percent properly applied from config
- **Datetime regression test suite**: `test_trip_manager_datetime_tz.py`
  - 24 `datetime.now(timezone.utc)` occurrences verified
  - 100% coverage on critical datetime handling
- **Dynamic E2E EMHASS tests**: Entity ID discovery in Shadow DOM
  - `test-panel-emhass-sensor.spec.ts` with dynamic dates
  - `getFutureIs()` helper for future date testing

### Fixed
- **Datetime naive/aware bug**: All `datetime.now()` → `datetime.now(timezone.utc)`
  - Prevents `TypeError` in timezone comparisons
  - Fixed in trip_manager.py, emhass_adapter.py (5 locations)
- **Coordinator race condition**: Concurrent updates during coordinator refresh
- **SOC calculation in sensor deletion**: Orphaned sensor cleanup
- **In-place mutation**: Dict expansion in `async_publish_all_deferrable_loads`
- **Blank panel issue**: Added `disconnectedCallback()` lifecycle method
- **EMHASS publishing after restart**: `publish_deferrable_loads` on setup
- **Trip 2 power profile**: Corrected watt calculation
- **EMHASS cache cleanup**: Cleared on trip deletion
- **vehicle_id/entry_id matching**: Fixed sensor cleanup

### Technical Details
- **Tests**: 1441 passing, 100% coverage on datetime code
- **E2E**: 10 Playwright specs passing
- **CI**: All GitHub Actions checks green (CodeRabbit, tests)

---

## [0.5.19] - 2026-04-20 - SOLID Refactoring & Test Infrastructure

### Added
- **SOLID architecture components**:
  - `protocols.py` - Formal interfaces for dependency decoupling
  - `definitions.py` - Centralized entity descriptions
  - `diagnostics.py` - HACS quality diagnostic support
- **Refactored coordinator**: Dependency injection pattern
- **Enhanced test infrastructure**:
  - `test_integration_uninstall.py` - Integration deletion tests
  - `test_post_restart_persistence.py` - HA restart survival tests
  - `test_emhass_adapter.py` - Adapter unit tests
  - `zzz-integration-deletion-cleanup.spec.ts` - E2E cleanup tests

### Fixed
- **Orphaned sensors**: Entity registry cleanup on vehicle deletion
- **Panel cross-contamination**: `entry_id` filtering prevents data mixing
- **Config entry update listeners**: Reactive charging power updates
- **Time validation**: Strict check for invalid time formats (e.g., "16:400")

### Technical Details
- **Test Coverage**: 85%+ (SOLID refactor goal achieved)
- **Total Tests**: 793 Python + 10 E2E (Playwright)
- **All Tests Passing**: 100% pass rate
