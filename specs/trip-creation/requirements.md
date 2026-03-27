# Trip Creation - Requirements

## Goal

Implement complete trip creation, edit, and delete functionality for the EV Trip Planner panel with proper error handling, form validation, and full E2E test coverage.

---

## User Stories

### US-1: Create Recurring Trip

**As a** EV Trip Planner user
**I want to** create a recurring trip (weekly schedule)
**So that** I can automatically track regular trips like commute to work

**Acceptance Criteria:**
- [ ] User can select "Recurring Trip" (Viaje Recurrente) option
- [ ] User can select day of week (Monday-Sunday)
- [ ] User can enter time in HH:MM format (24-hour)
- [ ] User can enter distance (km) as required field with positive number validation
- [ ] User can enter energy consumption (kWh) as required field with positive number validation
- [ ] User can add optional description with special character support
- [ ] Form validates all required fields before submission
- [ ] Service call is made to `ev_trip_planner.trip_create`
- [ ] Success notification is displayed (✅)
- [ ] Error notification is displayed on failure (❌)
- [ ] Form closes after successful creation
- [ ] Trip list refreshes immediately after creation
- [ ] New trip appears in the list with edit and delete buttons

---

### US-2: Create Punctual Trip

**As a** EV Trip Planner user
**I want to** create a punctual trip (one-time event)
**So that** I can track special trips like airport transfers or vacations

**Acceptance Criteria:**
- [ ] User can select "Punctual Trip" (Viaje Puntual) option
- [ ] User can select date and time using datetime picker
- [ ] User can enter distance (km) as required field with positive number validation
- [ ] User can enter energy consumption (kWh) as required field with positive number validation
- [ ] User can add optional description with special character support
- [ ] Form validates all required fields before submission
- [ ] Service call is made to `ev_trip_planner.trip_create`
- [ ] Success notification is displayed (✅)
- [ ] Error notification is displayed on failure (❌)
- [ ] Form closes after successful creation
- [ ] Trip list refreshes immediately after creation
- [ ] New trip appears in the list with edit and delete buttons

---

### US-3: Edit Existing Trip

**As a** EV Trip Planner user
**I want to** edit an existing trip
**So that** I can correct mistakes or update trip details

**Acceptance Criteria:**
- [ ] User can click edit button on any trip card
- [ ] Form modal opens with existing trip data pre-filled
- [ ] Form type selector changes to match trip type (recurring/punctual)
- [ ] All fields are editable (type, day/time/datetime, km, kwh, description)
- [ ] Service call is made to `ev_trip_planner.trip_update`
- [ ] Success notification is displayed (✅)
- [ ] Error notification is displayed on failure (❌)
- [ ] Trip list refreshes with updated data
- [ ] Form closes after successful update

---

### US-4: Delete Trip

**As a** EV Trip Planner user
**I want to** delete a trip
**So that** I can remove incorrect or unwanted trips

**Acceptance Criteria:**
- [ ] User can click delete button on any trip card
- [ ] Confirmation dialog appears asking "Are you sure?"
- [ ] User can confirm or cancel deletion
- [ ] Service call is made to `ev_trip_planner.delete_trip`
- [ ] Success notification is displayed on confirmation (✅)
- [ ] Error notification is displayed if deletion fails (❌)
- [ ] Trip is removed from the list immediately
- [ ] Trip list refreshes after deletion

---

### US-5: Form Validation

**As a** EV Trip Planner user
**I want to** receive clear validation feedback
**So that** I can correct input errors before submission

**Acceptance Criteria:**
- [ ] Required fields (km, kwh) must have values
- [ ] Distance (km) must be a positive number (> 0)
- [ ] Energy (kwh) must be a positive number (> 0)
- [ ] Time format must be HH:MM (24-hour format)
- [ ] Date-time must be in valid ISO format (YYYY-MM-DDTHH:MM)
- [ ] Validation errors display inline or as toast notifications
- [ ] Form cannot be submitted with validation errors
- [ ] Invalid input is highlighted visually
- [ ] Validation messages use clear language (e.g., "La distancia debe ser un número positivo")

---

### US-6: Error Handling

**As a** EV Trip Planner user
**I want to** see clear error messages when something goes wrong
**So that** I understand what went wrong and can take action

