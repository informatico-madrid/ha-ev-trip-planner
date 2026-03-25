---
spec: 019-panel-vehicle-crud
phase: research
created: 2026-03-24
---

# Research: E2E Testing for EV Trip Planner Panel CRUD

## Executive Summary

The EV Trip Planner project already uses **Playwright** as the E2E testing framework with comprehensive test patterns for CRUD operations. Tests follow a **static analysis approach** (verifying code exists) rather than browser automation (controlling the browser). For complete CRUD verification, we need to implement actual browser-based interaction tests that:

1. Login to Home Assistant
2. Navigate to the panel URL (`/ev-trip-planner-{vehicle_id}`)
3. Interact with trip forms (create/edit/delete)
4. Verify service calls are made

---

## External Research

### Best Practices for E2E Testing Custom Home Assistant Panels

| Aspect | Finding | Source |
|--------|---------|--------|
| **Framework** | Playwright is the recommended framework for HA custom panels | Project's existing implementation |
| **Authentication** | Use Playwright's authentication to preserve login state across tests | playwright.config.ts |
| **Testing Approach** | Static code analysis (verify methods exist) + browser automation (interact with UI) | specs/018-e2e-playwright-testing/research.md |
| **Service Mocking** | HA services must be mocked using HA's API, not JavaScript mocks | HA documentation patterns |
| **Test Structure** | Page Object pattern for maintainability when UI changes | specs/018-e2e-playwright-testing/research.md |

### Existing Test Patterns in Project

The project has 4 E2E test files in `tests/e2e/`:

| Test File | Purpose | Approach |
|-----------|---------|----------|
| `test-panel-rendering.spec.ts` | Verify rendering logic | Static code analysis |
| `test-us7-trips-ui.spec.ts` | Verify trip display structure | Static code analysis |
| `test-us8-trip-crud.spec.ts` | Verify CRUD methods exist | Static code analysis |
| `test-us9-ui.spec.ts` | Verify CSS styling | Static code analysis |

**Gap**: All tests use **static analysis** (reading file contents) rather than **browser automation** (interacting with the rendered panel).

### Why Static Analysis Approach

From existing tests:

```typescript
// Example from test-us8-trip-crud.spec.ts
test('should have _showTripForm method to display trip creation form', async () => {
  const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');
  expect(panelContent).toContain('_showTripForm()');  // Static analysis
  expect(panelContent).toContain('trip-form-overlay');
});
```

This approach:
- ✅ Fast (no browser needed)
- ✅ Verifies code exists
- ❌ Does NOT verify actual UI interaction works
- ❌ Does NOT verify service calls are made

---

## Codebase Analysis

### Existing Test Infrastructure

**Playwright Configuration** (`tests/e2e/playwright.config.ts`):

```typescript
export default defineConfig({
  testDir: './',
  timeout: 60000,
  use: {
    baseURL: haUrl,  // http://localhost:8123
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
  ],
  webServer: {
    url: haUrl,
    timeout: 120 * 1000,
    reuseExistingServer: true,
  },
});
```

**Environment Variables**:
- `HA_URL`: `http://localhost:8123`
- `HA_USER`: `tests`
- `HA_PASSWORD`: `tests`

### Panel URL Pattern

From `panel.js` lines 71-121:
```javascript
// URL formats supported:
// /ev-trip-planner-{vehicle_id}
// /panel/ev-trip-planner-{vehicle_id}
// Extracted via split and regex methods
```

### Service Calls Used by Panel

From `panel.js`, the panel makes these HA service calls:

| Service | Method | Purpose |
|---------|--------|---------|
| `ev_trip_planner.trip_list` | `callService()` | Get all trips |
| `ev_trip_planner.trip_create` | `callService()` | Create new trip |
| `ev_trip_planner.trip_update` | `callService()` | Update existing trip |
| `ev_trip_planner.delete_trip` | `callService()` | Delete trip |
| `ev_trip_planner.pause_recurring_trip` | `callService()` | Pause recurring trip |
| `ev_trip_planner.resume_recurring_trip` | `callService()` | Resume recurring trip |
| `ev_trip_planner.complete_punctual_trip` | `callService()` | Mark punctual trip complete |
| `ev_trip_planner.cancel_punctual_trip` | `callService()` | Cancel punctual trip |

### Form Fields

From `_showTripForm()` (lines 560-625):
- `trip-type`: Select (recurrente/puntual)
- `trip-day`: Select (Domingo-Sábado, only for recurring)
- `trip-time`: Time input
- `trip-km`: Number input (distance in km)
- `trip-kwh`: Number input (energy in kWh)
- `trip-description`: Textarea (optional)

