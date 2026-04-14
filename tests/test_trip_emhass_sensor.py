"""Tests for TripEmhassSensor class."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_VEHICLE_NAME,
)
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter


@pytest.mark.asyncio
async def test_trip_emhass_sensor_native_value(mock_store, hass: HomeAssistant):
    """TripEmhassSensor.native_value returns emhass_index from per_trip_emhass_params.

    This is the RED test for task 1.23:
    - Create stub coordinator.data with per_trip_emhass_params
    - Trip has emhass_index=2
    - Sensor.native_value should return 2
    - Current: TripEmhassSensor class does not exist yet
    - Test must FAIL to confirm the feature doesn't exist
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Mock coordinator.async_refresh
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh = AsyncMock()
        adapter._get_coordinator = MagicMock(return_value=mock_coordinator)

        # Mock async_publish_deferrable_load
        adapter.async_publish_deferrable_load = AsyncMock(return_value=True)

        # Mock _update_error_status
        adapter._update_error_status = MagicMock()

        # Mock _index_map
        adapter._index_map = {"trip_001": 2}

        # Publish the trip (use "id" key to match production API)
        trip = {
            "id": "trip_001",
            "kwh": 7.4,
            "hora": "09:00",
            "datetime": datetime(2026, 4, 11, 20, 0, 0).isoformat(),
        }
        await adapter.publish_deferrable_loads([trip])

        # Get cached results (this is what coordinator.data will have)
        cached_results = adapter.get_cached_optimization_results()

        # Create mock coordinator with this data
        mock_coordinator = MagicMock()
        mock_coordinator.data = cached_results

        # Import and create the sensor (this should fail because class doesn't exist)
        from custom_components.ev_trip_planner.sensor import TripEmhassSensor

        sensor = TripEmhassSensor(mock_coordinator, "test_vehicle", "trip_001")

        # This should return the emhass_index from per_trip_emhass_params
        assert sensor.native_value == 2, (
            f"Sensor native_value should be emhass_index=2, got {sensor.native_value}"
        )


