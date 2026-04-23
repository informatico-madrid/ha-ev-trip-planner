# Sprint Change Proposal: E2E UX Tests UX-01 y UX-02

**Fecha:** 2026-04-22  
**Trigger:** Branch `fix-sensor-deletion-calculating-soc` — fix completado, tests pendientes  
**Scope Classification:** **Minor** — Solo implementación de tests, sin cambios en código de producción  
**Handoff Recipients:** Code Mode (implementación de 2 tests E2E)

---

## Section 1: Issue Summary

### Trigger
El branch `fix-sensor-deletion-calculating-soc` tiene el fix de race condition COMPLETADO y verificado. Los únicos pendientes son 2 tests E2E propuestos en [`plans/e2e-ux-test-proposal-fix-sensor-deletion.md`](plans/e2e-ux-test-proposal-fix-sensor-deletion.md:1).

### Estado Actual del Fix
| Componente | Estado | Referencia |
|-----------|--------|-----------|
| [`services.py`](custom_components/ev_trip_planner/services.py) | ✅ Fix aplicado — handlers llaman `mgr.publish_deferrable_loads()` | [`plans/e2e-ux01-root-cause-fix.md`](plans/e2e-ux01-root-cause-fix.md:35) |
| [`trip_manager.py`](custom_components/ev_trip_planner/trip_manager.py) | ✅ Fix aplicado — removido `coordinator.async_refresh()` | [`plans/e2e-ux01-root-cause-fix.md`](plans/e2e-ux01-root-cause-fix.md:68) |
| [`emhass_adapter.py`](custom_components/ev_trip_planner/emhass_adapter.py) | ✅ Fix aplicado — `async_set_data()` directo en línea 729 | [`plans/e2e-ux01-root-cause-and-fix.md`](plans/e2e-ux01-root-cause-and-fix.md:86) |
| `tests/ha-manual/configuration.yaml` | ✅ SOC cambiado 80% → 20% | [`plans/e2e-ux01-root-cause-fix.md`](plans/e2e-ux01-root-cause-fix.md:118) |
| RED tests | ✅ Pasan verificando fix funciona | [`plans/BUG-ROOT-CAUSE-MEMORY.md`](plans/BUG-ROOT-CAUSE-MEMORY.md:57) |
| **E2E UX-01** | ⏳ PENDIENTE | [`plans/e2e-ux-test-proposal-fix-sensor-deletion.md`](plans/e2e-ux-test-proposal-fix-sensor-deletion.md:25) |
| **E2E UX-02** | ⏳ PENDIENTE | [`plans/e2e-ux-test-proposal-fix-sensor-deletion.md`](plans/e2e-ux-test-proposal-fix-sensor-deletion.md:55) |

---

## Section 2: Contexto Técnico del Fix Aplicado

### Race Condition Original
```
ANTES (roto):
handle_trip_create()
  ├── async_add_recurring_trip() → almacena trip
  └── coordinator.async_refresh_trips() → lee de get_cached_optimization_results()
                                        → retorna datos STALE → sensor muestra ceros
```

```
DESPUÉS (fix):
handle_trip_create()
  ├── async_add_recurring_trip() → almacena trip
  └── mgr.publish_deferrable_loads()
       └── async_publish_all_deferrable_loads(trips)
            ├── _calculate_power_profile_from_trips() → calcula perfil
            ├── coordinator.async_set_data({...}) → actualiza coordinator.data DIRECTAMENTE
            └── (SIN async_refresh que sobreescribiría con datos stale)
```

### Clave para los Tests E2E
- **`coordinator.async_set_data()`** actualiza `coordinator.data` inmediatamente sin debouncing
- **`coordinator.async_refresh()`** dispara `_async_update_data()` que lee de fuentes externas y puede sobreescribir
- El fix usa `async_set_data()` para datos NO-vacíos (trips existentes)
- El fix usa `async_set_data()` + `async_refresh()` para datos vacíos (eliminación) — ver [`emhass_adapter.py:729-745`](custom_components/ev_trip_planner/emhass_adapter.py:729)

---

## Section 3: Story 1 — E2E UX-01: Flujo Completo Recurrente + Sensor Sync

### Historia
```
Como QA, quiero verificar que un viaje recurrente completo (crear → propagar → eliminar) 
se sincroniza correctamente con el sensor EMHASS, para garantizar que el fix de race 
condition funciona en el caso más complejo (recurrente, no solo puntual).
```

### Contexto de Implementación

