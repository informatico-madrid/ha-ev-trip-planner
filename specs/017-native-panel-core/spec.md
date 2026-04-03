# Feature Specification: Panel de Control Nativo Integrado en Home Assistant Core

**Feature Branch**: `017-native-panel-core`  
**Created**: 2026-03-21  
**Status**: Draft  
**Input**: User description: "Crear panel de control nativo integrado en el core de Home Assistant usando panel_custom en lugar de depender de Lovelace"

## Resumen Ejecutivo

El problema actual es que el dashboard de EV Trip Planner depende completamente de Lovelace UI, que no siempre está disponible (especialmente en instalaciones Container sin modo storage). Cuando Lovelace no está disponible, el dashboard genera un archivo YAML que requiere intervención manual del usuario, lo cual es inaceptable para un proyecto que debe ser "totalmente automático y nativo".

La solución es utilizar el componente `panel_custom` del core de Home Assistant para crear un panel de control nativo que:
- Se integre en el sidebar de Home Assistant como los paneles del core (configuración, desarrolladores, etc.)
- No dependa de Lovelace UI
- Se cree automáticamente cuando se configura un vehículo
- Funcione en todas las instalaciones de Home Assistant (Core, Container, Supervised, OS)

### Decisiones de Diseño Confirmadas

- **Un panel por vehículo**: Cada vehículo configurado tendrá su propio panel en el sidebar (ej: "EV Tesla Model 3", "EV Nissan Leaf")
- **Eliminación automática**: Cuando se elimina un vehículo, el panel correspondiente se elimina automáticamente del sidebar
- **Actualización en tiempo real**: El panel se actualiza automáticamente cuando los datos de los sensores cambian

## Análisis del Core de Home Assistant

### Cómo funcionan los paneles del core

Home Assistant proporciona el componente `panel_custom` que permite crear paneles personalizados integrados en el core. La API principal es:

```python
from homeassistant.components.panel_custom import async_register_panel

await async_register_panel(
    hass,
    frontend_url_path="ev-trip-planner",
    webcomponent_name="ev-trip-planner-panel",
    sidebar_title="EV Trip Planner",
    sidebar_icon="mdi:car-electric",
    module_url="/local/ev_trip_planner/panel.js",
    config={"vehicle_id": "tesla_model_3"},
)
```

Este método registra el panel en `hass.data[DATA_PANELS]` y lo hace aparecer en el sidebar de Home Assistant automáticamente.

### Diferencias con Lovelace

| Aspecto | Lovelace Dashboard | Panel Custom Nativo |
|---------|-------------------|-------------------|
| Dependencia | Requiere Lovelace UI instalado | Funciona en cualquier instalación HA |
| Creación | Manual o via API storage | Automático via código Python |
| Sidebar | No aparece en sidebar | Aparece como panel del core |
| Intervención manual | Requiere importación manual | Completamente automático |
| Actualización | Requiere re-importación | Se actualiza con la integración |

## User Scenarios & Testing

### User Story 1 - Creación automática del panel al configurar vehículo (Priority: P1)

**Como** usuario de EV Trip Planner,  
**Quiero** que al configurar un vehículo desde el config flow se cree automáticamente un panel de control en el sidebar de Home Assistant,  
**Para** que pueda acceder inmediatamente al dashboard sin configuración adicional.

**Why this priority**: Esta es la funcionalidad core del proyecto. Sin ella, el dashboard requiere intervención manual, lo cual es inaceptable.

**Independent Test**: 
- Configurar un nuevo vehículo mediante el config flow
- Verificar que aparece un nuevo panel en el sidebar de Home Assistant
- El panel debe mostrar información del vehículo sin errores

**Acceptance Scenarios**:

1. **Given** el usuario tiene Home Assistant Container sin Lovelace storage, **When** configura un vehículo mediante el config flow, **Then** el panel de EV Trip Planner aparece automáticamente en el sidebar

2. **Given** el usuario tiene Home Assistant OS con Lovelace, **When** configura un vehículo, **Then** el panel nativo se crea además del dashboard Lovelace (ambos funcionan)

3. **Given** hay múltiples vehículos configurados, **When** se crea el segundo vehículo, **Then** aparece un segundo panel en el sidebar con el nombre del vehículo

---

### User Story 2 - Ver información del vehículo en el panel nativo (Priority: P1)

**Como** usuario,  
**Quiero** ver el estado actual del vehículo (SOC, autonomía, carga) en el panel nativo,  
**Para** tomar decisiones informadas sobre mis viajes.

**Why this priority**: Información básica que el usuario necesita para planificar viajes.

**Independent Test**:
- Acceder al panel desde el sidebar
- Verificar que se muestra el estado actual del vehículo
- Los datos deben coincidir con los sensores de Home Assistant

**Acceptance Scenarios**:

1. **Given** el vehículo está configurado y los sensores existen, **When** el usuario abre el panel, **Then** se muestra: estado de carga, nivel de batería, autonomía estimada

2. **Given** el vehículo está cargando, **When** se muestra el panel, **Then** se indica tiempo restante de carga y potencia de carga actual

