# Release Notes v0.5.9 — EMHASS Hotfixes & Per-Trip Cache

## Summary

- Critical hotfixes for EMHASS integration that fixed issues where charging power changes were being ignored.
- Added per-trip EMHASS params cache and new APIs/sensors to expose trip-specific data.
- Various helpers and safeguards added (`entry.options` read before `entry.data`, guards when `_published_trips` is empty, robust SOC/return time handling).

## Highlighted Changes

- **Fix**: Read `charging_power_kw` from `entry.options` first; use `is None` to not treat `0` as falsy.
- **Fix**: Register config entry listener during `async_setup_entry` to ensure power updates.
- **Fix**: Reload trips when `_published_trips` is empty before publishing to EMHASS.
- **Feature**: Per-trip cache (`per_trip_emhass_params`) with precalculated parameters (hours, powers, power profiles, start/end timestep, kWh needed, deadline, emhass_index).
- **Feature**: New `TripEmhassSensor` sensor to expose 9 attributes per trip and CRUD functions (`async_create_trip_emhass_sensor` / `async_remove_trip_emhass_sensor`).
- **Fix**: `async_publish_deferrable_load` now calculates `def_start_timestep` from charging windows instead of using fixed `0`.

## Tests & Quality

- TDD tests added for each hotfix and feature (tests in `tests/` related to `emhass_adapter` and `TripEmhassSensor`).
- Local verifications: relevant tests executed; ruff/mypy applied to modified modules per spec.

## Notes for Integrators

- No known breaking changes for end users; configure `charging_power_kw` as before, but the option in the entry (`options`) now takes priority.
- Per-trip sensors (`TripEmhassSensor`) are only created when the creation API is invoked or when the manager creates sensors in the trip lifecycle.

## References

- Specification: `specs/m401-emhass-hotfixes`
- Associated main commit: `feat/m401-emhass-per-trip-sensors` branch