**Archivo destino:** [`tests/e2e/emhass-sensor-updates.spec.ts`](tests/e2e/emhass-sensor-updates.spec.ts)  
**Helpers existentes:**
- [`navigateToPanel()`](tests/e2e/trips-helpers.ts:23) — navega al panel con retry
- [`createTestTrip()`](tests/e2e/trips-helpers.ts:129) — crea viajes (puntual o recurrente)
- [`cleanupTestTrips()`](tests/e2e/trips-helpers.ts:272) — elimina todos los viajes
- [`deleteTestTrip()`](tests/e2e/trips-helpers.ts:187) — elimina un viaje específico
- [`getFutureIso()`](tests/e2e/zzz-integration-deletion-cleanup.spec.ts:44) — computa datetime futuro

**Helpers a agregar al archivo:**
```typescript
// Helper: get sensor attributes from HA frontend hass.states object
const getSensorAttributes = async (page: Page, entityId: string): Promise<Record<string, any>> => {
  return await page.evaluate((eid: string) => {
    const haMain = document.querySelector('home-assistant') as any;
    if (!haMain?.hass?.states?.[eid]) {
      throw new Error(`Entity ${eid} not found in hass.states`);
    }
    return haMain.hass.states[eid].attributes;
  }, entityId);
};

// Helper: discover EMHASS sensor entity ID from hass.states
const discoverEmhassSensorEntityId = async (page: Page): Promise<string | null> => {
  return await page.evaluate(() => {
    const haMain = document.querySelector('home-assistant') as any;
    if (!haMain?.hass?.states) return null;
    for (const [entityId, state] of Object.entries(haMain.hass.states)) {
      if (!entityId.startsWith('sensor.emhass_perfil_diferible_')) continue;
      const attrs = (state as any).attributes;
      if (attrs?.vehicle_id === 'test_vehicle') return entityId;
    }
    for (const entityId of Object.keys(haMain.hass.states)) {
      if (entityId.includes('emhass_perfil_diferible')) return entityId;
    }
    return null;
  });
};
```

### Contract of Execution — Validaciones UX-01

| # | Validación | Criterio | Timeout | Herramienta |
|---|-----------|----------|---------|-------------|
| V1 | Viaje recurrente aparece en UI | `getByText(description)` visible | 10s | `expect.toBeVisible()` |
| V2 | Sensor tiene `power_profile_watts` NO-CERO | `attrs.power_profile_watts.some(v => v > 0) === true` | 15s polling | `expect.toBe(true)` |
| V3 | Sensor tiene `deferrables_schedule` populated | `Array.isArray(attrs.deferrables_schedule) && attrs.deferrables_schedule.length > 0` | 15s polling | `expect.toBe(true)` |
| V4 | Sensor tiene `emhass_status === "ready"` | `attrs.emhass_status === "ready"` | 15s polling | `expect.toBe("ready")` |
| V5 | Después de eliminar: sensor va a TODOS Ceros | `attrs.power_profile_watts.every(v => v === 0)` | 15s polling | `expect.toBe(true)` |
| V6 | Viaje ya no aparece en UI | `getByText(description)` no visible | 5s | `expect.toNotBeVisible()` |

### Flujo Detallado UX-01

```
1. beforeEach: navigateToPanel(page) + cleanupTestTrips(page)
2. Crear viaje recurrente:
   createTestTrip(page, 'recurrente', getFutureIso(1, '08:00'), 50, 10, 'UX01 Recurring Trip', {day: '1', time: '08:00'})
3. Esperar propagación: page.waitForTimeout(3000)
4. Descubrir sensor: const entityId = await discoverEmhassSensorEntityId(page)
5. Validar V2-V4 con polling 15s:
   await expect(async () => {
     const attrs = await getSensorAttributes(page, entityId);
     expect(attrs.power_profile_watts.some(v => v > 0)).toBe(true);
     expect(Array.isArray(attrs.deferrables_schedule) && attrs.deferrables_schedule.length > 0).toBe(true);
     expect(attrs.emhass_status).toBe('ready');
   }).toPass({ timeout: 15000 });
6. Eliminar viaje: deleteTestTrip(page, tripId)
7. Esperar propagación: page.waitForTimeout(3000)
8. Validar V5 con polling 15s:
   await expect(async () => {
     const attrs = await getSensorAttributes(page, entityId);
     expect(attrs.power_profile_watts.every(v => v === 0)).toBe(true);
   }).toPass({ timeout: 15000 });
9. Validar V6: expect(page.getByText('UX01 Recurring Trip')).toNotBeVisible()
```

### Edge Cases a Considerar

