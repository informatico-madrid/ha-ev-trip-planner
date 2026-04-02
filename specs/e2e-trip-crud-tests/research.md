# Research: E2E Trip CRUD Tests - Panel URL Authentication

## Executive Summary

Investigation of repeated 404 errors on panel URLs revealed the **root cause is navigation strategy, not authentication**. Home Assistant has two routing systems: React Router (which redirects to auth) and Custom Panels (which return 404 when unauthenticated). The correct approach is **sidebar navigation**, not direct URL access.

## Key Discovery: Two Routing Systems

Home Assistant uses **two separate frontend systems** with different authentication handling:

| System | URLs | Unauthenticated Behavior |
|--------|------|------------------------|
| React Router | `/`, `/config`, etc. | Redirects to `/auth/authorize` |
| Custom Panels | `/ev-trip-planner-{vehicle_id}` | Returns **404** (not redirect) |

### Why Panels Return 404

Custom panels are registered as **static file paths** via `panel_custom.async_register_panel()`:

```python
# panel.py lines 70-81
module_url = f"/{DOMAIN.replace('_', '-')}/panel.js?t={cache_bust}"
await panel_custom.async_register_panel(
    hass=hass,
    frontend_url_path=frontend_url_path,  # e.g., "ev-trip-planner-coche2"
    webcomponent_name=PANEL_COMPONENT_NAME,
    module_url=module_url,  # /ev-trip-planner/panel.js - STATIC PATH
    ...
)
```

The `module_url` (`/ev-trip-planner/panel.js`) is registered as a **static HTTP path** via `hass.http.register_static_path()`. Static paths bypass the React frontend's authentication middleware.

## Why storageState Alone is Insufficient

**Experiment results:**
1. Navigate to `/` without auth → redirects to `/auth/authorize` (login) ✓
2. Navigate to `/ev-trip-planner-coche2` without auth → **404** (no redirect!) ✗
3. Navigate to panel with storageState → page loads, **panel content doesn't render**

**Reason**: The panel's JavaScript needs a valid `hass` object from an **authenticated WebSocket connection**. StorageState cookies allow the browser to load the page and JS files, but without proper login flow, the panel initializes with an invalid `hass` context.

## Root Causes Identified

### 1. URL Case Mismatch
- `auth.setup.ts` transforms `vehicleName` to lowercase: `coche2`
- But `trips.page.ts` `DEFAULT_PANEL_URL` uses capitalized: `Coche2`
- Tests read from `panel-url.txt` (correct) but fallback uses wrong URL

### 2. Direct Navigation vs Sidebar Navigation

| Navigation Method | Behavior |
|-------------------|----------|
| `navigateViaSidebar()` | Clicks sidebar item, HA handles auth token automatically |
| `navigateDirect()` | Uses `page.goto()` which bypasses sidebar's auth mechanism |

**Key insight from HA E2E Testing Patterns**: "Never `page.goto('/panel-url')` - always use sidebar navigation."

### 3. Two Panel Registration Mechanisms

| File | Registration Type |
|------|-------------------|
| `panel_custom.py` (old) | Static: `/ev-trip-planner` (no vehicle suffix) |
| `panel.py` (current) | Dynamic: `/ev-trip-planner-{vehicle_id}` |

## Correct E2E Testing Approach

### Rule 1: Always Use Sidebar Navigation

```typescript
// WRONG - causes 404
await page.goto('/ev-trip-planner-coche2');

// CORRECT - sidebar handles auth
await page.getByRole('link', { name: /EV Trip Planner/i }).click();
```

### Rule 2: Save storageState AFTER Config Flow

```typescript
// auth.setup.ts must:
1. Login via UI (dev/dev credentials)
2. Complete Config Flow (installs integration, registers panel)
3. Navigate to panel to verify it works
4. ONLY THEN save storageState
await page.context().storageState({ path: 'user.json' });
```

### Rule 3: A 404 on Panel URL = Integration Not Installed

Not an auth problem. If 404:
1. Config Flow didn't complete successfully
2. Panel URL is wrong
3. Panel registration failed

## Findings from Codebase Analysis

### Panel Registration Flow

1. User completes Config Flow UI
2. `setup_entry()` calls `panel_module.async_register_panel()`
3. Panel registers at `/ev-trip-planner-{vehicle_id}`
4. Sidebar link appears in HA sidebar

### Key Files

| File | Purpose |
|------|---------|
| `panel.py` | Dynamic panel registration with vehicle_id suffix |
| `panel_custom.py` | Old static panel registration (legacy) |
| `__init__.py` | `setup_entry()` calls panel registration |
| `auth.setup.ts` | Login + Config Flow + storageState |
| `trips.page.ts` | `navigateViaSidebar()` vs `navigateDirect()` |

## Recommendations

### Immediate Fixes Required

1. **Use sidebar navigation in tests** - Replace `navigateDirect()` with `navigateViaSidebar()`
2. **Fix DEFAULT_PANEL_URL case** - Change to lowercase `coche2` to match auth.setup.ts
3. **Verify storageState is saved AFTER Config Flow** - Already fixed (added `storageState()` call)
4. **Run Config Flow before each test suite** - Tests should depend on auth.setup.ts

### Test Strategy

```typescript
// trips.spec.ts - Use sidebar navigation
test.beforeEach(async ({ page }) => {
  tripsPage = new TripsPage(page);
  tripsPage.setupDialogHandler();
  // Navigate via sidebar, NOT direct URL
  await tripsPage.navigateViaSidebar();
});
```

### Why US-1 Tests Pass

The 4 US-1 tests that pass do so because:
- `displays empty state when no trips exist` - Uses conditional logic that skips assertions when panel inaccessible
- The panel IS accessible via sidebar in auth.setup.ts run

### Why US-2+ Tests Fail

- US-2 tests use `navigateDirect()` which goes to wrong URL (case mismatch)
- Even with correct URL, direct navigation returns 404 (panels bypass auth middleware)
- Sidebar navigation is the only reliable method

## Feasibility Assessment

| Aspect | Assessment | Notes |
|--------|------------|-------|
| URL case fix | High | One-line change in DEFAULT_PANEL_URL |
| Sidebar navigation | High | Requires refactoring tests to use navigateViaSidebar() |
| storageState timing | High | Already fixed - saved after Config Flow |
| Full test suite pass | Medium | Requires all three fixes above |

## Conclusion

The 404 errors are NOT caused by authentication failures. They are caused by:

1. **Using direct URL navigation** (`page.goto()`) instead of sidebar navigation
2. **URL case mismatch** in DEFAULT_PANEL_URL

**Solution**: Replace `navigateDirect()` calls with `navigateViaSidebar()` in all tests, and fix the DEFAULT_PANEL_URL to use lowercase vehicle_id.

## References

- HA E2E Testing Patterns skill (`ha-e2e-testing`)
- `panel.py` - Panel registration using `panel_custom.async_register_panel`
- `config_flow.py` - Config Flow that triggers panel registration
- Experiment: Unauthenticated navigation to `/` vs `/ev-trip-planner-X`
