"""Additional tests for sensor coverage - EmhassDeferrableLoadSensor and error paths."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.ev_trip_planner.sensor import (
    EmhassDeferrableLoadSensor,
    KwhTodaySensor,
    HoursTodaySensor,
    NextTripSensor,
    NextDeadlineSensor,
    RecurringTripsCountSensor,
    PunctualTripsCountSensor,
    TripsListSensor,
    TripPlannerSensor,
)
from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def mock_trip_manager_for_sensor(hass: HomeAssistant, mock_store):
    """Create a mock TripManager for sensor testing."""
    manager = TripManager(hass, "test_vehicle")
    manager._store = mock_store
    return manager


class TestEmhassDeferrableLoadSensor:
    """Tests for EmhassDeferrableLoadSensor."""

    async def test_emhass_sensor_unique_id(self, hass: HomeAssistant, mock_trip_manager_for_sensor):
        """Test EmhassDeferrableLoadSensor unique_id property."""
        sensor = EmhassDeferrableLoadSensor(
            hass, mock_trip_manager_for_sensor, "test_vehicle"
        )
        assert sensor.unique_id == "emhass_perfil_diferible_test_vehicle"

    async def test_emhass_sensor_device_info(self, hass: HomeAssistant, mock_trip_manager_for_sensor):
        """Test EmhassDeferrableLoadSensor device_info property."""
        sensor = EmhassDeferrableLoadSensor(
            hass, mock_trip_manager_for_sensor, "test_vehicle"
        )
        device_info = sensor.device_info
        assert device_info["identifiers"] == {("ev_trip_planner", "test_vehicle")}
        assert device_info["name"] == "EV Trip Planner test_vehicle"

    async def test_emhass_sensor_extra_state_attributes(
        self, hass: HomeAssistant, mock_trip_manager_for_sensor
    ):
        """Test EmhassDeferrableLoadSensor extra_state_attributes property."""
        sensor = EmhassDeferrableLoadSensor(
            hass, mock_trip_manager_for_sensor, "test_vehicle"
        )
        # Initially empty
        assert sensor.extra_state_attributes == {}

    async def test_emhass_sensor_async_update_success(
        self, hass: HomeAssistant, mock_trip_manager_for_sensor
    ):
        """Test EmhassDeferrableLoadSensor async_update with successful data."""
        # Create a mock config entry
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.data = {
            "vehicle_name": "test_vehicle",
            "charging_power": 7.0,
            "planning_horizon_days": 7,
        }
        mock_entry.entry_id = "test_entry_id"
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Mock the power profile and schedule generation
        mock_trip_manager_for_sensor.async_generate_power_profile = AsyncMock(
            return_value=[1000, 2000, 3000]
        )
        mock_trip_manager_for_sensor.async_generate_deferrables_schedule = AsyncMock(
            return_value=[{"hour": 0, "power": 1000}, {"hour": 1, "power": 2000}]
        )

        sensor = EmhassDeferrableLoadSensor(
            hass, mock_trip_manager_for_sensor, "test_vehicle"
        )
        await sensor.async_update()

        assert sensor.native_value == "ready"
        assert "power_profile_watts" in sensor.extra_state_attributes
        assert "deferrables_schedule" in sensor.extra_state_attributes

    async def test_emhass_sensor_async_update_no_config_entry(
        self, hass: HomeAssistant, mock_trip_manager_for_sensor
    ):
        """Test EmhassDeferrableLoadSensor async_update without config entry."""
        hass.config_entries.async_get_entry = MagicMock(return_value=None)

        sensor = EmhassDeferrableLoadSensor(
            hass, mock_trip_manager_for_sensor, "test_vehicle"
        )
        await sensor.async_update()

        # Should not crash and keep default state
        assert sensor.native_value == "ready"

    async def test_emhass_sensor_async_update_exception(
        self, hass: HomeAssistant, mock_trip_manager_for_sensor
    ):
        """Test EmhassDeferrableLoadSensor async_update with exception."""
        # Create a mock config entry
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.data = {
            "vehicle_name": "test_vehicle",
            "charging_power": 7.0,
            "planning_horizon_days": 7,
        }
        mock_entry.entry_id = "test_entry_id"
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Mock to raise exception
        mock_trip_manager_for_sensor.async_generate_power_profile = AsyncMock(
            side_effect=Exception("Test error")
        )

        sensor = EmhassDeferrableLoadSensor(
            hass, mock_trip_manager_for_sensor, "test_vehicle"
        )
        await sensor.async_update()

        assert sensor.native_value == "error"


class TestSensorNativeValueWarningPaths:
    """Tests for sensor native_value warning paths (no coordinator data)."""

    async def test_recurring_trips_count_sensor_no_coordinator_data(
        self, hass: HomeAssistant
    ):
        """Test RecurringTripsCountSensor when coordinator has no data."""
        # Create a mock coordinator without data
        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        sensor = RecurringTripsCountSensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == 0

    async def test_recurring_trips_count_sensor_no_data_key(
        self, hass: HomeAssistant
    ):
        """Test RecurringTripsCountSensor when data doesn't have key."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = {}

        sensor = RecurringTripsCountSensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == 0

    async def test_punctual_trips_count_sensor_no_coordinator_data(
        self, hass: HomeAssistant
    ):
        """Test PunctualTripsCountSensor when coordinator has no data."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        sensor = PunctualTripsCountSensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == 0

    async def test_punctual_trips_count_sensor_no_data_key(
        self, hass: HomeAssistant
    ):
        """Test PunctualTripsCountSensor when data doesn't have key."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = {}

        sensor = PunctualTripsCountSensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == 0

    async def test_trips_list_sensor_no_coordinator_data(self, hass: HomeAssistant):
        """Test TripsListSensor when coordinator has no data."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        sensor = TripsListSensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == 0

    async def test_trips_list_sensor_no_data_key(self, hass: HomeAssistant):
        """Test TripsListSensor when data doesn't have key."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = {}

        sensor = TripsListSensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == 0

    async def test_kwh_today_sensor_no_coordinator_data(self, hass: HomeAssistant):
        """Test KwhTodaySensor when coordinator has no data."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        sensor = KwhTodaySensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == 0.0

    async def test_kwh_today_sensor_no_data_key(self, hass: HomeAssistant):
        """Test KwhTodaySensor when data doesn't have key."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = {}

        sensor = KwhTodaySensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == 0.0

    async def test_hours_today_sensor_no_coordinator_data(self, hass: HomeAssistant):
        """Test HoursTodaySensor when coordinator has no data."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        sensor = HoursTodaySensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == 0

    async def test_hours_today_sensor_no_data_key(self, hass: HomeAssistant):
        """Test HoursTodaySensor when data doesn't have key."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = {}

        sensor = HoursTodaySensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == 0

    async def test_next_trip_sensor_no_coordinator_data(self, hass: HomeAssistant):
        """Test NextTripSensor when coordinator has no data."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        sensor = NextTripSensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == "No trips"

    async def test_next_trip_sensor_no_data_key(self, hass: HomeAssistant):
        """Test NextTripSensor when data doesn't have key."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = {}

        sensor = NextTripSensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == "No trips"

    async def test_next_trip_sensor_with_next_trip_data(self, hass: HomeAssistant):
        """Test NextTripSensor when data has next_trip."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "next_trip": {"descripcion": "Work", "km": 25, "kwh": 3.75}
        }

        sensor = NextTripSensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == "Work"

    async def test_next_deadline_sensor_no_coordinator_data(self, hass: HomeAssistant):
        """Test NextDeadlineSensor when coordinator has no data."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        sensor = NextDeadlineSensor("test_vehicle", mock_coordinator)
        assert sensor.native_value is None

    async def test_next_deadline_sensor_no_data_key(self, hass: HomeAssistant):
        """Test NextDeadlineSensor when data doesn't have key."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = {}

        sensor = NextDeadlineSensor("test_vehicle", mock_coordinator)
        assert sensor.native_value is None

    async def test_next_deadline_sensor_with_next_trip(self, hass: HomeAssistant):
        """Test NextDeadlineSensor when data has next_trip with datetime."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "next_trip": {"descripcion": "Work", "datetime": "2025-11-25T10:00"}
        }

        sensor = NextDeadlineSensor("test_vehicle", mock_coordinator)
        assert sensor.native_value == "2025-11-25T10:00"