| Edge Case | Manejo |
|-----------|--------|
| Sensor no encontrado al inicio | `discoverEmhassSensorEntityId()` con fallback a entity_id hardcoded |
| Propagación lenta en CI | `expect(async () => {...}).toPass({ timeout: 15000 })` para todas las validaciones de sensor |
| Dialog de confirmación | `deleteTestTrip()` maneja dialogs internamente |
| SOC alto produce ceros | Configuration.yaml ya tiene SOC=20%, pero usar `getFutureIso()` para trips en futuro donde el cálculo tiene sentido |

### Código Base del Test

```typescript
test('should verify complete recurring trip lifecycle with sensor sync (UX-01)', async ({ page }) => {
  // Setup
  const tripDescription = 'UX01 Recurring Trip';
  const tripDatetime = getFutureIso(1, '08:00');
  
  // Step 1: Create recurring trip
  await createTestTrip(page, 'recurrente', tripDatetime, 50, 10, tripDescription, { day: '1', time: '08:00' });
  
  // Step 2: Wait for EMHASS propagation
  await page.waitForTimeout(3000);
  
  // Step 3: Discover sensor
  const sensorEntityId = await discoverEmhassSensorEntityId(page);
  expect(sensorEntityId).toBeTruthy();
  
  // Step 4: Verify sensor attributes (V2, V3, V4)
  await expect(async () => {
    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.power_profile_watts.some((v: number) => v > 0)).toBe(true);
    expect(Array.isArray(attrs.deferrables_schedule) && attrs.deferrables_schedule.length > 0).toBe(true);
    expect(attrs.emhass_status).toBe('ready');
  }).toPass({ timeout: 15000 });
  
  // Step 5: Delete trip
  await deleteTestTrip(page, `${tripDatetime}-${tripDescription}`);
  await page.waitForTimeout(3000);
  
  // Step 6: Verify sensor went to zeros (V5)
  await expect(async () => {
    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.power_profile_watts.every((v: number) => v === 0)).toBe(true);
  }).toPass({ timeout: 15000 });
  
  // Step 7: Verify trip removed from UI (V6)
  await expect(page.getByText(tripDescription)).toNotBeVisible();
});
```

---

## Section 4: Story 2 — E2E UX-02: Múltiples Viajes + No-Duplicación

### Historia
```
Como QA, quiero verificar que al crear MÚLTIPLES viajes simultáneos (2 recurrentes + 1 puntual), 
no se duplican dispositivos ni sensores en Home Assistant, y que la eliminación individual de 
un viaje no afecta los demás, para garantizar la integridad del sistema bajo carga.
```

### Contract of Execution — Validaciones UX-02

| # | Validación | Criterio | Timeout | Herramienta |
|---|-----------|----------|---------|-------------|
| V1 | 3 viajes aparecen en UI | `getByText('Trip 1')`, `getByText('Trip 2')`, `getByText('Trip 3')` visibles | 10s c/u | `expect.toBeVisible()` |
| V2 | Solo 1 dispositivo en `/config/devices` | `getByText('EV Trip Planner test_vehicle').all().length === 1` | 10s | `expect.toBe(1)` |
| V3 | Solo 1 sensor EMHASS en `/config/entities` | Count de entities con `emhass_perfil_diferible` === 1 | 10s | `expect.toBe(1)` |
| V4 | Eliminar 1 viaje no afecta los otros 2 | `getByText('Trip 1')` y `getByText('Trip 3')` siguen visibles | 5s c/u | `expect.toBeVisible()` |
| V5 | Sensor sigue con NO-CERO después de eliminar 1 de 3 | `attrs.power_profile_watts.some(v => v > 0) === true` | 15s polling | `expect.toBe(true)` |
| V6 | Después de eliminar TODOS: sensor va a ceros | `attrs.power_profile_watts.every(v => v === 0)` | 15s polling | `expect.toBe(true)` |

### Flujo Detallado UX-02

