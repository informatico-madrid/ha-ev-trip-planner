# EV Trip Planner — Reglas de Código y Arquitectura (v2)

> Documento de referencia obligatorio para cualquier agente de IA o desarrollador.  
> Versión: 2026-04-v2 · Análisis multi-integración: Bambu Lab (2085★), Bermuda (1695★), Battery Notes (1028★), Versatile Thermostat (1021★), Nordpool (Platinum)

***

## 1. Resumen Ejecutivo de Gaps Críticos

Este análisis comparó `ha-ev-trip-planner` contra cinco integraciones HACS de referencia activas en 2025-2026. Se identificaron **12 gaps críticos** organizados en 4 categorías. Cada gap tiene una regla de código que lo cierra. ESTO ES LA GUIA GENERAL SI ES NECESARIO EN CASOS MUY DETERMINADOS SE PUEDEN HACER EXCEPCIONES PERO DEBEN SER JUSTIFICADAS Y DOCUMENTADAS EN EL CÓDIGOBASE CON UN COMENTARIO EXPLICATIVO Y APROVADOS POR EL HUMANO. 

| ID | Categoría | Severidad | Impacto Visible |
|---|---|---|---|
| G-01 | Identidad de entidades | 🔴 Crítico | Sensores duplicados al reinstalar |
| G-02 | Ciclo de actualización | 🔴 Crítico | Sensores no reflejan cambios |
| G-03 | Arquitectura de entidades | 🔴 Crítico | Código imposible de mantener |
| G-04 | Ciclo de vida de la integración | 🔴 Crítico | Sensores zombi tras desinstalar |
| G-05 | Runtime data storage | 🟠 Alto | Fallos aleatorios tras reinicios |
| G-06 | Código de test en producción | 🔴 Crítico | Estados de sensor inventados |
| G-07 | Patrón `SensorEntityDescription` | 🟠 Alto | Código duplicado × cada sensor |
| G-08 | `RestoreEntity` / `RestoreSensor` | 🟠 Alto | Sensores en `Unknown` tras reinicio HA |
| G-09 | `async_migrate_entry` incompleto | 🟠 Alto | Migraciones silenciosamente incorrectas |
| G-10 | `diagnostics.py` ausente | 🟡 Medio | Imposible depurar en producción |
| G-11 | `ConfigEntryNotReady` no se lanza | 🟡 Medio | Errores de setup silenciosos |
| G-12 | Separación de responsabilidades | 🔴 Crítico | God Object de 5000+ líneas |

***

## 2. Análisis por Integración de Referencia

### 2.1 · ha-bambulab (2085★, actualizado diariamente)

**Patrón clave que falta en ev-trip-planner: `SensorEntityDescription` + `definitions.py`**

Bambu Lab separa la **definición** de los sensores de su **implementación**. Todos los sensores comparten una clase base única y sus diferencias se expresan como datos, no como código.

```python
# bambu_lab/definitions.py
@dataclass(frozen=True)
class BambuLabSensorEntityDescription(SensorEntityDescription):
    """Descriptor de sensor extendido."""
    value_fn: Callable[[BambuDataUpdateCoordinator], StateType] = None
    exists_fn: Callable[[BambuDataUpdateCoordinator], bool] = lambda _: True
    is_restoring: bool = False

PRINTER_SENSORS: tuple[BambuLabSensorEntityDescription, ...] = (
    BambuLabSensorEntityDescription(
        key="stage",
        translation_key="stage",
        value_fn=lambda coordinator: coordinator.get_model().info.gcode_state,
        exists_fn=lambda coordinator: coordinator.get_model().has_full_printer_data,
        is_restoring=True,
    ),
    # ...decenas de sensores definidos como datos, NO como clases
)
```

```python
# bambu_lab/sensor.py — UNA sola clase para todos los sensores
class BambuLabSensor(BambuLabEntity, SensorEntity):
    def __init__(self, coordinator, description: BambuLabSensorEntityDescription):
        self._attr_unique_id = f"{printer.serial}_{description.key}"  # ← SIEMPRE presente
        self.entity_description = description  # ← HA gestiona name, unit, device_class
    
    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator)  # ← Lee del coordinator
```

