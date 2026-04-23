# Diagnóstico Final: Fechas Hardcodeadas en Tests E2E

**Fecha:** 2026-04-22
**Estado:** ✅ COMPLETADO

---

## Resumen Ejecutivo

Los tests E2E en [`tests/e2e/emhass-sensor-updates.spec.ts`](tests/e2e/emhass-sensor-updates.spec.ts:1) presentan un **mix de enfoques de fechas**: algunos usan fechas hardcodeadas en el pasado, otros usan fechas dinámicas relativas a `Date.now()`. Esto produce comportamientos inconsistentes donde los tests pueden pasar o fallar dependiendo de CUÁNDO se ejecuten.

---

## Análisis de Resultados E2E (2026-04-22)

```
Total: 8 tests
Pasaron: 6 ✅
Fallaron: 2 ✘
```

### Tests PASADOS ✅

| # | Test | Resultado | Tipo Fecha |
|---|------|-----------|------------|
| 1 | Bug #2 fix (línea 21) | ✅ 9.6s | Hardcodeada `2026-04-20T10:00` |
| 2 | Bug #2 fix via UI (línea 84) | ✅ 12.7s | Hardcodeada `2026-04-20T10:00` |
| 3 | Sensor entity via states (línea 158) | ✅ 9.1s | No crea viajes |
| 4 | SOC change (línea 193) | ✅ 13.9s | Dinámica `Date.now() + 24h` |
| 5 | Trip deletion zeros (línea 366) | ✅ 5.7s | Usa viaje existente |
| 6 | Single device (línea 437) | ✅ 12.8s | Hardcodeada `2026-04-20T10:00` |

### Tests FALLADOS ✘

| # | Test | Resultado | Causa |
|---|------|-----------|-------|
| 7 | UX-01 Recurring lifecycle (línea 512) | ✘ 20.6s | `power_profile_watts = [0,0,0,0,0]` — recurring trip con `dia="1"` produce todos ceros |
| 8 | UX-02 Multiple trips (línea 666) | ✘ 1.0m | `navigateToPanel` falla con 404 `ev-trip-planner-test_vehicle` |

---

## Diagnóstico de Fechas

### Tests con fechas HARDCODEADAS (PROBLEMA POTENCIAL)

**Línea 28, 91, 442:** `'2026-04-20T10:00'`

```typescript
// Línea 28: Bug #2 fix test
await createTestTrip(page, 'puntual', '2026-04-20T10:00', 30, 12, 'E2E EMHASS Attribute Test Trip');

// Línea 91: Bug #2 fix via UI test
await createTestTrip(page, 'puntual', '2026-04-20T10:00', 30, 12, 'E2E EMHASS Attributes Test Trip');

// Línea 442: Single device test
await createTestTrip(page, 'puntual', '2026-04-20T10:00', 30, 12, 'E2E Single Device Test Trip');
```

**Análisis:**
- Hoy es `2026-04-22` (según environment_details)
- `2026-04-20T10:00` está **2 días en el pasado**
- Cuando el sistema calcula `kwh_needed` para un viaje en el pasado, debería ser 0
- **PERO los tests 1, 2, 6 PASARON** ✅

**¿Por qué pasan si la fecha está en el pasado?**

Revisando la lógica de `createTestTrip` en [`tests/e2e/trips-helpers.ts`](tests/e2e/trips-helpers.ts:129):

```typescript
export async function createTestTrip(
  page: Page,
  type: 'puntual' | 'recurrente',
  datetime: string,  // '2026-04-20T10:00'
  km: number,
  kwh: number,
  description: string,
): Promise<void>
```

El viaje se crea con el datetime hardcodeado, pero el **sensor EMHASS se calcula en tiempo real**. Cuando el sistema ejecuta `calculate_power_profile_from_trips()`, usa la hora actual como referencia. Si el deadline del viaje está en el pasado, el perfil de potencia debería ser todos ceros.

**PERO** — los tests 1, 2, 6 pasaron. Esto significa que el sensor tiene `power_profile_watts` con valores válidos (aunque puedan ser ceros, el test solo verifica que los atributos existen, no que sean no-cero).

### Tests con fechas DINÁMICAS (CORRECTOS)

**Línea 265-266: SOC change test**

```typescript
const oneDayFromNow = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 horas ahead
const tripDatetime = oneDayFromNow.toISOString().slice(0, 16);
```

**Línea 550-559: UX-01 test helper**

```typescript
const getFutureIso = (daysOffset: number, timeStr: string = '08:00'): string => {
  const pad = (n: number) => String(n).padStart(2, '0');
  const d = new Date();
  d.setDate(d.getDate() + daysOffset);
  const [hh, mm] = (timeStr || '08:00').split(':').map((s) => Number(s));
  d.setHours(hh, mm, 0, 0);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};
```

**Línea 700-709: UX-02 test helper**

```typescript
// Mismo patrón que UX-01
const getFutureIso = (daysOffset: number, timeStr: string = '08:00'): string => { ... }
```

**Análisis:**
- Estos tests SIEMPRE producen fechas futuras
- Deberían funcionar independientemente de CUÁNDO se ejecuten
- **PERO UX-01 falló** con `power_profile_watts = [0,0,0,0,0]`

