# Fix Vehicle Creation, Dashboard Import, Notifications, and CRUD Dashboard

**Feature ID**: 009-fix-vehicle-creation-dashboard-notifications  
**Status**: Draft  
**Created**: 2026-03-20  
**Component**: EV Trip Planner Integration  
**Priority**: Critical

---

## Problem Summary

Al configurar un nuevo vehículo llamado "chispitas", se produjeron los siguientes errores críticos:

1. **Error de trip_manager**: `No trip_manager found for chispitas` - Los sensores no pueden acceder al gestor de viajes
2. **Dashboard no se crea**: El dashboard de Lovelace no se importa automáticamente
3. **Notificaciones no aparecen**: Los dispositivos de notificación de Nabu Casa no se muestran en el selector
4. **Dashboard sin CRUD**: El dashboard actual no tiene funcionalidad completa para gestionar viajes

---

## User Scenarios

### Scenario 1: Crear vehículo con notificaciones
**Como** usuario que configura un nuevo vehículo eléctrico  
**Quiero** poder seleccionar dispositivos de notificación de Nabu Casa  
**Para** recibir alertas en mis altavoces inteligentes

### Scenario 2: Dashboard automático con CRUD
**Como** usuario que configura un nuevo vehículo  
**Quiero** que se cree automáticamente un dashboard de Lovelace con CRUD completo  
**Para** gestionar viajes recurrentes y puntuales sin usar services

### Scenario 3: Sensores funcionales
**Como** usuario que configura un nuevo vehículo  
**Quiero** que los sensores se creen correctamente  
**Para** ver el estado del vehículo y viajes programados

### Scenario 4: Dashboard CRUD - Crear viaje
**Como** usuario con dashboard de Lovelace  
**Quiero** crear viajes recurrentes y puntuales desde el dashboard  
**Para** planificar mis viajes sin usar la UI de Home Assistant

### Scenario 5: Dashboard CRUD - Editar/Eliminar viaje
**Como** usuario con dashboard de Lovelace  
**Quiero** editar y eliminar viajes desde el dashboard  
**Para** mantener actualizada mi planificación

---

## Functional Requirements

### FR-001: Fix trip_manager lookup in sensor.py
**Descripción**: Corregir la búsqueda del trip_manager en el namespace correcto  
**Criterios de aceptación**:
- El sensor.py debe acceder al trip_manager desde el namespace correcto (`ev_trip_planner_{entry_id}`)
- Los sensores deben crearse sin errores "No trip_manager found"
- Los sensores deben mostrar datos válidos después de la configuración

### FR-002: Fix dashboard import permissions
**Descripción**: Corregir la importación del dashboard cuando no hay permisos de storage  
**Criterios de aceptación**:
- El sistema debe verificar la disponibilidad de Lovelace antes de intentar importar
- Si no hay permisos de storage, el sistema debe intentar el método fallback (lovelace.import service)
- El dashboard debe crearse o reportar claramente el error
- El flujo de configuración no debe fallar si el dashboard no se importa

### FR-003: Fix notification devices selector
**Descripción**: Corregir el selector de entidades para mostrar todos los dispositivos de notificación  
**Criterios de aceptación**:
- El selector debe mostrar dispositivos de notificación de Nabu Casa (altavoces)
- El selector debe mostrar todos los servicios de notificación disponibles en HA
- El selector debe permitir selección múltiple de dispositivos

### FR-004: Implement CRUD dashboard for vehicle trips
**Descripción**: Crear dashboard Lovelace con funcionalidad CRUD completa para gestionar viajes
**Criterios de aceptación**:
- Dashboard debe tener vista para listar viajes recurrentes y puntuales
- Dashboard debe permitir crear nuevos viajes recurrentes (formulario con día_semana, hora, km, kwh, descripcion)
- Dashboard debe permitir crear nuevos viajes puntuales (formulario con datetime, km, kwh, descripcion)
- Dashboard debe permitir editar viajes existentes (modal con campos editables)
- Dashboard debe permitir eliminar viajes (confirmación antes de eliminar)
- Dashboard debe permitir completar viajes puntuales
- Dashboard debe permitir pausar/reanudar viajes recurrentes
- Todos los cambios deben reflejarse inmediatamente en el dashboard
- Dashboard debe usar card-mod para estilos consistentes
- Dashboard debe ser responsive y funcionar en móvil
- Dashboard debe cargar en < 2 segundos para < 100 viajes