```
1. beforeEach: navigateToPanel(page) + cleanupTestTrips(page)
2. Crear 3 viajes:
   a. createTestTrip(page, 'recurrente', getFutureIso(1, '08:00'), 50, 10, 'UX02 Trip 1', {day: '1', time: '08:00'})
   b. createTestTrip(page, 'recurrente', getFutureIso(2, '10:00'), 30, 7, 'UX02 Trip 2', {day: '2', time: '10:00'})
   c. createTestTrip(page, 'puntual', getFutureIso(3, '14:00'), 20, 5, 'UX02 Trip 3')
3. Esperar propagación: page.waitForTimeout(5000)
4. Validar V1: expect todos visibles
5. Validar V2: page.goto('/config/devices') → verificar 1 dispositivo
6. Validar V3: page.goto('/config/entities') → verificar 1 sensor EMHASS
7. Eliminar viaje del medio (UX02 Trip 2):
   deleteTestTrip(page, 'UX02 Trip 2')
   page.waitForTimeout(3000)
8. Validar V4: Trip 1 y Trip 3 siguen visibles
9. Validar V5: sensor sigue con NO-CERO
10. Eliminar Trip 1 y Trip 3:
    deleteTestTrip(page, 'UX02 Trip 1')
    deleteTestTrip(page, 'UX02 Trip 3')
    page.waitForTimeout(3000)
11. Validar V6: sensor va a ceros
```

### Edge Cases a Considerar

| Edge Case | Manejo |
|-----------|--------|
| Orden de eliminación importa | Eliminar primero el del medio (Trip 2) para verificar que los extremos persisten |
| Duplicación de dispositivos | Verificar explícitamente en `/config/devices` que solo hay 1 fila con "EV Trip Planner test_vehicle" |
| Duplicación de sensores | Verificar explícitamente en `/config/entities` que solo hay 1 entity con `emhass_perfil_diferible` |
| Propagación múltiple | Usar `waitForTimeout(5000)` después de crear 3 viajes antes de verificar |

### Código Base del Test

```typescript
test('should verify multiple trips with no device/sensor duplication (UX-02)', async ({ page }) => {
  // Setup: crear 3 viajes
  const trip1Id = `${getFutureIso(1, '08:00')}-UX02 Trip 1`;
  const trip2Id = `${getFutureIso(2, '10:00')}-UX02 Trip 2`;
  const trip3Id = `${getFutureIso(3, '14:00')}-UX02 Trip 3`;
  
  await createTestTrip(page, 'recurrente', getFutureIso(1, '08:00'), 50, 10, 'UX02 Trip 1', { day: '1', time: '08:00' });
  await createTestTrip(page, 'recurrente', getFutureIso(2, '10:00'), 30, 7, 'UX02 Trip 2', { day: '2', time: '10:00' });
  await createTestTrip(page, 'puntual', getFutureIso(3, '14:00'), 20, 5, 'UX02 Trip 3');
  
  // Esperar propagación completa
  await page.waitForTimeout(5000);
  
  // V1: Verificar 3 viajes visibles
  await expect(page.getByText('UX02 Trip 1')).toBeVisible();
  await expect(page.getByText('UX02 Trip 2')).toBeVisible();
  await expect(page.getByText('UX02 Trip 3')).toBeVisible();
  
  // V2: Verificar 1 dispositivo
  await page.goto('/config/devices');
  await page.waitForLoadState('networkidle');
  const deviceCount = await page.getByText('EV Trip Planner test_vehicle').all().then(arr => arr.length);
  expect(deviceCount).toBe(1);
  
  // V3: Verificar 1 sensor EMHASS
  await page.goto('/config/entities');
  await page.waitForLoadState('networkidle');
  const sensorCount = await page.getByText('emhass_perfil_diferible').all().then(arr => arr.length);
  expect(sensorCount).toBe(1);
  
  // Eliminar viaje del medio
  await deleteTestTrip(page, trip2Id);
  await page.waitForTimeout(3000);
  
  // V4: Verificar que los otros 2 siguen visibles
  await expect(page.getByText('UX02 Trip 1')).toBeVisible();
  await expect(page.getByText('UX02 Trip 3')).toBeVisible();
  
  // V5: Sensor sigue con NO-CERO
  const sensorEntityId = await discoverEmhassSensorEntityId(page);
  await expect(async () => {
    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.power_profile_watts.some((v: number) => v > 0)).toBe(true);
  }).toPass({ timeout: 15000 });
  
  // Eliminar restantes
  await deleteTestTrip(page, trip1Id);
  await deleteTestTrip(page, trip3Id);
  await page.waitForTimeout(3000);
  
  // V6: Sensor va a ceros
  await expect(async () => {
    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.power_profile_watts.every((v: number) => v === 0)).toBe(true);
  }).toPass({ timeout: 15000 });
});
```

---

## Section 5: Diferencias Clave vs Tests Existentes

