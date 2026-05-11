"""Dashboard module — transitional re-exports from dashboard package.

This file exists alongside the dashboard/ package directory. During the SOLID
decomposition, the full implementation lives in the sub-modules. This file
re-exports everything from the package to maintain backward-compatible import
paths (e.g., tests that patch ``dashboard.import_dashboard``).

Note: When both dashboard.py and dashboard/ directory exist, Python's import
resolution prefers the package directory. This shim exists only so that code
which explicitly imports from the .py file still works.
"""

from __future__ import annotations

# Re-export everything from the dashboard package for backward compatibility.
# Any code that does ``from custom_components.ev_trip_planner.dashboard import foo``
# will get these re-exports transparently.
from custom_components.ev_trip_planner.dashboard import (  # noqa: F401,F403
    DashboardBuilder,
    DashboardConfig,
    DashboardError,
    DashboardImportResult,
    DashboardNotFoundError,
    DashboardStorageError,
    DashboardValidationError,
    _await_executor_result,
    _call_async_executor_sync,
    _check_path_exists,
    _create_directory,
    _load_dashboard_template,
    _read_file_content,
    _save_dashboard_yaml_fallback,
    _save_lovelace_dashboard,
    _validate_dashboard_config,
    _verify_storage_permissions,
    _write_file_content,
    dashboard_exists,
    dashboard_path,
    import_dashboard,
    is_lovelace_available,
)

__all__ = [
    "DashboardBuilder",
    "DashboardConfig",
    "DashboardError",
    "DashboardImportResult",
    "DashboardNotFoundError",
    "DashboardStorageError",
    "DashboardValidationError",
    "_await_executor_result",
    "_call_async_executor_sync",
    "_check_path_exists",
    "_create_directory",
    "_load_dashboard_template",
    "_read_file_content",
    "_save_dashboard_yaml_fallback",
    "_save_lovelace_dashboard",
    "_validate_dashboard_config",
    "_verify_storage_permissions",
    "_write_file_content",
    "dashboard_exists",
    "dashboard_path",
    "import_dashboard",
    "is_lovelace_available",
]