@pytest.mark.asyncio
async def test_trip_emhass_sensor_attributes_all_9(mock_store, hass: HomeAssistant):
    """TripEmhassSensor.extra_state_attributes returns all 9 attributes.

    This is the RED test for task 1.25:
    - Create sensor with full per_trip_emhass_params dict
    - Assert extra_state_attributes has all 9 keys
    - Current: TripEmhassSensor doesn't have extra_state_attributes
    - Test must FAIL to confirm the feature doesn't exist
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Mock coordinator.async_refresh
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh = AsyncMock()
        adapter._get_coordinator = MagicMock(return_value=mock_coordinator)

        # Mock async_publish_deferrable_load
        adapter.async_publish_deferrable_load = AsyncMock(return_value=True)

        # Mock _update_error_status
        adapter._update_error_status = MagicMock()

        # Mock _index_map
        adapter._index_map = {"trip_001": 2}

        # Publish the trip (use "id" key to match production API)
        trip = {
            "id": "trip_001",
            "kwh": 7.4,
            "hora": "09:00",
            "datetime": datetime(2026, 4, 11, 20, 0, 0).isoformat(),
        }
        await adapter.publish_deferrable_loads([trip])

        # Get cached results (this is what coordinator.data will have)
        cached_results = adapter.get_cached_optimization_results()

        # Create mock coordinator with this data
        mock_coordinator.data = cached_results

        # Import and create the sensor
        from custom_components.ev_trip_planner.sensor import TripEmhassSensor

        sensor = TripEmhassSensor(mock_coordinator, "test_vehicle", "trip_001")

        # Get attributes (this will fail because extra_state_attributes doesn't exist yet)
        attrs = sensor.extra_state_attributes

        # Verify all 9 expected keys are present
        expected_keys = {
            "def_total_hours",
            "P_deferrable_nom",
            "def_start_timestep",
            "def_end_timestep",
            "power_profile_watts",
            "trip_id",
            "emhass_index",
            "kwh_needed",
            "deadline",
        }
        actual_keys = set(attrs.keys())
        # Assert EXACTLY 9 keys — no extra keys allowed (data leak prevention)
        assert actual_keys == expected_keys, (
            f"extra_state_attributes must have EXACTLY 9 keys, no more. "
            f"Expected: {expected_keys}, Got: {actual_keys}. "
            f"Extra keys detected: {actual_keys - expected_keys}"
        )


@pytest.mark.asyncio
async def test_trip_emhass_sensor_zeroed(mock_store, hass: HomeAssistant):
    """TripEmhassSensor returns zeroed attrs when trip not found.

    This is the RED test for task 1.27:
    - Create sensor with non-existent trip_id
    - Assert extra_state_attributes returns zeroed values
    - Current: _get_params() may return None/empty, _zeroed_attributes() not called
    - Test must FAIL to confirm the feature doesn't work yet
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Mock coordinator.async_refresh
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh = AsyncMock()
        adapter._get_coordinator = MagicMock(return_value=mock_coordinator)

        # Mock async_publish_deferrable_load
        adapter.async_publish_deferrable_load = AsyncMock(return_value=True)

        # Mock _update_error_status
        adapter._update_error_status = MagicMock()

        # Mock _index_map
        adapter._index_map = {"trip_001": 2}

        # Publish the trip (use "id" key to match production API)
        trip = {
            "id": "trip_001",
            "kwh": 7.4,
            "hora": "09:00",
            "datetime": datetime(2026, 4, 11, 20, 0, 0).isoformat(),
        }
        await adapter.publish_deferrable_loads([trip])

        # Get cached results (this is what coordinator.data will have)
        cached_results = adapter.get_cached_optimization_results()

        # Create mock coordinator with this data
        mock_coordinator.data = cached_results

        # Import and create sensor for NON-EXISTENT trip
        from custom_components.ev_trip_planner.sensor import TripEmhassSensor

        sensor = TripEmhassSensor(mock_coordinator, "test_vehicle", "nonexistent_trip")

        # Get attributes
        attrs = sensor.extra_state_attributes

        # Verify zeroed values
        assert attrs["emhass_index"] == -1, (
            f"emhass_index should be -1, got {attrs['emhass_index']}"
        )
        assert attrs["kwh_needed"] == 0.0, (
            f"kwh_needed should be 0.0, got {attrs['kwh_needed']}"
        )
        assert attrs["power_profile_watts"] == [], (
            f"power_profile_watts should be [], got {attrs['power_profile_watts']}"
        )


@pytest.mark.asyncio
async def test_trip_emhass_sensor_device_info(mock_store, hass: HomeAssistant):
    """TripEmhassSensor.device_info uses vehicle_id identifiers.

    This is the RED test for task 1.29:
    - Create sensor with vehicle_id="test_vehicle"
    - Assert device_info.identifiers={(DOMAIN, vehicle_id)}
    - Current: device_info not yet implemented
    - Test must FAIL to confirm the feature doesn't exist
    """

    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Mock coordinator.async_refresh
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh = AsyncMock()
        adapter._get_coordinator = MagicMock(return_value=mock_coordinator)

        # Mock async_publish_deferrable_load
        adapter.async_publish_deferrable_load = AsyncMock(return_value=True)

        # Mock _update_error_status
        adapter._update_error_status = MagicMock()

        # Mock _index_map
        adapter._index_map = {"trip_001": 2}

        # Publish the trip (use "id" key to match production API)
        trip = {
            "id": "trip_001",
            "kwh": 7.4,
            "hora": "09:00",
            "datetime": datetime(2026, 4, 11, 20, 0, 0).isoformat(),
        }
        await adapter.publish_deferrable_loads([trip])

        # Get cached results (this is what coordinator.data will have)
        cached_results = adapter.get_cached_optimization_results()

        # Create mock coordinator with this data
        mock_coordinator.data = cached_results

        # Import and create the sensor
        from custom_components.ev_trip_planner.const import DOMAIN
        from custom_components.ev_trip_planner.sensor import TripEmhassSensor

        sensor = TripEmhassSensor(mock_coordinator, "test_vehicle", "trip_001")

        # This should return device_info with identifiers={(DOMAIN, vehicle_id)}
        device_info = sensor.device_info
        assert device_info is not None, "device_info should not be None"

        identifiers = device_info.get("identifiers")
        assert identifiers is not None, "identifiers should not be None"

        # Check that identifiers contains (DOMAIN, vehicle_id)
        assert (DOMAIN, "test_vehicle") in identifiers, (
            f"identifiers should contain {(DOMAIN, 'test_vehicle')}, got {identifiers}"
        )


