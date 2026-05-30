"""EMHASS adapter — facade delegating to sub-components."""

from __future__ import annotations

import logging  # pragma: no mutate  # EQ-085
import math
import operator
from contextlib import suppress
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

from .. import const
from ..calculations import _helpers
from .error_handler import ErrorHandler
from .index_manager import IndexManager
from .load_publisher import LoadPublisher, LoadPublisherConfig

_LOGGER = logging.getLogger(__name__)

# ── Log format string constants (US-5 testability) ──────────────────────
_LOG_DEBUG_FLOW2_GET_CURRENT_SOC = "FLOW2-DEBUG: _get_current_soc called"


# qg-accepted: BMAD consensus 2026-05-12 — ACCEPTED AS ORCHESTRATOR (not facade):
#   80% business logic (SOC fetching, charging windows, deficit propagation,
#   power profiles). High LOC justified as central EMHASS orchestration layer
#   composing IndexManager, LoadPublisher, ErrorHandler.


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
        # qg-accepted: complexity=11 is inherent to EMHASS adapter init with HA deps
        """Initialize the EMHASS adapter facade.

        Args:
            hass: HomeAssistant instance.
            entry: ConfigEntry for the integration.
        """
        self.hass = hass
        self._entry = entry
        self.vehicle_id = entry.entry_id if hasattr(entry, "entry_id") else "unknown"
        self.entry_id = getattr(entry, "entry_id", "unknown")

        # Read vehicle config from entry data.
        # NO silent defaults — these are required vehicle values.
        # Validation happens at init; missing values raise ValueError.
        battery_capacity_kwh = None
        charging_power_kw = None
        safety_margin_percent = None
        if entry:
            entry_data = dict(getattr(entry, "options", {}) or {})
            raw_data = getattr(entry, "data", None) or {}
            entry_data.update(dict(raw_data))
            # Handle legacy tests that pass a dict directly as entry
            if isinstance(entry, dict):
                entry_data.update(entry)
            battery_capacity_kwh = entry_data.get("battery_capacity_kwh")
            charging_power_kw = entry_data.get("charging_power_kw")
            safety_margin_percent = entry_data.get("safety_margin_percent")

        if battery_capacity_kwh is None:
            raise ValueError(
                f"Config entry missing required 'battery_capacity_kwh' "
                f"for vehicle {self.vehicle_id}. Provide a valid battery capacity."
            )
        if charging_power_kw is None:
            raise ValueError(
                f"Config entry missing required 'charging_power_kw' "
                f"for vehicle {self.vehicle_id}. Provide a valid charging power."
            )
        if safety_margin_percent is None:
            raise ValueError(
                f"Config entry missing required 'safety_margin_percent' "
                f"for vehicle {self.vehicle_id}. Provide a valid safety margin."
            )

        battery_capacity_kwh = float(battery_capacity_kwh)
        charging_power_kw = float(charging_power_kw)
        safety_margin_percent = float(safety_margin_percent)

        # Sub-component initialization
        self._index_manager = IndexManager()
        soc_sensor = None
        soh_sensor = None
        if self._entry:
            entry_data = dict(getattr(self._entry, "options", {}) or {})
            entry_data.update(dict(getattr(self._entry, "data", {}) or {}))
            soc_sensor = entry_data.get("soc_sensor")
            soh_sensor = entry_data.get("soh_sensor") or None
        self._load_publisher = LoadPublisher(
            hass=hass,
            vehicle_id=self.vehicle_id,  # pragma: no mutate  # EQ-087
            config=LoadPublisherConfig(
                index_manager=self._index_manager,
                battery_capacity_kwh=battery_capacity_kwh,
                charging_power_kw=charging_power_kw,
                safety_margin_percent=safety_margin_percent,
                soc_sensor=soc_sensor,
                soh_sensor=soh_sensor,
            ),
        )
        self._error_handler = ErrorHandler(hass=hass)

        # Store the read values for later use
        self._stored_charging_power_kw = charging_power_kw
        self._default_consumption = (
            const.DEFAULT_CONSUMPTION
        )  # kWh/km, fallback when kwh_per_km missing

        # State attributes (used by callers and tests)
        self._published_trips: set[str] = set()
        self._cached_per_trip_params: Dict[str, Any] = {}
        self._cached_power_profile: List[Any] | None = None
        self._cached_deferrables_schedule: List[Any] | None = None
        self._cached_emhass_status: str | None = None
        self._config_entry_listener = None
        self._shutting_down = False
        self._charging_power_kw: float | None = None
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

    async def async_assign_index_to_trip(self, trip_id: str) -> Optional[int]:
        """Assign an index to a trip."""
        try:
            return self._index_manager.assign_index(trip_id)
        except Exception as err:
            self._error_handler.handle_error("assign_index", err, {"trip_id": trip_id})
            return None

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

    def get_available_indices(
        self,
    ) -> List[int]:
        """Get list of available indices."""
        if not self._index_manager._index_map:
            return [0]
        max_idx = max(self._index_manager._index_map.values())
        return list(range(max_idx + 1))

    def get_cached_optimization_results(self) -> Dict[str, Any]:
        """Return cached optimization results for coordinator retrieval.

        Returns:
            Dict with emhass_power_profile, emhass_deferrables_schedule,
            emhass_status, and per_trip_emhass_params keys.
        """
        return {
            "emhass_power_profile": self._cached_power_profile,
            "emhass_deferrables_schedule": self._cached_deferrables_schedule,  # pragma: no mutate  # EQ-086
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

        # Pre-compute multi-trip charging windows and process trips.
        # Use SOH-adjusted real capacity so battery degradation affects the plan.
        battery_capacity_kwh = self._load_publisher.get_real_capacity_kwh()
        soc_current = await self._precompute_and_process_trips(
            trips, battery_capacity_kwh
        )

        # Run window pipeline: SOC cap (health) then deficit propagation (factibilidad)
        self._run_window_pipeline(soc_current)

        # Build power profile and deferrables schedule
        horizon = self._get_horizon_hours()
        power_profile: List[float] = [0.0] * horizon
        deferrables_schedule: List[Dict[str, Any]] = []

        self._build_power_profile_and_schedule(
            horizon, power_profile, deferrables_schedule
        )

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

        now = dt_util.now()
        soc_current = await self._get_current_soc()
        # If SOC sensor is not yet available (e.g., during initial setup),
        # fall back to 50.0 so the publish pipeline can still compute real
        # per-trip params.  This matches the previous production behavior.
        if soc_current is None:
            _LOGGER.info(
                "SOC sensor unavailable — using default 50.0 for trip window "
                "computation. Ensure '%s' returns a numeric value.",
                self._entry.data.get("soc_sensor", "unknown")
                if self._entry
                else "unknown",
            )
            # qg-accepted: AP05 — default SOC fallback
            soc_current = 50.0

        trip_deadlines = self._build_trip_deadlines(trips)
        pre_computed_windows = self._compute_charging_windows(
            trip_deadlines, soc_current, battery_capacity_kwh, now
        )

        window_by_trip_id = self._build_window_lookup(pre_computed_windows)
        await self._process_trips_with_windows(
            trips, battery_capacity_kwh, soc_current, window_by_trip_id
        )

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
        trip_deadlines.sort(key=operator.itemgetter(0))
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
        from ..calculations.windows import (
            MultiTripChargingParams,
            calculate_multi_trip_charging_windows,
        )

        return calculate_multi_trip_charging_windows(
            trips=trip_deadlines,
            params=MultiTripChargingParams(
                soc_actual=soc_current,
                hora_regreso=None,
                charging_power_kw=self._load_publisher.charging_power_kw,
                battery_capacity_kwh=battery_capacity_kwh,
                safety_margin_percent=self._load_publisher.safety_margin_percent,
                now=now,
            ),
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
                # Pass the full pre-computed charging window so batch mode
                # doesn't recalculate independently (which loses multi-trip context).
                pre_computed_charging_window = [win] if win else []
                try:
                    await self._populate_per_trip_cache_entry(
                        PerTripCacheParams(
                            trip=trip,
                            trip_id=trip_id,
                            charging_power_kw=self._load_publisher.charging_power_kw,
                            battery_capacity_kwh=battery_capacity_kwh,
                            safety_margin_percent=self._load_publisher.safety_margin_percent,
                            soc_current=soc_current,
                        ),
                        pre_computed_inicio_ventana=pre_computed_inicio,
                        pre_computed_fin_ventana=pre_computed_fin,
                        pre_computed_charging_window=pre_computed_charging_window,
                    )
                except Exception:
                    self._cached_emhass_status = "error"
            else:
                trip_success = await self.async_publish_deferrable_load(trip)
                if not trip_success:
                    self._cached_emhass_status = "error"

    def _get_horizon_hours(self) -> int:
        """Read planning horizon from config entry."""
        # qg-accepted: AP05 — hours-per-day conversion
        horizon = const.DEFAULT_PLANNING_HORIZON * 24
        with suppress(Exception):
            entry_data = dict(getattr(self._entry, "options", {}) or {})
            entry_data.update(dict(getattr(self._entry, "data", {}) or {}))
            # qg-accepted: AP05 — default planning horizon days + hours-per-day
            horizon = int(entry_data.get("planning_horizon_days", 7)) * 24
        return horizon

    def _build_power_profile_and_schedule(
        self,
        horizon: int,
        power_profile: List[float],
        deferrables_schedule: List[Dict[str, Any]],
    ) -> None:
        """Build power_profile and deferrables_schedule from cached params."""
        from ..calculations.windows import build_deferrable_matrix_row

        for params in self._cached_per_trip_params.values():
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

    # ------------------------------------------------------------------
    # Backward-compat methods for test compatibility (SOLID refactor)
    # ------------------------------------------------------------------

    # qg-accepted: complexity=13 is inherent to SOC fetching with error handling
    async def _get_current_soc(self) -> Optional[float]:
        """Get current SOC from configured sensor.

        Returns:
            SOC percentage as float, or None if sensor unavailable.
        """
        # Read soc_sensor from ConfigEntry
        soc_sensor = None
        _LOGGER.warning(_LOG_DEBUG_FLOW2_GET_CURRENT_SOC)
        if self._entry:
            entry_data = dict(getattr(self._entry, "options", {}) or {})
            entry_data.update(dict(getattr(self._entry, "data", {}) or {}))
            soc_sensor = entry_data.get("soc_sensor")
        _LOGGER.warning(
            "FLOW2-DEBUG: _get_current_soc resolved sensor=%s entry=%s",
            soc_sensor,
            self._entry is not None,
        )
        if not soc_sensor:
            _LOGGER.warning(
                "FLOW2-DEBUG: _get_current_soc NO_SENSOR sensor=%s",
                soc_sensor,
            )
            return None
        state = self.hass.states.get(soc_sensor)
        _LOGGER.warning(
            "FLOW2-DEBUG: _get_current_soc states.get=%s for sensor=%s",
            state is not None,
            soc_sensor,
        )
        if state is None:
            _LOGGER.warning(
                "FLOW2-DEBUG: _get_current_soc STATE_NONE sensor=%s",
                soc_sensor,
            )
            return None
        try:
            result = float(state.state)
            _LOGGER.warning(
                "FLOW2-DEBUG: _get_current_soc SUCCESS sensor=%s state=%s soc=%s",
                soc_sensor,
                state.state,
                result,
            )
            return result
        except (ValueError, TypeError):
            _LOGGER.warning(
                "FLOW2-DEBUG: _get_current_soc PARSE_FAIL sensor=%s state=%s",
                soc_sensor,
                state.state,
            )
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
        pre_computed_inicio_ventana: Optional[datetime] = None,
        pre_computed_fin_ventana: Optional[datetime] = None,
        pre_computed_charging_window: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Build and cache per-trip EMHASS parameters.

        Args:
            params: Bundled per-trip cache parameters (reduced arity from 11 to 2).
            pre_computed_inicio_ventana: Test-only batch-mode parameter.
            pre_computed_fin_ventana: Test-only batch-mode parameter.
            pre_computed_charging_window: Test-only batch-mode parameter.
        """
        trip = params.trip
        trip_id = params.trip_id
        charging_power_kw = params.charging_power_kw
        battery_capacity_kwh = params.battery_capacity_kwh
        safety_margin_percent = params.safety_margin_percent
        soc_current = params.soc_current

        # Read planning_horizon from config entry
        # qg-accepted: AP05 — hours-per-day for horizon
        horizon_hours = const.DEFAULT_PLANNING_HORIZON * 24  # default: 7 days
        entry = self._entry
        if entry:
            entry_data = dict(getattr(entry, "options", {}) or {})
            entry_data.update(dict(getattr(entry, "data", {}) or {}))
            # qg-accepted: AP05 — default planning horizon days
            horizon_days = int(entry_data.get("planning_horizon_days", 7))
            # qg-accepted: AP05 — hours-per-day conversion
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
            # qg-accepted: AP05 — seconds-to-hours conversion
            hours_available = (deadline_dt - now).total_seconds() / 3600

            # Calculate charging windows
            if pre_computed_charging_window:
                # Batch mode: use pre-computed windows that have multi-trip context.
                charging_windows = pre_computed_charging_window
            else:
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
                    (
                        self._load_publisher._ensure_aware(pre_computed_inicio_ventana)
                        - now
                    ).total_seconds()
                    / 3600
                )  # qg-accepted: AP05 — seconds-to-hours conversion
                # RULE: Each fraction of hour = 1 full hour slot. math.ceil() because 1 minute = 1 slot.
                def_start_timestep = max(0, min(math.ceil(delta_hours), horizon_hours))
            elif charging_windows and charging_windows[0].get("inicio_ventana"):
                inicio = charging_windows[0]["inicio_ventana"]
                delta_hours = (
                    (self._load_publisher._ensure_aware(inicio) - now).total_seconds()
                    / 3600
                )  # qg-accepted: AP05 — seconds-to-hours conversion
                def_start_timestep = max(0, min(int(delta_hours), horizon_hours))

            # Handle pre-computed fin_ventana (batch/test mode)
            if pre_computed_fin_ventana is not None:
                delta_fin = (
                    (
                        self._load_publisher._ensure_aware(pre_computed_fin_ventana)
                        - now
                    ).total_seconds()
                    / 3600
                )  # qg-accepted: AP05 — seconds-to-hours conversion
                def_end_timestep = max(
                    0, min(int(math.ceil(delta_fin - 0.001)), horizon_hours)
                )
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

            # FIX: def_end_timestep must be based on fin_ventana (trip departure time),
            # not def_start + total_hours. The formula def_start + total_hours gives
            # charging duration (2h), but def_end_timestep should be the charging
            # window end = when the trip departs (~7h away).
            if _pre_computed_fin:
                pass  # pre-computed def_end_timestep stays as-is
            elif charging_windows and charging_windows[0].get("fin_ventana"):
                # Use trip departure time (fin_ventana) for charging window end
                fin = charging_windows[0]["fin_ventana"]
                # qg-accepted: AP05 — seconds-to-hours conversion
                delta_fin = (
                    self._load_publisher._ensure_aware(fin) - now
                ).total_seconds() / 3600
                def_end_timestep = max(
                    0, min(int(math.ceil(delta_fin - 0.001)), horizon_hours)
                )
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
        # Single source of truth: scalar fields only. Sensor derives arrays
        # from scalars on-demand in _collect_arrays (entity_emhass_deferrable).
        self._cached_per_trip_params[trip_id] = {
            "activo": True,
            "emhass_index": emhass_index,
            "def_start_timestep": def_start_timestep,
            "def_end_timestep": def_end_timestep,
            "def_total_hours": total_hours,
            "total_hours": total_hours,
            "power_watts": _helpers.kw_to_watts(charging_power_kw)
            if total_hours > 0
            else 0.0,
            "kwh_needed": total_hours * charging_power_kw,
            "charging_window": charging_windows,
            "p_deferrable_matrix": trip_matrix,
        }

    def _get_t_base(self) -> float:
        """Read t_base from config entry with fallback to default.

        options takes precedence over data (options = user-editable via options flow).
        """
        if not self._entry:
            return const.DEFAULT_T_BASE
        entry_data = dict(getattr(self._entry, "data", {}) or {})
        entry_data.update(dict(getattr(self._entry, "options", {}) or {}))
        return float(entry_data.get("t_base", const.DEFAULT_T_BASE))

    def _run_window_pipeline(self, soc_current: float = 50.0) -> None:
        """Execute the window transformation pipeline across all active trips.

        Applies SOC cap (health, Componentes 1+2) then deficit propagation
        (factibilidad) in order. Updates def_total_hours, kwh_needed, and
        p_deferrable_matrix in cache.
        """
        if not self._cached_per_trip_params:
            return

        active = self._get_active_trips_sorted()
        if not active:
            return

        windows, trip_ids = self._build_pipeline_windows(active)
        if not windows:
            return

        from homeassistant.util import dt as dt_util

        from ..calculations.window_pipeline import PipelineContext, run_window_pipeline

        battery_capacity_kwh = self._load_publisher.get_real_capacity_kwh()
        charging_power_kw = self._load_publisher.charging_power_kw
        context = PipelineContext(
            charging_power_kw=charging_power_kw,
            battery_capacity_kwh=battery_capacity_kwh,
            t_base=self._get_t_base(),
            now=dt_util.now(),
            soc_current=soc_current,
        )
        results = run_window_pipeline(windows, context)
        self._apply_pipeline_results(results, active, trip_ids)

    def _get_active_trips_sorted(self) -> List[Dict[str, Any]]:
        """Return active trips sorted by (start_timestep, index)."""
        active: List[Dict[str, Any]] = [
            params
            for params in self._cached_per_trip_params.values()
            if params.get("activo", False)
        ]
        active.sort(
            key=lambda x: (x.get("def_start_timestep", 0), x.get("emhass_index", 0))
        )
        return active

    def _build_pipeline_windows(  # pragma: no mutate  # EQ-084
        self, active: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """Build window dicts and aligned trip_ids for the pipeline.

        Includes all charging_window fields (ventana_horas, horas_carga_necesarias,
        fin_ventana, trip, etc.) so pipeline transforms can access trip context.
        """
        windows: List[Dict[str, Any]] = []
        trip_ids: List[str] = []
        for p in active:
            cws = p.get("charging_window", [])
            if cws:
                windows.append(cws[0].copy())
            else:
                th = p.get("def_total_hours", 0)
                windows.append({"ventana_horas": th, "horas_carga_necesarias": th})
            trip_id = self._find_trip_id_for_params(p)
            trip_ids.append(trip_id or "")
        return windows, trip_ids

    def _apply_pipeline_results(
        self,
        results: List[Dict[str, Any]],
        active: List[Dict[str, Any]],
        trip_ids: Optional[List[str]] = None,
    ) -> None:
        """Apply pipeline results to cached params.

        Results are in the same order as the input windows / active lists.
        trip_ids, if provided, are used directly; otherwise identity lookup is used.
        """
        for i, result in enumerate(results):
            if trip_ids is not None:
                trip_id = trip_ids[i] if i < len(trip_ids) else None
            else:
                params = active[i] if i < len(active) else {}
                trip_id = self._find_trip_id_for_params(params)

            if not trip_id:
                continue

            adjusted = result.get("adjusted_def_total_hours")
            if adjusted is None:
                continue

            params = active[i] if i < len(active) else {}
            self._cached_per_trip_params[trip_id]["def_total_hours"] = math.ceil(
                adjusted
            )
            power_watts = params.get("power_watts", 0)
            if power_watts > 0:
                self._cached_per_trip_params[trip_id]["kwh_needed"] = round(
                    adjusted * (power_watts / 1000.0), 2
                )

            # Recalculate p_deferrable_matrix so the matrix stays consistent
            # with the updated def_total_hours after cap + deficit.
            horizon = self._get_horizon_hours()
            from ..calculations.windows import build_deferrable_matrix_row

            new_def_total = math.ceil(adjusted)
            end_timestep = self._cached_per_trip_params[trip_id].get(
                "def_end_timestep", 0
            )
            new_row = build_deferrable_matrix_row(
                horizon_hours=horizon,
                charging_power_kw=power_watts / 1000.0 if power_watts else 0.0,
                hours_needed=new_def_total,
                end_timestep=end_timestep,
            )
            self._cached_per_trip_params[trip_id]["p_deferrable_matrix"] = [new_row]

    def _find_trip_id_for_params(self, params: Dict[str, Any]) -> Optional[str]:
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
        with suppress(Exception):
            soc_current = await self._get_current_soc()
            if soc_current is None:
                _LOGGER.error(
                    "SOC sensor unavailable — cannot publish deferrable load for trip '%s'",
                    trip_id,
                )
                return False
            await self._populate_per_trip_cache_entry(
                PerTripCacheParams(
                    trip=trip,
                    trip_id=trip_id,
                    charging_power_kw=self._load_publisher.charging_power_kw,
                    battery_capacity_kwh=self._load_publisher.get_real_capacity_kwh(),
                    safety_margin_percent=self._load_publisher.safety_margin_percent,
                    soc_current=soc_current,
                ),
            )

        # Delegate actual publish to LoadPublisher
        result = await self._load_publisher.publish(trip)

        # Track published trips
        if result:
            self._published_trips.add(trip_id)

        return result