---

### User Story 3 - Gestionar viajes desde el panel nativo (Priority: P1)

**Como** usuario,  
**Quiero** poder crear, editar y eliminar viajes desde el panel nativo,  
**Para** gestionar mis desplazamientos sin necesidad de Lovelace.

**Why this priority**: CRUD completo de viajes es funcionalidad esencial que debe funcionar sin depender de Lovelace.

**Independent Test**:
- Crear un nuevo viaje desde el panel
- Editar un viaje existente
- Eliminar un viaje
- Verificar que los cambios se reflejan en los sensores de HA

**Acceptance Scenarios**:

1. **Given** el usuario está en el panel nativo, **When** hace clic en "Crear viaje", **Then** se muestra un formulario con: destino, fecha/hora salida, SOC objetivo

2. **Given** existe un viaje programado, **When** el usuario lo selecciona, **Then** puede editar destino, hora, o eliminar el viaje

3. **Given** se elimina un viaje, **When** se confirma la eliminación, **Then** el viaje desaparece de la lista y se actualizan los sensores

---

### User Story 4 - Ver perfil de carga diferible (Priority: P2)

**Como** usuario con EMHASS configurado,  
**Quiero** ver el perfil de carga diferible en el panel nativo,  
**Para** verificar cuándo se cargará el vehículo según la optimización.

**Why this priority**: Información importante para usuarios que usan optimización de energía.

**Independent Test**:
- Con EMHASS configurado, abrir el panel
- Verificar que se muestra el gráfico de carga
- Los datos deben coincidir con el sensor EMHASS

**Acceptance Scenarios**:

1. **Given** EMHASS está configurado y hay cargas diferibles activas, **When** se abre el panel, **Then** se muestra un gráfico de las próximas 24-48 horas con los momentos de carga programados

2. **Given** EMHASS no está configurado, **When** se abre el panel, **Then** se muestra un mensaje indicando que EMHASS no está disponible

---

### User Story 5 - Fallback cuando panel_custom no está disponible (Priority: P2)

**Como** usuario,  
**Quiero** que si el panel_custom no está disponible, el sistema tenga un comportamiento degradado apropiado,  
**Para** que no falle silenciosamente.

**Why this priority**: Manejo de errores robusto para todas las instalaciones de HA.

**Independent Test**:
- Simular un entorno donde panel_custom no está disponible
- Verificar que se usa el fallback de YAML o se muestra un error claro
- Verificar que el error se registra apropiadamente

**Acceptance Scenarios**:

1. **Given** el componente panel_custom no está disponible en HA, **When** se intenta crear un vehículo, **Then** se usa el fallback de archivo YAML y se notifica al usuario

2. **Given** el componente panel_custom falla durante la creación, **When** se detecta el error, **Then** se registra el error y se usa fallback sin romper la creación del vehículo

---

### Edge Cases

- **Qué pasa cuando se elimina un vehículo**: El panel debe eliminarse del sidebar automáticamente
- **Qué pasa cuando hay error de red al obtener datos**: Mostrar estado offline con opción de reintentar
- **Qué pasa cuando el usuario no tiene permisos de admin**: El panel debe ser accesible sin ser admin (configurable)
- **Qué pasa con caracteres especiales en nombres de vehículos**: El URL path debe sanitizarse correctamente
- **Qué pasa cuando se reinicia Home Assistant**: El panel debe reaparecer automáticamente (no requiere recrear)

## Requirements

### Functional Requirements

- **FR-001**: El sistema DEBE crear un panel de control en el sidebar de Home Assistant automáticamente cuando se configura un nuevo vehículo mediante el config flow
- **FR-001b**: El sistema DEBE crear un panel SEPARADO para cada vehículo configurado (no un panel único con selector)
- **FR-002**: El sistema DEBE usar `panel_custom.async_register_panel` para el registro del panel (no Lovelace)
- **FR-003**: El sistema DEBE funcionar en instalaciones Container de Home Assistant donde Lovelace storage no está disponible
- **FR-004**: El sistema DEBE mostrar información del vehículo: SOC actual, autonomía estimada, estado de carga
- **FR-005**: El sistema DEBE permitir crear nuevos viajes con: destino, fecha/hora de salida, SOC objetivo
- **FR-006**: El sistema DEBE permitir editar viajes existentes
- **FR-007**: El sistema DEBE permitir eliminar viajes existentes
- **FR-008**: El sistema DEBE mostrar el perfil de carga diferible cuando EMHASS está configurado
- **FR-009**: El sistema DEBE eliminar el panel del sidebar cuando se elimina el vehículo usando `frontend.async_remove_panel`
- **FR-009b**: El sistema DEBE actualizar la lista de paneles cuando se modifica un viaje (añadir/editar/eliminar)
- **FR-010**: El sistema DEBE tener un fallback apropiado cuando `panel_custom` no está disponible
- **FR-011**: El panel DEBE usar la API REST de Home Assistant para obtener y modificar datos
- **FR-012**: El panel DEBE actualizarse automáticamente cuando cambian los datos de los sensores (mediante suscripciones WebSocket o polling)

