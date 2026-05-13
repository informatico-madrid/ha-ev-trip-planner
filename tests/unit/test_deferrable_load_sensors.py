"""Tests for EmhassDeferrableLoadSensor and power_profile_watts calculation.

Tests the EmhassDeferrableLoadSensor entity which provides:
- power_profile_watts: Array of power in watts per hour (0W = no charging, positive = charging)
- deferrables_schedule: Schedule of deferrable loads

File: tests/test_deferrable_load_sensors.py

PHASE 3: Tests updated to use coordinator-based architecture.
EmhassDeferrableLoadSensor now inherits CoordinatorEntity and reads from
coordinator.data instead of calling trip_manager methods directly.
"""

from unittest.mock import Mock

import pytest

from custom_components.ev_trip_planner.const import DOMAIN
from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator
from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_coordinator(mock_hass):
    """Create mock TripPlannerCoordinator with EMHASS data structure."""
    coordinator = Mock(spec=TripPlannerCoordinator)
    coordinator.hass = mock_hass
    coordinator.vehicle_id = "test_vehicle"
    coordinator.last_update_success = True

    # Initial data structure with EMHASS fields
    coordinator.data = {
        "recurring_trips": {},
        "punctual_trips": {},
        "kwh_today": 0.0,
        "hours_today": 0.0,
        "next_trip": None,
        "emhass_power_profile": None,
        "emhass_deferrables_schedule": None,
        "emhass_status": "ready",
    }

    return coordinator


@pytest.fixture
def sensor(mock_coordinator):
    """Create EmhassDeferrableLoadSensor instance with coordinator."""
    s = EmhassDeferrableLoadSensor(
        coordinator=mock_coordinator,
        entry_id="test_entry_id",
    )
    return s


class TestPowerProfileWattsCalculation:
    """Tests for power_profile_watts calculation: 0W = no charging, positive = charging."""

    async def test_power_profile_watts_all_zeros_when_no_trips(
        self, mock_coordinator, sensor
    ):
        """Test that power_profile_watts is all zeros when there are no trips needing charge."""
        # Set coordinator data with empty power profile
        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": [0.0] * 168,
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }

        assert sensor.extra_state_attributes["power_profile_watts"] == [0.0] * 168

    async def test_power_profile_watts_positive_values_for_charging(
        self, mock_coordinator, sensor
    ):
        """Test that power_profile_watts contains positive values when charging is needed."""
        # Create a power profile with some charging hours
        power_profile = [0.0] * 168
        power_profile[10] = 3600.0  # 3.6 kW charging at hour 10
        power_profile[11] = 3600.0  # 3.6 kW charging at hour 11
        power_profile[12] = 3600.0  # 3.6 kW charging at hour 12

        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": power_profile,
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }

        result = sensor.extra_state_attributes["power_profile_watts"]
        assert result[10] == 3600.0
        assert result[11] == 3600.0
        assert result[12] == 3600.0

    async def test_power_profile_watts_mixed_zeros_and_positive(
        self, mock_coordinator, sensor
    ):
        """Test that power_profile_watts correctly shows 0W (no charging) and positive (charging)."""
        # Mixed profile: some hours with charging, some without
        power_profile = [0.0] * 24
        power_profile[5] = 0.0  # No charging at hour 5
        power_profile[6] = 3600.0  # Charging at hour 6
        power_profile[7] = 0.0  # No charging at hour 7
        power_profile[8] = 7200.0  # Higher charging at hour 8 (7.2 kW)

        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": power_profile,
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }

        result = sensor.extra_state_attributes["power_profile_watts"]
        # Verify: 0W = no charging
        assert result[5] == 0.0
        assert result[7] == 0.0
        # Verify: positive = charging
        assert result[6] == 3600.0
        assert result[8] == 7200.0

    async def test_power_profile_watts_uses_charging_power_kw(
        self, mock_coordinator, sensor
    ):
        """Test that power_profile_watts uses the configured charging power in kW."""
        # Set config to use 7.2 kW charging
        power_profile = [0.0] * 168
        power_profile[10] = 7200.0  # Should be 7.2 kW * 1000

        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": power_profile,
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }

        result = sensor.extra_state_attributes["power_profile_watts"]
        assert result[10] == 7200.0

    async def test_power_profile_watts_default_charging_power(
        self, mock_coordinator, sensor
    ):
        """Test that power_profile_watts uses default charging power when not configured."""
        # Use default 3.6 kW
        power_profile = [0.0] * 168
        power_profile[0] = 3600.0  # 3.6 kW * 1000 = 3600 W

        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": power_profile,
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }

        result = sensor.extra_state_attributes["power_profile_watts"]
        assert result[0] == 3600.0


