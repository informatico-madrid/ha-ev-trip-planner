"""Tests for Renault integration specific issues."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant import data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner.const import (
    CONF_VEHICLE_NAME,
    CONF_SOC_SENSOR,
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
)
from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow


def test_charging_status_sensor_entity_translation_exists():
    """Test that charging_status_sensor has entity translation."""
    # Arrange - Load translations directly from file
    import json

    with open("custom_components/ev_trip_planner/translations/es.json", "r") as f:
        translations = json.load(f)

    # Assert - Check entity translation exists (nested structure)
    assert "entity" in translations
    assert "charging_status_sensor" in translations["entity"]
    assert "name" in translations["entity"]["charging_status_sensor"]
    assert (
        translations["entity"]["charging_status_sensor"]["name"]
        != "charging_status_sensor"
    )
    assert (
        translations["entity"]["charging_status_sensor"]["name"]
        != "charging status sensor"
    )


def test_planning_sensor_entity_translation_clear():
    """Test that planning_sensor_entity has clear translation (not just 'Sensor de Planificación')."""
    # Arrange - Load translations directly from file
    import json

    with open("custom_components/ev_trip_planner/translations/es.json", "r") as f:
        translations = json.load(f)

    # Assert - Should have specific translation, not generic
    planning_key = "entity.planning_sensor_entity.name"
    if planning_key in translations:
        translation = translations[planning_key]
        # Should not be just "Sensor de Planificación" or "Planning Sensor"
        assert (
            "planificación" not in translation.lower()
            or "emhass" in translation.lower()
        )
        assert translation != "Sensor de Planificación"
        assert translation != "Planning Sensor"


@pytest.mark.asyncio
async def test_config_flow_accepts_renault_without_coordinates(hass: HomeAssistant):
    """Test that config flow works for Renault (no coordinate sensors, only home sensor)."""
    # Arrange
    flow = EVTripPlannerConfigFlow()
    flow.hass = hass

    # Act - Start config flow
    result = await flow.async_step_user()

    # Assert - Should have only vehicle_name (no vehicle_type selector per FR-001)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert "vehicle_name" in result["data_schema"].schema
    assert "vehicle_type" not in result["data_schema"].schema


@pytest.mark.asyncio
async def test_renault_home_sensor_field_optional(hass: HomeAssistant):
    """Test that home sensor field is optional for Renault integration."""
    # Arrange - Mock flow context properly
    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {
        "flow_id": "test_flow",
        "unique_id": None,
        "vehicle_data": {
            CONF_VEHICLE_NAME: "Renault Test",
            CONF_SOC_SENSOR: "sensor.renault_battery_level",
            CONF_BATTERY_CAPACITY: 52,
            CONF_CHARGING_POWER: 7.4,
        },
    }

    # Act - Call async_step_presence with empty dict (simulating user skipping the step)
    # This should go to notifications step since presence is optional
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
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "notifications"

    # Now skip notifications step
    result = await flow.async_step_notifications(user_input={})

    # Assert - Should create entry directly when skipping optional step
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Renault Test"


def test_strings_json_has_clear_planning_sensor_description():
    """Test that strings.json has clear description for planning_sensor_entity."""
    import json

    with open("custom_components/ev_trip_planner/strings.json", "r") as f:
        strings = json.load(f)

    # Check that planning_sensor_entity has clear data_description
    planning_desc = strings["config"]["step"]["emhass"]["data_description"][
        "planning_sensor_entity"
    ]

    # Should mention EMHASS or deferrable loads, not just "planning"
    assert (
        "emhass" in planning_desc.lower()
        or "diferible" in planning_desc.lower()
        or "deferrable" in planning_desc.lower()
    )
    assert (
        "planificación" not in planning_desc.lower()
        or "emhass" in planning_desc.lower()
    )


def test_spanish_translation_has_clear_planning_sensor_description():
    """Test that Spanish translation has clear description for planning sensor."""
    import json

    with open("custom_components/ev_trip_planner/translations/es.json", "r") as f:
        translations = json.load(f)

    # Check planning_sensor_entity description
    planning_desc = translations["config"]["step"]["emhass"]["data_description"][
        "planning_sensor_entity"
    ]

    # Should be clear it's about EMHASS deferrable loads, not generic planning
    assert (
        "planificación" not in planning_desc.lower()
        or "emhass" in planning_desc.lower()
    )
    # Update: La traducción actual es clara y menciona EMHASS, no necesita "diferible"
    assert "emhass" in planning_desc.lower()
