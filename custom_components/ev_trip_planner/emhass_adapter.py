"""EMHASS Adapter for EV Trip Planner."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_CHARGING_POWER,
    CONF_VEHICLE_NAME,
)

_LOGGER = logging.getLogger(__name__)


class EMHASSAdapter:
    """Adapter to publish trips as EMHASS deferrable loads."""
    
    def __init__(self, hass: HomeAssistant, vehicle_config: Dict[str, Any]):
        """Initialize adapter."""
        self.hass = hass
        self.vehicle_id = vehicle_config[CONF_VEHICLE_NAME]
        self.max_deferrable_loads = vehicle_config.get(CONF_MAX_DEFERRABLE_LOADS, 50)
        self.charging_power = vehicle_config.get(CONF_CHARGING_POWER, 7.4)
        
        # Storage for trip_id → emhass_index mapping
        self._store = Store(hass, version=1, key=f"ev_trip_planner_{self.vehicle_id}_emhass_indices")
        self._index_map: Dict[str, int] = {}  # trip_id → emhass_index
        self._available_indices: List[int] = list(range(self.max_deferrable_loads))
        
        _LOGGER.debug(
            "Created EMHASSAdapter for %s with %d available indices",
            self.vehicle_id,
            len(self._available_indices)
        )
    
    async def async_load(self):
        """Load index mapping from storage."""
        data = await self._store.async_load()
        if data:
            self._index_map = data.get("index_map", {})
            # Rebuild available indices
            used_indices = set(self._index_map.values())
            self._available_indices = [i for i in range(self.max_deferrable_loads) if i not in used_indices]
            _LOGGER.info(
                "Loaded %d trip-index mappings for %s, %d indices still available",
                len(self._index_map),
                self.vehicle_id,
                len(self._available_indices)
            )
    
    async def async_save(self):
        """Save index mapping to storage."""
        await self._store.async_save({
            "index_map": self._index_map,
            "vehicle_id": self.vehicle_id,
        })
    
    async def async_assign_index_to_trip(self, trip_id: str) -> Optional[int]:
        """
        Assign an available EMHASS index to a trip.
        
        Returns:
            Assigned index or None if no indices available
        """
        if trip_id in self._index_map:
            # Trip already has an index, reuse it
            return self._index_map[trip_id]
        
        if not self._available_indices:
            _LOGGER.error(
                "No available EMHASS indices for vehicle %s. "
                "Max deferrable loads: %d, currently used: %d",
                self.vehicle_id,
                self.max_deferrable_loads,
                len(self._index_map)
            )
            return None
        
        # Assign the smallest available index
        assigned_index = min(self._available_indices)
        self._available_indices.remove(assigned_index)
        self._index_map[trip_id] = assigned_index
        
        await self.async_save()
        
        _LOGGER.info(
            "Assigned EMHASS index %d to trip %s for vehicle %s. "
            "%d indices remaining available",
            assigned_index,
            trip_id,
            self.vehicle_id,
            len(self._available_indices)
        )
        
        return assigned_index
    
    async def async_release_trip_index(self, trip_id: str) -> bool:
        """
        Release an EMHASS index when trip is deleted/completed.
        
        Returns:
            True if index was released, False if trip not found
        """
        if trip_id not in self._index_map:
            _LOGGER.warning(
                "Attempted to release index for unknown trip %s",
                trip_id
            )
            return False
        
        released_index = self._index_map.pop(trip_id)
        self._available_indices.append(released_index)
        self._available_indices.sort()
        
        await self.async_save()
        
        _LOGGER.info(
            "Released EMHASS index %d from trip %s for vehicle %s. "
            "Index now available for reuse",
            released_index,
            trip_id,
            self.vehicle_id
        )
        
        return True
    
    def _get_config_sensor_id(self, emhass_index: int) -> str:
        """Get entity ID for EMHASS config sensor."""
        return f"sensor.emhass_deferrable_load_config_{emhass_index}"
    
    async def async_publish_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """
        Publish a trip as deferrable load configuration.
        
        Args:
            trip: Trip dictionary with kwh, deadline, etc.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            trip_id = trip.get("id")
            if not trip_id:
                _LOGGER.error("Trip missing ID")
                return False
            
            # Assign index to trip
            emhass_index = await self.async_assign_index_to_trip(trip_id)
            if emhass_index is None:
                return False
            
            # Calculate parameters
            kwh = float(trip.get("kwh", 0))
            deadline = trip.get("datetime")
            
            if not deadline:
                _LOGGER.error("Trip missing deadline: %s", trip_id)
                await self.async_release_trip_index(trip_id)
                return False
            
            # Calculate hours available
            now = datetime.now()
            if isinstance(deadline, str):
                deadline_dt = datetime.fromisoformat(deadline)
            else:
                deadline_dt = deadline
            
            hours_available = (deadline_dt - now).total_seconds() / 3600
            
            if hours_available <= 0:
                _LOGGER.warning("Trip deadline in past: %s", trip_id)
                await self.async_release_trip_index(trip_id)
                return False
            
            # Calculate EMHASS parameters
            total_hours = kwh / self.charging_power
            power_watts = self.charging_power * 1000  # Convert to Watts
            end_timestep = min(int(hours_available), 168)  # Max 7 days
            
            # Create attributes
            attributes = {
                "def_total_hours": round(total_hours, 2),
                "P_deferrable_nom": round(power_watts, 0),
                "def_start_timestep": 0,
                "def_end_timestep": end_timestep,
                "trip_id": trip_id,
                "vehicle_id": self.vehicle_id,
                "trip_description": trip.get("descripcion", ""),
                "status": "pending",
                "kwh_needed": kwh,
                "deadline": deadline_dt.isoformat(),
                "emhass_index": emhass_index,
            }
            
            # Set state
            config_sensor_id = self._get_config_sensor_id(emhass_index)
            await self.hass.states.async_set(
                config_sensor_id,
                "active",
                attributes
            )
            
            _LOGGER.info(
                "Published deferrable load for trip %s (index %d): %s hours, %s W",
                trip_id,
                emhass_index,
                round(total_hours, 2),
                round(power_watts, 0)
            )
            
            return True
            
        except Exception as err:
            _LOGGER.error("Error publishing deferrable load: %s", err)
            # Release index on error
            if 'trip_id' in locals() and trip_id in self._index_map:
                await self.async_release_trip_index(trip_id)
            return False
    
    async def async_remove_deferrable_load(self, trip_id: str) -> bool:
        """Remove a trip from deferrable load configuration."""
        try:
            if trip_id not in self._index_map:
                _LOGGER.warning(
                    "Attempted to remove unknown trip %s",
                    trip_id
                )
                return False
            
            emhass_index = self._index_map[trip_id]
            config_sensor_id = self._get_config_sensor_id(emhass_index)
            
            # Clear the configuration
            await self.hass.states.async_set(
                config_sensor_id,
                "idle",
                {}
            )
            
            # Release the index
            await self.async_release_trip_index(trip_id)
            
            _LOGGER.info(
                "Removed deferrable load for trip %s (index %d)",
                trip_id,
                emhass_index
            )
            
            return True
            
        except Exception as err:
            _LOGGER.error("Error removing deferrable load: %s", err)
            return False
    
    async def async_update_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """Update existing deferrable load with new parameters."""
        return await self.async_publish_deferrable_load(trip)
    
    async def async_publish_all_deferrable_loads(self, trips: List[Dict[str, Any]]) -> bool:
        """
        Publish multiple trips, each with its own index.
        
        Returns:
            True if all trips published successfully, False otherwise
        """
        success_count = 0
        
        for trip in trips:
            if await self.async_publish_deferrable_load(trip):
                success_count += 1
        
        _LOGGER.info(
            "Published %d/%d deferrable loads for vehicle %s",
            success_count,
            len(trips),
            self.vehicle_id
        )
        
        return success_count == len(trips)
    
    def get_assigned_index(self, trip_id: str) -> Optional[int]:
        """Get the EMHASS index assigned to a trip."""
        return self._index_map.get(trip_id)
    
    def get_all_assigned_indices(self) -> Dict[str, int]:
        """Get all trip-index mappings."""
        return self._index_map.copy()