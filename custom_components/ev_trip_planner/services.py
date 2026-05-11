"""Service handlers for EV Trip Planner integration.

Transitional shim — imports the original services code from services_orig.py.
The services/ package (with handler factories) is the new implementation.
This file remains for backward-compat direct imports.
"""

from __future__ import annotations

# Re-export everything from the original module for backward compatibility.
# The services/ package provides the handler factory implementations.
from .services_orig import (
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
    register_services,
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
    "register_services",
]
