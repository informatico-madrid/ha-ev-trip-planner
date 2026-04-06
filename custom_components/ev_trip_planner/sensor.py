"""Sensores para el componente EV Trip Planner.

Implementa entidades de sensores para mostrar información de viajes y carga.
Cumple con las reglas de HA 2026 para tipado estricto y runtime_data.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DATA_RUNTIME
from .definitions import TripSensorEntityDescription, TRIP_SENSORS
from .const import (
    CONF_CHARGING_POWER,
    DEFAULT_CHARGING_POWER,
    DOMAIN,
    EMHASS_STATE_ERROR,
    EMHASS_STATE_READY,
    TRIP_TYPE_PUNCTUAL,
)
from .coordinator import TripPlannerCoordinator
from .trip_manager import TripManager

_LOGGER = logging.getLogger(__name__)


def _format_window_time(value: Any) -> str | None:
    """Format window time to HH:MM from datetime or ISO string.

    Args:
        value: Either a datetime object or an ISO format string

    Returns:
        Time formatted as HH:MM, or None if formatting fails
    """
    if value is None:
        return None
    try:
        if isinstance(value, datetime):
            dt_value = value
        elif isinstance(value, str):
            dt_value = datetime.fromisoformat(value)
        else:
            return None
        return dt_value.strftime("%H:%M")
    except (ValueError, TypeError, AttributeError):
        return None


class TripPlannerSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity):
    """Sensor base for EV Trip Planner using CoordinatorEntity pattern.

    Reads from coordinator.data via entity_description.value_fn().
    Sets _attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}".
    """

    def __init__(
        self,
        coordinator: TripPlannerCoordinator,
        vehicle_id: str,
        entity_description: TripSensorEntityDescription,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: TripPlannerCoordinator instance.
            vehicle_id: Vehicle identifier.
            entity_description: Description with value_fn and attrs_fn.
        """
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._vehicle_id = vehicle_id
        self.entity_description = entity_description
        self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_{entity_description.key}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_has_entity_name = True
        self._attr_name = f"EV Trip Planner {entity_description.key}"
        # Store cached attributes for synchronous access
        self._cached_attrs: Dict[str, Any] = {}

    @property
    def native_value(self) -> Any:
        """Return sensor value via entity_description.value_fn."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return attributes from coordinator.data via entity_description.attrs_fn."""
        if self.coordinator.data is None:
            return {}
        return self.entity_description.attrs_fn(self.coordinator.data)

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device info for the vehicle."""
        return {
            "identifiers": {(DOMAIN, self._vehicle_id)},
            "name": f"EV Trip Planner {self._vehicle_id}",
            "manufacturer": "Home Assistant",
            "model": "EV Trip Planner",
            "sw_version": "2026.3.0",
        }


class EmhassDeferrableLoadSensor(SensorEntity):
    """Sensor para el perfil de carga diferible de EMHASS.

    Este sensor proporciona los datos necesarios para la integración con EMHASS:
    - power_profile_watts: Array de potencia en watts por hora
    - deferrables_schedule: Calendario de cargas diferibles

    Platform: template
    Entity: sensor.emhass_perfil_diferible_{entry_id}
    """

    def __init__(
        self,
        hass: HomeAssistant,
        trip_manager: TripManager,
        entry_id: str,
    ) -> None:
        """Inicializa el sensor de carga diferible."""
        self.hass = hass
        self.trip_manager = trip_manager
        self._entry_id = entry_id
        self._attr_unique_id = f"emhass_perfil_diferible_{entry_id}"
        self._attr_name = f"EMHASS Perfil Diferible {entry_id}"
        self._attr_has_entity_name = True
        self._attr_native_value = "ready"
        self._cached_attrs: Dict[str, Any] = {}

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return self._attr_unique_id

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device info.

        Returns device info with the vehicle_name from the config entry,
        ensuring the device name uses the slug-based identifier and
        displays the human-readable vehicle name.
        """
        vehicle_id = self.trip_manager.vehicle_id
        vehicle_name = vehicle_id  # Fallback to vehicle_id if config entry not found

        try:
            # Find the config entry for this specific vehicle_id
            for config_entry in self.hass.config_entries.async_entries(DOMAIN):
                if (
                    config_entry.data
                    and config_entry.data.get("vehicle_name") == vehicle_id
                ):
                    vehicle_name = config_entry.data.get("vehicle_name", vehicle_id)
                    break
        except Exception:
            pass

        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"EV Trip Planner {vehicle_name}",
            "manufacturer": "Home Assistant",
            "model": "EV Trip Planner",
            "sw_version": "2026.3.0",
        }

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return self._cached_attrs

    async def async_update(self) -> None:
        """Actualiza el estado del sensor."""
        try:
            # Find config entry by entry_id
            entry = None
            for config_entry in self.hass.config_entries.async_entries(DOMAIN):
                if config_entry.entry_id == self._entry_id:
                    entry = config_entry
                    break

            if not entry or not entry.data:
                _LOGGER.warning("No config entry found for %s", self._entry_id)
                return

            charging_power_kw = entry.data.get(
                CONF_CHARGING_POWER, DEFAULT_CHARGING_POWER
            )
            planning_horizon_days = entry.data.get("planning_horizon_days", 7)
            _LOGGER.debug(
                "EmhassDeferrableLoadSensor update for %s: charging_power=%s, horizon=%s",
                self._entry_id,
                charging_power_kw,
                planning_horizon_days,
            )

            power_profile = await self.trip_manager.async_generate_power_profile(
                charging_power_kw=charging_power_kw,
                planning_horizon_days=planning_horizon_days,
            )

            schedule = await self.trip_manager.async_generate_deferrables_schedule(
                charging_power_kw=charging_power_kw,
                planning_horizon_days=planning_horizon_days,
            )

            # Get active trips count for sensor attributes
            recurring_trips = await self.trip_manager.async_get_recurring_trips()
            punctual_trips = await self.trip_manager.async_get_punctual_trips()
            trips_count = len(recurring_trips) + len(punctual_trips)
            vehicle_id = self.trip_manager.vehicle_id

            self._cached_attrs = {
                "power_profile_watts": power_profile,
                "deferrables_schedule": schedule,
                "last_update": datetime.now().isoformat(),
                "emhass_status": EMHASS_STATE_READY,
                "trips_count": trips_count,
                "vehicle_id": vehicle_id,
            }
            self._attr_native_value = EMHASS_STATE_READY
            self.async_schedule_update_ha_state()
            _LOGGER.debug(
                "EmhassDeferrableLoadSensor update for %s: ready, profile_len=%d, schedule_len=%d",
                self._entry_id,
                len(power_profile) if power_profile else 0,
                len(schedule) if schedule else 0,
            )

        except Exception as err:
            _LOGGER.error(
                "Error actualizando sensor EMHASS %s: %s",
                self._entry_id,
                err,
                exc_info=True,
            )
            self._cached_attrs["emhass_status"] = EMHASS_STATE_ERROR
            self._cached_attrs["last_update"] = datetime.now().isoformat()
            self._attr_native_value = EMHASS_STATE_ERROR

    async def async_will_remove_from_hass(self) -> None:
        """Clean up when entity is removed from Home Assistant."""
        if hasattr(self.trip_manager, "_emhass_adapter") and self.trip_manager._emhass_adapter is not None:
            await self.trip_manager._emhass_adapter.async_cleanup_vehicle_indices()


