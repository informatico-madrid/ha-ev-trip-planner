# Research: E2E Trip CRUD Tests — Investigation Plan

## ⚠️ Methodology Note

This document distinguishes between **confirmed facts** (verified by reading actual code or running tests) and **hypotheses** (working theories pending confirmation). Nothing in the Hypotheses section should be treated as a fix until the corresponding Investigation Step confirms it.

---

## Confirmed Facts

### F1 — Task 3.6 result: 2 passed, 30 failed
Error reported: `ReferenceError: TripsPage is not defined` in `page.evaluate()` callbacks.
Source: `.progress.md` Task 3.6 FAIL entry.

### F2 — Current `trips.page.ts` already passes constants as arguments to `page.evaluate()`
Reading `trips.page.ts` (SHA: 55b569f7bfd03076ac70390f674442ceecb45039) confirms that `getTripCount()`, `isTripPaused()`, and all `callXxxService()` methods pass class constants as serialized arguments `{ PANEL_SELECTOR, TRIP_CARD_CLASS, ... }`, NOT via `TripsPage.CONSTANT` inside the callback.
**Implication:** The `ReferenceError` from Task 3.6 may be stale — the code may have already been fixed AFTER Task 3.6 ran. Needs confirmation by running tests again.

### F3 — `auth.setup.ts` saves `storageState` AFTER Config Flow + panel navigation
`auth.setup.ts` (SHA: 60a774dcd6fdebb208a8518867a318397dcfc421): login → Config Flow 4 steps → `page.goto(panelUrl)` → `page.context().storageState()`. Timing is correct.

### F4 — `DEFAULT_PANEL_URL` already uses lowercase `coche2`
`trips.page.ts` line: `static readonly DEFAULT_PANEL_URL = 'http://127.0.0.1:8123/ev-trip-planner-coche2'`
The previously documented "case mismatch" hypothesis (uppercase `Coche2`) appears already resolved in the current code. Needs confirmation.

### F5 — HA Custom Panels return 404 on direct navigation without active WebSocket session
`panel_custom.async_register_panel()` registers panels as static file paths that bypass React Router's auth middleware. `page.goto('/ev-trip-planner-coche2')` without an active authenticated WebSocket returns 404.
Source: `research.md` previous version + codebase analysis of `panel.py`.

### F6 — `auth.setup.ts` contains multiple hardcoded `waitForTimeout()` calls
`waitForTimeout(3000)` for CI Shadow DOM rendering, `waitForTimeout(2000)` between Config Flow steps, `waitForTimeout(1000)` for form redisplay checks. These are potential sources of flakiness in slow CI environments.

### F7 — `trips.spec.ts` uses `async` inside `page.evaluate()` in service call methods
All `callXxxService()` methods use `await this.page.evaluate(async ({ ... }) => { ... })`. Playwright supports async callbacks in `evaluate`, but if `panel.hass` is not available (panel not rendered), these throw `'Cannot call service: panel or hass not available'` — not a `ReferenceError`. This distinguishes this failure mode from F1.

---

## Hypotheses (unconfirmed — pending investigation steps)

### H1 — The `ReferenceError` from Task 3.6 is stale
**Theory:** The code was refactored AFTER the Task 3.6 checkpoint. The current `trips.page.ts` already has the fix. The real current failure mode is different.
**Confirmation step:** Step 1 — run `auth.setup.ts` + `trips.spec.ts` and capture the actual current error.

### H2 — `navigateDirect()` in US-2+ `beforeEach` is the real blocker
**Theory:** US-1 tests pass because they use `navigateViaSidebar()`. US-2+ tests use `navigateDirect()` → panel returns 404 → `panel.hass` is null → service calls throw.
**Confirmation step:** Step 3 — read `trips.spec.ts` `beforeEach` blocks for each US suite.

### H3 — `callXxxService()` fails because `panel.hass` is null (panel not rendered via direct URL)
**Theory:** When navigation is via direct URL (H2), the panel web component loads but HA's WebSocket is not initialized, so `panel.hass` is null. `callTripCreateService()` and similar methods then throw `'Cannot call service: panel or hass not available'`.
**Confirmation step:** Step 1 actual error output + Step 3.

### H4 — `waitForTimeout()` in `auth.setup.ts` causes intermittent failures in CI
**Theory:** Hardcoded timeouts are too short on slow CI machines or too long locally. Replacing with `waitFor({ state: 'visible' })` on specific elements would be more robust.
**Confirmation step:** Step 4 — verify if auth.setup.ts passes consistently or flakes.

### H5 — `navigateViaSidebar()` requires panel to already be registered (Config Flow must have run)
**Theory:** If `auth.setup.ts` fails silently mid-Config-Flow, the panel is never registered, sidebar link never appears, and `navigateViaSidebar()` clicks nothing or the wrong element.
**Confirmation step:** Step 2 — verify `panel-url.txt` exists and contains a valid URL after auth setup runs.

---

## External Sources — Proven Patterns

These patterns from the community have been validated by other developers in similar setups:

| Source | Pattern | Applicability |
|--------|---------|--------------|
| `rianadon/hass-taste-test` | Uses real browser + full login flow for all panel interactions. No `page.goto()` to panel URLs directly. | Directly applicable — this project uses `hass-taste-test`. |
| Playwright docs — `page.evaluate()` serialization | Functions passed to `evaluate` are serialized as strings. No closure access. All external values must be passed as JSON-serializable arguments. | F2 confirms this is already handled correctly in current code. |
| Playwright community — `storageState` timing | `storageState` must be saved AFTER the full authenticated session is established, including any post-login redirects. Saving too early causes "second test asks for login" flakiness. | F3 confirms this is already handled correctly. |
| HA Community — Shadow DOM inputs | `page.locator('input[name="..."]').click()` + `.type({ delay: 50 })` is the reliable pattern for Shadow DOM form fields inside HA config flows. `getByRole('textbox')` may not work inside Shadow DOM. | Already applied in `auth.setup.ts`. |

