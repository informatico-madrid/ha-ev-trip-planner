"""Schedule Monitor for EV Trip Planner."""

import logging
from typing import Any, Callable, Dict, List

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_NOTIFICATION_SERVICE, CONF_VEHICLE_NAME

_LOGGER = logging.getLogger(__name__)


class ScheduleMonitor:
    """Monitors EMHASS schedules and executes vehicle control."""

    def __init__(self, hass: HomeAssistant):
        """Initialize monitor."""
        self.hass = hass
        self._vehicle_monitors: Dict[str, "VehicleScheduleMonitor"] = {}
        self._unsub_handlers: List[Callable[..., Any]] = []

    async def async_setup(self, vehicle_configs: Dict[str, Dict[str, Any]]):
        """Set up monitoring for all vehicles."""
        for entry_id, config in vehicle_configs.items():
            vehicle_id = config[CONF_VEHICLE_NAME]

            # Create vehicle monitor
            vehicle_monitor = VehicleScheduleMonitor(
                hass=self.hass,
                vehicle_id=vehicle_id,
                control_strategy=config["control_strategy"],
                presence_monitor=config.get("presence_monitor"),
                notification_service=config.get(CONF_NOTIFICATION_SERVICE),
                emhass_adapter=config.get("emhass_adapter"),  # NEW: Pass adapter
            )

            await vehicle_monitor.async_start()
            self._vehicle_monitors[vehicle_id] = vehicle_monitor

        _LOGGER.info(
            "ScheduleMonitor setup complete for %d vehicles",
            len(self._vehicle_monitors),
        )

    async def async_stop(self):
        """Stop all monitoring."""
        for monitor in self._vehicle_monitors.values():
            await monitor.async_stop()

        self._vehicle_monitors.clear()
        _LOGGER.info("ScheduleMonitor stopped")


