"""Execution tests for TripPlannerCoordinator.

Covers __init__, vehicle_id property, _async_update_data, and async_refresh_trips.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.coordinator import (
    CoordinatorConfig,
    TripPlannerCoordinator,
)


# FIX: Mock frame reporting for HA 2026.3+ compatibility
# DataUpdateCoordinator requires frame helper to be set up
# This fixture mocks report_usage to bypass the check
@pytest.fixture(autouse=True)
def mock_frame_reporting():
    """Mock frame reporting to avoid 'Frame helper not set up' error."""
    with patch("homeassistant.helpers.frame.report_usage", return_value=None):
        yield


_LOGGER = logging.getLogger(__name__)


def _make_mock_hass():
    """Create a minimal mock HomeAssistant."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return hass


def _make_mock_entry(vehicle_name="test_vehicle", extra_data=None, extra_options=None):
    """Create a minimal mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        "vehicle_name": vehicle_name,
        "charging_power_kw": 7.0,
        "battery_capacity_kwh": 75.0,
        "kwh_per_km": 0.15,
        "safety_margin_percent": 10.0,
        "soc_base": 20.0,
        "t_base": 24.0,
    }
    entry.options = extra_options or {}
    if extra_data:
        entry.data.update(extra_data)
    return entry


def _make_trip_manager():
    """Create a TripManager-like mock with sub-component mocks."""
    tm = MagicMock()
    tm._crud = MagicMock()
    tm._crud.async_get_recurring_trips = AsyncMock(
        return_value=[
            {
                "id": "rec_1",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "09:00",
                "km": 50,
                "kwh": 7.5,
                "activo": True,
            }
        ]
    )
    tm._crud.async_get_punctual_trips = AsyncMock(return_value=[])
    tm._soc_query = MagicMock()
    tm._soc_query.async_get_kwh_needed_today = AsyncMock(return_value=12.5)
    tm._soc_query.async_get_hours_needed_today = AsyncMock(return_value=2.0)
    tm._navigator = MagicMock()
    tm._navigator.async_get_next_trip = AsyncMock(return_value=None)
    return tm


def _make_coordinator(
    vehicle_name="test_vehicle",
    trip_manager=None,
    emhass_adapter=None,
    extra_entry_data=None,
):
    """Create a fully wired TripPlannerCoordinator."""
    hass = _make_mock_hass()
    entry = _make_mock_entry(vehicle_name=vehicle_name, extra_data=extra_entry_data)
    if trip_manager is None:
        trip_manager = _make_trip_manager()
    config = CoordinatorConfig(emhass_adapter=emhass_adapter)
    return TripPlannerCoordinator(
        hass=hass,
        entry=entry,
        trip_manager=trip_manager,
        config=config,
    )


class TestCoordinatorInit:
    """Test TripPlannerCoordinator.__init__."""

    def test_init_default_config(self):
        """Default config creates coordinator with correct defaults."""
        coord = _make_coordinator()
        assert coord._vehicle_id == "test_vehicle"
        assert coord._entry is not None
        assert coord._emhass_adapter is None

    def test_init_with_custom_config(self):
        """Custom config passes through emhass_adapter and logger."""
        adapter = MagicMock()
        custom_logger = logging.getLogger("custom")
        config = CoordinatorConfig(emhass_adapter=adapter, logger=custom_logger)
        hass = _make_mock_hass()
        entry = _make_mock_entry()
        coord = TripPlannerCoordinator(
            hass=hass,
            entry=entry,
            trip_manager=_make_trip_manager(),
            config=config,
        )
        assert coord._emhass_adapter is adapter
        assert coord.logger is custom_logger

    def test_init_vehicle_name_normalized(self):
        """Vehicle name is lowercased with spaces replaced by underscores."""
        coord = _make_coordinator(vehicle_name="My Test Vehicle")
        assert coord._vehicle_id == "my_test_vehicle"

    def test_init_vehicle_name_empty(self):
        """Empty vehicle_name results in empty string (code doesn't default to 'unknown')."""
        coord = _make_coordinator(vehicle_name="")
        assert coord._vehicle_id == ""


class TestCoordinatorVehicleId:
    """Test TripPlannerCoordinator.vehicle_id property."""

    def test_vehicle_id_returns_normalized_name(self):
        """vehicle_id property returns normalized vehicle name."""
        coord = _make_coordinator(vehicle_name="Test Vehicle")
        assert coord.vehicle_id == "test_vehicle"


class TestCoordinatorAsyncUpdateData:
    """Test TripPlannerCoordinator._async_update_data."""

    @pytest.mark.asyncio
    async def test_async_update_data_with_emhass(self):
        """Full path: coordinator has emhass_adapter → reads cached results."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {"rec_1": {"index": 0}},
            "emhass_power_profile": [100, 200, 300],
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }
        tm = _make_trip_manager()
        coord = _make_coordinator(
            trip_manager=tm,
            emhass_adapter=adapter,
        )
        result = await coord._async_update_data()
        assert result["recurring_trips"] is not None
        assert result["punctual_trips"] is not None
        assert result["kwh_today"] == 12.5
        assert result["hours_today"] == 2.0
        assert result["next_trip"] is None
        assert result["emhass_power_profile"] == [100, 200, 300]
        assert all(isinstance(v, int) for v in result["emhass_power_profile"])
        tm._crud.async_get_recurring_trips.assert_called_once()
        tm._crud.async_get_punctual_trips.assert_called_once()
        tm._soc_query.async_get_kwh_needed_today.assert_called_once()
        tm._soc_query.async_get_hours_needed_today.assert_called_once()
        tm._navigator.async_get_next_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_update_data_without_emhass(self):
        """No emhass_adapter → EMHASS keys are None."""
        coord = _make_coordinator(emhass_adapter=None)
        result = await coord._async_update_data()
        assert result["emhass_power_profile"] is None
        assert result["emhass_deferrables_schedule"] is None
        assert result["emhass_status"] is None

    @pytest.mark.asyncio
    async def test_async_update_data_emhass_empty_returns_empty_params(self):
        """EMHASS returns empty cache → per_trip_emhass_params is empty, no fallback."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {},
            "emhass_power_profile": [],
        }
        tm = _make_trip_manager()
        tm._crud.async_get_recurring_trips = AsyncMock(
            return_value=[
                {
                    "id": "rec_1",
                    "kwh": 7.5,
                    "km": 50,
                    "datetime": "2026-05-20T09:00:00+00:00",
                }
            ]
        )
        coord = _make_coordinator(
            trip_manager=tm,
            emhass_adapter=adapter,
        )
        result = await coord._async_update_data()
        # No mock fallback — empty EMHASS params means empty dict
        assert result["per_trip_emhass_params"] == {}
        # Main trip data is unaffected
        assert "rec_1" in result["recurring_trips"]

    @pytest.mark.asyncio
    async def test_async_update_data_empty_trips(self):
        """No trips → EMHASS adapter not called with empty trips."""
        tm = _make_trip_manager()
        tm._crud.async_get_recurring_trips = AsyncMock(return_value=[])
        tm._crud.async_get_punctual_trips = AsyncMock(return_value=[])
        coord = _make_coordinator(trip_manager=tm, emhass_adapter=None)
        result = await coord._async_update_data()
        assert result["recurring_trips"] == {}
        assert result["punctual_trips"] == {}

    @pytest.mark.asyncio
    async def test_async_update_data_punctual_trips_included(self):
        """Punctual trips are included alongside recurring trips."""
        tm = _make_trip_manager()
        tm._crud.async_get_punctual_trips = AsyncMock(
            return_value=[
                {
                    "id": "pun_1",
                    "kwh": 3.0,
                    "km": 20,
                    "datetime": "2026-05-20T08:00:00+00:00",
                }
            ]
        )
        coord = _make_coordinator(trip_manager=tm, emhass_adapter=None)
        result = await coord._async_update_data()
        assert "pun_1" in result["punctual_trips"]


class TestCoordinatorRefreshTrips:
    """Test TripPlannerCoordinator.async_refresh_trips."""

    @pytest.mark.asyncio
    async def test_async_refresh_trips_calls_parent_refresh(self):
        """async_refresh_trips delegates to async_refresh()."""
        coord = _make_coordinator()
        # async_refresh is a DataUpdateCoordinator method — mock it
        coord.async_refresh = AsyncMock(return_value=MagicMock())
        await coord.async_refresh_trips()
        coord.async_refresh.assert_called_once()

