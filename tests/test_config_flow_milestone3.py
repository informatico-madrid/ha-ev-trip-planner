"""Tests for Milestone 3 config flow extensions."""

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ev_trip_planner.const import (
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_PLANNING_HORIZON,
    CONF_PLANNING_SENSOR,
    CONF_HOME_SENSOR,
    CONF_PLUGGED_SENSOR,
    CONF_CHARGING_SENSOR,
    CONF_HOME_COORDINATES,
    CONF_VEHICLE_COORDINATES_SENSOR,
    CONF_NOTIFICATION_SERVICE,
    DEFAULT_PLANNING_HORIZON,
    DEFAULT_MAX_DEFERRABLE_LOADS,
    DEFAULT_NOTIFICATION_SERVICE,
    DOMAIN,
)


@pytest.mark.asyncio
async def test_step_emhass_valid_config(hass: HomeAssistant):
    """Test EMHASS step with valid configuration."""
    # Setup
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow
    
    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}
    
    # Execute: Submit planning horizon and max deferrable loads
    result = await flow.async_step_emhass(
        user_input={
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    )
    
    # Verify: Flow continues to presence step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    
    # Verify: Data stored correctly
    assert flow.context["vehicle_data"][CONF_PLANNING_HORIZON] == 7
    assert flow.context["vehicle_data"][CONF_MAX_DEFERRABLE_LOADS] == 50


@pytest.mark.asyncio
async def test_step_emhass_invalid_horizon_too_high(hass: HomeAssistant):
    """Test EMHASS step rejects horizon > 365 days."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {}}

    # Execute: Submit horizon > 365 days
    result = await flow.async_step_emhass(
        user_input={
            CONF_PLANNING_HORIZON: 366,
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    )

    # Verify: Error shown
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    assert "errors" in result
    assert result["errors"]["base"] == "invalid_planning_horizon"


@pytest.mark.asyncio
async def test_step_emhass_invalid_horizon_too_low(hass: HomeAssistant):
    """Test EMHASS step rejects horizon < 1 day."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow
    
    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {}}
    
    # Execute: Submit horizon < 1 day
    result = await flow.async_step_emhass(
        user_input={
            CONF_PLANNING_HORIZON: 0,
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    )
    
    # Verify: Error shown
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    assert "errors" in result
    assert result["errors"]["base"] == "invalid_planning_horizon"


@pytest.mark.asyncio
async def test_step_emhass_invalid_max_loads_too_high(hass: HomeAssistant):
    """Test EMHASS step rejects max loads > 100."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow
    
    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {}}
    
    # Execute: Submit max loads > 100
    result = await flow.async_step_emhass(
        user_input={
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 101,
        }
    )
    
    # Verify: Error shown
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    assert "errors" in result
    assert result["errors"]["base"] == "invalid_max_deferrable_loads"


@pytest.mark.asyncio
async def test_step_emhass_invalid_max_loads_too_low(hass: HomeAssistant):
    """Test EMHASS step rejects max loads < 10."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow
    
    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {}}
    
    # Execute: Submit max loads < 10
    result = await flow.async_step_emhass(
        user_input={
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 9,
        }
    )
    
    # Verify: Error shown
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    assert "errors" in result
    assert result["errors"]["base"] == "invalid_max_deferrable_loads"


@pytest.mark.asyncio
async def test_step_emhass_with_planning_sensor(hass: HomeAssistant):
    """Test EMHASS step with planning sensor entity."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow
    
    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}
    
    # Create a mock sensor entity
    await hass.states.async_set("sensor.test_planning_sensor", "5")
    
    # Execute: Submit with planning sensor
    result = await flow.async_step_emhass(
        user_input={
            CONF_PLANNING_HORIZON: 7,
            CONF_PLANNING_SENSOR: "sensor.test_planning_sensor",
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    )
    
    # Verify: Flow continues and sensor stored
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert flow.context["vehicle_data"][CONF_PLANNING_SENSOR] == "sensor.test_planning_sensor"


@pytest.mark.asyncio
async def test_step_presence_optional_skip(hass: HomeAssistant):
    """Test presence step can be skipped with empty input."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Execute: Skip presence step (empty user_input)
    result = await flow.async_step_presence(user_input={})

    # Verify: Should advance to notifications step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"

    # Now skip notifications step
    result = await flow.async_step_notifications(user_input={})

    # Verify: Entry created without presence sensors
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "test_vehicle"
    assert CONF_HOME_SENSOR not in result["data"]
    assert CONF_PLUGGED_SENSOR not in result["data"]
    assert CONF_CHARGING_SENSOR not in result["data"]


