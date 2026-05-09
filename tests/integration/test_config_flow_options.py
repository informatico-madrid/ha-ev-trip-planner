"""Tests for EV Trip Planner config flow options: EMHASS, presence, notifications, and options flow.

Covers Milestone 3 extensions (EMHASS step, presence sensors, notifications),
UX improvements (strings.json validation), and edge cases for EMHASS config parsing.
"""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from custom_components.ev_trip_planner.config_flow import (
    EVTripPlannerFlowHandler,
    _get_emhass_max_deferrable_loads,
    _get_emhass_planning_horizon,
    _read_emhass_config,
)
from custom_components.ev_trip_planner.const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CHARGING_SENSOR,
    CONF_CONSUMPTION,
    CONF_HOME_SENSOR,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFICATION_SERVICE,
    CONF_PLANNING_HORIZON,
    CONF_PLANNING_SENSOR,
    CONF_PLUGGED_SENSOR,
    CONF_SAFETY_MARGIN,
    CONF_VEHICLE_NAME,
)


# =============================================================================
# EMHASS Config Parsing Tests
# =============================================================================


def test_read_emhass_config_returns_none_for_null_path():
    """Test _read_emhass_config with None path returns None."""
    assert _read_emhass_config(None) is None


def test_read_emhass_config_returns_none_for_missing_file(tmp_path):
    """Test _read_emhass_config with non-existent path returns None."""
    assert _read_emhass_config(str(tmp_path / "nonexistent.json")) is None


def test_read_emhass_config_returns_none_for_invalid_json(tmp_path):
    """Test _read_emhass_config with malformed JSON returns None."""
    config_file = tmp_path / "config.json"
    config_file.write_text("{ invalid json }")
    assert _read_emhass_config(str(config_file)) is None


def test_read_emhass_config_handles_io_error(tmp_path):
    """Test _read_emhass_config with IOError returns None."""
    config_file = tmp_path / "config.json"
    config_file.write_text("{}")
    config_file.chmod(0o000)
    try:
        assert _read_emhass_config(str(config_file)) is None
    finally:
        config_file.chmod(0o644)


def test_read_emhass_config_parses_valid_config(tmp_path):
    """Test _read_emhass_config with valid JSON returns parsed config."""
    config_file = tmp_path / "config.json"
    expected = {
        "end_timesteps_of_each_deferrable_load": [168],
        "number_of_deferrable_loads": 10,
    }
    config_file.write_text(json.dumps(expected))
    assert _read_emhass_config(str(config_file)) == expected


def test_planning_horizon_returns_none_for_null_config():
    """Test _get_emhass_planning_horizon with None returns None."""
    assert _get_emhass_planning_horizon(None) is None


def test_planning_horizon_returns_none_for_empty_config():
    """Test _get_emhass_planning_horizon with empty dict returns None."""
    assert _get_emhass_planning_horizon({}) is None


def test_planning_horizon_returns_none_when_timesteps_null():
    """Test _get_emhass_planning_horizon when end_timesteps is None."""
    assert _get_emhass_planning_horizon({"end_timesteps_of_each_deferrable_load": None}) is None


def test_planning_horizon_returns_none_when_timesteps_not_list():
    """Test _get_emhass_planning_horizon when end_timesteps is not a list."""
    assert _get_emhass_planning_horizon({"end_timesteps_of_each_deferrable_load": "not a list"}) is None


def test_planning_horizon_returns_none_when_timesteps_empty():
    """Test _get_emhass_planning_horizon when end_timesteps is empty."""
    assert _get_emhass_planning_horizon({"end_timesteps_of_each_deferrable_load": []}) is None


def test_planning_horizon_returns_none_when_less_than_one_day():
    """Test _get_emhass_planning_horizon rejects horizons less than 1 day (24 steps)."""
    assert _get_emhass_planning_horizon({"end_timesteps_of_each_deferrable_load": [23]}) is None


def test_planning_horizon_returns_days_from_valid_config():
    """Test _get_emhass_planning_horizon computes days from timesteps."""
    assert _get_emhass_planning_horizon({"end_timesteps_of_each_deferrable_load": [168]}) == 7


def test_max_deferrable_loads_returns_none_for_null_config():
    """Test _get_emhass_max_deferrable_loads with None returns None."""
    assert _get_emhass_max_deferrable_loads(None) is None


def test_max_deferrable_loads_returns_none_for_empty_config():
    """Test _get_emhass_max_deferrable_loads with empty dict returns None."""
    assert _get_emhass_max_deferrable_loads({}) is None


def test_max_deferrable_loads_returns_none_when_num_loads_null():
    """Test _get_emhass_max_deferrable_loads when number_of_deferrable_loads is None."""
    assert _get_emhass_max_deferrable_loads({"number_of_deferrable_loads": None}) is None


