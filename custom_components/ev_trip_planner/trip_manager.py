"""Trip Manager for EV Trip Planner.

Handles storage and management of recurring and punctual trips.
"""

from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    SIGNAL_TRIPS_UPDATED,
    TRIP_STATUS_CANCELLED,
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_PENDING,
    TRIP_TYPE_PUNCTUAL,
    TRIP_TYPE_RECURRING,
)

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1


class TripManager:
    """Manage trips for a vehicle."""
    
    # Class constants
    _DAY_MAP = {
        "lunes": 0,
        "martes": 1,
        "miercoles": 2,
        "jueves": 3,
        "viernes": 4,
        "sabado": 5,
        "domingo": 6,
    }

    def __init__(self, hass: HomeAssistant, vehicle_id: str) -> None:
        """Initialize trip manager.

        Args:
            hass: Home Assistant instance
            vehicle_id: Unique identifier for the vehicle
        """
        self.hass = hass
        self.vehicle_id = vehicle_id
        # Use Storage API instead of input_text
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{vehicle_id}.trips")
        _LOGGER.debug("Initialized TripManager for vehicle: %s", vehicle_id)

    async def async_setup(self) -> None:
        """Set up trip manager and load existing trips."""
        # Load existing trips from storage
        stored_data = await self._store.async_load()
        if stored_data is None:
            # Initialize empty storage
            await self._store.async_save([])
            _LOGGER.info("Initialized empty trip storage for vehicle: %s", self.vehicle_id)
        else:
            _LOGGER.info("Loaded %d trips for vehicle: %s", len(stored_data), self.vehicle_id)

    async def _async_load_trips(self) -> list[dict[str, Any]]:
        """Load trips from storage.

        Returns:
            List of trip dictionaries
        """
        trips = await self._store.async_load()
        if trips is None:
            _LOGGER.debug("No trips found for vehicle %s", self.vehicle_id)
            return []
        
        _LOGGER.debug("Loaded %d trips for vehicle %s", len(trips), self.vehicle_id)
        return trips

    async def _async_save_trips(self, trips: list[dict[str, Any]]) -> None:
        """Save trips to storage.

        Args:
            trips: List of trip dictionaries
        """
        await self._store.async_save(trips)
        _LOGGER.debug("Saved %d trips for vehicle %s", len(trips), self.vehicle_id)
        # Notify listeners (sensors) that trips have changed
        async_dispatcher_send(self.hass, f"{SIGNAL_TRIPS_UPDATED}_{self.vehicle_id}")

    def _generate_trip_id(self, trip_type: str, trip_data: dict[str, Any]) -> str:
        """Generate unique trip ID.

        Args:
            trip_type: Type of trip (recurring or punctual)
            trip_data: Trip data dictionary

        Returns:
            Unique trip ID
        """
        if trip_type == TRIP_TYPE_RECURRING:
            # Format: rec_<dia>_<short_uuid>
            dia = trip_data.get("dia_semana", "unknown")[:3]
            short_id = str(uuid.uuid4())[:8]
            return f"rec_{dia}_{short_id}"
        else:
            # Format: pun_<fecha>_<short_uuid>
            datetime_str = trip_data.get("datetime", "")
            fecha = datetime_str[:10].replace("-", "") if datetime_str else "unknown"
            short_id = str(uuid.uuid4())[:8]
            return f"pun_{fecha}_{short_id}"

    async def async_add_recurring_trip(
        self,
        dia_semana: str,
        hora: str,
        km: float,
        kwh: float,
        descripcion: str,
    ) -> str:
        """Add a recurring trip.

        Args:
            dia_semana: Day of week (lunes-domingo)
            hora: Time in HH:MM format
            km: Distance in kilometers
            kwh: Energy needed in kWh
            descripcion: Trip description

        Returns:
            Trip ID

        Raises:
            ValueError: If input validation fails
        """
        # Validate inputs
        if dia_semana not in [
            "lunes",
            "martes",
            "miercoles",
            "jueves",
            "viernes",
            "sabado",
            "domingo",
        ]:
            raise ValueError(f"Invalid day of week: {dia_semana}")

        trip_data = {
            "tipo": TRIP_TYPE_RECURRING,
            "dia_semana": dia_semana,
            "hora": hora,
            "km": km,
            "kwh": kwh,
            "descripcion": descripcion,
            "activo": True,
            "creado": datetime.now().isoformat(),
        }

        trip_id = self._generate_trip_id(TRIP_TYPE_RECURRING, trip_data)
        trip_data["id"] = trip_id

        trips = await self._async_load_trips()
        trips.append(trip_data)
        await self._async_save_trips(trips)

        _LOGGER.info("Added recurring trip: %s (%s)", trip_id, descripcion)
        return trip_id

    async def async_add_punctual_trip(
        self,
        datetime_str: str,
        km: float,
        kwh: float,
        descripcion: str,
    ) -> str:
        """Add a punctual (one-time) trip.

        Args:
            datetime_str: Datetime in ISO format (YYYY-MM-DDTHH:MM:SS)
            km: Distance in kilometers
            kwh: Energy needed in kWh
            descripcion: Trip description

        Returns:
            Trip ID

        Raises:
            ValueError: If datetime format is invalid
        """
        # Validate datetime format
        try:
            datetime.fromisoformat(datetime_str)
        except ValueError as err:
            raise ValueError(f"Invalid datetime format: {datetime_str}") from err

        trip_data = {
            "tipo": TRIP_TYPE_PUNCTUAL,
            "datetime": datetime_str,
            "km": km,
            "kwh": kwh,
            "descripcion": descripcion,
            "estado": TRIP_STATUS_PENDING,
            "creado": datetime.now().isoformat(),
        }

        trip_id = self._generate_trip_id(TRIP_TYPE_PUNCTUAL, trip_data)
        trip_data["id"] = trip_id

        trips = await self._async_load_trips()
        trips.append(trip_data)
        await self._async_save_trips(trips)

        _LOGGER.info("Added punctual trip: %s (%s)", trip_id, descripcion)
        return trip_id

    async def async_get_trip(self, trip_id: str) -> dict[str, Any] | None:
        """Get a specific trip by ID.

        Args:
            trip_id: Trip identifier

        Returns:
            Trip dictionary or None if not found
        """
        trips = await self._async_load_trips()
        for trip in trips:
            if trip.get("id") == trip_id:
                return trip
        return None

    async def async_get_all_trips(self) -> list[dict[str, Any]]:
        """Get all trips.

        Returns:
            List of all trip dictionaries
        """
        return await self._async_load_trips()

    async def async_get_recurring_trips(self) -> list[dict[str, Any]]:
        """Get all recurring trips.

        Returns:
            List of recurring trip dictionaries
        """
        trips = await self._async_load_trips()
        return [t for t in trips if t.get("tipo") == TRIP_TYPE_RECURRING]

    async def async_get_punctual_trips(self) -> list[dict[str, Any]]:
        """Get all punctual trips.

        Returns:
            List of punctual trip dictionaries
        """
        trips = await self._async_load_trips()
        return [t for t in trips if t.get("tipo") == TRIP_TYPE_PUNCTUAL]

    async def async_update_trip(self, trip_id: str, updates: dict[str, Any]) -> bool:
        """Update a trip.

        Args:
            trip_id: Trip identifier
            updates: Dictionary of fields to update

        Returns:
            True if trip was found and updated, False otherwise
        """
        trips = await self._async_load_trips()
        for trip in trips:
            if trip.get("id") == trip_id:
                trip.update(updates)
                await self._async_save_trips(trips)
                _LOGGER.info("Updated trip: %s", trip_id)
                return True

        _LOGGER.warning("Trip not found for update: %s", trip_id)
        return False

    async def async_delete_trip(self, trip_id: str) -> bool:
        """Delete a trip.

        Args:
            trip_id: Trip identifier

        Returns:
            True if trip was found and deleted, False otherwise
        """
        trips = await self._async_load_trips()
        initial_count = len(trips)
        trips = [t for t in trips if t.get("id") != trip_id]

        if len(trips) < initial_count:
            await self._async_save_trips(trips)
            _LOGGER.info("Deleted trip: %s", trip_id)
            return True

        _LOGGER.warning("Trip not found for deletion: %s", trip_id)
        return False

    async def async_pause_recurring_trip(self, trip_id: str) -> bool:
        """Pause a recurring trip (set activo=False).

        Args:
            trip_id: Trip identifier

        Returns:
            True if trip was found and paused, False otherwise
        """
        trip = await self.async_get_trip(trip_id)
        if trip and trip.get("tipo") == TRIP_TYPE_RECURRING:
            return await self.async_update_trip(trip_id, {"activo": False})

        _LOGGER.warning("Recurring trip not found for pause: %s", trip_id)
        return False

    async def async_resume_recurring_trip(self, trip_id: str) -> bool:
        """Resume a paused recurring trip (set activo=True).

        Args:
            trip_id: Trip identifier

        Returns:
            True if trip was found and resumed, False otherwise
        """
        trip = await self.async_get_trip(trip_id)
        if trip and trip.get("tipo") == TRIP_TYPE_RECURRING:
            return await self.async_update_trip(trip_id, {"activo": True})

        _LOGGER.warning("Recurring trip not found for resume: %s", trip_id)
        return False

    async def async_complete_punctual_trip(self, trip_id: str) -> bool:
        """Mark a punctual trip as completed.

        Args:
            trip_id: Trip identifier

        Returns:
            True if trip was found and completed, False otherwise
        """
        trip = await self.async_get_trip(trip_id)
        if trip and trip.get("tipo") == TRIP_TYPE_PUNCTUAL:
            return await self.async_update_trip(
                trip_id, {"estado": TRIP_STATUS_COMPLETED}
            )

        _LOGGER.warning("Punctual trip not found for completion: %s", trip_id)
        return False

    async def async_cancel_punctual_trip(self, trip_id: str) -> bool:
        """Cancel a punctual trip.

        Args:
            trip_id: Trip identifier

        Returns:
            True if trip was found and cancelled, False otherwise
        """
        trip = await self.async_get_trip(trip_id)
        if trip and trip.get("tipo") == TRIP_TYPE_PUNCTUAL:
            return await self.async_update_trip(
                trip_id, {"estado": TRIP_STATUS_CANCELLED}
            )

        _LOGGER.warning("Punctual trip not found for cancellation: %s", trip_id)
        return False

    def _ensure_timezone_aware(self, dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware using HA's local timezone.
        
        Args:
            dt: Datetime object (may be naive or aware)
            
        Returns:
            Timezone-aware datetime object
        """
        if dt.tzinfo is None:
            return dt_util.as_local(dt)
        return dt

    def _parse_hour_minute(self, time_str: str) -> tuple[int, int] | None:
        """Parse hour and minute from HH:MM format.
        
        Args:
            time_str: Time string in HH:MM format
            
        Returns:
            Tuple of (hour, minute) or None if invalid
        """
        try:
            hour, minute = map(int, time_str.split(":"))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour, minute
            _LOGGER.warning("Hour/minute out of range: %s", time_str)
            return None
        except (ValueError, AttributeError):
            _LOGGER.warning("Invalid hour format: %s", time_str)
            return None

    async def async_expand_recurring_trips(self, days: int = 7) -> List[Dict]:
        """Expand recurring trips into concrete instances for the next N days.

        Args:
            days: Number of days to expand (default: 7)

        Returns:
            List of expanded trip instances with concrete datetimes
        """
        try:
            expanded_trips = []
            today = dt_util.now().date()
            
            recurring_trips = await self.async_get_recurring_trips()
            
            _LOGGER.debug("Expanding %d recurring trips for next %d days",
                         len(recurring_trips), days)
            
            for trip in recurring_trips:
                if not trip.get("activo", True):
                    _LOGGER.debug("Skipping inactive trip: %s", trip.get("descripcion"))
                    continue
                    
                dia_semana = trip.get("dia_semana", "")
                hora = trip.get("hora", "00:00")
                
                if dia_semana not in self._DAY_MAP:
                    _LOGGER.warning("Invalid day of week in trip: %s", dia_semana)
                    continue
                    
                target_weekday = self._DAY_MAP[dia_semana]
                
                # Parse hour using helper
                time_parsed = self._parse_hour_minute(hora)
                if time_parsed is None:
                    continue
                hour, minute = time_parsed
                
                # Generate instances for the next 'days' days
                for i in range(days):
                    current_date = today + timedelta(days=i)
                    
                    # Check if this date matches the target weekday
                    if current_date.weekday() == target_weekday:
                        # Combine date with time
                        trip_datetime = datetime.combine(
                            current_date,
                            datetime.min.time().replace(hour=hour, minute=minute)
                        )
                        
                        # Localize the datetime using helper
                        trip_datetime = self._ensure_timezone_aware(trip_datetime)
                        
                        expanded_trip = {
                            "descripcion": trip.get("descripcion", "Viaje recurrente"),
                            "datetime": trip_datetime,
                            "kwh": trip.get("kwh", 0.0),
                            "source": "recurring",
                        }
                        expanded_trips.append(expanded_trip)
                        
                        _LOGGER.debug("Expanded trip: %s at %s (weekday %d == target %d)",
                                     trip.get("descripcion"), trip_datetime,
                                     current_date.weekday(), target_weekday)
            
            _LOGGER.debug("Expanded %d recurring trips into %d instances",
                         len(recurring_trips), len(expanded_trips))
            return expanded_trips
            
        except Exception as err:
            _LOGGER.error("Error expanding recurring trips: %s", err)
            return []

    async def async_get_next_trip(self) -> Optional[Dict]:
        """Get the next upcoming trip.

        Returns:
            Dictionary with trip details or None if no trips found
        """
        try:
            all_trips = await self.async_get_all_trips_expanded()
            
            if not all_trips:
                _LOGGER.debug("No trips found for next trip calculation")
                return None
            
            # Sort by datetime (ensure all datetimes are comparable)
            all_trips.sort(key=lambda x: x.get("datetime"))
            
            now = dt_util.now()
            _LOGGER.debug("Current time: %s", now)
            _LOGGER.debug("Total trips to check: %d", len(all_trips))
            
            # Debug: print all trips
            for i, trip in enumerate(all_trips):
                _LOGGER.debug("Trip %d: %s at %s (type: %s)",
                             i, trip.get("descripcion"), trip.get("datetime"),
                             type(trip.get("datetime")))
            
            # Find first trip that is in the future
            for trip in all_trips:
                trip_datetime = trip.get("datetime")
                if trip_datetime:
                    _LOGGER.debug("Checking trip: %s at %s (now: %s, comparison: %s)",
                                 trip.get("descripcion"), trip_datetime, now,
                                 trip_datetime > now)
                    if trip_datetime > now:
                        _LOGGER.debug("Next trip found: %s at %s",
                                     trip.get("descripcion"), trip_datetime)
                        return trip
            
            _LOGGER.debug("No future trips found")
            return None
            
        except Exception as err:
            _LOGGER.error("Error getting next trip: %s", err)
            return None

    async def async_get_kwh_needed_today(self) -> float:
        """Calculate total kWh needed for all trips today.

        Returns:
            Sum of kWh for all trips scheduled today
        """
        try:
            all_trips = await self.async_get_all_trips_expanded()
            
            if not all_trips:
                _LOGGER.debug("No trips found for kWh calculation")
                return 0.0
            
            # Get today in local timezone
            now = dt_util.now()
            today = now.date()
            
            total_kwh = 0.0
            trips_found = 0
            
            _LOGGER.debug("Calculating kWh for today (%s) from %d trips (now: %s)",
                         today, len(all_trips), now)
            
            for trip in all_trips:
                try:
                    trip_datetime = trip.get("datetime")
                    if trip_datetime:
                        # Convert to local timezone for consistent date comparison
                        if hasattr(trip_datetime, 'astimezone'):
                            trip_local = trip_datetime.astimezone(now.tzinfo)
                        else:
                            trip_local = dt_util.as_local(trip_datetime)
                        
                        trip_date = trip_local.date()
                        _LOGGER.debug("Checking trip: %s at %s (local: %s, date: %s)",
                                     trip.get("descripcion"), trip_datetime, trip_local, trip_date)
                        
                        if trip_date == today:
                            kwh = float(trip.get("kwh", 0.0))
                            total_kwh += kwh
                            trips_found += 1
                            _LOGGER.debug("Added trip %s: %.2f kWh (total: %.2f)",
                                         trip.get("descripcion"), kwh, total_kwh)
                        else:
                            _LOGGER.debug("Skipping trip %s: date %s != today %s",
                                         trip.get("descripcion"), trip_date, today)
                except (ValueError, TypeError, AttributeError) as e:
                    _LOGGER.warning("Invalid datetime or kwh in trip %s: %s", trip, e)
                    continue
            
            _LOGGER.debug("Total kWh needed today: %.2f (%d trips)", total_kwh, trips_found)
            return total_kwh
            
        except Exception as err:
            _LOGGER.error("Error calculating kWh needed today: %s", err)
            return 0.0

    async def async_get_hours_needed_today(self, charging_power_kw: float = 3.6) -> int:
        """Calculate hours needed to charge for today's trips.

        Args:
            charging_power_kw: Charging power in kW (default: 3.6)

        Returns:
            Hours needed (rounded up)
        """
        try:
            if charging_power_kw <= 0:
                _LOGGER.warning("Invalid charging power: %s", charging_power_kw)
                return 0
            
            kwh_needed = await self.async_get_kwh_needed_today()
            
            if kwh_needed <= 0:
                return 0
            
            hours = math.ceil(kwh_needed / charging_power_kw)
            
            _LOGGER.debug("Hours needed today: %d (kwh: %.2f, power: %.2f kW)",
                         hours, kwh_needed, charging_power_kw)
            return hours
            
        except Exception as err:
            _LOGGER.error("Error calculating hours needed today: %s", err)
            return 0

    async def async_get_all_trips_expanded(self) -> List[Dict]:
        """Get all trips (recurring expanded + punctual) sorted by datetime.

        Returns:
            Combined and sorted list of all trip instances
        """
        try:
            # Get expanded recurring trips
            recurring_expanded = await self.async_expand_recurring_trips()
            
            # Get punctual trips
            punctual_trips = await self.async_get_punctual_trips()
            
            # Convert punctual trips to same format
            punctual_formatted = []
            for trip in punctual_trips:
                if trip.get("estado") == TRIP_STATUS_PENDING:
                    # Parse datetime and ensure it's timezone-aware
                    datetime_str = trip.get("datetime", "")
                    if datetime_str:
                        trip_datetime = dt_util.parse_datetime(datetime_str)
                        if trip_datetime:
                            # Ensure datetime is timezone-aware
                            trip_datetime = dt_util.as_local(trip_datetime)
                            
                            punctual_formatted.append({
                                "descripcion": trip.get("descripcion", "Viaje puntual"),
                                "datetime": trip_datetime,
                                "kwh": trip.get("kwh", 0.0),
                                "source": "punctual",
                            })
            
            # Combine all trips
            all_trips = recurring_expanded + punctual_formatted
            
            # Sort by datetime (all datetimes are now timezone-aware)
            all_trips.sort(key=lambda x: x.get("datetime"))
            
            _LOGGER.debug("Total trips expanded: %d", len(all_trips))
            return all_trips
            
        except Exception as err:
            _LOGGER.error("Error getting all trips expanded: %s", err)
            return []
