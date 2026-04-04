"""Additional tests for sensor coverage - EmhassDeferrableLoadSensor and error paths."""

import pytest
from unittest.mock import MagicMock, AsyncMock, Mock
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
            hass, mock_trip_manager_for_sensor, "test_entry_id"
        )
        assert sensor.unique_id == "emhass_perfil_diferible_test_entry_id"

    async def test_emhass_sensor_device_info(self, hass: HomeAssistant, mock_trip_manager_for_sensor):
        """Test EmhassDeferrableLoadSensor device_info property."""
        sensor = EmhassDeferrableLoadSensor(
            hass, mock_trip_manager_for_sensor, "test_entry_id"
        )
        device_info = sensor.device_info
        assert device_info["identifiers"] == {("ev_trip_planner", "test_entry_id")}
        assert device_info["name"] == "EV Trip Planner test_vehicle"

    async def test_emhass_sensor_extra_state_attributes(
        self, hass: HomeAssistant, mock_trip_manager_for_sensor
    ):
        """Test EmhassDeferrableLoadSensor extra_state_attributes property."""
        sensor = EmhassDeferrableLoadSensor(
            hass, mock_trip_manager_for_sensor, "test_entry_id"
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
        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

        # Mock the power profile and schedule generation
        mock_trip_manager_for_sensor.async_generate_power_profile = AsyncMock(
            return_value=[1000, 2000, 3000]
        )
        mock_trip_manager_for_sensor.async_generate_deferrables_schedule = AsyncMock(
            return_value=[{"hour": 0, "power": 1000}, {"hour": 1, "power": 2000}]
        )

        sensor = EmhassDeferrableLoadSensor(
            hass, mock_trip_manager_for_sensor, "test_entry_id"
        )
        sensor.async_schedule_update_ha_state = Mock()
        await sensor.async_update()

        assert sensor.native_value == "ready"
        assert "power_profile_watts" in sensor.extra_state_attributes
        assert "deferrables_schedule" in sensor.extra_state_attributes

    async def test_emhass_sensor_async_update_no_config_entry(
        self, hass: HomeAssistant, mock_trip_manager_for_sensor
    ):
        """Test EmhassDeferrableLoadSensor async_update without config entry."""
        hass.config_entries.async_get_entry = MagicMock(return_value=None)
        hass.config_entries.async_entries = MagicMock(return_value=[])

        sensor = EmhassDeferrableLoadSensor(
            hass, mock_trip_manager_for_sensor, "test_entry_id"
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
        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

        # Mock to raise exception
        mock_trip_manager_for_sensor.async_generate_power_profile = AsyncMock(
            side_effect=Exception("Test error")
        )

        sensor = EmhassDeferrableLoadSensor(
            hass, mock_trip_manager_for_sensor, "test_entry_id"
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


class TestNextTripSensorNoTrips:
    """Tests for NextTripSensor when there are no trips scheduled.

    These tests reproduce the P003 bug: NextTripSensor returns string values
    ("N/A", "No trips") when there are no trips, but the base class
    TripPlannerSensor has device_class=ENERGY which only accepts numeric values.
    This causes:
    ValueError: Sensor has device class 'energy', state class 'measurement'
    unit 'kWh' thus indicating it has a numeric value; however, it has the
    non-numeric value: 'N/A' (<class 'str'>)

    Expected: FAIL with ValueError before fix
    After fix (removing device_class from NextTripSensor): PASS
    """

    async def test_next_trip_sensor_has_energy_device_class(
        self, hass: HomeAssistant
    ):
        """Test that NextTripSensor inherits device_class=ENERGY from base class.

        This test verifies the root cause of the P003 bug: NextTripSensor
        inherits device_class=ENERGY from TripPlannerSensor, but NextTripSensor
        returns string values like "N/A" when there are no trips.

        Before fix: NextTripSensor has device_class=ENERGY (BUG - incompatible)
        After fix: NextTripSensor should NOT have device_class=ENERGY

        This test should PASS now (verifying the bug exists) and the fix
        will remove device_class from NextTripSensor.
        """
        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "next_trip": None,
        }

        sensor = NextTripSensor("test_vehicle", mock_coordinator)

        # After fix: NextTripSensor should NOT have device_class=ENERGY
        # because it returns string values like "N/A" when there are no trips
        current_device_class = getattr(
            sensor, "_attr_device_class", None
        )

        # Verify device_class is not ENERGY (this is the fix for P003)
        assert current_device_class is None or current_device_class.value != "energy", (
            "NextTripSensor should not have device_class=ENERGY because it "
            "returns string values like 'N/A' when there are no trips (P003 fix)"
        )

    async def test_next_trip_sensor_returns_string_with_no_trips(self):
        """Test that NextTripSensor returns string when no trips available.

        This test verifies that when there are no trips, the sensor returns
        a string value ("No trips"). This is the behavior that causes the
        ValueError when device_class=ENERGY is set.
        """
        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "next_trip": None,
        }

        sensor = NextTripSensor("test_vehicle", mock_coordinator)

        # The sensor returns "No trips" when there are no trips
        # This is correct behavior but incompatible with device_class=ENERGY
        value = sensor.native_value
        assert value == "No trips", (
            "NextTripSensor should return 'No trips' when no trips available"
        )

    async def test_next_trip_sensor_with_empty_trip_list(self):
        """Test NextTripSensor when coordinator.data is empty dict.

        This test verifies the sensor handles edge cases correctly.
        """
        mock_coordinator = MagicMock()
        mock_coordinator.data = {}  # Empty data

        sensor = NextTripSensor("test_vehicle", mock_coordinator)

        # Should return a sensible default when data is empty
        value = sensor.native_value
        assert value == "No trips", (
            "NextTripSensor should return 'No trips' for empty data"
        )


class TestEmhassDeferrableLoadSensorCreation:
    """Tests for EmhassDeferrableLoadSensor creation on vehicle setup.

    RED test: EmhassDeferrableLoadSensor should be created when async_setup_entry
    is called. This verifies AC-2: Vehicle addition creates all necessary sensors
    including EmhassDeferrableLoadSensor.
    """

    async def test_emhass_deferrable_sensor_created_on_setup(
        self, hass: HomeAssistant, mock_trip_manager_for_sensor
    ):
        """Test that EmhassDeferrableLoadSensor is created when vehicle config completes.

        This test verifies AC-2: When async_setup_entry is called (vehicle setup),
        EmhassDeferrableLoadSensor should be created and added to the entities list.
        """
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

        # Verify EmhassDeferrableLoadSensor is in the created entities
        entities = async_add_entities.call_args[0][0]
        entity_types = [type(e).__name__ for e in entities]

        assert "EmhassDeferrableLoadSensor" in entity_types, (
            f"EmhassDeferrableLoadSensor should be created on vehicle setup. "
            f"Created entities: {entity_types}"
        )


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


class TestTripStateChangeUpdatesSensor:
    """Tests for AC-4: Trip state change updates corresponding sensor.

    RED test: When a trip state changes (via async_update_trip or similar),
    the EmhassDeferrableLoadSensor should be updated to reflect the change.
    """

    async def test_trip_state_change_triggers_emhass_sensor_update(
        self, hass: HomeAssistant, mock_trip_manager_for_sensor
    ):
        """Test that trip state change triggers EmhassDeferrableLoadSensor update.

        This test verifies AC-4: When a trip's state is modified
        (e.g., km, datetime, estado), the EmhassDeferrableLoadSensor should
        be updated to reflect the new trip state.

        Before implementation: Sensor state does not reflect trip changes
        After implementation: Sensor state updates when trips change
        """
        from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor

        # Set up the emhass_adapter on trip_manager (required for EMHASS sync)
        mock_emhass_adapter = MagicMock()
        mock_emhass_adapter.async_update_deferrable_load = AsyncMock(return_value=True)
        mock_emhass_adapter.async_publish_deferrable_load = AsyncMock(return_value=True)
        mock_trip_manager_for_sensor._emhass_adapter = mock_emhass_adapter

        # Create the EmhassDeferrableLoadSensor
        sensor = EmhassDeferrableLoadSensor(
            hass, mock_trip_manager_for_sensor, "test_entry_id"
        )

        # Set up mock config entry
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.data = {
            "vehicle_name": "test_vehicle",
            "charging_power": 7.0,
            "planning_horizon_days": 7,
        }
        mock_entry.entry_id = "test_entry_id"
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

        # Mock trip_manager methods used by sensor's async_update
        mock_trip_manager_for_sensor.async_generate_power_profile = AsyncMock(
            return_value=[1000, 2000, 3000]
        )
        mock_trip_manager_for_sensor.async_generate_deferrables_schedule = AsyncMock(
            return_value=[{"hour": 0, "power": 1000}, {"hour": 1, "power": 2000}]
        )
        mock_trip_manager_for_sensor.async_get_recurring_trips = AsyncMock(
            return_value=[{"id": "trip_1", "km": 30, "kwh": 4.5}]
        )
        mock_trip_manager_for_sensor.async_get_punctual_trips = AsyncMock(
            return_value=[{"id": "trip_2", "km": 50, "kwh": 7.5}]
        )

        # Initial update - sensor should be ready
        await sensor.async_update()
        initial_native_value = sensor.native_value

        assert initial_native_value == "ready", "Sensor should be ready after initial update"

        # Now change the trip state by updating a trip
        # This simulates what happens when user edits a trip
        # Pre-populate _recurring_trips so the real async_update_trip can find and sync the trip
        mock_trip_manager_for_sensor._recurring_trips["trip_1"] = {
            "id": "trip_1",
            "km": 30,
            "kwh": 4.5,
            "activo": True,
        }
        # Use side_effect to call the real async_update_trip implementation
        real_update_trip = mock_trip_manager_for_sensor.__class__.async_update_trip

        async def side_effect_impl(tid, upd, **kw):
            return await real_update_trip(mock_trip_manager_for_sensor, tid, upd, **kw)

        mock_trip_manager_for_sensor.async_update_trip = AsyncMock(side_effect=side_effect_impl)

        # Trigger trip state change
        await mock_trip_manager_for_sensor.async_update_trip(
            "trip_1",
            {"km": 35, "kwh": 5.25}  # Change trip distance
        )

        # The sensor should detect the trip state change and update
        # Verify by checking that async_update_deferrable_load was called
        # on the emhass_adapter (this is the mechanism for updating EMHASS sensors)
        assert mock_emhass_adapter.async_update_deferrable_load.called, (
            "Trip state change should trigger async_update_deferrable_load call "
            "to update the EMHASS sensor"
        )

    async def test_trip_state_change_updates_emhass_sensor_attributes(
        self, hass: HomeAssistant, mock_trip_manager_for_sensor
    ):
        """Test that trip state change updates EmhassDeferrableLoadSensor attributes.

        When a trip's state changes (e.g., new trip added, trip modified,
        trip deleted), the EmhassDeferrableLoadSensor attributes should be
        updated to reflect the current trip state.
        """
        from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor

        # Set up emhass_adapter
        mock_emhass_adapter = MagicMock()
        mock_emhass_adapter.async_update_deferrable_load = AsyncMock(return_value=True)
        mock_trip_manager_for_sensor._emhass_adapter = mock_emhass_adapter

        # Create sensor
        sensor = EmhassDeferrableLoadSensor(
            hass, mock_trip_manager_for_sensor, "test_entry_id"
        )

        # Set up mocks
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.data = {
            "vehicle_name": "test_vehicle",
            "charging_power": 7.0,
            "planning_horizon_days": 7,
        }
        mock_entry.entry_id = "test_entry_id"
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

        mock_trip_manager_for_sensor.async_generate_power_profile = AsyncMock(
            return_value=[1000]
        )
        mock_trip_manager_for_sensor.async_generate_deferrables_schedule = AsyncMock(
            return_value=[{"hour": 0, "power": 1000}]
        )
        mock_trip_manager_for_sensor.async_get_recurring_trips = AsyncMock(
            return_value=[]
        )
        mock_trip_manager_for_sensor.async_get_punctual_trips = AsyncMock(
            return_value=[]
        )

        # Initial state
        await sensor.async_update()
        initial_trips_count = sensor.extra_state_attributes.get("trips_count", 0)

        # Simulate adding a trip (trip state change)
        mock_trip_manager_for_sensor.async_get_punctual_trips = AsyncMock(
            return_value=[{"id": "new_trip", "km": 25, "kwh": 3.75}]
        )

        # Update sensor after trip was added
        await sensor.async_update()
        updated_trips_count = sensor.extra_state_attributes.get("trips_count", 0)

        # After trip was added, trips_count should increase
        assert updated_trips_count > initial_trips_count, (
            "EmhassDeferrableLoadSensor should reflect trip count changes. "
            f"Expected trips_count to increase from {initial_trips_count}, "
            f"but got {updated_trips_count}"
        )
