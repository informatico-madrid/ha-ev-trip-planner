"""Service handlers for EV Trip Planner integration — transitional shim.

The package services/ contains the actual implementation:
- _handler_factories.py: handler factory closures
- __init__.py: register_services() using factories + re-exports

This module exists for backward compatibility. Direct imports of
register_services, PLATFORMS, etc. still work via the package.
"""

from __future__ import annotations

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
