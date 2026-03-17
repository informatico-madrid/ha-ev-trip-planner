"""Flujo de configuración para el componente EV Trip Planner.

Permite añadir vehículos y configurar parámetros de planificación.
Cumple con las reglas de Home Assistant 2026 para tipado estricto y runtime_data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from . import import_dashboard, is_lovelace_available
from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CONSUMPTION,
    CONF_SAFETY_MARGIN,
    CONF_VEHICLE_NAME,
    DEFAULT_CONSUMPTION,
    DEFAULT_SAFETY_MARGIN,
    DOMAIN,
    VEHICLE_TYPE_EV,
    VEHICLE_TYPE_PHEV,
)

_LOGGER = logging.getLogger(__name__)

class EVTripPlannerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Maneja el flujo de configuración para EV Trip Planner."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso inicial del flujo de configuración."""
        if user_input is not None:
            vehicle_name = user_input[CONF_VEHICLE_NAME]
            vehicle_id = vehicle_name.lower().replace(" ", "_")

            # Create the config entry
            result = self.async_create_entry(
                title=vehicle_name,
                data=user_input,
            )

            # Try to import dashboard after entry creation
            # We do this after creation to ensure hass is fully initialized
            try:
                # Check Lovelace availability
                use_charts = is_lovelace_available(self.hass)
                _LOGGER.info(
                    "Lovelace available: %s, will use %s dashboard",
                    use_charts,
                    "full" if use_charts else "simple",
                )

                # Attempt to import dashboard (non-blocking)
                # Note: This may fail silently if Lovelace is not fully ready
                # The dashboard can also be imported manually from UI
                await import_dashboard(
                    self.hass,
                    vehicle_id=vehicle_id,
                    vehicle_name=vehicle_name,
                    use_charts=use_charts,
                )
            except Exception as err:  # pragma: no cover
                # Log but don't fail the flow - dashboard import is optional
                _LOGGER.warning(
                    "Could not auto-import dashboard for %s: %s",
                    vehicle_name,
                    err,
                )

            return result

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VEHICLE_NAME): str,
                    vol.Required("vehicle_type", default=VEHICLE_TYPE_EV): vol.In(
                        [VEHICLE_TYPE_EV, VEHICLE_TYPE_PHEV]
                    ),
                    vol.Required(CONF_BATTERY_CAPACITY, default=60.0): vol.Coerce(float),
                    vol.Required(CONF_CHARGING_POWER, default=11.0): vol.Coerce(float),
                    vol.Required(
                        CONF_CONSUMPTION,
                        default=DEFAULT_CONSUMPTION,
                        description="Consumo en tiempo real (kWh/km) + fallback manual",
                    ): vol.Coerce(float),
                    vol.Required(CONF_SAFETY_MARGIN, default=DEFAULT_SAFETY_MARGIN): vol.Coerce(int),
                }
            ),
        )

    @callback
    def async_get_options_flow(
        self, config_entry: config_entries.ConfigEntry
    ) -> config_entries.OptionsFlow:
        """Devuelve el flujo de opciones para la entrada de configuración."""
        return EVTripPlannerOptionsFlowHandler(config_entry)

class EVTripPlannerOptionsFlowHandler(config_entries.OptionsFlow):
    """Maneja las opciones de configuración para EV Trip Planner."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Inicializa el flujo de opciones."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso inicial del flujo de opciones."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BATTERY_CAPACITY, default=self.config_entry.data.get(CONF_BATTERY_CAPACITY, 60.0)
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_CHARGING_POWER, default=self.config_entry.data.get(CONF_CHARGING_POWER, 11.0)
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_CONSUMPTION,
                        default=self.config_entry.data.get(CONF_CONSUMPTION, DEFAULT_CONSUMPTION),
                        description="Consumo en tiempo real (kWh/km) + fallback manual",
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_SAFETY_MARGIN, default=self.config_entry.data.get(CONF_SAFETY_MARGIN, DEFAULT_SAFETY_MARGIN)
                    ): vol.Coerce(int),
                }
            ),
        )


# Alias for backward compatibility with tests
EVTripPlannerConfigFlow = EVTripPlannerFlowHandler
