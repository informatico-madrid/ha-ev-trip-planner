"""Services package — transitional re-export shim.

All public names are re-exported from the original services module.
Sub-modules break out logical groupings; the original services.py
remains the canonical source until Phase 3 (move code).
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, SupportsResponse

from ..services_orig import (
    PLATFORMS,
    CoordinatorType,
    async_cleanup_orphaned_emhass_sensors,
    async_cleanup_stale_storage,
    async_import_dashboard_for_entry,
    async_register_panel_for_entry,
    async_register_static_paths,
    async_remove_entry_cleanup,
    async_unload_entry_cleanup,
    build_presence_config,
    create_dashboard_input_helpers,
)
from ._handler_factories import (
    make_add_recurring_handler,
    make_add_punctual_handler,
    make_cancel_punctual_handler,
    make_complete_punctual_handler,
    make_delete_trip_handler,
    make_edit_trip_handler,
    make_import_weekly_pattern_handler,
    make_pause_recurring_handler,
    make_resume_recurring_handler,
    make_trip_create_handler,
    make_trip_get_handler,
    make_trip_list_handler,
    make_trip_update_handler,
    trip_create_schema,
    trip_id_schema,
    trip_update_schema,
)

__all__ = [
    "PLATFORMS",
    "CoordinatorType",
    "async_cleanup_orphaned_emhass_sensors",
    "async_cleanup_stale_storage",
    "async_import_dashboard_for_entry",
    "async_register_panel_for_entry",
    "async_register_static_paths",
    "async_remove_entry_cleanup",
    "async_unload_entry_cleanup",
    "build_presence_config",
    "create_dashboard_input_helpers",
    "make_add_recurring_handler",
    "make_add_punctual_handler",
    "make_cancel_punctual_handler",
    "make_complete_punctual_handler",
    "make_delete_trip_handler",
    "make_edit_trip_handler",
    "make_import_weekly_pattern_handler",
    "make_pause_recurring_handler",
    "make_resume_recurring_handler",
    "make_trip_create_handler",
    "make_trip_get_handler",
    "make_trip_list_handler",
    "make_trip_update_handler",
    "register_services",
    "trip_create_schema",
    "trip_id_schema",
    "trip_update_schema",
]


def register_services(hass: HomeAssistant) -> None:
    """Register all ev_trip_planner services using handler factories.

    This transitional shim delegates to factory functions in
    _handler_factories.py. Each factory returns the async handler
    that closes over hass for service operations.
    """
    hass.services.async_register(
        "ev_trip_planner",
        "add_recurring_trip",
        make_add_recurring_handler(hass),
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
        "ev_trip_planner",
        "add_punctual_trip",
        make_add_punctual_handler(hass),
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
        "ev_trip_planner",
        "edit_trip",
        make_edit_trip_handler(hass),
        schema=vol.Schema(
            {
                vol.Required("vehicle_id"): str,
                vol.Required("trip_id"): str,
                vol.Required("updates"): dict,
            }
        ),
    )
    hass.services.async_register(
        "ev_trip_planner",
        "trip_update",
        make_trip_update_handler(hass),
        schema=trip_update_schema,
    )
    hass.services.async_register(
        "ev_trip_planner",
        "trip_create",
        make_trip_create_handler(hass),
        schema=trip_create_schema,
    )
    hass.services.async_register(
        "ev_trip_planner",
        "delete_trip",
        make_delete_trip_handler(hass),
        schema=trip_id_schema,
    )
    hass.services.async_register(
        "ev_trip_planner",
        "pause_recurring_trip",
        make_pause_recurring_handler(hass),
        schema=trip_id_schema,
    )
    hass.services.async_register(
        "ev_trip_planner",
        "resume_recurring_trip",
        make_resume_recurring_handler(hass),
        schema=trip_id_schema,
    )
    hass.services.async_register(
        "ev_trip_planner",
        "complete_punctual_trip",
        make_complete_punctual_handler(hass),
        schema=trip_id_schema,
    )
    hass.services.async_register(
        "ev_trip_planner",
        "cancel_punctual_trip",
        make_cancel_punctual_handler(hass),
        schema=trip_id_schema,
    )
    hass.services.async_register(
        "ev_trip_planner",
        "import_from_weekly_pattern",
        make_import_weekly_pattern_handler(hass),
        schema=vol.Schema(
            {
                vol.Required("vehicle_id"): str,
                vol.Required("pattern"): dict,
                vol.Optional("clear_existing", default=True): bool,
            }
        ),
    )
    hass.services.async_register(
        "ev_trip_planner",
        "trip_list",
        make_trip_list_handler(hass),
        schema=vol.Schema({vol.Required("vehicle_id"): str}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        "ev_trip_planner",
        "trip_get",
        make_trip_get_handler(hass),
        schema=vol.Schema(
            {
                vol.Required("vehicle_id"): str,
                vol.Required("trip_id"): str,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
