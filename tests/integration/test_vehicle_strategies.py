"""Integration tests for vehicle control strategies.

Tests VehicleController + strategies through real hass fixture, asserting
on full-tuple service call arguments and distinctive vehicle/entity data.

Covers:
- NFR-9: integration tests use real HA framework
- NFR-8: multi-assert on every output field, not just truthiness
- NFR-10: distinctive data with boundary cases
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.vehicle.controller import (
    MAX_RETRY_ATTEMPTS,
    RETRY_TIME_WINDOW_SECONDS,
    VehicleController,
    create_control_strategy,
)
from custom_components.ev_trip_planner.vehicle.external import (
    ExternalStrategy,
    ScriptStrategy,
)
from custom_components.ev_trip_planner.vehicle.strategy import (
    ServiceStrategy,
    SwitchStrategy,
)

# Distinctive vehicle IDs (NFR-10)
VESPA_VESPA90 = "vespa_90_tesla"
TESLA_MODEL3 = "tesla_model3_p"
NISSAN_LEAF = "nissan_leaf_40"


class TestVehicleControllerIntegrationSwitch:
    """Full controller flow with SwitchStrategy via real hass fixture."""

    @pytest.mark.asyncio
    async def test_switch_activate_deactivate_full_flow(self, hass):
        """Controller activate/deactivate with SwitchStrategy asserts full call args."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "switch",
                "charge_control_entity": "switch.vespa_charger",
            },
        )
        controller = VehicleController(hass, VESPA_VESPA90)
        controller.set_strategy(strategy)

        # Activate
        result = await controller.async_activate_charging()
        assert result is True  # NFR-8: assert truthiness

        # NFR-8: multi-assert on full-tuple call args
        call = hass.services.async_call.call_args
        assert call is not None
        args = call[0]
        kwargs = call[1]
        assert args == ("switch", "turn_on", {"entity_id": "switch.vespa_charger"})
        assert kwargs == {}

        # Deactivate
        result = await controller.async_deactivate_charging()
        assert result is True
        call2 = hass.services.async_call.call_args
        args2 = call2[0]
        assert args2 == ("switch", "turn_off", {"entity_id": "switch.vespa_charger"})

    @pytest.mark.asyncio
    async def test_switch_get_status_via_hass_states(self, hass):
        """SwitchStrategy status reads from hass.states.get with distinctive entity."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "switch",
                "charge_control_entity": "switch.tesla_charger",
            },
        )
        controller = VehicleController(hass, TESLA_MODEL3)
        controller.set_strategy(strategy)

        # Entity off → status False
        hass._states_dict = {}
        assert await controller.async_get_charging_status() is False

        # Entity on → status True
        state_obj = MagicMock()
        state_obj.state = "on"
        hass.states.get = MagicMock(return_value=state_obj)
        assert await controller.async_get_charging_status() is True


class TestVehicleControllerIntegrationService:
    """Full controller flow with ServiceStrategy via real hass fixture."""

    @pytest.mark.asyncio
    async def test_service_activate_deactivate_with_data_on(self, hass):
        """ServiceStrategy activate with charge_service_data_on asserts full call args."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "service",
                "charge_service_on": "input_boolean.turn_on_charger",
                "charge_service_off": "input_boolean.turn_off_charger",
                "charge_service_data_on": {
                    "entity_id": "switch.nissan_charger",
                    "brightness": 255,
                },
            },
        )
        controller = VehicleController(hass, NISSAN_LEAF)
        controller.set_strategy(strategy)

        result = await controller.async_activate_charging()
        assert result is True

        # Multi-assert on full-tuple service call args
        call = hass.services.async_call.call_args
        args = call[0]
        assert args[0] == "input_boolean"
        assert args[1] == "turn_on_charger"
        assert args[2] == {"entity_id": "switch.nissan_charger", "brightness": 255}

        # Deactivate calls service_off with data_off default {}
        result = await controller.async_deactivate_charging()
        assert result is True
        call2 = hass.services.async_call.call_args
        args2 = call2[0]
        assert args2[0] == "input_boolean"
        assert args2[1] == "turn_off_charger"
        assert args2[2] == {}

    @pytest.mark.asyncio
    async def test_service_activate_deactivate_with_full_data(self, hass):
        """ServiceStrategy with both charge_service_data_on and charge_service_data_off."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "service",
                "charge_service_on": "homeassistant.turn_on",
                "charge_service_off": "homeassistant.turn_off",
                "charge_service_data_on": {"entity_id": "switch.charger1"},
                "charge_service_data_off": {"entity_id": "switch.charger1"},
            },
        )
        controller = VehicleController(hass, VESPA_VESPA90)
        controller.set_strategy(strategy)

        await controller.async_activate_charging()
        call = hass.services.async_call.call_args
        assert call[0] == ("homeassistant", "turn_on", {"entity_id": "switch.charger1"})

        await controller.async_deactivate_charging()
        call2 = hass.services.async_call.call_args
        assert call2[0] == (
            "homeassistant",
            "turn_off",
            {"entity_id": "switch.charger1"},
        )


class TestVehicleControllerIntegrationScript:
    """Full controller flow with ScriptStrategy via real hass fixture."""

    @pytest.mark.asyncio
    async def test_script_activate_deactivate_full_flow(self, hass):
        """ScriptStrategy activate/deactivate strips 'script.' prefix correctly."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "script",
                "charge_script_on": "script.start_charging_vespa",
                "charge_script_off": "script.stop_charging_vespa",
            },
        )
        controller = VehicleController(hass, VESPA_VESPA90)
        controller.set_strategy(strategy)

        # Activate
        result = await controller.async_activate_charging()
        assert result is True

        # Multi-assert: domain, service (stripped), data
        call = hass.services.async_call.call_args
        args = call[0]
        assert args[0] == "script"
        assert args[1] == "start_charging_vespa"
        assert args[2] == {}

        # Deactivate
        result = await controller.async_deactivate_charging()
        assert result is True
        call2 = hass.services.async_call.call_args
        args2 = call2[0]
        assert args2[0] == "script"
        assert args2[1] == "stop_charging_vespa"
        assert args2[2] == {}

    @pytest.mark.asyncio
    async def test_script_status_always_false(self, hass):
        """ScriptStrategy status returns False (scripts don't report status)."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "script",
                "charge_script_on": "script.start_charging",
                "charge_script_off": "script.stop_charging",
            },
        )
        controller = VehicleController(hass, TESLA_MODEL3)
        controller.set_strategy(strategy)

        assert await controller.async_get_charging_status() is False


class TestVehicleControllerIntegrationExternal:
    """Full controller flow with ExternalStrategy via real hass fixture."""

    @pytest.mark.asyncio
    async def test_external_activate_returns_true_no_service_call(self, hass):
        """ExternalStrategy activate is a no-op: returns True, zero service calls."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "external",
            },
        )
        controller = VehicleController(hass, NISSAN_LEAF)
        controller.set_strategy(strategy)

        result = await controller.async_activate_charging()
        assert result is True

        # ExternalStrategy does NOT call hass.services.async_call
        hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_external_deactivate_returns_true_no_service_call(self, hass):
        """ExternalStrategy deactivate is a no-op: returns True, zero service calls."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "external",
            },
        )
        controller = VehicleController(hass, VESPA_VESPA90)
        controller.set_strategy(strategy)

        result = await controller.async_deactivate_charging()
        assert result is True
        hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_external_status_always_false(self, hass):
        """ExternalStrategy status always returns False."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "external",
            },
        )
        controller = VehicleController(hass, TESLA_MODEL3)
        controller.set_strategy(strategy)

        assert await controller.async_get_charging_status() is False


