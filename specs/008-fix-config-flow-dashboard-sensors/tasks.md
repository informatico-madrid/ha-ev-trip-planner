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

- [x] T001 [P] Verificar estructura del proyecto en custom_components/ev_trip_planner/
- [x] T002 [P] Revisar manifest.json para dependencias (Home Assistant Core, voluptuous, PyYAML)

---

## Phase 2: Foundational - Forensic Analysis

### T003: Analizar config_flow.py - Eliminar selector vehicle_type

**File**: `custom_components/ev_trip_planner/config_flow.py`

**Done When**:
- [x] Se documentan todas las ocurrencias de vehicle_type
- [x] Se identifica el STEP_USER_SCHEMA completo
- [x] Se identifican las constantes VEHICLE_TYPE_EV y VEHICLE_TYPE_PHEV
- [x] Se documentan las traducciones en strings.json que deben eliminarse

---

## T003: Documentación de ocurrencias de vehicle_type

### Ocurrencias encontradas:

#### 1. config_flow.py
- **Línea 40-41**: Importaciones de `VEHICLE_TYPE_EV` y `VEHICLE_TYPE_PHEV` desde const
- **Línea 50-52**: Definición en `STEP_USER_SCHEMA`:
  ```python
  vol.Required("vehicle_type", default=VEHICLE_TYPE_EV): vol.In(
      [VEHICLE_TYPE_EV, VEHICLE_TYPE_PHEV]
  ),
  ```

#### 2. const.py
- **Línea 20**: `CONF_VEHICLE_TYPE = "vehicle_type"` (clave de configuración)
- **Línea 56**: `VEHICLE_TYPE_EV = "ev"` (valor para vehículos eléctricos)
- **Línea 57**: `VEHICLE_TYPE_PHEV = "phev"` (valor para híbridos)
- **Línea 64**: `DEFAULT_VEHICLE_TYPE = VEHICLE_TYPE_EV` (valor por defecto)

#### 3. strings.json (Inglés)
- **Línea 9**: `"vehicle_type": "Vehicle Type"` (en data)
- **Línea 13**: `"vehicle_type": "Select the type of vehicle you want to configure"` (en data_description)

#### 4. translations/es.json (Español)
- **Línea 14**: `"vehicle_type": "Tipo de Vehículo"` (en data)
- **Línea 18**: `"vehicle_type": "Selecciona el tipo de vehículo que quieres configurar"` (en data_description)

### STEP_USER_SCHEMA completo (líneas 47-54):
```python
STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_VEHICLE_NAME): str,
        vol.Required("vehicle_type", default=VEHICLE_TYPE_EV): vol.In(
            [VEHICLE_TYPE_EV, VEHICLE_TYPE_PHEV]
        ),
    }
)
```

### Traducciones a eliminar:
- **strings.json líneas 9 y 13** (vehicle_type en step user)
- **translations/es.json líneas 14 y 18** (vehicle_type en step user)

---

### T004: Analizar strings.json - Traducción charging_status_sensor

**File**: `custom_components/ev_trip_planner/strings.json`

**Done When**:
- [x] Se documenta el estado actual de charging_status_sensor (español/inglés)
- [x] Se documenta la estructura actual de data_description
- [x] Se documenta la traducción exacta requerida
- [x] Se documenta el hint de ayuda sugerido

---

## T004: Documentación de charging_status_sensor

### Estado actual:

#### strings.json (Inglés):
- **Línea 24** (step sensors → data): `"charging_status": "Charging Status (optional)"`
- **Línea 31** (step sensors → data_description): `"charging_status": "Optional: Binary sensor that shows 'on' when vehicle is charging. Look for sensors with 'charging', 'charge', or 'plugged' in the name. Example: binary_sensor.ovms_chispitas_charging or binary_sensor.renault_charging"`

#### translations/es.json (Español):
- **Líneas 2-6** (entity): `"charging_status_sensor": "Sensor de Estado de Carga del Vehículo"`
- **Línea 29** (step sensors → data): `"charging_status": "Estado de Carga (opcional)"`
- **Línea 36** (step sensors → data_description): `"charging_status": "Opcional: Sensor binario que muestra 'on' cuando el vehículo está cargando. Busca sensores con 'charging', 'charge' o 'plugged' en el nombre. Ejemplo: binary_sensor.ovms_chispitas_charging o binary_sensor.renault_charging"`

