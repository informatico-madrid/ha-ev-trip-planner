# E2E Tests — EV Trip Planner

> 📖 **Guía completa:** [`_ai/TESTING_E2E.md`](../../_ai/TESTING_E2E.md)

Tests end-to-end con Playwright que verifican el flujo completo de CRUD de viajes
(crear, editar, eliminar) y operaciones de ciclo de vida (pausar, reanudar, completar, cancelar).

## ⚠️ NUNCA USAR DOCKER PARA E2E

> E2E usa `hass` directo desde Python venv. **Staging usa Docker.** Son entornos completamente separados.
> Ver [`docs/staging-vs-e2e-separation.md`](../../docs/staging-vs-e2e-separation.md).

## Ejecución rápida

> ⚠️ **NO se usa Docker para E2E.** El método actual es `hass` directo via `scripts/run-e2e.sh`.

```bash
# 1. Arrancar HA + ejecutar E2E (todo automático — método actual):
make e2e

# 2. Debug mode:
make e2e-debug
```

Ver [`_ai/TESTING_E2E.md`](../../_ai/TESTING_E2E.md) para instrucciones completas, troubleshooting y detalles de configuración.

## Estructura

```
tests/e2e/
  trips-helpers.ts              # Helpers compartidos: createTestTrip, deleteTestTrip, navigateToPanel
  create-trip.spec.ts           # US-1: Crear viaje puntual y recurrente
  edit-trip.spec.ts             # US-2: Editar viaje existente
  delete-trip.spec.ts           # US-3: Eliminar viaje (confirmar / cancelar)
  pause-resume-trip.spec.ts     # US-4: Pausar y reanudar viaje recurrente
  complete-cancel-trip.spec.ts  # US-5: Completar y cancelar viaje puntual
  trip-list-view.spec.ts        # US-6: Vista lista, detalles, botones por tipo
  form-validation.spec.ts       # US-7: Campos del formulario, cambio de tipo, opciones
```

## Cobertura de User Stories

| User Story | Fichero | Escenarios |
|------------|---------|-----------|
| US-1: Crear viaje | `create-trip.spec.ts` | Puntual, Recurrente |
| US-2: Editar viaje | `edit-trip.spec.ts` | Recurrente, Puntual |
| US-3: Eliminar viaje | `delete-trip.spec.ts` | Confirmar, Cancelar diálogo |
| US-4: Pausar/Reanudar | `pause-resume-trip.spec.ts` | Pausar, Reanudar |
| US-5: Completar/Cancelar | `complete-cancel-trip.spec.ts` | Completar, Cancelar, Descartar diálogo |
| US-6: Vista lista | `trip-list-view.spec.ts` | Cabecera, botón Agregar, detalles, botones por tipo |
| US-7: Validación formulario | `form-validation.spec.ts` | Campos por tipo, cambio tipo, opciones día |

## Patrón de navegación

El panel se accede directamente por URL (la sesión autenticada se carga desde `storageState`):

```typescript
// navigateToPanel() en trips-helpers.ts
await page.goto('/ev-trip-planner-test_vehicle');
await page.waitForURL(/\/ev-trip-planner-/, { timeout: 30_000 });
await page.getByRole('button', { name: '+ Agregar Viaje' }).waitFor({ state: 'visible' });
```

## Selectores

Los tests usan IDs de elemento (auto-piercing de Shadow DOM):

```typescript
page.locator('#trip-type')       // selector tipo viaje
page.locator('#trip-km')         // distancia km
page.locator('#trip-kwh')        // energía kWh
page.locator('#trip-description') // descripción
page.locator('#trip-datetime')   // fecha/hora (puntual)
page.locator('#trip-day')        // día semana (recurrente, 0=Domingo..6=Sábado)
page.locator('#trip-time')       // hora (recurrente)
```

## Diálogos nativos

Las acciones destructivas usan `confirm()` y `alert()` del navegador:

```typescript
// SIEMPRE registrar el handler ANTES de la acción
const dialogPromise = setupDialogHandler(page, true); // true = aceptar
await tripCard.getByText('Eliminar').click();
const msg = await dialogPromise;
```

## Configuración HA

> **NOTA**: E2E usa `hass` directo (sin Docker). La configuración está en `tests/ha-manual/configuration.yaml`.

`tests/ha-manual/configuration.yaml` debe incluir:

```yaml
homeassistant:
  auth_providers:
    - type: trusted_networks
      trusted_networks: [127.0.0.1, 172.17.0.0/16]
      allow_bypass_login: true
    - type: homeassistant

input_boolean:
  test_ev_charging:         # Requerido por el Config Flow (paso de presencia)
    name: "EV Charging Test"
```


End-to-end smoke tests for the EV Trip Planner Home Assistant custom component. Tests verify the complete CRUD workflow (Create, Edit, Delete) and lifecycle operations (Pause, Resume, Complete, Cancel) by simulating real user interactions with the panel UI.

## Test Structure

