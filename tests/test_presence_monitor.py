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
)


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.states = Mock()
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    return hass


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


@pytest.mark.asyncio
async def test_check_home_status_sensor_not_found(mock_hass):
    """Test home status check when sensor doesn't exist."""
    config = {
        CONF_HOME_SENSOR: "binary_sensor.vehicle_home",
    }

    monitor = PresenceMonitor(mock_hass, "test_vehicle", config)

    # Mock hass.states.get to return None (sensor not found)
    mock_hass.states.get = Mock(return_value=None)

    # Should return False (assume not home) when sensor not found
    result = await monitor.async_check_home_status()

    assert result is False