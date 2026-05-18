"""Tests for config_flow.py missing coverage lines.

Covers:
- _read_emhass_config error handling (lines 196-203)
- _get_emhass_planning_horizon branches (lines 221-234)
- _get_emhass_max_deferrable_loads branches (lines 251-255)
- async_step_emhass branches (lines 420-425, 441-448, 475-482, 501-507)
- async_step_presence exception handling (lines 612-613)
- async_step_notifications entity registry (lines 704-727, 731-742)
- async_step_notifications non-notify service (lines 771-772)
- _async_create_entry exceptions (lines 849-851, 867-869)
- async_get_options_flow (line 884)
"""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ev_trip_planner.config_flow import (
    EVTripPlannerFlowHandler,
    _get_emhass_max_deferrable_loads,
    _get_emhass_planning_horizon,
    _read_emhass_config,
)
from custom_components.ev_trip_planner.const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CONSUMPTION,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_NOTIFICATION_SERVICE,
    CONF_PLANNING_HORIZON,
    CONF_SAFETY_MARGIN,
    CONF_VEHICLE_NAME,
)


# =============================================================================
# Tests for _read_emhass_config (lines 181-203)
# =============================================================================


def test_read_emhass_config_none_path():
    """Test _read_emhass_config with None path returns None."""
    result = _read_emhass_config(None)
    assert result is None


def test_read_emhass_config_path_not_exists():
    """Test _read_emhass_config with non-existent path returns None."""
    result = _read_emhass_config("/nonexistent/path/config.json")
    assert result is None


def test_read_emhass_config_invalid_json(tmp_path):
    """Test _read_emhass_config with invalid JSON returns None (line 201-202)."""
    config_file = tmp_path / "config.json"
    config_file.write_text("{ invalid json }")

    result = _read_emhass_config(str(config_file))
    assert result is None


def test_read_emhass_config_io_error(tmp_path):
    """Test _read_emhass_config with IOError returns None (line 201-202)."""
    config_file = tmp_path / "config.json"
    config_file.write_text("{}")

    # Make file unreadable
    config_file.chmod(0o000)

    try:
        result = _read_emhass_config(str(config_file))
        assert result is None
    finally:
        # Restore permissions for cleanup
        config_file.chmod(0o644)


def test_read_emhass_config_valid(tmp_path):
    """Test _read_emhass_config with valid JSON returns config."""
    config_file = tmp_path / "config.json"
    config_data = {
        "end_timesteps_of_each_deferrable_load": [168],
        "number_of_deferrable_loads": 10,
    }
    config_file.write_text(json.dumps(config_data))

    result = _read_emhass_config(str(config_file))
    assert result == config_data


# =============================================================================
# Tests for _get_emhass_planning_horizon (lines 206-234)
# =============================================================================


def test_get_emhass_planning_horizon_none_config():
    """Test _get_emhass_planning_horizon with None config returns None."""
    result = _get_emhass_planning_horizon(None)
    assert result is None


def test_get_emhass_planning_horizon_empty_config():
    """Test _get_emhass_planning_horizon with empty config returns None."""
    result = _get_emhass_planning_horizon({})
    assert result is None


def test_get_emhass_planning_horizon_end_timesteps_none():
    """Test _get_emhass_planning_horizon when end_timesteps is None (line 222)."""
    config = {"end_timesteps_of_each_deferrable_load": None}
    result = _get_emhass_planning_horizon(config)
    assert result is None


def test_get_emhass_planning_horizon_end_timesteps_not_list():
    """Test _get_emhass_planning_horizon when end_timesteps is not a list (line 222)."""
    config = {"end_timesteps_of_each_deferrable_load": "not a list"}
    result = _get_emhass_planning_horizon(config)
    assert result is None


def test_get_emhass_planning_horizon_end_timesteps_empty():
    """Test _get_emhass_planning_horizon when end_timesteps is empty (line 224)."""
    config = {"end_timesteps_of_each_deferrable_load": []}
    result = _get_emhass_planning_horizon(config)
    assert result is None


def test_get_emhass_planning_horizon_less_than_one_day():
    """Test _get_emhass_planning_horizon when horizon < 1 day (line 231)."""
    # 24 timesteps = 24 hours = 1 day, so 23 timesteps should return None
    config = {"end_timesteps_of_each_deferrable_load": [23]}
    result = _get_emhass_planning_horizon(config)
    assert result is None


def test_get_emhass_planning_horizon_valid():
    """Test _get_emhass_planning_horizon with valid config."""
    # 168 timesteps = 168 hours = 7 days
    config = {"end_timesteps_of_each_deferrable_load": [168]}
    result = _get_emhass_planning_horizon(config)
    assert result == 7


# =============================================================================
# Tests for _get_emhass_max_deferrable_loads (lines 237-255)
# =============================================================================


def test_get_emhass_max_deferrable_loads_none_config():
    """Test _get_emhass_max_deferrable_loads with None config returns None."""
    result = _get_emhass_max_deferrable_loads(None)
    assert result is None


