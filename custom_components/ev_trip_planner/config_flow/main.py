"""Config flow — main module (EVTripPlannerFlowHandler).

This module holds all shared definitions (imports, schemas, private helpers)
and the primary ConfigFlow class.  Imported by options.py via normal
``from .main import …`` to avoid circular imports.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from . import _entities
from . import _emhass as _emhass_helpers

from .. import panel as panel_module
from ..const import (
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

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Form schemas
# ---------------------------------------------------------------------------

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
        vol.Optional(
            CONF_T_BASE,
            default=DEFAULT_T_BASE,
            description={
                "suggested_value": DEFAULT_T_BASE,
                "placeholder": f"{DEFAULT_T_BASE}",
                "description": (
                    "Tiempo que puedes mantener la batería a alto SOC sin dañarla. "
                    "Valores más bajos = protección más agresiva de la batería. "
                    "Rango: 6-48h. Ejemplo: 24 (balance entre protección y flexibilidad)"
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

# ---------------------------------------------------------------------------
# EVTripPlannerFlowHandler
# ---------------------------------------------------------------------------

# qg-accepted: BMAD consensus 2026-05-12 — 8 public methods is required for HA
#   ConfigFlow (async_step_user, async_step_sensors, async_step_emhass,
#   async_step_presence, async_step_notifications, async_migrate_entry,
#   async_get_options_flow, __init__). Entity scanning extracted to _entities.py.


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

    # qg-accepted: arity=6 is the numeric field validation API
    def _validate_field(
        self,
        user_input: Dict[str, Any],
        key: str,
        min_val: float,
        max_val: float,
        error_key: str,
        description: str,
    ) -> FlowResult | None:
        """Validate a single numeric sensor field and return error form or None."""
        value = user_input.get(key)
        if value is not None and (value < min_val or value > max_val):
            return self.async_show_form(
                step_id="sensors",
                data_schema=STEP_SENSORS_SCHEMA,
                errors={"base": error_key},
                description_placeholders={"description": description},
            )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]
        return None

    def _validate_sensor_exists(
        self, entity_id: str, error_key: str
    ) -> FlowResult | None:
        """Validate that a sensor entity exists in Home Assistant."""
        if not self.hass.states.get(entity_id):
            return self.async_show_form(
                step_id="presence",
                data_schema=STEP_PRESENCE_SCHEMA,
                errors={"base": error_key},
                description_placeholders={
                    "description": "Configure presence detection."
                },
            )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]
        return None

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
        if user_input is not None:
            # Validate each sensor field
            return await self._validate_sensors(user_input)

        return self.async_show_form(
            step_id="sensors",
            data_schema=STEP_SENSORS_SCHEMA,
            description_placeholders={
                "description": "Select the sensors for battery monitoring"
            },
        )  # type: ignore[return-value] # HA stub: ConfigFlowResult vs FlowResult[FlowContext, str]

    async def _validate_sensors(self, user_input: Dict[str, Any]) -> FlowResult:
        """Validate sensor fields and return appropriate response."""
        # Validate battery capacity (reasonable range: 10-200 kWh)
        result = self._validate_field(
            user_input,
            CONF_BATTERY_CAPACITY,
            10,
            200,
            "invalid_battery_capacity",
            "Battery capacity must be between 10 and 200 kWh",
        )
        if result:
            return result

        # Validate consumption (reasonable range: 0.05-0.5 kWh/km)
        result = self._validate_field(
            user_input,
            CONF_CONSUMPTION,
            0.05,
            0.5,
            "invalid_consumption",
            "Consumption must be between 0.05 and 0.5 kWh/km",
        )
        if result:
            return result

        # Validate safety margin (reasonable range: 0-50%)
        result = self._validate_field(
            user_input,
            CONF_SAFETY_MARGIN,
            0,
            50,
            "invalid_safety_margin",
            "Safety margin must be between 0 and 50%",
        )
        if result:
            return result

        # All validations passed — store step 2 data and proceed
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

    async def async_step_emhass(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso 3: Configuración de integración EMHASS (opcional)."""
        _LOGGER.debug("Config flow step 3 (emhass): showing form")

        if user_input is not None:
            emhass_config_path = os.environ.get(
                "EMHASS_CONFIG_PATH",
                "/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/test-ha/config",
            )
            # Validate before accessing vehicle_data (avoids context init on error paths)
            vehicle_data = self._get_vehicle_data()
            ctx = _emhass_helpers._EmhassCtx(
                user_input,
                self.hass,
                vehicle_data,
                "Configure EMHASS (optional).",
            )
            error = _emhass_helpers.validate_emhass_input(ctx, emhass_config_path)
            if error:
                return self.async_show_form(
                    step_id="emhass",
                    data_schema=STEP_EMHASS_SCHEMA,
                    errors={"base": error},
                    description_placeholders={
                        "description": "Configure EMHASS (optional)."
                    },
                )  # type: ignore[return-value]
            return await self.async_step_presence(None)

        return self.async_show_form(
            step_id="emhass",
            data_schema=STEP_EMHASS_SCHEMA,
            description_placeholders={"description": "Configure EMHASS (optional)."},
        )  # type: ignore[return-value]

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
            user_input = _entities.auto_select_sensor(
                self.hass,
                ["binary_sensor", "input_boolean"],
                user_input,
                CONF_CHARGING_SENSOR,
            )
            charging_sensor = user_input.get(CONF_CHARGING_SENSOR)
            if charging_sensor:
                _LOGGER.info(
                    "Config flow step 4 (presence): auto-selected charging_sensor=%s",
                    charging_sensor,
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
        result = self._validate_sensor_exists(
            charging_sensor, "charging_sensor_not_found"
        )
        if result:
            return result

        # Validate optional sensors exist (if provided)
        for key, error_key in [
            (CONF_HOME_SENSOR, "home_sensor_not_found"),
            (CONF_PLUGGED_SENSOR, "plugged_sensor_not_found"),
        ]:
            entity = user_input.get(key)
            if entity:
                result = self._validate_sensor_exists(entity, error_key)
                if result:
                    return result

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
            _entities.scan_notify_entities(
                self.hass
            )  # Available entities not yet wired to form

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
        # Lazy import to avoid circular dependency with options.py
        from .options import EVTripPlannerOptionsFlowHandler

        return EVTripPlannerOptionsFlowHandler(config_entry)