@pytest.mark.asyncio
async def test_step_presence_with_sensors(hass: HomeAssistant):
    """Test presence step with sensor selection."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Create mock binary_sensors
    await hass.states.async_set("binary_sensor.test_charging", "on")
    await hass.states.async_set("binary_sensor.test_home", "on")
    await hass.states.async_set("binary_sensor.test_plugged", "off")

    # Execute: Select sensors
    result = await flow.async_step_presence(
        user_input={
            CONF_CHARGING_SENSOR: "binary_sensor.test_charging",
            CONF_HOME_SENSOR: "binary_sensor.test_home",
            CONF_PLUGGED_SENSOR: "binary_sensor.test_plugged",
        }
    )

    # Verify: Should advance to notifications step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"

    # Now skip notifications step
    result = await flow.async_step_notifications(user_input={})

    # Verify: Sensors stored in config entry
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CHARGING_SENSOR] == "binary_sensor.test_charging"
    assert result["data"][CONF_HOME_SENSOR] == "binary_sensor.test_home"
    assert result["data"][CONF_PLUGGED_SENSOR] == "binary_sensor.test_plugged"


@pytest.mark.asyncio
async def test_step_presence_home_sensor_not_found(hass: HomeAssistant):
    """Test presence step validates home sensor exists."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Create charging sensor but not home sensor
    await hass.states.async_set("binary_sensor.test_charging", "on")

    # Execute: Select non-existent home sensor
    result = await flow.async_step_presence(
        user_input={
            CONF_CHARGING_SENSOR: "binary_sensor.test_charging",
            CONF_HOME_SENSOR: "binary_sensor.nonexistent",
        }
    )

    # Verify: Error shown
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "errors" in result
    assert result["errors"]["base"] == "home_sensor_not_found"


@pytest.mark.asyncio
async def test_step_presence_plugged_sensor_not_found(hass: HomeAssistant):
    """Test presence step validates plugged sensor exists."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Create charging and home sensors but not plugged sensor
    await hass.states.async_set("binary_sensor.test_charging", "on")
    await hass.states.async_set("binary_sensor.test_home", "on")

    # Execute: Select non-existent plugged sensor
    result = await flow.async_step_presence(
        user_input={
            CONF_CHARGING_SENSOR: "binary_sensor.test_charging",
            CONF_HOME_SENSOR: "binary_sensor.test_home",
            CONF_PLUGGED_SENSOR: "binary_sensor.nonexistent_plugged",
        }
    )

    # Verify: Error shown
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "errors" in result
    assert result["errors"]["base"] == "plugged_sensor_not_found"


@pytest.mark.asyncio
async def test_step_presence_with_all_sensors(hass: HomeAssistant):
    """Test presence step with all sensors."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Create all sensors
    await hass.states.async_set("binary_sensor.test_charging", "on")
    await hass.states.async_set("binary_sensor.test_home", "on")
    await hass.states.async_set("binary_sensor.test_plugged", "on")

    # Execute: Provide all presence sensors
    result = await flow.async_step_presence(
        user_input={
            CONF_CHARGING_SENSOR: "binary_sensor.test_charging",
            CONF_HOME_SENSOR: "binary_sensor.test_home",
            CONF_PLUGGED_SENSOR: "binary_sensor.test_plugged",
        }
    )

    # Verify: Should advance to notifications step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"

    # Now skip notifications step
    result = await flow.async_step_notifications(user_input={})

    # Verify: Sensor data stored correctly
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CHARGING_SENSOR] == "binary_sensor.test_charging"
    assert result["data"][CONF_HOME_SENSOR] == "binary_sensor.test_home"
    assert result["data"][CONF_PLUGGED_SENSOR] == "binary_sensor.test_plugged"


