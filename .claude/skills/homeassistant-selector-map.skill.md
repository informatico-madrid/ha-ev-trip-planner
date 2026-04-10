# Skill: homeassistant-selector-map

> **Ejemplo de dominio específico** — basado en `selector-map.skill.md`.
> Estrategia de selectores estables para tests Playwright contra la UI de
> Home Assistant (Lovelace, paneles custom, integraciones).
>
> Para apps que no son HA, usa `../selector-map.skill.md` como base
> y crea tu propio `{tu-dominio}-selector-map.skill.md`.

---

## Regla principal

Un selector inestable rompe el test aunque el código esté bien.
Elige siempre el selector más semántico y resistente a cambios de UI.

---

## Jerarquía de selectores (orden de preferencia)

```text
1. getByRole()          — accesibilidad semántica, más estable
2. getByLabel()         — asociado al label del formulario
3. getByTestId()        — data-testid explícito, sin semántica UI
4. getByText()          — solo para texto visible único y estable
5. locator('css')       — último recurso, solo si no hay alternativa
```

### Cuándo usar cada uno

| Selector | Cuándo | Ejemplo HA |
|---|---|---|
| `getByRole` | Botones, links, inputs, headings | `getByRole('button', { name: 'Calcular ruta EV' })` |
| `getByLabel` | Inputs con `<label>` asociado | `getByLabel('Origen')` |
| `getByTestId` | Componentes web / shadow DOM / cards custom | `getByTestId('ev-route-card-MAD-BCN')` |
| `getByText` | Mensajes de estado, badges únicos | `getByText('Ruta guardada')` |
| `locator('css')` | Nunca en tests nuevos — solo legado | — |

---

## Shadow DOM en Home Assistant

La mayor parte de la UI de HA está dentro de shadow roots.
Playwright los atraviesa automáticamente con `getByRole` y `getByTestId`,
pero si necesitas acceder manualmente:

```typescript
// Atravesar shadow root explícitamente
const haCard = page.locator('ha-card').first()
const shadowContent = haCard.locator(':scope >> text=Ruta activa')

// Mejor: usa getByTestId si el componente lo expone
const card = page.getByTestId('ev-route-card')
```

Regla: si `getByRole` / `getByTestId` no llegan, investiga si el componente
expone atributos ARIA antes de atravesar el shadow DOM manualmente.

---

## Convención `data-testid` para componentes HA custom

Formato: `{dominio}-{entidad}-{variante}-{acción}`

```html
<!-- Card de ruta -->
<ha-card data-testid="ev-route-card">

<!-- Card con variante específica -->
<ha-card data-testid="ev-route-card-mad-bcn">

<!-- Acción sobre la card -->
<mwc-button data-testid="ev-route-card-delete">

<!-- Listado de rutas -->
<div data-testid="ev-route-list">
<ha-card data-testid="ev-route-list-item">

<!-- Input del panel -->
<ha-textfield data-testid="ev-origin-input">
```

Reglas:
- Prefijo de dominio siempre (`ev-`, `sensor-`, `climate-`)
- Minúsculas con guiones
- Sin entity_id ni IDs de HA (son inestables entre instancias)
- Nombrar por función, no por posición

---

## Anti-patrones — nunca usar en HA

```typescript
// ❌ Shadow DOM hardcodeado por profundidad
page.locator('home-assistant >>> ha-panel-lovelace >>> hui-card-container')

// ❌ entity_id en selector
page.locator('[data-entity-id="sensor.ev_battery_level"]')

// ❌ Clase CSS de Polymer/Lit (cambia con versiones de HA)
page.locator('.card-content.ha-scrollbar')

// ❌ XPath
page.locator('//ha-card[@class="ev-route"]')

// ❌ Posición en lista
page.locator('hui-entities-card:nth-child(3)')
```

---

## Patrones correctos

