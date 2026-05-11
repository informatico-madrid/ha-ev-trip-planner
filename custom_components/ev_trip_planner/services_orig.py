"""Service handlers for EV Trip Planner integration.

Extracted from __init__.py as part of Phase 4 refactoring.
Contains all service handlers and helper functions for trip management services.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, cast

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback

from .const import DOMAIN
from .coordinator import TripPlannerCoordinator
from .dashboard import DashboardImportResult  # type: ignore[reportAttributeAccessIssue]
from .services.cleanup import (
    async_cleanup_orphaned_emhass_sensors,
    async_cleanup_stale_storage,
    async_remove_entry_cleanup,
    async_unload_entry_cleanup,
)
from .trip import TripManager
from .utils import normalize_vehicle_id

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Type alias for coordinator
CoordinatorType = TripPlannerCoordinator

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
        _LOGGER.debug("=== trip_list SERVICE HANDLER CALLED ===")
        _LOGGER.debug("=== call.data: %s", call.data)
        data = call.data
        vehicle_id = data.get("vehicle_id", "unknown")
        _LOGGER.debug("=== trip_list SERVICE CALLED === vehicle: %s", vehicle_id)

        mgr = await _get_manager(hass, vehicle_id)
        # _get_manager already calls async_setup which loads trips from storage
        _LOGGER.debug("=== _get_manager returned manager ===")
        _LOGGER.debug(
            "=== Before async_get_recurring_trips - mgr._recurring_trips: %d",
            len(mgr._recurring_trips),
        )
        _LOGGER.debug(
            "=== Before async_get_punctual_trips - mgr._punctual_trips: %d",
            len(mgr._punctual_trips),
        )

        try:
            _LOGGER.debug("Getting recurring trips for %s", vehicle_id)
            recurring_trips = await mgr.async_get_recurring_trips()
            _LOGGER.debug("Got %d recurring trips", len(recurring_trips))

            _LOGGER.debug("Getting punctual trips for %s", vehicle_id)
            punctual_trips = await mgr.async_get_punctual_trips()
            _LOGGER.debug("Got %d punctual trips", len(punctual_trips))

            _LOGGER.info(
                "Retrieved %d recurring trips and %d punctual trips for vehicle %s",
                len(recurring_trips),
                len(punctual_trips),
                vehicle_id,
            )

            # Debug: Log each recurring trip
            for i, trip in enumerate(recurring_trips):
                _LOGGER.debug(
                    "Recurring trip %d: id=%s, tipo=%s, activo=%s",
                    i,
                    trip.get("id"),
                    trip.get("tipo"),
                    trip.get("activo"),
                )

            # Debug: Log each punctual trip
            for i, trip in enumerate(punctual_trips):
                _LOGGER.debug(
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
            _LOGGER.debug("=== trip_list result ===")
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
        _LOGGER.debug("=== trip_get SERVICE HANDLER CALLED ===")
        _LOGGER.debug("=== call.data: %s", call.data)
        data = call.data
        vehicle_id = data.get("vehicle_id", "unknown")
        trip_id = data.get("trip_id", "unknown")
        _LOGGER.warning(
            "=== trip_get SERVICE CALLED === vehicle: %s, trip_id: %s",
            vehicle_id,
            trip_id,
        )

        mgr = await _get_manager(hass, vehicle_id)
        _LOGGER.debug("=== _get_manager returned manager ===")

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
                _LOGGER.debug("=== trip_get SUCCESS - Found trip: %s ===", trip_found)
                return {
                    "vehicle_id": vehicle_id,
                    "trip": trip_found,
                    "found": True,
                }
            else:
                _LOGGER.debug("=== trip_get NOT FOUND - trip_id: %s ===", trip_id)
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
        # Normalize entry_vehicle_name using centralized utility
        normalized_entry_name = normalize_vehicle_id(entry_vehicle_name)
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
    _LOGGER.debug("=== _get_manager - runtime_data: %s ===", runtime_data)

    # Retrieve trip_manager from entry.runtime_data
    trip_manager = runtime_data.trip_manager if runtime_data else None
    _LOGGER.debug(
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
            _LOGGER.info("=== _get_manager - Calling trip_manager.async_setup() ===")
            await trip_manager.async_setup()
            _LOGGER.info(
                "=== _get_manager - After async_setup - trips: recurring=%d, punctual=%d ===",
                len(trip_manager._recurring_trips),
                len(trip_manager._punctual_trips),
            )
        except Exception as setup_err:  # pragma: no cover — factory function error path; requires broken factory to trigger
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
    """Ensure TripManager is set up before operations.

    The trip_manager from runtime_data should already be set up by the coordinator.
    We no longer call async_setup() here to prevent _load_trips() from overwriting
    in-memory data with stale storage data.
    """
    # No-op - trip_manager from coordinator is already set up
    pass


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


# Dashboard helpers — re-exported from services.dashboard_helpers
from .services.dashboard_helpers import (
    async_import_dashboard_for_entry,
    async_register_panel_for_entry,
    async_register_static_paths,
    create_dashboard_input_helpers,
)


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