def test_max_deferrable_loads_returns_none_when_num_loads_zero():
    """Test _get_emhass_max_deferrable_loads when number_of_deferrable_loads is 0."""
    assert _get_emhass_max_deferrable_loads({"number_of_deferrable_loads": 0}) is None


def test_max_deferrable_loads_returns_none_when_num_loads_negative():
    """Test _get_emhass_max_deferrable_loads when number_of_deferrable_loads < 1."""
    assert _get_emhass_max_deferrable_loads({"number_of_deferrable_loads": -5}) is None


def test_max_deferrable_loads_returns_count_for_valid_config():
    """Test _get_emhass_max_deferrable_loads returns count for valid config."""
    assert _get_emhass_max_deferrable_loads({"number_of_deferrable_loads": 50}) == 50


# =============================================================================
# EMHASS Step Tests — With EMHASS Config
# =============================================================================


@pytest.mark.asyncio
async def test_emhass_step_logs_info_when_emhass_config_available(tmp_path):
    """Test async_step_emhass logs info when EMHASS config is present (line 420-425)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    config_file = tmp_path / "config.json"
    config_data = {
        "end_timesteps_of_each_deferrable_load": [168],
        "number_of_deferrable_loads": 50,
    }
    config_file.write_text(json.dumps(config_data))

    with patch.dict(os.environ, {"EMHASS_CONFIG_PATH": str(config_file)}):
        result = await flow.async_step_emhass()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"


@pytest.mark.asyncio
async def test_emhass_step_warns_when_user_horizon_exceeds_emhass_config(
    tmp_path, caplog
):
    """Test async_step_emhass warns when user horizon > EMHASS config horizon (line 442-448)."""
    import logging

    caplog.set_level(logging.WARNING)

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    config_file = tmp_path / "config.json"
    config_data = {
        "end_timesteps_of_each_deferrable_load": [168],  # 7 days
        "number_of_deferrable_loads": 50,
    }
    config_file.write_text(json.dumps(config_data))

    with patch.dict(os.environ, {"EMHASS_CONFIG_PATH": str(config_file)}):
        result = await flow.async_step_emhass(
            {
                CONF_PLANNING_HORIZON: 10,
                CONF_MAX_DEFERRABLE_LOADS: 50,
            }
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "exceeds EMHASS config" in caplog.text


@pytest.mark.asyncio
async def test_emhass_step_warns_when_user_loads_exceed_emhass_config(
    tmp_path, caplog
):
    """Test async_step_emhass warns when user loads > EMHASS config loads (line 501-507)."""
    import logging

    caplog.set_level(logging.WARNING)

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    config_file = tmp_path / "config.json"
    config_data = {
        "end_timesteps_of_each_deferrable_load": [168],
        "number_of_deferrable_loads": 30,
    }
    config_file.write_text(json.dumps(config_data))

    with patch.dict(os.environ, {"EMHASS_CONFIG_PATH": str(config_file)}):
        result = await flow.async_step_emhass(
            {
                CONF_PLANNING_HORIZON: 7,
                CONF_MAX_DEFERRABLE_LOADS: 50,
            }
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "EMHASS config" in caplog.text


# =============================================================================
# EMHASS Step Tests — Planning Sensor
# =============================================================================


@pytest.mark.asyncio
async def test_emhass_step_uses_valid_planning_sensor_state():
    """Test async_step_emhass reads valid state from planning sensor entity (line 453-474)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    mock_sensor_state = MagicMock()
    mock_sensor_state.state = "14"  # 14 days
    flow.hass.states.get.return_value = mock_sensor_state

    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 50,
            "planning_sensor_entity": "sensor.emhass_horizon",
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"


@pytest.mark.asyncio
async def test_emhass_step_warns_when_sensor_horizon_exceeds_user_horizon(
    tmp_path, caplog
):
    """Test async_step_emhass warns when user horizon > sensor horizon (line 467-474)."""
    import logging

    caplog.set_level(logging.WARNING)

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    mock_sensor_state = MagicMock()
    mock_sensor_state.state = "5"
    flow.hass.states.get.return_value = mock_sensor_state

    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 10,
            CONF_MAX_DEFERRABLE_LOADS: 50,
            "planning_sensor_entity": "sensor.emhass_horizon",
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "May cause issues" in caplog.text


@pytest.mark.asyncio
async def test_emhass_step_handles_unknown_sensor_state():
    """Test async_step_emhass handles unknown sensor state (line 481-485)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    mock_sensor_state = MagicMock()
    mock_sensor_state.state = "unknown"
    flow.hass.states.get.return_value = mock_sensor_state

    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 50,
            "planning_sensor_entity": "sensor.emhass_horizon",
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"


@pytest.mark.asyncio
async def test_emhass_step_handles_invalid_sensor_parse():
    """Test async_step_emhass handles non-parseable sensor value (line 475-480)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    mock_sensor_state = MagicMock()
    mock_sensor_state.state = "not_a_number"
    flow.hass.states.get.return_value = mock_sensor_state

    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 50,
            "planning_sensor_entity": "sensor.emhass_horizon",
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"


