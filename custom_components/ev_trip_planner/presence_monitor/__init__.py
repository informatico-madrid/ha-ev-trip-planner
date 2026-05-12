"""Presence Monitor for EV Trip Planner.

Extracted from presence_monitor_orig.py as part of the SOLID decomposition.
Monitors vehicle presence and charging status using sensor or coordinate data.
"""

from __future__ import annotations

import logging
from datetime import datetime
from math import atan2, cos, radians, sin, sqrt
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Tuple

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import storage as ha_storage
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from ..const import (
    CONF_HOME_COORDINATES,
    CONF_HOME_SENSOR,
    CONF_NOTIFICATION_SERVICE,
    CONF_PLUGGED_SENSOR,
    CONF_SOC_SENSOR,
    CONF_VEHICLE_COORDINATES_SENSOR,
    DOMAIN,
)

if TYPE_CHECKING:
    from ..trip import TripManager

_LOGGER = logging.getLogger(__name__)

# Umbral de distancia para considerar que el vehículo está "en casa"
HOME_DISTANCE_THRESHOLD_METERS = 30.0

# Umbral de cambio de SOC para disparar recálculo (debouncing)
SOC_CHANGE_DEBOUNCE_PERCENT = 5.0

__all__ = [
    "HOME_DISTANCE_THRESHOLD_METERS",
    "PresenceMonitor",
    "SOC_CHANGE_DEBOUNCE_PERCENT",
]


