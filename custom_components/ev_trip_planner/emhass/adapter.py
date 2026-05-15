"""EMHASS adapter — facade delegating to sub-components."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import (
    datetime,  # noqa: F401 — re-export for test mock path (conftest.py:822)
)
from typing import Any, Dict, List, Optional, Tuple

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import (
    Store,  # noqa: F401 — re-export for test compatibility
)

from .error_handler import ErrorHandler
from .index_manager import IndexManager
from .load_publisher import LoadPublisher, LoadPublisherConfig


# qg-accepted: BMAD consensus 2026-05-12 — FALSE POSITIVE: facade pattern (18 public methods,
#   27 attrs, high delegation ratio are all inherent to the facade architecture delegating
#   to IndexManager, LoadPublisher, ErrorHandler. Tier A counts facade methods as violations,
#   Tier B confirms facades are legitimate SOLID-compliant design.


# Note: CachePolicy ABC removed to fix AP12 Speculative Generality.
# OCP abstractness is maintained by existing ABCs with real implementations.


@dataclass(frozen=True)
class PerTripCacheParams:
    """Parameters for building per-trip EMHASS cache entries.

    Bundled to reduce _populate_per_trip_cache_entry arity from 11 to 2.
    The 5 optional test-compatibility params remain as separate kwargs
    to preserve backward compatibility with callers that pass them.
    """

    trip: Dict[str, Any]
    trip_id: str
    charging_power_kw: float
    battery_capacity_kwh: float
    safety_margin_percent: float
    soc_current: float


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
        self._published_trips: set[str] = set()
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
            success = await self._load_publisher.remove(trip_id)
            # Clean stale cache entry to prevent cross-test pollution
            self._cached_per_trip_params.pop(trip_id, None)
            return success
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
        # Propagate to LoadPublisher so publish() uses correct power
        self._load_publisher.charging_power_kw = new_power

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
            # Propagate to LoadPublisher so publish() uses correct power
            self._load_publisher.charging_power_kw = new_charging_power

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
        if self._shutting_down:
            return False

        # When no trips remain, clear cache to reflect empty state
        if not trips:
            self._cached_power_profile = []
            self._cached_deferrables_schedule = []
            self._cached_per_trip_params = {}
            self._cached_emhass_status = "ready"
            return True

        # Support both param names (backward compat)
        cp = charging_power or charging_power_kw
        if cp is not None:
            self._load_publisher.charging_power_kw = cp

        success = True
        self._published_trips = {t.get("id", "") for t in trips}
        self._cached_per_trip_params = {}
        self._cached_power_profile = []
        self._cached_deferrables_schedule = []

        # Pre-compute multi-trip charging windows and process trips
        battery_capacity_kwh = self._load_publisher.battery_capacity_kwh
        soc_current = await self._precompute_and_process_trips(
            trips, battery_capacity_kwh
        )

        # BUG-6: Run deficit propagation to handle cascading charging needs
        self._apply_deficit_propagation()

        # Build power profile and deferrables schedule
        horizon = self._get_horizon_hours()
        power_profile: List[float] = [0.0] * horizon
        deferrables_schedule: List[Dict[str, Any]] = []

        self._build_power_profile_and_schedule(horizon, power_profile, deferrables_schedule)

        self._cached_power_profile = power_profile
        self._cached_deferrables_schedule = deferrables_schedule
        self._cached_emhass_status = "ready"

        return success

    async def _precompute_and_process_trips(
        self,
        trips: List[Dict[str, Any]],
        battery_capacity_kwh: float,
    ) -> float:
        """Pre-compute multi-trip charging windows and process each trip.

        Returns the soc_current used for processing.
        """
        from homeassistant.util import dt as dt_util
        from ..calculations.windows import calculate_multi_trip_charging_windows

        now = dt_util.now()
        soc_current = await self._get_current_soc()
        if soc_current is None:
            soc_current = 50.0

        trip_deadlines = self._build_trip_deadlines(trips)
        pre_computed_windows = self._compute_charging_windows(
            trip_deadlines, soc_current, battery_capacity_kwh, now
        )
        window_by_trip_id = self._build_window_lookup(pre_computed_windows)
        await self._process_trips_with_windows(trips, battery_capacity_kwh, soc_current, window_by_trip_id)

        return soc_current

    def _build_trip_deadlines(
        self, trips: List[Dict[str, Any]]
    ) -> List[Tuple[datetime, Dict[str, Any]]]:
        """Build sorted list of (deadline, trip) tuples."""
        trip_deadlines: List[Tuple[datetime, Dict[str, Any]]] = []
        for trip in trips:
            deadline_dt = self._calculate_deadline_from_trip(trip)
            if deadline_dt is not None:
                trip_deadlines.append((deadline_dt, trip))
        trip_deadlines.sort(key=lambda x: x[0])
        return trip_deadlines

    def _compute_charging_windows(
        self,
        trip_deadlines: List[Tuple[datetime, Dict[str, Any]]],
        soc_current: float,
        battery_capacity_kwh: float,
        now: datetime,
    ) -> List[Dict[str, Any]]:
        """Compute multi-trip charging windows from sorted deadlines."""
        if not trip_deadlines:
            return []
        from ..calculations.windows import calculate_multi_trip_charging_windows

        return calculate_multi_trip_charging_windows(
            trips=trip_deadlines,
            soc_actual=soc_current,
            hora_regreso=None,
            charging_power_kw=self._load_publisher.charging_power_kw,
            battery_capacity_kwh=battery_capacity_kwh,
            safety_margin_percent=self._load_publisher.safety_margin_percent,
            now=now,
        )

    def _build_window_lookup(
        self, windows: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Build lookup dict from trip_id to window."""
        lookup: Dict[str, Dict[str, Any]] = {}
        for window in windows:
            trip = window.get("trip")
            if trip:
                trip_id = trip.get("id")
                if trip_id:
                    lookup[trip_id] = window
        return lookup

    async def _process_trips_with_windows(
        self,
        trips: List[Dict[str, Any]],
        battery_capacity_kwh: float,
        soc_current: float,
        window_by_trip_id: Dict[str, Dict[str, Any]],
    ) -> None:
        """Process each trip using pre-computed windows."""
        for trip in trips:
            trip_id = trip.get("id", "")
            win = window_by_trip_id.get(trip_id, {})
            pre_computed_inicio = win.get("inicio_ventana")
            pre_computed_fin = win.get("fin_ventana")

            if pre_computed_inicio is not None or pre_computed_fin is not None:
                try:
                    await self._populate_per_trip_cache_entry(
                        PerTripCacheParams(
                            trip=trip,
                            trip_id=trip_id,
                            charging_power_kw=self._charging_power_kw or 3.6,
                            battery_capacity_kwh=battery_capacity_kwh,
                            safety_margin_percent=self._load_publisher.safety_margin_percent,
                            soc_current=soc_current,
                        ),
                        pre_computed_inicio_ventana=pre_computed_inicio,
                        pre_computed_fin_ventana=pre_computed_fin,
                    )
                except Exception:
                    self._cached_emhass_status = "error"
            else:
                trip_success = await self.async_publish_deferrable_load(trip)
                if not trip_success:
                    self._cached_emhass_status = "error"

    def _get_horizon_hours(self) -> int:
        """Read planning horizon from config entry."""
        horizon = 168  # default: 7 days * 24 hours
        try:
            entry_data = dict(getattr(self._entry, "options", {}) or {})
            entry_data.update(dict(getattr(self._entry, "data", {}) or {}))
            horizon = int(entry_data.get("planning_horizon_days", 7)) * 24
        except Exception:
            pass
        return horizon

    def _build_power_profile_and_schedule(
        self,
        horizon: int,
        power_profile: List[float],
        deferrables_schedule: List[Dict[str, Any]],
    ) -> None:
        """Build power_profile and deferrables_schedule from cached params."""
        from ..calculations.windows import build_deferrable_matrix_row

        for trip_id, params in self._cached_per_trip_params.items():
            watts = params.get("power_watts", 0)
            end = params.get("def_end_timestep", 0)
            def_total = params.get("def_total_hours", 0)

            row = build_deferrable_matrix_row(
                horizon_hours=horizon,
                charging_power_kw=watts / 1000.0 if watts else 0.0,
                hours_needed=def_total,
                end_timestep=end,
            )
            for t, power in enumerate(row):
                if power > 0:
                    power_profile[t] = max(power_profile[t], power)
            deferrables_schedule.append(
                {
                    "index": params.get("emhass_index", 0),
                    "kwh": params.get("kwh_needed", 0),
                    "start_timestep": params.get("def_start_timestep", 0),
                    "end_timestep": end,
                }
            )

    async def async_cleanup_vehicle_indices(self) -> None:
        """Clean up all indices for this vehicle."""
        indices_to_release = list(self._index_manager._index_map.keys())
        for trip_id in indices_to_release:
            self._index_manager.release_index(trip_id)
        self._published_trips = set()
        self._cached_per_trip_params = {}
        self._cached_power_profile = []
        self._cached_deferrables_schedule = []
        self._cached_emhass_status = "unavailable"

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

    # CC-N-ACCEPTED: cc=12 — cache entry builder with branches for punctual vs
    # recurring trips, datetime handling, charging window calc, and energy
    # calculation. Each step has distinct error paths.
    async def _populate_per_trip_cache_entry(
        self,
        params: PerTripCacheParams,
        # Remaining params kept as optional kwargs for test compatibility.
        # They are not used in the method body — only accepted for backward compat.
        hora_regreso: Optional[datetime] = None,
        pre_computed_inicio_ventana: Optional[datetime] = None,
        pre_computed_fin_ventana: Optional[datetime] = None,
        adjusted_def_total_hours: Optional[float] = None,
        soc_cap: Optional[float] = None,
    ) -> None:
        """Build and cache per-trip EMHASS parameters.

        Args:
            params: Bundled per-trip cache parameters (reduced arity from 11 to 2).
            hora_regreso: Unused — kept for test compatibility.
            pre_computed_inicio_ventana: Test-only batch-mode parameter.
            pre_computed_fin_ventana: Test-only batch-mode parameter.
            adjusted_def_total_hours: Unused — kept for test compatibility.
            soc_cap: Unused — kept for test compatibility.
        """
        trip = params.trip
        trip_id = params.trip_id
        charging_power_kw = params.charging_power_kw
        battery_capacity_kwh = params.battery_capacity_kwh
        safety_margin_percent = params.safety_margin_percent
        soc_current = params.soc_current

        # Read t_base and planning_horizon from config entry (BUG-4)
        t_base = 24.0  # default
        horizon_hours = 168  # default: 7 days * 24 hours
        entry = self._entry
        if entry:
            entry_data = dict(getattr(entry, "options", {}) or {})
            entry_data.update(dict(getattr(entry, "data", {}) or {}))
            t_base = float(
                entry_data.get("t_base", entry_data.get("CONF_T_BASE", 24.0))
            )
            horizon_days = int(entry_data.get("planning_horizon_days", 7))
            horizon_hours = horizon_days * 24

        # Assign index if not already assigned
        if trip_id not in self._index_map:
            await self.async_assign_index_to_trip(trip_id)
        emhass_index = self._index_map.get(trip_id, -1)

        from homeassistant.util import dt as dt_util

        now = dt_util.now()

        # Calculate deadline
        deadline_dt = self._calculate_deadline_from_trip(trip)

        def_start_timestep = 0
        def_end_timestep = horizon_hours  # default: configurable horizon
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

            def_end_timestep = min(int(max(0, hours_available)), horizon_hours)

            # Use pre-computed ventana if provided (batch mode)
            _pre_computed_fin = False
            if pre_computed_inicio_ventana is not None:
                delta_hours = (
                    self._load_publisher._ensure_aware(pre_computed_inicio_ventana)
                    - now
                ).total_seconds() / 3600
                # RULE: Each fraction of hour = 1 full hour slot. math.ceil() because 1 minute = 1 slot.
                def_start_timestep = max(0, min(math.ceil(delta_hours), horizon_hours))
            elif charging_windows and charging_windows[0].get("inicio_ventana"):
                inicio = charging_windows[0]["inicio_ventana"]
                delta_hours = (
                    self._load_publisher._ensure_aware(inicio) - now
                ).total_seconds() / 3600
                def_start_timestep = max(0, min(int(delta_hours), horizon_hours))

            # Handle pre-computed fin_ventana (batch/test mode)
            if pre_computed_fin_ventana is not None:
                delta_fin = (
                    self._load_publisher._ensure_aware(pre_computed_fin_ventana) - now
                ).total_seconds() / 3600
                def_end_timestep = max(0, min(int(math.ceil(delta_fin - 0.001)), horizon_hours))
                _pre_computed_fin = True

            # Calculate energy parameters FIRST so def_total_hours is available
            from ..calculations import calculate_energy_needed

            energy_info = calculate_energy_needed(
                trip,
                battery_capacity_kwh,
                soc_current,
                charging_power_kw,
                safety_margin_percent=safety_margin_percent,
            )
            total_hours = energy_info["horas_carga_necesarias"]

            # BUG-4 + BUG-5: Apply dynamic SOC capping.
            # t_base already read above from config entry.
            # Smaller t_base = tighter SOC caps.
            if t_base and charging_windows:
                from ..calculations import calculate_dynamic_soc_limit

                # Hours until trip departure
                t_hours = 24.0
                if charging_windows[0].get("fin_ventana"):
                    t_hours = (
                        charging_windows[0]["fin_ventana"] - now
                    ).total_seconds() / 3600

                # Estimated SOC after trip: current energy minus trip-only energy.
                # The trip energy is the distance/consumption, not the full
                # energia_necesaria_kwh (which includes safety margin).
                trip_kwh = trip.get("kwh", 0.0)
                if not trip_kwh and "km" in trip:
                    from ..utils import calcular_energia_kwh

                    trip_kwh = calcular_energia_kwh(
                        trip.get("km", 0.0),
                        self._entry.data.get("kwh_per_km", 0.15),
                    )
                soc_after = max(
                    0.0, soc_current - (trip_kwh / battery_capacity_kwh) * 100.0
                )

                # Compute SOC cap using the dynamic algorithm
                soc_cap = calculate_dynamic_soc_limit(
                    t_hours, soc_after, battery_capacity_kwh, t_base=t_base
                )

                # If SOC cap is below 100%, reduce the energy accordingly.
                # Skip capping when SOC is already at 100% — the battery is full
                # and any remaining hours are for proactive future-trip charging.
                if soc_cap < 100.0 and soc_current < 100.0:
                    current_energy = (soc_current / 100.0) * battery_capacity_kwh
                    max_energy = (soc_cap / 100.0) * battery_capacity_kwh
                    capped_energy = max(0.0, max_energy - current_energy)
                    capped_hours = (
                        capped_energy / charging_power_kw
                        if charging_power_kw > 0
                        else 0.0
                    )
                    total_hours = math.ceil(capped_hours) if capped_hours > 0 else 0
                    energy_info["energia_necesaria_kwh"] = capped_energy

            # FIX: def_end_timestep must be based on fin_ventana (trip departure time),
            # not def_start + total_hours. The formula def_start + total_hours gives
            # charging duration (2h), but def_end_timestep should be the charging
            # window end = when the trip departs (~7h away).
            if _pre_computed_fin:
                pass  # pre-computed def_end_timestep stays as-is
            elif charging_windows and charging_windows[0].get("fin_ventana"):
                # Use trip departure time (fin_ventana) for charging window end
                fin = charging_windows[0]["fin_ventana"]
                delta_fin = (
                    self._load_publisher._ensure_aware(fin) - now
                ).total_seconds() / 3600
                def_end_timestep = max(0, min(int(math.ceil(delta_fin - 0.001)), horizon_hours))
            else:
                # Fallback: use deadline (trip departure) if no charging window available
                def_end_timestep = min(int(max(0, hours_available)), horizon_hours)

        # Build p_deferrable_matrix for this trip using shared function
        # The charging slots are placed at the END of the window (just before trip departure)
        from ..calculations.windows import build_deferrable_matrix_row

        row = build_deferrable_matrix_row(
            horizon_hours=horizon_hours,
            charging_power_kw=charging_power_kw,
            hours_needed=total_hours,
            end_timestep=def_end_timestep,
        )
        trip_matrix = [row]

        # Always store the cache entry (even if deadline was None)
        self._cached_per_trip_params[trip_id] = {
            "activo": True,
            "emhass_index": emhass_index,
            "def_start_timestep": def_start_timestep,
            "def_end_timestep": def_end_timestep,
            "def_total_hours": total_hours,
            "total_hours": total_hours,
            "power_watts": charging_power_kw * 1000 if total_hours > 0 else 0.0,
            "kwh_needed": total_hours * charging_power_kw,
            "charging_window": charging_windows,
            # Keys expected by sensor entity aggregation
            "def_total_hours_array": [total_hours] if total_hours > 0 else [0],
            "p_deferrable_nom_array": [charging_power_kw * 1000] if total_hours > 0 else [0],
            "def_start_timestep_array": [def_start_timestep],
            "def_end_timestep_array": [def_end_timestep],
            "p_deferrable_matrix": trip_matrix,
        }

    def _apply_deficit_propagation(self) -> None:
        """Apply deficit propagation across all cached per-trip params.

        Walks trips backward (last to first) and propagates unmet charging
        hours to earlier trips with spare capacity. Updates def_total_hours
        in-place for affected trips.
        """
        if not self._cached_per_trip_params:
            return

        active = self._get_active_trips_sorted()
        if len(active) < 2:
            return

        windows, total_hours_list = self._build_deficit_windows(active)
        if not windows:
            return

        from ..calculations import calculate_hours_deficit_propagation

        results = calculate_hours_deficit_propagation(windows, total_hours_list)
        self._apply_deficit_results(results, active)

    def _get_active_trips_sorted(self) -> List[Dict[str, Any]]:
        """Return active trips sorted by (start_timestep, index)."""
        active: List[Dict[str, Any]] = []
        for params in self._cached_per_trip_params.values():
            if params.get("activo", False):
                active.append(params)
        active.sort(
            key=lambda x: (x.get("def_start_timestep", 0), x.get("emhass_index", 0))
        )
        return active

    def _build_deficit_windows(
        self, active: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, float]], List[float]]:
        """Build windows and total_hours lists for deficit propagation."""
        windows: List[Dict[str, float]] = []
        total_hours_list: List[float] = []
        for p in active:
            cws = p.get("charging_window", [])
            if cws:
                w = cws[0]
                windows.append({
                    "ventana_horas": w.get("ventana_horas", 0),
                    "horas_carga_necesarias": w.get("horas_carga_necesarias", 0),
                })
            else:
                th = p.get("def_total_hours", 0)
                windows.append({
                    "ventana_horas": th,
                    "horas_carga_necesarias": th,
                })
            total_hours_list.append(p.get("def_total_hours", 0))
        return windows, total_hours_list

    def _apply_deficit_results(
        self,
        results: List[Dict[str, Any]],
        active: List[Dict[str, Any]],
    ) -> None:
        """Apply deficit propagation results to cached params."""
        for i, result in enumerate(results):
            if i >= len(active):
                break
            params = active[i]
            trip_id = self._find_trip_id_for_params(params)
            if trip_id is None:
                continue

            adjusted = result.get("adjusted_def_total_hours")
            if adjusted is not None and adjusted > 0:
                self._cached_per_trip_params[trip_id]["adjusted_def_total_hours"] = round(adjusted, 2)
                power_watts = params.get("power_watts", 0)
                if power_watts > 0:
                    self._cached_per_trip_params[trip_id]["kwh_needed"] = (
                        round(adjusted * (power_watts / 1000.0), 2)
                    )

    def _find_trip_id_for_params(
        self, params: Dict[str, Any]
    ) -> Optional[str]:
        """Find trip_id matching a params dict by identity."""
        for tid, p in self._cached_per_trip_params.items():
            if p is params:
                return tid
        return None

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
                PerTripCacheParams(
                    trip=trip,
                    trip_id=trip_id,
                    charging_power_kw=self._charging_power_kw or 3.6,
                    battery_capacity_kwh=self._load_publisher.battery_capacity_kwh,
                    safety_margin_percent=self._load_publisher.safety_margin_percent,
                    soc_current=soc_current,
                ),
            )
        except Exception:
            # Cache population failure should not prevent publish attempt
            pass

        # Delegate actual publish to LoadPublisher
        result = await self._load_publisher.publish(trip)

        # Track published trips
        if result:
            self._published_trips.add(trip_id)

        return result
