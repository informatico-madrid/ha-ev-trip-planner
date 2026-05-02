"""Tests for Presence Monitor."""

import pytest
from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner.presence_monitor import PresenceMonitor
from custom_components.ev_trip_planner.const import (
    CONF_HOME_SENSOR,
    CONF_PLUGGED_SENSOR,
    CONF_HOME_COORDINATES,
    CONF_VEHICLE_COORDINATES_SENSOR,
    CONF_NOTIFICATION_SERVICE,
    CONF_SOC_SENSOR,
)


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance with required attributes for Store."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {}  # Required by ha_storage.Store
    hass.states = Mock()
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    # Mock hass.bus for async_track_state_change_event
    hass.bus = Mock()
    hass.bus.async_listen = Mock()

    # Mock async_run_hass_job for debounce
    async def mock_async_run_hass_job(job, *_args, **_kwargs):
        return None

    hass.async_run_hass_job = mock_async_run_hass_job
    return hass


@pytest.fixture(autouse=True)
def mock_store_class():
    """Fixture to patch the Store class for testing (autouse for all tests)."""
    from homeassistant.helpers import storage as ha_storage
    from unittest.mock import patch

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


@pytest.mark.asyncio
async def test_presence_monitor_instantiation_sensor_based(mock_hass):
    """Test PresenceMonitor can be created with sensor-based config."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    assert monitor.hass == mock_hass
    assert monitor.vehicle_id == "test_vehicle"
    assert monitor.home_sensor == "binary_sensor.vehicle_home"
    assert monitor.plugged_sensor == "binary_sensor.vehicle_plugged"
    assert monitor.home_coords is None
    assert monitor.vehicle_coords_sensor is None


@pytest.mark.asyncio
async def test_presence_monitor_instantiation_coordinate_based(mock_hass):
    """Test PresenceMonitor can be created with coordinate-based config."""
    config = {
        CONF_HOME_COORDINATES: "40.4168,-3.7038",
        CONF_VEHICLE_COORDINATES_SENSOR: "sensor.vehicle_location",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    assert monitor.home_coords == (40.4168, -3.7038)
    assert monitor.vehicle_coords_sensor == "sensor.vehicle_location"


@pytest.mark.asyncio
async def test_presence_monitor_instantiation_mixed_config(mock_hass):
    """Test PresenceMonitor with both sensor and coordinate config."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_HOME_COORDINATES: "40.4168,-3.7038",
        CONF_VEHICLE_COORDINATES_SENSOR: "sensor.vehicle_location",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Sensor should take priority over coordinates
    assert monitor.home_sensor == "binary_sensor.vehicle_home"
    assert monitor.home_coords == (40.4168, -3.7038)


@pytest.mark.asyncio
async def test_check_home_status_sensor_on(mock_hass):
    """Test home status check when sensor is on."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock sensor state
    mock_state = Mock()
    mock_state.state = "on"
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_home_status()

    assert result is True
    mock_hass.states.get.assert_called_once_with("binary_sensor.vehicle_home")


@pytest.mark.asyncio
async def test_check_home_status_sensor_off(mock_hass):
    """Test home status check when sensor is off."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock sensor state
    mock_state = Mock()
    mock_state.state = "off"
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_home_status()

    assert result is False