**Acceptance Criteria:**
- [ ] Network errors display "Error de conexión - intenta de nuevo"
- [ ] Backend errors display appropriate error message
- [ ] Validation errors show which fields are invalid
- [ ] Service call failures are caught and displayed
- [ ] Error notifications are dismissible
- [ ] Form remains open on error (allows retry)
- [ ] Success state is not shown on error
- [ ] Loading button state is reset on error

---

### US-7: Loading States

**As a** EV Trip Planner user
**I want to** see visual feedback when the system is processing
**So that** I know the action is in progress

**Acceptance Criteria:**
- [ ] Submit button shows "Creando..." during trip creation
- [ ] Submit button shows "Guardando..." during trip update
- [ ] Submit button is disabled during service call
- [ ] Loading text is restored after operation completes
- [ ] Button is re-enabled after operation completes
- [ ] No duplicate submissions possible during loading state

---

### US-8: Trip List Display

**As a** EV Trip Planner user
**I want to** see all my trips in organized lists
**So that** I can manage them easily

**Acceptance Criteria:**
- [ ] Recurring trips are grouped separately from punctual trips
- [ ] Each trip card shows: description, time/date, km, kwh
- [ ] Edit and delete buttons are visible on each trip card
- [ ] New trips appear immediately after creation
- [ ] Deleted trips disappear immediately
- [ ] Updated trips reflect changes immediately
- [ ] Empty state message displays when no trips exist

---

### US-9: Special Character Handling

**As a** EV Trip Planner user
**I want to** use special characters in descriptions
**So that** I can describe trips accurately in my language

**Acceptance Criteria:**
- [ ] Accented characters (á, é, í, ó, ú, ñ) are stored correctly
- [ ] Special symbols (&, <, >, etc.) are handled safely
- [ ] XSS attempts are escaped and not executed
- [ ] Long descriptions (>1000 chars) are stored without truncation
- [ ] Unicode characters are preserved in storage

---

### US-10: E2E Test Coverage

**As a** Developer
**I want to** have comprehensive E2E tests
**So that** I can verify the complete user experience works correctly

**Acceptance Criteria:**
- [ ] Test creates a recurring trip and verifies backend state
- [ ] Test creates a punctual trip and verifies backend state
- [ ] Test validates required field enforcement
- [ ] Test verifies special character handling
- [ ] Test verifies long description handling
- [ ] Test verifies edit functionality
- [ ] Test verifies delete functionality with confirmation
- [ ] Tests use Playwright with page object pattern
- [ ] Tests verify actual backend state, not just UI behavior
- [ ] Tests are deterministic and reliable

---

## Functional Requirements

### Form Handling (FR-1 to FR-5)

**FR-1:** Form submission must use `e.preventDefault()` to prevent default behavior

**FR-2:** FormData API must be used to extract form values consistently

**FR-3:** Service calls must be made to `ev_trip_planner` domain with appropriate service names:
- `trip_create` for new trips
- `trip_update` for existing trips
- `delete_trip` for removal

**FR-4:** Form must close after successful submission

**FR-5:** Trip list must be refreshed (`_loadTrips()`) after any CRUD operation

### Service Integration (FR-6 to FR-8)

**FR-6:** Service data must include:
- `vehicle_id`: from panel context
- `type`: "recurrente" or "puntual"
- For recurring: `dia_semana`, `hora`
- For punctual: `datetime`
- Common: `km`, `kwh`, `description`

**FR-7:** Service calls must use `await this._hass.callService()` with proper error handling

**FR-8:** Service response must be checked for success before showing confirmation

### State Management (FR-9 to FR-11)

**FR-9:** All form state must be managed in Lit component properties

**FR-10:** Form must be reset after successful submission

**FR-11:** Edit mode must set form values from existing trip data

### Error Handling (FR-12 to FR-14)

**FR-12:** Try-catch blocks must wrap all service calls

**FR-13:** Error messages must be displayed using alert system with emoji (❌)

**FR-14:** Form must remain open on error to allow retry

### UI/UX (FR-15 to FR-18)

**FR-15:** Success notification must use alert system with emoji (✅)

**FR-16:** Error notification must use alert system with emoji (❌)

**FR-17:** Loading button state must be shown during service calls

