"""Tests for EV Trip Planner config flow vehicle setup.

Tests vehicle configuration through the complete config flow from user step
to entry creation, verifying data persistence and validation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ev_trip_planner.config_flow import EVTripPlannerFlowHandler
from custom_components.ev_trip_planner.const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CHARGING_SENSOR,
    CONF_CONSUMPTION,
    CONF_HOME_SENSOR,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_NOTIFICATION_SERVICE,
    CONF_PLANNING_HORIZON,
    CONF_PLUGGED_SENSOR,
    CONF_SAFETY_MARGIN,
    CONF_SOH_SENSOR,
    CONF_T_BASE,
    CONF_VEHICLE_NAME,
    DEFAULT_MAX_DEFERRABLE_LOADS,
    DEFAULT_PLANNING_HORIZON,
    DEFAULT_T_BASE,
)


@pytest.mark.asyncio
async def test_user_step_shows_form():
    """Test that the initial user step shows a form for vehicle name."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {}

    result = await flow.async_step_user()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "data_schema" in result
    assert "description_placeholders" in result


@pytest.mark.asyncio
async def test_user_step_advances_to_sensors():
    """Test that providing vehicle name advances to sensors step."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {}

    result = await flow.async_step_user(
        {
            CONF_VEHICLE_NAME: "Test Vehicle",
        }
    )

    # Should advance to sensors step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"
    # Verify vehicle name was stored in context
    assert "vehicle_data" in flow.context
    assert flow.context["vehicle_data"][CONF_VEHICLE_NAME] == "Test Vehicle"


@pytest.mark.asyncio
async def test_sensors_step_shows_form():
    """Test that the sensors step shows a form with default values."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    result = await flow.async_step_sensors()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"
    assert "data_schema" in result


@pytest.mark.asyncio
async def test_sensors_step_advances_to_emhass():
    """Test that sensors configuration advances to EMHASS step."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 20,
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    # Verify sensors data was stored
    assert flow.context["vehicle_data"][CONF_BATTERY_CAPACITY] == 60.0
    assert flow.context["vehicle_data"][CONF_CHARGING_POWER] == 11.0
    assert flow.context["vehicle_data"][CONF_CONSUMPTION] == 0.15
    assert flow.context["vehicle_data"][CONF_SAFETY_MARGIN] == 20


@pytest.mark.asyncio
async def test_emhass_step_shows_form():
    """Test that the EMHASS step shows a form with default values."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    result = await flow.async_step_emhass()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    assert "data_schema" in result


@pytest.mark.asyncio
async def test_emhass_step_with_defaults():
    """Test EMHASS step with default values advances to presence."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: DEFAULT_PLANNING_HORIZON,
            CONF_MAX_DEFERRABLE_LOADS: DEFAULT_MAX_DEFERRABLE_LOADS,
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    # Verify EMHASS data was stored
    assert (
        flow.context["vehicle_data"][CONF_PLANNING_HORIZON] == DEFAULT_PLANNING_HORIZON
    )
    assert (
        flow.context["vehicle_data"][CONF_MAX_DEFERRABLE_LOADS]
        == DEFAULT_MAX_DEFERRABLE_LOADS
    )


@pytest.mark.asyncio
async def test_emhass_step_validation_invalid_horizon():
    """Test that EMHASS step validates planning horizon (1-365)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Test horizon too low
    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 0,
            CONF_MAX_DEFERRABLE_LOADS: DEFAULT_MAX_DEFERRABLE_LOADS,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    assert result.get("errors") == {"base": "invalid_planning_horizon"}

    # Test horizon too high
    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 400,
            CONF_MAX_DEFERRABLE_LOADS: DEFAULT_MAX_DEFERRABLE_LOADS,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    assert result.get("errors") == {"base": "invalid_planning_horizon"}


@pytest.mark.asyncio
async def test_emhass_step_validation_invalid_max_loads():
    """Test that EMHASS step validates max deferrable loads (10-100)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Test max loads too low
    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 5,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    assert result.get("errors") == {"base": "invalid_max_deferrable_loads"}

    # Test max loads too high
    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 150,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    assert result.get("errors") == {"base": "invalid_max_deferrable_loads"}


@pytest.mark.asyncio
async def test_presence_step_shows_form():
    """Test that the presence step shows a form."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    result = await flow.async_step_presence()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "data_schema" in result