### FR-005: Implement high-quality tests
**Descripción**: Implementar tests de alta calidad con mocks y fixtures para todas las funcionalidades  
**Criterios de aceptación**:
- Tests unitarios para TripManager con mocks de Home Assistant
- Tests unitarios para VehicleController con fixtures de configuración
- Tests de integración para config_flow con mocks de entidades
- Tests de servicio para todos los services (add_recurring, add_punctual, edit, delete, pause, resume, complete, cancel)
- Tests de dashboard con mocks de Lovelace
- Tests de notificaciones con mocks de notify service
- Cobertura de tests > 90%
- Todos los tests deben pasar en CI/CD
- Tests deben usar pytest-homeassistant-custom-component best practices

---

## Success Criteria

1. **Funcionalidad completa**: El usuario puede crear un vehículo nuevo sin errores en el log
2. **Dashboard importado**: El dashboard de Lovelace se crea automáticamente o se reporta el error claramente
3. **Notificaciones visibles**: Los dispositivos de notificación de Nabu Casa aparecen en el selector
4. **Sensores funcionales**: Todos los sensores se crean y actualizan correctamente
5. **Dashboard CRUD**: El dashboard permite crear, editar, eliminar, completar, pausar y reanudar viajes
6. **Tests de alta calidad**: Todos los tests pasan con >90% de cobertura
7. **Sin errores en log**: No aparecen mensajes de error "No trip_manager found" después de la configuración

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

---

## Key Entities

| Entidad | Descripción |
|---------|-------------|
| TripManager | Gestor central de viajes y configuración del vehículo |
| TripPlannerSensor | Clase base para todos los sensores del componente |
| ConfigFlow | Flujo de configuración de 5 pasos (vehicle, sensors, emhass, presence, notifications) |
| LovelaceDashboard | Dashboard YAML que se importa automáticamente con CRUD |
| NotificationDevices | Lista de dispositivos de notificación disponibles |
| Trip | Viaje recurrente o puntual con estado y atributos |
| TestFixtures | Fixtures para tests de Home Assistant |

---

## Data Model

### Trip Entity
```yaml
Trip:
  id: str (trip_id generado)
  tipo: str (recurrente | puntual)
  dia_semana: str (opcional, para recurrente)
  datetime: str (opcional, para puntual)
  km: float
  kwh: float
  descripcion: str
  estado: str (pendiente | completado | cancelado)
  activo: bool (para recurrente)
```

### TripManager State
```python
{
    "_recurring_trips": {
        trip_id: Trip,
        ...
    },
    "_punctual_trips": {
        trip_id: Trip,
        ...
    },
    "_last_update": datetime
}
```

---

## Assumptions

1. **Home Assistant Container**: La instalación no tiene supervisor, por lo que el storage API puede no estar disponible
2. **Lovelace disponible**: El usuario tiene Lovelace instalado pero puede no tener permisos de escritura
3. **Nabu Casa notificaciones**: Los dispositivos de notificación de Nabu Casa usan el domain `notify` y son visibles en HA
4. **Config entry ID**: Cada config entry tiene un `entry_id` único que se usa para namespacing en `hass.data`
5. **pytest-homeassistant-custom-component**: Se usa esta librería para tests de Home Assistant
6. **card-mod**: Se usa card-mod para estilos en el dashboard
7. **Home Assistant 2026**: Se usa la API runtime_data y patterns modernos de HA

---

## Technical Notes

### Root Cause Analysis

**Problema 1: No trip_manager found**
- **Ubicación**: `custom_components/ev_trip_planner/sensor.py:474-478`
- **Causa**: El sensor busca el trip_manager en `hass.data.get(namespace, {})` pero el namespace está mal construido
- **Solución**: Usar el entry_id correcto y acceder a `hass.data[DATA_RUNTIME][namespace]`

**Problema 2: Dashboard no se importa**
- **Ubicación**: `custom_components/ev_trip_planner/__init__.py:284-295`
- **Causa**: `hass.storage` no está disponible en instalación Container
- **Solución**: Implementar fallback al servicio `lovelace.import` o usar `lovelace.save` service

