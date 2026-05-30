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
    DEFAULT_BATTERY_CAPACITY_KWH,
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
        # Assert default values — kills default_value mutations (→ None)
        # Defaults are on Required keys as callable factories
        # Build a lookup dict from vol.Required keys
        schema_map: dict[str, float] = {}
        for key, _value in result["data_schema"].schema.items():
            schema_map[str(key)] = key.default()  # type: ignore[union-attr]
        assert schema_map[CONF_BATTERY_CAPACITY] == DEFAULT_BATTERY_CAPACITY_KWH

    @pytest.mark.asyncio
    async def test_show_form_defaults_from_entry_data(self):
        """Form shows values from entry data when options is empty — kills default_value mutants.

        When entry.data has values, the form should show those values as defaults.
        Mutant: config_data.get(key, default) → config_data.get(key, None)
        would change the default from the entry data value to None.
        """
        entry = MagicMock()
        entry.data = {
            CONF_BATTERY_CAPACITY: 80.0,
            CONF_CHARGING_POWER: 22.0,
            CONF_CONSUMPTION: 0.2,
            CONF_SAFETY_MARGIN: 25,
            CONF_T_BASE: 18.0,
        }
        entry.options = {}
        handler = EVTripPlannerOptionsFlowHandler(entry)

        result = await handler.async_step_init()
        assert result["type"] is FlowResultType.FORM

        # Voluptuous schema: keys are vol.Required objects, values are validators.
        # Find defaults by scanning the schema dict.
        schema_map: dict[str, float] = {}
        for key, _value in result["data_schema"].schema.items():
            schema_map[str(key)] = key.default()  # type: ignore[union-attr]

        # These assertions kill the default_value→None mutations
        assert schema_map[CONF_BATTERY_CAPACITY] == 80.0
        assert schema_map[CONF_CHARGING_POWER] == 22.0
        assert schema_map[CONF_CONSUMPTION] == 0.2
        assert schema_map[CONF_SAFETY_MARGIN] == 25
        assert schema_map[CONF_T_BASE] == 18.0

    @pytest.mark.asyncio
    async def test_show_form_defaults_from_entry_options(self):
        """Options take precedence over data — kills default_value mutants.

        When entry.options has values, they should take precedence over entry.data.
        """
        entry = MagicMock()
        entry.data = {CONF_BATTERY_CAPACITY: 50.0}
        entry.options = {CONF_BATTERY_CAPACITY: 70.0, CONF_CONSUMPTION: 0.18}
        handler = EVTripPlannerOptionsFlowHandler(entry)

        result = await handler.async_step_init()
        assert result["type"] is FlowResultType.FORM
        # Build a lookup dict from vol.Required keys
        schema_map: dict[str, float] = {}
        for key, _value in result["data_schema"].schema.items():
            schema_map[str(key)] = key.default()  # type: ignore[union-attr]
        # Options precedence: 70.0 not 50.0 (kills mutations that would use data instead of options)
        assert schema_map[CONF_BATTERY_CAPACITY] == 70.0
        assert schema_map[CONF_CONSUMPTION] == 0.18

    @pytest.mark.asyncio
    async def test_submit_all_options(self):
        """Submit all options → creates entry with data."""
        entry = MagicMock()
        entry.data = {}
        entry.options = {}
        handler = EVTripPlannerOptionsFlowHandler(entry)

        result = await handler.async_step_init(
            {
                CONF_BATTERY_CAPACITY: 75.0,
                CONF_CHARGING_POWER: 22.0,
                CONF_CONSUMPTION: 0.15,
                CONF_SAFETY_MARGIN: 30,
                CONF_T_BASE: 12.0,
                CONF_SOH_SENSOR: "sensor.soh",
            }
        )
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

        result = await handler.async_step_init(
            {
                CONF_BATTERY_CAPACITY: 80.0,
            }
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == {CONF_BATTERY_CAPACITY: 80.0}

    @pytest.mark.asyncio
    async def test_submit_without_soh_sensor(self):
        """Submit without SOH sensor → omits SOH from data."""
        entry = MagicMock()
        entry.data = {}
        entry.options = {}
        handler = EVTripPlannerOptionsFlowHandler(entry)

        result = await handler.async_step_init(
            {
                CONF_BATTERY_CAPACITY: 65.0,
                CONF_CONSUMPTION: 0.18,
            }
        )
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

    @pytest.mark.asyncio
    async def test_soh_entity_selector_single_select(self):
        """EntitySelectorConfig for SOH sensor has multiple=False.
        Kills mutant: multiple=False→True which would make it multi-select."""
        entry = MagicMock()
        entry.data = {}
        entry.options = {}
        handler = EVTripPlannerOptionsFlowHandler(entry)

        result = await handler.async_step_init()
        assert result["type"] is FlowResultType.FORM
        schema = result["data_schema"].schema
        soh_field = schema.get("soh_sensor")
        assert soh_field is not None
        # EntitySelector.config is a dict with 'multiple' key
        config = soh_field.config  # type: ignore[union-attr]
        assert (
            config["multiple"] is False
        )  # NOT multi-select (kills boolean flip mutant)
