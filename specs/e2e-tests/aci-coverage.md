# Acceptance Criteria Coverage: E2E Tests for EV Trip Planner

## Coverage Summary

| User Story | AC | Status | Test File | Test Name |
|------------|-----|--------|-----------|-----------|
| **US-1: Create Recurring Trip** |
| AC-1.1 | [x] | ✅ | trip-crud.spec.ts | should create a recurring trip |
| AC-1.2 | [x] | ✅ | trip-crud.spec.ts | should create a recurring trip |
| AC-1.3 | [ ] | ❌ | - | Service parameter validation |
| AC-1.4 | [x] | ✅ | trip-crud.spec.ts | should create a recurring trip |
| AC-1.5 | [ ] | ❌ | - | Trip-card data attributes |
| **US-2: Create Punctual Trip** |
| AC-2.1 | [ ] | ❌ | - | Missing test |
| AC-2.2 | [ ] | ❌ | - | Missing test |
| AC-2.3 | [ ] | ❌ | - | Missing test |
| **US-3: Edit Trip** |
| AC-3.1 | [x] | ✅ | trip-crud.spec.ts | should edit an existing trip |
| AC-3.2 | [x] | ✅ | trip-crud.spec.ts | should edit an existing trip |
| AC-3.3 | [x] | ✅ | trip-crud.spec.ts | should edit an existing trip |
| AC-3.4 | [ ] | ❌ | - | Service update validation |
| **US-4: Delete Trip** |
| AC-4.1 | [x] | ✅ | trip-crud.spec.ts | should delete an existing trip |
| AC-4.2 | [x] | ✅ | trip-crud.spec.ts | should delete an existing trip |
| AC-4.3 | [x] | ✅ | trip-crud.spec.ts | should delete an existing trip |
| AC-4.4 | [ ] | ❌ | - | Service delete validation |
| **US-5: Pause/Resume Trip** |
| AC-5.1 | [x] | ✅ | trip-states.spec.ts | should pause a recurring trip |
| AC-5.2 | [x] | ✅ | trip-states.spec.ts | should pause a recurring trip |
| AC-5.3 | [x] | ✅ | trip-states.spec.ts | should pause a recurring trip |
| AC-5.4 | [x] | ✅ | trip-states.spec.ts | should resume a paused trip |
| AC-5.5 | [x] | ✅ | trip-states.spec.ts | should resume a paused trip |
| **US-6: Complete/Cancel Trip** |
| AC-6.1 | [x] | ✅ | trip-states.spec.ts | should complete a punctual trip |
| AC-6.2 | [x] | ✅ | trip-states.spec.ts | should complete a punctual trip |
| AC-6.3 | [x] | ✅ | trip-states.spec.ts | should cancel a punctual trip |
| AC-6.4 | [x] | ✅ | trip-states.spec.ts | should cancel a punctual trip |
| AC-6.5 | [x] | ✅ | trip-states.spec.ts | should cancel a punctual trip |
| **US-7: Auth Bypass** |
| AC-7.1 | [x] | ✅ | All tests | waitUntil: domcontentloaded |
| AC-7.2 | [x] | ✅ | Configuration | trusted_networks configured |
| AC-7.3 | [x] | ✅ | All tests | No login required |
| AC-7.4 | [x] | ✅ | All tests | Direct panel access |
| AC-7.5 | [x] | ✅ | Configuration | trusted_users configured |

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total AC | 29 |
| Covered | 22 |
| Missing | 7 |
| Coverage % | 76% |

## Missing AC Details

### US-1: Create Recurring Trip (2 missing)
- **AC-1.3**: Service parameter validation - Need to validate `ev_trip_planner.trip_create` parameters
- **AC-1.5**: Trip-card data attributes - Need to validate data attributes on created trip-card

### US-2: Create Punctual Trip (3 missing)
- **AC-2.1**: No test exists for creating punctual trips
- **AC-2.2**: No test exists for service validation on punctual creation
- **AC-2.3**: No test exists for pending state validation

### US-3: Edit Trip (1 missing)
- **AC-3.4**: Service update validation - Need to validate `ev_trip_planner.trip_update` service

### US-4: Delete Trip (1 missing)
- **AC-4.4**: Service delete validation - Need to validate `ev_trip_planner.delete_trip` service

## Recommendations

1. **Priority 1**: Add US-2 tests (create punctual trip) - completely missing
2. **Priority 2**: Add service validation comments to create/edit/delete tests
3. **Priority 3**: Validate data attributes on trip-cards after operations
