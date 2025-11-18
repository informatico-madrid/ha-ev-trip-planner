"""EV Trip Planner Integration for Home Assistant.

Plan your Electric Vehicle trips and optimize charging schedules.
Supports recurring weekly routines and one-time punctual trips.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .trip_manager import TripManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the EV Trip Planner component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EV Trip Planner from a config entry."""
    vehicle_id = entry.data.get("vehicle_name")
    _LOGGER.info("Setting up EV Trip Planner for vehicle: %s", vehicle_id)

    hass.data.setdefault(DOMAIN, {})
    
    # Create and initialize TripManager for this vehicle
    trip_manager = TripManager(hass, vehicle_id)
    await trip_manager.async_setup()
    
    # Store both config and trip_manager
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "trip_manager": trip_manager,
    }

    # Ensure services use the same TripManager instance for this vehicle
    managers = hass.data[DOMAIN].setdefault("managers", {})
    managers[vehicle_id] = trip_manager

    # Registrar servicios del dominio (idempotente)
    try:
        register_services(hass)
    except Exception:  # pragma: no cover
        _LOGGER.debug("Services already registered or failed to register.")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info(
        "Unloading EV Trip Planner for vehicle: %s", entry.data.get("vehicle_name")
    )

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def register_services(hass: HomeAssistant) -> None:
    """Registrar servicios del dominio ev_trip_planner."""

    managers: dict[str, TripManager] = hass.data.setdefault(DOMAIN, {}).setdefault(
        "managers", {}
    )

    def _get_manager(vehicle_id: str) -> TripManager:
        mgr = managers.get(vehicle_id)
        if mgr is None:
            mgr = TripManager(hass, vehicle_id)
            managers[vehicle_id] = mgr
        return mgr

    async def _ensure_setup(mgr: TripManager) -> None:
        try:
            await mgr.async_setup()
        except Exception:  # pragma: no cover
            # No bloquear servicio por fallo de creación si ya existe
            pass

    async def handle_add_recurring(call: ServiceCall) -> None:
        data = call.data
        mgr = _get_manager(data["vehicle_id"])  # type: ignore[index]
        await _ensure_setup(mgr)
        await mgr.async_add_recurring_trip(
            dia_semana=data["dia_semana"],
            hora=data["hora"],
            km=float(data["km"]),
            kwh=float(data["kwh"]),
            descripcion=str(data.get("descripcion", "")),
        )

    async def handle_add_punctual(call: ServiceCall) -> None:
        data = call.data
        mgr = _get_manager(data["vehicle_id"])  # type: ignore[index]
        await _ensure_setup(mgr)
        await mgr.async_add_punctual_trip(
            datetime_str=data["datetime"],
            km=float(data["km"]),
            kwh=float(data["kwh"]),
            descripcion=str(data.get("descripcion", "")),
        )

    async def handle_edit_trip(call: ServiceCall) -> None:
        data = call.data
        mgr = _get_manager(data["vehicle_id"])  # type: ignore[index]
        await _ensure_setup(mgr)
        await mgr.async_update_trip(str(data["trip_id"]), dict(data["updates"]))

    async def handle_delete_trip(call: ServiceCall) -> None:
        data = call.data
        mgr = _get_manager(data["vehicle_id"])  # type: ignore[index]
        await _ensure_setup(mgr)
        await mgr.async_delete_trip(str(data["trip_id"]))

    async def handle_pause_recurring(call: ServiceCall) -> None:
        data = call.data
        mgr = _get_manager(data["vehicle_id"])  # type: ignore[index]
        await _ensure_setup(mgr)
        await mgr.async_pause_recurring_trip(str(data["trip_id"]))

    async def handle_resume_recurring(call: ServiceCall) -> None:
        data = call.data
        mgr = _get_manager(data["vehicle_id"])  # type: ignore[index]
        await _ensure_setup(mgr)
        await mgr.async_resume_recurring_trip(str(data["trip_id"]))

    async def handle_complete_punctual(call: ServiceCall) -> None:
        data = call.data
        mgr = _get_manager(data["vehicle_id"])  # type: ignore[index]
        await _ensure_setup(mgr)
        await mgr.async_complete_punctual_trip(str(data["trip_id"]))

    async def handle_cancel_punctual(call: ServiceCall) -> None:
        data = call.data
        mgr = _get_manager(data["vehicle_id"])  # type: ignore[index]
        await _ensure_setup(mgr)
        await mgr.async_cancel_punctual_trip(str(data["trip_id"]))

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
    hass.services.async_register(
        DOMAIN,
        "delete_trip",
        handle_delete_trip,
        schema=vol.Schema({vol.Required("vehicle_id"): str, vol.Required("trip_id"): str}),
    )
    hass.services.async_register(
        DOMAIN,
        "pause_recurring_trip",
        handle_pause_recurring,
        schema=vol.Schema({vol.Required("vehicle_id"): str, vol.Required("trip_id"): str}),
    )
    hass.services.async_register(
        DOMAIN,
        "resume_recurring_trip",
        handle_resume_recurring,
        schema=vol.Schema({vol.Required("vehicle_id"): str, vol.Required("trip_id"): str}),
    )
    hass.services.async_register(
        DOMAIN,
        "complete_punctual_trip",
        handle_complete_punctual,
        schema=vol.Schema({vol.Required("vehicle_id"): str, vol.Required("trip_id"): str}),
    )
    hass.services.async_register(
        DOMAIN,
        "cancel_punctual_trip",
        handle_cancel_punctual,
        schema=vol.Schema({vol.Required("vehicle_id"): str, vol.Required("trip_id"): str}),
    )

    async def handle_import_weekly_pattern(call: ServiceCall) -> None:
        data = call.data
        mgr = _get_manager(data["vehicle_id"])  # type: ignore[index]
        await _ensure_setup(mgr)

        clear_existing = bool(data.get("clear_existing", True))
        pattern: dict = dict(data["pattern"])  # type: ignore[assignment]

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
