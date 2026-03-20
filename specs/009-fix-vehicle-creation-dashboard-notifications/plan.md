# Plan de Implementación - Fix Vehicle Creation, Dashboard, Notifications, CRUD Dashboard, High-Quality Tests

## Overview

Este plan detalla los pasos técnicos para corregir los problemas identificados e implementar todas las funcionalidades requeridas incluyendo dashboard CRUD completo y tests de alta calidad.

---

## Task Breakdown

### T001: Fix trip_manager lookup in sensor.py

**Descripción**: Corregir la búsqueda del trip_manager en sensor.py para usar el namespace correcto.

**Pasos**:
1. Analizar cómo se almacena trip_manager en `async_setup_entry` de `__init__.py`
2. Corregir la búsqueda en `sensor.py:474-478` para usar el namespace correcto
3. Añadir logging para diagnóstico
4. Probar la creación de sensores

**Archivo**: `custom_components/ev_trip_planner/sensor.py`

**Código actual**:
```python
trip_manager = hass.data.get(namespace, {}).get("trip_manager")
coordinator = hass.data.get(namespace, {}).get("coordinator")

if not trip_manager:
    trip_manager = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("trip_manager")
    coordinator = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("coordinator")
```

**Código esperado**:
```python
from . import DATA_RUNTIME

# Usar DATA_RUNTIME namespace correctamente
namespace = f"ev_trip_planner_{entry_id}"
trip_manager = hass.data.get(DATA_RUNTIME, {}).get(namespace, {}).get("trip_manager")
coordinator = hass.data.get(DATA_RUNTIME, {}).get(namespace, {}).get("coordinator")
```

**Criterios de aceptación**:
- [ ] No aparece "No trip_manager found" en el log
- [ ] Los sensores se crean correctamente
- [ ] Los sensores muestran datos válidos

---

### T002: Fix dashboard import permissions

**Descripción**: Mejorar la importación del dashboard de Lovelace con métodos fallback.

**Pasos**:
1. Analizar `import_dashboard` en `__init__.py`
2. Mejorar la verificación de Lovelace
3. Implementar fallback a `lovelace.import` service
4. Añadir logging detallado

**Archivo**: `custom_components/ev_trip_planner/__init__.py`

**Mejoras**:
1. Verificar múltiples métodos de importación
2. Fallback a `lovelace.import` service
3. Fallback a `lovelace.save` service
4. Logging detallado de cada intento

**Criterios de aceptación**:
- [ ] Dashboard se importa si hay permisos de storage
- [ ] Dashboard se importa vía service si no hay storage
- [ ] Logging claro de errores

---

### T003: Fix notification devices selector

**Descripción**: Corregir el EntitySelectorConfig para mostrar todos los dispositivos de notificación.

**Pasos**:
1. Analizar `STEP_NOTIFICATIONS_SCHEMA` en `config_flow.py`
2. Verificar configuración del EntitySelector
3. Probar diferentes configuraciones
4. Añadir fallback manual

**Archivo**: `custom_components/ev_trip_planner/config_flow.py`

**Mejoras**:
1. Verificar que el selector usa la configuración correcta
2. Añadir logging de dispositivos encontrados
3. Probar con diferentes versiones de HA

**Criterios de aceptación**:
- [ ] Dispositivos de Nabu Casa aparecen en el selector
- [ ] Todos los servicios notify son visibles
- [ ] Selección múltiple funciona

---

### T004: Implement CRUD dashboard for vehicle trips

**Descripción**: Crear dashboard Lovelace con funcionalidad CRUD completa para gestionar viajes.

**Pasos**:
1. Crear estructura de dashboard YAML con Lovelace UI
2. Implementar cards para listar viajes (recurring y punctual)
3. Implementar cards para crear viajes recurrentes (formulario)
4. Implementar cards para crear viajes puntuales (formulario)
5. Implementar cards para editar viajes (modal)
6. Implementar cards para eliminar viajes (confirmación)
7. Implementar cards para completar/pausar viajes
8. Integrar con services de Home Assistant
9. Añadir card-mod para estilos consistentes
10. Hacer dashboard responsive

**Archivos**:
- `custom_components/ev_trip_planner/dashboard/ev-trip-planner-crud.yaml`
- `custom_components/ev_trip_planner/dashboard/ev-trip-planner-full.yaml`

**Estructura del dashboard**:
```yaml
title: "EV Trip Planner - {{ vehicle_name }}"
path: "ev-trip-planner-{{ vehicle_id }}"
icon: "mdi:car-electric"
views:
  - title: "Viajes"
    cards:
      # Lista de viajes recurrentes
      - type: custom:button-card
        # ... configuración para mostrar viajes
      # Botón para crear nuevo viaje
      - type: custom:button-card
        # ... configuración para abrir modal
      # Modal para crear/editar viaje
      - type: custom:button-card
        # ... configuración del formulario
```