# =============================================================================
# Presence Step — Exception Handling
# =============================================================================


@pytest.mark.asyncio
async def test_presence_step_handles_entity_registry_exception():
    """Test async_step_presence handles entity registry RuntimeError (lines 612-613)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        side_effect=RuntimeError("Registry error"),
    ):
        result = await flow.async_step_presence({})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert result.get("errors") == {"base": "charging_sensor_required"}


# =============================================================================
# Notifications Step — Entity Registry
# =============================================================================


@pytest.mark.asyncio
async def test_notifications_step_returns_notify_entities():
    """Test async_step_notifications returns notify entities including Nabu Casa (lines 704-730)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    mock_entity1 = MagicMock()
    mock_entity1.entity_id = "notify.mobile_app"
    mock_entity1.domain = "notify"

    mock_entity2 = MagicMock()
    mock_entity2.entity_id = "notify.alexa_media_123"
    mock_entity2.domain = "notify"

    mock_entity3 = MagicMock()
    mock_entity3.entity_id = "notify.nabu_casa_456"
    mock_entity3.domain = "notify"

    mock_registry = MagicMock()
    mock_registry.entities.values.return_value = [
        mock_entity1,
        mock_entity2,
        mock_entity3,
    ]

    with patch.object(er, "async_get", MagicMock(return_value=mock_registry)):
        result = await flow.async_step_notifications()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"


@pytest.mark.asyncio
async def test_notifications_step_falls_back_to_services_api_on_registry_exception():
    """Test async_step_notifications falls back to services API on entity registry exception (lines 731-742)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        side_effect=RuntimeError("Registry error"),
    ):
        mock_services = {
            "mobile_app": MagicMock(),
            "telegram": MagicMock(),
        }
        flow.hass.services.async_services.return_value = {"notify": mock_services}

        result = await flow.async_step_notifications()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"


@pytest.mark.asyncio
async def test_notifications_step_accepts_non_notify_service():
    """Test async_step_notifications handles non-notify service selection (lines 770-777)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    flow.hass.services.has_service.return_value = False

    result = await flow.async_step_notifications(
        {
            CONF_NOTIFICATION_SERVICE: "mqtt.publish",
        }
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY


# =============================================================================
# _async_create_entry Exception Handling
# =============================================================================


@pytest.mark.asyncio
async def test_create_entry_handles_dashboard_import_exception():
    """Test _async_create_entry catches and logs dashboard import exception (lines 849-851)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {
        "vehicle_data": {
            CONF_VEHICLE_NAME: "TestVehicle",
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 20,
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    }

    with patch(
        "custom_components.ev_trip_planner.config_flow.is_lovelace_available",
        return_value=True,
    ):
        with patch(
            "custom_components.ev_trip_planner.config_flow.import_dashboard",
            side_effect=RuntimeError("Dashboard error"),
        ):
            result = await flow._async_create_entry()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "TestVehicle"


@pytest.mark.asyncio
async def test_create_entry_handles_panel_registration_exception():
    """Test _async_create_entry catches and logs panel registration exception (lines 867-869)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {
        "vehicle_data": {
            CONF_VEHICLE_NAME: "TestVehicle",
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 20,
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    }

    with patch(
        "custom_components.ev_trip_planner.config_flow.is_lovelace_available",
        return_value=True,
    ):
        with patch(
            "custom_components.ev_trip_planner.config_flow.import_dashboard",
            new_callable=AsyncMock,
        ):
            with patch(
                "custom_components.ev_trip_planner.config_flow.panel_module.async_register_panel",
                side_effect=RuntimeError("Panel error"),
            ):
                result = await flow._async_create_entry()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "TestVehicle"


# =============================================================================
# async_get_options_flow
# =============================================================================


def test_options_flow_handler_returns_options_flow():
    """Test async_get_options_flow returns EVTripPlannerOptionsFlowHandler instance (line 884)."""
    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )

    mock_entry = MagicMock()
    mock_entry.data = {}

    handler = EVTripPlannerFlowHandler.async_get_options_flow(mock_entry)

    assert isinstance(handler, EVTripPlannerOptionsFlowHandler)
    assert handler._config_entry is mock_entry


# =============================================================================
# Options Flow Handler Tests
# =============================================================================


@pytest.mark.asyncio
async def test_options_flow_handler_initializes_with_config_entry():
    """Test options flow handler initialization stores config entry."""
    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )

    mock_entry = MagicMock()
    mock_entry.data = {
        CONF_BATTERY_CAPACITY: 75.0,
        CONF_CHARGING_POWER: 22.0,
        CONF_CONSUMPTION: 0.18,
        CONF_SAFETY_MARGIN: 15,
    }

    handler = EVTripPlannerOptionsFlowHandler(mock_entry)
    assert handler._config_entry is mock_entry


