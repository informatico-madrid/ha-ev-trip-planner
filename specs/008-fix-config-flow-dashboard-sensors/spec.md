# Feature Specification: Fix Config Flow Dashboard Sensors

**Feature Branch**: `[008-fix-config-flow-dashboard-sensors]`  
**Created**: 2026-03-19  
**Status**: Draft  
**Input**: User description: "Corregir problemas reportados en revisión manual de Home Assistant: ELIMINAR selector de tipo de vehículo, TRADUCIR campo charging_status_sensor, CORREGIR problema de dashboard no guardado, SOLUCIONAR sensores no actualizados"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configurar vehículo sin selector de tipo irrelevante (Priority: P1)

Como usuario que configura el EV Trip Planner, quiero poder añadir mi vehículo eléctrico sin que el sistema me pregunte si es "hibrido" o "eléctrico", ya que esta distinción no es relevante para la planificación de viajes.

**Why this priority**: La eliminación del selector de tipo de vehículo simplifica el flujo de configuración y reduce la fricción inicial para el usuario.

**Independent Test**: El usuario puede completar el flujo de configuración en 3 pasos (nombre, sensores, presencia) sin ver un selector de tipo de vehículo.

**Acceptance Scenarios**:

1. **Given** el usuario inicia la configuración del EV Trip Planner, **When** llega al primer paso del flujo, **Then** solo se muestra el campo "Vehicle Name" sin selector de tipo de vehículo
2. **Given** el usuario completa el flujo de configuración, **THEN** la entrada se crea correctamente sin el campo vehicle_type

---

### User Story 2 - Configurar sensores con ayuda traducida y clara (Priority: P1)

Como usuario hispanohablante, quiero ver todos los mensajes, labels y hints de ayuda en español para poder configurar correctamente los sensores de mi vehículo.

**Why this priority**: Los mensajes en idioma incorrecto causan confusión y errores de configuración.

**Independent Test**: El usuario puede completar el flujo de configuración sin encontrar ningún texto en inglés.

**Acceptance Scenarios**:

1. **Given** el usuario está en el paso de sensores, **When** ve el campo charging_status_sensor, **Then** el label y la descripción están en español
2. **Given** el usuario ve el hint de ayuda para charging_status_sensor, **THEN** incluye instrucciones claras sobre qué tipo de sensor buscar

---

### User Story 3 - Dashboard importado automáticamente tras configuración (Priority: P2)

Como usuario, quiero que el dashboard de EV Trip Planner se cree automáticamente cuando configuro un nuevo vehículo, para poder ver el estado de mis viajes inmediatamente.

**Why this priority**: El dashboard es la interfaz principal del componente y su ausencia tras la configuración deja al usuario sin visibilidad de la funcionalidad.

**Independent Test**: Tras completar el flujo de configuración, el dashboard aparece en la interfaz Lovelace con el nombre del vehículo.

**Acceptance Scenarios**:

1. **Given** el usuario completa el flujo de configuración de un nuevo vehículo, **When** el sistema intenta importar el dashboard, **Then** el dashboard se crea con éxito o el usuario recibe un mensaje claro si falla
2. **Given** existe un dashboard manual con el mismo nombre, **THEN** el sistema maneja el conflicto sin perder la configuración manual del usuario

---

### User Story 4 - Sensores muestran trips correctamente guardados (Priority: P1)

Como usuario, quiero que los sensores de EV Trip Planner muestren correctamente los viajes que he configurado, para poder ver el estado actual de mis viajes programados.

**Why this priority**: Los sensores son la principal forma de visibilidad del estado del sistema. Si muestran datos incorrectos, el usuario pierde confianza en el componente.

**Independent Test**: El usuario puede crear un viaje mediante el servicio `add_punctual_trip` o `add_recurring_trip` y ver inmediatamente que el sensor `trips_count` muestra el valor correcto.

**Acceptance Scenarios**:

1. **Given** el usuario crea un viaje puntual mediante el servicio, **When** los sensores se actualizan, **Then** el sensor `trips_count` muestra 1
2. **Given** el usuario crea un viaje recurrente, **THEN** el sensor `recurring_trips_count` refleja correctamente el nuevo viaje
3. **Given** existen viajes en storage, **THEN** todos los sensores muestran los datos correctos al cargar el componente