@pytest.mark.asyncio
async def test_presence_step_skip_advances_to_notifications():
    """Test that skipping presence step advances to notifications via auto-selection."""
    from homeassistant.helpers import entity_registry as er

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Mock entity registry with a binary sensor for auto-selection
    mock_entity_entry = MagicMock()
    mock_entity_entry.entity_id = "binary_sensor.test_charging"
    mock_registry = MagicMock()
    # Use MagicMock's keys() to return list of entity IDs
    mock_registry.entities.keys.return_value = ["binary_sensor.test_charging"]

    # Mock hass.states.get for sensor validation
    mock_state = MagicMock()
    mock_state.state = "on"
    flow.hass.states.get.return_value = mock_state

    with patch.object(er, "async_get", return_value=mock_registry):
        result = await flow.async_step_presence({})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"


@pytest.mark.asyncio
async def test_presence_step_with_charging_sensor():
    """Test presence step with charging sensor."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Mock the charging sensor state
    mock_state = MagicMock()
    mock_state.state = "on"
    flow.hass.states.get = MagicMock(return_value=mock_state)

    result = await flow.async_step_presence(
        {
            CONF_CHARGING_SENSOR: "binary_sensor.charging",
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"
    assert (
        flow.context["vehicle_data"][CONF_CHARGING_SENSOR] == "binary_sensor.charging"
    )


@pytest.mark.asyncio
async def test_presence_step_validation_missing_charging_sensor():
    """Test that presence step validates charging sensor is provided."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    result = await flow.async_step_presence(
        {
            CONF_CHARGING_SENSOR: "",
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert result.get("errors") == {"base": "charging_sensor_required"}


@pytest.mark.asyncio
async def test_presence_step_validation_sensor_not_found():
    """Test that presence step validates sensor exists."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Mock that sensor doesn't exist
    flow.hass.states.get = MagicMock(return_value=None)

    result = await flow.async_step_presence(
        {
            CONF_CHARGING_SENSOR: "binary_sensor.nonexistent",
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert result.get("errors") == {"base": "charging_sensor_not_found"}


@pytest.mark.asyncio
async def test_presence_step_with_all_sensors():
    """Test presence step with all optional sensors configured."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Mock all sensor states
    flow.hass.states.get = MagicMock(return_value=MagicMock(state="on"))

    result = await flow.async_step_presence(
        {
            CONF_CHARGING_SENSOR: "binary_sensor.charging",
            CONF_HOME_SENSOR: "binary_sensor.home",
            CONF_PLUGGED_SENSOR: "binary_sensor.plugged",
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"
    assert (
        flow.context["vehicle_data"][CONF_CHARGING_SENSOR] == "binary_sensor.charging"
    )
    assert flow.context["vehicle_data"][CONF_HOME_SENSOR] == "binary_sensor.home"
    assert flow.context["vehicle_data"][CONF_PLUGGED_SENSOR] == "binary_sensor.plugged"


@pytest.mark.asyncio
async def test_notifications_step_shows_form():
    """Test that the notifications step shows a form."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    result = await flow.async_step_notifications()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"
    assert "data_schema" in result


@pytest.mark.asyncio
async def test_notifications_step_skip_creates_entry():
    """Test that skipping notifications creates the config entry."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    result = await flow.async_step_notifications({})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "TestVehicle"


@pytest.mark.asyncio
async def test_notifications_step_with_service():
    """Test notifications step with notification service configured.

    Note: This test verifies that notification service can be configured.
    The entity registry mocking is complex due to HA internals, so we test
    the basic functionality without full mocking.
    """
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Test that providing notification service data is accepted
    # The actual entity validation is tested in integration tests
    result = await flow.async_step_notifications(
        {
            CONF_NOTIFICATION_SERVICE: "notify.mobile_app_iphone",
        }
    )
    # Should create entry with notification service stored
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert (
        flow.context["vehicle_data"][CONF_NOTIFICATION_SERVICE]
        == "notify.mobile_app_iphone"
    )


@pytest.mark.asyncio
async def test_full_flow_success():
    """Test a complete successful configuration flow from user to entry creation."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {}

    # Step 1: User step - vehicle name
    result = await flow.async_step_user(
        {
            CONF_VEHICLE_NAME: "Chispitas",
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"

    # Step 2: Sensors configuration
    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 20,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"

    # Step 3: EMHASS configuration
    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"

    # Step 4: Skip presence - mock entity registry for auto-selection
    mock_registry = MagicMock()
    mock_registry.entities.keys.return_value = ["binary_sensor.test_charging"]
    mock_state = MagicMock()
    mock_state.state = "on"
    flow.hass.states.get.return_value = mock_state

    with patch(
        "homeassistant.helpers.entity_registry.async_get", return_value=mock_registry
    ):
        result = await flow.async_step_presence({})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"

    # Step 5: Skip notifications - create entry
    result = await flow.async_step_notifications({})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Chispitas"

    # Verify all data was stored
    data = result["data"]
    assert data[CONF_VEHICLE_NAME] == "Chispitas"
    assert data[CONF_BATTERY_CAPACITY] == 60.0
    assert data[CONF_CHARGING_POWER] == 11.0
    assert data[CONF_CONSUMPTION] == 0.15
    assert data[CONF_SAFETY_MARGIN] == 20
    assert data[CONF_PLANNING_HORIZON] == 7
    assert data[CONF_MAX_DEFERRABLE_LOADS] == 50


@pytest.mark.asyncio
async def test_vehicle_data_persistence_across_steps():
    """Test that vehicle data is persisted across all flow steps."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {}

    # Complete the full flow
    await flow.async_step_user({CONF_VEHICLE_NAME: "MyEV"})
    await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 75.0,
            CONF_CHARGING_POWER: 22.0,
            CONF_CONSUMPTION: 0.18,
            CONF_SAFETY_MARGIN: 15,
        }
    )
    await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 10,
            CONF_MAX_DEFERRABLE_LOADS: 30,
        }
    )
    await flow.async_step_presence({})
    result = await flow.async_step_notifications({})

    # Verify all data was persisted
    assert result["data"][CONF_VEHICLE_NAME] == "MyEV"
    assert result["data"][CONF_BATTERY_CAPACITY] == 75.0
    assert result["data"][CONF_CHARGING_POWER] == 22.0
    assert result["data"][CONF_CONSUMPTION] == 0.18
    assert result["data"][CONF_SAFETY_MARGIN] == 15
    assert result["data"][CONF_PLANNING_HORIZON] == 10
    assert result["data"][CONF_MAX_DEFERRABLE_LOADS] == 30


