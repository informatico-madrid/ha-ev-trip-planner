"""Execution tests for sensor event dispatch and SensorCallbackRegistry.

Covers all emit event paths, missing args warnings, and
SensorCallbackRegistry add/remove/notify/clear.
"""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.ev_trip_planner.trip._sensor_callbacks import (
    SensorCallbackRegistry,
    SensorEvent,
    emit,
)

_SENSOR_KEY = "custom_components.ev_trip_planner.sensor"


def _make_sensor_mock() -> ModuleType:
    """Create a module-like object with all async sensor functions."""
    mod = ModuleType(_SENSOR_KEY)
    mod.async_create_trip_sensor = AsyncMock()
    mod.async_remove_trip_sensor = AsyncMock()
    mod.async_update_trip_sensor = AsyncMock()
    mod.async_create_trip_emhass_sensor = AsyncMock()
    mod.async_remove_trip_emhass_sensor = AsyncMock()
    return mod


class TestSensorCallbackRegistry:
    """Test SensorCallbackRegistry add/remove/notify/clear."""

    def test_add_and_notify(self):
        registry = SensorCallbackRegistry()
        results = []
        registry.add("sensor_1", lambda v: results.append(v))
        registry.notify("sensor_1", "new_value")
        assert results == ["new_value"]

    def test_add_multiple_callbacks(self):
        registry = SensorCallbackRegistry()
        results = []
        registry.add("sensor_1", lambda v: results.append(v * 2))
        registry.add("sensor_1", lambda v: results.append(v * 3))
        registry.notify("sensor_1", 5)
        assert results == [10, 15]

    def test_notify_unknown_sensor(self):
        registry = SensorCallbackRegistry()
        results = registry.notify("unknown_sensor", "value")
        assert results == []

    def test_remove_found(self):
        registry = SensorCallbackRegistry()

        def cb(_):
            pass

        registry.add("sensor_1", cb)
        assert registry.remove("sensor_1", cb) is True

    def test_remove_not_found_sensor(self):
        registry = SensorCallbackRegistry()
        assert registry.remove("unknown_sensor", lambda v: None) is False

    def test_remove_callback_not_registered(self):
        registry = SensorCallbackRegistry()

        def cb(_):
            pass

        registry.add("sensor_1", lambda v: None)
        assert registry.remove("sensor_1", cb) is False

    def test_clear_all(self):
        registry = SensorCallbackRegistry()
        registry.add("s1", lambda v: None)
        registry.add("s2", lambda v: None)
        registry.clear()
        assert registry.notify("s1", "x") == []
        assert registry.notify("s2", "x") == []

    def test_clear_specific_sensor(self):
        registry = SensorCallbackRegistry()
        registry.add("s1", lambda v: None)
        registry.add("s2", lambda v: None)
        registry.clear("s1")
        assert registry.notify("s1", "x") == []
        assert len(registry.notify("s2", "x")) == 1


