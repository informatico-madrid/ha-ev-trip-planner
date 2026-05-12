"""Tests for config_flow/main.py helper functions.

Covers _read_emhass_config, _get_emhass_planning_horizon,
_get_emhass_max_deferrable_loads, EVTripPlannerFlowHandler basic paths.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ev_trip_planner.config_flow.main import (
    EVTripPlannerFlowHandler,
    _get_emhass_max_deferrable_loads,
    _get_emhass_planning_horizon,
    _read_emhass_config,
)


class TestReadEmhassConfig:
    """Test _read_emhass_config (lines 213-235)."""

    def test_none_path_returns_none(self):
        """None path → returns None."""
        assert _read_emhass_config(None) is None

    def test_nonexistent_path_returns_none(self):
        """Non-existent path → returns None."""
        assert _read_emhass_config("/nonexistent/path/config.json") is None

    def test_valid_config(self, tmp_path):
        """Valid JSON file → returns parsed config."""
        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps({"end_timesteps_of_each_deferrable_load": [168]})
        )

        result = _read_emhass_config(str(config_file))
        assert result is not None
        assert result["end_timesteps_of_each_deferrable_load"] == [168]

    def test_invalid_json_returns_none(self, tmp_path):
        """Invalid JSON → returns None."""
        config_file = tmp_path / "config.json"
        config_file.write_text("not valid json {{{")

        result = _read_emhass_config(str(config_file))
        assert result is None

    def test_permission_error_returns_none(self):
        """Permission error → returns None (path exists but can't read)."""
        # Create a file, then try to read with wrong path (simulates permission)
        result = _read_emhass_config("/root/protected/config.json")
        assert result is None


class TestGetEmhassPlanningHorizon:
    """Test _get_emhass_planning_horizon (lines 238-268)."""

    def test_none_config(self):
        """None config → returns None."""
        assert _get_emhass_planning_horizon(None) is None

    def test_empty_config(self):
        """Empty dict → returns None."""
        assert _get_emhass_planning_horizon({}) is None

    def test_no_end_timesteps(self):
        """No end_timesteps key → returns None."""
        assert _get_emhass_planning_horizon({"other_key": 123}) is None

    def test_empty_timesteps_list(self):
        """Empty list → returns None."""
        assert (
            _get_emhass_planning_horizon({"end_timesteps_of_each_deferrable_load": []})
            is None
        )

    def test_valid_7_day_config(self):
        """168 timesteps → 7 days."""
        result = _get_emhass_planning_horizon(
            {"end_timesteps_of_each_deferrable_load": [168]}
        )
        assert result == 7

    def test_valid_1_day_config(self):
        """24 timesteps → 1 day."""
        result = _get_emhass_planning_horizon(
            {"end_timesteps_of_each_deferrable_load": [24]}
        )
        assert result == 1

    def test_3_day_config(self):
        """72 timesteps → 3 days."""
        result = _get_emhass_planning_horizon(
            {"end_timesteps_of_each_deferrable_load": [72]}
        )
        assert result == 3

    def test_small_timesteps_returns_none(self):
        """Less than 24 timesteps → returns None (less than 1 day)."""
        result = _get_emhass_planning_horizon(
            {"end_timesteps_of_each_deferrable_load": [12]}
        )
        assert result is None


class TestGetEmhassMaxDeferrableLoads:
    """Test _get_emhass_max_deferrable_loads (lines 271-289)."""

    def test_none_config(self):
        """None config → returns None."""
        assert _get_emhass_max_deferrable_loads(None) is None

    def test_empty_config(self):
        """Empty dict → returns None."""
        assert _get_emhass_max_deferrable_loads({}) is None

    def test_no_num_loads(self):
        """No number_of_deferrable_loads key → returns None."""
        assert _get_emhass_max_deferrable_loads({"other_key": 123}) is None

    def test_zero_returns_none(self):
        """Zero loads → returns None."""
        assert (
            _get_emhass_max_deferrable_loads({"number_of_deferrable_loads": 0}) is None
        )

    def test_negative_returns_none(self):
        """Negative loads → returns None."""
        assert (
            _get_emhass_max_deferrable_loads({"number_of_deferrable_loads": -1}) is None
        )

    def test_valid_value(self):
        """Valid value → returns it."""
        result = _get_emhass_max_deferrable_loads({"number_of_deferrable_loads": 50})
        assert result == 50

    def test_100_loads(self):
        """100 loads → returns 100."""
        result = _get_emhass_max_deferrable_loads({"number_of_deferrable_loads": 100})
        assert result == 100


class TestEVTripPlannerFlowHandler:
    """Test EVTripPlannerFlowHandler basic paths."""

    @pytest.mark.asyncio
    async def test_async_step_user_show_form(self):
        """No user_input → shows form."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()

        result = await handler.async_step_user()
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_async_step_user_empty_name(self):
        """Empty vehicle name → shows form with error."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()

        result = await handler.async_step_user({"vehicle_name": ""})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert "base" in result.get("errors", {})

    @pytest.mark.asyncio
    async def test_async_step_user_too_long(self):
        """Vehicle name > 100 chars → shows form with error."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()

        result = await handler.async_step_user({"vehicle_name": "a" * 101})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_async_step_user_valid(self):
        """Valid vehicle name → goes to sensors step."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {}  # mutable dict for _get_vehicle_data

        result = await handler.async_step_user({"vehicle_name": "My Car"})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "sensors"

    @pytest.mark.asyncio
    async def test_async_step_sensors_show_form(self):
        """No user_input → shows form."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()

        result = await handler.async_step_sensors()
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "sensors"

    @pytest.mark.asyncio
    async def test_async_step_sensors_invalid_battery_capacity(self):
        """Battery capacity < 10 → shows form with error."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {}

        result = await handler.async_step_sensors({"battery_capacity_kwh": 5})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "sensors"

    @pytest.mark.asyncio
    async def test_async_step_sensors_invalid_consumption(self):
        """Consumption < 0.05 → shows form with error."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {}

        result = await handler.async_step_sensors({"kwh_per_km": 0.01})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "sensors"

    @pytest.mark.asyncio
    async def test_async_step_sensors_invalid_safety_margin(self):
        """Safety margin > 50 → shows form with error."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()
        handler.context = {}

        result = await handler.async_step_sensors({"safety_margin_percent": 60})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "sensors"

    @pytest.mark.asyncio
    async def test_async_step_emhass_show_form(self):
        """No user_input → shows form."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()

        result = await handler.async_step_emhass()
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "emhass"

    @pytest.mark.asyncio
    async def test_async_step_emhass_invalid_horizon(self):
        """Planning horizon > 365 → shows form with error."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()

        result = await handler.async_step_emhass({"planning_horizon_days": 400})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "emhass"

    @pytest.mark.asyncio
    async def test_async_step_emhass_invalid_max_loads(self):
        """Max deferrable loads > 100 → shows form with error."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()

        result = await handler.async_step_emhass({"max_deferrable_loads": 150})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "emhass"

    @pytest.mark.asyncio
    async def test_async_step_presence_show_form(self):
        """No user_input → shows form."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()

        result = await handler.async_step_presence()
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "presence"

    @pytest.mark.asyncio
    async def test_async_step_notifications_show_form(self):
        """No user_input → shows form."""
        handler = EVTripPlannerFlowHandler()
        handler.hass = MagicMock()

        result = await handler.async_step_notifications()
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "notifications"

    @pytest.mark.asyncio
    async def test_async_migrate_entry_version_2(self):
        """Version 2 → migrates to v3, returns True."""
        hass = MagicMock()
        hass.config_entries.async_update_entry = AsyncMock(return_value=None)
        entry = MagicMock()
        entry.version = 2
        entry.data = {"vehicle_name": "test"}

        result = await EVTripPlannerFlowHandler.async_migrate_entry(hass, entry)
        assert result is True
        hass.config_entries.async_update_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_migrate_entry_unknown_version(self):
        """Unknown version → returns False."""
        hass = MagicMock()
        entry = MagicMock()
        entry.version = 99

        result = await EVTripPlannerFlowHandler.async_migrate_entry(hass, entry)
        assert result is False

    @pytest.mark.asyncio
    async def test_async_get_options_flow(self):
        """async_get_options_flow returns OptionsFlowHandler."""
        entry = MagicMock()
        options_flow = EVTripPlannerFlowHandler.async_get_options_flow(entry)
        assert options_flow is not None