**ev-trip-planner tiene 8+ clases separadas** (`RecurringTripsCountSensor`, `PunctualTripsCountSensor`, etc.) cuando debería tener **1 clase base + un archivo de definiciones**.

***

### 2.2 · Bermuda (1695★, actualizado ayer)

**Patrón clave que falta: `entry.runtime_data` con `@dataclass` + `TypeAlias` de ConfigEntry**

```python
# bermuda/__init__.py
from dataclasses import dataclass

type BermudaConfigEntry = ConfigEntry[BermudaData]  # TypeAlias tipado

@dataclass
class BermudaData:
    """Datos de runtime almacenados en config_entry.runtime_data."""
    coordinator: BermudaDataUpdateCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: BermudaConfigEntry) -> bool:
    coordinator = BermudaDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()  # ← Lanza ConfigEntryNotReady si falla
    entry.runtime_data = BermudaData(coordinator)  # ← Una sola línea, tipada, sin strings
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: BermudaConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # ← NO necesita limpiar hass.data porque usó runtime_data
```

**ev-trip-planner usa** `DATA_RUNTIME = f"{DOMAIN}_runtime_data"` como string global, con múltiples namespaces (`f"{DOMAIN}_{entry_id}"`, `f"ev_trip_planner_{entry_id}"`) y fallbacks legacy anidados. Esto produce fallos aleatorios cuando HA intenta acceder a datos que fueron liberados antes de tiempo.

**Patrón adicional de Bermuda: `async_migrate_entries` para Entity Registry**

```python
# bermuda/__init__.py
from homeassistant.helpers.entity_registry import async_migrate_entries

async def async_migrate_entry(hass, config_entry):
    # Migra los unique_id de entidades existentes en el Entity Registry
    async def migrate_unique_id(entity_entry):
        if entity_entry.unique_id.startswith("OLD_PREFIX"):
            return {"new_unique_id": entity_entry.unique_id.replace("OLD_PREFIX", "NEW_PREFIX")}
    await async_migrate_entries(hass, config_entry.entry_id, migrate_unique_id)
    return True
```

ev-trip-planner tiene un `async_migrate_entry` que solo migra `config_entry.data` pero **nunca migra los `unique_id` de las entidades en el Entity Registry**. Si el formato del `unique_id` cambia entre versiones, las entidades antiguas quedan como zombis.

***

### 2.3 · Battery Notes (1028★, actualizado ayer)

**Patrón clave que falta: `diagnostics.py`**

Battery Notes implementa `diagnostics.py` — un módulo estándar de HA que permite a los usuarios descargar un informe de diagnóstico desde la UI sin acceder a logs.

```python
# battery_notes/diagnostics.py
from homeassistant.components.diagnostics import async_redact_data

TO_REDACT = {"serial_number", "mac_address"}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Retorna datos de diagnóstico para mostrar en la UI de HA."""
    coordinator = entry.runtime_data.coordinator
    return async_redact_data({
        "config_entry": dict(entry.data),
        "coordinator_data": coordinator.data,
        "entity_count": len(coordinator.entities),
    }, TO_REDACT)
```

ev-trip-planner no tiene `diagnostics.py`. Cuando un usuario reporta un bug, no hay manera estándar de obtener el estado interno sin hackear el sistema.

**Patrón adicional: `ConfigSubentry` para elementos dinámicos**

Battery Notes usa `ConfigSubentry` (disponible desde HA 2024.x) para representar cada batería como una subentrada de configuración. Esto resuelve exactamente el mismo problema que ev-trip-planner tiene con los viajes: **elementos creados dinámicamente por el usuario que necesitan su propio ciclo de vida**.

```python
# Cada viaje podría ser un ConfigSubentry con su propio unique_id
subentry = ConfigSubentry(
    subentry_type="trip",
    unique_id=f"trip_{trip_id}",
    title=trip_name,
    data=trip_data,
)
hass.config_entries.async_add_subentry(config_entry, subentry)
```

***

### 2.4 · Versatile Thermostat (1021★)

