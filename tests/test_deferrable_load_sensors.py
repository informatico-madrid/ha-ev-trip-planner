"""Tests for EmhassDeferrableLoadSensor and power_profile_watts calculation.

Tests the EmhassDeferrableLoadSensor entity which provides:
- power_profile_watts: Array of power in watts per hour (0W = no charging, positive = charging)
- deferrables_schedule: Schedule of deferrable loads

File: tests/test_deferrable_load_sensors.py
"""

import pytest
from unittest.mock import Mock, AsyncMock

from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor
from custom_components.ev_trip_planner.trip_manager import TripManager
from custom_components.ev_trip_planner.const import DOMAIN


pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance with config entry."""
    from custom_components.ev_trip_planner.const import DOMAIN as EV_TRIP_DOMAIN

    hass = Mock()
    hass.data = {}

    # Mock config entry
    mock_entry = Mock()
    mock_entry.data = {
        "vehicle_name": "test_vehicle",
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "planning_horizon_days": 7,
    }
    mock_entry.config_entry_id = "test_entry_id"

    # Mock async_get_entry to return the entry
    hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

    # Mock async_entries to return a list of config entries (required for vehicle_name matching)
    hass.config_entries.async_entries = Mock(return_value=[mock_entry])

    return hass


@pytest.fixture
def mock_trip_manager():
    """Create mock TripManager instance."""
    trip_manager = Mock(spec=TripManager)
    trip_manager.vehicle_id = "test_vehicle"
    return trip_manager


@pytest.fixture
def sensor(mock_hass, mock_trip_manager):
    """Create EmhassDeferrableLoadSensor instance."""
    return EmhassDeferrableLoadSensor(
        hass=mock_hass,
        trip_manager=mock_trip_manager,
        vehicle_id="test_vehicle",
    )


class TestPowerProfileWattsCalculation:
    """Tests for power_profile_watts calculation: 0W = no charging, positive = charging."""

    async def test_power_profile_watts_all_zeros_when_no_trips(self, sensor):
        """Test that power_profile_watts is all zeros when there are no trips needing charge."""
        # Mock trip_manager to return empty power profile
        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            return_value=[0.0] * 168  # 7 days * 24 hours
        )
        sensor.trip_manager.async_generate_deferrables_schedule = AsyncMock(
            return_value=[]
        )

        await sensor.async_update()

        assert sensor.extra_state_attributes["power_profile_watts"] == [0.0] * 168

    async def test_power_profile_watts_positive_values_for_charging(self, sensor):
        """Test that power_profile_watts contains positive values when charging is needed."""
        # Create a power profile with some charging hours
        power_profile = [0.0] * 24
        power_profile[10] = 3600.0  # 3.6 kW charging at hour 10
        power_profile[11] = 3600.0  # 3.6 kW charging at hour 11
        power_profile[12] = 3600.0  # 3.6 kW charging at hour 12

        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            return_value=power_profile
        )
        sensor.trip_manager.async_generate_deferrables_schedule = AsyncMock(
            return_value=[]
        )

        await sensor.async_update()

        result = sensor.extra_state_attributes["power_profile_watts"]
        assert result[10] == 3600.0
        assert result[11] == 3600.0
        assert result[12] == 3600.0

    async def test_power_profile_watts_mixed_zeros_and_positive(self, sensor):
        """Test that power_profile_watts correctly shows 0W (no charging) and positive (charging)."""
        # Mixed profile: some hours with charging, some without
        power_profile = [0.0] * 24
        power_profile[5] = 0.0     # No charging at hour 5
        power_profile[6] = 3600.0  # Charging at hour 6
        power_profile[7] = 0.0     # No charging at hour 7
        power_profile[8] = 7200.0  # Higher charging at hour 8 (7.2 kW)

        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            return_value=power_profile
        )
        sensor.trip_manager.async_generate_deferrables_schedule = AsyncMock(
            return_value=[]
        )

        await sensor.async_update()

        result = sensor.extra_state_attributes["power_profile_watts"]
        # Verify: 0W = no charging
        assert result[5] == 0.0
        assert result[7] == 0.0
        # Verify: positive = charging
        assert result[6] == 3600.0
        assert result[8] == 7200.0

    async def test_power_profile_watts_uses_charging_power_kw(self, sensor):
        """Test that power_profile_watts uses the configured charging power in kW."""
        # Update config to use 7.2 kW charging
        sensor.hass.config_entries.async_get_entry = Mock(
            return_value=Mock(
                data={
                    "vehicle_name": "test_vehicle",
                    "battery_capacity_kwh": 50.0,
                    "charging_power_kw": 7.2,  # 7.2 kW
                    "planning_horizon_days": 7,
                }
            )
        )

        # The power profile should use 7.2 kW = 7200 W
        power_profile = [0.0] * 168
        power_profile[10] = 7200.0  # Should be 7.2 kW * 1000

        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            return_value=power_profile
        )
        sensor.trip_manager.async_generate_deferrables_schedule = AsyncMock(
            return_value=[]
        )

        await sensor.async_update()

        result = sensor.extra_state_attributes["power_profile_watts"]
        assert result[10] == 7200.0

    async def test_power_profile_watts_default_charging_power(self, sensor):
        """Test that power_profile_watts uses default charging power when not configured."""
        # Use default 3.6 kW
        power_profile = [0.0] * 168
        power_profile[0] = 3600.0  # 3.6 kW * 1000 = 3600 W

        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            return_value=power_profile
        )
        sensor.trip_manager.async_generate_deferrables_schedule = AsyncMock(
            return_value=[]
        )

        await sensor.async_update()

        result = sensor.extra_state_attributes["power_profile_watts"]
        assert result[0] == 3600.0


class TestDeferrablesScheduleGeneration:
    """Tests for deferrables_schedule generation in the sensor."""

    async def test_deferrables_schedule_generated(self, sensor):
        """Test that deferrables_schedule is generated and stored."""
        schedule = [
            {"date": "2026-03-17T10:00:00+01:00", "p_deferrable0": "0.0"},
            {"date": "2026-03-17T11:00:00+01:00", "p_deferrable0": "3600.0"},
        ]

        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            return_value=[0.0, 3600.0]
        )
        sensor.trip_manager.async_generate_deferrables_schedule = AsyncMock(
            return_value=schedule
        )

        await sensor.async_update()

        result = sensor.extra_state_attributes["deferrables_schedule"]
        assert result == schedule

    async def test_deferrables_schedule_length_matches_horizon(self, sensor):
        """Test that deferrables_schedule has correct number of entries."""
        # Test with 1 day horizon (24 hours)
        schedule = [{"date": f"2026-03-17T{i:02d}:00:00+01:00", "p_deferrable0": "0.0"}
                    for i in range(24)]

        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            return_value=[0.0] * 24
        )
        sensor.trip_manager.async_generate_deferrables_schedule = AsyncMock(
            return_value=schedule
        )

        await sensor.async_update()

        result = sensor.extra_state_attributes["deferrables_schedule"]
        assert len(result) == 24

    async def test_deferrables_schedule_multiple_deferrables(self, sensor):
        """Test that deferrables_schedule supports multiple p_deferrableN keys."""
        schedule = [
            {
                "date": "2026-03-17T10:00:00+01:00",
                "p_deferrable0": "3600.0",  # First trip charging
                "p_deferrable1": "0.0",     # Second trip not charging
            },
        ]

        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            return_value=[3600.0]
        )
        sensor.trip_manager.async_generate_deferrables_schedule = AsyncMock(
            return_value=schedule
        )

        await sensor.async_update()

        result = sensor.extra_state_attributes["deferrables_schedule"]
        assert "p_deferrable0" in result[0]
        assert "p_deferrable1" in result[0]


class TestEmhassDeferrableLoadSensor:
    """Tests for EmhassDeferrableLoadSensor entity."""

    async def test_sensor_initial_state(self, sensor):
        """Test sensor initial state."""
        assert sensor._attr_native_value == "ready"
        assert sensor._cached_attrs == {}
        assert sensor.unique_id == "emhass_perfil_diferible_test_vehicle"

    async def test_sensor_updates_attributes(self, sensor):
        """Test that sensor correctly updates all attributes."""
        power_profile = [0.0] * 168
        power_profile[5] = 3600.0

        schedule = [{"date": "2026-03-17T10:00:00+01:00", "p_deferrable0": "0.0"}]

        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            return_value=power_profile
        )
        sensor.trip_manager.async_generate_deferrables_schedule = AsyncMock(
            return_value=schedule
        )

        await sensor.async_update()

        assert sensor.extra_state_attributes["power_profile_watts"] == power_profile
        assert sensor.extra_state_attributes["deferrables_schedule"] == schedule
        assert sensor._attr_native_value == "ready"

    async def test_sensor_handles_missing_config_entry(self, sensor):
        """Test sensor handles missing config entry gracefully."""
        sensor.hass.config_entries.async_get_entry = Mock(return_value=None)

        await sensor.async_update()

        # Should not crash, attributes should be empty
        assert sensor._attr_native_value == "ready"

    async def test_sensor_handles_exception(self, sensor):
        """Test sensor handles exceptions during update."""
        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            side_effect=Exception("Test error")
        )

        await sensor.async_update()

        # Should set state to error on exception
        assert sensor._attr_native_value == "error"

    async def test_sensor_device_info(self, sensor):
        """Test sensor device info."""
        device_info = sensor.device_info

        assert device_info["identifiers"] == {(DOMAIN, "test_vehicle")}
        assert device_info["name"] == "EV Trip Planner test_vehicle"
        assert device_info["manufacturer"] == "Home Assistant"
        assert device_info["model"] == "EV Trip Planner"


class TestPowerProfileSemantics:
    """Tests for power_profile_watts semantic meaning: 0W = no charging, positive = charging."""

    async def test_zero_watts_means_no_charging(self, sensor):
        """Test that 0W in power_profile means no charging at that hour."""
        # Profile with zeros = no charging hours
        power_profile = [0.0] * 24

        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            return_value=power_profile
        )
        sensor.trip_manager.async_generate_deferrables_schedule = AsyncMock(
            return_value=[]
        )

        await sensor.async_update()

        result = sensor.extra_state_attributes["power_profile_watts"]
        # All hours should be 0 = no charging
        assert all(p == 0.0 for p in result)

    async def test_positive_watts_means_charging(self, sensor):
        """Test that positive watts in power_profile means charging at that hour."""
        # Profile with positive values = charging hours
        power_profile = [0.0] * 24
        for i in range(24):
            if i % 4 == 0:  # Every 4th hour is charging
                power_profile[i] = 3600.0

        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            return_value=power_profile
        )
        sensor.trip_manager.async_generate_deferrables_schedule = AsyncMock(
            return_value=[]
        )

        await sensor.async_update()

        result = sensor.extra_state_attributes["power_profile_watts"]
        # Every 4th hour should have 3600W = charging
        charging_hours = [i for i, p in enumerate(result) if p > 0]
        assert len(charging_hours) == 6  # 24/4 = 6 charging hours
        assert charging_hours == [0, 4, 8, 12, 16, 20]

    async def test_power_profile_length_168_for_7_days(self, sensor):
        """Test that power_profile has 168 entries for 7-day horizon."""
        power_profile = [0.0] * 168

        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            return_value=power_profile
        )
        sensor.trip_manager.async_generate_deferrables_schedule = AsyncMock(
            return_value=[]
        )

        await sensor.async_update()

        result = sensor.extra_state_attributes["power_profile_watts"]
        assert len(result) == 168  # 7 days * 24 hours

    async def test_power_profile_with_multiple_charging_levels(self, sensor):
        """Test power_profile with different charging power levels."""
        power_profile = [0.0] * 24
        power_profile[0] = 3600.0   # 3.6 kW
        power_profile[1] = 7200.0   # 7.2 kW
        power_profile[2] = 11000.0  # 11 kW
        power_profile[3] = 22000.0  # 22 kW (high power charging)

        sensor.trip_manager.async_generate_power_profile = AsyncMock(
            return_value=power_profile
        )
        sensor.trip_manager.async_generate_deferrables_schedule = AsyncMock(
            return_value=[]
        )

        await sensor.async_update()

        result = sensor.extra_state_attributes["power_profile_watts"]
        assert result[0] == 3600.0
        assert result[1] == 7200.0
        assert result[2] == 11000.0
        assert result[3] == 22000.0
