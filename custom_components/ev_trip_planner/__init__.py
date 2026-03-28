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
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .dashboard import DashboardImportResult
from .dashboard import import_dashboard as import_dashboard
from .dashboard import is_lovelace_available as is_lovelace_available
from .emhass_adapter import EMHASSAdapter
from .panel import async_unregister_panel
from .trip_manager import TripManager

# Type aliases for cleaner signatures
CoordinatorType = DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Global storage for runtime data (compatible with HA versions without runtime_data)
DATA_RUNTIME = f"{DOMAIN}_runtime_data"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


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
        day_options = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
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
            _LOGGER.debug("Created input_datetime for datetime: %s_punctual_datetime", vehicle_id)
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
            _LOGGER.debug("Created input_select for edit: %s_edit_trip_selector", vehicle_id)
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
            _LOGGER.debug("Created input_datetime for edit time: %s_edit_trip_time", vehicle_id)
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
            _LOGGER.debug("Created input_number for edit km: %s_edit_trip_km", vehicle_id)
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
            _LOGGER.debug("Created input_number for edit kwh: %s_edit_trip_kwh", vehicle_id)
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
            _LOGGER.debug("Created input_text for edit desc: %s_edit_trip_desc", vehicle_id)
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
            _LOGGER.debug("Created input_datetime for edit datetime: %s_edit_punctual_datetime", vehicle_id)
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


