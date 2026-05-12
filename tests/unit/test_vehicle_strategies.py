"""Tests for vehicle/ modules: strategy, controller, external.

Covers RetryState, HomeAssistantWrapper, SwitchStrategy, ServiceStrategy,
ScriptStrategy, ExternalStrategy, create_control_strategy, VehicleController.
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
    HomeAssistantWrapper,
    RetryState,
    ServiceStrategy,
    SwitchStrategy,
)


class TestRetryState:
    """Test RetryState dataclass (strategy.py lines 23-55)."""

    def test_reset_empty_attempts(self):
        """Reset clears all attempts."""
        rs = RetryState()
        rs.add_attempt()
        assert rs.get_attempt_count() == 1
        rs.reset()
        assert rs.get_attempt_count() == 0
        assert rs.should_retry() is True

    def test_add_attempt_increments_count(self):
        """add_attempt increases count."""
        rs = RetryState()
        rs.add_attempt()
        assert rs.get_attempt_count() == 1
        rs.add_attempt()
        assert rs.get_attempt_count() == 2

    def test_should_retry_under_limit(self):
        """Within limit → should_retry returns True."""
        rs = RetryState()
        rs.add_attempt()
        rs.add_attempt()
        assert rs.should_retry() is True

    def test_should_retry_at_limit(self):
        """At limit → should_retry returns False."""
        rs = RetryState()
        for _ in range(MAX_RETRY_ATTEMPTS):
            rs.add_attempt()
        assert rs.should_retry() is False

    def test_should_retry_over_limit(self):
        """Over limit → should_retry returns False."""
        rs = RetryState()
        for _ in range(MAX_RETRY_ATTEMPTS + 5):
            rs.add_attempt()
        assert rs.should_retry() is False

    def test_get_attempt_count(self):
        """get_attempt_count returns current count."""
        rs = RetryState()
        assert rs.get_attempt_count() == 0
        rs.add_attempt()
        assert rs.get_attempt_count() == 1


class TestHomeAssistantWrapper:
    """Test HomeAssistantWrapper (strategy.py lines 58-72)."""

    @pytest.mark.asyncio
    async def test_async_call_service(self):
        """Calls hass.services.async_call with correct args."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock()
        wrapper = HomeAssistantWrapper(hass)
        await wrapper.async_call_service("switch", "turn_on", {"entity_id": "sw.1"})
        hass.services.async_call.assert_called_once_with(
            "switch", "turn_on", {"entity_id": "sw.1"}
        )

    def test_get_state(self):
        """get_state returns hass.states.get result."""
        hass = MagicMock()
        hass.states.get = MagicMock(return_value=MagicMock(state="on"))
        wrapper = HomeAssistantWrapper(hass)
        state = wrapper.get_state("sensor.battery")
        assert state.state == "on"


