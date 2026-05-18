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

_LOGGER = logging.getLogger(__name__)


def _register_static_paths_legacy(
    hass: HomeAssistant,
    static_paths: list[Any],
    context_label: str,
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


# CC-N-ACCEPTED: cc=12 — static path registration with branches for different
# dashboard file types, vehicle-specific path computation, and conditional
# path registration for each discovered file.
async def async_register_static_paths(
    hass: HomeAssistant,
) -> None:
    """Register static paths for the panel JS/CSS files.

    This must be called early before any browser tries to load the panel.
    """
    try:
        from homeassistant.components.http import StaticPathConfig

        HAS_STATIC_PATH_CONFIG = True
    except ImportError:  # pragma: no cover reason=HA version dependency — static_path_config only available in newer HA versions, tested via integration
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
    except (
        TypeError,
        AttributeError,
        RuntimeError,
    ):  # pragma: no cover reason=HA version compatibility fallback — triggered when async registration method fails with type/attribute/runtime error
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