class TripSensor(SensorEntity):
    """Sensor para un viaje específico.

    Crea una entidad de sensor para cada viaje programado.
    El sensor muestra información del viaje como:
    - Descripción/destino
    - Distancia (km)
    - Energía estimada (kWh)
    - Fecha/hora del viaje
    - Estado (pendiente/completado/cancelado)

    Entity: sensor.trip_{trip_id}
    """

    def __init__(
        self,
        hass: HomeAssistant,
        trip_manager: TripManager,
        trip_data: Dict[str, Any],
    ) -> None:
        """Inicializa el sensor del viaje.

        Args:
            hass: Home Assistant instance
            trip_manager: TripManager instance for this vehicle
            trip_data: Complete trip data including id, tipo, etc.
        """
        self.hass = hass
        self.trip_manager = trip_manager
        self._trip_data = trip_data
        self._trip_id = trip_data.get("id", "unknown")
        self._trip_type = trip_data.get("tipo", "unknown")

        # Build unique_id from trip_id
        self._attr_unique_id = f"trip_{self._trip_id}"
        self._attr_name = f"Trip {trip_data.get('descripcion', self._trip_id)}"
        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_state_class = None

        # Set enum options for estado
        self._attr_options = ["pendiente", "completado", "cancelado"]

        # Set native value (estado)
        if self._trip_type == TRIP_TYPE_PUNCTUAL:
            self._attr_native_value = trip_data.get("estado", "pendiente")
        else:
            self._attr_native_value = "recurrente"

        # Store trip details as attributes
        self._attr_extra_state_attributes: Dict[str, Any] = {
            "trip_id": self._trip_id,
            "trip_type": self._trip_type,
            "descripcion": trip_data.get("descripcion", ""),
            "km": trip_data.get("km", 0.0),
            "kwh": trip_data.get("kwh", 0.0),
            "fecha_hora": trip_data.get("datetime", trip_data.get("hora", "")),
            "activo": trip_data.get("activo", True),
            "estado": trip_data.get("estado", "pendiente"),
        }

        # Add soc_target if soc_objetivo is present (AC-3)
        soc_objetivo = trip_data.get("soc_objetivo")
        if soc_objetivo is not None:
            self._attr_extra_state_attributes["soc_target"] = soc_objetivo

        # Add deficit_from_previous if deficit_acumulado is present (AC-3)
        deficit_acumulado = trip_data.get("deficit_acumulado")
        if deficit_acumulado is not None:
            self._attr_extra_state_attributes["deficit_from_previous"] = deficit_acumulado

        # Add EMHASS-related info
        self._attr_extra_state_attributes.update(self._get_emhass_info())

        # Add charging_window if ventana_carga exists
        ventana_carga = trip_data.get("ventana_carga")
        if ventana_carga:
            inicio = ventana_carga.get("inicio_ventana", "")
            fin = ventana_carga.get("fin_ventana", "")
            start_time = _format_window_time(inicio)
            end_time = _format_window_time(fin)
            if start_time and end_time:
                self._attr_extra_state_attributes["charging_window"] = {
                    "start": start_time,
                    "end": end_time,
                }

    def _get_emhass_info(self) -> Dict[str, Any]:
        """Get EMHASS-related info for this trip.

        Returns dict with EMHASS-related attributes (e.g., p_deferrable_index).
        Designed to be extended with future EMHASS attributes like soc_target.
        """
        emhass_info: Dict[str, Any] = {}
        emhass_adapter = self.trip_manager.get_emhass_adapter()
        if emhass_adapter is not None:
            p_deferrable_index = emhass_adapter.get_assigned_index(self._trip_id)
            if p_deferrable_index is not None:
                emhass_info["p_deferrable_index"] = p_deferrable_index
        return emhass_info

    @property
    def native_value(self) -> Any:
        """Return sensor value based on trip type and status."""
        if self._trip_type == TRIP_TYPE_PUNCTUAL:
            return self._trip_data.get("estado", "pendiente")
        return "recurrente"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return trip details as attributes."""
        return self._attr_extra_state_attributes.copy()

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device info for the trip sensor.

        Returns device info with the vehicle_name from the config entry,
        ensuring the device name uses the slug-based identifier and
        displays the human-readable vehicle name.
        """
        vehicle_id = self.trip_manager.vehicle_id
        vehicle_name = vehicle_id  # Fallback to vehicle_id if config entry not found

        try:
            # Find the config entry for this specific vehicle_id
            for config_entry in self.hass.config_entries.async_entries(DOMAIN):
                if (
                    config_entry.data
                    and config_entry.data.get("vehicle_name") == vehicle_id
                ):
                    vehicle_name = config_entry.data.get("vehicle_name", vehicle_id)
                    break
        except Exception:
            pass

        return {
            "identifiers": {(DOMAIN, f"{vehicle_id}_{self._trip_id}")},
            "name": f"Trip {self._trip_id} - {vehicle_name}",
            "manufacturer": "Home Assistant",
            "model": "EV Trip Planner",
            "sw_version": "2026.3.0",
            "via_device": (DOMAIN, vehicle_id),
        }

    def _update_state_attributes_from_trip_data(
        self, trip_data: Dict[str, Any]
    ) -> None:
        """Update extra_state_attributes from trip data.

        Args:
            trip_data: Trip data to extract attributes from.
        """
        # Add deficit_from_previous if deficit_acumulado is present (AC-3)
        deficit_acumulado = trip_data.get("deficit_acumulado")
        if deficit_acumulado is not None:
            self._attr_extra_state_attributes["deficit_from_previous"] = deficit_acumulado

        # Add soc_target if soc_objetivo is present (AC-3)
        soc_objetivo = trip_data.get("soc_objetivo")
        if soc_objetivo is not None:
            self._attr_extra_state_attributes["soc_target"] = soc_objetivo

        # Add EMHASS-related info
        self._attr_extra_state_attributes.update(self._get_emhass_info())

        # Add charging_window if ventana_carga exists
        ventana_carga = trip_data.get("ventana_carga")
        if ventana_carga:
            inicio = ventana_carga.get("inicio_ventana", "")
            fin = ventana_carga.get("fin_ventana", "")
            start_time = _format_window_time(inicio)
            end_time = _format_window_time(fin)
            if start_time and end_time:
                self._attr_extra_state_attributes["charging_window"] = {
                    "start": start_time,
                    "end": end_time,
                }

    def update_from_trip_data(self, trip_data: Dict[str, Any]) -> None:
        """Update sensor state from trip data.

        Args:
            trip_data: Updated trip data
        """
        self._trip_data = trip_data
        self._attr_name = f"Trip {trip_data.get('descripcion', self._trip_id)}"
        if self._trip_type == TRIP_TYPE_PUNCTUAL:
            self._attr_native_value = trip_data.get("estado", "pendiente")
        else:
            self._attr_native_value = "recurrente"
        self._attr_extra_state_attributes = {
            "trip_id": self._trip_id,
            "trip_type": self._trip_type,
            "descripcion": trip_data.get("descripcion", ""),
            "km": trip_data.get("km", 0.0),
            "kwh": trip_data.get("kwh", 0.0),
            "fecha_hora": trip_data.get("datetime", trip_data.get("hora", "")),
            "activo": trip_data.get("activo", True),
            "estado": trip_data.get("estado", "pendiente"),
        }
        # Update state attributes from trip data (AC-4)
        self._update_state_attributes_from_trip_data(trip_data)

        # Trigger state update only if entity_id is set (entity is registered)
        if self.entity_id is not None:
            self.async_schedule_update_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Any
) -> bool:
    """Set up sensors from config entry."""
    vehicle_id = entry.data.get("vehicle_name", "")
    entry_id = entry.entry_id

    # Use the same namespace pattern as __init__.py: f"{DOMAIN}_{entry_id}"
    namespace = f"{DOMAIN}_{entry_id}"

    # Use DATA_RUNTIME namespace correctly
    runtime_data = hass.data.get(DATA_RUNTIME, {})
    namespace_data = runtime_data.get(namespace, {})
    trip_manager = namespace_data.get("trip_manager")
    coordinator = namespace_data.get("coordinator")

    _LOGGER.debug(
        "trip_manager lookup for %s: namespace=%s, found=%s",
        vehicle_id,
        namespace,
        trip_manager is not None,
    )

    if not trip_manager:
        # Legacy fallback for older configurations
        _LOGGER.debug(
            "trip_manager lookup: trying legacy fallback for %s (entry_id=%s)",
            vehicle_id,
            entry_id,
        )
        # Try legacy namespace pattern
        legacy_namespace = f"ev_trip_planner_{entry_id}"
        legacy_runtime_data = hass.data.get(DATA_RUNTIME, {})
        legacy_namespace_data = legacy_runtime_data.get(legacy_namespace, {})
        trip_manager = legacy_namespace_data.get("trip_manager")
        coordinator = legacy_namespace_data.get("coordinator")

        if not trip_manager:
            # Try old DOMAIN-based storage
            trip_manager = (
                hass.data.get(DOMAIN, {}).get(entry_id, {}).get("trip_manager")
            )
            coordinator = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("coordinator")
        _LOGGER.debug(
            "trip_manager lookup: legacy fallback result for %s: found=%s",
            vehicle_id,
            trip_manager is not None,
        )

    if not trip_manager:
        _LOGGER.error(
            "No trip_manager found for %s (namespace=%s, runtime_data keys=%s)",
            vehicle_id,
            namespace,
            list(runtime_data.keys()) if runtime_data else [],
            exc_info=True,
        )
        return False

    _LOGGER.debug(
        "Setting up sensors for vehicle_id=%s, entry_id=%s, coordinator=%s",
        vehicle_id,
        entry_id,
        coordinator is not None,
    )

    entities = [
        TripPlannerSensor(coordinator, vehicle_id, desc)
        for desc in TRIP_SENSORS
    ]
    entities.append(EmhassDeferrableLoadSensor(hass, trip_manager, entry_id))

    # Create trip sensors for existing trips
    trip_sensors = await _async_create_trip_sensors(
        hass, trip_manager, vehicle_id, entry_id
    )
    entities.extend(trip_sensors)

    _LOGGER.debug(
        "Created sensors for %s: %s",
        vehicle_id,
        [type(e).__name__ for e in entities],
    )

    async_add_entities(entities)
    return True


