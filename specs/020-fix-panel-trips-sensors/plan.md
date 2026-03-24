# Plan: Fix EV Trip Planner Panel - Trips and Sensors

## Goal
Fix the EV Trip Planner native panel so that:
1. Sensors display actual values instead of 0.0%
2. Trips load correctly instead of showing "Cargando viajes..."
3. Add trip button works and opens modal
4. Panel renders correctly with proper CSS

## Context
The panel was created in spec 017 (native-panel-core) and extended in 018-019 for CRUD functionality, but it's not working in production. The issues are:
- CSS 404 error (path mismatch between panel.js and __init__.py)
- Sensors showing 0.0% (likely unavailable/unknown state filtering)
- Trips stuck in loading state (service call or vehicle ID extraction issue)
- Add trip button not working (event binding issue)

## Approach
1. Debug vehicle ID extraction from URL
2. Add logging to trip_list service call response
3. Verify sensor value formatting handles unavailable states correctly
4. Test add trip modal event binding
5. Compare with working dashboard code for patterns

## Files to Modify
- `custom_components/ev_trip_planner/frontend/panel.js` - Debug and fix
- `custom_components/ev_trip_planner/__init__.py` - Verify CSS path registration

## Acceptance Criteria
- [ ] Panel loads without CSS 404 errors
- [ ] Sensors show actual values (not 0.0%)
- [ ] Trips load and display correctly
- [ ] Add trip button opens modal
- [ ] Trip creation works end-to-end
