"""Tests for uncovered emhass/adapter.py paths.

Lines 92, 97, 102: ValueError raises in async_validate_config
Lines 685, 688: _get_current_soc returns None paths
Lines 1065, 1077: deficit results loop break/continue
Lines 1118-1122: SOC unavailable error path in publish_deferrable_load
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter


def _valid_entry():
    """Return a ConfigEntry-like mock with all required fields."""
    entry = MagicMock()
    entry.entry_id = "entry_1"
    entry.data = {
        "vehicle_name": "Test Vehicle",
        "battery_capacity_kwh": 60.0,
        "charging_power_kw": 7.0,
        "safety_margin_percent": 10.0,
    }
    entry.options = {}
    return entry


def _make_hass_mock():
    """Mock HomeAssistant with default state returns."""
    hass = MagicMock()
    hass.config_entries.async_get_entry.return_value = _valid_entry()
    hass.states.get.return_value = MagicMock(state="50.0")
    return hass


class TestAsyncValidateConfig:
    """Test async_validate_config error branches (lines 92, 97, 102)."""

    @pytest.mark.asyncio
    async def test_missing_battery_capacity_kwh_raises(self):
        """Line 91-95: Missing battery_capacity_kwh raises ValueError."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_vehicle"
        entry.data = {}  # No required fields
        entry.options = {}
        hass.config_entries.async_get_entry.return_value = entry

        with pytest.raises(ValueError) as exc_info:
            EMHASSAdapter(hass, entry)
        assert "battery_capacity_kwh" in str(exc_info.value)
        assert "test_vehicle" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_charging_power_kw_raises(self):
        """Line 96-100: Missing charging_power_kw raises ValueError."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_vehicle"
        entry.data = {"battery_capacity_kwh": 60.0}  # Missing charging_power_kw
        entry.options = {}
        hass.config_entries.async_get_entry.return_value = entry

        with pytest.raises(ValueError) as exc_info:
            EMHASSAdapter(hass, entry)
        assert "charging_power_kw" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_safety_margin_percent_raises(self):
        """Line 101-105: Missing safety_margin_percent raises ValueError."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_vehicle"
        entry.data = {
            "battery_capacity_kwh": 60.0,
            "charging_power_kw": 7.0,
            # Missing safety_margin_percent
        }
        entry.options = {}
        hass.config_entries.async_get_entry.return_value = entry

        with pytest.raises(ValueError) as exc_info:
            EMHASSAdapter(hass, entry)
        assert "safety_margin_percent" in str(exc_info.value)


class TestGetCurrentSoc:
    """Test _get_current_soc branches (lines 685, 688)."""

    @pytest.mark.asyncio
    async def test_get_current_soc_no_sensor_configured(self):
        """Line 684-685: No soc_sensor in entry → returns None."""
        hass = _make_hass_mock()
        entry = _valid_entry()
        entry.data["soc_sensor"] = None  # No sensor

        adapter = EMHASSAdapter(hass, entry)
        result = await adapter._get_current_soc()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_soc_sensor_not_in_hass(self):
        """Lines 686-688: Sensor entity not found in hass.states → returns None."""
        hass = _make_hass_mock()
        hass.states.get.return_value = None  # Sensor not found
        entry = _valid_entry()
        entry.data["soc_sensor"] = "sensor.missing"

        adapter = EMHASSAdapter(hass, entry)
        result = await adapter._get_current_soc()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_soc_invalid_state_value(self):
        """Lines 689-692: State value can't be converted to float → returns None."""
        hass = _make_hass_mock()
        mock_state = MagicMock()
        mock_state.state = "not_a_number"
        hass.states.get.return_value = mock_state
        entry = _valid_entry()
        entry.data["soc_sensor"] = "sensor.invalid"

        adapter = EMHASSAdapter(hass, entry)
        result = await adapter._get_current_soc()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_soc_valid_value(self):
        """Valid SOC float value from sensor state."""
        hass = _make_hass_mock()
        mock_state = MagicMock()
        mock_state.state = "75.0"
        hass.states.get.return_value = mock_state
        entry = _valid_entry()
        entry.data["soc_sensor"] = "sensor.valid"

        adapter = EMHASSAdapter(hass, entry)
        result = await adapter._get_current_soc()
        assert result == 75.0




class TestPublishDeferrableLoad:
    """Test async_publish_deferrable_load SOC unavailable path (lines 1117-1122)."""

    @pytest.mark.asyncio
    async def test_publish_deferrable_load_returns_false_when_soc_unavailable(self):
        """Lines 1117-1122: SOC sensor unavailable → returns False."""
        hass = _make_hass_mock()
        entry = _valid_entry()
        entry.data["soc_sensor"] = None  # No sensor
        adapter = EMHASSAdapter(hass, entry)

        trip = {
            "id": "trip_1",
            "kwh": 10.0,
            "datetime": "2026-05-20T08:00:00+00:00",
        }

        result = await adapter.async_publish_deferrable_load(trip)
        assert result is False