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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from . import panel as panel_module
from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CHARGING_SENSOR,
    CONF_CONSUMPTION,
    CONF_HOME_SENSOR,
    CONF_INDEX_COOLDOWN_HOURS,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFICATION_SERVICE,
    CONF_PLANNING_HORIZON,
    CONF_PLANNING_SENSOR,
    CONF_PLUGGED_SENSOR,
    CONF_SAFETY_MARGIN,
    CONF_SOC_SENSOR,
    CONF_SOH_SENSOR,
    CONF_T_BASE,
    CONF_VEHICLE_NAME,
    CONFIG_VERSION,
    DEFAULT_CONSUMPTION,
    DEFAULT_INDEX_COOLDOWN_HOURS,
    DEFAULT_MAX_DEFERRABLE_LOADS,
    DEFAULT_PLANNING_HORIZON,
    DEFAULT_SAFETY_MARGIN,
    DEFAULT_SOH_SENSOR,
    DEFAULT_T_BASE,
    DOMAIN,
    MAX_T_BASE,
    MIN_T_BASE,
)
from .dashboard import import_dashboard, is_lovelace_available

_LOGGER = logging.getLogger(__name__)

# Step 1: Vehicle basic info
STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_VEHICLE_NAME): vol.All(
            str,
            vol.Length(min=1, max=100, msg="vehicle_name_required"),
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
        vol.Required(CONF_SAFETY_MARGIN, default=DEFAULT_SAFETY_MARGIN): vol.Coerce(
            int
        ),
        vol.Optional(CONF_SOC_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="sensor",
                multiple=False,
            )
        ),
        # Battery health: T_base slider (user-configurable idle time window)
        vol.Required(
            CONF_T_BASE,
            default=DEFAULT_T_BASE,
            description={
                "suggested_value": DEFAULT_T_BASE,
                "placeholder": f"{DEFAULT_T_BASE}",
                "description": (
                    "Ventana de tiempo base (horas). Cuanto mayor sea, más conservadora "
                    "será la limitación dinámica de SOC. Rango: 6-48h."
                ),
            },
        ): vol.All(vol.Coerce(float), vol.Range(min=MIN_T_BASE, max=MAX_T_BASE)),
        # SOH sensor for real battery capacity
        vol.Optional(CONF_SOH_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="sensor",
                multiple=False,
            )
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
        vol.Required(
            CONF_INDEX_COOLDOWN_HOURS,
            default=DEFAULT_INDEX_COOLDOWN_HOURS,
            description={
                "suggested_value": "24",
                "placeholder": "24",
                # Note: Max 168 hours = 1 week
                "description": "Horas de cooldown antes de reutilizar un índice liberado (1-168).",
            },
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=168)),
        vol.Optional(CONF_PLANNING_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="sensor",
                multiple=False,
            )
        ),
    }
)

# Step 4: Presence configuration
# NOTE: CONF_CHARGING_SENSOR is Optional - validation is handled in async_step_presence
# because we auto-select if not provided. Using Optional allows form submission without
# triggering voluptuous validation failure before async_step_presence can auto-select.
STEP_PRESENCE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CHARGING_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["binary_sensor", "input_boolean"],
                multiple=False,
            )
        ),
        vol.Optional(CONF_HOME_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["binary_sensor", "input_boolean"],
                multiple=False,
            )
        ),
        vol.Optional(CONF_PLUGGED_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["binary_sensor", "input_boolean"],
                multiple=False,
            )
        ),
    }
)

