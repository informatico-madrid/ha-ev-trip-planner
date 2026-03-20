"""Tests for sensor.py - TripPlannerSensor and derived sensors."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_hass():
    """Create a mock hass instance."""
    hass = MagicMock()
    mock_entry = MagicMock(data={"charging_power_kw": 7.4})
    hass.config_entries.async_get_entry = AsyncMock(return_value=mock_entry)
    return hass


class FakeCoordinator:
    """Fake coordinator for testing sensors that read from coordinator.data."""

    def __init__(self, data: dict, trip_manager=None):
        self.data = data
        self.trip_manager = trip_manager


@pytest.mark.asyncio
async def test_trip_planner_sensor_kwh_needed_today_async_update(mock_hass):
    """Test TripPlannerSensor.async_update for kwh_needed_today sensor type."""
    from custom_components.ev_trip_planner.sensor import TripPlannerSensor
    from custom_components.ev_trip_planner.trip_manager import TripManager

    # Create mock trip manager
    trip_manager = MagicMock(spec=TripManager)
    trip_manager.vehicle_id = "test_vehicle"
    trip_manager.async_get_kwh_needed_today = AsyncMock(return_value=15.5)
    trip_manager.async_get_recurring_trips = AsyncMock(return_value=[{"id": "rec_1"}])
    trip_manager.async_get_punctual_trips = AsyncMock(return_value=[{"id": "pun_1"}])

    # Create sensor
    sensor = TripPlannerSensor(mock_hass, trip_manager, "kwh_needed_today")

    # Call async_update
    await sensor.async_update()

    # Verify the sensor value
    assert sensor._attr_native_value == 15.5
    # Verify cached attributes were set
    assert sensor._cached_attrs.get("viajes_hoy") == 1
    assert sensor._cached_attrs.get("viajes_puntuales") == 1


@pytest.mark.asyncio
async def test_trip_planner_sensor_hours_needed_today_async_update(mock_hass):
    """Test TripPlannerSensor.async_update for hours_needed_today sensor type."""
    from custom_components.ev_trip_planner.sensor import TripPlannerSensor
    from custom_components.ev_trip_planner.trip_manager import TripManager

    # Create mock trip manager - get_charging_power is now on TripManager directly
    trip_manager = MagicMock(spec=TripManager)
    trip_manager.vehicle_id = "test_vehicle"
    trip_manager.async_get_hours_needed_today = AsyncMock(return_value=2)
    trip_manager.get_charging_power = MagicMock(return_value=7.4)

    # Create sensor
    sensor = TripPlannerSensor(mock_hass, trip_manager, "hours_needed_today")

    # Call async_update
    await sensor.async_update()

    # Verify the sensor value
    assert sensor._attr_native_value == 2
    # Verify cached attributes were set
    assert sensor._cached_attrs.get("potencia_carga") == 7.4


@pytest.mark.asyncio
async def test_trip_planner_sensor_next_trip_async_update(mock_hass):
    """Test TripPlannerSensor.async_update for next_trip sensor type."""
    from custom_components.ev_trip_planner.sensor import TripPlannerSensor
    from custom_components.ev_trip_planner.trip_manager import TripManager

    # Create mock trip manager
    trip_manager = MagicMock(spec=TripManager)
    trip_manager.vehicle_id = "test_vehicle"
    trip_manager.async_get_next_trip = AsyncMock(
        return_value={
            "id": "rec_lun_123",
            "tipo": "recurrente",
            "descripcion": "Trabajo",
            "dia_semana": "lunes",
            "km": 24.0,
            "kwh": 3.6,
        }
    )

    # Create sensor
    sensor = TripPlannerSensor(mock_hass, trip_manager, "next_trip")

    # Call async_update
    await sensor.async_update()

    # Verify the sensor value is the description
    assert sensor._attr_native_value == "Trabajo"
    # Verify cached attributes were set
    assert sensor._cached_attrs.get("fecha_hora") == "lunes"
    assert sensor._cached_attrs.get("distancia") == 24.0
    assert sensor._cached_attrs.get("energia") == 3.6


@pytest.mark.asyncio
async def test_trip_planner_sensor_next_trip_no_trips(mock_hass):
    """Test TripPlannerSensor.async_update when no trips exist."""
    from custom_components.ev_trip_planner.sensor import TripPlannerSensor
    from custom_components.ev_trip_planner.trip_manager import TripManager

    # Create mock trip manager returning None
    trip_manager = MagicMock(spec=TripManager)
    trip_manager.vehicle_id = "test_vehicle"
    trip_manager.async_get_next_trip = AsyncMock(return_value=None)

    # Create sensor
    sensor = TripPlannerSensor(mock_hass, trip_manager, "next_trip")

    # Call async_update
    await sensor.async_update()

    # Verify the sensor value is N/A
    assert sensor._attr_native_value == "N/A"
    # Cached attrs should be cleared
    assert sensor._cached_attrs == {}


@pytest.mark.asyncio
async def test_trip_planner_sensor_handles_exception(mock_hass):
    """Test TripPlannerSensor.async_update handles exceptions gracefully."""
    from custom_components.ev_trip_planner.sensor import TripPlannerSensor
    from custom_components.ev_trip_planner.trip_manager import TripManager

    # Create mock trip manager that raises exception
    trip_manager = MagicMock(spec=TripManager)
    trip_manager.vehicle_id = "test_vehicle"
    error = RuntimeError("Test error")
    trip_manager.async_get_kwh_needed_today = AsyncMock(side_effect=error)

    # Create sensor
    sensor = TripPlannerSensor(mock_hass, trip_manager, "kwh_needed_today")

    # Call async_update - should not raise
    await sensor.async_update()

    # Verify the sensor value is None after error
    assert sensor._attr_native_value is None


@pytest.mark.asyncio
async def test_trip_planner_sensor_extra_state_attributes(mock_hass):
    """Test TripPlannerSensor.extra_state_attributes returns cached attributes."""
    from custom_components.ev_trip_planner.sensor import TripPlannerSensor
    from custom_components.ev_trip_planner.trip_manager import TripManager

    # Create mock trip manager
    trip_manager = MagicMock(spec=TripManager)
    trip_manager.vehicle_id = "test_vehicle"

    # Create sensor and set cached attrs
    sensor = TripPlannerSensor(mock_hass, trip_manager, "kwh_needed_today")
    sensor._cached_attrs = {"viajes_hoy": 3, "viajes_puntuales": 2}

    # Get extra state attributes
    attrs = sensor.extra_state_attributes

    # Verify attributes are returned
    assert attrs.get("viajes_hoy") == 3
    assert attrs.get("viajes_puntuales") == 2


@pytest.mark.asyncio
async def test_trip_planner_sensor_extra_state_attributes_empty(mock_hass):
    """Test TripPlannerSensor.extra_state_attributes returns defaults."""
    from custom_components.ev_trip_planner.sensor import TripPlannerSensor
    from custom_components.ev_trip_planner.trip_manager import TripManager

    # Create mock trip manager
    trip_manager = MagicMock(spec=TripManager)
    trip_manager.vehicle_id = "test_vehicle"

    # Create sensor without cached attrs
    sensor = TripPlannerSensor(mock_hass, trip_manager, "kwh_needed_today")
    sensor._cached_attrs = {}

    # Get extra state attributes
    attrs = sensor.extra_state_attributes

    # Verify default empty arrays are returned
    assert attrs.get("recurring_trips") == []
    assert attrs.get("punctual_trips") == []


@pytest.mark.asyncio
async def test_trip_planner_sensor_device_info(mock_hass):
    """Test TripPlannerSensor.device_info returns correct device info."""
    from custom_components.ev_trip_planner.sensor import TripPlannerSensor
    from custom_components.ev_trip_planner.trip_manager import TripManager

    # Create mock trip manager with vehicle_id
    trip_manager = MagicMock(spec=TripManager)
    trip_manager.vehicle_id = "chispitas"

    # Create sensor
    sensor = TripPlannerSensor(mock_hass, trip_manager, "kwh_needed_today")

    # Get device info
    device_info = sensor.device_info

    # Verify device info
    assert device_info["identifiers"] == {("ev_trip_planner", "chispitas")}
    assert device_info["name"] == "EV Trip Planner chispitas"
    assert device_info["manufacturer"] == "Home Assistant"
    assert device_info["model"] == "EV Trip Planner"


# Tests for alias sensors that read from coordinator.data


@pytest.mark.asyncio
async def test_kwh_today_sensor_native_value():
    """Test KwhTodaySensor reads from coordinator.data."""
    from custom_components.ev_trip_planner.sensor import KwhTodaySensor

    coordinator = FakeCoordinator(
        data={
            "kwh_today": 15.5,
            "recurring_trips": [],
            "punctual_trips": [],
        },
        trip_manager=MagicMock(hass=MagicMock()),
    )

    sensor = KwhTodaySensor(vehicle_id="test_vehicle", coordinator=coordinator)

    assert sensor.native_value == 15.5


@pytest.mark.asyncio
async def test_kwh_today_sensor_no_data():
    """Test KwhTodaySensor returns 0.0 when no data available."""
    from custom_components.ev_trip_planner.sensor import KwhTodaySensor

    coordinator = FakeCoordinator(data={}, trip_manager=MagicMock(hass=MagicMock()))

    sensor = KwhTodaySensor(vehicle_id="test_vehicle", coordinator=coordinator)

    assert sensor.native_value == 0.0


@pytest.mark.asyncio
async def test_hours_today_sensor_native_value():
    """Test HoursTodaySensor reads from coordinator.data."""
    from custom_components.ev_trip_planner.sensor import HoursTodaySensor

    coordinator = FakeCoordinator(
        data={
            "hours_today": 2,
            "recurring_trips": [],
            "punctual_trips": [],
        },
        trip_manager=MagicMock(hass=MagicMock()),
    )

    sensor = HoursTodaySensor(vehicle_id="test_vehicle", coordinator=coordinator)

    assert sensor.native_value == 2


@pytest.mark.asyncio
async def test_hours_today_sensor_no_data():
    """Test HoursTodaySensor returns 0 when no data available."""
    from custom_components.ev_trip_planner.sensor import HoursTodaySensor

    coordinator = FakeCoordinator(data={}, trip_manager=MagicMock(hass=MagicMock()))

    sensor = HoursTodaySensor(vehicle_id="test_vehicle", coordinator=coordinator)

    assert sensor.native_value == 0


@pytest.mark.asyncio
async def test_next_trip_sensor_native_value():
    """Test NextTripSensor reads from coordinator.data."""
    from custom_components.ev_trip_planner.sensor import NextTripSensor

    coordinator = FakeCoordinator(
        data={
            "next_trip": {
                "descripcion": "Trabajo",
                "tipo": "recurrente",
                "dia_semana": "lunes",
            },
            "recurring_trips": [],
            "punctual_trips": [],
        },
        trip_manager=MagicMock(hass=MagicMock()),
    )

    sensor = NextTripSensor(vehicle_id="test_vehicle", coordinator=coordinator)

    assert sensor.native_value == "Trabajo"


@pytest.mark.asyncio
async def test_next_trip_sensor_no_data():
    """Test NextTripSensor returns 'No trips' when no data available."""
    from custom_components.ev_trip_planner.sensor import NextTripSensor

    coordinator = FakeCoordinator(data={}, trip_manager=MagicMock(hass=MagicMock()))

    sensor = NextTripSensor(vehicle_id="test_vehicle", coordinator=coordinator)

    assert sensor.native_value == "No trips"


@pytest.mark.asyncio
async def test_next_deadline_sensor_native_value():
    """Test NextDeadlineSensor reads from coordinator.data."""
    from custom_components.ev_trip_planner.sensor import NextDeadlineSensor

    coordinator = FakeCoordinator(
        data={
            "next_trip": {
                "datetime": "2025-01-06T09:00:00",
                "tipo": "puntual",
            },
            "recurring_trips": [],
            "punctual_trips": [],
        },
        trip_manager=MagicMock(hass=MagicMock()),
    )

    sensor = NextDeadlineSensor(vehicle_id="test_vehicle", coordinator=coordinator)

    assert sensor.native_value == "2025-01-06T09:00:00"


@pytest.mark.asyncio
async def test_next_deadline_sensor_no_data():
    """Test NextDeadlineSensor returns None when no data available."""
    from custom_components.ev_trip_planner.sensor import NextDeadlineSensor

    coordinator = FakeCoordinator(data={}, trip_manager=MagicMock(hass=MagicMock()))

    sensor = NextDeadlineSensor(vehicle_id="test_vehicle", coordinator=coordinator)

    assert sensor.native_value is None
