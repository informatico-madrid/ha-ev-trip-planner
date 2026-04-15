"""Integration tests for EMHASS aggregated sensor data flow.

These tests verify the critical path where TripManager.publish_deferrable_loads()
populates the aggregated power profile that the EmhassDeferrableLoadSensor uses.

CRITICAL: The aggregated sensor (sensor.emhass_perfil_diferible_{entry_id}) reads
from coordinator.data["emhass_power_profile"], which comes from
emhass_adapter._cached_power_profile. If this is None or empty, the sensor shows
no data.

These tests complement the existing test_async_publish_all_deferrable_loads tests
by verifying NOT just that _cached_power_profile is set, but that it contains
ACTUAL DATA (non-empty, non-zero values).
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.const import (
    CONF_VEHICLE_NAME,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_CHARGING_POWER,
)


class MockConfigEntry:
    """Mock ConfigEntry for testing."""
    def __init__(self, vehicle_id="test_vehicle", data=None):
        self.entry_id = "test_entry_id"
        self.data = data or {
            CONF_VEHICLE_NAME: vehicle_id,
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }


class MockRuntimeData:
    """Mock runtime_data for ConfigEntry."""
    def __init__(self, coordinator=None, trip_manager=None):
        self.coordinator = coordinator
        self.trip_manager = trip_manager


@pytest.fixture
def mock_hass():
    """Create a mock hass instance."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    hass.states.async_set = AsyncMock()
    return hass


@pytest.fixture
def mock_store(hass):
    """Create a mock store."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock(return_value=None)
    return store


@pytest.fixture
def mock_coordinator():
    """Create a mock TripPlannerCoordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "recurring_trips": {},
        "punctual_trips": {},
        "kwh_today": 0.0,
        "hours_today": 0.0,
    }
    coordinator.async_refresh = AsyncMock()
    return coordinator


# =============================================================================
# AGGREGATED SENSOR DATA FLOW TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_async_publish_all_deferrable_loads_populates_non_empty_power_profile(
    hass, mock_store
):
    """Test that async_publish_all_deferrable_loads populates _cached_power_profile with real data.

    CRITICAL VERIFICATION: The aggregated EMHASS sensor (sensor.emhass_perfil_diferible_{entry_id})
    reads from coordinator.data["emhass_power_profile"], which comes from
    emhass_adapter._cached_power_profile. This test verifies:

    1. _cached_power_profile is NOT None
    2. _cached_power_profile is NOT empty list []
    3. _cached_power_profile contains at least some non-zero values

    This test complements test_async_publish_all_deferrable_loads_uses_fallback_charging_power_when_none
    (line 789 in test_emhass_adapter.py) which only checks `is not None`. A value could be [0,0,0]
    or None, both of which would cause the sensor to show no data.

    E2E TEST REFERENCE: emhass-sensor-updates.spec.ts:278-284 verifies the same thing at E2E level:
    "power_profile_watts should have non-zero values after trip creation"
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    entry = MockConfigEntry("test_vehicle", config)
    entry.runtime_data = MockRuntimeData()

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

        # Create a trip that SHOULD trigger power profile calculation
        trips = [
            {
                "id": "trip_001",
                "descripcion": "Test Trip",
                "kwh": 10.0,
                "hora": "09:00",
                "dias_semana": ["monday", "wednesday", "friday"],
                "datetime": (datetime.now() + timedelta(days=1)).isoformat(),
            },
        ]

        # Publish trips - this is what TripManager.publish_deferrable_loads() does
        await adapter.async_publish_all_deferrable_loads(trips)

        # CRITICAL: _cached_power_profile must have actual values, not just be non-None
        assert adapter._cached_power_profile is not None, (
            "BUG: _cached_power_profile is None after async_publish_all_deferrable_loads(). "
            "The aggregated EMHASS sensor cannot provide power_profile_watts data."
        )

        # CRITICAL: Must have data, not empty list
        assert len(adapter._cached_power_profile) > 0, (
            f"BUG: _cached_power_profile is empty list. Expected 168 hourly values (24h * 7 days), "
            f"got {len(adapter._cached_power_profile)}. The sensor will show no deferrable schedule."
        )

        # CRITICAL: Must have at least some non-zero values (actual charging hours)
        non_zero_count = sum(1 for v in adapter._cached_power_profile if v > 0)
        assert non_zero_count > 0, (
            f"BUG: _cached_power_profile has all zeros. Expected at least some charging hours "
            f"with positive values. Full profile length: {len(adapter._cached_power_profile)}. "
            f"The sensor will show no active deferrable loads."
        )

        # Log for debugging
        print(f"SUCCESS: _cached_power_profile populated with {len(adapter._cached_power_profile)} "
              f"hourly values, {non_zero_count} with non-zero values")


@pytest.mark.asyncio
async def test_aggregated_sensor_can_access_power_profile_via_coordinator(
    hass, mock_store, mock_coordinator
):
    """Test the complete data flow: adapter -> coordinator -> sensor.

    This test verifies the ACTUAL INTEGRATION PATH:
    1. EMHASSAdapter.async_publish_all_deferrable_loads() populates _cached_power_profile
    2. Coordinator._async_update_data() calls adapter.get_cached_optimization_results()
    3. EmhassDeferrableLoadSensor.extra_state_attributes reads coordinator.data["emhass_power_profile"]

    The sensor reads this in sensor.py:215:
        "power_profile_watts": self.coordinator.data.get("emhass_power_profile")

    If step 1 doesn't populate _cached_power_profile with REAL DATA, step 3 returns None or [].
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    entry = MockConfigEntry("test_vehicle", config)
    entry.runtime_data = MockRuntimeData(coordinator=mock_coordinator)

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

        trips = [
            {
                "id": "trip_001",
                "kwh": 10.0,
                "hora": "09:00",
                "datetime": (datetime.now() + timedelta(days=1)).isoformat(),
            },
        ]

        # Publish trips (simulating TripManager.publish_deferrable_loads())
        await adapter.async_publish_all_deferrable_loads(trips)

        # Simulate what coordinator._async_update_data() does (line 126 in coordinator.py)
        cached_results = adapter.get_cached_optimization_results()

        # Simulate what EmhassDeferrableLoadSensor.extra_state_attributes does (line 215 in sensor.py)
        power_profile = cached_results.get("emhass_power_profile")

        # THE CRITICAL CHECK: power_profile must have real data
        assert power_profile is not None, (
            "BUG: Coordinator cannot provide emhass_power_profile via get_cached_optimization_results(). "
            "The aggregated sensor reads from here and will show no data."
        )

        # THE REAL TEST: Must have values > 0
        non_zero_count = sum(1 for v in power_profile if v > 0)
        assert non_zero_count > 0, (
            f"BUG: Coordinator provides emhass_power_profile but it's all zeros. "
            f"Non-zero count: {non_zero_count}. The EMHASS integration cannot schedule deferrable loads."
        )

        print(f"SUCCESS: Coordinator can provide power_profile: {len(power_profile)} hours, "
              f"{non_zero_count} with non-zero values")


