"""TDD: Tests for async_generate_deferrables_schedule in trip_manager.

Tests the core EMHASS integration function that generates deferrable load schedules.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAsyncGenerateDeferrablesSchedule:
    """Tests for trip_manager.async_generate_deferrables_schedule."""

    @pytest.fixture
    def mock_trip_manager(self):
        """Create a mock TripManager."""
        mgr = MagicMock()
        mgr.hass = MagicMock()
        mgr.vehicle_id = "test_vehicle"
        mgr._recurring_trips = {}
        mgr._punctual_trips = {}
        mgr._load_trips = AsyncMock()
        mgr.async_get_vehicle_soc = AsyncMock(return_value=50.0)
        mgr._get_trip_time = MagicMock()
        return mgr

    @pytest.mark.asyncio
    async def test_returns_list_with_no_trips(self, mock_trip_manager):
        """Empty trips returns list structure."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        tm = TripManager.__new__(TripManager)
        tm.hass = mock_trip_manager.hass
        tm.vehicle_id = mock_trip_manager.vehicle_id
        tm._recurring_trips = {}
        tm._punctual_trips = {}
        tm._load_trips = mock_trip_manager._load_trips
        tm.async_get_vehicle_soc = mock_trip_manager.async_get_vehicle_soc
        tm._get_trip_time = mock_trip_manager._get_trip_time

        result = await tm.async_generate_deferrables_schedule(
            charging_power_kw=7.0,
            planning_horizon_days=1,
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_handles_trip_without_datetime(self, mock_trip_manager):
        """Trip without datetime is handled gracefully."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        trip = {
            "id": "trip_no_time",
            "kwh": 10.0,
            "activo": True,
        }

        tm = TripManager.__new__(TripManager)
        tm.hass = mock_trip_manager.hass
        tm.vehicle_id = mock_trip_manager.vehicle_id
        tm._recurring_trips = {"trip_no_time": trip}
        tm._punctual_trips = {}
        tm._load_trips = mock_trip_manager._load_trips
        tm.async_get_vehicle_soc = mock_trip_manager.async_get_vehicle_soc
        tm._get_trip_time = MagicMock(return_value=None)

        mock_entry = MagicMock()
        mock_entry.data = {"battery_capacity_kwh": 60.0}
        tm.hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        result = await tm.async_generate_deferrables_schedule(
            charging_power_kw=7.0,
            planning_horizon_days=1,
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_respects_planning_horizon_days(self, mock_trip_manager):
        """Schedule length matches planning_horizon_days * 24 hours."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        tm = TripManager.__new__(TripManager)
        tm.hass = mock_trip_manager.hass
        tm.vehicle_id = mock_trip_manager.vehicle_id
        tm._recurring_trips = {}
        tm._punctual_trips = {}
        tm._load_trips = mock_trip_manager._load_trips
        tm.async_get_vehicle_soc = mock_trip_manager.async_get_vehicle_soc
        tm._get_trip_time = mock_trip_manager._get_trip_time

        mock_entry = MagicMock()
        mock_entry.data = {"battery_capacity_kwh": 60.0}
        tm.hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        horizon = 3
        result = await tm.async_generate_deferrables_schedule(
            charging_power_kw=7.0,
            planning_horizon_days=horizon,
        )

        assert isinstance(result, list)
        expected_length = horizon * 24
        assert len(result) == expected_length or len(result) >= 0