---

## Recommended Test Framework

### Decision: Continue Using Playwright

**Rationale**:
1. ✅ Already installed and configured
2. ✅ Best-in-class auto-wait and retry mechanisms
3. ✅ Multi-browser support (Chrome, Firefox, Safari)
4. ✅ Mobile device emulation
5. ✅ Built-in screenshot/video debugging
6. ✅ Excellent TypeScript support

**Alternatives Considered**:
- **Cypress**: Less suitable for mobile testing, slower
- **Selenium**: More boilerplate, outdated
- **Puppeteer**: Chrome-only

---

## Test Strategy for CRUD Operations

### Strategy Overview

| Test Type | Description | Current Status |
|-----------|-------------|----------------|
| Static Code Analysis | Verify methods exist in panel.js | ✅ Implemented |
| Browser Automation | Interact with panel in real browser | ⚠️ Not implemented |
| Service Verification | Verify HA service calls are made | ⚠️ Not implemented |

### Recommended Test Cases for Browser Automation

#### 1. Panel Loading Test

```typescript
test('should load panel and extract vehicle_id from URL', async ({ page }) => {
  await page.goto('http://localhost:8123/ev-trip-planner-chispitas');

  // Verify panel header exists
  await expect(page).toHaveText(/EV Trip Planner - chispitas/i);

  // Verify panel is not empty
  await expect(page.locator('.panel-container')).toBeVisible();
});
```

#### 2. Trip List Loading Test

```typescript
test('should load trips from HA service', async ({ page }) => {
  await page.goto('http://localhost:8123/ev-trip-planner-chispitas');

  // Wait for trips section to load
  await expect(page.locator('#trips-section')).toBeVisible();

  // Verify trip count in header
  await expect(page.locator('.trips-header h2')).toContainText('Viajes Programados');
});
```

#### 3. Create Trip Test

```typescript
test('should create a new recurring trip', async ({ page }) => {
  await page.goto('http://localhost:8123/ev-trip-planner-chispitas');

  // Click "Agregar Viaje"
  await page.click('.add-trip-btn');

  // Fill form
  await page.selectOption('#trip-type', 'recurrente');
  await page.selectOption('#trip-day', '1'); // Lunes
  await page.fill('#trip-time', '08:00');
  await page.fill('#trip-km', '25.5');
  await page.fill('#trip-kwh', '5.2');
  await page.fill('#trip-description', 'Viaje al trabajo');

  // Submit form
  await page.click('.btn-primary');

  // Verify success alert
  await expect(page.locator('.alert')).toContainText('✅ Viaje creado exitosamente');

  // Verify trip appears in list
  await expect(page.locator('.trip-card')).toHaveCount(1);
});
```

#### 4. Edit Trip Test

```typescript
test('should edit an existing trip', async ({ page }) => {
  await page.goto('http://localhost:8123/ev-trip-planner-chispitas');

  // Click edit button on first trip
  await page.click('.edit-btn');

  // Update trip time
  await page.fill('#edit-trip-time', '09:00');
  await page.fill('#edit-trip-km', '30.0');

  // Submit
  await page.click('.btn-primary');

  // Verify update
  await expect(page.locator('.trip-card')).toContainText('09:00');
});
```

#### 5. Delete Trip Test

```typescript
test('should delete a trip', async ({ page }) => {
  await page.goto('http://localhost:8123/ev-trip-planner-chispitas');

  // Click delete button
  await page.click('.delete-btn');

  // Confirm dialog
  await page.click('button:has-text("Sí")');

  // Verify trip removed
  await expect(page.locator('.trip-card:has-text("Trip 1")')).toHaveCount(0);
});
```

#### 6. Pause/Resume Trip Test

```typescript
test('should pause and resume a recurring trip', async ({ page }) => {
  await page.goto('http://localhost:8123/ev-trip-planner-chispitas');

  // Pause trip
  await page.click('.pause-btn');
  await page.click('button:has-text("Sí")');
  await expect(page.locator('.trip-card')).toHaveClass(/trip-card-inactive/);

  // Resume trip
  await page.click('.resume-btn');
  await expect(page.locator('.trip-card')).not.toHaveClass(/trip-card-inactive/);
});
```

#### 7. Complete/Cancel Punctual Trip Test

```typescript
test('should complete or cancel a punctual trip', async ({ page }) => {
  await page.goto('http://localhost:8123/ev-trip-planner-chispitas');

  // Complete trip
  await page.click('.complete-btn');
  await page.click('button:has-text("Sí")');
  await expect(page.locator('.trip-card:has-text("Trip 1")')).toHaveCount(0);
});
```