class TestDeferrablesScheduleGeneration:
    """Tests for deferrables_schedule generation in the sensor."""

    async def test_deferrables_schedule_generated(self, mock_coordinator, sensor):
        """Test that deferrables_schedule is generated and stored."""
        schedule = [
            {"date": "2026-03-17T10:00:00+01:00", "p_deferrable0": "0.0"},
            {"date": "2026-03-17T11:00:00+01:00", "p_deferrable0": "3600.0"},
        ]

        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": [0.0, 3600.0],
            "emhass_deferrables_schedule": schedule,
            "emhass_status": "ready",
        }

        result = sensor.extra_state_attributes["deferrables_schedule"]
        assert result == schedule

    async def test_deferrables_schedule_length_matches_horizon(
        self, mock_coordinator, sensor
    ):
        """Test that deferrables_schedule has correct number of entries."""
        # Test with 1 day horizon (24 hours)
        schedule = [
            {"date": f"2026-03-17T{i:02d}:00:00+01:00", "p_deferrable0": "0.0"}
            for i in range(24)
        ]

        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": [0.0] * 24,
            "emhass_deferrables_schedule": schedule,
            "emhass_status": "ready",
        }

        result = sensor.extra_state_attributes["deferrables_schedule"]
        assert len(result) == 24

    async def test_deferrables_schedule_multiple_deferrables(
        self, mock_coordinator, sensor
    ):
        """Test that deferrables_schedule supports multiple p_deferrableN keys."""
        schedule = [
            {
                "date": "2026-03-17T10:00:00+01:00",
                "p_deferrable0": "3600.0",  # First trip charging
                "p_deferrable1": "0.0",  # Second trip not charging
            },
        ]

        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": [3600.0],
            "emhass_deferrables_schedule": schedule,
            "emhass_status": "ready",
        }

        result = sensor.extra_state_attributes["deferrables_schedule"]
        assert "p_deferrable0" in result[0]
        assert "p_deferrable1" in result[0]


