# Revisión Adversaria: C2+C7+C8 Fixes — E2E Test Improvements

**Archivo:** `tests/e2e/emhass-sensor-updates.spec.ts`
**Fecha:** 2026-04-23
**Revisor:** Architect Mode (Adversarial Review)

---

## Veredicto General: ✅ APROBADO — Ambos fixes son correctos y seguros

---

## 1. C2+C7 Fix — Eliminación del fallback loop en `discoverEmhassSensorEntityId()`

### Análisis del código actual (líneas 33-47)

```typescript
const discoverEmhassSensorEntityId = async (pg): Promise<string | null> => {
  return await pg.evaluate(() => {
    const haMain = document.querySelector('home-assistant') as any;
    if (!haMain?.hass?.states) return null;
    for (const [entityId, state] of Object.entries(haMain.hass.states)) {
      if (!entityId.startsWith('sensor.emhass_perfil_diferible_')) continue;
      const attrs = (state as any).attributes;
      if (attrs?.vehicle_id === 'test_vehicle') return entityId;
    }
    return null;
  });
};
```

### Pregunta 1: ¿Rompe algún test existente?

**NO.** Verificación exhaustiva de los 7 call sites:

| Call Site | Test | Línea | Non-null Assert | ¿Riesgo? |
|-----------|------|-------|-----------------|----------|
| #1 | Task 4.4 (SOC change) | 308 | `!` | Ninguno — sensor siempre tiene `vehicle_id` |
| #2 | Task 4.4b (deletion) | 427 | `!` | Ninguno — sensor persiste sin viajes |
| #3 | race-condition-immediate | 575 | `toBeTruthy()` | Ninguno — viaje ya creado |
| #4 | race-condition-rapid Step3 | 628 | `toBeTruthy()` | Ninguno — viaje 1 ya creado |
| #5 | race-condition-rapid Step5 | 651 | `toBeTruthy()` | Ninguno — viajes 1+2 ya creados |
| #6 | UX-01 lifecycle | 693 | `!` | Ninguno — viaje recurrente creado |
| #7 | UX-02 multi-trip | 779 | `!` | Ninguno — 3 viajes creados |

**Razonamiento:** El sensor EMHASS SIEMPRE establece `vehicle_id` en sus atributos (verificado en [`sensor.py:243`](custom_components/ev_trip_planner/sensor.py:243): `"vehicle_id": vehicle_id`). En el entorno E2E solo existe un vehículo (`test_vehicle`), por lo que el fallback nunca fue necesario.

### Pregunta 5: ¿Consistencia con el patrón del panel frontend?

**SÍ.** El panel frontend usa el MISMO patrón de filtrado por `vehicle_id`. Verificado en [`panel.js:1266-1281`](custom_components/ev_trip_planner/frontend/panel.js:1266):

```javascript
if (entityId.includes('emhass_perfil_diferible_')) {
  const vehicleId = state.attributes?.vehicle_id;
  if (vehicleId === this._vehicleId) {
    result[entityId] = state;
  }
}
```

El fix alinea el helper de test con el código de producción. **Esto es una mejora de calidad.**

### Veredicto C2+C7: ✅ CORRECTO

- Elimina riesgo de cross-vehicle contamination
- Consistente con código de producción (`panel.js`)
- No rompe ningún test existente
- Si el sensor no existe, retorna `null` → test falla con error claro en vez de match incorrecto

---

## 2. C8 Fix — Aserciones Step 5 en `race-condition-regression-rapid-successive-creation`

### Análisis del código actual (líneas 646-662)

```typescript
await expect(async () => {
  const sensorEntityId = await discoverEmhassSensorEntityId(page);
  expect(sensorEntityId).toBeTruthy();
  const a = await getSensorAttributes(page, sensorEntityId!);
  expect(Array.isArray(a.power_profile_watts)).toBe(true);
  expect(a.power_profile_watts.some((v: number) => v > 0)).toBe(true);
  // C8 FIX: Verify both trips contribute data
  expect(Array.isArray(a.def_total_hours_array)).toBe(true);
  expect((a.def_total_hours_array as number[]).length).toBeGreaterThanOrEqual(2);
  expect(Array.isArray(a.p_deferrable_matrix)).toBe(true);
  expect((a.p_deferrable_matrix as number[][]).length).toBeGreaterThanOrEqual(2);
}).toPass({ timeout: 15000 });
```

### Pregunta 2: ¿Las aserciones son correctas o demasiado frágiles?

**CORRECTAS y NO frágiles.** Verificación contra el modelo de datos:

