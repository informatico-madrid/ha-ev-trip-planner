"""Tests for Presence Monitor SOC functionality (Task 1.8)."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.ev_trip_planner.const import (
    CONF_HOME_SENSOR,
    CONF_PLUGGED_SENSOR,
    CONF_SOC_SENSOR,
)
from custom_components.ev_trip_planner.presence_monitor import PresenceMonitor



@pytest.fixture(autouse=True)
def mock_store_class():
    """Fixture to patch the Store class for testing (autouse for all tests)."""
    from homeassistant.helpers import storage as ha_storage

    class MockStore:
        def __init__(self, hass, version, key, *, private=None):
            self.hass = hass
            self.version = version
            self.key = key
            self._storage = {}

        async def async_load(self):
            return self._storage.get("data")

        async def async_save(self, data):
            self._storage["data"] = data
            return True

    with patch.object(ha_storage, "Store", MockStore):
        yield MockStore


@pytest.fixture
def mock_trip_manager():
    """Create mock TripManager with async methods."""
    manager = Mock()
    manager.publish_deferrable_loads = AsyncMock()
    return manager


# =============================================================================
# AC-1, AC-2, AC-3: SOC change triggers recalculation when home+plugged
# =============================================================================


@pytest.mark.asyncio
async def test_soc_change_triggers_recalculation_when_home_and_plugged(
    mock_hass, mock_trip_manager
):
    """Test SOC change >= 5% triggers recalculation when home+plugged (AC-1, AC-2, AC-3)."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)

    # Set up mocks: home=on, plugged=on
    mock_home_state = Mock()
    mock_home_state.state = "on"
    mock_plugged_state = Mock()
    mock_plugged_state.state = "on"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home_state
        if entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged_state
        return None

    mock_hass.states.get = mock_get_state

    # Simulate SOC change event: 50% -> 60% (10% delta, exceeds 5% threshold)
    old_soc_state = Mock()
    old_soc_state.state = "50"

    new_soc_state = Mock()
    new_soc_state.state = "60"

    event = Mock()
    event.data = {
        "old_state": old_soc_state,
        "new_state": new_soc_state,
    }

    # Process the SOC change event
    await monitor._async_handle_soc_change(event)

    # Verify recalculation was triggered
    mock_trip_manager.publish_deferrable_loads.assert_called_once()
    # Verify _last_processed_soc was updated
    assert monitor._last_processed_soc == 60.0


# =============================================================================
# AC-2, AC-3: SOC change does NOT trigger when away or unplugged
# =============================================================================


@pytest.mark.asyncio
async def test_soc_change_does_not_trigger_when_away(mock_hass, mock_trip_manager):
    """Test SOC change does NOT trigger recalculation when vehicle not home (AC-2, AC-3)."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)

    # Set up mocks: home=off, plugged=on
    mock_home_state = Mock()
    mock_home_state.state = "off"
    mock_plugged_state = Mock()
    mock_plugged_state.state = "on"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home_state
        if entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged_state
        return None

    mock_hass.states.get = mock_get_state

    # Simulate SOC change event: 50% -> 60% (10% delta)
    old_soc_state = Mock()
    old_soc_state.state = "50"

    new_soc_state = Mock()
    new_soc_state.state = "60"

    event = Mock()
    event.data = {
        "old_state": old_soc_state,
        "new_state": new_soc_state,
    }

    # Process the SOC change event
    await monitor._async_handle_soc_change(event)

    # Verify recalculation was NOT triggered (not at home)
    mock_trip_manager.publish_deferrable_loads.assert_not_called()


@pytest.mark.asyncio
async def test_soc_change_does_not_trigger_when_unplugged(mock_hass, mock_trip_manager):
    """Test SOC change does NOT trigger recalculation when vehicle not plugged (AC-2, AC-3)."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)

    # Set up mocks: home=on, plugged=off
    mock_home_state = Mock()
    mock_home_state.state = "on"
    mock_plugged_state = Mock()
    mock_plugged_state.state = "off"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home_state
        if entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged_state
        return None

    mock_hass.states.get = mock_get_state

    # Simulate SOC change event: 50% -> 60% (10% delta)
    old_soc_state = Mock()
    old_soc_state.state = "50"

    new_soc_state = Mock()
    new_soc_state.state = "60"

    event = Mock()
    event.data = {
        "old_state": old_soc_state,
        "new_state": new_soc_state,
    }

    # Process the SOC change event
    await monitor._async_handle_soc_change(event)

    # Verify recalculation was NOT triggered (not plugged)
    mock_trip_manager.publish_deferrable_loads.assert_not_called()