### Key Entities

- **Panel Config**: Configuración del panel que incluye URL path, título del sidebar, icono, y configuración específica del vehículo
- **Vehicle Entity**: Entidad del vehículo en Home Assistant (config entry)
- **Trip Entities**: Entidades de sensores que contienen la información de los viajes programados
- **EMHASS Sensor**: Sensor que contiene el perfil de carga diferible

## Success Criteria

### Measurable Outcomes

- **SC-001**: El 100% de las instalaciones de Home Assistant (Core, Container, Supervised, OS) crean el panel automáticamente al configurar un vehículo, sin intervención manual
- **SC-002**: El panel se muestra en el sidebar de Home Assistant en menos de 5 segundos después de completar el config flow
- **SC-003**: Los usuarios pueden completar la creación de un viaje desde el panel nativo en menos de 60 segundos
- **SC-004**: El panel muestra datos en tiempo real sincronizados con los sensores de Home Assistant (latencia máxima 5 segundos)
- **SC-005**: 0% de errores críticos cuando se crea un vehículo en instalaciones Container (donde Lovelace storage no está disponible)
- **SC-006**: El panel se elimina correctamente del sidebar cuando se elimina el vehículo

## State Verification Plan

### Existence Check
Cómo probar que el cambio existe en el sistema real:
- [ ] Verificar que el componente `panel_custom` está cargado en Home Assistant: `curl -s http://HA_URL/api/states | jq '.[] | select(.entity_id == "sensor.ev_trip_planner_version")'`
- [ ] Verificar que las entidades del vehículo existen: `curl -s http://HA_URL/api/states | jq '.[] | select(.entity_id | startswith("sensor.{vehicle_id}"))'`
- [ ] Verificar que el panel está registrado en el frontend: Acceder a Dev Tools > Events y buscar `panels_updated`

### Effect Check
Cómo probar que el cambio funciona:
- [ ] El panel aparece en el sidebar de Home Assistant después de configurar un vehículo
- [ ] El panel carga y muestra datos correctamente
- [ ] No hay errores en los logs de Home Assistant relacionados con el panel
- [ ] Los servicios de EV Trip Planner están disponibles: `curl -s http://HA_URL/api/services | jq '.ev_trip_planner'`

### Reality Sensor Result
- STATE_MATCH = éxito real ✓
- STATE_MISMATCH = fallo real, tarea NO marcada [x]

## Assumptions

1. Se asume que Home Assistant tiene el componente `panel_custom` disponible (es parte del core desde hace muchas versiones)
2. Se asume que el usuario tiene acceso a la API de Home Assistant para el panel (no requiere auth especial más allá de la sesión)
3. Se asume que los sensores de EV Trip Planner ya están funcionando correctamente (el panel solo los consume)
4. Se asume que el componente web del panel se sirve desde `/local/` usando `hass.http.register_static_path`

## Technical Notes

### API de registro de panel (del core de HA)

```python
# Ubicación: homeassistant/components/panel_custom/__init__.py

async def async_register_panel(
    hass: HomeAssistant,
    frontend_url_path: str,      # URL del panel, ej: "ev-trip-planner-mi_vehiculo"
    webcomponent_name: str,       # Nombre del web component
    sidebar_title: str | None,    # Título en sidebar
    sidebar_icon: str | None,     # Icono en sidebar (mdi:car-electric)
    module_url: str | None,       # URL del módulo JavaScript
    config: dict | None,          # Configuración pasada al panel
    require_admin: bool = False,   # Requiere admin
) -> None:
```

### Componente web necesario

El panel requiere un componente web (JavaScript) que:
- Use la API de Home Assistant (WebSocket o REST)
- Renderice la interfaz de usuario
- Se comunique con los servicios de EV Trip Planner

### API para eliminar paneles

```python
# Para eliminar un panel cuando se elimina el vehículo
from homeassistant.components import frontend

frontend.async_remove_panel(hass, "ev-trip-planner-vehicle_id")
```

## Clarifications

### Sesión 2026-03-21

- **Q: ¿Cómo se gestionan múltiples vehículos?**
  → **A: Opción A - Un panel por vehículo**. Cada vehículo configurado tendrá su propio panel en el sidebar con el nombre del vehículo.

- **Q: ¿Qué pasa si panel_custom no funciona?**
  → **A: El módulo panel_custom ES parte del core de Home Assistant desde hace años** (disponible en todas las versiones modernas). Además, se implementará FR-010 con fallback apropiado. El método `async_register_panel` está disponible en `homeassistant.components.panel_custom` y `async_remove_panel` en `homeassistant.components.frontend`.

- **Q: ¿El panel se actualiza cuando se modifica un viaje?**
  → **A: Sí, FR-009b añade requisito de actualizar la lista de paneles cuando se modifica un viaje.**

- **Q: ¿El panel se elimina cuando se elimina un vehículo?**
  → **A: Sí, FR-009 especifica que se usa `frontend.async_remove_panel` para eliminar el panel del sidebar.**
