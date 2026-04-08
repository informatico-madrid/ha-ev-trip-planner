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
import os
from typing import Any, Optional

import yaml
from homeassistant.core import HomeAssistant

# from .const import DOMAIN  # Not directly used in this module

_LOGGER = logging.getLogger(__name__)

# Type alias for dashboard configuration
DashboardConfig = dict[str, Any]


def _read_file_content(file_path: str) -> str:
    """Read file content asynchronously.

    Args:
        file_path: Path to the file to read.

    Returns:
        File content as string.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def _write_file_content(file_path: str, content: str) -> None:
    """Write content to file asynchronously.

    Args:
        file_path: Path to the file to write.
        content: Content to write to the file.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def _check_path_exists(path: str) -> bool:
    """Check if a path exists asynchronously.

    Args:
        path: Path to check.

    Returns:
        True if path exists, False otherwise.
    """
    return os.path.exists(path)


def _create_directory(dir_path: str, mode: int = 0o755) -> None:
    """Create directory asynchronously.

    Args:
        dir_path: Path to the directory to create.
        mode: Directory permissions.
    """
    os.makedirs(dir_path, mode=mode, exist_ok=True)  # pragma: no cover — HA I/O bound


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


class DashboardError(Exception):
    """Base exception for dashboard-related errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        """Initialize the dashboard error.

        Args:
            message: Human-readable error message.
            details: Optional additional error details (e.g., file paths, config).
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
    """Structured result from dashboard import operations.

    Provides detailed error information for troubleshooting dashboard deployment
    failures without requiring log inspection.
    """

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
        """Convert to dictionary representation.

        Returns:
            Dictionary with all result fields.
        """
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

    # Check if Lovelace is available
    if not is_lovelace_available(hass):
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
    try:
        dashboard_config = await _load_dashboard_template(
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
        _validate_dashboard_config(dashboard_config, vehicle_id)
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
        if await _save_lovelace_dashboard(hass, dashboard_config, vehicle_id):
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
            "Storage API method failed, generating YAML fallback for Container"
        )

    except DashboardStorageError as e:
        _LOGGER.warning("Storage API failed, attempting YAML fallback: %s", e)
    except Exception as e:
        _LOGGER.warning("Storage API exception, attempting YAML fallback: %s", e)

    # Fallback: Generate YAML file for Container environment
    _LOGGER.info("Attempting YAML fallback for Container environment")
    try:
        yaml_result = await _save_dashboard_yaml_fallback(
            hass, dashboard_config, vehicle_id
        )

        if yaml_result.success:
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


def _validate_dashboard_config(
    dashboard_config: DashboardConfig,
    vehicle_id: str,
) -> None:
    """Validate dashboard configuration before saving.

    Validates that the dashboard config has all required fields and proper
    structure. Raises DashboardValidationError if validation fails.

    Args:
        dashboard_config: The dashboard configuration dictionary.
        vehicle_id: The vehicle ID for validation context.

    Raises:
        DashboardValidationError: If validation fails.
    """
    if not isinstance(dashboard_config, dict):
        raise DashboardValidationError(
            "invalid_config",
            f"Dashboard config must be a dict, got {type(dashboard_config).__name__}",
        )

    if "title" not in dashboard_config:
        raise DashboardValidationError(
            "missing_title",
            "Dashboard config missing required 'title' field",
        )

    if "views" not in dashboard_config:
        raise DashboardValidationError(
            "missing_views",
            "Dashboard config missing required 'views' field",
        )

    if not isinstance(dashboard_config["views"], list):
        raise DashboardValidationError(
            "invalid_views_type",
            "Dashboard 'views' must be a list",
        )

    if len(dashboard_config["views"]) == 0:
        raise DashboardValidationError(
            "empty_views",
            "Dashboard 'views' list cannot be empty",
        )

    for i, view in enumerate(dashboard_config["views"]):
        if not isinstance(view, dict):
            raise DashboardValidationError(
                f"view_{i}_type",
                f"Dashboard view at index {i} must be a dict",
            )
        if "path" not in view:
            raise DashboardValidationError(
                f"view_{i}_missing_path",
                f"Dashboard view at index {i} missing required 'path' field",
            )
        if "title" not in view:
            raise DashboardValidationError(
                f"view_{i}_missing_title",
                f"Dashboard view at index {i} missing required 'title' field",
            )
        if "cards" not in view:
            raise DashboardValidationError(
                f"view_{i}_missing_cards",
                f"Dashboard view at index {i} missing required 'cards' field",
            )

    # Validate vehicle_id is in view paths
    views = dashboard_config.get("views", [])
    has_vehicle_path = any(vehicle_id in v.get("path", "") for v in views)
    if not has_vehicle_path:
        _LOGGER.warning("Vehicle ID '%s' not found in any view path", vehicle_id)


