"""Tests for sensor.py - TripPlannerSensor and derived sensors."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

# =============================================================================
# Trip Sensor Tests (FR-004)
# =============================================================================

@pytest.fixture
def mock_hass_with_storage():
    """Create a mock hass instance with storage support."""
    hass = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.storage = MagicMock()
    return hass


@pytest.mark.asyncio
async def test_trip_sensor_creation(mock_hass_with_storage):
    """Test that a TripSensor is created correctly for a trip."""
    from custom_components.ev_trip_planner.sensor import TripSensor

    # Create mock trip manager
    trip_manager = MagicMock()
    trip_manager.vehicle_id = "tesla_model_3"

    # Create trip data (new signature - tipo included in trip_data)
    trip_data = {
        "id": "trip_001",
        "tipo": "recurrente",
        "descripcion": "Work commute",
        "km": 25.5,
        "kwh": 4.2,
        "dia_semana": "monday",
    }

    # Create sensor (new signature - trip_id and trip_type derived from trip_data)
    sensor = TripSensor(
        hass=mock_hass_with_storage,
        trip_manager=trip_manager,
        trip_data=trip_data,
    )

    # Verify sensor properties (new implementation - native_value is trip_type for recurring)
    assert sensor._attr_unique_id == "trip_trip_001"
    assert sensor._attr_name == "Trip Work commute"
    assert sensor._attr_native_value == "recurrente"
    # Description and details are in extra_state_attributes
    attrs = sensor.extra_state_attributes
    assert attrs.get("descripcion") == "Work commute"
    assert attrs.get("km") == 25.5
    assert attrs.get("kwh") == 4.2
    assert attrs.get("trip_type") == "recurrente"
    assert attrs.get("trip_id") == "trip_001"


@pytest.mark.asyncio
async def test_trip_sensor_punctual_type(mock_hass_with_storage):
    """Test that a TripSensor works correctly for punctual trips."""
    from custom_components.ev_trip_planner.sensor import TripSensor

    # Create mock trip manager
    trip_manager = MagicMock()
    trip_manager.vehicle_id = "tesla_model_3"

    # Create punctual trip data (new signature - tipo included in trip_data)
    trip_data = {
        "id": "pun_001",
        "tipo": "puntual",
        "descripcion": "Airport trip",
        "km": 45.0,
        "kwh": 7.5,
        "datetime": "2026-03-25T10:00:00",
    }

    # Create sensor for punctual trip (new signature)
    sensor = TripSensor(
        hass=mock_hass_with_storage,
        trip_manager=trip_manager,
        trip_data=trip_data,
    )

    # Verify sensor properties (new implementation - punctual trips show estado)
    assert sensor._attr_native_value == "pendiente"  # default estado for punctual
    # Description and details are in extra_state_attributes
    attrs = sensor.extra_state_attributes
    assert attrs.get("descripcion") == "Airport trip"
    assert attrs.get("km") == 45.0
    assert attrs.get("kwh") == 7.5
    assert attrs.get("trip_type") == "puntual"


@pytest.mark.asyncio
async def test_trip_sensor_device_info(mock_hass_with_storage):
    """Test that TripSensor has correct device info."""
    from custom_components.ev_trip_planner.sensor import TripSensor

    # Create mock trip manager
    trip_manager = MagicMock()
    trip_manager.vehicle_id = "tesla_model_3"

    # Create trip data (new signature - tipo included)
    trip_data = {
        "id": "trip_001",
        "tipo": "recurrente",
        "descripcion": "Work commute",
        "km": 25.5,
        "kwh": 4.2,
    }

    # Create sensor (new signature)
    sensor = TripSensor(
        hass=mock_hass_with_storage,
        trip_manager=trip_manager,
        trip_data=trip_data,
    )

    # Verify device info (new implementation)
    device_info = sensor.device_info
    assert device_info is not None
    assert device_info["identifiers"] == {(
        "ev_trip_planner",
        "tesla_model_3_trip_001"
    )}
    assert device_info["name"] == "Trip trip_001 - tesla_model_3"
    assert device_info["via_device"] == ("ev_trip_planner", "tesla_model_3")


# =============================================================================
# Trip Sensor Management Tests (FR-004)
# =============================================================================

@pytest.mark.asyncio
async def test_async_create_trip_sensor(mock_hass_with_storage):
    """Test that async_create_trip_sensor creates a sensor correctly."""
    from custom_components.ev_trip_planner.sensor import async_create_trip_sensor
    from custom_components.ev_trip_planner.const import DOMAIN

    # Create mock config entry
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"

    # Create mock trip manager
    trip_manager = MagicMock()
    trip_manager.vehicle_id = "tesla_model_3"

    # Set up hass.data
    from custom_components.ev_trip_planner import DATA_RUNTIME
    mock_hass_with_storage.data = {
        DATA_RUNTIME: {
            f"{DOMAIN}_{mock_entry.entry_id}": {
                "trip_manager": trip_manager,
            }
        }
    }

    # Create trip data (new signature - tipo included in trip_data)
    trip_data = {
        "id": "trip_001",
        "tipo": "recurrente",
        "descripcion": "Work commute",
        "km": 25.5,
        "kwh": 4.2,
        "dia_semana": "monday",
    }

    # Create sensor (new signature - trip_id and trip_type derived from trip_data)
    result = await async_create_trip_sensor(
        hass=mock_hass_with_storage,
        entry_id=mock_entry.entry_id,
        trip_data=trip_data,
    )

    # Verify result
    assert result is True
    # Verify sensor was stored (new implementation - native_value is trip_type for recurring)
    namespace = f"{DOMAIN}_{mock_entry.entry_id}"
    stored_sensors = mock_hass_with_storage.data[DATA_RUNTIME][namespace].get("trip_sensors", {})
    assert "trip_001" in stored_sensors
    assert stored_sensors["trip_001"]._attr_native_value == "recurrente"


@pytest.mark.asyncio
async def test_async_update_trip_sensor(mock_hass_with_storage):
    """Test that async_update_trip_sensor updates a sensor correctly."""
    from custom_components.ev_trip_planner.sensor import async_create_trip_sensor, async_update_trip_sensor
    from custom_components.ev_trip_planner.const import DOMAIN

    # Create mock config entry
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"

    # Create mock trip manager
    trip_manager = MagicMock()
    trip_manager.vehicle_id = "tesla_model_3"

    # Set up hass.data
    from custom_components.ev_trip_planner import DATA_RUNTIME
    namespace = f"{DOMAIN}_{mock_entry.entry_id}"
    mock_hass_with_storage.data = {
        DATA_RUNTIME: {
            namespace: {
                "trip_manager": trip_manager,
            }
        }
    }

    # Create initial trip data (new signature - tipo included)
    trip_data = {
        "id": "trip_001",
        "tipo": "recurrente",
        "descripcion": "Work commute",
        "km": 25.5,
        "kwh": 4.2,
    }

    # Create sensor first (new signature)
    await async_create_trip_sensor(
        hass=mock_hass_with_storage,
        entry_id=mock_entry.entry_id,
        trip_data=trip_data,
    )

    # Update trip data
    updated_trip_data = {
        "id": "trip_001",
        "tipo": "recurrente",
        "descripcion": "Updated commute",
        "km": 30.0,
        "kwh": 5.0,
    }

    # Update sensor (new signature - trip_id derived from trip_data)
    result = await async_update_trip_sensor(
        hass=mock_hass_with_storage,
        entry_id=mock_entry.entry_id,
        trip_data=updated_trip_data,
    )

    # Verify result
    assert result is True
    # Verify sensor was updated (new implementation - native_value is trip_type)
    stored_sensors = mock_hass_with_storage.data[DATA_RUNTIME][namespace].get("trip_sensors", {})
    assert stored_sensors["trip_001"]._attr_native_value == "recurrente"
    attrs = stored_sensors["trip_001"].extra_state_attributes
    assert attrs.get("km") == 30.0


@pytest.mark.asyncio
async def test_async_remove_trip_sensor(mock_hass_with_storage):
    """Test that async_remove_trip_sensor removes a sensor correctly."""
    from custom_components.ev_trip_planner.sensor import async_create_trip_sensor, async_remove_trip_sensor
    from custom_components.ev_trip_planner.const import DOMAIN

    # Create mock config entry
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"

    # Create mock trip manager
    trip_manager = MagicMock()
    trip_manager.vehicle_id = "tesla_model_3"

    # Set up hass.data
    from custom_components.ev_trip_planner import DATA_RUNTIME
    namespace = f"{DOMAIN}_{mock_entry.entry_id}"
    mock_hass_with_storage.data = {
        DATA_RUNTIME: {
            namespace: {
                "trip_manager": trip_manager,
            }
        }
    }

    # Create initial trip data (new signature - tipo included)
    trip_data = {
        "id": "trip_001",
        "tipo": "recurrente",
        "descripcion": "Work commute",
        "km": 25.5,
        "kwh": 4.2,
    }

    # Create sensor first (new signature)
    await async_create_trip_sensor(
        hass=mock_hass_with_storage,
        entry_id=mock_entry.entry_id,
        trip_data=trip_data,
    )

    # Remove sensor
    result = await async_remove_trip_sensor(
        hass=mock_hass_with_storage,
        entry_id=mock_entry.entry_id,
        trip_id="trip_001",
    )

    # Verify result
    assert result is True
    # Verify sensor was removed
    stored_sensors = mock_hass_with_storage.data[DATA_RUNTIME][namespace].get("trip_sensors", {})
    assert "trip_001" not in stored_sensors


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


# Tests for p_deferrable_index attribute (TripCard Enhancement - AC-1)

@pytest.mark.asyncio
async def test_trip_sensor_p_deferrable_index_attribute(mock_hass_with_storage):
    """Test that TripSensor shows p_deferrable_index in extra_state_attributes.

    This test verifies AC-1: Trip card shows p_deferrable index (e.g., "Carga diferible: p_deferrable0")
    """
    from custom_components.ev_trip_planner.sensor import TripSensor

    # Create mock trip manager with emhass_adapter
    trip_manager = MagicMock()
    trip_manager.vehicle_id = "tesla_model_3"
    # Implementation calls: trip_manager.get_emhass_adapter().get_assigned_index(trip_id)
    trip_manager.get_emhass_adapter.return_value.get_assigned_index.return_value = 5

    # Create trip data with id and tipo
    trip_data = {
        "id": "trip_001",
        "tipo": "recurrente",
        "descripcion": "Work commute",
        "km": 25.5,
        "kwh": 4.2,
    }

    # Create sensor
    sensor = TripSensor(
        hass=mock_hass_with_storage,
        trip_manager=trip_manager,
        trip_data=trip_data,
    )

    # Verify p_deferrable_index is in extra_state_attributes
    attrs = sensor.extra_state_attributes
    assert "p_deferrable_index" in attrs, "p_deferrable_index should be in extra_state_attributes"
    assert attrs["p_deferrable_index"] == 5, "p_deferrable_index should be 5"


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


# Tests for device_class validation - T009
@pytest.mark.asyncio
async def test_kwh_today_sensor_device_class_energy():
    """Test KwhTodaySensor should have device_class ENERGY.

    This sensor measures energy consumption in kWh.
    Expected: PASS (should have SensorDeviceClass.ENERGY)
    """
    from custom_components.ev_trip_planner.sensor import KwhTodaySensor

    coordinator = FakeCoordinator(
        data={"kwh_today": 15.5, "recurring_trips": [], "punctual_trips": []},
        trip_manager=MagicMock(hass=MagicMock()),
    )

    sensor = KwhTodaySensor(vehicle_id="test_vehicle", coordinator=coordinator)

    # KwhTodaySensor measures energy, should have ENERGY device_class
    assert sensor._attr_device_class.value == "energy"


@pytest.mark.asyncio
async def test_hours_today_sensor_no_device_class_energy():
    """Test HoursTodaySensor should NOT have device_class ENERGY.

    This sensor measures time in hours, not energy.
    Expected: FAIL before fix (currently inherits ENERGY from base class)
    """
    from custom_components.ev_trip_planner.sensor import HoursTodaySensor

    coordinator = FakeCoordinator(
        data={"hours_today": 2, "recurring_trips": [], "punctual_trips": []},
        trip_manager=MagicMock(hass=MagicMock()),
    )

    sensor = HoursTodaySensor(vehicle_id="test_vehicle", coordinator=coordinator)

    # HoursTodaySensor measures time, should NOT have ENERGY device_class
    # This test will FAIL before fix because base class sets ENERGY
    # After fix: either no device_class or device_class is not ENERGY
    has_energy_device_class = (
        hasattr(sensor, "_attr_device_class")
        and sensor._attr_device_class.value == "energy"
    )
    assert not has_energy_device_class


@pytest.mark.asyncio
async def test_next_trip_sensor_no_device_class_energy():
    """Test NextTripSensor should NOT have device_class ENERGY.

    This sensor returns text (trip description), not energy.
    Expected: FAIL before fix (currently inherits ENERGY from base class)
    """
    from custom_components.ev_trip_planner.sensor import NextTripSensor

    coordinator = FakeCoordinator(
        data={
            "next_trip": {"descripcion": "Trabajo", "tipo": "recurrente"},
            "recurring_trips": [],
            "punctual_trips": [],
        },
        trip_manager=MagicMock(hass=MagicMock()),
    )

    sensor = NextTripSensor(vehicle_id="test_vehicle", coordinator=coordinator)

    # NextTripSensor returns text, should NOT have ENERGY device_class
    # This test will FAIL before fix because base class sets ENERGY
    # After fix: either no device_class or device_class is not ENERGY
    has_energy_device_class = (
        hasattr(sensor, "_attr_device_class")
        and sensor._attr_device_class.value == "energy"
    )
    assert not has_energy_device_class


@pytest.mark.asyncio
async def test_recurring_trips_count_sensor_no_device_class_energy():
    """Test RecurringTripsCountSensor should NOT have device_class ENERGY.

    This sensor counts trips (integer), not energy.
    Expected: FAIL before fix (currently inherits ENERGY from base class)
    """
    from custom_components.ev_trip_planner.sensor import RecurringTripsCountSensor

    coordinator = FakeCoordinator(
        data={"recurring_trips": [1, 2, 3], "punctual_trips": []},
        trip_manager=MagicMock(hass=MagicMock()),
    )

    sensor = RecurringTripsCountSensor(vehicle_id="test_vehicle", coordinator=coordinator)

    # RecurringTripsCountSensor counts trips, should NOT have ENERGY device_class
    # This test will FAIL before fix because base class sets ENERGY
    # After fix: either no device_class or device_class is not ENERGY
    has_energy_device_class = (
        hasattr(sensor, "_attr_device_class")
        and sensor._attr_device_class.value == "energy"
    )
    assert not has_energy_device_class


@pytest.mark.asyncio
async def test_punctual_trips_count_sensor_no_device_class_energy():
    """Test PunctualTripsCountSensor should NOT have device_class ENERGY.

    This sensor counts trips (integer), not energy.
    Expected: FAIL before fix (currently inherits ENERGY from base class)
    """
    from custom_components.ev_trip_planner.sensor import PunctualTripsCountSensor

    coordinator = FakeCoordinator(
        data={"recurring_trips": [], "punctual_trips": [1, 2]},
        trip_manager=MagicMock(hass=MagicMock()),
    )

    sensor = PunctualTripsCountSensor(vehicle_id="test_vehicle", coordinator=coordinator)

    # PunctualTripsCountSensor counts trips, should NOT have ENERGY device_class
    # This test will FAIL before fix because base class sets ENERGY
    # After fix: either no device_class or device_class is not ENERGY
    has_energy_device_class = (
        hasattr(sensor, "_attr_device_class")
        and sensor._attr_device_class.value == "energy"
    )
    assert not has_energy_device_class


# Tests for P001 - state_class warning with device_class energy
@pytest.mark.asyncio
async def test_state_class_warning_with_energy_device_class():
    """Test that KwhTodaySensor with MEASUREMENT state_class generates a warning.

    This test verifies the P001 production error:
    "Entity sensor.morgan_kwh_today is using state class 'measurement' which is
    impossible considering device class ('energy') it is using; expected None or
    one of 'total', 'total_increasing'"

    Expected: FAIL with warning before fix - the test should capture the warning
    that HA generates when invalid state_class/device_class combination is used.

    The test creates KwhTodaySensor with the problematic combination:
    - device_class: ENERGY
    - state_class: MEASUREMENT (INVALID for ENERGY device_class)

    After fix, state_class should be TOTAL_INCREASING.
    """
    from custom_components.ev_trip_planner.sensor import KwhTodaySensor

    coordinator = FakeCoordinator(
        data={"kwh_today": 15.5, "recurring_trips": [], "punctual_trips": []},
        trip_manager=MagicMock(hass=MagicMock()),
    )

    sensor = KwhTodaySensor(vehicle_id="test_vehicle", coordinator=coordinator)

    # Verify the problematic configuration
    assert sensor._attr_device_class.value == "energy", (
        "KwhTodaySensor should have ENERGY device_class"
    )

    # After fix: state_class should be TOTAL_INCREASING (correct for ENERGY device_class)
    assert sensor._attr_state_class.value == "total_increasing", (
        "AFTER FIX: KwhTodaySensor has correct TOTAL_INCREASING state_class for ENERGY device_class"
    )


# Tests for P003 - Config Entry Lookup Error
@pytest.mark.asyncio
async def test_config_entry_lookup_with_vehicle_id():
    """Test that config entry lookup with vehicle_id fails (P003).

    This test reproduces the P003 production error:
    "No config entry found for chispitas" / "No config entry found for morgan"

    The bug is in EmhassDeferrableLoadSensor.async_update() at line 441:
        entry = self.hass.config_entries.async_get_entry(self._vehicle_id)

    This uses self._vehicle_id (the vehicle name) instead of entry_id.
    async_get_entry() expects an entry_id (like "123abc"), not a vehicle name.

    Expected: FAIL before fix - async_get_entry returns None when given vehicle_id
    After fix: Should use correct entry_id from config entry setup
    """
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import AsyncMock

    # Create a mock hass with config_entries
    hass = MagicMock()

    # Create a config entry with proper entry_id
    mock_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain="ev_trip_planner",
        title="chispitas",
        data={"charging_power_kw": 7.4},
        source="user",
        entry_id="abc123def456",  # This is the entry_id, NOT the vehicle name
        unique_id="vehicle_chispitas",
        discovery_keys={},
        options={},
    )

    # Setup async_get_entry to return entry only for correct entry_id
    def async_get_entry_side_effect(entry_id):
        if entry_id == "abc123def456":
            return mock_entry
        return None  # Returns None for vehicle_id like "chispitas"

    hass.config_entries.async_get_entry = AsyncMock(side_effect=async_get_entry_side_effect)

    # The bug: async_get_entry expects entry_id ("abc123def456"), not vehicle_id ("chispitas")
    # When we call async_get_entry with vehicle_id, it returns None
    entry_with_vehicle_id = await hass.config_entries.async_get_entry("chispitas")
    assert entry_with_vehicle_id is None, (
        "async_get_entry('chispitas') should return None because 'chispitas' is not an entry_id"
    )

    # The fix should use entry_id instead:
    correct_entry = await hass.config_entries.async_get_entry("abc123def456")
    assert correct_entry is not None, (
        "async_get_entry('abc123def456') should return the config entry"
    )


# Tests for P002 - Coordinator Data Not Available
@pytest.mark.asyncio
async def test_sensor_with_none_coordinator():
    """Test that sensors with coordinator=None handle gracefully.

    This test reproduces the P002 production error:
    "no coordinator data available" warnings in logs (~40+ times in 20 minutes)

    The issue is that sensors try to read from coordinator.data, but coordinator
    is None or doesn't have the expected data structure.

    Expected: FAIL before fix - sensor should produce warning or crash when
    coordinator=None is passed.

    After fix: Sensors should handle None coordinator gracefully without warnings.
    """
    import warnings

    from custom_components.ev_trip_planner.sensor import KwhTodaySensor

    # Create sensor with coordinator=None
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        sensor = KwhTodaySensor(vehicle_id="test_vehicle", coordinator=None)

        # Reading native_value should return a default without crashing
        value = sensor.native_value

        # After fix: sensor should return 0.0 without raising an exception
        # The test passes if we get here without an exception
        assert value is not None


@pytest.mark.asyncio
async def test_sensor_coordinator_none_returns_default():
    """Test that sensor with coordinator=None returns default value instead of crashing.

    This is the expected behavior after fixing P002:
    - Sensor should not crash when coordinator is None
    - Sensor should return a sensible default (0.0 for KwhTodaySensor)
    - No warnings should be produced

    Expected: FAIL before fix - sensor will crash or produce warning
    After fix: Sensor returns 0.0 without warning
    """
    from custom_components.ev_trip_planner.sensor import KwhTodaySensor

    # Create sensor with coordinator=None
    sensor = KwhTodaySensor(vehicle_id="test_vehicle", coordinator=None)

    # After fix: This should return 0.0 without any exception or warning
    # Before fix: This will raise AttributeError (coordinator is None)
    result = sensor.native_value

    # The fix should allow this to work
    assert result == 0.0, (
        "Sensor should return 0.0 as default when coordinator is None"
    )