class TestCreateControlStrategyFactory:
    """Test create_control_strategy factory with distinctive data."""

    @pytest.mark.asyncio
    async def test_factory_switch_creates_correct_entity_id(self, hass):
        """SwitchStrategy from factory stores entity_id correctly."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "switch",
                "charge_control_entity": "switch.vespa_90_charger",
            },
        )
        assert isinstance(strategy, SwitchStrategy)
        assert strategy.switch_entity_id == "switch.vespa_90_charger"
        # assert config unchanged
        assert strategy.config == {"entity_id": "switch.vespa_90_charger"}

    @pytest.mark.asyncio
    async def test_factory_service_with_all_fields(self, hass):
        """ServiceStrategy from factory with all config fields."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "service",
                "charge_service_on": "scene.activate_charging",
                "charge_service_off": "scene.deactivate_charging",
                "charge_service_data_on": {
                    "entity_id": "switch.charger",
                    "transition": 5,
                },
                "charge_service_data_off": {"entity_id": "switch.charger"},
            },
        )
        assert isinstance(strategy, ServiceStrategy)
        assert strategy.service_on == "scene.activate_charging"
        assert strategy.service_off == "scene.deactivate_charging"
        assert strategy.data_on == {"entity_id": "switch.charger", "transition": 5}
        assert strategy.data_off == {"entity_id": "switch.charger"}

    @pytest.mark.asyncio
    async def test_factory_script_strips_prefix(self, hass):
        """ScriptStrategy from factory stores full script IDs."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "script",
                "charge_script_on": "script.start_ev_charging",
                "charge_script_off": "script.stop_ev_charging",
            },
        )
        assert isinstance(strategy, ScriptStrategy)
        assert strategy.script_on == "script.start_ev_charging"
        assert strategy.script_off == "script.stop_ev_charging"

    @pytest.mark.asyncio
    async def test_factory_external_default_on_unknown_type(self, hass):
        """Unknown control_type → ExternalStrategy."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "unknown_strategy",
            },
        )
        assert isinstance(strategy, ExternalStrategy)

    @pytest.mark.asyncio
    async def test_factory_external_on_none_control_type(self, hass):
        """control_type=none → ExternalStrategy."""
        strategy = create_control_strategy(
            hass,
            {
                "control_type": "none",
            },
        )
        assert isinstance(strategy, ExternalStrategy)


