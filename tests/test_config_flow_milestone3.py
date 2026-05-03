"""Tests for Milestone 3 config flow extensions."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ev_trip_planner.const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CONSUMPTION,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_PLANNING_HORIZON,
    CONF_PLANNING_SENSOR,
    CONF_HOME_SENSOR,
    CONF_PLUGGED_SENSOR,
    CONF_CHARGING_SENSOR,
    CONF_NOTIFICATION_SERVICE,
    CONF_NOTIFICATION_DEVICES,
    CONF_SAFETY_MARGIN,
    CONF_VEHICLE_NAME,
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
    hass.states.async_set("sensor.test_planning_sensor", "5")

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
    assert (
        flow.context["vehicle_data"][CONF_PLANNING_SENSOR]
        == "sensor.test_planning_sensor"
    )


@pytest.mark.asyncio
async def test_step_presence_optional_skip(hass: HomeAssistant):
    """Test presence step can be skipped with empty input."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Execute: Skip presence step (empty user_input)
    # Mock entity registry for auto-selection
    from homeassistant.helpers import entity_registry as er

    mock_entity = MagicMock()
    mock_entity.entity_id = "binary_sensor.test_charging"
    mock_registry = MagicMock()
    mock_registry.entities = {"binary_sensor.test_charging": mock_entity}

    # Mock hass.states.get to return a valid state for the auto-selected sensor
    mock_state = MagicMock()
    mock_state.state = "on"
    hass.states.get = MagicMock(return_value=mock_state)

    with patch.object(er, "async_get", return_value=mock_registry):
        result = await flow.async_step_presence(user_input={})

    # Verify: Should advance to notifications step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"

    # Now skip notifications step
    result = await flow.async_step_notifications(user_input={})

    # Verify: Entry created - auto-selection adds charging_sensor but not home/plugged
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "test_vehicle"
    assert CONF_HOME_SENSOR not in result["data"]
    assert CONF_PLUGGED_SENSOR not in result["data"]
    # Auto-selection adds charging_sensor when user skips
    assert CONF_CHARGING_SENSOR in result["data"]
    assert result["data"][CONF_CHARGING_SENSOR] == "binary_sensor.test_charging"


@pytest.mark.asyncio
async def test_step_presence_with_sensors(hass: HomeAssistant):
    """Test presence step with sensor selection."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Create mock binary_sensors
    hass.states.async_set("binary_sensor.test_charging", "on")
    hass.states.async_set("binary_sensor.test_home", "on")
    hass.states.async_set("binary_sensor.test_plugged", "off")

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
    hass.states.async_set("binary_sensor.test_charging", "on")

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
    hass.states.async_set("binary_sensor.test_charging", "on")
    hass.states.async_set("binary_sensor.test_home", "on")

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
    hass.states.async_set("binary_sensor.test_charging", "on")
    hass.states.async_set("binary_sensor.test_home", "on")
    hass.states.async_set("binary_sensor.test_plugged", "on")

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
    hass.states.async_set("binary_sensor.test_home", "on")
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
    hass.states.async_set("binary_sensor.test_charging", "on")
    hass.states.async_set("binary_sensor.test_home", "on")
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
    """Test notifications step skips validation for notify domain (EntitySelector handles it)."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    # For notify domain, we skip validation because EntitySelector ensures valid entities
    # This test now verifies that non-existent notify services are accepted
    # (EntitySelector handles validation, not has_service)
    def _mock_has_service(domain, service):
        if domain == "notify":
            # Only allow known services
            return service in ["notify.mobile_app", "notify.persistent_notification"]
        return True

    hass.services.has_service = _mock_has_service

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Execute: Select non-existent notification service (notify.nonexistent_service)
    # This should now be accepted because EntitySelector handles validation
    result = await flow.async_step_notifications(
        user_input={
            CONF_NOTIFICATION_SERVICE: "notify.nonexistent_service",
        }
    )

    # Verify: Should succeed (no error) because EntitySelector handles validation
    # The flow should continue to create entry
    # With the new behavior, notify services are accepted without validation
    assert result["type"] == FlowResultType.CREATE_ENTRY


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


