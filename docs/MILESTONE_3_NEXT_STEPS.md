# 🎯 Milestone 3 - Próximos Pasos

## 📋 Resumen

Este documento detalla los pasos necesarios para completar el Milestone 3: Integración con EMHASS. Basado en el análisis del estado actual del proyecto, se identifican las tareas pendientes y el plan de acción para su completitud.

## 📊 Estado Actual

### Avances Realizados
- ✅ Se han creado los archivos principales para la integración con EMHASS
- ✅ Se han definido las constantes necesarias en `const.py`
- ✅ Se ha implementado la lógica básica en `emhass_adapter.py`
- ✅ Se han modificado `config_flow.py` para soportar la configuración de EMHASS

### Tareas Pendientes
- [ ] Configuración de parámetros de EMHASS (3A.1-3A.5)
- [ ] Implementación completa del adaptador EMHASS (3B.1-3B.5)
- [ ] Implementación del control de carga (3C.1-3C.5)
- [ ] Implementación del monitor de horarios (3D.1-3D.5)
- [ ] Implementación del monitor de presencia (3E.1-3E.5)

## 🛠️ Próximos Pasos

### Fase 1: Configuración de EMHASS (3A)
**Objetivo:** Integrar la configuración de EMHASS en el flujo de instalación

#### Tareas Pendientes:
1. **3A.1** - Adicionar constantes a `const.py`:
   - `CONF_PLANNING_HORIZON` (int, 1-30 días)
   - `CONF_HOME_SENSOR` (opcional entity_id)
   - `CONF_PLUGGED_SENSOR` (opcional entity_id)
   - `CONF_NOTIFICATION_SERVICE` (default: `persistent_notification.create`)
   - `CONF_MAX_DEFERRABLE_LOADS` (int, default: 50)

2. **3A.2** - Extender `config_flow.py` - Paso adicional "EMHASS Configuration"

3. **3A.3** - Extender `config_flow.py` - Paso adicional "Presence Detection (Opcional)"

4. **3A.4** - Crear tests de flujo de configuración

5. **3A.5** - Actualizar `sensor.py` - Nuevos sensores:
   - `sensor.{vehicle}_presence_status`
   - `sensor.{vehicle}_charging_readiness`
   - `sensor.{vehicle}_active_trips_count`

### Fase 2: Adaptador EMHASS (3B)
**Objetivo:** Publicar viajes como cargas diferibles en EMHASS

#### Tareas Pendientes:
1. **3B.1** - Implementar `emhass_adapter.py`:
   - Clase `EMHASSAdapter`
   - `__init__`: Almacenar configuración del vehículo, hass, índice

2. **3B.2** - Implementar cálculo de parámetros:
   - `def_total_hours`: `kwh / charging_power`
   - `P_deferrable_nom`: `charging_power * 1000`
   - `def_start_timestep`: 0
   - `def_end_timestep`: `(deadline - now).hours`

3. **3B.3** - Crear entidad de sensor:
   - ID de entidad: `sensor.emhass_deferrable_load_config_{index}`
   - Estado: "active" cuando se publica el viaje

4. **3B.4** - Activar en cambios de viajes:
   - Escuchar `SIGNAL_TRIPS_UPDATED_{vehicle_id}`
   - Publicar `async_publish_deferrable_load()` para cada viaje activo

5. **3B.5** - Tests unitarios:
   - Validación de cálculo de parámetros
   - Validación de creación de entidad de sensor
   - Validación de actualizaciones de viajes

### Fase 3: Control de Carga (3C)
**Objetivo:** Activar/desactivar carga física basado en condiciones de presencia

#### Tareas Pendientes:
1. **3C.1** - Implementar `vehicle_controller.py`:
   - Clase `VehicleController`
   - `__init__`: Almacenar configuración del vehículo, hass

2. **3C.2** - Implementar control de carga:
   - Método para activar carga
   - Método para desactivar carga
   - Manejo de errores

3. **3C.3** - Integrar con sensores de presencia:
   - Verificar si el vehículo está en casa
   - Verificar si el vehículo está enchufado