@pytest.mark.asyncio
async def test_get_cached_results_provides_real_data_to_sensor(
    hass, mock_store
):
    """Test that get_cached_optimization_results returns usable data for the sensor.

    This is a focused test on the integration point between EMHASSAdapter and the sensor.
    The sensor's extra_state_attributes reads directly from this method's output.

    COMPLEMENTARY TO:
    - test_get_cached_optimization_results_returns_dict (line 508): Only checks keys exist
    - test_get_cached_results_includes_per_trip_params (line 1277): Only checks per_trip key

    THIS TEST VERIFIES:
    - The ACTUAL VALUES are usable (not None, not empty, not all zeros)
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    entry = MockConfigEntry("test_vehicle", config)

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

        trips = [
            {
                "id": "trip_001",
                "kwh": 15.0,
                "hora": "10:00",
                "datetime": (datetime.now() + timedelta(hours=2)).isoformat(),
            },
            {
                "id": "trip_002",
                "kwh": 20.0,
                "hora": "14:00",
                "datetime": (datetime.now() + timedelta(hours=5)).isoformat(),
            },
        ]

        # Publish multiple trips
        await adapter.async_publish_all_deferrable_loads(trips)

        # Get what the sensor reads
        sensor_data = adapter.get_cached_optimization_results()

        # Verify structure (complements test_get_cached_optimization_results_returns_dict)
        assert "emhass_power_profile" in sensor_data
        assert "emhass_deferrables_schedule" in sensor_data
        assert "emhass_status" in sensor_data
        assert "per_trip_emhass_params" in sensor_data

        # Verify actual data quality (THIS IS THE UNIQUE CONTRIBUTION)
        power_profile = sensor_data["emhass_power_profile"]
        assert isinstance(power_profile, list), "emhass_power_profile must be a list"
        assert len(power_profile) > 0, "emhass_power_profile must not be empty"

        # The most important check: non-zero values exist
        has_charging_hours = any(v > 0 for v in power_profile)
        assert has_charging_hours, (
            "emhass_power_profile must have at least one hour with charging power (>0W). "
            "Without this, the EMHASS optimization has no deferrable load schedule to work with."
        )

        print(f"Sensor data verification: power_profile has {len(power_profile)} hours, "
              f"{sum(1 for v in power_profile if v > 0)} with charging power")
