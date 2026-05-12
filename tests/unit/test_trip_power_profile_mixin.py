"""Execution tests for _PowerProfileMixin (async_generate_power_profile).

Covers vehicle_config path, SOC fetching, and empty trip handling.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.trip._power_profile_mixin import _PowerProfileMixin
from custom_components.ev_trip_planner.trip.state import TripManagerState


class TestPowerProfileMixin(unittest.TestCase):
    """_PowerProfileMixin must be importable from trip._power_profile_mixin."""

    def test_power_profile_mixin_is_importable(self):
        """_PowerProfileMixin can be imported from custom_components.ev_trip_planner.trip._power_profile_mixin."""
        from custom_components.ev_trip_planner.trip._power_profile_mixin import _PowerProfileMixin

        self.assertIsNotNone(_PowerProfileMixin)

    def test_has_async_generate_power_profile(self):
        from custom_components.ev_trip_planner.trip._power_profile_mixin import _PowerProfileMixin

        self.assertTrue(hasattr(_PowerProfileMixin, "async_generate_power_profile"))
        self.assertTrue(callable(getattr(_PowerProfileMixin, "async_generate_power_profile")))


def _make_pmix():
    """Create a _PowerProfileMixin with proper state."""
    state = TripManagerState(
        hass=MagicMock(),
        vehicle_id="test_vehicle",
        entry_id="test_entry",
    )
    state._get_trip_time = MagicMock(return_value=None)
    state.async_get_vehicle_soc = AsyncMock(return_value=50.0)
    state._load_trips = AsyncMock()
    state.recurring_trips = {}
    state.punctual_trips = {}
    return _PowerProfileMixin(state)


class TestPowerProfileMixinExecution:
    """Test async_generate_power_profile execution paths."""

    @pytest.mark.asyncio
    async def test_generate_power_profile_with_vehicle_config(self):
        """Passing vehicle_config skips HA lookup path."""
        pmix = _make_pmix()
        result = await pmix.async_generate_power_profile(
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
        pmix = _make_pmix()
        result = await pmix.async_generate_power_profile(
            vehicle_config={
                "battery_capacity_kwh": 60.0,
                "soc_current": 65.0,
                "safety_margin_percent": 10,
            }
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_power_profile_no_config(self):
        """No vehicle_config → falls back to HA lookup (fails gracefully with mock)."""
        pmix = _make_pmix()
        pmix._state.hass.config_entries.async_get_entry = MagicMock(return_value=None)
        result = await pmix.async_generate_power_profile(vehicle_config=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_power_profile_config_entry_scan(self):
        """Direct lookup fails, scans entries by vehicle_name."""
        pmix = _make_pmix()
        pmix._state.hass.config_entries.async_get_entry = MagicMock(return_value=None)

        matching_entry = MagicMock()
        matching_entry.data = {"vehicle_name": "test_vehicle", "battery_capacity_kwh": 60.0}
        pmix._state.hass.config_entries.async_entries = MagicMock(return_value=[matching_entry])

        result = await pmix.async_generate_power_profile(vehicle_config=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_power_profile_config_scan_no_match(self):
        """Scan entries but no vehicle_name match → defaults used."""
        pmix = _make_pmix()
        pmix._state.hass.config_entries.async_get_entry = MagicMock(return_value=None)

        other_entry = MagicMock()
        other_entry.data = {"vehicle_name": "other_vehicle", "battery_capacity_kwh": 60.0}
        pmix._state.hass.config_entries.async_entries = MagicMock(return_value=[other_entry])

        result = await pmix.async_generate_power_profile(vehicle_config=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_power_profile_with_presence_monitor(self):
        """With presence_monitor set, async_get_hora_regreso is called."""
        pmix = _make_pmix()

        presence_monitor = MagicMock()
        presence_monitor.async_get_hora_regreso = AsyncMock(
            return_value=datetime.now(timezone.utc)
        )
        pmix._state.vehicle_controller = MagicMock()
        pmix._state.vehicle_controller._presence_monitor = presence_monitor

        result = await pmix.async_generate_power_profile(vehicle_config={
            "battery_capacity_kwh": 75.0,
            "safety_margin_percent": 15,
        })

        assert result is not None
        presence_monitor.async_get_hora_regreso.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_power_profile_config_lookup_exception(self):
        """Exception during config lookup → defaults used."""
        pmix = _make_pmix()
        pmix._state.hass.config_entries.async_get_entry = MagicMock(
            side_effect=RuntimeError("config error")
        )
        result = await pmix.async_generate_power_profile(vehicle_config=None)
        assert result is not None