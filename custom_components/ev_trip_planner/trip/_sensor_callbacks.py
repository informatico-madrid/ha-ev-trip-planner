"""Sensor callback system for trip lifecycle events.

Replaces lazy `from .sensor import ...` imports with a single
`_sensor_callbacks.emit(event, ...)` call pattern used by the
_CRUDMixin.

The sensor module is imported at runtime to avoid circular imports.

AP18 fix: Event dispatch uses a dict-based handler map instead of
a 7-branch if-elif chain. Adding new events requires only adding
an entry to EVENT_HANDLERS — no new elif branch.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_UNSET = object()

_LOGGER = logging.getLogger(__name__)


# ── Dispatch map ────────────────────────────────────────────────────────
# AP18 fix: dict dispatch replaces 7-branch if-elif chain.
# Each entry maps an event name to a handler function.
# Adding a new event requires only adding a new entry below.

EVENT_HANDLERS: Dict[str, Callable[..., None]] = {}


def _register(event_name: str) -> Callable:
    """Decorator to register an event handler in EVENT_HANDLERS."""

    def decorator(func):
        EVENT_HANDLERS[event_name] = func
        return func

    return decorator


# ── Event handlers ──────────────────────────────────────────────────────


@_register("trip_created_recurring")
def _handle_trip_created_recurring(
    sensor_mod, hass, entry_id, trip_data, trip_id, vehicle_id
) -> None:
    """Create a trip sensor for a new recurring trip."""
    if trip_data is None:
        _LOGGER.warning("trip_data required for trip_created_recurring event")
        return
    asyncio.ensure_future(
        sensor_mod.async_create_trip_sensor(hass, entry_id, trip_data)
    )


@_register("trip_created_punctual")
def _handle_trip_created_punctual(
    sensor_mod, hass, entry_id, trip_data, trip_id, vehicle_id
) -> None:
    """Create a trip sensor for a new punctual trip."""
    if trip_data is None:
        _LOGGER.warning("trip_data required for trip_created_punctual event")
        return
    asyncio.ensure_future(
        sensor_mod.async_create_trip_sensor(hass, entry_id, trip_data)
    )


@_register("trip_sensor_created_emhass")
def _handle_trip_sensor_created_emhass(
    sensor_mod, hass, entry_id, trip_data, trip_id, vehicle_id
) -> None:
    """Create an EMHASS sensor for a trip."""
    if trip_id is None:
        _LOGGER.warning("trip_id required for trip_sensor_created_emhass event")
        return
    _emit_create_emhass(hass, entry_id, vehicle_id or "", trip_id)


@_register("trip_removed")
def _handle_trip_removed(
    sensor_mod, hass, entry_id, trip_data, trip_id, vehicle_id
) -> None:
    """Remove a trip sensor."""
    if trip_id is None:
        _LOGGER.warning("trip_id required for trip_removed event")
        return
    asyncio.ensure_future(sensor_mod.async_remove_trip_sensor(hass, entry_id, trip_id))


@_register("trip_sensor_removed_emhass")
def _handle_trip_sensor_removed_emhass(
    sensor_mod, hass, entry_id, trip_data, trip_id, vehicle_id
) -> None:
    """Remove an EMHASS sensor for a trip."""
    if trip_id is None:
        _LOGGER.warning("trip_id required for trip_sensor_removed_emhass event")
        return
    _emit_remove_emhass(hass, entry_id, vehicle_id or "", trip_id)


@_register("trip_sensor_updated")
def _handle_trip_sensor_updated(
    sensor_mod, hass, entry_id, trip_data, trip_id, vehicle_id
) -> None:
    """Update a trip sensor with new data."""
    if trip_data is None:
        _LOGGER.warning("trip_data required for trip_sensor_updated event")
        return
    asyncio.ensure_future(
        sensor_mod.async_update_trip_sensor(hass, entry_id, trip_data)
    )


# ── EMHASS helpers ──────────────────────────────────────────────────────


def _emit_create_emhass(
    hass: HomeAssistant,
    entry_id: str,
    vehicle_id: str,
    trip_id: str,
) -> None:
    """Create an EMHASS sensor for a trip.

    Extracts the coordinator from the config entry's runtime_data.
    Called from _handle_trip_sensor_created_emhass via the dispatch map.
    """
    try:
        from .. import sensor as _sensor_mod

        entry: ConfigEntry | None = hass.config_entries.async_get_entry(entry_id)
        if not entry or not entry.runtime_data:
            _LOGGER.warning(
                "Trip EMHASS sensor %s: no config entry or runtime_data",
                trip_id,
            )
            return

        coordinator = entry.runtime_data.coordinator
        if coordinator is None:
            _LOGGER.warning(
                "Trip EMHASS sensor %s: coordinator is None",
                trip_id,
            )
            return

        asyncio.ensure_future(
            _sensor_mod.async_create_trip_emhass_sensor(
                hass, entry_id, coordinator, vehicle_id, trip_id
            )
        )
    except Exception as err:
        _LOGGER.debug(
            "Error creating EMHASS sensor for trip %s: %s",
            trip_id,
            err,
        )


def _emit_remove_emhass(
    hass: HomeAssistant,
    entry_id: str,
    vehicle_id: str,
    trip_id: str,
) -> None:
    """Remove an EMHASS sensor for a trip."""
    from .. import sensor as _sensor_mod

    asyncio.ensure_future(
        _sensor_mod.async_remove_trip_emhass_sensor(hass, entry_id, vehicle_id, trip_id)
    )


# ── Public API ──────────────────────────────────────────────────────────


class SensorCallbackRegistry:
    """Manages callbacks for sensor value changes.

    Provides a simple registry pattern with add, remove, and notify
    methods for reacting to sensor updates.
    """

    def __init__(self) -> None:
        """Initialize the registry with an empty callback map."""
        self._callbacks: dict[str, list[Callable[..., None]]] = {}

    def add(
        self,
        sensor_id: str,
        callback: Callable[..., None],
    ) -> None:
        """Register a callback for a specific sensor.

        Args:
            sensor_id: Unique sensor identifier.
            callback: Callable invoked on sensor update.
        """
        self._callbacks.setdefault(sensor_id, []).append(callback)

    def remove(
        self,
        sensor_id: str,
        callback: Callable[..., None],
    ) -> bool:
        """Remove a previously registered callback.

        Args:
            sensor_id: Sensor identifier the callback was registered under.
            callback: The callback to remove.

        Returns:
            True if the callback was found and removed, False otherwise.
        """
        if sensor_id not in self._callbacks:
            return False
        try:
            self._callbacks[sensor_id].remove(callback)
            return True
        except ValueError:
            return False

    def notify(
        self,
        sensor_id: str,
        value: Any,
    ) -> list[Any]:
        """Notify all registered callbacks for a sensor.

        Args:
            sensor_id: Sensor identifier whose callbacks should fire.
            value: New sensor value passed to each callback.

        Returns:
            List of callback return values.
        """
        results: list[Any] = []
        for cb in self._callbacks.get(sensor_id, []):
            results.append(cb(value))
        return results

    def clear(self, sensor_id: Optional[str] = None) -> None:
        """Remove all callbacks, optionally scoped to one sensor.

        Args:
            sensor_id: If provided, clear only this sensor's callbacks.
                       If None, clear all callbacks.
        """
        if sensor_id is None:
            self._callbacks.clear()
        elif sensor_id in self._callbacks:
            del self._callbacks[sensor_id]


@dataclass(frozen=True)
class SensorEvent:
    """Event data for sensor lifecycle operations."""

    event: str
    hass: HomeAssistant
    entry_id: str
    trip_data: Optional[Dict[str, Any]] = None
    trip_id: Optional[str] = None
    vehicle_id: Optional[str] = None


def emit(event: SensorEvent) -> None:
    """Dispatch a sensor lifecycle event via dict-based handler map.

    Replaces the previous if-elif chain with a dispatch map to avoid
    AP18 branch explosion (7+ branches). Adding new events requires
    only adding an entry to EVENT_HANDLERS — no new elif branch.

    Args:
        event: SensorEvent with all required data.
    """
    event_str = event.event
    hass = event.hass
    entry_id = event.entry_id
    trip_data = event.trip_data
    trip_id = event.trip_id
    vehicle_id = event.vehicle_id
    try:
        from .. import sensor as _sensor_mod

        handler = EVENT_HANDLERS.get(event_str)
        if handler is None:
            _LOGGER.debug("Unknown sensor event: %s", event_str)
            return
        handler(_sensor_mod, hass, entry_id, trip_data, trip_id, vehicle_id)

    except Exception as err:
        _LOGGER.error(
            "Error emitting sensor event '%s': %s",
            event,
            err,
            exc_info=True,
        )
