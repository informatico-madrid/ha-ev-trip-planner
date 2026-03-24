"""
Panel management for EV Trip Planner native panel.

This module provides functions to register and unregister native panels
in Home Assistant's sidebar for each configured vehicle.

The panel appears as a native HA panel (like 'config', 'developer-tools')
without requiring Lovelace UI.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from homeassistant.components import frontend, panel_custom
from homeassistant.core import HomeAssistant

from .const import DOMAIN

# Get the module path for static file serving
_MODULE_PATH = os.path.dirname(__file__)

_LOGGER = logging.getLogger(__name__)

# Panel configuration constants
PANEL_COMPONENT_NAME = "ev-trip-planner-panel"
PANEL_URL_PREFIX = "ev-trip-planner"
DEFAULT_SIDEBAR_ICON = "mdi:car-electric"

# Storage key for vehicle-to-panel mapping
VEHICLE_PANEL_MAPPING_KEY = f"{DOMAIN}_vehicle_panel_mapping"


async def async_register_panel(
    hass: HomeAssistant,
    vehicle_id: str,
    vehicle_name: str,
) -> bool:
    """
    Register a native panel for a vehicle in Home Assistant sidebar.

    Args:
        hass: Home Assistant instance
        vehicle_id: Unique vehicle identifier
        vehicle_name: Display name for the vehicle in sidebar

    Returns:
        True if panel was registered successfully, False otherwise
    """
    frontend_url_path = f"{PANEL_URL_PREFIX}-{vehicle_id}"

    try:
        # First, try to unregister any existing panel to avoid "Overwriting panel" error
        try:
            await frontend.async_remove_panel(hass, frontend_url_path)
            _LOGGER.debug("Removed existing panel at path %s", frontend_url_path)
        except Exception:
            # It's OK if there's no existing panel to remove
            pass

        # Use panel_custom.async_register_panel - this is the correct API
        # Note: js_url uses absolute path from root - all vehicles share the same panel.js
        # Using absolute path to avoid URL resolution issues in HA
        await panel_custom.async_register_panel(
            hass=hass,
            frontend_url_path=frontend_url_path,
            webcomponent_name=PANEL_COMPONENT_NAME,
            js_url=f"/{DOMAIN.replace('_', '-')}/panel.js",
            sidebar_title=vehicle_name,
            sidebar_icon=DEFAULT_SIDEBAR_ICON,
            config={"vehicle_id": vehicle_id},
            require_admin=False,
            embed_iframe=False,
        )

        # Register additional static resource for panel.css
        # This ensures the CSS file is served correctly
        try:
            hass.http.register_static_paths(
                [
                    (
                        f"/{DOMAIN.replace('_', '-')}/panel.css",
                        f"{_MODULE_PATH}/frontend/panel.css",
                    ),
                ]
            )
            _LOGGER.debug("Registered static path for panel.css")
        except Exception as ex:
            _LOGGER.warning("Failed to register static path for panel.css: %s", ex)

        # Store vehicle-to-panel mapping
        _store_vehicle_panel_mapping(hass, vehicle_id, frontend_url_path)

        _LOGGER.info(
            "Registered native panel for vehicle %s at path %s",
            vehicle_id,
            frontend_url_path,
        )
        return True

    except Exception as ex:  # pylint: disable=broad-except
        _LOGGER.error(
            "Failed to register panel for vehicle %s: %s",
            vehicle_id,
            ex,
        )
        return False


async def async_unregister_panel(
    hass: HomeAssistant,
    vehicle_id: str,
) -> bool:
    """
    Unregister a native panel for a vehicle from Home Assistant sidebar.

    Args:
        hass: Home Assistant instance
        vehicle_id: Unique vehicle identifier

    Returns:
        True if panel was unregistered successfully, False otherwise
    """
    frontend_url_path = f"{PANEL_URL_PREFIX}-{vehicle_id}"

    try:
        # Remove the panel from frontend
        await frontend.async_remove_panel(hass, frontend_url_path)

        # Remove from vehicle-to-panel mapping
        _remove_vehicle_panel_mapping(hass, vehicle_id)

        _LOGGER.info(
            "Unregistered native panel for vehicle %s from path %s",
            vehicle_id,
            frontend_url_path,
        )
        return True

    except Exception as ex:  # pylint: disable=broad-except
        _LOGGER.error(
            "Failed to unregister panel for vehicle %s: %s",
            vehicle_id,
            ex,
        )
        return False


def _store_vehicle_panel_mapping(
    hass: HomeAssistant,
    vehicle_id: str,
    frontend_url_path: str,
) -> None:
    """
    Store the mapping between vehicle ID and panel URL path.

    Args:
        hass: Home Assistant instance
        vehicle_id: Unique vehicle identifier
        frontend_url_path: URL path where the panel is registered
    """
    if VEHICLE_PANEL_MAPPING_KEY not in hass.data:
        hass.data[VEHICLE_PANEL_MAPPING_KEY] = {}

    hass.data[VEHICLE_PANEL_MAPPING_KEY][vehicle_id] = frontend_url_path
    _LOGGER.debug(
        "Stored panel mapping: vehicle_id=%s -> path=%s",
        vehicle_id,
        frontend_url_path,
    )


def _remove_vehicle_panel_mapping(
    hass: HomeAssistant,
    vehicle_id: str,
) -> None:
    """
    Remove the mapping between vehicle ID and panel URL path.

    Args:
        hass: Home Assistant instance
        vehicle_id: Unique vehicle identifier
    """
    if VEHICLE_PANEL_MAPPING_KEY in hass.data:
        hass.data[VEHICLE_PANEL_MAPPING_KEY].pop(vehicle_id, None)
        _LOGGER.debug("Removed panel mapping for vehicle_id=%s", vehicle_id)


def get_vehicle_panel_url_path(
    hass: HomeAssistant,
    vehicle_id: str,
) -> str | None:
    """
    Get the panel URL path for a vehicle.

    Args:
        hass: Home Assistant instance
        vehicle_id: Unique vehicle identifier

    Returns:
        The panel URL path or None if not found
    """
    return hass.data.get(VEHICLE_PANEL_MAPPING_KEY, {}).get(vehicle_id)


def get_all_panel_mappings(
    hass: HomeAssistant,
) -> dict[str, str]:
    """
    Get all vehicle-to-panel mappings.

    Args:
        hass: Home Assistant instance

    Returns:
        Dictionary mapping vehicle_id to panel_url_path
    """
    return hass.data.get(VEHICLE_PANEL_MAPPING_KEY, {})


async def async_register_all_panels(
    hass: HomeAssistant,
    vehicles: list[dict[str, Any]],
) -> None:
    """
    Register panels for all existing vehicles.

    This is useful during startup to restore panels for all
    previously configured vehicles.

    Args:
        hass: Home Assistant instance
        vehicles: List of vehicle configuration dictionaries
    """
    for vehicle in vehicles:
        vehicle_id = vehicle.get("vehicle_id")
        vehicle_name = vehicle.get("name", vehicle.get("vehicle_id", "Unknown"))

        if vehicle_id:
            await async_register_panel(hass, vehicle_id, vehicle_name)
