"""Sensor callback system for trip lifecycle events.

Replaces lazy `from .sensor import ...` imports with a single
`_sensor_callbacks.emit(event, ...)` call pattern used by the
_CRUDMixin.

The sensor module is imported at runtime to avoid circular imports.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

_UNSET = object()

_LOGGER = logging.getLogger(__name__)


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


class _SensorCallbacks:
    """Handles all sensor lifecycle operations for trips.

    Provides a single `emit` method that replaces the pattern of
    `from .sensor import <func>` in multiple CRUD methods.
    """

    def _get_sensor_mod(self):
        """Lazy import sensor module to avoid circular dependency."""
        # pylint: disable=import-outside-toplevel
        from . import sensor as _sensor_mod
        return _sensor_mod

    def emit(
        self,
        event: str,
        hass: HomeAssistant,
        entry_id: str,
        trip_data: Dict[str, Any] | None = None,
        trip_id: str | None = None,
    ) -> None:
        """Dispatch a sensor lifecycle event.

        Args:
            event: One of 'trip_created_recurring', 'trip_created_punctual',
                   'trip_removed', 'trip_sensor_created', 'trip_sensor_updated',
                   'trip_sensor_removed', 'trip_sensor_created_emhass',
                   'trip_sensor_removed_emhass'.
            hass: HomeAssistant instance (required for all operations).
            entry_id: Config entry ID for entity registry lookups.
            trip_data: Trip dictionary (required for create/update).
            trip_id: Trip ID (required for remove/EMHASS sensor).
        """
        try:
            sensor_mod = self._get_sensor_mod()
            if event == "trip_created_recurring":
                sensor_mod.async_create_trip_sensor(hass, entry_id, trip_data)

            elif event == "trip_created_punctual":
                sensor_mod.async_create_trip_sensor(hass, entry_id, trip_data)

            elif event == "trip_sensor_created_emhass":
                self._emit_create_emhass(hass, entry_id, trip_id)

            elif event == "trip_removed":
                sensor_mod.async_remove_trip_sensor(hass, entry_id, trip_id)

            elif event == "trip_sensor_removed_emhass":
                self._emit_remove_emhass(hass, entry_id, trip_id)

            elif event == "trip_sensor_updated":
                sensor_mod.async_update_trip_sensor(hass, entry_id, trip_data)

            else:
                _LOGGER.debug("Unknown sensor event: %s", event)

        except Exception as err:
            _LOGGER.error(
                "Error emitting sensor event '%s': %s",
                event,
                err,
                exc_info=True,
            )

    def _emit_create_emhass(
        self,
        hass: HomeAssistant,
        entry_id: str,
        trip_id: str,
    ) -> None:
        """Create an EMHASS sensor for a trip.

        Extracts the coordinator from the config entry's runtime_data.
        """
        try:
            entry: ConfigEntry | None = hass.config_entries.async_get_entry(
                entry_id
            )
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

            sensor_mod = self._get_sensor_mod()
            sensor_mod.async_create_trip_emhass_sensor(
                hass, entry_id, coordinator, trip_id
            )
        except Exception as err:
            _LOGGER.debug(
                "Error creating EMHASS sensor for trip %s: %s",
                trip_id,
                err,
            )

    def _emit_remove_emhass(
        self,
        hass: HomeAssistant,
        entry_id: str,
        trip_id: str,
    ) -> None:
        """Remove an EMHASS sensor for a trip."""
        sensor_mod = self._get_sensor_mod()
        sensor_mod.async_remove_trip_emhass_sensor(
            hass, entry_id, trip_id
        )