| Aspecto | Tests Existentes | UX-01 | UX-02 |
|---------|-----------------|-------|-------|
| Tipo de viaje | Solo puntual | **Recurrente** (caso complejo) | **Mixto**: 2 recurrentes + 1 puntual |
| Viajes simultáneos | Máximo 1 | 1 | **3 simultáneos** |
| Verificación de sensor | Atributos básicos | **power_profile + deferrables_schedule + emhass_status** | **power_profile con eliminación parcial** |
| Eliminación | Todos de golpe | Individual | **Individual + verificación de persistencia** |
| Device/entity count | Solo device (1 test) | No verifica | **Verifica device + entity** |
| Propagación | 3s fijo | **Polling 15s con toPass()** | **Polling 15s con toPass()** |

---

## Section 6: Implementation Handoff

### Scope Classification: Minor

### Handoff Recipients

| Role | Responsabilidad |
|------|-----------------|
| **Code Mode** | Implementar E2E UX-01 en `emhass-sensor-updates.spec.ts` |
| **Code Mode** | Implementar E2E UX-02 en `emhass-sensor-updates.spec.ts` |
| **Code Mode** | Agregar helpers (`getSensorAttributes`, `discoverEmhassSensorEntityId`, `getFutureIso`) al archivo |

### Success Criteria

1. **E2E UX-01:**
   - [ ] Test pasa en entorno HA local con SOC=20%
   - [ ] Todas las 6 validaciones (V1-V6) verificadas
   - [ ] Usa polling `toPass({ timeout: 15000 })` para verificaciones de sensor
   - [ ] Usa `getFutureIso()` para evitar problemas de datetime

2. **E2E UX-02:**
   - [ ] Test pasa en entorno HA local con SOC=20%
   - [ ] Todas las 6 validaciones (V1-V6) verificadas
   - [ ] Verifica 1 dispositivo y 1 sensor con MÚLTIPLES viajes
   - [ ] Verifica eliminación individual sin afectar otros viajes

3. **Código:**
   - [ ] Helpers agregados al inicio del archivo (antes del describe)
   - [ ] Tests agregados dentro del mismo `describe('EMHASS Sensor Updates')`
   - [ ] No se requieren cambios en `scripts/run-e2e.sh`
   - [ ] No se requieren cambios en código de producción

### Dependencies

| Dependency | Status |
|-----------|--------|
| Fix race condition en `services.py` | ✅ Completado |
| Fix en `trip_manager.py` | ✅ Completado |
| SOC=20% en configuration.yaml | ✅ Completado |
| Helpers `navigateToPanel`, `createTestTrip`, `cleanupTestTrips` | ✅ Existentes |
| Helper `getFutureIso` | ✅ Existe en `zzz-integration-deletion-cleanup.spec.ts:44` |
| Helper `getSensorAttributes` | ⏳ Por agregar al archivo |
| Helper `discoverEmhassSensorEntityId` | ⏳ Por agregar al archivo |

---

## Appendix: Referencias

### Documentación del Fix
- [`plans/e2e-ux-test-proposal-fix-sensor-deletion.md`](plans/e2e-ux-test-proposal-fix-sensor-deletion.md:1) — Propuesta original de tests
- [`plans/e2e-ux01-root-cause-and-fix.md`](plans/e2e-ux01-root-cause-and-fix.md:1) — Root cause analysis
- [`plans/e2e-ux01-root-cause-fix.md`](plans/e2e-ux01-root-cause-fix.md:1) — Detalles del fix aplicado
- [`plans/BUG-ROOT-CAUSE-MEMORY.md`](plans/BUG-ROOT-CAUSE-MEMORY.md:1) — Memoria del fix de coordinator fallback

### Código Modificado
- [`custom_components/ev_trip_planner/services.py`](custom_components/ev_trip_planner/services.py) — Handlers actualizados
- [`custom_components/ev_trip_planner/trip_manager.py`](custom_components/ev_trip_planner/trip_manager.py) — publish_deferrable_loads() simplificado
- [`custom_components/ev_trip_planner/emhass_adapter.py`](custom_components/ev_trip_planner/emhass_adapter.py) — async_set_data() directo
- [`tests/ha-manual/configuration.yaml`](tests/ha-manual/configuration.yaml) — SOC=20%

### Código Existente Reutilizado
- [`tests/e2e/trips-helpers.ts`](tests/e2e/trips-helpers.ts:23) — navigateToPanel, createTestTrip, cleanupTestTrips
- [`tests/e2e/zzz-integration-deletion-cleanup.spec.ts`](tests/e2e/zzz-integration-deletion-cleanup.spec.ts:44) — getFutureIso
- [`tests/e2e/emhass-sensor-updates.spec.ts`](tests/e2e/emhass-sensor-updates.spec.ts:197) — Patrón getSensorAttributes ya usado en test existente