def test_get_emhass_max_deferrable_loads_empty_config():
    """Test _get_emhass_max_deferrable_loads with empty config returns None."""
    result = _get_emhass_max_deferrable_loads({})
    assert result is None


def test_get_emhass_max_deferrable_loads_num_loads_none():
    """Test _get_emhass_max_deferrable_loads when num_loads is None (line 252)."""
    config = {"number_of_deferrable_loads": None}
    result = _get_emhass_max_deferrable_loads(config)
    assert result is None


def test_get_emhass_max_deferrable_loads_num_loads_zero():
    """Test _get_emhass_max_deferrable_loads when num_loads is 0 (line 252)."""
    config = {"number_of_deferrable_loads": 0}
    result = _get_emhass_max_deferrable_loads(config)
    assert result is None


def test_get_emhass_max_deferrable_loads_num_loads_negative():
    """Test _get_emhass_max_deferrable_loads when num_loads < 1 (line 252)."""
    config = {"number_of_deferrable_loads": -5}
    result = _get_emhass_max_deferrable_loads(config)
    assert result is None


def test_get_emhass_max_deferrable_loads_valid():
    """Test _get_emhass_max_deferrable_loads with valid config."""
    config = {"number_of_deferrable_loads": 50}
    result = _get_emhass_max_deferrable_loads(config)
    assert result == 50


# =============================================================================
# Tests for async_step_emhass branches (lines 420-425, 441-448, 475-482, 501-507)
# =============================================================================


@pytest.mark.asyncio
async def test_async_step_emhass_with_emhass_config(tmp_path):
    """Test async_step_emhass with EMHASS config available logs info (line 420-425)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Create a valid EMHASS config file
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
async def test_async_step_emhass_horizon_exceeds_emhass_config_warning(
    tmp_path, caplog
):
    """Test async_step_emhass warns when user horizon > EMHASS horizon (line 442-448)."""
    import logging

    caplog.set_level(logging.WARNING)

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Create EMHASS config with 7-day horizon
    config_file = tmp_path / "config.json"
    config_data = {
        "end_timesteps_of_each_deferrable_load": [168],  # 7 days
        "number_of_deferrable_loads": 50,
    }
    config_file.write_text(json.dumps(config_data))

    with patch.dict(os.environ, {"EMHASS_CONFIG_PATH": str(config_file)}):
        # User requests 10 days which exceeds EMHASS config of 7 days
        result = await flow.async_step_emhass(
            {
                CONF_PLANNING_HORIZON: 10,
                CONF_MAX_DEFERRABLE_LOADS: 50,
            }
        )

    # Should still advance (just a warning)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "exceeds EMHASS config" in caplog.text


@pytest.mark.asyncio
async def test_async_step_emhass_planning_sensor_valid_state():
    """Test async_step_emhass with planning sensor returning valid state (line 453-474)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Mock sensor returning valid horizon
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
async def test_async_step_emhass_planning_sensor_unknown_state():
    """Test async_step_emhass with planning sensor in unknown state (line 481-485)."""

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Mock sensor returning unknown state
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
async def test_async_step_emhass_planning_sensor_invalid_parse():
    """Test async_step_emhass handles invalid sensor value (line 475-480)."""

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Mock sensor returning non-parseable value
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

    # Should still proceed (just log warning)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"


@pytest.mark.asyncio
async def test_async_step_emhass_sensor_horizon_warning(tmp_path, caplog):
    """Test async_step_emhass warns when user horizon > sensor horizon (line 467-474)."""
    import logging

    caplog.set_level(logging.WARNING)

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Mock sensor returning 5 days
    mock_sensor_state = MagicMock()
    mock_sensor_state.state = "5"
    flow.hass.states.get.return_value = mock_sensor_state

    # User requests 10 days which exceeds sensor value of 5 days
    result = await flow.async_step_emhass(
        {
            CONF_PLANNING_HORIZON: 10,
            CONF_MAX_DEFERRABLE_LOADS: 50,
            "planning_sensor_entity": "sensor.emhass_horizon",
        }
    )

    # Should still advance (just a warning)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "May cause issues" in caplog.text


@pytest.mark.asyncio
async def test_async_step_emhass_max_loads_exceeds_emhass_config_warning(
    tmp_path, caplog
):
    """Test async_step_emhass warns when user loads > EMHASS loads (line 501-507)."""
    import logging

    caplog.set_level(logging.WARNING)

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Create EMHASS config with max 30 loads
    config_file = tmp_path / "config.json"
    config_data = {
        "end_timesteps_of_each_deferrable_load": [168],
        "number_of_deferrable_loads": 30,
    }
    config_file.write_text(json.dumps(config_data))

    with patch.dict(os.environ, {"EMHASS_CONFIG_PATH": str(config_file)}):
        # User requests 50 loads which exceeds EMHASS config of 30
        result = await flow.async_step_emhass(
            {
                CONF_PLANNING_HORIZON: 7,
                CONF_MAX_DEFERRABLE_LOADS: 50,
            }
        )

    # Should still advance (just a warning)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert "EMHASS config" in caplog.text


