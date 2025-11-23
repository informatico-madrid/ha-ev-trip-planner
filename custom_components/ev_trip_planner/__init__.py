"""EV Trip Planner Integration for Home Assistant.

Plan your Electric Vehicle trips and optimize charging schedules.
Supports recurring weekly routines and one-time punctual trips.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .trip_manager import TripManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


class TripPlannerCoordinator(DataUpdateCoordinator):
    """Coordinator to manage and update trip data."""

    def __init__(self, hass: HomeAssistant, trip_manager: TripManager) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=30),  # Fallback interval, pero usaremos refresh manual
        )
        self.trip_manager = trip_manager

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch and calculate all trip data from TripManager."""
        try:
            recurring_trips = await self.trip_manager.async_get_recurring_trips()
            punctual_trips = await self.trip_manager.async_get_punctual_trips()
            
            # Calculate Milestone 2 values
            kwh_today = await self.trip_manager.async_get_kwh_needed_today()
            hours_today = await self.trip_manager.async_get_hours_needed_today()
            next_trip = await self.trip_manager.async_get_next_trip()
            
            return {
                "recurring_trips": recurring_trips,
                "punctual_trips": punctual_trips,
                "kwh_today": kwh_today,
                "hours_today": hours_today,
                "next_trip": next_trip,
            }
        except Exception as err:
            _LOGGER.error("Error updating trip data: %s", err)
            return {
                "recurring_trips": [],
                "punctual_trips": [],
                "kwh_today": 0.0,
                "hours_today": 0,
                "next_trip": None,
            }
    
    async def async_refresh_trips(self) -> None:
        """Force refresh of trip data and notify all sensors."""
        await self.async_request_refresh()


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
    
    # Create coordinator for this vehicle
    coordinator = TripPlannerCoordinator(hass, trip_manager)
    await coordinator.async_config_entry_first_refresh()
    
    # Store config, trip_manager AND coordinator
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "trip_manager": trip_manager,
        "coordinator": coordinator,
    }

    # Ensure services use the same TripManager instance for this vehicle
    managers = hass.data[DOMAIN].setdefault("managers", {})
    managers[vehicle_id] = trip_manager
    
    # FIX: Store coordinator by vehicle_id so services can access it
    coordinators = hass.data[DOMAIN].setdefault("coordinators", {})
    coordinators[vehicle_id] = coordinator

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
    
    # FIX: Acceder a los coordinators por vehicle_id
    coordinators: dict[str, TripPlannerCoordinator] = hass.data.setdefault(DOMAIN, {}).setdefault(
        "coordinators", {}
    )

    def _get_manager(vehicle_id: str) -> TripManager:
        mgr = managers.get(vehicle_id)
        if mgr is None:
            mgr = TripManager(hass, vehicle_id)
            managers[vehicle_id] = mgr
        return mgr
    
    # FIX: Función para obtener el coordinator correcto por vehicle_id
    def _get_coordinator(vehicle_id: str) -> TripPlannerCoordinator | None:
        return coordinators.get(vehicle_id)

    async def _ensure_setup(mgr: TripManager) -> None:
        try:
            await mgr.async_setup()
        except Exception:  # pragma: no cover
            # No bloquear servicio por fallo de creación si ya existe
            pass

    async def handle_add_recurring(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = _get_manager(vehicle_id)
        await _ensure_setup(mgr)
        await mgr.async_add_recurring_trip(
            dia_semana=data["dia_semana"],
            hora=data["hora"],
            km=float(data["km"]),
            kwh=float(data["kwh"]),
            descripcion=str(data.get("descripcion", "")),
        )
        # FIX: Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(vehicle_id)
        if coordinator:
            await coordinator.async_refresh_trips()

    async def handle_add_punctual(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = _get_manager(vehicle_id)
        await _ensure_setup(mgr)
        await mgr.async_add_punctual_trip(
            datetime_str=data["datetime"],
            km=float(data["km"]),
            kwh=float(data["kwh"]),
            descripcion=str(data.get("descripcion", "")),
        )
        # FIX: Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(vehicle_id)
        if coordinator:
            await coordinator.async_refresh_trips()

    async def handle_edit_trip(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = _get_manager(vehicle_id)
        await _ensure_setup(mgr)
        await mgr.async_update_trip(str(data["trip_id"]), dict(data["updates"]))
        # FIX: Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(vehicle_id)
        if coordinator:
            await coordinator.async_refresh_trips()

    async def handle_delete_trip(call: ServiceCall) -> None:
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = _get_manager(vehicle_id)
        await _ensure_setup(mgr)
        await mgr.async_delete_trip(str(data["trip_id"]))
        # FIX: Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(vehicle_id)
        if coordinator:
            await coordinator.async_refresh_trips()

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