### Estructura actual:
- El campo `charging_status` en config flow **ya tiene traducción completa al español** (data + data_description)
- El entity `charging_status_sensor` **ya tiene traducción** en la sección "entity"
- La estructura de data_description sigue el patrón: descripción breve + ejemplos específicos

### Observaciones:
- El campo ya está completamente traducido al español
- El hint de ayuda es claro y proporciona ejemplos
- No se requiere modificación para traducción

---

### T005: Analizar __init__.py - Dashboard import

**File**: `custom_components/ev_trip_planner/__init__.py`

**Done When**:
- [x] Se documenta el flujo actual de import_dashboard
- [x] Se documenta el comportamiento cuando dashboard existe
- [x] Se documenta el problema de permisos de escritura (si existe)
- [x] Se documenta el comportamiento esperado (sobrescribir)

---

## T005: Documentación del flujo de import_dashboard

### Flujo actual de import_dashboard

#### 1. Función principal: `import_dashboard()` (líneas 52-135)

El flujo actual de importación del dashboard es:

1. **Verificar disponibilidad de Lovelace** (líneas 82-87)
   - Llama a `is_lovelace_available(hass)` que checks:
     - `hass.config.components` contains "lovelace"
     - OR `hass.services.has_service("lovelace", "import")`
   - Si no está disponible, retorna `False` ylogged warning

2. **Cargar plantilla del dashboard** (líneas 90-92)
   - Llama a `_load_dashboard_template(vehicle_id, vehicle_name, use_charts)`
   - Busca en dos ubicaciones:
     - `{custom_components}/ev_trip_planner/dashboard/{template_file}`
     - `{parent}/custom_components/ev_trip_planner/dashboard/{template_file}`
   - Template substitution: `{{ vehicle_id }}` → vehicle_id, `{{ vehicle_name }}` → vehicle_name

3. **Guardar dashboard - Método primario** (líneas 102-106)
   - Llama a `_save_lovelace_dashboard(hass, dashboard_config)`
   - Este método tiene dos estrategias:
     a. **Estrategia 1** (líneas 212-231): Usar `lovelace.save` service
        - Guarda solo el primer view como dashboard principal
     b. **Estrategia 2** (líneas 234-256): Usar API de storage directamente
        - Lee configuración actual de Lovelace: `await hass.storage.async_read("lovelace")`
        - Agrega el nuevo view a la lista existente
        - Guarda: `await hass.storage.async_write_dict("lovelace", {...})`

4. **Fallback: Servicio import** (líneas 109-126)
   - Si `_save_lovelace_dashboard` retorna `False`
   - Intenta usar `lovelace.import` service
   - Pasa: url, config (title, path, icon)

#### 2. Ubicación de llamada en config_flow.py (línea 584)

```python
await import_dashboard(
    self.hass,
    vehicle_id=vehicle_id,
    vehicle_name=vehicle_name,
    use_charts=use_charts,
)
```

Se llama en `async_step_consume()` después de crear la entrada de configuración.

### Comportamiento cuando dashboard existe

**Problema identificado**: El código actual **NO sobrescribe** dashboards existentes.

#### Análisis del código:

1. **Estrategia 1 (lovelace.save service)** - Líneas 212-231:
   - NO verifica si ya existe un dashboard
   - Simplemente guarda el nuevo config
   - **Comportamiento**: Sobrescribe el dashboard existente

2. **Estrategia 2 (storage API)** - Líneas 234-256:
   - Lee configuración actual: `await hass.storage.async_read("lovelace")`
   - Agrega nuevo view: `views.append(new_view)`
   - **Comportamiento**: Añade view, NO reemplaza

3. **Fallback (lovelace.import)** - Líneas 109-126:
   - Crea nuevo dashboard con path específico: `ev-trip-planner-{vehicle_id}`
   - **Comportamiento**: Puede fallar si ya existe (conflicto de path)

### Problemas de permisos de escritura

**Posibles problemas**:
1. El directorio `.storage` de HA debe tener permisos de escritura
2. El archivo `lovelace` en storage debe ser editable
3. El servicio `lovelace.save` puede no estar disponible en modo YAML