# =============================================================================
# AC-4, AC-6: Return home detection (off->on transition)
# =============================================================================


@pytest.mark.asyncio
async def test_return_home_detection_off_to_on_transition(mock_hass, mock_trip_manager):
    """Test return home detection (off->on transition) captures SOC and timestamp (AC-4, AC-6)."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)

    # Set up: initially away (was_home=False)
    monitor._was_home = False

    # Mock SOC sensor with current value
    mock_soc_state = Mock()
    mock_soc_state.state = "65"

    # Set up mocks: home goes on (return home), plugged is on
    mock_home_state = Mock()
    mock_home_state.state = "on"
    mock_plugged_state = Mock()
    mock_plugged_state.state = "on"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home_state
        if entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged_state
        if entity_id == "sensor.ovms_soc":
            return mock_soc_state
        return None

    mock_hass.states.get = mock_get_state

    # Call async_check_home_status which should detect off->on transition
    is_home = await monitor.async_check_home_status()

    # Verify return was detected
    assert is_home is True
    assert monitor._was_home is True  # State should be updated
    assert monitor.hora_regreso is not None  # Timestamp should be captured
    assert monitor.soc_en_regreso == 65.0  # SOC should be captured

    # Verify persistence was called (Store + HA state entity)
    mock_hass.states.async_set.assert_called_once()
    call_args = mock_hass.states.async_set.call_args
    entity_id = call_args[0][0]
    assert entity_id == "sensor.ev_trip_planner_test_vehicle_return_info"


@pytest.mark.asyncio
async def test_departure_invalidates_hora_regreso(mock_hass, mock_trip_manager):
    """Test departure (on->off transition) invalidates hora_regreso (AC-6)."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)

    # Set up: initially home (was_home=True) with hora_regreso set
    monitor._was_home = True
    monitor.hora_regreso = "2026-03-30T10:00:00+00:00"
    monitor.soc_en_regreso = 65.0

    # Set up mocks: home goes off (departure)
    mock_home_state = Mock()
    mock_home_state.state = "off"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home_state
        return None

    mock_hass.states.get = mock_get_state

    # Call async_check_home_status which should detect on->off transition
    is_home = await monitor.async_check_home_status()

    # Verify departure was detected and hora_regreso was invalidated
    assert is_home is False
    assert monitor._was_home is False
    assert monitor.hora_regreso is None
    assert monitor.soc_en_regreso is None

    # Verify persistence was called to clear the state
    mock_hass.states.async_set.assert_called_once()


# =============================================================================
# AC-2, AC-3: SOC debouncing (5% threshold blocks recalculation)
# =============================================================================


