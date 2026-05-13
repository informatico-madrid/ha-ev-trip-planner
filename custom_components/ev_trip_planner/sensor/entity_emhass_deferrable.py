"""EmhassDeferrableLoadSensor entity implementation.

Extracted from sensor_orig.py as part of the SOLID decomposition (Spec 3).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import TripPlannerCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceInfo

_LOGGER = logging.getLogger(__name__)


class EmhassDeferrableLoadSensor(
    CoordinatorEntity[TripPlannerCoordinator],
    SensorEntity,  # type: ignore[misc]  # HA stub: CoordinatorEntity mixin typing
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
    ) -> None:  # pragma: no cover reason=HA entity lifecycle — async_will_remove_from_hass called only when entity is removed from HA entity registry, requires HA runtime
        """Clean up when entity is removed from Home Assistant."""
        trip_manager = getattr(self.coordinator, "trip_manager", None)
        if (
            trip_manager
            and hasattr(trip_manager, "_emhass_adapter")
            and trip_manager._emhass_adapter is not None
        ):
            await trip_manager._emhass_adapter.async_cleanup_vehicle_indices()