4. **3C.4** - Implementar notificaciones:
   - Servicio de notificaciones por defecto
   - Mensajes de estado de carga

5. **3C.5** - Tests de control de carga:
   - Validación de activación de carga
   - Validación de desactivación de carga
   - Validación de notificaciones

### Fase 4: Monitor de Horarios (3D)
**Objetivo:** Monitorear horarios de EMHASS y activar carga

#### Tareas Pendientes:
1. **3D.1** - Implementar `schedule_monitor.py`:
   - Clase `ScheduleMonitor`
   - `__init__`: Almacenar hass, controladores de vehículo

2. **3D.2** - Descubrir horarios de EMHASS:
   - Escuchar eventos de cambio de estado
   - Construir mapa: `deferrable_index -> vehicle_id`

3. **3D.3** - Analizar formato de horario:
   - Interpretar formato de horario de EMHASS
   - Determinar si se debe cargar

4. **3D.4** - Implementar control de carga basado en horario

5. **3D.5** - Tests de monitor de horarios:
   - Validación de análisis de horario
   - Validación de control de carga

### Fase 5: Monitor de Presencia (3E)
**Objetivo:** Gestionar notificaciones y seguridad basadas en presencia

#### Tareas Pendientes:
1. **3E.1** - Implementar `presence_monitor.py`:
   - Clase `PresenceMonitor`
   - `__init__`: Almacenar configuración de presencia

2. **3E.2** - Implementar notificaciones:
   - Servicio de notificaciones por defecto
   - Mensajes de estado de vehículo

3. **3E.3** - Integrar con sensores de presencia:
   - Sensor de casa (binary_sensor.*)
   - Sensor de enchufado (binary_sensor.*)

4. **3E.4** - Implementar lógica de seguridad:
   - Prevenir activación cuando el vehículo no está en casa
   - Prevenir activación cuando el vehículo no está enchufado

5. **3E.5** - Tests de monitor de presencia:
   - Validación de notificaciones
   - Validación de lógica de seguridad

## 🧪 Pruebas y Validación

### Requisitos de Prueba
- Todos los tests unitarios deben pasar
- Pruebas de integración con EMHASS
- Pruebas de carga en entornos de prueba
- Cobertura de código > 80%

### Criterios de Aceptación
- Integración funcional con EMHASS
- Manejo adecuado de errores
- Notificaciones funcionales
- Seguridad en el control de carga

## 📅 Cronograma Estimado

| Fase | Duración Estimada | Estado |
|------|-------------------|---------|
| Configuración EMHASS | 2-3 días | ⚠️ Pendiente |
| Adaptador EMHASS | 3-4 días | ⚠️ Pendiente |
| Control de Carga | 2-3 días | ⚠️ Pendiente |
| Monitor de Horarios | 3-4 días | ⚠️ Pendiente |
| Monitor de Presencia | 2-3 días | ⚠️ Pendiente |

## 📚 Recursos Adicionales

- Documentación de arquitectura: `MILESTONE_3_ARCHITECTURE_ANALYSIS.md`
- Documentación de TDD: `TDD_METHODOLOGY.md`
- Documentación de servicios: `SERVICIOS.md`
- Documentación de mejoras: `IMPROVEMENTS_POST_MILESTONE3.md`

## 🔧 Consideraciones Técnicas

1. **Agnosticismo**: El sistema debe funcionar con múltiples optimizadores
2. **Escalabilidad**: Soporte para múltiples vehículos
3. **Seguridad**: Validación de presencia antes de activar carga
4. **Monitoreo**: Registro detallado de operaciones críticas
5. **Documentación**: Actualización continua de la documentación técnica

## 🚨 Riesgos y Mitigaciones

- **Riesgo**: Falta de compatibilidad con EMHASS
  - **Mitigación**: Pruebas en entornos de prueba
- **Riesgo**: Problemas de seguridad en control de carga
  - **Mitigación**: Validación de presencia y estado de enchufado
- **Riesgo**: Complejidad de integración
  - **Mitigación**: Desarrollo modular y pruebas continuas