**Logging actual** (líneas 75-79, 103-106):
- Info: "Importing dashboard for {vehicle_name} (type: {dashboard_type})"
- Warning: "Lovelace not available for {vehicle_name}, skipping dashboard import"
- Error: "Could not load dashboard template for {vehicle_name}"
- Info: "Dashboard imported successfully for {vehicle_name}"

### Comportamiento esperado (sobrescribir)

Según spec.md:
- **FR-004**: "El sistema sobrescribe el dashboard existente al importar automáticamente"

**Solución requerida**:
1. En Estrategia 2 (storage API), verificar si ya existe un dashboard con el mismo path
2. Si existe, reemplazar en lugar de añadir
3. Usar el path `ev-trip-planner-{vehicle_id}` como identificador único

---

### T006: Analizar sensor.py - Lectura de trips

**File**: `custom_components/ev_trip_planner/sensor.py`

**Done When**:
- [x] Se documenta el flujo actual de lectura de trips en sensores
- [x] Se documenta la fuente de datos (coordinator.data)
- [x] Se documenta el problema de actualización (si existe)
- [x] Se documenta el flujo de actualización esperado

---

## T006: Documentación del flujo de lectura de trips en sensores

### Flujo actual de lectura de trips

#### 1. Sensores y fuente de datos

Los sensores leen los datos directamente de `coordinator.data`, que es un diccionario actualizado por `TripPlannerCoordinator`:

**Clases de sensores** (sensor.py líneas 119-278):
- `RecurringTripsCountSensor` (líneas 119-141): Lee `data["recurring_trips"]`
- `PunctualTripsCountSensor` (líneas 143-163): Lee `data["punctual_trips"]`
- `TripsListSensor` (líneas 166-189): Lee `data["recurring_trips"]` y `data["punctual_trips"]`
- `KwhTodaySensor` (líneas 193-211): Lee `data["kwh_today"]`
- `HoursTodaySensor` (líneas 214-232): Lee `data["hours_today"]`
- `NextTripSensor` (líneas 235-255): Lee `data["next_trip"]`
- `NextDeadlineSensor` (líneas 258-278): Lee `data["next_trip"]`

**Patrón de lectura** (todas las clases):
```python
@property
def native_value(self) -> Any:
    """Return sensor value - read directly from coordinator.data."""
    if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
        data = self._coordinator.data
        # Lee la clave específica del diccionario
        return data.get("clave_especifica", valor_por_defecto)
    return valor_por_defecto
```

#### 2. Coordinator y actualización de datos

**TripPlannerCoordinator** (__init__.py líneas 265-308):

1. **Inicialización** (línea 339): `coordinator = TripPlannerCoordinator(hass, trip_manager)`

2. **Primera carga** (línea 340): `await coordinator.async_config_entry_first_refresh()`
   - Llama a `_async_update_data()` inmediatamente

3. **_async_update_data()** (líneas 278-304):
   ```python
   async def _async_update_data(self) -> dict[str, Any]:
       recurring_trips = await self.trip_manager.async_get_recurring_trips()
       punctual_trips = await self.trip_manager.async_get_punctual_trips()
       kwh_today = await self.trip_manager.async_get_kwh_needed_today()
       hours_today = await self.trip_manager.async_get_hours_needed_today()
       next_trip = await self.trip_manager.async_get_next_trip()

       return {
           "recurring_trips": recurring_trips,
           "punctual_trips": punctual_trips,
           "kwh_today": kwh_today,
           "hours_today": hours_today,
           "next_trip": next_trip,
       }
   ```

4. **Refresh manual** (líneas 306-308):
   ```python
   async def async_refresh_trips(self) -> None:
       """Force refresh of trip data and notify all sensors."""
       await self.async_request_refresh()
   ```

#### 3. TripManager y persistencia

**Persistencia con hass.storage** (trip_manager.py):

- **Carga** (líneas 67-69):
  ```python
  stored_data = await self.hass.storage.async_read(storage_key)
  ```

- **Guardado** (líneas 98-100):
  ```python
  await self.hass.storage.async_write_dict(storage_key, {...})
  ```

#### 4. Flujo de actualización después de crear un trip

