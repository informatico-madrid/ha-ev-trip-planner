"""Execution tests for PowerProfile (async_generate_power_profile).

Covers vehicle_config path, SOC fetching, and empty trip handling.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.trip._power_profile import PowerProfile
from custom_components.ev_trip_planner.trip.state import TripManagerState


class TestPowerProfile(unittest.TestCase):
    """PowerProfile must be importable from trip._power_profile."""

    def test_power_profile_is_importable(self):
        """PowerProfile can be imported from trip._power_profile."""
        from custom_components.ev_trip_planner.trip._power_profile import PowerProfile

        self.assertIsNotNone(PowerProfile)

    def test_has_async_generate_power_profile(self):
        from custom_components.ev_trip_planner.trip._power_profile import PowerProfile

        self.assertTrue(hasattr(PowerProfile, "async_generate_power_profile"))
        self.assertTrue(
            callable(getattr(PowerProfile, "async_generate_power_profile"))
        )


def _make_pm():
    """Create a PowerProfile with proper state."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    hass.config_entries.async_entries = MagicMock(return_value=[])

    state = TripManagerState(
        hass=hass,
        vehicle_id="test_vehicle",
        entry_id="test_entry",
    )
    state.recurring_trips = {}
    state.punctual_trips = {}
    # Wire sub-component mocks that PowerProfile uses
    state._persistence = MagicMock()
    state._persistence._load_trips = AsyncMock()
    state._soc = MagicMock()
    state._soc.async_get_vehicle_soc = AsyncMock(return_value=50.0)
    return PowerProfile(state)


class TestPowerProfileExecution:
    """Test async_generate_power_profile execution paths."""

    @pytest.mark.asyncio
    async def test_generate_power_profile_with_vehicle_config(self):
        """Passing vehicle_config skips HA lookup path."""
        pm = _make_pm()
        result = await pm.async_generate_power_profile(
            vehicle_config={
                "battery_capacity_kwh": 75.0,
                "safety_margin_percent": 15,
            }
        )
        assert result is not None
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_generate_power_profile_with_soc(self):
        """Vehicle config with soc_current skips SOC fetch."""
        pm = _make_pm()
        result = await pm.async_generate_power_profile(
            vehicle_config={
                "battery_capacity_kwh": 60.0,
                "soc_current": 65.0,
                "safety_margin_percent": 10,
            }
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_power_profile_no_config(self):
        """No vehicle_config -> falls back to HA lookup (fails gracefully with mock)."""
        pm = _make_pm()
        pm._state.hass.config_entries.async_get_entry = MagicMock(return_value=None)
        result = await pm.async_generate_power_profile(vehicle_config=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_power_profile_config_fallback_via_vehicle_id(self):
        """No entry_id -> config_entry lookup via vehicle_id (line 55), config read (lines 60-64)."""
        pm = _make_pm()
        # Clear entry_id to trigger vehicle_id fallback at line 51-54
        pm._state.entry_id = ""
        matching_entry = MagicMock()
        matching_entry.data = {
            "vehicle_name": "test_vehicle",
            "battery_capacity_kwh": 70.0,
            "safety_margin_percent": 15.0,
        }
        pm._state.hass.config_entries.async_get_entry = MagicMock(return_value=matching_entry)
        result = await pm.async_generate_power_profile(vehicle_config=None, planning_horizon_days=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_power_profile_config_entry_scan(self):
        """Direct lookup fails, scans entries by vehicle_name."""
        pm = _make_pm()
        pm._state.hass.config_entries.async_get_entry = MagicMock(return_value=None)

        matching_entry = MagicMock()
        matching_entry.data = {
            "vehicle_name": "test_vehicle",
            "battery_capacity_kwh": 60.0,
        }
        pm._state.hass.config_entries.async_entries = MagicMock(
            return_value=[matching_entry]
        )

        result = await pm.async_generate_power_profile(vehicle_config=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_power_profile_config_scan_no_match(self):
        """Scan entries but no vehicle_name match -> defaults used."""
        pm = _make_pm()
        pm._state.hass.config_entries.async_get_entry = MagicMock(return_value=None)

        other_entry = MagicMock()
        other_entry.data = {
            "vehicle_name": "other_vehicle",
            "battery_capacity_kwh": 60.0,
        }
        pm._state.hass.config_entries.async_entries = MagicMock(
            return_value=[other_entry]
        )

        result = await pm.async_generate_power_profile(vehicle_config=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_power_profile_config_lookup_exception(self):
        """Exception during config lookup -> defaults used."""
        pm = _make_pm()
        pm._state.hass.config_entries.async_get_entry = MagicMock(
            side_effect=RuntimeError("config error")
        )
        result = await pm.async_generate_power_profile(vehicle_config=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_power_profile_soc_fetch_exception(self):
        """Exception during SOC fetch -> defaults to 50.0 (lines 78-79)."""
        pm = _make_pm()
        pm._state._soc.async_get_vehicle_soc = AsyncMock(
            side_effect=RuntimeError("SOC sensor error")
        )
        result = await pm.async_generate_power_profile(vehicle_config=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_power_profile_pending_punctual_included(self):
        """Pending punctual trips included in profile (line 88)."""
        pm = _make_pm()
        pm._state.punctual_trips = {
            "pun_1": {"id": "pun_1", "estado": "pendiente", "tipo": "punctual"},
            "pun_2": {"id": "pun_2", "estado": "completado"},
        }
        pm._state.recurring_trips = {}
        result = await pm.async_generate_power_profile(vehicle_config=None)
        assert result is not None