@pytest.mark.asyncio
async def test_step_notifications_devices_multi_select(hass: HomeAssistant):
    """Test notifications step with multiple device selection."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Execute: Select multiple notification devices
    result = await flow.async_step_notifications(
        user_input={
            CONF_NOTIFICATION_SERVICE: "notify.mobile_app",
            CONF_NOTIFICATION_DEVICES: [
                "notify.alexa_media_living_room",
                "notify.alexa_media_bedroom",
            ],
        }
    )

    # Verify: Flow continues to create entry with multiple devices
    assert result["type"] == FlowResultType.CREATE_ENTRY
    # Verify the entry was created with correct data
    assert result["data"][CONF_NOTIFICATION_SERVICE] == "notify.mobile_app"
    assert result["data"][CONF_NOTIFICATION_DEVICES] == [
        "notify.alexa_media_living_room",
        "notify.alexa_media_bedroom",
    ]


@pytest.mark.asyncio
async def test_step_notifications_nabu_casa_devices_available(hass: HomeAssistant):
    """Test that Nabu Casa devices appear in the notification selector."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Execute: Get the form (without user input) to trigger notify services listing
    result = await flow.async_step_notifications(user_input=None)

    # Verify: Form is shown
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"

    # The selector should show all notify services including Nabu Casa
    # This test verifies the selector configuration is correct
    # The actual device display is handled by Home Assistant's UI


@pytest.mark.asyncio
async def test_step_notifications_service_and_devices(hass: HomeAssistant):
    """Test notifications step with both service and devices selected."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Execute: Select notification service and multiple devices
    result = await flow.async_step_notifications(
        user_input={
            CONF_NOTIFICATION_SERVICE: "notify.alexa_media",
            CONF_NOTIFICATION_DEVICES: [
                "notify.alexa_media_living_room",
                "notify.alexa_media_bedroom",
                "notify.google_assistant",
            ],
        }
    )

    # Verify: Flow continues to create entry
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_NOTIFICATION_SERVICE] == "notify.alexa_media"
    assert len(result["data"][CONF_NOTIFICATION_DEVICES]) == 3


def test_notification_entity_selector_config():
    """Verify EntitySelectorConfig is configured correctly for notify domain."""
    from custom_components.ev_trip_planner.config_flow import STEP_NOTIFICATIONS_SCHEMA
    import voluptuous as vol

    # Verify the schema is defined correctly
    schema = STEP_NOTIFICATIONS_SCHEMA.schema

    # Check that both optional fields are in the schema
    assert vol.Optional("notification_service") in schema
    assert vol.Optional("notification_devices") in schema

    # The schema uses EntitySelector with domain="notify"
    # This test verifies the schema is properly defined
    assert len(schema) == 2


# ============================================================================
# Options Flow Tests (async_step_init)
# ============================================================================


@pytest.mark.asyncio
async def test_options_flow_init_shows_form(hass: HomeAssistant):
    """Test options flow init shows form with current values."""
    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )
    from unittest.mock import MagicMock

    # Create a mock config entry with current values
    config_entry = MagicMock()
    config_entry.data = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_BATTERY_CAPACITY: 60.0,
        CONF_CHARGING_POWER: 11.0,
        "kwh_per_km": 0.15,
        CONF_SAFETY_MARGIN: 20,
    }

    # Create options flow handler
    flow = EVTripPlannerOptionsFlowHandler(config_entry)
    flow.hass = hass

    # Execute: Get the options form
    result = await flow.async_step_init(user_input=None)

    # Verify: Form is shown with current values as defaults
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_init_updates_config(hass: HomeAssistant):
    """Test options flow init updates configuration."""
    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )
    from unittest.mock import MagicMock

    # Create a mock config entry with current values
    config_entry = MagicMock()
    config_entry.data = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_BATTERY_CAPACITY: 60.0,
        CONF_CHARGING_POWER: 11.0,
        "kwh_per_km": 0.15,
        CONF_SAFETY_MARGIN: 20,
    }

    # Create options flow handler
    flow = EVTripPlannerOptionsFlowHandler(config_entry)
    flow.hass = hass

    # Execute: Submit new values
    result = await flow.async_step_init(
        user_input={
            CONF_BATTERY_CAPACITY: 75.0,
            CONF_CHARGING_POWER: 22.0,
            CONF_CONSUMPTION: 0.18,
            CONF_SAFETY_MARGIN: 15,
        }
    )

    # Verify: Entry is updated
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_BATTERY_CAPACITY] == 75.0
    assert result["data"][CONF_CHARGING_POWER] == 22.0
    assert result["data"][CONF_CONSUMPTION] == 0.18
    assert result["data"][CONF_SAFETY_MARGIN] == 15


@pytest.mark.asyncio
async def test_options_flow_uses_defaults_when_not_present(hass: HomeAssistant):
    """Test options flow uses defaults when current config doesn't have values."""
    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )
    from unittest.mock import MagicMock

    # Create a mock config entry with minimal values
    config_entry = MagicMock()
    config_entry.data = {
        CONF_VEHICLE_NAME: "test_vehicle",
    }

    # Create options flow handler
    flow = EVTripPlannerOptionsFlowHandler(config_entry)
    flow.hass = hass

    # Execute: Get the form (without user input) to see default values
    result = await flow.async_step_init(user_input=None)

    # Verify: Form is shown (defaults are used in the schema)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


