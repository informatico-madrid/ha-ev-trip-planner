"""EV Trip Planner Integration for Home Assistant.

Plan your Electric Vehicle trips and optimize charging schedules.
Supports recurring weekly routines and one-time punctual trips.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Optional

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .trip_manager import TripManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


def is_lovelace_available(hass: HomeAssistant) -> bool:
    """Check if Lovelace UI is available in Home Assistant.

    Returns True if Lovelace is installed and accessible.

    Args:
        hass: The Home Assistant instance.

    Returns:
        True if Lovelace is available, False otherwise.
    """
    # Check if lovelace is in loaded components
    if "lovelace" in hass.config.components:
        return True
    # Also check for the legacy method
    if hass.services.has_service("lovelace", "import"):
        return True
    return False


async def import_dashboard(
    hass: HomeAssistant,
    vehicle_id: str,
    vehicle_name: str,
    use_charts: bool = False,
) -> bool:
    """Import a Lovelace dashboard for the vehicle.

    Uses homeassistant.helpers.importer.async_import_dashboard when available,
    with fallback to storage API for older versions.

    Args:
        hass: The Home Assistant instance.
        vehicle_id: Unique identifier for the vehicle.
        vehicle_name: Display name for the vehicle.
        use_charts: Whether to use full dashboard with charts.

    Returns:
        True if dashboard was imported successfully, False otherwise.
    """
    try:
        # Determine which dashboard template to use (for logging)
        dashboard_type = "full" if use_charts else "simple"
        _LOGGER.info(
            "Importing dashboard for %s (type: %s)",
            vehicle_name,
            dashboard_type,
        )

        # Check if Lovelace is available
        if not is_lovelace_available(hass):
            _LOGGER.warning(
                "Lovelace not available for %s, skipping dashboard import",
                vehicle_name,
            )
            return False

        # Try to use the modern async_import_dashboard helper
        # This is available in newer HA versions (2024.4+)
        try:
            from homeassistant.helpers import importer as importer_module

            if hasattr(importer_module, "async_import_dashboard"):
                dashboard_path = f"ev-trip-planner-{vehicle_id}"
                result = await importer_module.async_import_dashboard(
                    hass,
                    url=dashboard_path,
                    suggest_filename=f"EV Trip Planner - {vehicle_name}",
                )
                _LOGGER.info(
                    "Dashboard imported via async_import_dashboard for %s",
                    vehicle_name,
                )
                return result
        except ImportError:
            _LOGGER.debug(
                "async_import_dashboard not available, using fallback method"
            )

        # Fallback: Use the lovelace.import service (older method)
        # This works for both storage and YAML mode
        if hass.services.has_service("lovelace", "import"):
            await hass.services.async_call(
                "lovelace",
                "import",
                {
                    "url": f"ev-trip-planner-{vehicle_id}",
                    "config": {
                        "title": f"EV Trip Planner - {vehicle_name}",
                        "path": f"ev-trip-planner-{vehicle_id}",
                        "icon": "mdi:car-electric",
                    },
                },
            )
            _LOGGER.info(
                "Dashboard imported via lovelace.import service for %s",
                vehicle_name,
            )
            return True

        _LOGGER.warning(
            "No dashboard import method available for %s", vehicle_name
        )
        return False

    except Exception as err:  # pragma: no cover
        _LOGGER.error("Failed to import dashboard for %s: %s", vehicle_name, err)
        return False


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

    # FIX: Usar namespace con entry_id para runtime_data
    namespace = f"{DOMAIN}_{entry.entry_id}"
    entry.runtime_data.setdefault(namespace, {})
    
    # Create and initialize TripManager for this vehicle
    trip_manager = TripManager(hass, vehicle_id)
    await trip_manager.async_setup()
    
    # Create coordinator for this vehicle
    coordinator = TripPlannerCoordinator(hass, trip_manager)
    await coordinator.async_config_entry_first_refresh()
    
    # Store config, trip_manager AND coordinator
    entry.runtime_data[namespace] = {
        "config": entry.data,
        "trip_manager": trip_manager,
        "coordinator": coordinator,
    }

    # Ensure services use the same TripManager instance for this vehicle
    managers = entry.runtime_data[namespace].setdefault("managers", {})
    managers[vehicle_id] = trip_manager
    
    # FIX: Store coordinator by vehicle_id so services can access it
    coordinators = entry.runtime_data[namespace].setdefault("coordinators", {})
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
        # FIX: Usar namespace con entry_id para limpiar runtime_data
        namespace = f"{DOMAIN}_{entry.entry_id}"
        entry.runtime_data.pop(namespace, None)

    return unload_ok


def register_services(hass: HomeAssistant) -> None:
    """Registrar servicios del dominio ev_trip_planner."""

    async def handle_add_recurring(call: ServiceCall) -> None:
        """Handle adding a recurring trip."""
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = _get_manager(hass, vehicle_id)
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
            await coordinator.async_refresh_trips()

    async def handle_add_punctual(call: ServiceCall) -> None:
        """Handle adding a punctual trip."""
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = _get_manager(hass, vehicle_id)
        await mgr.async_add_punctual_trip(
            datetime_str=data["datetime"],
            km=float(data["km"]),
            kwh=float(data["kwh"]),
            descripcion=str(data.get("descripcion", "")),
        )
        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            await coordinator.async_refresh_trips()

    async def handle_edit_trip(call: ServiceCall) -> None:
        """Handle editing a trip."""
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr.async_update_trip(str(data["trip_id"]), dict(data["updates"]))
        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            await coordinator.async_refresh_trips()

    async def handle_delete_trip(call: ServiceCall) -> None:
        """Handle deleting a trip."""
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr.async_delete_trip(str(data["trip_id"]))
        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            await coordinator.async_refresh_trips()

    async def handle_pause_recurring(call: ServiceCall) -> None:
        """Handle pausing a recurring trip."""
        data = call.data
        mgr = _get_manager(data["vehicle_id"])  # type: ignore[index]
        await _ensure_setup(mgr)
        await mgr.async_pause_recurring_trip(str(data["trip_id"]))

    async def handle_resume_recurring(call: ServiceCall) -> None:
        """Handle resuming a recurring trip."""
        data = call.data
        mgr = _get_manager(data["vehicle_id"])  # type: ignore[index]
        await _ensure_setup(mgr)
        await mgr.async_resume_recurring_trip(str(data["trip_id"]))

    async def handle_complete_punctual(call: ServiceCall) -> None:
        """Handle completing a punctual trip."""
        data = call.data
        mgr = _get_manager(data["vehicle_id"])  # type: ignore[index]
        await _ensure_setup(mgr)
        await mgr.async_complete_punctual_trip(str(data["trip_id"]))

    async def handle_cancel_punctual(call: ServiceCall) -> None:
        """Handle cancelling a punctual trip."""
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

# Helper functions with proper type hints
def _get_manager(hass: HomeAssistant, vehicle_id: str) -> TripManager:
    """Get or create TripManager for vehicle."""
    entry = next(
        (e for e in hass.config_entries.async_entries(DOMAIN) if e.data.get("vehicle_name") == vehicle_id),
        None,
    )
    if not entry:
        raise ValueError(f"Vehicle {vehicle_id} not found in config entries")
    # FIX: Usar namespace con entry_id para acceder a managers
    namespace = f"{DOMAIN}_{entry.entry_id}"
    return entry.runtime_data[namespace]["managers"].get(vehicle_id) or TripManager(hass, vehicle_id)


async def _ensure_setup(mgr: TripManager) -> None:
    """Ensure TripManager is set up before operations."""
    # Check if manager needs setup - call async_setup if not already done
    try:
        await mgr.async_setup()
    except Exception:
        # Already set up or not needed
        pass

@callback
def _get_coordinator(hass: HomeAssistant, vehicle_id: str) -> Optional[TripPlannerCoordinator]:
    """Get coordinator for vehicle."""
    entry = next(
        (e for e in hass.config_entries.async_entries(DOMAIN) if e.data.get("vehicle_name") == vehicle_id),
        None,
    )
    if not entry:
        return None
    # FIX: Usar namespace con entry_id para acceder a coordinators
    namespace = f"{DOMAIN}_{entry.entry_id}"
    return entry.runtime_data[namespace]["coordinators"].get(vehicle_id) if entry else None
