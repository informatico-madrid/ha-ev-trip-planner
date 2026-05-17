"""Tests for uncovered _power_profile.py error branches (lines 50-51, 53-54, 74-75, 77-78)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.trip._power_profile import PowerProfile


def _make_state(vehicle_id: str = "test_vehicle", entry_id: str = "entry_1", **overrides):
    """Create a mock TripManagerState for testing."""
    state = MagicMock()
    state.vehicle_id = vehicle_id
    state.entry_id = entry_id
    state.hass = MagicMock()
    state.hass.config_entries.async_get_entry.return_value = None
    state.hass.config_entries.async_entries.return_value = []
    state._persistence = MagicMock()
    state._persistence._load_trips = AsyncMock()
    state._soc = MagicMock()
    state._soc.async_get_vehicle_soc = AsyncMock(return_value=50.0)
    state.get_active_trips = MagicMock(return_value=[])
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


class TestAsyncGeneratePowerProfileVehicleConfigErrors:
    """Test error branches when vehicle_config is missing required fields."""

    @pytest.mark.asyncio
    async def test_missing_battery_capacity_kwh_returns_empty(self):
        """Lines 50-51: Missing battery_capacity_kwh in vehicle_config returns []."""
        state = _make_state()
        profile = PowerProfile(state)
        vehicle_config = {
            "safety_margin_percent": 10.0,
            # Missing battery_capacity_kwh
        }
        result = await profile.async_generate_power_profile(
            charging_power_kw=7.0,
            planning_horizon_days=7,
            vehicle_config=vehicle_config,
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_safety_margin_percent_returns_empty(self):
        """Lines 53-54: Missing safety_margin_percent in vehicle_config returns []."""
        state = _make_state()
        profile = PowerProfile(state)
        vehicle_config = {
            "battery_capacity_kwh": 60.0,
            # Missing safety_margin_percent
        }
        result = await profile.async_generate_power_profile(
            charging_power_kw=7.0,
            planning_horizon_days=7,
            vehicle_config=vehicle_config,
        )
        assert result == []


class TestAsyncGeneratePowerProfileConfigEntryErrors:
    """Test error branches when config_entry.data is missing required fields."""

    @pytest.mark.asyncio
    async def test_config_entry_missing_battery_capacity_kwh_returns_empty(self):
        """Lines 74-75: config_entry.data missing battery_capacity_kwh returns []."""
        mock_entry = MagicMock()
        mock_entry.data = {
            # Missing battery_capacity_kwh
            "safety_margin_percent": 10.0,
            "vehicle_name": "test_vehicle",
        }
        mock_entry.entry_id = "entry_1"

        state = _make_state()
        state.hass.config_entries.async_get_entry.return_value = mock_entry

        profile = PowerProfile(state)
        result = await profile.async_generate_power_profile(
            charging_power_kw=7.0,
            planning_horizon_days=7,
            vehicle_config=None,
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_config_entry_missing_safety_margin_percent_returns_empty(self):
        """Lines 77-78: config_entry.data missing safety_margin_percent returns []."""
        mock_entry = MagicMock()
        mock_entry.data = {
            "battery_capacity_kwh": 60.0,
            # Missing safety_margin_percent
            "vehicle_name": "test_vehicle",
        }
        mock_entry.entry_id = "entry_1"

        state = _make_state()
        state.hass.config_entries.async_get_entry.return_value = mock_entry

        profile = PowerProfile(state)
        result = await profile.async_generate_power_profile(
            charging_power_kw=7.0,
            planning_horizon_days=7,
            vehicle_config=None,
        )
        assert result == []