class TestSwitchStrategy:
    """Test SwitchStrategy (strategy.py lines 95-128)."""

    @pytest.mark.asyncio
    async def test_activate_success(self):
        """Success → returns True."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock()
        wrapper = HomeAssistantWrapper(hass)
        strategy = SwitchStrategy(wrapper, {"entity_id": "switch.charger"})

        result = await strategy.async_activate()
        assert result is True

    @pytest.mark.asyncio
    async def test_activate_failure(self):
        """Exception → returns False."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock(side_effect=RuntimeError("fail"))
        wrapper = HomeAssistantWrapper(hass)
        strategy = SwitchStrategy(wrapper, {"entity_id": "switch.charger"})

        result = await strategy.async_activate()
        assert result is False

    @pytest.mark.asyncio
    async def test_deactivate_success(self):
        """Deactivate calls turn_off → returns True."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock()
        wrapper = HomeAssistantWrapper(hass)
        strategy = SwitchStrategy(wrapper, {"entity_id": "switch.charger"})

        result = await strategy.async_deactivate()
        assert result is True

    @pytest.mark.asyncio
    async def test_deactivate_failure(self):
        """Deactivate exception → returns False."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock(side_effect=RuntimeError("fail"))
        wrapper = HomeAssistantWrapper(hass)
        strategy = SwitchStrategy(wrapper, {"entity_id": "switch.charger"})

        result = await strategy.async_deactivate()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_status_on(self):
        """Entity state is 'on' → True."""
        hass = MagicMock()
        hass.states.get = MagicMock(return_value=MagicMock(state="on"))
        wrapper = HomeAssistantWrapper(hass)
        strategy = SwitchStrategy(wrapper, {"entity_id": "switch.charger"})

        assert await strategy.async_get_status() is True

    @pytest.mark.asyncio
    async def test_get_status_off(self):
        """Entity state is 'off' → False."""
        hass = MagicMock()
        hass.states.get = MagicMock(return_value=MagicMock(state="off"))
        wrapper = HomeAssistantWrapper(hass)
        strategy = SwitchStrategy(wrapper, {"entity_id": "switch.charger"})

        assert await strategy.async_get_status() is False

    @pytest.mark.asyncio
    async def test_get_status_none(self):
        """Entity not found → False."""
        hass = MagicMock()
        hass.states.get = MagicMock(return_value=None)
        wrapper = HomeAssistantWrapper(hass)
        strategy = SwitchStrategy(wrapper, {"entity_id": "switch.charger"})

        assert await strategy.async_get_status() is False


class TestServiceStrategy:
    """Test ServiceStrategy (strategy.py lines 131-166)."""

    @pytest.mark.asyncio
    async def test_activate_success(self):
        """Success → returns True."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock()
        wrapper = HomeAssistantWrapper(hass)
        strategy = ServiceStrategy(
            wrapper,
            {
                "service_on": "input_boolean.turn_on",
                "service_off": "input_boolean.turn_off",
            },
        )

        result = await strategy.async_activate()
        assert result is True
        hass.services.async_call.assert_called_once_with("input_boolean", "turn_on", {})

    @pytest.mark.asyncio
    async def test_activate_with_data(self):
        """Service call includes data_on."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock()
        wrapper = HomeAssistantWrapper(hass)
        strategy = ServiceStrategy(
            wrapper,
            {
                "service_on": "script.start_charging",
                "service_off": "script.stop_charging",
                "data_on": {"entity_id": "switch.charger"},
            },
        )

        await strategy.async_activate()
        call_args = hass.services.async_call.call_args
        assert call_args[0][2] == {"entity_id": "switch.charger"}

    @pytest.mark.asyncio
    async def test_activate_failure(self):
        """Exception → returns False."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock(side_effect=RuntimeError("fail"))
        wrapper = HomeAssistantWrapper(hass)
        strategy = ServiceStrategy(
            wrapper,
            {
                "service_on": "script.start",
                "service_off": "script.stop",
            },
        )

        assert await strategy.async_activate() is False

    @pytest.mark.asyncio
    async def test_deactivate_success(self):
        """Deactivate → calls service_off."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock()
        wrapper = HomeAssistantWrapper(hass)
        strategy = ServiceStrategy(
            wrapper,
            {
                "service_on": "script.start",
                "service_off": "script.stop",
            },
        )

        result = await strategy.async_deactivate()
        assert result is True

    @pytest.mark.asyncio
    async def test_deactivate_failure(self):
        """Deactivate exception → returns False."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock(side_effect=RuntimeError("fail"))
        wrapper = HomeAssistantWrapper(hass)
        strategy = ServiceStrategy(
            wrapper,
            {
                "service_on": "script.start",
                "service_off": "script.stop",
            },
        )

        assert await strategy.async_deactivate() is False

    @pytest.mark.asyncio
    async def test_get_status_always_false(self):
        """ServiceStrategy always returns False for status."""
        hass = MagicMock()
        wrapper = HomeAssistantWrapper(hass)
        strategy = ServiceStrategy(
            wrapper,
            {
                "service_on": "script.start",
                "service_off": "script.stop",
            },
        )

        assert await strategy.async_get_status() is False


class TestScriptStrategy:
    """Test ScriptStrategy (external.py lines 18-56)."""

    @pytest.mark.asyncio
    async def test_activate_success(self):
        """Success → returns True."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock()
        wrapper = HomeAssistantWrapper(hass)
        strategy = ScriptStrategy(
            wrapper,
            {
                "script_on": "script.start_charging",
                "script_off": "script.stop_charging",
            },
        )

        result = await strategy.async_activate()
        assert result is True

    @pytest.mark.asyncio
    async def test_activate_failure(self):
        """Exception → returns False."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock(side_effect=RuntimeError("fail"))
        wrapper = HomeAssistantWrapper(hass)
        strategy = ScriptStrategy(
            wrapper,
            {
                "script_on": "script.start",
                "script_off": "script.stop",
            },
        )

        assert await strategy.async_activate() is False

    @pytest.mark.asyncio
    async def test_deactivate_success(self):
        """Deactivate → calls stop script."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock()
        wrapper = HomeAssistantWrapper(hass)
        strategy = ScriptStrategy(
            wrapper,
            {
                "script_on": "script.start",
                "script_off": "script.stop",
            },
        )

        result = await strategy.async_deactivate()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_status_always_false(self):
        """Scripts don't return status."""
        hass = MagicMock()
        wrapper = HomeAssistantWrapper(hass)
        strategy = ScriptStrategy(
            wrapper,
            {
                "script_on": "script.start",
                "script_off": "script.stop",
            },
        )

        assert await strategy.async_get_status() is False


