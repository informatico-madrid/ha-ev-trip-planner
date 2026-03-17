"""Tests for EMHASSAdapter class."""

import pytest
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from unittest.mock import patch, AsyncMock, MagicMock

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.const import (
    CONF_VEHICLE_NAME,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_CHARGING_POWER,
    CONF_NOTIFICATION_SERVICE,
)


@pytest.mark.asyncio
async def test_adapter_instantiation(hass: HomeAssistant, mock_store):
    """Test adapter can be created with valid config."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }
    
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        assert adapter.vehicle_id == "test_vehicle"
        assert adapter.max_deferrable_loads == 50
        assert adapter.charging_power == 7.4
        assert len(adapter._available_indices) == 50  # All indices available initially


@pytest.mark.asyncio
async def test_load_index_mappings(hass: HomeAssistant, mock_store):
    """Test loading existing index mappings from storage."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }
    
    # Pre-populate storage with existing mappings
    mock_store.async_load = AsyncMock(return_value={
        "index_map": {"trip_001": 0, "trip_002": 1},
        "vehicle_id": "test_vehicle",
    })
    
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        
        # Execute: Load from storage
        await adapter.async_load()
        
        # Verify: Index map restored, available indices calculated correctly
        assert adapter.get_assigned_index("trip_001") == 0
        assert adapter.get_assigned_index("trip_002") == 1
        assert len(adapter._available_indices) == 48  # 50 - 2 used
        assert 0 not in adapter._available_indices
        assert 1 not in adapter._available_indices
        assert 2 in adapter._available_indices


@pytest.mark.asyncio
async def test_assign_index_to_trip(hass: HomeAssistant, mock_store):
    """Test dynamic index assignment."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }
    
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        
        # Assign first index
        index1 = await adapter.async_assign_index_to_trip("trip_001")
        assert index1 == 0
        assert len(adapter._available_indices) == 49
        
        # Assign second index
        index2 = await adapter.async_assign_index_to_trip("trip_002")
        assert index2 == 1
        assert len(adapter._available_indices) == 48
        
        # Reassign same trip (should return same index)
        index1_again = await adapter.async_assign_index_to_trip("trip_001")
        assert index1_again == index1
        assert len(adapter._available_indices) == 48  # No change


@pytest.mark.asyncio
async def test_assign_index_no_available(hass: HomeAssistant, mock_store, caplog):
    """Test behavior when no indices available."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 3,  # Small number for testing
        CONF_CHARGING_POWER: 7.4,
    }
    
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        
        # Use up all indices
        for i in range(3):
            await adapter.async_assign_index_to_trip(f"trip_{i:03d}")
        
        # Try to assign one more
        index = await adapter.async_assign_index_to_trip("trip_003")
        assert index is None
        assert "No available EMHASS indices" in caplog.text


@pytest.mark.asyncio
async def test_release_trip_index(hass: HomeAssistant, mock_store):
    """Test releasing an index when trip deleted."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }
    
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        
        # Setup: Assign index to trip
        index = await adapter.async_assign_index_to_trip("trip_001")
        assert index == 0
        assert len(adapter._available_indices) == 49
        
        # Release index
        result = await adapter.async_release_trip_index("trip_001")
        assert result is True
        assert len(adapter._available_indices) == 50
        assert 0 in adapter._available_indices
        
        # Verify trip no longer in map
        assert adapter.get_assigned_index("trip_001") is None


@pytest.mark.asyncio
async def test_publish_single_trip(hass: HomeAssistant, mock_store):
    """Test publishing a single trip with dynamic index."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }
    
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        
        # Create test trip
        trip = {
            "id": "trip_001",
            "kwh": 3.6,
            "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
            "descripcion": "Work commute",
        }
        
        # Publish
        result = await adapter.async_publish_deferrable_load(trip)
        
        # Verify
        assert result is True
        index = adapter.get_assigned_index("trip_001")
        assert index is not None
        assert index >= 0
        
        # Verify sensor created
        sensor_id = f"sensor.emhass_deferrable_load_config_{index}"
        state = hass.states.get(sensor_id)
        assert state is not None
        assert state.state == "active"
        assert state.attributes["trip_id"] == "trip_001"
        assert state.attributes["kwh_needed"] == 3.6
        assert state.attributes["vehicle_id"] == "test_vehicle"
        assert state.attributes["emhass_index"] == index


