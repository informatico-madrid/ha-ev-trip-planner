# Release Notes v0.5.16 — Panel Fixes & EMHASS Cleanup

## Summary

This version fixes critical panel issues causing blank screens when switching tabs, improves EMHASS data publishing after Home Assistant restarts, and adds automatic cleanup of orphaned sensors during integration removal.

## Highlighted Changes

### Fixed
- **Blank panel**: Added missing `disconnectedCallback()` to prevent blank screens when switching Lovelace panel tabs.
- **EMHASS publishing after restart**: Ensured `publish_deferrable_loads` is called after EMHASS adapter setup to keep data updated after restarts.
- **Trip 2 power profile**: Fixed the second trip's watt calculation which was returning incorrect values.
- **Safety margin percent**: Correctly applying safety margin from vehicle configuration to energy calculations.
- **Sequential charging windows**: Fixed charging window logic for multiple sequential trips.
- **EMHASS cache cleanup**: Cleared cached EMHASS data when deleting trips to prevent stale state.
- **vehicle_id/entry_id matching**: Fixed the relationship handling between vehicle_id and entry_id in sensor cleanup.

### Added
- **Centralized vehicle_id normalization**: Improved centralization of vehicle_id normalization and updated TripManager to use YamlTripStorage.
- **Integration tests for cleanup**: New tests to verify correct behavior during integration and trip removal.
- **Post-restart persistence tests**: Tests to ensure data persists correctly after HA restarts.
- **E2E rules for Shadow DOM**: Documentation for E2E selectors in the Shadow DOM panel.

## Technical Details

### Modified Files
- `custom_components/ev_trip_planner/__init__.py` - EMHASS adapter setup and cleanup
- `custom_components/ev_trip_planner/coordinator.py` - Coordinator refresh
- `custom_components/ev_trip_planner/emhass_adapter.py` - Per-trip cache and cleanup
- `custom_components/ev_trip_planner/frontend/panel.js` - Panel lifecycle
- `custom_components/ev_trip_planner/sensor.py` - Additional sensors
- `custom_components/ev_trip_planner/services.py` - Service APIs
- `custom_components/ev_trip_planner/trip_manager.py` - Trip management
- `custom_components/ev_trip_planner/utils.py` - Normalization utilities

### Tests Added
- `tests/test_integration_uninstall.py` - Uninstallation tests
- `tests/test_post_restart_persistence.py` - Post-restart persistence
- `tests/test_emhass_adapter.py` - EMHASS adapter tests
- `tests/test_trip_manager_core.py` - TripManager core tests
- `tests/e2e/zzz-integration-deletion-cleanup.spec.ts` - E2E cleanup tests

## Migration Notes

- No known breaking changes
- Existing users can update without additional actions
- Recommended to clean up orphaned EMHASS sensors after updating if any exist

## References

- Commit: `7532e42 Fix panel in blank (#32)`
- Related specifications: `specs/e2e-trip-crud/`, `plans/bmad-migration-plan-phase3.md`
