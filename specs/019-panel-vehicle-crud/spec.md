# Feature Specification: Panel de Control de Vehículo con CRUD de Viajes

**Feature Branch**: `019-panel-vehicle-crud`  
**Created**: 2026-03-22  
**Status**: Draft  
**Input**: User description: "Cuando se crea un vehiculo en agregar integracion de homeassistant se crea un panel en el menu principal para este vehiculo. este es el punto de control inicial que ya funciona. tenemos que hacer que este panel de control sea dependiente del vehiculo que lo creo. si elimino el vehiculo en integraciones este panel debe eliminarse. si reconfiguro el vehiculo cambiando los sensores el panel debe usar automaticamente los sensores del vehiculo. el panel deberia usar siempre los datos actualizados del vehiculo. Este panel debe listar todos los datos del vehiculo relevantes. en el config flow ahora mismo para notificaciones deben salir las notificqaciones del altavoz nabu . es un altavoz satelite que ya tiene automatizaciones con avisos y notificaicones. encontrar porque ese dispositivo de comunicación no sale en el listado actual del config flow y hacer que salida. al crear un vehiculo se me crea un device por ejemplo asi http://192.168.1.100:8123/config/devices/device/0d8f6f833e83dc74470339963eb792cc con este nombre EV Trip Planner 01KMA7JV3X1S4VW0Q4JCNQ9K66 . deberia crear usando a ser posible un slug del nombre que le pase . si le pongo nombre \"Chispitas\" deberia quedar esta url http://192.168.1.100:8123/config/devices/device/chispitas y el nombre deberia ser \"EV Trip Planner Chispitas\" al crear la integracion(vehiculo) ahora mismo se crea un panel en esta url http://192.168.1.100:8123/ev-trip-planner-chispitas pero hay un error que dice \"panel.js:187 EV Trip Planner Panel: Cannot render - no vehicle_id\" EL ERROR DEBE CORREGIRSE y el panel de control debe mostrar todos los sensores de la integracion que se acaba de crear y esta vinculada con este panel. y operaciones crud para viajes de este coche ya disponible como acciones en home assistant. Ademas de los datos o sensores basicos de la integracion(vehiculo - device) que acabamos de crear, el panel debe mostrar los viajes de este vehiculo, si no hay viajes mostrara un mensaje que diga que no hay viajes. y si hay viajes listara los viajes mostrando sus propiedades de forma bonita para humanos. y con acciones y botones CRUD mostrados de la manera mas ordenada y bonita posible , estas acciones CRUD como te digo son acciones CRUD que ya deberian existir para los viajes de los vehiculos."

## User Scenarios & Testing

### User Story 1 - Corregir error "Cannot render - no vehicle_id" en el panel nativo (Priority: P1)

**Descripción**: El panel nativo de EV Trip Planner muestra un error "Cannot render - no vehicle_id" al acceder a la URL del panel. Esto impide que el usuario vea la información del vehículo.

**Por qué esta prioridad**: Este es un error crítico que bloquea la funcionalidad básica del panel. Sin la corrección, el panel es inutilizable.

**Test Independiente**: Acceder a la URL del panel `http://HA/ev-trip-planner-{vehicle_id}` y verificar que se muestra el contenido del panel correctamente con los datos del vehículo (no error de vehicle_id).

**Acceptance Scenarios**:

1. **Dado** un vehículo creado con nombre "Chispitas", **Cuando** se accede al panel en `/ev-trip-planner-chispitas`, **Entonces** el panel debe renderizarse correctamente mostrando "EV Trip Planner - Chispitas" sin errores.
2. **Dado** un vehículo creado, **Cuando** se recarga la página del panel, **Entonces** el vehicle_id debe persistir correctamente.

---

### User Story 2 - Nombre de dispositivo personalizado con slug (Priority: P1)

**Descripción**: Al crear un vehículo, el dispositivo en Home Assistant debe usar un slug del nombre proporcionado por el usuario (en lugar del ID interno largo) y el nombre debe ser "EV Trip Planner {nombre}".

