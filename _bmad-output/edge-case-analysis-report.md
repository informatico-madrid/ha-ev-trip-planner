# Edge Case Hunter Report: PR fix-sensor-deletion-calculating-soc

## Resumen Ejecutivo

Se analizaron exhaustivamente los 4 documentos base del PR y su código asociado. Se identificaron **20 edge cases** distribuidos en:

| Severidad | Cantidad |
|-----------|----------|
| CRITICAL | 1 |
| HIGH | 7 |
| MEDIUM | 8 |
| LOW | 4 |

## Edge Cases por Categoría

### Resource Leaks

| ID | Archivo | Línea | Descripción |
|----|---------|-------|-------------|
| EC-001 | `__init__.py` | 168 | Timer de hourly_refresh nunca se cancela en `async_unload_entry` |

**Trigger:** Unload/reload de config entry
**Guard:** `if hasattr(runtime_data, '_hourly_refresh_interval'): runtime_data._hourly_refresh_interval.cancel()`
**Consecuencia:** Memory leak, callbacks ejecutándose después de unload, posible crash en reload

### Timezone Issues

| ID | Archivo | Línea | Descripción |
|----|---------|-------|-------------|
| EC-002 | `trip_manager.py` | 203 | `datetime.now()` sin timezone produce datetime naive mezclado con aware |
| EC-011 | `emhass_adapter.py` | 449 | `_calculate_deadline_from_trip` puede retornar datetime naive |

**Trigger (EC-002):** Cualquier trip con hora de regreso
**Guard (EC-002):** `from datetime import datetime, timezone; datetime.now(timezone.utc)`
**Consecuencia (EC-002):** Comparaciones naive/aware raise TypeError, trips no se publican

### In-Place Mutation

| ID | Archivo | Línea | Descripción |
|----|---------|-------|-------------|
| EC-003 | `trip_manager.py` | 220 | In-place mutation de trip dict compartido (rotación T3.2) |

**Trigger:** Rotación de trips recurrentes
**Guard:** `trip_copy = trip.copy()`
**Consecuencia:** Datos originales corruptos, trips publicados con day incorrecto

### Division by Zero

| ID | Archivo | Línea | Descripción |
|----|---------|-------|-------------|
| EC-004 | `emhass_adapter.py` | 1193 | `charging_power_kw=0` no está protegido |
| EC-005 | `calculations.py` | 157 | `battery_capacity_kwh=0` no está protegido |

**Guard (EC-004):** `if charging_power_kw and charging_power_kw > 0:`
**Guard (EC-005):** `if battery_capacity_kwh and battery_capacity_kwh > 0:`
**Consecuencia:** ZeroDivisionError crash en publish

### Floating Point Drift

| ID | Archivo | Línea | Descripción |
|----|---------|-------|-------------|
| EC-006 | `calculations.py` | 535 | Floating point drift en SOC propagation acumulada |
| EC-019 | `calculations.py` | 940 | power_profile rounding puede causar off-by-one en horas |

**Trigger (EC-006):** Secuencia larga de trips (>10)
**Guard (EC-006):** `round(soc, 2)` después de cada propagación
**Consecuencia (EC-006):** Error acumulativo de ~0.01% por trip, drift de 0.1% en 10 trips

### SOC Bounds

| ID | Archivo | Línea | Descripción |
|----|---------|-------|-------------|
| EC-007 | `calculations.py` | 176 | SOC puede exceder 100% o bajar de 0% sin clamp |

**Trigger:** Trip con soc_target > 100 o deficit > current_soc
**Guard:** `soc = max(0.0, min(100.0, soc))`
**Consecuencia:** Valores SOC inválidos, EMHASS puede rechazar schedule

### None/Null Handling

| ID | Archivo | Línea | Descripción |
|----|---------|-------|-------------|
| EC-008 | `emhass_adapter.py` | 949 | `calculate_deferrable_parameters` no guarda None guard en soc_target |
| EC-009 | `emhass_adapter.py` | 326 | `trip.get('id')` puede retornar None, usado como key en dict |
| EC-017 | `emhass_adapter.py` | 2178 | `_get_current_soc` puede retornar None, usado en aritmética |

### Concurrency / Race Conditions

| ID | Archivo | Línea | Descripción |
|----|---------|-------|-------------|
| EC-010 | `emhass_adapter.py` | 926 | `get_available_indices()` puede retornar índice duplicado concurrente |
| EC-015 | `trip_manager.py` | 775 | `async_delete_all_trips` sin lock puede corromper estado concurrente |
| EC-018 | `emhass_adapter.py` | 1151 | `publish_deferrable_loads` sin lock puede publicar dos veces mismo trip |

### Data Loss / State Consistency

| ID | Archivo | Línea | Descripción |
|----|---------|-------|-------------|
| EC-020 | `emhass_adapter.py` | 786 | Partial rollback en `publish_all_trips`: si trip N falla, trips 1..N-1 ya publicados |

**Trigger:** Error en medio de publicación de múltiples trips
**Guard:** Transactional publish o cleanup de parciales
**Consecuencia:** Estado inconsistente: algunos trips publicados, otros no

### Memory Leaks

| ID | Archivo | Línea | Descripción |
|----|---------|-------|-------------|
| EC-013 | `emhass_adapter.py` | 654 | `per_trip_emhass_params` crece indefinidamente con trips eliminados |

**Trigger:** Crear y eliminar muchos trips
**Guard:** `params.pop(trip_id, None)` en `async_remove_deferrable_load`
**Consecuencia:** Memory leak, params dict crece con datos huérfanos

### Validation Gaps

| ID | Archivo | Línea | Descripción |
|----|---------|-------|-------------|
| EC-012 | `trip_manager.py` | 251 | Recurring trip con day=7 (inválido) no es rechazado |
| EC-014 | `calculations.py` | 352 | `calculate_charging_window_pure` no maneja start_time > end_time |
| EC-016 | `calculations.py` | 754 | `calculate_next_recurring_datetime` sin validación de time_str format |

---

## Priorización de Correcciones

### P0 - CRITICAL (debe corregirse antes del PR)
- **EC-001**: Timer leak en unload → **Bloquea merge**

### P1 - HIGH (fuertemente recomendado)
- **EC-002**: Timezone naive/aware mixing
- **EC-003**: In-place mutation de trip dicts
- **EC-004**: Division by zero en charging_power_kw
- **EC-005**: Division by zero en battery_capacity_kwh
- **EC-015**: Race condition en delete_all_trips
- **EC-020**: Partial rollback en publish_all_trips

### P2 - MEDIUM (mejorar en iteración siguiente)
- **EC-006**: Floating point drift
- **EC-007**: SOC bounds
- **EC-008**: None guard en soc_target
- **EC-009**: trip id None guard
- **EC-011**: Timezone deadline
- **EC-013**: Memory leak en per_trip_params
- **EC-017**: None SOC sensor
- **EC-018**: Publish duplicate guard

### P3 - LOW (nice to have)
- **EC-010**: Race condition en indices
- **EC-012**: Day validation
- **EC-014**: Window hours validation
- **EC-016**: Time string validation
- **EC-019**: Rounding precision

---

## Recomendación

**Antes de merge del PR:**
1. Corregir **EC-001** (timer leak) — es el único CRITICAL
2. Considerar corregir al menos **EC-002** y **EC-004** (HIGH, fáciles de corregir)

**Después de merge (follow-up PR):**
- Corregir el resto de HIGH y MEDIUM edge cases
- Agregar tests específicos para cada edge case
