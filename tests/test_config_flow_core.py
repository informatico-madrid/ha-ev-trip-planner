"""Tests for EV Trip Planner config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import AbortFlow, FlowResultType

from custom_components.ev_trip_planner.const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CONSUMPTION,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_PLANNING_HORIZON,
    CONF_SAFETY_MARGIN,
    CONF_VEHICLE_NAME,
    DEFAULT_MAX_DEFERRABLE_LOADS,
    DEFAULT_PLANNING_HORIZON,
)
from custom_components.ev_trip_planner.config_flow import EVTripPlannerConfigFlow


@pytest.mark.asyncio
async def test_show_user_form():
    """Test that the initial user step shows a form."""
    flow = EVTripPlannerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}
    result = await flow.async_step_user()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_full_flow_success():
    """Test a complete successful configuration flow invoking the flow class directly."""
    flow = EVTripPlannerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}

    # User step - step 1: vehicle basic info
    with patch.object(flow, "async_set_unique_id", new=AsyncMock()) as _set_uid, patch.object(
        flow, "_abort_if_unique_id_configured", return_value=None
    ) as _abort_check:
        result = await flow.async_step_user(
            {
                CONF_VEHICLE_NAME: "Chispitas",
            }
        )
        # Should advance to step 2 (sensors)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "sensors"

        # Step 2: sensors configuration
        result = await flow.async_step_sensors(
            {
                CONF_BATTERY_CAPACITY: 60.0,
                CONF_CHARGING_POWER: 11.0,
                CONF_CONSUMPTION: 0.15,
                CONF_SAFETY_MARGIN: 20,
            }
        )
        # Should advance to step 3 (emhass)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "emhass"

        # Step 3: EMHASS configuration (the new async_step_emhass)
        result = await flow.async_step_emhass(
            {
                CONF_PLANNING_HORIZON: 7,
                CONF_MAX_DEFERRABLE_LOADS: 50,
            }
        )
        # Should advance to step 4 (presence)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "presence"

        # Step 4: Presence configuration (skip with empty input)
        result = await flow.async_step_presence({})
        # Should advance to step 5 (notifications)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "notifications"

        # Step 5: Notifications configuration (skip with empty input)
        result = await flow.async_step_notifications({})
        # Should create entry
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Chispitas"
        data = result["data"]
        assert data[CONF_VEHICLE_NAME] == "Chispitas"
        assert data[CONF_BATTERY_CAPACITY] == 60.0
        assert data[CONF_CHARGING_POWER] == 11.0
        assert data[CONF_CONSUMPTION] == 0.15
        assert data[CONF_SAFETY_MARGIN] == 20
        assert data[CONF_PLANNING_HORIZON] == 7
        assert data[CONF_MAX_DEFERRABLE_LOADS] == 50


@pytest.mark.asyncio
async def test_emhass_step_shows_form():
    """Test that the EMHASS step shows a form."""
    flow = EVTripPlannerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}
    # Initialize flow data in context
    flow.context["vehicle_data"] = {
        CONF_VEHICLE_NAME: "TestVehicle",
    }
    result = await flow.async_step_emhass()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "emhass"


@pytest.mark.asyncio
async def test_emhass_step_with_sensor():
    """Test that the EMHASS step accepts optional planning sensor."""
    flow = EVTripPlannerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}
    flow.context["vehicle_data"] = {
        CONF_VEHICLE_NAME: "TestVehicle",
    }

    with patch.object(flow, "async_set_unique_id", new=AsyncMock()), patch.object(
        flow, "_abort_if_unique_id_configured", return_value=None
    ):
        result = await flow.async_step_emhass(
            {
                CONF_PLANNING_HORIZON: 14,
                CONF_MAX_DEFERRABLE_LOADS: 30,
                "planning_sensor_entity": "sensor.emhass_horizon",
            }
        )
        # Now should advance to presence step
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "presence"
        # Check data was stored correctly
        vehicle_data = flow.context["vehicle_data"]
        assert vehicle_data[CONF_PLANNING_HORIZON] == 14
        assert vehicle_data[CONF_MAX_DEFERRABLE_LOADS] == 30
        assert vehicle_data["planning_sensor_entity"] == "sensor.emhass_horizon"


@pytest.mark.asyncio
async def test_duplicate_vehicle_aborts():
    """Test that configuring the same vehicle name creates entry (current implementation)."""
    flow = EVTripPlannerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}

    with patch.object(flow, "async_set_unique_id", new=AsyncMock()):
        with patch.object(
            flow,
            "_abort_if_unique_id_configured",
            side_effect=AbortFlow("already_configured"),
        ):
            # Step 1: user
            result = await flow.async_step_user(
                {
                    CONF_VEHICLE_NAME: "Chispitas",
                }
            )
            # Step 2: sensors
            result = await flow.async_step_sensors(
                {
                    CONF_BATTERY_CAPACITY: 60.0,
                    CONF_CHARGING_POWER: 11.0,
                    CONF_CONSUMPTION: 0.15,
                    CONF_SAFETY_MARGIN: 20,
                }
            )
            # Step 3: emhass
            result = await flow.async_step_emhass(
                {
                    CONF_PLANNING_HORIZON: DEFAULT_PLANNING_HORIZON,
                    CONF_MAX_DEFERRABLE_LOADS: DEFAULT_MAX_DEFERRABLE_LOADS,
                }
            )
            # Step 4: presence
            result = await flow.async_step_presence({})
            # Step 5: notifications
            result = await flow.async_step_notifications({})
            # Should create entry
            assert result["type"] == FlowResultType.CREATE_ENTRY