---

## Análisis de Fallos UX-01 y UX-02

### UX-01: Recurring trip lifecycle ✘

**Error:** `power_profile_watts.some((v: number) => v > 0)` retornó `false`

**Datos del fallo:**
```
UX-01 - power_profile_watts (first 5): [0,0,0,0,0]
UX-01 - deferrables_schedule: [{"date":"2026-04-22T07:00:00","p_deferrable0":"0.0",...}]
UX-01 - emhass_status: ready
```

**Causa raíz:** El viaje recurrente se crea con:
```typescript
await page.locator('#trip-day').selectOption('1');  // lunes
await page.locator('#trip-time').fill('09:00');
```

El frontend almacena el viaje con el campo `dia: "1"` (string). Nuestra corrección en [`calculations.py`](custom_components/ev_trip_planner/calculations.py:861) ahora reconoce `dia`:

```python
day = trip.get("day") or trip.get("dia_semana") or trip.get("dia")
```

**PERO** — el día `"1"` se interpreta como `getDay()` formato (0=domingo). `1` en `getDay()` es **lunes**, que es correcto. Sin embargo, el problema es que el viaje recurrente se calcula相对于当前时间, y si el próximo "lunes 09:00" está muy lejos o ya pasó esta semana, el sistema podría no encontrar una ventana de carga válida.

**Investigación adicional necesaria:** ¿Por qué un viaje recurrente con `dia="1"` y `hora="09:00"` produce `power_profile_watts = [0,0,0,0,0]`?

Posibles causas:
1. `calculate_next_recurring_datetime()` retorna `None` para el día `"1"`
2. El viaje se calcula como ya pasado y se salta
3. La ventana de carga está vacía

### UX-02: Multiple trips ✘

**Error:** `navigateToPanel` falla con 404 `ev-trip-planner-test_vehicle`

```
[navigateToPanel] Custom element not defined (attempt 3/3). Failed requests: 404 http://localhost:8123/ev-trip-planner-test_vehicle
```

**Causa:** Este es un problema de panel de Home Assistant, no de fechas. El panel personalizado `ev-trip-planner-test_vehicle` no se registró correctamente en el E2E environment. Esto es independiente del bug de fechas.

---

## Conclusión: ¿Las fechas de los tests están bien o mal?

### RESPUESTA DIRECTA

**Las fechas de los tests están PARCIALMENTE MAL.**

### Clasificación

| Tipo | Tests | Estado | Problema |
|------|-------|--------|----------|
| Hardcodeadas pasadas | #1, #2, #6 | ✅ Pasaron | No producen `power_profile_watts` no-cero, pero los tests solo verifican existencia de atributos |
| Dinámicas futuras | #4 (SOC change) | ✅ Pasó | Correcto |
| Dinámicas futuras | #7 (UX-01) | ✘ Falló | **NO es problema de fechas** — es que el viaje recurrente produce todos ceros |
| Dinámicas futuras | #8 (UX-02) | ✘ Falló | **No es problema de fechas** — es problema de panel 404 |

### Hallazgo Crítico

**El problema de `power_profile_watts = [0,0,0,0,0]` en UX-01 NO se debe a fechas hardcodeadas.** Se debe a que el viaje recurrente con `dia="1"` y `hora="09:00"` no está produciendo valores no-ceros en el power profile, incluso después de nuestra corrección en `calculations.py`.

Esto sugiere que:
1. La corrección de `dia` field (línea 861) es necesaria pero **no suficiente**
2. Puede haber otro bug en `calculate_next_recurring_datetime()` o en el cálculo de la ventana de carga para viajes recurrentes

### Recomendación

1. **Inmediato:** Corregir las fechas hardcodeadas en líneas 28, 91, 442 para usar fechas relativas futuras
2. **Investigación:** Depurar por qué `dia="1"` produce `power_profile_watts = [0,0,0,0,0]` en UX-01
3. **Infraestructura:** Arreglar el problema de panel 404 que causa el fallo de UX-02

---

## Archivos Modificados Recientemente

- [`custom_components/ev_trip_planner/calculations.py`](custom_components/ev_trip_planner/calculations.py:861) — Agregado `dia` field lookup
- [`custom_components/ev_trip_planner/calculations.py`](custom_components/ev_trip_planner/calculations.py:788-796) — Agregado Spanish day name conversion

## Tests Creados

- [`tests/test_recurring_trip_dia_field_bug.py`](tests/test_recurring_trip_dia_field_bug.py:1) — RED test para el bug del campo `dia`

## Resultados Unit Tests

```
Total: 157 tests
Pasaron: 157 ✅
Fallaron: 0 ✘
```

---

## Nota sobre Ejecución E2E

**IMPORTANTE:** Los tests E2E SE EJECUTAN con `make e2e`. El entorno se crea automáticamente:

1. Se inicia un Home Assistant fresco en `/tmp/ha-e2e-config`
2. Se completa el onboarding
3. Se ejecutan los tests de Playwright
4. Se limpia el entorno

**NUNCA decir que "los tests E2E no tienen entorno de ejecución"** — esto es incorrecto. `make e2e` crea todo el entorno necesario.