**Problema 3: Notificaciones no aparecen**
- **Ubicación**: `custom_components/ev_trip_planner/config_flow.py:127-138`
- **Causa**: EntitySelectorConfig con domain="notify" puede no mostrar todos los servicios
- **Solución**: Verificar que el selector use la configuración correcta y mostrar todos los servicios notify

**Problema 4: Dashboard sin CRUD**
- **Ubicación**: `custom_components/ev_trip_planner/dashboard/`
- **Causa**: Los dashboards actuales solo muestran datos, no permiten edición
- **Solución**: Crear nuevo dashboard con Lovelace UI con cards para CRUD (button-card, custom:button-card, template)

**Problema 5: Tests de baja calidad**
- **Ubicación**: `tests/`
- **Causa**: Tests incompletos, falta de mocks y fixtures
- **Solución**: Implementar tests con pytest-homeassistant-custom-component, mocks de entidades, fixtures de configuración

---

## Implementation Approach

### Phase 1: Fix Critical Errors
1. Corregir trip_manager lookup en sensor.py
2. Corregir dashboard import con fallback methods
3. Corregir notification devices selector

### Phase 2: Implement CRUD Dashboard
1. Crear dashboard YAML con estructura CRUD
2. Implementar cards para listar viajes
3. Implementar cards para crear viajes
4. Implementar cards para editar viajes
5. Implementar cards para eliminar viajes
6. Implementar cards para completar/pausar viajes
7. Integrar con services de Home Assistant
8. Añadir card-mod para estilos

### Phase 3: Implement High-Quality Tests
1. Configurar fixtures de pytest-homeassistant-custom-component
2. Implementar mocks de Home Assistant entities
3. Implementar tests unitarios para TripManager
4. Implementar tests unitarios para VehicleController
5. Implementar tests de integración para config_flow
6. Implementar tests de servicios
7. Implementar tests de dashboard
8. Implementar tests de notificaciones
9. Asegurar >90% cobertura de tests

### Phase 4: Documentation and Validation
1. Documentar todas las APIs y servicios
2. Crear quickstart.md para desarrollo
3. Validar todos los tests en CI/CD
4. Documentar patterns y best practices

---

## Testing Requirements

### Unit Tests
- [ ] TripManager tests con mocks de HA
- [ ] VehicleController tests con fixtures
- [ ] ConfigFlow tests con mocks de entidades
- [ ] Sensor tests con mocks de coordinators

### Integration Tests
- [ ] Service tests para todos los services
- [ ] Dashboard tests con mocks de Lovelace
- [ ] Notification tests con mocks de notify
- [ ] End-to-end tests para config flow

### Test Quality Requirements
- [ ] Cobertura > 90%
- [ ] Todos los tests deben pasar en CI/CD
- [ ] Tests deben ser independientes y reproducibles
- [ ] Tests deben usar pytest-homeassistant-custom-component best practices
- [ ] Tests deben tener fixtures reutilizables
- [ ] Tests deben tener mocks para entidades externas

---

## Dependencies

- Home Assistant Core >= 2024.x (runtime_data API)
- Lovelace UI (para dashboard import y CRUD)
- Notify integration (para dispositivos de notificación)
- EMHASS (opcional, para planificación avanzada)
- pytest-homeassistant-custom-component (para tests)
- card-mod (para estilos en dashboard)

---

## Open Questions

1. ¿Qué método de importación de dashboard es más compatible con diferentes versiones de HA?
2. ¿El EntitySelectorConfig con domain="notify" es suficiente o se necesita una configuración adicional?
3. ¿Qué permisos de storage son necesarios para que funcione la importación automática?
4. ¿Qué pattern de Lovelace UI es mejor para CRUD: custom:button-card o custom:card-modder?
5. ¿Cómo manejar actualizaciones en tiempo real en el dashboard sin refresh manual?

---

## Migration Notes

### Breaking Changes
- Namespace de hass.data cambia de `hass.data[DOMAIN]` a `hass.data[DATA_RUNTIME]`
- TripManager storage cambia a usar hass.storage.async_write_dict

### Backward Compatibility
- Dashboard import es opcional, no bloquea config flow
- Services mantienen compatibilidad con versiones anteriores
- Tests son backward compatible con pytest-homeassistant-custom-component
