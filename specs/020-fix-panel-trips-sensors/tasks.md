# Tasks: Fix Panel Trips Sensors

## Phase 1: Make It Work (POC)

Focus: Validate the fixes work end-to-end. Skip tests, accept hardcoded values.

- [ ] 1.1 [P] Fix vehicle ID extraction from URL with 3 fallback methods
  - **Do**: Implement 3 extraction methods (split, regex, hash) with logging at each step
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js
  - **Done when**: Vehicle ID extracted from `/ev-trip-planner-{id}` patterns with debug logs
  - **Verify**: `grep -A5 "extract vehicle_id from URL" custom_components/ev_trip_planner/frontend/panel.js | head -20`
  - **Commit**: `feat(panel): add 3 fallback methods for vehicle ID extraction from URL`
  - _Requirements: FR-1, AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5_
  - _Design: URL Parser component_

- [ ] 1.2 [P] Add debug logging to URL extraction methods
  - **Do**: Log extraction method used, URL path, and vehicle ID result
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js lines 67-102
  - **Done when**: Console shows extraction method and vehicle ID for every panel load
  - **Verify**: `grep "EV Trip Planner Panel: vehicle_id from" custom_components/ev_trip_planner/frontend/panel.js`
  - **Commit**: `feat(panel): add debug logging to vehicle ID extraction`
  - _Requirements: FR-10_
  - _Design: Debug logging section_

- [ ] 1.3 [P] Fix trip list service response normalization for 3 formats
  - **Do**: Handle direct result, array `[result]`, and object `{result: ...}` response formats
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js lines 397-435
  - **Done when**: Service call returns trips regardless of HA version response format
  - **Verify**: `grep -A10 "Handle array response" custom_components/ev_trip_planner/frontend/panel.js`
  - **Commit**: `feat(panel): normalize 3 trip list service response formats`
  - _Requirements: FR-2, AC-2.1, AC-2.2, AC-2.3_
  - _Design: Trip Service Handler component_

- [ ] 1.4 [P] Add response format logging to trip service handler
  - **Do**: Log the raw response, normalized tripsData, and extraction method used
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js lines 400-430
  - **Done when**: Console shows response format and trip count for every trip fetch
  - **Verify**: `grep "EV Trip Planner Panel: Trips data" custom_components/ev_trip_planner/frontend/panel.js`
  - **Commit**: `feat(panel): add debug logging to trip service handler`
  - _Requirements: FR-10, AC-2.6_
  - _Design: Debug logging section_

- [ ] 1.5 Fix sensor filtering to show "N/A" instead of filtering unavailable
  - **Do**: Remove filter that excludes unavailable/unknown sensors, allow them to display "N/A"
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js lines 2088-2110
  - **Done when**: Sensors with unavailable state show "N/A" value instead of being hidden
  - **Verify**: `grep -A3 "Filter out sensors with unavailable" custom_components/ev_trip_planner/frontend/panel.js | head -10`
  - **Commit**: `fix(panel): show N/A for unavailable sensors instead of filtering`
  - _Requirements: FR-4, AC-3.1_
  - _Design: Sensor Manager component_

- [ ] 1.6 Implement smart value formatting by unit type
  - **Do**: Format percentages (1 decimal), energy kWh (2 decimals), distance km (1 decimal)
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js lines 1775-1831
  - **Done when**: Values display with appropriate precision based on unit type
  - **Verify**: `grep -A15 "_formatNumericValue" custom_components/ev_trip_planner/frontend/panel.js | head -25`
  - **Commit**: `feat(panel): implement smart numeric formatting by unit type`
  - _Requirements: FR-5, AC-3.2_
  - _Design: Sensor Manager component_

- [ ] 1.7 Format boolean values with icons
  - **Do**: Convert 'on'/'true' to "✓ Activo", 'off'/'false' to "✗ Inactivo"
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js lines 1761-1769
  - **Done when**: Boolean sensor values display Spanish icons
  - **Verify**: `grep -A8 "_formatBooleanValue" custom_components/ev_trip_planner/frontend/panel.js`
  - **Commit**: `feat(panel): format boolean values with check icons`
  - _Requirements: AC-3.3_
  - _Design: Sensor Manager component_