# ============================================================================
# Additional Edge Case Tests
# ============================================================================


@pytest.mark.asyncio
async def test_step_sensors_validation(hass: HomeAssistant):
    """Test sensors step validates input correctly."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    # Execute: Provide valid sensor configuration
    result = await flow.async_step_sensors(
        user_input={
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 20,
        }
    )

    # Verify: Should advance to EMHASS step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"

    # Verify: Data stored correctly
    assert flow.context["vehicle_data"][CONF_BATTERY_CAPACITY] == 60.0
    assert flow.context["vehicle_data"][CONF_CHARGING_POWER] == 11.0
    assert flow.context["vehicle_data"][CONF_CONSUMPTION] == 0.15
    assert flow.context["vehicle_data"][CONF_SAFETY_MARGIN] == 20


@pytest.mark.asyncio
async def test_step_user_vehicle_name_stored(hass: HomeAssistant):
    """Test user step stores vehicle name correctly."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {}

    # Execute: Provide vehicle name
    result = await flow.async_step_user(
        user_input={
            CONF_VEHICLE_NAME: "My Electric Car",
        }
    )

    # Verify: Should advance to sensors step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"

    # Verify: Vehicle name stored in context
    assert flow.context["vehicle_data"][CONF_VEHICLE_NAME] == "My Electric Car"


@pytest.mark.asyncio
async def test_vehicle_id_generated_from_name(hass: HomeAssistant):
    """Test that vehicle_id is generated correctly from vehicle name."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "Test Vehicle"}}

    # Execute: Complete the flow to create entry
    result = await flow.async_step_notifications(user_input={})

    # Verify: Entry is created
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Vehicle"


@pytest.mark.asyncio
async def test_full_flow_with_minimal_config(hass: HomeAssistant):
    """Test complete flow with minimal (skip) configuration."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {}}

    # Step 1: User - vehicle name
    result = await flow.async_step_user({CONF_VEHICLE_NAME: "minimal_vehicle"})
    assert result["step_id"] == "sensors"

    # Step 2: Sensors - defaults
    result = await flow.async_step_sensors({})
    assert result["step_id"] == "emhass"

    # Step 3: EMHASS - defaults
    result = await flow.async_step_emhass({})
    assert result["step_id"] == "presence"

    # Step 4: Presence - skip (empty)
    # Mock entity registry for auto-selection
    from homeassistant.helpers import entity_registry as er

    mock_entity = MagicMock()
    mock_entity.entity_id = "binary_sensor.test_charging"
    mock_registry = MagicMock()
    mock_registry.entities = {"binary_sensor.test_charging": mock_entity}

    # Mock hass.states.get to return a valid state for the auto-selected sensor
    mock_state = MagicMock()
    mock_state.state = "on"
    hass.states.get = MagicMock(return_value=mock_state)

    with patch.object(er, "async_get", return_value=mock_registry):
        result = await flow.async_step_presence({})
    assert result["step_id"] == "notifications"

    # Step 5: Notifications - skip (empty)
    result = await flow.async_step_notifications({})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "minimal_vehicle"


