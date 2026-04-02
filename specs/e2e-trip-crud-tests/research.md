# Research: e2e-trip-crud-tests

## Executive Summary

Research for creating E2E Playwright tests that verify CRUD functionality of trips for a vehicle in the EV Trip Planner Home Assistant integration. The existing `auth.setup.ts` provides a working authentication and Config Flow setup that must be preserved. Key findings: Home Assistant requires UI-based integration installation (not just login), Shadow DOM requires web-first locators, and trip CRUD tests should cover create, read, update, delete, pause/resume, and complete/cancel operations.

## External Research

### Best Practices for Home Assistant E2E Testing

#### 1. Authentication & Setup Pattern

**Critical Rule:** Home Assistant integrations require full UI-based setup, not just login.

From `auth.setup.ts` (working implementation):
- Login via UI at `/login` with credentials `dev/dev`
- Navigate to Settings > Devices & Services
- Install integration via "Add Integration" button
- Complete Config Flow steps (vehicle_name, sensors, EMHASS, presence sensors)
- Save `storageState` to `playwright/.auth/user.json`

**Key Finding:** The existing `auth.setup.ts` performs login + Config Flow + saves storageState. This is the CORRECT pattern and must NOT be modified.

#### 2. Shadow DOM Handling

Home Assistant uses Lit Elements with Shadow DOM. Critical rules:

- **ALWAYS use web-first locators:** `getByRole()`, `getByText()`, `getByLabel()`
- **NEVER use CSS selectors or XPath** - they break with Shadow DOM
- **NEVER use `page.evaluate()` to traverse Shadow DOM manually**
- **NEVER use `waitForTimeout()`** - use `await expect()` with auto-waiting

```typescript
// CORRECT - traverses Shadow DOM automatically
await page.getByRole('button', { name: /Save/i }).click()

// WRONG - CSS selector inside Shadow DOM
await page.click('.clase-css-random')
```

#### 3. Trip CRUD Testing Patterns

Based on requirements from 021 spec:

**Create Trip Flow:**
1. Click "+ Agregar Viaje" / "Add Trip" button
2. Modal/form opens with trip type selector (Recurrente/Puntual)
3. Fill required fields (day, time for recurring; date/time for punctual)
4. Submit and verify new trip appears in list

**Edit Trip Flow:**
1. Click "Editar" on existing trip
2. Form pre-fills with existing data
3. Modify and submit
4. Verify updated values displayed

**Delete Trip Flow:**
1. Click "Eliminar" button
2. Confirmation dialog appears
3. Confirm or cancel
4. Verify trip removed/present in list

**Pause/Resume Flow (Recurring):**
1. Click "Pausar" on active recurring trip
2. Verify trip shows as inactive/paused
3. Click "Reanudar" to reactivate
4. Verify trip shows as active

**Complete/Cancel Flow (Punctual):**
1. Click "Completar" on punctual trip
2. Verify trip marked complete and removed from active list
3. Click "Cancelar" to cancel
4. Verify trip removed from list

#### 4. Critical Anti-Patterns (Blacklist)

| PROHIBITED | Alternative |
|------------|-------------|
| `waitForTimeout()` | `await expect()` with timeout |
| CSS/XPath selectors | `getByRole()`, `getByText()`, `getByLabel()` |
| Hardcoded panel URLs | Navigate via sidebar click |
| Manual Shadow DOM traversal | Web-first locators |
| Login code in test files | Use `storageState` from auth.setup |

#### 5. Debugging & Verification Tools

- **Trace Viewer:** `npx playwright show-trace playwright/trace.zip` - better than screenshots
- **DOM Inspection:** Use `page.snapshot()` or browser DevTools to understand real element roles
- **Selector Validation:** Verify `getByRole` matches actual DOM structure before using

## Codebase Analysis

### Existing Test Infrastructure

```
tests/e2e/
├── auth.setup.ts          # Authentication and Config Flow setup (WORKS)
├── pages/
│   ├── ev-trip-planner.page.ts
│   ├── ha-login.page.ts
│   └── index.ts
├── skills/
│   ├── ha-core-frontend.skill.md
│   ├── e2e-verify-integration.skill.md
│   └── selector-map.skill.md
├── playwright-report/
├── playwright-results.xml
├── test-helpers.ts
└── package-lock.json
```

### auth.setup.ts Analysis

**Location:** `tests/e2e/auth.setup.ts`