```
1. Usuario llama servicio (ev_trip_planner.add_recurring_trip)
   ↓
2. handle_add_recurring() (__init__.py líneas 391-406)
   ↓
3. mgr.async_add_recurring_trip() → Guarda en hass.storage
   ↓
4. coordinator.async_refresh_trips() → Llama async_request_refresh()
   ↓
5. coordinator._async_update_data() → Recarga de trip_manager
   ↓
6. trip_manager.async_get_recurring_trips() → Lee de hass.storage
   ↓
7. coordinator.data se actualiza con nuevos valores
   ↓
8. Sensores leen coordinator.data en próxima actualización
```

### Problema de actualización identificado

**Problema**: Si `hass.data` se usaba en lugar de `hass.storage`:
- Los trips NO persistían entre reinicios de Home Assistant
- Los sensores mostraban 0 trips después de reiniciar

**Solución implementada**: Usar `hass.storage.async_write_dict()` y `hass.storage.async_read()` para persistencia (trip_manager.py líneas 67-100)

### Flujo esperado después del fix

1. **Crear trip**: Servicio guarda en `hass.storage` (persistente)
2. **Refresh**: Coordinator llama a trip_manager que lee de `hass.storage`
3. **Lectura**: Sensores leen `coordinator.data` actualizado
4. **Reinicio**: Coordinator carga datos de `hass.storage` al iniciar

### Timing de actualización

- El coordinator tiene `update_interval=timedelta(seconds=30)` (línea 274)
- Pero el refresh manual es inmediato: `await coordinator.async_request_refresh()`
- Los servicios llaman a `async_refresh_trips()` después de guardar (líneas 404-406)

---

### T007: Analizar trip_manager.py - Persistencia

**File**: `custom_components/ev_trip_planner/trip_manager.py`

**Done When**:
- [x] Se documenta el uso actual de hass.data para storage
- [x] Se documenta el namespace usado
- [x] Se documenta el problema: hass.data no persiste entre reinicios
- [x] Se documenta la solución: usar hass.storage.async_write_dict y async_read

---

## T007: Documentación de persistencia en trip_manager.py

### Uso actual de storage (FIX APLICADO)

El código ya ha sido corregido para usar `hass.storage` en lugar de `hass.data`:

#### Carga de viajes - `_load_trips()` (líneas 64-93)

```python
async def _load_trips(self) -> None:
    """Carga los viajes desde el almacenamiento persistente."""
    try:
        # FIX: Usar hass.storage para persistencia entre reinicios
        storage_key = f"{DOMAIN}_{self.vehicle_id}"
        stored_data = await self.hass.storage.async_read(storage_key)

        if stored_data and "data" in stored_data:
            data = stored_data["data"]
            self._trips = data.get("trips", {})
            self._recurring_trips = data.get("recurring_trips", {})
            self._punctual_trips = data.get("punctual_trips", {})
            self._last_update = data.get("last_update")
```

#### Guardado de viajes - `async_save_trips()` (líneas 95-118)

```python
async def async_save_trips(self) -> None:
    """Guarda los viajes en el almacenamiento persistente."""
    try:
        # FIX: Usar hass.storage.async_write_dict para persistencia
        storage_key = f"{DOMAIN}_{self.vehicle_id}"
        await self.hass.storage.async_write_dict(
            storage_key,
            {
                "version": 1,
                "data": {
                    "trips": self._trips,
                    "recurring_trips": self._recurring_trips,
                    "punctual_trips": self._punctual_trips,
                    "last_update": datetime.now().isoformat(),
                },
            },
        )
```

### Namespace usado

- **Storage key**: `f"{DOMAIN}_{self.vehicle_id}"` → `ev_trip_planner_{vehicle_id}`
- **Ubicación**: `.storage/ev_trip_planner_{vehicle_id}.json` en el directorio de configuración de HA

### Problema original: hass.data no persiste entre reinicios

**Problema identificado**:
- `hass.data` es un diccionario en memoria que se pierde al reiniciar Home Assistant
- Los trips guardados con `hass.data` desaparecían después de un reinicio
- Los sensores mostraban 0 trips tras reiniciar

### Solución implementada: hass.storage

**Solución aplicada**:
- Usar `hass.storage.async_write_dict()` para guardar datos de forma persistente
- Usar `hass.storage.async_read()` para cargar datos al iniciar
- Los datos se almacenan en `.storage/` del directorio de configuración de HA
- Formato JSON con versionado para futuras migraciones

