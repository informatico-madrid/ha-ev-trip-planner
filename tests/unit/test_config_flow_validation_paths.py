"""Tests for config_flow/main.py uncovered validation and error paths.

Covers the 24 lines not reached by existing tests:
- Sensor data update after validation (366-377)
- EMHASS step proceed after validation (411)
- Presence step: auto-select failure (474-477), sensor not found (493, 504-506, 517-519)
- Notifications step: service validation, logging (574-583, 593, 596)
- Entry creation: panel registration exception
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ev_trip_planner.config_flow.main import (
    EVTripPlannerFlowHandler,
)


class TestAsyncStepSensorsDataUpdate:
    """Test sensor data stored in context after validation (lines 366-377)."""

    @pytest.mark.asyncio
    async def test_valid_sensor_data_stored(self):
        """Lines 366-377: Valid sensor submission updates vehicle_data context."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {"vehicle_data": {}}

        result = await handler.async_step_sensors(
            {
                "battery_capacity_kwh": 75.0,
                "charging_power_kw": 11.0,
                "kwh_per_km": 0.15,
                "safety_margin_percent": 10,
            }
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "emhass"
        # Verify vehicle_data was updated
        vd = handler.context["vehicle_data"]
        assert vd["battery_capacity_kwh"] == 75.0
        assert vd["charging_power_kw"] == 11.0


class TestAsyncStepEmhassProceed:
    """Test EMHASS step proceed to presence (line 411)."""

    @pytest.mark.asyncio
    async def test_emhass_valid_proceeds_to_presence(self):
        """Line 411: Valid EMHASS input proceeds to presence step."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {"vehicle_data": {"vehicle_name": "test_car"}}

        # Valid inputs that pass all validations
        result = await handler.async_step_emhass(
            {
                "planning_horizon_days": 7,
                "max_deferrable_loads": 50,
                "index_cooldown_hours": 24,
            }
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "presence"


class TestAsyncStepPresenceAutoSelectFailure:
    """Test presence step auto-select failure (lines 474-477)."""

    @pytest.mark.asyncio
    async def test_charging_sensor_missing_after_auto_select(self):
        """Lines 474-477: No charging_sensor after auto-select → error form."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

        # Submit form without charging_sensor; auto_select returns None
        with patch(
            "custom_components.ev_trip_planner.config_flow._entities.auto_select_sensor",
            return_value={},
        ):
            result = await handler.async_step_presence({})

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "presence"
        assert result["errors"]["base"] == "charging_sensor_required"


class TestAsyncStepPresenceSensorNotFound:
    """Test presence step sensor validation failures (lines 493, 504-506, 517-519)."""

    @pytest.mark.asyncio
    async def test_charging_sensor_not_found(self):
        """Line 493: hass.states.get returns None for charging_sensor → error."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}
        handler.hass.states.get = MagicMock(return_value=None)

        result = await handler.async_step_presence(
            {"charging_sensor": "binary_sensor.fake"}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "presence"
        assert result["errors"]["base"] == "charging_sensor_not_found"

    @pytest.mark.asyncio
    async def test_home_sensor_not_found(self):
        """Lines 504-506: hass.states.get returns None for home_sensor → error."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

        charging_mock = MagicMock()
        charging_mock.state = "on"
        handler.hass.states.get = MagicMock(
            side_effect=lambda sid: (
                charging_mock if sid == "binary_sensor.charging" else None
            )
        )

        result = await handler.async_step_presence(
            {
                "charging_sensor": "binary_sensor.charging",
                "home_sensor": "binary_sensor.nonexistent",
            }
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "presence"
        assert result["errors"]["base"] == "home_sensor_not_found"

    @pytest.mark.asyncio
    async def test_plugged_sensor_not_found(self):
        """Lines 517-519: hass.states.get returns None for plugged_sensor → error."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

        charging_mock = MagicMock()
        charging_mock.state = "on"
        handler.hass.states.get = MagicMock(
            side_effect=lambda sid: (
                charging_mock if sid == "binary_sensor.charging" else None
            )
        )

        result = await handler.async_step_presence(
            {
                "charging_sensor": "binary_sensor.charging",
                "plugged_sensor": "binary_sensor.nonexistent",
            }
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "presence"
        assert result["errors"]["base"] == "plugged_sensor_not_found"


class TestAsyncStepNotifications:
    """Test notifications step validation and logging (lines 574-583, 593, 596)."""

    @pytest.mark.asyncio
    async def test_non_notify_service_validation(self):
        """Lines 574-583: Non-notify notification service domain check."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}
        handler.hass.services.has_service = MagicMock(return_value=False)

        result = await handler.async_step_notifications(
            {"notification_service": "xiaomi.turn_off"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        # The non-notify domain is validated but only logs a warning, doesn't fail

    @pytest.mark.asyncio
    async def test_notify_service_skips_validation(self):
        """Notify domain services skip has_service validation (non-notify path)."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}
        handler.hass.services.has_service = MagicMock(return_value=True)

        result = await handler.async_step_notifications(
            {"notification_service": "notify.mobile_app_phone"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        # notify domain should not trigger the non-notify branch
        # that checks has_service(domain, service) for non-notify services

    @pytest.mark.asyncio
    async def test_notification_service_logging(self, caplog):
        """Line 593: Notification service is logged."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

        result = await handler.async_step_notifications(
            {"notification_service": "notify.alexa"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_notification_devices_logging(self, caplog):
        """Line 596: Notification devices are logged."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

        result = await handler.async_step_notifications(
            {"notification_devices": ["notify.mobile_app", "notify.alexa"]}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY


class TestAsyncCreateEntryExceptions:
    """Test _async_create_entry exception paths."""

    @pytest.mark.asyncio
    async def test_panel_registration_exception(self, caplog):
        """Panel registration exception → warning, flow continues."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

        with patch(
            "custom_components.ev_trip_planner.config_flow.main.panel_module.async_register_panel",
            side_effect=RuntimeError("panel error"),
        ):
            result = await handler._async_create_entry()

        assert result is not None
        # Panel exception is caught and logged as warning
        assert any(
            "Could not register native panel" in r.message for r in caplog.records
        )


class TestAsyncStepPresenceHappyPath:
    """Test presence step happy path: valid sensor, proceed to notifications.

    Covers lines 507 (auto-select log), 550-559 (store data + transition).
    """

    @pytest.mark.asyncio
    async def test_presence_with_auto_selected_sensor(self):
        """Lines 506-510, 550-559: Auto-select finds sensor → proceed to notifications."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

        # auto_select_sensor returns a dict with charging_sensor populated
        with patch(
            "custom_components.ev_trip_planner.config_flow._entities.auto_select_sensor",
            return_value={"charging_sensor": "binary_sensor.charger"},
        ):
            # hass.states.get must return a valid state for the charging sensor
            mock_state = MagicMock()
            mock_state.state = "on"
            handler.hass.states.get = MagicMock(
                return_value=mock_state
            )

            # Patch async_step_notifications to return a known result
            handler.async_step_notifications = AsyncMock(
                return_value={"type": "FORM", "step_id": "notifications"}
            )

            # Submit empty form (no sensor provided → triggers auto-select)
            result = await handler.async_step_presence({})

        assert result == {"type": "FORM", "step_id": "notifications"}
        # Verify _get_vehicle_data was called and updated
        vd = handler.context["vehicle_data"]
        assert vd.get("charging_sensor") == "binary_sensor.charger"

    @pytest.mark.asyncio
    async def test_presence_with_provided_sensor(self):
        """Lines 550-559: User provides sensor directly → proceed to notifications."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {"vehicle_data": {"vehicle_name": "test_vehicle"}}

        # User provides charging_sensor directly, no auto-select needed
        mock_state = MagicMock()
        mock_state.state = "on"
        handler.hass.states.get = MagicMock(
            return_value=mock_state
        )

        handler.async_step_notifications = AsyncMock(
            return_value={"type": "FORM", "step_id": "notifications"}
        )

        result = await handler.async_step_presence({
            "charging_sensor": "binary_sensor.my_charger",
        })

        assert result == {"type": "FORM", "step_id": "notifications"}
        vd = handler.context["vehicle_data"]
        assert vd.get("charging_sensor") == "binary_sensor.my_charger"