@pytest.mark.asyncio
async def test_create_trip_emhass_sensor_no_entry(mock_store, hass: HomeAssistant):
    """async_create_trip_emhass_sensor returns False when entry not found.

    This is the RED test for task 1.33:
    - Call async_create_trip_emhass_sensor with non-existent entry_id
    - Assert returns False
    - Assert callback NOT called
    - Current: Function exists with entry lookup guard (task 1.32)
    - Test should PASS if guard is implemented
    """
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator

    # Create mock coordinator
    mock_coordinator = MagicMock(spec=TripPlannerCoordinator)
    mock_coordinator.data = {
        "per_trip_emhass_params": {
            "trip_001": {
                "emhass_index": 2,
                "kwh_needed": 7.4,
            }
        }
    }

    # Create mock runtime_data with async_add_entities callback
    mock_add_entities = AsyncMock()
    mock_runtime_data = MagicMock()
    mock_runtime_data.sensor_async_add_entities = mock_add_entities

    # Mock ConfigEntry
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    mock_entry.data = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }
    mock_entry.runtime_data = mock_runtime_data

    # Patch async_get_entry to return None (entry not found)
    with patch.object(hass.config_entries, "async_get_entry", return_value=None):
        # Import and call the function
        from custom_components.ev_trip_planner.sensor import async_create_trip_emhass_sensor

        result = await async_create_trip_emhass_sensor(
            hass, "nonexistent_entry", mock_coordinator, "test_vehicle", "trip_001"
        )

        # Assert callback was NOT called
        mock_add_entities.assert_not_called()

        # Assert function returns False
        assert result is False, (
            f"async_create_trip_emhass_sensor should return False when entry not found, got {result}"
        )


@pytest.mark.asyncio
async def test_create_trip_emhass_sensor_success(mock_store, hass: HomeAssistant):
    """async_create_trip_emhass_sensor calls async_add_entities with TripEmhassSensor.

    This is the RED test for task 1.31:
    - Create mock runtime_data with sensor_async_add_entities callback
    - Call async_create_trip_emhass_sensor
    - Assert callback called with list containing TripEmhassSensor instance
    - Assert function returns True
    - Current: async_create_trip_emhass_sensor function does not exist yet
    - Test must FAIL to confirm the feature doesn't exist
    """
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator
    from custom_components.ev_trip_planner.sensor import TripEmhassSensor

    # Create mock coordinator
    mock_coordinator = MagicMock(spec=TripPlannerCoordinator)
    mock_coordinator.data = {
        "per_trip_emhass_params": {
            "trip_001": {
                "emhass_index": 2,
                "kwh_needed": 7.4,
            }
        }
    }

    # Create mock runtime_data with async_add_entities callback
    mock_add_entities = AsyncMock()
    mock_runtime_data = MagicMock()
    mock_runtime_data.sensor_async_add_entities = mock_add_entities

    # Mock ConfigEntry and entity_platform
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    mock_entry.data = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    # Set up entry.runtime_data for the function to access
    mock_entry.runtime_data = mock_runtime_data

    # Patch the config_entries.async_get_entry method on the hass object
    with patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry):
        # Import and call the function
        from custom_components.ev_trip_planner.sensor import async_create_trip_emhass_sensor

        result = await async_create_trip_emhass_sensor(
            hass, mock_entry.entry_id, mock_coordinator, "test_vehicle", "trip_001"
        )

        # Assert callback was called with TripEmhassSensor instance
        mock_add_entities.assert_called_once()
        args, _ = mock_add_entities.call_args
        sensors = args[0]

        # Assert list contains TripEmhassSensor instance
        assert len(sensors) == 1, (
            f"async_add_entities should be called with 1 sensor, got {len(sensors)}"
        )
        assert isinstance(sensors[0], TripEmhassSensor), (
            f"async_add_entities should be called with TripEmhassSensor instance, got {type(sensors[0])}"
        )

        # Assert function returns True
        assert result is True, (
            f"async_create_trip_emhass_sensor should return True, got {result}"
        )