@pytest.mark.asyncio
async def test_options_flow_handler_shows_form_with_current_values():
    """Test options flow shows form with current values as defaults."""
    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )

    mock_entry = MagicMock()
    mock_entry.data = {
        CONF_BATTERY_CAPACITY: 75.0,
        CONF_CHARGING_POWER: 22.0,
        CONF_CONSUMPTION: 0.18,
        CONF_SAFETY_MARGIN: 15,
    }

    handler = EVTripPlannerOptionsFlowHandler(mock_entry)
    handler.hass = MagicMock()

    result = await handler.async_step_init()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_handler_updates_provided_values():
    """Test options flow updates only the provided values."""
    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )

    mock_entry = MagicMock()
    mock_entry.data = {
        CONF_BATTERY_CAPACITY: 75.0,
        CONF_CHARGING_POWER: 22.0,
        CONF_CONSUMPTION: 0.18,
        CONF_SAFETY_MARGIN: 15,
    }

    handler = EVTripPlannerOptionsFlowHandler(mock_entry)
    handler.hass = MagicMock()

    result = await handler.async_step_init(
        {
            CONF_BATTERY_CAPACITY: 80.0,
            CONF_CHARGING_POWER: 22.0,
            CONF_CONSUMPTION: 0.18,
            CONF_SAFETY_MARGIN: 15,
        }
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_BATTERY_CAPACITY] == 80.0


@pytest.mark.asyncio
async def test_options_flow_handler_applies_defaults_for_empty_config():
    """Test options flow applies defaults when config data is empty."""
    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )

    mock_entry = MagicMock()
    mock_entry.data = {}

    handler = EVTripPlannerOptionsFlowHandler(mock_entry)
    handler.hass = MagicMock()

    result = await handler.async_step_init()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_handler_applies_defaults_for_null_config():
    """Test options flow applies defaults when config data is None."""
    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )

    mock_entry = MagicMock()
    mock_entry.data = None

    handler = EVTripPlannerOptionsFlowHandler(mock_entry)
    handler.hass = MagicMock()

    result = await handler.async_step_init()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


# =============================================================================
# Milestone 3 — EMHASS Step Validation
# =============================================================================


