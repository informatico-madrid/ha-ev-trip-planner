# Pyright Baseline - Tooling Foundation Spec

**Date**: 2026-05-08
**Spec**: tooling-foundation
**Purpose**: Document pre-existing type errors for future remediation

## Summary

After installing pyright and configuring `exclude = ["**/tests/**"]`, the production code has:
- **1 error**
- **237 warnings**

## Error Details

1. `custom_components/ev_trip_planner/yaml_trip_storage.py:65:38` - Argument type partially unknown
   - Function: `async_save` parameter `data`
   - Issue: `dict[str, Unknown]` type inference
   - Severity: Medium - type annotation needed

## Warning Categories

- `reportUnknownVariableType`: ~150 warnings
- `reportUnknownMemberType`: ~50 warnings
- `reportUnknownArgumentType`: ~30 warnings
- `reportAttributeAccessIssue`: ~7 warnings

## Files with Most Warnings

1. `vehicle_controller.py` - Unknown types in retry logic
2. `yaml_trip_storage.py` - Dict type inference issues
3. `emhass_adapter.py` - Home Assistant API type stubs missing

## Recommendations for Future Spec

1. Add type hints to `yaml_trip_storage.py` save/load functions
2. Add HA type stubs to `dev-dependencies` (homeassistant-stubs package)
3. Consider `pyright-mode: strict` for new code only
4. Focus on critical paths first (config_flow.py, coordinator.py)

## Out of Scope for Tooling Foundation

Per spec requirements, fixing these type errors is **separate work**. The tooling is verified working correctly.
