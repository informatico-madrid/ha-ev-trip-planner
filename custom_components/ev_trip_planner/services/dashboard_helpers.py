"""Dashboard helper functions for EV Trip Planner.

Contains dashboard-related helper functions extracted from the original
services module as part of SOLID decomposition.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..dashboard import (
    DashboardImportResult,  # type: ignore[reportAttributeAccessIssue]
)

_LOGGER = logging.getLogger(__name__)


async def create_dashboard_input_helpers(
    hass: HomeAssistant,
    vehicle_id: str,
) -> DashboardImportResult:
    """Create input helpers for dashboard CRUD forms.

    Creates the required input entities that the dashboard template
    uses for creating and editing trips.

    Args:
        hass: The Home Assistant instance.
        vehicle_id: Unique identifier for the vehicle.

    Returns:
        DashboardImportResult with success status.
    """
    _LOGGER.info("Creating input helpers for dashboard: %s", vehicle_id)

    try:
        # Create input_select for day of week (recurring trips)
        day_options = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        try:
            await hass.services.async_call(
                "input_select",
                "create",
                {
                    "name": f"{vehicle_id} - Trip Day",
                    "options": day_options,
                    "icon": "mdi:calendar-week",
                },
            )
            _LOGGER.debug("Created input_select for day: %s_trip_day", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input select may already exist: %s", e)

        # Create input_datetime for recurring trip time
        try:
            await hass.services.async_call(
                "input_datetime",
                "create",
                {
                    "name": f"{vehicle_id} - Trip Time",
                    "has_date": False,
                    "has_time": True,
                    "icon": "mdi:clock",
                },
            )
            _LOGGER.debug("Created input_datetime for time: %s_trip_time", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input datetime may already exist: %s", e)

        # Create input_number for recurring trip km
        try:
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "name": f"{vehicle_id} - Trip km",
                    "min": 0,
                    "max": 1000,
                    "unit_of_measurement": "km",
                    "icon": "mdi:map-marker-distance",
                },
            )
            _LOGGER.debug("Created input_number for km: %s_trip_km", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input number may already exist: %s", e)

        # Create input_number for recurring trip kwh
        try:
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "name": f"{vehicle_id} - Trip kWh",
                    "min": 0,
                    "max": 200,
                    "unit_of_measurement": "kWh",
                    "icon": "mdi:lightning-bolt",
                },
            )
            _LOGGER.debug("Created input_number for kwh: %s_trip_kwh", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input number may already exist: %s", e)

        # Create input_text for recurring trip description
        try:
            await hass.services.async_call(
                "input_text",
                "create",
                {
                    "name": f"{vehicle_id} - Trip Description",
                    "icon": "mdi:text",
                },
            )
            _LOGGER.debug("Created input_text for desc: %s_trip_desc", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input text may already exist: %s", e)

        # Create input_datetime for punctual trip datetime
        try:
            await hass.services.async_call(
                "input_datetime",
                "create",
                {
                    "name": f"{vehicle_id} - Punctual Trip DateTime",
                    "has_date": True,
                    "has_time": True,
                    "icon": "mdi:calendar-clock",
                },
            )
            _LOGGER.debug(
                "Created input_datetime for datetime: %s_punctual_datetime", vehicle_id
            )
        except Exception as e:
            _LOGGER.debug("Input datetime may already exist: %s", e)

        # Create input_number for punctual trip km
        try:
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "name": f"{vehicle_id} - Punctual Trip km",
                    "min": 0,
                    "max": 1000,
                    "unit_of_measurement": "km",
                    "icon": "mdi:map-marker-distance",
                },
            )
            _LOGGER.debug("Created input_number for km: %s_punctual_km", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input number may already exist: %s", e)

        # Create input_number for punctual trip kwh
        try:
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "name": f"{vehicle_id} - Punctual Trip kWh",
                    "min": 0,
                    "max": 200,
                    "unit_of_measurement": "kWh",
                    "icon": "mdi:lightning-bolt",
                },
            )
            _LOGGER.debug("Created input_number for kwh: %s_punctual_kwh", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input number may already exist: %s", e)

        # Create input_text for punctual trip description
        try:
            await hass.services.async_call(
                "input_text",
                "create",
                {
                    "name": f"{vehicle_id} - Punctual Trip Description",
                    "icon": "mdi:text",
                },
            )
            _LOGGER.debug("Created input_text for desc: %s_punctual_desc", vehicle_id)
        except Exception as e:
            _LOGGER.debug("Input text may already exist: %s", e)

        # === Edit Trip Input Helpers ===
        # Input to select which trip to edit
        try:
            await hass.services.async_call(
                "input_select",
                "create",
                {
                    "name": f"{vehicle_id} - Edit Trip Selector",
                    "options": ["-- Seleccionar viaje --"],
                    "icon": "mdi:pencil",
                },
            )
            _LOGGER.debug(
                "Created input_select for edit: %s_edit_trip_selector", vehicle_id
            )
        except Exception as e:
            _LOGGER.debug("Input select may already exist: %s", e)

        # Input datetime for edit trip time
        try:
            await hass.services.async_call(
                "input_datetime",
                "create",
                {
                    "name": f"{vehicle_id} - Edit Trip Time",
                    "has_date": False,
                    "has_time": True,
                    "icon": "mdi:clock-edit",
                },
            )
            _LOGGER.debug(
                "Created input_datetime for edit time: %s_edit_trip_time", vehicle_id
            )
        except Exception as e:
            _LOGGER.debug("Input datetime may already exist: %s", e)

        # Input number for edit trip km
        try:
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "name": f"{vehicle_id} - Edit Trip km",
                    "min": 0,
                    "max": 1000,
                    "unit_of_measurement": "km",
                    "icon": "mdi:map-marker-distance",
                },
            )
            _LOGGER.debug(
                "Created input_number for edit km: %s_edit_trip_km", vehicle_id
            )
        except Exception as e:
            _LOGGER.debug("Input number may already exist: %s", e)

        # Input number for edit trip kwh
        try:
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "name": f"{vehicle_id} - Edit Trip kWh",
                    "min": 0,
                    "max": 200,
                    "unit_of_measurement": "kWh",
                    "icon": "mdi:lightning-bolt",
                },
            )
            _LOGGER.debug(
                "Created input_number for edit kwh: %s_edit_trip_kwh", vehicle_id
            )
        except Exception as e:
            _LOGGER.debug("Input number may already exist: %s", e)

        # Input text for edit trip description
        try:
            await hass.services.async_call(
                "input_text",
                "create",
                {
                    "name": f"{vehicle_id} - Edit Trip Description",
                    "icon": "mdi:text",
                },
            )
            _LOGGER.debug(
                "Created input_text for edit desc: %s_edit_trip_desc", vehicle_id
            )
        except Exception as e:
            _LOGGER.debug("Input text may already exist: %s", e)

        # Input datetime for edit punctual trip datetime
        try:
            await hass.services.async_call(
                "input_datetime",
                "create",
                {
                    "name": f"{vehicle_id} - Edit Punctual DateTime",
                    "has_date": True,
                    "has_time": True,
                    "icon": "mdi:calendar-edit",
                },
            )
            _LOGGER.debug(
                "Created input_datetime for edit datetime: %s_edit_punctual_datetime",
                vehicle_id,
            )
        except Exception as e:
            _LOGGER.debug("Input datetime may already exist: %s", e)

        _LOGGER.info("Input helpers created successfully for: %s", vehicle_id)
        return DashboardImportResult(
            success=True,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_id,
            dashboard_type="simple",
            storage_method="input_helpers",
        )

    except Exception as e:
        _LOGGER.error("Failed to create input helpers for %s: %s", vehicle_id, e)
        return DashboardImportResult(
            success=False,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_id,
            error=str(e),
            dashboard_type="simple",
            storage_method="input_helpers",
        )


def _register_static_paths_legacy(
    hass: HomeAssistant, static_paths: list[Any], context_label: str,
) -> None:
    """Register static paths using the legacy HA register_static_path API.

    Called as a fallback when the new StaticPathConfig API is unavailable.
    """
    for path_spec in static_paths:
        try:
            if isinstance(path_spec, tuple):
                url_path, file_path, _ = path_spec
                hass.http.register_static_path(url_path, file_path)  # type: ignore[attr-defined]
            else:
                hass.http.register_static_path(  # type: ignore[attr-defined]
                    path_spec.url_path, path_spec.path
                )
        except RuntimeError as path_err:
            if "already registered" in str(path_err).lower():
                continue
            raise
    _LOGGER.info("Registered static paths using legacy method (%s)", context_label)


async def async_register_static_paths(
    hass: HomeAssistant,
) -> None:
    """Register static paths for the panel JS/CSS files.

    This must be called early before any browser tries to load the panel.
    """
    try:
        from homeassistant.components.http import StaticPathConfig

        HAS_STATIC_PATH_CONFIG = True
    except (
        ImportError
    ):  # pragma: no cover — depends on HA version; tested via integration
        HAS_STATIC_PATH_CONFIG = False

    component_dir = Path(__file__).parent.parent
    panel_js_path = component_dir / "frontend" / "panel.js"
    panel_css_path = component_dir / "frontend" / "panel.css"
    lit_bundle_path = component_dir / "frontend" / "lit-bundle.js"

    static_paths: list[Any] = []

    if panel_js_path.exists():
        static_paths.append(
            StaticPathConfig(  # pyright: ignore[reportPossiblyUnboundVariable]  # pyright: ignore[reportPossiblyUnboundVariable]
                "/ev-trip-planner/panel.js",
                str(panel_js_path),
                cache_headers=False,
            )
            if HAS_STATIC_PATH_CONFIG
            else ("/ev-trip-planner/panel.js", str(panel_js_path), False)
        )
    if lit_bundle_path.exists():
        static_paths.append(
            StaticPathConfig(  # pyright: ignore[reportPossiblyUnboundVariable]
                "/ev-trip-planner/lit-bundle.js",
                str(lit_bundle_path),
                cache_headers=False,
            )
            if HAS_STATIC_PATH_CONFIG
            else ("/ev-trip-planner/lit-bundle.js", str(lit_bundle_path), False)
        )
    if panel_css_path.exists():
        static_paths.append(
            StaticPathConfig(  # pyright: ignore[reportPossiblyUnboundVariable]
                "/ev-trip-planner/panel.css",
                str(panel_css_path),
                cache_headers=False,
            )
            if HAS_STATIC_PATH_CONFIG
            else ("/ev-trip-planner/panel.css", str(panel_css_path), False)
        )

    if not static_paths or hass.http is None:
        label = "early"
        reason = "hass.http is None" if static_paths else "no static files found"
        _LOGGER.warning("Cannot register static paths (%s): %s", label, reason)
        return

    try:
        await hass.http.async_register_static_paths(static_paths)
        _LOGGER.info(
            "Registered %d static path(s) for EV Trip Planner panel (early)",
            len(static_paths),
        )
    except (TypeError, AttributeError, RuntimeError):  # pragma: no cover
        _register_static_paths_legacy(hass, static_paths, "early")


async def async_register_panel_for_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    vehicle_id: str,
    vehicle_name: str,
) -> bool:
    """Register native panel for a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.
        vehicle_id: The vehicle ID string.
        vehicle_name: The vehicle display name.

    Returns:
        True if panel was registered successfully.
    """
    from .. import panel as panel_module

    panel_registered = False
    try:
        panel_result = await panel_module.async_register_panel(
            hass,
            vehicle_id=vehicle_id,
            vehicle_name=vehicle_name,
        )
        panel_registered = panel_result is True
        if not panel_registered:
            _LOGGER.error(
                "Panel registration returned False for vehicle %s - panel will not be available in sidebar",
                vehicle_name,
            )
    except Exception as err:
        _LOGGER.error(
            "Failed to register panel for vehicle %s: %s. Panel will not be available.",
            vehicle_name,
            err,
            exc_info=True,
        )
    return panel_registered


async def async_import_dashboard_for_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    vehicle_id: str,
) -> None:
    """Import dashboard configuration for a vehicle.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.
        vehicle_id: The vehicle ID string.
    """
    from ..dashboard import (
        import_dashboard as import_dashboard,  # type: ignore[reportAttributeAccessIssue]
    )

    try:
        use_charts = entry.data.get("use_charts", False)
        import_result = await import_dashboard(
            hass,
            vehicle_id,
            entry.data.get("vehicle_name", vehicle_id),
            use_charts=use_charts,
        )
        if not import_result.success:
            _LOGGER.warning(
                "Dashboard import failed for %s: %s",
                entry.data.get("vehicle_name", vehicle_id),
                import_result.error,
            )
    except Exception as e:
        _LOGGER.warning(
            "Dashboard import exception for %s: %s",
            entry.data.get("vehicle_name", vehicle_id),
            e,
        )