@pytest.mark.asyncio
async def test_publish_multiple_trips_dynamic_indices(hass: HomeAssistant, mock_store):
    """Test publishing multiple trips, each gets unique index."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }
    
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        
        # Create multiple trips
        trips = [
            {
                "id": f"trip_{i:03d}",
                "kwh": 3.0 + i,
                "datetime": (datetime.now() + timedelta(hours=8+i)).isoformat(),
                "descripcion": f"Trip {i}",
            }
            for i in range(5)
        ]
        
        # Publish all
        result = await adapter.async_publish_all_deferrable_loads(trips)
        assert result is True
        
        # Verify each trip has unique index
        assigned_indices = []
        for trip in trips:
            index = adapter.get_assigned_index(trip["id"])
            assert index is not None
            assert index not in assigned_indices  # Unique
            assigned_indices.append(index)
            
            # Verify sensor created
            sensor_id = f"sensor.emhass_deferrable_load_config_{index}"
            state = hass.states.get(sensor_id)
            assert state is not None
            assert state.state == "active"
            assert state.attributes["trip_id"] == trip["id"]
        
        # Verify all indices are unique
        assert len(assigned_indices) == len(set(assigned_indices))


@pytest.mark.asyncio
async def test_publish_trip_past_deadline(hass: HomeAssistant, mock_store, caplog):
    """Test publishing trip with deadline in past."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }
    
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        
        # Create trip with deadline < now
        trip = {
            "id": "trip_old",
            "kwh": 3.6,
            "datetime": (datetime.now() - timedelta(hours=1)).isoformat(),
        }
        
        # Publish
        result = await adapter.async_publish_deferrable_load(trip)
        
        # Verify
        assert result is False
        assert "deadline in past" in caplog.text
        # Index should be released
        assert adapter.get_assigned_index("trip_old") is None


@pytest.mark.asyncio
async def test_remove_deferrable_load(hass: HomeAssistant, mock_store):
    """Test removing deferrable load and releasing index."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }
    
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        
        # Setup: Publish trip
        trip = {
            "id": "trip_001",
            "kwh": 3.6,
            "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
        }
        await adapter.async_publish_deferrable_load(trip)
        index = adapter.get_assigned_index("trip_001")
        assert index is not None
        
        # Remove
        result = await adapter.async_remove_deferrable_load("trip_001")
        assert result is True
        
        # Verify index released
        assert adapter.get_assigned_index("trip_001") is None
        assert index in adapter._available_indices
        
        # Verify sensor cleared
        sensor_id = f"sensor.emhass_deferrable_load_config_{index}"
        state = hass.states.get(sensor_id)
        assert state.state == "idle"
        assert state.attributes == {}


@pytest.mark.asyncio
async def test_index_persistence(hass: HomeAssistant, mock_store):
    """Test that index mappings persist across restarts."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }
    
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        
        # Setup: Assign some indices
        await adapter.async_assign_index_to_trip("trip_001")
        await adapter.async_assign_index_to_trip("trip_002")
        
        # Save
        await adapter.async_save()
        
        # Create new adapter instance (simulating restart)
        adapter2 = EMHASSAdapter(hass, config)
        await adapter2.async_load()
        
        # Verify mappings restored
        assert adapter2.get_assigned_index("trip_001") == 0
        assert adapter2.get_assigned_index("trip_002") == 1
        assert len(adapter2._available_indices) == 48  # 50 - 2 used


@pytest.mark.asyncio
async def test_update_deferrable_load(hass: HomeAssistant, mock_store):
    """Test updating existing deferrable load."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }
    
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()
        
        # Create and publish initial trip
        trip = {
            "id": "trip_001",
            "kwh": 3.6,
            "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
            "descripcion": "Initial",
        }
        await adapter.async_publish_deferrable_load(trip)
        
        # Update trip with new parameters
        updated_trip = {
            "id": "trip_001",
            "kwh": 5.0,  # Increased kWh
            "datetime": (datetime.now() + timedelta(hours=10)).isoformat(),  # Later deadline
            "descripcion": "Updated",
        }
        
        # Update
        result = await adapter.async_update_deferrable_load(updated_trip)
        assert result is True
        
        # Verify sensor updated
        index = adapter.get_assigned_index("trip_001")
        sensor_id = f"sensor.emhass_deferrable_load_config_{index}"
        state = hass.states.get(sensor_id)
        assert state.attributes["kwh_needed"] == 5.0
        assert state.attributes["trip_description"] == "Updated"


def test_calculate_deferrable_parameters_basic():
    """Test basic deferrable parameter calculation."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    hass = MagicMock()

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store'):
        adapter = EMHASSAdapter(hass, config)

    trip = {
        "id": "trip_001",
        "kwh": 7.5,
        "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
    }

    params = adapter.calculate_deferrable_parameters(trip, 7.4)

    assert params["total_energy_kwh"] == 7.5
    assert params["power_watts"] == 7400.0
    assert params["total_hours"] == pytest.approx(1.01, rel=0.1)
    assert params["start_timestep"] == 0
    assert params["is_single_constant"] is True


