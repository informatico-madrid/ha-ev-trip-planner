# UI Map — EV Trip Planner E2E (Local Verification)

> Generado: 2026-04-01
> Actualizado: 2026-04-01 con selectors verificados del navegador real
> Fuente: Snapshots reales del navegador MCP Playwright + tests E2E
> HA Instance: http://192.168.1.201:8124 (local test)
> Login: `/` (auth en raíz, `/auth` siempre devuelve 404)

---

## Login HA — `/` (VERIFIED 2026-04-01)

> **IMPORTANTE**: `/auth` devuelve siempre 404. El login es en `/`.
> Si no hay sesión, HA redirige automáticamente al formulario de login.
> Si hay sesión, `/` redirige al dashboard.

### Login Form (HA Auth — español)
| Elemento | Selector | Notas |
|---|---|---|
| Username input | `getByRole('textbox', { name: 'Nombre de usuario' })` | |
| Password input | `getByRole('textbox', { name: 'Contraseña' })` | |
| Login button | `getByRole('button', { name: 'Iniciar sesión' })` | |
| Remember me | `getByRole('checkbox', { name: 'Mantenerme conectado' })` | |
| Error message | `alert` con texto "Nombre de usuario o contraseña no válidos" | Solo en error |
| Forgot password | `getByText('¿Olvidaste la contraseña?')` | |

### Login Flow
```ts
// Ir a / — si no hay sesión, HA muestra el formulario automáticamente
await page.goto(`${baseUrl}/`);
await page.getByRole('textbox', { name: 'Nombre de usuario' }).fill('admin');
await page.getByRole('textbox', { name: 'Contraseña' }).fill('admin1234');
await page.getByRole('button', { name: 'Iniciar sesión' }).click();
await expect(page.locator('ha-sidebar')).toBeVisible({ timeout: 15000 });
```

---

## Sidebar HA (post-login) — VERIFIED 2026-04-01

| Elemento | Selector | Notas |
|---|---|---|
| Sidebar wrapper | `ha-sidebar` | Esperar `toBeVisible` antes de navegar |
| Item vehículo | `page.locator('ha-sidebar').getByText(VEHICLE_ID).first()` | VEHICLE_ID = ej. `'chispitas'` |
| Settings link | `text="Settings"` | |
| Devices & services | `text="Devices & services"` | |

---

## Dashboard HA — `/home` (VERIFIED 2026-04-01)

| Elemento | Selector | Notas |
|---|---|---|
| Welcome heading | `getByRole('heading', { name: /Bienvenido/ })` | |
| Sidebar | `ha-sidebar` | |
| Areas buttons | `page.locator('ha-sidebar').getByText('Living Room')` | |
| Reparaciones button | `getByRole('button', { name: /Reparaciones/ })` | |

---

## Integrations Dashboard — `/config/integrations/dashboard` (VERIFIED 2026-04-01)

| Elemento | Selector | Ref | Notas |
|---|---|---|---|
| Añadir integración button | `getByRole('button', { name: 'Añadir integración' })` | e157 | |
| Search textbox | `getByRole('textbox', { name: 'Buscar un nombre de marca' })` | e182 | Dentro del diálogo |
| EV Trip Planner result | `page.locator('ha-integration-list-item').filter({ hasText: /EV Trip Planner/i })` | e314 | Click con force:true |
| Planificador de Viajes EV link | `getByText('Planificador de Viajes EV')` | e117 | |
| Tab Integraciones | `tab("Integraciones")` | e58 | |
| Tab Dispositivos | `tab("Dispositivos")` | e63 | |
| Tab Entidades | `tab("Entidades")` | e68 | |
| Volver link | `getByText('Volver')` | e19 | |

---

## Config Flow Dialog — 5 Steps (VERIFIED 2026-04-01)

### Step 1: Configuración del Vehículo (VERIFIED)
| Elemento | Selector | Ref | Notas |
|---|---|---|---|
| Dialog heading | `getByText('Planificador de Viajes EV - Configuración del Vehículo')` | e335 | |
| Vehicle name input | `getByRole('textbox', { name: 'Nombre del Vehículo*' })` | e356 | input[name="vehicle_name"] |
| Vehicle description | `getByText("Un nombre amigable para tu vehículo")` | e350 | paragraph hint |
| Enviar button | `getByRole('button', { name: 'Enviar' })` | e364 | |
| Cerrar button | `getByRole('button', { name: 'Cerrar' })` | e330 | |

### Step 2: Sensores del Vehículo (VERIFIED)
| Elemento | Selector | Ref | Notas |
|---|---|---|---|
| Dialog heading | `getByText('Sensores del Vehículo')` | e366 | |
| Battery capacity | `getByRole('spinbutton', { name: 'battery_capacity_kwh*' })` | e383 | Default: 60 |
| Charging power | `getByRole('spinbutton', { name: 'charging_power_kw*' })` | e388 | Default: 11 |
| KWH per km | `getByRole('spinbutton', { name: 'kwh_per_km*' })` | e393 | Default: 0.15 |
| Safety margin | `getByRole('spinbutton', { name: 'safety_margin_percent*' })` | e398 | Default: 10 |
| SOC sensor selector | `getByLabel('Sensor SOC de Batería').getByRole('listitem')` | e409 | Entity selector |
| Enviar button | `getByRole('button', { name: 'Enviar' })` | e420 | |