---

### Edge Cases

- ¿Qué pasa cuando el usuario tiene un dashboard manual con el mismo nombre que el dashboard automático?
- ¿Qué pasa cuando el storage de viajes no tiene permisos de escritura?
- ¿Qué pasa cuando el coordinator falla al actualizar los sensores?
- ¿Cómo se maneja la migración de datos de versiones anteriores?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema NO debe mostrar un selector de tipo de vehículo (hibrido/eléctrico) en el flujo de configuración
- **FR-002**: Todos los mensajes, labels y hints de ayuda en el flujo de configuración deben estar en español
- **FR-003**: El sistema debe intentar importar el dashboard automáticamente tras completar el flujo de configuración
- **FR-004**: El sistema sobrescribe el dashboard existente al importar automáticamente (se pierde la configuración manual previa)
- **FR-005**: Los sensores deben leer correctamente los viajes almacenados en storage
- **FR-006**: Los sensores deben actualizarse automáticamente cuando se añaden nuevos viajes
- **FR-007**: El sistema debe persistir correctamente los viajes en storage entre reinicios

### Key Entities

- **Vehicle**: Entidad principal con nombre, configuración de sensores, y parámetros de carga
- **Trip**: Viaje con tipo (recurrente/puntual), fecha/hora, distancia, energía necesaria, y estado
- **Dashboard**: Vista Lovelace que muestra el estado de viajes y métricas del vehículo
- **Sensor**: Entidad que muestra información de viajes, energía necesaria, y estado del vehículo

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El flujo de configuración se completa en menos de 5 pasos (antes tenía 5 pasos con selector irrelevante, ahora debe tener 4)
- **SC-002**: 100% de los mensajes en el flujo de configuración están en español
- **SC-003**: El dashboard se importa correctamente en al menos el 90% de las configuraciones exitosas
- **SC-004**: Los sensores muestran el número correcto de viajes después de crear un viaje (funcionalidad prioritaria sobre tiempo)
- **SC-005**: Los viajes persisten correctamente entre reinicios de Home Assistant (100% de persistencia)

## Assumptions

- El usuario tiene Home Assistant instalado con integración Lovelace disponible
- El usuario tiene permisos de escritura en el almacenamiento de Home Assistant
- Los servicios de trips (`add_punctual_trip`, `add_recurring_trip`) están disponibles y funcionando
- El usuario habla español y prefiere todos los mensajes en este idioma
- El dashboard simple es suficiente para la mayoría de los casos de uso

## Known Issues from Forensic Analysis

### Issue 1: Selector de tipo de vehículo irrelevante
El campo `vehicle_type` con opciones "hibrido" o "eléctrico" no es relevante para el caso de uso actual. Este campo debe eliminarse del flujo de configuración.

### Issue 2: charging_status_sensor sin traducción
El campo `charging_status_sensor` aparece sin traducción en el flujo de configuración. Debe traducirse al español y añadirse un hint de ayuda claro.

### Issue 3: Dashboard no importado
Tras completar el flujo de configuración, el dashboard no se crea automáticamente. Esto puede deberse a:
- Problemas de permisos de escritura en storage
- Conflicto con dashboard manual existente
- Fallo en la lógica de importación

### Issue 4: Sensores no actualizados
A pesar de que los logs confirman que los viajes se guardan correctamente en storage, los sensores muestran 0 viajes. Posibles causas:
- El storage no se persiste correctamente entre reinicios
- Los sensores leen de una fuente incorrecta (no del trip_manager)
- El coordinator no se actualiza después de crear viajes
- El path del storage file no es el correcto o no tiene permisos de escritura

## Clarifications Needed

### Dashboard Conflict Resolution
**Context**: El usuario tiene un dashboard manual "lovelace-ev-trip-planner/ev-trip-planner" que podría estar causando conflicto.

**Decision**: El sistema debe sobrescribir el dashboard manual con el dashboard automático cuando se completa el flujo de configuración.

**Rationale**: El dashboard automático es generado por el componente y contiene la configuración correcta para el vehículo. Sobrescribir el dashboard manual asegura que el usuario siempre tenga la versión más actualizada y funcional.

---

**Note**: El spec está completo y listo para proceder a la planificación.
