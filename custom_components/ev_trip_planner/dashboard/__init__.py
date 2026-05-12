# qg-accepted: BMAD consensus 2026-05-12 — AP23 FALSE POSITIVE: This file uses standard
#   Python re-export packaging (``from .importer import X`` + ``__all__``), NOT code
#   duplication. The Tier A checker conflates import statements with code definitions.
#   See specs/3-solid-refactor/consensus-party-verdict.md for details.

"""Dashboard package — SOLID decomposition of dashboard.py.

This package replaces the legacy dashboard.py module. All public API names
are re-exported from sub-modules for backward-compatible import paths.

Shared exception classes are defined here at the top to avoid circular imports
with sub-modules (template_manager, importer) which import them via ``from . import``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

# ============================================================================
# Shared classes — MUST be defined before sub-module imports
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


@dataclass
class DashboardImportResult:
    """Structured result from dashboard import operations."""

    success: bool
    vehicle_id: str
    vehicle_name: str
    error: Optional[str] = None
    error_details: Optional[dict[str, Any]] = None
    dashboard_type: str = "simple"
    storage_method: str = "unknown"

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
# Sub-module re-exports
# ============================================================================

from .builder import DashboardBuilder  # noqa: E402
from .importer import (  # noqa: E402
    DashboardConfig,
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

# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Exception classes
    "DashboardError",
    "DashboardImportResult",
    "DashboardNotFoundError",
    "DashboardStorageError",
    "DashboardValidationError",
    # Config type
    "DashboardConfig",
    # Builder
    "DashboardBuilder",
    # Importer — public API
    "import_dashboard",
    "is_lovelace_available",
    "dashboard_exists",
    "dashboard_path",
    # Importer — private helpers (used by tests)
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
]
