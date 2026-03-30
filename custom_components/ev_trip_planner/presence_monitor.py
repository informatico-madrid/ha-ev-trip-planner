"""Presence Monitor for EV Trip Planner."""

import logging
from math import radians, sin, cos, sqrt, atan2
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .trip_manager import TripManager

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import storage as ha_storage
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt_util

from .const import (
    CONF_HOME_SENSOR,
    CONF_PLUGGED_SENSOR,
    CONF_HOME_COORDINATES,
    CONF_VEHICLE_COORDINATES_SENSOR,
    CONF_NOTIFICATION_SERVICE,
    CONF_SOC_SENSOR,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Umbral de distancia para considerar que el vehículo está "en casa"
# Los GPS modernos tienen precisión de 3-5m, así que 30m es un valor más preciso
# que permite pequeñas variaciones sin ser exagerado
HOME_DISTANCE_THRESHOLD_METERS = 30.0


class PresenceMonitor:
    """Monitors vehicle presence and charging status."""
    
    def __init__(self, hass: HomeAssistant, vehicle_id: str, config: Dict[str, Any], trip_manager: Optional["TripManager"] = None):
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
        self.home_coords = self._parse_coordinates(config.get(CONF_HOME_COORDINATES))
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

        # Persistence store for return info (ha_storage.Store API)
        self._return_info_store = ha_storage.Store(
            hass,
            version=1,
            key=f"{DOMAIN}_{vehicle_id}_return_info",
        )
        # Entity ID for HA state entity
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
        """
        Check if vehicle is at home.

        Priority:
        1. Use sensor if configured
        2. Use coordinates if configured
        3. Return True (blind mode) if nothing configured

        Detects off->on transition (return home) and on->off transition (departure).
        """
        # Priority 1: Sensor-based detection
        if self.home_sensor:
            is_home = await self._async_check_home_sensor()
        # Priority 2: Coordinate-based detection
        elif self.home_coords and self.vehicle_coords_sensor:
            is_home = await self._async_check_home_coordinates()
        # Priority 3: Blind mode - assume at home
        else:
            _LOGGER.debug(
                "No home detection configured for %s, assuming at home (blind mode)",
                self.vehicle_id,
            )
            is_home = True

        # Detect off->on transition (return home)
        if is_home and not self._was_home:
            _LOGGER.info(
                "Vehicle %s returned home (off->on transition)",
                self.vehicle_id,
            )
            # Get current SOC if available
            soc_value: Optional[float] = None
            if self.soc_sensor:
                state = self.hass.states.get(self.soc_sensor)
                if state:
                    try:
                        soc_value = float(state.state)
                    except (ValueError, AttributeError):
                        pass
            await self.async_handle_return_home(soc_value)

        # Detect on->off transition (departure) - invalidate hora_regreso
        if not is_home and self._was_home:
            _LOGGER.info(
                "Vehicle %s departed (on->off transition), invalidating hora_regreso",
                self.vehicle_id,
            )
            self.hora_regreso = None
            self.soc_en_regreso = None
            # Persist cleared state to Store and update HA state entity
            await self._async_persist_return_info()

        # Update previous state tracking
        self._was_home = is_home

        return is_home
    
    async def async_check_plugged_status(self) -> bool:
        """
        Check if vehicle is plugged in.
        
        Returns True if no sensor configured (blind mode).
        """
        if not self.plugged_sensor:
            _LOGGER.debug(
                "No plugged sensor configured for %s, assuming plugged (blind mode)",
                self.vehicle_id,
            )
            return True
        
        state = self.hass.states.get(self.plugged_sensor)
        if not state:
            _LOGGER.warning(
                "Plugged sensor %s not found for %s, assuming plugged",
                self.plugged_sensor,
                self.vehicle_id,
            )
            return True
        
        is_plugged = state.state.lower() in ["on", "true", "yes", "connected"]
        _LOGGER.debug(
            "Plugged status for %s: %s = %s",
            self.vehicle_id,
            self.plugged_sensor,
            is_plugged,
        )
        return is_plugged

    async def async_handle_return_home(self, soc_value: Optional[float]) -> None:
        """
        Handle return home event (off->on transition).

        Captures the return timestamp and SOC for calculating the charging window.

        Args:
            soc_value: The SOC value at the time of return, if available
        """
        now = dt_util.now()
        self.hora_regreso = now.isoformat()
        self.soc_en_regreso = soc_value

        _LOGGER.info(
            "Return home detected for %s: hora_regreso=%s, soc_en_regreso=%s",
            self.vehicle_id,
            self.hora_regreso,
            self.soc_en_regreso,
        )

        # Persist to Store and update HA state entity
        await self._async_persist_return_info()

    async def _async_persist_return_info(self) -> None:
        """
        Persist return info to HA storage and update HA state entity.

        Saves hora_regreso and soc_en_regreso to ha_storage.Store,
        then updates the sensor.ev_trip_planner_{vehicle_id}_return_info entity.
        """
        # Save to HA storage
        await self._return_info_store.async_save({
            "hora_regreso": self.hora_regreso,
            "soc_en_regreso": self.soc_en_regreso,
        })

        # Update HA state entity
        self.hass.states.async_set(
            self._return_info_entity_id,
            self.hora_regreso or "unknown",
            {
                "soc_en_regreso": self.soc_en_regreso,
                "hora_regreso_iso": self.hora_regreso,
                "vehicle_id": self.vehicle_id,
            },
        )

        _LOGGER.debug(
            "Return info persisted for %s: entity=%s, hora_regreso=%s, soc_en_regreso=%s",
            self.vehicle_id,
            self._return_info_entity_id,
            self.hora_regreso,
            self.soc_en_regreso,
        )

    async def async_check_charging_readiness(self) -> Tuple[bool, Optional[str]]:
        """
        Check if vehicle is ready for charging.
        
        Returns:
            Tuple of (is_ready, reason_if_not_ready)
        """
        # Check home status
        is_at_home = await self.async_check_home_status()
        if not is_at_home:
            return False, "Vehicle not at home"
        
        # Check plugged status
        is_plugged = await self.async_check_plugged_status()
        if not is_plugged:
            return False, "Vehicle not plugged in"
        
        return True, None
    
    async def _async_check_home_sensor(self) -> bool:
        """Check home status using sensor."""
        state = self.hass.states.get(self.home_sensor)
        if not state:
            _LOGGER.warning(
                "Home sensor %s not found for %s, returning False",
                self.home_sensor,
                self.vehicle_id,
            )
            return False
        
        is_home = state.state.lower() in ["on", "true", "yes", "home"]
        _LOGGER.debug(
            "Home status for %s: %s = %s",
            self.vehicle_id,
            self.home_sensor,
            is_home,
        )
        return is_home
    
    async def _async_check_home_coordinates(self) -> bool:
        """Check home status using coordinates."""
        if not self.home_coords:
            _LOGGER.error("Home coordinates not set for %s", self.vehicle_id)
            return False
        
        state = self.hass.states.get(self.vehicle_coords_sensor)
        if not state:
            _LOGGER.warning(
                "Vehicle coordinates sensor %s not found for %s, assuming at home",
                self.vehicle_coords_sensor,
                self.vehicle_id,
            )
            return True
        
        vehicle_coords = self._parse_coordinates(state.state)
        if not vehicle_coords:
            _LOGGER.warning(
                "Could not parse vehicle coordinates from %s for %s, assuming at home",
                state.state,
                self.vehicle_id,
            )
            return True
        
        distance = self._calculate_distance(self.home_coords, vehicle_coords)
        
        _LOGGER.debug(
            "Distance from home for %s: %.1f meters (threshold: %.1f m)",
            self.vehicle_id,
            distance,
            HOME_DISTANCE_THRESHOLD_METERS,
        )
        
        return distance <= HOME_DISTANCE_THRESHOLD_METERS
    
    def _parse_coordinates(self, coord_string: str) -> Optional[Tuple[float, float]]:
        """
        Parse coordinates from string.
        
        Supports formats:
        - "40.4168, -3.7038"
        - "[40.4168, -3.7038]"
        - "40.4168 -3.7038"
        """
        if not coord_string:
            return None
        
        try:
            # Remove brackets if present
            coord_string = coord_string.strip("[]")
            
            # Split by comma or space
            parts = coord_string.replace(",", " ").split()
            
            if len(parts) != 2:
                return None
            
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            
            # Basic validation
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return None
            
            return (lat, lon)
        except (ValueError, AttributeError):
            return None
    
    def _calculate_distance(
        self, coords1: Tuple[float, float], coords2: Tuple[float, float]
    ) -> float:
        """
        Calculate distance between two coordinates using Haversine formula.
        
        Returns distance in meters.
        """
        lat1, lon1 = coords1
        lat2, lon2 = coords2
        
        # Convert to radians
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        # Earth's radius in meters
        earth_radius = 6371000

        return earth_radius * c

    def _async_setup_soc_listener(self) -> None:
        """Set up SOC sensor state change listener."""
        if not self.soc_sensor:
            _LOGGER.debug(
                "No SOC sensor configured for %s, SOC listener not set up",
                self.vehicle_id,
            )
            return

        _LOGGER.debug(
            "Setting up SOC listener for %s with sensor %s",
            self.vehicle_id,
            self.soc_sensor,
        )

        async_track_state_change_event(
            self.hass,
            self.soc_sensor,
            self._async_handle_soc_change,
        )

    async def _async_handle_soc_change(self, event: Dict[str, Any]) -> None:
        """Handle SOC state change event.

        Called when the SOC sensor state changes. If the vehicle is home
        and plugged in, triggers power profile and schedule recalculation.

        Debouncing: Only triggers recalculation if SOC change >= 5% delta.

        Args:
            event: The state change event from Home Assistant
        """
        if not self._trip_manager:
            _LOGGER.debug(
                "SOC change detected for %s but no trip_manager available, skipping",
                self.vehicle_id,
            )
            return

        # Get new SOC value from event
        new_state = event.get("data", {}).get("new_state")
        if not new_state:
            _LOGGER.debug(
                "SOC change event for %s has no new_state, skipping",
                self.vehicle_id,
            )
            return

        # Handle unavailable/unknown states - skip without updating _last_processed_soc
        if new_state.state in ["unavailable", "unknown", "None", ""]:
            _LOGGER.debug(
                "SOC state for %s is '%s', skipping",
                self.vehicle_id,
                new_state.state,
            )
            return

        try:
            new_soc = float(new_state.state)
        except (ValueError, AttributeError):
            _LOGGER.debug(
                "Could not parse SOC value from %s for %s",
                new_state.state,
                self.vehicle_id,
            )
            return

        # Debounce: calculate delta from last processed SOC
        last_soc = self._last_processed_soc
        if last_soc is not None:
            delta = abs(new_soc - last_soc)
            if delta < 5.0:
                _LOGGER.debug(
                    "SOC change for %s (%.1f%% -> %.1f%%, delta=%.2f%%) below 5%% threshold, skipping",
                    self.vehicle_id,
                    last_soc,
                    new_soc,
                    delta,
                )
                return

        _LOGGER.debug(
            "SOC change detected for %s: new SOC = %s",
            self.vehicle_id,
            new_soc,
        )

        # Check if home and plugged
        is_home = await self.async_check_home_status()
        is_plugged = await self.async_check_plugged_status()

        if not is_home:
            _LOGGER.debug(
                "SOC change for %s skipped: vehicle not at home (is_home=%s)",
                self.vehicle_id,
                is_home,
            )
            return

        if not is_plugged:
            _LOGGER.debug(
                "SOC change for %s skipped: vehicle not plugged (is_plugged=%s)",
                self.vehicle_id,
                is_plugged,
            )
            return

        # Vehicle is home and plugged - trigger recalculation
        _LOGGER.info(
            "SOC changed to %s%% while %s is home and plugged, triggering recalculation",
            new_soc,
            self.vehicle_id,
        )

        # Update last_processed_soc only when recalculation is triggered
        self._last_processed_soc = new_soc

        # Call the public async methods on trip_manager
        await self._trip_manager.async_generate_power_profile()
        await self._trip_manager.async_generate_deferrables_schedule()

    async def async_notify_charging_not_possible(
        self,
        reason: str,
        trip_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send notification when charging is necessary but not possible.

        Args:
            reason: The reason why charging is not possible
            trip_info: Optional trip information (destination, energy needed, etc.)

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.notification_service:
            _LOGGER.debug(
                "No notification service configured for %s, skipping notification",
                self.vehicle_id,
            )
            return False

        # Build notification message
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
        """
        Send notification when vehicle is not at home but charging is needed.

        Args:
            trip_info: Optional trip information

        Returns:
            True if notification was sent successfully, False otherwise
        """
        return await self.async_notify_charging_not_possible(
            reason="Vehicle not at home",
            trip_info=trip_info,
        )

    async def async_notify_vehicle_not_plugged(
        self, trip_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send notification when vehicle is not plugged in but charging is needed.

        Args:
            trip_info: Optional trip information

        Returns:
            True if notification was sent successfully, False otherwise
        """
        return await self.async_notify_charging_not_possible(
            reason="Vehicle not plugged in",
            trip_info=trip_info,
        )

    async def _async_send_notification(self, title: str, message: str) -> bool:
        """
        Send notification via configured notification service.

        Args:
            title: Notification title
            message: Notification message

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.notification_service:
            _LOGGER.warning(
                "No notification service configured for vehicle %s",
                self.vehicle_id,
            )
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
            _LOGGER.info(
                "Notification sent for vehicle %s: %s",
                self.vehicle_id,
                title,
            )
            return True
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Failed to send notification for vehicle %s: %s",
                self.vehicle_id,
                err,
            )
            return False

    def get_home_condition_config(self) -> Optional[Dict[str, Any]]:
        """
        Get native state condition configuration for home status.

        Returns a native 'condition: state' configuration for use in
        Home Assistant automations, following HA best practices:
        https://www.home-assistant.io/docs/automation/templating/#state-conditions

        Returns:
            Dict with native condition: state configuration, or None if not configured
        """
        if not self.home_sensor:
            _LOGGER.debug(
                "No home sensor configured for %s, cannot provide condition config",
                self.vehicle_id,
            )
            return None

        # Native condition: state - more efficient than template conditions
        return {
            "condition": "state",
            "entity_id": self.home_sensor,
            "state": "on",
        }

    def get_plugged_condition_config(self) -> Optional[Dict[str, Any]]:
        """
        Get native state condition configuration for plugged status.

        Returns a native 'condition: state' configuration for use in
        Home Assistant automations, following HA best practices.

        Returns:
            Dict with native condition: state configuration, or None if not configured
        """
        if not self.plugged_sensor:
            _LOGGER.debug(
                "No plugged sensor configured for %s, cannot provide condition config",
                self.vehicle_id,
            )
            return None

        # Native condition: state - more efficient than template conditions
        return {
            "condition": "state",
            "entity_id": self.plugged_sensor,
            "state": "on",
        }

    def validate_condition_is_native(
        self, condition: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that an automation condition uses native state format.

        This method checks if the condition follows Home Assistant best practices:
        - Uses 'condition: state' instead of 'condition: template'
        - Has 'entity_id' and 'state' keys

        Args:
            condition: The condition dict to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(condition, dict):
            return False, "Condition must be a dictionary"

        # Check for template condition (anti-pattern)
        if condition.get("condition") == "template":
            return False, (
                "Using 'condition: template' is not recommended. "
                "Use native 'condition: state' instead for better performance. "
                "Example: condition: state\\n  entity_id: "
                "binary_sensor.vehicle_home\\n  state: 'on'"
            )

        # Check for native state condition
        if condition.get("condition") == "state":
            if "entity_id" not in condition:
                return False, "Native state condition missing 'entity_id'"
            if "state" not in condition:
                return False, "Native state condition missing 'state'"
            return True, None

        # Other condition types are acceptable
        return True, None