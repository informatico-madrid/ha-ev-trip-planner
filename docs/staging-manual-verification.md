# Verificación Manual en Staging — Procedimiento Playwright MCP

> **Propósito:** Documentar el proceso paso a paso para verificar manualmente que un fix funciona en staging real usando Playwright MCP (navegación por la UI).
> **No confundir con:** E2E tests (`npx playwright test`) o API calls directas.

## Contexto

Staging es un HA real en Docker (puerto 8124). Para verificar cambios, un agente IA navega por la UI como lo haría un usuario real, usando las herramientas MCP de Playwright (`browser_snapshot`, `browser_click`, `browser_type`, `browser_take_screenshot`).

**Regla fundamental:** Nunca usar API calls directas (`/api/states`). Siempre navegar por la UI.

---

## Procedimiento: Verificar un sensor en Developer Tools > States

### 1. Asegurar que staging está corriendo

```bash
docker ps --format '{{.Names}} {{.Status}}' | grep staging
```

Debe mostrar `ha-staging Up ...`. Si no:

```bash
make staging-up
```

### 2. Verificar que el código nuevo está en el contenedor

```bash
docker exec ha-staging grep -n 'cap_ratio' /config/custom_components/ev_trip_planner/emhass_adapter.py || echo "CLEAN - no cap_ratio"
```

### 3. Reiniciar staging para aplicar cambios

```bash
docker compose -f docker-compose.staging.yml restart homeassistant
sleep 15 && curl -s -o /dev/null -w "%{http_code}" http://localhost:8124/
```

Debe devolver `200`.

### 4. Navegar a staging con Playwright MCP

```
browser_navigate → http://localhost:8124/
```

Si aparece login, usar `browser_run_code_unsafe` para llenar el formulario:
```js
async (page) => {
  const usernameInput = page.locator('host').locator('ha-text-input[label="User"]');
  const passwordInput = page.locator('host').locator('ha-text-input[label="Password"]');
  await usernameInput.fill('admin');
  await passwordInput.fill('admin123');
  await page.locator('host').locator('ha-login-button').click();
  await page.waitForLoadState('networkidle');
}
```

Si ya está logueado, redirige automáticamente a `/home/overview`.

### 5. Ir a Herramientas para desarrolladores > Estados

Usar navegación directa por URL:

```js
async (page) => {
  await page.goto('http://localhost:8124/developer-tools/state');
  await page.waitForLoadState('networkidle');
}
```

### 6. Filtrar por la entidad del sensor

Primero tomar snapshot para identificar el textbox de búsqueda:

```
browser_snapshot → buscar 'textbox "Entidades de filtro" [ref=...' en el resultado
```

Luego escribir el nombre de la entidad:

```
browser_type → target: textbox ref (ej: e161), text: emhass_perfil_diferible_mi_ev
```

El snapshot mostrará la entidad filtrada con su estado y atributos en la tabla.

### 7. Verificar los atributos del sensor

En el snapshot, buscar los atributos clave en la columna "Atributos":

| Atributo | Qué validar |
|----------|-------------|
| `p_deferrable_nom_array` | Todos los valores no-cero deben ser IGUALES (power fijo del cargador). No deben haber valores intermedios/distorsionados. |
| `power_profile_watts` | Solo debe contener `0` y el power fijo del cargador. Nunca valores como `10266`, `8511`, etc. |
| `def_total_hours_array` | Horas de carga por viaje. El SOC cap debe reducir estas horas, no la potencia. |
| `def_start_timestep_array` / `def_end_timestep_array` | Ventanas de carga por viaje. |

### 8. Validar visualmente con screenshot

Si la tabla está truncada o no se ven todos los atributos:

```
browser_take_screenshot → filename: staging-sensor-check.png
```

---

## Ejemplo Real: Verificar Fix de P_deferrable_nom

### Bug original
- `p_deferrable_nom_array`: `1509, 1126, 475` ❌ (valores intermedios/distorsionados por `cap_ratio`)
- `power_profile_watts`: `10266, 8511, ...` ❌

### Fix aplicado
- `cap_ratio` eliminado de `emhass_adapter.py`
- Power fijo = `charging_power_kw * 1000` (ej: 3600W)

### Resultado verificado en staging
- `p_deferrable_nom_array`: `3600, 3600, 3600` ✅ (todos iguales = power fijo del cargador)
- `power_profile_watts`: solo `0` y `3600` ✅ (nunca valores intermedios)
- `def_total_hours_array`: `5, 3, 1` ✅ (horas reducidas por SOC cap, power intacto)

---

## Navegación por Shadow DOM de HA

Los web components de Home Assistant están en Shadow DOM y no aparecen correctamente en `browser_snapshot`. Si necesitas interactuar con elementos que no aparecen en el snapshot:

### Hacer screenshot para ver la UI

```
browser_take_screenshot → filename: staging-check.png
```

### Click en elementos del sidebar del menú

Los items del sidebar aparecen en el snapshot con el atributo `nav-label`:

```
browser_snapshot → buscar ref del elemento nav-label
browser_click → target: ref found in snapshot
```

### Navegación directa por URL

Si no se encuentra un elemento:

```js
async (page) => {
  await page.goto('http://localhost:8124/<path>');
  await page.waitForLoadState('networkidle');
}
```

Rutas útiles:
- Dashboard del plugin: `/ev-trip-planner-mi_ev`
- Lista de entidades: `/config/entity`
- Developer tools > States: `/developer-tools/state`
- Device/Entity detail: `/config/entity/<entity_id>`

---

## Comandos Útiles de Docker

```bash
# Verificar logs del contenedor
docker logs -f ha-staging

# Ver archivos montados
docker exec ha-staging ls /config/custom_components/ev_trip_planner/

# Revisar configuración de HA
docker exec ha-staging cat /config/configuration.yaml | head -50
```

---

## Checklist de Verificación

- [ ] Contenedor staging corriendo (`docker ps | grep staging`)
- [ ] Código actualizado en contenedor (`docker exec ... grep`)
- [ ] HA responde en `localhost:8124` (HTTP 200)
- [ ] Login funciona (`admin` / `admin123`)
- [ ] Entidad del sensor aparece filtrada en Developer Tools > States
- [ ] Atributos clave visibles en la columna "Atributos"
- [ ] `p_deferrable_nom_array` = todos iguales (power fijo) ✅
- [ ] `power_profile_watts` = solo 0 + power fijo ✅
- [ ] `def_total_hours_array` = horas reducidas por SOC cap ✅
