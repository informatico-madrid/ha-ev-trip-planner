"""Service handlers for EV Trip Planner integration.

Extracted from __init__.py as part of Phase 4 refactoring.
Contains all service handlers and helper functions for trip management services.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .dashboard import DashboardImportResult
from .trip_manager import TripManager

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Type alias for coordinator
CoordinatorType = DataUpdateCoordinator[dict[str, Any]]

_LOGGER = logging.getLogger(__name__)


def register_services(hass: HomeAssistant) -> None:
    """Registrar servicios del dominio ev_trip_planner."""

    async def handle_add_recurring(call: ServiceCall) -> None:
        """Handle adding a recurring trip."""
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await mgr.async_add_recurring_trip(
            dia_semana=data["dia_semana"],
            hora=data["hora"],
            km=float(data["km"]),
            kwh=float(data["kwh"]),
            descripcion=str(data.get("descripcion", "")),
        )
        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
            await coordinator.async_refresh_trips()

    async def handle_add_punctual(call: ServiceCall) -> None:
        """Handle adding a punctual trip."""
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await mgr.async_add_punctual_trip(
            datetime_str=data["datetime"],
            km=float(data["km"]),
            kwh=float(data["kwh"]),
            descripcion=str(data.get("descripcion", "")),
        )
        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
            await coordinator.async_refresh_trips()

    async def handle_trip_create(call: ServiceCall) -> None:
        """Handle creating a trip (either recurring or punctual).

        This unified service accepts a 'type' parameter to determine whether
        to create a recurring trip (recurrente) or a punctual trip (puntual).
        Thin facade - delegates to trip_manager and coordinator.
        """
        data = call.data
        vehicle_id = data["vehicle_id"]
        trip_type = data.get("type", data.get("trip_type", "recurrente"))
        mgr = await _get_manager(hass, vehicle_id)  # Raises if vehicle not found

        if trip_type == "recurrente":
            # Create recurring trip
            # Support both Spanish and English field names
            dia_semana = data.get("dia_semana") or data.get("day_of_week")
            hora = data.get("hora") or data.get("time")
            descripcion = data.get("descripcion") or data.get("description", "")
            await mgr.async_add_recurring_trip(
                dia_semana=dia_semana,
                hora=hora,
                km=float(data["km"]),
                kwh=float(data["kwh"]),
                descripcion=descripcion,
            )
            _LOGGER.info(
                "Created recurring trip for vehicle %s: %s at %s, %s km",
                vehicle_id,
                dia_semana,
                hora,
                data["km"],
            )
        elif trip_type == "puntual":
            # Create punctual trip
            datetime_str = data.get("datetime")
            descripcion = data.get("descripcion") or data.get("description", "")
            await mgr.async_add_punctual_trip(
                datetime_str=datetime_str,
                km=float(data["km"]),
                kwh=float(data["kwh"]),
                descripcion=descripcion,
            )
            _LOGGER.info(
                "Created punctual trip for vehicle %s: %s, %s km",
                vehicle_id,
                datetime_str,
                data["km"],
            )
        else:
            _LOGGER.error(
                "Invalid trip type '%s' for vehicle %s. Must be 'recurrente' or 'puntual'",
                trip_type,
                vehicle_id,
            )
            return

        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
            await coordinator.async_refresh_trips()

    async def handle_trip_update(call: ServiceCall) -> None:
        """Handle updating a trip.

        This unified service accepts:
        - vehicle_id: The vehicle to update the trip for
        - trip_id: The ID of the trip to update
        - type: 'recurrente' or 'puntual'
        - Recurring fields: dia_semana, hora
        - Punctual fields: datetime
        - Common fields: km, kwh, descripcion/description
        """
        data = call.data
        vehicle_id = data["vehicle_id"]
        trip_id = str(data["trip_id"])
        trip_type = data.get("type", "recurrente")

        # Support both direct fields and updates object for backward compatibility
        if "updates" in data:
            # Old format: {vehicle_id, trip_id, updates: {...}}
            updates = dict(data["updates"])
        else:
            # New unified format: fields directly in request
            updates = {}
            if "dia_semana" in data:
                updates["dia_semana"] = data["dia_semana"]
            if "day_of_week" in data:
                updates["dia_semana"] = data["day_of_week"]
            if "hora" in data:
                updates["hora"] = data["hora"]
            if "time" in data:
                updates["hora"] = data["time"]
            if "datetime" in data:
                updates["datetime"] = data["datetime"]
            if "km" in data:
                updates["km"] = float(data["km"])
            if "kwh" in data:
                updates["kwh"] = float(data["kwh"])
            if "descripcion" in data:
                updates["descripcion"] = str(data["descripcion"])
            if "description" in data:
                updates["descripcion"] = str(data["description"])

        _LOGGER.info(
            "Updating trip %s for vehicle %s with updates: %s",
            trip_id,
            vehicle_id,
            updates,
        )

        # Find config entry to get entry_id
        entry = _find_entry_by_vehicle(hass, vehicle_id)
        if not entry:
            _LOGGER.error("Config entry not found for vehicle %s", vehicle_id)
            return

        mgr = await _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr.async_update_trip(trip_id, updates)

        # Get the updated trip and update sensor
        try:
            from .sensor import async_update_trip_sensor

            trip_type = "recurrente" if updates.get("dia_semana") else "puntual"
            if trip_type == "recurrente":
                trips = await mgr.async_get_recurring_trips()
            else:
                trips = await mgr.async_get_punctual_trips()

            for trip in trips:
                if str(trip.get("id")) == trip_id:
                    trip_data = {**trip, "id": trip_id}
                    await async_update_trip_sensor(hass, entry.entry_id, trip_data)
                    break
        except Exception as err:
            _LOGGER.warning("Failed to update trip sensor: %s", err)

        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
            await coordinator.async_refresh_trips()

    async def handle_edit_trip(call: ServiceCall) -> None:
        """Handle editing a trip (deprecated alias for trip_update)."""
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr.async_update_trip(str(data["trip_id"]), dict(data["updates"]))
        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
            await coordinator.async_refresh_trips()

    async def handle_delete_trip(call: ServiceCall) -> None:
        """Handle deleting a trip.

        Thin facade - delegates to trip_manager and coordinator.
        Sensor removal is handled internally by async_delete_trip.
        """
        data = call.data
        vehicle_id = data["vehicle_id"]
        trip_id = str(data["trip_id"])
        mgr = await _get_manager(hass, vehicle_id)  # Raises if vehicle not found
        await _ensure_setup(mgr)

        # Delete the trip (sensor removal handled internally by async_delete_trip)
        await mgr.async_delete_trip(trip_id)

        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
            await coordinator.async_refresh_trips()

    async def handle_pause_recurring(call: ServiceCall) -> None:
        """Handle pausing a recurring trip."""
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr.async_pause_recurring_trip(str(data["trip_id"]))
        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
            await coordinator.async_refresh_trips()

    async def handle_resume_recurring(call: ServiceCall) -> None:
        """Handle resuming a recurring trip."""
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr.async_resume_recurring_trip(str(data["trip_id"]))
        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
            await coordinator.async_refresh_trips()

    async def handle_complete_punctual(call: ServiceCall) -> None:
        """Handle completing a punctual trip."""
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr.async_complete_punctual_trip(str(data["trip_id"]))
        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
            await coordinator.async_refresh_trips()

    async def handle_cancel_punctual(call: ServiceCall) -> None:
        """Handle cancelling a punctual trip."""
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr.async_cancel_punctual_trip(str(data["trip_id"]))
        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
            await coordinator.async_refresh_trips()

    # Registro de servicios (schemas mínimos; validación completa en fases posteriores)
    hass.services.async_register(
        DOMAIN,
        "add_recurring_trip",
        handle_add_recurring,
        schema=vol.Schema(
            {
                vol.Required("vehicle_id"): str,
                vol.Required("dia_semana"): str,
                vol.Required("hora"): str,
                vol.Required("km"): vol.Coerce(float),
                vol.Required("kwh"): vol.Coerce(float),
                vol.Optional("descripcion", default=""): str,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "add_punctual_trip",
        handle_add_punctual,
        schema=vol.Schema(
            {
                vol.Required("vehicle_id"): str,
                vol.Required("datetime"): str,
                vol.Required("km"): vol.Coerce(float),
                vol.Required("kwh"): vol.Coerce(float),
                vol.Optional("descripcion", default=""): str,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "edit_trip",
        handle_edit_trip,
        schema=vol.Schema(
            {
                vol.Required("vehicle_id"): str,
                vol.Required("trip_id"): str,
                vol.Required("updates"): dict,
            }
        ),
    )

    # Schema for trip_update service
    trip_update_schema = vol.Schema(
        {
            vol.Required("vehicle_id"): str,
            vol.Required("trip_id"): str,
            vol.Required("type"): vol.In(["recurrente", "puntual"]),
            # Recurring trip fields
            vol.Optional("dia_semana"): str,
            vol.Optional("day_of_week"): str,  # Alternative name for compatibility
            vol.Optional("hora"): str,
            vol.Optional("time"): str,  # Alternative name for compatibility
            # Punctual trip fields
            vol.Optional("datetime"): str,
            # Common fields
            vol.Optional("km"): vol.Coerce(float),
            vol.Optional("kwh"): vol.Coerce(float),
            vol.Optional("descripcion"): str,
            vol.Optional("description"): str,  # Alternative name for compatibility
        }
    )

    # Register trip_update service
    hass.services.async_register(
        DOMAIN,
        "trip_update",
        handle_trip_update,
        schema=trip_update_schema,
    )

    # Common schema for trip operations
    trip_id_schema = vol.Schema(
        {
            vol.Required("vehicle_id"): str,
            vol.Required("trip_id"): str,
        }
    )

    # Schema for unified trip_create service
    trip_create_schema = vol.Schema(
        {
            vol.Required("vehicle_id"): str,
            vol.Required("type"): vol.In(["recurrente", "puntual"]),
            # Recurring trip fields (required if type == 'recurrente')
            vol.Optional("dia_semana"): str,
            vol.Optional("day_of_week"): str,  # Alternative name for compatibility
            vol.Optional("hora"): str,
            vol.Optional("time"): str,  # Alternative name for compatibility
            # Punctual trip fields (required if type == 'puntual')
            vol.Optional("datetime"): str,
            # Common fields (required for both types)
            vol.Required("km"): vol.Coerce(float),
            vol.Required("kwh"): vol.Coerce(float),
            vol.Optional("descripcion", default=""): str,
            vol.Optional(
                "description", default=""
            ): str,  # Alternative name for compatibility
        }
    )

    # Register trip_create service
    hass.services.async_register(
        DOMAIN,
        "trip_create",
        handle_trip_create,
        schema=trip_create_schema,
    )

    hass.services.async_register(
        DOMAIN,
        "delete_trip",
        handle_delete_trip,
        schema=trip_id_schema,
    )
    hass.services.async_register(
        DOMAIN,
        "pause_recurring_trip",
        handle_pause_recurring,
        schema=trip_id_schema,
    )
    hass.services.async_register(
        DOMAIN,
        "resume_recurring_trip",
        handle_resume_recurring,
        schema=trip_id_schema,
    )
    hass.services.async_register(
        DOMAIN,
        "complete_punctual_trip",
        handle_complete_punctual,
        schema=trip_id_schema,
    )
    hass.services.async_register(
        DOMAIN,
        "cancel_punctual_trip",
        handle_cancel_punctual,
        schema=trip_id_schema,
    )

    async def handle_import_weekly_pattern(call: ServiceCall) -> None:
        """Handle importing a weekly pattern."""
        data = call.data
        mgr = await _get_manager(hass, data["vehicle_id"])
        await _ensure_setup(mgr)

        clear_existing = bool(data.get("clear_existing", True))
        pattern: dict[str, Any] = dict(data["pattern"])

        if clear_existing:
            try:
                existing = await mgr.async_get_recurring_trips()
            except Exception:
                existing = []
            for trip in existing:
                trip_id = str(trip.get("id"))
                if trip_id:
                    await mgr.async_delete_trip(trip_id)

        # Importar nuevos
        for dia, items in pattern.items():
            for item in items or []:
                await mgr.async_add_recurring_trip(
                    dia_semana=str(dia),
                    hora=str(item["hora"]),
                    km=float(item["km"]),
                    kwh=float(item["kwh"]),
                    descripcion=str(item.get("descripcion", "")),
                )

    async def handle_trip_list(call: ServiceCall) -> dict[str, Any]:
        """Handle listing all trips for a vehicle.

        Returns both recurring and punctual trips in a single list.

        Returns a dict with vehicle_id, trips, and total count.
        """
        _LOGGER.warning("=== trip_list SERVICE HANDLER CALLED ===")
        _LOGGER.warning("=== call.data: %s", call.data)
        data = call.data
        vehicle_id = data.get("vehicle_id", "unknown")
        _LOGGER.warning("=== trip_list SERVICE CALLED === vehicle: %s", vehicle_id)

        mgr = await _get_manager(hass, vehicle_id)
        # _get_manager already calls async_setup which loads trips from storage
        _LOGGER.warning("=== _get_manager returned manager ===")
        _LOGGER.warning(
            "=== Before async_get_recurring_trips - mgr._recurring_trips: %d",
            len(mgr._recurring_trips),
        )
        _LOGGER.warning(
            "=== Before async_get_punctual_trips - mgr._punctual_trips: %d",
            len(mgr._punctual_trips),
        )

        try:
            _LOGGER.warning("Getting recurring trips for %s", vehicle_id)
            recurring_trips = await mgr.async_get_recurring_trips()
            _LOGGER.warning("Got %d recurring trips", len(recurring_trips))

            _LOGGER.warning("Getting punctual trips for %s", vehicle_id)
            punctual_trips = await mgr.async_get_punctual_trips()
            _LOGGER.warning("Got %d punctual trips", len(punctual_trips))

            _LOGGER.warning(
                "Retrieved %d recurring trips and %d punctual trips for vehicle %s",
                len(recurring_trips),
                len(punctual_trips),
                vehicle_id,
            )

            # Debug: Log each recurring trip
            for i, trip in enumerate(recurring_trips):
                _LOGGER.warning(
                    "Recurring trip %d: id=%s, tipo=%s, activo=%s",
                    i,
                    trip.get("id"),
                    trip.get("tipo"),
                    trip.get("activo"),
                )

            # Debug: Log each punctual trip
            for i, trip in enumerate(punctual_trips):
                _LOGGER.warning(
                    "Punctual trip %d: id=%s, tipo=%s, estado=%s",
                    i,
                    trip.get("id"),
                    trip.get("tipo"),
                    trip.get("estado"),
                )

            # Combine trips for dashboard display
            # Return ONLY the data, no context wrapper
            result = {
                "vehicle_id": vehicle_id,
                "recurring_trips": recurring_trips,
                "punctual_trips": punctual_trips,
                "total_trips": len(recurring_trips) + len(punctual_trips),
            }
            _LOGGER.warning("=== trip_list result ===")
            _LOGGER.warning("recurring_trips count: %d", len(recurring_trips))
            _LOGGER.warning("punctual_trips count: %d", len(punctual_trips))
            _LOGGER.warning("total_trips: %d", result["total_trips"])
            if recurring_trips:
                _LOGGER.warning("First recurring trip: %s", recurring_trips[0])
            if punctual_trips:
                _LOGGER.warning("First punctual trip: %s", punctual_trips[0])

            # Return the result - MUST return explicitly
            return result
        except Exception as err:
            _LOGGER.error(
                "Error listing trips for vehicle %s: %s", vehicle_id, err, exc_info=True
            )
            return {
                "vehicle_id": vehicle_id,
                "recurring_trips": [],
                "punctual_trips": [],
                "total_trips": 0,
                "error": str(err),
            }

    hass.services.async_register(
        DOMAIN,
        "import_from_weekly_pattern",
        handle_import_weekly_pattern,
        schema=vol.Schema(
            {
                vol.Required("vehicle_id"): str,
                vol.Required("pattern"): dict,
                vol.Optional("clear_existing", default=True): bool,
            }
        ),
    )

    # Schema for trip_list service
    trip_list_schema = vol.Schema(
        {
            vol.Required("vehicle_id"): str,
        }
    )

    # Register trip_list service
    hass.services.async_register(
        DOMAIN,
        "trip_list",
        handle_trip_list,
        schema=trip_list_schema,
        supports_response=SupportsResponse.ONLY,
    )

    # Schema for trip_get service - get single trip by ID
    trip_get_schema = vol.Schema(
        {
            vol.Required("vehicle_id"): str,
            vol.Required("trip_id"): str,
        }
    )

    async def handle_trip_get(call: ServiceCall) -> dict[str, Any]:
        """Handle getting a single trip by ID.

        Returns the trip data for a specific trip_id.
        """
        _LOGGER.warning("=== trip_get SERVICE HANDLER CALLED ===")
        _LOGGER.warning("=== call.data: %s", call.data)
        data = call.data
        vehicle_id = data.get("vehicle_id", "unknown")
        trip_id = data.get("trip_id", "unknown")
        _LOGGER.warning(
            "=== trip_get SERVICE CALLED === vehicle: %s, trip_id: %s",
            vehicle_id,
            trip_id,
        )

        mgr = await _get_manager(hass, vehicle_id)
        _LOGGER.warning("=== _get_manager returned manager ===")

        try:
            # Get all trips and find the one with matching ID
            _LOGGER.warning("Getting all trips to find trip_id: %s", trip_id)
            recurring_trips = await mgr.async_get_recurring_trips()
            punctual_trips = await mgr.async_get_punctual_trips()

            _LOGGER.warning(
                "Found %d recurring and %d punctual trips",
                len(recurring_trips),
                len(punctual_trips),
            )

            # Search for the trip in both lists
            all_trips = [
                *recurring_trips,
                *punctual_trips,
            ]

            _LOGGER.warning(
                "Searching through %d trips for ID: %s", len(all_trips), trip_id
            )
            trip_found = None
            for trip in all_trips:
                if str(trip.get("id")) == trip_id:
                    trip_found = trip
                    _LOGGER.warning("Found trip: %s", trip)
                    break

            if trip_found:
                _LOGGER.warning("=== trip_get SUCCESS - Found trip: %s ===", trip_found)
                return {
                    "vehicle_id": vehicle_id,
                    "trip": trip_found,
                    "found": True,
                }
            else:
                _LOGGER.warning("=== trip_get NOT FOUND - trip_id: %s ===", trip_id)
                return {
                    "vehicle_id": vehicle_id,
                    "trip": None,
                    "found": False,
                    "error": f"Trip with ID {trip_id} not found",
                }
        except Exception as err:
            _LOGGER.error(
                "Error getting trip %s for vehicle %s: %s",
                trip_id,
                vehicle_id,
                err,
                exc_info=True,
            )
            return {
                "vehicle_id": vehicle_id,
                "trip": None,
                "found": False,
                "error": str(err),
            }

    # Register trip_get service
    hass.services.async_register(
        DOMAIN,
        "trip_get",
        handle_trip_get,
        schema=trip_get_schema,
        supports_response=SupportsResponse.ONLY,
    )


# Helper functions with proper type hints
def _find_entry_by_vehicle(hass: HomeAssistant, vehicle_id: str):
    """Find config entry by vehicle name (case-insensitive).

    Matches by comparing vehicle_name (normalized with underscores) against vehicle_id.
    Handles both 'Test Vehicle' -> 'test_vehicle' and 'test_vehicle' -> 'test_vehicle' formats.
    """
    normalized_vehicle_id = vehicle_id.lower()
    for e in hass.config_entries.async_entries(DOMAIN):
        if e.data is None:
            _LOGGER.warning(
                "Entry %s has None data, skipping in _find_entry_by_vehicle",
                e.entry_id,
            )
            continue
        entry_vehicle_name = e.data.get("vehicle_name", "")
        # Normalize entry_vehicle_name the same way as in async_setup_entry
        normalized_entry_name = entry_vehicle_name.lower().replace(" ", "_")
        if normalized_entry_name == normalized_vehicle_id:
            return e
    return None


async def _get_manager(hass: HomeAssistant, vehicle_id: str) -> TripManager:
    """Get or create TripManager for vehicle."""
    _LOGGER.info("=== _get_manager START - vehicle_id: %s ===", vehicle_id)
    entry = _find_entry_by_vehicle(hass, vehicle_id)
    if not entry:
        _LOGGER.error(
            "=== _get_manager ERROR - Vehicle %s not found in config entries ===",
            vehicle_id,
        )
        raise ValueError(f"Vehicle {vehicle_id} not found in config entries")
    _LOGGER.info(
        "=== _get_manager - Found entry: %s, entry_id: %s ===",
        entry.unique_id,
        entry.entry_id,
    )

    # Use entry.runtime_data set by __init__.py::async_setup_entry
    runtime_data = entry.runtime_data
    _LOGGER.info("=== _get_manager - runtime_data: %s ===", runtime_data)

    # Retrieve trip_manager from entry.runtime_data
    trip_manager = runtime_data.trip_manager
    _LOGGER.info(
        "=== _get_manager - trip_manager from runtime_data: %s ===", trip_manager
    )

    # If manager not found in runtime storage, create new one and load from HA storage
    if not trip_manager:
        _LOGGER.info(
            "=== _get_manager - Creating new TripManager for vehicle %s ===", vehicle_id
        )
        trip_manager = TripManager(hass, vehicle_id)
        _LOGGER.info(
            "=== _get_manager - Before async_setup - trips: recurring=%d, punctual=%d ===",
            len(trip_manager._recurring_trips),
            len(trip_manager._punctual_trips),
        )

        # Load trips from HA storage
        try:
            _LOGGER.info(
                "=== _get_manager - Calling trip_manager.async_setup() ==="
            )
            await trip_manager.async_setup()
            _LOGGER.info(
                "=== _get_manager - After async_setup - trips: recurring=%d, punctual=%d ===",
                len(trip_manager._recurring_trips),
                len(trip_manager._punctual_trips),
            )
        except Exception as setup_err:
            _LOGGER.error(
                "=== _get_manager - Error setting up manager for %s: %s ===",
                vehicle_id,
                setup_err,
                exc_info=True,
            )

        _LOGGER.info(
            "=== _get_manager - Manager created and set up for %s ===", vehicle_id
        )
        _LOGGER.info(
            "=== _get_manager - Trips loaded: %d recurring, %d punctual ===",
            len(trip_manager._recurring_trips),
            len(trip_manager._punctual_trips),
        )
    else:
        _LOGGER.info(
            "=== _get_manager - Manager already exists for %s, trips: %d recurring, %d punctual ===",
            vehicle_id,
            len(trip_manager._recurring_trips),
            len(trip_manager._punctual_trips),
        )

    _LOGGER.info(
        "=== _get_manager END - returning manager for vehicle %s ===", vehicle_id
    )
    return trip_manager


async def _ensure_setup(mgr: TripManager) -> None:
    """Ensure TripManager is set up before operations."""
    # Check if manager needs setup - call async_setup if not already done
    try:
        await mgr.async_setup()
    except Exception as err:
        _LOGGER.debug("TripManager async_setup raised (may already be set up): %s", err)


@callback
def _get_coordinator(
    hass: HomeAssistant,
    vehicle_id: str,
) -> Optional[CoordinatorType]:
    """Get coordinator for vehicle."""
    entry = _find_entry_by_vehicle(hass, vehicle_id)
    if not entry:
        return None
    # Use entry.runtime_data set by __init__.py::async_setup_entry
    return entry.runtime_data.coordinator if entry.runtime_data else None


async def create_dashboard_input_helpers(
    hass: HomeAssistant,
    vehicle_id: str,
) -> DashboardImportResult:
    """Create input helpers for dashboard CRUD forms.

    Creates the required input entities that the dashboard template
    uses for creating and editing trips.

    Args:
        hass: The Home Assistant instance.
        vehicle_id: Unique identifier for the vehicle.

    Returns:
        DashboardImportResult with success status.
    """
    _LOGGER.info("Creating input helpers for dashboard: %s", vehicle_id)

    try:
        # Create input_select for day of week (recurring trips)
        day_options = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        try:
            await hass.services.async_call(
                "input_select",
                "create",
                {
                    "name": f"{vehicle_id} - Trip Day",
                    "options": day_options,
                    "icon": "mdi:calendar-week",
                },
            )
            _LOGGER.debug("Created input_select for day: %s_trip_day", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input select may already exist: %s", e)

        # Create input_datetime for recurring trip time
        try:
            await hass.services.async_call(
                "input_datetime",
                "create",
                {
                    "name": f"{vehicle_id} - Trip Time",
                    "has_date": False,
                    "has_time": True,
                    "icon": "mdi:clock",
                },
            )
            _LOGGER.debug("Created input_datetime for time: %s_trip_time", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input datetime may already exist: %s", e)

        # Create input_number for recurring trip km
        try:
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "name": f"{vehicle_id} - Trip km",
                    "min": 0,
                    "max": 1000,
                    "unit_of_measurement": "km",
                    "icon": "mdi:map-marker-distance",
                },
            )
            _LOGGER.debug("Created input_number for km: %s_trip_km", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input number may already exist: %s", e)

        # Create input_number for recurring trip kwh
        try:
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "name": f"{vehicle_id} - Trip kWh",
                    "min": 0,
                    "max": 200,
                    "unit_of_measurement": "kWh",
                    "icon": "mdi:lightning-bolt",
                },
            )
            _LOGGER.debug("Created input_number for kwh: %s_trip_kwh", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input number may already exist: %s", e)

        # Create input_text for recurring trip description
        try:
            await hass.services.async_call(
                "input_text",
                "create",
                {
                    "name": f"{vehicle_id} - Trip Description",
                    "icon": "mdi:text",
                },
            )
            _LOGGER.debug("Created input_text for desc: %s_trip_desc", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input text may already exist: %s", e)

        # Create input_datetime for punctual trip datetime
        try:
            await hass.services.async_call(
                "input_datetime",
                "create",
                {
                    "name": f"{vehicle_id} - Punctual Trip DateTime",
                    "has_date": True,
                    "has_time": True,
                    "icon": "mdi:calendar-clock",
                },
            )
            _LOGGER.debug(
                "Created input_datetime for datetime: %s_punctual_datetime", vehicle_id
            )
        except Exception as e:
            _LOGGER.debug("Input datetime may already exist: %s", e)

        # Create input_number for punctual trip km
        try:
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "name": f"{vehicle_id} - Punctual Trip km",
                    "min": 0,
                    "max": 1000,
                    "unit_of_measurement": "km",
                    "icon": "mdi:map-marker-distance",
                },
            )
            _LOGGER.debug("Created input_number for km: %s_punctual_km", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input number may already exist: %s", e)

        # Create input_number for punctual trip kwh
        try:
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "name": f"{vehicle_id} - Punctual Trip kWh",
                    "min": 0,
                    "max": 200,
                    "unit_of_measurement": "kWh",
                    "icon": "mdi:lightning-bolt",
                },
            )
            _LOGGER.debug("Created input_number for kwh: %s_punctual_kwh", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input number may already exist: %s", e)

        # Create input_text for punctual trip description
        try:
            await hass.services.async_call(
                "input_text",
                "create",
                {
                    "name": f"{vehicle_id} - Punctual Trip Description",
                    "icon": "mdi:text",
                },
            )
            _LOGGER.debug("Created input_text for desc: %s_punctual_desc", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input text may already exist: %s", e)

        # === Edit Trip Input Helpers ===
        # Input to select which trip to edit
        try:
            await hass.services.async_call(
                "input_select",
                "create",
                {
                    "name": f"{vehicle_id} - Edit Trip Selector",
                    "options": ["-- Seleccionar viaje --"],
                    "icon": "mdi:pencil",
                },
            )
            _LOGGER.debug(
                "Created input_select for edit: %s_edit_trip_selector", vehicle_id
            )
        except Exception as e:
            _LOGGER.debug("Input select may already exist: %s", e)

        # Input datetime for edit trip time
        try:
            await hass.services.async_call(
                "input_datetime",
                "create",
                {
                    "name": f"{vehicle_id} - Edit Trip Time",
                    "has_date": False,
                    "has_time": True,
                    "icon": "mdi:clock-edit",
                },
            )
            _LOGGER.debug(
                "Created input_datetime for edit time: %s_edit_trip_time", vehicle_id
            )
        except Exception as e:
            _LOGGER.debug("Input datetime may already exist: %s", e)

        # Input number for edit trip km
        try:
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "name": f"{vehicle_id} - Edit Trip km",
                    "min": 0,
                    "max": 1000,
                    "unit_of_measurement": "km",
                    "icon": "mdi:map-marker-distance",
                },
            )
            _LOGGER.debug(
                "Created input_number for edit km: %s_edit_trip_km", vehicle_id
            )
        except Exception as e:
            _LOGGER.debug("Input number may already exist: %s", e)

        # Input number for edit trip kwh
        try:
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "name": f"{vehicle_id} - Edit Trip kWh",
                    "min": 0,
                    "max": 200,
                    "unit_of_measurement": "kWh",
                    "icon": "mdi:lightning-bolt",
                },
            )
            _LOGGER.debug(
                "Created input_number for edit kwh: %s_edit_trip_kwh", vehicle_id
            )
        except Exception as e:
            _LOGGER.debug("Input number may already exist: %s", e)

        # Input text for edit trip description
        try:
            await hass.services.async_call(
                "input_text",
                "create",
                {
                    "name": f"{vehicle_id} - Edit Trip Description",
                    "icon": "mdi:text",
                },
            )
            _LOGGER.debug(
                "Created input_text for edit desc: %s_edit_trip_desc", vehicle_id
            )
        except Exception as e:
            _LOGGER.debug("Input text may already exist: %s", e)

        # Input datetime for edit punctual trip datetime
        try:
            await hass.services.async_call(
                "input_datetime",
                "create",
                {
                    "name": f"{vehicle_id} - Edit Punctual DateTime",
                    "has_date": True,
                    "has_time": True,
                    "icon": "mdi:calendar-edit",
                },
            )
            _LOGGER.debug(
                "Created input_datetime for edit datetime: %s_edit_punctual_datetime",
                vehicle_id,
            )
        except Exception as e:
            _LOGGER.debug("Input datetime may already exist: %s", e)

        _LOGGER.info("Input helpers created successfully for: %s", vehicle_id)
        from custom_components.ev_trip_planner.dashboard import DashboardImportResult

        return DashboardImportResult(
            success=True,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_id,
            dashboard_type="simple",
            storage_method="input_helpers",
        )

    except Exception as e:
        _LOGGER.error("Failed to create input helpers for %s: %s", vehicle_id, e)
        from custom_components.ev_trip_planner.dashboard import DashboardImportResult

        return DashboardImportResult(
            success=False,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_id,
            error=str(e),
            dashboard_type="simple",
            storage_method="input_helpers",
        )


async def async_cleanup_stale_storage(hass: HomeAssistant, vehicle_id: str) -> None:
    """Clean up any existing storage for this vehicle_id BEFORE loading.

    This handles the case where async_remove_entry wasn't called (e.g., due to HA bugs).
    When a user deletes and re-adds an integration, we want a fresh start.
    """
    try:
        from homeassistant.helpers import storage as ha_storage
        import os
        from pathlib import Path

        cleanup_key = f"{DOMAIN}_{vehicle_id}"
        _LOGGER.warning(
            "=== async_cleanup_stale_storage - Checking for stale storage: %s ===",
            cleanup_key,
        )
        cleanup_store = ha_storage.Store(hass, version=1, key=cleanup_key)
        existing_data = await cleanup_store.async_load()
        if existing_data:
            _LOGGER.warning(
                "=== async_cleanup_stale_storage - Found stale storage for %s, cleaning up ===",
                vehicle_id,
            )
            await cleanup_store.async_remove()
            _LOGGER.info(
                "Cleaned up stale storage for vehicle %s during setup", vehicle_id
            )
        else:
            _LOGGER.warning(
                "=== async_cleanup_stale_storage - No stale storage found for %s ===",
                vehicle_id,
            )
        # Also check for YAML fallback storage and remove it
        yaml_path = (
            Path(hass.config.config_dir or "/config")
            / "ev_trip_planner"
            / f"{cleanup_key}.yaml"
        )
        if yaml_path.exists():
            _LOGGER.warning(
                "=== async_cleanup_stale_storage - Found stale YAML storage for %s, cleaning up ===",
                vehicle_id,
            )
            os.unlink(yaml_path)
            _LOGGER.info(
                "Cleaned up stale YAML storage for vehicle %s during setup", vehicle_id
            )
    except Exception as cleanup_err:
        _LOGGER.warning(
            "=== async_cleanup_stale_storage - Storage cleanup error (continuing): %s ===",
            cleanup_err,
        )


async def async_cleanup_orphaned_emhass_sensors(hass: HomeAssistant) -> None:
    """Clean up orphaned EMHASS state-based sensors from deleted integrations.

    This iterates over all entity registry entries and removes any EMHASS
    deferrable load sensors that reference a config entry that no longer exists.
    """
    try:
        from homeassistant.helpers import entity_registry as er

        registry = er.async_get(hass)
        for entry in hass.config_entries.async_entries(DOMAIN):
            entries = er.async_entries_for_config_entry(registry, entry.entry_id)
            for _entry in entries:
                pass  # Placeholder - actual cleanup logic would go here
    except Exception as e:
        _LOGGER.debug("Error cleaning up orphaned EMHASS sensors: %s", e)


def build_presence_config(entry: ConfigEntry) -> dict[str, Any]:
    """Build presence_config dict from entry.data for PresenceMonitor.

    Args:
        entry: The config entry containing vehicle configuration.

    Returns:
        Dict with presence configuration keys.
    """
    from .const import (
        CONF_CHARGING_SENSOR,
        CONF_HOME_COORDINATES,
        CONF_HOME_SENSOR,
        CONF_NOTIFICATION_SERVICE,
        CONF_PLUGGED_SENSOR,
        CONF_SOC_SENSOR,
        CONF_VEHICLE_COORDINATES_SENSOR,
    )

    return {
        CONF_HOME_SENSOR: entry.data.get(CONF_HOME_SENSOR),
        CONF_PLUGGED_SENSOR: entry.data.get(CONF_PLUGGED_SENSOR),
        CONF_CHARGING_SENSOR: entry.data.get(CONF_CHARGING_SENSOR),
        CONF_HOME_COORDINATES: entry.data.get(CONF_HOME_COORDINATES),
        CONF_VEHICLE_COORDINATES_SENSOR: entry.data.get(
            CONF_VEHICLE_COORDINATES_SENSOR
        ),
        CONF_NOTIFICATION_SERVICE: entry.data.get(CONF_NOTIFICATION_SERVICE),
        CONF_SOC_SENSOR: entry.data.get(CONF_SOC_SENSOR),
    }


async def async_register_static_paths(
    hass: HomeAssistant,
) -> None:
    """Register static paths for the panel JS/CSS files.

    This must be called early before any browser tries to load the panel.
    """
    from pathlib import Path

    try:
        from homeassistant.components.http import StaticPathConfig

        HAS_STATIC_PATH_CONFIG = True
    except ImportError:
        HAS_STATIC_PATH_CONFIG = False

    component_dir = Path(__file__).parent
    panel_js_path = component_dir / "frontend" / "panel.js"
    panel_css_path = component_dir / "frontend" / "panel.css"
    lit_bundle_path = component_dir / "frontend" / "lit-bundle.js"

    static_paths: list[Any] = []
    if panel_js_path.exists():
        static_paths.append(
            StaticPathConfig(
                "/ev-trip-planner/panel.js",
                str(panel_js_path),
                cache_headers=False,
            )
            if HAS_STATIC_PATH_CONFIG
            else ("/ev-trip-planner/panel.js", str(panel_js_path), False)
        )
    if lit_bundle_path.exists():
        static_paths.append(
            StaticPathConfig(
                "/ev-trip-planner/lit-bundle.js",
                str(lit_bundle_path),
                cache_headers=False,
            )
            if HAS_STATIC_PATH_CONFIG
            else ("/ev-trip-planner/lit-bundle.js", str(lit_bundle_path), False)
        )
    if panel_css_path.exists():
        static_paths.append(
            StaticPathConfig(
                "/ev-trip-planner/panel.css",
                str(panel_css_path),
                cache_headers=False,
            )
            if HAS_STATIC_PATH_CONFIG
            else ("/ev-trip-planner/panel.css", str(panel_css_path), False)
        )

    if static_paths and hass.http is not None:
        try:
            await hass.http.async_register_static_paths(static_paths)
            _LOGGER.info(
                "Registered %d static path(s) for EV Trip Planner panel (early)",
                len(static_paths),
            )
        except (TypeError, AttributeError, RuntimeError) as err:
            _LOGGER.warning(
                "async_register_static_paths (early) error: %s, trying legacy",
                err,
            )
            try:
                for path_spec in static_paths:
                    try:
                        if isinstance(path_spec, tuple):
                            url_path, file_path, _ = path_spec
                            hass.http.register_static_path(url_path, file_path)
                        else:
                            hass.http.register_static_path(
                                path_spec.url_path, path_spec.path
                            )
                    except RuntimeError as path_err:
                        if "already registered" in str(path_err).lower():
                            continue
                        raise
                _LOGGER.info("Registered static paths using legacy method (early)")
            except Exception as legacy_err:
                _LOGGER.error("Failed to register static paths (early): %s", legacy_err)
    elif static_paths:
        _LOGGER.warning("hass.http is None - static paths cannot be registered early")


async def async_register_panel_for_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    vehicle_id: str,
    vehicle_name: str,
) -> bool:
    """Register native panel for a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.
        vehicle_id: The vehicle ID string.
        vehicle_name: The vehicle display name.

    Returns:
        True if panel was registered successfully.
    """
    from . import panel as panel_module

    panel_registered = False
    try:
        panel_result = await panel_module.async_register_panel(
            hass,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_name,
        )
        panel_registered = panel_result is True
        if not panel_registered:
            _LOGGER.error(
                "Panel registration returned False for vehicle %s - panel will not be available in sidebar",
                vehicle_name,
            )
    except Exception as err:
        _LOGGER.error(
            "Failed to register panel for vehicle %s: %s. Panel will not be available.",
            vehicle_name,
            err,
            exc_info=True,
        )
    return panel_registered


async def async_import_dashboard_for_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    vehicle_id: str,
) -> None:
    """Import dashboard configuration for a vehicle.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.
        vehicle_id: The vehicle ID string.
    """
    from .dashboard import import_dashboard as import_dashboard

    try:
        use_charts = entry.data.get("use_charts", False)
        import_result = await import_dashboard(
            hass,
            vehicle_id,
            entry.data.get("vehicle_name", vehicle_id),
            use_charts=use_charts,
        )
        if not import_result.success:
            _LOGGER.warning(
                "Dashboard import failed for %s: %s",
                entry.data.get("vehicle_name", vehicle_id),
                import_result.error,
            )
    except Exception as e:
        _LOGGER.warning(
            "Dashboard import exception for %s: %s",
            entry.data.get("vehicle_name", vehicle_id),
            e,
        )


async def async_unload_entry_cleanup(
    hass: HomeAssistant,
    entry: ConfigEntry,
    vehicle_id: str,
    vehicle_name: str,
) -> bool:
    """Perform cleanup operations during entry unload.

    Performs cascade delete of trips, cleans up EMHASS adapters,
    unregisters panel, and removes runtime data.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.
        vehicle_id: The vehicle ID string.
        vehicle_name: The vehicle display name.

    Returns:
        True if unload was successful.
    """
    # Get runtime data from entry.runtime_data (HA-recommended)
    runtime_data = getattr(entry, "runtime_data", None)
    trip_manager = getattr(runtime_data, "trip_manager", None) if runtime_data else None
    emhass_adapter = getattr(runtime_data, "emhass_adapter", None) if runtime_data else None

    if trip_manager:
        _LOGGER.warning("Cascade deleting all trips for vehicle %s", vehicle_name)
        await trip_manager.async_delete_all_trips()

    # Cleanup EMHASS vehicle indices before unload
    if emhass_adapter:
        if hasattr(emhass_adapter, "_config_entry_listener") and emhass_adapter._config_entry_listener:
            emhass_adapter._config_entry_listener()
            emhass_adapter._config_entry_listener = None
        await emhass_adapter.async_cleanup_vehicle_indices()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Clean up entity registry for this config entry
    # This removes all sensor entities from the registry when the entry is unloaded
    try:
        from homeassistant.helpers import entity_registry as er

        # Try hass.entity_registry first (some test mocks set this directly)
        # Fall back to er.async_get(hass) for real HA
        entity_registry = getattr(hass, "entity_registry", None)
        if entity_registry is None:
            entity_registry = er.async_get(hass)
        # Use the registry's async_entries_for_config_entry method directly
        for entity_entry in entity_registry.async_entries_for_config_entry(entry.entry_id):
            await entity_registry.async_remove(entity_entry.entity_id)
    except Exception as ex:
        _LOGGER.warning("Failed to clean up entity registry: %s", ex)

    # Remove the native panel from sidebar
    try:
        from .panel import async_unregister_panel

        await async_unregister_panel(hass, vehicle_id)
    except Exception as ex:
        _LOGGER.warning("Failed to unregister panel for vehicle %s: %s", vehicle_id, ex)

    return unload_ok


async def async_remove_entry_cleanup(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Remove a config entry and all its data.

    This handles final cleanup of persistent storage after unload.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry to remove.
    """
    _LOGGER.warning("=== async_remove_entry CALLED === entry_id: %s", entry.entry_id)

    # Safely extract vehicle_name from entry.data
    vehicle_name_raw = entry.data.get("vehicle_name") if entry.data else None
    if not vehicle_name_raw:
        vehicle_id = entry.entry_id
        vehicle_name = f"unknown_{entry.entry_id[:8]}"
    else:
        vehicle_id = vehicle_name_raw.lower().replace(" ", "_")
        vehicle_name = vehicle_name_raw

    try:
        # Delete persistent storage for this vehicle
        from homeassistant.helpers import storage as ha_storage

        storage_key = f"{DOMAIN}_{vehicle_id}"
        store = ha_storage.Store(hass, version=1, key=storage_key)
        try:
            await store.async_remove()
        except Exception as store_err:
            _LOGGER.warning("Could not remove storage for %s: %s", storage_key, store_err)

        # Clean up YAML fallback storage
        try:
            import os
            from pathlib import Path

            config_dir = hass.config.config_dir or "/config"
            yaml_path = Path(config_dir) / "ev_trip_planner" / f"{storage_key}.yaml"
            if yaml_path.exists():
                os.unlink(yaml_path)
        except Exception as yaml_err:
            _LOGGER.warning("Could not remove YAML storage: %s", yaml_err)

        # Clean up input helpers created for this vehicle
        input_helper_entities = [
            f"{vehicle_id}_trip_day",
            f"{vehicle_id}_trip_time",
            f"{vehicle_id}_trip_km",
            f"{vehicle_id}_trip_kwh",
            f"{vehicle_id}_trip_desc",
            f"{vehicle_id}_punctual_datetime",
            f"{vehicle_id}_punctual_km",
            f"{vehicle_id}_punctual_kwh",
            f"{vehicle_id}_punctual_desc",
            f"{vehicle_id}_edit_trip_selector",
            f"{vehicle_id}_edit_trip_time",
            f"{vehicle_id}_edit_trip_km",
            f"{vehicle_id}_edit_trip_kwh",
            f"{vehicle_id}_edit_trip_desc",
            f"{vehicle_id}_edit_punctual_datetime",
        ]

        for entity_id in input_helper_entities:
            for prefix in ["input_select.", "input_datetime.", "input_number.", "input_text."]:
                full_entity_id = f"{prefix}{entity_id}"
                try:
                    if hass.states.get(full_entity_id):
                        await hass.services.async_call(
                            full_entity_id.split(".", maxsplit=1)[0],
                            "remove",
                            {"entity_id": full_entity_id},
                            blocking=True,
                        )
                except Exception:
                    pass  # Entity might not exist

        _LOGGER.info("Entry removal complete for vehicle %s", vehicle_name)
    except Exception as err:
        _LOGGER.error("Error removing entry for vehicle %s: %s", vehicle_name, err)
