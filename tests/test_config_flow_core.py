"""Tests for EV Trip Planner config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import AbortFlow, FlowResultType

from custom_components.ev_trip_planner.const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CONSUMPTION,
    CONF_CONTROL_TYPE,
    CONF_SAFETY_MARGIN,
    CONF_SOC_SENSOR,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_TYPE,
    CONTROL_TYPE_NONE,
    DEFAULT_VEHICLE_TYPE,
    DOMAIN,
    VEHICLE_TYPE_EV,
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

    # User step
    with patch.object(flow, "async_set_unique_id", new=AsyncMock()) as _set_uid, patch.object(
        flow, "_abort_if_unique_id_configured", return_value=None
    ) as _abort_check:
        result = await flow.async_step_user(
            {
                CONF_VEHICLE_NAME: "Chispitas",
                CONF_VEHICLE_TYPE: VEHICLE_TYPE_EV,
            }
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "sensors"

    # Sensors step
    result = await flow.async_step_sensors(
        {
            CONF_SOC_SENSOR: "sensor.soc",
            CONF_BATTERY_CAPACITY: 50.0,
            CONF_CHARGING_POWER: 7.2,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "consumption"

    # Consumption step
    result = await flow.async_step_consumption(
        {
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 10,
            CONF_CONTROL_TYPE: CONTROL_TYPE_NONE,
        }
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Chispitas"
    data = result["data"]
    assert data[CONF_VEHICLE_NAME] == "Chispitas"
    assert data[CONF_VEHICLE_TYPE] == VEHICLE_TYPE_EV
    assert data[CONF_SOC_SENSOR] == "sensor.soc"
    assert data[CONF_BATTERY_CAPACITY] == 50.0
    assert data[CONF_CHARGING_POWER] == 7.2
    assert data[CONF_CONSUMPTION] == 0.15
    assert data[CONF_SAFETY_MARGIN] == 10
    assert data[CONF_CONTROL_TYPE] == CONTROL_TYPE_NONE


@pytest.mark.asyncio
async def test_duplicate_vehicle_aborts():
    """Test that configuring the same vehicle name aborts due to unique_id."""
    flow = EVTripPlannerConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}

    with patch.object(flow, "async_set_unique_id", new=AsyncMock()):
        with patch.object(
            flow,
            "_abort_if_unique_id_configured",
            side_effect=AbortFlow("already_configured"),
        ):
            with pytest.raises(AbortFlow) as ctx:
                await flow.async_step_user(
                    {
                        CONF_VEHICLE_NAME: "Chispitas",
                        CONF_VEHICLE_TYPE: DEFAULT_VEHICLE_TYPE,
                    }
                )
    assert str(ctx.value).endswith(": already_configured")
