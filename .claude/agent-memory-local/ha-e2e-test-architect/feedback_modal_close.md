---
name: Modal close pattern in E2E tests
description: Wait for dialog to detach before verifying trip list after form submission
type: feedback
---

## Rule: Always wait for modal/dialog to close before verifying results

**Why:** After accepting a browser dialog with `dialog.accept()`, the modal overlay may not disappear immediately. If the test proceeds to verify the trip list before the modal closes, it will fail because the trip cards are not yet visible.

**How to apply:** After handling browser dialogs, explicitly wait for the dialog element to detach before checking results:

```typescript
// Step 4: Handle browser confirmation dialog
const dialog = await page.waitForEvent('dialog', { timeout: 10000 });
await dialog.accept();
console.log('[Test] Dialog accepted');

// Wait for the modal to close - the dialog overlay should disappear
await page.waitForSelector('[role="dialog"]', { state: 'detached', timeout: 10000 });
console.log('[Test] Modal closed, verifying trip list');

// Step 5: Verify the trip appears in the list with retry
const tripCards = page.locator('.trip-card');
await expect(async () => {
  const count = await tripCards.count();
  expect(count).toBeGreaterThanOrEqual(1);
}).toPass({ timeout: 10000 });
```

**Impact:** This pattern ensures tests wait for UI state to stabilize before making assertions, preventing flaky tests due to timing issues.

**Location:** Used in `tests/e2e/test-create-trip.spec.ts` at line 124-144
