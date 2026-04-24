"""EV Trip Planner Integration for Home Assistant.

Plan your Electric Vehicle trips and optimize charging schedules.
Supports recurring weekly routines and one-time punctual trips.
"""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, TypeAlias

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import async_migrate_entries
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN  # noqa: F401
from .coordinator import TripPlannerCoordinator
from .emhass_adapter import EMHASSAdapter
from .panel import async_unregister_panel  # noqa: F401 (re-export for tests)
from .services import (
    async_cleanup_orphaned_emhass_sensors,
    async_cleanup_stale_storage,
    async_import_dashboard_for_entry,
    async_register_panel_for_entry,
    async_register_static_paths,
    async_remove_entry_cleanup,
    async_unload_entry_cleanup,
    build_presence_config,
    create_dashboard_input_helpers,
    register_services,
)
from .trip_manager import TripManager
from .utils import normalize_vehicle_id
from .yaml_trip_storage import YamlTripStorage

# Type aliases for cleaner signatures
CoordinatorType: TypeAlias = DataUpdateCoordinator[dict[str, Any]]

_LOGGER = logging.getLogger(__name__)



@dataclass
class EVTripRuntimeData:
    """Runtime data container for a single vehicle config entry."""

    coordinator: Any
    trip_manager: TripManager | None = None
    sensor_async_add_entities: (
        Callable[[list[SensorEntity], bool], Awaitable[None]] | None
    ) = None
    emhass_adapter: Any = None
    # T3.1: Timer handle for hourly refresh — must be cancelled on unload to prevent EC-001 leak
    hourly_refresh_cancel: Callable[[], None] | None = None


PLATFORMS: list[Platform] = [Platform.SENSOR]


