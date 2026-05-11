"""Dashboard package — transitional re-exports from dashboard.py.

This package directory exists alongside dashboard.py during the SOLID
decomposition. Re-exports the full public API from the sibling dashboard.py
module to maintain backward-compatible import paths.

Shared classes are defined here to avoid circular imports with template_manager.
"""

from __future__ import annotations

from typing import Any, Optional


# ============================================================================
# Shared classes (defined before importlib to avoid circular imports)
# ============================================================================


class DashboardError(Exception):
    """Base exception for dashboard-related errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        """Initialize the dashboard error.

        Args:
            message: Human-readable error message.
            details: Optional additional error details.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DashboardNotFoundError(DashboardError):
    """Raised when a dashboard template is not found."""

    def __init__(self, template_file: str, searched_paths: list[str]) -> None:
        """Initialize the dashboard not found error.

        Args:
            template_file: The template file that was not found.
            searched_paths: List of paths that were searched.
        """
        message = f"Dashboard template not found: {template_file}"
        super().__init__(
            message,
            {
                "template_file": template_file,
                "searched_paths": searched_paths,
                "error_type": "template_not_found",
            },
        )


class DashboardValidationError(DashboardError):
    """Raised when a dashboard configuration fails validation."""

    def __init__(self, error_type: str, validation_message: str) -> None:
        """Initialize the dashboard validation error.

        Args:
            error_type: The type of validation error.
            validation_message: The validation error message.
        """
        message = f"Dashboard validation failed: {validation_message}"
        super().__init__(
            message,
            {
                "error_type": error_type,
                "validation_message": validation_message,
            },
        )


class DashboardStorageError(DashboardError):
    """Raised when dashboard storage fails."""

    def __init__(self, storage_method: str, error: str) -> None:
        """Initialize the dashboard storage error.

        Args:
            storage_method: The storage method that failed.
            error: The storage error message.
        """
        message = f"Dashboard storage failed for {storage_method}: {error}"
        super().__init__(
            message,
            {
                "storage_method": storage_method,
                "error": error,
                "error_type": "storage_error",
            },
        )


class DashboardImportResult:
    """Structured result from dashboard import operations."""

    def __init__(
        self,
        success: bool,
        vehicle_id: str,
        vehicle_name: str,
        error: Optional[str] = None,
        error_details: Optional[dict[str, Any]] = None,
        dashboard_type: str = "simple",
        storage_method: str = "unknown",
    ) -> None:
        """Initialize the dashboard import result.

        Args:
            success: Whether the dashboard import was successful.
            vehicle_id: The vehicle ID.
            vehicle_name: The vehicle name.
            error: Error message if import failed.
            error_details: Additional error details.
            dashboard_type: Type of dashboard imported (simple/full).
            storage_method: Method used for storage (storage/YAML).
        """
        self.success = success
        self.vehicle_id = vehicle_id
        self.vehicle_name = vehicle_name
        self.error = error
        self.error_details = error_details or {}
        self.dashboard_type = dashboard_type
        self.storage_method = storage_method

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "vehicle_id": self.vehicle_id,
            "vehicle_name": self.vehicle_name,
            "error": self.error,
            "error_details": self.error_details,
            "dashboard_type": self.dashboard_type,
            "storage_method": self.storage_method,
        }

    def __str__(self) -> str:
        """String representation of the import result."""
        status = "SUCCESS" if self.success else "FAILED"
        result = f"[Dashboard Import {status}] Vehicle: {self.vehicle_name} ({self.vehicle_id})"
        if not self.success:
            result += f"\n  Error: {self.error}"
            if self.error_details:
                result += f"\n  Details: {self.error_details}"
        return result


# ============================================================================
# Importlib re-export from sibling dashboard.py
# ============================================================================

import importlib.util as _importlib_util
import os as _os

_pkg_dir = _os.path.dirname(__file__)
_parent_dir = _os.path.dirname(_pkg_dir)
_module_path = _os.path.join(_parent_dir, "dashboard.py")

_spec = _importlib_util.spec_from_file_location("dashboard_file", _module_path)
_dashboard_file = _importlib_util.module_from_spec(_spec)  # type: ignore[assignment]
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
]
