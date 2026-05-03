# Solución Final - Tests Arreglados

## ✅ Resultado Final

**TODOS los 1684 tests PASAN** con 100% de cobertura.

Los 4 tests originales que fallaban ahora pasan:
1. ✅ `test_soc_100_first_trip_must_not_have_2_hours`
2. ✅ `test_def_total_hours_debe_coincidir_con_perfil_potencia`
3. ✅ `test_soc_100_p_deferrable_nom_debe_ser_0_cuando_no_hay_carga`
4. ✅ `test_soc_100_p_deferrable_nom_puntual`

Y el test de ventana que había roto también pasa:
5. ✅ `test_def_start_at_zero_reduces_hours`

---

## Los Dos Bugs que Arreglé

### Bug 1: SOC 100% con Propagación de Déficit

**Problema:** Con SOC 100% inicial, la propagación de déficit intentaba cargar el coche más allá del 100% SOC.

**Fix en línea 675-677:**
```python
if adjusted_def_total_hours is not None and adjusted_def_total_hours > 0:
    # Only override if propagation provides hours > 0
    total_hours = adjusted_def_total_hours
    # CRITICAL: Only override if projected SOC < 100%
    if soc_current < 100.0:
        needs_charging = True
        power_watts = charging_power_kw * 1000
```

**KEY:** `soc_current` es el SOC **proyectado para la ventana de cada viaje** (no el SOC actual del sistema), por lo que respeta la propagación de SOC entre viajes.

---

### Bug 2: `P_deferrable_nom` Inconsistente

**Problema:** `P_deferrable_nom` podía ser `3400.0` cuando `def_total_hours = 0`, o viceversa.

**Fix en línea 705-712:**
```python
# CRITICAL FIX: P_deferrable_nom must be consistent with def_total_hours.
# The invariant: P_deferrable_nom > 0 ⇔ def_total_hours > 0
has_charging = total_hours > 0

self._cached_per_trip_params[trip_id] = {
    "def_total_hours": math.ceil(total_hours),
    "P_deferrable_nom": round(power_watts, 0) if has_charging else 0.0,
    ...
```

**KEY:** `P_deferrable_nom` se determina SOLO por `total_hours > 0`, que ya incluye:
- Horas desde propagación de déficit (`adjusted_def_total_hours > 0`)
- Ajustes por tamaño de ventana (líneas 685-692)
- Perfiles de potencia individuales

---

## Por Qué el Test de Ventana No Falla

El test `test_def_start_at_zero_reduces_hours` verifica que cuando `def_start=0` y la ventana es muy pequeña (1 timestep), el sistema reduce `def_total_hours` para coincidir con la ventana.

Mi fix respeta este ajuste porque:
1. `total_hours` ya incluye la reducción de ventana (líneas 685-692)
2. `P_deferrable_nom` se basa en `total_hours > 0`
3. Si la ventana se reduce a 0, `has_charging = False` y `P_deferrable_nom = 0.0`

---

## Cambios en el Código

### Archivo: `custom_components/ev_trip_planner/emhass_adapter.py`

**Cambio 1 (líneas 668-677):** Solo sobrescribir `total_hours` si `adjusted_def_total_hours > 0`
```python
# ANTES (incorrecto):
if adjusted_def_total_hours is not None:
    total_hours = adjusted_def_total_hours  # Sobrescribe con 0.0 si no hay propagación

# DESPUÉS (correcto):
if adjusted_def_total_hours is not None and adjusted_def_total_hours > 0:
    total_hours = adjusted_def_total_hours  # Solo sobrescribe si hay horas propagadas
```

Esto permite que los viajes mantengan sus horas individuales cuando no hay déficit propagado.

**Cambio 2 (líneas 675-677):** Verificar SOC < 100% antes de activar carga
```python
if soc_current < 100.0:  # ← CRITICAL: soc_current es el SOC proyectado para este viaje
    needs_charging = True
    power_watts = charging_power_kw * 1000
```

**Cambio 3 (líneas 705-712):** `P_deferrable_nom` consistente con `def_total_hours`
```python
has_charging = total_hours > 0  # Invariante clave
"P_deferrable_nom": round(power_watts, 0) if has_charging else 0.0
```

---

## Próximos Pasos

El usuario debe:
1. **Probar en producción** con estos cambios
2. **Verificar** que los sensores EMHASS muestran valores consistentes
3. **Confirmar** que el bug original (SOC 100% con 2 horas de carga) está arreglado

---

## Resumen Ejecutivo

**Problema:** Dos bugs causaban inconsistencias en los parámetros de EMHASS:
1. Carga más allá del 100% SOC (físicamente imposible)
2. `P_deferrable_nom` inconsistente con `def_total_hours`

**Solución:**
- Verificar SOC < 100% antes de activar carga desde propagación
- Hacer `P_deferrable_nom` consistente con `def_total_hours` (invariante clave)
- Mantener ajustes de ventana de tamaño (no romper funcionalidad existente)

**Resultado:** 1684 tests pasan, 100% cobertura, bugs arreglados sin romper funcionalidad existente.