class TestEmhassDeferrableLoadSensor:
    """Tests for EmhassDeferrableLoadSensor entity."""

    async def test_sensor_initial_state(self, mock_coordinator, sensor):
        """Test sensor initial state from coordinator data."""
        assert sensor.native_value == "ready"
        assert sensor.unique_id == "emhass_perfil_diferible_test_entry_id"

    async def test_sensor_updates_attributes(self, mock_coordinator, sensor):
        """Test that sensor correctly reads all attributes from coordinator.data."""
        power_profile = [0.0] * 168
        power_profile[5] = 3600.0

        schedule = [{"date": "2026-03-17T10:00:00+01:00", "p_deferrable0": "0.0"}]

        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": power_profile,
            "emhass_deferrables_schedule": schedule,
            "emhass_status": "ready",
        }

        assert sensor.extra_state_attributes["power_profile_watts"] == power_profile
        assert sensor.extra_state_attributes["deferrables_schedule"] == schedule
        assert sensor.native_value == "ready"

    async def test_sensor_handles_missing_config_entry(self, mock_coordinator, sensor):
        """Test sensor handles missing config entry gracefully via coordinator."""
        # Set coordinator data to None to simulate no data
        mock_coordinator.data = None

        # Should not crash, native_value should return "unknown" when data is None
        assert sensor.native_value == "unknown"

    async def test_sensor_handles_exception(self, mock_coordinator, sensor):
        """Test sensor handles exceptions via coordinator status."""
        # Simulate error state in coordinator data
        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": None,
            "emhass_deferrables_schedule": None,
            "emhass_status": "error",
        }

        # Should set state to error
        assert sensor.native_value == "error"

    async def test_sensor_device_info(self, mock_coordinator, sensor):
        """Test sensor device info uses vehicle_id from coordinator.

        Task 1.4 test: expects device_info to use vehicle_id, not entry_id.
        """
        device_info = sensor.device_info

        assert device_info["identifiers"] == {(DOMAIN, "test_vehicle")}
        assert device_info["name"] == "EV Trip Planner test_vehicle"
        assert device_info["manufacturer"] == "Home Assistant"
        assert device_info["model"] == "EV Trip Planner"

    async def test_sensor_includes_emhass_status_attribute(
        self, mock_coordinator, sensor
    ):
        """Test that emhass_status attribute is present and correct."""
        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": [0.0] * 168,
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }

        attrs = sensor.extra_state_attributes
        assert "emhass_status" in attrs
        assert attrs["emhass_status"] == "ready"

    async def test_sensor_emhass_status_error_on_exception(
        self, mock_coordinator, sensor
    ):
        """Test that exception in coordinator sets emhass_status to error."""
        # Simulate error state in coordinator data
        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": None,
            "emhass_deferrables_schedule": None,
            "emhass_status": "error",
        }

        assert sensor.native_value == "error"
        assert sensor.extra_state_attributes["emhass_status"] == "error"

    async def test_sensor_name_uses_vehicle_id(self, mock_coordinator, sensor):
        """Test sensor _attr_name uses vehicle_id from coordinator, not entry_id.

        Task 1.7 test: expects sensor name to use vehicle_id, not entry_id UUID.
        """
        assert sensor._attr_name == "EMHASS Perfil Diferible test_vehicle"
        assert "test_entry_id" not in sensor._attr_name


