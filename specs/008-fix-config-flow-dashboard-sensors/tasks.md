# Implementation Tasks: fix-config-flow-dashboard-sensors

**Branch**: `008-fix-config-flow-dashboard-sensors` | **Date**: 2026-03-19 | **Spec**: [spec.md](spec.md)

## User Stories

| Story | Priority | Description |
|-------|----------|-------------|
| US1 | P1 | Configurar vehículo sin selector de tipo irrelevante |
| US2 | P1 | Configurar sensores con ayuda traducida y clara |
| US3 | P2 | Dashboard importado automáticamente tras configuración |
| US4 | P1 | Sensores muestran trips correctamente guardados |

## Dependency Graph

```
Phase 1 (Setup) → Phase 2 (Foundational) → US1 → US2 → US4 → US3
```

## Parallel Execution Opportunities

- T005 y T006 pueden ejecutarse en paralelo (archivos diferentes)
- T008 y T009 pueden ejecutarse en paralelo (archivos diferentes)
- T012 y T013 pueden ejecutarse en paralelo (modelos independientes)

## Independent Test Criteria

- **US1**: El flujo de configuración tiene exactamente 4 pasos (no 5), sin selector vehicle_type
- **US2**: Todos los mensajes en config flow están en español, charging_status_sensor tiene hint de ayuda
- **US3**: Dashboard se importa tras completar config flow
- **US4**: Sensores muestran trips count correcto después de crear viaje (funcionalidad prioritaria)

---

## Phase 1: Setup

- [ ] T001 [P] Verificar estructura del proyecto en custom_components/ev_trip_planner/
- [ ] T002 [P] Revisar manifest.json para dependencias (Home Assistant Core, voluptuous, PyYAML)

---

## Phase 2: Foundational - Forensic Analysis

### T003: Analizar config_flow.py - Eliminar selector vehicle_type

**File**: `custom_components/ev_trip_planner/config_flow.py`

**Done When**:
- [ ] Se documentan todas las ocurrencias de vehicle_type
- [ ] Se identifica el STEP_USER_SCHEMA completo
- [ ] Se identifican las constantes VEHICLE_TYPE_EV y VEHICLE_TYPE_PHEV
- [ ] Se documentan las traducciones en strings.json que deben eliminarse

---

### T004: Analizar strings.json - Traducción charging_status_sensor

**File**: `custom_components/ev_trip_planner/strings.json`

**Done When**:
- [ ] Se documenta el estado actual de charging_status_sensor (español/inglés)
- [ ] Se documenta la estructura actual de data_description
- [ ] Se documenta la traducción exacta requerida
- [ ] Se documenta el hint de ayuda sugerido

---

### T005: Analizar __init__.py - Dashboard import

**File**: `custom_components/ev_trip_planner/__init__.py`

**Done When**:
- [ ] Se documenta el flujo actual de import_dashboard
- [ ] Se documenta el comportamiento cuando dashboard existe
- [ ] Se documenta el problema de permisos de escritura (si existe)
- [ ] Se documenta el comportamiento esperado (sobrescribir)

---

### T006: Analizar sensor.py - Lectura de trips

**File**: `custom_components/ev_trip_planner/sensor.py`

**Done When**:
- [ ] Se documenta el flujo actual de lectura de trips en sensores
- [ ] Se documenta la fuente de datos (coordinator.data)
- [ ] Se documenta el problema de actualización (si existe)
- [ ] Se documenta el flujo de actualización esperado

---

### T007: Analizar trip_manager.py - Persistencia

**File**: `custom_components/ev_trip_planner/trip_manager.py`

**Done When**:
- [ ] Se documenta el uso actual de hass.data para storage
- [ ] Se documenta el namespace usado
- [ ] Se documenta el problema: hass.data no persiste entre reinicios
- [ ] Se documenta la solución: usar hass.storage.async_write_dict y async_read

---

### T008: Analizar __init__.py - Coordinator refresh

**File**: `custom_components/ev_trip_planner/__init__.py`

**Done When**:
- [ ] Se documenta el flujo actual de async_refresh_trips
- [ ] Se documenta si async_request_refresh() se llama después de crear trip
- [ ] Se documenta el problema de propagación a sensores (si existe)
- [ ] Se documenta el timing entre save y refresh

---

### T009: Analizar logs de Home Assistant

**File**: Logs de HA (no en repo)

**Done When**:
- [ ] Se documentan los logs de config_flow al crear vehículo
- [ ] Se documentan los logs de dashboard import
- [ ] Se documentan los logs de sensor updates
- [ ] Se documentan los errores de storage (si existen)
- [ ] Se documentan los logs que confirman trips guardados
- [ ] Se documentan los logs que muestran sensores con valor 0

---

## Phase 3: User Story 1 - Eliminar selector vehicle_type

### T010: Eliminar vehicle_type de config_flow.py

**File**: `custom_components/ev_trip_planner/config_flow.py`

**Tasks**:
- [ ] T010 [US1] Eliminar vehicle_type de STEP_USER_SCHEMA (líneas 50-52)
- [ ] T011 [US1] Eliminar VEHICLE_TYPE_EV y VEHICLE_TYPE_PHEV de const.py si no se usan
- [ ] T012 [US1] Actualizar async_step_user para no pasar vehicle_type al context

