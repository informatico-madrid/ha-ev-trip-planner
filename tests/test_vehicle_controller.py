"""Tests for Vehicle Control Strategies."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner.vehicle_controller import (
    VehicleControlStrategy,
    VehicleController,
    SwitchStrategy,
    ServiceStrategy,
    ScriptStrategy,
    ExternalStrategy,
    create_control_strategy,
    HomeAssistantWrapper,
)


@pytest.mark.asyncio
async def test_switch_strategy_instantiation(hass: HomeAssistant):
    """Test SwitchStrategy can be created."""
    wrapper = HomeAssistantWrapper(hass)
    config = {"entity_id": "switch.test_charger"}
    strategy = SwitchStrategy(wrapper, config)
    
    assert strategy.hass_wrapper == wrapper
    assert strategy.switch_entity_id == "switch.test_charger"


@pytest.mark.asyncio
async def test_switch_strategy_activate(hass: HomeAssistant):
    """Test SwitchStrategy activates charging."""
    wrapper = HomeAssistantWrapper(hass)
    config = {"entity_id": "switch.test_charger"}
    strategy = SwitchStrategy(wrapper, config)
    
    # Mock the wrapper's service call
    calls = []
    async def mock_service_call(domain, service, data):
        calls.append((domain, service, data))
    
    wrapper.async_call_service = mock_service_call
    
    # Activate
    result = await strategy.async_activate()
    
    assert result is True
    assert len(calls) == 1
    assert calls[0] == ("switch", "turn_on", {"entity_id": "switch.test_charger"})


@pytest.mark.asyncio
async def test_switch_strategy_deactivate(hass: HomeAssistant):
    """Test SwitchStrategy deactivates charging."""
    wrapper = HomeAssistantWrapper(hass)
    config = {"entity_id": "switch.test_charger"}
    strategy = SwitchStrategy(wrapper, config)
    
    calls = []
    async def mock_service_call(domain, service, data):
        calls.append((domain, service, data))
    
    wrapper.async_call_service = mock_service_call
    
    # Deactivate
    result = await strategy.async_deactivate()
    
    assert result is True
    assert len(calls) == 1
    assert calls[0] == ("switch", "turn_off", {"entity_id": "switch.test_charger"})


@pytest.mark.asyncio
async def test_switch_strategy_get_status_on(hass: HomeAssistant):
    """Test SwitchStrategy gets status when switch is on."""
    wrapper = HomeAssistantWrapper(hass)
    config = {"entity_id": "switch.test_charger"}
    strategy = SwitchStrategy(wrapper, config)
    
    # Mock state
    mock_state = Mock()
    mock_state.state = "on"
    wrapper.get_state = lambda entity_id: mock_state if entity_id == "switch.test_charger" else None
    
    status = await strategy.async_get_status()
    assert status is True


@pytest.mark.asyncio
async def test_switch_strategy_get_status_off(hass: HomeAssistant):
    """Test SwitchStrategy gets status when switch is off."""
    wrapper = HomeAssistantWrapper(hass)
    config = {"entity_id": "switch.test_charger"}
    strategy = SwitchStrategy(wrapper, config)
    
    # Mock state
    mock_state = Mock()
    mock_state.state = "off"
    wrapper.get_state = lambda entity_id: mock_state if entity_id == "switch.test_charger" else None
    
    status = await strategy.async_get_status()
    assert status is False


@pytest.mark.asyncio
async def test_switch_strategy_get_status_unknown(hass: HomeAssistant):
    """Test SwitchStrategy gets status when switch is unavailable."""
    wrapper = HomeAssistantWrapper(hass)
    config = {"entity_id": "switch.test_charger"}
    strategy = SwitchStrategy(wrapper, config)
    
    wrapper.get_state = lambda entity_id: None
    
    status = await strategy.async_get_status()
    assert status is False


@pytest.mark.asyncio
async def test_service_strategy_instantiation(hass: HomeAssistant):
    """Test ServiceStrategy can be created."""
    wrapper = HomeAssistantWrapper(hass)
    config = {
        "service_on": "ovms.start_charge",
        "service_off": "ovms.stop_charge",
        "data_on": {"vehicle_id": "chispitas"},
        "data_off": {"vehicle_id": "chispitas"},
    }
    strategy = ServiceStrategy(wrapper, config)
    
    assert strategy.hass_wrapper == wrapper
    assert strategy.service_on == "ovms.start_charge"
    assert strategy.service_off == "ovms.stop_charge"
    assert strategy.data_on == {"vehicle_id": "chispitas"}
    assert strategy.data_off == {"vehicle_id": "chispitas"}


@pytest.mark.asyncio
async def test_service_strategy_activate(hass: HomeAssistant):
    """Test ServiceStrategy activates charging."""
    wrapper = HomeAssistantWrapper(hass)
    config = {
        "service_on": "ovms.start_charge",
        "service_off": "ovms.stop_charge",
        "data_on": {"vehicle_id": "chispitas"},
        "data_off": {"vehicle_id": "chispitas"},
    }
    strategy = ServiceStrategy(wrapper, config)
    
    calls = []
    async def mock_service_call(domain, service, data):
        calls.append((domain, service, data))
    
    wrapper.async_call_service = mock_service_call
    
    # Activate
    result = await strategy.async_activate()
    
    assert result is True
    assert len(calls) == 1
    assert calls[0] == ("ovms", "start_charge", {"vehicle_id": "chispitas"})


@pytest.mark.asyncio
async def test_service_strategy_deactivate(hass: HomeAssistant):
    """Test ServiceStrategy deactivates charging."""
    wrapper = HomeAssistantWrapper(hass)
    config = {
        "service_on": "ovms.start_charge",
        "service_off": "ovms.stop_charge",
        "data_on": {"vehicle_id": "chispitas"},
        "data_off": {"vehicle_id": "chispitas"},
    }
    strategy = ServiceStrategy(wrapper, config)
    
    calls = []
    async def mock_service_call(domain, service, data):
        calls.append((domain, service, data))
    
    wrapper.async_call_service = mock_service_call
    
    # Deactivate
    result = await strategy.async_deactivate()
    
    assert result is True
    assert len(calls) == 1
    assert calls[0] == ("ovms", "stop_charge", {"vehicle_id": "chispitas"})


@pytest.mark.asyncio
async def test_service_strategy_get_status(hass: HomeAssistant):
    """Test ServiceStrategy get status returns False (no status tracking)."""
    wrapper = HomeAssistantWrapper(hass)
    config = {
        "service_on": "ovms.start_charge",
        "service_off": "ovms.stop_charge",
    }
    strategy = ServiceStrategy(wrapper, config)
    
    status = await strategy.async_get_status()
    assert status is False  # No status tracking by default


@pytest.mark.asyncio
async def test_script_strategy_instantiation(hass: HomeAssistant):
    """Test ScriptStrategy can be created."""
    wrapper = HomeAssistantWrapper(hass)
    config = {
        "script_on": "script.start_ev_charging",
        "script_off": "script.stop_ev_charging",
    }
    strategy = ScriptStrategy(wrapper, config)
    
    assert strategy.hass_wrapper == wrapper
    assert strategy.script_on == "script.start_ev_charging"
    assert strategy.script_off == "script.stop_ev_charging"


@pytest.mark.asyncio
async def test_script_strategy_activate(hass: HomeAssistant):
    """Test ScriptStrategy activates charging."""
    wrapper = HomeAssistantWrapper(hass)
    config = {
        "script_on": "script.start_ev_charging",
        "script_off": "script.stop_ev_charging",
    }
    strategy = ScriptStrategy(wrapper, config)
    
    calls = []
    async def mock_service_call(domain, service, data):
        calls.append((domain, service, data))
    
    wrapper.async_call_service = mock_service_call
    
    # Activate
    result = await strategy.async_activate()
    
    assert result is True
    assert len(calls) == 1
    assert calls[0] == ("script", "start_ev_charging", {})


@pytest.mark.asyncio
async def test_script_strategy_deactivate(hass: HomeAssistant):
    """Test ScriptStrategy deactivates charging."""
    wrapper = HomeAssistantWrapper(hass)
    config = {
        "script_on": "script.start_ev_charging",
        "script_off": "script.stop_ev_charging",
    }
    strategy = ScriptStrategy(wrapper, config)
    
    calls = []
    async def mock_service_call(domain, service, data):
        calls.append((domain, service, data))
    
    wrapper.async_call_service = mock_service_call
    
    # Deactivate
    result = await strategy.async_deactivate()
    
    assert result is True
    assert len(calls) == 1
    assert calls[0] == ("script", "stop_ev_charging", {})


@pytest.mark.asyncio
async def test_script_strategy_get_status(hass: HomeAssistant):
    """Test ScriptStrategy get status returns False."""
    wrapper = HomeAssistantWrapper(hass)
    config = {
        "script_on": "script.start_ev_charging",
        "script_off": "script.stop_ev_charging",
    }
    strategy = ScriptStrategy(wrapper, config)
    
    status = await strategy.async_get_status()
    assert status is False


@pytest.mark.asyncio
async def test_external_strategy(hass: HomeAssistant):
    """Test ExternalStrategy always returns success."""
    wrapper = HomeAssistantWrapper(hass)
    config = {}
    strategy = ExternalStrategy(wrapper, config)
    
    # Activate
    result = await strategy.async_activate()
    assert result is True
    
    # Deactivate
    result = await strategy.async_deactivate()
    assert result is True
    
    # Get status
    status = await strategy.async_get_status()
    assert status is False


@pytest.mark.asyncio
async def test_create_control_strategy_switch(hass: HomeAssistant):
    """Test factory creates SwitchStrategy."""
    config = {
        "control_type": "switch",
        "charge_control_entity": "switch.test_charger",
    }
    strategy = create_control_strategy(hass, config)
    
    assert isinstance(strategy, SwitchStrategy)
    assert strategy.switch_entity_id == "switch.test_charger"


@pytest.mark.asyncio
async def test_create_control_strategy_service(hass: HomeAssistant):
    """Test factory creates ServiceStrategy."""
    config = {
        "control_type": "service",
        "charge_service_on": "ovms.start_charge",
        "charge_service_off": "ovms.stop_charge",
    }
    strategy = create_control_strategy(hass, config)
    
    assert isinstance(strategy, ServiceStrategy)
    assert strategy.service_on == "ovms.start_charge"


@pytest.mark.asyncio
async def test_create_control_strategy_script(hass: HomeAssistant):
    """Test factory creates ScriptStrategy."""
    config = {
        "control_type": "script",
        "charge_script_on": "script.start_charging",
        "charge_script_off": "script.stop_charging",
    }
    strategy = create_control_strategy(hass, config)
    
    assert isinstance(strategy, ScriptStrategy)
    assert strategy.script_on == "script.start_charging"


@pytest.mark.asyncio
async def test_create_control_strategy_external(hass: HomeAssistant):
    """Test factory creates ExternalStrategy for unknown type."""
    config = {
        "control_type": "unknown",
    }
    strategy = create_control_strategy(hass, config)
    
    assert isinstance(strategy, ExternalStrategy)


@pytest.mark.asyncio
async def test_create_control_strategy_default(hass: HomeAssistant):
    """Test factory creates ExternalStrategy by default."""
    config = {}
    strategy = create_control_strategy(hass, config)
    
    assert isinstance(strategy, ExternalStrategy)


@pytest.mark.asyncio
async def test_switch_strategy_error_handling(hass: HomeAssistant):
    """Test SwitchStrategy handles service call errors."""
    wrapper = HomeAssistantWrapper(hass)
    config = {"entity_id": "switch.test_charger"}
    strategy = SwitchStrategy(wrapper, config)
    
    async def mock_service_call_error(domain, service, data):
        raise Exception("Service call failed")
    
    wrapper.async_call_service = mock_service_call_error
    
    # Activate should return False on error
    result = await strategy.async_activate()
    assert result is False


@pytest.mark.asyncio
async def test_service_strategy_error_handling(hass: HomeAssistant):
    """Test ServiceStrategy handles service call errors."""
    wrapper = HomeAssistantWrapper(hass)
    config = {
        "service_on": "ovms.start_charge",
        "service_off": "ovms.stop_charge",
    }
    strategy = ServiceStrategy(wrapper, config)
    
    async def mock_service_call_error(domain, service, data):
        raise Exception("Service call failed")
    
    wrapper.async_call_service = mock_service_call_error
    
    # Activate should return False on error
    result = await strategy.async_activate()
    assert result is False


@pytest.mark.asyncio
async def test_script_strategy_error_handling(hass: HomeAssistant):
    """Test ScriptStrategy handles service call errors."""
    wrapper = HomeAssistantWrapper(hass)
    config = {
        "script_on": "script.start_charging",
        "script_off": "script.stop_charging",
    }
    strategy = ScriptStrategy(wrapper, config)
    
    async def mock_service_call_error(domain, service, data):
        raise Exception("Service call failed")
    
    wrapper.async_call_service = mock_service_call_error
    
    # Activate should return False on error
    result = await strategy.async_activate()
    assert result is False

class TestVehicleController:
    """Tests for VehicleController class."""

    @pytest.mark.asyncio
    async def test_vehicle_controller_init(self, hass: HomeAssistant):
        """Test VehicleController can be instantiated."""
        controller = VehicleController(hass, "test_vehicle")
        assert controller.vehicle_id == "test_vehicle"
        assert controller.hass == hass

    @pytest.mark.asyncio
    async def test_vehicle_controller_with_presence_config(self, hass: HomeAssistant):
        """Test VehicleController with presence config."""
        presence_config = {
            "home_sensor": "binary_sensor.home",
            "plugged_sensor": "binary_sensor.plugged",
            "charging_sensor": "binary_sensor.charging",
        }
        controller = VehicleController(hass, "test_vehicle", presence_config)
        assert controller._presence_monitor is not None

    @pytest.mark.asyncio
    async def test_vehicle_controller_set_strategy(self, hass: HomeAssistant):
        """Test setting control strategy."""
        controller = VehicleController(hass, "test_vehicle")
        wrapper = HomeAssistantWrapper(hass)
        strategy = SwitchStrategy(wrapper, {"entity_id": "switch.test"})
        controller.set_strategy(strategy)
        assert controller._strategy is strategy

    @pytest.mark.asyncio
    async def test_vehicle_controller_update_config(self, hass: HomeAssistant):
        """Test updating config stores the config."""
        controller = VehicleController(hass, "test_vehicle")

        # Set initial config
        config1 = {
            "control_type": "switch",
            "charge_control_entity": "switch.test1",
        }
        controller.update_config(config1)
        # Config is stored, strategy is only recreated if one exists
        assert controller._config == config1

        # Set a strategy first
        wrapper = HomeAssistantWrapper(hass)
        strategy = SwitchStrategy(wrapper, {"entity_id": "switch.test1"})
        controller.set_strategy(strategy)

        # Update config - strategy should be recreated
        config2 = {
            "control_type": "switch",
            "charge_control_entity": "switch.test2",
        }
        controller.update_config(config2)
        assert isinstance(controller._strategy, SwitchStrategy)

    @pytest.mark.asyncio
    async def test_vehicle_controller_activate_charging_no_strategy(self, hass: HomeAssistant):
        """Test activating charging with no strategy returns False."""
        controller = VehicleController(hass, "test_vehicle")
        result = await controller.async_activate_charging()
        assert result is False

    @pytest.mark.asyncio
    async def test_vehicle_controller_deactivate_charging_no_strategy(self, hass: HomeAssistant):
        """Test deactivating charging with no strategy returns False."""
        controller = VehicleController(hass, "test_vehicle")
        result = await controller.async_deactivate_charging()
        assert result is False

    @pytest.mark.asyncio
    async def test_vehicle_controller_get_charging_status_no_strategy(self, hass: HomeAssistant):
        """Test getting charging status with no strategy returns False."""
        controller = VehicleController(hass, "test_vehicle")
        status = await controller.async_get_charging_status()
        assert status is False

    @pytest.mark.asyncio
    async def test_vehicle_controller_activate_charging_success(self, hass: HomeAssistant):
        """Test successful charging activation."""
        controller = VehicleController(hass, "test_vehicle")

        # Create and set strategy
        wrapper = HomeAssistantWrapper(hass)
        strategy = SwitchStrategy(wrapper, {"entity_id": "switch.test"})
        controller.set_strategy(strategy)

        # Mock the service call
        calls = []
        async def mock_service_call(domain, service, data):
            calls.append((domain, service, data))
        wrapper.async_call_service = mock_service_call

        # Activate should succeed
        result = await controller.async_activate_charging()
        assert result is True

    @pytest.mark.asyncio
    async def test_vehicle_controller_check_presence_status_ready(self, hass: HomeAssistant):
        """Test presence check returns ready when no presence config."""
        controller = VehicleController(hass, "test_vehicle")
        is_ready, reason = await controller.async_check_presence_status()
        assert is_ready is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_vehicle_controller_check_presence_status_already_charging(self, hass: HomeAssistant):
        """Test presence check returns ready when already charging."""
        # Use only charging_sensor (not full presence config) to skip presence monitor
        controller = VehicleController(hass, "test_vehicle")
        controller._charging_sensor = "binary_sensor.charging"

        # Mock the charging sensor to return "charging"
        mock_state = Mock()
        mock_state.state = "charging"
        hass.states.get = lambda entity_id: mock_state if entity_id == "binary_sensor.charging" else None

        is_ready, reason = await controller.async_check_presence_status()
        assert is_ready is True

    @pytest.mark.asyncio
    async def test_vehicle_controller_check_presence_status_charging_on(self, hass: HomeAssistant):
        """Test presence check returns ready when charging sensor is 'on'."""
        # Use only charging_sensor (not full presence config) to skip presence monitor
        controller = VehicleController(hass, "test_vehicle")
        controller._charging_sensor = "binary_sensor.charging"

        # Mock the charging sensor to return "on"
        mock_state = Mock()
        mock_state.state = "on"
        hass.states.get = lambda entity_id: mock_state if entity_id == "binary_sensor.charging" else None

        is_ready, reason = await controller.async_check_presence_status()
        assert is_ready is True

    @pytest.mark.asyncio
    async def test_vehicle_controller_check_presence_status_charging_true(self, hass: HomeAssistant):
        """Test presence check returns ready when charging sensor is 'true'."""
        # Use only charging_sensor (not full presence config) to skip presence monitor
        controller = VehicleController(hass, "test_vehicle")
        controller._charging_sensor = "binary_sensor.charging"

        # Mock the charging sensor to return "true"
        mock_state = Mock()
        mock_state.state = "true"
        hass.states.get = lambda entity_id: mock_state if entity_id == "binary_sensor.charging" else None

        is_ready, reason = await controller.async_check_presence_status()
        assert is_ready is True

    @pytest.mark.asyncio
    async def test_vehicle_controller_check_presence_status_charging_yes(self, hass: HomeAssistant):
        """Test presence check returns ready when charging sensor is 'yes'."""
        # Use only charging_sensor (not full presence config) to skip presence monitor
        controller = VehicleController(hass, "test_vehicle")
        controller._charging_sensor = "binary_sensor.charging"

        # Mock the charging sensor to return "yes"
        mock_state = Mock()
        mock_state.state = "yes"
        hass.states.get = lambda entity_id: mock_state if entity_id == "binary_sensor.charging" else None

        is_ready, reason = await controller.async_check_presence_status()
        assert is_ready is True

    @pytest.mark.asyncio
    async def test_vehicle_controller_check_presence_status_sensor_not_found(self, hass: HomeAssistant):
        """Test presence check returns ready when charging sensor not found."""
        # Use only charging_sensor (not full presence config) to skip presence monitor
        controller = VehicleController(hass, "test_vehicle")
        controller._charging_sensor = "binary_sensor.charging"

        # Mock sensor not found
        hass.states.get = lambda entity_id: None

        is_ready, reason = await controller.async_check_presence_status()
        # Sensor not found should return False for charging, but ready overall
        assert is_ready is True

    @pytest.mark.asyncio
    async def test_vehicle_controller_check_presence_status_sensor_off(self, hass: HomeAssistant):
        """Test presence check returns ready when charging sensor is 'off'."""
        # Use only charging_sensor (not full presence config) to skip presence monitor
        controller = VehicleController(hass, "test_vehicle")
        controller._charging_sensor = "binary_sensor.charging"

        # Mock the charging sensor to return "off"
        mock_state = Mock()
        mock_state.state = "off"
        hass.states.get = lambda entity_id: mock_state if entity_id == "binary_sensor.charging" else None

        is_ready, reason = await controller.async_check_presence_status()
        # Should still be ready (not currently charging)
        assert is_ready is True


class TestHomeAssistantWrapper:
    """Tests for HomeAssistantWrapper class."""

    @pytest.mark.asyncio
    async def test_wrapper_get_state(self, hass: HomeAssistant):
        """Test wrapper can get entity state."""
        wrapper = HomeAssistantWrapper(hass)
        # hass.states.get should return None for unknown entity
        state = wrapper.get_state("sensor.unknown")
        assert state is None