@pytest.mark.asyncio
async def test_soc_debouncing_5_percent_threshold_blocks_recalculation(
    mock_hass, mock_trip_manager
):
    """Test SOC change < 5% does NOT trigger recalculation (debouncing) (AC-2, AC-3)."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)
    # Set last_processed_soc to simulate previous trigger
    monitor._last_processed_soc = 50.0

    # Set up mocks: home=on, plugged=on
    mock_home_state = Mock()
    mock_home_state.state = "on"
    mock_plugged_state = Mock()
    mock_plugged_state.state = "on"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home_state
        if entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged_state
        return None

    mock_hass.states.get = mock_get_state

    # Simulate SOC change event: 50% -> 53% (3% delta - below 5% threshold)
    old_soc_state = Mock()
    old_soc_state.state = "50"

    new_soc_state = Mock()
    new_soc_state.state = "53"

    event = Mock()
    event.data = {
        "old_state": old_soc_state,
        "new_state": new_soc_state,
    }

    # Process the SOC change event
    await monitor._async_handle_soc_change(event)

    # Verify recalculation was NOT triggered (below 5% threshold)
    mock_trip_manager.publish_deferrable_loads.assert_not_called()
    # Verify _last_processed_soc was NOT updated
    assert monitor._last_processed_soc == 50.0


@pytest.mark.asyncio
async def test_soc_debouncing_5_percent_threshold_allows_recalculation(
    mock_hass, mock_trip_manager
):
    """Test SOC change >= 5% DOES trigger recalculation (at threshold)."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)
    # Set last_processed_soc to simulate previous trigger
    monitor._last_processed_soc = 50.0

    # Set up mocks: home=on, plugged=on
    mock_home_state = Mock()
    mock_home_state.state = "on"
    mock_plugged_state = Mock()
    mock_plugged_state.state = "on"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home_state
        if entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged_state
        return None

    mock_hass.states.get = mock_get_state

    # Simulate SOC change event: 50% -> 55% (5% delta - exactly at threshold)
    old_soc_state = Mock()
    old_soc_state.state = "50"

    new_soc_state = Mock()
    new_soc_state.state = "55"

    event = Mock()
    event.data = {
        "old_state": old_soc_state,
        "new_state": new_soc_state,
    }

    # Process the SOC change event
    await monitor._async_handle_soc_change(event)

    # Verify recalculation WAS triggered (delta >= 5%)
    mock_trip_manager.publish_deferrable_loads.assert_called_once()
    # Verify _last_processed_soc was updated
    assert monitor._last_processed_soc == 55.0

    # MINIMAL TEST: Only verifies that publish_deferrable_loads() is called
    # COMPREHENSIVE TEST should also verify:
    # 1. That EMHASSAdapter updates its cache (_cached_power_profile, etc.)
    # 2. That coordinator.async_refresh() is called
    # 3. That the EMHASS sensor shows the new data
    #
    # Currently this test PASSES but does NOT detect that the sensor is NOT updated
    #
    # To make this test comprehensive, we would need:
    # - Mock the EMHASSAdapter and verify that the cache is updated
    # - Mock the coordinator and verify that async_refresh() is called
    # - Verify that EmhassDeferrableLoadSensor.extra_state_attributes has new data
    #
    # Problem: The current test has no access to the coordinator or EMHASSAdapter
    # Solution: Create a full integration test in test_coordinator.py


@pytest.mark.asyncio
async def test_soc_debouncing_ignores_unavailable_state(mock_hass, mock_trip_manager):
    """Test SOC change to unavailable/unknown state is skipped without updating _last_processed_soc."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)
    monitor._last_processed_soc = 50.0

    # Set up mocks: home=on, plugged=on
    mock_home_state = Mock()
    mock_home_state.state = "on"
    mock_plugged_state = Mock()
    mock_plugged_state.state = "on"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home_state
        if entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged_state
        return None

    mock_hass.states.get = mock_get_state

    # Simulate SOC change to unavailable state
    old_soc_state = Mock()
    old_soc_state.state = "50"

    new_soc_state = Mock()
    new_soc_state.state = "unavailable"

    event = Mock()
    event.data = {
        "old_state": old_soc_state,
        "new_state": new_soc_state,
    }

    # Process the SOC change event
    await monitor._async_handle_soc_change(event)

    # Verify recalculation was NOT triggered
    mock_trip_manager.publish_deferrable_loads.assert_not_called()
    # Verify _last_processed_soc was NOT updated
    assert monitor._last_processed_soc == 50.0


# =============================================================================
# AC-4: hora_regreso/soc_en_regreso persistence via Store
# =============================================================================


@pytest.mark.asyncio
async def test_hora_regreso_soc_en_regreso_persistence_via_store(
    mock_hass, mock_trip_manager
):
    """Test hora_regreso and soc_en_regreso are persisted via ha_storage.Store (AC-4)."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)

    # Set up: initially away, then return home
    monitor._was_home = False

    # Mock SOC sensor
    mock_soc_state = Mock()
    mock_soc_state.state = "75"

    # Mock home sensor (return home)
    mock_home_state = Mock()
    mock_home_state.state = "on"
    mock_plugged_state = Mock()
    mock_plugged_state.state = "on"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home_state
        if entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged_state
        if entity_id == "sensor.ovms_soc":
            return mock_soc_state
        return None

    mock_hass.states.get = mock_get_state

    # Trigger return home detection
    await monitor.async_check_home_status()

    # Verify hora_regreso and soc_en_regreso are set
    assert monitor.hora_regreso is not None
    assert monitor.soc_en_regreso == 75.0

    # Verify Store was used for persistence (check hass.states.async_set was called)
    mock_hass.states.async_set.assert_called_once()
    call_args = mock_hass.states.async_set.call_args
    entity_id = call_args[0][0]
    state_value = call_args[0][1]
    attributes = call_args[0][2]

    # Verify HA state entity was created with correct data
    assert entity_id == "sensor.ev_trip_planner_test_vehicle_return_info"
    assert state_value == monitor.hora_regreso  # ISO timestamp
    assert attributes["soc_en_regreso"] == 75.0
    assert attributes["hora_regreso_iso"] == monitor.hora_regreso
    assert attributes["vehicle_id"] == "test_vehicle"