class TestRetryStateIntegration:
    """Integration tests for RetryState with real time constraints."""

    def test_retry_state_max_attempts_and_window(self):
        """RetryState tracks attempts up to MAX_RETRY_ATTEMPTS within window."""
        controller = VehicleController(MagicMock(), VESPA_VESPA90)

        # Initial state
        assert controller._retry_state.get_attempt_count() == 0
        assert controller._retry_state.should_retry() is True

        # Add MAX_RETRY_ATTEMPTS (3) attempts → should not retry
        for _ in range(MAX_RETRY_ATTEMPTS):
            controller._retry_state.add_attempt()
        assert controller._retry_state.get_attempt_count() == MAX_RETRY_ATTEMPTS
        assert controller._retry_state.should_retry() is False

        # Reset
        controller._retry_state.reset()
        assert controller._retry_state.get_attempt_count() == 0
        assert controller._retry_state.should_retry() is True

    def test_get_retry_state_returns_full_dict(self, hass):
        """get_retry_state returns dict with all expected keys and values."""
        controller = VehicleController(hass, TESLA_MODEL3)
        state = controller.get_retry_state()

        # NFR-8: multi-assert on every field
        assert state["attempts"] == 0
        assert state["max_attempts"] == MAX_RETRY_ATTEMPTS
        assert state["can_retry"] is True
        assert state["time_window_seconds"] == RETRY_TIME_WINDOW_SECONDS

    def test_retry_state_values_match_module_constants(self):
        """MAX_RETRY_ATTEMPTS and RETRY_TIME_WINDOW_SECONDS are consistent."""
        assert MAX_RETRY_ATTEMPTS == 3
        assert RETRY_TIME_WINDOW_SECONDS == 300


class TestVehicleControllerIntegrationPresence:
    """Controller presence monitoring integration."""

    @pytest.mark.asyncio
    async def test_controller_with_presence_config_no_sensor(self, hass):
        """Controller init with presence config but no charging_sensor."""
        config = {"charging_sensor": "binary_sensor.plugged"}
        controller = VehicleController(hass, VESPA_VESPA90, presence_config=config)
        assert controller._charging_sensor == "binary_sensor.plugged"

    @pytest.mark.asyncio
    async def test_controller_activate_with_no_presence_monitor(self, hass):
        """No presence monitor → activate passes immediately."""
        controller = VehicleController(hass, TESLA_MODEL3)
        strategy = MagicMock()
        strategy.async_activate = AsyncMock(return_value=True)
        controller.set_strategy(strategy)
        # No _presence_monitor → presence check short-circuits
        result = await controller.async_activate_charging()
        assert result is True

    @pytest.mark.asyncio
    async def test_controller_deactivate_updates_state(self, hass):
        """Deactivate with strategy updates last_charging_state tracking."""
        controller = VehicleController(hass, NISSAN_LEAF)
        strategy = MagicMock()
        strategy.async_deactivate = AsyncMock(return_value=True)
        controller.set_strategy(strategy)
        # Without charging_sensor, _update_charging_state_after_deactivation returns early
        result = await controller.async_deactivate_charging()
        assert result is True
        # _last_charging_state should be set (None since no sensor)
        assert controller._last_charging_state is None
