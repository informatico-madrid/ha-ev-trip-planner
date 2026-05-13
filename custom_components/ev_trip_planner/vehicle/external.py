"""External strategies — ScriptStrategy and ExternalStrategy.

These strategies control charging via script execution or by delegating
to an external system that manages charging independently.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .strategy import HomeAssistantWrapper, VehicleControlStrategy

_LOGGER = logging.getLogger(__name__)


class ScriptStrategy(VehicleControlStrategy):
    """Control via script execution."""

    def __init__(self, hass_wrapper: HomeAssistantWrapper, config: Dict[str, Any]):
        super().__init__(hass_wrapper, config)
        self.script_on: str = config["script_on"]
        self.script_off: str = config["script_off"]

    async def async_activate(self) -> bool:
        """Execute start charging script."""
        try:
            await self.hass_wrapper.async_call_service(
                "script", self.script_on.replace("script.", ""), {}
            )
            _LOGGER.info("Activated charging via script: %s", self.script_on)
            return True
        except Exception as err:
            _LOGGER.error(
                "Error executing script %s: %s", self.script_on, err, exc_info=True
            )
            return False

    async def async_deactivate(self) -> bool:
        """Execute stop charging script."""
        try:
            await self.hass_wrapper.async_call_service(
                "script", self.script_off.replace("script.", ""), {}
            )
            _LOGGER.info("Deactivated charging via script: %s", self.script_off)
            return True
        except Exception as err:  # pragma: no cover reason=script execution failure requires HA runtime
            _LOGGER.error(
                "Error executing script %s: %s", self.script_off, err, exc_info=True
            )
            return False  # pragma: no cover reason=paired with above exception handler

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
