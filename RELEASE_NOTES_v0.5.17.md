# Release Notes v0.5.17 — Datetime Fix & Race Condition Resolution

## Summary

This version fixes a critical timezone bug in TripManager datetime calculations, resolves race conditions in the coordinator, and improves E2E test infrastructure for EMHASS sensors.

## Highlighted Changes

### Fixed
- **Naive/Aware datetime bug**: Fixed `datetime.now()` to `datetime.now(timezone.utc)` in [`trip_manager.py`](custom_components/ev_trip_planner/trip_manager.py:1470-1471) to prevent `TypeError` errors in timezone comparisons.
- **Coordinator race condition**: Resolved race condition in the coordinator that could cause inconsistent states during concurrent updates.
- **SOC calculation in sensor deletion**: Fixed SOC calculation when deleting orphaned sensors.
- **In-place mutation**: Replaced in-place mutation with dict expansion in `async_publish_all_deferrable_loads` and `async_cleanup_vehicle_indices`.

### Added
- **Datetime regression tests**: New [`tests/test_trip_manager_datetime_tz.py`](tests/test_trip_manager_datetime_tz.py) file with naive/aware datetime regression tests.
- **Refactored `_parse_trip_datetime`**: Centralized method for datetime parsing in TripManager with type hints for SOLID compliance.
- **Dynamic E2E EMHASS tests**: E2E tests with dynamic entity ID discovery instead of hardcoded values.
- **100% coverage**: 100% coverage on critical datetime handling lines.

### Changed
- **Test infrastructure**: Improved E2E tests with dynamic dates using `getFutureIs` instead of hardcoded dates.
- **Chore files cleanup**: Removed obsolete presentation files (Saga, Freya) and unused skills.

## Technical Details

### Modified Files
- `custom_components/ev_trip_planner/trip_manager.py` - Datetime handling and refactoring
- `custom_components/ev_trip_planner/coordinator.py` - Race condition fixes
- `custom_components/ev_trip_planner/emhass_adapter.py` - In-place mutation fix
- `custom_components/ev_trip_planner/__init__.py` - Cleanup imports
- `tests/test_trip_manager_datetime_tz.py` - New regression test file
- `tests/e2e/emhass-sensor-updates.spec.ts` - Dynamic E2E tests
- `_bmad/` - Removed obsolete agent files

### Files Removed
- `_bmad/cis/agents/artifact-analyzer.md`
- `_bmad/cis/agents/opportunity-reviewer.md`
- `_bmad/cis/agents/skeptic-reviewer.md`
- `_bmad/cis/agents/web-researcher.md`
- `_bmad/core/agents/distillate-compressor.md`
- `_bmad/core/agents/round-trip-reconstructor.md`
- `_bmad/bmb/agents/tech-writer-sidecar/documentation-standards.md`
- `docs/e2e-date-diagnosis-final.md`

## Migration Notes

- No known breaking changes
- Existing users can update without additional actions
- Recommended to restart Home Assistant after updating to ensure consistent coordinator state

## References

- Commit: `df4f68d Fix sensor deletion calculating soc & fix: datetime bug, coordinator race condition, test infrastructure (#34)`
- Specifications: `specs/e2e-ux-tests-fix/`
