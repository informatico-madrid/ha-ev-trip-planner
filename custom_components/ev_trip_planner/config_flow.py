"""Flujo de configuración para el componente EV Trip Planner.

Permite añadir vehículos y configurar parámetros de planificación.
Cumple con las reglas de Home Assistant 2026 para tipado estricto y runtime_data.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .__init__ import import_dashboard, is_lovelace_available
from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CHARGING_SENSOR,
    CONF_CONSUMPTION,
    CONF_HOME_SENSOR,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFICATION_SERVICE,
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
)

_LOGGER = logging.getLogger(__name__)

# Step 1: Vehicle basic info
STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_VEHICLE_NAME): str,
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
        vol.Required(CONF_SAFETY_MARGIN, default=DEFAULT_SAFETY_MARGIN): vol.Coerce(
            int
        ),
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
                "description": (
                    "Número de días de planificación (1-365). "
                    "Máximo: 365 días. Recomendado: 7 días."
                ),
            },
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
        vol.Required(
            CONF_MAX_DEFERRABLE_LOADS,
            default=DEFAULT_MAX_DEFERRABLE_LOADS,
            description={
                "suggested_value": "50",
                "placeholder": "50",
                "description": "Cargas diferibles (10-100). Valor recomendado: 50.",
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

# Step 4: Presence configuration
STEP_PRESENCE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CHARGING_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="binary_sensor",
                multiple=False,
            )
        ),
        vol.Optional(CONF_HOME_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="binary_sensor",
                multiple=False,
            )
        ),
        vol.Optional(CONF_PLUGGED_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="binary_sensor",
                multiple=False,
            )
        ),
    }
)

# Step 5: Notifications configuration
STEP_NOTIFICATIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NOTIFICATION_SERVICE): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="notify",
                multiple=False,
            )
        ),
        vol.Optional(CONF_NOTIFICATION_DEVICES): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="notify",
                multiple=True,
            )
        ),
    }
)


def _read_emhass_config(
    config_path: str = "/home/malka/emhass/config/config.json",
) -> Optional[Dict[str, Any]]:
    """Lee la configuración de EMHASS desde el archivo de configuración.

    Args:
        config_path: Ruta al archivo de configuración de EMHASS.

    Returns:
        Diccionario con la configuración o None si no se puede leer.
    """
    if not os.path.exists(config_path):
        _LOGGER.debug("EMHASS config file not found at %s", config_path)
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        _LOGGER.debug("EMHASS config loaded successfully from %s", config_path)
        return config
    except (json.JSONDecodeError, IOError) as err:
        _LOGGER.warning("Could not read EMHASS config from %s: %s", config_path, err)
        return None


def _get_emhass_planning_horizon(
    emhass_config: Optional[Dict[str, Any]],
) -> Optional[int]:
    """Extrae el horizonte de planificación desde la configuración de EMHASS.

    Args:
        emhass_config: Diccionario con la configuración de EMHASS.

    Returns:
        Horizonte de planificación en días o None si no se puede determinar.
    """
    if not emhass_config:
        return None

    # Get end_timesteps from the first deferrable load
    end_timesteps = emhass_config.get("end_timesteps_of_each_deferrable_load")
    if not end_timesteps or not isinstance(end_timesteps, list):
        return None
    if len(end_timesteps) == 0:
        return None

    # EMHASS uses 60-minute timesteps, so 168 timesteps = 168 hours = 7 days
    max_timesteps = end_timesteps[0]
    planning_horizon_days = max_timesteps // 24

    if planning_horizon_days < 1:
        return None

    return planning_horizon_days


def _get_emhass_max_deferrable_loads(
    emhass_config: Optional[Dict[str, Any]],
) -> Optional[int]:
    """Extrae el número máximo de cargas diferibles desde la configuración de EMHASS.

    Args:
        emhass_config: Diccionario con la configuración de EMHASS.

    Returns:
        Número máximo de cargas diferibles o None si no se puede determinar.
    """
    if not emhass_config:
        return None

    num_loads = emhass_config.get("number_of_deferrable_loads")
    if num_loads is None or num_loads < 1:
        return None

    return num_loads


@config_entries.HANDLERS.register(DOMAIN)
class EVTripPlannerFlowHandler(config_entries.ConfigFlow):
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
        _LOGGER.debug("Config flow step 1 (user): showing form")
        if user_input is not None:
            # Store step 1 data in context
            vehicle_data = self._get_vehicle_data()
            vehicle_data.update(user_input)
            _LOGGER.debug(
                "Config flow step 1 (user): vehicle_name=%s",
                user_input.get(CONF_VEHICLE_NAME),
            )
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
        _LOGGER.debug("Config flow step 2 (sensors): showing form")
        if user_input is not None:
            # Store step 2 data in context
            vehicle_data = self._get_vehicle_data()
            vehicle_data.update(user_input)
            _LOGGER.debug(
                "Config flow step 2 (sensors): battery_capacity=%.1f, "
                "charging_power=%.1f, consumption=%.2f, safety_margin=%d",
                user_input.get(CONF_BATTERY_CAPACITY, 0),
                user_input.get(CONF_CHARGING_POWER, 0),
                user_input.get(CONF_CONSUMPTION, 0),
                user_input.get(CONF_SAFETY_MARGIN, 0),
            )
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

        Validation:
        - Try to read EMHASS config from /home/malka/emhass/config/config.json
        - If planning sensor is configured, try to read its value
        - Validate planning horizon against sensor value if available
        - Manual input fallback if sensor not available
        """
        _LOGGER.debug("Config flow step 3 (emhass): showing form")

        # Try to read EMHASS config for validation defaults
        emhass_config = _read_emhass_config()
        emhass_horizon = _get_emhass_planning_horizon(emhass_config)
        emhass_max_loads = _get_emhass_max_deferrable_loads(emhass_config)

        if emhass_horizon:
            _LOGGER.info(
                "EMHASS config: horizon=%s days, max_loads=%s",
                emhass_horizon,
                emhass_max_loads,
            )

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
                            "description": "Configure EMHASS (optional)."
                        },
                    )

                # Validate against EMHASS config if available
                if emhass_horizon and planning_horizon > emhass_horizon:
                    _LOGGER.warning(
                        "User planning_horizon (%d) exceeds EMHASS config (%d days). "
                        "This may cause optimization issues.",
                        planning_horizon,
                        emhass_horizon,
                    )

                # Validate against planning sensor if configured
                planning_sensor = user_input.get(CONF_PLANNING_SENSOR)
                if planning_sensor:
                    sensor_state = self.hass.states.get(planning_sensor)
                    if sensor_state and sensor_state.state not in (
                        "unknown",
                        "unavailable",
                        "",
                    ):
                        try:
                            sensor_horizon = int(float(sensor_state.state))
                            _LOGGER.info(
                                "Planning sensor %s value: %d days",
                                planning_sensor,
                                sensor_horizon,
                            )
                            # Warn if user input exceeds sensor value
                            if planning_horizon > sensor_horizon:
                                _LOGGER.warning(
                                    "User horizon (%d) > sensor (%d days). "
                                    "May cause issues. Consider <= %d.",
                                    planning_horizon,
                                    sensor_horizon,
                                    sensor_horizon,
                                )
                        except (ValueError, TypeError) as err:
                            _LOGGER.warning(
                                "Could not parse planning sensor %s value: %s",
                                planning_sensor,
                                err,
                            )
                    else:
                        _LOGGER.info(
                            "Planning sensor %s not available, using manual input",
                            planning_sensor,
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
                            "description": "Configure EMHASS (optional)."
                        },
                    )

                # Validate against EMHASS config if available
                if emhass_max_loads and max_loads > emhass_max_loads:
                    _LOGGER.warning(
                        "User loads (%d) > EMHASS config (%d loads). "
                        "This may cause optimization issues.",
                        max_loads,
                        emhass_max_loads,
                    )

            # Store step 3 data in context
            vehicle_data = self._get_vehicle_data()
            vehicle_data.update(user_input)

            # Log planning sensor configuration
            if CONF_PLANNING_SENSOR in user_input and user_input[CONF_PLANNING_SENSOR]:
                planning_sensor = user_input[CONF_PLANNING_SENSOR]
                _LOGGER.info(
                    "EMHASS planning sensor configured: %s",
                    planning_sensor,
                )

            # Log EMHASS configuration
            _LOGGER.info(
                "EMHASS config: horizon=%s, max_loads=%s, sensor=%s",
                vehicle_data.get(CONF_PLANNING_HORIZON),
                vehicle_data.get(CONF_MAX_DEFERRABLE_LOADS),
                vehicle_data.get(CONF_PLANNING_SENSOR, "not configured"),
            )

            _LOGGER.debug(
                "Config flow step 3 (emhass): horizon=%s, max_loads=%s",
                user_input.get(CONF_PLANNING_HORIZON),
                user_input.get(CONF_MAX_DEFERRABLE_LOADS),
            )

            # Go to presence step
            return await self.async_step_presence(None)

        return self.async_show_form(
            step_id="emhass",
            data_schema=STEP_EMHASS_SCHEMA,
            description_placeholders={
                "description": "Configure EMHASS (optional)."
            },
        )

    async def async_step_presence(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso 4: Configuración de detección de presencia.

        Fields:
        - charging_sensor (entity selector, binary_sensor domain) - MANDATORY
        - home_sensor (entity selector, binary_sensor domain)
        - plugged_sensor (entity selector, binary_sensor domain)
        """
        # Show the presence form with entity selectors
        _LOGGER.debug("Config flow step 4 (presence): showing form")
        if user_input is None:
            return self.async_show_form(
                step_id="presence",
                data_schema=STEP_PRESENCE_SCHEMA,
                description_placeholders={
                    "description": "Configure presence detection."
                },
            )

        # If user clicks "Skip" or provides empty dict, go to notifications step
        if not user_input or user_input == {}:
            return await self.async_step_notifications(None)

        # Validate charging_sensor (mandatory)
        charging_sensor = user_input.get(CONF_CHARGING_SENSOR)
        if not charging_sensor:
            return self.async_show_form(
                step_id="presence",
                data_schema=STEP_PRESENCE_SCHEMA,
                errors={"base": "charging_sensor_required"},
                description_placeholders={
                    "description": "Configure presence detection."
                },
            )

        # Validate charging sensor exists
        if not self.hass.states.get(charging_sensor):
            return self.async_show_form(
                step_id="presence",
                data_schema=STEP_PRESENCE_SCHEMA,
                errors={"base": "charging_sensor_not_found"},
                description_placeholders={
                    "description": "Configure presence detection."
                },
            )

        # Validate home sensor exists (if provided)
        if CONF_HOME_SENSOR in user_input and user_input[CONF_HOME_SENSOR]:
            home_sensor = user_input[CONF_HOME_SENSOR]
            if not self.hass.states.get(home_sensor):
                return self.async_show_form(
                    step_id="presence",
                    data_schema=STEP_PRESENCE_SCHEMA,
                    errors={"base": "home_sensor_not_found"},
                    description_placeholders={
                        "description": "Configure presence detection."
                    },
                )

        # Validate plugged sensor exists (if provided)
        if CONF_PLUGGED_SENSOR in user_input and user_input[CONF_PLUGGED_SENSOR]:
            plugged_sensor = user_input[CONF_PLUGGED_SENSOR]
            if not self.hass.states.get(plugged_sensor):
                return self.async_show_form(
                    step_id="presence",
                    data_schema=STEP_PRESENCE_SCHEMA,
                    errors={"base": "plugged_sensor_not_found"},
                    description_placeholders={
                        "description": "Configure presence detection."
                    },
                )

        # Store the presence data and go to notifications step
        vehicle_data = self._get_vehicle_data()
        vehicle_data.update(user_input)
        _LOGGER.debug(
            "Config flow step 4 (presence): charging_sensor=%s, "
            "home_sensor=%s, plugged_sensor=%s",
            user_input.get(CONF_CHARGING_SENSOR),
            user_input.get(CONF_HOME_SENSOR, "not set"),
            user_input.get(CONF_PLUGGED_SENSOR, "not set"),
        )
        return await self.async_step_notifications(None)

    async def async_step_notifications(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso 5: Configuración de notificaciones (opcional).

        Fields:
        - notification_service (entity selector, notify domain)
        - notification_devices (multi-select, notify devices)
        """
        _LOGGER.debug("Config flow step 5 (notifications): showing form")
        if user_input is None:
            # Log available notify services for debugging
            notify_services = self.hass.services.async_services().get("notify", {})
            available_services = list(notify_services.keys())
            _LOGGER.debug(
                "Available notify services: %s",
                available_services,
            )
            _LOGGER.info(
                "Notification step: %d notify services available",
                len(available_services),
            )
            return self.async_show_form(
                step_id="notifications",
                data_schema=STEP_NOTIFICATIONS_SCHEMA,
                description_placeholders={
                    "description": "Configure notifications (optional)."
                },
            )

        # Store step 5 data in context (even if empty - user skipped)
        vehicle_data = self._get_vehicle_data()
        vehicle_data.update(user_input)

        # Validate notification service if provided
        if (
            CONF_NOTIFICATION_SERVICE in user_input
            and user_input[CONF_NOTIFICATION_SERVICE]
        ):
            notification_service = user_input[CONF_NOTIFICATION_SERVICE]
            # Extract domain and service from entity ID (e.g., "notify.mobile_app")
            if "." in notification_service:
                domain, service = notification_service.split(".", 1)
                # Check if service exists in Home Assistant
                if not self.hass.services.has_service(domain, service):
                    _LOGGER.warning(
                        "Notification service not found: %s",
                        notification_service,
                    )
                    return self.async_show_form(
                        step_id="notifications",
                        data_schema=STEP_NOTIFICATIONS_SCHEMA,
                        errors={
                            "notification_service": "notification_service_not_found"
                        },
                        description_placeholders={
                            "description": "Configure notifications (optional)."
                        },
                    )

        # Log notification configuration
        notify_service = user_input.get(CONF_NOTIFICATION_SERVICE)
        if notify_service:
            _LOGGER.info("Notification service configured: %s", notify_service)
        notify_devices = user_input.get(CONF_NOTIFICATION_DEVICES)
        if notify_devices:
            _LOGGER.info(
                "Notification devices configured: %s",
                notify_devices,
            )

        _LOGGER.debug(
            "Config flow step 5 (notifications): service=%s, devices=%s",
            user_input.get(CONF_NOTIFICATION_SERVICE, "not set"),
            user_input.get(CONF_NOTIFICATION_DEVICES, "not set"),
        )

        # Create entry after notifications step
        return await self._async_create_entry()

    async def _async_create_entry(self) -> FlowResult:
        """Crea la entrada de configuración."""
        vehicle_data = self._get_vehicle_data()
        vehicle_name = vehicle_data[CONF_VEHICLE_NAME]
        vehicle_id = vehicle_name.lower().replace(" ", "_")

        # Log all collected configuration data for diagnosis
        _LOGGER.debug(
            "Creating config entry for vehicle: %s (ID: %s)",
            vehicle_name,
            vehicle_id,
        )
        _LOGGER.debug(
            "Config flow final data keys: %s",
            list(vehicle_data.keys()),
        )

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
        _LOGGER.debug("Options flow step init: showing form")
        if user_input is not None:
            _LOGGER.debug(
                "Options flow step init: battery=%.1f, charging=%.1f, "
                "consumption=%.2f, safety=%d",
                user_input.get(CONF_BATTERY_CAPACITY, 0),
                user_input.get(CONF_CHARGING_POWER, 0),
                user_input.get(CONF_CONSUMPTION, 0),
                user_input.get(CONF_SAFETY_MARGIN, 0),
            )
            return self.async_create_entry(title="", data=user_input)

        # Get current values from config entry
        current_battery = self.config_entry.data.get(
            CONF_BATTERY_CAPACITY, 60.0
        )
        current_charging = self.config_entry.data.get(CONF_CHARGING_POWER, 11.0)
        current_consumption = self.config_entry.data.get(
            CONF_CONSUMPTION, DEFAULT_CONSUMPTION
        )
        current_safety = self.config_entry.data.get(
            CONF_SAFETY_MARGIN, DEFAULT_SAFETY_MARGIN
        )

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
                }
            ),
        )


# Alias for backward compatibility with tests
EVTripPlannerConfigFlow = EVTripPlannerFlowHandler
