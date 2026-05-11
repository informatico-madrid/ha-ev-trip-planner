"""Dashboard helper functions — re-exported from services_orig.py (transitional)."""

from __future__ import annotations

from ..services_orig import (
    async_import_dashboard_for_entry,
    async_register_panel_for_entry,
    async_register_static_paths,
    create_dashboard_input_helpers,
)

__all__ = [
    "async_import_dashboard_for_entry",
    "async_register_panel_for_entry",
    "async_register_static_paths",
    "create_dashboard_input_helpers",
]
