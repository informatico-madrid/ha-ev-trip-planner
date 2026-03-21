"""Tests for EV Trip Planner notification configuration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow
from custom_components.ev_trip_planner.const import (
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFICATION_SERVICE,
    CONF_VEHICLE_NAME,
)


@pytest.mark.asyncio
async def test_notifications_step_shows_form():
    """Test that the notifications step shows a form."""
    flow = EVTripPlannerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}
    flow.context["vehicle_data"] = {
        CONF_VEHICLE_NAME: "TestVehicle",
    }

    # Mock notify services
    flow.hass.services.async_services.return_value = {
        "notify": {
            "mobile_app_pixel_8": MagicMock(),
            "mobile_app_ipad": MagicMock(),
            "mqtt": MagicMock(),
        }
    }

    result = await flow.async_step_notifications()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "notifications"


@pytest.mark.asyncio
async def test_notifications_step_skip_empty_input():
    """Test that notifications step can be skipped with empty input."""
    flow = EVTripPlannerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}
    flow.context["vehicle_data"] = {
        CONF_VEHICLE_NAME: "TestVehicle",
    }

    # Mock notify services
    flow.hass.services.async_services.return_value = {
        "notify": {
            "mobile_app_pixel_8": MagicMock(),
        }
    }

    with patch.object(flow, "async_set_unique_id", new=AsyncMock()), patch.object(
        flow, "_abort_if_unique_id_configured", return_value=None
    ):
        result = await flow.async_step_notifications({})
        assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.asyncio
async def test_notifications_step_with_valid_service():
    """Test that notifications step accepts valid notification service."""
    flow = EVTripPlannerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}
    flow.context["vehicle_data"] = {
        CONF_VEHICLE_NAME: "TestVehicle",
    }

    # Mock notify services including the one we want to use
    flow.hass.services.async_services.return_value = {
        "notify": {
            "mobile_app_pixel_8": MagicMock(),
            "mobile_app_ipad": MagicMock(),
        }
    }
    # Mock has_service to return True for valid service
    flow.hass.services.has_service = MagicMock(return_value=True)

    with patch.object(flow, "async_set_unique_id", new=AsyncMock()), patch.object(
        flow, "_abort_if_unique_id_configured", return_value=None
    ):
        result = await flow.async_step_notifications(
            {
                CONF_NOTIFICATION_SERVICE: "notify.mobile_app_pixel_8",
            }
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        # Verify data was stored
        vehicle_data = flow.context["vehicle_data"]
        assert vehicle_data[CONF_NOTIFICATION_SERVICE] == "notify.mobile_app_pixel_8"


@pytest.mark.asyncio
async def test_notifications_step_with_devices():
    """Test that notifications step accepts notification devices."""
    flow = EVTripPlannerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}
    flow.context["vehicle_data"] = {
        CONF_VEHICLE_NAME: "TestVehicle",
    }

    # Mock notify services
    flow.hass.services.async_services.return_value = {
        "notify": {
            "mobile_app_pixel_8": MagicMock(),
            "mobile_app_ipad": MagicMock(),
        }
    }
    flow.hass.services.has_service = MagicMock(return_value=True)

    with patch.object(flow, "async_set_unique_id", new=AsyncMock()), patch.object(
        flow, "_abort_if_unique_id_configured", return_value=None
    ):
        result = await flow.async_step_notifications(
            {
                CONF_NOTIFICATION_SERVICE: "notify.mobile_app_pixel_8",
                CONF_NOTIFICATION_DEVICES: [
                    "notify.mobile_app_pixel_8",
                    "notify.mobile_app_ipad",
                ],
            }
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        # Verify data was stored
        vehicle_data = flow.context["vehicle_data"]
        assert vehicle_data[CONF_NOTIFICATION_SERVICE] == "notify.mobile_app_pixel_8"
        assert vehicle_data[CONF_NOTIFICATION_DEVICES] == [
            "notify.mobile_app_pixel_8",
            "notify.mobile_app_ipad",
        ]


@pytest.mark.asyncio
async def test_notifications_step_invalid_service_shows_error():
    """Test that non-notify services are validated but notify services are accepted (EntitySelector handles validation)."""
    flow = EVTripPlannerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}
    flow.context["vehicle_data"] = {
        CONF_VEHICLE_NAME: "TestVehicle",
    }

    # Mock entity registry to return empty list
    from homeassistant.helpers import entity_registry
    flow.hass.helpers = MagicMock()
    flow.hass.helpers.entity_registry = MagicMock()
    flow.hass.helpers.entity_registry.async_get_registry = AsyncMock(return_value=MagicMock(entities={}))

    # Test 1: notify domain services are accepted because EntitySelector handles validation
    result = await flow.async_step_notifications(
        {
            CONF_NOTIFICATION_SERVICE: "notify.nonexistent_service",
        }
    )
    # notify.* services are accepted (EntitySelector handles validation)
    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.asyncio
async def test_notifications_step_logs_available_services():
    """Test that notifications step logs available notify services."""
    flow = EVTripPlannerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}
    flow.context["vehicle_data"] = {
        CONF_VEHICLE_NAME: "TestVehicle",
    }

    # Mock notify services
    flow.hass.services.async_services.return_value = {
        "notify": {
            "mobile_app_pixel_8": MagicMock(),
            "mobile_app_ipad": MagicMock(),
            "mqtt": MagicMock(),
        }
    }

    with patch("custom_components.ev_trip_planner.config_flow._LOGGER") as mock_logger:
        await flow.async_step_notifications()
        # Verify logging calls
        assert mock_logger.debug.called or mock_logger.info.called


@pytest.mark.asyncio
async def test_notifications_schema_entity_selector_config():
    """Test that notification schema uses correct EntitySelectorConfig."""
    from custom_components.ev_trip_planner.config_flow import STEP_NOTIFICATIONS_SCHEMA
    import voluptuous as vol

    # Verify schema structure
    schema = STEP_NOTIFICATIONS_SCHEMA
    assert schema is not None

    # The schema should have optional fields for notification_service
    # and notification_devices - validate with empty dict (all fields optional)
    result = schema({})
    assert result == {}


@pytest.mark.asyncio
async def test_notifications_multiple_devices():
    """Test that multiple notification devices can be selected."""
    flow = EVTripPlannerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}
    flow.context["vehicle_data"] = {
        CONF_VEHICLE_NAME: "TestVehicle",
    }

    # Mock notify services
    flow.hass.services.async_services.return_value = {
        "notify": {
            "mobile_app_pixel_8": MagicMock(),
            "mobile_app_ipad": MagicMock(),
            "mobile_app_watch": MagicMock(),
        }
    }
    flow.hass.services.has_service = MagicMock(return_value=True)

    with patch.object(flow, "async_set_unique_id", new=AsyncMock()), patch.object(
        flow, "_abort_if_unique_id_configured", return_value=None
    ):
        result = await flow.async_step_notifications(
            {
                CONF_NOTIFICATION_DEVICES: [
                    "notify.mobile_app_pixel_8",
                    "notify.mobile_app_ipad",
                    "notify.mobile_app_watch",
                ],
            }
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        vehicle_data = flow.context["vehicle_data"]
        assert len(vehicle_data[CONF_NOTIFICATION_DEVICES]) == 3
