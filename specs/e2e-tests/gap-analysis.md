# Gap Analysis: E2E Tests for EV Trip Planner

## Current Test Count

| File | Tests |
|------|-------|
| trip-crud.spec.ts | 3 |
| trip-states.spec.ts | 4 |
| **Total** | **7** |

## Service Validation Gaps

### trip-crud.spec.ts

#### Test: "should create a recurring trip"
**Current validation**:
- ✅ Form overlay closes (`toBeHidden()`)
- ✅ Trip cards count > 0

**Missing validation**:
- ❌ No explicit validation that `ev_trip_planner.trip_create` service was called
- ❌ No validation of service parameters (vehicle_id, type, day_of_week, time, km, kwh)
- ❌ No validation of trip-card data attributes

#### Test: "should edit an existing trip"
**Current validation**:
- ✅ Form overlay closes
- ✅ Trip cards contain updated text ("40.0 km", "14:30")

**Missing validation**:
- ❌ No explicit validation that `ev_trip_planner.trip_update` service was called
- ❌ No validation of updated data attributes

#### Test: "should delete an existing trip"
**Current validation**:
- ✅ Trip count decreases
- ✅ Empty state shown if last trip deleted

**Missing validation**:
- ❌ No explicit validation that `ev_trip_planner.delete_trip` service was called

### trip-states.spec.ts

#### Test: "should pause a recurring trip"
**Current validation**:
- ✅ Dialog handler present (`page.on('dialog')`)
- ✅ Pause button hidden
- ✅ data-active="false"
- ✅ Badge contains "Inactivo"

**Status**: GOOD - Validates service call via UI persistence

#### Test: "should resume a paused trip"
**Current validation**:
- ✅ Dialog handler present
- ✅ Resume button hidden
- ✅ data-active="true"
- ✅ Badge contains "Activo"

**Status**: GOOD - Validates service call via UI persistence

#### Test: "should complete a punctual trip"
**Current validation**:
- ✅ Complete button hidden
- ✅ Badge contains "Completado"
- ✅ Action buttons count = 0

**Status**: GOOD - Validates service call via UI persistence

#### Test: "should cancel a punctual trip"
**Current validation**:
- ✅ Dialog handler present
- ✅ Cancel button hidden
- ✅ Badge contains "Cancelado"
- ✅ Action buttons count = 0

**Status**: GOOD - Validates service call via UI persistence

## AC Coverage Summary

| User Story | AC Count | Covered | Missing |
|------------|----------|---------|---------|
| US-1 (Create recurring) | 5 | 3 | AC-1.3, AC-1.5 |
| US-2 (Create punctual) | 3 | 0 | AC-2.1, AC-2.2, AC-2.3 |
| US-3 (Edit trip) | 4 | 2 | AC-3.4 |
| US-4 (Delete trip) | 4 | 2 | AC-4.4 |
| US-5 (Pause/Resume) | 5 | 5 | None |
| US-6 (Complete/Cancel) | 5 | 5 | None |
| US-7 (Auth bypass) | 5 | 5 | None |

**Total**: 29 AC, 22 covered, 7 missing (76% coverage)

## Key Findings

1. **US-2 completely missing**: No tests for creating punctual trips
2. **Service validation indirect**: Current tests validate via UI persistence (acceptable pattern)
3. **Dialog handlers**: All dialog handlers in trip-states.spec.ts are correctly placed BEFORE clicks
4. **Data attributes**: trip-states.spec.ts correctly validates `data-active` for state changes

## Recommendations

1. Add test for punctual trip creation (US-2)
2. Add explicit service validation comments to create/edit/delete tests
3. Document that UI persistence validation is the E2E pattern (no need for direct service mocking)
