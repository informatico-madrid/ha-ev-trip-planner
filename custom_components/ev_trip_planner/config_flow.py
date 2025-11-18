"""Config flow for EV Trip Planner integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CHARGING_STATUS,
    CONF_CONSUMPTION,
    CONF_CONTROL_TYPE,
    CONF_RANGE_SENSOR,
    CONF_SAFETY_MARGIN,
    CONF_SOC_SENSOR,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_TYPE,
    CONTROL_TYPE_EXTERNAL,
    CONTROL_TYPE_NONE,
    CONTROL_TYPE_SERVICE,
    CONTROL_TYPE_SWITCH,
    DEFAULT_CONSUMPTION,
    DEFAULT_CONTROL_TYPE,
    DEFAULT_SAFETY_MARGIN,
    DEFAULT_VEHICLE_TYPE,
    DOMAIN,
    VEHICLE_TYPE_EV,
    VEHICLE_TYPE_PHEV,
)

_LOGGER = logging.getLogger(__name__)


class EVTripPlannerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EV Trip Planner."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step - Vehicle basic info."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate vehicle name is unique
            await self.async_set_unique_id(user_input[CONF_VEHICLE_NAME].lower())
            self._abort_if_unique_id_configured()
            
            # Store basic vehicle info and move to sensors step
            self.context["vehicle_data"] = user_input
            return await self.async_step_sensors()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_VEHICLE_NAME): cv.string,
                vol.Required(
                    CONF_VEHICLE_TYPE, default=DEFAULT_VEHICLE_TYPE
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=VEHICLE_TYPE_EV, label="Electric Vehicle (EV)"
                            ),
                            selector.SelectOptionDict(
                                value=VEHICLE_TYPE_PHEV,
                                label="Plug-in Hybrid (PHEV)",
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "name": "Enter a friendly name for your vehicle (e.g., 'Tesla Model 3', 'Chispitas')"
            },
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the sensors configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Merge with previous step data
            vehicle_data = self.context["vehicle_data"]
            vehicle_data.update(user_input)
            self.context["vehicle_data"] = vehicle_data
            
            return await self.async_step_consumption()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SOC_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_BATTERY_CAPACITY): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=200)
                ),
                vol.Required(CONF_CHARGING_POWER): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=50)
                ),
                vol.Optional(CONF_RANGE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_CHARGING_STATUS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
            }
        )

        return self.async_show_form(
            step_id="sensors",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "soc": "Select the sensor that reports battery level (%)",
                "capacity": "Enter total battery capacity in kWh",
                "power": "Enter your charger power in kW",
            },
        )

    async def async_step_consumption(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle consumption configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Merge all data and create entry
            vehicle_data = self.context["vehicle_data"]
            vehicle_data.update(user_input)
            
            return self.async_create_entry(
                title=vehicle_data[CONF_VEHICLE_NAME],
                data=vehicle_data,
            )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_CONSUMPTION, default=DEFAULT_CONSUMPTION
                ): vol.All(vol.Coerce(float), vol.Range(min=0.05, max=0.5)),
                vol.Required(
                    CONF_SAFETY_MARGIN, default=DEFAULT_SAFETY_MARGIN
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=50)),
                vol.Required(
                    CONF_CONTROL_TYPE, default=DEFAULT_CONTROL_TYPE
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=CONTROL_TYPE_NONE,
                                label="None (Notifications only)",
                            ),
                            selector.SelectOptionDict(
                                value=CONTROL_TYPE_SWITCH,
                                label="Switch entity",
                            ),
                            selector.SelectOptionDict(
                                value=CONTROL_TYPE_SERVICE,
                                label="HA Service call",
                            ),
                            selector.SelectOptionDict(
                                value=CONTROL_TYPE_EXTERNAL,
                                label="External (e.g., EMHASS)",
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="consumption",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "consumption": "Average energy consumption per km (kWh/km)",
                "margin": "Safety margin percentage to add to calculations",
                "control": "How should charging be controlled?",
            },
        )
