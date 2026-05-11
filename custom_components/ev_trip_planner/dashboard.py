"""Dashboard auto-deployment module for EV Trip Planner.

This module handles automatic deployment of Lovelace dashboards for each
configured vehicle when the config entry is set up. It supports both
storage mode (Supervisor) and YAML fallback mode (Container).

The dashboard includes:
- Vehicle status view with SOC, range, and charging status
- Trip list view showing all scheduled trips
- CRUD operations for creating, editing, and deleting trips
- EMHASS integration status when configured
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional

from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner.dashboard import (
    DashboardError,
    DashboardImportResult,
    DashboardNotFoundError,
    DashboardStorageError,
    DashboardValidationError,
)

# Reference to the dashboard package module for dynamic function lookups.
# This enables test mocks that patch dashboard._load_dashboard_template etc.
# to take effect in import_dashboard (which otherwise uses local names).
_dashboard_mod = sys.modules.get("custom_components.ev_trip_planner.dashboard")

from custom_components.ev_trip_planner.dashboard.template_manager import (
    DashboardConfig,
    _check_path_exists,
    _create_directory,
    _read_file_content,
    _write_file_content,
    load_template as _load_template,
    save_lovelace_dashboard as _save_lovelace,
    save_yaml_fallback as _save_yaml,
    validate_config as _validate_config,
    verify_storage_permissions as _verify_storage,
)

_LOGGER = logging.getLogger(__name__)

# Type alias for dashboard configuration — re-exported from template_manager
# DashboardConfig imported from .template_manager

# File I/O helpers — imported from .template_manager
# _read_file_content, _write_file_content, _check_path_exists, _create_directory


def _call_async_executor_sync(hass, func, *args):
    """Call a function via async executor with fallback for tests.

    Returns the actual result (not a coroutine) for compatibility with tests.

    Args:
        hass: HomeAssistant instance or MagicMock.
        func: Function to call.
        *args: Arguments to pass to the function.

    Returns:
        Result of the function call (synchronous result).
    """
    if hasattr(hass, "async_add_executor_job"):
        async_add_executor_job = getattr(hass, "async_add_executor_job")
        import inspect

        if inspect.iscoroutinefunction(async_add_executor_job):
            # In production, return the coroutine to be awaited
            return async_add_executor_job(func, *args)
        else:
            # Fallback for tests where hass is MagicMock
            # Return the direct result
            return func(*args)
    else:
        # Fallback for tests where hass doesn't have async_add_executor_job
        # Return the direct result
        return func(*args)


async def _await_executor_result(result):
    """Helper to await executor result if it's a coroutine.

    Args:
        result: Result from _call_async_executor_sync (could be coroutine or direct result)

    Returns:
        Synchronous result of the function.
    """
    if hasattr(result, "__await__"):
        return await result
    return result


def is_lovelace_available(hass: HomeAssistant) -> bool:
    """Check if Lovelace UI is available in Home Assistant.

    Returns True if Lovelace is installed and accessible.

    Args:
        hass: The Home Assistant instance.

    Returns:
        True if Lovelace is available, False otherwise.
    """
    # Check if lovelace is in loaded components
    if "lovelace" in hass.config.components:
        return True
    # Also check for the legacy method
    if hass.services.has_service("lovelace", "import"):
        return True
    return False


async def import_dashboard(
    hass: HomeAssistant,
    vehicle_id: str,
    vehicle_name: str,
    use_charts: bool = False,
) -> DashboardImportResult:
    """Import a Lovelace dashboard for the vehicle.

    Loads the dashboard template from the custom_components folder,
    substitutes variables, and saves it to Lovelace storage or YAML.

    Returns a structured result with detailed error information for
    troubleshooting dashboard deployment failures.

    Args:
        hass: The Home Assistant instance.
        vehicle_id: Unique identifier for the vehicle.
        vehicle_name: Display name for the vehicle.
        use_charts: Whether to use full dashboard with charts.

    Returns:
        DashboardImportResult with success status and error details.
    """
    dashboard_type = "full" if use_charts else "simple"
    _LOGGER.info(
        "=== DASHBOARD IMPORT START === Vehicle: %s | ID: %s | Type: %s",
        vehicle_name,
        vehicle_id,
        dashboard_type,
    )

    # Validate inputs
    if not vehicle_id or not isinstance(vehicle_id, str):
        error_msg = "Invalid vehicle_id: must be a non-empty string"
        _LOGGER.error("DASHBOARD IMPORT FAILED: %s", error_msg)
        return DashboardImportResult(
            success=False,
            vehicle_id=vehicle_id or "unknown",
            vehicle_name=vehicle_name,
            error=error_msg,
            error_details={"validation": "invalid_vehicle_id"},
            dashboard_type=dashboard_type,
            storage_method="none",
        )

    if not vehicle_name or not isinstance(vehicle_name, str):
        error_msg = "Invalid vehicle_name: must be a non-empty string"
        _LOGGER.error("DASHBOARD IMPORT FAILED: %s", error_msg)
        return DashboardImportResult(
            success=False,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_name or "unknown",
            error=error_msg,
            error_details={"validation": "invalid_vehicle_name"},
            dashboard_type=dashboard_type,
            storage_method="none",
        )

    # Check if Lovelace is available (use getattr to support test mocks)
    _lovelace_fn = getattr(_dashboard_mod, "is_lovelace_available", is_lovelace_available) if _dashboard_mod else is_lovelace_available
    if not _lovelace_fn(hass):
        error_msg = "Lovelace UI not available - dashboard cannot be deployed"
        _LOGGER.error(
            "DASHBOARD IMPORT FAILED: Lovelace not available for %s (ID: %s)",
            vehicle_name,
            vehicle_id,
        )
        return DashboardImportResult(
            success=False,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_name,
            error=error_msg,
            error_details={"check_lovelace": True},
            dashboard_type=dashboard_type,
            storage_method="none",
        )

    _LOGGER.info("Lovelace available, proceeding with dashboard import")

    # Load dashboard template from custom_components folder
    # Use getattr to support test mocks that patch dashboard._load_dashboard_template
    _load_fn = (
        getattr(_dashboard_mod, "_load_dashboard_template", _load_dashboard_template)
        if _dashboard_mod else _load_dashboard_template
    )
    try:
        dashboard_config = await _load_fn(
            hass, vehicle_id, vehicle_name, use_charts
        )

        if dashboard_config is None:
            error_msg = "Failed to load dashboard template"
            _LOGGER.error(
                "DASHBOARD IMPORT FAILED: Could not load template for %s (ID: %s)",
                vehicle_name,
                vehicle_id,
            )
            return DashboardImportResult(
                success=False,
                vehicle_id=vehicle_id,
                vehicle_name=vehicle_name,
                error=error_msg,
                error_details={"stage": "template_load"},
                dashboard_type=dashboard_type,
                storage_method="none",
            )

        _LOGGER.info(
            "Dashboard template loaded successfully for %s: %d views",
            vehicle_name,
            len(dashboard_config.get("views", [])),
        )

    except DashboardNotFoundError as e:
        error_msg = f"Template not found: {str(e)}"
        _LOGGER.error("DASHBOARD IMPORT FAILED: %s", error_msg)
        return DashboardImportResult(
            success=False,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_name,
            error=error_msg,
            error_details=e.details,
            dashboard_type=dashboard_type,
            storage_method="none",
        )

    except Exception as e:
        error_msg = f"Unexpected error loading template: {str(e)}"
        _LOGGER.error(
            "DASHBOARD IMPORT FAILED: Exception loading template: %s", e, exc_info=True
        )
        return DashboardImportResult(
            success=False,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_name,
            error=error_msg,
            error_details={"exception": str(e), "stage": "template_load"},
            dashboard_type=dashboard_type,
            storage_method="none",
        )

    # Validate dashboard config before saving
    try:
        _validate_fn = (
            getattr(_dashboard_mod, "_validate_dashboard_config", _validate_dashboard_config)
            if _dashboard_mod else _validate_dashboard_config
        )
        _validate_fn(dashboard_config, vehicle_id)
    except DashboardValidationError as e:
        error_msg = f"Dashboard validation failed: {str(e)}"
        _LOGGER.error("DASHBOARD IMPORT FAILED: Validation error: %s", e)
        return DashboardImportResult(
            success=False,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_name,
            error=error_msg,
            error_details=e.details,
            dashboard_type=dashboard_type,
            storage_method="none",
        )

    storage_method = "none"

    # Try to save using the Lovelace storage API first
    _LOGGER.info("Attempting DASHBOARD IMPORT via storage API for %s", vehicle_id)

    try:
        # Call the save helper and check its structured result explicitly.
        # Use getattr to support test mocks that patch dashboard._save_lovelace_dashboard
        _save_lovelace_fn = (
            getattr(_dashboard_mod, "_save_lovelace_dashboard", _save_lovelace_dashboard)
            if _dashboard_mod else _save_lovelace_dashboard
        )
        save_result = await _save_lovelace_fn(
            hass, dashboard_config, vehicle_id, vehicle_name
        )

        # If helper returns a DashboardImportResult, respect its .success flag.
        if isinstance(save_result, DashboardImportResult):
            if save_result.success:
                storage_method = save_result.storage_method or "storage_api"
                _LOGGER.info(
                    "=== DASHBOARD IMPORT SUCCESS === via %s for %s (ID: %s)",
                    storage_method,
                    vehicle_name,
                    vehicle_id,
                )
                return save_result
            # Explicit failure -> fall through to YAML fallback

        # Backwards-compatible: if helper returns bare True/False, handle that too
        elif save_result is True:
            storage_method = "storage_api"
            _LOGGER.info(
                "=== DASHBOARD IMPORT SUCCESS === via storage API for %s (ID: %s)",
                vehicle_name,
                vehicle_id,
            )
            return DashboardImportResult(
                success=True,
                vehicle_id=vehicle_id,
                vehicle_name=vehicle_name,
                dashboard_type=dashboard_type,
                storage_method=storage_method,
            )

        _LOGGER.info(
            "Storage API method failed or returned non-success, generating YAML fallback for Container"
        )

    except DashboardStorageError as e:  # pragma: no cover  # HA storage I/O exception - storage API failure triggers fallback path
        _LOGGER.warning("Storage API failed, attempting YAML fallback: %s", e)
    except Exception as e:  # pragma: no cover  # HA storage I/O exception - unexpected storage errors trigger fallback path
        _LOGGER.warning("Storage API exception, attempting YAML fallback: %s", e)

    # Fallback: Generate YAML file for Container environment
    _LOGGER.info("Attempting YAML fallback for Container environment")
    try:
        # Use getattr to support test mocks
        _save_yaml_fn = (
            getattr(_dashboard_mod, "_save_dashboard_yaml_fallback", _save_dashboard_yaml_fallback)
            if _dashboard_mod else _save_dashboard_yaml_fallback
        )
        yaml_result = await _save_yaml_fn(
            hass, dashboard_config, vehicle_id, vehicle_name
        )

        # `_save_dashboard_yaml_fallback` may return a DashboardImportResult
        # or (legacy) a bare boolean. Handle both forms explicitly.
        if isinstance(yaml_result, DashboardImportResult):
            if yaml_result.success:
                storage_method = yaml_result.storage_method or "yaml_fallback"
                _LOGGER.info(
                    "=== DASHBOARD IMPORT SUCCESS === via %s for %s",
                    storage_method,
                    vehicle_name,
                )
                return yaml_result
            # explicit failure from YAML helper
            _LOGGER.error(
                "=== DASHBOARD IMPORT FAILED === No import method available for %s",
                vehicle_name,
            )
            return DashboardImportResult(
                success=False,
                vehicle_id=vehicle_id,
                vehicle_name=vehicle_name,
                error="All import methods failed",
                error_details={
                    "storage_api_failed": True,
                    "yaml_fallback_failed": True,
                },
                dashboard_type=dashboard_type,
                storage_method="none",
            )

        # Legacy boolean return handling
        if yaml_result is True:
            storage_method = "yaml_fallback"
            _LOGGER.info(
                "=== DASHBOARD IMPORT SUCCESS === via YAML fallback for %s",
                vehicle_name,
            )
            return DashboardImportResult(
                success=True,
                vehicle_id=vehicle_id,
                vehicle_name=vehicle_name,
                dashboard_type=dashboard_type,
                storage_method=storage_method,
            )

        # Any other result is a failure
        _LOGGER.error(
            "=== DASHBOARD IMPORT FAILED === No import method available for %s",
            vehicle_name,
        )
        return DashboardImportResult(
            success=False,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_name,
            error="All import methods failed",
            error_details={
                "storage_api_failed": True,
                "yaml_fallback_failed": True,
            },
            dashboard_type=dashboard_type,
            storage_method="none",
        )

    except Exception as e:
        _LOGGER.error("YAML fallback exception: %s", e, exc_info=True)
        return DashboardImportResult(
            success=False,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_name,
            error=f"YAML fallback failed: {str(e)}",
            error_details={"stage": "yaml_fallback", "exception": str(e)},
            dashboard_type=dashboard_type,
            storage_method="none",
        )


# Wrapper functions delegating to template_manager

def _validate_dashboard_config(
    dashboard_config: DashboardConfig,
    vehicle_id: str,
) -> None:
    """Validate dashboard configuration before saving.

    Delegates to template_manager.validate_config.

    Args:
        dashboard_config: The dashboard configuration dictionary.
        vehicle_id: The vehicle ID for validation context.

    Raises:
        DashboardError: If validation fails.
    """
    _validate_config(dashboard_config, vehicle_id)


async def _load_dashboard_template(
    hass: HomeAssistant,
    vehicle_id: str,
    vehicle_name: str,
    use_charts: bool,
) -> Optional[DashboardConfig]:
    """Load dashboard template and substitute variables.

    Delegates to template_manager.load_template.

    Args:
        hass: The Home Assistant instance.
        vehicle_id: Unique identifier for the vehicle.
        vehicle_name: Display name for the vehicle.
        use_charts: Whether to use full dashboard with charts.

    Returns:
        Dashboard configuration dictionary or None if failed.
    """
    return await _load_template(hass, vehicle_id, vehicle_name, use_charts)


async def _save_lovelace_dashboard(
    hass: HomeAssistant,
    dashboard_config: DashboardConfig,
    vehicle_id: str,
    vehicle_name: str = "",
) -> DashboardImportResult:
    """Save dashboard to Lovelace storage.

    Delegates to template_manager.save_lovelace_dashboard.

    Args:
        hass: The Home Assistant instance.
        dashboard_config: The dashboard configuration dictionary.
        vehicle_id: The vehicle ID for logging purposes.
        vehicle_name: The vehicle name for logging purposes.

    Returns:
        DashboardImportResult object with success status.
    """
    return await _save_lovelace(hass, dashboard_config, vehicle_id, vehicle_name)


async def _verify_storage_permissions(hass: HomeAssistant, vehicle_id: str) -> bool:
    """Verify storage write permissions for dashboard import.

    Delegates to template_manager.verify_storage_permissions.

    Args:
        hass: The Home Assistant instance.
        vehicle_id: The vehicle ID for logging purposes.

    Returns:
        True if storage is writable, False otherwise.
    """
    return await _verify_storage(hass, vehicle_id)


async def _save_dashboard_yaml_fallback(
    hass: HomeAssistant,
    dashboard_config: DashboardConfig,
    vehicle_id: str,
    vehicle_name: str = "",
) -> DashboardImportResult:
    """Save dashboard as YAML file for Container environment.

    Delegates to template_manager.save_yaml_fallback.

    Args:
        hass: The Home Assistant instance.
        dashboard_config: The dashboard configuration dictionary.
        vehicle_id: The vehicle ID for file naming.
        vehicle_name: The vehicle name for logging purposes.

    Returns:
        DashboardImportResult object with success status.
    """
    return await _save_yaml(hass, dashboard_config, vehicle_id, vehicle_name)