async def _load_dashboard_template(
    hass: HomeAssistant,
    vehicle_id: str,
    vehicle_name: str,
    use_charts: bool,
) -> Optional[DashboardConfig]:
    """Load dashboard template and substitute variables.

    Uses async I/O when hass.async_add_executor_job is available (production).
    Falls back to sync I/O for testing compatibility.

    Args:
        hass: The Home Assistant instance.
        vehicle_id: Unique identifier for the vehicle.
        vehicle_name: Display name for the vehicle.
        use_charts: Whether to use full dashboard with charts.

    Returns:
        Dashboard configuration dictionary or None if failed.
    """
    try:
        # Determine template filename
        if use_charts:
            template_file = "ev-trip-planner-full.yaml"
        else:
            template_file = "ev-trip-planner-simple.yaml"

        _LOGGER.debug(
            "Loading dashboard template: file=%s, vehicle_id=%s, vehicle_name=%s",
            template_file,
            vehicle_id,
            vehicle_name,
        )

        # Find the dashboard template - check multiple locations
        comp_dir = os.path.dirname(__file__)
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        possible_paths = [
            os.path.join(comp_dir, "dashboard", template_file),
            os.path.join(
                parent_dir,
                "custom_components",
                "ev_trip_planner",
                "dashboard",
                template_file,
            ),
        ]

        _LOGGER.debug("Searching for template in: %s", possible_paths)

        # Use sync I/O for file operations - works in both production and test
        template_path = None
        for path in possible_paths:
            if os.path.exists(path):
                template_path = path
                _LOGGER.debug("Found template at: %s", template_path)
                break

        if template_path is None:
            _LOGGER.error(
                "Dashboard template not found: %s (searched in %s)",
                template_file,
                possible_paths,
            )
            return None

        # Read and parse YAML template using async executor
        _LOGGER.debug("Reading template file: %s", template_path)
        try:
            # Check if we can use async executor (production) or fall back to sync (tests)
            # In production, async_add_executor_job is a coroutine function
            # In tests with MagicMock, it's just a mock object
            if hasattr(hass, "async_add_executor_job"):
                async_add_executor_job = getattr(hass, "async_add_executor_job")
                # Check if it's actually a coroutine function (has __await__ or is coroutine)
                import inspect

                if inspect.iscoroutinefunction(async_add_executor_job):
                    template_content = await async_add_executor_job(
                        _read_file_content, template_path
                    )
                else:
                    # Fallback for tests where hass is MagicMock
                    template_content = _read_file_content(template_path)
            else:
                # Fallback for tests where hass doesn't have async_add_executor_job
                template_content = _read_file_content(template_path)
        except Exception as e:
            _LOGGER.error("Failed to read template file: %s", e)
            return None

        if template_content is None:
            _LOGGER.error("Failed to read template file: %s", template_path)
            return None

        _LOGGER.debug("Template content length: %d chars", len(template_content))

        # Substitute template variables
        template_content = template_content.replace("{{ vehicle_id }}", vehicle_id)
        template_content = template_content.replace("{{ vehicle_name }}", vehicle_name)

        # Parse YAML to dict
        dashboard_config = yaml.safe_load(template_content)

        _LOGGER.debug(
            "Loaded dashboard template from %s: title=%s, views=%d",
            template_path,
            dashboard_config.get("title") if dashboard_config else "N/A",
            len(dashboard_config.get("views", [])) if dashboard_config else 0,
        )

        return dashboard_config

    except Exception as err:
        _LOGGER.error(
            "TEMPLATE LOAD FAILED for %s: %s",
            vehicle_id,
            err,
            exc_info=True,
        )
        return None


