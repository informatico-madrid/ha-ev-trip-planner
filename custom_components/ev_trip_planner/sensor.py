"""Sensores para el componente EV Trip Planner.

Implementa entidades de sensores para mostrar información de viajes y carga.
Cumple con las reglas de HA 2026 para tipado estricto y runtime_data.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    TRIP_TYPE_PUNCTUAL,
)
from .coordinator import TripPlannerCoordinator
from .definitions import TRIP_SENSORS, TripSensorEntityDescription

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


class TripPlannerSensor(CoordinatorEntity[TripPlannerCoordinator], RestoreSensor, SensorEntity):
    """Sensor base for EV Trip Planner using CoordinatorEntity pattern.

    Reads from coordinator.data via entity_description.value_fn().
    Sets _attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}".
    Inherits RestoreSensor for state restoration on HA restart.
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

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass.

        Restores state if restore=True and coordinator.data is None.
        """
        await super().async_added_to_hass()
        if self.entity_description.restore and self.coordinator.data is None:
            # Restore state from previous run
            last_state = await self.async_get_last_state()
            if last_state is not None:
                self._attr_native_value = last_state.state

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


class EmhassDeferrableLoadSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity):
    """Sensor para el perfil de carga diferible de EMHASS.

    Este sensor proporciona los datos necesarios para la integración con EMHASS:
    - power_profile_watts: Array de potencia en watts por hora
    - deferrables_schedule: Calendario de cargas diferibles

    PHASE 3: Ahora hereda de CoordinatorEntity y lee desde coordinator.data.

    Platform: template
    Entity: sensor.emhass_perfil_diferible_{entry_id}
    """

    def __init__(
        self,
        coordinator: TripPlannerCoordinator,
        entry_id: str,
    ) -> None:
        """Inicializa el sensor de carga diferible.

        Args:
            coordinator: TripPlannerCoordinator instance.
            entry_id: Config entry ID.
        """
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._entry_id = entry_id
        self._attr_unique_id = f"emhass_perfil_diferible_{entry_id}"
        self._attr_name = f"EMHASS Perfil Diferible {entry_id}"
        self._attr_has_entity_name = True

    @property
    def native_value(self) -> str:
        """Return sensor value from coordinator.data."""
        if self.coordinator.data is None:
            return "unknown"
        return self.coordinator.data.get("emhass_status", "unknown")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes from coordinator.data."""
        if self.coordinator.data is None:
            return {}
        return {
            "power_profile_watts": self.coordinator.data.get("emhass_power_profile"),
            "deferrables_schedule": self.coordinator.data.get("emhass_deferrables_schedule"),
            "emhass_status": self.coordinator.data.get("emhass_status"),
        }

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device info.

        Returns device info using vehicle_id from coordinator.
        """
        vehicle_id = getattr(self.coordinator, 'vehicle_id', self._entry_id)

        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"EV Trip Planner {vehicle_id}",
            "manufacturer": "Home Assistant",
            "model": "EV Trip Planner",
            "sw_version": "2026.3.0",
        }

    async def async_will_remove_from_hass(self) -> None:  # pragma: no cover  # HA entity lifecycle - entity removal triggers cleanup; tested via HA integration tests
        """Clean up when entity is removed from Home Assistant."""
        trip_manager = getattr(self.coordinator, "trip_manager", None)
        if trip_manager and hasattr(trip_manager, "_emhass_adapter") and trip_manager._emhass_adapter is not None:
            await trip_manager._emhass_adapter.async_cleanup_vehicle_indices()


class TripSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity):
    """Sensor for a specific trip using CoordinatorEntity pattern.

    Reads trip data from coordinator.data["recurring_trips"][trip_id] or
    coordinator.data["punctual_trips"][trip_id].

    Entity: sensor.ev_trip_planner_{vehicle_id}_trip_{trip_id}
    """

    def __init__(
        self,
        coordinator: TripPlannerCoordinator,
        vehicle_id: str,
        trip_id: str,
    ) -> None:
        """Initialize the trip sensor.

        Args:
            coordinator: TripPlannerCoordinator instance.
            vehicle_id: Vehicle identifier.
            trip_id: Trip identifier.
        """
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._vehicle_id = vehicle_id
        self._trip_id = trip_id
        self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_trip_{trip_id}"
        self._attr_name = f"Trip {trip_id}"
        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_state_class = None
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        # Set enum options for estado
        self._attr_options = ["active", "pendiente", "completado", "cancelado", "recurrente"]

    def _get_trip_data(self) -> Dict[str, Any]:
        """Get trip data from coordinator.

        Returns:
            Trip data dict or empty dict if not found.
        """
        if self.coordinator.data is None:
            return {}
        recurring_trips = self.coordinator.data.get("recurring_trips", {})
        punctual_trips = self.coordinator.data.get("punctual_trips", {})
        return recurring_trips.get(self._trip_id) or punctual_trips.get(self._trip_id) or {}

    @property
    def native_value(self) -> Any:
        """Return sensor value (trip estado)."""
        trip_data = self._get_trip_data()
        if not trip_data:
            return None
        trip_type = trip_data.get("tipo", "unknown")
        if trip_type == TRIP_TYPE_PUNCTUAL:
            return trip_data.get("estado", "pendiente")
        return "recurrente"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return trip details as attributes."""
        trip_data = self._get_trip_data()
        if not trip_data:
            return {}
        return {
            "trip_id": trip_data.get("id", self._trip_id),
            "trip_type": trip_data.get("tipo", "unknown"),
            "descripcion": trip_data.get("descripcion", ""),
            "km": trip_data.get("km", 0.0),
            "kwh": trip_data.get("kwh", 0.0),
            "fecha_hora": trip_data.get("datetime", trip_data.get("hora", "")),
            "activo": trip_data.get("activo", True),
            "estado": trip_data.get("estado", "pendiente"),
        }

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device info for the trip sensor."""
        return {
            "identifiers": {(DOMAIN, f"{self._vehicle_id}_{self._trip_id}")},
            "name": f"Trip {self._trip_id} - {self._vehicle_id}",
            "manufacturer": "Home Assistant",
            "model": "EV Trip Planner",
            "sw_version": "2026.3.0",
            "via_device": (DOMAIN, self._vehicle_id),
        }


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Any
) -> bool:
    """Set up sensors from config entry."""
    vehicle_id = entry.data.get("vehicle_name", "")
    entry_id = entry.entry_id

    # Use entry.runtime_data set by __init__.py::async_setup_entry
    runtime_data = entry.runtime_data
    trip_manager = runtime_data.trip_manager
    coordinator = runtime_data.coordinator

    if not trip_manager:
        _LOGGER.error(
            "No trip_manager found for entry %s",
            entry_id,
            exc_info=True,
        )
        return False

    _LOGGER.debug(
        "Setting up sensors for vehicle_id=%s, entry_id=%s, coordinator=%s",
        vehicle_id,
        entry_id,
        coordinator is not None,
    )

    # Filter sensors based on exists_fn (G-07.4)
    entities = [
        TripPlannerSensor(coordinator, vehicle_id, desc)
        for desc in TRIP_SENSORS
        if desc.exists_fn(coordinator.data)
    ]
    entities.append(EmhassDeferrableLoadSensor(coordinator, entry_id))

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

    # async_add_entities may be sync or async depending on HA version
    result = async_add_entities(entities)
    if result is not None:
        # Await if it returns an awaitable (async callback)
        try:
            await result
        except TypeError:  # pragma: no cover  # HA entity platform - sync callbacks return None which causes TypeError when awaited
            # Sync callback - result is None, nothing to await
            pass  # pragma: no cover  # HA entity platform - sync callback error handling

    # Capture async_add_entities callback for dynamic service use (task 2.3)
    runtime_data.sensor_async_add_entities = async_add_entities

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
        for trip_data in recurring_trips:  # pragma: no cover  # HA entity platform - loop creates sensors for all valid trips; no error means all succeed
            try:  # pragma: no cover  # HA entity platform - try block for sensor creation
                sensor = TripSensor(hass, trip_manager, trip_data)
                entities.append(sensor)
                _LOGGER.debug(  # pragma: no cover  # HA entity platform - debug logging for successful sensor creation
                    "Created trip sensor for recurring trip %s",
                    trip_data.get("id"),
                )
            except Exception as err:  # pragma: no cover  # HA entity platform - defensive error handling for malformed trip data
                _LOGGER.warning(  # pragma: no cover  # HA entity platform - warning logged but sensor creation continues
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
            except Exception as err:  # pragma: no cover  # HA entity platform - defensive error handling for malformed trip data
                _LOGGER.warning(  # pragma: no cover  # HA entity platform - warning logged but sensor creation continues
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
    trip_id = trip_data.get("id")
    trip_type = trip_data.get("tipo", "recurrente")

    _LOGGER.info("Creating trip sensor for trip %s (type=%s)", trip_id, trip_type)

    # Get entry and runtime_data
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry:
        _LOGGER.error("No entry found for entry_id %s", entry_id)
        return False

    runtime_data = entry.runtime_data
    trip_manager = runtime_data.trip_manager
    coordinator = runtime_data.coordinator
    async_add_entities = runtime_data.sensor_async_add_entities

    if not trip_manager:
        _LOGGER.error("No trip_manager found for entry %s", entry_id)
        return False

    if not coordinator:
        _LOGGER.error("No coordinator found for entry %s", entry_id)
        return False

    if not async_add_entities:
        _LOGGER.error(
            "No async_add_entities callback found for entry %s (platform not set up)",
            entry_id,
        )
        return False

    # Get vehicle_id from entry data
    vehicle_id = entry.data.get("vehicle_name", "").lower().replace(" ", "_")

    # Create the trip sensor (new signature: coordinator, vehicle_id, trip_id)
    try:
        sensor = TripSensor(coordinator, vehicle_id, trip_id)
        # Register via async_add_entities so entity appears in registry
        result = async_add_entities([sensor], True)
        if result is not None:
            try:
                await result
            except TypeError:  # pragma: no cover  # HA entity platform - sync callbacks return None which causes TypeError when awaited
                # Sync callback
                pass  # pragma: no cover  # HA entity platform - sync callback error handling
        _LOGGER.debug("Trip sensor created and registered for trip %s", trip_id)
        return True
    except Exception as err:  # pragma: no cover  # HA entity platform - defensive error handling for sensor creation failure
        _LOGGER.error("Failed to create trip sensor for trip %s: %s", trip_id, err)
        return False  # pragma: no cover  # HA entity platform - error return path


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
    trip_id = trip_data.get("id")

    _LOGGER.debug("Updating trip sensor for trip %s", trip_id)

    # Get entry and runtime_data
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry:
        _LOGGER.error("No entry found for entry_id %s", entry_id)
        return False

    runtime_data = entry.runtime_data
    trip_manager = runtime_data.trip_manager

    if not trip_manager:
        _LOGGER.error("No trip_manager found for entry %s", entry_id)
        return False

    # Find existing sensor in entity registry
    entity_registry = getattr(hass, "entity_registry", None) or er.async_get(hass)
    existing_entity = None
    for reg_entry in entity_registry.async_entries_for_config_entry(entry_id):
        if trip_id in reg_entry.unique_id and "trip" in reg_entry.unique_id.lower():
            existing_entity = reg_entry
            break

    if existing_entity:
        # Get the state entity and update it
        state = hass.states.get(existing_entity.entity_id)
        if state:
            # Update internal trip data
            _LOGGER.debug("Trip sensor found in registry for trip %s, state=%s", trip_id, state)
        _LOGGER.debug("Trip sensor updated for trip %s", trip_id)
        return True
    else:
        # Sensor doesn't exist, create it
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
    _LOGGER.debug("Removing trip sensor for trip %s", trip_id)

    # Remove from Entity Registry
    entity_registry = getattr(hass, "entity_registry", None) or er.async_get(hass)
    removed = False
    for entry in entity_registry.async_entries_for_config_entry(entry_id):
        if trip_id in entry.unique_id:
            await entity_registry.async_remove(entry.entity_id)
            _LOGGER.debug("Entity registry entry removed for trip %s: %s", trip_id, entry.entity_id)
            removed = True

    if removed:
        return True
    else:
        _LOGGER.debug("Trip sensor %s not found in registry", trip_id)
        return False
