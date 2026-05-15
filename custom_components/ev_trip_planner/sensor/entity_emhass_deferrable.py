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

    def _extract_active_trips_sorted(
        self, per_trip_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter active trips and sort by (def_start_timestep, emhass_index)."""
        active: List[Dict[str, Any]] = []
        for params in per_trip_params.values():
            if params.get("activo", False):
                active.append(params)
        active.sort(
            key=lambda x: (x.get("def_start_timestep", 0), x.get("emhass_index", 0))
        )
        return active

    def _aggregate_trip_params(
        self, active_trips: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate 6 array/matrix attributes from sorted active trips."""
        matrix, number_of_loads = self._extract_matrix_and_count(active_trips)
        arrays = self._collect_arrays(active_trips)
        return self._build_aggregate_result(matrix, number_of_loads, arrays)

    def _extract_matrix_and_count(
        self, active_trips: List[Dict[str, Any]]
    ) -> tuple:
        """Extract p_deferrable_matrix and count loads from active trips."""
        matrix: List[List[float]] = []
        count = 0
        for params in active_trips:
            p_matrix = params.get("p_deferrable_matrix")
            if p_matrix:
                matrix.extend(p_matrix)
                count += len(p_matrix)
            elif "p_deferrable_matrix" not in params:
                count += 1
        return matrix, count

    def _collect_arrays(
        self, active_trips: List[Dict[str, Any]]
    ) -> Dict[str, List[float]]:
        """Collect deferrable arrays from all active trips."""
        arrays: Dict[str, List] = {
            "def_total_hours_array": [],
            "p_deferrable_nom_array": [],
            "def_start_timestep_array": [],
            "def_end_timestep_array": [],
        }
        for params in active_trips:
            for key, target_list in arrays.items():
                if key in params:
                    target_list.extend(params[key])
        return {k: v for k, v in arrays.items() if v}

    def _build_aggregate_result(
        self,
        matrix: List[List[float]],
        number_of_loads: int,
        arrays: Dict[str, List],
    ) -> Dict[str, Any]:
        """Build final aggregate result dict with conditional keys."""
        result: Dict[str, Any] = {"number_of_deferrable_loads": number_of_loads}
        if matrix:
            result["p_deferrable_matrix"] = matrix
        result.update(arrays)
        return result

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes from coordinator.data.

        Includes aggregated deferrable load parameters from all active trips.
        """
        if self.coordinator.data is None:
            _LOGGER.warning("BUG-DEBUG: extra_state_attributes called but coordinator.data is None")
            return {}

        vehicle_id = getattr(self.coordinator, "vehicle_id", self._entry_id)
        
        per_trip = self.coordinator.data.get("per_trip_emhass_params", {})
        _LOGGER.warning(
            "BUG-DEBUG: extra_state_attributes per_trip_emhass_params=%d trips",
            len(per_trip),
        )
        for tid, tp in per_trip.items():
            _LOGGER.warning(
                "BUG-DEBUG: sensor per_trip[%s] def_total_hours_array=%s def_start_timestep_array=%s def_end_timestep_array=%s p_deferrable_nom_array=%s",
                tid,
                tp.get("def_total_hours_array"),
                tp.get("def_start_timestep_array"),
                tp.get("def_end_timestep_array"),
                tp.get("p_deferrable_nom_array"),
            )
        
        attrs: Dict[str, Any] = {
            "power_profile_watts": self.coordinator.data.get("emhass_power_profile"),
            "deferrables_schedule": self.coordinator.data.get("emhass_deferrables_schedule"),
            "emhass_status": self.coordinator.data.get("emhass_status"),
            "vehicle_id": vehicle_id,
        }

        per_trip_params = self.coordinator.data.get("per_trip_emhass_params", {})
        if per_trip_params:
            active = self._extract_active_trips_sorted(per_trip_params)
            aggregated = self._aggregate_trip_params(active)
            attrs.update(aggregated)
        else:
            attrs["number_of_deferrable_loads"] = 0

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
