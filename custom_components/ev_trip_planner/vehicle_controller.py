"""Vehicle Control Strategies for EV Trip Planner."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class HomeAssistantWrapper:
    """Wrapper for Home Assistant service and state calls to enable testing."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize wrapper."""
        self._hass = hass
    
    async def async_call_service(self, domain: str, service: str, data: Dict[str, Any]) -> None:
        """Call a service."""
        await self._hass.services.async_call(domain, service, data)
    
    def get_state(self, entity_id: str):
        """Get state of an entity."""
        return self._hass.states.get(entity_id)


class VehicleControlStrategy(ABC):
    """Abstract base class for vehicle control strategies."""
    
    def __init__(self, hass_wrapper: HomeAssistantWrapper, config: Dict[str, Any]):
        """Initialize strategy."""
        self.hass_wrapper = hass_wrapper
        self.config = config
    
    @abstractmethod
    async def async_activate(self) -> bool:
        """Activate vehicle charging."""
        pass
    
    @abstractmethod
    async def async_deactivate(self) -> bool:
        """Deactivate vehicle charging."""
        pass
    
    @abstractmethod
    async def async_get_status(self) -> bool:
        """Get current charging status."""
        pass


class SwitchStrategy(VehicleControlStrategy):
    """Control via switch entity."""
    
    def __init__(self, hass_wrapper: HomeAssistantWrapper, config: Dict[str, Any]):
        super().__init__(hass_wrapper, config)
        self.switch_entity_id = config["entity_id"]
    
    async def async_activate(self) -> bool:
        """Turn on switch."""
        try:
            await self.hass_wrapper.async_call_service(
                "switch", "turn_on", {"entity_id": self.switch_entity_id}
            )
            _LOGGER.info("Activated charging via switch: %s", self.switch_entity_id)
            return True
        except Exception as err:
            _LOGGER.error("Error activating switch: %s", err)
            return False
    
    async def async_deactivate(self) -> bool:
        """Turn off switch."""
        try:
            await self.hass_wrapper.async_call_service(
                "switch", "turn_off", {"entity_id": self.switch_entity_id}
            )
            _LOGGER.info("Deactivated charging via switch: %s", self.switch_entity_id)
            return True
        except Exception as err:
            _LOGGER.error("Error deactivating switch: %s", err)
            return False
    
    async def async_get_status(self) -> bool:
        """Get switch state."""
        state = self.hass_wrapper.get_state(self.switch_entity_id)
        if state is None:
            return False
        return state.state == "on"


class ServiceStrategy(VehicleControlStrategy):
    """Control via custom service call."""
    
    def __init__(self, hass_wrapper: HomeAssistantWrapper, config: Dict[str, Any]):
        super().__init__(hass_wrapper, config)
        self.service_on = config["service_on"]
        self.service_off = config["service_off"]
        self.data_on = config.get("data_on", {})
        self.data_off = config.get("data_off", {})
    
    async def async_activate(self) -> bool:
        """Call service to start charging."""
        try:
            domain, service = self.service_on.split(".", 1)
            await self.hass_wrapper.async_call_service(
                domain, service, self.data_on
            )
            _LOGGER.info("Activated charging via service: %s", self.service_on)
            return True
        except Exception as err:
            _LOGGER.error("Error calling service %s: %s", self.service_on, err)
            return False
    
    async def async_deactivate(self) -> bool:
        """Call service to stop charging."""
        try:
            domain, service = self.service_off.split(".", 1)
            await self.hass_wrapper.async_call_service(
                domain, service, self.data_off
            )
            _LOGGER.info("Deactivated charging via service: %s", self.service_off)
            return True
        except Exception as err:
            _LOGGER.error("Error calling service %s: %s", self.service_off, err)
            return False
    
    async def async_get_status(self) -> bool:
        """Get status via service or sensor."""
        # This would need a sensor or additional config
        # For now, return unknown
        return False


class ScriptStrategy(VehicleControlStrategy):
    """Control via script execution."""
    
    def __init__(self, hass_wrapper: HomeAssistantWrapper, config: Dict[str, Any]):
        super().__init__(hass_wrapper, config)
        self.script_on = config["script_on"]
        self.script_off = config["script_off"]
    
    async def async_activate(self) -> bool:
        """Execute start charging script."""
        try:
            await self.hass_wrapper.async_call_service(
                "script", self.script_on.replace("script.", ""), {}
            )
            _LOGGER.info("Activated charging via script: %s", self.script_on)
            return True
        except Exception as err:
            _LOGGER.error("Error executing script %s: %s", self.script_on, err)
            return False
    
    async def async_deactivate(self) -> bool:
        """Execute stop charging script."""
        try:
            await self.hass_wrapper.async_call_service(
                "script", self.script_off.replace("script.", ""), {}
            )
            _LOGGER.info("Deactivated charging via script: %s", self.script_off)
            return True
        except Exception as err:
            _LOGGER.error("Error executing script %s: %s", self.script_off, err)
            return False
    
    async def async_get_status(self) -> bool:
        """Get status - scripts typically don't return status."""
        return False


class ExternalStrategy(VehicleControlStrategy):
    """No direct control - external system manages charging."""
    
    async def async_activate(self) -> bool:
        """No-op."""
        _LOGGER.info("External strategy: no action taken")
        return True
    
    async def async_deactivate(self) -> bool:
        """No-op."""
        _LOGGER.info("External strategy: no action taken")
        return True
    
    async def async_get_status(self) -> bool:
        """Unknown status."""
        return False


def create_control_strategy(hass: HomeAssistant, config: Dict[str, Any]) -> VehicleControlStrategy:
    """Factory function to create appropriate control strategy."""
    control_type = config.get("control_type", "none")
    hass_wrapper = HomeAssistantWrapper(hass)
    
    if control_type == "switch":
        return SwitchStrategy(hass_wrapper, {"entity_id": config["charge_control_entity"]})
    elif control_type == "service":
        return ServiceStrategy(hass_wrapper, {
            "service_on": config["charge_service_on"],
            "service_off": config["charge_service_off"],
            "data_on": config.get("charge_service_data_on", {}),
            "data_off": config.get("charge_service_data_off", {}),
        })
    elif control_type == "script":
        return ScriptStrategy(hass_wrapper, {
            "script_on": config["charge_script_on"],
            "script_off": config["charge_script_off"],
        })
    else:
        return ExternalStrategy(hass_wrapper, {})