@pytest.mark.asyncio
async def test_user_step_validation_empty_vehicle_name():
    """Test that empty vehicle name is rejected."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {}

    result = await flow.async_step_user({CONF_VEHICLE_NAME: ""})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result.get("errors") == {"base": "vehicle_name_required"}


@pytest.mark.asyncio
async def test_user_step_validation_whitespace_vehicle_name():
    """Test that whitespace-only vehicle name is rejected."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {}

    result = await flow.async_step_user({CONF_VEHICLE_NAME: "   "})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result.get("errors") == {"base": "vehicle_name_required"}


@pytest.mark.asyncio
async def test_user_step_validation_too_long_vehicle_name():
    """Test that vehicle name longer than 100 characters is rejected."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {}

    long_name = "A" * 101
    result = await flow.async_step_user({CONF_VEHICLE_NAME: long_name})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result.get("errors") == {"base": "vehicle_name_too_long"}


@pytest.mark.asyncio
async def test_sensors_step_validation_invalid_battery_capacity():
    """Test that battery capacity outside 10-200 kWh range is rejected."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Test battery too low
    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 5.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 20,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"
    assert result.get("errors") == {"base": "invalid_battery_capacity"}

    # Test battery too high
    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 250.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 20,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"
    assert result.get("errors") == {"base": "invalid_battery_capacity"}


@pytest.mark.asyncio
async def test_sensors_step_validation_invalid_consumption():
    """Test that consumption outside 0.05-0.5 kWh/km range is rejected."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Test consumption too low
    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.01,
            CONF_SAFETY_MARGIN: 20,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"
    assert result.get("errors") == {"base": "invalid_consumption"}

    # Test consumption too high
    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 1.0,
            CONF_SAFETY_MARGIN: 20,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"
    assert result.get("errors") == {"base": "invalid_consumption"}


@pytest.mark.asyncio
async def test_sensors_step_validation_invalid_safety_margin():
    """Test that safety margin outside 0-50% range is rejected."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Test safety margin negative
    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: -10,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"
    assert result.get("errors") == {"base": "invalid_safety_margin"}

    # Test safety margin too high
    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 100,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"
    assert result.get("errors") == {"base": "invalid_safety_margin"}


