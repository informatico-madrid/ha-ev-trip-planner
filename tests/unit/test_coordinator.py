"""Execution tests for TripPlannerCoordinator.

Covers __init__, vehicle_id property, _async_update_data, async_refresh_trips,
and _generate_mock_emhass_params.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

# FIX: Mock frame reporting for HA 2026.3+ compatibility
# DataUpdateCoordinator requires frame helper to be set up
# This fixture mocks report_usage to bypass the check
@pytest.fixture(autouse=True)
def mock_frame_reporting():
    """Mock frame reporting to avoid 'Frame helper not set up' error."""
    with patch("homeassistant.helpers.frame.report_usage", return_value=None):
        yield

from custom_components.ev_trip_planner.coordinator import (
    CoordinatorConfig,
    TripPlannerCoordinator,
)

_LOGGER = logging.getLogger(__name__)


def _make_mock_hass():
    """Create a minimal mock HomeAssistant."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return hass


def _make_mock_entry(vehicle_name="test_vehicle", extra_data=None):
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
    if extra_data:
        entry.data.update(extra_data)
    return entry


def _make_trip_manager():
    """Create a TripManager-like mock with sub-component mocks."""
    tm = MagicMock()
    tm._crud = MagicMock()
    tm._crud.async_get_recurring_trips = AsyncMock(return_value=[
        {"id": "rec_1", "tipo": "recurrente", "dia_semana": "lunes", "hora": "09:00", "km": 50, "kwh": 7.5, "activo": True}
    ])
    tm._crud.async_get_punctual_trips = AsyncMock(return_value=[])
    tm._soc_query = MagicMock()
    tm._soc_query.async_get_kwh_needed_today = AsyncMock(return_value=12.5)
    tm._soc_query.async_get_hours_needed_today = AsyncMock(return_value=2.0)
    tm._navigator = MagicMock()
    tm._navigator.async_get_next_trip = AsyncMock(return_value=None)
    return tm


