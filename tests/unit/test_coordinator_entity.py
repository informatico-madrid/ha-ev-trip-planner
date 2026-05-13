"""Tests for TripPlannerSensor CoordinatorEntity pattern."""

from unittest.mock import MagicMock

from custom_components.ev_trip_planner.definitions import TRIP_SENSORS
from custom_components.ev_trip_planner.sensor import (
    EmhassDeferrableLoadSensor,
    TripPlannerSensor,
    TripSensor,
)


def make_test_coordinator(data):
    """Create a mock coordinator with given data."""
    coordinator = MagicMock()
    coordinator.data = data
    return coordinator


class TestTripPlannerSensorBasics:
    """Basic tests for TripPlannerSensor."""

    def test_trip_planner_sensor_creation(self):
        """Test TripPlannerSensor can be created with coordinator."""
        coordinator = make_test_coordinator(
            {
                "recurring_trips": {},
                "punctual_trips": {},
                "kwh_today": 0.0,
                "hours_today": 0.0,
                "next_trip": None,
            }
        )
        desc = TRIP_SENSORS[0]  # Use first sensor description
        sensor = TripPlannerSensor(coordinator, "test_vehicle", desc)
        assert sensor._vehicle_id == "test_vehicle"
        assert sensor.coordinator == coordinator

    def test_trip_planner_sensor_native_value(self):
        """Test TripPlannerSensor returns value from coordinator.data."""
        coordinator = make_test_coordinator(
            {
                "recurring_trips": {},
                "punctual_trips": {},
                "kwh_today": 12.5,
                "hours_today": 2.0,
                "next_trip": None,
            }
        )
        # Find a description that reads kwh_today
        for desc in TRIP_SENSORS:
            if desc.key == "kwh_needed_today":
                sensor = TripPlannerSensor(coordinator, "test_vehicle", desc)
                assert sensor.native_value == 12.5
                return

    def test_trip_planner_sensor_extra_state_attributes(self):
        """Test TripPlannerSensor extra_state_attributes returns trips."""
        coordinator = make_test_coordinator(
            {
                "recurring_trips": {"rec_1": {"id": "rec_1", "tipo": "recurrente"}},
                "punctual_trips": {"pun_1": {"id": "pun_1", "tipo": "puntual"}},
                "kwh_today": 5.0,
                "hours_today": 1.0,
                "next_trip": None,
            }
        )
        for desc in TRIP_SENSORS:
            if desc.key == "recurring_trips_count":
                sensor = TripPlannerSensor(coordinator, "test_vehicle", desc)
                attrs = sensor.extra_state_attributes
                assert "recurring_trips" in attrs
                assert "punctual_trips" in attrs
                return


class TestEmhassDeferrableLoadSensor:
    """Tests for EmhassDeferrableLoadSensor."""

    def test_emhass_sensor_creation(self):
        """Test EmhassDeferrableLoadSensor can be created."""
        coordinator = make_test_coordinator(
            {
                "emhass_power_profile": None,
                "emhass_deferrables_schedule": None,
                "emhass_status": None,
            }
        )
        sensor = EmhassDeferrableLoadSensor(coordinator, "test_entry")
        assert sensor._entry_id == "test_entry"
        assert sensor.coordinator == coordinator

    def test_emhass_sensor_native_value_with_status(self):
        """Test EmhassDeferrableLoadSensor returns status."""
        coordinator = make_test_coordinator(
            {
                "emhass_power_profile": [100] * 168,
                "emhass_deferrables_schedule": [],
                "emhass_status": "ready",
            }
        )
        sensor = EmhassDeferrableLoadSensor(coordinator, "test_entry")
        assert sensor.native_value == "ready"

    def test_emhass_sensor_native_value_unknown_when_no_data(self):
        """Test EmhassDeferrableLoadSensor returns unknown when no data."""
        coordinator = make_test_coordinator(None)
        sensor = EmhassDeferrableLoadSensor(coordinator, "test_entry")
        assert sensor.native_value == "unknown"

    def test_emhass_sensor_extra_state_attributes(self):
        """Test EmhassDeferrableLoadSensor extra_state_attributes."""
        coordinator = make_test_coordinator(
            {
                "emhass_power_profile": [1.0] * 168,
                "emhass_deferrables_schedule": [{"id": "trip_1"}],
                "emhass_status": "computing",
            }
        )
        sensor = EmhassDeferrableLoadSensor(coordinator, "test_entry")
        attrs = sensor.extra_state_attributes
        assert "emhass_status" in attrs
        assert "power_profile_watts" in attrs
        assert "deferrables_schedule" in attrs
        assert attrs["emhass_status"] == "computing"