**Criterios de aceptación**:
- [ ] Dashboard muestra lista de viajes
- [ ] Dashboard permite crear viajes recurrentes
- [ ] Dashboard permite crear viajes puntuales
- [ ] Dashboard permite editar viajes
- [ ] Dashboard permite eliminar viajes
- [ ] Dashboard permite completar/pausar viajes
- [ ] Dashboard es responsive
- [ ] Todos los cambios se reflejan inmediatamente

---

### T005: Implement high-quality tests

**Descripción**: Implementar tests de alta calidad con mocks y fixtures para todas las funcionalidades.

**Pasos**:

#### T005.1: Setup de tests
1. Configurar pytest-homeassistant-custom-component
2. Crear fixtures base en `tests/conftest.py`
3. Crear fixtures para config entries
4. Crear fixtures para entities

**Archivo**: `tests/conftest.py`

#### T005.2: Unit tests para TripManager
1. Tests para async_setup
2. Tests para async_add_recurring_trip
3. Tests para async_add_punctual_trip
4. Tests para async_update_trip
5. Tests para async_delete_trip
6. Tests para async_pause_recurring_trip
7. Tests para async_resume_recurring_trip
8. Tests para async_complete_punctual_trip
9. Tests para async_cancel_punctual_trip
10. Tests para async_get_kwh_needed_today
11. Tests para async_get_hours_needed_today
12. Tests para async_get_next_trip

**Archivo**: `tests/test_trip_manager.py`

#### T005.3: Unit tests para VehicleController
1. Tests para async_setup
2. Tests para get_charging_power
3. Tests para get_battery_capacity
4. Tests para get_consumption

**Archivo**: `tests/test_vehicle_controller.py`

#### T005.4: Integration tests para config_flow
1. Tests para async_step_user
2. Tests para async_step_sensors
3. Tests para async_step_emhass
4. Tests para async_step_presence
5. Tests para async_step_notifications
6. Tests para async_step_init (options flow)

**Archivo**: `tests/test_config_flow.py`

#### T005.5: Service tests
1. Tests para add_recurring_trip service
2. Tests para add_punctual_trip service
3. Tests para edit_trip service
4. Tests para delete_trip service
5. Tests para pause_recurring_trip service
6. Tests para resume_recurring_trip service
7. Tests para complete_punctual_trip service
8. Tests para cancel_punctual_trip service

**Archivo**: `tests/test_services.py`

#### T005.6: Dashboard tests
1. Tests para import_dashboard
2. Tests para _load_dashboard_template
3. Tests para _save_lovelace_dashboard

**Archivo**: `tests/test_dashboard.py`

#### T005.7: Notification tests
1. Tests para notification service validation
2. Tests para notification devices selection

**Archivo**: `tests/test_notifications.py`

#### T005.8: Sensor tests
1. Tests para TripPlannerSensor
2. Tests para async_update

**Archivo**: `tests/test_sensor.py`

**Criterios de aceptación**:
- [ ] Tests unitarios para TripManager
- [ ] Tests unitarios para VehicleController
- [ ] Tests de integración para config_flow
- [ ] Tests de servicios para todos los services
- [ ] Tests de dashboard
- [ ] Tests de notificaciones
- [ ] Tests de sensores
- [ ] Cobertura > 90%
- [ ] Todos los tests pasan en CI/CD

---

### T006: Add comprehensive logging

**Descripción**: Añadir logging detallado para troubleshooting y debugging.

**Pasos**:
1. Añadir logging en puntos clave del config flow
2. Añadir logging en sensor.py para troubleshooting
3. Añadir logging en __init__.py para dashboard import
4. Añadir logging en trip_manager.py para operaciones

**Archivo**: Múltiples archivos

**Criterios de aceptación**:
- [ ] Logging detallado del flujo de configuración
- [ ] Logging de errores con contexto
- [ ] Logging de intentos de importación

---

### T007: Test and validate

**Descripción**: Probar todas las correcciones con un vehículo nuevo.

**Pasos**:
1. Crear vehículo de prueba "test-vehicle"
2. Verificar que no hay errores en el log
3. Verificar dashboard se crea
4. Verificar notificaciones aparecen
5. Verificar sensores funcionan
6. Ejecutar todos los tests
7. Verificar cobertura > 90%

**Criterios de aceptación**:
- [ ] Sin errores en log
- [ ] Dashboard creado o error reportado
- [ ] Notificaciones visibles
- [ ] Sensores funcionales
- [ ] Todos los tests pasan
- [ ] Cobertura > 90%

---

## Implementation Order