class TripPlannerCoordinator(DataUpdateCoordinator):
    """Coordinator to manage and update trip data."""

    def __init__(self, hass: HomeAssistant, trip_manager: TripManager) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            # Fallback interval, but we use manual refresh
            update_interval=timedelta(seconds=30),
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


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry to latest schema version.

    This handles schema migrations when configuration format changes.
    Currently V1 is the only version, so we just log the migration.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry to migrate.

    Returns:
        True if migration was successful, False otherwise.
    """
    _LOGGER.info(
        "Migrating config entry from version %s to %s",
        entry.version,
        entry.REQUIRED_VERSION,
    )

    # Migrate data from old format to new format if needed
    new_data = entry.data.copy()
    changed = False

    # Example migration: Convert old 'battery_capacity' to 'battery_capacity_kwh'
    if "battery_capacity" in new_data and "battery_capacity_kwh" not in new_data:
        new_data["battery_capacity_kwh"] = new_data.pop("battery_capacity")
        changed = True
        _LOGGER.info(
            "Migrated battery_capacity to battery_capacity_kwh for vehicle %s",
            new_data.get("vehicle_name"),
        )

    # Update the entry if data changed
    if changed:
        hass.config_entries.async_update_entry(entry, data=new_data)
        _LOGGER.info(
            "Updated config entry data for vehicle %s",
            new_data.get("vehicle_name"),
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EV Trip Planner from a config entry.

    This function is called when a config entry is first added or reloaded.
    It initializes all vehicle-specific components:
    - TripManager for CRUD operations
    - DataUpdateCoordinator for real-time updates
    - EMHASS adapter for energy-aware planning (if configured)
    - Services registration for CRUD operations

    Args:
        hass: The Home Assistant instance.
        entry: The config entry containing vehicle configuration.

    Returns:
        True if setup was successful, False otherwise.
    """
    vehicle_id = entry.data.get("vehicle_name")
    _LOGGER.warning("=== async_setup_entry START === vehicle=%s", vehicle_id)
    _LOGGER.warning("=== async_setup_entry - namespace: %s ===", f"{DOMAIN}_{entry.entry_id}")

    # Use hass.data for runtime storage (compatible with all HA versions)
    namespace = f"{DOMAIN}_{entry.entry_id}"
    hass.data.setdefault(DATA_RUNTIME, {})
    hass.data[DATA_RUNTIME].setdefault(namespace, {})
    
    # Create and initialize TripManager for this vehicle
    _LOGGER.warning("=== async_setup_entry - Creating TripManager ===")
    trip_manager = TripManager(hass, vehicle_id)
    _LOGGER.warning("=== async_setup_entry - Before async_setup - trips: recurring=%d, punctual=%d ===", len(trip_manager._recurring_trips), len(trip_manager._punctual_trips))
    _LOGGER.warning("=== async_setup_entry - Calling await trip_manager.async_setup() ===")
    await trip_manager.async_setup()

    # Create EMHASS adapter for this vehicle (if EMHASS config exists)
    emhass_adapter = None
    has_planning = entry.data.get("planning_horizon_days")
    has_deferrable = entry.data.get("max_deferrable_loads")
    if has_planning or has_deferrable:
        emhass_adapter = EMHASSAdapter(hass, entry.data)
        await emhass_adapter.async_load()
        # Wire EMHASS adapter to trip manager
        trip_manager.set_emhass_adapter(emhass_adapter)
        _LOGGER.info("EMHASS adapter initialized for vehicle %s", vehicle_id)

    # Create coordinator for this vehicle
    coordinator = TripPlannerCoordinator(hass, trip_manager)
    await coordinator.async_config_entry_first_refresh()

    # Register static paths for the native panel (must be done in async_setup_entry)
    from pathlib import Path

    # Try to import StaticPathConfig for HA 2024.7+
    try:
        from homeassistant.components.http import StaticPathConfig

        HAS_STATIC_PATH_CONFIG = True
    except ImportError:
        HAS_STATIC_PATH_CONFIG = False

    component_dir = Path(__file__).parent
    # Use frontend folder for panel files
    panel_js_path = component_dir / "frontend" / "panel.js"
    panel_css_path = component_dir / "frontend" / "panel.css"

    # Build list of static paths to register
    static_paths = []

    # Register the JavaScript file
    if panel_js_path.exists():
        static_paths.append(
            StaticPathConfig("/ev-trip-planner/panel.js", str(panel_js_path), cache_headers=False)
            if HAS_STATIC_PATH_CONFIG
            else ("ev-trip-planner/panel.js", str(panel_js_path), False)
        )
        _LOGGER.info("Registering panel.js at /ev-trip-planner/panel.js from %s (cache_headers=False)", panel_js_path)

    # Register the CSS file
    if panel_css_path.exists():
        static_paths.append(
            StaticPathConfig("/ev_trip_planner/panel.css", str(panel_css_path), cache_headers=False)
            if HAS_STATIC_PATH_CONFIG
            else ("ev_trip_planner/panel.css", str(panel_css_path), False)
        )
        _LOGGER.info("Registering panel.css at ev_trip_planner/panel.css from %s (cache_headers=False)", panel_css_path)

    # Register all static paths
    if static_paths and hass.http is not None:
        try:
            await hass.http.async_register_static_paths(static_paths)
            _LOGGER.info("Registered %d static path(s) for EV Trip Planner panel", len(static_paths))
        except (TypeError, AttributeError) as err:
            # Fallback for different HA versions - use legacy register_static_path
            _LOGGER.warning(
                "async_register_static_paths not available or error: %s, trying legacy method",
                err,
            )
            try:
                for path_spec in static_paths:
                    if isinstance(path_spec, tuple):
                        url_path, file_path, _ = path_spec
                        hass.http.register_static_path(url_path, file_path)
                    else:
                        # StaticPathConfig - try to extract values
                        hass.http.register_static_path(path_spec.path, path_spec.url_path)
                _LOGGER.info("Registered static paths using legacy method")
            except Exception as legacy_err:
                _LOGGER.error(
                    "Failed to register static paths with legacy method: %s",
                    legacy_err,
                )
    elif static_paths:
        _LOGGER.warning("hass.http is None - static paths will be served via panel_custom")

    # Register native panel for this vehicle
    # This creates a sidebar entry in HA without requiring Lovelace
    vehicle_name = entry.data.get("name", vehicle_id)
    try:
        # Import the panel module
        from . import panel as panel_module
        await panel_module.async_register_panel(
            hass,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_name,
        )
    except Exception as err:  # pragma: no cover
        # Log but don't fail - panel registration is optional
        _LOGGER.warning(
            "Could not register native panel for %s: %s",
            vehicle_name,
            err,
        )

    # Store config, trip_manager, coordinator AND emhass_adapter
    hass.data[DATA_RUNTIME][namespace] = {
        "config": entry.data,
        "trip_manager": trip_manager,
        "coordinator": coordinator,
        "emhass_adapter": emhass_adapter,
    }

    # Ensure services use the same TripManager instance for this vehicle
    managers = hass.data[DATA_RUNTIME][namespace].setdefault("managers", {})
    managers[vehicle_id] = trip_manager

    # Store EMHASS adapter for direct access by services
    if emhass_adapter:
        runtime_data = hass.data[DATA_RUNTIME][namespace]
        emhass_adapters = runtime_data.setdefault("emhass_adapters", {})
        emhass_adapters[vehicle_id] = emhass_adapter
    
    # FIX: Store coordinator by vehicle_id so services can access it
    coordinators = hass.data[DATA_RUNTIME][namespace].setdefault("coordinators", {})
    coordinators[vehicle_id] = coordinator

    # Registrar servicios del dominio (idempotente)
    try:
        register_services(hass)
    except Exception:  # pragma: no cover
        _LOGGER.debug("Services already registered or failed to register.")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Create input helpers for dashboard CRUD forms
    # These are required for the dashboard to allow creating trips
    try:
        await create_dashboard_input_helpers(hass, vehicle_id)
    except Exception:  # pragma: no cover
        _LOGGER.debug("Input helpers creation failed or helpers already exist.")

    # Deploy dashboard for the vehicle (FR-002)
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

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    vehicle_id = entry.data.get("vehicle_id", "")
    vehicle_name = entry.data.get("vehicle_name", vehicle_id)

    _LOGGER.info(
        "Unloading EV Trip Planner for vehicle: %s", vehicle_name
    )

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Clean up runtime data
        namespace = f"{DOMAIN}_{entry.entry_id}"
        if DATA_RUNTIME in hass.data:
            hass.data[DATA_RUNTIME].pop(namespace, None)

        # Remove the native panel from sidebar
        if vehicle_id:
            try:
                await async_unregister_panel(hass, vehicle_id)
            except Exception as ex:  # pragma: no cover
                _LOGGER.warning(
                    "Failed to unregister panel for vehicle %s: %s",
                    vehicle_id,
                    ex,
                )

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
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
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
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
            await coordinator.async_refresh_trips()

    async def handle_trip_create(call: ServiceCall) -> None:
        """Handle creating a trip (either recurring or punctual).

        This unified service accepts a 'type' parameter to determine whether
        to create a recurring trip (recurrente) or a punctual trip (puntual).
        """
        data = call.data
        vehicle_id = data["vehicle_id"]
        trip_type = data.get("type", data.get("trip_type", "recurrente"))
        mgr = _get_manager(hass, vehicle_id)

        # Find config entry to get entry_id
        entry = _find_entry_by_vehicle(hass, vehicle_id)
        if not entry:
            _LOGGER.error("Config entry not found for vehicle %s", vehicle_id)
            return

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

        # Get the newly created trip to create sensor
        if trip_type == "recurrente":
            trips = await mgr.async_get_recurring_trips()
            for trip in trips:
                if (trip.get("dia_semana") == data["dia_semana"] and
                    trip.get("hora") == data["hora"] and
                    trip.get("km") == float(data["km"])):
                    # Create trip sensor
                    try:
                        from .sensor import async_create_trip_sensor
                        await async_create_trip_sensor(
                            hass, entry.entry_id, str(trip.get("id")), trip_type, trip
                        )
                    except Exception as err:  # pragma: no cover
                        _LOGGER.warning("Failed to create trip sensor: %s", err)
                    break
        elif trip_type == "puntual":
            trips = await mgr.async_get_punctual_trips()
            for trip in trips:
                if trip.get("datetime") == data["datetime"] and trip.get("km") == float(data["km"]):
                    # Create trip sensor
                    try:
                        from .sensor import async_create_trip_sensor
                        await async_create_trip_sensor(
                            hass, entry.entry_id, str(trip.get("id")), trip_type, trip
                        )
                    except Exception as err:  # pragma: no cover
                        _LOGGER.warning("Failed to create trip sensor: %s", err)
                    break

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

        mgr = _get_manager(hass, vehicle_id)
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
                    await async_update_trip_sensor(hass, entry.entry_id, trip_id, trip)
                    break
        except Exception as err:  # pragma: no cover
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
        mgr = _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)
        await mgr.async_update_trip(str(data["trip_id"]), dict(data["updates"]))
        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
            await coordinator.async_refresh_trips()

    async def handle_delete_trip(call: ServiceCall) -> None:
        """Handle deleting a trip."""
        data = call.data
        vehicle_id = data["vehicle_id"]
        trip_id = str(data["trip_id"])

        # Find config entry to get entry_id
        entry = _find_entry_by_vehicle(hass, vehicle_id)
        if not entry:
            _LOGGER.error("Config entry not found for vehicle %s", vehicle_id)
            return

        mgr = _get_manager(hass, vehicle_id)
        await _ensure_setup(mgr)

        # Delete the trip
        await mgr.async_delete_trip(trip_id)

        # Remove trip sensor
        try:
            from .sensor import async_remove_trip_sensor
            await async_remove_trip_sensor(hass, entry.entry_id, trip_id)
        except Exception as err:  # pragma: no cover
            _LOGGER.warning("Failed to remove trip sensor: %s", err)

        # Refresh coordinator using vehicle_id
        coordinator = _get_coordinator(hass, vehicle_id)
        if coordinator:
            _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
            await coordinator.async_refresh_trips()

    async def handle_pause_recurring(call: ServiceCall) -> None:
        """Handle pausing a recurring trip."""
        data = call.data
        vehicle_id = data["vehicle_id"]
        mgr = _get_manager(hass, vehicle_id)
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
        mgr = _get_manager(hass, vehicle_id)
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
        mgr = _get_manager(hass, vehicle_id)
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
        mgr = _get_manager(hass, vehicle_id)
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
            vol.Required("updates"): dict,
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
    trip_id_schema = vol.Schema({
        vol.Required("vehicle_id"): str,
        vol.Required("trip_id"): str,
    })

    # Schema for unified trip_create service
    trip_create_schema = vol.Schema({
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
        vol.Optional("description", default=""): str,  # Alternative name for compatibility
    })

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
        mgr = _get_manager(hass, data["vehicle_id"])
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

    async def handle_trip_list(call: ServiceCall) -> dict:
        """Handle listing all trips for a vehicle.

        Returns both recurring and punctual trips in a single list.

        Returns a dict with vehicle_id, trips, and total count.
        """
        _LOGGER.warning("=== trip_list SERVICE HANDLER CALLED ===")
        _LOGGER.warning("=== call.data: %s", call.data)
        data = call.data
        vehicle_id = data.get("vehicle_id", "unknown")
        _LOGGER.warning("=== trip_list SERVICE CALLED === vehicle: %s", vehicle_id)

        mgr = _get_manager(hass, vehicle_id)
        # _get_manager already calls async_setup which loads trips from storage
        _LOGGER.warning("=== _get_manager returned manager ===")
        _LOGGER.warning("=== Before async_get_recurring_trips - mgr._recurring_trips: %d",
                     len(mgr._recurring_trips))
        _LOGGER.warning("=== Before async_get_punctual_trips - mgr._punctual_trips: %d",
                     len(mgr._punctual_trips))

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
                _LOGGER.warning("Recurring trip %d: id=%s, tipo=%s, activo=%s",
                           i, trip.get("id"), trip.get("tipo"), trip.get("activo"))

            # Debug: Log each punctual trip
            for i, trip in enumerate(punctual_trips):
                _LOGGER.warning("Punctual trip %d: id=%s, tipo=%s, estado=%s",
                           i, trip.get("id"), trip.get("tipo"), trip.get("estado"))

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
        except Exception as err:  # pragma: no cover
            _LOGGER.error("Error listing trips for vehicle %s: %s", vehicle_id, err, exc_info=True)
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
    trip_list_schema = vol.Schema({
        vol.Required("vehicle_id"): str,
    })

    # Register trip_list service
    hass.services.async_register(
        DOMAIN,
        "trip_list",
        handle_trip_list,
        schema=trip_list_schema,
        supports_response=SupportsResponse.ONLY,
    )