@pytest.mark.asyncio
async def test_check_home_status_sensor_not_found(mock_hass):
    """Test home status when sensor doesn't exist."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock sensor not found
    mock_hass.states.get = Mock(return_value=None)

    result = await monitor.async_check_home_status()

    assert result is False


@pytest.mark.asyncio
async def test_check_home_status_coordinate_at_home(mock_hass):
    """Test home status using coordinates when vehicle is at home."""
    config = {
        CONF_HOME_COORDINATES: "40.4168,-3.7038",
        CONF_VEHICLE_COORDINATES_SENSOR: "sensor.vehicle_location",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock vehicle coordinates (very close to home)
    mock_state = Mock()
    mock_state.state = "40.4169,-3.7039"  # ~15m away
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_home_status()

    assert result is True


@pytest.mark.asyncio
async def test_check_home_status_coordinate_away(mock_hass):
    """Test home status using coordinates when vehicle is away."""
    config = {
        CONF_HOME_COORDINATES: "40.4168,-3.7038",
        CONF_VEHICLE_COORDINATES_SENSOR: "sensor.vehicle_location",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock vehicle coordinates (far away)
    mock_state = Mock()
    mock_state.state = "41.0000,-4.0000"  # ~100km away
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_home_status()

    assert result is False


@pytest.mark.asyncio
async def test_check_home_status_coordinate_sensor_not_found(mock_hass):
    """Test home status when coordinate sensor doesn't exist."""
    config = {
        CONF_HOME_COORDINATES: "40.4168,-3.7038",
        CONF_VEHICLE_COORDINATES_SENSOR: "sensor.vehicle_location",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock sensor not found
    mock_hass.states.get = Mock(return_value=None)

    result = await monitor.async_check_home_status()

    # Should return True (blind mode) when sensor not found
    assert result is True


@pytest.mark.asyncio
async def test_check_home_status_no_config(mock_hass):
    """Test home status when no config provided (blind mode)."""
    config = {}

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    result = await monitor.async_check_home_status()

    # Should return True (blind mode)
    assert result is True


@pytest.mark.asyncio
async def test_check_plugged_status_sensor_on(mock_hass):
    """Test plugged status when sensor is on."""
    config = {
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock sensor state
    mock_state = Mock()
    mock_state.state = "on"
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_plugged_status()

    assert result is True


@pytest.mark.asyncio
async def test_check_plugged_status_sensor_off(mock_hass):
    """Test plugged status when sensor is off."""
    config = {
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock sensor state
    mock_state = Mock()
    mock_state.state = "off"
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_plugged_status()

    assert result is False


@pytest.mark.asyncio
async def test_check_plugged_status_no_sensor(mock_hass):
    """Test plugged status when no sensor configured."""
    config = {}

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    result = await monitor.async_check_plugged_status()

    # Should return True (assume plugged)
    assert result is True


@pytest.mark.asyncio
async def test_check_charging_readiness_ready(mock_hass):
    """Test charging readiness when all conditions met."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock both sensors on
    mock_home = Mock()
    mock_home.state = "on"
    mock_plugged = Mock()
    mock_plugged.state = "on"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home
        elif entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged
        return None

    mock_hass.states.get = mock_get_state

    ready, reason = await monitor.async_check_charging_readiness()

    assert ready is True
    assert reason is None


@pytest.mark.asyncio
async def test_check_charging_readiness_not_home(mock_hass):
    """Test charging readiness when vehicle not home."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock home sensor off, plugged on
    mock_home = Mock()
    mock_home.state = "off"
    mock_plugged = Mock()
    mock_plugged.state = "on"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home
        elif entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged
        return None

    mock_hass.states.get = mock_get_state

    ready, reason = await monitor.async_check_charging_readiness()

    assert ready is False
    assert reason == "Vehicle not at home"


@pytest.mark.asyncio
async def test_check_charging_readiness_not_plugged(mock_hass):
    """Test charging readiness when vehicle not plugged."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock home sensor on, plugged off
    mock_home = Mock()
    mock_home.state = "on"
    mock_plugged = Mock()
    mock_plugged.state = "off"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_home
        elif entity_id == "binary_sensor.vehicle_plugged":
            return mock_plugged
        return None

    mock_hass.states.get = mock_get_state

    ready, reason = await monitor.async_check_charging_readiness()

    assert ready is False
    assert reason == "Vehicle not plugged in"


@pytest.mark.asyncio
async def test_parse_coordinates_brackets(mock_hass):
    """Test parsing coordinates with brackets."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    result = monitor._parse_coordinates("[40.4168, -3.7038]")

    assert result == (40.4168, -3.7038)


@pytest.mark.asyncio
async def test_parse_coordinates_no_brackets(mock_hass):
    """Test parsing coordinates without brackets."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    result = monitor._parse_coordinates("40.4168, -3.7038")

    assert result == (40.4168, -3.7038)


@pytest.mark.asyncio
async def test_parse_coordinates_invalid(mock_hass):
    """Test parsing invalid coordinates."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    result = monitor._parse_coordinates("invalid")

    assert result is None


@pytest.mark.asyncio
async def test_parse_coordinates_malformed(mock_hass):
    """Test parsing malformed coordinates."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    result = monitor._parse_coordinates("40.4168")

    assert result is None


@pytest.mark.asyncio
async def test_calculate_distance_same_point(mock_hass):
    """Test distance calculation for same point."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Same coordinates should give 0 distance
    distance = monitor._calculate_distance((40.4168, -3.7038), (40.4168, -3.7038))

    assert abs(distance) < 0.001  # Very close to 0


@pytest.mark.asyncio
async def test_calculate_distance_known_points(mock_hass):
    """Test distance calculation for known points."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Madrid to Barcelona (approximate)
    distance = monitor._calculate_distance((40.4168, -3.7038), (41.3851, 2.1734))

    # Should be around 500km = 500,000 meters
    assert 400000 < distance < 600000


@pytest.mark.asyncio
async def test_coordinate_priority_over_sensor(mock_hass):
    """Test that sensor takes priority over coordinates."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_HOME_COORDINATES: "40.4168,-3.7038",
        CONF_VEHICLE_COORDINATES_SENSOR: "sensor.vehicle_location",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock sensor state (should be used instead of coordinates)
    mock_state = Mock()
    mock_state.state = "on"
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_home_status()

    assert result is True
    # Should have called sensor, not used coordinates
    mock_hass.states.get.assert_called_once_with("binary_sensor.vehicle_home")


@pytest.mark.asyncio
async def test_presence_monitor_instantiation_with_notification_service(mock_hass):
    """Test PresenceMonitor can be created with notification service config."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_NOTIFICATION_SERVICE: "notify.mobile_app",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    assert monitor.notification_service == "notify.mobile_app"


@pytest.mark.asyncio
async def test_presence_monitor_instantiation_no_notification_service(mock_hass):
    """Test PresenceMonitor works without notification service config."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    assert monitor.notification_service is None


@pytest.mark.asyncio
async def test_notify_charging_not_possible_no_service(mock_hass):
    """Test notification returns False when no service configured."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    result = await monitor.async_notify_charging_not_possible("Vehicle not at home")

    assert result is False


@pytest.mark.asyncio
async def test_notify_charging_not_possible_with_service_success(mock_hass):
    """Test notification sent successfully with valid service."""
    config = {
        CONF_NOTIFICATION_SERVICE: "notify.mobile_app",
    }
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    result = await monitor.async_notify_charging_not_possible("Vehicle not at home")

    assert result is True
    mock_hass.services.async_call.assert_called_once()
    call_args = mock_hass.services.async_call.call_args
    assert call_args[0][0] == "notify"  # domain
    assert call_args[0][1] == "mobile_app"  # service


@pytest.mark.asyncio
async def test_notify_charging_not_possible_with_trip_info(mock_hass):
    """Test notification includes trip information."""
    config = {
        CONF_NOTIFICATION_SERVICE: "notify.mobile_app",
    }
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    trip_info = {
        "destination": "Madrid",
        "energy_needed": 7.5,
        "deadline": "22:00",
    }

    result = await monitor.async_notify_charging_not_possible(
        "Vehicle not at home", trip_info
    )

    assert result is True
    call_args = mock_hass.services.async_call.call_args
    # args are (domain, service, data_dict) - data dict is the third positional arg
    service_data = call_args[0][2]
    assert "Madrid" in service_data["message"]
    assert "7.5" in service_data["message"]
    assert "22:00" in service_data["message"]


@pytest.mark.asyncio
async def test_notify_vehicle_not_home(mock_hass):
    """Test notification when vehicle not at home."""
    config = {
        CONF_NOTIFICATION_SERVICE: "notify.mobile_app",
    }
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    trip_info = {"destination": "Barcelona", "energy_needed": 15.0}
    result = await monitor.async_notify_vehicle_not_home(trip_info)

    assert result is True
    call_args = mock_hass.services.async_call.call_args
    service_data = call_args[0][2]
    assert "not at home" in service_data["message"]


@pytest.mark.asyncio
async def test_notify_vehicle_not_plugged(mock_hass):
    """Test notification when vehicle not plugged in."""
    config = {
        CONF_NOTIFICATION_SERVICE: "notify.mobile_app",
    }
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    trip_info = {"destination": "Barcelona", "energy_needed": 15.0}
    result = await monitor.async_notify_vehicle_not_plugged(trip_info)

    assert result is True
    call_args = mock_hass.services.async_call.call_args
    service_data = call_args[0][2]
    assert "not plugged" in service_data["message"]


@pytest.mark.asyncio
async def test_notify_charging_not_possible_service_failure(mock_hass):
    """Test notification handles service failure gracefully."""
    config = {
        CONF_NOTIFICATION_SERVICE: "notify.mobile_app",
    }
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock service call to raise exception
    mock_hass.services.async_call = AsyncMock(side_effect=Exception("Service error"))

    result = await monitor.async_notify_charging_not_possible("Vehicle not at home")

    assert result is False


def test_get_home_condition_config_with_sensor(mock_hass):
    """Test getting native home condition config when sensor is configured."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
    }
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    condition_config = monitor.get_home_condition_config()

    assert condition_config is not None
    assert condition_config["condition"] == "state"
    assert condition_config["entity_id"] == "binary_sensor.vehicle_home"
    assert condition_config["state"] == "on"


def test_get_home_condition_config_no_sensor(mock_hass):
    """Test getting home condition config when no sensor configured."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    condition_config = monitor.get_home_condition_config()

    assert condition_config is None


def test_get_plugged_condition_config_with_sensor(mock_hass):
    """Test getting native plugged condition config when sensor is configured."""
    config = {
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
    }
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    condition_config = monitor.get_plugged_condition_config()

    assert condition_config is not None
    assert condition_config["condition"] == "state"
    assert condition_config["entity_id"] == "binary_sensor.vehicle_plugged"
    assert condition_config["state"] == "on"


def test_get_plugged_condition_config_no_sensor(mock_hass):
    """Test getting plugged condition config when no sensor configured."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    condition_config = monitor.get_plugged_condition_config()

    assert condition_config is None


def test_validate_condition_is_native_valid_state_condition(mock_hass):
    """Test validation accepts native state condition."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    condition = {
        "condition": "state",
        "entity_id": "binary_sensor.vehicle_home",
        "state": "on",
    }

    is_valid, error = monitor.validate_condition_is_native(condition)

    assert is_valid is True
    assert error is None


def test_validate_condition_is_native_template_condition(mock_hass):
    """Test validation rejects template condition with helpful message."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    condition = {
        "condition": "template",
        "value_template": "{{ is_state('binary_sensor.vehicle_home', 'on') }}",
    }

    is_valid, error = monitor.validate_condition_is_native(condition)

    assert is_valid is False
    assert "template" in error.lower()
    assert "condition: state" in error


def test_validate_condition_is_native_missing_entity_id(mock_hass):
    """Test validation fails when state condition missing entity_id."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    condition = {
        "condition": "state",
        "state": "on",
    }

    is_valid, error = monitor.validate_condition_is_native(condition)

    assert is_valid is False
    assert "entity_id" in error


def test_validate_condition_is_native_missing_state(mock_hass):
    """Test validation fails when state condition missing state."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    condition = {
        "condition": "state",
        "entity_id": "binary_sensor.vehicle_home",
    }

    is_valid, error = monitor.validate_condition_is_native(condition)

    assert is_valid is False
    assert "state" in error