class TestTripPlannerSensorBase:
    """Tests for TripPlannerSensor base class."""

    async def test_sensor_device_info(self, hass: HomeAssistant, mock_trip_manager_for_sensor):
        """Test TripPlannerSensor device_info property."""
        sensor = TripPlannerSensor(hass, mock_trip_manager_for_sensor, "test_type")
        device_info = sensor.device_info

        assert device_info["identifiers"] == {("ev_trip_planner", "test_vehicle")}
        assert device_info["name"] == "EV Trip Planner test_vehicle"

    async def test_sensor_extra_state_attributes_empty(
        self, hass: HomeAssistant, mock_trip_manager_for_sensor
    ):
        """Test TripPlannerSensor extra_state_attributes with empty cache."""
        sensor = TripPlannerSensor(hass, mock_trip_manager_for_sensor, "test_type")
        attrs = sensor.extra_state_attributes

        assert attrs == {"recurring_trips": [], "punctual_trips": []}

    async def test_sensor_extra_state_attributes_with_data(
        self, hass: HomeAssistant, mock_trip_manager_for_sensor
    ):
        """Test TripPlannerSensor extra_state_attributes with cached data."""
        sensor = TripPlannerSensor(hass, mock_trip_manager_for_sensor, "kwh_needed_today")
        sensor._cached_attrs = {"viajes_hoy": 2, "viajes_puntuales": 1}

        attrs = sensor.extra_state_attributes

        assert attrs["viajes_hoy"] == 2
        assert attrs["viajes_puntuales"] == 1

    async def test_async_update_exception_handling(
        self, hass: HomeAssistant, mock_trip_manager_for_sensor, caplog
    ):
        """Test TripPlannerSensor async_update handles exceptions gracefully."""
        # Mock trip_manager to raise exception
        mock_trip_manager_for_sensor.async_get_kwh_needed_today = AsyncMock(
            side_effect=Exception("Test error")
        )
        mock_trip_manager_for_sensor.vehicle_id = "test_vehicle"

        sensor = TripPlannerSensor(
            hass, mock_trip_manager_for_sensor, "kwh_needed_today"
        )

        # Should not raise, should handle exception
        await sensor.async_update()

        # Verify that native_value is set to None on error
        assert sensor.native_value is None


