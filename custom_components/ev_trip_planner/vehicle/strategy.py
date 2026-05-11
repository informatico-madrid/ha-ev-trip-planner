"""Vehicle control strategies — imported from vehicle_controller.py during migration.

These classes are defined in vehicle_controller.py and will be moved here
in a later task as part of the SOLID decomposition.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

MAX_RETRY_ATTEMPTS = 3
RETRY_TIME_WINDOW_SECONDS = 300


@dataclass
class RetryState:
    """Tracks retry attempts for charging activation."""

    attempts: List[float] = field(default_factory=list)

    def add_attempt(self) -> None:
        """Record a retry attempt at the current time, pruning stale entries."""
        current_time = time.time()
        self.attempts.append(current_time)
        self.attempts = [
            t for t in self.attempts if current_time - t <= RETRY_TIME_WINDOW_SECONDS
        ]

    def should_retry(self) -> bool:
        """Return True if retry attempts are within the allowed limit."""
        current_time = time.time()
        self.attempts = [
            t for t in self.attempts if current_time - t <= RETRY_TIME_WINDOW_SECONDS
        ]
        return len(self.attempts) < MAX_RETRY_ATTEMPTS

    def get_attempt_count(self) -> int:
        """Return the number of recent retry attempts within the time window."""
        current_time = time.time()
        self.attempts = [
            t for t in self.attempts if current_time - t <= RETRY_TIME_WINDOW_SECONDS
        ]
        return len(self.attempts)

    def reset(self) -> None:
        """Clear all retry attempt records."""
        self.attempts = []


class HomeAssistantWrapper:
    """Wrapper for Home Assistant service and state calls."""

    def __init__(self, hass: HomeAssistant):
        self._hass = hass

    async def async_call_service(
        self, domain: str, service: str, data: Dict[str, Any]
    ) -> None:
        """Call a Home Assistant service asynchronously."""
        await self._hass.services.async_call(domain, service, data)

    def get_state(self, entity_id: str):
        """Get the current state of a Home Assistant entity."""
        return self._hass.states.get(entity_id)


class VehicleControlStrategy(ABC):
    """Abstract base class for vehicle control strategies."""

    def __init__(self, hass_wrapper: HomeAssistantWrapper, config: Dict[str, Any]):
        self.hass_wrapper = hass_wrapper
        self.config = config

    @abstractmethod
    async def async_activate(self) -> bool:
        """Activate vehicle charging. Returns True on success."""

    @abstractmethod
    async def async_deactivate(self) -> bool:
        """Deactivate vehicle charging. Returns True on success."""

    @abstractmethod
    async def async_get_status(self) -> bool:
        """Return the current charging status."""


class SwitchStrategy(VehicleControlStrategy):
    """Control via switch entity."""

    def __init__(self, hass_wrapper: HomeAssistantWrapper, config: Dict[str, Any]):
        super().__init__(hass_wrapper, config)
        self.switch_entity_id = config["entity_id"]

    async def async_activate(self) -> bool:
        try:
            await self.hass_wrapper.async_call_service(
                "switch", "turn_on", {"entity_id": self.switch_entity_id}
            )
            _LOGGER.info("Activated charging via switch: %s", self.switch_entity_id)
            return True
        except Exception as err:
            _LOGGER.error("Error activating switch: %s", err, exc_info=True)
            return False

    async def async_deactivate(self) -> bool:
        try:
            await self.hass_wrapper.async_call_service(
                "switch", "turn_off", {"entity_id": self.switch_entity_id}
            )
            _LOGGER.info("Deactivated charging via switch: %s", self.switch_entity_id)
            return True
        except Exception as err:
            _LOGGER.error("Error deactivating switch: %s", err, exc_info=True)
            return False

    async def async_get_status(self) -> bool:
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
        try:
            domain, service = self.service_on.split(".", 1)
            await self.hass_wrapper.async_call_service(domain, service, self.data_on)
            _LOGGER.info("Activated charging via service: %s", self.service_on)
            return True
        except Exception as err:
            _LOGGER.error(
                "Error calling service %s: %s", self.service_on, err, exc_info=True
            )
            return False

    async def async_deactivate(self) -> bool:
        try:
            domain, service = self.service_off.split(".", 1)
            await self.hass_wrapper.async_call_service(domain, service, self.data_off)
            _LOGGER.info("Deactivated charging via service: %s", self.service_off)
            return True
        except Exception as err:
            _LOGGER.error(
                "Error calling service %s: %s", self.service_off, err, exc_info=True
            )
            return False

    async def async_get_status(self) -> bool:
        return False