def test_validate_condition_is_native_other_conditions(mock_hass):
    """Test validation accepts other condition types."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Numeric state condition
    condition = {
        "condition": "numeric_state",
        "entity_id": "sensor.battery",
        "below": 50,
    }

    is_valid, error = monitor.validate_condition_is_native(condition)

    assert is_valid is True
    assert error is None


def test_validate_condition_is_native_invalid_input(mock_hass):
    """Test validation handles invalid input."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    is_valid, error = monitor.validate_condition_is_native("not a dict")

    assert is_valid is False
    assert "dictionary" in error


@pytest.mark.asyncio
async def test_check_plugged_status_sensor_not_found(mock_hass):
    """Test plugged status check when sensor doesn't exist."""
    config = {
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock hass.states.get to return None (sensor not found)
    mock_hass.states.get = Mock(return_value=None)

    # Should return True (assume plugged) when sensor not found
    result = await monitor.async_check_plugged_status()

    assert result is True


# =============================================================================
# SOC Listener Tests (Task 1.6)
# =============================================================================


@pytest.mark.asyncio
async def test_soc_listener_registered_with_soc_sensor(mock_hass):
    """Test SOC listener is registered when soc_sensor is configured."""
    from unittest.mock import patch

    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    with patch(
        "custom_components.ev_trip_planner.presence_monitor.async_track_state_change_event"
    ) as mock_track:
        mock_track.return_value = Mock()
        monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

        # Verify listener was registered for the SOC sensor
        mock_track.assert_called_once_with(
            mock_hass,
            "sensor.ovms_soc",
            monitor._async_handle_soc_change,
        )
        assert monitor._soc_listener_unsub is not None


@pytest.mark.asyncio
async def test_soc_listener_not_registered_without_soc_sensor(mock_hass):
    """Test SOC listener is NOT registered when soc_sensor is not configured."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # SOC listener should not be registered
    assert monitor._soc_listener_unsub is None


@pytest.mark.asyncio
async def test_soc_change_triggers_recalculation_when_home_and_plugged(mock_hass):
    """Test SOC change >= 5% triggers recalculation when home+plugged."""

    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    # Create mock trip_manager
    mock_trip_manager = Mock()
    mock_trip_manager.publish_deferrable_loads = AsyncMock()

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

    # Verify recalculation was triggered through publish_deferrable_loads
    mock_trip_manager.publish_deferrable_loads.assert_called_once()
    # Verify _last_processed_soc was updated
    assert monitor._last_processed_soc == 60.0


@pytest.mark.asyncio
async def test_soc_change_below_threshold_skips_recalculation(mock_hass):
    """Test SOC change < 5% does NOT trigger recalculation (debouncing)."""

    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    # Create mock trip_manager
    mock_trip_manager = Mock()
    mock_trip_manager.publish_deferrable_loads = AsyncMock()

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

    # Set _last_processed_soc to simulate previous trigger
    monitor._last_processed_soc = 50.0

    # Process the SOC change event
    await monitor._async_handle_soc_change(event)

    # Verify recalculation was NOT triggered (below 5% threshold)
    mock_trip_manager.publish_deferrable_loads.assert_not_called()
    # Verify _last_processed_soc was NOT updated
    assert monitor._last_processed_soc == 50.0


@pytest.mark.asyncio
async def test_soc_change_when_not_home_skips_recalculation(mock_hass):
    """Test SOC change does NOT trigger recalculation when vehicle not home."""

    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    # Create mock trip_manager
    mock_trip_manager = Mock()
    mock_trip_manager.publish_deferrable_loads = AsyncMock()

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
async def test_soc_change_when_not_plugged_skips_recalculation(mock_hass):
    """Test SOC change does NOT trigger recalculation when vehicle not plugged."""

    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    # Create mock trip_manager
    mock_trip_manager = Mock()
    mock_trip_manager.publish_deferrable_loads = AsyncMock()

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


@pytest.mark.asyncio
async def test_soc_change_with_unavailable_state_skips_without_update(mock_hass):
    """Test SOC change to unavailable/unknown state is skipped without updating _last_processed_soc."""

    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    mock_trip_manager = Mock()
    mock_trip_manager.publish_deferrable_loads = AsyncMock()

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


@pytest.mark.asyncio
async def test_soc_listener_duplicate_setup_prevented(mock_hass):
    """Test SOC listener setup is idempotent - duplicate registration prevented."""
    from unittest.mock import patch

    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    with patch(
        "custom_components.ev_trip_planner.presence_monitor.async_track_state_change_event"
    ) as mock_track:
        mock_track.return_value = Mock()
        monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

        # First call should register
        assert mock_track.call_count == 1

        # Call setup again manually - should NOT register again
        monitor._async_setup_soc_listener()

        # Should still only have been called once (duplicate prevented)
        assert mock_track.call_count == 1


# =============================================================================
# Mutation-Killing Tests — Cover survived mutants
# =============================================================================


@pytest.mark.asyncio
async def test_get_hora_regreso_with_valid_iso(mock_hass):
    """Test async_get_hora_regreso returns datetime when entity has valid hora_regreso_iso."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock entity with valid hora_regreso_iso attribute
    mock_state = Mock()
    mock_state.attributes = {"hora_regreso_iso": "2026-05-01T10:30:00"}
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_get_hora_regreso()

    assert result is not None
    assert result.year == 2026
    assert result.month == 5
    assert result.day == 1
    assert result.hour == 10
    assert result.minute == 30
    mock_hass.states.get.assert_called_once_with(monitor._return_info_entity_id)


@pytest.mark.asyncio
async def test_get_hora_regreso_entity_not_found(mock_hass):
    """Test async_get_hora_regreso returns None when entity doesn't exist."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    mock_hass.states.get = Mock(return_value=None)

    result = await monitor.async_get_hora_regreso()

    assert result is None


@pytest.mark.asyncio
async def test_get_hora_regreso_no_attribute(mock_hass):
    """Test async_get_hora_regreso returns None when attribute is missing."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    mock_state = Mock()
    mock_state.attributes = {}
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_get_hora_regreso()

    assert result is None


@pytest.mark.asyncio
async def test_get_hora_regreso_invalid_datetime(mock_hass):
    """Test async_get_hora_regreso returns None for malformed datetime string."""
    config = {}
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    mock_state = Mock()
    mock_state.attributes = {"hora_regreso_iso": "not-a-valid-datetime"}
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_get_hora_regreso()

    assert result is None


@pytest.mark.asyncio
async def test_soc_change_unknown_state_skips(mock_hass):
    """Test SOC change with 'unknown' state is skipped."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    mock_trip_manager = Mock()
    mock_trip_manager.publish_deferrable_loads = AsyncMock()

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)
    monitor._last_processed_soc = 50.0

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

    old_soc_state = Mock()
    old_soc_state.state = "50"
    new_soc_state = Mock()
    new_soc_state.state = "unknown"

    event = Mock()
    event.data = {"old_state": old_soc_state, "new_state": new_soc_state}

    await monitor._async_handle_soc_change(event)

    mock_trip_manager.publish_deferrable_loads.assert_not_called()
    assert monitor._last_processed_soc == 50.0


@pytest.mark.asyncio
async def test_soc_change_none_string_state_skips(mock_hass):
    """Test SOC change with 'None' string state is skipped."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    mock_trip_manager = Mock()
    mock_trip_manager.publish_deferrable_loads = AsyncMock()

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)
    monitor._last_processed_soc = 50.0

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

    old_soc_state = Mock()
    old_soc_state.state = "50"
    new_soc_state = Mock()
    new_soc_state.state = "None"

    event = Mock()
    event.data = {"old_state": old_soc_state, "new_state": new_soc_state}

    await monitor._async_handle_soc_change(event)

    mock_trip_manager.publish_deferrable_loads.assert_not_called()
    assert monitor._last_processed_soc == 50.0


