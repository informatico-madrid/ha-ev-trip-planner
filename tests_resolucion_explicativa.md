# Resolución de los 4 Tests que Fallaban

## Tests Originales

Los 4 tests que estaban fallando eran:

1. **`test_soc_100_first_trip_must_not_have_2_hours`** (test_soc_100_propagation_bug_pending.py)
2. **`test_def_total_hours_debe_coincidir_con_perfil_potencia`** (test_def_total_hours_mismatch_bug.py)
3. **`test_soc_100_p_deferrable_nom_debe_ser_0_cuando_no_hay_carga`** (test_soc_100_p_deferrable_nom_bug.py)
4. **`test_soc_100_p_deferrable_nom_puntual`** (test_soc_100_p_deferrable_nom_bug.py)

## Estado Actual: ✅ TODOS PASAN

```
tests/test_def_total_hours_mismatch_bug.py::TestDefTotalHoursMismatchBug::test_def_total_hours_debe_coincidir_con_perfil_potencia PASSED
tests/test_soc_100_p_deferrable_nom_bug.py::TestSOC100PDeferrableNomBug::test_soc_100_p_deferrable_nom_debe_ser_0_cuando_no_hay_carga PASSED
tests/test_soc_100_p_deferrable_nom_bug.py::TestSOC100PDeferrableNomBug::test_soc_100_p_deferrable_nom_puntual PASSED
tests/test_soc_100_propagation_bug_pending.py::TestSOC100PropagationBugPending::test_soc_100_first_trip_must_not_have_2_hours PASSED
```

## El Problema que Tenían

### Test 1 & 2: SOC 100% con Propagación de Consumo

**Escenario:**
- SOC inicial: 100%
- 5 viajes recurrentes que consumen energía progresivamente
- Viaje 1: 30 kWh (consume 60% de batería de 50 kWh)
- Viaje 2-5: Diversos kWh

**Lo que ocurría:**
```
SOC inicial: 100%
Viaje 1 consume 60% → SOC para viaje 2: 40%
Viaje 2 necesita 45 kWh pero solo tiene 40% (20 kWh) → necesita 25 kWh extra → 7.35 horas
```

**El bug original (antes de mis fixes):**
- La propagación de déficit asignaba horas de carga al viaje 1
- PERO el coche estaba al 100% SOC → físicamente imposible cargar más

**Mi fix anterior (líneas 672-677):**
```python
if adjusted_def_total_hours > 0 and soc_current < 100.0:
    needs_charging = True
    power_watts = charging_power_kw * 1000
```
- Agregué `soc_current < 100.0` para evitar cargar más allá del 100%
- `soc_current` es el SOC **proyectado para la ventana de ese viaje** (no el SOC actual del sistema)

**Estado actual:** ✅ PASA

---

### Test 3: Mismatch entre def_total_hours y P_deferrable_nom

**Escenario:**
- SOC inicial: 50% (25 kWh disponibles)
- 5 viajes de 10 kWh cada uno
- Consumo progresivo:
  - Viaje 1: consume a 30% SOC (15 kWh restantes)
  - Viaje 2: consume a 10% SOC (5 kWh restantes)
  - Viaje 3-5: Necesitan cargar porque SOC 10% < 10 kWh + 10% margen

**El bug:**
```
Viaje 3: Tiene 3 horas de carga en perfil
  Pero def_total_hours = 0 ❌
  Y P_deferrable_nom = 0.0 W ❌

Viaje 4-5: Similar (5 horas de carga en perfil)
  Pero def_total_hours = 0 ❌
  Y P_deferrable_nom = 0.0 W ❌
```

**La causa raíz:**

Mi código original detectaba la necesidad de carga usando `has_charging_in_profile`:
```python
has_charging_in_profile = any(p > 0 for p in power_profile)
"P_deferrable_nom": round(power_watts, 0) if has_charging_in_profile else 0.0
```

PERO cuando el SOC propagado llega a 0% (después de consumo de viajes anteriores):
1. `determine_charging_need()` dice `needs_charging=True` (el viaje SÍ necesita carga)
2. PERO `_calculate_power_profile_from_trips()` con SOC 0% devuelve perfil vacío (todos 0.0)
3. Entonces `has_charging_in_profile = False`
4. Y `P_deferrable_nom = 0.0` (INCORRECTO)

**El fix aplicado (líneas 720-738):**