class TestAsyncSetupEntryErrorPath:
    """Tests for async_setup_entry error paths."""

    async def test_async_setup_entry_no_trip_manager(self, hass: HomeAssistant):
        """Test async_setup_entry when trip_manager is not found."""
        from custom_components.ev_trip_planner.sensor import async_setup_entry

        entry = MagicMock(spec=ConfigEntry)
        entry.data = {"vehicle_name": "test_vehicle"}
        entry.entry_id = "test_entry_id"

        # Ensure hass.data doesn't have the trip_manager
        hass.data = {}

        async_add_entities = MagicMock()

        result = await async_setup_entry(hass, entry, async_add_entities)

        assert result is False
        async_add_entities.assert_not_called()

    async def test_async_setup_entry_with_trip_manager(
        self, hass: HomeAssistant, mock_trip_manager_for_sensor
    ):
        """Test async_setup_entry with trip_manager and coordinator."""
        from custom_components.ev_trip_planner import DATA_RUNTIME

        entry = MagicMock(spec=ConfigEntry)
        entry.data = {"vehicle_name": "test_vehicle"}
        entry.entry_id = "test_entry_id"

        # Set up runtime data with trip_manager
        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": [],
            "punctual_trips": [],
            "kwh_today": 0.0,
            "hours_today": 0,
            "next_trip": None,
        }

        hass.data = {
            DATA_RUNTIME: {
                "ev_trip_planner_test_entry_id": {
                    "trip_manager": mock_trip_manager_for_sensor,
                    "coordinator": mock_coordinator,
                }
            }
        }

        async_add_entities = MagicMock()

        from custom_components.ev_trip_planner.sensor import async_setup_entry
        result = await async_setup_entry(hass, entry, async_add_entities)

        assert result is True
        async_add_entities.assert_called_once()

        # Verify 8 entities were added
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 8
