# Selector Map — EV Trip Planner E2E
> Generado desde tests en verde. Fuente de verdad para agentes, nuevos tests y prompts.
> Repositorio: `informatico-madrid/ha-ev-trip-planner`
> Tests base: `tests/e2e/` (Playwright/TypeScript)

---

## 1. Navegación y Autenticación

### Login (HA Auth Flow)
| Elemento | Selector | Tipo | Notas |
|---|---|---|---|
| Username input | `input[type="text"]` | CSS | `page.locator(...)` — también `getByRole('textbox', {name:/Username/i})` |
| Password input | `input[type="password"]` | CSS | |
| Login button | `paper-button:not([disabled])` | CSS | Antiguo papel-button de HA |
| Error message | `ha-alert` | CSS | Visible solo si fallo |
| Remember me | `paper-checkbox` | CSS | |

**Patrón funcional:**
```ts
await page.getByRole('textbox', { name: /Username/i }).fill('dev');
await page.getByRole('textbox', { name: /Password/i }).fill('dev');
await page.getByRole('button', { name: /log in/i }).click();
await expect(page.locator('ha-sidebar, [role="navigation"]')).toBeVisible({ timeout: 10000 });
```

### Sidebar HA
| Elemento | Selector | Notas |
|---|---|---|
| Sidebar wrapper | `ha-sidebar` | Siempre esperar `toBeVisible` antes de navegar |
| Item vehículo | `page.locator('ha-sidebar').getByText(VEHICLE_ID).first()` | VEHICLE_ID = ej. `'Coche2'` |
| Settings link | `text="Settings"` | `page.click(...)` |

**Patrón de navegación al panel:**
```ts
await page.goto(baseUrl);
const sidebar = page.locator('ha-sidebar');
await expect(sidebar).toBeVisible({ timeout: 15000 });
const vehicleOption = sidebar.getByText(VEHICLE_ID).first();
await vehicleOption.waitFor({ state: 'visible', timeout: 10000 });
await vehicleOption.click();
await page.waitForTimeout(2000); // panel tarda en montar
```

---

## 2. Panel Principal

| Elemento | Selector | Tipo |
|---|---|---|
| Panel custom | `ev-trip-planner-panel, ha-panel-ev_trip_planner` | CSS (`.first()`) |
| Trip cards (lista) | `.trip-card` | CSS class — `.locator('.trip-card')` |
| Trip card recurrente | `.trip-card[recurring="true"], .trip-card[data-type="recurrente"]` | CSS attr |
| Trip card puntual | `.trip-card[punctual="true"], .trip-card[data-type="puntual"]` | CSS attr |

---

## 3. Formulario Crear/Editar Viaje

### Apertura del modal
| Elemento | Selector | Notas |
|---|---|---|
| Botón abrir modal | `getByRole('button', { name: /Agregar Viaje/i })` | Timeout 10000 |

### Campos del formulario (dentro del modal)
| Campo | Selector Playwright | Role type |
|---|---|---|
| Tipo de Viaje | `getByRole('combobox', { name: 'Tipo de Viaje' })` | combobox |
| Día de la Semana | `getByRole('combobox', { name: 'Día de la Semana' })` | combobox (solo viajes recurrentes) |
| Hora | `getByRole('textbox', { name: 'Hora' })` | textbox |
| Distancia (km) | `getByRole('spinbutton', { name: 'Distancia (km)' })` | spinbutton (number input) |
| Energía Estimada (kWh) | `getByRole('spinbutton', { name: 'Energía Estimada (kWh)' })` | spinbutton |
| Descripción (opcional) | `getByRole('textbox', { name: 'Descripción (opcional)' })` | textbox |

### Botón submit (scoped al overlay)
```ts
// ⚠️ CRÍTICO: scope al overlay para evitar colisiones con otros botones
const createButton = page.locator('.trip-form-overlay').getByRole('button', { name: 'Crear Viaje' });
```

### Overlay / modal wrappers
| Elemento | Selector | Notas |
|---|---|---|
| Form overlay | `.trip-form-overlay` | Contenedor del modal de viaje |
| Form container | `.trip-form-container` | Interior del overlay |
| Dialog activo | `[role="dialog"]` | Esperar `state: 'detached'` tras cerrar |