@pytest.mark.asyncio
async def test_soc_change_empty_state_skips(mock_hass):
    """Test SOC change with empty string state is skipped."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    mock_trip_manager = Mock()
    mock_trip_manager.publish_deferrable_loads = AsyncMock()

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)
    monitor._last_processed_soc = 50.0

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

    old_soc_state = Mock()
    old_soc_state.state = "50"
    new_soc_state = Mock()
    new_soc_state.state = ""

    event = Mock()
    event.data = {"old_state": old_soc_state, "new_state": new_soc_state}

    await monitor._async_handle_soc_change(event)

    mock_trip_manager.publish_deferrable_loads.assert_not_called()
    assert monitor._last_processed_soc == 50.0


@pytest.mark.asyncio
async def test_soc_change_exact_threshold_triggers(mock_hass):
    """Test SOC change exactly at 5% threshold triggers recalculation."""

    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    mock_trip_manager = Mock()
    mock_trip_manager.publish_deferrable_loads = AsyncMock()

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)

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

    # Exactly 5.0% delta: 50% -> 55%
    old_soc_state = Mock()
    old_soc_state.state = "50"
    new_soc_state = Mock()
    new_soc_state.state = "55"

    event = Mock()
    event.data = {"old_state": old_soc_state, "new_state": new_soc_state}

    # Set last_processed_soc to create exactly 5% delta
    monitor._last_processed_soc = 50.0

    await monitor._async_handle_soc_change(event)

    # Exactly 5.0% should NOT be below threshold, so it should trigger
    mock_trip_manager.publish_deferrable_loads.assert_called_once()
    assert monitor._last_processed_soc == 55.0


@pytest.mark.asyncio
async def test_soc_change_first_change_no_last_soc(mock_hass):
    """Test first SOC change (no _last_processed_soc) always triggers."""

    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    mock_trip_manager = Mock()
    mock_trip_manager.publish_deferrable_loads = AsyncMock()

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, mock_trip_manager)
    # _last_processed_soc is None by default (first change)

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

    # Even a small change like 1% should trigger on first event
    old_soc_state = Mock()
    old_soc_state.state = "50"
    new_soc_state = Mock()
    new_soc_state.state = "51"

    event = Mock()
    event.data = {"old_state": old_soc_state, "new_state": new_soc_state}

    await monitor._async_handle_soc_change(event)

    # First change should always trigger regardless of delta
    mock_trip_manager.publish_deferrable_loads.assert_called_once()
    assert monitor._last_processed_soc == 51.0


@pytest.mark.asyncio
async def test_check_plugged_status_true_string(mock_hass):
    """Test plugged status when sensor state is 'true'."""
    config = {
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    mock_state = Mock()
    mock_state.state = "true"
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_plugged_status()

    assert result is True


@pytest.mark.asyncio
async def test_check_plugged_status_yes_string(mock_hass):
    """Test plugged status when sensor state is 'yes'."""
    config = {
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    mock_state = Mock()
    mock_state.state = "yes"
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_plugged_status()

    assert result is True


@pytest.mark.asyncio
async def test_check_plugged_status_connected_string(mock_hass):
    """Test plugged status when sensor state is 'connected'."""
    config = {
        CONF_PLUGGED_SENSOR: "binary_sensor.vehicle_plugged",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    mock_state = Mock()
    mock_state.state = "connected"
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_plugged_status()

    assert result is True


@pytest.mark.asyncio
async def test_check_home_sensor_true_string(mock_hass):
    """Test home status when sensor state is 'true'."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    mock_state = Mock()
    mock_state.state = "true"
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_home_status()

    assert result is True