**Beneficios**:
- Persistencia entre reinicios de Home Assistant
- Formato legible (JSON) para depuración
- Versionado para migraciones futuras
- API oficial recomendada por Home Assistant

---

### T008: Analizar __init__.py - Coordinator refresh

**File**: `custom_components/ev_trip_planner/__init__.py`

**Done When**:
- [x] Se documenta el flujo actual de async_refresh_trips
- [x] Se documenta si async_request_refresh() se llama después de crear trip
- [x] Se documenta el problema de propagación a sensores (si existe)
- [x] Se documenta el timing entre save y refresh

---

### Documentación del flujo de async_refresh_trips

### Flujo actual de async_refresh_trips

#### 1. Función principal: `async_refresh_trips()` (líneas 306-308)

```python
async def async_refresh_trips(self) -> None:
    """Force refresh of trip data and notify all sensors."""
    await self.async_request_refresh()
```

**Comportamiento**:
- Llama a `async_request_refresh()` del `DataUpdateCoordinator` base
- Esto triggerea `_async_update_data()` para obtener nuevos datos
- Notifica a todos los sensores subscribers para que actualicen

#### 2. _async_update_data() (líneas 278-304)

```python
async def _async_update_data(self) -> dict[str, Any]:
    recurring_trips = await self.trip_manager.async_get_recurring_trips()
    punctual_trips = await self.trip_manager.async_get_punctual_trips()
    kwh_today = await self.trip_manager.async_get_kwh_needed_today()
    hours_today = await self.trip_manager.async_get_hours_needed_today()
    next_trip = await self.trip_manager.async_get_next_trip()

    return {
        "recurring_trips": recurring_trips,
        "punctual_trips": punctual_trips,
        "kwh_today": kwh_today,
        "hours_today": hours_today,
        "next_trip": next_trip,
    }
```

### async_request_refresh() se llama después de crear trip

**SÍ se llama** - Después de cada operación CRUD en trips:

1. **handle_add_recurring** (líneas 391-406):
```python
await mgr.async_add_recurring_trip(...)
# Refresh coordinator using vehicle_id
coordinator = _get_coordinator(hass, vehicle_id)
if coordinator:
    await coordinator.async_refresh_trips()
```

2. **handle_add_punctual** (líneas 408-422):
```python
await mgr.async_add_punctual_trip(...)
# Refresh coordinator using vehicle_id
coordinator = _get_coordinator(hass, vehicle_id)
if coordinator:
    await coordinator.async_refresh_trips()
```

3. **handle_edit_trip** (líneas 424-434):
```python
await mgr.async_update_trip(...)
# Refresh coordinator using vehicle_id
coordinator = _get_coordinator(hass, vehicle_id)
if coordinator:
    await coordinator.async_refresh_trips()
```

4. **handle_delete_trip** (líneas 436-446):
```python
await mgr.async_delete_trip(...)
# Refresh coordinator using vehicle_id
coordinator = _get_coordinator(hass, vehicle_id)
if coordinator:
    await coordinator.async_refresh_trips()
```

### Problema de propagación a sensores

**NO existe problema** - El flujo está correctamente implementado:

1. `async_refresh_trips()` → `async_request_refresh()` (DataUpdateCoordinator)
2. `async_request_refresh()` → `_async_update_data()` (obtiene datos frescos de trip_manager)
3. `_async_update_data()` → Actualiza `coordinator.data` con nuevos valores
4. `DataUpdateCoordinator` → Notifica a todos los listeners (sensores)订阅者
5. Sensores leen `coordinator.data` actualizado en su propiedad `native_value`

**Patrón correcto**:
- Los sensores se suscriben al coordinator automáticamente via `async_setup_entry`
- Cuando `async_request_refresh()` completa, los sensores reciben el callback de actualización
- Los sensores leen `self._coordinator.data` en su propiedad `native_value`

### Timing entre save y refresh

**Timing correcto** (inmediato):

```
1. Servicio (add_recurring_trip)
   ↓
2. trip_manager.async_add_recurring_trip() → Guarda en hass.storage
   ↓
3. coordinator.async_refresh_trips() → Llama async_request_refresh() INMEDIATAMENTE
   ↓
4. coordinator._async_update_data() → Recarga de trip_manager (lee hass.storage)
   ↓
5. coordinator.data se actualiza
   ↓
6. Sensores notificados y actualizados
```