class TestTripSensor:
    """Tests for TripSensor."""

    def test_trip_sensor_creation(self):
        """Test TripSensor can be created."""
        coordinator = make_test_coordinator(
            {
                "recurring_trips": {},
                "punctual_trips": {},
                "kwh_today": 0.0,
                "hours_today": 0.0,
                "next_trip": None,
            }
        )
        sensor = TripSensor(coordinator, "test_vehicle", "trip_123")
        assert sensor._vehicle_id == "test_vehicle"
        assert sensor._trip_id == "trip_123"

    def test_trip_sensor_native_value_recurring(self):
        """Test TripSensor returns 'recurrente' for recurring trips."""
        coordinator = make_test_coordinator(
            {
                "recurring_trips": {
                    "trip_123": {"id": "trip_123", "tipo": "recurrente"}
                },
                "punctual_trips": {},
                "kwh_today": 0.0,
                "hours_today": 0.0,
                "next_trip": None,
            }
        )
        sensor = TripSensor(coordinator, "test_vehicle", "trip_123")
        assert sensor.native_value == "recurrente"

    def test_trip_sensor_native_value_when_coordinator_data_none(self):
        """Coordinator data=None → _get_trip_data returns empty → native_value=None (lines 75, 88)."""
        coordinator = MagicMock()
        coordinator.data = None
        sensor = TripSensor(coordinator, "test_vehicle", "trip_123")
        assert sensor.native_value is None

    def test_trip_sensor_device_info(self):
        """device_info returns DeviceInfo with correct identifiers (line 114)."""

        coordinator = make_test_coordinator(
            {
                "recurring_trips": {"trip_123": {"id": "trip_123", "tipo": "recurrente"}},
                "punctual_trips": {},
                "kwh_today": 0.0,
                "hours_today": 0.0,
                "next_trip": None,
            }
        )
        sensor = TripSensor(coordinator, "test_vehicle", "trip_123")
        device_info = sensor.device_info
        assert device_info is not None
        assert isinstance(device_info, dict)
        assert "trip_123" in str(device_info.get("identifiers", {}))
        assert "test_vehicle" in device_info.get("name", "")

    def test_trip_sensor_native_value_punctual(self):
        """Test TripSensor returns estado for punctual trips."""
        coordinator = make_test_coordinator(
            {
                "recurring_trips": {},
                "punctual_trips": {
                    "trip_456": {
                        "id": "trip_456",
                        "tipo": "puntual",
                        "estado": "pendiente",
                    }
                },
                "kwh_today": 0.0,
                "hours_today": 0.0,
                "next_trip": None,
            }
        )
        sensor = TripSensor(coordinator, "test_vehicle", "trip_456")
        assert sensor.native_value == "pendiente"

    def test_trip_sensor_extra_state_attributes(self):
        """Test TripSensor extra_state_attributes returns trip data."""
        coordinator = make_test_coordinator(
            {
                "recurring_trips": {},
                "punctual_trips": {
                    "trip_789": {
                        "id": "trip_789",
                        "tipo": "punctual",
                        "descripcion": "Work commute",
                        "km": 25.0,
                        "kwh": 3.75,
                        "datetime": "2025-11-25T08:00:00",
                        "activo": True,
                        "estado": "pendiente",
                    }
                },
                "kwh_today": 0.0,
                "hours_today": 0.0,
                "next_trip": None,
            }
        )
        sensor = TripSensor(coordinator, "test_vehicle", "trip_789")
        attrs = sensor.extra_state_attributes
        assert attrs["trip_id"] == "trip_789"
        assert attrs["descripcion"] == "Work commute"
        assert attrs["km"] == 25.0
        assert attrs["kwh"] == 3.75

    def test_trip_sensor_returns_empty_dict_when_no_data(self):
        """Test TripSensor returns empty dict when trip not found."""
        coordinator = make_test_coordinator(
            {
                "recurring_trips": {},
                "punctual_trips": {},
                "kwh_today": 0.0,
                "hours_today": 0.0,
                "next_trip": None,
            }
        )
        sensor = TripSensor(coordinator, "test_vehicle", "nonexistent")
        attrs = sensor.extra_state_attributes
        assert attrs == {}


class TestTRIPSensorsTuple:
    """Tests for TRIP_SENSORS tuple."""

    def test_trip_sensors_has_seven_descriptions(self):
        """Test TRIP_SENSORS has 7 sensor descriptions as per Phase 1 spec."""
        assert len(TRIP_SENSORS) == 7

    def test_trip_sensors_keys(self):
        """Test all expected sensor keys are present."""
        keys = {desc.key for desc in TRIP_SENSORS}
        expected_keys = {
            "recurring_trips_count",
            "punctual_trips_count",
            "trips_list",
            "kwh_needed_today",
            "hours_needed_today",
            "next_trip",
            "next_deadline",
        }
        assert keys == expected_keys

    def test_trip_sensors_have_value_fn(self):
        """Test all sensor descriptions have value_fn callable."""
        for desc in TRIP_SENSORS:
            assert callable(desc.value_fn)

    def test_trip_sensors_have_attrs_fn(self):
        """Test all sensor descriptions have attrs_fn callable."""
        for desc in TRIP_SENSORS:
            assert callable(desc.attrs_fn)
