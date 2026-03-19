# Implementation Plan: Fix Config Flow Dashboard Sensors

**Branch**: `[008-fix-config-flow-dashboard-sensors]` | **Date**: 2026-03-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-fix-config-flow-dashboard-sensors/spec.md`

## Summary

Este plan aborda 4 problemas críticos identificados en la revisión manual de Home Assistant:

1. **Eliminar selector de tipo de vehículo irrelevante** (hibrido/eléctrico)
2. **Traducir campo charging_status_sensor** y agregar hint de ayuda en español
3. **Corregir importación de dashboard** tras config flow (sobrescribir dashboard existente)
4. **Solucionar sensores no actualizados** - trips se guardan pero sensores muestran 0

## Technical Context

**Language/Version**: Python 3.11+ (Home Assistant integration)  
**Primary Dependencies**: Home Assistant Core, voluptuous, PyYAML  
**Storage**: Home Assistant storage (JSON files in .storage)  
**Testing**: pytest con coverage >80% (`pytest tests/ -v --cov=custom_components/ev_trip_planner`)  
**Target Platform**: Home Assistant Container (Linux)  
**Project Type**: Home Assistant Custom Component  
**Performance Goals**: Sensores actualizados después de crear trip (tiempo no crítico, funcionalidad es prioritaria)
**Constraints**: Cumplir reglas HA 2026 para runtime_data y tipado estricto  
**Scale/Scope**: Componente para 1-5 vehículos por instalación

## Constitution Check

| Gate | Status | Notes |
|------|--------|-------|
| Code Style (88 chars) | ✅ Pass | Seguir guía de estilo del proyecto |
| Type Hints | ✅ Pass | Requeridos en todas las funciones públicas |
| Docstrings Google Style | ✅ Pass | Obligatorio en funciones públicas |
| Imports (isort) | ✅ Pass | stdlib → third party → HA → local |
| Async/Await | ✅ Pass | Usar async/await, sin blocking calls |
| Testing >80% coverage | ✅ Pass | Requerido para código de producción |
| Conventional Commits | ✅ Pass | formato: feat: / fix: / docs: |

**Sin violaciones de constitución.**

## Phase 0: Research (No se requiere - todas las clarificaciones resueltas)

El spec no contiene markers [NEEDS CLARIFICATION]. La decisión sobre dashboard conflict resolution fue tomada por el usuario (Option A: sobrescribir).

## Phase 1: Design

### Documentos a generar

1. **data-model.md** - Entidades y relaciones
2. **quickstart.md** - Guía rápida de implementación

### Estructura del Proyecto

```text
custom_components/ev_trip_planner/
├── __init__.py          # Coordinators y servicios
├── config_flow.py       # Flujo de configuración (MODIFICAR)
├── sensor.py            # Sensores (MODIFICAR)
├── trip_manager.py      # Gestión de trips (MODIFICAR)
├── strings.json         # Traducciones (MODIFICAR)
└── dashboard/           # Dashboard templates
    └── ev-trip-planner-simple.yaml
    └── ev-trip-planner-full.yaml

tests/
├── test_config_flow_issues.py    # Tests config flow
├── test_sensor_update.py         # Tests sensores
└── test_coordinator_update.py    # Tests coordinator
```

### Cambios Técnicos Requeridos

#### 1. config_flow.py - Eliminar selector vehicle_type
- Remover campo `vehicle_type` del STEP_USER_SCHEMA (líneas 50-52)
- Remover constantes VEHICLE_TYPE_EV y VEHICLE_TYPE_PHEV si no se usan
- Actualizar strings.json para quitar traducciones de vehicle_type

#### 2. strings.json - Traducir charging_status_sensor
- Agregar entrada para charging_status_sensor en español
- Añadir data_description con hint de ayuda claro

#### 3. __init__.py - Corregir dashboard import
- Modificar función `import_dashboard` para sobrescribir dashboard existente
- Mejorar logging para diagnosticar fallos

#### 4. sensor.py / __init__.py - Corregir actualización de sensores
- Verificar que coordinator.use `trip_manager._trips` correctamente
- Asegurar que `async_refresh_trips()` llama a `coordinator.async_request_refresh()`
- Posible problema: trip_manager guarda en `hass.data[namespace]` pero sensors leen de otra fuente

#### 5. trip_manager.py - Persistencia con hass.storage
- Usar `hass.storage.async_write_dict()` para persistir trips
- Usar `hass.storage.async_read()` para cargar trips
- hass.storage es la API recomendada de Home Assistant para persistencia entre reinicios
- hass.data NO persiste entre reinicios (es memoria temporal)

## Complexity Tracking

No hay violaciones que requieran justificación.

## Next Steps

1. Crear data-model.md con entidades del dominio
2. Crear quickstart.md con guía de implementación
3. Ejecutar `/speckit.tasks` para generar tareas de implementación
4. Implementar cambios siguiendo TDD
5. Verificar coverage >80%