### Flujo completo crear viaje
```ts
// 1. Abrir modal
await page.getByRole('button', { name: /Agregar Viaje/i }).click();

// 2. Rellenar campos
await page.getByRole('combobox', { name: 'Tipo de Viaje' }).selectOption(tripData.type);
await page.getByRole('combobox', { name: 'Día de la Semana' }).selectOption(tripData.day); // solo recurrentes
await page.getByRole('textbox', { name: 'Hora' }).fill('14:00');
await page.getByRole('spinbutton', { name: 'Distancia (km)' }).fill('150');
await page.getByRole('spinbutton', { name: 'Energía Estimada (kWh)' }).fill('20');
await page.getByRole('textbox', { name: 'Descripción (opcional)' }).fill('Test description');

// 3. Submit (scoped al overlay)
await page.locator('.trip-form-overlay').getByRole('button', { name: 'Crear Viaje' }).click();

// 4. HA usa window.confirm → hay que aceptar el dialog nativo
const dialog = await page.waitForEvent('dialog', { timeout: 10000 });
await dialog.accept();

// 5. Esperar a que el modal desaparezca
await page.waitForSelector('[role="dialog"]', { state: 'detached', timeout: 10000 });
```

---

## 4. Sensores / Entidades Dinámicas

| Elemento | Selector | Notas |
|---|---|---|
| Sensor por entity_id | `[data-entity="sensor.{entityId}"]` | Genérico |
| Trip distance | `[data-entity="{entityId}"]` o `[data-testid="sensor.{entityId}"]` | Page Object |
| Energy used | `[data-entity="sensor.{entityId}_energy_used"]` | |
| Charging status | `[data-entity="sensor.{entityId}_charging_status"]` | |
| Charging status card | `[data-testid="charging-status-{vehicleId}"]` | |
| Vehicle card | `[data-testid="vehicle-card"]` | |
| Trip list | `[data-testid="trip-list"]` | |

---

## 5. Integrations Dashboard (Config Flow / Delete)

### Navegación
```ts
await page.goto(`${baseUrl}/config/integrations/dashboard`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2000);
```

### Añadir integración
| Acción | Selector |
|---|---|
| Botón Add integration | `getByRole('button', { name: /Add integration/i })` |
| Search input | `getByRole('textbox', { name: /Search for a brand name/i })` |
| Resultado EV Trip Planner | `getByText('EV Trip Planner')` |
| Campo vehicle_name | `locator('input[name="vehicle_name"]')` — usar `.type(value, {delay:50})` |
| Submit | `getByRole('button', { name: 'Submit' })` |

**Patrón completo añadir integración:**
```ts
await page.getByRole('button', { name: /Add integration/i }).click();
await page.getByRole('textbox', { name: /Search for a brand name/i }).fill('EV Trip Planner');
await expect(page.getByText('EV Trip Planner')).toBeVisible({ timeout: 5000 });
await page.getByText('EV Trip Planner').click();
await page.waitForTimeout(2000);
const vehicleNameField = page.locator('input[name="vehicle_name"]');
await vehicleNameField.waitFor({ state: 'visible', timeout: 30000 });
await vehicleNameField.click();
await vehicleNameField.type(vehicleName, { delay: 50 });
await page.getByRole('button', { name: 'Submit' }).click();
```

### Eliminar integración (flujo complicado — múltiples fallbacks)
```ts
// Acceder a la integración
const integrationElement = page.locator(`text="${vehicleName}"`).first();
await integrationElement.waitFor({ state: 'visible', timeout: 10000 });
await integrationElement.click();
await page.waitForTimeout(2000);

// Intento 1: botón Delete directo
const deleteButton = page.getByRole('button', { name: /Delete|Eliminar/i }).or(
  page.locator('ha-icon-button').filter({ has: page.locator('ha-svg-icon') }).last()
);

// Intento 2: menú "more options"
const moreOptionsBtn = page.locator(
  'button[aria-label*="delete" i], button[aria-label*="remove" i], button[aria-label*="eliminar" i]'
).first();

// Intento 3: ha-button-menu overflow
const overflowBtn = page.locator('ha-button-menu').or(page.locator('button[aria-label*="more"]'));
const menuDelete = page.getByRole('menuitem', { name: /Delete|Eliminar/i });

// Confirmar eliminación
const confirmDialog = page.locator('[role="alertdialog"], [role="dialog"]')
  .filter({ hasText: /delete|eliminar|confirm/i });
const confirmButton = page.getByRole('button', { name: /Delete|Confirm|Eliminar|Confirmar/i });
// o si es window.confirm nativo:
const nativeDialog = await page.waitForEvent('dialog', { timeout: 3000 });
await nativeDialog.accept();
```

---

## 6. Selectores de la Page Object Class (EVTripPlannerPage)

> Archivo: `tests/e2e/pages/ev-trip-planner.page.ts`

