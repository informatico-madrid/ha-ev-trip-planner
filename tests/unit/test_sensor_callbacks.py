"""Execution tests for _SensorCallbacks and SensorCallbackRegistry.

Covers all emit event paths, missing args warnings, and
SensorCallbackRegistry add/remove/notify/clear.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.ev_trip_planner.trip._sensor_callbacks import (
    SensorCallbackRegistry,
    _SensorCallbacks,
)


class TestSensorCallbackRegistry:
    """Test SensorCallbackRegistry add/remove/notify/clear."""

    def test_add_and_notify(self):
        """Add callback, notify, verify it fires."""
        registry = SensorCallbackRegistry()
        results = []
        registry.add("sensor_1", lambda v: results.append(v))
        registry.notify("sensor_1", "new_value")
        assert results == ["new_value"]

    def test_add_multiple_callbacks(self):
        """Multiple callbacks for same sensor all fire."""
        registry = SensorCallbackRegistry()
        results = []
        registry.add("sensor_1", lambda v: results.append(v * 2))
        registry.add("sensor_1", lambda v: results.append(v * 3))
        registry.notify("sensor_1", 5)
        assert results == [10, 15]

    def test_notify_unknown_sensor(self):
        """Notify on unknown sensor returns empty list."""
        registry = SensorCallbackRegistry()
        results = registry.notify("unknown_sensor", "value")
        assert results == []

    def test_remove_found(self):
        """Remove existing callback returns True."""
        registry = SensorCallbackRegistry()

        def cb(_):
            pass

        registry.add("sensor_1", cb)
        assert registry.remove("sensor_1", cb) is True

    def test_remove_not_found_sensor(self):
        """Remove from unknown sensor returns False (line 63)."""
        registry = SensorCallbackRegistry()
        assert registry.remove("unknown_sensor", lambda v: None) is False

    def test_remove_callback_not_registered(self):
        """Remove callback not in list returns False."""
        registry = SensorCallbackRegistry()

        def cb(_):
            pass

        registry.add("sensor_1", lambda v: None)
        assert registry.remove("sensor_1", cb) is False

    def test_clear_all(self):
        """Clear without sensor_id removes all callbacks."""
        registry = SensorCallbackRegistry()
        registry.add("s1", lambda v: None)
        registry.add("s2", lambda v: None)
        registry.clear()
        assert registry.notify("s1", "x") == []
        assert registry.notify("s2", "x") == []

    def test_clear_specific_sensor(self):
        """Clear with sensor_id removes only that sensor's callbacks."""
        registry = SensorCallbackRegistry()
        registry.add("s1", lambda v: None)
        registry.add("s2", lambda v: None)
        registry.clear("s1")
        assert registry.notify("s1", "x") == []
        assert len(registry.notify("s2", "x")) == 1