- [ ] 1.8 Fix panel rendering timing to prevent race conditions
  - **Do**: Set _rendered = true only after trips section fully loads in _renderTripsLater()
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js lines 2200-2233
  - **Done when**: _rendered flag set after innerHTML written AND trips section rendered
  - **Verify**: `grep -A5 "_renderTripsLater()" custom_components/ev_trip_planner/frontend/panel.js | tail -10`
  - **Commit**: `fix(panel): set _rendered flag after trips section fully rendered`
  - _Requirements: FR-9, AC-5.4, AC-5.5_
  - _Design: Renderer component_

- [ ] 1.9 Add early exit guards to connectedCallback
  - **Do**: Check _rendered flag and hasContent before re-rendering
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js lines 41-60
  - **Done when**: Panel exits early if already fully rendered with content
  - **Verify**: `grep -A3 "Already fully rendered" custom_components/ev_trip_planner/frontend/panel.js`
  - **Commit**: `fix(panel): add early exit guards to connectedCallback`
  - _Requirements: AC-5.1, AC-5.6_
  - _Design: Renderer component_

- [ ] 1.10 Stop polling immediately when panel begins rendering
  - **Do**: Clear _pollTimeout when _render() is called, set _pollStarted = false
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js lines 2000-2020
  - **Done when**: Polling stops as soon as rendering starts, no race conditions
  - **Verify**: `grep "_pollStarted = false" custom_components/ev_trip_planner/frontend/panel.js`
  - **Commit**: `fix(panel): stop polling immediately when rendering begins`
  - _Requirements: AC-5.1, AC-5.5_
  - _Design: HA Connection Polling component_

- [ ] 1.11 [VERIFY] Quality checkpoint: verify panel.js syntax
  - **Do**: Run JavaScript syntax validation on panel.js
  - **Verify**: `node -c custom_components/ev_trip_planner/frontend/panel.js && echo "SYNTAX_OK"`
  - **Done when**: No syntax errors in panel.js
  - **Commit**: None

## Phase 2: Refactoring

After POC validated, clean up code and improve error handling.

- [ ] 2.1 Refactor URL extraction into reusable helper function
  - **Do**: Extract vehicle ID logic into dedicated function with clear interface
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js
  - **Done when**: URL extraction is in single function, called from connectedCallback and hass setter
  - **Verify**: `grep "_extractVehicleIdFromUrl" custom_components/ev_trip_planner/frontend/panel.js`
  - **Commit**: `refactor(panel): extract vehicle ID extraction into reusable function`
  - _Design: URL Parser component_

- [ ] 2.2 Refactor response normalization into dedicated method
  - **Do**: Extract trip response handling into _normalizeTripResponse() method
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js
  - **Done when**: Response normalization logic is in single method
  - **Verify**: `grep "_normalizeTripResponse" custom_components/ev_trip_planner/frontend/panel.js`
  - **Commit**: `refactor(panel): extract response normalization into dedicated method`
  - _Design: Trip Service Handler component_

- [ ] 2.3 Add comprehensive error handling for service calls
  - **Do**: Wrap service calls in try/catch with graceful error messages in UI
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js
  - **Done when**: Service failures show error message instead of breaking panel
  - **Verify**: `grep -A5 "catch (error)" custom_components/ev_trip_planner/frontend/panel.js | head -20`
  - **Commit**: `refactor(panel): add comprehensive error handling for service calls`
  - _Design: Error Handling section_

- [ ] 2.4 Add error boundary for sensor rendering
  - **Do**: Catch errors during sensor value formatting and show fallback
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js
  - **Done when**: Sensor formatting errors don't crash panel rendering
  - **Verify**: `grep "_formatSensorValue" custom_components/ev_trip_planner/frontend/panel.js`
  - **Commit**: `refactor(panel): add error boundary for sensor rendering`
  - _Design: Sensor Manager component_

- [ ] 2.5 [VERIFY] Quality checkpoint: syntax and linting
  - **Do**: Verify JavaScript syntax and check for common issues
  - **Verify**: `node -c custom_components/ev_trip_planner/frontend/panel.js && echo "CHECK_PASS"`
  - **Done when**: No syntax errors or linting issues
  - **Commit**: None

## Phase 3: Testing