```ts
// Sidebar
this.sidebar = page.locator('home-assistant-sidebar, aside');
this.evTripPlannerMenuItem = page.getByText(/ev trip planner|planificador de viajes ev/i);

// Dashboard
this.dashboardTitle = page.getByRole('heading', { name: /ev trip planner|planificador de viajes/i });
this.vehicleCards = page.locator('[data-testid="vehicle-card"]');
this.addVehicleButton = page.getByRole('button', { name: /add vehicle|añadir vehículo/i });

// Dinámicos
this.tripDistanceSensor = (entityId) => page.locator(`[data-entity="${entityId}"], [data-testid="sensor.${entityId}"]`);
this.energyUsedSensor = (entityId) => page.locator(`[data-entity="sensor.${entityId}_energy_used"]`);
this.chargingStatusSensor = (entityId) => page.locator(`[data-entity="sensor.${entityId}_charging_status"]`);

// Trip management
this.createTripButton = page.getByRole('button', { name: /create trip|crear viaje/i });
this.tripList = page.locator('[data-testid="trip-list"]');

// Settings
this.settingsButton = page.getByRole('button', { name: /settings|ajustes/i });
this.configurationButton = page.getByRole('button', { name: /configure|configurar/i });
```

---

## 7. EMHASS / Power Config

| Elemento | Selector | Notas |
|---|---|---|
| Botón abrir modal EMHASS | `getByRole('button', { name: /Agregar Viaje/i })` | Mismo flujo de viaje base |

> Ver `tests/e2e/test-emhass-power.spec.ts` — reutiliza los mismos selectores de formulario de viaje con campos adicionales de potencia.

---

## 8. Constantes de Entorno

```ts
const VEHICLE_ID = 'Coche2'; // usado en selectores de sidebar
const SERVER_INFO_PATH = join(process.cwd(), 'playwright/.auth/server-info.json');

function getBaseUrl(): string {
  const info = JSON.parse(fs.readFileSync(SERVER_INFO_PATH, 'utf-8'));
  return new URL(info.link || info.baseUrl || process.env.HA_BASE_URL!).origin;
}
```

---

## 9. Timeouts de Referencia

| Contexto | Timeout | Selector |
|---|---|---|
| Sidebar visible | 15000ms | `ha-sidebar` |
| Vehicle option visible | 10000ms | `sidebar.getByText(VEHICLE_ID)` |
| Botón Agregar Viaje | 10000ms | `getByRole('button', ...)` |
| Crear Viaje button | 10000ms | `.trip-form-overlay button` |
| Dialog nativo | 10000ms | `page.waitForEvent('dialog')` |
| Dialog detach | 10000ms | `waitForSelector('[role="dialog"]', {state:'detached'})` |
| Panel montar | 2000ms | `page.waitForTimeout(2000)` |
| vehicle_name field | 30000ms | `input[name="vehicle_name"]` |
| Integración aparecer en lista | 5000ms | `getByText('EV Trip Planner')` |

---

## 10. Antipatrones Detectados en Tests

- ❌ **NO usar** `page.waitForLoadState('networkidle')` en HA custom panels — puede colgar
- ❌ **NO buscar** `Crear Viaje` sin scope al `.trip-form-overlay` — hay colisiones de selectores
- ❌ **NO asumir** que el delete de integración usa siempre un botón visible — hay 3 flujos posibles
- ✅ Siempre scoped: `page.locator('.trip-form-overlay').getByRole('button', { name: 'Crear Viaje' })`
- ✅ Siempre esperar `dialog` nativo tras submit de formulario de viaje
- ✅ Usar `getByText(VEHICLE_ID).first()` — puede haber múltiples nodos con el mismo texto en el DOM

---

## 11. Estructura de Archivos E2E

```
tests/e2e/
├── auth.setup.ts                        — login + config flow completo (setup global)
├── test-helpers.ts                      — getHassInstance(), hass-taste-test wrapper
├── pages/
│   ├── ev-trip-planner.page.ts          — Page Object principal
│   ├── ha-login.page.ts                 — Page Object login
│   └── index.ts                         — re-exports
├── skills/
│   ├── ha-core-frontend.skill.md        — cómo HA sirve panel.js
│   └── selector-map.skill.md            — este archivo
├── test-crud-trip.spec.ts               — crear/editar viaje
├── test-cascade-delete.spec.ts          — eliminar integración + cleanup
├── test-trip-list.spec.ts               — lista de viajes
├── test-emhass-power.spec.ts            — configuración EMHASS
└── test-single-panel-chispitas.spec.ts  — panel individual
```
