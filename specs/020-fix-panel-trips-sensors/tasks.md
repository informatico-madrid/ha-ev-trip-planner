# Tasks: EV Trip Planner Panel Fixes

## Task 1: Fix Vehicle ID Extraction

**Description**: Fix vehicle ID extraction to handle all URL formats including `/panel/ev-trip-planner-{vehicle_id}`

**Files**:
- `custom_components/ev_trip_planner/frontend/panel.js` (lines 67-102)

**Steps**:
1. Read current vehicle ID extraction code
2. Add support for `/panel/` prefix in URL
3. Add more flexible pattern matching
4. Test with actual HA panel URLs

**Acceptance Criteria**:
- [ ] Vehicle ID extracted from `/ev-trip-planner-{vehicle_id}`
- [ ] Vehicle ID extracted from `/panel/ev-trip-planner-{vehicle_id}`
- [ ] Vehicle ID extracted from `/panel/ev-trip-planner-{vehicle_id}/`
- [ ] Console logs show correct extraction

**Related**: research.md Section 1, design.md Phase 1

---

## Task 2: Fix Trip List Service Call

**Description**: Fix trip list service call response handling to handle all possible response formats

**Files**:
- `custom_components/ev_trip_planner/frontend/panel.js` (lines 397-458)

**Steps**:
1. Read current service call response handling
2. Add robust handling for array, object, and direct response formats
3. Validate response structure (recurring_trips, punctual_trips are arrays)
4. Add error handling for malformed responses

**Acceptance Criteria**:
- [ ] Service call succeeds with valid vehicle_id
- [ ] Response format validated and normalized
- [ ] Trips retrieved correctly from service
- [ ] Empty trips handled gracefully

**Related**: research.md Section 2, design.md Phase 2

---

## Task 3: Fix Sensor Value Display

**Description**: Show "N/A" for unavailable sensors instead of filtering them out

**Files**:
- `custom_components/ev_trip_planner/frontend/panel.js` (line 1767)

**Steps**:
1. Read current sensor filtering code
2. Change `return null` to `return 'N/A'` for unavailable states
3. Verify sensors show "N/A" instead of being hidden

**Acceptance Criteria**:
- [ ] Sensors with unavailable state show "N/A"
- [ ] Sensors with valid state show correct value
- [ ] No sensors silently filtered out

**Related**: research.md Section 3, design.md Phase 3

---

## Task 4: Ensure Panel Renders Completely

**Description**: Ensure panel renders completely before enabling interactions

**Files**:
- `custom_components/ev_trip_planner/frontend/panel.js` (around line 2109)

**Steps**:
1. Verify `window._tripPanel` is set after all rendering
2. Verify trips section renders after panel content
3. Verify add trip button is functional

**Acceptance Criteria**:
- [ ] `window._tripPanel` is set correctly
- [ ] Panel renders completely
- [ ] Add trip button is functional
- [ ] Modal opens when clicked

**Related**: research.md Section 4, design.md Phase 4

---

## Task 5: Test and Deploy

**Description**: Deploy fixes and test in Home Assistant

**Files**:
- All modified files

**Steps**:
1. Deploy updated panel.js to Home Assistant
2. Restart Home Assistant
3. Clear browser cache
4. Test panel functionality
5. Check browser console for errors

**Acceptance Criteria**:
- [ ] Panel loads without errors
- [ ] Vehicle ID displayed correctly
- [ ] Sensors show values (not 0.0%)
- [ ] Trips section loads
- [ ] Add trip button works
- [ ] Trip creation works

**Related**: design.md Deployment Steps

---

## Summary

**Total Tasks**: 5

**Estimated Effort**: 2-4 hours

**Priority**: High (blocks trip management functionality)

**Dependencies**:
- Task 1 must complete before Task 2 (vehicle ID needed for service calls)
- Task 2 must complete before Task 4 (panel needs to load trips)
- Task 3 can be done in parallel

**Rollback Plan**: If fixes don't work, revert to previous panel.js version and re-analyze.