---

## Investigation Steps

Execute in order. Each step produces evidence that feeds the next.

### Step 1 — Get the actual current error (FIRST PRIORITY)
**Goal:** Confirm or invalidate H1. Determine the real current failure mode.
**Action:** Run `npx playwright test tests/e2e/trips.spec.ts` (after `auth.setup.ts`) and capture full output including stack traces.
**Expected outputs:**
- If still `ReferenceError: TripsPage is not defined` → F2 is wrong, refactor is incomplete somewhere
- If `Cannot call service: panel or hass not available` → H3 confirmed, H2 likely confirmed
- If 404 errors → H2 confirmed directly
- If different error → new hypothesis needed
**Success criterion:** We know the exact error type and which test/method triggers it.

### Step 2 — Verify auth.setup.ts output artifacts
**Goal:** Confirm H5 — that Config Flow completed and panel was registered.
**Action:** After running `auth.setup.ts`, check:
- Does `playwright/.auth/panel-url.txt` exist?
- Does `playwright/.auth/user.json` exist and contain valid cookies?
- Does `playwright/.auth/server-info.json` exist?
- Is the URL in `panel-url.txt` lowercase and matching `DEFAULT_PANEL_URL`?
**Success criterion:** All three files exist with valid content. F4 confirmed or refuted.

### Step 3 — Trace navigation strategy per US suite
**Goal:** Confirm H2 — identify which suites use `navigateDirect()` vs `navigateViaSidebar()`.
**Action:** Read `trips.spec.ts` `beforeEach` blocks for each `describe` block (US-1 through US-6).
**Expected output:** A table showing which US uses which navigation method.
**Success criterion:** We know exactly which tests are affected by direct-URL navigation.

### Step 4 — Verify auth.setup.ts stability
**Goal:** Confirm or invalidate H4 — flakiness from hardcoded timeouts.
**Action:** Run `auth.setup.ts` three times in sequence. Check if it passes consistently.
**Success criterion:** 3/3 passes = stable. Any failure = investigate which `waitForTimeout` step failed.

### Step 5 — Formulate fixes based on Steps 1-4 evidence
**Goal:** With confirmed data, propose concrete diffs.
**Action:** Write the minimal set of changes to `trips.spec.ts` (and possibly `trips.page.ts`) needed to fix the confirmed issues.
**Important:** Do NOT change `auth.setup.ts` unless Step 4 reveals a concrete failure there.
**Success criterion:** Proposed diffs reviewed and approved before applying.

### Step 6 — Apply fixes and run full test suite
**Goal:** Confirm that the fixes work.
**Action:** Apply approved diffs, run `npx playwright test` (full suite including `auth.setup.ts` as dependency).
**Success criterion:** 32/32 tests pass. Or if partial: understand which tests still fail and why.

---

## Key Files Reference

| File | SHA (current) | Notes |
|------|--------------|-------|
| `tests/e2e/auth.setup.ts` | 60a774dcd6fdebb208a8518867a318397dcfc421 | Pre-existing. Do not modify unless Step 4 shows concrete failure. |
| `tests/global.setup.ts` | 5f11a856095e8075dd74e4252c9b5096427ff0a9 | Pre-existing. Starts ephemeral HA server. |
| `tests/e2e/pages/trips.page.ts` | 55b569f7bfd03076ac70390f674442ceecb45039 | Created by agent. Already has correct `evaluate` argument passing. |
| `tests/e2e/trips.spec.ts` | efd4f1e195d44af9102270246fcc8e8943cee40e | Created by agent. `beforeEach` navigation strategy is the primary suspect. |
| `playwright.config.ts` | 03f470f75460aa7b9ffd53c6b1c7c700fa1a83c9 | Pre-existing. Do not modify. |

---

## Previous Research (preserved)

The following sections from the original `research.md` are preserved as historical context. The conclusions have been reclassified above as confirmed facts (F5) or hypotheses pending re-verification (H2, H3).

### Original: Two Routing Systems Discovery

Home Assistant uses **two separate frontend systems** with different authentication handling:

| System | URLs | Unauthenticated Behavior |
|--------|------|--------------------------|
| React Router | `/`, `/config`, etc. | Redirects to `/auth/authorize` |
| Custom Panels | `/ev-trip-planner-{vehicle_id}` | Returns **404** (not redirect) |

Custom panels are registered via `panel_custom.async_register_panel()` as static file paths that bypass React Router's authentication middleware. This is **confirmed fact F5**.

### Original: storageState Alone is Insufficient

The panel's JavaScript needs a valid `hass` object from an authenticated WebSocket connection. StorageState cookies allow the browser to load the page and JS files, but without proper login flow, the panel initializes with an invalid `hass` context. This explains why `callXxxService()` fails with `panel.hass` null — see H3.

### Original: Panel Registration Flow

1. User completes Config Flow UI
2. `setup_entry()` calls `panel_module.async_register_panel()`
3. Panel registers at `/ev-trip-planner-{vehicle_id}`
4. Sidebar link appears in HA sidebar