**Patrón clave que falta: `RestoreSensor` / `RestoreEntity`**

Versatile Thermostat restaura el último estado conocido de sus sensores tras un reinicio de HA, evitando el estado `Unknown` inicial.

```python
from homeassistant.helpers.restore_state import RestoreEntity, RestoreSensor

class VersatileThermostatSensor(CoordinatorEntity, RestoreSensor):
    async def async_added_to_hass(self) -> None:
        """Restaura el estado al añadirse a HA."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_sensor_data()
        if last_state:
            self._attr_native_value = last_state.native_value
            # El sensor muestra el valor anterior hasta la primera actualización real
```

ev-trip-planner no implementa `RestoreSensor`. Cada vez que HA reinicia, todos los sensores muestran `Unknown` hasta el primer ciclo de polling — que puede tardar minutos si el coordinador tiene un `update_interval` largo.

***

## 3. Reglas de Código (Versión Completa)

### R-01 · Todo Sensor Debe Tener `_attr_unique_id` — CRÍTICO

```python
# ❌ ACTUAL — sin unique_id (produce duplicados)
class RecurringTripsCountSensor(TripPlannerSensor):
    def __init__(self, vehicle_id, coordinator):
        super().__init__(...)
        self._attr_name = f"{vehicle_id} recurring trips count"
        # ← SIN unique_id

# ✅ CORRECTO
class TripPlannerSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity):
    def __init__(self, coordinator, vehicle_id, description: TripSensorEntityDescription):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}"
        self.entity_description = description
```

### R-02 · Usar `SensorEntityDescription` + `definitions.py` — CRÍTICO

Eliminar las 8 clases de sensor separadas. Reemplazar con una clase base + descriptores.

```python
# ev_trip_planner/definitions.py
from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntityDescription

@dataclass(frozen=True)
class TripSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[dict], Any] = lambda data: None
    attrs_fn: Callable[[dict], dict] = lambda data: {}
    restore: bool = False

TRIP_SENSORS: tuple[TripSensorEntityDescription, ...] = (
    TripSensorEntityDescription(
        key="recurring_trips_count",
        translation_key="recurring_trips_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: len(data.get("recurring_trips", [])),
    ),
    TripSensorEntityDescription(
        key="kwh_needed_today",
        translation_key="kwh_needed_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda data: data.get("kwh_today", 0.0),
        restore=True,
    ),
    # ... todos los demás sensores como datos
)
```

```python
# ev_trip_planner/sensor.py — UNA SOLA clase
class TripPlannerSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity):
    def __init__(self, coordinator, vehicle_id, description):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}"
        self._vehicle_id = vehicle_id
        self.entity_description = description

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self):
        if self.coordinator.data is None:
            return {}
        return self.entity_description.attrs_fn(self.coordinator.data)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._vehicle_id)},
            name=f"EV Trip Planner {self._vehicle_id}",
            entry_type=DeviceEntryType.SERVICE,
        )
```

### R-03 · Usar `entry.runtime_data` con `@dataclass` Tipado — CRÍTICO

```python
# ev_trip_planner/__init__.py
from dataclasses import dataclass
from homeassistant.config_entries import ConfigEntry

type EVTripConfigEntry = ConfigEntry[EVTripRuntimeData]

@dataclass
class EVTripRuntimeData:
    coordinator: TripPlannerCoordinator
    trip_manager: TripManager

async def async_setup_entry(hass: HomeAssistant, entry: EVTripConfigEntry) -> bool:
    trip_manager = TripManager(hass, entry)
    coordinator = TripPlannerCoordinator(hass, entry, trip_manager)
    
    await coordinator.async_config_entry_first_refresh()  # Lanza ConfigEntryNotReady si falla
    
    entry.runtime_data = EVTripRuntimeData(
        coordinator=coordinator,
        trip_manager=trip_manager,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: EVTripConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # ← NO necesita limpiar hass.data
```

Eliminar completamente `DATA_RUNTIME` y todos los namespaces `f"{DOMAIN}_{entry_id}"`.

### R-04 · `async_remove_entry` Limpia Entity Registry y usa runtime_data — CRÍTICO