# Helper functions with proper type hints
def _find_entry_by_vehicle(hass: HomeAssistant, vehicle_id: str):
    """Find config entry by vehicle name."""
    return next(
        (e for e in hass.config_entries.async_entries(DOMAIN)
         if e.data.get("vehicle_name") == vehicle_id),
        None,
    )


def _get_manager(hass: HomeAssistant, vehicle_id: str) -> TripManager:
    """Get or create TripManager for vehicle."""
    _LOGGER.info("=== _get_manager START - vehicle_id: %s ===", vehicle_id)
    entry = _find_entry_by_vehicle(hass, vehicle_id)
    if not entry:
        _LOGGER.error("=== _get_manager ERROR - Vehicle %s not found in config entries ===", vehicle_id)
        raise ValueError(f"Vehicle {vehicle_id} not found in config entries")
    _LOGGER.info("=== _get_manager - Found entry: %s, entry_id: %s ===", entry.unique_id, entry.entry_id)

    # Use hass.data for runtime storage
    namespace = f"{DOMAIN}_{entry.entry_id}"
    runtime_data = hass.data.get(DATA_RUNTIME, {})
    _LOGGER.info("=== _get_manager - namespace: %s ===", namespace)
    _LOGGER.info("=== _get_manager - runtime_data keys: %s ===", list(runtime_data.keys()) if runtime_data else "empty")

    # Retrieve from the correct storage location where trip_manager is stored
    trip_manager = runtime_data.get(namespace, {}).get("trip_manager")
    _LOGGER.info("=== _get_manager - trip_manager from runtime_data: %s ===", trip_manager)

    # If manager not found in runtime storage, create new one and load from HA storage
    if not trip_manager:
        _LOGGER.info("=== _get_manager - Creating new TripManager for vehicle %s ===", vehicle_id)
        trip_manager = TripManager(hass, vehicle_id)
        _LOGGER.info("=== _get_manager - Before async_setup - trips: recurring=%d, punctual=%d ===",
                     len(trip_manager._recurring_trips), len(trip_manager._punctual_trips))

        # Load trips from HA storage - use hass.loop.run_until_complete
        # This is safe because we're in the callback, not inside an async context
        try:
            _LOGGER.info("=== _get_manager - Calling hass.loop.run_until_complete(trip_manager.async_setup()) ===")
            hass.loop.run_until_complete(trip_manager.async_setup())
            _LOGGER.info("=== _get_manager - After async_setup - trips: recurring=%d, punctual=%d ===",
                         len(trip_manager._recurring_trips), len(trip_manager._punctual_trips))
        except Exception as setup_err:
            _LOGGER.error("=== _get_manager - Error setting up manager for %s: %s ===", vehicle_id, setup_err, exc_info=True)

        # Save manager back to runtime storage for future calls
        if namespace not in runtime_data:
            runtime_data[namespace] = {}
        runtime_data[namespace]["trip_manager"] = trip_manager
        _LOGGER.info("=== _get_manager - Manager saved to runtime_data ===")
        _LOGGER.info("=== _get_manager - Manager created and set up for %s ===", vehicle_id)
        _LOGGER.info("=== _get_manager - Trips loaded: %d recurring, %d punctual ===",
                     len(trip_manager._recurring_trips), len(trip_manager._punctual_trips))
    else:
        _LOGGER.info("=== _get_manager - Manager already exists for %s, trips: %d recurring, %d punctual ===",
                     vehicle_id, len(trip_manager._recurring_trips), len(trip_manager._punctual_trips))

    _LOGGER.info("=== _get_manager END - returning manager for vehicle %s ===", vehicle_id)
    return trip_manager


async def _ensure_setup(mgr: TripManager) -> None:
    """Ensure TripManager is set up before operations."""
    # Check if manager needs setup - call async_setup if not already done
    try:
        await mgr.async_setup()
    except Exception:
        # Already set up or not needed
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
    # Use hass.data for runtime storage
    namespace = f"{DOMAIN}_{entry.entry_id}"
    runtime_data = hass.data.get(DATA_RUNTIME, {})
    coordinators = runtime_data.get(namespace, {}).get("coordinators", {})
    return coordinators.get(vehicle_id) if entry else None


def _get_emhass_adapter(
    hass: HomeAssistant,
    vehicle_id: str,
) -> Optional[EMHASSAdapter]:
    """Get EMHASS adapter for vehicle."""
    entry = _find_entry_by_vehicle(hass, vehicle_id)
    if not entry:
        return None
    namespace = f"{DOMAIN}_{entry.entry_id}"
    runtime_data = hass.data.get(DATA_RUNTIME, {})
    emhass_adapters = runtime_data.get(namespace, {}).get("emhass_adapters", {})
    return emhass_adapters.get(vehicle_id)
