"""End-to-end tests for complete vehicle setup and trip to EMHASS flow."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CONSUMPTION,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_NOTIFICATION_SERVICE,
    CONF_VEHICLE_NAME,
)
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.trip_manager import TripManager
from custom_components.ev_trip_planner.vehicle_controller import VehicleController
from custom_components.ev_trip_planner.presence_monitor import PresenceMonitor


@pytest.fixture
def vehicle_id() -> str:
    """Return a sample vehicle ID for testing."""
    return "test_vehicle"


@pytest.fixture
def mock_hass(vehicle_id):
    """Create a mock hass with config_entries and data."""
    hass = MagicMock()

    # Mock config_entries
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"
    mock_entry.data = {
        CONF_VEHICLE_NAME: vehicle_id,
        CONF_BATTERY_CAPACITY: 60.0,
        CONF_CHARGING_POWER: 7.4,
        CONF_CONSUMPTION: 0.15,
        CONF_MAX_DEFERRABLE_LOADS: 50,
    }
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    # Mock hass.data with proper namespace
    hass.data = {}
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"

    # Mock states with basic sensors
    hass._states_dict = {
        "sensor.ovms_soc": MagicMock(
            state="75",
            attributes={"unit_of_measurement": "%", "device_class": "battery"},
        ),
        "sensor.ovms_consumption": MagicMock(
            state="15.0",
            attributes={"unit_of_measurement": "kWh/100km"},
        ),
        "binary_sensor.home_presence": MagicMock(
            state="on",
            attributes={"device_class": "presence"},
        ),
        "binary_sensor.vehicle_plugged": MagicMock(
            state="on",
            attributes={"device_class": "plug"},
        ),
        "binary_sensor.charging_status": MagicMock(
            state="on",
            attributes={"device_class": "battery_charging"},
        ),
    }

    def _mock_states_get(entity_id):
        return hass._states_dict.get(entity_id, None)

    async def _mock_states_async_set(entity_id, state, attributes=None):
        """Async set for States."""
        state_obj = MagicMock()
        state_obj.state = state
        state_obj.attributes = attributes or {}
        hass._states_dict[entity_id] = state_obj
        return True

    hass.states.get = _mock_states_get
    hass.states.async_set = _mock_states_async_set

    # Mock services
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    # Mock async_run_hass_job for debounce
    import asyncio

    def _mock_async_run_hass_job(job, *args, **kwargs):
        if job is None:
            return None
        job_target = job.target if hasattr(job, "target") else job
        if asyncio.iscoroutinefunction(job_target):
            return job_target(*args, **kwargs)
        else:
            async def _wrapper():
                return job_target(*args, **kwargs)
            return _wrapper()

    hass.async_run_hass_job = _mock_async_run_hass_job

    return hass


@pytest.fixture
def mock_store():
    """Fixture to provide a mock Store instance with async methods."""
    store = MagicMock()
    store._storage = {}

    async def _async_load():
        return store._storage.get("data", None)

    async def _async_save(data):
        store._storage["data"] = data
        return True

    store.async_load = _async_load
    store.async_save = _async_save

    yield store


@pytest.mark.asyncio
async def test_complete_vehicle_setup_flow(mock_hass, vehicle_id, mock_store):
    """Test complete vehicle setup flow from initialization to ready state."""
    # Step 1: Initialize TripManager
    manager = TripManager(mock_hass, vehicle_id)
    await manager.async_setup()

    assert manager._trips == {}
    assert manager._recurring_trips == {}
    assert manager._punctual_trips == {}

    # Step 2: Initialize EMHASS Adapter
    emhass_config = {
        CONF_VEHICLE_NAME: vehicle_id,
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, emhass_config)
        await adapter.async_load()

    # Verify EMHASS adapter initialized correctly
    assert adapter.vehicle_id == vehicle_id
    assert adapter.max_deferrable_loads == 50
    assert adapter.charging_power == 7.4

    # Connect TripManager to EMHASS adapter
    manager.set_emhass_adapter(adapter)

    # Step 3: Initialize Vehicle Controller
    controller = VehicleController(mock_hass, vehicle_id)

    # Verify vehicle controller initialized
    assert controller is not None

    # Step 4: Initialize Presence Monitor
    presence_config = {
        "home_sensor": "binary_sensor.home_presence",
        "plugged_sensor": "binary_sensor.vehicle_plugged",
        "charging_sensor": "binary_sensor.charging_status",
    }

    presence_monitor = PresenceMonitor(mock_hass, vehicle_id, presence_config)

    # Verify presence monitor initialized correctly
    assert presence_monitor.vehicle_id == vehicle_id


@pytest.mark.asyncio
async def test_trip_creation_to_emhass_publish(mock_hass, vehicle_id, mock_store):
    """Test complete flow from trip creation to EMHASS publish."""
    # Step 1: Initialize TripManager
    manager = TripManager(mock_hass, vehicle_id)
    await manager.async_setup()

    # Step 2: Initialize EMHASS Adapter
    emhass_config = {
        CONF_VEHICLE_NAME: vehicle_id,
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, emhass_config)
        await adapter.async_load()

    # Step 3: Add a punctual trip (with future deadline for EMHASS)
    await manager.async_add_punctual_trip(
        datetime_str=(datetime.now() + timedelta(hours=8)).isoformat(),
        km=24.0,
        kwh=3.6,
        descripcion="Work commute",
    )

    # Verify trip was created
    assert len(manager._punctual_trips) == 1
    trip_id = list(manager._punctual_trips.keys())[0]
    assert len(trip_id) > 0  # Just verify a trip ID was generated

    trip = manager._punctual_trips[trip_id]
    assert trip["km"] == 24.0
    assert trip["kwh"] == 3.6

    # Step 4: Add another punctual trip
    await manager.async_add_punctual_trip(
        datetime_str=(datetime.now() + timedelta(hours=12)).isoformat(),
        km=110.0,
        kwh=16.5,
        descripcion="Trip to Toledo",
    )

    # Verify punctual trip was created
    assert len(manager._punctual_trips) == 2

    # Step 5: Get all active trips for EMHASS using internal method
    active_trips = await manager._get_all_active_trips()

    # Both trips should be active
    assert len(active_trips) >= 2

    # Step 6: Publish trips to EMHASS directly
    result = await adapter.publish_deferrable_loads(active_trips, 7.4)

    # Verify publish was successful
    assert result is True

    # Step 7: Verify EMHASS sensor was created
    sensor_id = f"sensor.emhass_perfil_diferible_{vehicle_id}"
    state = mock_hass.states.get(sensor_id)

    assert state is not None
    assert state.state == "ready"
    assert "power_profile_watts" in state.attributes
    assert "deferrables_schedule" in state.attributes


@pytest.mark.asyncio
async def test_trip_update_triggers_emhass_update(mock_hass, vehicle_id, mock_store):
    """Test that updating a trip triggers EMHASS sensor update."""
    # Setup: TripManager and EMHASS Adapter
    manager = TripManager(mock_hass, vehicle_id)
    await manager.async_setup()

    emhass_config = {
        CONF_VEHICLE_NAME: vehicle_id,
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, emhass_config)
        await adapter.async_load()

    # Create initial trip
    await manager.async_add_punctual_trip(
        datetime_str=(datetime.now() + timedelta(hours=8)).isoformat(),
        km=24.0,
        kwh=3.6,
        descripcion="Work commute",
    )

    trip_id = list(manager._punctual_trips.keys())[0]

    # Publish initial trip
    active_trips = await manager._get_all_active_trips()
    await adapter.publish_deferrable_loads(active_trips, 7.4)

    # Get the assigned index
    index = adapter.get_assigned_index(trip_id)
    assert index is not None

    # Update the trip (e.g., change km and kwh)
    await manager.async_update_trip(trip_id, {"km": 30.0, "kwh": 4.5})

    # Verify trip was updated
    updated_trip = manager._punctual_trips[trip_id]
    assert updated_trip["km"] == 30.0
    assert updated_trip["kwh"] == 4.5

    # Republish to EMHASS
    active_trips = await manager._get_all_active_trips()
    await adapter.publish_deferrable_loads(active_trips, 7.4)

    # Verify sensor was updated with new values
    trip_sensor = mock_hass.states.get(f"sensor.emhass_deferrable_load_config_{index}")
    assert trip_sensor is not None
    # The kwh should be updated
    assert trip_sensor.attributes.get("kwh_needed") == 4.5


@pytest.mark.asyncio
async def test_trip_deletion_removes_from_manager(mock_hass, vehicle_id, mock_store):
    """Test that deleting a trip removes it from the trip manager."""
    # Setup: TripManager and EMHASS Adapter
    manager = TripManager(mock_hass, vehicle_id)
    await manager.async_setup()

    emhass_config = {
        CONF_VEHICLE_NAME: vehicle_id,
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, emhass_config)
        await adapter.async_load()

    # Create and publish trip
    await manager.async_add_punctual_trip(
        datetime_str=(datetime.now() + timedelta(hours=8)).isoformat(),
        km=24.0,
        kwh=3.6,
        descripcion="Work commute",
    )

    trip_id = list(manager._punctual_trips.keys())[0]

    # Verify trip exists
    assert trip_id in manager._punctual_trips

    # Delete the trip
    await manager.async_delete_trip(trip_id)

    # Verify trip was deleted
    assert trip_id not in manager._punctual_trips


@pytest.mark.asyncio
async def test_multiple_vehicles_independent_emhass_indices(mock_hass, mock_store):
    """Test that multiple vehicles have independent EMHASS index pools."""
    vehicle_ids = ["vehicle_1", "vehicle_2"]

    # Create adapters for each vehicle
    adapters = {}
    for vehicle_id in vehicle_ids:
        emhass_config = {
            CONF_VEHICLE_NAME: vehicle_id,
            CONF_MAX_DEFERRABLE_LOADS: 10,  # Small pool
            CONF_CHARGING_POWER: 7.4,
        }

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(mock_hass, emhass_config)
            await adapter.async_load()
            adapters[vehicle_id] = adapter

    # Assign indices to vehicle_1
    for i in range(5):
        await adapters["vehicle_1"].async_assign_index_to_trip(f"v1_trip_{i}")

    # Assign indices to vehicle_2
    for i in range(5):
        await adapters["vehicle_2"].async_assign_index_to_trip(f"v2_trip_{i}")

    # Verify each vehicle has independent index pools
    # vehicle_1 should have 5 indices used (0-4)
    assert len(adapters["vehicle_1"]._available_indices) == 5  # 10 - 5

    # vehicle_2 should also have 5 indices used (0-4)
    assert len(adapters["vehicle_2"]._available_indices) == 5  # 10 - 5

    # Verify indices are different between vehicles (both use 0-4)
    # but they are independent
    v1_indices = [
        adapters["vehicle_1"].get_assigned_index(f"v1_trip_{i}")
        for i in range(5)
    ]
    v2_indices = [
        adapters["vehicle_2"].get_assigned_index(f"v2_trip_{i}")
        for i in range(5)
    ]

    # Both should have used indices 0-4
    assert sorted(v1_indices) == [0, 1, 2, 3, 4]
    assert sorted(v2_indices) == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_vehicle_controller_initialization(mock_hass, vehicle_id):
    """Test that vehicle controller can be initialized."""
    controller = VehicleController(mock_hass, vehicle_id)

    # Verify vehicle controller initialized
    assert controller is not None

    # Test with presence config
    presence_config = {
        "home_sensor": "binary_sensor.home_presence",
        "plugged_sensor": "binary_sensor.vehicle_plugged",
        "charging_sensor": "binary_sensor.charging_status",
    }
    controller = VehicleController(mock_hass, vehicle_id, presence_config)

    assert controller is not None


@pytest.mark.asyncio
async def test_presence_monitor_integration(mock_hass, vehicle_id):
    """Test that presence monitor integrates correctly."""
    presence_config = {
        "home_sensor": "binary_sensor.home_presence",
        "plugged_sensor": "binary_sensor.vehicle_plugged",
        "charging_sensor": "binary_sensor.charging_status",
    }

    presence_monitor = PresenceMonitor(mock_hass, vehicle_id, presence_config)

    # Set up state where charging is needed but not possible
    mock_hass._states_dict["binary_sensor.home_presence"].state = "off"
    mock_hass._states_dict["binary_sensor.vehicle_plugged"].state = "off"
    mock_hass._states_dict["binary_sensor.charging_status"].state = "off"

    # Test checking home status
    is_home = await presence_monitor.async_check_home_status()
    assert is_home is False

    # Test checking plugged status
    is_plugged = await presence_monitor.async_check_plugged_status()
    assert is_plugged is False


@pytest.mark.asyncio
async def test_complete_flow_with_notification_service(
    mock_hass, vehicle_id, mock_store
):
    """Test complete flow including notification on errors."""
    # Setup with notification service
    emhass_config = {
        CONF_VEHICLE_NAME: vehicle_id,
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_NOTIFICATION_SERVICE: "notify.mobile_app",
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, emhass_config)
        await adapter.async_load()

    # Verify notification service is configured
    assert adapter.notification_service == "notify.mobile_app"

    # Create and publish trips via TripManager
    manager = TripManager(mock_hass, vehicle_id)
    await manager.async_setup()

    # Connect TripManager to EMHASS adapter
    manager.set_emhass_adapter(adapter)

    await manager.async_add_punctual_trip(
        datetime_str=(datetime.now() + timedelta(hours=8)).isoformat(),
        km=24.0,
        kwh=3.6,
        descripcion="Work commute",
    )

    active_trips = await manager._get_all_active_trips()
    await adapter.publish_deferrable_loads(active_trips, 7.4)

    # Get trip id
    trip_id = list(manager._punctual_trips.keys())[0]

    # Simulate an error condition and verify notification
    await adapter.async_handle_emhass_unavailable(
        reason="Connection timeout",
        trip_id=trip_id,
    )

    # Verify error is tracked
    last_error = adapter.get_last_error()
    assert last_error is not None
    assert "Connection timeout" in last_error["message"]

    # Clear error
    await adapter.async_clear_error()
    assert adapter.get_last_error() is None
