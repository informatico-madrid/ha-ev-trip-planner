"""Panel custom configuration for EV Trip Planner."""

import logging

from homeassistant.components.panel_custom import async_register_panel

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up the panel custom integration."""
    # Register panel for dynamic vehicle IDs
    # The panel will be accessible at /panel/ev-trip-planner-{vehicle_id}
    async_register_panel(
        hass,
        frontend_url_path="ev-trip-planner",
        webcomponent_name="ev-trip-planner-panel",
        sidebar_title="EV Trip Planner",
        sidebar_icon="mdi:car",
        config={},
    )

    _LOGGER.info("EV Trip Planner panel registered successfully")
    return True