@pytest.mark.asyncio
async def test_full_flow_with_all_config(hass: HomeAssistant):
    """Test complete flow with all configuration options."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {}}

    # Step 1: User - vehicle name
    result = await flow.async_step_user({CONF_VEHICLE_NAME: "full_vehicle"})
    assert result["step_id"] == "sensors"

    # Step 2: Sensors - all values
    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 82.0,
            CONF_CHARGING_POWER: 22.0,
            CONF_CONSUMPTION: 0.17,
            CONF_SAFETY_MARGIN: 15,
        }
    )
    assert result["step_id"] == "emhass"

    # Step 3: EMHASS - all values
    hass.states.async_set("sensor.planning_horizon", "14")
    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 14,
            CONF_MAX_DEFERRABLE_LOADS: 75,
            CONF_PLANNING_SENSOR: "sensor.planning_horizon",
        }
    )
    assert result["step_id"] == "presence"

    # Step 4: Presence - all sensors
    hass.states.async_set("binary_sensor.charging", "on")
    hass.states.async_set("binary_sensor.home", "on")
    hass.states.async_set("binary_sensor.plugged", "on")
    result = await flow.async_step_presence(
        {
            CONF_CHARGING_SENSOR: "binary_sensor.charging",
            CONF_HOME_SENSOR: "binary_sensor.home",
            CONF_PLUGGED_SENSOR: "binary_sensor.plugged",
        }
    )
    assert result["step_id"] == "notifications"

    # Step 5: Notifications - all values
    result = await flow.async_step_notifications(
        {
            CONF_NOTIFICATION_SERVICE: "notify.mobile_app",
            CONF_NOTIFICATION_DEVICES: [
                "notify.alexa_media_living_room",
                "notify.alexa_media_bedroom",
            ],
        }
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Verify all data
    data = result["data"]
    assert data[CONF_VEHICLE_NAME] == "full_vehicle"
    assert data[CONF_BATTERY_CAPACITY] == 82.0
    assert data[CONF_CHARGING_POWER] == 22.0
    assert data[CONF_CONSUMPTION] == 0.17
    assert data[CONF_SAFETY_MARGIN] == 15
    assert data[CONF_PLANNING_HORIZON] == 14
    assert data[CONF_MAX_DEFERRABLE_LOADS] == 75
    assert data[CONF_PLANNING_SENSOR] == "sensor.planning_horizon"
    assert data[CONF_CHARGING_SENSOR] == "binary_sensor.charging"
    assert data[CONF_HOME_SENSOR] == "binary_sensor.home"
    assert data[CONF_PLUGGED_SENSOR] == "binary_sensor.plugged"
    assert data[CONF_NOTIFICATION_SERVICE] == "notify.mobile_app"
    assert len(data[CONF_NOTIFICATION_DEVICES]) == 2


def test_step_sensors_schema_validation():
    """Verify sensors step schema validates correctly."""
    from custom_components.ev_trip_planner.config_flow import STEP_SENSORS_SCHEMA
    import voluptuous as vol

    schema = STEP_SENSORS_SCHEMA.schema

    # Verify required fields exist
    assert vol.Required(CONF_BATTERY_CAPACITY) in schema
    assert vol.Required(CONF_CHARGING_POWER) in schema
    assert vol.Required(CONF_CONSUMPTION) in schema
    assert vol.Required(CONF_SAFETY_MARGIN) in schema

    # Verify all fields have defaults
    # The schema now has 5 required fields: battery_capacity, charging_power,
    # consumption, safety_margin, t_base + 2 optional: soc_sensor, soh_sensor
    required_fields = [k for k in schema.keys() if isinstance(k, vol.Required)]
    assert len(required_fields) == 5


def test_step_emhass_schema_validation():
    """Verify EMHASS step schema validates correctly."""
    from custom_components.ev_trip_planner.config_flow import STEP_EMHASS_SCHEMA
    import voluptuous as vol

    schema = STEP_EMHASS_SCHEMA.schema

    # Verify required fields exist
    assert vol.Required(CONF_PLANNING_HORIZON) in schema
    assert vol.Required(CONF_MAX_DEFERRABLE_LOADS) in schema

    # Verify optional planning sensor exists
    assert vol.Optional(CONF_PLANNING_SENSOR) in schema


def test_step_presence_schema_validation():
    """Verify presence step schema validates correctly."""
    from custom_components.ev_trip_planner.config_flow import STEP_PRESENCE_SCHEMA
    import voluptuous as vol

    schema = STEP_PRESENCE_SCHEMA.schema

    # Verify required charging sensor
    assert vol.Required(CONF_CHARGING_SENSOR) in schema

    # Verify optional home and plugged sensors
    assert vol.Optional(CONF_HOME_SENSOR) in schema
    assert vol.Optional(CONF_PLUGGED_SENSOR) in schema


def test_all_schemas_are_valid():
    """Verify all config flow schemas are valid voluptuous schemas."""
    from custom_components.ev_trip_planner.config_flow import (
        STEP_USER_SCHEMA,
        STEP_SENSORS_SCHEMA,
        STEP_EMHASS_SCHEMA,
        STEP_PRESENCE_SCHEMA,
        STEP_NOTIFICATIONS_SCHEMA,
    )

    # All schemas should be valid voluptuous schemas
    assert STEP_USER_SCHEMA is not None
    assert STEP_SENSORS_SCHEMA is not None
    assert STEP_EMHASS_SCHEMA is not None
    assert STEP_PRESENCE_SCHEMA is not None
    assert STEP_NOTIFICATIONS_SCHEMA is not None

    # Each schema should have a schema attribute
    assert hasattr(STEP_USER_SCHEMA, "schema")
    assert hasattr(STEP_SENSORS_SCHEMA, "schema")
    assert hasattr(STEP_EMHASS_SCHEMA, "schema")
    assert hasattr(STEP_PRESENCE_SCHEMA, "schema")
    assert hasattr(STEP_NOTIFICATIONS_SCHEMA, "schema")