---

## Phase 4: User Story 2 - Traducir charging_status_sensor

### T013: Agregar traducción a strings.json

**File**: `custom_components/ev_trip_planner/strings.json`

**Tasks**:
- [ ] T013 [US2] Agregar charging_status_sensor en español en presence.data
- [ ] T014 [US2] Agregar data_description con hint de ayuda claro
- [ ] T015 [US2] Verificar todas las traducciones del config flow están en español

---

## Phase 5: User Story 4 - Sensores actualizados

### T016: Corregir persistencia de trips

**File**: `custom_components/ev_trip_planner/trip_manager.py`

**Tasks**:
- [ ] T016 [US4] Cambiar de hass.data a hass.storage para persistencia
- [ ] T017 [US4] Implementar hass.storage.async_write_dict para trips
- [ ] T018 [US4] Implementar hass.storage.async_read para cargar trips

---

### T019: Corregir refresh de coordinator

**File**: `custom_components/ev_trip_planner/__init__.py`

**Tasks**:
- [ ] T019 [US4] Verificar async_refresh_trips se llama correctamente
- [ ] T020 [US4] Agregar logging para diagnosticar problemas de refresh
- [ ] T021 [US4] Verificar que coordinator.data se actualiza antes de refresh

---

### T022: Corregir lectura de sensores

**File**: `custom_components/ev_trip_planner/sensor.py`

**Tasks**:
- [ ] T022 [US4] Verificar que sensores leen de coordinator.data correctamente
- [ ] T023 [US4] Agregar logging para diagnosticar problemas de lectura
- [ ] T024 [US4] Verificar que async_update se llama después de refresh

---

## Phase 6: User Story 3 - Dashboard import

### T025: Corregir import de dashboard

**File**: `custom_components/ev_trip_planner/__init__.py`

**Tasks**:
- [ ] T025 [US3] Modificar import_dashboard para sobrescribir dashboard existente
- [ ] T026 [US3] Agregar logging detallado para diagnosticar fallos
- [ ] T027 [US3] Verificar permisos de escritura en storage

---

## Phase 7: Tests

### T028: Tests config_flow

**File**: `tests/test_config_flow_issues.py`

**Tasks**:
- [ ] T028 [US1] Test: Config flow no tiene vehicle_type
- [ ] T029 [US2] Test: charging_status_sensor está en español
- [ ] T030 [US2] Test: charging_status_sensor tiene hint de ayuda

---

### T031: Tests sensor update

**File**: `tests/test_sensor_update.py`

**Tasks**:
- [ ] T031 [US4] Test: Sensores muestran trips después de crear viaje
- [ ] T032 [US4] Test: Sensores se actualizan después de crear viaje (funcionalidad prioritaria)
- [ ] T033 [US4] Test: Persistencia entre reinicios

---

### T034: Tests coordinator

**File**: `tests/test_coordinator_update.py`

**Tasks**:
- [ ] T034 [US4] Test: Coordinator se actualiza después de crear trip
- [ ] T035 [US4] Test: Refresh se propaga a todos los sensores

---

## Phase 8: Polish

### T036: Logging y observabilidad

**File**: `custom_components/ev_trip_planner/`

**Tasks**:
- [ ] T036 [P] Agregar logging en config flow para diagnóstico
- [ ] T037 [P] Agregar logging en dashboard import para diagnóstico
- [ ] T038 [P] Agregar logging en sensor updates para diagnóstico

---

### T039: Documentation

**File**: `custom_components/ev_trip_planner/`

**Tasks**:
- [ ] T039 [P] Actualizar README.md con cambios
- [ ] T040 [P] Actualizar CHANGELOG.md con los fixes

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| Phase 1 | 2 | Setup y verificación |
| Phase 2 | 7 | Forensic analysis de todos los problemas |
| Phase 3 | 3 | US1: Eliminar vehicle_type |
| Phase 4 | 3 | US2: Traducir charging_status_sensor |
| Phase 5 | 9 | US4: Sensores actualizados (persistencia + refresh) |
| Phase 6 | 3 | US3: Dashboard import |
| Phase 7 | 8 | Tests |
| Phase 8 | 4 | Logging y documentation |

**Total Tasks**: 40

**MVP Scope**: US1 + US2 (eliminar vehicle_type + traducir)

**Estimated Coverage**: >80% (tests incluidos)

---

## Notes

- **Forensic Analysis Required**: Cada task de errores (T003-T009) debe revisar logs y comportamiento actual antes de implementar
- **Persistence Fix**: El problema principal es que hass.data no persiste entre reinicios; usar hass.storage
- **CRITICAL**: hass.storage es la API recomendada de Home Assistant para persistencia
- **Refresh Timing**: El coordinator debe actualizar data antes de llamar async_request_refresh()
- **Dashboard Conflict**: La decisión es sobrescribir dashboard existente (ya documentada en spec.md)
- **Performance**: Funcionalidad prioritaria sobre tiempo de actualización
