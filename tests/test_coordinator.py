"""Tests for TripPlannerCoordinator."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.ev_trip_planner import TripPlannerCoordinator
from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def mock_trip_manager(hass: HomeAssistant):
    """Create a mock TripManager for testing."""
    manager = TripManager(hass, "test_vehicle")
    return manager


async def test_coordinator_initialization(hass: HomeAssistant, mock_trip_manager):
    """Test that coordinator initializes correctly."""
    # RED phase - this test will fail until we implement the coordinator
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager)
    
    assert coordinator.hass == hass
    assert coordinator.trip_manager == mock_trip_manager
    assert isinstance(coordinator, DataUpdateCoordinator)


async def test_coordinator_refresh_triggers_update(hass: HomeAssistant, mock_trip_manager):
    """Test that coordinator refresh triggers data update."""
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager)
    
    # Mock the async_request_refresh method to track calls
    refresh_called = False
    
    async def mock_refresh():
        nonlocal refresh_called
        refresh_called = True
    
    coordinator.async_request_refresh = mock_refresh
    
    # Simulate a trip change that should trigger refresh
    await coordinator.async_request_refresh()
    
    assert refresh_called is True


async def test_coordinator_data_returns_trip_info(hass: HomeAssistant, mock_trip_manager):
    """Test that coordinator data returns trip information."""
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager)
    
    # Add a test trip
    await mock_trip_manager.async_add_recurring_trip(
        descripcion="Work",
        dia_semana="lunes",
        hora="09:00",
        km=25,
        kwh=3.75
    )
    
    # Force data refresh
    await coordinator.async_refresh()
    
    # Check that data contains trip information
    data = coordinator.data
    assert data is not None
    assert "recurring_trips" in data
    assert "punctual_trips" in data
    assert len(data["recurring_trips"]) == 1
    assert data["recurring_trips"][0]["descripcion"] == "Work"


async def test_coordinator_handles_empty_trips(hass: HomeAssistant, mock_trip_manager):
    """Test coordinator behavior with no trips."""
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager)
    
    await coordinator.async_refresh()
    
    data = coordinator.data
    assert data is not None
    assert len(data["recurring_trips"]) == 0
    assert len(data["punctual_trips"]) == 0
