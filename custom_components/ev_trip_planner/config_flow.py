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
from homeassistant.helpers import selector

from . import import_dashboard, is_lovelace_available
from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CONSUMPTION,
    CONF_HOME_COORDINATES,
    CONF_HOME_SENSOR,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_PLANNING_HORIZON,
    CONF_PLANNING_SENSOR,
    CONF_PLUGGED_SENSOR,
    CONF_SAFETY_MARGIN,
    CONF_VEHICLE_NAME,
    DEFAULT_CONSUMPTION,
    DEFAULT_MAX_DEFERRABLE_LOADS,
    DEFAULT_PLANNING_HORIZON,
    DEFAULT_SAFETY_MARGIN,
    DOMAIN,
    VEHICLE_TYPE_EV,
    VEHICLE_TYPE_PHEV,
)

_LOGGER = logging.getLogger(__name__)

# Step 1: Vehicle basic info
STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_VEHICLE_NAME): str,
        vol.Required("vehicle_type", default=VEHICLE_TYPE_EV): vol.In(
            [VEHICLE_TYPE_EV, VEHICLE_TYPE_PHEV]
        ),
    }
)

# Step 2: Sensors configuration
STEP_SENSORS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BATTERY_CAPACITY, default=60.0): vol.Coerce(float),
        vol.Required(CONF_CHARGING_POWER, default=11.0): vol.Coerce(float),
        vol.Required(
            CONF_CONSUMPTION,
            default=DEFAULT_CONSUMPTION,
            description="Consumo en tiempo real (kWh/km) + fallback manual",
        ): vol.Coerce(float),
        vol.Required(CONF_SAFETY_MARGIN, default=DEFAULT_SAFETY_MARGIN): vol.Coerce(int),
    }
)

# Step 3: EMHASS configuration
STEP_EMHASS_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_PLANNING_HORIZON,
            default=DEFAULT_PLANNING_HORIZON,
            description={
                "suggested_value": "7",
                "placeholder": "7",
                "description": "Número de días de planificación (1-365). Máximo: 365 días. Recomendado: 7 días para recurrencia semanal.",
            },
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
        vol.Required(
            CONF_MAX_DEFERRABLE_LOADS,
            default=DEFAULT_MAX_DEFERRABLE_LOADS,
            description={
                "suggested_value": "50",
                "placeholder": "50",
                "description": "Número máximo de cargas diferibles (10-100). Valor recomendado: 50.",
            },
        ): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
        vol.Optional(CONF_PLANNING_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="sensor",
                multiple=False,
            )
        ),
    }
)


class EVTripPlannerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Maneja el flujo de configuración para EV Trip Planner."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self) -> None:
        """Inicializa el flujo de configuración."""
        self._data: Dict[str, Any] = {}

    def _get_vehicle_data(self) -> Dict[str, Any]:
        """Get or initialize vehicle data from context."""
        if "vehicle_data" not in self.context:
            self.context["vehicle_data"] = {}
        return self.context["vehicle_data"]

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso 1: Configuración básica del vehículo."""
        if user_input is not None:
            # Store step 1 data in context
            vehicle_data = self._get_vehicle_data()
            vehicle_data.update(user_input)
            return await self.async_step_sensors()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            description_placeholders={
                "description": "Configure your electric vehicle for trip planning"
            },
        )

    async def async_step_sensors(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso 2: Configuración de sensores del vehículo."""
        if user_input is not None:
            # Store step 2 data in context
            vehicle_data = self._get_vehicle_data()
            vehicle_data.update(user_input)
            return await self.async_step_emhass()

        return self.async_show_form(
            step_id="sensors",
            data_schema=STEP_SENSORS_SCHEMA,
            description_placeholders={
                "description": "Select the sensors for battery monitoring"
            },
        )

    async def async_step_emhass(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso 3: Configuración de integración EMHASS (opcional).

        Fields:
        - planning_horizon_days (1-365, recommended 7)
        - max_deferrable_loads (manual input)
        - planning_sensor_entity (optional, entity selector)
        """
        if user_input is not None:
            # Validate planning horizon (1-365 days)
            planning_horizon = user_input.get(CONF_PLANNING_HORIZON)
            if planning_horizon is not None:
                if planning_horizon < 1 or planning_horizon > 365:
                    return self.async_show_form(
                        step_id="emhass",
                        data_schema=STEP_EMHASS_SCHEMA,
                        errors={"base": "invalid_planning_horizon"},
                        description_placeholders={
                            "description": "Configure EMHASS integration for smart charging optimization. This step is optional."
                        },
                    )

            # Validate max deferrable loads (10-100)
            max_loads = user_input.get(CONF_MAX_DEFERRABLE_LOADS)
            if max_loads is not None:
                if max_loads < 10 or max_loads > 100:
                    return self.async_show_form(
                        step_id="emhass",
                        data_schema=STEP_EMHASS_SCHEMA,
                        errors={"base": "invalid_max_deferrable_loads"},
                        description_placeholders={
                            "description": "Configure EMHASS integration for smart charging optimization. This step is optional."
                        },
                    )

            # Store step 3 data in context
            vehicle_data = self._get_vehicle_data()
            vehicle_data.update(user_input)

            # Validate planning horizon if sensor is provided
            if CONF_PLANNING_SENSOR in user_input and user_input[CONF_PLANNING_SENSOR]:
                planning_sensor = user_input[CONF_PLANNING_SENSOR]
                _LOGGER.info(
                    "EMHASS planning sensor configured: %s",
                    planning_sensor,
                )

            # Log EMHASS configuration
            _LOGGER.info(
                "EMHASS configuration: planning_horizon=%s days, max_deferrable_loads=%s",
                vehicle_data.get(CONF_PLANNING_HORIZON),
                vehicle_data.get(CONF_MAX_DEFERRABLE_LOADS),
            )

            # Return form for presence step (let user click Next)
            return self.async_show_form(
                step_id="presence",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "description": "Configure presence detection to prevent charging when vehicle is away."
                },
            )

        return self.async_show_form(
            step_id="emhass",
            data_schema=STEP_EMHASS_SCHEMA,
            description_placeholders={
                "description": "Configure EMHASS integration for smart charging optimization. This step is optional."
            },
        )

    async def async_step_presence(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso 4: Configuración de detección de presencia (opcional).

        Fields:
        - home_sensor (entity selector, binary_sensor domain)
        - plugged_sensor (entity selector, binary_sensor domain)
        - home_coordinates (optional)
        - vehicle_coordinates_sensor (optional)
        - notification_service (optional)
        """
        if user_input is not None and user_input:  # Has actual data
            # Validate home sensor exists
            if CONF_HOME_SENSOR in user_input:
                home_sensor = user_input[CONF_HOME_SENSOR]
                if not self.hass.states.get(home_sensor):
                    return self.async_show_form(
                        step_id="presence",
                        data_schema=vol.Schema({}),
                        errors={"base": "home_sensor_not_found"},
                        description_placeholders={
                            "description": "Configure presence detection to prevent charging when vehicle is away."
                        },
                    )

            # Validate plugged sensor exists
            if CONF_PLUGGED_SENSOR in user_input:
                plugged_sensor = user_input[CONF_PLUGGED_SENSOR]
                if not self.hass.states.get(plugged_sensor):
                    return self.async_show_form(
                        step_id="presence",
                        data_schema=vol.Schema({}),
                        errors={"base": "plugged_sensor_not_found"},
                        description_placeholders={
                            "description": "Configure presence detection to prevent charging when vehicle is away."
                        },
                    )

            # Validate coordinates format
            if CONF_HOME_COORDINATES in user_input:
                coords = user_input[CONF_HOME_COORDINATES]
                if coords:
                    try:
                        parts = coords.split(",")
                        if len(parts) != 2:
                            raise ValueError("Invalid format")
                        lat = float(parts[0].strip())
                        lon = float(parts[1].strip())
                        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                            raise ValueError("Out of range")
                    except (ValueError, AttributeError):
                        return self.async_show_form(
                            step_id="presence",
                            data_schema=vol.Schema({}),
                            errors={"base": "invalid_coordinates_format"},
                            description_placeholders={
                                "description": "Configure presence detection to prevent charging when vehicle is away."
                            },
                        )

            vehicle_data = self._get_vehicle_data()
            vehicle_data.update(user_input)
            # Presence step has data - create entry directly
            return await self._async_create_entry()

        # No input (None) - skip all optional steps and create entry
        if user_input is None:
            return await self._async_create_entry()

        # Empty input ({}) - go to notifications step
        return self.async_show_form(
            step_id="notifications",
            data_schema=vol.Schema({}),
            description_placeholders={
                "description": "Configure notification service for alerts."
            },
        )

    async def async_step_notifications(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso 5: Configuración de notificaciones (opcional).

        Fields:
        - notification_service (entity selector, notify domain)
        - notification_devices (multi-select, notify devices)
        """
        if user_input is not None:
            # Store step 5 data in context
            vehicle_data = self._get_vehicle_data()
            vehicle_data.update(user_input)

        # Always create entry from notifications step
        return await self._async_create_entry()

    async def _async_create_entry(self) -> FlowResult:
        """Crea la entrada de configuración."""
        vehicle_data = self._get_vehicle_data()
        vehicle_name = vehicle_data[CONF_VEHICLE_NAME]
        vehicle_id = vehicle_name.lower().replace(" ", "_")

        # Create the config entry
        result = self.async_create_entry(
            title=vehicle_name,
            data=vehicle_data,
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