class PresenceMonitor:
    """Monitors vehicle presence and charging status."""

    def __init__(
        self,
        hass: HomeAssistant,
        vehicle_id: str,
        config: Dict[str, Any],
        trip_manager: Optional["TripManager"] = None,
    ):
        """Initialize presence monitor."""
        self.hass = hass
        self.vehicle_id = vehicle_id
        self._trip_manager = trip_manager

        # Sensor-based detection (priority 1)
        self.home_sensor = config.get(CONF_HOME_SENSOR)
        self.plugged_sensor = config.get(CONF_PLUGGED_SENSOR)

        # SOC sensor for state of charge tracking
        self.soc_sensor = config.get(CONF_SOC_SENSOR)

        # Coordinate-based detection (priority 2)
        self.home_coords = self._parse_coordinates(
            config.get(CONF_HOME_COORDINATES) or ""
        )
        self.vehicle_coords_sensor = config.get(CONF_VEHICLE_COORDINATES_SENSOR)

        # Notification configuration
        self.notification_service = config.get(CONF_NOTIFICATION_SERVICE)

        # Track previous home state for return/departure detection
        self._was_home: bool = False

        # Return time tracking (AC-4, AC-6)
        self.hora_regreso: Optional[str] = None
        self.soc_en_regreso: Optional[float] = None

        # SOC debouncing state - last processed SOC for delta comparison
        self._last_processed_soc: Optional[float] = None

        # SOC listener registration guard
        from homeassistant.core import CALLBACK_TYPE

        self._soc_listener_unsub: Optional[CALLBACK_TYPE] = None

        # Persistence store for return info (ha_storage.Store API)
        self._return_info_store: ha_storage.Store[dict[str, Any]] = ha_storage.Store(
            hass,
            version=1,
            key=f"{DOMAIN}_{vehicle_id}_return_info",
        )
        self._return_info_entity_id = f"sensor.{DOMAIN}_{vehicle_id}_return_info"

        _LOGGER.debug(
            "Created PresenceMonitor for %s: home_sensor=%s, home_coords=%s, "
            "notification_service=%s, soc_sensor=%s",
            vehicle_id,
            self.home_sensor,
            self.home_coords,
            self.notification_service,
            self.soc_sensor,
        )

        # Set up SOC change listener if soc_sensor is configured
        self._async_setup_soc_listener()

    async def async_check_home_status(self) -> bool:
        """Check if vehicle is at home with priority-based detection."""
        if self.home_sensor:
            is_home = await self._async_check_home_sensor()
        elif self.home_coords and self.vehicle_coords_sensor:
            is_home = await self._async_check_home_coordinates()
        else:
            _LOGGER.debug(
                "No home detection configured for %s, assuming at home",
                self.vehicle_id,
            )
            is_home = True

        if is_home and not self._was_home:
            await self.async_handle_return_home(self._get_soc_from_sensor())

        if not is_home and self._was_home:
            self.hora_regreso = None
            self.soc_en_regreso = None
            await self._async_persist_return_info()

        self._was_home = is_home
        return is_home

    def _get_soc_from_sensor(self) -> Optional[float]:
        """Get SOC value from sensor if configured."""
        if not self.soc_sensor:
            return None
        state = self.hass.states.get(self.soc_sensor)
        if not state:
            return None
        try:
            return float(state.state)
        except (ValueError, AttributeError):
            return None

    async def async_check_plugged_status(self) -> bool:
        """Check if vehicle is plugged in."""
        if not self.plugged_sensor:
            return True

        state = self.hass.states.get(self.plugged_sensor)
        if not state:
            return True

        return state.state.lower() in ["on", "true", "yes", "connected"]

    async def async_handle_return_home(self, soc_value: Optional[float]) -> None:
        """Handle return home event."""
        now = dt_util.now()
        self.hora_regreso = now.isoformat()
        self.soc_en_regreso = soc_value
        _LOGGER.info(
            "Return home detected for %s: hora_regreso=%s, soc_en_regreso=%s",
            self.vehicle_id,
            self.hora_regreso,
            self.soc_en_regreso,
        )
        await self._async_persist_return_info()

    async def async_get_hora_regreso(self) -> Optional[datetime]:
        """Get the hora_regreso (return time) from the HA state entity."""
        state = self.hass.states.get(self._return_info_entity_id)
        if not state:
            return None

        hora_regreso_iso = state.attributes.get("hora_regreso_iso")
        if not hora_regreso_iso:
            return None

        try:
            return datetime.fromisoformat(hora_regreso_iso)
        except (ValueError, AttributeError) as err:
            _LOGGER.warning(
                "Failed to parse hora_regreso_iso '%s' for %s: %s",
                hora_regreso_iso,
                self.vehicle_id,
                err,
            )
            return None

    async def async_notify_charging_not_possible(
        self,
        reason: str,
        trip_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send notification when charging is necessary but not possible."""
        if not self.notification_service:
            return False

        title = f"⚠️ EV Trip Planner: {self.vehicle_id}"
        message = f"Charging required but not possible: {reason}"

        if trip_info:
            if "destination" in trip_info:
                message += f"\n\nTrip destination: {trip_info['destination']}"
            if "energy_needed" in trip_info:
                message += f"\nEnergy needed: {trip_info['energy_needed']} kWh"
            if "deadline" in trip_info:
                message += f"\nDeadline: {trip_info['deadline']}"

        message += "\n\nPlease connect the vehicle or ensure it's at home."
        return await self._async_send_notification(title, message)

    async def async_notify_vehicle_not_home(
        self, trip_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send notification when vehicle is not at home but charging is needed."""
        return await self.async_notify_charging_not_possible(
            reason="Vehicle not at home",
            trip_info=trip_info,
        )

    async def async_notify_vehicle_not_plugged(
        self, trip_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send notification when vehicle is not plugged in but charging is needed."""
        return await self.async_notify_charging_not_possible(
            reason="Vehicle not plugged in",
            trip_info=trip_info,
        )

    async def async_check_charging_readiness(self) -> Tuple[bool, Optional[str]]:
        """Check if vehicle is ready for charging."""
        is_at_home = await self.async_check_home_status()
        if not is_at_home:
            return False, "Vehicle not at home"

        is_plugged = await self.async_check_plugged_status()
        if not is_plugged:
            return False, "Vehicle not plugged in"

        return True, None

    def get_home_condition_config(self) -> Optional[Dict[str, Any]]:
        """Get native state condition configuration for home status."""
        if not self.home_sensor:
            return None
        return {
            "condition": "state",
            "entity_id": self.home_sensor,
            "state": "on",
        }

    def get_plugged_condition_config(self) -> Optional[Dict[str, Any]]:
        """Get native state condition configuration for plugged status."""
        if not self.plugged_sensor:
            return None
        return {
            "condition": "state",
            "entity_id": self.plugged_sensor,
            "state": "on",
        }

    def validate_condition_is_native(
        self, condition: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate that an automation condition uses native state format."""
        if not isinstance(condition, dict):
            return False, "Condition must be a dictionary"

        if condition.get("condition") == "template":
            return False, (
                "Using 'condition: template' is not recommended. "
                "Use native 'condition: state' instead."
            )

        if condition.get("condition") == "state":
            if "entity_id" not in condition:
                return False, "Native state condition missing 'entity_id'"
            if "state" not in condition:
                return False, "Native state condition missing 'state'"
            return True, None

        return True, None

    # --- Private helpers ---

    async def _async_check_home_sensor(self) -> bool:
        """Check home status using sensor."""
        if self.home_sensor is None:
            return False
        state_obj = self.hass.states.get(self.home_sensor)
        if not state_obj:
            return False

        state = state_obj.state
        if state is None:
            return False
        return state.lower() in ["on", "true", "yes", "home"]

    async def _async_check_home_coordinates(self) -> bool:
        """Check home status using coordinates."""
        if not self.home_coords:
            return False

        if self.vehicle_coords_sensor is None:
            return True

        state_obj = self.hass.states.get(self.vehicle_coords_sensor)
        if not state_obj:
            return True

        state = state_obj.state
        if state is None:
            return True
        vehicle_coords = self._parse_coordinates(state)
        if not vehicle_coords:
            return True

        distance = self._calculate_distance(self.home_coords, vehicle_coords)
        return distance <= HOME_DISTANCE_THRESHOLD_METERS

    async def _async_persist_return_info(self) -> None:
        """Persist return info to HA storage and update HA state entity."""
        await self._return_info_store.async_save(
            {
                "hora_regreso": self.hora_regreso,
                "soc_en_regreso": self.soc_en_regreso,
            }
        )
        self.hass.states.async_set(
            self._return_info_entity_id,
            self.hora_regreso or "unknown",
            {
                "soc_en_regreso": self.soc_en_regreso,
                "hora_regreso_iso": self.hora_regreso,
                "vehicle_id": self.vehicle_id,
            },
        )

    async def _async_send_notification(self, title: str, message: str) -> bool:
        """Send notification via configured notification service."""
        if not self.notification_service:
            return False

        try:
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
            _LOGGER.info("Notification sent for %s: %s", self.vehicle_id, title)
            return True
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Failed to send notification for %s: %s", self.vehicle_id, err
            )
            return False

    def _parse_coordinates(self, coord_string: str) -> Optional[Tuple[float, float]]:
        """Parse coordinates from string like '40.4168, -3.7038'."""
        if not coord_string:
            return None

        try:
            coord_string = coord_string.strip("[]")
            parts = coord_string.replace(",", " ").split()

            if len(parts) != 2:
                return None

            lat = float(parts[0].strip())
            lon = float(parts[1].strip())

            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return None

            return (lat, lon)
        except (ValueError, AttributeError):
            return None

    def _calculate_distance(
        self, coords1: Tuple[float, float], coords2: Tuple[float, float]
    ) -> float:
        """Calculate distance between two coordinates using Haversine formula."""
        lat1, lon1 = coords1
        lat2, lon2 = coords2

        lat1_rad, lon1_rad = radians(lat1), radians(lon1)
        lat2_rad, lon2_rad = radians(lat2), radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return 6371000 * c

    def _async_setup_soc_listener(self) -> None:
        """Set up SOC sensor state change listener (idempotent)."""
        if not self.soc_sensor:
            return

        if self._soc_listener_unsub is not None:
            return

        self._soc_listener_unsub = async_track_state_change_event(
            self.hass,
            self.soc_sensor,
            self._async_handle_soc_change,  # type: ignore[arg-type] # HA stub mismatch
        )

    async def _async_handle_soc_change(self, event: Event[Mapping[str, Any]]) -> None:
        """Handle SOC state change event."""
        if not self._trip_manager:
            return

        new_state = event.data.get("new_state")
        if not new_state:
            return

        if new_state.state in ["unavailable", "unknown", "None", ""]:
            return

        try:
            new_soc = float(new_state.state)
        except (ValueError, AttributeError):
            return

        last_soc = self._last_processed_soc
        if last_soc is not None:
            delta = abs(new_soc - last_soc)
            if delta < SOC_CHANGE_DEBOUNCE_PERCENT:
                return

        is_home = await self.async_check_home_status()
        is_plugged = await self.async_check_plugged_status()

        if not is_home or not is_plugged:
            return

        self._last_processed_soc = new_soc
        await self._trip_manager._schedule.publish_deferrable_loads()