**What it does (confirmed working):**
1. Reads server info from `playwright/.auth/server-info.json`
2. Navigates to HA login page
3. Checks for sidebar (indicates auth state)
4. If not authenticated: fills `dev/dev` credentials via `getByRole`
5. Navigates: Settings > Devices & Services > Add Integration
6. Searches for "EV Trip Planner" and installs it
7. Completes Config Flow:
   - Step 1: Vehicle name (e.g., "Coche2")
   - Step 2: Sensors (battery_capacity=75.0, charging_power=11.0, consumption=0.17, safety_margin=15)
   - Step 3: EMHASS (optional, submit skip)
   - Step 4: Presence sensors (auto-selected by backend)
8. Saves storageState to `playwright/.auth/user.json`
9. Saves panel URL to `playwright/.auth/panel-url.txt`

**CRITICAL: This file works and must NOT be modified.**

### Trip Panel Implementation

**Panel URL Pattern:** `/ev-trip-planner-{vehicle_name}` (e.g., `/ev-trip-planner-Coche2`)

**UI Elements to interact with:**
- "+ Agregar Viaje" / "Add Trip" button
- Trip type selector (Recurrente/Puntual)
- Day selector (for recurring)
- Time/date fields
- Edit ("Editar") button per trip
- Delete ("Eliminar") button per trip
- Pause ("Pausar") button for active recurring
- Resume ("Reanudar") button for paused recurring
- Complete ("Completar") button for punctual
- Cancel ("Cancelar") button for punctual

### Dependencies

- Playwright with `@playwright/test` framework
- Storage state for auth persistence in `.auth/user.json`
- Server info read from `.auth/server-info.json`
- EV Trip Planner integration installed via Config Flow
- Vehicle "Coche2" configured with sensors

### Constraints

1. **auth.setup.ts must NOT be modified** - It works perfectly
2. **Tests must use storageState** - No login code in test files
3. **Must use web-first locators** - getByRole, getByText, getByLabel
4. **No hardcoded URLs** - Navigate via sidebar
5. **No waitForTimeout** - Use expect() with auto-waiting

## Related Specs

| Spec | Relevance | Relationship | May Need Update |
|------|-----------|--------------|-----------------|
| 021-e2e-trip-crud-panel-tests | High | Same goal, broader scope (full panel loading + CRUD) | 021 test strategy mentions "Static Code Analysis" - current spec should focus ONLY on browser-based E2E |
| 019-panel-vehicle-crud | Medium | Vehicle CRUD patterns | Similar testing approach |
| 020-fix-panel-trips-sensors | Low | Trip panel fixes | May inform trip display format |

## Quality Commands

| Type | Command | Source |
|------|---------|--------|
| Run auth setup | `npx playwright test auth.setup.ts --reporter=list` | ha-e2e-testing skill |
| Run trip CRUD tests | `npx playwright test tests/e2e/trips.spec.ts` | ha-e2e-testing skill |
| Check session | `node scripts/check_session.js` | ha-e2e-testing skill |
| Get HA URL | `node scripts/get_ha_url.js` | ha-e2e-testing skill |

## Feasibility Assessment

| Aspect | Assessment | Notes |
|--------|------------|-------|
| Technical Feasibility | High | auth.setup.ts works, HA E2E patterns well-documented |
| Test Reliability | Medium | HA JS caching issues - need timestamp verification |
| Scope | Medium | 7 user stories + 11 functional requirements |
| Browser Support | Medium | 021 spec targets Chrome/Firefox/Safari, may need verification |

## Recommendations for Requirements

1. **Focus on browser-based E2E only** - Skip static code analysis approach from 021
2. **Use auth.setup.ts as-is** - Do not modify, just reuse
3. **Test each CRUD operation separately** - Create, Read, Update, Delete, Pause/Resume, Complete/Cancel
4. **Verify Shadow DOM selectors before implementing** - Use browser_snapshot to confirm element roles
5. **Set realistic timeouts** - HA frontend hydration is async
6. **Consider cross-browser testing** - Chrome primary, verify Firefox/Safari compatibility

## Open Questions

1. Should the spec target all 3 browsers (Chrome/Firefox/Safari) or just Chrome initially?
2. Is the "Coche2" vehicle name fixed, or should tests be parameterized?
3. Should tests clean up created trips after each test, or use isolated vehicles?
4. What is the expected format for trip display cards in the UI?

## Sources

- ha-e2e-testing skill (`/home/malka/.claude/skills/ha-e2e-testing`)
- e2e-testing skill
- tests/e2e/auth.setup.ts (working implementation)
- tests/e2e/pages/ev-trip-planner.page.ts
- tests/e2e/pages/ha-login.page.ts
- tests/e2e/test-helpers.ts
- specs/021-e2e-trip-crud-panel-tests/requirements.md
