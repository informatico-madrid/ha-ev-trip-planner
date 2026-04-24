# E2E Testing Guide — EV Trip Planner

This guide explains how to run End-to-End tests (Playwright) both **locally** and in the **CI pipeline**. The configuration is 100% compatible between both environments.

---

## Table of Contents

1. [How Tests Work](#how-tests-work)
2. [Prerequisites](#prerequisites)
3. [Local Execution — Option A (Docker Compose, recommended)](#option-a-docker-compose-recommended)
4. [Local Execution — Option B (manual hass)](#option-b-manual-hass-without-docker)
5. [CI Execution (GitHub Actions)](#ci-execution-github-actions)
6. [Test Structure](#test-structure)
7. [Users and Authentication](#users-and-authentication)
8. [Useful Commands](#useful-commands)
9. [Troubleshooting](#troubleshooting)

---

## How Tests Work

```
npm run test:e2e
       │
       ├─► auth.setup.ts (globalSetup — runs ONCE at start)
       │     ├─ Waits for HA to respond at http://localhost:8123
       │     ├─ Calls HA REST API to create user "dev/dev" (if not exists)
       │     ├─ Configures ev_trip_planner integration via Config Flow REST API
       │     │     vehicle_name = "test_vehicle"
       │     │     charging_sensor = "input_boolean.test_ev_charging"
       │     └─ Saves authenticated session to playwright/.auth/user.json
       │
       ├─► tests/e2e/*.spec.ts  (each test)
       │     ├─ Loads saved session (storageState)
       │     ├─ Navigates directly to /ev-trip-planner-test_vehicle
       │     ├─ Performs action (create/edit/delete trip...)
       │     └─ Cleans up created data
       │
       └─► globalTeardown.ts  (cleans up temporary files)
```

**Key points:**
- HA **must be running** before executing `npx playwright test`. The suite does NOT start HA.
- Authentication is done via **trusted_networks** (no login form, automatic bypass from 127.0.0.1).
- Integration is configured via REST API in `auth.setup.ts`, not via UI.
- Panel is registered in the sidebar with the name `test_vehicle`.
- Panel navigation uses the direct URL `/ev-trip-planner-test_vehicle`.

---

## Prerequisites

### All environments

```bash
# Node.js ≥ 18 (check)
node --version

# Install Node dependencies
npm install

# Install Chromium (only Chromium is needed)
npx playwright install chromium --with-deps
```

### Only for local execution (without Docker)

```bash
# Python 3.11-3.14
python3 --version

# Install Home Assistant
pip install homeassistant
```

### Only for Docker execution

```bash
# Docker + docker compose
docker --version
docker compose version
```

---

## Option A: Docker Compose (recommended)

This is the simplest and most reproducible way. The `docker-compose.yml` is already configured with:
- `trusted_networks` for login bypass from localhost.
- `input_boolean.test_ev_charging` required for Config Flow.
- Volume mounting `custom_components/ev_trip_planner` from the local repo.

### 1. Start Home Assistant

```bash
# From the repository root
docker compose up -d

# Check that HA is ready (wait ~30-60 seconds)
docker compose logs -f homeassistant
# Ctrl+C when you see: "Home Assistant is running"
```

### 2. Complete HA onboarding (first time only)

When HA starts for the first time in Docker, it needs the **initial onboarding** (create admin user). You have two options:

**Option A1 — Automatic onboarding via script:**
```bash
./scripts/ha-onboard.sh
```

**Option A2 — Manual onboarding via UI:**
1. Open http://localhost:8123 in the browser.
2. Create the user: name=`Developer`, username=`dev`, password=`dev`.
3. Accept all screens until reaching the dashboard.

> ⚠️ The `dev`/`dev` credentials are hardcoded in `auth.setup.ts`. If you use different credentials, edit that file.

### 3. Run tests

```bash
# Run all E2E tests
npx playwright test tests/e2e/ --workers=1

# Or with make
make test-e2e

# With visible browser (to see what it does)
make test-e2e-headed

# Single file
npx playwright test tests/e2e/create-trip.spec.ts

# Debug mode (pauses at each step)
make test-e2e-debug
```

### 4. Stop Home Assistant

```bash
docker compose down
```

---

## Option B: manual hass (without Docker)

Useful if you already have Python installed and prefer not to use Docker.

### 1. Install Home Assistant

```bash
pip install homeassistant
```

### 2. Prepare the configuration directory

```bash
# Create test config directory
mkdir -p /tmp/ha-e2e-config/custom_components

# Link test configuration
cp tests/ha-manual/configuration.yaml /tmp/ha-e2e-config/configuration.yaml

# Link the custom component
ln -sf $(pwd)/custom_components/ev_trip_planner \
       /tmp/ha-e2e-config/custom_components/ev_trip_planner
```

### 3. Start Home Assistant

```bash
nohup hass -c /tmp/ha-e2e-config > /tmp/ha-e2e.log 2>&1 &
echo "HA PID: $!"

# Wait for it to be ready (~30-60 seconds)
until curl -sf -o /dev/null -w "%{http_code}" http://localhost:8123/api/ | grep -qE "401|200"; do
  echo "Waiting for HA..."
  sleep 3
done
echo "HA ready!"
```

### 4. Complete onboarding (first time only)

```bash
# Automatic script
./scripts/ha-onboard.sh

# Or open http://localhost:8123 and create the dev/dev user manually
```

### 5. Run tests

```bash
npx playwright test tests/e2e/ --workers=1
```

### 6. Stop Home Assistant

```bash
kill $(cat /tmp/ha-pid.txt) 2>/dev/null
# or
pkill -f "hass -c /tmp/ha-e2e-config"
```

---

## CI Execution (GitHub Actions)

The `.github/workflows/playwright.yml` workflow reproduces exactly the steps of Option B:

1. Code checkout.
2. Install Node and dependencies (`npm install`, `npx playwright install chromium`).
3. Install `homeassistant` via pip.
4. Copy test configuration to `/tmp/ha-e2e-config/`.
5. Start `hass -c /tmp/ha-e2e-config` in background.
6. Wait for API to respond (`HTTP 401`).
7. Complete onboarding automatically via REST API.
8. Execute `npx playwright test tests/e2e/ --workers=1`.
9. Upload artifacts (`playwright-report/`, `test-results/`, HA logs).

**No difference** between local execution (Option B) and CI — they use the same configuration.

---

## Test Structure

```
tests/e2e/
  trips-helpers.ts              # Helpers: createTestTrip, deleteTestTrip, navigateToPanel
  create-trip.spec.ts           # US-1: Create punctual and recurring trips
  edit-trip.spec.ts             # US-2: Edit existing trip
  delete-trip.spec.ts           # US-3: Delete trip (confirm / cancel)
  pause-resume-trip.spec.ts     # US-4: Pause and resume recurring trip
  complete-cancel-trip.spec.ts  # US-5: Complete and cancel punctual trip
  trip-list-view.spec.ts        # US-6: List view, details, buttons by type
  form-validation.spec.ts       # US-7: Form fields, type change, options
```

### Panel URL

The test vehicle panel is registered at:
```
http://localhost:8123/ev-trip-planner-test_vehicle
```

Each test navigates directly to this URL (the authenticated session is in `storageState`).

### Selectors used

Tests use element IDs (`#trip-type`, `#trip-km`, etc.) and visible text:

| Element | Selector |
|---------|----------|
| Trip type | `page.locator('#trip-type')` |
| Distance | `page.locator('#trip-km')` |
| Energy | `page.locator('#trip-kwh')` |
| Description | `page.locator('#trip-description')` |
| Date/time | `page.locator('#trip-datetime')` |
| Day of week | `page.locator('#trip-day')` |
| Time (recurring) | `page.locator('#trip-time')` |
| Create button | `page.getByRole('button', { name: 'Create Trip' })` |
| Add button | `page.getByRole('button', { name: '+ Add Trip' })` |
| Save changes | `page.getByRole('button', { name: 'Save Changes' })` |
| Edit | `page.getByText('Edit')` |
| Delete | `page.locator('.delete-btn')` |
| Pause | `page.getByText('Pause')` |
| Complete | `page.getByText('Complete')` |

### Native dialogs

Delete/Pause/Complete/Cancel buttons use native browser `confirm()` and `alert()`. Tests handle them with:

```typescript
// Register handler BEFORE the action
const dialogPromise = setupDialogHandler(page, true);  // true = accept
await tripCard.getByText('Delete').click();
const msg = await dialogPromise;
```

---

## Users and Authentication

### Test user

| Field | Value |
|-------|-------|
| Name | Developer |
| Username | `dev` |
| Password | `dev` |

These credentials are hardcoded in `auth.setup.ts`. Change them if you use an HA with different credentials.

### trusted_networks

The `tests/ha-manual/configuration.yaml` configuration includes:

```yaml
homeassistant:
  auth_providers:
    - type: trusted_networks
      trusted_networks:
        - 127.0.0.1
        - 172.17.0.0/16
        - ::1
      allow_bypass_login: true
    - type: homeassistant
```

This allows the Playwright browser (from 127.0.0.1) to authenticate automatically without login form.

### Saved session

The session is saved in `playwright/.auth/user.json` during `globalSetup`. This file is in `.gitignore` and is regenerated on each execution.

---

## Useful Commands

```bash
# Run ALL E2E tests
make test-e2e

# With visible browser
make test-e2e-headed

# Interactive debug mode (opens Playwright Inspector)
make test-e2e-debug

# Single test file
npx playwright test tests/e2e/form-validation.spec.ts

# Single specific test (by name)
npx playwright test tests/e2e/ --grep "should create a new punctual trip"

# View HTML report (after a run)
npx playwright show-report

# Python tests (unit, without E2E)
make test

# All checks (Python + lint + mypy)
make check
```

---

## Troubleshooting

### HA does not start / tests fail with "connection refused"

```bash
# Check that HA is running
curl -s -o /dev/null -w "%{http_code}" http://localhost:8123/api/

# View HA logs
docker compose logs homeassistant   # if using Docker
tail -50 /tmp/ha-e2e.log            # if using manual hass
```

### "Integration already set up" or error in globalSetup

The `auth.setup.ts` detects if the integration is already configured and skips it. If there is a corrupt state:

```bash
# Docker: remove volumes and recreate
docker compose down -v
docker compose up -d

# hass manual: clean configuration
rm -rf /tmp/ha-e2e-config/.storage
```

### "trusted_networks" not working / login form appears

Make sure `configuration.yaml` has the correct configuration under `homeassistant:` (not at root level):

```yaml
# ✅ CORRECT
homeassistant:
  auth_providers:
    - type: trusted_networks
      ...

# ❌ INCORRECT (root level, does not work in modern HA)
auth_providers:
  - type: trusted_networks
    ...
```

### Lit not loading / blank panel

The panel uses `lit-bundle.js` served locally by HA. If the panel appears blank:

1. Open http://localhost:8123/ev-trip-planner/lit-bundle.js — it must return JS code.
2. If it returns 404, restart HA to register the static paths.

### Slow tests or timeouts

Tests have a 60-second timeout per test. If the system is slow:

```typescript
// In playwright.config.ts, increase the timeout
timeout: 120_000,
```

### "strict mode violation" — selector finds multiple elements

Some tests use `getByText('15')` which can match both date and kWh. In that case, scope to the trip card:

```typescript
const tripCard = page.locator('.trip-card', { hasText: 'My Trip' }).last();
await expect(tripCard.getByText('15 kWh')).toBeVisible();
```

---

## Environment Variables

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `HA_URL` | `http://localhost:8123` | Home Assistant URL |
| `CI` | (empty) | If `"true"`, enables retries and CI format |

To change the HA URL (for example, if you use a different port):

```bash
HA_URL=http://localhost:8124 npx playwright test tests/e2e/
```

> Note: `auth.setup.ts` uses the constant `HA_URL = 'http://localhost:8123'`. Edit that file if you need a different port permanently.