async def _hourly_refresh_callback(now: datetime, runtime_data: EVTripRuntimeData) -> None:
    """Hourly callback to refresh deferrable loads profile.
    
    This callback is called every hour to trigger rotation of recurring trips.
    The timer is registered in async_setup_entry and cleaned up in async_unload_entry.
    """
    try:
        if runtime_data.trip_manager:
            await runtime_data.trip_manager.publish_deferrable_loads()
    except Exception as err:
        _LOGGER.warning("Hourly profile refresh failed: %s", err)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry to latest schema version."""
    new_data = entry.data.copy()
    changed = False

    # Migrate from version 1 to version 2
    if entry.version < 2:
        # battery_capacity field rename
        if "battery_capacity" in new_data and "battery_capacity_kwh" not in new_data:
            new_data["battery_capacity_kwh"] = new_data.pop("battery_capacity")
            changed = True

        # Migrate entity registry unique_ids from old format (no vehicle_id) to new format (with vehicle_id)
        vehicle_id = entry.data.get("vehicle_name", "").lower().replace(" ", "_")
        if vehicle_id:

            def migrate_unique_id(old_entry: er.RegistryEntry) -> dict[str, Any] | None:
                # OLD: "ev_trip_planner_kwh_today"
                # NEW: "ev_trip_planner_{vehicle_id}_kwh_today"
                old_uid = old_entry.unique_id
                if old_uid.startswith(f"{DOMAIN}_") and f"{DOMAIN}_{vehicle_id}_" not in old_uid:
                    new_uid = f"{DOMAIN}_{vehicle_id}_{old_uid[len(f"{DOMAIN}_"):]}"
                    return {"new_unique_id": new_uid}
                return None

            await async_migrate_entries(hass, entry.entry_id, migrate_unique_id)

    # Always update version to 2 when migrating from version < 2
    hass.config_entries.async_update_entry(entry, data=new_data, version=2)
    if changed:
        runtime_data = getattr(entry, "runtime_data", None)
        emhass_adapter = getattr(runtime_data, "emhass_adapter", None) if runtime_data else None
        if emhass_adapter:
            await emhass_adapter.update_charging_power()

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EV Trip Planner from a config entry."""
    vehicle_name_raw = entry.data.get("vehicle_name") or ""
    vehicle_id = normalize_vehicle_id(vehicle_name_raw)
    vehicle_name = vehicle_name_raw or vehicle_id

    await async_cleanup_stale_storage(hass, vehicle_id)
    await async_cleanup_orphaned_emhass_sensors(hass)
    await async_register_static_paths(hass)

    presence_config = build_presence_config(entry)
    # Use YamlTripStorage for consistent storage mechanism
    storage = YamlTripStorage(hass, vehicle_id)
    trip_manager = TripManager(hass, vehicle_id, entry.entry_id, presence_config, storage)
    await trip_manager.async_setup()

    soc_sensor = entry.data.get("soc_sensor")
    if soc_sensor and hasattr(trip_manager, "vehicle_controller") and trip_manager.vehicle_controller._presence_monitor:
        trip_manager.vehicle_controller._presence_monitor._async_setup_soc_listener()

    emhass_adapter = None
    if entry.data.get("planning_horizon_days") or entry.data.get("max_deferrable_loads"):
        emhass_adapter = EMHASSAdapter(hass, entry)
        await emhass_adapter.async_load()
        # FR-2, AC-1.2: Set up config entry listener for charging power updates
        emhass_adapter.setup_config_entry_listener()
        trip_manager.set_emhass_adapter(emhass_adapter)

    # Create coordinator BEFORE publishing to EMHASS, so sensor platform setup
    # always has a coordinator reference (even if empty EMHASS data initially).
    coordinator = TripPlannerCoordinator(hass, entry, trip_manager, emhass_adapter)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        raise  # Re-raise to allow HA's built-in retry mechanism

    # Store runtime data using entry.runtime_data (HA-recommended pattern)
    # Must be assigned BEFORE publish_deferrable_loads so that the publish path
    # can safely access entry.runtime_data without a None race condition.
    entry.runtime_data = EVTripRuntimeData(
        coordinator=coordinator,
        trip_manager=trip_manager,
        emhass_adapter=emhass_adapter,
    )

    # Now that coordinator and runtime_data are ready, publish loaded trips to EMHASS.
    # This populates the EMHASS cache and triggers a coordinator refresh
    # so sensors see the correct data immediately (not waiting for periodic refresh).
    if emhass_adapter is not None:
        await trip_manager.publish_deferrable_loads()
    await async_register_panel_for_entry(hass, entry, vehicle_id, vehicle_name)
    
    # T3.1: Setup hourly refresh timer OUTSIDE coordinator
    # This timer triggers every hour to rotate recurring trips
    # Timer is registered here to avoid infinite loop in coordinator
    # Use module-level _hourly_refresh_callback for testability
    # EC-001 FIX: Save cancel handle to prevent timer leak on unload
    runtime_data = entry.runtime_data
    runtime_data.hourly_refresh_cancel = async_track_time_interval(
        hass,
        functools.partial(_hourly_refresh_callback, runtime_data=runtime_data),
        timedelta(hours=1),
    )

    register_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await create_dashboard_input_helpers(hass, vehicle_id)
    await async_import_dashboard_for_entry(hass, entry, vehicle_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # EC-001 FIX: Cancel hourly refresh timer BEFORE cleanup to prevent leak
    runtime_data = getattr(entry, "runtime_data", None)
    if runtime_data and hasattr(runtime_data, "hourly_refresh_cancel") and runtime_data.hourly_refresh_cancel:
        runtime_data.hourly_refresh_cancel()
        runtime_data.hourly_refresh_cancel = None
        _LOGGER.debug("Cancelled hourly refresh timer for vehicle %s", entry.entry_id)
    
    vehicle_name_raw = entry.data.get("vehicle_name") or ""
    vehicle_id = normalize_vehicle_id(vehicle_name_raw)
    vehicle_name = vehicle_name_raw or vehicle_id
    unload_ok = await async_unload_entry_cleanup(hass, entry, vehicle_id, vehicle_name)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry and all its data."""
    await async_remove_entry_cleanup(hass, entry)