async def _save_lovelace_dashboard(
    hass: HomeAssistant,
    dashboard_config: DashboardConfig,
    vehicle_id: str,
) -> DashboardImportResult:
    """Save dashboard to Lovelace storage.

    Handles both Supervisor (storage API) and Container (YAML fallback) environments.

    Args:
        hass: The Home Assistant instance.
        dashboard_config: The dashboard configuration dictionary.
        vehicle_id: The vehicle ID for logging purposes.

    Returns:
        DashboardImportResult object with success status.

    Raises:
        DashboardStorageError: If storage operation fails with structured error.
    """
    storage_method = "lovelace_save_service"

    try:
        # Check if we can use the lovelace.config service
        if hass.services.has_service("lovelace", "save"):
            _LOGGER.info("METHOD: Using lovelace.save service for dashboard import")

            # Try to save each view as a separate dashboard
            views = dashboard_config.get("views", [])
            _LOGGER.info(
                "Dashboard config has %d views, will save first view", len(views)
            )

            # For now, we'll save the first view as the main dashboard
            if views:
                first_view = views[0]
                view_path = first_view.get("path", "unknown")
                view_title = first_view.get("title", "unknown")
                _LOGGER.info(
                    "Saving first view: path=%s, title=%s", view_path, view_title
                )
                view_config = {
                    "title": dashboard_config.get("title", "EV Trip Planner"),
                    "views": [first_view],
                }

                await hass.services.async_call(
                    "lovelace",
                    "save",
                    {"config": view_config},
                )
                _LOGGER.info("DASHBOARD SAVED via lovelace.save service")
                return DashboardImportResult(
                    success=True,
                    vehicle_id=vehicle_id,
                    vehicle_name=vehicle_id,
                    dashboard_type="simple",
                    storage_method="lovelace_save_service",
                )

            _LOGGER.warning("Dashboard config has no views to save")
            raise DashboardStorageError(
                storage_method,
                "Dashboard config has no views to save",
            )
        else:
            _LOGGER.info(
                "METHOD: lovelace.save service NOT available, trying storage API"
            )

        # Use HA's official Store API for persistence
        from homeassistant.helpers import storage as ha_storage

        _LOGGER.info("METHOD: Using Store API for dashboard import")

        # Verify storage write permissions before attempting to write
        if not await _verify_storage_permissions(hass, vehicle_id):
            _LOGGER.warning(
                "Store API NOT AVAILABLE for %s, using YAML fallback",
                vehicle_id,
            )
            _LOGGER.info(
                "Store API not available, falling back to YAML for %s", vehicle_id
            )
            return await _save_dashboard_yaml_fallback(
                hass, dashboard_config, vehicle_id
            )

        try:
            # Get current lovelace config using Store API
            _LOGGER.info("Reading current Lovelace config from storage")

            store = ha_storage.Store(
                hass,
                version=1,
                key="lovelace",
            )

            lovelace_config = await store.async_load()

            if lovelace_config and "data" in lovelace_config:
                current_data = lovelace_config["data"]
                views = current_data.get("views", [])
                _LOGGER.info("Current Lovelace config has %d views", len(views))

                # Get new dashboard view
                new_views = dashboard_config.get("views", [])
                if not new_views:
                    _LOGGER.error(
                        "STORAGE API FAILED: No views found in dashboard config"
                    )
                    raise DashboardStorageError(
                        "storage_api",
                        "No views found in dashboard config",
                    )
                new_view = new_views[0]

                # FR-004: Replace existing view with same path, or append
                new_path = new_view.get("path", vehicle_id)
                _LOGGER.info("New dashboard view path: %s", new_path)

                replaced = False
                for i, existing_view in enumerate(views):
                    if existing_view.get("path") == new_path:
                        views[i] = new_view
                        replaced = True
                        _LOGGER.info("Replaced existing dashboard view: %s", new_path)
                        break

                if not replaced:
                    views.append(new_view)
                    _LOGGER.info("Added new dashboard view: %s", new_path)

                _LOGGER.info(
                    "Saving dashboard: total views=%d, vehicle_id=%s",
                    len(views),
                    vehicle_id,
                )
                # Save updated config using HA's official Store API
                from homeassistant.helpers import storage as ha_storage

                _LOGGER.info("Writing dashboard config to storage: lovelace")

                # Use HA's official Store API for persistence
                store = ha_storage.Store(
                    hass,
                    version=1,
                    key="lovelace",
                )

                await store.async_save(
                    {
                        "version": 1,
                        "data": {**current_data, "views": views},
                    }
                )

                _LOGGER.info("DASHBOARD SAVED via storage API")
                return DashboardImportResult(
                    success=True,
                    vehicle_id=vehicle_id,
                    vehicle_name=vehicle_id,
                    dashboard_type="simple",
                    storage_method="storage_api",
                )
        except Exception as e:
            _LOGGER.error(
                "STORAGE API FAILED for %s: %s",
                vehicle_id,
                e,
                exc_info=True,
            )
            raise DashboardStorageError(
                "storage_api",
                f"Storage operation failed: {str(e)}",
            )

    except DashboardStorageError as e:
        # Storage operation failed - fall back to YAML
        _LOGGER.warning(
            "STORAGE API FAILED for %s: %s, falling back to YAML",
            vehicle_id,
            e,
        )
    except Exception as e:
        _LOGGER.error(
            "Unexpected error in _save_lovelace_dashboard for %s: %s",
            vehicle_id,
            e,
            exc_info=True,
        )
        # Fall back to YAML on any error
        yaml_result = await _save_dashboard_yaml_fallback(
            hass, dashboard_config, vehicle_id
        )
        if isinstance(yaml_result, DashboardImportResult):
            return yaml_result
        return DashboardImportResult(
            success=(
                yaml_result if isinstance(yaml_result, bool) else yaml_result.success
            ),
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_id,
            dashboard_type="simple",
            storage_method="yaml_fallback",
        )

    # Storage not available - fall back to YAML
    _LOGGER.info("Storage API not available, falling back to YAML for %s", vehicle_id)
    yaml_result = await _save_dashboard_yaml_fallback(
        hass, dashboard_config, vehicle_id
    )
    if isinstance(yaml_result, DashboardImportResult):
        return yaml_result
    # If YAML fallback returns boolean, wrap it
    return DashboardImportResult(
        success=yaml_result if isinstance(yaml_result, bool) else yaml_result.success,
        vehicle_id=vehicle_id,
        vehicle_name=vehicle_id,
        dashboard_type="simple",
        storage_method="yaml_fallback",
    )


