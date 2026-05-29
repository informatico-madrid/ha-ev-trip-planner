"""Integration test: EMHASS sensor must have all required deferrable attributes.

This test verifies that when a trip is published, the EMHASS sensor entity
has all the required attributes for EMHASS to consume:
- number_of_deferrable_loads
- def_total_hours_array
- p_deferrable_nom_array
- def_start_timestep_array
- def_end_timestep_array

BUG: Currently the sensor only has power_profile_watts attribute,
missing the 5 deferrable array attributes.
"""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

# Required attributes for EMHASS sensor
REQUIRED_EMHASS_ATTRIBUTES = [
    "number_of_deferrable_loads",
    "def_total_hours_array",
    "p_deferrable_nom_array",
    "def_start_timestep_array",
    "def_end_timestep_array",
]


def mock_logger():
    """Create a mock logger for DataUpdateCoordinator."""
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def mock_hass():
    """Create mock HomeAssistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create mock ConfigEntry with vehicle data."""
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    entry.data = {
        "vehicle_name": "mi_ev",
        "battery_capacity_kwh": 28.0,
        "kwh_per_km": 0.18,
        "safety_margin_percent": 20.0,
        "charging_power_kw": 3.4,
    }
    entry.options = {"charging_power_kw": 3.4}
    return entry


@pytest.fixture
def mock_trip_manager():
    """Create mock TripManager with one active trip."""
    tm = MagicMock()
    tm.vehicle_id = "mi_ev"

    # Mock trip manager methods
    tm._crud.async_get_recurring_trips = AsyncMock(return_value=[])
    tm._crud.async_get_punctual_trips = AsyncMock(return_value=[])
    tm._soc_query.async_get_kwh_needed_today = AsyncMock(return_value=5.0)
    tm._soc_query.async_get_hours_needed_today = AsyncMock(return_value=2.0)
    tm._navigator.async_get_next_trip = AsyncMock(return_value=None)

    return tm


@pytest.fixture
def mock_emhass_adapter():
    """Create a mock EMHASS adapter with cached data."""
    from custom_components.ev_trip_planner.const import EMHASS_STATE_READY

    mock = MagicMock()
    mock.get_cached_optimization_results.return_value = {
        "emhass_power_profile": [3600.0] * 24,
        "emhass_deferrables_schedule": [],
        "emhass_status": EMHASS_STATE_READY,
        "per_trip_emhass_params": {},
    }
    return mock


@pytest.fixture
def mock_coordinator(hass, mock_config_entry, mock_trip_manager, mock_emhass_adapter):
    """Create a mock coordinator for testing."""
    from custom_components.ev_trip_planner.coordinator import (
        CoordinatorConfig,
        TripPlannerCoordinator,
    )

    config = CoordinatorConfig(emhass_adapter=mock_emhass_adapter)
    coordinator = TripPlannerCoordinator(
        hass, mock_config_entry, mock_trip_manager, config
    )
    return coordinator


def test_emhass_sensor_has_all_required_attributes(mock_coordinator, mock_config_entry):
    """Test that EMHASS sensor has all required deferrable attributes.

    When coordinator provides per_trip_emhass_params, the sensor entity should
    have ALL of these attributes:
    - number_of_deferrable_loads
    - def_total_hours_array
    - p_deferrable_nom_array
    - def_start_timestep_array
    - def_end_timestep_array

    Currently this test FAILS because only power_profile_watts is populated.
    """
    from custom_components.ev_trip_planner.sensor.entity_emhass_deferrable import (
        EmhassDeferrableLoadSensor,
    )

    # Create sensor with coordinator that has mock EMHASS data
    sensor = EmhassDeferrableLoadSensor(mock_coordinator, mock_config_entry.entry_id)

    # Simulate coordinator.data with per_trip_emhass_params containing a trip
    mock_coordinator.data = {
        "hours_today": 2.0,
        "next_trip": {"id": "trip_001", "tipo": "recurrente", "activo": True},
        "emhass_power_profile": [3600.0] * 24,
        "emhass_deferrables_schedule": [],
        "emhass_status": "ready",
        "per_trip_emhass_params": {
            "trip_001": {
                "emhass_index": 0,
                "def_start_timestep": 8,
                "def_end_timestep": 10,
                "def_total_hours": 2,
                "total_hours": 2,
                "power_watts": 3400.0,
                "kwh_needed": 6.8,
                "activo": True,
                "p_deferrable_nom_array": [3400.0],
                "def_total_hours_array": [2],
                "def_start_timestep_array": [8],
                "def_end_timestep_array": [10],
            }
        },
    }

    # Force sensor to update by accessing extra_state_attributes
    attrs = sensor.extra_state_attributes

    # Debug: Print what attributes we have
    print("\n=== DEBUG: Sensor attributes ===")
    print(f"Available attributes: {list(attrs.keys())}")
    print(f"number_of_deferrable_loads: {attrs.get('number_of_deferrable_loads')}")
    print(f"def_total_hours_array: {attrs.get('def_total_hours_array')}")
    print(f"p_deferrable_nom_array: {attrs.get('p_deferrable_nom_array')}")
    print(f"def_start_timestep_array: {attrs.get('def_start_timestep_array')}")
    print(f"def_end_timestep_array: {attrs.get('def_end_timestep_array')}")
    print(f"power_profile_watts: {attrs.get('power_profile_watts')}")
    print("=== END DEBUG ===\n")

    # Assert: All required EMHASS attributes must be present
    missing_attrs = []
    for attr in REQUIRED_EMHASS_ATTRIBUTES:
        if attr not in attrs:
            missing_attrs.append(attr)

    # This assertion will FAIL - that's expected until the bug is fixed
    assert len(missing_attrs) == 0, (
        f"EMHASS sensor is missing required attributes: {missing_attrs}. "
        f"Current attributes: {list(attrs.keys())}"
    )