Add comprehensive tests to verify all fixes work correctly.

- [ ] 3.1 [P] Add unit tests for URL extraction methods
  - **Do**: Create test file testing each URL extraction method with various URL patterns
  - **Files**: tests/unit/test-url-extraction.js
  - **Done when**: All URL patterns tested: `/ev-trip-planner-{id}`, `/panel/ev-trip-planner-{id}`
  - **Verify**: `npx playwright test tests/unit/test-url-extraction.js --grep "URL extraction"`
  - **Commit**: `test(panel): add unit tests for URL extraction`
  - _Requirements: AC-1.1, AC-1.2, AC-1.3_

- [ ] 3.2 [P] Add unit tests for trip response normalization
  - **Do**: Test all 3 response formats: direct, array `[result]`, object `{result: ...}`
  - **Files**: tests/unit/test-trip-response.js
  - **Done when**: All response formats correctly normalized
  - **Verify**: `npx playwright test tests/unit/test-trip-response.js --grep "response normalization"`
  - **Commit**: `test(panel): add unit tests for trip response normalization`
  - _Requirements: AC-2.1, AC-2.2, AC-2.3_

- [ ] 3.3 [P] Add unit tests for sensor value formatting
  - **Do**: Test numeric formatting for percentages, energy, distance, booleans
  - **Files**: tests/unit/test-sensor-formatting.js
  - **Done when**: All value types format correctly with appropriate precision
  - **Verify**: `npx playwright test tests/unit/test-sensor-formatting.js --grep "formatting"`
  - **Commit**: `test(panel): add unit tests for sensor value formatting`
  - _Requirements: AC-3.2, AC-3.3_

## Phase 4: Quality Gates

Verify all quality gates pass before PR.

- [ ] 4.1 Local quality check: syntax and code quality
  - **Do**: Run all quality checks locally
  - **Verify**:
    - Syntax: `node -c custom_components/ev_trip_planner/frontend/panel.js && echo "OK"`
    - No console warnings: `grep -c "console.warn" custom_components/ev_trip_planner/frontend/panel.js`
  - **Done when**: No syntax errors, all code follows project patterns
  - **Commit**: `chore(panel): pass local quality checks`

- [ ] 4.2 Create PR and verify CI
  - **Do**:
    1. Verify current branch is feature branch: `git branch --show-current`
    2. Push branch: `git push -u origin feat/020-fix-panel-trips-sensors`
    3. Create PR: `gh pr create --title "feat(panel): fix vehicle ID extraction, sensor display, and rendering" --body "Fix panel bugs: vehicle ID extraction, trip list response handling, N/A sensor display, render timing"`
    4. Monitor CI: `gh pr checks --watch`
  - **Verify**: All CI checks show ✓ (passing)
  - **Done when**: CI pipeline passes, PR ready for review
  - **If CI fails**: Read failure, fix locally, re-push, re-verify

## Phase 5: PR Lifecycle

Continuous validation until all completion criteria met.

- [ ] 5.1 Address code review comments
  - **Do**: Review PR comments, make requested changes, re-push
  - **Verify**: All review comments addressed
  - **Done when**: LGTM from reviewer, no pending comments

- [ ] 5.2 Final validation: AC checklist
  - **Do**: Programmatically verify each acceptance criterion:
    - grep for vehicle ID extraction patterns
    - grep for response normalization logic
    - grep for N/A sensor display
    - grep for _rendered flag timing
  - **Verify**: All AC-1.* through AC-5.* satisfied in code
  - **Done when**: All acceptance criteria verified via automated checks
  - **Commit**: None

- [ ] 5.7 VE4 [VERIFY] Goal verification: panel now works end-to-end
  - **Do**:
    1. Open panel in browser or verify via API
    2. Confirm vehicle ID extracted correctly
    3. Confirm trips load
    4. Confirm sensors show values (not hidden)
  - **Verify**: `curl http://localhost:8123/api/states | jq . | grep -c "ev_trip_planner"`
  - **Done when**: Panel displays all data correctly
  - **Commit**: None

## Notes

- **POC shortcuts taken**: Debug logs left in place (will be removed in production), error messages are basic console logs
- **Production TODOs**: Remove debug logging, add structured error logging, improve error messages for users
