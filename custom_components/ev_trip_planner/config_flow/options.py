"""Config flow — options handler (EVTripPlannerOptionsFlowHandler).

The primary ConfigFlow imports this module via ``from .options import
EVTripPlannerOptionsFlowHandler`` so that ``main.py`` can reference the
options class without circular imports.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from ..const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CONSUMPTION,
    CONF_SAFETY_MARGIN,
    CONF_SOH_SENSOR,
    CONF_T_BASE,
    DEFAULT_CONSUMPTION,
    DEFAULT_SAFETY_MARGIN,
    DEFAULT_SOH_SENSOR,
    DEFAULT_T_BASE,
    MIN_T_BASE,
    MAX_T_BASE,
)

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# EVTripPlannerOptionsFlowHandler
# ---------------------------------------------------------------------------


class EVTripPlannerOptionsFlowHandler(config_entries.OptionsFlow):
    """Maneja las opciones de configuración para EV Trip Planner."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Inicializa el flujo de opciones."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso inicial del flujo de opciones."""
        _LOGGER.debug("Options flow step init: showing form")

        if user_input is not None:
            _LOGGER.debug(
                "Options flow step init: battery=%.1f, charging=%.1f, "
                "consumption=%.2f, safety=%d, t_base=%.1f",
                user_input.get(CONF_BATTERY_CAPACITY, 0),
                user_input.get(CONF_CHARGING_POWER, 0),
                user_input.get(CONF_CONSUMPTION, 0),
                user_input.get(CONF_SAFETY_MARGIN, 0),
                user_input.get(CONF_T_BASE, 0),
            )

            # Only include options that were actually provided
            update_data = {}
            if CONF_BATTERY_CAPACITY in user_input:
                update_data[CONF_BATTERY_CAPACITY] = user_input[CONF_BATTERY_CAPACITY]
            if CONF_CHARGING_POWER in user_input:
                update_data[CONF_CHARGING_POWER] = user_input[CONF_CHARGING_POWER]
            if CONF_CONSUMPTION in user_input:
                update_data[CONF_CONSUMPTION] = user_input[CONF_CONSUMPTION]
            if CONF_SAFETY_MARGIN in user_input:
                update_data[CONF_SAFETY_MARGIN] = user_input[CONF_SAFETY_MARGIN]
            if CONF_T_BASE in user_input:
                update_data[CONF_T_BASE] = user_input[CONF_T_BASE]
            if CONF_SOH_SENSOR in user_input:
                update_data[CONF_SOH_SENSOR] = user_input[CONF_SOH_SENSOR]

            return self.async_create_entry(title="", data=update_data)  # type: ignore[return-value]

        # Get current values from config entry with safe defaults
        # Use .get() with safe handling for None data
        # Options take precedence over data for options flow (HA best practice)
        config_data: dict[str, Any] = {
            **dict(self._config_entry.data or {}),
            **dict(self._config_entry.options or {}),
        }
        current_battery = config_data.get(CONF_BATTERY_CAPACITY, 60.0)
        current_charging = config_data.get(CONF_CHARGING_POWER, 11.0)
        current_consumption = config_data.get(CONF_CONSUMPTION, DEFAULT_CONSUMPTION)
        current_safety = config_data.get(CONF_SAFETY_MARGIN, DEFAULT_SAFETY_MARGIN)
        current_t_base = config_data.get(CONF_T_BASE, DEFAULT_T_BASE)
        current_soh = config_data.get(CONF_SOH_SENSOR, DEFAULT_SOH_SENSOR)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BATTERY_CAPACITY, default=current_battery
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_CHARGING_POWER, default=current_charging
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_CONSUMPTION,
                        default=current_consumption,
                        description="Consumo en tiempo real (kWh/km) + fallback manual",
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_SAFETY_MARGIN, default=current_safety
                    ): vol.Coerce(int),
                    vol.Required(
                        CONF_T_BASE,
                        default=current_t_base,
                        description={
                            "suggested_value": current_t_base,
                            "placeholder": f"{current_t_base}",
                            "description": (
                                "Ventana de tiempo base (horas). Cuanto mayor sea, "
                                "más conservadora será la limitación dinámica de SOC. "
                                "Rango: 6-48h."
                            ),
                        },
                    ): vol.All(
                        vol.Coerce(float), vol.Range(min=MIN_T_BASE, max=MAX_T_BASE)
                    ),
                    vol.Optional(
                        CONF_SOH_SENSOR, default=current_soh
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            multiple=False,
                        )
                    ),
                }
            ),
        )  # type: ignore[return-value]


def async_get_options_flow(
    config_entry: config_entries.ConfigEntry,
) -> config_entries.OptionsFlow:
    """Devuelve el flujo de opciones para la entrada de configuración."""
    return EVTripPlannerOptionsFlowHandler(config_entry)