class TestSensorCallbacksEmit:
    """Test _SensorCallbacks.emit event paths."""

    def _make_callbacks(self):
        """Create a _SensorCallbacks with mocked state."""
        return _SensorCallbacks()

    def test_emit_unknown_event(self):
        """Unknown event logs debug message."""
        sc = self._make_callbacks()
        hass = MagicMock()

        # Should not raise
        sc.emit("unknown_event", hass, "entry_1")

    def test_emit_trip_created_recurring_missing_data(self):
        """trip_created_recurring without trip_data logs warning (line 141)."""
        sc = self._make_callbacks()
        hass = MagicMock()
        with patch.object(sc, "_get_sensor_mod") as mock_mod:
            mock_mod.return_value = MagicMock()
            sc.emit("trip_created_recurring", hass, "entry_1")
            # Should not raise, just log warning

    def test_emit_trip_created_punctual_missing_data(self):
        """trip_created_punctual without trip_data logs warning (line 149)."""
        sc = self._make_callbacks()
        hass = MagicMock()
        with patch.object(sc, "_get_sensor_mod") as mock_mod:
            mock_mod.return_value = MagicMock()
            sc.emit("trip_created_punctual", hass, "entry_1")

    def test_emit_trip_sensor_created_emhass_missing_trip_id(self):
        """trip_sensor_created_emhass without trip_id logs warning (line 157)."""
        sc = self._make_callbacks()
        hass = MagicMock()
        with patch.object(sc, "_get_sensor_mod") as mock_mod:
            mock_mod.return_value = MagicMock()
            sc.emit("trip_sensor_created_emhass", hass, "entry_1", trip_id=None)

    def test_emit_trip_removed_missing_trip_id(self):
        """trip_removed without trip_id logs warning (line 163)."""
        sc = self._make_callbacks()
        hass = MagicMock()
        with patch.object(sc, "_get_sensor_mod") as mock_mod:
            mock_mod.return_value = MagicMock()
            sc.emit("trip_removed", hass, "entry_1")

    def test_emit_trip_sensor_removed_emhass_missing_trip_id(self):
        """trip_sensor_removed_emhass without trip_id logs warning (line 171)."""
        sc = self._make_callbacks()
        hass = MagicMock()
        with patch.object(sc, "_get_sensor_mod") as mock_mod:
            mock_mod.return_value = MagicMock()
            sc.emit("trip_sensor_removed_emhass", hass, "entry_1")

    def test_emit_trip_sensor_updated_missing_data(self):
        """trip_sensor_updated without trip_data logs warning (line 177)."""
        sc = self._make_callbacks()
        hass = MagicMock()
        with patch.object(sc, "_get_sensor_mod") as mock_mod:
            mock_mod.return_value = MagicMock()
            sc.emit("trip_sensor_updated", hass, "entry_1")

    def test_emit_trip_created_recurring_with_data(self):
        """trip_created_recurring with trip_data calls async_create_trip_sensor."""
        sc = self._make_callbacks()
        hass = MagicMock()
        mock_mod = MagicMock()
        mock_mod.async_create_trip_sensor = AsyncMock()
        with patch.object(sc, "_get_sensor_mod", return_value=mock_mod):
            sc.emit(
                "trip_created_recurring", hass, "entry_1",
                trip_data={"id": "rec_1", "tipo": "recurring"},
            )
            mock_mod.async_create_trip_sensor.assert_called_once()

    def test_emit_trip_created_punctual_with_data(self):
        """trip_created_punctual with trip_data calls async_create_trip_sensor."""
        sc = self._make_callbacks()
        hass = MagicMock()
        mock_mod = MagicMock()
        mock_mod.async_create_trip_sensor = AsyncMock()
        with patch.object(sc, "_get_sensor_mod", return_value=mock_mod):
            sc.emit(
                "trip_created_punctual", hass, "entry_1",
                trip_data={"id": "pun_1", "tipo": "punctual"},
            )
            mock_mod.async_create_trip_sensor.assert_called_once()

    def test_emit_trip_removed_with_trip_id(self):
        """trip_removed with trip_id calls async_remove_trip_sensor."""
        sc = self._make_callbacks()
        hass = MagicMock()
        mock_mod = MagicMock()
        mock_mod.async_remove_trip_sensor = AsyncMock()
        with patch.object(sc, "_get_sensor_mod", return_value=mock_mod):
            sc.emit("trip_removed", hass, "entry_1", trip_id="pun_1")
            mock_mod.async_remove_trip_sensor.assert_called_once()

    def test_emit_trip_sensor_updated_with_data(self):
        """trip_sensor_updated with trip_data calls async_update_trip_sensor."""
        sc = self._make_callbacks()
        hass = MagicMock()
        mock_mod = MagicMock()
        mock_mod.async_update_trip_sensor = AsyncMock()
        with patch.object(sc, "_get_sensor_mod", return_value=mock_mod):
            sc.emit(
                "trip_sensor_updated", hass, "entry_1",
                trip_data={"id": "rec_1"},
            )
            mock_mod.async_update_trip_sensor.assert_called_once()

    def test_emit_trip_sensor_created_emhass_with_trip_id(self):
        """trip_sensor_created_emhass with trip_id calls _emit_create_emhass."""
        sc = self._make_callbacks()
        hass = MagicMock()
        entry = MagicMock()
        entry.runtime_data = MagicMock()
        entry.runtime_data.coordinator = MagicMock()
        hass.config_entries.async_get_entry = MagicMock(return_value=entry)
        mock_mod = MagicMock()
        mock_mod.async_create_trip_emhass_sensor = AsyncMock()
        with patch.object(sc, "_get_sensor_mod", return_value=mock_mod):
            sc.emit(
                "trip_sensor_created_emhass", hass, "entry_1",
                trip_id="pun_1", vehicle_id="test_vehicle",
            )
            mock_mod.async_create_trip_emhass_sensor.assert_called_once()

    def test_emit_trip_sensor_removed_emhass_with_trip_id(self):
        """trip_sensor_removed_emhass with trip_id calls _emit_remove_emhass."""
        sc = self._make_callbacks()
        hass = MagicMock()
        mock_mod = MagicMock()
        mock_mod.async_remove_trip_emhass_sensor = AsyncMock()
        with patch.object(sc, "_get_sensor_mod", return_value=mock_mod):
            sc.emit(
                "trip_sensor_removed_emhass", hass, "entry_1",
                trip_id="pun_1", vehicle_id="test_vehicle",
            )
            mock_mod.async_remove_trip_emhass_sensor.assert_called_once()

    def test_emit_with_exception_is_caught(self):
        """Exception in emit is logged, not propagated."""
        sc = self._make_callbacks()
        hass = MagicMock()
        with patch.object(sc, "_get_sensor_mod") as mock_mod:
            mock_mod.side_effect = RuntimeError("import failed")
            # Should not raise
            sc.emit(
                "trip_created_recurring", hass, "entry_1",
                trip_data={"id": "rec_1"},
            )
