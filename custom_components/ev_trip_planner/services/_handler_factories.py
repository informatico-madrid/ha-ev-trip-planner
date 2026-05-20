"""Handler factory closures — make_*_handler(hass) returns async service handlers.

Each factory captures `hass` and returns a coroutine that accepts ServiceCall.
Helpers (_get_manager, _get_coordinator, etc.) are defined in _utils.py.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall

from ._utils import (
    _ensure_setup,
    _find_entry_by_vehicle,
    _get_coordinator,
    _get_manager,
)

# ── Log format string constants (US-5 testability) ──────────────────────
_LOG_HANDLER_TRIP_LIST_CALLED = "=== trip_list SERVICE HANDLER CALLED ==="
_LOG_HANDLER_GET_MANAGER_OK = "=== _get_manager returned manager ==="
_LOG_HANDLER_TRIP_GET_CALLED = "=== trip_get SERVICE HANDLER CALLED ==="
_LOG_HANDLER_TRIP_LIST_RESULT = "=== trip_list result ==="
_LOG_REFRESH = "Refrescando trips para vehículo: %s"
_LOG_CALL_DATA = "=== call.data: %s"
_LOG_TRIP_LIST_SERVICE_CALLED = "=== trip_list SERVICE CALLED === vehicle: %s"
_LOG_RECURRING_TRIPS_BEFORE = "=== Before async_get_recurring_trips - mgr._state.recurring_trips: %d"
_LOG_PUNCTUAL_TRIPS_BEFORE = "=== Before async_get_punctual_trips - mgr._state.punctual_trips: %d"
_LOG_GETTING_RECURRING = "Getting recurring trips for %s"
_LOG_GOT_RECURRING = "Got %d recurring trips"
_LOG_GETTING_PUNCTUAL = "Getting punctual trips for %s"
_LOG_GOT_PUNCTUAL = "Got %d punctual trips"
_LOG_RETRIEVED = "Retrieved %d recurring trips and %d punctual trips for vehicle %s"
_LOG_RECURRING_TRIP_ENTRY = "Recurring trip %d: id=%s, tipo=%s, activo=%s"
_LOG_PUNCTUAL_TRIP_ENTRY = "Punctual trip %d: id=%s, tipo=%s, estado=%s"
_LOG_RECURRING_COUNT = "recurring_trips count: %d"
_LOG_PUNCTUAL_COUNT = "punctual_trips count: %d"
_LOG_TOTAL_COUNT = "total_trips: %d"
_LOG_FIRST_RECURRING = "First recurring trip: %s"
_LOG_FIRST_PUNCTUAL = "First punctual trip: %s"
_LOG_ERROR_LISTING = "Error listing trips for vehicle %s: %s"
_LOG_UPDATING_TRIP = "Updating trip %s for vehicle %s with updates: %s"
_LOG_ENTRY_NOT_FOUND = "Config entry not found for vehicle %s"
_LOG_UPDATE_FAILED = "Failed to update trip sensor: %s"
_LOG_CREATED_RECURRING = "Created recurring trip for vehicle %s: %s at %s, %s km"
_LOG_CREATED_PUNCTUAL = "Created punctual trip for vehicle %s: %s, %s km"
_LOG_INVALID_TRIP_TYPE = "Invalid trip type '%s' for vehicle %s. Must be 'recurrente' or 'puntual'"
_LOG_CALL_DATA_TRIP_GET = "=== call.data: %s"
_LOG_TRIP_GET_SERVICE_CALLED = "=== trip_get SERVICE CALLED === vehicle: %s, trip_id: %s"
_LOG_TRIP_GET_SUCCESS = "=== trip_get SUCCESS - Found trip: %s ==="
_LOG_TRIP_GET_NOT_FOUND = "=== trip_get NOT FOUND - trip_id: %s ==="
_LOG_GETTING_ALL_TO_FIND = "Getting all trips to find trip_id: %s"
_LOG_FOUND_TRIPS_COUNT = "Found %d recurring and %d punctual trips"
_LOG_SEARCHING_FOR_ID = "Searching through %d trips for ID: %s"
_LOG_FOUND_TRIP = "Found trip: %s"
_LOG_ERROR_GETTING_TRIP = "Error getting trip %s for vehicle %s: %s"
_LOG_FINDING_ALL_TO_FIND_ID = "Getting all trips to find trip_id: %s"

_LOGGER = logging.getLogger(__name__)

# --- Common schemas (for register_services to pass) ---

trip_id_schema = vol.Schema(
    {
        vol.Required("vehicle_id"): str,
        vol.Required("trip_id"): str,
    }
)

trip_update_schema = vol.Schema(
    {
        vol.Required("vehicle_id"): str,
        vol.Required("trip_id"): str,
        vol.Required("type"): vol.In(["recurrente", "puntual"]),
        vol.Optional("dia_semana"): str,
        vol.Optional("day_of_week"): str,
        vol.Optional("hora"): str,
        vol.Optional("time"): str,
        vol.Optional("datetime"): str,
        vol.Optional("km"): vol.Coerce(float),
        vol.Optional("kwh"): vol.Coerce(float),
        vol.Optional("descripcion"): str,
        vol.Optional("description"): str,
    }
)

trip_create_schema = vol.Schema(
    {
        vol.Required("vehicle_id"): str,
        vol.Required("type"): vol.In(["recurrente", "puntual"]),
        vol.Optional("dia_semana"): str,
        vol.Optional("day_of_week"): str,
        vol.Optional("hora"): str,
        vol.Optional("time"): str,
        vol.Optional("datetime"): str,
        vol.Required("km"): vol.Coerce(float),
        vol.Required("kwh"): vol.Coerce(float),
        vol.Optional("descripcion", default=""): str,
        vol.Optional("description", default=""): str,
    }
)


# === Factory: add_recurring_trip ===


def make_add_recurring_handler(hass: HomeAssistant):
    """Return async handler for add_recurring_trip service."""

    async def handler(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await mgr._crud.async_add_recurring_trip(
            dia_semana=data["dia_semana"],
            hora=data["hora"],
            km=float(data["km"]),
            kwh=float(data["kwh"]),
            descripcion=str(data.get("descripcion", "")),
        )
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug(_LOG_REFRESH, vehicle_id)
            await coordinator.async_refresh_trips()

    return handler


# === Factory: add_punctual_trip ===


def make_add_punctual_handler(hass: HomeAssistant):
    """Return async handler for add_punctual_trip service."""

    async def handler(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await mgr._crud.async_add_punctual_trip(
            datetime_str=data["datetime"],
            km=float(data["km"]),
            kwh=float(data["kwh"]),
            descripcion=str(data.get("descripcion", "")),
        )
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug(_LOG_REFRESH, vehicle_id)
            await coordinator.async_refresh_trips()

    return handler


# === Factory: trip_update ===


def make_trip_update_handler(hass: HomeAssistant):
    """Return async handler for trip_update service."""

    # qg-accepted: complexity=13 is inherent to trip update handler with field mapping
    async def handler(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        trip_id = str(data["trip_id"])
        _ = data.get("type", "recurrente")

        if "updates" in data:
            updates = dict(data["updates"])
        else:
            updates: dict[str, Any] = {}
            for src, dst in [
                ("dia_semana", "dia_semana"),
                ("day_of_week", "dia_semana"),
                ("hora", "hora"),
                ("time", "hora"),
                ("datetime", "datetime"),
            ]:
                if src in data:
                    updates[dst] = data[src]
            if "km" in data:
                updates["km"] = float(data["km"])
            if "kwh" in data:
                updates["kwh"] = float(data["kwh"])
            if "descripcion" in data:
                updates["descripcion"] = str(data["descripcion"])
            if "description" in data:
                updates["descripcion"] = str(data["description"])

        _LOGGER.info(_LOG_UPDATING_TRIP, trip_id, vehicle_id, updates)

        entry = _find_entry_by_vehicle(hass, vehicle_id)
        if not entry:
            _LOGGER.error(_LOG_ENTRY_NOT_FOUND, vehicle_id)
            return

        mgr = await _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr._crud.async_update_trip(trip_id, updates)

        try:
            from ..sensor import async_update_trip_sensor

            t = "recurrente" if updates.get("dia_semana") else "puntual"
            trips = (
                await mgr._crud.async_get_recurring_trips()
                if t == "recurrente"
                else await mgr._crud.async_get_punctual_trips()
            )
            for trip in trips:
                if str(trip.get("id")) == trip_id:
                    await async_update_trip_sensor(
                        hass, entry.entry_id, {**trip, "id": trip_id}
                    )
                    break
        except Exception as err:
            _LOGGER.warning(_LOG_UPDATE_FAILED, err)

        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug(_LOG_REFRESH, vehicle_id)
            await coordinator.async_refresh_trips()

    return handler


# === Factory: edit_trip ===


def make_edit_trip_handler(hass: HomeAssistant):
    """Return async handler for edit_trip service (deprecated alias)."""

    async def handler(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr._crud.async_update_trip(str(data["trip_id"]), dict(data["updates"]))
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug(_LOG_REFRESH, vehicle_id)
            await coordinator.async_refresh_trips()

    return handler


# === Factory: delete_trip ===


def make_delete_trip_handler(hass: HomeAssistant):
    """Return async handler for delete_trip service."""

    async def handler(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        trip_id = str(data["trip_id"])
        mgr = await _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr._crud.async_delete_trip(trip_id)
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug(_LOG_REFRESH, vehicle_id)
            await coordinator.async_refresh_trips()

    return handler


# === Factory: pause_recurring_trip ===


def make_pause_recurring_handler(hass: HomeAssistant):
    """Return async handler for pause_recurring_trip service."""

    async def handler(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr._lifecycle.async_pause_recurring_trip(str(data["trip_id"]))
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug(_LOG_REFRESH, vehicle_id)
            await coordinator.async_refresh_trips()

    return handler


# === Factory: resume_recurring_trip ===


def make_resume_recurring_handler(hass: HomeAssistant):
    """Return async handler for resume_recurring_trip service."""

    async def handler(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr._lifecycle.async_resume_recurring_trip(str(data["trip_id"]))
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug(_LOG_REFRESH, vehicle_id)
            await coordinator.async_refresh_trips()

    return handler


# === Factory: complete_punctual_trip ===


def make_complete_punctual_handler(hass: HomeAssistant):
    """Return async handler for complete_punctual_trip service."""

    async def handler(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr._lifecycle.async_complete_punctual_trip(str(data["trip_id"]))
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug(_LOG_REFRESH, vehicle_id)
            await coordinator.async_refresh_trips()

    return handler


# === Factory: cancel_punctual_trip ===


def make_cancel_punctual_handler(hass: HomeAssistant):
    """Return async handler for cancel_punctual_trip service."""

    async def handler(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = await _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr._lifecycle.async_cancel_punctual_trip(str(data["trip_id"]))
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug(_LOG_REFRESH, vehicle_id)
            await coordinator.async_refresh_trips()

    return handler


# === Factory: trip_create ===


def make_trip_create_handler(hass: HomeAssistant):
    """Return async handler for trip_create service (unified)."""

    async def handler(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        trip_type = data.get("type", data.get("trip_type", "recurrente"))
        mgr = await _get_manager(hass, vehicle_id)

        if trip_type == "recurrente":
            dia_semana = data.get("dia_semana") or data.get("day_of_week")
            hora = data.get("hora") or data.get("time")
            descripcion = data.get("descripcion") or data.get("description", "")
            await mgr._crud.async_add_recurring_trip(
                dia_semana=dia_semana,
                hora=hora,
                km=float(data["km"]),
                kwh=float(data["kwh"]),
                descripcion=descripcion,
            )
            _LOGGER.info(_LOG_CREATED_RECURRING, vehicle_id, dia_semana, hora, data["km"])
        elif trip_type == "puntual":
            datetime_str = data.get("datetime")
            descripcion = data.get("descripcion") or data.get("description", "")
            await mgr._crud.async_add_punctual_trip(
                datetime_str=datetime_str,
                km=float(data["km"]),
                kwh=float(data["kwh"]),
                descripcion=descripcion,
            )
            _LOGGER.info(_LOG_CREATED_PUNCTUAL, vehicle_id, datetime_str, data["km"])
        else:
            _LOGGER.error(_LOG_INVALID_TRIP_TYPE, trip_type, vehicle_id)
            return

        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug(_LOG_REFRESH, vehicle_id)
            await coordinator.async_refresh_trips()

    return handler


# === Factory: import_weekly_pattern ===


def make_import_weekly_pattern_handler(hass: HomeAssistant):
    """Return async handler for import_from_weekly_pattern service."""

    async def handler(call: ServiceCall) -> None:
        data = call.data
        mgr = await _get_manager(hass, data["vehicle_id"])
        await _ensure_setup(mgr)

        clear_existing = bool(data.get("clear_existing", True))
        pattern: dict[str, Any] = dict(data["pattern"])

        if clear_existing:
            try:
                existing = await mgr._crud.async_get_recurring_trips()
            except Exception:
                existing = []
            for trip in existing:
                trip_id = str(trip.get("id"))
                if trip_id:
                    await mgr._crud.async_delete_trip(trip_id)

        for dia, items in pattern.items():
            for item in items or []:
                await mgr._crud.async_add_recurring_trip(
                    dia_semana=str(dia),
                    hora=str(item["hora"]),
                    km=float(item["km"]),
                    kwh=float(item["kwh"]),
                    descripcion=str(item.get("descripcion", "")),
                )

    return handler


# === Factory: trip_list ===


def make_trip_list_handler(hass: HomeAssistant):
    """Return async handler for trip_list service."""

    async def handler(call: ServiceCall) -> dict[str, Any]:
        _LOGGER.debug(_LOG_HANDLER_TRIP_LIST_CALLED)
        _LOGGER.debug(_LOG_CALL_DATA, call.data)
        data = call.data
        vehicle_id = data.get("vehicle_id", "unknown")
        _LOGGER.debug(_LOG_TRIP_LIST_SERVICE_CALLED, vehicle_id)

        mgr = await _get_manager(hass, vehicle_id)
        _LOGGER.debug(_LOG_HANDLER_GET_MANAGER_OK)
        _LOGGER.debug(
            _LOG_RECURRING_TRIPS_BEFORE,
            len(mgr._state.recurring_trips),
        )
        _LOGGER.debug(
            _LOG_PUNCTUAL_TRIPS_BEFORE,
            len(mgr._state.punctual_trips),
        )

        try:
            _LOGGER.debug(_LOG_GETTING_RECURRING, vehicle_id)
            recurring_trips = await mgr._crud.async_get_recurring_trips()
            _LOGGER.debug(_LOG_GOT_RECURRING, len(recurring_trips))

            _LOGGER.debug(_LOG_GETTING_PUNCTUAL, vehicle_id)
            punctual_trips = await mgr._crud.async_get_punctual_trips()
            _LOGGER.debug(_LOG_GOT_PUNCTUAL, len(punctual_trips))

            _LOGGER.info(
                _LOG_RETRIEVED,
                len(recurring_trips),
                len(punctual_trips),
                vehicle_id,
            )

            for i, trip in enumerate(recurring_trips):
                _LOGGER.debug(
                    _LOG_RECURRING_TRIP_ENTRY,
                    i,
                    trip.get("id"),
                    trip.get("tipo"),
                    trip.get("activo"),
                )

            for i, trip in enumerate(punctual_trips):
                _LOGGER.debug(
                    _LOG_PUNCTUAL_TRIP_ENTRY,
                    i,
                    trip.get("id"),
                    trip.get("tipo"),
                    trip.get("estado"),
                )

            result = {
                "vehicle_id": vehicle_id,
                "recurring_trips": recurring_trips,
                "punctual_trips": punctual_trips,
                "total_trips": len(recurring_trips) + len(punctual_trips),
            }
            _LOGGER.debug(_LOG_HANDLER_TRIP_LIST_RESULT)
            _LOGGER.warning(_LOG_RECURRING_COUNT, len(recurring_trips))
            _LOGGER.warning(_LOG_PUNCTUAL_COUNT, len(punctual_trips))
            _LOGGER.warning(_LOG_TOTAL_COUNT, result["total_trips"])
            if recurring_trips:
                _LOGGER.warning(_LOG_FIRST_RECURRING, recurring_trips[0])
            if punctual_trips:
                _LOGGER.warning(_LOG_FIRST_PUNCTUAL, punctual_trips[0])

            return result
        except Exception as err:
            _LOGGER.error(_LOG_ERROR_LISTING, vehicle_id, err, exc_info=True)
            return {
                "vehicle_id": vehicle_id,
                "recurring_trips": [],
                "punctual_trips": [],
                "total_trips": 0,
                "error": str(err),
            }

    return handler


# === Factory: trip_get ===


def make_trip_get_handler(hass: HomeAssistant):
    """Return async handler for trip_get service."""

    async def handler(call: ServiceCall) -> dict[str, Any]:
        _LOGGER.debug(_LOG_HANDLER_TRIP_GET_CALLED)
        _LOGGER.debug(_LOG_CALL_DATA_TRIP_GET, call.data)
        data = call.data
        vehicle_id = data.get("vehicle_id", "unknown")
        trip_id = data.get("trip_id", "unknown")
        _LOGGER.warning(_LOG_TRIP_GET_SERVICE_CALLED, vehicle_id, trip_id)

        mgr = await _get_manager(hass, vehicle_id)
        _LOGGER.debug(_LOG_HANDLER_GET_MANAGER_OK)

        try:
            _LOGGER.warning(_LOG_GETTING_ALL_TO_FIND, trip_id)
            recurring_trips = await mgr._crud.async_get_recurring_trips()
            punctual_trips = await mgr._crud.async_get_punctual_trips()

            _LOGGER.warning(_LOG_FOUND_TRIPS_COUNT, len(recurring_trips), len(punctual_trips))

            all_trips = [*recurring_trips, *punctual_trips]

            _LOGGER.warning(_LOG_SEARCHING_FOR_ID, len(all_trips), trip_id)
            trip_found = None
            for trip in all_trips:
                if str(trip.get("id")) == trip_id:
                    trip_found = trip
                    _LOGGER.warning(_LOG_FOUND_TRIP, trip)
                    break

            if trip_found:
                _LOGGER.debug(_LOG_TRIP_GET_SUCCESS, trip_found)
                return {
                    "vehicle_id": vehicle_id,
                    "trip": trip_found,
                    "found": True,
                }
            else:
                _LOGGER.debug(_LOG_TRIP_GET_NOT_FOUND, trip_id)
                return {
                    "vehicle_id": vehicle_id,
                    "trip": None,
                    "found": False,
                    "error": f"Trip with ID {trip_id} not found",
                }
        except Exception as err:
            _LOGGER.error(_LOG_ERROR_GETTING_TRIP, trip_id, vehicle_id, err, exc_info=True)
            return {
                "vehicle_id": vehicle_id,
                "trip": None,
                "found": False,
                "error": str(err),
            }

    return handler


__all__: list[str] = [
    "trip_id_schema",
    "trip_update_schema",
    "trip_create_schema",
    "make_add_recurring_handler",
    "make_add_punctual_handler",
    "make_trip_create_handler",
    "make_trip_update_handler",
    "make_edit_trip_handler",
    "make_delete_trip_handler",
    "make_pause_recurring_handler",
    "make_resume_recurring_handler",
    "make_complete_punctual_handler",
    "make_cancel_punctual_handler",
    "make_import_weekly_pattern_handler",
    "make_trip_list_handler",
    "make_trip_get_handler",
]