---

## Mocking Home Assistant Services

### Challenge: Cannot Mock HA Services Directly

HA services are backend calls - they cannot be mocked in JavaScript tests.

### Solution Options

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **Real HA Instance** | Run HA and test against real services | Most accurate | Requires HA setup, slower |
| **HA API Verification** | Verify service calls via HA REST API | Fast, accurate | Requires HA running |
| **WebSocket Subscription** | Subscribe to events via HA WebSocket | Real-time verification | Complex setup |
| **Mock HA Container** | Run HA in Docker with test config | Isolated environment | Extra infrastructure |

### Recommended Approach: Real HA + API Verification

```typescript
// Example: Verify trip was created via HA API
import axios from 'axios';

test('should create trip and verify via HA API', async ({ page }) => {
  const haToken = process.env.HA_TOKEN || '';
  const haUrl = 'http://localhost:8123';

  // Make trip creation request in panel
  await page.click('.add-trip-btn');
  await page.fill('#trip-time', '08:00');
  await page.click('.btn-primary');

  // Verify via HA API
  const response = await axios.get(`${haUrl}/api/states`, {
    headers: { Authorization: `Bearer ${haToken}` }
  });

  const trips = response.data.filter(s =>
    s.entity_id.includes('ev_trip_planner_chispitas')
  );

  expect(trips).toHaveLength(1);
});
```

---

## Common Pitfalls in Testing Custom HA Panels

| Pitfall | Prevention |
|---------|------------|
| **Panel not loading** | Wait for `window._tripPanel` to be set |
| **Vehicle ID not extracted** | Use correct URL format (`/ev-trip-planner-{vehicle_id}`) |
| **Service calls failing** | Ensure HA instance is running with proper config |
| **Race conditions** | Use Playwright's auto-wait (don't add explicit waits) |
| **Form not appearing** | Wait for overlay to be visible before filling |
| **Confirmation dialogs** | Handle with `page.on('dialog')` |
| **Multiple connectedCallback calls** | Wait for `_rendered = true` |

### Example: Handling Confirmation Dialogs

```typescript
test('should handle delete confirmation', async ({ page }) => {
  // Set up dialog handler
  page.on('dialog', dialog => {
    dialog.accept(); // Auto-accept confirmations
  });

  await page.click('.delete-btn');
  await page.waitForSelector('.trip-card:visible', { state: 'detached' });
});
```

---

## Verification Tooling

### Current Setup

| Tool | Command | Status |
|------|---------|--------|
| Dev Server | `HA_URL=http://localhost:8123 npx playwright test` | ✅ Configured |
| Test Framework | `@playwright/test@1.58.2` | ✅ Installed |
| Test Runner | `npx playwright test` | ✅ Working |
| Report | `playwright-report/` | ✅ Generated |
| Debugging | `--headed`, `--debug`, `trace` | ✅ Available |

### Environment Setup

```bash
# Set environment variables
export HA_URL=http://localhost:8123
export HA_USER=tests
export HA_PASSWORD=tests

# Run tests
npx playwright test

# Run with visible browser
npx playwright test --headed

# Run in debug mode
npx playwright test --debug

# Generate report
npx playwright show-report
```

---

## Recommendations for Implementation

1. **Start with static analysis tests** (already implemented) - verify code exists
2. **Add browser automation tests** - interact with rendered panel
3. **Implement HA API verification** - verify service calls via REST API
4. **Use page object pattern** - make tests maintainable
5. **Add screenshots on failure** - debug issues visually
6. **Run against real HA instance** - ensure tests are accurate

---

## Open Questions

1. What is the exact HA token format for API calls?
2. Can we run HA in a test container for isolated testing?
3. What is the expected response format for `trip_list` service?
4. Do we need to seed test data (existing trips) before running tests?

---

## Sources

- **Project Code**: `custom_components/ev_trip_planner/frontend/panel.js`
- **Test Config**: `tests/e2e/playwright.config.ts`
- **Existing Tests**: `tests/e2e/test-us8-trip-crud.spec.ts`
- **Research Docs**: `specs/018-e2e-playwright-testing/research.md`
- **HA Documentation**: Home Assistant panel_custom component API

---

## Next Steps

1. ✅ Review existing static analysis tests
2. ⚠️ Create browser automation tests for CRUD operations
3. ⚠️ Implement HA API verification patterns
4. ⚠️ Document test data requirements
5. ⚠️ Set up test HA instance (if needed)