@pytest.mark.asyncio
async def test_check_home_sensor_yes_string(mock_hass):
    """Test home status when sensor state is 'yes'."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    mock_state = Mock()
    mock_state.state = "yes"
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_home_status()

    assert result is True


@pytest.mark.asyncio
async def test_check_home_sensor_home_string(mock_hass):
    """Test home status when sensor state is 'home'."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    mock_state = Mock()
    mock_state.state = "home"
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_home_status()

    assert result is True


@pytest.mark.asyncio
async def test_handle_return_home_sets_hora_regreso(mock_hass):
    """Test async_handle_return_home sets hora_regreso and soc_en_regreso."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    await monitor.async_handle_return_home(45.5)

    assert monitor.hora_regreso is not None
    assert monitor.soc_en_regreso == 45.5
    # Verify persist was called (entity state updated)
    mock_hass.states.async_set.assert_called_once()


@pytest.mark.asyncio
async def test_handle_return_home_none_soc(mock_hass):
    """Test async_handle_return_home with None SOC."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    await monitor.async_handle_return_home(None)

    assert monitor.hora_regreso is not None
    assert monitor.soc_en_regreso is None


@pytest.mark.asyncio
async def test_persist_return_info_saves_data(mock_hass):
    """Test _async_persist_return_info saves correct data to store and entity."""
    config = {}

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)
    monitor.hora_regreso = "2026-05-01T10:00:00"
    monitor.soc_en_regreso = 55.0

    await monitor._async_persist_return_info()

    # Verify entity state was set
    mock_hass.states.async_set.assert_called_once()
    call_args = mock_hass.states.async_set.call_args
    assert call_args[0][0] == monitor._return_info_entity_id
    assert call_args[0][1] == "2026-05-01T10:00:00"
    attrs = call_args[0][2]
    assert attrs["soc_en_regreso"] == 55.0
    assert attrs["hora_regreso_iso"] == "2026-05-01T10:00:00"
    assert attrs["vehicle_id"] == "test_vehicle"


