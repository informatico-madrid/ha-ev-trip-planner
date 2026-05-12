"""Diagnostics support for EV Trip Planner integration.

Provides diagnostic data for Home Assistant's integration diagnostics API.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

# Keys to redact for privacy
REDACT_KEYS = [
    "vehicle_name",
    "soc_sensor",
    "range_sensor",
]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.

    Returns:
        Dict containing diagnostic data.
    """
    # Get runtime data from entry
    runtime_data = getattr(entry, "runtime_data", None)

    # Extract available data
    coordinator = getattr(runtime_data, "coordinator", None) if runtime_data else None
    trip_manager = getattr(runtime_data, "trip_manager", None) if runtime_data else None
    emhass_adapter = (
        getattr(runtime_data, "emhass_adapter", None) if runtime_data else None
    )

    # Build diagnostics dict
    diagnostics_data = {
        "entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "data": async_redact_data(entry.data, REDACT_KEYS),
        },
        "coordinator": {
            "data_keys": list(coordinator.data.keys())
            if coordinator and coordinator.data
            else [],
            "last_update_success": coordinator.last_update_success
            if coordinator
            else None,
        },
        "trip_manager": {
            "vehicle_id": trip_manager._state.vehicle_id if trip_manager else None,
            "recurring_trips_count": len(trip_manager._state.recurring_trips)
            if trip_manager
            else 0,
            "punctual_trips_count": len(trip_manager._state.punctual_trips)
            if trip_manager
            else 0,
        },
    }

    # Add EMHASS data if available
    if emhass_adapter:
        diagnostics_data["emhass"] = {
            "vehicle_id": emhass_adapter.vehicle_id,
            "index_map": emhass_adapter._index_map,
            "available_indices": emhass_adapter._available_indices,
        }

    return diagnostics_data