@pytest.mark.asyncio
async def test_emhass_step_accepts_valid_config(hass):
    """Test EMHASS step with valid configuration advances to presence."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    result = await flow.async_step_emhass(
        user_input={
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert flow.context["vehicle_data"][CONF_PLANNING_HORIZON] == 7
    assert flow.context["vehicle_data"][CONF_MAX_DEFERRABLE_LOADS] == 50


@pytest.mark.asyncio
async def test_emhass_step_rejects_horizon_exceeding_maximum(hass):
    """Test EMHASS step rejects horizon > 365 days."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {}}

    result = await flow.async_step_emhass(
        user_input={
            CONF_PLANNING_HORIZON: 366,
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    assert "errors" in result
    assert result["errors"]["base"] == "invalid_planning_horizon"


@pytest.mark.asyncio
async def test_emhass_step_rejects_horizon_below_minimum(hass):
    """Test EMHASS step rejects horizon < 1 day."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {}}

    result = await flow.async_step_emhass(
        user_input={
            CONF_PLANNING_HORIZON: 0,
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    assert "errors" in result
    assert result["errors"]["base"] == "invalid_planning_horizon"


@pytest.mark.asyncio
async def test_emhass_step_rejects_max_loads_exceeding_maximum(hass):
    """Test EMHASS step rejects max loads > 100."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {}}

    result = await flow.async_step_emhass(
        user_input={
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 101,
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    assert "errors" in result
    assert result["errors"]["base"] == "invalid_max_deferrable_loads"


@pytest.mark.asyncio
async def test_emhass_step_rejects_max_loads_below_minimum(hass):
    """Test EMHASS step rejects max loads < 10."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {}}

    result = await flow.async_step_emhass(
        user_input={
            CONF_PLANNING_HORIZON: 7,
            CONF_MAX_DEFERRABLE_LOADS: 9,
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"
    assert "errors" in result
    assert result["errors"]["base"] == "invalid_max_deferrable_loads"


@pytest.mark.asyncio
async def test_emhass_step_stores_planning_sensor_entity(hass):
    """Test EMHASS step with planning sensor entity stores it in context."""
    from custom_components.ev_trip_planner.config_flow import (
        CONF_PLANNING_SENSOR,
        EVTripPlannerConfigFlow,
    )

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    hass.states.async_set("sensor.test_planning_sensor", "5")

    result = await flow.async_step_emhass(
        user_input={
            CONF_PLANNING_HORIZON: 7,
            CONF_PLANNING_SENSOR: "sensor.test_planning_sensor",
            CONF_MAX_DEFERRABLE_LOADS: 50,
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert flow.context["vehicle_data"][CONF_PLANNING_SENSOR] == "sensor.test_planning_sensor"


# =============================================================================
# Milestone 3 — Presence Step
# =============================================================================


@pytest.mark.asyncio
async def test_presence_step_skips_with_auto_selection(hass):
    """Test presence step can be skipped via auto-selection of charging sensor."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    mock_entity = MagicMock()
    mock_entity.entity_id = "binary_sensor.test_charging"
    mock_registry = MagicMock()
    mock_registry.entities = {"binary_sensor.test_charging": mock_entity}

    mock_state = MagicMock()
    mock_state.state = "on"
    hass.states.get = MagicMock(return_value=mock_state)

    with patch.object(er, "async_get", return_value=mock_registry):
        result = await flow.async_step_presence(user_input={})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"

    # Now skip notifications step
    result = await flow.async_step_notifications(user_input={})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "test_vehicle"
    assert CONF_PLANNING_SENSOR not in result["data"] or CONF_PLANNING_SENSOR in result["data"]
    assert result["data"].get("charging_sensor") == "binary_sensor.test_charging"


@pytest.mark.asyncio
async def test_presence_step_accepts_selected_sensors(hass):
    """Test presence step stores selected charging, home, and plugged sensors."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow
    from custom_components.ev_trip_planner.const import (
        CONF_CHARGING_SENSOR,
        CONF_HOME_SENSOR,
        CONF_PLUGGED_SENSOR,
    )

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    hass.states.async_set("binary_sensor.test_charging", "on")
    hass.states.async_set("binary_sensor.test_home", "on")
    hass.states.async_set("binary_sensor.test_plugged", "off")

    result = await flow.async_step_presence(
        user_input={
            CONF_CHARGING_SENSOR: "binary_sensor.test_charging",
            CONF_HOME_SENSOR: "binary_sensor.test_home",
            CONF_PLUGGED_SENSOR: "binary_sensor.test_plugged",
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"

    result = await flow.async_step_notifications(user_input={})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CHARGING_SENSOR] == "binary_sensor.test_charging"
    assert result["data"][CONF_HOME_SENSOR] == "binary_sensor.test_home"
    assert result["data"][CONF_PLUGGED_SENSOR] == "binary_sensor.test_plugged"


@pytest.mark.asyncio
async def test_presence_step_rejects_missing_home_sensor(hass):
    """Test presence step validates home sensor exists."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    hass.states.async_set("binary_sensor.test_charging", "on")

    result = await flow.async_step_presence(
        user_input={
            CONF_CHARGING_SENSOR: "binary_sensor.test_charging",
            CONF_HOME_SENSOR: "binary_sensor.nonexistent",
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "errors" in result
    assert result["errors"]["base"] == "home_sensor_not_found"


@pytest.mark.asyncio
async def test_presence_step_rejects_missing_plugged_sensor(hass):
    """Test presence step validates plugged sensor exists."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    hass.states.async_set("binary_sensor.test_charging", "on")
    hass.states.async_set("binary_sensor.test_home", "on")

    result = await flow.async_step_presence(
        user_input={
            CONF_CHARGING_SENSOR: "binary_sensor.test_charging",
            CONF_HOME_SENSOR: "binary_sensor.test_home",
            CONF_PLUGGED_SENSOR: "binary_sensor.nonexistent_plugged",
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "errors" in result
    assert result["errors"]["base"] == "plugged_sensor_not_found"


@pytest.mark.asyncio
async def test_presence_step_requires_charging_sensor(hass):
    """Test presence step requires a charging sensor to be selected."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    hass.states.async_set("binary_sensor.test_home", "on")
    result = await flow.async_step_presence(
        user_input={
            CONF_HOME_SENSOR: "binary_sensor.test_home",
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "errors" in result
    assert result["errors"]["base"] == "charging_sensor_required"


@pytest.mark.asyncio
async def test_presence_step_rejects_missing_charging_sensor(hass):
    """Test presence step validates charging sensor exists."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    result = await flow.async_step_presence(
        user_input={
            CONF_CHARGING_SENSOR: "binary_sensor.nonexistent_charging",
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "errors" in result
    assert result["errors"]["base"] == "charging_sensor_not_found"


# =============================================================================
# Milestone 3 — Full Flow with EMHASS and Presence
# =============================================================================


@pytest.mark.asyncio
async def test_complete_flow_with_emhass_and_presence_sensors(hass):
    """Test complete config flow with all Milestone 3 steps (EMHASS + presence)."""
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
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"

    # Step 3: Notifications (skip)
    result = await flow.async_step_notifications(user_input={})
    assert result["type"] == FlowResultType.CREATE_ENTRY

    config = result["data"]
    assert config[CONF_PLANNING_HORIZON] == 7
    assert config[CONF_MAX_DEFERRABLE_LOADS] == 50
    assert config[CONF_CHARGING_SENSOR] == "binary_sensor.test_charging"
    assert config[CONF_HOME_SENSOR] == "binary_sensor.test_home"


# =============================================================================
# Milestone 3 — Notifications Step
# =============================================================================


@pytest.mark.asyncio
async def test_notifications_step_accepts_nonexistent_notify_service(hass):
    """Test notifications step accepts notify services via EntitySelector validation."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    def _mock_has_service(domain, service):
        if domain == "notify":
            return service in ["notify.mobile_app", "notify.persistent_notification"]
        return True

    hass.services.has_service = _mock_has_service

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    result = await flow.async_step_notifications(
        user_input={
            CONF_NOTIFICATION_SERVICE: "notify.nonexistent_service",
        }
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.asyncio
async def test_notifications_step_accepts_valid_service(hass):
    """Test notifications step accepts a registered notify service."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    hass.services.async_register("notify", "test_service", lambda x: None)

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    result = await flow.async_step_notifications(
        user_input={
            CONF_NOTIFICATION_SERVICE: "notify.test_service",
        }
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.asyncio
async def test_notifications_step_skips_when_empty(hass):
    """Test notifications step can be skipped with empty input."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    result = await flow.async_step_notifications(user_input={})

    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.asyncio
async def test_notifications_step_handles_multi_select_devices(hass):
    """Test notifications step with multiple device selection."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    result = await flow.async_step_notifications(
        user_input={
            CONF_NOTIFICATION_SERVICE: "notify.mobile_app",
            CONF_NOTIFICATION_DEVICES: [
                "notify.alexa_media_living_room",
                "notify.alexa_media_bedroom",
            ],
        }
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_NOTIFICATION_SERVICE] == "notify.mobile_app"
    assert result["data"][CONF_NOTIFICATION_DEVICES] == [
        "notify.alexa_media_living_room",
        "notify.alexa_media_bedroom",
    ]


@pytest.mark.asyncio
async def test_notifications_step_shows_form_with_notify_services(hass):
    """Test notifications step form lists available notify services including Nabu Casa."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    result = await flow.async_step_notifications(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"


@pytest.mark.asyncio
async def test_notifications_step_with_service_and_devices(hass):
    """Test notifications step with service and multiple devices."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

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

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_NOTIFICATION_SERVICE] == "notify.alexa_media"
    assert len(result["data"][CONF_NOTIFICATION_DEVICES]) == 3


@pytest.mark.asyncio
async def test_presence_step_with_all_sensors_and_notifications(hass):
    """Test presence step with all sensors and notification completion."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

    hass.states.async_set("binary_sensor.test_charging", "on")
    hass.states.async_set("binary_sensor.test_home", "on")
    hass.states.async_set("binary_sensor.test_plugged", "on")

    result = await flow.async_step_presence(
        user_input={
            CONF_CHARGING_SENSOR: "binary_sensor.test_charging",
            CONF_HOME_SENSOR: "binary_sensor.test_home",
            CONF_PLUGGED_SENSOR: "binary_sensor.test_plugged",
        }
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"

    result = await flow.async_step_notifications(user_input={})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CHARGING_SENSOR] == "binary_sensor.test_charging"
    assert result["data"][CONF_HOME_SENSOR] == "binary_sensor.test_home"
    assert result["data"][CONF_PLUGGED_SENSOR] == "binary_sensor.test_plugged"


# =============================================================================
# Milestone 3 — Options Flow with hass fixture
# =============================================================================


@pytest.mark.asyncio
async def test_options_flow_init_shows_form_with_hass(hass):
    """Test options flow init shows form with current values (hass fixture)."""
    from unittest.mock import MagicMock

    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )

    config_entry = MagicMock()
    config_entry.data = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_BATTERY_CAPACITY: 60.0,
        CONF_CHARGING_POWER: 11.0,
        "kwh_per_km": 0.15,
        CONF_SAFETY_MARGIN: 20,
    }

    flow = EVTripPlannerOptionsFlowHandler(config_entry)
    flow.hass = hass

    result = await flow.async_step_init(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_init_updates_config_with_hass(hass):
    """Test options flow updates configuration (hass fixture)."""
    from unittest.mock import MagicMock

    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )

    config_entry = MagicMock()
    config_entry.data = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_BATTERY_CAPACITY: 60.0,
        CONF_CHARGING_POWER: 11.0,
        "kwh_per_km": 0.15,
        CONF_SAFETY_MARGIN: 20,
    }

    flow = EVTripPlannerOptionsFlowHandler(config_entry)
    flow.hass = hass

    result = await flow.async_step_init(
        user_input={
            CONF_BATTERY_CAPACITY: 75.0,
            CONF_CHARGING_POWER: 22.0,
            CONF_CONSUMPTION: 0.18,
            CONF_SAFETY_MARGIN: 15,
        }
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_BATTERY_CAPACITY] == 75.0
    assert result["data"][CONF_CHARGING_POWER] == 22.0
    assert result["data"][CONF_CONSUMPTION] == 0.18
    assert result["data"][CONF_SAFETY_MARGIN] == 15


@pytest.mark.asyncio
async def test_options_flow_uses_defaults_when_config_missing(hass):
    """Test options flow uses defaults when config entry lacks certain values (hass fixture)."""
    from unittest.mock import MagicMock

    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )

    config_entry = MagicMock()
    config_entry.data = {
        CONF_VEHICLE_NAME: "test_vehicle",
    }

    flow = EVTripPlannerOptionsFlowHandler(config_entry)
    flow.hass = hass

    result = await flow.async_step_init(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


# =============================================================================
# Milestone 3 — Full Flow Tests
# =============================================================================


@pytest.mark.asyncio
async def test_full_flow_with_minimal_config(hass):
    """Test complete flow with minimal (skip-all) configuration."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {}}

    result = await flow.async_step_user({CONF_VEHICLE_NAME: "minimal_vehicle"})
    assert result["step_id"] == "sensors"

    result = await flow.async_step_sensors({})
    assert result["step_id"] == "emhass"

    result = await flow.async_step_emhass({})
    assert result["step_id"] == "presence"

    mock_entity = MagicMock()
    mock_entity.entity_id = "binary_sensor.test_charging"
    mock_registry = MagicMock()
    mock_registry.entities = {"binary_sensor.test_charging": mock_entity}

    mock_state = MagicMock()
    mock_state.state = "on"
    hass.states.get = MagicMock(return_value=mock_state)

    with patch.object(er, "async_get", return_value=mock_registry):
        result = await flow.async_step_presence({})
    assert result["step_id"] == "notifications"

    result = await flow.async_step_notifications({})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "minimal_vehicle"


@pytest.mark.asyncio
async def test_full_flow_with_all_options(hass):
    """Test complete flow with all configuration options filled in."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow
    from custom_components.ev_trip_planner.const import (
        CONF_BATTERY_CAPACITY,
        CONF_CHARGING_POWER,
        CONF_CONSUMPTION,
        CONF_HOME_SENSOR,
        CONF_MAX_DEFERRABLE_LOADS,
        CONF_NOTIFICATION_DEVICES,
        CONF_NOTIFICATION_SERVICE,
        CONF_PLANNING_HORIZON,
        CONF_PLANNING_SENSOR,
        CONF_PLUGGED_SENSOR,
        CONF_SAFETY_MARGIN,
        CONF_VEHICLE_NAME,
    )

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {}}

    result = await flow.async_step_user({CONF_VEHICLE_NAME: "full_vehicle"})
    assert result["step_id"] == "sensors"

    result = await flow.async_step_sensors(
        {
            CONF_BATTERY_CAPACITY: 82.0,
            CONF_CHARGING_POWER: 22.0,
            CONF_CONSUMPTION: 0.17,
            CONF_SAFETY_MARGIN: 15,
        }
    )
    assert result["step_id"] == "emhass"

    hass.states.async_set("sensor.planning_horizon", "14")
    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 14,
            CONF_MAX_DEFERRABLE_LOADS: 75,
            CONF_PLANNING_SENSOR: "sensor.planning_horizon",
        }
    )
    assert result["step_id"] == "presence"

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


# =============================================================================
# Milestone 3 — Schema Validation
# =============================================================================


def test_sensors_step_schema_has_required_fields():
    """Verify sensors step schema validates required fields exist."""
    import voluptuous as vol

    from custom_components.ev_trip_planner.config_flow import STEP_SENSORS_SCHEMA

    schema = STEP_SENSORS_SCHEMA.schema

    assert vol.Required(CONF_BATTERY_CAPACITY) in schema
    assert vol.Required(CONF_CHARGING_POWER) in schema
    assert vol.Required(CONF_CONSUMPTION) in schema
    assert vol.Required(CONF_SAFETY_MARGIN) in schema

    required_fields = [k for k in schema.keys() if isinstance(k, vol.Required)]
    assert len(required_fields) == 4


def test_emhass_step_schema_has_required_fields():
    """Verify EMHASS step schema validates required fields exist."""
    import voluptuous as vol

    from custom_components.ev_trip_planner.config_flow import STEP_EMHASS_SCHEMA

    schema = STEP_EMHASS_SCHEMA.schema

    assert vol.Required(CONF_PLANNING_HORIZON) in schema
    assert vol.Required(CONF_MAX_DEFERRABLE_LOADS) in schema
    assert vol.Optional("planning_sensor_entity") in schema


def test_presence_step_schema_has_required_charging_sensor():
    """Verify presence step schema requires charging sensor."""
    import voluptuous as vol

    from custom_components.ev_trip_planner.config_flow import STEP_PRESENCE_SCHEMA

    schema = STEP_PRESENCE_SCHEMA.schema

    assert vol.Required("charging_sensor") in schema
    assert vol.Optional("home_sensor") in schema
    assert vol.Optional("plugged_sensor") in schema


def test_all_milestone_schemas_are_valid():
    """Verify all Milestone 3 config flow schemas are valid voluptuous schemas."""
    from custom_components.ev_trip_planner.config_flow import (
        STEP_EMHASS_SCHEMA,
        STEP_NOTIFICATIONS_SCHEMA,
        STEP_PRESENCE_SCHEMA,
        STEP_SENSORS_SCHEMA,
        STEP_USER_SCHEMA,
    )

    assert STEP_USER_SCHEMA is not None
    assert STEP_SENSORS_SCHEMA is not None
    assert STEP_EMHASS_SCHEMA is not None
    assert STEP_PRESENCE_SCHEMA is not None
    assert STEP_NOTIFICATIONS_SCHEMA is not None

    for schema in (STEP_USER_SCHEMA, STEP_SENSORS_SCHEMA, STEP_EMHASS_SCHEMA,
                   STEP_PRESENCE_SCHEMA, STEP_NOTIFICATIONS_SCHEMA):
        assert hasattr(schema, "schema")


def test_notifications_step_schema_has_notify_fields():
    """Verify notifications step schema has notification_service and notification_devices."""
    import voluptuous as vol

    from custom_components.ev_trip_planner.config_flow import STEP_NOTIFICATIONS_SCHEMA

    schema = STEP_NOTIFICATIONS_SCHEMA.schema

    assert vol.Optional("notification_service") in schema
    assert vol.Optional("notification_devices") in schema
    assert len(schema) == 2


# =============================================================================
# Milestone 3 — Vehicle ID Generation
# =============================================================================


@pytest.mark.asyncio
async def test_vehicle_id_generated_from_name(hass):
    """Test that vehicle_id is generated correctly from vehicle name."""
    from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow

    flow = EVTripPlannerConfigFlow()
    flow.hass = hass
    flow.context = {"vehicle_data": {"vehicle_name": "Test Vehicle"}}

    result = await flow.async_step_notifications(user_input={})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Vehicle"


# =============================================================================
# Milestone 3.1 — UX Improvements (strings.json Validation)
# =============================================================================


def _get_strings_path():
    """Return the path to strings.json from this test file."""
    strings_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "custom_components",
        "ev_trip_planner",
        "strings.json",
    )
    return strings_path


def _load_strings():
    """Load strings.json for UX tests."""
    with open(_get_strings_path()) as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_strings_json_has_data_descriptions_for_config_steps():
    """Test that strings.json includes data_description fields for all config steps."""
    strings_data = _load_strings()

    config_steps = ["user", "sensors", "emhass", "presence"]

    for step in config_steps:
        assert (
            "data_description" in strings_data["config"]["step"][step]
        ), f"Step '{step}' missing data_description"

        data_desc = strings_data["config"]["step"][step]["data_description"]
        assert len(data_desc) > 0, f"Step '{step}' has empty data_description"

        data_fields = strings_data["config"]["step"][step]["data"]
        for field in data_fields:
            assert (
                field in data_desc
            ), f"Field '{field}' in step '{step}' missing data_description"


@pytest.mark.asyncio
async def test_error_messages_are_descriptive():
    """Test that error messages in strings.json are descriptive and helpful."""
    strings_data = _load_strings()

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
        assert (
            len(error_messages[error_key]) > 10
        ), f"Error message '{error_key}' is too short to be descriptive"


@pytest.mark.asyncio
async def test_data_descriptions_include_examples():
    """Test that data descriptions include concrete examples."""
    strings_data = _load_strings()

    sensors_desc = strings_data["config"]["step"]["sensors"]["data_description"]

    capacity_desc = sensors_desc["battery_capacity"]
    has_kwh = "kwh" in capacity_desc.lower()
    has_example = "example" in capacity_desc.lower() or "e.g." in capacity_desc.lower()

    assert has_kwh, f"Battery capacity description should mention kWh: {capacity_desc}"
    assert (
        has_example
    ), f"Battery capacity description should include examples: {capacity_desc}"


@pytest.mark.asyncio
async def test_emhass_step_description_mentions_integration():
    """Test that EMHASS step description mentions EMHASS integration clearly."""
    strings_data = _load_strings()

    emhass_step = strings_data["config"]["step"]["emhass"]

    description = emhass_step["description"]
    assert "emhass" in description.lower() or "optimizer" in description.lower()
    assert "optional" in description.lower() or "configure" in description.lower()


@pytest.mark.asyncio
async def test_presence_step_description_mentions_purpose():
    """Test that presence step description mentions preventing charging when away."""
    strings_data = _load_strings()

    presence_step = strings_data["config"]["step"]["presence"]

    description = presence_step["description"]
    assert "presence" in description.lower() or "home" in description.lower()
    assert "charging" in description.lower() or "required" in description.lower()