**Por qué esta prioridad**: Mejora significativamente la experiencia de usuario al identificar fácilmente los dispositivos en la página de dispositivos de HA.

**Test Independiente**: Crear un vehículo con nombre "Chispitas" y verificar que:
- La URL del dispositivo sea `/config/devices/device/chispitas`
- El nombre del dispositivo sea "EV Trip Planner Chispitas"

**Acceptance Scenarios**:

1. **Dado** el usuario ingresa "Chispitas" como nombre del vehículo en el config flow, **Cuando** se completa la configuración, **Entonces** el dispositivo se crea con identifier "chispitas" y nombre "EV Trip Planner Chispitas".
2. **Dado** el usuario ingresa "Mi Coche Eléctrico" como nombre, **Cuando** se completa la configuración, **Entonces** el dispositivo se crea con identifier "mi_coche_electrico" y nombre "EV Trip Planner Mi Coche Eléctrico".

---

### User Story 3 - Incluir dispositivos assist_satellite en selector de notificaciones (Priority: P2)

**Descripción**: El selector de notificaciones en el config flow debe mostrar los dispositivos assist_satellite (como el Home Assistant Voice Satellite) además de los servicios notify tradicionales.

**Por qué esta prioridad**: El usuario tiene automatizaciones existentes que usan `assist_satellite.announce` para notificaciones por voz. El config flow actual solo muestra domain="notify", excluyendo estos dispositivos.

**Causa raíz identificada**: En config_flow.py, STEP_NOTIFICATIONS_SCHEMA usa `selector.EntitySelectorConfig(domain="notify")`, pero los dispositivos assist_satellite están registrados en el domain "assist_satellite", no en "notify".

**Test Independiente**: En el paso de notificaciones del config flow, verificar que aparecen los dispositivos assist_satellite en el selector.

**Acceptance Scenarios**:

1. **Dado** existe un dispositivo `assist_satellite.home_assistant_voice_XXXX` en Home Assistant, **Cuando** se llega al paso de notificaciones del config flow, **Entonces** el dispositivo debe aparecer en el selector.
2. **Dado** el usuario selecciona un dispositivo assist_satellite, **Cuando** se guarda la configuración, **Entonces** el servicio debe poder usarse en las automatizaciones.

---

### User Story 4 - Panel dependiente del vehículo: eliminación automática (Priority: P1)

**Descripción**: Cuando se elimina un vehículo en Integraciones, el panel nativo creado para ese vehículo debe eliminarse automáticamente.

**Por qué esta prioridad**: Mantiene la consistencia del sistema y evita paneles huérfanos que referencian vehículos inexistentes.

**Test Independiente**: Eliminar un vehículo desde Integraciones y verificar que el panel对应的 desaparece del menú lateral.

**Acceptance Scenarios**:

1. **Dado** un vehículo "Chispitas" con panel registrado, **Cuando** se elimina el vehículo desde Integraciones, **Entonces** el panel /ev-trip-planner-chispitas debe dejar de existir.
2. **Dado** un vehículo con panel, **Cuando** se elimina, **Then** no debe haber errores en los logs relacionados con paneles huérfanos.

---

### User Story 5 - Panel dependiente del vehículo: actualización automática de sensores (Priority: P2)

**Descripción**: Si se reconfigura un vehículo cambiando los sensores en opciones, el panel debe usar automáticamente los nuevos sensores sin necesidad de recrear el panel.

**Por qué esta prioridad**: El usuario no debe tener que eliminar y recrear el vehículo para actualizar los sensores utilizados por el panel.

**Test Independiente**: Modificar los sensores de un vehículo desde las opciones de integración y verificar que el panel muestra los nuevos valores.

**Acceptance Scenarios**:

1. **Dado** un vehículo con panel activo, **Cuando** se cambian los sensores de batería en opciones, **Entonces** el panel debe mostrar los valores actualizados en la próxima actualización.
2. **Dado** un vehículo reconfigurado, **Cuando** se accede al panel, **Entonces** los datos shown deben corresponder a la última configuración guardada.