- **Save**: Inmediato en el servicio
- **Refresh**: Llama INMEDIATAMENTE después del save (líneas 404-406, 420-422, 432-434, 444-446)
- **No hay delay**: El refresh es síncrono después del save

### Resumen

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| async_refresh_trips existe | ✓ SÍ | Líneas 306-308 |
| Se llama después de add_recurring | ✓ SÍ | Líneas 404-406 |
| Se llama después de add_punctual | ✓ SÍ | Líneas 420-422 |
| Se llama después de edit_trip | ✓ SÍ | Líneas 432-434 |
| Se llama después de delete_trip | ✓ SÍ | Líneas 444-446 |
| Propagación a sensores | ✓ CORRECTO | DataUpdateCoordinator maneja esto |
| Timing | ✓ INMEDIATO | No hay delay entre save y refresh |

---

### T009: Analizar logs de Home Assistant

**File**: `custom_components/ev_trip_planner/config_flow.py`, `__init__.py`, `trip_manager.py`, `sensor.py`

**Done When**:
- [x] Se documentan los logs de config_flow al crear vehículo
- [x] Se documentan los logs de dashboard import
- [x] Se documentan los logs de sensor updates
- [x] Se documentan los errores de storage (si existen)
- [x] Se documentan los logs que confirman trips guardados
- [x] Se documentan los logs que muestran sensores con valor 0

---

## T009: Documentación de logs de Home Assistant

### 1. Logs de config_flow al crear vehículo

#### config_flow.py - Logging durante la creación de vehículo:

| Nivel | Línea | Mensaje | Cuándo se produce |
|-------|-------|---------|-------------------|
| DEBUG | 155 | `EMHASS config file not found at {path}` | Si no existe config EMHASS |
| DEBUG | 161 | `EMHASS config loaded successfully from {path}` | Si config EMHASS existe |
| WARNING | 164 | `Could not read EMHASS config from {path}: {error}` | Error al leer config EMHASS |
| INFO | 294 | `EMHASS config: horizon={X} days, max_loads={Y}` | Si hay config EMHASS válida |
| INFO | 389 | `EMHASS planning sensor configured: {sensor}` | Si se configura sensor de planificación |
| INFO | 395-400 | `EMHASS config: horizon={X}, max_loads={Y}, sensor={Z}` | Siempre en step sensors |
| INFO | 542 | `Notification service configured: {service}` | Si se configura servicio de notificación |
| INFO | 570-574 | `Lovelace available: {bool}, will use {type} dashboard` | Siempre al finalizar configuración |
| WARNING | 587-589 | `Could not auto-import dashboard for {vehicle}: {error}` | Si falla importación de dashboard |

#### Flujo de logs durante creación de vehículo:
```
1. DEBUG: EMHASS config file not found/loaded
2. INFO: EMHASS config: horizon=X, max_loads=Y
3. INFO: EMHASS planning sensor configured: sensor_id
4. INFO: EMHASS config: horizon=X, max_loads=Y, sensor=Z
5. INFO: Notification service configured: notify.service
6. INFO: Lovelace available: True/False, will use full/simple dashboard
7. (si falla) WARNING: Could not auto-import dashboard
```

---

### 2. Logs de dashboard import

#### __init__.py - Logging de importación de dashboard:

| Nivel | Línea | Mensaje | Cuándo se produce |
|-------|-------|---------|-------------------|
| INFO | 75-79 | `Importing dashboard for {name} (type: {type})` | Siempre al iniciar importación |
| WARNING | 83-86 | `Lovelace not available for {name}, skipping dashboard import` | Si Lovelace no está disponible |
| ERROR | 95-97 | `Could not load dashboard template for {name}` | Si no se encuentra plantilla |
| ERROR | 183 | `Dashboard template not found: {file}` | Si plantilla no existe |
| ERROR | 204 | `Failed to load dashboard template: {error}` | Error al cargar plantilla |
| INFO | 242 | `Dashboard saved via lovelace.save service` | Si se guarda con servicio |
| WARNING | 259 | `No views found in dashboard config` | Si config está vacía |
| INFO | 270 | `Replaced existing dashboard view: {path}` | Si se reemplaza view existente (FIX US3) |
| INFO | 277 | `Added new dashboard view: {path}` | Si se añade nuevo view |
| INFO | 284 | `Dashboard saved via storage API` | Si se guarda via storage |
| DEBUG | 287 | `Storage API method failed: {error}` | Si falla método storage |
| DEBUG | 292 | `Failed to save dashboard: {error}` | Si falla guardado |

