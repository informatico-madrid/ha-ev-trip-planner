# SPEC: 011-fix-production-errors

## Feature ID: 011-fix-production-errors

**Status**: Draft

**Created**: 2026-03-20

**Input**: User description: "ES CRITICO - crear nueva spec, revision y ejecución de las tareas de la spec 010, dashboard sigue sin verse, análisis de errores del log,tests intensivos contra todo tipo de errores posibles, verificar contra código fuente de Home Assistant"

---

## Problema

Después de las specs 008, 009 y 010, el dashboard sigue sin funcionar y hay errores críticos en los logs de producción.

## Errores Identificados en Logs de Producción (2026-03-20)

### P001 (CRITICAL) - Sensor state_class inválido con device_class energy

**Archivo**: `custom_components/ev_trip_planner/sensor.py`
**Líneas**: 263-264

**Problema**: `KwhTodaySensor` tiene:
```python
self._attr_device_class = SensorDeviceClass.ENERGY
self._attr_state_class = SensorStateClass.MEASUREMENT  # INVALIDO!
```

**Error del log**: "Entity sensor.morgan_kwh_today is using state class 'measurement' which is impossible considering device class ('energy') it is using; expected None or one of 'total', 'total_increasing'"

**Referencia MASTERGUIDE**: 
- "LEY — ENUMS para device_class y unit_of_measurement" - DEBE utilizarse Enums canónicos
- Para device_class 'energy', state_class debe ser 'total' o 'total_increasing'

**Fix**: Cambiar `state_class` de `MEASUREMENT` a `TOTAL_INCREASING`

---

### P002 - Sensores Sin Datos del Coordinator

**Archivos**: `sensor.py` - `NextTripSensor`, `NextDeadlineSensor`, `KwhTodaySensor`

**Log Error**: "no coordinator data available" (~40+ veces en 20 minutos)

**Root Cause**: Los sensores usan `coordinator.data` pero el coordinator es None o no tiene datos

**Fix**: Verificar que el coordinator se pasa correctamente a todos los sensores

---

### P003 - Error de Búsqueda de Config Entry

**Archivo**: `sensor.py` línea 441

**Problema**: El código usa `async_get_entry(self._vehicle_id)` pero espera `entry_id`, no `vehicle_id`

**Log Error**: "No config entry found for chispitas" / "No config entry found for morgan"

**Fix**: Usar la búsqueda correcta de entry_id

---

### P004 - Storage API No Disponible en Container

**Archivo**: `trip_manager.py` líneas 85, 119

**Problema**: Usa `hass.storage.async_read()` y `hass.storage.async_write_dict()`

**Log Error**: "'HomeAssistant' object has no attribute 'storage'" / "Storage API not available for vehicle morgan"

**Root Cause**: Home Assistant Container no tiene storage API

**Fix**: Implementar fallback YAML para persistencia de trips

---

## Análisis de Código Fuente HA

### Referencias al Código Fuente de Home Assistant

El código fuente de Home Assistant está en: $HOMEASSISTANT_SRC (default: `$HOME/homeassistant`)

**APIs a verificar**:

1. **Sensor state_class + device_class**: 
   - En HA 2024+, device_class 'energy' requiere state_class 'total' o 'total_increasing'
   - NO se permite 'measurement' con 'energy'

2. **Storage API**:
   - En Container, `hass.storage` puede no estar disponible
   - Hay que verificar con `hasattr(hass, "storage")`

3. **Config Entry Lookup**:
   - Usar `hass.config_entries.async_get_entry(entry_id)` no `vehicle_id`

---

## Tareas por Prioridad

### Phase 1: P001 - Fix Sensor state_class (CRITICAL)

**Skill**: `homeassistant-best-practices`

- [ ] T001: Test P001 - Verificar que sensor con MEASUREMENT + ENERGY genera warning
- [ ] T002: Fix KwhTodaySensor - Cambiar state_class a TOTAL_INCREASING
- [ ] T003: Test P001 - Verificar fix

### Phase 2: P003 - Fix Config Entry Lookup

**Skill**: `homeassistant-config`

- [ ] T004: Test P003 - Verificar error de "No config entry found"
- [ ] T005: Fix EmhassDeferrableLoadSensor - Usar entry_id correcto
- [ ] T006: Test P003 - Verificar fix

### Phase 3: P004 - Storage API Fallback

**Skill**: `homeassistant-ops`, `python-testing-patterns`

- [ ] T007: Test P004 - Verificar que storage no disponible en Container
- [ ] T008: Implementar YAML fallback en trip_manager.py
- [ ] T009: Test P004 - Verificar persistencia con YAML fallback

### Phase 4: P002 - Coordinator Data

**Skill**: `python-testing-patterns`

- [ ] T010: Test P002 - Verificar sensores sin datos
- [ ] T011: Fix - Asegurar coordinator correcto para todos los sensores
- [ ] T012: Test P002 - Verificar fix

### Phase 5: Tests Intensivos

**Skill**: `python-testing-patterns`, `homeassistant-best-practices`

- [ ] T013: Test coverage para todos los fixes
- [ ] T014: Test edge cases - storage no disponible, config entry no existe, etc.
- [ ] T015: Verificar contra código fuente HA - confirmar APIs correctas

### Phase 6: Dashboard Verification

**Skill**: `homeassistant-dashboard-designer`

- [ ] T016: Verificar dashboard se carga correctamente
- [ ] T017: Test CRUD operations en dashboard
- [ ] T018: Verificar sin errores en logs

---

## Success Criteria

1. **Sin errores críticos**: 0 errores de tipo CRITICAL en logs
2. **Sensores funcionales**: Todos los sensores se crean sin warnings
3. **Dashboard cargado**: El dashboard aparece en el panel de control
4. **CRUD funciona**: Operaciones create/read/update/delete de viajes funcionan
5. **Tests pasan**: 100% tests passing con >80% coverage

---

## Dependencies

- pytest-homeassistant-custom-component
- Python 3.11+
- Home Assistant 2026.x

---

## Notes

- El código fuente de HA está en `/home/malka/homeassistant` - verificar APIs ahí
- Tests deben cubrir TODOS los casos de error posibles
- NO hay excusas - todo debe funcionar perfectamente