# Step 5: Notifications configuration
# Using EntitySelector with domain=["notify", "assist_satellite"] to show all notify
# services/entities AND assist_satellite devices (e.g., Home Assistant Voice Satellite)
# This includes Nabu Casa devices (notify.alexa_media_*) and mobile app notifications.
# The selector queries the entity registry for entities in the notify and assist_satellite
# domains. Note: EntitySelector works with notify services in HA because they are
# registered as entities in the entity registry (notify.<service_name>). assist_satellite
# devices are also registered in the entity registry and need explicit inclusion.
STEP_NOTIFICATIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NOTIFICATION_SERVICE): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["notify", "assist_satellite"],
                multiple=False,
            )
        ),
        vol.Optional(CONF_NOTIFICATION_DEVICES): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["notify", "assist_satellite"],
                multiple=True,
            )
        ),
    }
)

# TODO: Make EMHASS config path configurable via HA config or environment variable
# Hardcoded /home/malka/emhass path is not portable


def _read_emhass_config(
    config_path: str | None = None,
) -> Optional[Dict[str, Any]]:
    """Lee la configuración de EMHASS desde el archivo de configuración.

    Args:
        config_path: Ruta al archivo de configuración de EMHASS.

    Returns:
        Diccionario con la configuración o None si no se puede leer.
    """
    if config_path is None or not os.path.exists(config_path):
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
    if (
        len(end_timesteps) == 0
    ):  # pragma: no cover — structurally unreachable; empty list is falsy, caught above
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

    VERSION = CONFIG_VERSION
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    @staticmethod
    async def async_migrate_entry(hass: Any, entry: config_entries.ConfigEntry) -> bool:
        """Migrar entrada de configuración de versión anterior.

        v2 -> v3: Add battery health config (t_base, soh_sensor).
        """
        _LOGGER.info(
            "Migrating config entry from version %s to %s",
            entry.version,
            CONFIG_VERSION,
        )

        if entry.version == 2:
            # Add new v3 fields with safe defaults
            new_data = dict(entry.data)
            new_data[CONF_T_BASE] = DEFAULT_T_BASE
            new_data[CONF_SOH_SENSOR] = DEFAULT_SOH_SENSOR
            await hass.config_entries.async_update_entry(
                entry, data=new_data, version=CONFIG_VERSION
            )
            _LOGGER.info("Config entry migrated to version %d", CONFIG_VERSION)
            return True

        _LOGGER.warning(
            "Unknown config entry version %s, cannot migrate", entry.version
        )
        return False

    def __init__(self) -> None:
        """Inicializa el flujo de configuración."""
        self._data: Dict[str, Any] = {}

    def _get_vehicle_data(self) -> Dict[str, Any]:
        """Get or initialize vehicle data from context."""
        if "vehicle_data" not in self.context:
            self.context["vehicle_data"] = {}  # type: ignore[typeddict-unknown-key] # HA stub: ConfigFlowContext missing vehicle_data in stubs
        return self.context["vehicle_data"]  # type: ignore[typeddict-item] # HA stub: TypedDict item access not in stubs

    async def async_step_user(  # type: ignore[override] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso 1: Configuración básica del vehículo."""
        _LOGGER.debug("Config flow step 1 (user): showing form")
        if user_input is not None:
            # Validate vehicle name
            vehicle_name = user_input.get(CONF_VEHICLE_NAME, "").strip()
            if not vehicle_name:
                return self.async_show_form(
                    step_id="user",
                    data_schema=STEP_USER_SCHEMA,
                    errors={"base": "vehicle_name_required"},
                    description_placeholders={
                        "description": "Configure your electric vehicle for trip planning"
                    },
                )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

            # Validate vehicle name length
            if len(vehicle_name) > 100:
                return self.async_show_form(
                    step_id="user",
                    data_schema=STEP_USER_SCHEMA,
                    errors={"base": "vehicle_name_too_long"},
                    description_placeholders={
                        "description": "Vehicle name must be less than 100 characters"
                    },
                )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

            # Store step 1 data in context
            vehicle_data = self._get_vehicle_data()
            vehicle_data[CONF_VEHICLE_NAME] = vehicle_name
            _LOGGER.debug(
                "Config flow step 1 (user): vehicle_name=%s",
                vehicle_name,
            )
            return await self.async_step_sensors()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            description_placeholders={
                "description": "Configure your electric vehicle for trip planning"
            },
        )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

    async def async_step_sensors(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso 2: Configuración de sensores del vehículo.

        Validates:
        - Battery capacity: 10-200 kWh
        - Consumption: 0.05-0.5 kWh/km
        - Safety margin: 0-50%
        """
        _LOGGER.debug("Config flow step 2 (sensors): showing form")
        if user_input is not None:
            # Validate battery capacity (reasonable range: 10-200 kWh)
            battery_capacity = user_input.get(CONF_BATTERY_CAPACITY)
            if battery_capacity is not None:
                if battery_capacity < 10 or battery_capacity > 200:
                    return self.async_show_form(
                        step_id="sensors",
                        data_schema=STEP_SENSORS_SCHEMA,
                        errors={"base": "invalid_battery_capacity"},
                        description_placeholders={
                            "description": "Battery capacity must be between 10 and 200 kWh"
                        },
                    )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

            # Validate consumption (reasonable range: 0.05-0.5 kWh/km)
            consumption = user_input.get(CONF_CONSUMPTION)
            if consumption is not None:
                if consumption < 0.05 or consumption > 0.5:
                    return self.async_show_form(
                        step_id="sensors",
                        data_schema=STEP_SENSORS_SCHEMA,
                        errors={"base": "invalid_consumption"},
                        description_placeholders={
                            "description": "Consumption must be between 0.05 and 0.5 kWh/km"
                        },
                    )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

            # Validate safety margin (reasonable range: 0-50%)
            safety_margin = user_input.get(CONF_SAFETY_MARGIN)
            if safety_margin is not None:
                if safety_margin < 0 or safety_margin > 50:
                    return self.async_show_form(
                        step_id="sensors",
                        data_schema=STEP_SENSORS_SCHEMA,
                        errors={"base": "invalid_safety_margin"},
                        description_placeholders={
                            "description": "Safety margin must be between 0 and 50%"
                        },
                    )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

            # Validate t_base (reasonable range: 6-48 hours)
            t_base = user_input.get(CONF_T_BASE)
            if t_base is not None:
                if t_base < MIN_T_BASE or t_base > MAX_T_BASE:
                    return self.async_show_form(
                        step_id="sensors",
                        data_schema=STEP_SENSORS_SCHEMA,
                        errors={"base": "invalid_t_base"},
                        description_placeholders={
                            "description": f"T_base must be between {MIN_T_BASE} and {MAX_T_BASE} hours"
                        },
                    )  # type: ignore[return-value]

            # Store step 2 data in context
            vehicle_data = self._get_vehicle_data()
            vehicle_data.update(user_input)
            _LOGGER.debug(
                "Config flow step 2 (sensors): battery_capacity=%.1f, "
                "charging_power=%.1f, consumption=%.2f, safety_margin=%d, t_base=%.1f",
                user_input.get(CONF_BATTERY_CAPACITY, 0),
                user_input.get(CONF_CHARGING_POWER, 0),
                user_input.get(CONF_CONSUMPTION, 0),
                user_input.get(CONF_SAFETY_MARGIN, 0),
                user_input.get(CONF_T_BASE, 0),
            )
            return await self.async_step_emhass()

        return self.async_show_form(
            step_id="sensors",
            data_schema=STEP_SENSORS_SCHEMA,
            description_placeholders={
                "description": "Select the sensors for battery monitoring"
            },
        )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

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
        emhass_config_path = os.environ.get(
            "EMHASS_CONFIG_PATH",
            "/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/test-ha/config",
        )
        emhass_config = _read_emhass_config(emhass_config_path)
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
                    )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

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
                    )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

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
            description_placeholders={"description": "Configure EMHASS (optional)."},
        )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

    async def async_step_presence(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso 4: Configuración de detección de presencia.

        Fields:
        - charging_sensor (entity selector, binary_sensor domain) - MANDATORY
        - home_sensor (entity selector, binary_sensor domain)
        - plugged_sensor (entity selector, binary_sensor domain)
        """
        _LOGGER.info(
            "Config flow step 4 (presence): called with user_input=%s", user_input
        )

        # If user_input is None, show the form (first visit or "Skip" via back button)
        if user_input is None:
            _LOGGER.info(
                "Config flow step 4 (presence): showing form (user_input is None)"
            )
            return self.async_show_form(
                step_id="presence",
                data_schema=STEP_PRESENCE_SCHEMA,
                description_placeholders={
                    "description": "Configure presence detection."
                },
            )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

        # User submitted the presence form (user_input is dict, possibly empty)
        _LOGGER.info(
            "Config flow step 4 (presence): processing submission, user_input=%s",
            user_input,
        )
        charging_sensor = user_input.get(CONF_CHARGING_SENSOR)
        _LOGGER.info(
            "Config flow step 4 (presence): charging_sensor from form=%s",
            charging_sensor,
        )

        # Auto-select first available entity if not provided
        if not charging_sensor:
            _LOGGER.warning(
                "Config flow step 4 (presence): no charging_sensor selected, auto-selecting first available"
            )
            try:
                # er.async_get returns EntityRegistry directly (not a coroutine)
                entity_registry = er.async_get(self.hass)
                entities = [
                    entity_id
                    for entity_id in entity_registry.entities.keys()
                    if entity_id.startswith("binary_sensor.")
                    or entity_id.startswith("input_boolean.")
                ]
                _LOGGER.info(
                    "Config flow step 4 (presence): found %d entities in registry: %s",
                    len(entities),
                    entities,
                )
                if entities:
                    charging_sensor = entities[0]
                    user_input = {**user_input, CONF_CHARGING_SENSOR: charging_sensor}
                    _LOGGER.info(
                        "Config flow step 4 (presence): auto-selected charging_sensor=%s",
                        charging_sensor,
                    )
                else:
                    _LOGGER.error(
                        "Config flow step 4 (presence): no entities available for auto-selection"
                    )
            except Exception as e:
                _LOGGER.error(
                    "Config flow step 4 (presence): error getting entity registry: %s",
                    str(e),
                )

        # If still no charging_sensor after auto-selection, show error
        if not charging_sensor:
            _LOGGER.warning(
                "Config flow step 4 (presence): charging_sensor still empty after auto-selection, showing error"
            )
            return self.async_show_form(
                step_id="presence",
                data_schema=STEP_PRESENCE_SCHEMA,
                errors={"base": "charging_sensor_required"},
                description_placeholders={
                    "description": "Please select a charging sensor or restart Home Assistant to register entities."
                },
            )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

        _LOGGER.info(
            "Config flow step 4 (presence): proceeding to notifications with charging_sensor=%s",
            charging_sensor,
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
            )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

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
                )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

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
                )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

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
            # Use entity registry to get all notify entities
            # This includes Nabu Casa devices (notify.alexa_media_*) and mobile app notifications
            # EntitySelector works with notify entities because they are registered
            # as entities in the entity registry (notify.<entity_name>)
            available_services = []
            try:
                entity_registry_obj = er.async_get(self.hass)
                notify_entities = [
                    entity.entity_id
                    for entity in entity_registry_obj.entities.values()
                    if entity.domain == "notify"
                ]
                available_services = sorted(notify_entities)

                _LOGGER.debug(
                    "Available notify entities: %s",
                    available_services,
                )
                _LOGGER.info(
                    "Notification step: %d notify entities available",
                    len(available_services),
                )
            except Exception as err:
                _LOGGER.warning(
                    "Failed to get notify entities from registry: %s, using services API",
                    err,
                )
                # Fallback to services if registry fails
                notify_services = self.hass.services.async_services().get("notify", {})
                available_services = sorted(notify_services.keys())
                _LOGGER.info(
                    "Using services API: %d notify services available",
                    len(available_services),
                )

            return self.async_show_form(
                step_id="notifications",
                data_schema=STEP_NOTIFICATIONS_SCHEMA,
                description_placeholders={
                    "description": "Configure notifications (optional)."
                },
            )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

        # Store step 5 data in context (even if empty - user skipped)
        vehicle_data = self._get_vehicle_data()
        vehicle_data.update(user_input)

        # Validate notification service if provided
        # Note: We skip validation for entity-based notifications (notify.*) because
        # the EntitySelector ensures only valid entities are selectable
        if (
            CONF_NOTIFICATION_SERVICE in user_input
            and user_input[CONF_NOTIFICATION_SERVICE]
        ):
            notification_service = user_input[CONF_NOTIFICATION_SERVICE]
            # Extract domain and service from entity ID (e.g., "notify.mobile_app")
            if "." in notification_service:
                domain, service = notification_service.split(".", 1)
                # For notify domain entities, validation is handled by EntitySelector
                # so we don't need to check with has_service
                # Only validate non-notify services (legacy support)
                if domain != "notify":
                    if not self.hass.services.has_service(domain, service):
                        _LOGGER.warning(
                            "Notification service not found: %s",
                            notification_service,
                        )
                        # Don't fail - just log a warning and continue
                        # The EntitySelector ensures valid entities are selected

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
        # HA stub: Context TypedDict may have missing keys, .get() safe for object
        vehicle_name_for_log = self.context.get("vehicle_data", {}).get(
            "vehicle_name", "unknown"
        )  # type: ignore[attr-defined,unused-ignore]
        _LOGGER.info(
            "Starting _async_create_entry for vehicle: %s",
            vehicle_name_for_log,
        )

        vehicle_data = self._get_vehicle_data()
        vehicle_name = vehicle_data[CONF_VEHICLE_NAME]
        vehicle_id = vehicle_name.lower().replace(" ", "_")

        # Log all collected configuration data for diagnosis
        _LOGGER.info(
            "Creating config entry for vehicle: %s (ID: %s)",
            vehicle_name,
            vehicle_id,
        )
        _LOGGER.info(
            "Config flow final data keys: %s",
            list(vehicle_data.keys()),
        )

        # Create the config entry
        result = self.async_create_entry(
            title=vehicle_name,
            data=vehicle_data,
        )
        _LOGGER.info("Config entry created successfully for %s", vehicle_name)

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
            _LOGGER.info("Dashboard imported successfully for %s", vehicle_name)
        except Exception as err:
            # Log but don't fail the flow - dashboard import is optional
            _LOGGER.warning(
                "Could not auto-import dashboard for %s: %s",
                vehicle_name,
                err,
            )

        # Register native panel for the vehicle
        # This creates a sidebar entry in HA without requiring Lovelace
        # Use vehicle_id (from vehicle name) for cleaner URLs like /ev-trip-planner-chispitas
        try:
            await panel_module.async_register_panel(
                self.hass,
                vehicle_id=vehicle_id,  # Use friendly ID from vehicle name
                vehicle_name=vehicle_name,
            )
            _LOGGER.info("Panel registered successfully for %s", vehicle_name)
        except Exception as err:
            # Log but don't fail the flow - panel registration is optional
            _LOGGER.warning(
                "Could not register native panel for %s: %s",
                vehicle_name,
                err,
            )

        _LOGGER.info("Returning FlowResult for %s", vehicle_name)
        return result  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Devuelve el flujo de opciones para la entrada de configuración."""
        return EVTripPlannerOptionsFlowHandler(config_entry)


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

            return self.async_create_entry(title="", data=update_data)  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

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
        )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]


# Alias for backward compatibility with tests
EVTripPlannerConfigFlow = EVTripPlannerFlowHandler
