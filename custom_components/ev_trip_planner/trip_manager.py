"""Trip Manager for EV Trip Planner.

Handles storage and management of recurring and punctual trips.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

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
