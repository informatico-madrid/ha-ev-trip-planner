"""Dashboard package — transitional re-exports from dashboard.py.

This package directory exists alongside dashboard.py during the SOLID
decomposition. Re-exports the full public API from the sibling dashboard.py
module to maintain backward-compatible import paths.
"""

from __future__ import annotations

# Re-export everything from the sibling dashboard.py file using importlib
# to avoid circular import (..dashboard resolves to this __init__.py).
import importlib.util as _importlib_util
import os as _os

_pkg_dir = _os.path.dirname(__file__)
_parent_dir = _os.path.dirname(_pkg_dir)
_module_path = _os.path.join(_parent_dir, "dashboard.py")

_spec = _importlib_util.spec_from_file_location("dashboard_file", _module_path)
_dashboard_file = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_dashboard_file)  # type: ignore[union-attr]

# Re-export all public and private names from the dashboard file
for _name in dir(_dashboard_file):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_dashboard_file, _name)

# Also re-export key private names used by tests
_private_names = [
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
    "DashboardConfig",
]
for _name in _private_names:
    if hasattr(_dashboard_file, _name):
        globals()[_name] = getattr(_dashboard_file, _name)

# Clean up internal references
del (
    _dashboard_file,
    _importlib_util,
    _module_path,
    _os,
    _pkg_dir,
    _parent_dir,
    _private_names,
    _spec,
    _name,
)

__all__ = [
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
    "_save_lovelace_dashboard",
    "_validate_dashboard_config",
    "_write_file_content",
    "import_dashboard",
    "is_lovelace_available",
    "dashboard_exists",
    "dashboard_path",
]