class VehicleScheduleMonitor:
    """Monitors schedules for a single vehicle."""

    def __init__(
        self,
        hass: HomeAssistant,
        vehicle_id: str,
        control_strategy,
        presence_monitor,
        notification_service: str | None,
        emhass_adapter,
    ):
        """Initialize vehicle monitor."""
        self.hass = hass
        self.vehicle_id = vehicle_id
        self.control_strategy = control_strategy
        self.presence_monitor = presence_monitor
        self.notification_service = notification_service
        self.emhass_adapter = emhass_adapter  # NEW: For index lookup

        self._unsub_handlers: Dict[int, Callable[..., Any]] = (
            {}
        )  # index -> unsub function
        self._last_actions: Dict[int, str] = {}  # index -> last action

        _LOGGER.debug("Created VehicleScheduleMonitor for %s", vehicle_id)

    async def async_start(self):
        """Start monitoring all schedules for this vehicle."""
        if not self.emhass_adapter:
            _LOGGER.warning(
                "No EMHASS adapter for vehicle %s, cannot start monitoring",
                self.vehicle_id,
            )
            return

        # Get all assigned indices for this vehicle
        assigned_indices = self.emhass_adapter.get_all_assigned_indices()

        if not assigned_indices:
            _LOGGER.info(
                "No active trips for vehicle %s, monitoring will start when trips added",
                self.vehicle_id,
            )  # noqa: E501
            return

        # Subscribe to schedule for each index
        for trip_id, emhass_index in assigned_indices.items():
            await self._async_monitor_schedule(emhass_index)

        _LOGGER.info(
            "Started monitoring %d schedules for vehicle %s",
            len(assigned_indices),
            self.vehicle_id,
        )

    async def async_stop(self):
        """Stop monitoring all schedules."""
        for unsub in self._unsub_handlers.values():
            if bool(unsub):
                unsub()
        self._unsub_handlers.clear()
        self._last_actions.clear()

    async def _async_monitor_schedule(self, emhass_index: int):
        """Start monitoring a specific schedule."""
        schedule_entity_id = f"sensor.emhass_deferrable{emhass_index}_schedule"

        # Check if schedule entity exists
        if not self.hass.states.get(schedule_entity_id):
            _LOGGER.warning(
                "Schedule entity %s not found for vehicle %s. "
                "Ensure EMHASS is configured correctly.",
                schedule_entity_id,
                self.vehicle_id,
            )
            return

        # Subscribe to state changes
        @callback
        def schedule_changed(event):
            """Handle schedule change."""
            self.hass.async_create_task(  # pragma: no cover  # HA event bus - async task creation for schedule change handling
                self._async_handle_schedule_change(emhass_index)
            )

        unsub = async_track_state_change_event(
            self.hass, [schedule_entity_id], schedule_changed
        )

        self._unsub_handlers[emhass_index] = unsub

        _LOGGER.debug(
            "Monitoring schedule for %s: %s", self.vehicle_id, schedule_entity_id
        )

        # Initial check
        await self._async_handle_schedule_change(emhass_index)

    async def _async_handle_schedule_change(self, emhass_index: int):
        """Process schedule change and execute control."""
        try:
            schedule_entity_id = f"sensor.emhass_deferrable{emhass_index}_schedule"

            # Get current schedule
            schedule_state = self.hass.states.get(schedule_entity_id)
            if (
                not schedule_state
            ):  # pragma: no cover  # HA sensor I/O - entity may disappear between HA restarts
                _LOGGER.warning("Schedule entity disappeared: %s", schedule_entity_id)
                return  # pragma: no cover  # HA sensor I/O - early return when entity not found

            # Parse schedule
            should_charge = self._parse_schedule(schedule_state.state)

            if should_charge:
                await self._async_start_charging(emhass_index)
            else:
                await self._async_stop_charging(emhass_index)

        except Exception as err:
            _LOGGER.error(
                "Error handling schedule change for index %d: %s", emhass_index, err
            )

    def _parse_schedule(self, schedule_state: str) -> bool:
        """
        Parse EMHASS schedule to determine if should charge now.

        Expected format: "02:00-03:00, 05:00-06:00" or JSON
        """
        if not schedule_state or schedule_state in ["unknown", "unavailable"]:
            return False

        # For now, simple check - expand based on actual EMHASS format
        # TODO: Implement proper schedule parsing
        return "on" in schedule_state.lower() or "true" in schedule_state.lower()

    async def _async_start_charging(self, emhass_index: int):
        """Start charging with safety checks."""
        if self._last_actions.get(emhass_index) == "start":
            # Already started, avoid duplicate
            return

        _LOGGER.info(
            "Schedule indicates charging should start for %s (index %d)",
            self.vehicle_id,
            emhass_index,
        )

        # CRITICAL: Check presence first
        if self.presence_monitor:
            is_at_home = await self.presence_monitor.async_check_home_status()
            if not is_at_home:
                _LOGGER.info(
                    "Vehicle %s not at home, ignoring start charging request (index %d)",
                    self.vehicle_id,
                    emhass_index,
                )
                await self._async_notify(
                    f"⚠️ Charging skipped: {self.vehicle_id} not at home",
                    "Schedule requested charging but vehicle is not at home",
                )
                return

            is_plugged = await self.presence_monitor.async_check_plugged_status()
            if not is_plugged:
                _LOGGER.info(
                    "Vehicle %s not plugged, ignoring start charging request (index %d)",
                    self.vehicle_id,
                    emhass_index,
                )
                await self._async_notify(
                    f"🔌 Connect vehicle: {self.vehicle_id}",
                    "Schedule requested charging but vehicle is not plugged in",
                )
                return

        # Execute control
        success = await self.control_strategy.async_activate()

        if success:
            self._last_actions[emhass_index] = "start"
            _LOGGER.info(
                "Started charging for vehicle %s (index %d)",
                self.vehicle_id,
                emhass_index,
            )
        else:  # pragma: no cover  # HA control I/O - control strategy activation failure triggers error logging and notification
            _LOGGER.error(
                "Failed to start charging for vehicle %s (index %d)",
                self.vehicle_id,
                emhass_index,
            )
            await self._async_notify(  # pragma: no cover  # HA control I/O - notification on charging failure
                f"❌ Charging failed: {self.vehicle_id}",
                "Failed to start charging. Check logs for errors.",
            )

    async def _async_stop_charging(self, emhass_index: int):
        """Stop charging."""
        if self._last_actions.get(emhass_index) == "stop":
            # Already stopped
            return

        _LOGGER.info(
            "Schedule indicates charging should stop for %s (index %d)",
            self.vehicle_id,
            emhass_index,
        )

        success = await self.control_strategy.async_deactivate()

        if success:
            self._last_actions[emhass_index] = "stop"
            _LOGGER.info(
                "Stopped charging for vehicle %s (index %d)",
                self.vehicle_id,
                emhass_index,
            )
        else:  # pragma: no cover  # HA control I/O - control strategy deactivation failure triggers error logging
            _LOGGER.error(
                "Failed to stop charging for vehicle %s (index %d)",
                self.vehicle_id,
                emhass_index,
            )

    async def _async_notify(self, title: str, message: str):
        """Send notification."""
        try:
            if self.notification_service is None:
                return
            domain, service = self.notification_service.split(".", 1)
            await self.hass.services.async_call(
                domain,
                service,
                {
                    "title": title,
                    "message": message,
                    "notification_id": f"ev_trip_planner_{self.vehicle_id}",
                },
            )
        except Exception as err:
            _LOGGER.error("Error sending notification: %s", err)

    async def async_add_trip_monitor(self, trip_id: str, emhass_index: int):
        """Start monitoring a new trip's schedule."""
        if emhass_index in self._unsub_handlers:
            _LOGGER.debug(
                "Already monitoring index %d for vehicle %s",
                emhass_index,
                self.vehicle_id,
            )
            return

        await self._async_monitor_schedule(emhass_index)

    async def async_remove_trip_monitor(self, emhass_index: int):
        """Stop monitoring a trip's schedule."""
        if emhass_index not in self._unsub_handlers:
            return

        unsub = self._unsub_handlers.pop(emhass_index)
        if bool(unsub):
            unsub()

        self._last_actions.pop(emhass_index, None)

        _LOGGER.info(
            "Stopped monitoring schedule for %s (index %d)",
            self.vehicle_id,
            emhass_index,
        )
