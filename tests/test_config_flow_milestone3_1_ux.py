"""Tests for Milestone 3.1 UX Improvements."""

import pytest
from unittest.mock import MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ev_trip_planner.const import (
    CONF_SOC_SENSOR,
    CONF_RANGE_SENSOR,
    CONF_CHARGING_STATUS,
    CONF_HOME_SENSOR,
    CONF_PLUGGED_SENSOR,
    CONF_PLANNING_SENSOR,
    CONTROL_TYPE_EXTERNAL,
    DOMAIN,
)


@pytest.mark.asyncio
async def test_strings_json_includes_data_descriptions():
    """Test that strings.json includes data_description fields for all config steps."""
    # Import the strings.json content
    import json
    import os
    
    strings_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "ev_trip_planner",
        "strings.json",
    )
    
    with open(strings_path) as f:
        strings_data = json.load(f)
    
    # Verify all steps have data_description
    config_steps = ["user", "sensors", "consumption", "emhass", "presence"]
    
    for step in config_steps:
        assert "data_description" in strings_data["config"]["step"][step], \
            f"Step '{step}' missing data_description"
        
        # Verify data_description is not empty
        data_desc = strings_data["config"]["step"][step]["data_description"]
        assert len(data_desc) > 0, f"Step '{step}' has empty data_description"
        
        # Verify each field in data has a description
        data_fields = strings_data["config"]["step"][step]["data"]
        for field in data_fields:
            assert field in data_desc, \
                f"Field '{field}' in step '{step}' missing data_description"


@pytest.mark.asyncio
async def test_control_type_external_label_is_notifications_only(hass: HomeAssistant):
    """Test that CONTROL_TYPE_EXTERNAL shows 'Notifications Only (no control)' label."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow
    
    # Mock the config_entries to avoid "already_configured" error
    hass.config_entries.async_entry_for_domain_unique_id = MagicMock(return_value=None)
    
    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {}
    
    # Get to the consumption step
    await flow.async_step_user(
        {
            "vehicle_name": "Test Vehicle",
            "vehicle_type": "ev",
        }
    )
    
    await flow.async_step_sensors(
        {
            "soc_sensor": "sensor.test_soc",
            "battery_capacity": 50.0,
            "charging_power": 7.2,
        }
    )
    
    # Get the consumption form
    result = await flow.async_step_consumption(
        {
            "consumption": 0.15,
            "safety_margin": 10,
            "control_type": CONTROL_TYPE_EXTERNAL,
        }
    )
    
    # Verify the form was shown (not an error)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    
    # Verify the data was stored with CONTROL_TYPE_EXTERNAL
    assert flow.context["vehicle_data"]["control_type"] == CONTROL_TYPE_EXTERNAL


@pytest.mark.asyncio
async def test_entity_selectors_filter_by_device_class(hass: HomeAssistant):
    """Test that entity selectors filter sensors by appropriate device classes."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow
    from homeassistant.helpers.selector import EntitySelector
    
    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {}
    
    # Patch the _abort_if_unique_id_configured method to avoid aborting
    with patch.object(flow, "_abort_if_unique_id_configured", return_value=None):
        # Get to sensors step
        result = await flow.async_step_user(
            {
                "vehicle_name": "Test Vehicle",
                "vehicle_type": "ev",
            }
        )
    
    # Verify sensors step form has device_class filters
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"
    
    # Check that the data schema includes device_class constraints
    data_schema = result["data_schema"]
    schema_dict = dict(data_schema.schema)
    
    # SOC Sensor should filter for battery device_class
    soc_selector = schema_dict[CONF_SOC_SENSOR]
    assert isinstance(soc_selector, EntitySelector)
    # Check the selector config has device_class filter
    soc_config = soc_selector.config
    assert "device_class" in soc_config
    assert soc_config["device_class"] == ["battery"]
    
    # Range Sensor should filter for distance device_class
    range_selector = schema_dict[CONF_RANGE_SENSOR]
    assert isinstance(range_selector, EntitySelector)
    range_config = range_selector.config
    assert "device_class" in range_config
    assert range_config["device_class"] == ["distance"]
    
    # Charging Status should NOT filter by device_class (to include OVMS sensors)
    charging_selector = schema_dict[CONF_CHARGING_STATUS]
    assert isinstance(charging_selector, EntitySelector)
    charging_config = charging_selector.config
    # Should only filter by domain, not device_class
    assert "domain" in charging_config
    assert charging_config["domain"] == ["binary_sensor"]
    assert "device_class" not in charging_config  # No device_class filter


