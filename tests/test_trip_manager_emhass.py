"""Tests for TripManager EMHASS sync methods."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from custom_components.ev_trip_planner.const import (
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_PENDING,
)
from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def vehicle_id() -> str:
    return "test_vehicle"


@pytest.fixture
def mock_hass():
    """Create a mock hass with config_entries and data."""
    hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_vehicle"  # Must match vehicle_id
    mock_entry.data = {}  # Default empty data - no charging power
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    hass.data = {}
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    return hass


@pytest.fixture
def mock_hass_with_charging_power():
    """Create a mock hass with charging power configured."""
    hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_vehicle"  # Must match vehicle_id
    mock_entry.data = {"charging_power": 11.0}
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    hass.data = {}
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    return hass


@pytest.fixture
def mock_emhass_adapter():
    """Create a mock EMHASS adapter."""
    adapter = Mock()
    adapter.async_update_deferrable_load = AsyncMock()
    adapter.async_remove_deferrable_load = AsyncMock()
    adapter.async_publish_deferrable_load = AsyncMock()
    adapter.async_publish_all_deferrable_loads = AsyncMock(return_value=True)
    adapter.async_get_deferrable_params = AsyncMock(
        return_value={
            "treat_as_deferrable": 1,
            "optimization_cost_fun": "cost",
        }
    )
    adapter.get_all_assigned_indices = Mock(return_value={})
    adapter.vehicle_id = "test_vehicle"
    return adapter


class TestTripManagerEMHASSMethods:
    """Tests for TripManager EMHASS-related methods."""

    @pytest.mark.asyncio
    async def test_get_charging_power_with_config(
        self, mock_hass_with_charging_power, vehicle_id
    ):
        """Test _get_charging_power returns configured value."""
        manager = TripManager(mock_hass_with_charging_power, vehicle_id)

        result = manager._get_charging_power()

        assert result == 11.0

    @pytest.mark.asyncio
    async def test_get_charging_power_default(self, mock_hass, vehicle_id):
        """Test _get_charging_power returns default when not set."""
        manager = TripManager(mock_hass, vehicle_id)

        result = manager._get_charging_power()

        # Should return default 11.0 kW
        assert result == 11.0

    @pytest.mark.asyncio
    async def test_get_all_active_trips_with_trips(self, mock_hass, vehicle_id):
        """Test _get_all_active_trips returns active trips."""
        manager = TripManager(mock_hass, vehicle_id)

        # Add a punctual trip
        manager._punctual_trips["trip_1"] = {
            "descripcion": "Test trip",
            "estado": TRIP_STATUS_PENDING,
            "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
            "km": 50.0,
            "kwh": 7.5,
        }

        # Add a recurring trip
        manager._recurring_trips["recurring_1"] = {
            "descripcion": "Daily commute",
            "activo": True,
            "hora": "08:00",
            "km": 30.0,
            "kwh": 4.5,
        }

        active_trips = await manager._get_all_active_trips()

        assert len(active_trips) == 2

    @pytest.mark.asyncio
    async def test_get_all_active_trips_empty(self, mock_hass, vehicle_id):
        """Test _get_all_active_trips returns empty list when no trips."""
        manager = TripManager(mock_hass, vehicle_id)

        active_trips = await manager._get_all_active_trips()

        assert active_trips == []

    @pytest.mark.asyncio
    async def test_get_all_active_trips_inactive_recurring(self, mock_hass, vehicle_id):
        """Test _get_all_active_trips excludes inactive recurring trips."""
        manager = TripManager(mock_hass, vehicle_id)

        # Add active recurring trip
        manager._recurring_trips["active"] = {
            "descripcion": "Active trip",
            "activo": True,
            "hora": "08:00",
        }

        # Add inactive recurring trip
        manager._recurring_trips["inactive"] = {
            "descripcion": "Inactive trip",
            "activo": False,
            "hora": "09:00",
        }

        active_trips = await manager._get_all_active_trips()

        # Should only include active trip
        assert len(active_trips) == 1
        assert active_trips[0]["descripcion"] == "Active trip"

    @pytest.mark.asyncio
    async def test_get_all_active_trips_completed_punctual(self, mock_hass, vehicle_id):
        """Test _get_all_active_trips excludes completed punctual trips."""
        manager = TripManager(mock_hass, vehicle_id)

        # Add pending punctual trip
        manager._punctual_trips["pending"] = {
            "descripcion": "Pending trip",
            "estado": TRIP_STATUS_PENDING,
        }

        # Add completed punctual trip
        manager._punctual_trips["completed"] = {
            "descripcion": "Completed trip",
            "estado": TRIP_STATUS_COMPLETED,
        }

        active_trips = await manager._get_all_active_trips()

        # Should only include pending trip
        assert len(active_trips) == 1
        assert active_trips[0]["descripcion"] == "Pending trip"

    @pytest.mark.asyncio
    async def test_sync_trip_to_emhass_no_adapter(self, mock_hass, vehicle_id):
        """Test sync_trip_to_emhass does nothing without adapter."""
        manager = TripManager(mock_hass, vehicle_id)

        # No adapter set
        manager._emhass_adapter = None

        # Should not raise - method signature is (trip_id, old_trip, updates)
        await manager._async_sync_trip_to_emhass("trip_1", {}, {"descripcion": "test"})

    @pytest.mark.asyncio
    async def test_sync_trip_to_emhass_inactive_trip_removes(
        self, mock_hass, vehicle_id, mock_emhass_adapter
    ):
        """Test sync_trip_to_emhass removes inactive trip."""
        manager = TripManager(mock_hass, vehicle_id)
        manager._emhass_adapter = mock_emhass_adapter

        # Set up inactive recurring trip
        manager._recurring_trips["trip_1"] = {
            "descripcion": "Inactive trip",
            "activo": False,
        }

        await manager._async_sync_trip_to_emhass(
            "trip_1", {"activo": False}, {"descripcion": "test"}
        )

        mock_emhass_adapter.async_remove_deferrable_load.assert_called_once_with(
            "trip_1"
        )

    @pytest.mark.asyncio
    async def test_sync_trip_to_emhass_updates_active(
        self, mock_hass, vehicle_id, mock_emhass_adapter
    ):
        """Test sync_trip_to_emhass updates active trip."""
        manager = TripManager(mock_hass, vehicle_id)
        manager._emhass_adapter = mock_emhass_adapter
        manager._charging_power_kw = 11.0

        # Set up active punctual trip
        manager._punctual_trips["trip_1"] = {
            "descripcion": "Active trip",
            "estado": TRIP_STATUS_PENDING,
            "km": 50.0,
            "kwh": 7.5,
            "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
        }

        # Non-critical update (just description)
        await manager._async_sync_trip_to_emhass(
            "trip_1",
            {"descripcion": "Active trip"},
            {"descripcion": "Updated description"},
        )

        mock_emhass_adapter.async_update_deferrable_load.assert_called()

    @pytest.mark.asyncio
    async def test_sync_trip_to_emhass_recalculates(
        self, mock_hass, vehicle_id, mock_emhass_adapter
    ):
        """Test sync_trip_to_emhass recalculates when critical fields change."""
        manager = TripManager(mock_hass, vehicle_id)
        manager._emhass_adapter = mock_emhass_adapter
        manager._charging_power_kw = 11.0

        # Set up active punctual trip
        manager._punctual_trips["trip_1"] = {
            "descripcion": "Active trip",
            "estado": TRIP_STATUS_PENDING,
            "km": 50.0,
            "kwh": 7.5,
            "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
        }

        # Critical update (km changes)
        await manager._async_sync_trip_to_emhass("trip_1", {"km": 50.0}, {"km": 100.0})

        # Should call publish to recalculate
        mock_emhass_adapter.async_publish_all_deferrable_loads.assert_called()

    @pytest.mark.asyncio
    async def test_remove_trip_from_emhass(
        self, mock_hass, vehicle_id, mock_emhass_adapter
    ):
        """Test _async_remove_trip_from_emhass."""
        manager = TripManager(mock_hass, vehicle_id)
        manager._emhass_adapter = mock_emhass_adapter
        manager._charging_power_kw = 7.4

        # Add a trip
        manager._punctual_trips["trip_1"] = {
            "descripcion": "Test",
            "estado": TRIP_STATUS_PENDING,
            "km": 50.0,
        }

        await manager._async_remove_trip_from_emhass("trip_1")

        mock_emhass_adapter.async_remove_deferrable_load.assert_called_once_with(
            "trip_1"
        )
        mock_emhass_adapter.async_publish_all_deferrable_loads.assert_called()

    @pytest.mark.asyncio
    async def test_publish_new_trip_to_emhass(
        self, mock_hass, vehicle_id, mock_emhass_adapter
    ):
        """Test _async_publish_new_trip_to_emhass."""
        manager = TripManager(mock_hass, vehicle_id)
        manager._emhass_adapter = mock_emhass_adapter
        manager._charging_power_kw = 11.0

        trip = {
            "descripcion": "New trip",
            "km": 50.0,
            "kwh": 7.5,
        }

        await manager._async_publish_new_trip_to_emhass(trip)

        # Should call async_publish_deferrable_load
        mock_emhass_adapter.async_publish_deferrable_load.assert_called()
        mock_emhass_adapter.async_publish_all_deferrable_loads.assert_called()


class TestTripManagerHelperMethods:
    """Tests for TripManager helper methods."""

    @pytest.mark.asyncio
    async def test_get_day_index_monday(self, mock_hass, vehicle_id):
        """Test _get_day_index returns correct value for Monday (lunes)."""
        manager = TripManager(mock_hass, vehicle_id)

        result = manager._get_day_index("lunes")

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_day_index_sunday(self, mock_hass, vehicle_id):
        """Test _get_day_index returns correct value for Sunday (domingo)."""
        manager = TripManager(mock_hass, vehicle_id)

        result = manager._get_day_index("domingo")

        assert result == 6

    @pytest.mark.asyncio
    async def test_get_day_index_invalid(self, mock_hass, vehicle_id):
        """Test _get_day_index handles invalid day."""
        manager = TripManager(mock_hass, vehicle_id)

        # Invalid day defaults to Monday (index 0 in DAYS_OF_WEEK)
        result = manager._get_day_index("invalid_day")
        assert result == 0  # Monday (index 0)