---

### User Story 6 - Panel muestra todos los sensores del vehículo (Priority: P1)

**Descripción**: El panel debe listar todos los sensores relevantes de la integración del vehículo, no solo algunos sensores básicos.

**Por qué esta prioridad**: Permite al usuario ver toda la información del vehículo en un solo lugar sin necesidad de ir a múltiples páginas.

**Test Independiente**: Acceder al panel de un vehículo y verificar que se muestran todos los sensores disponibles.

**Acceptance Scenarios**:

1. **Dado** un vehículo con múltiples sensores configurados (SOC, Range, Charging, etc.), **Cuando** se accede al panel, **Entonces** todos los sensores deben aparecer listados con sus valores actuales.
2. **Dado** un sensor que no está configurado (None), **Cuando** se muestra el panel, **Then** debe mostrarse como "No disponible" o similar en lugar de un valor incorrecto.

---

### User Story 7 - Panel muestra los viajes del vehículo con UI legible (Priority: P1)

**Descripción**: El panel debe mostrar los viajes programados del vehículo en un formato legible para humanos, incluyendo toda la información relevante de cada viaje.

**Por qué esta prioridad**: El usuario necesita ver claramente qué viajes tiene programados sin necesidad de acceder a otras secciones de HA.

**Test Independiente**: Verificar que al acceder al panel se muestran los viajes existentes con formato legible.

**Acceptance Scenarios**:

1. **Dado** un vehículo con viajes programados, **Cuando** se accede al panel, **Entonces** los viajes deben mostrarse con formato legible (ej: "Lunes a las 08:00 - Trabajo - 25km").
2. **Dado** un vehículo sin viajes, **Cuando** se accede al panel, **Entonces** debe mostrar mensaje "No hay viajes programados".

---

### User Story 8 - Panel muestra operaciones CRUD de viajes (Priority: P1)

**Descripción**: El panel debe incluir botones y acciones para las operaciones CRUD de viajes que ya están disponibles como servicios en Home Assistant.

**Por qué esta prioridad**: Permite al usuario gestionar los viajes directamente desde el panel sin necesidad de usar servicios YAML o developer tools.

**Capa existente**: Los servicios ya existen en __init__.py:
- `ev_trip_planner.trip_create` (crear)
- `ev_trip_planner.trip_update` (actualizar)
- `ev_trip_planner.delete_trip` (eliminar)
- `ev_trip_planner.pause_recurring_trip` / `resume_recurring_trip` (pausar/reanudar)
- `ev_trip_planner.complete_punctual_trip` / `cancel_punctual_trip` (completar/cancelar)

**Test Independiente**: Realizar una operación de creación de viaje desde el panel y verificar que aparece en la lista.

**Acceptance Scenarios**:

1. **Dado** un vehículo con panel abierto, **Cuando** se hace clic en "Agregar Viaje", **Then** debe abrirse un formulario para crear un nuevo viaje.
2. **Dado** un viaje existente en la lista, **Cuando** se hace clic en "Editar", **Entonces** debe mostrarse un formulario con los datos actuales para editar.
3. **Dado** un viaje existente, **Cuando** se hace clic en "Eliminar", **Entonces** debe pedirse confirmación y luego eliminar el viaje.
4. **Dado** un viaje recurrente, **Cuando** se hace clic en "Pausar", **Entonces** el viaje debe marcarse como inactivo sin eliminarse.

---

### User Story 9 - UI del panel ordenada y bonita (Priority: P2)

**Descripción**: El panel debe tener un diseño limpio y profesional, con los elementos organizados de manera clara y los botones de acción claramente visibles.

**Por qué esta prioridad**: Una buena UI mejora la experiencia de usuario y hace que el panel sea más fácil de usar.

**Test Independiente**: Verificar visualmente que el panel tiene un diseño ordenado con secciones claramente diferenciadas.

**Acceptance Scenarios**:

1. **Dado** un panel con múltiples secciones, **Cuando** se visualiza, **Entonces** las secciones deben estar claramente separadas con títulos y espacios adecuados.
2. **Dado** los botones de acción, **Cuando** se visualizan, **Entonces** deben ser fácilmente identificables y estar agrupados lógicamente.

---

### Edge Cases

- ¿Qué sucede si el vehicle_id contiene caracteres especiales? (ej: "Mi-Coche.123") - debe sanitizarse para crear un slug válido.
- ¿Qué sucede si se elimina un vehículo mientras el panel está abierto? - debe mostrar un mensaje de error o redireccionar.
- ¿Qué sucede si no hay sensores configurados para el vehículo? - debe mostrar un mensaje apropiado.
- ¿Qué sucede si el nombre del vehículo es muy largo? - debe truncarse apropiadamente en el nombre del dispositivo.

---

## Requirements

### Functional Requirements

- **FR-001**: El panel nativo debe renderizarse correctamente sin error de "vehicle_id" cuando se accede a la URL del panel.
- **FR-002**: El dispositivo en Home Assistant debe usar el slug del nombre del vehículo como identifier (no el ID interno largo).
- **FR-003**: El nombre del dispositivo debe seguir el formato "EV Trip Planner {nombre}" donde {nombre} es el nombre proporcionado por el usuario.
- **FR-004**: El selector de notificaciones en el config flow debe incluir dispositivos del dominio "assist_satellite" además de "notify".
- **FR-005**: Al eliminar un vehículo desde Integraciones, el panel asociado debe eliminarse automáticamente.
- **FR-006**: Al reconfigurar un vehículo (cambiar sensores), el panel debe reflejar automáticamente los nuevos valores.
- **FR-007**: El panel debe listar todos los sensores del vehículo con sus valores actuales.
- **FR-008**: El panel debe mostrar los viajes programados en formato legible para humanos.
- **FR-009**: El panel debe incluir operaciones CRUD para los viajes: crear, editar, eliminar, pausar/reanudar, completar/cancelar.
- **FR-010**: La UI del panel debe tener un diseño limpio con secciones claras y botones de acción visibles.

### Key Entities

- **Vehículo (Vehicle)**: Representa el coche eléctrico configurado en la integración. Incluye vehicle_id, vehicle_name, y configuración de sensores.
- **Sensor del vehículo**: Entidades de Home Assistant que proporcionan datos del vehículo (SOC, rango, carga, etc.).
- **Viaje (Trip)**: Viaje programado, ya sea recurrente (semanal) o puntual. Incluye propiedades: día/hora, distancia (km), energía (kWh), descripción, estado.
- **Panel nativo**: Página personalizada en el menú lateral de Home Assistant que muestra información del vehículo y permite gestión de viajes.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: El panel se renderiza correctamente (sin error "Cannot render - no vehicle_id") en el 100% de los accesos válidos.
- **SC-002**: El dispositivo se crea con el slug del nombre correcto y nombre legible en el 100% de las creaciones.
- **SC-003**: Los dispositivos assist_satellite aparecen en el selector de notificaciones del config flow.
- **SC-004**: El panel se elimina automáticamente cuando se elimina el vehículo asociado.
- **SC-005**: Los sensores actualizados se reflejan en el panel sin intervención manual.
- **SC-006**: Todos los sensores disponibles del vehículo se muestran en el panel.
- **SC-007**: Viajes existentes se muestran en formato legible.
- **SC-008**: Las operaciones CRUD de viajes funcionan correctamente desde el panel.
- **SC-009**: La UI del panel es usable y profesional.

---

## State Verification Plan

### Existence Check
- Verificar que el componente está desplegado: buscar en /api/components
- Verificar que las entidades existen: curl a /api/states | grep sensor.ev_trip_planner

### Effect Check
- Estado de entidad ≠ unavailable/unknown
- Log de HA muestra inicialización (buscar en logs)
- Servicios disponibles: curl a /api/services | grep ev_trip_planner

### Reality Sensor Result
- STATE_MATCH = éxito real ✓
- STATE_MISMATCH = fallo real, tarea NO marcada [x]