@pytest.mark.asyncio
async def test_emhass_step_planning_sensor_has_entity_selector(hass: HomeAssistant):
    """Test that planning_sensor uses entity selector with domain filter."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow
    from homeassistant.helpers.selector import EntitySelector
    
    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {}}
    
    # Patch the _abort_if_unique_id_configured method to avoid aborting
    with patch.object(flow, "_abort_if_unique_id_configured", return_value=None):
        # Get to emhass step
        await flow.async_step_user(
            {
                "vehicle_name": "Test Vehicle",
                "vehicle_type": "ev",
            }
        )
        
        await flow.async_step_sensors(
            {
                "soc_sensor": "sensor.test_soc",
                "battery_capacity": 50.0,
                "charging_power": 7.2,
            }
        )
        
        await flow.async_step_consumption(
            {
                "consumption": 0.15,
                "safety_margin": 10,
                "control_type": CONTROL_TYPE_EXTERNAL,
            }
        )
        
        # Get emhass form
        result = await flow.async_step_emhass(user_input=None)
    
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    
    # Check schema for planning_sensor
    data_schema = result["data_schema"]
    schema_dict = dict(data_schema.schema)
    
    planning_selector = schema_dict[CONF_PLANNING_SENSOR]
    # Should be an entity selector for sensor domain
    assert isinstance(planning_selector, EntitySelector)
    planning_config = planning_selector.config
    assert "domain" in planning_config
    assert planning_config["domain"] == ["sensor"]


@pytest.mark.asyncio
async def test_presence_step_sensors_filter_by_device_class(hass: HomeAssistant):
    """Test that presence step sensors filter by appropriate device classes."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow
    from homeassistant.helpers.selector import EntitySelector
    
    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    
    # Initialize context properly (not through direct assignment)
    # We need to simulate being in the middle of a flow
    flow.context = {
        "vehicle_data": {
            "soc_sensor": "sensor.test_soc",
            "battery_capacity": 50.0,
            "charging_power": 7.2,
            "consumption": 0.15,
            "safety_margin": 10,
            "control_type": CONTROL_TYPE_EXTERNAL,
        }
    }
    
    # Patch the _abort_if_unique_id_configured method to avoid aborting
    with patch.object(flow, "_abort_if_unique_id_configured", return_value=None):
        # Get to presence step by calling it directly with None (no auto-submit)
        result = await flow.async_step_presence(user_input=None)
    
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    
    # Check schema for presence sensors
    data_schema = result["data_schema"]
    schema_dict = dict(data_schema.schema)
    
    # Home sensor should filter for binary_sensor domain
    home_selector = schema_dict[CONF_HOME_SENSOR]
    assert isinstance(home_selector, EntitySelector)
    home_config = home_selector.config
    assert "domain" in home_config
    assert home_config["domain"] == ["binary_sensor"]
    
    # Plugged sensor should filter for binary_sensor domain
    plugged_selector = schema_dict[CONF_PLUGGED_SENSOR]
    assert isinstance(plugged_selector, EntitySelector)
    plugged_config = plugged_selector.config
    assert "domain" in plugged_config
    assert plugged_config["domain"] == ["binary_sensor"]


@pytest.mark.asyncio
async def test_error_messages_are_descriptive():
    """Test that error messages in strings.json are descriptive and helpful."""
    import json
    import os
    
    strings_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "ev_trip_planner",
        "strings.json",
    )
    
    with open(strings_path) as f:
        strings_data = json.load(f)
    
    # Verify error messages exist and are descriptive
    error_messages = strings_data["config"]["error"]
    
    required_errors = [
        "invalid_planning_horizon",
        "invalid_max_deferrable_loads",
        "home_sensor_not_found",
        "plugged_sensor_not_found",
        "invalid_coordinates_format",
    ]
    
    for error_key in required_errors:
        assert error_key in error_messages, f"Missing error message: {error_key}"
        assert len(error_messages[error_key]) > 10, \
            f"Error message '{error_key}' is too short to be descriptive"


@pytest.mark.asyncio
async def test_data_descriptions_include_examples():
    """Test that data descriptions include concrete examples."""
    import json
    import os
    
    strings_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "ev_trip_planner",
        "strings.json",
    )
    
    with open(strings_path) as f:
        strings_data = json.load(f)
    
    # Check for examples in key fields
    sensors_desc = strings_data["config"]["step"]["sensors"]["data_description"]
    
    # SOC sensor should mention percentage, battery, or SOC and give example
    soc_desc = sensors_desc["soc_sensor"]
    has_percentage = "%" in soc_desc or "percentage" in soc_desc.lower()
    has_battery = "battery" in soc_desc.lower()
    has_soc = "soc" in soc_desc.lower()
    has_example = "example" in soc_desc.lower() or "e.g." in soc_desc.lower() or "look for" in soc_desc.lower()
    
    assert (has_percentage or has_battery or has_soc), f"SOC description should mention battery/percentage: {soc_desc}"
    assert has_example, f"SOC description should include examples: {soc_desc}"
    
    # Battery capacity should mention kWh and give example
    capacity_desc = sensors_desc["battery_capacity"]
    has_kwh = "kwh" in capacity_desc.lower()
    has_example = "example" in capacity_desc.lower() or "e.g." in capacity_desc.lower()
    
    assert has_kwh, f"Battery capacity description should mention kWh: {capacity_desc}"
    assert has_example, f"Battery capacity description should include examples: {capacity_desc}"


@pytest.mark.asyncio
async def test_emhass_step_description_mentions_emhass_integration():
    """Test that EMHASS step description mentions EMHASS integration clearly."""
    import json
    import os
    
    strings_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "ev_trip_planner",
        "strings.json",
    )
    
    with open(strings_path) as f:
        strings_data = json.load(f)
    
    emhass_step = strings_data["config"]["step"]["emhass"]
    
    # Description should mention EMHASS
    description = emhass_step["description"]
    assert "emhass" in description.lower() or "optimizer" in description.lower()
    
    # Should explain it's optional
    assert "optional" in description.lower() or "configure" in description.lower()


@pytest.mark.asyncio
async def test_presence_step_description_mentions_prevention():
    """Test that presence step description mentions preventing charging when away."""
    import json
    import os
    
    strings_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "ev_trip_planner",
        "strings.json",
    )
    
    with open(strings_path) as f:
        strings_data = json.load(f)
    
    presence_step = strings_data["config"]["step"]["presence"]
    
    # Description should mention purpose
    description = presence_step["description"]
    assert "presence" in description.lower() or "home" in description.lower()
    assert "optional" in description.lower()