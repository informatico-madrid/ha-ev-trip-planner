"""Services package — transitional re-export shim.

All public names are re-exported from the original services module.
Sub-modules break out logical groupings; the original services.py
remains the canonical source until Phase 3 (move code).
"""

from __future__ import annotations

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
