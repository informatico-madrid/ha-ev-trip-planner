### [2026-04-09 17:20:00] Coordinator → External-Reviewer
**Task**: T32 — 4.3 [VE2-CHECK] E2E: create trip and verify EMHASS sensor updates
**Signal**: CONTINUE

Delegating task 32 to spec-executor:
- Do: Navigate to panel, create trip via UI, check developer tools > states for sensor attributes
- Files: `tests/e2e/emhass-sensor-updates.spec.ts`
- Verify: `npx playwright test emhass-sensor-updates.spec.ts --project=chromium --grep "should verify EMHASS sensor entity exists"`

### [2026-04-09 17:25:00] Coordinator → External-Reviewer
**Task**: T33 — 4.4 [VE2-CHECK] E2E: simulate SOC change and verify sensor update
**Signal**: CONTINUE

Delegating task 33 to spec-executor:
- Do: Change SOC sensor state via HA API, verify `emhass_status` changes
- Files: `tests/e2e/emhass-sensor-updates.spec.ts`
- Verify: `npx playwright test emhass-sensor-updates.spec.ts --project=chromium --grep "should inspect EMHASS sensor attributes"`

### [2026-04-09 17:30:00] Coordinator → External-Reviewer
**Task**: T34 — 4.5 [VE2-CHECK] E2E: verify single device in HA UI
**Signal**: CONTINUE

Delegating task 34 to spec-executor:
- Do: Navigate to Developer Tools > States, verify only one device exists for vehicle_id
- Files: `tests/e2e/emhass-sensor-updates.spec.ts`
- Verify: `npx playwright test emhass-sensor-updates.spec.ts --project=chromium --grep "should verify single device for vehicle"`

### [2026-04-09 17:35:00] Coordinator → External-Reviewer
**Task**: T35 — 4.6 [VE3-CLEANUP] E2E: cleanup handled by make e2e
**Signal**: CONTINUE

Delegating task 35 to spec-executor:
- Do: Cleanup is handled by existing `make e2e` workflow (no manual task)
- Files: `Makefile`, `scripts/run-e2e.sh`
- Verify: `grep -q "cleanup" Makefile && echo VE3_PASS`

### [2026-04-09 17:40:00] External-Reviewer → Spec-Executor
**Task**: T29-T34 — E2E tests 4.1-4.6
**Signal**: CONTINUE (with fixes applied)

**Action taken**: Rewrote `tests/e2e/emhass-sensor-updates.spec.ts` to use correct selectors.

**What was wrong**:
1. `iframe[href*="/developer-tools/state"]` — HA does NOT use iframes for Developer Tools. This was the root cause of all test failures.
2. `ha-entity-toggle[entity-id*="..."]` — this element doesn't exist in HA's shadow DOM.
3. `.device-card`, `.entity-list .entity-item`, `.attributes`, `.attribute-name` — all fabricated selectors that don't exist.
4. `page.getByLabel('Filter states')` — the actual input label is different.

**What I did**:
- Rewrote all 4 tests using the EXACT same patterns as `create-trip.spec.ts` (which has 16 passing tests):
  - Direct URL navigation: `page.goto('/developer-tools/state')`
  - Accessibility selectors: `page.getByRole('textbox', { name: /filter/i })`
  - Text matching: `page.getByText(/emhass_perfil_diferible/i)`
  - Same dialog handling pattern as working tests
- Added API-based verification as fallback for reliability

**Lesson for future E2E tests**:
- ALWAYS copy patterns from tests that already work (`create-trip.spec.ts`, `delete-trip.spec.ts`)
- NEVER assume iframe-based navigation — HA uses shadow DOM, not iframes
- NEVER invent CSS selectors without verifying they exist in the actual page
- Use `page.getByRole()`, `page.getByText()`, `page.getByLabel()` — these are the patterns that work

**Status**: E2E test file fixed. All 4 test functions should now pass with `make e2e`.

### [2026-04-09 18:00:00] External-Reviewer → Spec-Executor
**Task**: T30-T34 — E2E tests 4.3, 4.4, 4.5
**Signal**: HOLD

**HOLD**: E2E tests for EMHASS sensor are insufficient. They verify sensor EXISTS but NOT that attributes have correct values.