async def _async_create_trip_sensors(
    hass: HomeAssistant,
    trip_manager: Any,
    vehicle_id: str,
    entry_id: str,
) -> List["TripSensor"]:
    """Create sensor entities for existing trips in the trip manager.

    Args:
        hass: The Home Assistant instance.
        trip_manager: The TripManager instance.
        vehicle_id: The vehicle identifier.
        entry_id: The config entry ID.

    Returns:
        List of TripSensor entities created.
    """
    entities: List[TripSensor] = []

    try:
        # Get existing trips from trip manager
        recurring_trips = await trip_manager.async_get_recurring_trips()
        punctual_trips = await trip_manager.async_get_punctual_trips()

        _LOGGER.debug(
            "Creating trip sensors for %s: %d recurring, %d punctual trips",
            vehicle_id,
            len(recurring_trips),
            len(punctual_trips),
        )

        # Create sensors for recurring trips
        for trip_data in recurring_trips:
            try:
                sensor = TripSensor(hass, trip_manager, trip_data)
                entities.append(sensor)
                _LOGGER.debug(
                    "Created trip sensor for recurring trip %s",
                    trip_data.get("id"),
                )
            except Exception as err:
                _LOGGER.warning(
                    "Failed to create sensor for recurring trip %s: %s",
                    trip_data.get("id"),
                    err,
                )

        # Create sensors for punctual trips
        for trip_data in punctual_trips:
            try:
                sensor = TripSensor(hass, trip_manager, trip_data)
                entities.append(sensor)
                _LOGGER.debug(
                    "Created trip sensor for punctual trip %s",
                    trip_data.get("id"),
                )
            except Exception as err:
                _LOGGER.warning(
                    "Failed to create sensor for punctual trip %s: %s",
                    trip_data.get("id"),
                    err,
                )

        _LOGGER.info(
            "Created %d trip sensors for vehicle %s",
            len(entities),
            vehicle_id,
        )

    except Exception as err:
        _LOGGER.error(
            "Error creating trip sensors for vehicle %s: %s",
            vehicle_id,
            err,
            exc_info=True,
        )

    return entities