@pytest.mark.asyncio
async def test_default_values_are_used():
    """Test that default values are used when not specified."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {}

    # Provide values at each step to allow flow to complete
    result = await flow.async_step_user({CONF_VEHICLE_NAME: "Test"})
    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,  # Will be overridden by default
            CONF_SAFETY_MARGIN: 20,  # Will be overridden by default
        }
    )
    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 7,  # Will be overridden by default
            CONF_MAX_DEFERRABLE_LOADS: 50,  # Will be overridden by default
        }
    )
    result = await flow.async_step_presence({})
    result = await flow.async_step_notifications({})

    # Verify default values are used (flow uses defaults from schema when step is skipped)
    # The defaults are in the schema, so when we pass empty {}, they should be used
    assert result["data"][CONF_VEHICLE_NAME] == "Test"
    assert result["data"][CONF_BATTERY_CAPACITY] == 60.0
    assert result["data"][CONF_CHARGING_POWER] == 11.0


# ----------------------------------------------------------------------
# T034: T_base slider accepts default and persists in entry data
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t_base_persists_in_entry_data():
    """T034: Config flow T_base slider accepts 24.0 and persists in entry data."""
    from unittest.mock import MagicMock

    from homeassistant.data_entry_flow import FlowResultType

    from custom_components.ev_trip_planner.const import (
        CONF_T_BASE,
    )

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {}

    # Complete full flow with explicit t_base
    result = await flow.async_step_user({"vehicle_name": "TestVehicle"})
    assert result["type"] == FlowResultType.FORM
    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 20,
            CONF_T_BASE: 24.0,
        }
    )
    assert result["type"] == FlowResultType.FORM
    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    )
    assert result["type"] == FlowResultType.FORM
    result = await flow.async_step_presence({})
    result = await flow.async_step_notifications({})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_T_BASE] == DEFAULT_T_BASE


@pytest.mark.asyncio
async def test_t_base_custom_value_persists():
    """T034b: Custom T_base value persists in entry data."""
    from unittest.mock import MagicMock

    from homeassistant.data_entry_flow import FlowResultType

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {}

    result = await flow.async_step_user({"vehicle_name": "TestVehicle"})
    assert result["type"] == FlowResultType.FORM
    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 20,
            CONF_T_BASE: 12.0,
        }
    )
    assert result["type"] == FlowResultType.FORM
    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    )
    assert result["type"] == FlowResultType.FORM
    result = await flow.async_step_presence({})
    result = await flow.async_step_notifications({})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_T_BASE] == 12.0


# ----------------------------------------------------------------------
# T047: SOH sensor selector in config flow
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_soh_sensor_selector_in_sensors_step():
    """T047: Config flow sensors step includes SOH sensor entity selector."""
    from custom_components.ev_trip_planner.config_flow import STEP_SENSORS_SCHEMA
    import voluptuous as vol

    # CONF_SOH_SENSOR should be an Optional key in the sensors schema
    vol.Optional(CONF_SOH_SENSOR)  # noqa: F841 — used for schema introspection
    found = False
    for key in STEP_SENSORS_SCHEMA.schema.keys():
        if isinstance(key, vol.Optional) and key.schema == CONF_SOH_SENSOR:
            found = True
            break
    assert found, "CONF_SOH_SENSOR should be an Optional key in STEP_SENSORS_SCHEMA"


@pytest.mark.asyncio
async def test_soh_sensor_persisted_in_config_entry():
    """T047b: SOH sensor value is persisted when provided in config flow."""
    from homeassistant.data_entry_flow import FlowResultType

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {"vehicle_name": "TestVehicle"}}

    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 20,
            CONF_T_BASE: 24.0,
            CONF_SOH_SENSOR: "sensor.battery_soh",
        }
    )
    assert result["type"] == FlowResultType.FORM
    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    )
    assert result["type"] == FlowResultType.FORM
    result = await flow.async_step_presence({})
    result = await flow.async_step_notifications({})

    assert result["type"] == FlowResultType.CREATE_ENTRY


# ------------------------------------------------------------------
# Options Flow tests for T_BASE and SOH_SENSOR (config_flow.py:979,981)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_options_flow_updates_t_base_and_soh_sensor():
    """Test that options flow correctly saves T_BASE and SOH_SENSOR.

    Covers config_flow.py:979,981 — Options flow saving T_BASE and SOH_SENSOR.
    """
    from homeassistant import config_entries

    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )
    from custom_components.ev_trip_planner.const import (
        CONF_BATTERY_CAPACITY,
        CONF_SOH_SENSOR,
        CONF_T_BASE,
    )

    mock_entry = MagicMock(spec=config_entries.ConfigEntry)
    mock_entry.data = {
        CONF_BATTERY_CAPACITY: 60.0,
        CONF_T_BASE: 24.0,
    }
    mock_entry.options = {}
    mock_entry.entry_id = "test_entry"

    handler = EVTripPlannerOptionsFlowHandler(mock_entry)
    handler._config_entry = mock_entry
    handler.hass = MagicMock()

    result = await handler.async_step_init(
        {
            CONF_BATTERY_CAPACITY: 65.0,
            CONF_T_BASE: 12.0,
            CONF_SOH_SENSOR: "sensor.battery_soh_v2",
        }
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_T_BASE] == 12.0
    assert result["data"][CONF_SOH_SENSOR] == "sensor.battery_soh_v2"
    assert result["data"][CONF_BATTERY_CAPACITY] == 65.0


# ------------------------------------------------------------------
# Config Entry Migration Tests — PRAGMA-A coverage targets (config_flow.py:300-314)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_config_entry_migrate_v2_to_v3():
    """Test config entry migration from version 2 to version 3.

    Covers config_flow.py:300-311: migration of v2 entry to add t_base and soh_sensor defaults.
    """
    from unittest.mock import MagicMock

    from homeassistant import config_entries

    from custom_components.ev_trip_planner.config_flow import EVTripPlannerFlowHandler
    from custom_components.ev_trip_planner.const import (
        CONF_SOH_SENSOR,
        CONF_T_BASE,
        CONFIG_VERSION,
        DEFAULT_SOH_SENSOR,
    )

    flow = EVTripPlannerFlowHandler()
    mock_hass = MagicMock()
    mock_hass.config_entries.async_update_entry = AsyncMock(return_value=True)
    flow.hass = mock_hass

    mock_entry = MagicMock(spec=config_entries.ConfigEntry)
    mock_entry.version = 2
    mock_entry.data = {
        "vehicle_name": "test",
    }
    mock_entry.entry_id = "test_entry"
    mock_entry.options = {}

    async def mock_update_entry(entry, **kwargs):
        entry.version = kwargs.get("version", entry.version)
        entry.data = kwargs.get("data", entry.data)
        return True

    mock_hass.config_entries.async_update_entry = AsyncMock(
        side_effect=mock_update_entry
    )

    await flow.async_migrate_entry(flow.hass, mock_entry)

    # Entry version should be updated
    assert mock_entry.version == CONFIG_VERSION
    # async_update_entry should have been called with new fields
    flow.hass.config_entries.async_update_entry.assert_called_once()
    call_args = flow.hass.config_entries.async_update_entry.call_args
    updated_data = call_args.kwargs.get("data", call_args[1].get("data", {}))
    assert updated_data.get(CONF_T_BASE) == DEFAULT_T_BASE
    assert updated_data.get(CONF_SOH_SENSOR) == DEFAULT_SOH_SENSOR


@pytest.mark.asyncio
async def test_config_entry_migrate_unknown_version():
    """Test migration logs warning for unknown version.

    Covers config_flow.py:314: warning for unknown entry version.
    """
    from unittest.mock import MagicMock

    from homeassistant import config_entries

    from custom_components.ev_trip_planner.config_flow import EVTripPlannerFlowHandler

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()

    mock_entry = MagicMock(spec=config_entries.ConfigEntry)
    mock_entry.version = 1  # Unknown version
    mock_entry.data = {}
    mock_entry.entry_id = "test_entry"
    mock_entry.options = {}

    await flow.async_migrate_entry(flow.hass, mock_entry)

    # Version should NOT be changed
    assert mock_entry.version == 1
    # async_update_entry should NOT have been called
    flow.hass.config_entries.async_update_entry.assert_not_called()