```python
async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Elimina completamente todos los rastros de la integración."""
    from homeassistant.helpers import entity_registry as er
    
    # 1. Limpiar Entity Registry
    entity_registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        entity_registry.async_remove(entity_entry.entity_id)
    
    # 2. Limpiar storage del trip_manager
    if hasattr(entry, 'runtime_data') and entry.runtime_data:
        await entry.runtime_data.trip_manager.async_remove_all_data()
    
    # 3. Eliminar helpers de input si existen
    # (código de limpieza de input_datetime, etc.)
```

### R-05 · Implementar `RestoreSensor` para Sensores con Datos Valiosos — ALTO

```python
# Para sensores de energía, siguiente viaje, etc.
from homeassistant.helpers.restore_state import RestoreSensor

class TripPlannerSensor(CoordinatorEntity[TripPlannerCoordinator], RestoreSensor):
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Restaurar estado previo para evitar Unknown tras reinicio
        last_data = await self.async_get_last_sensor_data()
        if last_data and self.coordinator.data is None:
            self._attr_native_value = last_data.native_value
```

Solo aplicar a sensores donde mostrar el valor anterior es mejor que `Unknown`:
- `kwh_needed_today`, `hours_needed_today`, `next_trip`, `next_deadline`

### R-06 · Prohibido `unittest.mock` en Producción — CRÍTICO

```python
# ❌ ABSOLUTAMENTE PROHIBIDO en cualquier archivo fuera de tests/
from unittest.mock import MagicMock

# ✅ CORRECTO: Si coordinator es None, es un bug. Fallar rápido.
if coordinator is None:
    raise ConfigEntryError(f"coordinator cannot be None for vehicle {vehicle_id}")
```

### R-07 · Implementar `diagnostics.py` — MEDIO (requerido para HACS Quality)

```python
# ev_trip_planner/diagnostics.py
from homeassistant.components.diagnostics import async_redact_data

TO_REDACT = {"vehicle_name", "license_plate", "home_address"}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    runtime = entry.runtime_data
    return async_redact_data({
        "config_version": entry.version,
        "coordinator_last_update": str(runtime.coordinator.last_update_success),
        "coordinator_data_keys": list(runtime.coordinator.data.keys()) if runtime.coordinator.data else [],
        "trip_count": {
            "recurring": len(runtime.coordinator.data.get("recurring_trips", [])) if runtime.coordinator.data else 0,
            "punctual": len(runtime.coordinator.data.get("punctual_trips", [])) if runtime.coordinator.data else 0,
        },
    }, TO_REDACT)
```

Añadir `"diagnostics"` a `manifest.json`:
```json
{
  "quality_scale": "silver"
}
```

### R-08 · `async_migrate_entry` Debe Migrar Entity Registry — ALTO

```python
from homeassistant.helpers.entity_registry import async_migrate_entries

async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    current_version = entry.version
    
    if current_version < 2:
        # Migrar formato de unique_id: "ev_trip_planner_kwh_today" → "ev_trip_planner_{vehicle_id}_kwh_today"
        vehicle_id = entry.data.get("vehicle_id", "default")
        
        async def migrate_unique_id(entity_entry):
            old = entity_entry.unique_id
            if old.startswith(f"{DOMAIN}_") and f"_{vehicle_id}_" not in old:
                suffix = old.removeprefix(f"{DOMAIN}_")
                return {"new_unique_id": f"{DOMAIN}_{vehicle_id}_{suffix}"}
        
        await async_migrate_entries(hass, entry.entry_id, migrate_unique_id)
        hass.config_entries.async_update_entry(entry, version=2)
    
    return True
```

### R-09 · `ConfigEntryNotReady` Obligatorio en `async_setup_entry` — MEDIO

```python
from homeassistant.exceptions import ConfigEntryNotReady

async def async_setup_entry(hass, entry):
    coordinator = TripPlannerCoordinator(hass, entry, trip_manager)
    
    try:
        await coordinator.async_config_entry_first_refresh()
        # ← async_config_entry_first_refresh lanza ConfigEntryNotReady automáticamente
        # si _async_update_data lanza UpdateFailed o cualquier excepción
    except ConfigEntryNotReady:
        raise  # Re-lanzar para que HA reintente el setup
```

