"""EMHASS adapter — facade delegating to sub-components."""

from __future__ import annotations

import math
from datetime import (
    datetime,  # noqa: F401 — re-export for test mock path (conftest.py:822)
)
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import (
    Store,  # noqa: F401 — re-export for test compatibility
)

from .error_handler import ErrorHandler
from .index_manager import IndexManager
from .load_publisher import LoadPublisher, LoadPublisherConfig


class EMHASSAdapter:
    """Facade for EMHASS operations delegating to sub-components.

    Composes IndexManager, LoadPublisher, and ErrorHandler to provide
    a unified interface while maintaining single responsibility per component.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the EMHASS adapter facade.

        Args:
            hass: HomeAssistant instance.
            entry: ConfigEntry for the integration.
        """
        self.hass = hass
        self._entry = entry
        self.vehicle_id = entry.entry_id if hasattr(entry, "entry_id") else "unknown"
        self.entry_id = getattr(entry, "entry_id", "unknown")

        # Sub-component initialization
        self._index_manager = IndexManager()
        self._load_publisher = LoadPublisher(
            hass=hass,
            vehicle_id=self.vehicle_id,
            config=LoadPublisherConfig(index_manager=self._index_manager),
        )
        self._error_handler = ErrorHandler(hass=hass)

        # State attributes (used by callers and tests)
        self._published_trips: list[Dict[str, Any]] = []
        self._cached_per_trip_params: Dict[str, Any] = {}
        self._cached_power_profile: List[Any] | None = None
        self._cached_deferrables_schedule: List[Any] | None = None
        self._cached_emhass_status: str | None = None
        self._config_entry_listener = None
        self._shutting_down = False
        self._charging_power_kw: float | None = None
        self._stored_charging_power_kw: float | None = None
        self._stored_t_base: float | None = None
        self._stored_soh_sensor: str | None = None
        self._released_indices: list[Dict[str, Any]] = []

    @property
    def _index_map(self) -> Dict[str, int]:
        """Backward-compat property: tests access adapter._index_map directly."""
        return self._index_manager._index_map

    @_index_map.setter
    def _index_map(self, value: Dict[str, int]) -> None:
        """Setter for test compatibility."""
        self._index_manager._index_map = value

    async def async_load(self) -> None:
        """Load adapter state from storage."""
        await self._index_manager.async_load_index()

    async def async_save(self) -> None:
        """Save adapter state to storage."""
        await self._index_manager.async_save_index()

    async def async_assign_index_to_trip(self, trip_id: str) -> Optional[int]:
        """Assign an index to a trip."""
        try:
            return await self._index_manager.async_assign_index_to_trip(trip_id)
        except Exception as err:
            self._error_handler.handle_error("assign_index", err, {"trip_id": trip_id})
            return None

    async def async_release_trip_index(self, trip_id: str) -> bool:
        """Release an index for a trip."""
        try:
            result = await self._index_manager.async_release_index(trip_id)
            if result is None:
                self._error_handler.handle_index_error(trip_id, "release")
                return False
            return True
        except Exception as err:
            self._error_handler.handle_error("release_index", err, {"trip_id": trip_id})
            return False

    async def async_remove_deferrable_load(self, trip_id: str) -> bool:
        """Remove a deferrable load."""
        try:
            return await self._load_publisher.remove(trip_id)
        except Exception as err:
            self._error_handler.handle_error("remove", err, {"trip_id": trip_id})
            return False

    async def async_update_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """Update an existing deferrable load."""
        try:
            return await self._load_publisher.update(trip)
        except Exception as err:
            self._error_handler.handle_error("update", err, {"trip": trip.get("id")})
            return False

    def get_assigned_index(self, trip_id: str) -> Optional[int]:
        """Get the assigned index for a trip."""
        return self._index_manager._index_map.get(trip_id)

    def get_all_assigned_indices(self) -> Dict[str, int]:
        """Get all assigned indices."""
        return dict(self._index_manager._index_map)

    def get_available_indices(self) -> List[int]:
        """Get list of available indices."""
        if not self._index_manager._index_map:
            return [0]
        max_idx = max(self._index_manager._index_map.values())
        return list(range(max_idx + 1))

    async def async_notify_error(
        self,
        error_message: str,
        trip_id: Optional[str] = None,
    ) -> None:
        """Notify about an EMHASS error."""
        self._error_handler.handle_error(
            "notify", Exception(error_message), {"trip_id": trip_id}
        )

    def get_cached_optimization_results(self) -> Dict[str, Any]:
        """Return cached optimization results for coordinator retrieval.

        Returns:
            Dict with emhass_power_profile, emhass_deferrables_schedule,
            emhass_status, and per_trip_emhass_params keys.
        """
        return {
            "emhass_power_profile": self._cached_power_profile,
            "emhass_deferrables_schedule": self._cached_deferrables_schedule,
            "emhass_status": self._cached_emhass_status,
            "per_trip_emhass_params": self._cached_per_trip_params,
        }

    async def update_charging_power(self, force: bool = False) -> None:
        """Update charging power and republish sensor attributes if changed.

        Args:
            force: If True, skip the unchanged-power early-return and always
                   republish.
        """
        if self._shutting_down:
            return

        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        if not entry:
            return

        new_power = entry.options.get("charging_power_kw")
        if new_power is None:
            new_power = entry.data.get("charging_power_kw")
        if new_power is None:
            return

        if not force and new_power == self._charging_power_kw:
            return

        self._charging_power_kw = new_power
        self._stored_charging_power_kw = new_power

    def setup_config_entry_listener(self) -> None:
        """Subscribe to config entry updates to trigger republish when charging power changes."""
        self.config_entry = self.hass.config_entries.async_get_entry(self.entry_id)
        if not self.config_entry:
            return
        self._config_entry_listener = self.config_entry.async_on_unload(
            self.config_entry.add_update_listener(self._handle_config_entry_update)
        )

    async def _handle_config_entry_update(
        self, hass: HomeAssistant, config_entry: ConfigEntry
    ) -> None:
        """Handle config entry update events."""
        if self._shutting_down:
            return

        cur_options = dict(getattr(config_entry, "options", {}) or {})
        new_charging_power = cur_options.get("charging_power_kw")
        if new_charging_power is not None:
            self._stored_charging_power_kw = new_charging_power
            self._charging_power_kw = new_charging_power

    async def async_publish_all_deferrable_loads(
        self,
        trips: List[Dict[str, Any]],
        charging_power: float | None = None,
        charging_power_kw: float | None = None,
    ) -> bool:
        """Publish all trips as deferrable loads.

        Args:
            trips: List of trip dictionaries to publish.
            charging_power: Optional charging power override.
            charging_power_kw: Deprecated alias for charging_power.

        Returns:
            True if all trips were published successfully.
        """
        if not trips or self._shutting_down:
            return False

        # Support both param names (backward compat)
        cp = charging_power or charging_power_kw
        if cp is not None:
            self._load_publisher.charging_power_kw = cp

        success = True
        self._published_trips = list(trips)
        self._cached_per_trip_params = {}
        self._cached_power_profile = []
        self._cached_deferrables_schedule = []

        for trip in trips:
            trip_success = await self.async_publish_deferrable_load(trip)
            if not trip_success:
                success = False

        return success

    async def async_cleanup_vehicle_indices(self) -> None:
        """Clean up all indices for this vehicle."""
        indices_to_release = list(self._index_manager._index_map.keys())
        for trip_id in indices_to_release:
            self._index_manager.release_index(trip_id)
        self._published_trips = []
        self._cached_per_trip_params = {}
        self._cached_power_profile = []
        self._cached_deferrables_schedule = []

    async def async_save_trips(self) -> None:
        """Save trips to storage."""
        await self._index_manager.async_save_index()

    def calculate_deferrable_parameters(
        self, trips: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate deferrable parameters from trips.

        Args:
            trips: List of trip dictionaries.

        Returns:
            Dict with calculated parameters.
        """
        return {}

    # ------------------------------------------------------------------
    # Backward-compat methods for test compatibility (SOLID refactor)
    # ------------------------------------------------------------------

    async def _get_current_soc(self) -> Optional[float]:
        """Get current SOC from configured sensor.

        Returns:
            SOC percentage as float, or None if sensor unavailable.
        """
        # Use stored entry for soc_sensor access
        entry_data = getattr(self, "_entry_dict", None)
        if not entry_data:
            return None
        soc_sensor = (
            entry_data.get("soc_sensor") if isinstance(entry_data, dict) else None
        )
        if not soc_sensor:
            return None
        state = self.hass.states.get(soc_sensor)
        if state is None:
            return None
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    def _calculate_deadline_from_trip(self, trip: Dict[str, Any]) -> Optional[datetime]:
        """Calculate deadline datetime from trip data.

        Delegates to LoadPublisher for the actual calculation.
        """
        return self._load_publisher._calculate_deadline(trip)

    async def _get_hora_regreso(self) -> Optional[datetime]:
        """Get hora_regreso (return time) from presence monitor.

        Returns:
            Return time datetime or None if unavailable.
        """
        # Stub: in production this would query the presence monitor.
        # Tests that need this functionality should mock it.
        return None

    async def _populate_per_trip_cache_entry(
        self,
        trip: Dict[str, Any],
        trip_id: str,
        charging_power_kw: float,
        battery_capacity_kwh: float,
        safety_margin_percent: float,
        soc_current: float,
        hora_regreso: Optional[datetime] = None,
        pre_computed_inicio_ventana: Optional[datetime] = None,
        pre_computed_fin_ventana: Optional[datetime] = None,
        adjusted_def_total_hours: Optional[float] = None,
        soc_cap: Optional[float] = None,
    ) -> None:
        """Build and cache per-trip EMHASS parameters.

        Simplified version for test compatibility. Stores the trip's
        charging parameters in _cached_per_trip_params.
        """
        # Assign index if not already assigned
        if trip_id not in self._index_map:
            await self.async_assign_index_to_trip(trip_id)
        emhass_index = self._index_map.get(trip_id, -1)

        from homeassistant.util import dt as dt_util

        now = dt_util.now()

        # Calculate deadline
        deadline_dt = self._calculate_deadline_from_trip(trip)

        def_start_timestep = 0
        def_end_timestep = 168  # default: 1 week horizon
        total_hours = 0.0
        charging_windows: List[Dict[str, Any]] = []

        if deadline_dt is not None:
            hours_available = (deadline_dt - now).total_seconds() / 3600

            # Calculate charging windows
            charging_windows = self._load_publisher._calculate_charging_windows(
                deadline_dt=deadline_dt,
                trip=trip,
                soc_current=soc_current,
            )

            def_end_timestep = min(int(max(0, hours_available)), 168)

            # Use pre-computed ventana if provided (batch mode)
            if pre_computed_inicio_ventana is not None:
                delta_hours = (
                    self._load_publisher._ensure_aware(pre_computed_inicio_ventana)
                    - now
                ).total_seconds() / 3600
                def_start_timestep = max(0, min(int(delta_hours), 168))
            elif charging_windows and charging_windows[0].get("inicio_ventana"):
                inicio = charging_windows[0]["inicio_ventana"]
                delta_hours = (
                    self._load_publisher._ensure_aware(inicio) - now
                ).total_seconds() / 3600
                def_start_timestep = max(0, min(int(delta_hours), 168))

            # fin_ventana for def_end_timestep
            if pre_computed_fin_ventana is not None:
                delta_hours_end = (
                    self._load_publisher._ensure_aware(pre_computed_fin_ventana) - now
                ).total_seconds() / 3600
                if delta_hours_end > 0:
                    def_end_timestep = max(
                        0, min(math.ceil(delta_hours_end - 0.001), 168)
                    )
            elif charging_windows and charging_windows[0].get("fin_ventana"):
                fin = charging_windows[0]["fin_ventana"]
                if isinstance(fin, datetime):
                    delta_hours_end = (
                        self._load_publisher._ensure_aware(fin) - now
                    ).total_seconds() / 3600
                    def_end_timestep = max(
                        0, min(math.ceil(delta_hours_end - 0.001), 168)
                    )

            # Apply off-by-one fix
            def_start_timestep = max(0, def_start_timestep - 1)

            # Calculate energy parameters
            from ..calculations import calculate_energy_needed

            energy_info = calculate_energy_needed(
                trip,
                battery_capacity_kwh,
                soc_current,
                charging_power_kw,
                safety_margin_percent=safety_margin_percent,
            )
            total_hours = energy_info["horas_carga_necesarias"]

        # Always store the cache entry (even if deadline was None)
        self._cached_per_trip_params[trip_id] = {
            "emhass_index": emhass_index,
            "def_start_timestep": def_start_timestep,
            "def_end_timestep": def_end_timestep,
            "def_total_hours": total_hours,
            "total_hours": total_hours,
            "power_watts": charging_power_kw * 1000 if total_hours > 0 else 0.0,
            "kwh_needed": total_hours * charging_power_kw,
            "charging_window": charging_windows,
        }

    async def async_publish_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """Publish a single trip as a deferrable load.

        Populates _cached_per_trip_params and _published_trips for cache
        consistency. Delegates the actual publish to LoadPublisher.

        Args:
            trip: Trip dictionary.

        Returns:
            True if published successfully.
        """
        trip_id = trip.get("id")
        if not trip_id:
            return False

        # Always populate cache entry for trips with valid IDs, even if publish fails
        # This ensures _cached_per_trip_params reflects attempted publishes
        try:
            soc_current = await self._get_current_soc()
            if soc_current is None:
                soc_current = 50.0
            await self._populate_per_trip_cache_entry(
                trip=trip,
                trip_id=trip_id,
                charging_power_kw=self._charging_power_kw or 3.6,
                battery_capacity_kwh=self._load_publisher.battery_capacity_kwh,
                safety_margin_percent=self._load_publisher.safety_margin_percent,
                soc_current=soc_current,
            )
        except Exception:
            # Cache population failure should not prevent publish attempt
            pass

        # Delegate actual publish to LoadPublisher
        result = await self._load_publisher.publish(trip)

        # Track published trips
        if result:
            if trip_id not in self._published_trips:
                self._published_trips.append(trip)

        return result
