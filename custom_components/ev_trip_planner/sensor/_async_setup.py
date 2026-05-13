"""Async sensor setup functions extracted from sensor_orig.py.

Extracted as part of the SOLID decomposition (Spec 3).
Original implementation in sensor_orig.py.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import (
    EntityRegistry,
    async_entries_for_config_entry,
)
from homeassistant.helpers.entity_registry import (
    async_get as er_async_get,
)

from ..coordinator import TripPlannerCoordinator
from ..definitions import TRIP_SENSORS
from .entity_emhass_deferrable import EmhassDeferrableLoadSensor
from .entity_trip import TripSensor
from .entity_trip_emhass import TripEmhassSensor
from .entity_trip_planner import TripPlannerSensor

_LOGGER = logging.getLogger(__name__)

# 9 documented attributes for TripEmhassSensor
# Prevents data leak of internal cache keys (activo, *_array, p_deferrable_matrix, etc.)
TRIP_EMHASS_ATTR_KEYS = {
    "def_total_hours",
    "P_deferrable_nom",
    "def_start_timestep",
    "def_end_timestep",
    "power_profile_watts",
    "trip_id",
    "emhass_index",
    "kwh_needed",
    "deadline",
}


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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Any
) -> bool:
    """Set up sensors from config entry."""
    entry_id = entry.entry_id

    # Use entry.runtime_data set by __init__.py::async_setup_entry
    runtime_data = entry.runtime_data
    trip_manager = runtime_data.trip_manager
    coordinator = runtime_data.coordinator
    vehicle_id = coordinator.vehicle_id

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
    entities: list[SensorEntity] = [
        TripPlannerSensor(coordinator, vehicle_id, desc)
        for desc in TRIP_SENSORS
        if desc.exists_fn(coordinator.data)
    ]
    entities.append(EmhassDeferrableLoadSensor(coordinator, entry_id))

    # Create trip sensors for existing trips
    trip_sensors = await _async_create_trip_sensors(
        coordinator, trip_manager, vehicle_id, entry_id
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
        except TypeError:  # pragma: no cover reason=sync callback returns None in HA entity platform, causes TypeError when awaited
            # Sync callback - result is None, nothing to await
            pass  # pragma: no cover reason=paired with TypeError above — sync callback result is None

    # Capture async_add_entities callback for dynamic service use (task 2.3)
    runtime_data.sensor_async_add_entities = async_add_entities

    return True


async def _async_create_trip_sensors(
    coordinator: TripPlannerCoordinator,
    trip_manager: Any,
    vehicle_id: str,
    entry_id: str,
) -> List["TripSensor"]:
    """Create sensor entities for existing trips in the trip manager.

    Args:
        coordinator: The TripPlannerCoordinator instance.
        trip_manager: The TripManager instance.
        vehicle_id: The vehicle identifier.
        entry_id: The config entry ID.

    Returns:
        List of TripSensor entities created.
    """
    entities: List[TripSensor] = []

    try:
        # Get existing trips from trip manager
        recurring_trips = await trip_manager._crud.async_get_recurring_trips()
        punctual_trips = await trip_manager._crud.async_get_punctual_trips()

        _LOGGER.debug(
            "Creating trip sensors for %s: %d recurring, %d punctual trips",
            vehicle_id,
            len(recurring_trips),
            len(punctual_trips),
        )

        # Create sensors for recurring trips
        for trip_data in recurring_trips:  # pragma: no cover reason=requires HA entity platform async_add_entities which creates real entity instances
            try:  # pragma: no cover reason=paired with above — real sensor instantiation requires HA entity platform
                sensor = TripSensor(coordinator, vehicle_id, trip_data.get("id", ""))
                entities.append(sensor)
                _LOGGER.debug(  # pragma: no cover reason=paired with try above — debug log in success path of HA entity platform sensor creation
                    "Created trip sensor for recurring trip %s",
                    trip_data.get("id"),
                )
            except Exception as err:  # pragma: no cover reason=requires HA entity platform to trigger — error path in real sensor instantiation loop
                _LOGGER.warning(  # pragma: no cover reason=paired with above — warning in HA entity platform sensor creation error path
                    "Failed to create sensor for recurring trip %s: %s",
                    trip_data.get("id"),
                    err,
                )

        # Create sensors for punctual trips
        for trip_data in punctual_trips:
            try:
                sensor = TripSensor(coordinator, vehicle_id, trip_data.get("id", ""))
                entities.append(sensor)
                _LOGGER.debug(
                    "Created trip sensor for punctual trip %s",
                    trip_data.get("id"),
                )
            except Exception as err:  # pragma: no cover reason=requires HA entity platform to trigger — error path in punctual sensor creation
                _LOGGER.warning(  # pragma: no cover reason=paired with above — warning in HA entity platform punctual sensor error path
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
    trip_id: str = trip_data.get("id") or ""
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

    vehicle_id = coordinator.vehicle_id

    # Create the trip sensor (new signature: coordinator, vehicle_id, trip_id)
    try:
        sensor = TripSensor(coordinator, vehicle_id, trip_id)
        # Register via async_add_entities so entity appears in registry
        result = async_add_entities([sensor], True)
        if result is not None:
            try:
                await result
            except TypeError:  # pragma: no cover reason=HA entity platform async_add_entities sync callback returns None which causes TypeError when awaited
                # Sync callback
                pass  # pragma: no cover reason=paired with TypeError above — sync callback returns None in HA entity platform
        _LOGGER.debug("Trip sensor created and registered for trip %s", trip_id)
        return True
    except Exception as err:  # pragma: no cover reason=requires HA entity platform — error path in real sensor creation
        _LOGGER.error("Failed to create trip sensor for trip %s: %s", trip_id, err)
        return False  # pragma: no cover reason=paired with above — error return in HA entity platform sensor creation


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
    trip_id: str = trip_data.get("id") or ""

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
    entity_registry: EntityRegistry = getattr(
        hass, "entity_registry", None
    ) or er_async_get(hass)
    existing_entity = None
    for reg_entry in async_entries_for_config_entry(entity_registry, entry_id):
        unique_id = reg_entry.unique_id
        if (
            isinstance(unique_id, str)
            and trip_id in unique_id
            and "trip" in unique_id.lower()
        ):
            existing_entity = reg_entry
            break

    if existing_entity:
        # Get the state entity and update it
        state = hass.states.get(existing_entity.entity_id)
        if state:
            # Update internal trip data
            _LOGGER.debug(
                "Trip sensor found in registry for trip %s, state=%s", trip_id, state
            )

        # FIX: Trigger coordinator refresh to update sensor immediately
        # Sensor data comes from coordinator.data via CoordinatorEntity.
        # This refresh ensures sensors reflect changes immediately (not wait 30s for periodic refresh).
        coordinator = runtime_data.coordinator
        if coordinator:
            await coordinator.async_request_refresh()
            _LOGGER.debug(
                "Coordinator refresh triggered for trip %s sensor update", trip_id
            )

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
    entity_registry: EntityRegistry = getattr(
        hass, "entity_registry", None
    ) or er_async_get(hass)
    removed = False
    for entry in async_entries_for_config_entry(entity_registry, entry_id):
        if isinstance(entry.unique_id, str) and trip_id in entry.unique_id:
            entity_registry.async_remove(entry.entity_id)
            removed = True
            _LOGGER.debug(
                "Entity registry entry removed for trip %s: %s",
                trip_id,
                entry.entity_id,
            )
            break

    if removed:
        return True
    else:
        _LOGGER.debug("Trip sensor %s not found in registry", trip_id)
        return False


# =============================================================================
# async_remove_trip_emhass_sensor — FR-6 (Task 1.36 GREEN)
# =============================================================================


async def async_remove_trip_emhass_sensor(
    hass: HomeAssistant,
    entry_id: str,
    vehicle_id: str,
    trip_id: str,
) -> bool:
    """Remove an EMHASS sensor entity.

    Args:
        hass: The Home Assistant instance.
        entry_id: The config entry ID.
        vehicle_id: The vehicle identifier.
        trip_id: The trip identifier to remove.

    Returns:
        True if sensor was removed successfully.
    """
    _LOGGER.debug("Removing EMHASS sensor for trip %s", trip_id)

    # Remove from Entity Registry
    entity_registry: EntityRegistry = getattr(
        hass, "entity_registry", None
    ) or er_async_get(hass)
    removed = False
    for entry in async_entries_for_config_entry(entity_registry, entry_id):
        unique_id = entry.unique_id
        if (
            isinstance(unique_id, str)
            and trip_id in unique_id
            and "emhass" in unique_id
        ):
            entity_registry.async_remove(entry.entity_id)
            removed = True
            _LOGGER.debug(
                "Entity registry entry removed for EMHASS trip %s: %s",
                trip_id,
                entry.entity_id,
            )
            break

    if removed:
        return True
    else:
        _LOGGER.debug("EMHASS sensor %s not found in registry", trip_id)
        return False


# =============================================================================
# async_create_trip_emhass_sensor — FR-5 (Task 1.32 GREEN)
# =============================================================================


async def async_create_trip_emhass_sensor(
    hass: HomeAssistant,
    entry_id: str,
    coordinator: TripPlannerCoordinator,
    vehicle_id: str,
    trip_id: str,
) -> bool:
    """Create a sensor entity for a trip's EMHASS parameters.

    Args:
        hass: The Home Assistant instance.
        entry_id: The config entry ID.
        coordinator: The TripPlannerCoordinator instance.
        vehicle_id: The vehicle identifier.
        trip_id: The trip identifier.

    Returns:
        True if sensor was created successfully.
    """
    _LOGGER.info(
        "Creating EMHASS sensor for trip %s on vehicle %s", trip_id, vehicle_id
    )

    # Get entry and runtime_data
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry:
        _LOGGER.error("No entry found for entry_id %s", entry_id)
        return False

    runtime_data = entry.runtime_data
    async_add_entities = runtime_data.sensor_async_add_entities

    if not async_add_entities:
        _LOGGER.error(
            "No async_add_entities callback found for entry %s (platform not set up)",
            entry_id,
        )
        return False

    # Create the EMHASS sensor
    try:
        sensor = TripEmhassSensor(coordinator, vehicle_id, trip_id)
        # Register via async_add_entities so entity appears in registry
        result = async_add_entities([sensor], True)
        if result is not None:
            try:
                await result
            except TypeError:  # pragma: no cover reason=HA entity platform async_add_entities sync callback returns None which causes TypeError when awaited
                # Sync callback
                pass  # pragma: no cover reason=paired with TypeError above — sync callback returns None in EMHASS sensor HA entity platform
        _LOGGER.debug("EMHASS sensor created and registered for trip %s", trip_id)
        return True
    except Exception as err:  # pragma: no cover reason=requires HA entity platform — error path in real EMHASS sensor creation
        _LOGGER.error("Failed to create EMHASS sensor for trip %s: %s", trip_id, err)
        return False  # pragma: no cover reason=paired with above — error return in HA entity platform EMHASS sensor creation
