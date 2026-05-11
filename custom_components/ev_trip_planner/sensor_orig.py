"""Sensores para el componente EV Trip Planner.

Implementa entidades de sensores para mostrar información de viajes y carga.
Cumple con las reglas de HA 2026 para tipado estricto y runtime_data.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceInfo

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_registry import (
    EntityRegistry,
    async_entries_for_config_entry,
    async_get as er_async_get,
)
from homeassistant.helpers.entity import EntityCategory  # type: ignore[attr-defined] # HA stub: EntityCategory not explicitly exported
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    TRIP_TYPE_PUNCTUAL,
)
from .coordinator import TripPlannerCoordinator
from .definitions import TRIP_SENSORS, TripSensorEntityDescription

_LOGGER = logging.getLogger(__name__)

# 9 documented attributes for TripEmhassSensor
# Prevents data leak of internal cache keys (activo, *_array, p_deferrable_matrix, etc.)
TRIP_EMHASS_ATTR_KEYS = {
    "def_total_hours",
    "P_deferrable_nom",
    "def_start_timestep",
    "def_end_timestep",
    "power_profile_watts",
    "trip_id",
    "emhass_index",
    "kwh_needed",
    "deadline",
}


def _format_window_time(value: Any) -> str | None:
    """Format window time to HH:MM from datetime or ISO string.

    Args:
        value: Either a datetime object or an ISO format string

    Returns:
        Time formatted as HH:MM, or None if formatting fails
    """
    if value is None:
        return None
    try:
        if isinstance(value, datetime):
            dt_value = value
        elif isinstance(value, str):
            dt_value = datetime.fromisoformat(value)
        else:
            return None
        return dt_value.strftime("%H:%M")
    except (ValueError, TypeError, AttributeError):
        return None


class TripPlannerSensor(
    CoordinatorEntity[TripPlannerCoordinator], RestoreSensor, SensorEntity
):
    """Sensor base for EV Trip Planner using CoordinatorEntity pattern.

    Reads from coordinator.data via entity_description.value_fn().
    Sets _attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}".
    Inherits RestoreSensor for state restoration on HA restart.
    """

    def __init__(
        self,
        coordinator: TripPlannerCoordinator,
        vehicle_id: str,
        entity_description: TripSensorEntityDescription,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: TripPlannerCoordinator instance.
            vehicle_id: Vehicle identifier.
            entity_description: Description with value_fn and attrs_fn.
        """
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._vehicle_id = vehicle_id
        self.entity_description = entity_description
        self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_{entity_description.key}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_has_entity_name = True
        self._attr_name = f"EV Trip Planner {entity_description.key}"
        # Store cached attributes for synchronous access
        self._cached_attrs: Dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass.

        Restores state if restore=True and coordinator.data is None.
        """
        await super().async_added_to_hass()
        restore_val = getattr(self.entity_description, "restore", False)
        if restore_val and self.coordinator.data is None:
            # Restore state from previous run
            last_state = await self.async_get_last_state()
            if last_state is not None:
                self._attr_native_value = last_state.state

    @property
    def native_value(self) -> Any:
        """Return sensor value via entity_description.value_fn."""
        if self.coordinator.data is None:
            return None
        value_fn = getattr(self.entity_description, "value_fn", lambda _: None)
        return value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return attributes from coordinator.data via entity_description.attrs_fn."""
        if self.coordinator.data is None:
            return {}
        attrs_fn: Callable[[Dict[str, Any]], Dict[str, Any]] = getattr(
            self.entity_description, "attrs_fn", lambda _: {}
        )
        return attrs_fn(self.coordinator.data)

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device info for the vehicle."""
        return dr.DeviceInfo(
            identifiers={(DOMAIN, self._vehicle_id)},
            name=f"EV Trip Planner {self._vehicle_id}",
            manufacturer="Home Assistant",
            model="EV Trip Planner",
            sw_version="2026.3.0",
        )


class EmhassDeferrableLoadSensor(
    CoordinatorEntity[TripPlannerCoordinator], SensorEntity
):
    """Sensor para el perfil de carga diferible de EMHASS.

    Este sensor proporciona los datos necesarios para la integración con EMHASS:
    - power_profile_watts: Array de potencia en watts por hora
    - deferrables_schedule: Calendario de cargas diferibles

    PHASE 3: Ahora hereda de CoordinatorEntity y lee desde coordinator.data.

    Platform: template
    Entity: sensor.emhass_perfil_diferible_{entry_id}
    """

    def __init__(
        self,
        coordinator: TripPlannerCoordinator,
        entry_id: str,
    ) -> None:
        """Inicializa el sensor de carga diferible.

        Args:
            coordinator: TripPlannerCoordinator instance.
            entry_id: Config entry ID.
        """
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._entry_id = entry_id
        self._attr_unique_id = f"emhass_perfil_diferible_{entry_id}"
        vehicle_id = getattr(coordinator, "vehicle_id", entry_id)
        self._attr_name = f"EMHASS Perfil Diferible {vehicle_id}"
        self._attr_has_entity_name = True
        # Force HA to record state updates even when values are identical.
        # Coordinator refreshes are only triggered by meaningful events
        # (SOC change, trip CRUD, config change) so every refresh matters.
        self._attr_force_update = False

    @property
    def native_value(self) -> str:
        """Return sensor value from coordinator.data."""
        if self.coordinator.data is None:
            return "unknown"
        return self.coordinator.data.get("emhass_status", "unknown")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes from coordinator.data.

        Includes aggregated deferrable load parameters from all active trips.
        Implements 6 new attrs: p_deferrable_matrix, number_of_deferrable_loads,
        def_total_hours_array, p_deferrable_nom_array, def_start_timestep_array,
        def_end_timestep_array.

        Reads from per_trip_emhass_params with keys:
        - p_deferrable_matrix: list of lists (power_profile_watts for each deferrable load)
        - def_total_hours_array: list of hours per load
        - p_deferrable_nom_array: list of nominal power per load
        - def_start_timestep_array: list of start timesteps per load
        - def_end_timestep_array: list of end timesteps per load
        """
        if self.coordinator.data is None:
            _LOGGER.debug(
                "E2E-DEBUG EMHASS-SENSOR-CACHE-HUNT: extra_state_attributes called - coordinator.data is None! vehicle_id=%s",
                getattr(self.coordinator, "vehicle_id", "unknown"),
            )
            return {}

        vehicle_id = getattr(self.coordinator, "vehicle_id", self._entry_id)

        # E2E-DEBUG-CRITICAL: Log entire coordinator.data structure
        _LOGGER.debug(
            "E2E-DEBUG EMHASS-SENSOR-CACHE-HUNT: extra_state_attributes START - vehicle_id=%s",
            vehicle_id,
        )
        _LOGGER.debug(
            "E2E-DEBUG EMHASS-SENSOR-CACHE-HUNT: coordinator.data keys=%s",
            list(self.coordinator.data.keys()),
        )
        _LOGGER.debug(
            "E2E-DEBUG EMHASS-SENSOR-CACHE-HUNT: per_trip_emhass_params raw=%s",
            self.coordinator.data.get("per_trip_emhass_params"),
        )
        _LOGGER.debug(
            "E2E-DEBUG EMHASS-SENSOR-CACHE-HUNT: emhass_power_profile length=%d, non_zero=%d",
            len(self.coordinator.data.get("emhass_power_profile") or []),
            sum(
                1
                for x in (self.coordinator.data.get("emhass_power_profile") or [])
                if x > 0
            ),
        )

        attrs: Dict[str, Any] = {
            "power_profile_watts": self.coordinator.data.get("emhass_power_profile"),
            "deferrables_schedule": self.coordinator.data.get(
                "emhass_deferrables_schedule"
            ),
            "emhass_status": self.coordinator.data.get("emhass_status"),
            "vehicle_id": vehicle_id,
        }

        # Extract aggregated params from per_trip_emhass_params
        per_trip_params = self.coordinator.data.get("per_trip_emhass_params", {})

        # P1.1: Initialize number_of_deferrable_loads BEFORE per_trip_params block
        # This ensures the attribute is always set, even when there are no trips
        number_of_deferrable_loads = 0

        # DEBUG: Log per_trip_params for debugging
        _LOGGER.debug(
            "E2E-DEBUG EMHASS-SENSOR-CACHE-HUNT: per_trip_params count=%d, entries=%s",
            len(per_trip_params),
            list(per_trip_params.keys())[:10] if per_trip_params else [],
        )

        # CRITICAL: Log individual trip params structure
        for trip_id, params in per_trip_params.items():
            _LOGGER.debug(
                "E2E-DEBUG EMHASS-TRIP-PARAMS: trip_id=%s, activo=%s, keys=%s, def_total_hours_array=%s",
                trip_id,
                params.get("activo"),
                list(params.keys()),
                params.get("def_total_hours_array", "NOT_FOUND_KEY"),
            )

        if per_trip_params:
            # Helper: filter active trips and sort by deadline (def_start_timestep)
            active_trips_sorted: List[Dict[str, Any]] = []
            for trip_id, params in per_trip_params.items():
                if params.get("activo", False):
                    active_trips_sorted.append(params)
            # CRITICAL FIX: Sort by def_start_timestep (chronological deadline order)
            # Primary: def_start_timestep (chronological)
            # Secondary: emhass_index (deterministic tie-breaker)
            # This ensures arrays are in chronological order, with deterministic ordering when deadlines are equal
            active_trips_sorted.sort(
                key=lambda x: (x.get("def_start_timestep", 0), x.get("emhass_index", 0))
            )

            # Aggregate all 6 array/matrix attrs from sorted active trips
            matrix: List[List[float]] = []
            number_of_deferrable_loads = 0
            def_total_hours_array: List[float] = []
            p_deferrable_nom_array: List[float] = []
            def_start_timestep_array: List[int] = []
            def_end_timestep_array: List[int] = []

            for params in active_trips_sorted:
                # p_deferrable_matrix: list of lists (power profile per deferrable load)
                p_matrix = params.get("p_deferrable_matrix")
                if p_matrix:
                    matrix.extend(p_matrix)
                    number_of_deferrable_loads += len(p_matrix)
                elif "p_deferrable_matrix" not in params:
                    # P1.1: Count trip as 1 deferrable load if it has no p_deferrable_matrix
                    # This handles the case where trips have other EMHASS params but no power profile
                    number_of_deferrable_loads += 1

                # Array attrs: extend with trip's values
                # Note: keys use _array suffix as per task specification
                if "def_total_hours_array" in params:
                    def_total_hours_array.extend(params["def_total_hours_array"])
                if "p_deferrable_nom_array" in params:
                    p_deferrable_nom_array.extend(params["p_deferrable_nom_array"])
                if "def_start_timestep_array" in params:
                    def_start_timestep_array.extend(params["def_start_timestep_array"])
                if "def_end_timestep_array" in params:
                    def_end_timestep_array.extend(params["def_end_timestep_array"])

            # Add aggregated attrs if we have data
            if matrix:
                attrs["p_deferrable_matrix"] = matrix
            if def_total_hours_array:
                attrs["def_total_hours_array"] = def_total_hours_array
            if p_deferrable_nom_array:
                attrs["p_deferrable_nom_array"] = p_deferrable_nom_array
            if def_start_timestep_array:
                attrs["def_start_timestep_array"] = def_start_timestep_array
            if def_end_timestep_array:
                attrs["def_end_timestep_array"] = def_end_timestep_array

        # P1.1: Set number_of_deferrable_loads AFTER per_trip_params block
        # This ensures the attribute is always set, even when there are no trips
        attrs["number_of_deferrable_loads"] = number_of_deferrable_loads

        return attrs

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device info.

        Returns device info using vehicle_id from coordinator.
        """
        vehicle_id = getattr(self.coordinator, "vehicle_id", self._entry_id)

        return dr.DeviceInfo(
            identifiers={(DOMAIN, vehicle_id)},
            name=f"EV Trip Planner {vehicle_id}",
            manufacturer="Home Assistant",
            model="EV Trip Planner",
            sw_version="2026.3.0",
        )

    async def async_will_remove_from_hass(
        self,
    ) -> None:  # pragma: no cover  # HA entity lifecycle - entity removal triggers cleanup; tested via HA integration tests
        """Clean up when entity is removed from Home Assistant."""
        trip_manager = getattr(self.coordinator, "trip_manager", None)
        if (
            trip_manager
            and hasattr(trip_manager, "_emhass_adapter")
            and trip_manager._emhass_adapter is not None
        ):
            await trip_manager._emhass_adapter.async_cleanup_vehicle_indices()


class TripSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity):
    """Sensor for a specific trip using CoordinatorEntity pattern.

    Reads trip data from coordinator.data["recurring_trips"][trip_id] or
    coordinator.data["punctual_trips"][trip_id].

    Entity: sensor.ev_trip_planner_{vehicle_id}_trip_{trip_id}
    """

    def __init__(
        self,
        coordinator: TripPlannerCoordinator,
        vehicle_id: str,
        trip_id: str,
    ) -> None:
        """Initialize the trip sensor.

        Args:
            coordinator: TripPlannerCoordinator instance.
            vehicle_id: Vehicle identifier.
            trip_id: Trip identifier.
        """
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._vehicle_id = vehicle_id
        self._trip_id = trip_id
        self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_trip_{trip_id}"
        self._attr_name = f"Trip {trip_id}"
        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_state_class = None
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        # Set enum options for estado
        self._attr_options = [
            "active",
            "pendiente",
            "completado",
            "cancelado",
            "recurrente",
        ]

    def _get_trip_data(self) -> Dict[str, Any]:
        """Get trip data from coordinator.

        Returns:
            Trip data dict or empty dict if not found.
        """
        if self.coordinator.data is None:
            return {}
        recurring_trips = self.coordinator.data.get("recurring_trips", {})
        punctual_trips = self.coordinator.data.get("punctual_trips", {})
        trip_data = recurring_trips.get(self._trip_id)
        if trip_data is None:
            trip_data = punctual_trips.get(self._trip_id)
        return trip_data if trip_data is not None else {}

    @property
    def native_value(self) -> Any:
        """Return sensor value (trip estado)."""
        trip_data = self._get_trip_data()
        if not trip_data:
            return None
        trip_type = trip_data.get("tipo", "unknown")
        if trip_type == TRIP_TYPE_PUNCTUAL:
            return trip_data.get("estado", "pendiente")
        return "recurrente"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return trip details as attributes."""
        trip_data = self._get_trip_data()
        if not trip_data:
            return {}
        return {
            "trip_id": trip_data.get("id", self._trip_id),
            "trip_type": trip_data.get("tipo", "unknown"),
            "descripcion": trip_data.get("descripcion", ""),
            "km": trip_data.get("km", 0.0),
            "kwh": trip_data.get("kwh", 0.0),
            "fecha_hora": trip_data.get("datetime", trip_data.get("hora", "")),
            "activo": trip_data.get("activo", True),
            "estado": trip_data.get("estado", "pendiente"),
        }

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device info for the trip sensor."""
        return dr.DeviceInfo(
            identifiers={(DOMAIN, f"{self._vehicle_id}_{self._trip_id}")},
            name=f"Trip {self._trip_id} - {self._vehicle_id}",
            manufacturer="Home Assistant",
            model="EV Trip Planner",
            sw_version="2026.3.0",
            via_device=(DOMAIN, self._vehicle_id),
        )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Any
) -> bool:
    """Set up sensors from config entry."""
    entry_id = entry.entry_id

    # Use entry.runtime_data set by __init__.py::async_setup_entry
    runtime_data = entry.runtime_data
    trip_manager = runtime_data.trip_manager
    coordinator = runtime_data.coordinator
    vehicle_id = coordinator.vehicle_id

    if not trip_manager:
        _LOGGER.error(
            "No trip_manager found for entry %s",
            entry_id,
            exc_info=True,
        )
        return False

    _LOGGER.debug(
        "Setting up sensors for vehicle_id=%s, entry_id=%s, coordinator=%s",
        vehicle_id,
        entry_id,
        coordinator is not None,
    )

    # Filter sensors based on exists_fn (G-07.4)
    entities: list[SensorEntity] = [
        TripPlannerSensor(coordinator, vehicle_id, desc)
        for desc in TRIP_SENSORS
        if desc.exists_fn(coordinator.data)
    ]
    entities.append(EmhassDeferrableLoadSensor(coordinator, entry_id))

    # Create trip sensors for existing trips
    trip_sensors = await _async_create_trip_sensors(
        coordinator, trip_manager, vehicle_id, entry_id
    )
    entities.extend(trip_sensors)

    _LOGGER.debug(
        "Created sensors for %s: %s",
        vehicle_id,
        [type(e).__name__ for e in entities],
    )

    # async_add_entities may be sync or async depending on HA version
    result = async_add_entities(entities)
    if result is not None:
        # Await if it returns an awaitable (async callback)
        try:
            await result
        except TypeError:  # pragma: no cover  # HA entity platform - sync callbacks return None which causes TypeError when awaited
            # Sync callback - result is None, nothing to await
            pass  # pragma: no cover  # HA entity platform - sync callback error handling

    # Capture async_add_entities callback for dynamic service use (task 2.3)
    runtime_data.sensor_async_add_entities = async_add_entities

    return True


async def _async_create_trip_sensors(
    coordinator: TripPlannerCoordinator,
    trip_manager: Any,
    vehicle_id: str,
    entry_id: str,
) -> List["TripSensor"]:
    """Create sensor entities for existing trips in the trip manager.

    Args:
        coordinator: The TripPlannerCoordinator instance.
        trip_manager: The TripManager instance.
        vehicle_id: The vehicle identifier.
        entry_id: The config entry ID.

    Returns:
        List of TripSensor entities created.
    """
    entities: List[TripSensor] = []

    try:
        # Get existing trips from trip manager
        recurring_trips = await trip_manager.async_get_recurring_trips()
        punctual_trips = await trip_manager.async_get_punctual_trips()

        _LOGGER.debug(
            "Creating trip sensors for %s: %d recurring, %d punctual trips",
            vehicle_id,
            len(recurring_trips),
            len(punctual_trips),
        )

        # Create sensors for recurring trips
        for trip_data in recurring_trips:  # pragma: no cover  # HA entity platform - loop creates sensors for all valid trips; no error means all succeed
            try:  # pragma: no cover  # HA entity platform - try block for sensor creation
                sensor = TripSensor(coordinator, vehicle_id, trip_data.get("id", ""))
                entities.append(sensor)
                _LOGGER.debug(  # pragma: no cover  # HA entity platform - debug logging for successful sensor creation
                    "Created trip sensor for recurring trip %s",
                    trip_data.get("id"),
                )
            except Exception as err:  # pragma: no cover  # HA entity platform - defensive error handling for malformed trip data
                _LOGGER.warning(  # pragma: no cover  # HA entity platform - warning logged but sensor creation continues
                    "Failed to create sensor for recurring trip %s: %s",
                    trip_data.get("id"),
                    err,
                )

        # Create sensors for punctual trips
        for trip_data in punctual_trips:
            try:
                sensor = TripSensor(coordinator, vehicle_id, trip_data.get("id", ""))
                entities.append(sensor)
                _LOGGER.debug(
                    "Created trip sensor for punctual trip %s",
                    trip_data.get("id"),
                )
            except Exception as err:  # pragma: no cover  # HA entity platform - defensive error handling for malformed trip data
                _LOGGER.warning(  # pragma: no cover  # HA entity platform - warning logged but sensor creation continues
                    "Failed to create sensor for punctual trip %s: %s",
                    trip_data.get("id"),
                    err,
                )

        _LOGGER.info(
            "Created %d trip sensors for vehicle %s",
            len(entities),
            vehicle_id,
        )

    except Exception as err:
        _LOGGER.error(
            "Error creating trip sensors for vehicle %s: %s",
            vehicle_id,
            err,
            exc_info=True,
        )

    return entities


async def async_create_trip_sensor(
    hass: HomeAssistant,
    entry_id: str,
    trip_data: Dict[str, Any],
) -> bool:
    """Create a sensor entity for a trip.

    Args:
        hass: The Home Assistant instance.
        entry_id: The config entry ID.
        trip_data: The trip data dictionary (includes id and tipo).

    Returns:
        True if sensor was created successfully.
    """
    trip_id: str = trip_data.get("id") or ""
    trip_type = trip_data.get("tipo", "recurrente")

    _LOGGER.info("Creating trip sensor for trip %s (type=%s)", trip_id, trip_type)

    # Get entry and runtime_data
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry:
        _LOGGER.error("No entry found for entry_id %s", entry_id)
        return False

    runtime_data = entry.runtime_data
    trip_manager = runtime_data.trip_manager
    coordinator = runtime_data.coordinator
    async_add_entities = runtime_data.sensor_async_add_entities

    if not trip_manager:
        _LOGGER.error("No trip_manager found for entry %s", entry_id)
        return False

    if not coordinator:
        _LOGGER.error("No coordinator found for entry %s", entry_id)
        return False

    if not async_add_entities:
        _LOGGER.error(
            "No async_add_entities callback found for entry %s (platform not set up)",
            entry_id,
        )
        return False

    vehicle_id = coordinator.vehicle_id

    # Create the trip sensor (new signature: coordinator, vehicle_id, trip_id)
    try:
        sensor = TripSensor(coordinator, vehicle_id, trip_id)
        # Register via async_add_entities so entity appears in registry
        result = async_add_entities([sensor], True)
        if result is not None:
            try:
                await result
            except TypeError:  # pragma: no cover  # HA entity platform - sync callbacks return None which causes TypeError when awaited
                # Sync callback
                pass  # pragma: no cover  # HA entity platform - sync callback error handling
        _LOGGER.debug("Trip sensor created and registered for trip %s", trip_id)
        return True
    except Exception as err:  # pragma: no cover  # HA entity platform - defensive error handling for sensor creation failure
        _LOGGER.error("Failed to create trip sensor for trip %s: %s", trip_id, err)
        return False  # pragma: no cover  # HA entity platform - error return path


async def async_update_trip_sensor(
    hass: HomeAssistant,
    entry_id: str,
    trip_data: Dict[str, Any],
) -> bool:
    """Update a trip sensor entity with new data.

    Args:
        hass: The Home Assistant instance.
        entry_id: The config entry ID.
        trip_data: The updated trip data dictionary (includes id).

    Returns:
        True if sensor was updated successfully.
    """
    trip_id: str = trip_data.get("id") or ""

    _LOGGER.debug("Updating trip sensor for trip %s", trip_id)

    # Get entry and runtime_data
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry:
        _LOGGER.error("No entry found for entry_id %s", entry_id)
        return False

    runtime_data = entry.runtime_data
    trip_manager = runtime_data.trip_manager

    if not trip_manager:
        _LOGGER.error("No trip_manager found for entry %s", entry_id)
        return False

    # Find existing sensor in entity registry
    entity_registry: EntityRegistry = getattr(
        hass, "entity_registry", None
    ) or er_async_get(hass)
    existing_entity = None
    for reg_entry in async_entries_for_config_entry(entity_registry, entry_id):
        unique_id = reg_entry.unique_id
        if (
            isinstance(unique_id, str)
            and trip_id in unique_id
            and "trip" in unique_id.lower()
        ):
            existing_entity = reg_entry
            break

    if existing_entity:
        # Get the state entity and update it
        state = hass.states.get(existing_entity.entity_id)
        if state:
            # Update internal trip data
            _LOGGER.debug(
                "Trip sensor found in registry for trip %s, state=%s", trip_id, state
            )

        # FIX: Trigger coordinator refresh to update sensor immediately
        # Sensor data comes from coordinator.data via CoordinatorEntity.
        # This refresh ensures sensors reflect changes immediately (not wait 30s for periodic refresh).
        coordinator = runtime_data.coordinator
        if coordinator:
            await coordinator.async_request_refresh()
            _LOGGER.debug(
                "Coordinator refresh triggered for trip %s sensor update", trip_id
            )

        _LOGGER.debug("Trip sensor updated for trip %s", trip_id)
        return True
    else:
        # Sensor doesn't exist, create it
        return await async_create_trip_sensor(hass, entry_id, trip_data)


async def async_remove_trip_sensor(
    hass: HomeAssistant,
    entry_id: str,
    trip_id: str,
) -> bool:
    """Remove a trip sensor entity.

    Args:
        hass: The Home Assistant instance.
        entry_id: The config entry ID.
        trip_id: The trip identifier to remove.

    Returns:
        True if sensor was removed successfully.
    """
    _LOGGER.debug("Removing trip sensor for trip %s", trip_id)

    # Remove from Entity Registry
    entity_registry: EntityRegistry = getattr(
        hass, "entity_registry", None
    ) or er_async_get(hass)
    removed = False
    for entry in async_entries_for_config_entry(entity_registry, entry_id):
        if isinstance(entry.unique_id, str) and trip_id in entry.unique_id:
            entity_registry.async_remove(entry.entity_id)
            removed = True
            _LOGGER.debug(
                "Entity registry entry removed for trip %s: %s",
                trip_id,
                entry.entity_id,
            )
            break

    if removed:
        return True
    else:
        _LOGGER.debug("Trip sensor %s not found in registry", trip_id)
        return False


# =============================================================================
# async_remove_trip_emhass_sensor — FR-6 (Task 1.36 GREEN)
# =============================================================================


async def async_remove_trip_emhass_sensor(
    hass: HomeAssistant,
    entry_id: str,
    vehicle_id: str,
    trip_id: str,
) -> bool:
    """Remove an EMHASS sensor entity.

    Args:
        hass: The Home Assistant instance.
        entry_id: The config entry ID.
        vehicle_id: The vehicle identifier.
        trip_id: The trip identifier to remove.

    Returns:
        True if sensor was removed successfully.
    """
    _LOGGER.debug("Removing EMHASS sensor for trip %s", trip_id)

    # Remove from Entity Registry
    entity_registry: EntityRegistry = getattr(
        hass, "entity_registry", None
    ) or er_async_get(hass)
    removed = False
    for entry in async_entries_for_config_entry(entity_registry, entry_id):
        unique_id = entry.unique_id
        if (
            isinstance(unique_id, str)
            and trip_id in unique_id
            and "emhass" in unique_id
        ):
            entity_registry.async_remove(entry.entity_id)
            removed = True
            _LOGGER.debug(
                "Entity registry entry removed for EMHASS trip %s: %s",
                trip_id,
                entry.entity_id,
            )
            break

    if removed:
        return True
    else:
        _LOGGER.debug("EMHASS sensor %s not found in registry", trip_id)
        return False


# =============================================================================
# async_create_trip_emhass_sensor — FR-5 (Task 1.32 GREEN)
# =============================================================================


async def async_create_trip_emhass_sensor(
    hass: HomeAssistant,
    entry_id: str,
    coordinator: TripPlannerCoordinator,
    vehicle_id: str,
    trip_id: str,
) -> bool:
    """Create a sensor entity for a trip's EMHASS parameters.

    Args:
        hass: The Home Assistant instance.
        entry_id: The config entry ID.
        coordinator: The TripPlannerCoordinator instance.
        vehicle_id: The vehicle identifier.
        trip_id: The trip identifier.

    Returns:
        True if sensor was created successfully.
    """
    _LOGGER.info(
        "Creating EMHASS sensor for trip %s on vehicle %s", trip_id, vehicle_id
    )

    # Get entry and runtime_data
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry:
        _LOGGER.error("No entry found for entry_id %s", entry_id)
        return False

    runtime_data = entry.runtime_data
    async_add_entities = runtime_data.sensor_async_add_entities

    if not async_add_entities:
        _LOGGER.error(
            "No async_add_entities callback found for entry %s (platform not set up)",
            entry_id,
        )
        return False

    # Create the EMHASS sensor
    try:
        sensor = TripEmhassSensor(coordinator, vehicle_id, trip_id)
        # Register via async_add_entities so entity appears in registry
        result = async_add_entities([sensor], True)
        if result is not None:
            try:
                await result
            except TypeError:  # pragma: no cover  # HA entity platform - sync callbacks return None which causes TypeError when awaited
                # Sync callback
                pass  # pragma: no cover  # HA entity platform - sync callback error handling
        _LOGGER.debug("EMHASS sensor created and registered for trip %s", trip_id)
        return True
    except Exception as err:  # pragma: no cover  # HA entity platform - defensive error handling for sensor creation failure
        _LOGGER.error("Failed to create EMHASS sensor for trip %s: %s", trip_id, err)
        return False  # pragma: no cover  # HA entity platform - error return path


# =============================================================================
# TripEmhassSensor — New per-trip EMHASS sensor (Task 1.24 GREEN)
# =============================================================================


class TripEmhassSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity):
    """Sensor for per-trip EMHASS parameters.

    This is a new sensor class for PHASE 4, separate from existing trip sensors.
    It reads emhass_index from coordinator.data["per_trip_emhass_params"].

    Attributes:
        native_value: The emhass_index for the trip, or -1 if not found
    """

    def __init__(
        self,
        coordinator: TripPlannerCoordinator,
        vehicle_id: str,
        trip_id: str,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: TripPlannerCoordinator instance.
            vehicle_id: Vehicle identifier.
            trip_id: Trip identifier.
        """
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._vehicle_id = vehicle_id
        self._trip_id = trip_id
        self._attr_unique_id = f"emhass_trip_{vehicle_id}_{trip_id}"
        self._attr_has_entity_name = True
        self._attr_name = f"EMHASS Index for {trip_id}"

    @property
    def native_value(self) -> int:
        """Return the emhass_index for this trip.

        Reads from coordinator.data["per_trip_emhass_params"][trip_id]["emhass_index"].
        Returns -1 if trip not found or emhass_index not available.

        Returns:
            The emhass_index integer, or -1 if not found.
        """
        if self.coordinator.data is None:
            return -1

        per_trip_params = self.coordinator.data.get("per_trip_emhass_params", {})
        trip_params = per_trip_params.get(self._trip_id, {})
        emhass_index = trip_params.get("emhass_index", -1)

        return emhass_index if emhass_index is not None else -1

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes for this trip.

        Returns all 9 per-trip EMHASS parameters:
        - def_total_hours, P_deferrable_nom, def_start_timestep, def_end_timestep
        - power_profile_watts, trip_id, emhass_index, kwh_needed, deadline

        Returns:
            Dict with all 9 keys, or zeroed values if trip not found.
        """
        if self.coordinator.data is None:
            return self._zeroed_attributes()

        per_trip_params = self.coordinator.data.get("per_trip_emhass_params", {})
        trip_params = per_trip_params.get(self._trip_id)

        if trip_params is None:
            return self._zeroed_attributes()

        # Filter to ONLY the 9 documented keys — prevents data leak
        return {k: v for k, v in trip_params.items() if k in TRIP_EMHASS_ATTR_KEYS}

    def _zeroed_attributes(self) -> Dict[str, Any]:
        """Return zeroed/default values for all 9 attributes.

        Used when trip not found or data unavailable.

        Returns:
            Dict with all 9 keys set to zero/None/empty values.
        """
        return {
            "def_total_hours": 0.0,
            "P_deferrable_nom": 0.0,
            "def_start_timestep": 0,
            "def_end_timestep": 24,
            "power_profile_watts": [],
            "trip_id": self._trip_id,
            "emhass_index": -1,
            "kwh_needed": 0.0,
            "deadline": None,
        }

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device info for this sensor.

        Uses device identifiers={(DOMAIN, vehicle_id)} to group
        all TripEmhassSensor instances under the same vehicle device.

        Returns:
            DeviceInfo with 'identifiers' key containing {(DOMAIN, vehicle_id)},
            or None if not configured.
        """
        from .const import DOMAIN

        return dr.DeviceInfo(
            identifiers={(DOMAIN, self._vehicle_id)},
        )