```python
# Determine if charging is needed based on propagation or initial decision
if adjusted_def_total_hours is not None and adjusted_def_total_hours > 0:
    # When propagation provides hours > 0, use that as authoritative
    def_total_hours_value = math.ceil(adjusted_def_total_hours)
    has_charging = True
elif adjusted_def_total_hours is not None and adjusted_def_total_hours == 0:
    # Propagation says 0 hours, but trip may still need charging individually
    # Use profile hours and decision.needs_charging
    def_total_hours_value = non_zero_hours_in_profile
    has_charging = decision.needs_charging  # ← KEY FIX
else:
    # No propagation at all, use profile hours and decision
    def_total_hours_value = non_zero_hours_in_profile
    has_charging = decision.needs_charging
```

**La lógica corregida:**
1. Si `adjusted_def_total_hours > 0`: hay carga desde propagación → `has_charging = True`
2. Si `adjusted_def_total_hours == 0`: propagación dice 0, PERO el viaje puede necesitar carga individualmente → usar `decision.needs_charging`
3. Si `adjusted_def_total_hours is None`: no hay propagación → usar `decision.needs_charging`

**KEY INSIGHT:** `decision.needs_charging` se calcula ANTES de generar el perfil, por lo que NO está afectado por el problema de SOC 0% que causa perfiles vacíos.

**Estado actual:** ✅ PASA

---

### Test 4: Viaje Puntual con SOC 100%

**Escenario similar al Test 1-2 pero con viaje puntual.**

**Estado actual:** ✅ PASA (mismo fix que Test 1-2)

---

## Test Sigue Fallando (Pero es un Bug Diferente)

### `test_def_start_at_zero_reduces_hours`

**Ubicación:** [test_def_start_window_bug.py:190-240](tests/test_def_start_window_bug.py#L190-L240)

**Propósito:** Verificar que cuando `def_start_timestep = 0` y la ventana es muy pequeña (1 timestep), el sistema reduce `def_total_hours` para que coincida con la ventana disponible.

**El error:**
```
AssertionError: Window too small even after adjustment: 1 < 2
```

**Contexto:**
- Este es un bug diferente sobre **ventanas de carga muy pequeñas**
- No está relacionado con SOC 100% ni con P_deferrable_nom
- Está relacionado con el cálculo de `def_start_timestep` y `def_end_timestep`

**Reporte original del usuario para este bug:**
```
def_start_timestep: [36, 52, 131, 142, 152]
def_end_timestep:   [43, 122, 139, 143, 163]
def_total_hours:    [ 2,  2,   2,   2,   2]

Load 3 (index 3): start=142, end=143, window=1 < hours=2 → FAILS
```

La ventana de carga (1 timestep) es más pequeña que las horas necesarias (2), causando que EMHASS se niegue a optimizar.

---

## Resumen Ejecutivo

### ✅ Arreglados
- **Bug 1:** SOC 100% con propagación de déficit que intentaba cargar más allá del 100%
- **Bug 2:** `P_deferrable_nom = 0.0` cuando el viaje SÍ necesita carga pero el perfil está vacío (SOC <= 0%)

### ⏳ Pendiente
- **Bug 3:** Ventanas de carga muy pequeñas (`def_end - def_start < def_total_hours`)

Este último bug es diferente y menos crítico que los dos primeros. Los primeros dos bugs causaban que EMHASS tuviera parámetros inconsistentes o físicamente imposibles. El tercer bug causa que EMHASS se niegue a optimizar en casos extremos de ventanas muy pequeñas.

---

## Cambios Aplicados

### Archivo: `custom_components/ev_trip_planner/emhass_adapter.py`

**Líneas 672-677:** Fix Bug 1 - Verificar SOC < 100% antes de cargar
```python
if adjusted_def_total_hours > 0 and soc_current < 100.0:
    needs_charging = True
    power_watts = charging_power_kw * 1000
```

**Líneas 720-738:** Fix Bug 2 - Usar `decision.needs_charging` en lugar de perfil
```python
if adjusted_def_total_hours is not None and adjusted_def_total_hours > 0:
    def_total_hours_value = math.ceil(adjusted_def_total_hours)
    has_charging = True
elif adjusted_def_total_hours is not None and adjusted_def_total_hours == 0:
    def_total_hours_value = non_zero_hours_in_profile
    has_charging = decision.needs_charging  # KEY FIX
else:
    def_total_hours_value = non_zero_hours_in_profile
    has_charging = decision.needs_charging
```

---

## Próximos Pasos

El usuario debe:
1. **Probar en producción** con estos fixes aplicados
2. **Verificar** que los valores de `def_total_hours` y `P_deferrable_nom` son ahora consistentes
3. **Reportar** si sigue viendo el bug original o si aparecen nuevos problemas

El bug de ventanas pequeñas (test_def_start_at_zero_reduces_hours) puede ser abordado después si es necesario, pero es menos crítico que los dos bugs que acabamos de arreglar.