def test_calculate_deferrable_parameters_no_kwh():
    """Test calculation with zero kWh."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    hass = MagicMock()

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store'):
        adapter = EMHASSAdapter(hass, config)

    trip = {
        "id": "trip_001",
        "kwh": 0,
    }

    params = adapter.calculate_deferrable_parameters(trip, 7.4)

    assert params == {}


def test_calculate_deferrable_parameters_no_deadline():
    """Test calculation with no deadline."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    hass = MagicMock()

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store'):
        adapter = EMHASSAdapter(hass, config)

    trip = {
        "id": "trip_001",
        "kwh": 7.2,
    }

    params = adapter.calculate_deferrable_parameters(trip, 3.6)

    assert params["total_energy_kwh"] == 7.2
    assert params["power_watts"] == 3600.0
    assert params["end_timestep"] == 24  # Default


def test_calculate_power_profile_from_trips():
    """Test power profile calculation from trips."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    hass = MagicMock()

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store'):
        adapter = EMHASSAdapter(hass, config)

    trips = [
        {
            "id": "trip_001",
            "kwh": 7.4,
            "datetime": (datetime.now() + timedelta(hours=6)).isoformat(),
        }
    ]

    # Calculate with 7 days (168 hours)
    profile = adapter._calculate_power_profile_from_trips(trips, 7.4, 168)

    assert len(profile) == 168
    # First hours should be 0 until charging starts
    assert profile[0] == 0.0
    # Hours before deadline should have positive charging power
    # At 6 hours from now, charging should be at hours 0-5 (6 hours of 7.4kW)
    assert any(p > 0 for p in profile)
    assert all(p == 0.0 or p == 7400.0 for p in profile)


def test_calculate_power_profile_zero_kwh():
    """Test power profile with zero kWh trip."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    hass = MagicMock()

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store'):
        adapter = EMHASSAdapter(hass, config)

    trips = [
        {
            "id": "trip_001",
            "kwh": 0,
            "datetime": (datetime.now() + timedelta(hours=6)).isoformat(),
        }
    ]

    profile = adapter._calculate_power_profile_from_trips(trips, 7.4, 168)

    assert len(profile) == 168
    # All zeros when no kWh
    assert all(p == 0.0 for p in profile)


def test_generate_schedule_from_trips():
    """Test schedule generation from trips."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    hass = MagicMock()

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store'):
        adapter = EMHASSAdapter(hass, config)

    trips = [
        {
            "id": "trip_001",
            "kwh": 7.4,
            "datetime": (datetime.now() + timedelta(hours=6)).isoformat(),
        }
    ]

    schedule = adapter._generate_schedule_from_trips(trips, 7.4)

    assert len(schedule) == 168
    for entry in schedule:
        assert "date" in entry
        assert "p_deferrable0" in entry
        # Should have either "0.0" or positive value
        val = float(entry["p_deferrable0"])
        assert val >= 0


@pytest.mark.asyncio
async def test_publish_deferrable_loads(hass: HomeAssistant, mock_store):
    """Test publishing multiple deferrable loads."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        trips = [
            {
                "id": "trip_001",
                "kwh": 3.6,
                "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
                "descripcion": "Morning trip",
            },
            {
                "id": "trip_002",
                "kwh": 5.0,
                "datetime": (datetime.now() + timedelta(hours=12)).isoformat(),
                "descripcion": "Evening trip",
            },
        ]

        result = await adapter.publish_deferrable_loads(trips, 7.4)

        assert result is True

        # Verify template sensor created
        sensor_id = "sensor.emhass_perfil_diferible_test_vehicle"
        state = hass.states.get(sensor_id)
        assert state is not None
        assert state.state == "ready"
        assert "power_profile_watts" in state.attributes
        assert "deferrables_schedule" in state.attributes
        assert state.attributes["trips_count"] == 2

        # Verify individual trip sensors created
        for trip in trips:
            index = adapter.get_assigned_index(trip["id"])
            assert index is not None
            trip_sensor = hass.states.get(f"sensor.emhass_deferrable_load_config_{index}")
            assert trip_sensor is not None
            assert trip_sensor.state == "active"