#### Flujo de logs de importación:
```
1. INFO: Importing dashboard for {name} (type: full/simple)
2. (si no disponible) WARNING: Lovelace not available, skipping
3. (si hay error) ERROR: Could not load dashboard template
4. (si éxito) INFO: Dashboard saved via lovelace.save service
   O
   INFO: Replaced/Added new dashboard view: {path}
   INFO: Dashboard saved via storage API
```

---

### 3. Logs de sensor updates

#### sensor.py - Logging de actualizaciones de sensores:

| Nivel | Línea | Mensaje | Cuándo se produce |
|-------|-------|---------|-------------------|
| ERROR | 92 | `Error actualizando sensor {type}: {error}` | Si falla actualización |
| WARNING | 334 | `No config entry found for {vehicle_id}` | Si no hay config entry |
| ERROR | 357 | `Error actualizando sensor EMHASS {vehicle_id}: {error}` | Si falla sensor EMHASS |
| ERROR | 377 | `No trip_manager found for {vehicle_id}` | Si no hay trip_manager |

---

### 4. Errores de storage (persistencia)

#### trip_manager.py - Logging de almacenamiento:

| Nivel | Línea | Mensaje | Cuándo se produce |
|-------|-------|---------|-------------------|
| DEBUG | 52 | `EMHASS adapter set for vehicle {id}` | Si se configura adapter |
| INFO | 60 | `Configurando gestor de viajes para vehículo: {id}` | Al iniciar trip manager |
| INFO | 77 | `Viajes cargados para {vehicle_id}: {count} trips` | Si se cargan trips |
| INFO | 83 | `No se encontraron viajes almacenados para {vehicle_id}` | Si no hay trips |
| ERROR | 89 | `Error cargando viajes: {error}` | Si falla carga |
| INFO | 112 | `Viajes guardados para {vehicle_id}: {count} trips` | Si se guardan trips |
| ERROR | 118 | `Error guardando viajes: {error}` | Si falla guardado |

#### Flujo de logs de storage:
```
1. INFO: Configurando gestor de viajes para vehículo: {id}
2. (si hay trips) INFO: Viajes cargados: X trips
   O
   (si no hay) INFO: No se encontraron viajes almacenados
3. (al guardar) INFO: Viajes guardados: X trips
   O
   (si error) ERROR: Error guardando viajes
```

---

### 5. Logs que confirman trips guardados

Los logs que confirman que los trips se han guardado correctamente están en:
- **trip_manager.py línea 112**: `INFO: Viajes guardados para {vehicle_id}: {count} trips`
- **__init__.py líneas 404-406, 420-422, 432-434, 444-446**: Refresh de coordinator después de cada operación

---

### 6. Logs que muestran sensores con valor 0

Cuando los sensores muestran valor 0 (problema original de US4):

**Causa del problema identificado**:
- Se usaba `hass.data` en lugar de `hass.storage` para persistencia
- Los trips no persistían entre reinicios

**Solución implementada** (T016-T018):
- `trip_manager.py` ahora usa `hass.storage.async_write_dict()` y `hass.storage.async_read()`
- Los trips se guardan en `.storage/ev_trip_planner_{vehicle_id}.json`

**Logs después del fix**:
- Al iniciar: `INFO: Viajes cargados para {vehicle_id}: {count} trips`
- Si persistence falla: `ERROR: Error cargando viajes: {error}`

---

## Resumen de logging por componente

| Componente | Archivo | Propósito |
|------------|---------|-----------|
| Config flow | config_flow.py | Creación de vehículo, configuración EMHASS |
| Dashboard | __init__.py | Importación de dashboard Lovelace |
| Sensores | sensor.py | Actualización de valores de sensores |
| Persistencia | trip_manager.py | Carga/guardado de trips con hass.storage |
| Coordinator | __init__.py | Refresh de datos después de operaciones |