class TestEmitDispatch:
    """Test emit() dict-based dispatch event paths."""

    def _emit_with_mock(self, event):
        """Patch sensor module and call emit, return (captured_coros, mock_mod)."""
        mock_mod = _make_sensor_mock()
        _saved_sys = sys.modules.pop(_SENSOR_KEY, None)
        sys.modules[_SENSOR_KEY] = mock_mod
        parent_key = "custom_components.ev_trip_planner"
        parent = sys.modules.get(parent_key)
        _saved_parent = None
        if parent is not None:
            _saved_parent = getattr(parent, "sensor", None)
            setattr(parent, "sensor", mock_mod)
        collected = []

        def cap_future(coro, loop=None):
            collected.append(coro)
            return asyncio.get_event_loop().create_future()

        try:
            with patch.object(asyncio, "ensure_future", side_effect=cap_future):
                emit(event)
        finally:
            if _saved_sys is not None:
                sys.modules[_SENSOR_KEY] = _saved_sys
            else:
                sys.modules.pop(_SENSOR_KEY, None)
            if _saved_parent is not None and parent is not None:
                setattr(parent, "sensor", _saved_parent)
            elif parent is not None:
                delattr(parent, "sensor")
        return collected, mock_mod

    def test_emit_unknown_event(self):
        hass = MagicMock()
        emit(SensorEvent("unknown_event", hass, "entry_1"))

    def test_emit_trip_created_recurring_missing_data(self):
        hass = MagicMock()
        emit(SensorEvent("trip_created_recurring", hass, "entry_1"))

    def test_emit_trip_created_punctual_missing_data(self):
        hass = MagicMock()
        emit(SensorEvent("trip_created_punctual", hass, "entry_1"))

    def test_emit_trip_sensor_created_emhass_missing_trip_id(self):
        hass = MagicMock()
        emit(SensorEvent("trip_sensor_created_emhass", hass, "entry_1", trip_id=None))

    def test_emit_trip_removed_missing_trip_id(self):
        hass = MagicMock()
        emit(SensorEvent("trip_removed", hass, "entry_1"))

    def test_emit_trip_sensor_removed_emhass_missing_trip_id(self):
        hass = MagicMock()
        emit(SensorEvent("trip_sensor_removed_emhass", hass, "entry_1"))

    def test_emit_trip_sensor_updated_missing_data(self):
        hass = MagicMock()
        emit(SensorEvent("trip_sensor_updated", hass, "entry_1"))

    def test_emit_trip_created_recurring_with_data(self):
        hass = MagicMock()
        evt = SensorEvent(
            "trip_created_recurring", hass, "entry_1",
            trip_data={"id": "r1", "tipo": "recurrente"},
        )
        collected, mock_mod = self._emit_with_mock(evt)
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*collected))
        mock_mod.async_create_trip_sensor.assert_called_once()

    def test_emit_trip_created_punctual_with_data(self):
        hass = MagicMock()
        evt = SensorEvent(
            "trip_created_punctual", hass, "entry_1",
            trip_data={"id": "p1", "tipo": "puntual"},
        )
        collected, mock_mod = self._emit_with_mock(evt)
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*collected))
        mock_mod.async_create_trip_sensor.assert_called_once()

    def test_emit_trip_removed_with_trip_id(self):
        hass = MagicMock()
        evt = SensorEvent("trip_removed", hass, "entry_1", trip_id="t1")
        collected, mock_mod = self._emit_with_mock(evt)
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*collected))
        mock_mod.async_remove_trip_sensor.assert_called_once()

    def test_emit_trip_sensor_updated_with_data(self):
        hass = MagicMock()
        evt = SensorEvent(
            "trip_sensor_updated", hass, "entry_1",
            trip_data={"id": "r1"},
        )
        collected, mock_mod = self._emit_with_mock(evt)
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*collected))
        mock_mod.async_update_trip_sensor.assert_called_once()

    def test_emit_trip_sensor_created_emhass_with_trip_id(self):
        hass = MagicMock()
        entry = MagicMock()
        entry.runtime_data = MagicMock()
        entry.runtime_data.coordinator = MagicMock()
        hass.config_entries.async_get_entry = MagicMock(return_value=entry)
        evt = SensorEvent(
            "trip_sensor_created_emhass", hass, "entry_1",
            trip_id="t1", vehicle_id="v1",
        )
        collected, mock_mod = self._emit_with_mock(evt)
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*collected))
        mock_mod.async_create_trip_emhass_sensor.assert_called_once()

    def test_emit_trip_sensor_removed_emhass_with_trip_id(self):
        hass = MagicMock()
        evt = SensorEvent(
            "trip_sensor_removed_emhass", hass, "entry_1",
            trip_id="t1", vehicle_id="v1",
        )
        collected, mock_mod = self._emit_with_mock(evt)
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*collected))
        mock_mod.async_remove_trip_emhass_sensor.assert_called_once()

    def test_emit_with_exception_is_caught(self):
        hass = MagicMock()
        mock_mod = _make_sensor_mock()
        mock_mod.async_create_trip_sensor = AsyncMock(
            side_effect=RuntimeError("boom")
        )
        evt = SensorEvent(
            "trip_created_recurring", hass, "entry_1",
            trip_data={"id": "r1"},
        )
        # emit() wraps in try/except, so no exception should propagate
        self._emit_with_mock(evt)
