"""Integration tests for config_flow full user journey.

NFR-9: Uses real HA framework (pytest_homeassistant_custom_component) to walk
async_step_user → async_step_sensors → async_step_emhass → async_step_presence
→ async_step_notifications → _async_create_entry end-to-end.

NFR-8: Multi-assert on context["vehicle_data"] shape including every key the
schema declares, not just truthiness.

NFR-10: Distinctive real-shape config payloads with boundary cases.
"""

from __future__ import annotations

import pathlib
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


@pytest.fixture
def mock_hass_with_entities(mock_hass: HomeAssistant):
    """Create a mock hass with binary_sensor entities for presence step."""
    mock_hass.states.async_set(
        "binary_sensor.charging_port", "on",
        {"friendly_name": "Charging Port"}
    )
    mock_hass.states.async_set(
        "binary_sensor.home", "off",
        {"friendly_name": "Home"}
    )
    mock_hass.states.async_set(
        "input_boolean.guest_mode", "off",
        {"friendly_name": "Guest Mode"}
    )
    mock_hass.services.async_register(
        "notify", "test_service", lambda svc, msg: None
    )
    return mock_hass


# =============================================================================
# Helpers
# =============================================================================


def _mock_hass(mock_hass):
    """Configure mock_hass to avoid real _ServicesRegistry/EntityRegistry issues."""
    mock_hass.services.async_services = MagicMock(return_value={"notify": {}})
    mock_hass.entity_registry.entities = []
    return mock_hass


def _make_handler(mock_hass, vehicle_name="test_vehicle", **extra_vehicle_data):
    """Create and configure an EVTripPlannerFlowHandler with mutable context."""
    _mock_hass(mock_hass)
    from custom_components.ev_trip_planner.config_flow.main import (
        EVTripPlannerFlowHandler,
    )
    from custom_components.ev_trip_planner.const import CONF_VEHICLE_NAME

    handler = EVTripPlannerFlowHandler()
    handler.hass = mock_hass
    handler.context = {"vehicle_data": {CONF_VEHICLE_NAME: vehicle_name}}
    handler.context["vehicle_data"].update(extra_vehicle_data)
    return handler


# =============================================================================
# Full flow integration — user → sensors → emhass → presence → notifications
# =============================================================================