```typescript
// Botón de acción en card
await page.getByRole('button', { name: 'Calcular ruta EV' }).click()

// Input de origen
await page.getByLabel('Origen').fill('Madrid')

// Card por testid (componente complejo con shadow DOM)
const card = page.getByTestId('ev-route-card-mad-bcn')
await expect(card).toBeVisible()

// Verificar estado de la ruta
await expect(page.getByText('Ruta guardada')).toBeVisible()

// Scope: buscar dentro de un diálogo de HA
const dialog = page.getByRole('dialog')
await dialog.getByRole('button', { name: 'Confirmar' }).click()

// Esperar respuesta de la API de HA
await page.waitForResponse(resp =>
  resp.url().includes('/api/conversation/process') && resp.status() === 200
)
```

---

## Assertions recomendadas

```typescript
await expect(locator).toBeVisible()
await expect(locator).toBeHidden()
await expect(locator).toHaveText('Texto esperado')
await expect(locator).toContainText('parcial')
await expect(locator).toHaveAttribute('aria-disabled', 'true')
await expect(locator).toHaveValue('Madrid')
await expect(page).toHaveURL(/\/lovelace\/ev-routes/)
await expect(page.getByTestId('ev-route-list-item')).toHaveCount(3)
```

---

## Esperas — nunca `waitForTimeout`

```typescript
// ✅ Esperar a que la card sea visible tras navegación
await page.getByTestId('ev-route-card').waitFor({ state: 'visible' })

// ✅ Esperar respuesta de WebSocket de HA
await page.waitForResponse(resp =>
  resp.url().includes('/api/websocket') && resp.status() === 101
)

// ✅ Esperar cambio de URL en Lovelace
await page.waitForURL(/\/lovelace\//)

// ❌ Nunca
await page.waitForTimeout(2000)
```

---

## HA Core Pages (Developer Tools, Devices, States)

> **Aprendizaje de fix-emhass-sensor-attributes (2026-04-09)**
> Las páginas del core de HA (`/developer-tools/state`, `/config/devices/list`,
> `/config/entities`) NO son paneles custom. No tienen `data-testid` propios
> y su DOM interno puede cambiar entre versiones de HA.
> **Nunca escribas selectores para estas páginas sin hacer un snapshot primero.**

### Protocolo snapshot-first (OBLIGATORIO para páginas del core)

Antes de escribir UN SOLO selector para cualquier página del core de HA,
el agente DEBE ejecutar este protocolo:

```typescript
// PASO 1: Navegar y hacer screenshot — ejecutar esto PRIMERO
test('snapshot-discover: developer-tools/state', async ({ page }) => {
  await page.goto('/developer-tools/state')
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: 'playwright/snapshots/dev-tools-state.png', fullPage: true })
  // Imprimir el HTML del body para inspección
  const html = await page.locator('body').innerHTML()
  console.log('DOM snapshot:', html.substring(0, 3000))
})
```

Solo después de ver el screenshot y el DOM real, escribir los selectores reales.

### Alternativa preferida: HA REST API en lugar de DOM

Para verificar estados de sensores, la REST API es MÁS ESTABLE que el DOM
de Developer Tools. Usar siempre que el test solo necesite verificar valores,
no interacción UI:

```typescript
// ✅ Verificar estado de un sensor via REST API (sin DOM)
test('sensor has correct attributes', async ({ page }) => {
  // Obtener token de la sesión autenticada
  const token = await page.evaluate(() =>
    (window as any).hassConnection?.auth?.data?.access_token
  )

  // Llamar directamente a la API de HA
  const response = await page.request.get(
    'http://localhost:8123/api/states/sensor.ev_trip_planner_test_vehicle_deferrable_load',
    { headers: { Authorization: `Bearer ${token}` } }
  )
  expect(response.ok()).toBeTruthy()
  const state = await response.json()

  // Verificar atributos del sensor
  expect(state.attributes.power_profile_watts).not.toBeNull()
  expect(state.attributes.emhass_status).toBeDefined()
})

// ✅ Verificar dispositivos via API
const devResponse = await page.request.get(
  'http://localhost:8123/api/config/device_registry/list',
  { headers: { Authorization: `Bearer ${token}` } }
)
const devices = await devResponse.json()
const evDevices = devices.filter((d: any) =>
  d.identifiers?.some((id: any) => id[0] === 'ev_trip_planner')
)
expect(evDevices).toHaveLength(1)
```