**`def_total_hours_array`** — Cada viaje contribuye exactamente 1 elemento:
- [`emhass_adapter.py:653`](custom_components/ev_trip_planner/emhass_adapter.py:653): `"def_total_hours_array": [math.ceil(total_hours)]` — lista de 1 elemento por viaje
- [`sensor.py:300-301`](custom_components/ev_trip_planner/sensor.py:300): `def_total_hours_array.extend(params["def_total_hours_array"])` — agrega 1 elemento por viaje

→ Con 2 viajes: `def_total_hours_array.length === 2`. La aserción `>= 2` es semánticamente correcta.

**`p_deferrable_matrix`** — Cada viaje contribuye exactamente 1 fila (lista de potencia):
- [`emhass_adapter.py:657`](custom_components/ev_trip_planner/emhass_adapter.py:657): `"p_deferrable_matrix": [power_profile]` — lista con 1 perfil por viaje
- [`sensor.py:290-291`](custom_components/ev_trip_planner/sensor.py:290): `matrix.extend(p_matrix)` — agrega 1 fila por viaje

→ Con 2 viajes: `p_deferrable_matrix.length === 2`. La aserción `>= 2` es semánticamente correcta.

**Elección de `>=` vs `===`:** Usar `>= 2` en vez de `=== 2` es defensivamente correcto. Aunque `beforeEach` limpia viajes previos, si hubiera un edge case con datos residuales, el test no daría un falso negativo.

### Pregunta 3: ¿Los tipos TypeScript son correctos?

**SÍ.** El tipo de `a` es `Record<string, any>` (retornado por [`getSensorAttributes`](tests/e2e/emhass-sensor-updates.spec.ts:23)), por lo tanto `a.def_total_hours_array` es `any`.

- `(a.def_total_hours_array as number[])` — cast seguro porque está precedido por `Array.isArray(a.def_total_hours_array)` que verifica en runtime
- `(a.p_deferrable_matrix as number[][])` — mismo razonamiento

Los casts `as` son solo para satisfacer el compilador TypeScript; no tienen efecto en runtime. La validación real la hace `Array.isArray()` antes del acceso a `.length`.

### Pregunta 4: ¿Riesgo de falsos positivos/negativos?

**Falsos positivos:** No posibles. Si solo 1 viaje se procesó, `length` será 1, y `>= 2` falla correctamente.

**Falsos negativos:** Riesgo mínimo, mitigado por `toPass()`:
- Si EMHASS aún no procesó el segundo viaje cuando se evalúa la aserción, `length` será 1 → la aserción falla → `toPass()` reintenta hasta 15 segundos → eventualmente ambos viajes se procesan y `length >= 2` pasa.
- El timeout de 15 segundos es generoso para un entorno E2E con 2 viajes.

### Pregunta 5: ¿Consistente con el patrón `toPass()` del archivo?

**SÍ.** El archivo usa `toPass({ timeout: 15000 })` consistentemente en:
- Step 2 del test SOC (línea 325)
- Step 5 del test SOC (línea 355)
- Step 9 del test SOC (línea 389)
- Step 3 del race-immediate (línea 583)
- Step 5 del race-immediate (línea 590)
- Step 6 del race-immediate (línea 597)
- Step 3 del race-rapid (línea 627)
- **Step 5 del race-rapid (línea 650)** ← C8 fix
- Step 6 del race-rapid (línea 665)
- UX-01 V2-V4 (línea 697)
- UX-01 V5 (línea 709)
- UX-02 V5 (línea 780)
- UX-02 V6 (línea 791)

### Veredicto C8: ✅ CORRECTO

- Aserciones semánticamente correctas contra el modelo de datos
- Tipos TypeScript seguros con validación runtime previa
- No frágiles — `toPass()` maneja timing con retry
- Consistente con el patrón del archivo

---

## 3. Hallazgos Adicionales

### PRE-EXISTENTE: TS errors en líneas 330, 360, 394

Estas líneas usan `expect(boolean).toBe(boolean, 'message')` donde el segundo argumento es un mensaje custom. Esto puede causar warnings TS según la versión de `@playwright/test`, pero es un patrón válido en Playwright y **no fue introducido por este fix**.

### PRE-EXISTENTE: Test 4.4b (línea 413) depende de estado residual

El test "should verify trip deletion updates sensor attributes to zeros (Task 4.4b)" dice "Use a trip already created by previous tests" pero `beforeEach` llama a `cleanupTestTrips()`. Esto es un bug pre-existente no relacionado con C2+C7+C8.

---

## Resumen Final

| Fix | Veredicto | Riesgo | Notas |
|-----|-----------|--------|-------|
| C2+C7: Eliminar fallback loop | ✅ APROBADO | Ninguno | Alinea test con código de producción |
| C8: Aserciones Step 5 | ✅ APROBADO | Ninguno | Semánticamente correcto, no frágil |

**Recomendación:** Merge ambos fixes. Son mejoras netas de calidad que eliminan falsos negativos sin introducir fragilidad.
