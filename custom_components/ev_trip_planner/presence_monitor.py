"""Presence Monitor for EV Trip Planner."""

import logging
from math import radians, sin, cos, sqrt, atan2
from typing import Any, Dict, Optional, Tuple

from homeassistant.core import HomeAssistant

from .const import (
    CONF_HOME_SENSOR,
    CONF_PLUGGED_SENSOR,
    CONF_HOME_COORDINATES,
    CONF_VEHICLE_COORDINATES_SENSOR,
)

_LOGGER = logging.getLogger(__name__)

# Umbral de distancia para considerar que el vehículo está "en casa"
# Los GPS modernos tienen precisión de 3-5m, así que 30m es un valor más preciso
# que permite pequeñas variaciones sin ser exagerado
HOME_DISTANCE_THRESHOLD_METERS = 30.0


class PresenceMonitor:
    """Monitors vehicle presence and charging status."""
    
    def __init__(self, hass: HomeAssistant, vehicle_id: str, config: Dict[str, Any]):
        """Initialize presence monitor."""
        self.hass = hass
        self.vehicle_id = vehicle_id
        
        # Sensor-based detection (priority 1)
        self.home_sensor = config.get(CONF_HOME_SENSOR)
        self.plugged_sensor = config.get(CONF_PLUGGED_SENSOR)
        
        # Coordinate-based detection (priority 2)
        self.home_coords = self._parse_coordinates(config.get(CONF_HOME_COORDINATES))
        self.vehicle_coords_sensor = config.get(CONF_VEHICLE_COORDINATES_SENSOR)
        
        _LOGGER.debug(
            "Created PresenceMonitor for %s: home_sensor=%s, home_coords=%s",
            vehicle_id,
            self.home_sensor,
            self.home_coords,
        )
    
    async def async_check_home_status(self) -> bool:
        """
        Check if vehicle is at home.
        
        Priority:
        1. Use sensor if configured
        2. Use coordinates if configured
        3. Return True (blind mode) if nothing configured
        """
        # Priority 1: Sensor-based detection
        if self.home_sensor:
            return await self._async_check_home_sensor()
        
        # Priority 2: Coordinate-based detection
        if self.home_coords and self.vehicle_coords_sensor:
            return await self._async_check_home_coordinates()
        
        # Priority 3: Blind mode - assume at home
        _LOGGER.debug(
            "No home detection configured for %s, assuming at home (blind mode)",
            self.vehicle_id,
        )
        return True
    
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