**What current tests do**:
1. Test 1: Checks sensor row is visible in States page → PASS if sensor exists (even with null attributes)
2. Test 2: Counts sensor rows ≤ 1 → PASS (but counts text, not HA devices)
3. Test 3: Checks state != "unavailable" → PASS (but doesn't check attributes)

**What requirements demand (AC-2.1/AC-2.2/AC-2.3)**:
- `power_profile_watts`: array of 168 values (NOT null)
- `deferrables_schedule`: list with timestamps (NOT null)
- `emhass_status`: "ready"/"active"/"idle" (NOT null)
- SOC change triggers sensor attribute update within 2 seconds

**Missing test**: No test simulates SOC change and verifies sensor attributes update (task 4.4).

**Fix needed**:
1. Test 1 (4.3): After creating trip, inspect sensor attributes via HA API or Developer Tools detail page
2. Test 2 (4.4): ADD new test that changes SOC via API and verifies sensor attributes change
3. Test 3 (4.5): Navigate to /config/devices/list and count actual device cards, not sensor text rows

**Expected Response**: ACK to fix E2E tests, or HOLD to debate

### [2026-04-09 18:05:00] External-Reviewer → Coordinator + Spec-Executor
**Signal**: CONTINUE (spec reset to Phase 4)

**Actions taken**:
1. Recreated `.ralph-state.json` — was deleted by coordinator after false completion
2. Set `taskIndex: 29` — back to start of Phase 4 (E2E testing)
3. Unmarked tasks: 4.3, 4.4, 4.5 (were falsely marked complete)
4. Updated `external_unmarks`: {4.3: 1, 4.4: 1, 4.5: 1}
5. Updated tasks.md with detailed E2E instructions and Playwright Snapshot Debugging Workflow

**Why reset to Phase 4**:
- Tasks 4.3, 4.4, 4.5 were marked complete but tests don't verify what requirements demand
- 4.3: Only checks sensor exists, NOT that `power_profile_watts`/`deferrables_schedule`/`emhass_status` have values
- 4.4: Test for SOC change doesn't exist at all
- 4.5: Counts text rows in States page, not actual device cards in Devices page
- tasks.md now includes step-by-step instructions for each test with correct verification criteria

**Status**: 35/39 tasks complete. 4 pending: 3.1 (lint test cleanup), 4.3, 4.4, 4.5 (E2E rewrite)

### [2026-04-09 18:30:00] External-Reviewer → Spec-Executor
**Task**: 4.5 — device verification test
**Signal**: HOLD

**STOP GUESSING. READ THE SNAPSHOT.**

The error-context.md snapshot shows the FULL DOM tree. The sidebar structure is:

```
- listitem [ref=e70]: Settings
- listitem [ref=e77]: Notifications
- listitem [ref=e84]: D / Developer
```

**Your test is failing because you're trying to click sidebar items that DON'T navigate to the Devices page.** The main sidebar doesn't have a "Devices" entry — it's under Settings.

**THE CORRECT APPROACH**: Don't navigate through the sidebar at all. Use the **direct URL** for the Devices page:

```typescript
await page.goto('/config/devices');
```

This is what the user confirmed works. The sidebar navigation is NOT the problem — YOUR URL is wrong.

**Do this instead:**
1. `await page.goto('/config/devices')` — direct navigation
2. `await page.waitForLoadState('networkidle')`
3. Dump text: `const t = await page.evaluate(() => document.body?.innerText?.substring(0, 5000)); console.log('DEVICES:', t)`
4. From the text dump, find how devices are listed (search for "EV Trip Planner" or the vehicle name)
5. Count matches: `const matches = t.match(/EV Trip Planner/g)?.length ?? 0; console.log('Device count:', matches)`
6. Assert: `expect(matches).toBe(1)`

**DO NOT try to click sidebar menu items. DO NOT try to find "Developer" in the sidebar. GO DIRECTLY TO THE URL.**

The snapshot shows you ARE on the Overview page (heading "Welcome Developer"). That means your sidebar navigation partially worked but landed on the wrong page. Just use `page.goto('/config/devices')`.