**FR-18:** Submit button must be disabled during service call to prevent duplicate submissions

### Validation (FR-19 to FR-22)

**FR-19:** Required fields (km, kwh) must have values before submission

**FR-20:** Distance (km) must be validated as positive number (> 0)

**FR-21:** Energy (kwh) must be validated as positive number (> 0)

**FR-22:** Time format must be validated as HH:MM (24-hour)

---

## Non-Functional Requirements

### Performance (NFR-1 to NFR-2)

**NFR-1:** Service calls must complete within 5 seconds timeout

**NFR-2:** Trip list refresh must be immediate (no visible delay)

### Security (NFR-3 to NFR-4)

**NFR-3:** All user input must be escaped to prevent XSS attacks

**NFR-4:** Service calls must use proper authentication via Home Assistant context

### Reliability (NFR-5 to NFR-6)

**NFR-5:** Form submission must be idempotent (safe to retry)

**NFR-6:** Network failures must not corrupt existing trip data

### Maintainability (NFR-7 to NFR-8)

**NFR-7:** Code must follow Lit web component patterns

**NFR-8:** Error messages must be user-friendly and actionable

### Testability (NFR-9 to NFR-10)

**NFR-9:** Form handling must be testable via Playwright E2E tests

**NFR-10:** Service calls must be verifiable via backend state checks

### Accessibility (NFR-11 to NFR-12)

**NFR-11:** Form fields must have proper labels for screen readers

**NFR-12:** Error messages must be announced to screen readers

---

## Glossary

| Term | Definition |
|------|------------|
| **Recurring Trip** | Weekly trip that repeats every week on the same day and time |
| **Punctual Trip** | One-time trip with specific date and time |
| **Viaje Recurrente** | Spanish term for recurring trip |
| **Viaje Puntual** | Spanish term for punctual trip |
| **Day of Week** | Monday-Sunday selector for recurring trips |
| **Vehicle ID** | Unique identifier for the EV in Home Assistant |
| **Service Call** | Home Assistant service invocation (`ev_trip_planner.trip_create`) |
| **Trip Manager** | Backend module handling trip CRUD operations (`trip_manager.py`) |
| **Panel** | Lit web component UI (`ev-trip-planner-panel`) |

---

## Out of Scope

- Trip scheduling/calendaring integration
- Trip statistics or analytics
- Trip sharing or collaboration
- Integration with external mapping services (Google Maps, etc.)
- Import/export trips functionality
- Trip history or archive
- Multi-vehicle management (single vehicle focus)
- Trip notifications or reminders
- Automatic trip detection from GPS
- Trip cost estimation
- Carbon footprint calculation

---

## Dependencies

### Internal Dependencies

- **Home Assistant Core**: Service framework and storage API
- **Lit Web Components**: Panel UI framework
- **TripManager**: Backend CRUD operations module
- **Coordinator**: Data synchronization between frontend and backend

### External Dependencies

- **Home Assistant Services**: `ev_trip_planner` domain services
- **YAML Configuration**: Storage backend for Container environments
- **Storage API**: Storage backend for Supervisor environments

### Testing Dependencies

- **Playwright**: E2E test framework
- **Home Assistant Test Framework**: Test container setup
- **Vehicle ID**: Environment variable for test targeting

---

## Acceptance Criteria Summary

The implementation is complete when:

1. ✅ Recurring trips can be created and appear in the list
2. ✅ Punctual trips can be created and appear in the list
3. ✅ Existing trips can be edited with pre-filled form
4. ✅ Trips can be deleted with confirmation dialog
5. ✅ Form validation prevents submission of invalid data
6. ✅ Service calls handle errors gracefully
7. ✅ Success/error notifications are displayed appropriately
8. ✅ Trip list refreshes immediately after CRUD operations
9. ✅ Special characters and long descriptions are handled safely
10. ✅ E2E tests verify complete user flow and backend state
11. ✅ All tests pass successfully

---

## Success Metrics

- **Functional Coverage**: 100% of user stories implemented
- **Test Coverage**: All critical paths covered by E2E tests
- **Error Handling**: All error scenarios have appropriate feedback
- **User Experience**: Form completes in <3 steps (open, fill, submit)
- **Reliability**: No data loss on network failures
