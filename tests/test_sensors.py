"""Tests for EV Trip Planner sensors."""

import pytest
from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner import TripPlannerCoordinator
from custom_components.ev_trip_planner.sensor import (
    RecurringTripsCountSensor,
    PunctualTripsCountSensor,
    TripsListSensor,
)
from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def mock_trip_manager(hass: HomeAssistant):
    """Create a mock TripManager for testing."""
    manager = TripManager(hass, "test_vehicle")
    return manager


@pytest.fixture
async def coordinator(hass: HomeAssistant, mock_trip_manager):
    """Create a coordinator with test data."""
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager)
    
    # Add test trips
    await mock_trip_manager.async_add_recurring_trip(
        descripcion="Work",
        dia_semana="lunes",
        hora="09:00",
        km=25,
        kwh=3.75
    )
    await mock_trip_manager.async_add_punctual_trip(
        datetime_str="2025-11-25T10:00:00",
        km=50,
        kwh=7.5,
        descripcion="Airport"
    )
    
    await coordinator.async_refresh()
    return coordinator


async def test_recurring_trips_count_sensor(hass: HomeAssistant, coordinator):
    """Test recurring trips count sensor."""
    sensor = RecurringTripsCountSensor("test_vehicle", coordinator)
    
    assert sensor.native_value == 1
    assert sensor.name == "test_vehicle recurring trips count"


async def test_punctual_trips_count_sensor(hass: HomeAssistant, coordinator):
    """Test punctual trips count sensor."""
    sensor = PunctualTripsCountSensor("test_vehicle", coordinator)
    
    assert sensor.native_value == 1
    assert sensor.name == "test_vehicle punctual trips count"


async def test_trips_list_sensor(hass: HomeAssistant, coordinator):
    """Test trips list sensor."""
    sensor = TripsListSensor("test_vehicle", coordinator)
    
    assert sensor.native_value == 2  # Total trips
    assert sensor.name == "test_vehicle trips list"
    
    # Check attributes
    attrs = sensor.extra_state_attributes
    assert "recurring_trips" in attrs
    assert "punctual_trips" in attrs
    assert len(attrs["recurring_trips"]) == 1
    assert len(attrs["punctual_trips"]) == 1


async def test_sensor_updates_on_coordinator_refresh(hass: HomeAssistant, mock_trip_manager):
    """Test that sensors update when coordinator refreshes."""
    coordinator = TripPlannerCoordinator(hass, mock_trip_manager)
    sensor = RecurringTripsCountSensor("test_vehicle", coordinator)
    
    # Initially no trips
    await coordinator.async_refresh()
    assert sensor.native_value == 0
    
    # Add a trip and refresh
    await mock_trip_manager.async_add_recurring_trip(
        descripcion="New Work",
        dia_semana="martes",
        hora="08:00",
        km=30,
        kwh=4.5
    )
    await coordinator.async_refresh()
    
    assert sensor.native_value == 1