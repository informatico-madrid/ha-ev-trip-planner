"""Sensor callback registry for managing sensor value change callbacks."""

from __future__ import annotations

from typing import Any, Callable, Optional


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