Si el primer refresh falla, HA reintentará el setup automáticamente con backoff exponencial. Sin `ConfigEntryNotReady`, el setup falla silenciosamente y los sensores quedan en estado `Unavailable` permanentemente.

### R-10 · `__init__.py` Solo Ciclo de Vida (<150 líneas) — CRÍTICO

El archivo `__init__.py` solo puede contener:
- `PLATFORMS` constante
- `EVTripRuntimeData` dataclass
- `async_setup(hass, config)` (si existe)
- `async_setup_entry(hass, entry)`
- `async_unload_entry(hass, entry)`
- `async_remove_entry(hass, entry)`
- `async_migrate_entry(hass, entry)`

**Todo lo demás va en su propio módulo:**
- Handlers de servicios → `services.py`
- Lógica de coordinador → `coordinator.py` (crear este archivo)
- Helpers de dashboard → `dashboard.py` (ya existe, mantener)
- Definiciones de sensores → `definitions.py` (crear)

### R-11 · Logs Con Nivel Correcto — MEDIO

```python
# ❌ PROHIBIDO — spam de WARNING en flujo normal
_LOGGER.warning("=== async_setup_entry START === vehicle=%s", vehicle_id)
_LOGGER.warning("=== _get_manager - runtime_data keys: %s ===", ...)

# ✅ CORRECTO
_LOGGER.debug("async_setup_entry start vehicle=%s", vehicle_id)  # flujo normal
_LOGGER.info("Integration setup complete vehicle=%s", vehicle_id)  # evento importante
_LOGGER.warning("Coordinator failed, will retry: %s", err)  # situación anómala recuperable
_LOGGER.error("Cannot initialize trip_manager: %s", err)  # fallo crítico
```

### R-12 · No Duplicar Clases para Compatibilidad con Tests — CRÍTICO

```python
# ❌ PROHIBIDO — alias de compatibilidad que divergen de la implementación real
class RecurringTripsCountSensor(TripPlannerSensor):
    """Sensor for counting recurring trips (alias for backward compatibility)."""
    # ... implementación completamente diferente a la clase base

# ✅ CORRECTO — una clase, los tests usan la misma implementación
# Si los tests fallan porque la interfaz cambió, hay que actualizar los tests
```

***

## 4. Tabla Comparativa de Gaps vs. Integraciones de Referencia

| Patrón | ev-trip-planner | Bambu Lab | Bermuda | Battery Notes | Versatile Thermostat |
|---|---|---|---|---|---|
| `_attr_unique_id` en todos los sensores | ❌ 7/8 ausente | ✅ | ✅ | ✅ | ✅ |
| `CoordinatorEntity` como base | ❌ | ✅ | ✅ | ✅ | ✅ |
| `SensorEntityDescription` + `definitions.py` | ❌ | ✅ | ✅ | ✅ | ❌ |
| `entry.runtime_data` tipado | ❌ usa string global | ✅ | ✅ | ✅ | ❌ parcial |
| `RestoreSensor` / `RestoreEntity` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `diagnostics.py` | ❌ | ✅ | ❌ | ✅ | ❌ |
| `async_migrate_entry` + Entity Registry | ❌ solo config data | ❌ | ✅ | ✅ | ❌ |
| `ConfigEntryNotReady` en first refresh | ✅ parcial | ✅ | ✅ | ✅ | ✅ |
| `__init__.py` < 200 líneas | ❌ 5000+ | ✅ ~460 | ✅ ~140 | ✅ ~360 | ✅ ~210 |
| Cero imports de `unittest.mock` | ❌ | ✅ | ✅ | ✅ | ✅ |
| Sin clases alias de compatibilidad | ❌ | ✅ | ✅ | ✅ | ✅ |
| Limpiar Entity Registry en remove | ❌ | ✅ vía HA | ✅ vía HA | ✅ explícito | ✅ vía HA |

***

## 5. Arquitectura Target Final