async def async_create_trip_sensor(
    hass: HomeAssistant,
    entry_id: str,
    trip_data: Dict[str, Any],
) -> bool:
    """Create a sensor entity for a trip.

    Args:
        hass: The Home Assistant instance.
        entry_id: The config entry ID.
        trip_data: The trip data dictionary (includes id and tipo).

    Returns:
        True if sensor was created successfully.
    """
    from . import DATA_RUNTIME
    from .const import DOMAIN

    trip_id = trip_data.get("id")
    trip_type = trip_data.get("tipo", "recurrente")

    _LOGGER.info("Creating trip sensor for trip %s (type=%s)", trip_id, trip_type)

    # Get the namespace and trip_manager
    namespace = f"{DOMAIN}_{entry_id}"
    runtime_data = hass.data.get(DATA_RUNTIME, {})
    namespace_data = runtime_data.get(namespace, {})
    trip_manager = namespace_data.get("trip_manager")

    if not trip_manager:
        _LOGGER.error("No trip_manager found for entry %s", entry_id)
        return False

    # Create the trip sensor (new signature - trip_id and trip_type derived from trip_data)
    try:
        sensor = TripSensor(hass, trip_manager, trip_data)
        hass.data[DATA_RUNTIME][namespace]["trip_sensors"] = hass.data[DATA_RUNTIME][
            namespace
        ].get("trip_sensors", {})
        hass.data[DATA_RUNTIME][namespace]["trip_sensors"][trip_id] = sensor
        _LOGGER.debug("Trip sensor created for trip %s", trip_id)
        return True
    except Exception as err:  # pragma: no cover
        _LOGGER.error("Failed to create trip sensor for trip %s: %s", trip_id, err)
        return False