def _make_coordinator(vehicle_name="test_vehicle", trip_manager=None,
                      emhass_adapter=None, extra_entry_data=None):
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
    async def test_async_update_data_emhass_empty_triggers_fallback(self):
        """EMHASS returns empty cache → generates mock params."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {},
            "emhass_power_profile": [],
        }
        tm = _make_trip_manager()
        tm._crud.async_get_recurring_trips = AsyncMock(return_value=[
            {"id": "rec_1", "kwh": 7.5, "km": 50, "datetime": "2026-05-14T09:00:00+00:00"}
        ])
        coord = _make_coordinator(
            trip_manager=tm,
            emhass_adapter=adapter,
        )
        result = await coord._async_update_data()
        # Should have fallback mock params
        assert "per_trip_emhass_params" in result
        assert "rec_1" in result["per_trip_emhass_params"]
        assert result["emhass_power_profile"] is not None
        assert result["emhass_status"] == "ready"

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
        tm._crud.async_get_punctual_trips = AsyncMock(return_value=[
            {"id": "pun_1", "kwh": 3.0, "km": 20, "datetime": "2026-05-14T08:00:00+00:00"}
        ])
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


class TestGenerateMockEmhassParams:
    """Test TripPlannerCoordinator._generate_mock_emhass_params."""

    def _make_coord_for_mock(self, extra_entry_data=None):
        """Create coordinator with minimal trip_manager for mock testing."""
        tm = MagicMock()
        tm._crud.async_get_recurring_trips = AsyncMock(return_value=[])
        coord = _make_coordinator(
            extra_entry_data=extra_entry_data,
            trip_manager=tm,
        )
        return coord

    def test_mock_params_single_trip(self):
        """Single trip generates correct mock params."""
        coord = self._make_coord_for_mock()
        trips = {
            "rec_1": {
                "id": "rec_1",
                "status": "active",
                "kwh": 7.5,
                "km": 50,
                "datetime": "2026-05-14T09:00:00+00:00",
            }
        }
        result = coord._generate_mock_emhass_params(trips)
        assert "emhass_power_profile" in result
        assert "emhass_deferrables_schedule" in result
        assert result["emhass_status"] == "ready"
        assert "rec_1" in result["per_trip_emhass_params"]
        assert result["per_trip_emhass_params"]["rec_1"]["kwh_needed"] == 7.5

    def test_mock_params_skips_completed_trips(self):
        """Completed trips are skipped in mock generation."""
        coord = self._make_coord_for_mock()
        trips = {
            "rec_1": {
                "status": "completed",
                "kwh": 7.5,
                "km": 50,
            },
            "rec_2": {
                "status": "active",
                "kwh": 5.0,
                "km": 30,
            },
        }
        result = coord._generate_mock_emhass_params(trips)
        assert "rec_1" not in result["per_trip_emhass_params"]
        assert "rec_2" in result["per_trip_emhass_params"]

    def test_mock_params_skips_cancelled_trips(self):
        """Cancelled trips are skipped."""
        coord = self._make_coord_for_mock()
        trips = {
            "rec_1": {
                "status": "cancelled",
                "kwh": 7.5,
                "km": 50,
            },
        }
        result = coord._generate_mock_emhass_params(trips)
        assert "rec_1" not in result["per_trip_emhass_params"]

    def test_mock_params_matrix_shape(self):
        """Generated matrix rows have 96 columns (24h * 4 timesteps)."""
        coord = self._make_coord_for_mock()
        trips = {
            "rec_1": {
                "status": "active",
                "kwh": 7.5,
                "km": 50,
                "datetime": "2026-05-14T09:00:00+00:00",
            }
        }
        result = coord._generate_mock_emhass_params(trips)
        params = result["per_trip_emhass_params"]["rec_1"]
        # p_deferrable_matrix is a list of lists
        matrix = params.get("p_deferrable_matrix", [])
        assert len(matrix) > 0
        for row in matrix:
            assert len(row) == 96

    def test_mock_params_deferrables_schedule(self):
        """Deferrables schedule entries have correct structure."""
        coord = self._make_coord_for_mock()
        trips = {
            "rec_1": {
                "status": "active",
                "kwh": 5.0,
                "km": 30,
                "datetime": "2026-05-14T10:00:00+00:00",
            }
        }
        result = coord._generate_mock_emhass_params(trips)
        schedule = result["emhass_deferrables_schedule"]
        assert len(schedule) == 1
        entry = schedule[0]
        assert "index" in entry
        assert "kwh" in entry
        assert "start_timestep" in entry
        assert "end_timestep" in entry

    def test_mock_params_zero_charging_power(self):
        """Zero charging power → hours_needed defaults to 0.1."""
        coord = self._make_coord_for_mock(extra_entry_data={"charging_power_kw": 0})
        trips = {
            "rec_1": {
                "status": "active",
                "kwh": 7.5,
                "km": 50,
            }
        }
        result = coord._generate_mock_emhass_params(trips)
        params = result["per_trip_emhass_params"]["rec_1"]
        # hours_needed should be max(0/0, 0.1) = 0.1
        assert params["def_total_hours_array"] == [0.1]

    def test_mock_params_invalid_datetime(self):
        """Invalid datetime string handled gracefully."""
        coord = self._make_coord_for_mock()
        trips = {
            "rec_1": {
                "status": "active",
                "kwh": 7.5,
                "km": 50,
                "datetime": "not-a-date",
            }
        }
        result = coord._generate_mock_emhass_params(trips)
        assert "rec_1" in result["per_trip_emhass_params"]

    def test_mock_params_no_datetime(self):
        """Missing datetime → timestep starts at 0."""
        coord = self._make_coord_for_mock()
        trips = {
            "rec_1": {
                "status": "active",
                "kwh": 7.5,
                "km": 50,
            }
        }
        result = coord._generate_mock_emhass_params(trips)
        entry = result["per_trip_emhass_params"]["rec_1"]
        assert entry["def_start_timestep_array"] == [0]

    def test_mock_params_datetime_no_tzinfo(self):
        """Datetime without timezone → replace with UTC (line 274)."""
        coord = self._make_coord_for_mock()
        trips = {
            "rec_1": {
                "status": "active",
                "kwh": 7.5,
                "km": 50,
                "datetime": "2026-05-14T09:00:00",  # No timezone info
            }
        }
        result = coord._generate_mock_emhass_params(trips)
        assert "rec_1" in result["per_trip_emhass_params"]

    def test_mock_params_empty_trips(self):
        """Empty trips dict → empty results."""
        coord = self._make_coord_for_mock()
        result = coord._generate_mock_emhass_params({})
        assert result["per_trip_emhass_params"] == {}
        assert result["emhass_deferrables_schedule"] == []