# =============================================================================
# Tests for async_step_presence exception handling (lines 612-613)
# =============================================================================


@pytest.mark.asyncio
async def test_async_step_presence_entity_registry_exception():
    """Test async_step_presence handles entity registry exception (lines 612-613)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Mock entity registry to raise exception
    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        side_effect=RuntimeError("Registry error"),
    ):
        result = await flow.async_step_presence({})

    # Should show form with error since auto-selection failed
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert result.get("errors") == {"base": "charging_sensor_required"}


# =============================================================================
# Tests for async_step_notifications entity registry (lines 704-727, 731-742)
# =============================================================================


@pytest.mark.asyncio
async def test_async_step_notifications_with_notify_entities():
    """Test async_step_notifications returns notify entities including Nabu Casa (lines 704-730)."""
    from homeassistant.helpers import entity_registry as er

    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Mock entity registry with notify entities including Alexa/Nabu
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
async def test_async_step_notifications_entity_registry_exception_fallback():
    """Test async_step_notifications falls back to services API on exception (lines 731-742)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Mock entity registry to raise exception
    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        side_effect=RuntimeError("Registry error"),
    ):
        # Mock services API as fallback
        mock_services = {
            "mobile_app": MagicMock(),
            "telegram": MagicMock(),
        }
        flow.hass.services.async_services.return_value = {"notify": mock_services}

        result = await flow.async_step_notifications()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"


# =============================================================================
# Tests for async_step_notifications non-notify service (lines 771-772)
# =============================================================================


@pytest.mark.asyncio
async def test_async_step_notifications_non_notify_service_not_found():
    """Test async_step_notifications handles non-notify service (lines 770-777)."""
    flow = EVTripPlannerFlowHandler()
    flow.hass = MagicMock()
    flow.context = {"vehicle_data": {CONF_VEHICLE_NAME: "TestVehicle"}}

    # Mock service lookup to return False (service not found)
    flow.hass.services.has_service.return_value = False

    result = await flow.async_step_notifications(
        {
            CONF_NOTIFICATION_SERVICE: "mqtt.publish",
        }
    )

    # Should still create entry (just log warning)
    assert result["type"] == FlowResultType.CREATE_ENTRY


# =============================================================================
# Tests for _async_create_entry exceptions (lines 849-851, 867-869)
# =============================================================================


@pytest.mark.asyncio
async def test_async_create_entry_dashboard_import_exception():
    """Test _async_create_entry handles dashboard import exception (lines 849-851)."""
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

    # Mock is_lovelace_available to return True
    with patch(
        "custom_components.ev_trip_planner.config_flow.is_lovelace_available",
        return_value=True,
    ):
        # Mock import_dashboard to raise exception
        with patch(
            "custom_components.ev_trip_planner.config_flow.import_dashboard",
            side_effect=RuntimeError("Dashboard error"),
        ):
            result = await flow._async_create_entry()

    # Should still create entry (exception is caught and logged)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "TestVehicle"


@pytest.mark.asyncio
async def test_async_create_entry_panel_registration_exception():
    """Test _async_create_entry handles panel registration exception (lines 867-869)."""
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

    # Mock everything to succeed
    with patch(
        "custom_components.ev_trip_planner.config_flow.is_lovelace_available",
        return_value=True,
    ):
        with patch(
            "custom_components.ev_trip_planner.config_flow.import_dashboard",
            new_callable=AsyncMock,
        ):
            # Mock panel registration to raise exception
            with patch(
                "custom_components.ev_trip_planner.config_flow.panel_module.async_register_panel",
                side_effect=RuntimeError("Panel error"),
            ):
                result = await flow._async_create_entry()

    # Should still create entry (exception is caught and logged)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "TestVehicle"


# =============================================================================
# Tests for async_get_options_flow (line 884)
# =============================================================================


def test_async_get_options_flow():
    """Test async_get_options_flow returns options flow handler (line 884)."""
    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )

    mock_entry = MagicMock()
    mock_entry.data = {}

    handler = EVTripPlannerFlowHandler.async_get_options_flow(mock_entry)

    assert isinstance(handler, EVTripPlannerOptionsFlowHandler)
    assert handler._config_entry is mock_entry


# =============================================================================
# Tests for options flow handler
# =============================================================================


@pytest.mark.asyncio
async def test_options_flow_init():
    """Test options flow initialization."""
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
async def test_options_flow_show_form():
    """Test options flow shows form with current values."""
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
async def test_options_flow_update_values():
    """Test options flow updates only provided values."""
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

    # Only update battery capacity
    result = await handler.async_step_init(
        {
            CONF_BATTERY_CAPACITY: 80.0,
            CONF_CHARGING_POWER: 22.0,  # Include to avoid schema validation error
            CONF_CONSUMPTION: 0.18,
            CONF_SAFETY_MARGIN: 15,
        }
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_BATTERY_CAPACITY] == 80.0


@pytest.mark.asyncio
async def test_options_flow_empty_data_defaults():
    """Test options flow handles empty config data with defaults."""
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
async def test_options_flow_null_data():
    """Test options flow handles None config data."""
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