class TestExternalStrategy:
    """Test ExternalStrategy (external.py lines 59-74)."""

    @pytest.mark.asyncio
    async def test_activate_returns_true(self):
        """External activate is a no-op that returns True."""
        strategy = ExternalStrategy(
            MagicMock(),  # hass_wrapper
            {},
        )
        assert await strategy.async_activate() is True

    @pytest.mark.asyncio
    async def test_deactivate_returns_true(self):
        """External deactivate is a no-op that returns True."""
        strategy = ExternalStrategy(MagicMock(), {})
        assert await strategy.async_deactivate() is True

    @pytest.mark.asyncio
    async def test_get_status_returns_false(self):
        """External status is unknown."""
        strategy = ExternalStrategy(MagicMock(), {})
        assert await strategy.async_get_status() is False


class TestCreateControlStrategy:
    """Test create_control_strategy factory (controller.py lines 35-64)."""

    @pytest.mark.asyncio
    async def test_switch_strategy(self):
        """control_type=switch → SwitchStrategy."""
        hass = MagicMock()
        config = {
            "control_type": "switch",
            "charge_control_entity": "switch.charger",
        }
        strategy = create_control_strategy(hass, config)
        assert isinstance(strategy, SwitchStrategy)
        assert strategy.switch_entity_id == "switch.charger"

    @pytest.mark.asyncio
    async def test_service_strategy(self):
        """control_type=service → ServiceStrategy."""
        hass = MagicMock()
        config = {
            "control_type": "service",
            "charge_service_on": "script.start",
            "charge_service_off": "script.stop",
        }
        strategy = create_control_strategy(hass, config)
        assert isinstance(strategy, ServiceStrategy)
        assert strategy.service_on == "script.start"

    @pytest.mark.asyncio
    async def test_script_strategy(self):
        """control_type=script → ScriptStrategy."""
        hass = MagicMock()
        config = {
            "control_type": "script",
            "charge_script_on": "script.start_charging",
            "charge_script_off": "script.stop_charging",
        }
        strategy = create_control_strategy(hass, config)
        assert isinstance(strategy, ScriptStrategy)

    @pytest.mark.asyncio
    async def test_external_default(self):
        """Unknown/missing control_type → ExternalStrategy."""
        hass = MagicMock()
        config = {"control_type": "unknown"}
        strategy = create_control_strategy(hass, config)
        assert isinstance(strategy, ExternalStrategy)

    @pytest.mark.asyncio
    async def test_external_none_control_type(self):
        """control_type=none → ExternalStrategy."""
        hass = MagicMock()
        config = {"control_type": "none"}
        strategy = create_control_strategy(hass, config)
        assert isinstance(strategy, ExternalStrategy)

    @pytest.mark.asyncio
    async def test_service_with_data(self):
        """Service strategy with data_on/data_off."""
        hass = MagicMock()
        config = {
            "control_type": "service",
            "charge_service_on": "script.start",
            "charge_service_off": "script.stop",
            "charge_service_data_on": {"entity_id": "sw.1"},
            "charge_service_data_off": {},
        }
        strategy = create_control_strategy(hass, config)
        assert isinstance(strategy, ServiceStrategy)
        assert strategy.data_on == {"entity_id": "sw.1"}
        assert strategy.data_off == {}