@pytest.mark.asyncio
async def test_persist_return_info_cleared_state(mock_hass):
    """Test _async_persist_return_info with cleared state (departure)."""
    config = {}

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)
    monitor.hora_regreso = None
    monitor.soc_en_regreso = None

    await monitor._async_persist_return_info()

    mock_hass.states.async_set.assert_called_once()
    call_args = mock_hass.states.async_set.call_args
    assert call_args[0][0] == monitor._return_info_entity_id
    assert call_args[0][1] == "unknown"


@pytest.mark.asyncio
async def test_departure_clears_hora_regreso(mock_hass):
    """Test that departure (on->off transition) clears hora_regreso."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # First check: vehicle is home (sets _was_home = True)
    mock_state_home = Mock()
    mock_state_home.state = "on"
    mock_hass.states.get = Mock(return_value=mock_state_home)
    await monitor.async_check_home_status()

    assert monitor._was_home is True

    # Set hora_regreso manually to simulate a previous return
    monitor.hora_regreso = "2026-05-01T10:00:00"
    monitor.soc_en_regreso = 50.0

    # Second check: vehicle departed (on->off transition)
    mock_state_away = Mock()
    mock_state_away.state = "off"
    mock_hass.states.get = Mock(return_value=mock_state_away)
    result = await monitor.async_check_home_status()

    assert result is False
    assert monitor.hora_regreso is None
    assert monitor.soc_en_regreso is None


@pytest.mark.asyncio
async def test_initial_no_departure_event(mock_hass):
    """Test that initial check with vehicle away does NOT trigger departure."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # First check: vehicle is away (should NOT trigger departure)
    mock_state = Mock()
    mock_state.state = "off"
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_home_status()

    assert result is False
    # No persist should have been called for departure on initial check
    # (hora_regreso was already None, but _async_persist_return_info should NOT be called)
    # states.async_set is only called from _async_persist_return_info
    # On initial away check, no persist should happen
    persist_calls = [
        c
        for c in mock_hass.states.async_set.call_args_list
        if c[0][0] == monitor._return_info_entity_id
    ]
    assert len(persist_calls) == 0