async def async_update_trip_sensor(
    hass: HomeAssistant,
    entry_id: str,
    trip_data: Dict[str, Any],
) -> bool:
    """Update a trip sensor entity with new data.

    Args:
        hass: The Home Assistant instance.
        entry_id: The config entry ID.
        trip_data: The updated trip data dictionary (includes id).

    Returns:
        True if sensor was updated successfully.
    """
    from . import DATA_RUNTIME
    from .const import DOMAIN

    trip_id = trip_data.get("id")

    _LOGGER.debug("Updating trip sensor for trip %s", trip_id)

    # Get the namespace and trip_manager
    namespace = f"{DOMAIN}_{entry_id}"
    runtime_data = hass.data.get(DATA_RUNTIME, {})
    namespace_data = runtime_data.get(namespace, {})
    trip_manager = namespace_data.get("trip_manager")

    if not trip_manager:
        _LOGGER.error("No trip_manager found for entry %s", entry_id)
        return False

    # Get existing sensor and update it
    trip_sensors = namespace_data.get("trip_sensors", {})
    if trip_id in trip_sensors:
        sensor = trip_sensors[trip_id]
        # Update the trip data before refreshing the sensor
        sensor._trip_data = trip_data
        try:
            sensor.update_from_trip_data(trip_data)
        except Exception as err:
            # Handle case where entity is not registered (e.g., in tests)
            _LOGGER.warning(
                "Could not update trip sensor %s (entity not registered): %s",
                trip_id,
                err,
            )
            # Still update the internal data even if state update fails
            sensor._attr_name = f"Trip {trip_data.get('descripcion', trip_id)}"
            sensor._attr_extra_state_attributes = {
                "trip_id": sensor._trip_id,
                "trip_type": sensor._trip_type,
                "descripcion": trip_data.get("descripcion", ""),
                "km": trip_data.get("km", 0.0),
                "kwh": trip_data.get("kwh", 0.0),
                "fecha_hora": trip_data.get("datetime", trip_data.get("hora", "")),
                "activo": trip_data.get("activo", True),
                "estado": trip_data.get("estado", "pendiente"),
            }
        _LOGGER.debug("Trip sensor updated for trip %s", trip_id)
        return True
    else:
        # Sensor doesn't exist, create it (new signature)
        return await async_create_trip_sensor(hass, entry_id, trip_data)


async def async_remove_trip_sensor(
    hass: HomeAssistant,
    entry_id: str,
    trip_id: str,
) -> bool:
    """Remove a trip sensor entity.

    Args:
        hass: The Home Assistant instance.
        entry_id: The config entry ID.
        trip_id: The trip identifier to remove.

    Returns:
        True if sensor was removed successfully.
    """
    from . import DATA_RUNTIME
    from .const import DOMAIN

    _LOGGER.debug("Removing trip sensor for trip %s", trip_id)

    # Get the namespace
    namespace = f"{DOMAIN}_{entry_id}"
    runtime_data = hass.data.get(DATA_RUNTIME, {})
    namespace_data = runtime_data.get(namespace, {})

    # Remove from trip_sensors dict
    trip_sensors = namespace_data.get("trip_sensors", {})
    if trip_id in trip_sensors:
        del trip_sensors[trip_id]
        _LOGGER.debug("Trip sensor removed for trip %s", trip_id)
        return True
    else:
        _LOGGER.debug("Trip sensor %s not found", trip_id)
        return False