@pytest.mark.asyncio
async def test_remove_trip_emhass_sensor_success(mock_store, hass: HomeAssistant):
    """async_remove_trip_emhass_sensor removes from entity registry.

    This is the RED test for task 1.35:
    - Create mock entity_registry with matching entry
    - Call async_remove_trip_emhass_sensor
    - Assert registry.async_remove called with correct entity_id
    - Assert returns True
    - Current: async_remove_trip_emhass_sensor function does not exist yet
    - Test must FAIL to confirm the feature doesn't exist
    """
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator

    # Create mock coordinator
    mock_coordinator = MagicMock(spec=TripPlannerCoordinator)
    mock_coordinator.data = {
        "per_trip_emhass_params": {
            "trip_001": {
                "emhass_index": 2,
                "kwh_needed": 7.4,
            }
        }
    }

    # Create mock entry in entity registry using a simple class
    class MockRegEntry:
        entity_id = "sensor.emhass_params_trip_001_test_entry"
        unique_id = "emhass_params_trip_001_test_entry"

    mock_reg_entry = MockRegEntry()

    mock_registry = MagicMock()
    mock_registry.async_remove = MagicMock(return_value=None)

    # Mock ConfigEntry
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    mock_entry.data = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry), \
         patch.object(hass, "entity_registry", mock_registry), \
         patch("custom_components.ev_trip_planner.sensor.async_entries_for_config_entry", return_value=[mock_reg_entry]):
        # Import and call the function
        from custom_components.ev_trip_planner.sensor import async_remove_trip_emhass_sensor

        result = await async_remove_trip_emhass_sensor(
            hass, mock_entry.entry_id, "test_vehicle", "trip_001"
        )

        # Assert async_remove was called
        mock_registry.async_remove.assert_called_once()
        assert result is True, (
            f"async_remove_trip_emhass_sensor should return True, got {result}"
        )


@pytest.mark.asyncio
async def test_remove_trip_emhass_sensor_no_entry(mock_store, hass: HomeAssistant):
    """async_remove_trip_emhass_sensor returns False when sensor not found.

    This is the RED test for task 1.37:
    - Call async_remove_trip_emhass_sensor for non-existent sensor
    - Assert returns False
    - Current: Function may not exist or may not handle not-found case
    - Test should PASS if error handling implemented
    """
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator

    # Create mock coordinator
    mock_coordinator = MagicMock(spec=TripPlannerCoordinator)
    mock_coordinator.data = {
        "per_trip_emhass_params": {
            "trip_001": {
                "emhass_index": 2,
                "kwh_needed": 7.4,
            }
        }
    }

    # Create empty entity registry
    mock_registry = MagicMock()
    mock_registry.async_remove = MagicMock(return_value=None)

    # Mock ConfigEntry
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    mock_entry.data = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry), \
         patch.object(hass, "entity_registry", mock_registry), \
         patch("custom_components.ev_trip_planner.sensor.async_entries_for_config_entry", return_value=[]):
        # Import and call the function
        from custom_components.ev_trip_planner.sensor import async_remove_trip_emhass_sensor

        result = await async_remove_trip_emhass_sensor(
            hass, mock_entry.entry_id, "test_vehicle", "nonexistent_trip"
        )

        # Assert returns False
        assert result is False, (
            f"async_remove_trip_emhass_sensor should return False when sensor not found, got {result}"
        )