@pytest.mark.asyncio
async def test_publish_deferrable_loads_default_power(hass: HomeAssistant, mock_store):
    """Test publishing with default charging power."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        trips = [
            {
                "id": "trip_001",
                "kwh": 3.6,
                "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
            }
        ]

        # Don't specify charging power, should use default
        result = await adapter.publish_deferrable_loads(trips)

        assert result is True

        # Verify template sensor created with default power
        sensor_id = "sensor.emhass_perfil_diferible_test_vehicle"
        state = hass.states.get(sensor_id)
        assert state is not None
        profile = state.attributes["power_profile_watts"]
        assert any(p > 0 for p in profile)


@pytest.mark.asyncio
async def test_verify_shell_command_integration_no_sensor(hass: HomeAssistant, mock_store):
    """Test shell command verification when deferrable sensor doesn't exist."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        result = await adapter.async_verify_shell_command_integration()

        assert result["deferrable_sensor_exists"] is False
        assert "not found" in result["errors"][0]
        assert result["is_configured"] is False


@pytest.mark.asyncio
async def test_verify_shell_command_integration_with_sensor(hass: HomeAssistant, mock_store):
    """Test shell command verification when deferrable sensor exists with data."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # First publish trips to create the sensor
        trips = [
            {
                "id": "trip_001",
                "kwh": 3.6,
                "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
            }
        ]
        await adapter.publish_deferrable_loads(trips, 7.4)

        # Now verify
        result = await adapter.async_verify_shell_command_integration()

        assert result["deferrable_sensor_exists"] is True
        assert result["deferrable_sensor_has_data"] is True


@pytest.mark.asyncio
async def test_verify_shell_command_integration_no_emhass_sensors(hass: HomeAssistant, mock_store):
    """Test shell command verification when EMHASS response sensors missing."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Publish trips
        trips = [
            {
                "id": "trip_001",
                "kwh": 3.6,
                "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
            }
        ]
        await adapter.publish_deferrable_loads(trips, 7.4)

        # Verify - no EMHASS sensors configured yet
        result = await adapter.async_verify_shell_command_integration()

        assert result["deferrable_sensor_exists"] is True
        assert result["deferrable_sensor_has_data"] is True
        assert result["is_configured"] is False
        assert len(result["emhass_response_sensors"]) == 0
        assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_check_emhass_response_sensors_all_verified(hass: HomeAssistant, mock_store):
    """Test checking EMHASS response sensors when all trips are verified."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Publish trips to create sensors
        trips = [
            {
                "id": "trip_001",
                "kwh": 3.6,
                "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
            }
        ]
        await adapter.publish_deferrable_loads(trips, 7.4)

        # Check response sensors
        result = await adapter.async_check_emhass_response_sensors()

        # Our own config sensors should be found
        assert "trip_001" in result["verified_trips"]
        assert len(result["missing_trips"]) == 0
        assert result["all_trips_verified"] is True


@pytest.mark.asyncio
async def test_check_emhass_response_sensors_with_trip_ids(hass: HomeAssistant, mock_store):
    """Test checking EMHASS response sensors with specific trip IDs."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Publish trips
        trips = [
            {
                "id": "trip_001",
                "kwh": 3.6,
                "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
            },
            {
                "id": "trip_002",
                "kwh": 5.0,
                "datetime": (datetime.now() + timedelta(hours=12)).isoformat(),
            },
        ]
        await adapter.publish_deferrable_loads(trips, 7.4)

        # Check specific trips
        result = await adapter.async_check_emhass_response_sensors(trip_ids=["trip_001"])

        assert "trip_001" in result["verified_trips"]
        assert result["all_trips_verified"] is True


@pytest.mark.asyncio
async def test_check_emhass_response_sensors_no_trips(hass: HomeAssistant, mock_store):
    """Test checking EMHASS response sensors with no trips."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        result = await adapter.async_check_emhass_response_sensors()

        assert result["all_trips_verified"] is True
        assert len(result["verified_trips"]) == 0


@pytest.mark.asyncio
async def test_get_integration_status_ok(hass: HomeAssistant, mock_store):
    """Test getting integration status when everything is working."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Publish trips
        trips = [
            {
                "id": "trip_001",
                "kwh": 3.6,
                "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
            }
        ]
        await adapter.publish_deferrable_loads(trips, 7.4)

        # Get status
        status = await adapter.async_get_integration_status()

        assert status["vehicle_id"] == "test_vehicle"
        assert "verification" in status["details"]
        assert "response_check" in status["details"]