async def _verify_storage_permissions(hass: HomeAssistant, vehicle_id: str) -> bool:
    """Verify storage write permissions for dashboard import.

    Checks if the storage API is available and writable before attempting
    to import a dashboard.

    In Home Assistant Container, the Lovelace storage mode may not be available
    (YAML mode is active by default). This function detects the mode and returns
    False to trigger YAML fallback when storage mode is not available.

    Args:
        hass: The Home Assistant instance.
        vehicle_id: The vehicle ID for logging purposes.

    Returns:
        True if storage is writable, False otherwise.
    """
    try:
        _LOGGER.info("VERIFYING STORAGE PERMISSIONS for vehicle %s", vehicle_id)

        # Use HA's official Store API for persistence
        from homeassistant.helpers import storage as ha_storage

        # Try to create a test store to verify it works
        test_store = ha_storage.Store(
            hass,
            version=1,
            key="test_storage_check",
        )

        # Try to load to verify storage is available
        await test_store.async_load()
        _LOGGER.info("Store API test load succeeded for %s", vehicle_id)

        # Store API is available
        return True

    except Exception as e:
        _LOGGER.warning(
            "Store API not available for %s: %s, using YAML fallback", vehicle_id, e
        )
        return False


async def _save_dashboard_yaml_fallback(
    hass: HomeAssistant,
    dashboard_config: DashboardConfig,
    vehicle_id: str,
) -> DashboardImportResult:
    """Save dashboard as YAML file for Container environment.

    In HA Container, storage API is not available. This function generates
    a YAML file that can be manually imported via Lovelace UI.

    Args:
        hass: The Home Assistant instance.
        dashboard_config: The dashboard configuration dictionary.
        vehicle_id: The vehicle ID for file naming.

    Returns:
        DashboardImportResult object with success status.
    """
    try:
        # Validate dashboard config before writing
        if not dashboard_config:
            _LOGGER.error("Dashboard config is empty or None")
            return DashboardImportResult(
                success=False,
                vehicle_id=vehicle_id,
                vehicle_name=vehicle_id,
                error="Invalid dashboard config",
                dashboard_type="simple",
                storage_method="yaml_fallback",
            )

        if "title" not in dashboard_config:
            _LOGGER.error("Dashboard config missing required 'title' field")
            return DashboardImportResult(
                success=False,
                vehicle_id=vehicle_id,
                vehicle_name=vehicle_id,
                error="Invalid dashboard config",
                dashboard_type="simple",
                storage_method="yaml_fallback",
            )

        if "views" not in dashboard_config:
            _LOGGER.error("Dashboard config missing required 'views' field")
            return DashboardImportResult(
                success=False,
                vehicle_id=vehicle_id,
                vehicle_name=vehicle_id,
                error="Invalid dashboard config",
                dashboard_type="simple",
                storage_method="yaml_fallback",
            )

        if not isinstance(dashboard_config["views"], list):
            _LOGGER.error("Dashboard 'views' must be a list")
            return DashboardImportResult(
                success=False,
                vehicle_id=vehicle_id,
                vehicle_name=vehicle_id,
                error="Invalid dashboard config",
                dashboard_type="simple",
                storage_method="yaml_fallback",
            )

        if len(dashboard_config["views"]) == 0:
            _LOGGER.error("Dashboard 'views' list cannot be empty")
            return DashboardImportResult(
                success=False,
                vehicle_id=vehicle_id,
                vehicle_name=vehicle_id,
                error="Invalid dashboard config",
                dashboard_type="simple",
                storage_method="yaml_fallback",
            )

        for i, view in enumerate(dashboard_config["views"]):
            if not isinstance(view, dict):
                _LOGGER.error("Dashboard view at index %d must be a dict", i)
                return DashboardImportResult(
                    success=False,
                    vehicle_id=vehicle_id,
                    vehicle_name=vehicle_id,
                    error="Invalid dashboard config",
                    dashboard_type="simple",
                    storage_method="yaml_fallback",
                )
            if "path" not in view:
                _LOGGER.error(
                    "Dashboard view at index %d missing required 'path' field", i
                )
                return DashboardImportResult(
                    success=False,
                    vehicle_id=vehicle_id,
                    vehicle_name=vehicle_id,
                    error="Invalid dashboard config",
                    dashboard_type="simple",
                    storage_method="yaml_fallback",
                )
            if "title" not in view:
                _LOGGER.error(
                    "Dashboard view at index %d missing required 'title' field", i
                )
                return DashboardImportResult(
                    success=False,
                    vehicle_id=vehicle_id,
                    vehicle_name=vehicle_id,
                    error="Invalid dashboard config",
                    dashboard_type="simple",
                    storage_method="yaml_fallback",
                )
            if "cards" not in view:
                _LOGGER.error(
                    "Dashboard view at index %d missing required 'cards' field", i
                )
                return DashboardImportResult(
                    success=False,
                    vehicle_id=vehicle_id,
                    vehicle_name=vehicle_id,
                    error="Invalid dashboard config",
                    dashboard_type="simple",
                    storage_method="yaml_fallback",
                )

        # Get config directory path
        config_dir = hass.config.config_dir
        if not config_dir:
            _LOGGER.error("Could not determine config directory")
            return DashboardImportResult(
                success=False,
                vehicle_id=vehicle_id,
                vehicle_name=vehicle_id,
                error="Invalid dashboard config",
                dashboard_type="simple",
                storage_method="yaml_fallback",
            )

        # Generate unique filename to avoid collisions
        base_filename = f"ev-trip-planner-{vehicle_id}.yaml"
        yaml_path = os.path.join(config_dir, base_filename)

        # Handle duplicate filenames - append suffix like .2, .3, etc.
        counter = 2

        # Check path exists with async executor fallback
        path_check_result = _call_async_executor_sync(
            hass, _check_path_exists, yaml_path
        )
        path_exists = await _await_executor_result(path_check_result)

        while path_exists:
            yaml_path = os.path.join(config_dir, f"{base_filename}.{counter}")
            counter += 1
            path_check_result = _call_async_executor_sync(
                hass, _check_path_exists, yaml_path
            )
            path_exists = await _await_executor_result(path_check_result)

        _LOGGER.info(
            "Dashboard path: %s",
            os.path.basename(yaml_path),
        )

        # Create config directory if it doesn't exist
        config_check_result = _call_async_executor_sync(
            hass, _check_path_exists, config_dir
        )
        config_exists = await _await_executor_result(config_check_result)

        if not config_exists:
            await _await_executor_result(
                _call_async_executor_sync(hass, _create_directory, config_dir, 0o755)
            )
            _LOGGER.info("Created config directory: %s", config_dir)

        # Convert dashboard config to YAML
        yaml_content = yaml.dump(dashboard_config, default_flow_style=False)

        # Write YAML file to config directory using executor
        try:
            write_result = _call_async_executor_sync(
                hass, _write_file_content, yaml_path, yaml_content
            )
            await _await_executor_result(write_result)
            write_success = True
        except Exception as e:
            _LOGGER.error("Failed to write YAML file: %s", e)
            write_success = False

        if not write_success:
            _LOGGER.error("Failed to write dashboard YAML file")
            return DashboardImportResult(
                success=False,
                vehicle_id=vehicle_id,
                vehicle_name=vehicle_id,
                error="Invalid dashboard config",
                dashboard_type="simple",
                storage_method="yaml_fallback",
            )

        _LOGGER.info(
            "YAML file created at %s",
            yaml_path,
        )
        _LOGGER.info(
            "To import dashboard in Home Assistant Container, follow these steps:"
        )
        _LOGGER.info("1. Go to Settings > Dashboards in Home Assistant")
        _LOGGER.info("2. Click the three dots menu > Manage dashboards")
        _LOGGER.info(
            "3. Click 'Import dashboard' and select: %s",
            yaml_path,
        )
        _LOGGER.info(
            "Dashboard ready for import. File location: %s",
            yaml_path,
        )

        return DashboardImportResult(
            success=True,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_id,
            dashboard_type="simple",
            storage_method="yaml_fallback",
        )

    except Exception as e:
        _LOGGER.error("YAML fallback failed: %s", e, exc_info=True)
        return DashboardImportResult(
            success=False,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_id,
            error=str(e),
            dashboard_type="simple",
            storage_method="yaml_fallback",
        )