class TestFullConfigFlow:
    """End-to-end integration test for the full config flow."""

    @pytest.mark.asyncio
    async def test_full_flow_with_all_data(self, mock_hass: HomeAssistant):
        """Walk the full flow with valid data at every step.

        NFR-8: Assert on every context["vehicle_data"] key.
        NFR-10: Real-shape values with boundary values.
        """
        from custom_components.ev_trip_planner.const import (
            CONF_BATTERY_CAPACITY,
            CONF_CHARGING_POWER,
            CONF_CONSUMPTION,
            CONF_PLANNING_HORIZON,
            CONF_PLUGGED_SENSOR,
            CONF_SAFETY_MARGIN,
            CONF_VEHICLE_NAME,
        )

        handler = _make_handler(mock_hass)

        # Step 1: User — vehicle name
        result = await handler.async_step_user(
            {"vehicle_name": "My Tesla"}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "sensors"
        assert handler.context["vehicle_data"][CONF_VEHICLE_NAME] == "My Tesla"

        # Step 2: Sensors — valid data (boundary: min safety margin)
        result = await handler.async_step_sensors({
            CONF_BATTERY_CAPACITY: 10.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.05,
            CONF_SAFETY_MARGIN: 0,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "emhass"

        # Step 3: EMHASS — valid data (boundary: min planning horizon)
        result = await handler.async_step_emhass({
            CONF_PLANNING_HORIZON: 1,
            "max_deferrable_loads": 50,
            "index_cooldown_hours": 24,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "presence"

        # Step 4: Presence — with charging_sensor selected
        result = await handler.async_step_presence({
            "charging_sensor": "binary_sensor.charging_port",
            "home_sensor": "binary_sensor.home",
            "plugged_sensor": "input_boolean.guest_mode",
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "notifications"

        # Step 5: Notifications — skip (empty)
        result = await handler.async_step_notifications({})
        assert result["type"] is FlowResultType.CREATE_ENTRY

        # NFR-8: Assert on ALL context keys, not just truthiness
        vd = handler.context["vehicle_data"]
        assert set(vd.keys()) >= {
            CONF_VEHICLE_NAME,
            CONF_BATTERY_CAPACITY,
            CONF_CHARGING_POWER,
            CONF_CONSUMPTION,
            CONF_SAFETY_MARGIN,
            CONF_PLANNING_HORIZON,
            "max_deferrable_loads",
            "index_cooldown_hours",
            "charging_sensor",
            "home_sensor",
            "plugged_sensor",
        }
        # NFR-10: Verify distinctive values
        assert vd[CONF_VEHICLE_NAME] == "My Tesla"
        assert vd[CONF_BATTERY_CAPACITY] == 10.0
        assert vd[CONF_SAFETY_MARGIN] == 0

    @pytest.mark.asyncio
    async def test_full_flow_with_notifications(self, mock_hass: HomeAssistant):
        """Walk flow with notification service and devices provided."""
        from custom_components.ev_trip_planner.config_flow.main import (
            EVTripPlannerFlowHandler,
        )
        from custom_components.ev_trip_planner.const import (
            CONF_BATTERY_CAPACITY,
            CONF_CHARGING_POWER,
            CONF_CONSUMPTION,
            CONF_NOTIFICATION_DEVICES,
            CONF_NOTIFICATION_SERVICE,
            CONF_PLANNING_HORIZON,
            CONF_SAFETY_MARGIN,
            CONF_VEHICLE_NAME,
        )

        handler = _make_handler(mock_hass)

        # Steps 1-4
        await handler.async_step_user({CONF_VEHICLE_NAME: "Car"})
        await handler.async_step_sensors({
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 10,
        })
        await handler.async_step_emhass({
            CONF_PLANNING_HORIZON: 7,
            "max_deferrable_loads": 20,
            "index_cooldown_hours": 24,
        })
        await handler.async_step_presence({
            "charging_sensor": "binary_sensor.charging_port",
        })

        # Step 5: Notifications with data
        result = await handler.async_step_notifications({
            CONF_NOTIFICATION_SERVICE: "notify.mobile_app",
            CONF_NOTIFICATION_DEVICES: ["notify.mobile_app", "notify.alexa"],
        })
        assert result["type"] is FlowResultType.CREATE_ENTRY

        # Verify notification data stored
        vd = handler.context["vehicle_data"]
        assert vd[CONF_NOTIFICATION_SERVICE] == "notify.mobile_app"
        assert vd[CONF_NOTIFICATION_DEVICES] == ["notify.mobile_app", "notify.alexa"]

    @pytest.mark.asyncio
    async def test_full_flow_with_emhass_config(self, tmp_path: pathlib.Path):
        """Walk flow with EMHASS config file providing real horizon/load data."""
        from custom_components.ev_trip_planner.config_flow.main import (
            EVTripPlannerFlowHandler,
        )
        from custom_components.ev_trip_planner.const import (
            CONF_BATTERY_CAPACITY,
            CONF_CHARGING_POWER,
            CONF_CONSUMPTION,
            CONF_PLANNING_HORIZON,
            CONF_SAFETY_MARGIN,
            CONF_VEHICLE_NAME,
        )

        config_dir = tmp_path / "emhass_config"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text(
            '{"end_timesteps_of_each_deferrable_load": [168], '
            '"number_of_deferrable_loads": 25}'
        )

        mock_hass = MagicMock()
        handler = _make_handler(mock_hass)

        with patch.dict(
            "os.environ", {"EMHASS_CONFIG_PATH": str(config_dir)}
        ):
            await handler.async_step_user({CONF_VEHICLE_NAME: "Car"})
            await handler.async_step_sensors({
                CONF_BATTERY_CAPACITY: 60.0,
                CONF_CHARGING_POWER: 11.0,
                CONF_CONSUMPTION: 0.15,
                CONF_SAFETY_MARGIN: 10,
            })

            result = await handler.async_step_emhass({
                CONF_PLANNING_HORIZON: 7,
                "max_deferrable_loads": 20,
                "index_cooldown_hours": 24,
            })
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "presence"

            await handler.async_step_presence({
                "charging_sensor": "binary_sensor.charging_port",
            })
            result = await handler.async_step_notifications({})
            assert result["type"] is FlowResultType.CREATE_ENTRY


# =============================================================================
# Vehicle name edge cases
# =============================================================================


class TestVehicleNameEdgeCases:
    """Test vehicle name validation edge cases."""

    @pytest.mark.asyncio
    async def test_empty_string_vehicle_name(self, mock_hass: HomeAssistant):
        """Empty string → error form."""
        handler = _make_handler(mock_hass)
        result = await handler.async_step_user({"vehicle_name": ""})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert "base" in result.get("errors", {})

    @pytest.mark.asyncio
    async def test_whitespace_only_vehicle_name(self, mock_hass: HomeAssistant):
        """Whitespace-only → stripped to empty → error."""
        handler = _make_handler(mock_hass)
        result = await handler.async_step_user({"vehicle_name": "   "})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert "base" in result.get("errors", {})

    @pytest.mark.asyncio
    async def test_exact_100_char_vehicle_name(self, mock_hass: HomeAssistant):
        """Vehicle name exactly 100 chars → accepted (boundary)."""
        handler = _make_handler(mock_hass)
        result = await handler.async_step_user(
            {"vehicle_name": "a" * 100}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "sensors"

    @pytest.mark.asyncio
    async def test_101_char_vehicle_name(self, mock_hass: HomeAssistant):
        """Vehicle name > 100 chars → error."""
        handler = _make_handler(mock_hass)
        result = await handler.async_step_user(
            {"vehicle_name": "a" * 101}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert "base" in result.get("errors", {})


# =============================================================================
# EMHASS validation error paths
# =============================================================================


class TestEmhassValidationErrors:
    """Test EMHASS step validation error paths."""

    @pytest.mark.asyncio
    async def test_horizon_too_low(self, mock_hass: HomeAssistant):
        """Planning horizon < 1 → error."""
        handler = _make_handler(mock_hass)
        result = await handler.async_step_emhass({
            "planning_horizon_days": 0,
            "max_deferrable_loads": 50,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "emhass"

    @pytest.mark.asyncio
    async def test_horizon_too_high(self, mock_hass: HomeAssistant):
        """Planning horizon > 365 → error."""
        handler = _make_handler(mock_hass)
        result = await handler.async_step_emhass({
            "planning_horizon_days": 400,
            "max_deferrable_loads": 50,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "emhass"

    @pytest.mark.asyncio
    async def test_max_loads_below_min(self, mock_hass: HomeAssistant):
        """Max deferrable loads < 10 → error."""
        handler = _make_handler(mock_hass)
        result = await handler.async_step_emhass({
            "planning_horizon_days": 7,
            "max_deferrable_loads": 5,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "emhass"

    @pytest.mark.asyncio
    async def test_max_loads_above_max(self, mock_hass: HomeAssistant):
        """Max deferrable loads > 100 → error."""
        handler = _make_handler(mock_hass)
        result = await handler.async_step_emhass({
            "planning_horizon_days": 7,
            "max_deferrable_loads": 200,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "emhass"

    @pytest.mark.asyncio
    async def test_horizon_boundary_min(self, mock_hass: HomeAssistant):
        """Planning horizon = 1 → accepted (boundary)."""
        handler = _make_handler(mock_hass)
        result = await handler.async_step_emhass({
            "planning_horizon_days": 1,
            "max_deferrable_loads": 50,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "presence"

    @pytest.mark.asyncio
    async def test_max_loads_boundary_min(self, mock_hass: HomeAssistant):
        """Max deferrable loads = 10 → accepted (boundary)."""
        handler = _make_handler(mock_hass)
        result = await handler.async_step_emhass({
            "planning_horizon_days": 7,
            "max_deferrable_loads": 10,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "presence"


# =============================================================================
# Sensor validation edge cases
# =============================================================================


class TestSensorValidationEdgeCases:
    """Test sensors step validation edge cases."""

    @pytest.mark.asyncio
    async def test_battery_capacity_below_min(self, mock_hass: HomeAssistant):
        """Battery capacity < 10 → error."""
        from custom_components.ev_trip_planner.const import (
            CONF_BATTERY_CAPACITY,
            CONF_CHARGING_POWER,
            CONF_CONSUMPTION,
            CONF_SAFETY_MARGIN,
        )
        handler = _make_handler(mock_hass)
        result = await handler.async_step_sensors({
            CONF_BATTERY_CAPACITY: 5.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 10,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "sensors"

    @pytest.mark.asyncio
    async def test_battery_capacity_above_max(self, mock_hass: HomeAssistant):
        """Battery capacity > 200 → error."""
        from custom_components.ev_trip_planner.const import (
            CONF_BATTERY_CAPACITY,
            CONF_CHARGING_POWER,
            CONF_CONSUMPTION,
            CONF_SAFETY_MARGIN,
        )
        handler = _make_handler(mock_hass)
        result = await handler.async_step_sensors({
            CONF_BATTERY_CAPACITY: 250.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 10,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "sensors"

    @pytest.mark.asyncio
    async def test_consumption_below_min(self, mock_hass: HomeAssistant):
        """Consumption < 0.05 → error."""
        from custom_components.ev_trip_planner.const import (
            CONF_BATTERY_CAPACITY,
            CONF_CHARGING_POWER,
            CONF_CONSUMPTION,
            CONF_SAFETY_MARGIN,
        )
        handler = _make_handler(mock_hass)
        result = await handler.async_step_sensors({
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.01,
            CONF_SAFETY_MARGIN: 10,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "sensors"

    @pytest.mark.asyncio
    async def test_consumption_above_max(self, mock_hass: HomeAssistant):
        """Consumption > 0.5 → error."""
        from custom_components.ev_trip_planner.const import (
            CONF_BATTERY_CAPACITY,
            CONF_CHARGING_POWER,
            CONF_CONSUMPTION,
            CONF_SAFETY_MARGIN,
        )
        handler = _make_handler(mock_hass)
        result = await handler.async_step_sensors({
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.6,
            CONF_SAFETY_MARGIN: 10,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "sensors"

    @pytest.mark.asyncio
    async def test_safety_margin_above_max(self, mock_hass: HomeAssistant):
        """Safety margin > 50 → error."""
        from custom_components.ev_trip_planner.const import (
            CONF_BATTERY_CAPACITY,
            CONF_CHARGING_POWER,
            CONF_CONSUMPTION,
            CONF_SAFETY_MARGIN,
        )
        handler = _make_handler(mock_hass)
        result = await handler.async_step_sensors({
            CONF_BATTERY_CAPACITY: 60.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 60,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "sensors"

    @pytest.mark.asyncio
    async def test_sensor_boundary_values_all_pass(self, mock_hass: HomeAssistant):
        """All boundary values at minimum → accepted.

        Kills mutants: ranges become <= (rejects boundary) or > (rejects boundary).
        """
        from custom_components.ev_trip_planner.const import (
            CONF_BATTERY_CAPACITY,
            CONF_CHARGING_POWER,
            CONF_CONSUMPTION,
            CONF_SAFETY_MARGIN,
        )
        handler = _make_handler(mock_hass)
        result = await handler.async_step_sensors({
            CONF_BATTERY_CAPACITY: 10.0,
            CONF_CHARGING_POWER: 11.0,
            CONF_CONSUMPTION: 0.05,
            CONF_SAFETY_MARGIN: 0,
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "emhass"


# =============================================================================
# Presence step edge cases
# =============================================================================


class TestPresenceEdgeCases:
    """Test presence step edge cases."""

    @pytest.mark.asyncio
    async def test_charging_sensor_missing_no_auto_select(self, mock_hass: HomeAssistant):
        """No charging_sensor and no entities → error."""
        handler = _make_handler(mock_hass)
        result = await handler.async_step_presence({})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "presence"
        assert result["errors"]["base"] == "charging_sensor_required"

    @pytest.mark.asyncio
    async def test_all_three_presence_sensors(self, mock_hass: HomeAssistant):
        """All presence sensors provided → stores all in context."""
        from custom_components.ev_trip_planner.const import (
            CONF_CHARGING_SENSOR,
            CONF_HOME_SENSOR,
            CONF_PLUGGED_SENSOR,
        )
        handler = _make_handler(mock_hass)

        result = await handler.async_step_presence({
            CONF_CHARGING_SENSOR: "binary_sensor.charging_port",
            CONF_HOME_SENSOR: "binary_sensor.home",
            CONF_PLUGGED_SENSOR: "input_boolean.guest_mode",
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "notifications"

        vd = handler.context["vehicle_data"]
        assert vd[CONF_CHARGING_SENSOR] == "binary_sensor.charging_port"
        assert vd[CONF_HOME_SENSOR] == "binary_sensor.home"
        assert vd[CONF_PLUGGED_SENSOR] == "input_boolean.guest_mode"

    @pytest.mark.asyncio
    async def test_only_charging_sensor(self, mock_hass: HomeAssistant):
        """Only charging_sensor provided (others empty) → proceeds."""
        handler = _make_handler(mock_hass)
        result = await handler.async_step_presence({
            "charging_sensor": "binary_sensor.charging_port",
        })
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "notifications"


# =============================================================================
# Notifications step edge cases
# =============================================================================


class TestNotificationsEdgeCases:
    """Test notifications step edge cases."""

    @pytest.mark.asyncio
    async def test_empty_notification_submission(self, mock_hass: HomeAssistant):
        """Empty notification submission → creates entry."""
        from unittest.mock import patch
        handler = _make_handler(mock_hass, vehicle_name="Car")
        with patch(
            "custom_components.ev_trip_planner.config_flow.main._entities.scan_notify_entities"
        ):
            result = await handler.async_step_notifications({})
        assert result["type"] is FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_notify_domain_service_accepted(self, mock_hass: HomeAssistant):
        """Notify domain services accepted without has_service check."""
        from unittest.mock import patch
        handler = _make_handler(mock_hass, vehicle_name="Car")
        handler.hass.services.has_service = MagicMock(return_value=False)
        with patch(
            "custom_components.ev_trip_planner.config_flow.main._entities.scan_notify_entities"
        ):
            result = await handler.async_step_notifications({
                "notification_service": "notify.mobile_app",
            })
        assert result["type"] is FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_non_notify_service_warns_not_fails(self, mock_hass: HomeAssistant):
        """Non-notify service logs warning but doesn't fail."""
        from unittest.mock import patch
        handler = _make_handler(mock_hass, vehicle_name="Car")
        handler.hass.services.has_service = MagicMock(return_value=False)
        with patch(
            "custom_components.ev_trip_planner.config_flow.main._entities.scan_notify_entities"
        ):
            result = await handler.async_step_notifications({
                "notification_service": "xiaomi.turn_off",
            })
        assert result["type"] is FlowResultType.CREATE_ENTRY