class TestPowerProfileSemantics:
    """Tests for power_profile_watts semantic meaning: 0W = no charging, positive = charging."""

    async def test_zero_watts_means_no_charging(self, mock_coordinator, sensor):
        """Test that 0W in power_profile means no charging at that hour."""
        # Profile with zeros = no charging hours
        power_profile = [0.0] * 24

        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": power_profile,
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }

        result = sensor.extra_state_attributes["power_profile_watts"]
        # All hours should be 0 = no charging
        assert all(p == 0.0 for p in result)

    async def test_positive_watts_means_charging(self, mock_coordinator, sensor):
        """Test that positive watts in power_profile means charging at that hour."""
        # Profile with positive values = charging hours
        power_profile = [0.0] * 24
        for i in range(24):
            if i % 4 == 0:  # Every 4th hour is charging
                power_profile[i] = 3600.0

        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": power_profile,
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }

        result = sensor.extra_state_attributes["power_profile_watts"]
        # Every 4th hour should have 3600W = charging
        charging_hours = [i for i, p in enumerate(result) if p > 0]
        assert len(charging_hours) == 6  # 24/4 = 6 charging hours
        assert charging_hours == [0, 4, 8, 12, 16, 20]

    async def test_power_profile_length_168_for_7_days(self, mock_coordinator, sensor):
        """Test that power_profile has 168 entries for 7-day horizon."""
        power_profile = [0.0] * 168

        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": power_profile,
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }

        result = sensor.extra_state_attributes["power_profile_watts"]
        assert len(result) == 168  # 7 days * 24 hours

    async def test_power_profile_with_multiple_charging_levels(
        self, mock_coordinator, sensor
    ):
        """Test power_profile with different charging power levels."""
        power_profile = [0.0] * 24
        power_profile[0] = 3600.0  # 3.6 kW
        power_profile[1] = 7200.0  # 7.2 kW
        power_profile[2] = 11000.0  # 11 kW
        power_profile[3] = 22000.0  # 22 kW (high power charging)

        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": power_profile,
            "emhass_deferrables_schedule": [],
            "emhass_status": "ready",
        }

        result = sensor.extra_state_attributes["power_profile_watts"]
        assert result[0] == 3600.0
        assert result[1] == 7200.0
        assert result[2] == 11000.0
        assert result[3] == 22000.0

    async def test_extra_state_attributes_when_coordinator_data_is_none(self, sensor):
        """coordinator.data=None returns empty dict (lines 87-91)."""
        sensor.coordinator.data = None
        result = sensor.extra_state_attributes
        assert result == {}

    async def test_extra_state_attributes_with_per_trip_emhass_params(
        self, mock_coordinator, sensor
    ):
        """Aggregation loop with per_trip_emhass_params (lines 153-205)."""
        mock_coordinator.data = {
            "recurring_trips": {},
            "punctual_trips": {},
            "kwh_today": 12.5,
            "hours_today": 2.0,
            "next_trip": None,
            "emhass_power_profile": [100.0] * 96,
            "emhass_deferrables_schedule": [
                {"index": 0, "kwh": 5.0, "start_timestep": 10, "end_timestep": 20}
            ],
            "emhass_status": "ready",
            "per_trip_emhass_params": {
                "rec_1": {
                    "activo": True,
                    "kwh_needed": 5.0,
                    "p_deferrable_matrix": [[0.0] * 96],
                    "def_total_hours_array": [2.0],
                    "p_deferrable_nom_array": [3000.0],
                    "def_start_timestep_array": [10],
                    "def_end_timestep_array": [20],
                },
                "rec_2": {
                    "activo": False,  # Inactive — should be skipped
                    "kwh_needed": 3.0,
                },
            },
        }
        attrs = sensor.extra_state_attributes
        # Basic attrs
        assert attrs["vehicle_id"] == "test_vehicle"
        assert attrs["emhass_status"] == "ready"
        # Aggregated from active trips only (rec_1)
        assert "p_deferrable_matrix" in attrs
        # p_deferrable_matrix is a list of rows (one per deferrable load)
        assert len(attrs["p_deferrable_matrix"]) == 1
        assert len(attrs["p_deferrable_matrix"][0]) == 96  # Each row has 96 timesteps
        assert attrs["def_total_hours_array"] == [2.0]
        assert attrs["p_deferrable_nom_array"] == [3000.0]
        assert attrs["def_start_timestep_array"] == [10]
        assert attrs["def_end_timestep_array"] == [20]
        # Inactive trip (rec_2) should not contribute
        assert attrs["number_of_deferrable_loads"] == 1

    async def test_extra_state_attributes_trip_without_power_matrix(
        self, mock_coordinator, sensor
    ):
        """Trip with params but no p_deferrable_matrix counts as 1 load (lines 179-182)."""
        mock_coordinator.data = {
            **mock_coordinator.data,
            "emhass_power_profile": [0.0] * 96,
            "per_trip_emhass_params": {
                "rec_1": {
                    "activo": True,
                    "kwh_needed": 5.0,
                    # No p_deferrable_matrix — should count as 1 deferrable load
                },
            },
        }
        attrs = sensor.extra_state_attributes
        assert attrs["number_of_deferrable_loads"] == 1
        # No p_deferrable_matrix from this trip
        assert "p_deferrable_matrix" not in attrs

    async def test_extra_state_attributes_no_params_empty_arrays(self, mock_coordinator, sensor):
        """No per_trip_params → aggregation paths not taken but number_of_deferrable_loads=0."""
        mock_coordinator.data = {
            **mock_coordinator.data,
            "per_trip_emhass_params": {},
        }
        attrs = sensor.extra_state_attributes
        assert attrs["number_of_deferrable_loads"] == 0
        assert "p_deferrable_matrix" not in attrs
