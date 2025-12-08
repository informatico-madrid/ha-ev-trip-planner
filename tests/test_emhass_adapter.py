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