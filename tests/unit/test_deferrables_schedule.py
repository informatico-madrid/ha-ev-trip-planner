"""TDD: Tests for async_generate_deferrables_schedule in trip_manager.

Tests the core EMHASS integration function that generates deferrable load schedules.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.trip import TripManager
from custom_components.ev_trip_planner.trip.state import TripManagerState


def _make_partial_tm(mock_mgr):
    """Build a partial TripManager via __new__ with a proper _state.

    The composition refactor requires self._state to exist because mixins
    call self._state.xxx(). Tests that use TripManager.__new__() must
    manually create _state and attach mock method references to it.
    """
    tm = TripManager.__new__(TripManager)
    tm._state = TripManagerState(
        hass=mock_mgr.hass,
        vehicle_id=mock_mgr.vehicle_id,
        entry_id="",
    )
    tm._state._recurring_trips = mock_mgr._recurring_trips
    tm._state._punctual_trips = mock_mgr._punctual_trips
    tm._state._load_trips = mock_mgr._load_trips
    tm._state._get_trip_time = mock_mgr._get_trip_time
    tm._state.async_get_vehicle_soc = mock_mgr.async_get_vehicle_soc
    # Set up _persistence mock
    tm._state._persistence = MagicMock()
    tm._state._persistence._load_trips = mock_mgr._load_trips
    # Set up _soc mock
    tm._state._soc = MagicMock()
    tm._state._soc.async_get_vehicle_soc = mock_mgr.async_get_vehicle_soc
    tm._state._soc._get_trip_time = mock_mgr._get_trip_time
    tm._state._soc.async_calcular_energia_necesaria = AsyncMock(
        return_value={"energia_necesaria_kwh": 0, "horas_carga_necesarias": 0}
    )
    tm._state._soc._calcular_tasa_carga_soc = MagicMock(return_value=10.0)
    # Set up config entry mock
    tm._state.hass.config_entries.async_get_entry = MagicMock(return_value=None)
    # Create and wire schedule
    from custom_components.ev_trip_planner.trip._schedule import TripScheduler

    tm._schedule = TripScheduler(tm._state)
    return tm


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
        tm = _make_partial_tm(mock_trip_manager)

        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=7.0,
            planning_horizon_days=1,
        )

        assert isinstance(result, list)
        # Empty trips → schedule still has all time slots
        assert len(result) == 24  # 1 day * 24 hours
        assert isinstance(result[0], dict)
        assert "date" in result[0]

    @pytest.mark.asyncio
    async def test_handles_trip_without_datetime(self, mock_trip_manager):
        """Trip without datetime is handled gracefully."""
        trip = {
            "id": "trip_no_time",
            "kwh": 10.0,
            "activo": True,
        }

        mock_mgr = mock_trip_manager
        mock_mgr._recurring_trips = {"trip_no_time": trip}
        mock_mgr._get_trip_time = MagicMock(return_value=None)

        tm = _make_partial_tm(mock_mgr)

        mock_entry = MagicMock()
        mock_entry.data = {"battery_capacity_kwh": 60.0}
        tm._state.hass.config_entries.async_get_entry = MagicMock(
            return_value=mock_entry
        )

        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=7.0,
            planning_horizon_days=1,
        )

        assert isinstance(result, list)
        # Trip without datetime → schedule still has all time slots
        assert len(result) == 24
        assert isinstance(result[0], dict)

    @pytest.mark.asyncio
    async def test_respects_planning_horizon_days(self, mock_trip_manager):
        """Schedule length matches planning_horizon_days * 24 hours."""
        tm = _make_partial_tm(mock_trip_manager)

        mock_entry = MagicMock()
        mock_entry.data = {"battery_capacity_kwh": 60.0}
        tm._state.hass.config_entries.async_get_entry = MagicMock(
            return_value=mock_entry
        )

        horizon = 3
        result = await tm._schedule.async_generate_deferrables_schedule(
            charging_power_kw=7.0,
            planning_horizon_days=horizon,
        )

        assert isinstance(result, list)
        expected_length = horizon * 24
        assert len(result) == expected_length
