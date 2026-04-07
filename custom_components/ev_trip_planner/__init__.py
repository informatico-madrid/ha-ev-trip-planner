"""EV Trip Planner Integration for Home Assistant.

Plan your Electric Vehicle trips and optimize charging schedules.
Supports recurring weekly routines and one-time punctual trips.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeAlias

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import async_migrate_entries
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

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


PLATFORMS: list[Platform] = [Platform.SENSOR]


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

    if changed:
        hass.config_entries.async_update_entry(entry, data=new_data)
        runtime_data = getattr(entry, "runtime_data", None)
        emhass_adapter = getattr(runtime_data, "emhass_adapter", None) if runtime_data else None
        if emhass_adapter:
            await emhass_adapter.update_charging_power()

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EV Trip Planner from a config entry."""
    vehicle_id = entry.data.get("vehicle_name").lower().replace(" ", "_")
    vehicle_name = entry.data.get("vehicle_name", vehicle_id)

    await async_cleanup_stale_storage(hass, vehicle_id)
    await async_cleanup_orphaned_emhass_sensors(hass)
    await async_register_static_paths(hass)

    presence_config = build_presence_config(entry)
    trip_manager = TripManager(hass, vehicle_id, presence_config)
    await trip_manager.async_setup()

    soc_sensor = entry.data.get("soc_sensor")
    if soc_sensor and hasattr(trip_manager, "vehicle_controller") and trip_manager.vehicle_controller._presence_monitor:
        trip_manager.vehicle_controller._presence_monitor._async_setup_soc_listener()

    emhass_adapter = None
    if entry.data.get("planning_horizon_days") or entry.data.get("max_deferrable_loads"):
        emhass_adapter = EMHASSAdapter(hass, entry)
        await emhass_adapter.async_load()
        trip_manager.set_emhass_adapter(emhass_adapter)

    coordinator = TripPlannerCoordinator(hass, entry, trip_manager, emhass_adapter)
    await coordinator.async_config_entry_first_refresh()
    await async_register_panel_for_entry(hass, entry, vehicle_id, vehicle_name)

    # Store runtime data using entry.runtime_data (HA-recommended pattern)
    entry.runtime_data = EVTripRuntimeData(
        coordinator=coordinator,
        trip_manager=trip_manager,
        emhass_adapter=emhass_adapter,
    )

    register_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await create_dashboard_input_helpers(hass, vehicle_id)
    await async_import_dashboard_for_entry(hass, entry, vehicle_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    vehicle_id = entry.data.get("vehicle_name").lower().replace(" ", "_")
    vehicle_name = entry.data.get("vehicle_name", vehicle_id)
    unload_ok = await async_unload_entry_cleanup(hass, entry, vehicle_id, vehicle_name)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry and all its data."""
    await async_remove_entry_cleanup(hass, entry)
