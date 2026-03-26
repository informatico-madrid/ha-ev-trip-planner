"""Panel custom configuration for EV Trip Planner."""

import logging

from homeassistant.components.panel_custom import async_register_panel

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up the panel custom integration."""
    # Register panel for dynamic vehicle IDs
    # The panel will be accessible at /panel/ev-trip-planner-{vehicle_id}
    async_register_panel(
        hass,
        panel_url="ev-trip-planner",
        webcomponent_name="ev-trip-planner-panel",
        title="EV Trip Planner",
        frontend_url_path="ev-trip-planner",
        config={},
        side_panel_icon="mdi:car",
    )

    _LOGGER.info("EV Trip Planner panel registered successfully")
    return True
