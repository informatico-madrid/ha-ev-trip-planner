"""Shared utilities for services.

Provides helpers (_get_coordinator, _get_manager, _find_entry_by_vehicle, etc.)
used by _handler_factories.py, _lookup.py, and presence.py.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from ..const import DOMAIN
from ..coordinator import TripPlannerCoordinator
from ..trip.manager import TripManager
from ..utils import normalize_vehicle_id

if TYPE_CHECKING:
    pass  # no type-only imports needed

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Type alias for coordinator
CoordinatorType = TripPlannerCoordinator

_LOGGER = logging.getLogger(__name__)


def _find_entry_by_vehicle(hass: HomeAssistant, vehicle_id: str) -> ConfigEntry | None:
    """Find config entry by vehicle name (case-insensitive)."""
    normalized_vehicle_id = vehicle_id.lower()
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data is None:
            _LOGGER.warning("Entry %s has None data, skipping", entry.entry_id)
            continue
        entry_vehicle_name = entry.data.get("vehicle_name", "")
        normalized_entry_name = normalize_vehicle_id(entry_vehicle_name)
        if normalized_entry_name == normalized_vehicle_id:
            return entry
    return None


@callback
def _get_coordinator(
    hass: HomeAssistant,
    vehicle_id: str,
) -> Optional[CoordinatorType]:
    """Get coordinator for vehicle."""
    entry = _find_entry_by_vehicle(hass, vehicle_id)
    if not entry:
        return None
    return entry.runtime_data.coordinator if entry.runtime_data else None


async def _get_manager(hass: HomeAssistant, vehicle_id: str) -> TripManager:
    """Get or create TripManager for vehicle."""
    _LOGGER.info("=== _get_manager START - vehicle_id: %s ===", vehicle_id)
    entry = _find_entry_by_vehicle(hass, vehicle_id)
    if not entry:
        _LOGGER.error(
            "=== _get_manager ERROR - Vehicle %s not found in config entries ===",
            vehicle_id,
        )
        raise ValueError(f"Vehicle {vehicle_id} not found in config entries")
    _LOGGER.info(
        "=== _get_manager - Found entry: %s, entry_id: %s ===",
        entry.unique_id,
        entry.entry_id,
    )

    # Use entry.runtime_data set by __init__.py::async_setup_entry
    runtime_data = entry.runtime_data
    _LOGGER.debug("=== _get_manager - runtime_data: %s ===", runtime_data)

    # Retrieve trip_manager from entry.runtime_data
    trip_manager = runtime_data.trip_manager if runtime_data else None
    _LOGGER.debug(
        "=== _get_manager - trip_manager from runtime_data: %s ===", trip_manager
    )

    # If manager not found in runtime storage, create new one and load from HA storage
    if not trip_manager:
        _LOGGER.info(
            "=== _get_manager - Creating new TripManager for vehicle %s ===", vehicle_id
        )
        trip_manager = TripManager(hass, vehicle_id)
        _LOGGER.info(
            "=== _get_manager - Before async_setup - trips: recurring=%d, punctual=%d ===",
            len(trip_manager._recurring_trips),
            len(trip_manager._punctual_trips),
        )

        # Load trips from HA storage
        try:
            _LOGGER.info("=== _get_manager - Calling trip_manager.async_setup() ===")
            await trip_manager.async_setup()
            _LOGGER.info(
                "=== _get_manager - After async_setup - trips: recurring=%d, punctual=%d ===",
                len(trip_manager._recurring_trips),
                len(trip_manager._punctual_trips),
            )
        except Exception as setup_err:  # pragma: no cover
            _LOGGER.error(
                "=== _get_manager - Error setting up manager for %s: %s ===",
                vehicle_id,
                setup_err,
                exc_info=True,
            )

        _LOGGER.info(
            "=== _get_manager - Manager created and set up for %s ===", vehicle_id
        )
        _LOGGER.info(
            "=== _get_manager - Trips loaded: %d recurring, %d punctual ===",
            len(trip_manager._recurring_trips),
            len(trip_manager._punctual_trips),
        )
    else:
        _LOGGER.info(
            "=== _get_manager - Manager already exists for %s, trips: %d recurring, %d punctual ===",
            vehicle_id,
            len(trip_manager._recurring_trips),
            len(trip_manager._punctual_trips),
        )

    _LOGGER.info(
        "=== _get_manager END - returning manager for vehicle %s ===", vehicle_id
    )
    return trip_manager


async def _ensure_setup(mgr: TripManager) -> None:
    """Ensure TripManager is set up before operations.

    The trip_manager from runtime_data should already be set up.
    """
    pass


def build_presence_config(entry: ConfigEntry) -> dict[str, Any]:
    """Build presence_config dict from entry.data for PresenceMonitor."""
    from ..const import (
        CONF_CHARGING_SENSOR,
        CONF_HOME_COORDINATES,
        CONF_HOME_SENSOR,
        CONF_NOTIFICATION_SERVICE,
        CONF_PLUGGED_SENSOR,
        CONF_SOC_SENSOR,
        CONF_VEHICLE_COORDINATES_SENSOR,
    )

    return {
        CONF_HOME_SENSOR: entry.data.get(CONF_HOME_SENSOR),
        CONF_PLUGGED_SENSOR: entry.data.get(CONF_PLUGGED_SENSOR),
        CONF_CHARGING_SENSOR: entry.data.get(CONF_CHARGING_SENSOR),
        CONF_HOME_COORDINATES: entry.data.get(CONF_HOME_COORDINATES),
        CONF_VEHICLE_COORDINATES_SENSOR: entry.data.get(
            CONF_VEHICLE_COORDINATES_SENSOR
        ),
        CONF_NOTIFICATION_SERVICE: entry.data.get(CONF_NOTIFICATION_SERVICE),
        CONF_SOC_SENSOR: entry.data.get(CONF_SOC_SENSOR),
    }
