"""Config flow for EV Trip Planner integration."""

from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CHARGING_STATUS,
    CONF_CONSUMPTION,
    CONF_CONTROL_TYPE,
    CONF_HOME_COORDINATES,
    CONF_HOME_SENSOR,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_NOTIFICATION_SERVICE,
    CONF_PLANNING_HORIZON,
    CONF_PLANNING_SENSOR,
    CONF_PLUGGED_SENSOR,
    CONF_RANGE_SENSOR,
    CONF_SAFETY_MARGIN,
    CONF_SOC_SENSOR,
    CONF_VEHICLE_COORDINATES_SENSOR,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_TYPE,
    CONTROL_TYPE_EXTERNAL,
    CONTROL_TYPE_NONE,
    CONTROL_TYPE_SCRIPT,
    CONTROL_TYPE_SERVICE,
    CONTROL_TYPE_SWITCH,
    DEFAULT_CONSUMPTION,
    DEFAULT_CONTROL_TYPE,
    DEFAULT_MAX_DEFERRABLE_LOADS,
    DEFAULT_NOTIFICATION_SERVICE,
    DEFAULT_PLANNING_HORIZON,
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
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="battery",
                    )
                ),
                vol.Required(CONF_BATTERY_CAPACITY): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=200)
                ),
                vol.Required(CONF_CHARGING_POWER): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=50)
                ),
                vol.Optional(CONF_RANGE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="distance",
                    )
                ),
                vol.Optional(CONF_CHARGING_STATUS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="binary_sensor",
                    )
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
            # Merge all data and move to EMHASS step
            vehicle_data = self.context["vehicle_data"]
            vehicle_data.update(user_input)
            self.context["vehicle_data"] = vehicle_data

            return await self.async_step_emhass()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_CONSUMPTION, default=DEFAULT_CONSUMPTION): vol.All(
                    vol.Coerce(float), vol.Range(min=0.05, max=0.5)
                ),
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
                                value=CONTROL_TYPE_SCRIPT,
                                label="Script",
                            ),
                            selector.SelectOptionDict(
                                value=CONTROL_TYPE_EXTERNAL,
                                label="Notifications Only (no control)",
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

    async def async_step_emhass(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Configure EMHASS integration parameters."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate planning horizon (1-30 days)
            planning_horizon = user_input.get(CONF_PLANNING_HORIZON, DEFAULT_PLANNING_HORIZON)
            if planning_horizon < 1 or planning_horizon > 30:
                errors["base"] = "invalid_planning_horizon"
                return self.async_show_form(
                    step_id="emhass",
                    data_schema=self._get_emhass_schema(),
                    errors=errors,
                    description_placeholders=self._get_emhass_placeholders(),
                )

            # Validate max deferrable loads (10-100)
            max_loads = user_input.get(CONF_MAX_DEFERRABLE_LOADS, DEFAULT_MAX_DEFERRABLE_LOADS)
            if max_loads < 10 or max_loads > 100:
                errors["base"] = "invalid_max_deferrable_loads"
                return self.async_show_form(
                    step_id="emhass",
                    data_schema=self._get_emhass_schema(),
                    errors=errors,
                    description_placeholders=self._get_emhass_placeholders(),
                )

            # Store data and continue to presence step
            vehicle_data = self.context["vehicle_data"]
            vehicle_data.update(user_input)
            self.context["vehicle_data"] = vehicle_data

            # Return the presence form (don't auto-submit it)
            return self.async_show_form(
                step_id="presence",
                data_schema=self._get_presence_schema(),
                description_placeholders=self._get_presence_placeholders(),
            )

        return self.async_show_form(
            step_id="emhass",
            data_schema=self._get_emhass_schema(),
            errors=errors,
            description_placeholders=self._get_emhass_placeholders(),
        )

    def _get_emhass_schema(self) -> vol.Schema:
        """Get the data schema for EMHASS step."""
        return vol.Schema(
            {
                vol.Optional(
                    CONF_PLANNING_HORIZON, default=DEFAULT_PLANNING_HORIZON
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
                vol.Optional(CONF_PLANNING_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        # Filter for numeric sensors (no specific device_class for planning)
                    )
                ),
                vol.Optional(
                    CONF_MAX_DEFERRABLE_LOADS, default=DEFAULT_MAX_DEFERRABLE_LOADS
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
            }
        )

    def _get_emhass_placeholders(self) -> dict[str, str]:
        """Get description placeholders for EMHASS step."""
        return {
            "horizon_help": "Days to plan ahead (must be ≤ EMHASS planning horizon)",
            "max_loads_help": "Maximum number of simultaneous trips (affects EMHASS config)",
            "config_snippet": """
# Add to your EMHASS configuration.yaml:
# (Create as many entries as your max_deferrable_loads setting)
emhass:
  deferrable_loads:
    - def_total_hours: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'def_total_hours') | default(0) }}"
      P_deferrable_nom: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'P_deferrable_nom') | default(0) }}"
      # ... repeat for indices 1-49 as needed
            """,
        }

    async def async_step_presence(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Configure presence detection (optional)."""
        vehicle_data = self.context["vehicle_data"]
        
        # Skip this optional step if no user_input or empty dict
        # BUT only if we have the required vehicle_name to create entry
        if user_input is None or not user_input:
            if CONF_VEHICLE_NAME in vehicle_data:
                # We have enough data, create entry
                return self.async_create_entry(
                    title=vehicle_data[CONF_VEHICLE_NAME],
                    data=vehicle_data,
                )
            else:
                # Not enough data, show form (shouldn't happen in normal flow)
                return self.async_show_form(
                    step_id="presence",
                    data_schema=self._get_presence_schema(),
                    description_placeholders=self._get_presence_placeholders(),
                )

        # Process coordinate sensors (combine lat/lon if provided separately)
        processed_input = self._process_coordinate_sensors(user_input)
        user_input.update(processed_input)

        # Validate sensors if provided
        if CONF_HOME_SENSOR in user_input and user_input[CONF_HOME_SENSOR]:
            home_sensor = user_input[CONF_HOME_SENSOR]
            if not self.hass.states.get(home_sensor):
                return self.async_show_form(
                    step_id="presence",
                    data_schema=self._get_presence_schema(),
                    errors={"base": "home_sensor_not_found"},
                    description_placeholders=self._get_presence_placeholders(),
                )

        if CONF_PLUGGED_SENSOR in user_input and user_input[CONF_PLUGGED_SENSOR]:
            plugged_sensor = user_input[CONF_PLUGGED_SENSOR]
            if not self.hass.states.get(plugged_sensor):
                return self.async_show_form(
                    step_id="presence",
                    data_schema=self._get_presence_schema(),
                    errors={"base": "plugged_sensor_not_found"},
                    description_placeholders=self._get_presence_placeholders(),
                )

        # Validate coordinates format if provided
        if CONF_HOME_COORDINATES in user_input and user_input[CONF_HOME_COORDINATES]:
            coords = user_input[CONF_HOME_COORDINATES]
            if not self._validate_coordinates(coords):
                return self.async_show_form(
                    step_id="presence",
                    data_schema=self._get_presence_schema(),
                    errors={"base": "invalid_coordinates_format"},
                    description_placeholders=self._get_presence_placeholders(),
                )

        # Store data and create entry
        vehicle_data.update(user_input)
        
        return self.async_create_entry(
            title=vehicle_data[CONF_VEHICLE_NAME],
            data=vehicle_data,
        )

    def _get_presence_schema(self) -> vol.Schema:
        """Get the data schema for presence step."""
        return vol.Schema(
            {
                vol.Optional(CONF_HOME_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Optional(CONF_PLUGGED_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Optional(CONF_HOME_COORDINATES): cv.string,
                # Separate latitude and longitude sensors (OVMS style)
                vol.Optional("vehicle_coordinates_sensor_lat"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("vehicle_coordinates_sensor_lon"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                # Combined coordinates sensor (alternative)
                vol.Optional(CONF_VEHICLE_COORDINATES_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_NOTIFICATION_SERVICE, default=DEFAULT_NOTIFICATION_SERVICE
                ): cv.string,
            }
        )

    def _get_presence_placeholders(self) -> dict[str, str]:
        """Get description placeholders for presence step."""
        return {
            "presence_help": "Optional: Configure to prevent charging when vehicle not home/plugged",
            "sensor_help": "Select binary_sensors that indicate home/plugged status",
            "coordinates_help": "Or use coordinates: provide home coordinates and vehicle location sensor",
        }

    def _get_sensors_schema(self) -> vol.Schema:
        """Get the data schema for sensors step."""
        return vol.Schema(
            {
                vol.Required(CONF_SOC_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="battery",
                    )
                ),
                vol.Required(CONF_BATTERY_CAPACITY): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=200)
                ),
                vol.Required(CONF_CHARGING_POWER): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=50)
                ),
                vol.Optional(CONF_RANGE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="distance",
                    )
                ),
                vol.Optional(CONF_CHARGING_STATUS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="binary_sensor",
                    )
                ),
            }
        )

    def _process_coordinate_sensors(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Process separate lat/lon coordinate sensors into a single sensor reference."""
        result = {}
        
        # Check if we have separate lat/lon sensors (OVMS style)
        lat_sensor = user_input.get("vehicle_coordinates_sensor_lat")
        lon_sensor = user_input.get("vehicle_coordinates_sensor_lon")
        
        if lat_sensor and lon_sensor:
            # Combine them into a single reference (format: lat_sensor,lon_sensor)
            result[CONF_VEHICLE_COORDINATES_SENSOR] = f"{lat_sensor},{lon_sensor}"
        elif CONF_VEHICLE_COORDINATES_SENSOR in user_input:
            # Use the existing combined sensor if provided
            result[CONF_VEHICLE_COORDINATES_SENSOR] = user_input[CONF_VEHICLE_COORDINATES_SENSOR]
            
        return result

    def _validate_coordinates(self, coords: str) -> bool:
        """Validate coordinate format."""
        try:
            if coords.startswith("[") and coords.endswith("]"):
                coords = coords[1:-1]
            lat, lon = map(float, coords.split(","))
            return -90 <= lat <= 90 and -180 <= lon <= 180
        except (ValueError, AttributeError):
            return False