@pytest.mark.asyncio
async def test_return_home_triggers_with_soc(mock_hass):
    """Test return home event captures SOC from sensor."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # First check: away
    mock_state_away = Mock()
    mock_state_away.state = "off"

    mock_soc = Mock()
    mock_soc.state = "65"

    def mock_get_state(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_state_away
        if entity_id == "sensor.ovms_soc":
            return mock_soc
        return None

    mock_hass.states.get = mock_get_state
    await monitor.async_check_home_status()

    # Second check: return home (off->on transition)
    mock_state_home = Mock()
    mock_state_home.state = "on"

    def mock_get_state_home(entity_id):
        if entity_id == "binary_sensor.vehicle_home":
            return mock_state_home
        if entity_id == "sensor.ovms_soc":
            return mock_soc
        return None

    mock_hass.states.get = mock_get_state_home
    result = await monitor.async_check_home_status()

    assert result is True
    assert monitor.soc_en_regreso == 65.0
    assert monitor.hora_regreso is not None


@pytest.mark.asyncio
async def test_check_home_coordinates_no_vehicle_sensor(mock_hass):
    """Test home coordinates check when vehicle sensor is not configured."""
    config = {
        CONF_HOME_COORDINATES: "40.4168,-3.7038",
        # No CONF_VEHICLE_COORDINATES_SENSOR
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    result = await monitor.async_check_home_status()

    # Should use coordinates path, but no vehicle sensor → assume at home
    assert result is True


@pytest.mark.asyncio
async def test_check_home_coordinates_vehicle_state_none(mock_hass):
    """Test home coordinates check when vehicle sensor state is None."""
    config = {
        CONF_HOME_COORDINATES: "40.4168,-3.7038",
        CONF_VEHICLE_COORDINATES_SENSOR: "sensor.vehicle_location",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    mock_state = Mock()
    mock_state.state = None
    mock_hass.states.get = Mock(return_value=mock_state)

    result = await monitor.async_check_home_status()

    # None state should assume at home
    assert result is True


@pytest.mark.asyncio
async def test_soc_change_skipped_when_no_trip_manager(mock_hass):
    """Cover lines 479-484: early return when _trip_manager is None."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
        CONF_SOC_SENSOR: "sensor.ovms_soc",
    }

    # Create monitor WITHOUT a trip_manager (None)
    monitor = PresenceMonitor(mock_hass, "test_vehicle", config, trip_manager=None)

    # Create a mock SOC event
    old_state = Mock()
    old_state.state = "50"
    new_state = Mock()
    new_state.state = "60"
    event = Mock()
    event.data = {"old_state": old_state, "new_state": new_state}

    # Should return early without error (cover lines 479-484)
    import asyncio

    result = monitor._async_handle_soc_change(event)
    if asyncio.iscoroutine(result):
        await result
    # If we got here without exception, the guard at line 479 worked
