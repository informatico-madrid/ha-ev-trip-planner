"""Tests for config_flow/options.py.

Covers EVTripPlannerOptionsFlowHandler async_step_init, form display,
and async_get_options_flow factory.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ev_trip_planner.config_flow.options import (
    EVTripPlannerOptionsFlowHandler,
    async_get_options_flow,
)
from custom_components.ev_trip_planner.const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CONSUMPTION,
    CONF_SAFETY_MARGIN,
    CONF_SOH_SENSOR,
    CONF_T_BASE,
)


class TestOptionsFlowHandler:
    """Test EVTripPlannerOptionsFlowHandler async_step_init paths."""

    def test_init_stores_entry(self):
        """Options flow handler stores the config entry."""
        entry = MagicMock()
        handler = EVTripPlannerOptionsFlowHandler(entry)
        assert handler._config_entry is entry

    @pytest.mark.asyncio
    async def test_show_form_no_input(self):
        """No user_input → shows form with defaults."""
        entry = MagicMock()
        entry.data = {}
        entry.options = {}
        handler = EVTripPlannerOptionsFlowHandler(entry)

        result = await handler.async_step_init()
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_show_form_with_data_and_options(self):
        """Form shows values from options when present."""
        entry = MagicMock()
        entry.data = {CONF_BATTERY_CAPACITY: 50.0}
        entry.options = {CONF_BATTERY_CAPACITY: 70.0, CONF_CONSUMPTION: 0.2}
        handler = EVTripPlannerOptionsFlowHandler(entry)

        result = await handler.async_step_init()
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_show_form_none_data(self):
        """None data → safe defaults used."""
        entry = MagicMock()
        entry.data = None
        entry.options = None
        handler = EVTripPlannerOptionsFlowHandler(entry)

        result = await handler.async_step_init()
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_submit_all_options(self):
        """Submit all options → creates entry with data."""
        entry = MagicMock()
        entry.data = {}
        entry.options = {}
        handler = EVTripPlannerOptionsFlowHandler(entry)

        result = await handler.async_step_init({
            CONF_BATTERY_CAPACITY: 75.0,
            CONF_CHARGING_POWER: 22.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 30,
            CONF_T_BASE: 12.0,
            CONF_SOH_SENSOR: "sensor.soh",
        })
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == {
            CONF_BATTERY_CAPACITY: 75.0,
            CONF_CHARGING_POWER: 22.0,
            CONF_CONSUMPTION: 0.15,
            CONF_SAFETY_MARGIN: 30,
            CONF_T_BASE: 12.0,
            CONF_SOH_SENSOR: "sensor.soh",
        }

    @pytest.mark.asyncio
    async def test_submit_partial_options(self):
        """Submit only some options → only those included."""
        entry = MagicMock()
        entry.data = {}
        entry.options = {}
        handler = EVTripPlannerOptionsFlowHandler(entry)

        result = await handler.async_step_init({
            CONF_BATTERY_CAPACITY: 80.0,
        })
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == {CONF_BATTERY_CAPACITY: 80.0}

    @pytest.mark.asyncio
    async def test_submit_without_soh_sensor(self):
        """Submit without SOH sensor → omits SOH from data."""
        entry = MagicMock()
        entry.data = {}
        entry.options = {}
        handler = EVTripPlannerOptionsFlowHandler(entry)

        result = await handler.async_step_init({
            CONF_BATTERY_CAPACITY: 65.0,
            CONF_CONSUMPTION: 0.18,
        })
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert CONF_SOH_SENSOR not in result["data"]


class TestAsyncGetOptionsFlow:
    """Test async_get_options_flow factory."""

    def test_returns_handler(self):
        """async_get_options_flow returns an EVTripPlannerOptionsFlowHandler."""
        entry = MagicMock()
        handler = async_get_options_flow(entry)
        assert isinstance(handler, EVTripPlannerOptionsFlowHandler)
        assert handler._config_entry is entry
