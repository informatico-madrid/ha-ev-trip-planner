# Research: e2e-ev-trip-planner

## Executive Summary

The codebase has Playwright + hass-taste-test infrastructure already in place, but the actual `tests/e2e/` directory and `playwright.config.ts` are missing. The EV Trip Planner is a **native HA panel** (not Lovelace), requiring direct URL/sidebar navigation instead of hass-taste-test's Lovelace card APIs. Shadow DOM piercing uses the `>>` combinator. The Config Flow is required to install the integration.

## External Research

### hass-taste-test Architecture
- Creates ephemeral HA in temp dirs with Python venv, auto-installs latest HA from PyPI
- Uses lockfile to coordinate parallel instances on unique ports (starts at 8130)
- Handles full onboarding: creates `dev/dev` user, generates auth tokens, establishes WebSocket
- `PlaywrightBrowser` class manages browser lifecycle (launch once, reuse for multiple pages)
- Designed for Lovelace card testing — EV Trip Planner is a **native HA panel** (not Lovelace)

### Shadow DOM Patterns
- `>>` pierce combinator: `page.locator('ev-trip-planner-panel >> .add-trip-btn').click()`
- Built-in web-first locators (`getByRole`, `getByText`, `getByLabel`) pierce Shadow DOM automatically in light DOM contexts
- `getDiffable-html.js` (from hass-taste-test) traverses shadow root automatically when generating HTML diffs

### Custom Component Testing
- `customComponents` option symlinks directories into HA's `custom_components/`
- Panel URL: `/ev-trip-planner-{vehicle_id}` where vehicle_id is HA-generated UUID
- Config Flow is **required** to install the integration — `global.setup.ts` does NOT do this
- Need `auth.setup.ts` to run Config Flow UI and save `storageState`
- **Critical unknown**: After Config Flow, how to extract vehicle_id. Recommended: navigate via sidebar link.

## Codebase Analysis

### Existing Patterns
- GitHub Actions workflow at `.github/workflows/playwright.yml` runs `npx playwright test tests/e2e/`
- `tests/global.setup.ts` starts ephemeral HA, copies panel.js to www/, saves server-info.json
- `tests/global.teardown.ts` cleans up ephemeral HA
- `@playwright/test@^1.58.2` and `hass-taste-test@^0.2.7` already in package.json

### Gap Analysis
| Item | Status |
|------|--------|
| `tests/e2e/` directory | **MISSING** — workflow references it but dir doesn't exist |
| `playwright.config.ts` | **MISSING** — no Playwright config file |
| `auth.setup.ts` | **MISSING** — Config Flow not automated |
| `EVTripPlannerPage` POM | **MISSING** — needs to be created |
| `ConfigFlowPage` POM | **MISSING** — needs to be created |
| `vehicle.spec.ts` | **MISSING** — needs to be created |
| `trip.spec.ts` | **MISSING** — needs to be created |

### EV Trip Planner Panel Structure
- Lit web component at `custom_components/ev_trip_planner/frontend/panel.js`
- Class: `EVTripPlannerPanel extends LitElement`
- Custom element: `ev-trip-planner-panel`
- Panel URL: `/ev-trip-planner-{vehicle_id}`
- Key selectors (inside Shadow DOM):
  - `.add-trip-btn` — Add trip button
  - `.trip-form-overlay` / `.trip-form-container` — Modal form
  - `.trips-list` — Trips container
  - `.trip-card[data-trip-id]` — Individual trip
  - `#trip-name`, `#trip-type`, `#trip-time` — Form fields

### Config Flow Fields (needs verification)
- From `config_flow.py` and `strings.json`
- Expected fields: `vehicle_name`, entity selector for presence detection
- Post-Config Flow: HA adds panel to sidebar

## Related Specs

No directly related specs found in `./specs/`.

## Quality Commands

| Type | Command | Source |
|------|---------|--------|
| E2E tests | `npx playwright test tests/e2e/` | package.json |
| UI tests | `npx playwright test tests/e2e/card-loading.test.js` | package.json |
| Python tests | `hass-taste-test && node --experimental-vm-modules node_modules/jest/bin/jest.js` | package.json |

## Feasibility Assessment

| Aspect | Assessment | Notes |
|--------|------------|-------|
| Infrastructure | **Medium** | hass-taste-test + Playwright already wired, but gaps in config + test files |
| Shadow DOM testing | **Low risk** | `>>` pierce combinator is well-documented |
| Config Flow automation | **Medium risk** | UI-based, may need trial-and-error for selectors |
| Vehicle ID extraction | **Medium risk** | Sidebar nav avoids the problem |
| CI integration | **Low risk** | GitHub Actions workflow already exists |

## Recommendations for Requirements

1. **Create `playwright.config.ts`** with globalSetup/globalTeardown references
2. **Create `tests/e2e/auth.setup.ts`** to run Config Flow and save storageState
3. **Use sidebar navigation** (not direct URL) for robustness
4. **Use POM pattern** with page classes for Config Flow and EV Trip Planner panel
5. **MVP tests**: `vehicle.spec.ts` (create vehicle + view panel) and `trip.spec.ts` (create trip + verify listing)

## Open Questions

1. **Config Flow field names**: What are exact field names in EV Trip Planner Config Flow? (Need to check `strings.json` and `config_flow.py`)
2. **Sidebar link text**: Does HA show "EV Trip Planner" or the vehicle name in the sidebar after Config Flow?
3. **Post-Config Flow**: Does HA require a page reload for the panel to appear in the sidebar?
4. **Entity selector**: What entities should be available in ephemeral HA for presence detection?

## Sources

- hass-taste-test GitHub: https://github.com/rianadon/hass-taste-test
- hass-taste-test npm: https://www.npmjs.com/package/hass-taste-test
- Playwright Shadow DOM docs: https://playwright.dev/docs/locators#shadow-dsu
- Lit web components: https://lit.dev/
- Home Assistant panel_custom: https://www.home-assistant.io/cookbook/custom-panel/
- Project files: `tests/global.setup.ts`, `tests/global.teardown.ts`, `.github/workflows/playwright.yml`