### Selectores reales de Developer Tools > States

Estos selectores fueron verificados con snapshot en HA 2024.x:

```typescript
// Navegar a Developer Tools > States
await page.goto('/developer-tools/state')
await page.waitForLoadState('networkidle')

// Filtrar por entity_id — el input de búsqueda es el primero en la página
const searchInput = page.locator('input[placeholder*="Filter"]').first()
// Alternativa más estable si el placeholder cambia:
// const searchInput = page.getByRole('textbox').first()
await searchInput.fill('sensor.ev_trip_planner')

// Las filas de estados son elementos <tr> dentro de una tabla
// Buscar por el entity_id visible en texto
const stateRow = page.getByText('sensor.ev_trip_planner_test_vehicle_deferrable_load')
await expect(stateRow).toBeVisible()

// Para ver los atributos: click en la fila o en el ícono de expand
// ⚠️ Este selector es frágil — verificar con snapshot en cada versión de HA
await stateRow.click()
```

### Selectores reales de Developer Tools > Devices

```typescript
// Navegar a Devices
await page.goto('/config/devices/list')
await page.waitForLoadState('networkidle')

// Buscar por nombre de dispositivo — el search input principal
const deviceSearch = page.getByRole('textbox', { name: /search/i })
// Fallback si no tiene aria-label:
// const deviceSearch = page.locator('search-input input, ha-textfield input').first()
await deviceSearch.fill('EV Trip Planner')

// El dispositivo aparece como una card o fila con el nombre
const deviceCard = page.getByText('EV Trip Planner Test Vehicle')
await expect(deviceCard).toBeVisible()

// Verificar que SOLO hay un dispositivo (no duplicados)
const allEvDevices = page.getByText(/EV Trip Planner/)
await expect(allEvDevices).toHaveCount(1)
```

### Cuándo usar API vs DOM para páginas del core

| Necesidad | Usar |
|---|---|
| Verificar valor de atributo de sensor | REST API `/api/states/{entity_id}` |
| Verificar número de dispositivos registrados | REST API `/api/config/device_registry/list` |
| Verificar que la UI muestra el valor correcto | DOM con snapshot-first |
| Interacción UI (click, fill) | DOM con snapshot-first |

---

## Documento vivo — actualización continua

**Este skill DEBE actualizarse después de cada spec E2E** que navegue a
zonas nuevas de HA. El flujo es:

```
Spec E2E completa
  └─ VE0-DISCOVER encontró selectores reales
       └─ Añadir a la sección correspondiente de este skill
            └─ Commit: docs(skills): add {página} selectors from {spec-name}
```

Si no actualizas el skill, la siguiente spec que navegue a la misma página
inventará los selectores de nuevo. **El skill es memoria colectiva.**

---

## Checklist antes de entregar un test E2E

- [ ] Todos los selectores usan `getByRole`, `getByLabel` o `getByTestId`
- [ ] Ningún `locator('.clase')`, XPath ni shadow DOM hardcodeado
- [ ] Ningún `waitForTimeout`
- [ ] Ningún entity_id ni ID dinámico de HA en selectores
- [ ] Los `data-testid` siguen el formato `{dominio}-{entidad}-{variante}-{acción}`
- [ ] No hay testids duplicados en la misma vista
- [ ] Si el test navega a páginas del core de HA: se hizo snapshot-first y los selectores son reales
- [ ] Si el test solo verifica valores de sensores: se usó REST API en lugar de DOM