1. **T001** - Fix trip_manager lookup (crítico, bloquea funcionalidad)
2. **T002** - Fix dashboard import (mejora UX)
3. **T003** - Fix notification selector (mejora UX)
4. **T004** - Implement CRUD dashboard (nueva funcionalidad)
5. **T005** - Implement high-quality tests (calidad)
6. **T006** - Add comprehensive logging (diagnóstico)
7. **T007** - Test and validate (validación)

---

## Testing Strategy

### Test Pyramid
```
        / E2E Tests (10%)
       /
      / Integration Tests (30%)
     /
    / Unit Tests (60%)
   /
```

### Test Categories

#### Unit Tests
- TripManager con mocks de HA
- VehicleController con fixtures
- Utils functions con datos de prueba

#### Integration Tests
- ConfigFlow con mocks de entidades
- Services con config entries reales
- Dashboard con mocks de Lovelace

#### E2E Tests
- Config flow completo
- CRUD operations en dashboard
- Notification flow completo

---

## Risk Assessment

| Task | Risk | Mitigation |
|------|------|------------|
| T001 | Bajo | Cambio directo de namespace, fácil de revertir |
| T002 | Medio | Múltiples métodos fallback, no bloquea config flow |
| T003 | Medio | EntitySelector puede variar por versión HA |
| T004 | Alto | CRUD en Lovelace es complejo, requiere card-mod |
| T005 | Medio | Tests de HA requieren fixtures específicas |
| T006 | Bajo | Solo logging, sin impacto funcional |
| T007 | Bajo | Pruebas manuales, fácil de revertir |

---

## Dependencies

- Home Assistant Core >= 2024.x
- Lovelace UI (para dashboard import y CRUD)
- Notify integration (para dispositivos de notificación)
- EMHASS (opcional, para planificación avanzada)
- pytest-homeassistant-custom-component (para tests)
- card-mod (para estilos en dashboard)

---

## Rollback Plan

Si las correcciones causan problemas:
1. Revertir cambios de sensor.py a versión anterior
2. Deshabilitar dashboard import automático
3. Usar configuración manual de notificaciones
4. Eliminar dashboard CRUD temporalmente
5. Revertir tests a versión anterior

---

## Best Practices

### Home Assistant 2026 Patterns
- Usar `runtime_data` para storage en memoria
- Usar `hass.storage` para persistencia
- Usar `async_setup_entry` para configuración
- Usar `ConfigEntry` para configuración del usuario
- Usar `ServiceCall` para servicios

### Test Best Practices
- Usar `pytest-homeassistant-custom-component` fixtures
- Usar `MockConfigEntry` para config entries
- Usar `hass` fixture para Home Assistant instance
- Usar `async_test_home_assistant` para tests asíncronos
- Usar `entity_registry` para entidades
- Usar `device_registry` para dispositivos

### Code Best Practices
- Type hints en todas las funciones
- Docstrings en todas las clases y funciones
- Logging apropiado en todos los puntos críticos
- Error handling con try/except específico
- Validation de inputs con voluptuous

---

## Milestones

### Milestone 1: Fix Critical Errors (Day 1-2)
- [ ] T001: Fix trip_manager lookup
- [ ] T002: Fix dashboard import
- [ ] T003: Fix notification selector

### Milestone 2: CRUD Dashboard (Day 3-5)
- [ ] T004: Implement CRUD dashboard
- [ ] T006: Add comprehensive logging

### Milestone 3: High-Quality Tests (Day 6-8)
- [ ] T005.1: Setup de tests
- [ ] T005.2: Unit tests para TripManager
- [ ] T005.3: Unit tests para VehicleController
- [ ] T005.4: Integration tests para config_flow
- [ ] T005.5: Service tests
- [ ] T005.6: Dashboard tests
- [ ] T005.7: Notification tests
- [ ] T005.8: Sensor tests

### Milestone 4: Validation (Day 9)
- [ ] T007: Test and validate
- [ ] Code review
- [ ] Documentation update

---

## Estimated Timeline

## Success Metrics

1. **Funcionalidad**: 100% de las funcionalidades requeridas implementadas
2. **Calidad de tests**: >90% de cobertura de código
3. **Errores**: 0 errores en log después de configuración
4. **Dashboard**: CRUD completo funcional
5. **Notificaciones**: Todos los dispositivos visibles
6. **Sensores**: Todos los sensores funcionales

## Non-Functional Requirements

### Performance
- Dashboard debe cargar en < 2 segundos para < 100 viajes
- CRUD operations deben completar en < 1 segundo
- Sensor updates deben reflejarse en < 5 segundos

### Accessibility
- Dashboard debe ser navegable con teclado (tabindex, focus management)
- Todos los elementos interactivos deben tener aria-labels
- Contraste de color mínimo 4.5:1 para texto

### Reliability
- Dashboard debe manejar errores de API con fallback
- CRUD operations deben tener confirmación antes de acciones destructivas
- State debe persistir entre refreshes del navegador