---

## Phase 3: User Story 1 - Eliminar selector vehicle_type

### T010: Eliminar vehicle_type de config_flow.py

**File**: `custom_components/ev_trip_planner/config_flow.py`

**Tasks**:
- [x] T010 [US1] Eliminar vehicle_type de STEP_USER_SCHEMA (líneas 50-52)
- [x] T011 [US1] Eliminar VEHICLE_TYPE_EV y VEHICLE_TYPE_PHEV de const.py si no se usan
- [x] T012 [US1] Actualizar async_step_user para no pasar vehicle_type al context

---

## Phase 4: User Story 2 - Traducir charging_status_sensor

### T013: Agregar traducción a strings.json

**File**: `custom_components/ev_trip_planner/strings.json`

**Tasks**:
- [x] T013 [US2] Agregar charging_status_sensor en español en presence.data
- [x] T014 [US2] Agregar data_description con hint de ayuda claro
- [x] T015 [US2] Verificar todas las traducciones del config flow están en español

---

## Phase 5: User Story 4 - Sensores actualizados

### T016: Corregir persistencia de trips

**File**: `custom_components/ev_trip_planner/trip_manager.py`

**Tasks**:
- [x] T016 [US4] Cambiar de hass.data a hass.storage para persistencia
- [x] T017 [US4] Implementar hass.storage.async_write_dict para trips
- [x] T018 [US4] Implementar hass.storage.async_read para cargar trips

---

### T019: Corregir refresh de coordinator

**File**: `custom_components/ev_trip_planner/__init__.py`

**Tasks**:
- [x] T019 [US4] Verificar async_refresh_trips se llama correctamente
- [x] T020 [US4] Agregar logging para diagnosticar problemas de refresh
- [x] T021 [US4] Verificar que coordinator.data se actualiza antes de refresh

---

### T022: Corregir lectura de sensores

**File**: `custom_components/ev_trip_planner/sensor.py`

**Tasks**:
- [x] T022 [US4] Verificar que sensores leen de coordinator.data correctamente
- [x] T023 [US4] Agregar logging para diagnosticar problemas de lectura
- [x] T024 [US4] Verificar que async_update se llama después de refresh

---

## Phase 6: User Story 3 - Dashboard import

### T025: Corregir import de dashboard

**File**: `custom_components/ev_trip_planner/__init__.py`

**Tasks**:
- [x] T025 [US3] Modificar import_dashboard para sobrescribir dashboard existente
- [x] T026 [US3] Agregar logging detallado para diagnosticar fallos
- [x] T027 [US3] Verificar permisos de escritura en storage

---

## Phase 7: Tests

### T028: Tests config_flow

**File**: `tests/test_config_flow_issues.py`

**Tasks**:
- [x] T028 [US1] Test: Config flow no tiene vehicle_type
- [x] T029 [US2] Test: charging_status_sensor está en español
- [x] T030 [US2] Test: charging_status_sensor tiene hint de ayuda

---

### T031: Tests sensor update

**File**: `tests/test_sensor_update.py`

**Tasks**:
- [x] T031 [US4] Test: Sensores muestran trips después de crear viaje
- [x] T032 [US4] Test: Sensores se actualizan después de crear viaje (funcionalidad prioritaria)
- [x] T033 [US4] Test: Persistencia entre reinicios

---

### T034: Tests coordinator

**File**: `tests/test_coordinator_update.py`

**Tasks**:
- [x] T034 [US4] Test: Coordinator se actualiza después de crear trip
- [x] T035 [US4] Test: Refresh se propaga a todos los sensores

---

## Phase 8: Polish

### T036: Logging y observabilidad

**File**: `custom_components/ev_trip_planner/`

**Tasks**:
- [x] T036 [P] Agregar logging en config flow para diagnóstico
- [x] T037 [P] Agregar logging en dashboard import para diagnóstico
- [x] T038 [P] Agregar logging en sensor updates para diagnóstico

---

### T039: Documentation

**File**: `custom_components/ev_trip_planner/`

**Tasks**:
- [x] T039 [P] Actualizar README.md con cambios
- [x] T040 [P] Actualizar CHANGELOG.md con los fixes

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