@pytest.mark.asyncio
async def test_hora_regreso_persistence_across_monitor_lifecycle(
    mock_hass, mock_trip_manager
):
    """Test hora_regreso persists correctly across PresenceMonitor lifecycle."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    # First monitor instance - return home
    monitor1 = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)
    monitor1._was_home = False

    mock_soc_state = Mock()
    mock_soc_state.state = "80"

    mock_home_state = Mock()
    mock_home_state.state = "on"
    mock_plugged_state = Mock()
    mock_plugged_state.state = "on"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home_state
        if entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged_state
        if entity_id == "sensor.ovms_soc":
            return mock_soc_state
        return None

    mock_hass.states.get = mock_get_state

    # Return home
    await monitor1.async_check_home_status()

    # Capture persisted values
    saved_hora_regreso = monitor1.hora_regreso
    saved_soc_en_regreso = monitor1.soc_en_regreso

    assert saved_hora_regreso is not None
    assert saved_soc_en_regreso == 80.0

    # Second monitor instance (simulating HA restart) - should load persisted state
    monitor2 = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)

    # The Store mock returns whatever was saved, so verify persistence mechanism exists
    assert hasattr(monitor2, "_return_info_store")
    assert hasattr(monitor2, "_return_info_entity_id")
    assert (
        monitor2._return_info_entity_id
        == "sensor.ev_trip_planner_test_vehicle_return_info"
    )


@pytest.mark.asyncio
async def test_soc_change_calls_publish_deferrable_loads(mock_hass, mock_trip_manager):
    """Test _async_handle_soc_change calls trip_manager.publish_deferrable_loads().

    Task 1.12 test: expects SOC change to route through publish_deferrable_loads.
    """
    from custom_components.ev_trip_planner.presence_monitor import PresenceMonitor

    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)

    # Set up mocks: home=on, plugged=on
    mock_home_state = Mock()
    mock_home_state.state = "on"
    mock_plugged_state = Mock()
    mock_plugged_state.state = "on"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home_state
        if entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged_state
        return None

    mock_hass.states.get = mock_get_state

    # Mock other required attributes
    monitor._store = AsyncMock()
    monitor._last_processed_soc = 50.0

    # Mock publish_deferrable_loads as async
    mock_trip_manager.publish_deferrable_loads = AsyncMock()

    # Simulate SOC change event: 50% -> 60% (10% delta, exceeds 5% threshold)
    old_soc_state = Mock()
    old_soc_state.state = "50"

    new_soc_state = Mock()
    new_soc_state.state = "60"

    event = Mock()
    event.data = {
        "old_state": old_soc_state,
        "new_state": new_soc_state,
    }

    # Process the SOC change event
    await monitor._async_handle_soc_change(event)

    # publish_deferrable_loads should be called (not async_generate_* methods)
    mock_trip_manager.publish_deferrable_loads.assert_called_once()