### Step 3: Integración EMHASS (Opcional) (VERIFIED)
| Elemento | Selector | Ref | Notas |
|---|---|---|---|
| Dialog heading | `getByText('Integración EMHASS (Opcional)')` | e422 | |
| Planning horizon | `getByRole('spinbutton', { name: /Horizonte de Planificación/ })` | e439 | Default: 7 |
| Max deferrable loads slider | `slider` (sin name) | e449 | |
| Index cooldown hours slider | `slider` (sin name) | e461 | |
| Planning sensor selector | `getByLabel('Sensor de Planificación (opcional)').getByRole('listitem')` | e474 | |
| Enviar button | `getByRole('button', { name: 'Enviar' })` | e485 | |

### Step 4: Detección de Presencia (VERIFIED)
| Elemento | Selector | Ref | Notas |
|---|---|---|---|
| Dialog heading | `getByText('Detección de Presencia')` | e487 | |
| Carga sensor (REQUIRED) | `getByLabel('Sensor de Carga (').getByRole('listitem')` | e510 | Entity selector |
| Casa sensor | `getByLabel('Sensor de Casa (binary_sensor)').getByRole('listitem')` | e528 | Entity selector |
| Enchufado sensor | `getByLabel('Sensor Enchufado (').getByRole('listitem')` | e546 | Entity selector |
| Enviar button | `getByRole('button', { name: 'Enviar' })` | e557 | |

### Step 5: Notificaciones (desde auth.setup.ts)
| Elemento | Selector | Notas |
|---|---|---|
| Submit button | `getByRole('button', { name: /Submit|Next/i })` | Puede requerir doble submit |

---

## EV Trip Planner Panel — `/ev-trip-planner-{vehicle_id}` (VERIFIED 2026-04-01)

| Elemento | Selector | Ref | Notas |
|---|---|---|---|
| Panel heading | `getByRole('heading', { name: /EV Trip Planner -/ })` | e25 | |
| Vehicle Status heading | `getByRole('heading', { name: 'Vehicle Status' })` | e28 | |
| Viajes heading | `getByRole('heading', { name: 'Viajes' })` | e37 | |
| Agregar Viaje button | `getByRole('button', { name: '+ Agregar Viaje' })` | e186 | |
| Viajes Programados heading | `getByRole('heading', { name: 'Viajes Programados' })` | e183 | |
| Empty state | `getByText('No hay viajes programados')` | e187 | |
| Energy section | `getByRole('heading', { name: /Energía y Consumo/ })` | e152 | |
| Trip cards | `.trip-card` | CSS class | |
| Entity links | `getByText('chispitas_trips_list')` | e41 | |

---

## Trip Form Modal (VERIFIED desde tests)

| Elemento | Selector | Notas |
|---|---|---|
| Add trip button | `getByRole('button', { name: /Agregar Viaje/i })` | |
| Form overlay | `.trip-form-overlay` | Contenedor del modal |
| Tipo de Viaje combobox | `getByRole('combobox', { name: 'Tipo de Viaje' })` | |
| Día de la Semana combobox | `getByRole('combobox', { name: 'Día de la Semana' })` | Solo recurrente |
| Hora time input | `page.locator('#trip-time')` | ID para recurrente |
| Fecha datetime input | `page.locator('#trip-datetime')` | ID para puntual |
| Distancia spinbutton | `getByRole('spinbutton', { name: 'Distancia (km)' })` | |
| Energía spinbutton | `getByRole('spinbutton', { name: 'Energía Estimada (kWh)' })` | |
| Descripción textbox | `getByRole('textbox', { name: 'Descripción (opcional)' })` | |
| Crear Viaje button | `.trip-form-overlay.getByRole('button', { name: 'Crear Viaje' })` | Scoped al overlay |
| Cancel button | `.trip-form-overlay .btn-secondary` | |

---

## Constantes de Entorno

```ts
const VEHICLE_ID = 'chispitas';  // lowercase normalized
const BASE_URL = 'http://192.168.1.201:8124';
const SERVER_INFO_PATH = join(process.cwd(), 'playwright/.auth/server-info.json');
```

---

## Notas Importantes

1. **Login URL**: Solo `/` — nunca `/auth` (devuelve 404)
2. **Entity Selectors**: Usan Shadow DOM — Playwright web-first locators auto-piercen
3. **Config Flow Steps**: Pueden requerir doble submit por errores JS internos de HA
4. **Spinbuttons**: `browser_fill_form` no soporta spinbutton — usar `fill()` directo
5. **Panel URL**: `ev-trip-planner-{vehicle_id}` donde vehicle_id es lowercase normalizado

---

## Archivos Relacionados

- `tests/e2e/auth.setup.ts` — Login y config flow completo
- `tests/e2e/test-cascade-delete.spec.ts` — Delete integration flow
- `tests/e2e/test-single-panel-chispitas.spec.ts` — Panel creation y sidebar
- `.claude/playwright-env.local.md` — Configuración de entorno