class TestVehicleController:
    """Test VehicleController (controller.py lines 67-294)."""

    def test_init_no_presence_config(self):
        """No presence config → no monitor, no charging sensor."""
        hass = MagicMock()
        controller = VehicleController(hass, "test_vehicle")
        assert controller.vehicle_id == "test_vehicle"
        assert controller._presence_monitor is None
        assert controller._charging_sensor is None
        assert controller._strategy is None

    def test_init_with_presence_config(self):
        """Presence config → monitor created, sensor stored."""
        hass = MagicMock()
        config = {"charging_sensor": "binary_sensor.plugged"}
        controller = VehicleController(hass, "test_vehicle", presence_config=config)
        assert controller._charging_sensor == "binary_sensor.plugged"
        # PresenceMonitor should be created (may fail without real HA, but we test setup)

    def test_set_strategy(self):
        """set_strategy stores the strategy."""
        hass = MagicMock()
        controller = VehicleController(hass, "test_vehicle")
        strategy = MagicMock()
        controller.set_strategy(strategy)
        assert controller._strategy is strategy

    def test_update_config_recreates_strategy(self):
        """update_config recreates strategy when one already exists."""
        hass = MagicMock()
        controller = VehicleController(hass, "test_vehicle")
        # First set a strategy
        initial_strategy = MagicMock()
        controller.set_strategy(initial_strategy)
        # Now update with config → should recreate
        config = {
            "control_type": "switch",
            "charge_control_entity": "switch.charger",
        }
        controller.update_config(config)
        assert controller._strategy is not None
        assert controller._strategy is not initial_strategy
        assert isinstance(controller._strategy, SwitchStrategy)

    def test_update_config_no_existing_strategy(self):
        """update_config with no existing strategy → strategy stays None."""
        hass = MagicMock()
        controller = VehicleController(hass, "test_vehicle")
        config = {
            "control_type": "switch",
            "charge_control_entity": "switch.charger",
        }
        controller.update_config(config)
        # Since _strategy was None, update_config doesn't create a new one
        assert controller._strategy is None

    @pytest.mark.asyncio
    async def test_async_setup(self):
        """async_setup logs info."""
        hass = MagicMock()
        controller = VehicleController(hass, "test_vehicle")
        # Should not raise
        await controller.async_setup()

    @pytest.mark.asyncio
    async def test_activate_no_strategy(self):
        """No strategy → returns False."""
        hass = MagicMock()
        controller = VehicleController(hass, "test_vehicle")
        result = await controller.async_activate_charging()
        assert result is False

    @pytest.mark.asyncio
    async def test_activate_with_strategy_success(self):
        """Strategy activates successfully → returns True."""
        hass = MagicMock()
        controller = VehicleController(hass, "test_vehicle")
        strategy = MagicMock()
        strategy.async_activate = AsyncMock(return_value=True)
        controller.set_strategy(strategy)
        # Without presence monitor, presence check passes
        result = await controller.async_activate_charging()
        assert result is True

    @pytest.mark.asyncio
    async def test_activate_with_strategy_failure(self):
        """Strategy activation fails → returns False, increments retry."""
        hass = MagicMock()
        controller = VehicleController(hass, "test_vehicle")
        strategy = MagicMock()
        strategy.async_activate = AsyncMock(return_value=False)
        controller.set_strategy(strategy)
        result = await controller.async_activate_charging()
        assert result is False

    def test_reset_retry_state(self):
        """reset_retry_state clears retry counter."""
        hass = MagicMock()
        controller = VehicleController(hass, "test_vehicle")
        controller._retry_state.add_attempt()
        assert controller._retry_state.get_attempt_count() == 1
        controller.reset_retry_state()
        assert controller._retry_state.get_attempt_count() == 0

    def test_get_retry_state(self):
        """get_retry_state returns correct dict."""
        hass = MagicMock()
        controller = VehicleController(hass, "test_vehicle")
        state = controller.get_retry_state()
        assert state["max_attempts"] == MAX_RETRY_ATTEMPTS
        assert state["time_window_seconds"] == RETRY_TIME_WINDOW_SECONDS
        assert state["attempts"] == 0
        assert state["can_retry"] is True

    @pytest.mark.asyncio
    async def test_deactivate_no_strategy(self):
        """No strategy → returns False."""
        hass = MagicMock()
        controller = VehicleController(hass, "test_vehicle")
        result = await controller.async_deactivate_charging()
        assert result is False

    @pytest.mark.asyncio
    async def test_presence_monitor_blocks(self):
        """Presence monitor reports not ready → activate blocked."""
        hass_mock = MagicMock()
        controller = VehicleController(hass_mock, "test_vehicle")
        strategy = MagicMock()
        strategy.async_activate = AsyncMock(return_value=True)
        controller.set_strategy(strategy)

        # Create a mock presence monitor
        monitor = MagicMock()
        monitor.async_check_charging_readiness = AsyncMock(
            return_value=(False, "not home")
        )
        controller._presence_monitor = monitor

        result = await controller.async_activate_charging()
        assert result is False

    @pytest.mark.asyncio
    async def test_charging_sensor_not_found(self):
        """Charging sensor not found → not charging."""
        hass_mock = MagicMock()
        hass_mock.states.get = MagicMock(return_value=None)
        controller = VehicleController(hass_mock, "test_vehicle")
        controller._charging_sensor = "binary_sensor.plugged"
        controller._presence_monitor = None

        result = await controller._async_check_charging_sensor()
        assert result is False

    @pytest.mark.asyncio
    async def test_charging_sensor_is_on(self):
        """Charging sensor is 'on' → returns True."""
        hass_mock = MagicMock()
        hass_mock.states.get = MagicMock(return_value=MagicMock(state="on"))
        controller = VehicleController(hass_mock, "test_vehicle")
        controller._charging_sensor = "binary_sensor.plugged"

        result = await controller._async_check_charging_sensor()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_and_reset_retry_on_disconnect(self):
        """Disconnecting while previously charging → resets retry."""
        hass_mock = MagicMock()
        hass_mock.states.get = MagicMock(return_value=MagicMock(state="off"))
        controller = VehicleController(hass_mock, "test_vehicle")
        controller._charging_sensor = "binary_sensor.plugged"
        controller._last_charging_state = True
        controller._retry_state.add_attempt()
        assert controller._retry_state.get_attempt_count() == 1

        await controller._check_and_reset_retry_on_disconnect()
        assert controller._retry_state.get_attempt_count() == 0
        assert controller._last_charging_state is False

    @pytest.mark.asyncio
    async def test_check_and_reset_retry_still_charging(self):
        """Still charging → does NOT reset retry."""
        hass_mock = MagicMock()
        hass_mock.states.get = MagicMock(return_value=MagicMock(state="on"))
        controller = VehicleController(hass_mock, "test_vehicle")
        controller._charging_sensor = "binary_sensor.plugged"
        controller._last_charging_state = True

        await controller._check_and_reset_retry_on_disconnect()
        assert controller._last_charging_state is True
