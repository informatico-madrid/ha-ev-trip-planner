"""VehicleController and create_control_strategy factory.

VehicleController manages charging control strategies with presence
monitoring and retry logic.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from homeassistant.core import HomeAssistant

from ..const import CONF_CHARGING_SENSOR
from ..presence_monitor import PresenceMonitor
from .external import ExternalStrategy, ScriptStrategy
from .strategy import (
    HomeAssistantWrapper,
    RetryState,
    ServiceStrategy,
    SwitchStrategy,
    VehicleControlStrategy,
)

if TYPE_CHECKING:
    from ..trip import TripManager

_LOGGER = logging.getLogger(__name__)

# US-5: Extracted log format strings to constants for mutation-killing tests.
_LOG_SETUP = "Setting up vehicle controller for: %s"
_LOG_PRESENCE_FAILED = "Presence check failed: %s - %s"
_LOG_ALREADY_CHARGING = "Vehicle %s is already charging"
_LOG_SENSOR_NOT_FOUND = "Charging sensor %s not found for %s"
_LOG_CHARGING_STATUS = "Charging status for %s: %s = %s"
_LOG_CANNOT_ACTIVATE = "Cannot activate charging for %s: %s"
_LOG_NO_STRATEGY = "No strategy set for vehicle: %s"
_LOG_RETRY_EXCEEDED = "Max retry attempts (%d) exceeded for %s in %d seconds"
_LOG_ACTIVATED = "Successfully activated charging for %s"
_LOG_ACTIVATION_FAILED = "Failed to activate charging for %s (attempt %d/%d)"
_LOG_DISCONNECT_RESET = "Vehicle %s disconnected - resetting retry counter"
_LOG_RETRY_RESET = "Retry counter manually reset for %s"

# Retry configuration constants
MAX_RETRY_ATTEMPTS = 3
RETRY_TIME_WINDOW_SECONDS = 300  # 5 minutes


def create_control_strategy(  # pragma: no mutate  # EQ-001
    hass: HomeAssistant, config: Dict[str, Any]
) -> VehicleControlStrategy:
    """Factory function to create appropriate control strategy."""
    control_type = config.get("control_type", "none")
    hass_wrapper = HomeAssistantWrapper(hass)

    if control_type == "switch":
        entity_id = config["charge_control_entity"]
        return SwitchStrategy(hass_wrapper, {"entity_id": entity_id})
    elif control_type == "service":
        return ServiceStrategy(
            hass_wrapper,
            {
                "service_on": config["charge_service_on"],
                "service_off": config["charge_service_off"],
                "data_on": config.get("charge_service_data_on", {}),
                "data_off": config.get("charge_service_data_off", {}),
            },
        )
    elif control_type == "script":
        return ScriptStrategy(
            hass_wrapper,
            {
                "script_on": config["charge_script_on"],
                "script_off": config["charge_script_off"],
            },
        )
    else:
        return ExternalStrategy(hass_wrapper, {})


# qg-accepted: BMAD consensus 2026-05-12 — FALSE POSITIVE: facade pattern (9 public methods,
#   high delegation ratio are inherent to the facade+strategy architecture. Tier A counts
#   facade methods as violations, Tier B confirms this is legitimate SOLID-compliant design.
class VehicleController:
    """Vehicle controller for managing charging control strategies.

    This class provides an interface for controlling vehicle charging using
    different strategies (switch, service, script, or external).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        vehicle_id: str,
        presence_config: Optional[Dict[str, Any]] = None,
        trip_manager: Optional["TripManager"] = None,
    ) -> None:  # pragma: no mutate  # EQ-003
        """Initialize the vehicle controller."""
        self.hass = hass
        self.vehicle_id = vehicle_id
        self._strategy: Optional[VehicleControlStrategy] = None
        self._config: Dict[str, Any] = {}
        self._presence_monitor: Optional[PresenceMonitor] = None
        if presence_config:
            self._charging_sensor = presence_config.get(CONF_CHARGING_SENSOR)
        else:
            self._charging_sensor = None
        self._retry_state = RetryState()
        self._last_charging_state: Optional[bool] = None

        # Initialize presence monitor if config provided
        if presence_config:
            self._presence_monitor = PresenceMonitor(
                hass, vehicle_id, presence_config, trip_manager
            )

    async def async_setup(self) -> None:
        """Set up the vehicle controller."""
        _LOGGER.info(_LOG_SETUP, self.vehicle_id)

    def set_strategy(self, strategy: VehicleControlStrategy) -> None:
        """Set the control strategy."""
        self._strategy = strategy

    def update_config(self, config: Dict[str, Any]) -> None:
        """Update the configuration and recreate strategy if needed."""
        self._config = config
        if self._strategy is not None:
            self._strategy = create_control_strategy(self.hass, config)

    async def async_check_presence_status(self) -> Tuple[bool, Optional[str]]:
        """Check presence status: home, plugged, and charging sensor.

        Returns:
            Tuple of (is_ready, reason_if_not_ready)
        """
        # Check home status
        if self._presence_monitor:
            monitor = self._presence_monitor
            is_ready, reason = await monitor.async_check_charging_readiness()
            if not is_ready:
                _LOGGER.info(_LOG_PRESENCE_FAILED, self.vehicle_id, reason)
                return False, reason

        # Check charging sensor status (if configured)
        if self._charging_sensor:
            is_charging = await self._async_check_charging_sensor()
            if is_charging:
                _LOGGER.info(_LOG_ALREADY_CHARGING, self.vehicle_id)
                return True, None  # Already charging is fine

        return True, None

    async def _async_check_charging_sensor(self) -> bool:
        """Check if vehicle is currently charging via sensor.

        Returns:
            True if charging, False otherwise
        """
        if not self._charging_sensor:
            return False

        state = self.hass.states.get(self._charging_sensor)
        if not state:
            _LOGGER.warning(_LOG_SENSOR_NOT_FOUND, self._charging_sensor, self.vehicle_id)
            return False

        is_charging = state.state.lower() in ["on", "true", "yes", "charging"]
        _LOGGER.debug(_LOG_CHARGING_STATUS, self.vehicle_id, self._charging_sensor, is_charging)
        return is_charging

    async def async_activate_charging(self) -> bool:
        """Activate vehicle charging with retry logic.

        Checks presence conditions (home, plugged) before activating.
        Implements retry logic: up to 3 attempts within 5 minutes.
        Resets retry counter on disconnect/reconnect (when charging stops).
        """
        # Check presence conditions first
        is_ready, reason = await self.async_check_presence_status()
        if not is_ready:
            _LOGGER.warning(_LOG_CANNOT_ACTIVATE, self.vehicle_id, reason)
            return False

        if self._strategy is None:
            _LOGGER.warning(_LOG_NO_STRATEGY, self.vehicle_id)
            return False

        # Check for disconnect/reconnect - reset retry counter
        await self._check_and_reset_retry_on_disconnect()

        # Check if we should retry
        if not self._retry_state.should_retry():
            attempt_count = self._retry_state.get_attempt_count()
            _LOGGER.warning(_LOG_RETRY_EXCEEDED, MAX_RETRY_ATTEMPTS, self.vehicle_id, RETRY_TIME_WINDOW_SECONDS)
            return False

        # Attempt to activate charging
        success = await self._strategy.async_activate()

        if success:
            # Reset retry state on successful activation
            self._retry_state.reset()
            _LOGGER.info(_LOG_ACTIVATED, self.vehicle_id)
        else:
            # Record this attempt
            self._retry_state.add_attempt()
            attempt_count = self._retry_state.get_attempt_count()
            _LOGGER.warning(_LOG_ACTIVATION_FAILED, self.vehicle_id, attempt_count, MAX_RETRY_ATTEMPTS)

        return success

    async def _check_and_reset_retry_on_disconnect(self) -> None:
        """Check for disconnect/reconnect and reset retry counter if needed.

        Resets the retry counter when the vehicle was previously charging
        but is now disconnected (not charging).
        """
        if not self._charging_sensor:
            return

        current_charging = await self._async_check_charging_sensor()

        # If previously charging and now not charging, reset retry state
        if self._last_charging_state is True and current_charging is False:
            _LOGGER.info(_LOG_DISCONNECT_RESET, self.vehicle_id)
            self._retry_state.reset()

        # Update last known charging state
        self._last_charging_state = current_charging

    def reset_retry_state(self) -> None:  # pragma: no mutate  # EQ-004
        """Manually reset the retry counter.

        This can be called when the user wants to reset after being
        notified of charging failures.
        """
        self._retry_state.reset()
        _LOGGER.info(_LOG_RETRY_RESET, self.vehicle_id)

    def get_retry_state(self) -> Dict[str, Any]:
        """Get the current retry state information.

        Returns:
            Dict with attempt count and whether retry is allowed.
        """
        return {
            "attempts": self._retry_state.get_attempt_count(),
            "max_attempts": MAX_RETRY_ATTEMPTS,
            "can_retry": self._retry_state.should_retry(),
            "time_window_seconds": RETRY_TIME_WINDOW_SECONDS,
        }

    async def async_deactivate_charging(self) -> bool:
        """Deactivate vehicle charging.

        Also updates the charging state tracking for disconnect detection.
        """
        if self._strategy is None:
            _LOGGER.warning(_LOG_NO_STRATEGY, self.vehicle_id)
            return False

        result = await self._strategy.async_deactivate()

        # Update charging state after deactivation
        if result:
            await self._update_charging_state_after_deactivation()

        return result

    async def _update_charging_state_after_deactivation(
        self,
    ) -> None:  # pragma: no mutate  # EQ-003
        """Update charging state after deactivation to track disconnect."""
        if not self._charging_sensor:
            return

        current_charging = await self._async_check_charging_sensor()
        self._last_charging_state = current_charging

    async def async_get_charging_status(self) -> bool:
        """Get current charging status."""
        if self._strategy is None:
            return False
        return await self._strategy.async_get_status()
