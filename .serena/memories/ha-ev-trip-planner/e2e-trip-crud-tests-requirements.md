# E2E Trip CRUD Tests - Requirements

## User Stories
- US-1: Create Recurring Trip
- US-2: Create Punctual Trip
- US-3: Edit Trip
- US-4: Delete Trip

## Form Selectors (Shadow DOM)
- Create form: `#trip-type`, `#trip-day`, `#trip-datetime`, `#trip-time`, `#trip-km`, `#trip-kwh`, `#trip-description`
- Edit form: `#edit-trip-type`, `#edit-trip-day`, `#edit-trip-datetime`, `#edit-trip-time`, `#edit-trip-km`, `#edit-trip-kwh`, `#edit-trip-description`
- Buttons: `.btn-primary` (submit), `.btn-secondary` (cancel)
- Trip card actions: `.edit-btn`, `.delete-btn`
- Trip card: `.trip-card`

## Dialog Handling
- Delete shows `window.confirm()` dialog - must use `page.on('dialog')` before triggering

## Key Learnings
- test-helpers.ts has TripPanel base class with fillTripForm, submitTripForm, setupDialogHandler, getTripCount
- Approach (A): independent tests with cleanup in test.afterEach()
- Shadow DOM traversal: `ev-trip-planner-panel >> #selector`
- Vehicle "Coche2" configured via Config Flow in auth.setup.ts