@pytest.mark.asyncio
async def test_step_presence_charging_sensor_required(hass: HomeAssistant):
    """Test presence step requires charging sensor."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Execute: Provide only home sensor without charging sensor
    await hass.states.async_set("binary_sensor.test_home", "on")
    result = await flow.async_step_presence(
        user_input={
            CONF_HOME_SENSOR: "binary_sensor.test_home",
        }
    )

    # Verify: Error shown for missing charging sensor
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "errors" in result
    assert result["errors"]["base"] == "charging_sensor_required"


@pytest.mark.asyncio
async def test_step_presence_charging_sensor_not_found(hass: HomeAssistant):
    """Test presence step validates charging sensor exists."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Execute: Select non-existent charging sensor
    result = await flow.async_step_presence(
        user_input={
            CONF_CHARGING_SENSOR: "binary_sensor.nonexistent_charging",
        }
    )

    # Verify: Error shown
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "errors" in result
    assert result["errors"]["base"] == "charging_sensor_not_found"


@pytest.mark.asyncio
async def test_complete_config_flow_with_emhass_and_presence(hass: HomeAssistant):
    """Test complete config flow with all new steps."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Step 1: EMHASS configuration
    result = await flow.async_step_emhass(
        user_input={
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"

    # Step 2: Presence configuration
    await hass.states.async_set("binary_sensor.test_charging", "on")
    await hass.states.async_set("binary_sensor.test_home", "on")
    result = await flow.async_step_presence(
        user_input={
            CONF_CHARGING_SENSOR: "binary_sensor.test_charging",
            CONF_HOME_SENSOR: "binary_sensor.test_home",
        }
    )
    # Should advance to notifications step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"

    # Step 3: Notifications configuration (skip)
    result = await flow.async_step_notifications(user_input={})
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Verify: Complete config stored
    config = result["data"]
    assert config[CONF_PLANNING_HORIZON] == 7
    assert config[CONF_MAX_DEFERRABLE_LOADS] == 50
    assert config[CONF_CHARGING_SENSOR] == "binary_sensor.test_charging"
    assert config[CONF_HOME_SENSOR] == "binary_sensor.test_home"


@pytest.mark.asyncio
async def test_step_notifications_service_not_found(hass: HomeAssistant):
    """Test notifications step validates service exists."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    # Set up mock to return False for non-existent service
    def _mock_has_service(domain, service):
        if domain == "notify":
            # Only allow known services
            return service in ["notify.mobile_app", "notify.persistent_notification"]
        return True
    hass.services.has_service = _mock_has_service

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Execute: Select non-existent notification service
    result = await flow.async_step_notifications(
        user_input={
            CONF_NOTIFICATION_SERVICE: "notify.nonexistent_service",
        }
    )

    # Verify: Error shown
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"
    assert "errors" in result
    assert result["errors"]["notification_service"] == "notification_service_not_found"


@pytest.mark.asyncio
async def test_step_notifications_service_valid(hass: HomeAssistant):
    """Test notifications step accepts valid service."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    # Register a mock notify service
    hass.services.async_register("notify", "test_service", lambda x: None)

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Execute: Select existing notification service
    result = await flow.async_step_notifications(
        user_input={
            CONF_NOTIFICATION_SERVICE: "notify.test_service",
        }
    )

    # Verify: Flow continues to create entry
    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.asyncio
async def test_step_notifications_skip_optional(hass: HomeAssistant):
    """Test notifications step can be skipped."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Execute: Skip notifications step
    result = await flow.async_step_notifications(user_input={})

    # Verify: Flow continues to create entry
    assert result["type"] == FlowResultType.CREATE_ENTRY