@pytest.mark.asyncio
async def test_get_integration_status_no_sensor(hass: HomeAssistant, mock_store):
    """Test getting integration status when sensor doesn't exist."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Get status without publishing trips
        status = await adapter.async_get_integration_status()

        assert status["status"] == "error"
        assert "not found" in status["message"]


@pytest.mark.asyncio
async def test_notify_error_with_notification_service(hass: HomeAssistant, mock_store):
    """Test error notification with notification service configured."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_NOTIFICATION_SERVICE: "notify.notify",
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Send error notification
        await adapter.async_notify_error(
            error_type="emhass_unavailable",
            message="Test error message",
            trip_id="trip_001",
        )

        # Should update error status sensor
        sensor_id = f"sensor.emhass_perfil_diferible_{adapter.vehicle_id}"
        state = hass.states.get(sensor_id)
        assert state is not None
        assert state.state == "error"
        assert state.attributes.get("error_type") == "emhass_unavailable"
        assert state.attributes.get("error_message") == "Test error message"
        assert state.attributes.get("error_trip_id") == "trip_001"


@pytest.mark.asyncio
async def test_notify_error_without_notification_service(hass: HomeAssistant, mock_store):
    """Test error notification without notification service."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        # No notification service
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Send error notification
        await adapter.async_notify_error(
            error_type="sensor_missing",
            message="Test error message",
        )

        # Should still update error status sensor
        sensor_id = f"sensor.emhass_perfil_diferible_{adapter.vehicle_id}"
        state = hass.states.get(sensor_id)
        assert state is not None
        assert state.state == "error"


@pytest.mark.asyncio
async def test_handle_emhass_unavailable(hass: HomeAssistant, mock_store):
    """Test handling EMHASS unavailable error."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Handle unavailable
        await adapter.async_handle_emhass_unavailable(
            reason="Connection refused",
            trip_id="trip_001",
        )

        # Check error stored
        last_error = adapter.get_last_error()
        assert last_error is not None
        assert "Connection refused" in last_error["message"]

        # Verify sensor has trip_id in attributes
        sensor_id = f"sensor.emhass_perfil_diferible_{adapter.vehicle_id}"
        state = hass.states.get(sensor_id)
        assert state is not None
        assert state.attributes.get("error_trip_id") == "trip_001"


@pytest.mark.asyncio
async def test_handle_shell_command_failure(hass: HomeAssistant, mock_store):
    """Test handling shell command failure."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Handle shell command failure
        await adapter.async_handle_shell_command_failure(trip_id="trip_001")

        # Check error stored
        last_error = adapter.get_last_error()
        assert last_error is not None
        assert "shell command" in last_error["message"].lower()


@pytest.mark.asyncio
async def test_clear_error(hass: HomeAssistant, mock_store):
    """Test clearing error status."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # First set an error
        await adapter.async_notify_error(
            error_type="test_error",
            message="Test error",
        )

        # Verify error is set
        assert adapter.get_last_error() is not None

        # Clear error
        await adapter.async_clear_error()

        # Verify error is cleared
        assert adapter.get_last_error() is None


@pytest.mark.asyncio
async def test_get_last_error_no_error(hass: HomeAssistant, mock_store):
    """Test getting last error when no error occurred."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # No error set
        last_error = adapter.get_last_error()
        assert last_error is None


@pytest.mark.asyncio
async def test_error_notification_includes_trip_info(hass: HomeAssistant, mock_store):
    """Test that error notification includes trip info when provided."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Set error with trip ID
        await adapter.async_handle_emhass_unavailable(
            reason="API timeout",
            trip_id="trip_001",
        )

        # Verify trip ID is in sensor attributes
        sensor_id = f"sensor.emhass_perfil_diferible_{adapter.vehicle_id}"
        state = hass.states.get(sensor_id)
        assert state is not None
        assert state.attributes.get("error_trip_id") == "trip_001"


@pytest.mark.asyncio
async def test_adapter_with_notification_service_config(hass: HomeAssistant, mock_store):
    """Test adapter initialization with notification service."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_NOTIFICATION_SERVICE: "notify.mobile",
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)

        assert adapter.notification_service == "notify.mobile"


@pytest.mark.asyncio
async def test_async_handle_sensor_error(hass: HomeAssistant, mock_store):
    """Test handling sensor errors."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Handle sensor error
        await adapter.async_handle_sensor_error(
            sensor_id="sensor.emhass_perfil_diferible_test",
            error_details="Sensor not found",
            trip_id="trip_001",
        )

        # Check error stored
        last_error = adapter.get_last_error()
        assert last_error is not None
        assert "Sensor not found" in last_error["message"]
        assert "sensor.emhass_perfil_diferible_test" in last_error["message"]