```
tests/e2e/
  README.md                       # This file
  trips-helpers.ts                # Shared helper functions (createTestTrip, deleteTestTrip, navigateToPanel, etc.)
  create-trip.spec.ts             # US-1: Create puntual and recurrente trips
  edit-trip.spec.ts               # US-2: Edit existing trips (recurrente and puntual)
  delete-trip.spec.ts             # US-3: Delete trip with confirmation dialog + cancel deletion
  pause-resume-trip.spec.ts       # US-4: Pause and resume recurring trips
  complete-cancel-trip.spec.ts    # US-5: Complete and cancel punctual trips
  trip-list-view.spec.ts          # US-6: Panel view, trip details, action buttons
  form-validation.spec.ts         # US-7: Form fields, trip type switching, day options
```

## User Story Coverage

| User Story | Test File | Scenarios |
|------------|-----------|-----------|
| US-1: Create Trip | `create-trip.spec.ts` | Create puntual trip, Create recurrente trip |
| US-2: Edit Trip | `edit-trip.spec.ts` | Edit recurrente trip, Edit puntual trip |
| US-3: Delete Trip | `delete-trip.spec.ts` | Delete trip (confirm), Cancel deletion (dismiss) |
| US-4: Pause/Resume | `pause-resume-trip.spec.ts` | Pause recurring, Resume paused |
| US-5: Complete/Cancel | `complete-cancel-trip.spec.ts` | Complete puntual, Cancel puntual, Dismiss complete |
| US-6: View Trips | `trip-list-view.spec.ts` | Panel header, Agregar button, Trip details, Type badges, Action buttons per type |
| US-7: Form Validation | `form-validation.spec.ts` | Default fields, Puntual fields, Type switching, Close form, Day options, Type options |

## Test Files

### create-trip.spec.ts (US-1)

Verifies that users can create a new puntual (one-time) trip with valid data.

**Flow:**
1. Navigate to Home Assistant home page via `page.goto('/')` + `page.waitForURL('/home')`
2. Navigate to EV Trip Planner panel via sidebar click (NOT direct URL)
3. Click "+ Agregar Viaje" button
4. Select trip type "puntual" via combobox
5. Fill form fields: datetime-local, km, kwh, description
6. Submit via "Crear Viaje" button
7. Assert trip card appears with correct values
8. Clean up: delete the created trip

### edit-trip.spec.ts (US-2)

Verifies the edit flow for an existing recurrente (recurring) trip.

**Flow:**
1. Navigate to Home Assistant home page via `page.goto('/')` + `page.waitForURL('/home')`
2. Navigate to EV Trip Planner panel via sidebar click
3. Create a recurrente trip with initial values (km=30, kwh=10)
4. Click edit button (pencil icon) on trip card
5. Modify km from 30 to 35 and update description
6. Submit via "Guardar Cambios" button
7. Assert trip card shows updated values
8. Clean up: delete the test trip

### delete-trip.spec.ts (US-3)

Verifies the deletion flow with confirmation dialog.

**Flow:**
1. Navigate to Home Assistant home page via `page.goto('/')` + `page.waitForURL('/home')`
2. Navigate to EV Trip Planner panel via sidebar click
3. Create a puntual trip with known data
4. Set up dialog handler for confirmation (expects exact text: `¿Estás seguro de que quieres eliminar este viaje?`)
5. Click delete button (trash icon) on trip card
6. Assert trip card is no longer visible

## Test Values

| Test | Trip Type | Datetime | km | kwh | Description |
|------|-----------|----------|----|-----|-------------|
| create-trip.spec.ts | puntual | 2026-04-15T08:30 | 50 | 15 | Test Commute |
| edit-trip.spec.ts | recurrente | 2026-04-07T09:00 | 30 (initial) / 35 (edited) | 10 | Recurrente Test Trip / Updated Test Route |
| delete-trip.spec.ts | puntual | 2026-04-08T10:00 | 20 | 5 | Delete Test Trip |

## Navigation Pattern

HA is a SPA (Single Page Application). Tests follow strict navigation rules:

1. **Entry point**: `page.goto('/')` followed by `page.waitForURL('/home')` — the ONLY allowed entry point
2. **Panel navigation**: Sidebar click via `page.getByRole('link', { name: 'EV Trip Planner' }).click()`
3. **Wait for panel**: `page.waitForURL(/\/ev_trip_planner\/)`

**FORBIDDEN patterns:**
- `page.goto('/login')` — login form is bypassed via trusted_networks
- `page.goto('/ev_trip_planner')` — direct panel URL is forbidden (SPA navigation only)
- `page.goto()` to any internal route — always use sidebar navigation

## Selector Patterns

Tests use web-first locators. Playwright auto-pierces shadow DOM with these selectors:

| Element | Selector | Notes |
|---------|----------|-------|
| Sidebar link | `page.getByRole('link', { name: 'EV Trip Planner' })` | Navigate to panel |
| Add trip button | `page.getByRole('button', { name: /Agregar Viaje/i })` | Open creation form |
| Trip type select | `page.getByRole('combobox')` | Select puntual/recurrente |
| Datetime field | `page.getByLabel(/datetime/i)` | datetime-local input |
| KM field | `page.getByLabel(/km/i)` | Numeric spinbutton |
| KWH field | `page.getByLabel(/kwh/i)` | Numeric spinbutton |
| Description field | `page.getByLabel(/descripci/i)` | Textarea |
| Create button | `page.getByRole('button', { name: /Crear Viaje/i })` | Submit creation form |
| Edit button | `page.getByRole('button', { name: /edit/i })` | Open edit form |
| Save button | `page.getByRole('button', { name: /Guardar Cambios/i })` | Submit edit form |
| Delete button | `page.getByRole('button', { name: /delete/i })` | Trigger deletion |
| Trip card | `page.locator('div').filter({ hasText: '<description>' }).last()` | Locate trip by text |

## Running Tests

### Prerequisites

1. Home Assistant running on `http://localhost:8123`
2. EV Trip Planner integration installed via Config Flow (vehicle ID: `test_vehicle`)
3. Playwright browsers installed: `npx playwright install --with-deps`
4. Auth state saved at `playwright/.auth/user.json` (generated by globalSetup)

### Local Development

```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install --with-deps

# Run tests (uses globalSetup for auth)
npx playwright test tests/e2e/

# Run with headed browser (visible browser)
npx playwright test tests/e2e/ --headed

# Run specific test
npx playwright test tests/e2e/create-trip.spec.ts

# Debug mode (opens Playwright inspector)
npx playwright test tests/e2e/ --debug
```

### CI (GitHub Actions)

Tests run automatically on push/PR to main branch via `.github/workflows/playwright.yml`.

**CI setup:**
- HA runs as a GitHub Actions `services:` container (no Docker daemon needed)
- Auth bypasses login via `trusted_networks` with `allow_bypass_login: true`
- Integration installed automatically via Config Flow (4 steps) during globalSetup
- Vehicle ID hardcoded as `test_vehicle`

**CI environment variables:**
- `CI=true` — enables retries and CI-specific reporter output
- `HA_URL=http://localhost:8123` — auto-set by globalSetup from server-info.json

```bash
# Simulate CI environment locally
CI=true npx playwright test tests/e2e/
```

### Auth Setup (globalSetup)

The `auth.setup.ts` globalSetup handles authentication:

1. Waits for HA to be ready (HTTP 200 on `http://localhost:8123/`)
2. Navigates to `page.goto('/')` — trusted_networks bypasses login, auto-redirects to `/home`
3. Navigates to `/config/integrations` and runs Config Flow (4 steps):
   - Step 1: vehicle_name = "test_vehicle"
   - Step 2: battery_capacity_kwh=60, charging_power_kw=11, kwh_per_km=0.17, safety_margin_percent=20
   - Step 3: planning_horizon_days=7, max_deferrable_loads=50 (defaults accepted)
   - Step 4: charging_sensor (required entity selector)
4. Saves `storageState` to `playwright/.auth/user.json`

## Test Isolation

- Each test creates its own trip data before the test and deletes it after
- Tests run with a single worker (`workers: 1` in playwright.config.ts) to avoid port conflicts
- Each test is independent — they can run in any order

## Mock Boundary

| Layer | Mock allowed? |
|-------|--------------|
| Playwright test code | NEVER |
| HA services (trip_create, trip_update, delete_trip) | NEVER |
| Home Assistant frontend JS | NEVER |
| Browser (Chromium) | NEVER |
| HA service container | NEVER |
| Window.confirm dialog | MUST MOCK via `page.on('dialog')` |

## Troubleshooting

### Tests fail with "page.goto() forbidden"

HA is a SPA. Always use sidebar navigation to reach the panel:
```typescript
await page.goto('/');
await page.waitForURL('/home');
await page.getByRole('link', { name: 'EV Trip Planner' }).click();
```

### Shadow DOM selectors not working

Use web-first locators (getByRole, getByLabel) for robustness. Playwright auto-pierces open shadow DOM with these:
```typescript
// RECOMMENDED - web-first locator (robust, accessibility-friendly)
await page.getByRole('button', { name: /Agregar Viaje/i }).click();

// ALSO WORKS - CSS selectors auto-pierce open shadow DOM in Playwright
await page.locator('.add-trip-btn').click();

// NOTE: "ev-trip-planner-panel" chaining is unnecessary complexity - just use the selector directly
// XPath does NOT pierce shadow roots (avoid XPath for shadow DOM elements)
```

### Dialog handler not catching confirmation

Register the dialog handler BEFORE clicking the delete button:
```typescript
page.on('dialog', async dialog => {
  expect(dialog.message()).toContain('¿Estás seguro de que quieres eliminar este viaje?');
  await dialog.accept();
});
// THEN click delete
await page.getByRole('button', { name: /delete/i }).click();
```