```
custom_components/ev_trip_planner/
├── __init__.py          # <150 líneas: SOLO lifecycle (setup/unload/remove/migrate)
│                        # Exporta: EVTripRuntimeData, EVTripConfigEntry
├── coordinator.py       # TripPlannerCoordinator(DataUpdateCoordinator) — CREAR
├── definitions.py       # TRIP_SENSORS tuple[TripSensorEntityDescription] — CREAR
├── diagnostics.py       # async_get_config_entry_diagnostics — CREAR
├── sensor.py            # Una clase: TripPlannerSensor(CoordinatorEntity, RestoreSensor)
├── services.py          # Handlers de servicios + registro — EXTRAER de __init__.py
├── trip_manager.py      # Lógica de negocio (mantener, pocos cambios)
├── config_flow.py       # Config flow (mantener, añadir version=2)
├── const.py             # Constantes (mantener)
└── ...resto sin cambios
```

**Flujo de datos correcto (único camino válido):**

```
Servicio HA invocado (add_trip / remove_trip / etc.)
        │
        ▼
services.py handler
        │  solo llama a:
        ▼
trip_manager.async_add_trip(...)
        │
        ▼
coordinator.async_refresh()   ← única llamada que dispara actualizaciones
        │
        ▼
coordinator._async_update_data()
        │  construye coordinator.data = {...}
        ▼
CoordinatorEntity listeners notificados automáticamente
        │
        ▼
TripPlannerSensor.native_value lee coordinator.data
        │
        ▼
async_write_ha_state() → UI de HA actualizada
```

***

## 6. Orden de Prioridad para Refactoring

Implementar en este orden para maximizar estabilidad con el mínimo de cambios:

1. **Sprint 1 (Crítico — elimina duplicados y zombis):**
   - Añadir `_attr_unique_id` a todos los sensores existentes
   - Crear `coordinator.py` con `TripPlannerCoordinator(DataUpdateCoordinator)`
   - Cambiar herencia de sensores a `CoordinatorEntity`
   - Limpiar imports de `unittest.mock`

2. **Sprint 2 (Alto — estabilidad de lifecycle):**
   - Migrar a `entry.runtime_data` con `@dataclass` tipado
   - Refactorizar `__init__.py` extrayendo servicios a `services.py`
   - Implementar `async_remove_entry` con limpieza de Entity Registry
   - Añadir `ConfigEntryNotReady` en `async_config_entry_first_refresh`

3. **Sprint 3 (Medio — calidad y mantenibilidad):**
   - Crear `definitions.py` con `SensorEntityDescription`
   - Consolidar 8 clases de sensor en 1
   - Implementar `RestoreSensor`
   - Crear `diagnostics.py`
   - Migrar `async_migrate_entry` para incluir Entity Registry

***

## 7. Checklist de Revisión de PR

Antes de hacer merge de cualquier PR:

**Identidad de entidades:**
- [ ] ¿Todos los `SensorEntity` tienen `_attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}"`?
- [ ] ¿El `device_info` usa `identifiers={(DOMAIN, vehicle_id)}` consistente?

**Arquitectura:**
- [ ] ¿Los sensores heredan de `CoordinatorEntity`?
- [ ] ¿`native_value` lee de `self.coordinator.data`, nunca de `trip_manager` directamente?
- [ ] ¿No hay `async_update()` en sensores que usan coordinador?

**Código limpio:**
- [ ] ¿Cero imports de `unittest.mock` fuera de `tests/`?
- [ ] ¿No hay clases "alias" creadas para compatibilidad con tests?
- [ ] ¿Los logs de flujo normal usan `DEBUG`, no `WARNING`?

**Lifecycle:**
- [ ] ¿`__init__.py` tiene menos de 200 líneas?
- [ ] ¿`async_remove_entry` limpia Entity Registry?
- [ ] ¿`async_setup_entry` no limpia storage existente?
- [ ] ¿Se usa `entry.runtime_data` en vez de `hass.data[DATA_RUNTIME]`?

**Nuevo código:**
- [ ] ¿Nuevos sensores usan `TripSensorEntityDescription` en `definitions.py`?
- [ ] ¿Sensores con datos valiosos implementan `RestoreSensor`?