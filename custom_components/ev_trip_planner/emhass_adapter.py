"""EMHASS Adapter for EV Trip Planner."""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .calculations import (
    BatteryCapacity,
    calculate_deferrable_parameters as calc_deferrable_parameters,
    calculate_dynamic_soc_limit,
    calculate_hours_deficit_propagation,
    calculate_multi_trip_charging_windows,
    DEFAULT_T_BASE,
    determine_charging_need,
)
from .calculations import (
    calculate_power_profile_from_trips,
    calculate_trip_time,
    generate_deferrable_schedule_from_trips,
)
from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_INDEX_COOLDOWN_HOURS,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_NOTIFICATION_SERVICE,
    CONF_SOH_SENSOR,
    CONF_T_BASE,
    CONF_VEHICLE_NAME,
    DEFAULT_INDEX_COOLDOWN_HOURS,
    DEFAULT_SAFETY_MARGIN,
    DEFAULT_SOH_SENSOR,
    DEFAULT_T_BASE,
    DOMAIN,
    EMHASS_STATE_ACTIVE,
    EMHASS_STATE_ERROR,
    EMHASS_STATE_READY,
    RETURN_BUFFER_HOURS,
    TRIP_TYPE_RECURRING,
)

DATA_RUNTIME = f"{DOMAIN}_runtime_data"

_LOGGER = logging.getLogger(__name__)


def _ensure_aware(dt: datetime) -> datetime:
    """Convert naive datetime to aware (UTC) if needed."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class EMHASSAdapter:
    """Adapter to publish trips as EMHASS deferrable loads."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize adapter."""
        self.hass = hass
        # Always store entry (for _get_current_soc access to soc_sensor)
        self._entry = entry

        # Handle both dict (backward compatibility for tests) and ConfigEntry
        if isinstance(entry, dict):
            self.entry_id = entry.get("vehicle_name", "unknown")
            self._entry_dict: Any = entry  # Keep dict for _get_current_soc
            entry_data: Any = entry
        elif hasattr(entry, "data"):
            # ConfigEntry or MockConfigEntry with data attribute
            self.entry_id = entry.entry_id
            self._entry_dict = entry.data  # Keep dict for _get_current_soc
            entry_data = entry.data
        else:
            # Fallback - this path handles edge cases where entry is neither a dict nor has .data attribute
            self.entry_id = getattr(entry, "entry_id", "unknown")
            entry_data = entry

        self.vehicle_id = entry_data.get(CONF_VEHICLE_NAME)
        self.max_deferrable_loads = entry_data.get(CONF_MAX_DEFERRABLE_LOADS, 50)

        # Notification configuration
        self.notification_service = entry_data.get(CONF_NOTIFICATION_SERVICE)

        # Storage for trip_id → emhass_index mapping
        store_key = f"ev_trip_planner_{self.vehicle_id}_emhass_indices"
        self._store: Store[Dict[str, Any]] = Store(hass, version=1, key=store_key)
        self._index_map: Dict[str, int] = {}  # trip_id → emhass_index
        self._available_indices: List[int] = list(range(self.max_deferrable_loads))

        # Soft delete: released indices with timestamp for cooldown
        self._released_indices: Dict[int, datetime] = {}
        self._index_cooldown_hours: int = entry_data.get(
            CONF_INDEX_COOLDOWN_HOURS, DEFAULT_INDEX_COOLDOWN_HOURS
        )

        # Error tracking
        self._last_error: Optional[str] = None
        self._last_error_time: Optional[datetime] = None

        # Entity tracking for cleanup (FR-1, AC-1.4)
        self._published_entity_ids: Set[str] = set()

        # FR-3.1: Cache per-trip EMHASS params for coordinator retrieval
        # Initialized here (not lazily) to prevent stale entries bug
        self._cached_per_trip_params: Dict[str, Any] = {}

        # FR-3.1: Store last published trips for reactive republish when charging power changes
        self._published_trips: List[Dict[str, Any]] = []

        # FR-3.1: Config entry listener handle for cleanup
        self._config_entry_listener: Optional[Callable[[], None]] = None

        # Shutdown flag to prevent re-publishing during deletion
        # Set to True at start of cleanup to block update/republish callbacks
        self._shutting_down = False

        # FR-3.1: Store charging power for reactive updates
        self._charging_power_kw: float = entry_data.get(CONF_CHARGING_POWER, 3.6)
        self._battery_capacity_kwh: float = entry_data.get(CONF_BATTERY_CAPACITY, 50.0)
        self._safety_margin_percent: float = entry_data.get("safety_margin_percent", DEFAULT_SAFETY_MARGIN)

        # T064: Store baseline config values for change detection
        self._stored_charging_power_kw: float = entry_data.get(CONF_CHARGING_POWER, 3.6)
        self._stored_t_base: float = entry_data.get(CONF_T_BASE, DEFAULT_T_BASE)
        self._stored_soh_sensor: Optional[str] = entry_data.get(CONF_SOH_SENSOR) or None

        # T059/T062: Battery health config — t_base and SOH sensor for real capacity
        self._t_base: float = entry_data.get(CONF_T_BASE, DEFAULT_T_BASE)
        soh_sensor_entity_id: Optional[str] = entry_data.get(CONF_SOH_SENSOR) or None
        self._battery_cap = BatteryCapacity(
            nominal_capacity_kwh=self._battery_capacity_kwh,
            soh_sensor_entity_id=soh_sensor_entity_id,
        )

        # Presence monitor helper for _get_hora_regreso
        # Note: EMHASSAdapter doesn't have its own presence_monitor
        # It should get this from trip_manager or vehicle_controller
        self._presence_monitor = None

        # FR-3.1: Cached values initialized here to prevent W0201 (attribute-defined-outside-init)
        self._cached_power_profile: Optional[List[float]] = None
        self._cached_deferrables_schedule: Optional[List[Any]] = None
        self._cached_emhass_status: Optional[str] = None
        self.config_entry: Optional[Any] = None

        _LOGGER.debug(
            "Created EMHASSAdapter for %s, %d indices, "
            "notification_service=%s, charging_power_kw=%.2f",
            self.vehicle_id,
            len(self._available_indices),
            self.notification_service,
            self._charging_power_kw,
        )

    async def async_load(self):
        """Load index mapping and released indices from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self._index_map = data.get("index_map", {})

                # Restore released indices and recalculate which are still in cooldown
                self._released_indices = {}
                stored_released = data.get("released_indices", {})
                now = datetime.now(timezone.utc)
                for idx_str, released_iso in stored_released.items():
                    idx = int(idx_str)
                    try:
                        released_time = _ensure_aware(datetime.fromisoformat(released_iso))
                        elapsed = (now - released_time).total_seconds()
                        if elapsed < self._index_cooldown_hours * 3600:
                            # Still in cooldown
                            self._released_indices[idx] = released_time
                        # else: expired, don't restore
                    except (ValueError, TypeError):
                        pass

                # Rebuild available indices (exclude used and released in cooldown)
                used_indices = set(self._index_map.values())
                released_in_cooldown = set(self._released_indices.keys())
                self._available_indices = [
                    i
                    for i in range(self.max_deferrable_loads)
                    if i not in used_indices and i not in released_in_cooldown
                ]
                _LOGGER.info(
                    "Loaded %d trip-index mappings for %s, "
                    "%d indices available, %d in cooldown",
                    len(self._index_map),
                    self.vehicle_id,
                    len(self._available_indices),
                    len(self._released_indices),
                )
        except Exception as err:
            _LOGGER.error("Failed to load index mapping from storage: %s", err)
            await self.async_notify_error(
                error_type="storage_error",
                message=f"Failed to load data: {err}",
            )

    def _get_coordinator(self) -> Optional[Any]:
        """Get the TripPlannerCoordinator for this vehicle.

        PHASE 4 (4.3): Use entry.runtime_data instead of hass.data[DATA_RUNTIME].

        Returns:
            The coordinator if found, None otherwise.
        """
        # PHASE 4: Use entry.runtime_data (HA-recommended pattern)
        if self._entry is not None and hasattr(self._entry, "runtime_data"):
            coordinator = getattr(self._entry.runtime_data, "coordinator", None)
            if coordinator is not None:
                return coordinator
        # Fallback for test compatibility (when entry is a dict)
        namespace = f"{DOMAIN}_{self.entry_id}"
        runtime_data = self.hass.data.get(DATA_RUNTIME, {})
        coordinators = runtime_data.get(namespace, {}).get("coordinators", {})
        return coordinators.get(self.vehicle_id)

    def get_cached_optimization_results(self) -> Dict[str, Any]:
        """Return cached optimization results for coordinator retrieval.

        PHASE 3 (3.4): This method exposes computed EMHASS data to the
        TripPlannerCoordinator so it can populate coordinator.data.

        Returns:
            Dict with emhass_power_profile, emhass_deferrables_schedule,
            emhass_status, and per_trip_emhass_params keys.
        """
        cached_params = getattr(self, "_cached_per_trip_params", {})
        shutting_down = getattr(self, "_shutting_down", False)
        _LOGGER.warning(
            "DEBUG get_cached_optimization_results: _shutting_down=%s, vehicle_id=%s, "
            "returning per_trip_emhass_params with %d entries: %s",
            shutting_down,
            getattr(self, "vehicle_id", "unknown"),
            len(cached_params),
            list(cached_params.keys())[:5] if cached_params else [],
        )
        return {
            "emhass_power_profile": getattr(self, "_cached_power_profile", None),
            "emhass_deferrables_schedule": getattr(
                self, "_cached_deferrables_schedule", None
            ),
            "emhass_status": getattr(self, "_cached_emhass_status", None),
            "per_trip_emhass_params": cached_params,
        }

    async def async_save(self):
        """Save index mapping and released indices to storage."""
        try:
            # Serialize released_indices as {index_str: iso_timestamp}
            released_to_save = {
                str(idx): released_time.isoformat()
                for idx, released_time in self._released_indices.items()
            }
            await self._store.async_save(
                {
                    "index_map": self._index_map,
                    "vehicle_id": self.vehicle_id,
                    "released_indices": released_to_save,
                }
            )
        except Exception as err:
            _LOGGER.error("Failed to save index mapping to storage: %s", err)
            await self.async_notify_error(
                error_type="storage_error",
                message=f"Failed to save data: {err}",
            )

    async def async_assign_index_to_trip(self, trip_id: str) -> Optional[int]:
        """
        Assign an available EMHASS index to a trip.

        Returns:
            Assigned index or None if no indices available
        """
        if trip_id in self._index_map:
            # Trip already has an index, reuse it
            return self._index_map[trip_id]

        available = self.get_available_indices()
        if not available:
            _LOGGER.error(
                "No available EMHASS indices for vehicle %s. "
                "Max deferrable loads: %d, currently used: %d",
                self.vehicle_id,
                self.max_deferrable_loads,
                len(self._index_map),
            )
            return None

        # Assign the smallest available index
        assigned_index = min(available)
        self._available_indices.remove(assigned_index)
        self._index_map[trip_id] = assigned_index

        await self.async_save()

        _LOGGER.info(
            "Assigned EMHASS index %d to trip %s for vehicle %s. "
            "%d indices remaining available",
            assigned_index,
            trip_id,
            self.vehicle_id,
            len(self._available_indices),
        )

        return assigned_index

    async def async_release_trip_index(self, trip_id: str) -> bool:
        """
        Release an EMHASS index when trip is deleted/completed.
        Uses soft delete - index goes to cooldown for 24h before reuse.

        Returns:
            True if index was released, False if trip not found
        """
        if trip_id not in self._index_map:
            _LOGGER.warning("Attempted to release index for unknown trip %s", trip_id)
            return False

        released_index = self._index_map.pop(trip_id)
        # Soft delete: store in released_indices with timestamp
        # instead of returning to available
        self._released_indices[released_index] = datetime.now(timezone.utc)

        await self.async_save()

        _LOGGER.info(
            "Released EMHASS index %d from trip %s for vehicle %s. "
            "Index in soft-delete cooldown for %d hours",
            released_index,
            trip_id,
            self.vehicle_id,
            self._index_cooldown_hours,
        )

        return True

    def _get_config_sensor_id(self, emhass_index: int) -> str:
        """Get entity ID for EMHASS config sensor."""
        return f"sensor.emhass_deferrable_load_config_{emhass_index}"

    async def async_publish_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """
        Publish a trip as deferrable load configuration.

        Args:
            trip: Trip dictionary with kwh, deadline, etc.

        Returns:
            True if successful, False otherwise
        """
        trip_id = trip.get("id")
        if not trip_id:
            _LOGGER.error("Trip missing ID")
            return False

        # Assign index to trip
        emhass_index = await self.async_assign_index_to_trip(trip_id)
        if emhass_index is None:
            return False

        # Calculate parameters
        kwh = float(trip.get("kwh", 0))
        deadline = trip.get("datetime")

        # BUG FIX (recurring trips): Use _calculate_deadline_from_trip helper
        # This handles both punctual trips (datetime field) and recurring trips
        # (calculated from dia_semana/hora), eliminating code duplication
        deadline_dt = self._calculate_deadline_from_trip(trip)

        if deadline_dt is None:
            # Invalid trip - no datetime and not a valid recurring trip
            _LOGGER.error("Trip %s has no valid deadline", trip_id)
            await self.async_release_trip_index(trip_id)
            return False

        # Calculate hours available and def_start_timestep from charging windows
        now = datetime.now(timezone.utc)
        hours_available = (deadline_dt - now).total_seconds() / 3600

        # DEBUG: Log trip details before rejection check (debug level)
        _LOGGER.debug(
            "DEBUG async_publish_deferrable_load: trip_id=%s, deadline=%s, deadline_dt=%s, now=%s, hours_available=%.2f, kwh=%s",
            trip_id, deadline, deadline_dt, now, hours_available, trip.get("kwh")
        )

        if hours_available <= 0:
            _LOGGER.warning("Trip deadline in past: %s (hours_available=%.2f)", trip_id, hours_available)
            await self.async_release_trip_index(trip_id)
            return False

        # Calculate charging window start time for def_start_timestep
        # FR-9c: Use calculate_multi_trip_charging_windows to compute proper start timestep
        soc_current = await self._get_current_soc()
        if soc_current is None:
            soc_current = 50.0
        hora_regreso = await self._get_hora_regreso()

        # Create single-trip charging window
        charging_windows = calculate_multi_trip_charging_windows(
            trips=[(deadline_dt, trip)],
            soc_actual=soc_current,
            hora_regreso=hora_regreso,
            charging_power_kw=self._charging_power_kw,
            battery_capacity_kwh=self._battery_cap.get_capacity(self.hass),
            duration_hours=6.0,
            safety_margin_percent=self._safety_margin_percent,
            now=dt_util.now(),
        )

        # Extract inicio_ventana and fin_ventana (datetime) and convert to timesteps
        def_start_timestep = 0
        if charging_windows:
            inicio_ventana = charging_windows[0].get("inicio_ventana")
            fin_ventana = charging_windows[0].get("fin_ventana")
            if inicio_ventana:
                # Convert datetime to hours from now, clamped to 0-168 range
                delta_hours = (_ensure_aware(inicio_ventana) - now).total_seconds() / 3600
                def_start_timestep = max(0, min(int(delta_hours), 168))

        # Calculate EMHASS parameters using SOC-aware calculation
        # FIX: Use calculate_energy_needed instead of simple kwh / charging_power_kw
        from .calculations import calculate_energy_needed

        energia_info = calculate_energy_needed(
            trip,
            self._battery_cap.get_capacity(self.hass),
            soc_current,
            self._charging_power_kw,
            safety_margin_percent=self._safety_margin_percent,
        )

        # Use real calculated values considering SOC
        total_hours = energia_info["horas_carga_necesarias"]
        kwh_needed = energia_info["energia_necesaria_kwh"]

        # Only set power_watts if charging is actually needed
        if total_hours > 0:
            power_watts = self._charging_power_kw * 1000  # Convert to Watts
        else:
            power_watts = 0.0

        end_timestep = min(int(hours_available), 168)  # Max 7 days

        # BUG FIX: Use fin_ventana for end_timestep when available
        # Use math.ceil to avoid truncation issues (e.g., 95.99 hours -> 96)
        # Guard: Check charging_windows is not empty before accessing [0]
        if charging_windows and len(charging_windows) > 0 and charging_windows[0].get("fin_ventana"):
            fin_ventana = charging_windows[0].get("fin_ventana")
            # mypy: fin_ventana is Any|None, but we checked it's truthy above
            if isinstance(fin_ventana, datetime):
                delta_hours_end = (_ensure_aware(fin_ventana) - now).total_seconds() / 3600
                end_timestep = max(0, min(math.ceil(delta_hours_end - 0.001), 168))

        # Create attributes
        _attributes = {
            "def_total_hours": total_hours,
            "P_deferrable_nom": round(power_watts, 0),
            "def_start_timestep": def_start_timestep,
            "def_end_timestep": end_timestep,
            "trip_id": trip_id,
            "vehicle_id": self.vehicle_id,
            "entry_id": self.entry_id,  # FR-1.2: For orphan detection
            "trip_description": trip.get("descripcion", ""),
            "status": "pending",
            "kwh_needed": kwh_needed,
            "deadline": deadline_dt.isoformat(),
            "emhass_index": emhass_index,
        }

        # Set state
        # PHASE 3 REMOVED (3.1): Remove dual-writing path - data via coordinator
        #     config_sensor_id = self._get_config_sensor_id(emhass_index)
        #     config_sensor_id, EMHASS_STATE_ACTIVE, attributes
        # )

        _LOGGER.info(
            "Published deferrable load for trip %s (index %d): %s hours, %s W",
            trip_id,
            emhass_index,
            round(total_hours, 2),
            round(power_watts, 0),
        )

        return True

    def _calculate_deadline_from_trip(self, trip: Dict[str, Any]) -> Optional[datetime]:
        """Calculate deadline datetime from trip data.

        Handles both:
        - Punctual trips: trip["datetime"] exists (ISO format string)
        - Recurring trips: calculate from dia_semana/hora

        This method encapsulates the deadline calculation logic to avoid
        duplication between async_publish_deferrable_load and
        _populate_per_trip_cache_entry (SOLID: Single Responsibility).

        Args:
            trip: Trip dictionary with either "datetime" (punctual) or
                  "dia_semana"/"hora" (recurring).

        Returns:
            datetime: Calculated deadline, or None if trip is invalid.
        """
        # Punctual trip: use datetime field directly
        deadline = trip.get("datetime")
        if deadline:
            if isinstance(deadline, str):
                dt = datetime.fromisoformat(deadline)
                return _ensure_aware(dt)
            return _ensure_aware(deadline)  # Already a datetime

        # Recurring trip: calculate from day/time
        trip_type = trip.get("tipo", "")
        is_recurring = trip_type in ("recurrente", "recurring")

        if is_recurring:
            day = trip.get("day") or trip.get("dia_semana")
            time_str = trip.get("time") or trip.get("hora")

            if day is not None and time_str is not None:
                from .calculations import calculate_next_recurring_datetime, calculate_day_index

                # Convert day name to index (0=Monday for ES/EN names)
                if isinstance(day, str):
                    # Convert Spanish/English day name to 0-6 index (Monday=0)
                    day_index = calculate_day_index(day)
                    # Convert to JavaScript getDay() format (Sunday=0, Monday=1)
                    day_js_format = (day_index + 1) % 7
                else:
                    # Already a number - assume ES format (Monday=0), convert to JS format
                    day_js_format = (day + 1) % 7

                try:
                    _hass = getattr(self, 'hass', None)
                    result = calculate_next_recurring_datetime(
                        day_js_format, time_str, dt_util.now(),
                        tz=_hass.config.time_zone if _hass else None,
                    )
                    # EC-011 FIX: calculate_next_recurring_datetime returns naive datetime.
                    # _ensure_aware converts it to UTC-aware to prevent TypeError when
                    # subtracting from aware datetimes (e.g., now = datetime.now(timezone.utc)).
                    if result is not None:
                        return _ensure_aware(result)
                except ValueError:
                    # Invalid time string (e.g., hour out of range) should be
                    # treated as no deadline and not raise during publish.
                    return None

        return None

    async def _populate_per_trip_cache_entry(
        self,
        trip: dict[str, Any],
        trip_id: str,
        charging_power_kw: float,
        battery_capacity_kwh: float,
        safety_margin_percent: float,
        soc_current: float,
        hora_regreso: Optional[datetime],
        pre_computed_inicio_ventana: Optional[datetime] = None,
        pre_computed_fin_ventana: Optional[datetime] = None,
        adjusted_def_total_hours: Optional[float] = None,
        soc_cap: Optional[float] = None,
    ) -> None:
        # T062/T063: Wire t_base for dynamic SOC capping
        t_base = getattr(self, "_t_base", DEFAULT_T_BASE)
        """Build and cache per-trip EMHASS parameters.

        Encapsulates the logic for assigning trip index, calculating charging windows,
        and populating the _cached_per_trip_params dictionary. This eliminates
        duplicate code that was causing logic drift (e.g., recurring deadline bug).

        Args:
            trip: Trip dictionary.
            trip_id: Trip ID.
            charging_power_kw: Charging power in kW.
            battery_capacity_kwh: Battery capacity in kWh.
            safety_margin_percent: Safety margin percentage.
            soc_current: Current SOC percentage (or fallback 50.0).
            hora_regreso: Return time from presence_monitor or None.
            pre_computed_inicio_ventana: Pre-computed inicio_ventana from batch calculation.
        """
        # Assign index if not already assigned
        if trip_id not in self._index_map:
            await self.async_assign_index_to_trip(trip_id)
        emhass_index = self._index_map.get(trip_id, -1)

        # Capture current time once to avoid inconsistencies from multiple datetime.now() calls
        # near hour boundaries (off-by-one errors)
        now = dt_util.now()

        # Calculate per-trip params with charging windows
        # BUG FIX: Use _calculate_deadline_from_trip to handle both trip types
        
        # T1.1: Determine charging need using pure function (H4, H5)
        decision = determine_charging_need(
            trip, soc_current, battery_capacity_kwh,
            charging_power_kw, safety_margin_percent,
        )
        
        # Logging estructurado para observabilidad (H11)
        _LOGGER.info(
            "Charging decision for trip %s: kwh_needed=%.2f, needs_charging=%s, soc=%.1f%%",
            trip_id, decision.kwh_needed, decision.needs_charging, soc_current,
        )
        
        deadline_str = trip.get("datetime")

        # Calculate deadline_dt using the new helper method
        deadline_dt = self._calculate_deadline_from_trip(trip)
        if deadline_dt is None:
            # Fallback for invalid trips (should not happen in normal flow)
            deadline_dt = now

        def_start_timestep = 0
        if pre_computed_inicio_ventana is not None:
            # Use pre-computed inicio_ventana from batch calculation
            delta_hours = (_ensure_aware(pre_computed_inicio_ventana) - now).total_seconds() / 3600
            def_start_timestep = max(0, min(int(delta_hours), 168))
        else:
            # Fall back to existing single-trip calculation (backward compat)
            charging_windows = calculate_multi_trip_charging_windows(
                trips=[(deadline_dt, trip)],
                soc_actual=soc_current,
                hora_regreso=hora_regreso,
                charging_power_kw=charging_power_kw,
                battery_capacity_kwh=battery_capacity_kwh,
                duration_hours=6.0,
                safety_margin_percent=safety_margin_percent,
                now=now,
            )
            if charging_windows:
                inicio_ventana = charging_windows[0].get("inicio_ventana")
                if inicio_ventana:
                    delta_hours = (_ensure_aware(inicio_ventana) - now).total_seconds() / 3600
                    def_start_timestep = max(0, min(int(delta_hours), 168))

        hours_available = (deadline_dt - now).total_seconds() / 3600
        def_end_timestep = min(int(max(0, hours_available)), 168)

        # BUG FIX: Use fin_ventana for def_end_timestep when available
        # This ensures the charging window [def_start, def_end] matches the actual
        # charging window [inicio_ventana, fin_ventana] from calculations
        # Use math.ceil to avoid truncation issues (e.g., 95.99 hours -> 96)
        # Applies to both batch path (pre_computed_fin_ventana) and fallback path (charging_windows)
        fin_ventana_to_use = None
        if pre_computed_fin_ventana is not None:
            # Batch path: use pre_computed_fin_ventana from batch charging windows
            fin_ventana_to_use = pre_computed_fin_ventana
        elif pre_computed_inicio_ventana is None and "charging_windows" in locals() and charging_windows and len(charging_windows) > 0:
            # Fallback path: extract fin_ventana from locally calculated charging_windows
            fin_ventana_to_use = charging_windows[0].get("fin_ventana")

        if fin_ventana_to_use is not None:
            delta_hours_end = (_ensure_aware(fin_ventana_to_use) - now).total_seconds() / 3600
            # Guard: Skip if fin_ventana is in the past
            if delta_hours_end > 0:
                def_end_timestep = max(0, min(math.ceil(delta_hours_end - 0.001), 168))

        # BUG FIX: EMHASS off-by-one in window calculation.
        # The combination of int() for def_start and ceil(x-0.001) for def_end
        # systematically produces a window that is 1 timestep too narrow.
        # Subtract 1 from def_start to expand the window by 1 timestep.
        # If def_start would go below 0, we reduce total_hours instead (below).
        _def_start_before_expansion = def_start_timestep
        def_start_timestep = max(0, def_start_timestep - 1)

        # Edge case: only apply when window is genuinely impossible (not when clamped to horizon)
        # If delta_hours > 168, it was clamped to horizon - valid window at boundary, don't reduce
        # If delta_hours <= 168 but def_start >= def_end, it was truly impossible - reduce
        if pre_computed_inicio_ventana is None and "delta_hours" in locals():
            if delta_hours <= 168 and def_start_timestep >= def_end_timestep:
                def_start_timestep = max(0, def_end_timestep - 1)

        # T1.1: Usar decisión para poblar cache (kwh_needed, total_hours, power_watts)
        kwh_needed = decision.kwh_needed
        total_hours = decision.def_total_hours
        power_watts = decision.power_watts

        # T062/T063: Apply dynamic SOC cap to reduce kwh_needed
        # If a soc_cap < 100% is provided, proportionally reduce energy needed
        if soc_cap is not None and soc_cap < 100.0:
            cap_ratio = soc_cap / 100.0
            kwh_needed = kwh_needed * cap_ratio
            total_hours = total_hours * cap_ratio
            power_watts = power_watts * cap_ratio

        # Use adjusted hours from backward deficit propagation.
        # When a trip's charging needs exceed its window, excess hours are propagated
        # backward to earlier trips with spare capacity. The propagated trip receives
        # adjusted_def_total_hours that includes absorbed deficit from later trips.
        needs_charging = decision.needs_charging
        if adjusted_def_total_hours is not None and adjusted_def_total_hours > 0:
            # Only override total_hours if propagation provides hours > 0
            # If adjusted_def_total_hours = 0, it means "no deficit propagated to this trip"
            # but the trip may still need charging individually (keep decision.def_total_hours)
            total_hours = adjusted_def_total_hours
            # Override needs_charging based on adjusted hours.
            # A trip that originally needed no charging may now absorb propagated deficit.
            # CRITICAL: Only override if projected SOC for this trip allows charging (SOC < 100%).
            # soc_current parameter is the projected SOC at this trip's charging window,
            # not the current system SOC. This respects SOC propagation between trips.
            if soc_current < 100.0:
                needs_charging = True
                power_watts = charging_power_kw * 1000

        # BUG FIX (continued): If def_start was already 0 and couldn't be
        # expanded backward, cap total_hours to the available window size.
        # If there is no available timestep (window_size <= 0), skip charging
        # entirely to prevent creating an impossible one-hour load.
        # Note: We use a narrow guard here to not interfere with backward
        # deficit propagation - that system handles most window-too-small cases.
        if _def_start_before_expansion == 0:
            window_size = def_end_timestep - def_start_timestep
            if window_size <= 0:
                total_hours = 0
                needs_charging = False
                power_watts = 0
            elif window_size < math.ceil(total_hours):
                total_hours = window_size

        # T1.3: Optimización - no calcular perfil si no se necesita carga
        if not needs_charging:
            power_profile = [0.0] * 168
        else:
            power_profile = self._calculate_power_profile_from_trips(
                [trip], charging_power_kw,
                soc_current=soc_current,
                battery_capacity_kwh=battery_capacity_kwh,
                safety_margin_percent=safety_margin_percent,
            )

        # T062/T063: Cap per-trip power profile by SOC cap ratio
        if soc_cap is not None and soc_cap < 100.0:
            cap_ratio = soc_cap / 100.0
            power_profile = [v * cap_ratio for v in power_profile]

        # Cache per-trip params
        # CRITICAL FIX: P_deferrable_nom must be consistent with def_total_hours.
        # - def_total_hours already includes all adjustments (propagation + window size)
        # - P_deferrable_nom should be power_watts ONLY if def_total_hours > 0
        # This prevents the bug where needs_charging=True but total_hours=0 (e.g., due to
        # window size reduction or empty profile from SOC <= 0%).
        #
        # The invariant: P_deferrable_nom > 0 ⇔ def_total_hours > 0
        has_charging = total_hours > 0

        # T062/T063: Compute dynamic SOC cap using t_base and real capacity
        soc_target = 100.0
        if deadline_dt is not None:
            t_hours = (deadline_dt - now).total_seconds() / 3600.0
            if t_hours > 0:
                soc_target = calculate_dynamic_soc_limit(
                    t_hours=t_hours,
                    soc_post_trip=soc_current,
                    battery_capacity_kwh=battery_capacity_kwh,
                    t_base=t_base,
                )

        self._cached_per_trip_params[trip_id] = {
            "def_total_hours": math.ceil(total_hours),
            "P_deferrable_nom": round(power_watts, 0) if has_charging else 0.0,
            "p_deferrable_nom": round(power_watts, 0) if has_charging else 0.0,
            "def_start_timestep": def_start_timestep,
            "def_end_timestep": def_end_timestep,
            "power_profile_watts": power_profile,
            "def_total_hours_array": [math.ceil(total_hours)],
            "p_deferrable_nom_array": [round(power_watts, 0) if needs_charging else 0.0],
            "def_start_timestep_array": [def_start_timestep],
            "def_end_timestep_array": [def_end_timestep],
            "p_deferrable_matrix": [power_profile],
            "trip_id": trip_id,
            "emhass_index": emhass_index,
            "kwh_needed": kwh_needed,
            "deadline": deadline_str,
            "soc_target": soc_target,
            "activo": True,
        }

    async def async_remove_deferrable_load(self, trip_id: str) -> bool:
        """Remove a trip from deferrable load configuration."""
        try:
            if trip_id not in self._index_map:
                _LOGGER.warning("Attempted to remove unknown trip %s", trip_id)
                return False

            emhass_index = self._index_map[trip_id]

            # Clear the configuration
            # PHASE 3 REMOVED (3.1): Remove dual-writing path

            # Release the index
            await self.async_release_trip_index(trip_id)

            # EC-013 FIX: Clear per-trip cache entry when trip is removed.
            # Without this, stale cache entries persist indefinitely until the next
            # full republish, causing the EMHASS sensor to show deleted trips.
            self._cached_per_trip_params.pop(trip_id, None)

            _LOGGER.info(
                "Removed deferrable load for trip %s (index %d)", trip_id, emhass_index
            )

            return True

        except Exception as err:
            _LOGGER.error("Error removing deferrable load: %s", err)
            await self.async_notify_error(
                error_type="sensor_error",
                message=f"Failed to remove deferrable load: {err}",
                trip_id=trip_id,
            )
            return False

    async def async_update_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """Update existing deferrable load with new parameters."""
        return await self.async_publish_deferrable_load(trip)

    async def async_publish_all_deferrable_loads(
        self, trips: List[Dict[str, Any]], charging_power_kw: Optional[float] = None
    ) -> bool:
        """
        Publish multiple trips, each with its own index.

        Args:
            trips: List of trip dictionaries to publish
            charging_power_kw: Optional charging power override (not used, trips have their own)

        Returns:
            True if all trips published successfully, False otherwise
        """
        # CRITICAL FIX: When shutting down, only allow empty trips (deletion flow) to proceed.
        # This blocks presence_monitor callbacks and other operational calls during deletion.
        if self._shutting_down and trips:
            _LOGGER.debug(
                "Skipping async_publish_all_deferrable_loads for %s - shutting down with trips",
                self.vehicle_id,
            )
            return True

        # CRITICAL FIX: When trips is empty (cascade deletion), clear all cache and return early.
        # Without this, _cached_per_trip_params retains stale data and the EMHASS sensor
        # shows old trips after integration deletion.
        if not trips:
            _LOGGER.info("async_publish_all_deferrable_loads: Empty trips list, clearing cache and returning early")
            self._cached_per_trip_params.clear()
            self._cached_power_profile = []
            self._cached_deferrables_schedule = []
            self._published_trips = []
            self._cached_emhass_status = EMHASS_STATE_READY
            # CRITICAL FIX: Directly update coordinator.data so sensor sees empty state
            # immediately without waiting for async_refresh (which has debouncing/race issues).
            coordinator = self._get_coordinator()
            if coordinator is not None:
                try:
                    # Update coordinator.data directly first (immediate, no debouncing)
                    # Handle case where coordinator.data might be None before first refresh
                    existing_data = coordinator.data or {}
                    coordinator.data = {
                        **existing_data,
                        "per_trip_emhass_params": {},
                        "emhass_power_profile": [],
                        "emhass_deferrables_schedule": [],
                        "emhass_status": EMHASS_STATE_READY,
                    }
                    # Then trigger async_refresh to notify HA of the state change
                    await coordinator.async_refresh()
                except Exception:
                    pass
            return True

        _LOGGER.debug("DEBUG async_publish_all: trips count=%d, kwh values=%s", len(trips), [t.get("kwh") for t in trips])
        if charging_power_kw is None:
            charging_power_kw = self._charging_power_kw
        _LOGGER.debug("DEBUG: charging_power_kw=%.2f", charging_power_kw)

        success_count = 0
        failed_trip_ids: list[str] = []

        # Clear stale cache entries before republish
        current_trip_ids = {trip.get("id") for trip in trips if trip.get("id")}
        stale_ids = set(self._cached_per_trip_params.keys()) - current_trip_ids
        for stale_id in stale_ids:  # pragma: no cover - edge case: stale cache entries
            del self._cached_per_trip_params[stale_id]

        # EC-020 FIX: Atomic publish with rollback on failure.
        # Previously, if trip N failed, trips 0..N-1 remained published, causing
        # inconsistent state where the sensor shows partial data. Now we track
        # failed trips and roll back their cache entries on failure.
        for trip in trips:
            trip_id = trip.get("id")
            if not trip_id:
                continue
            if await self.async_publish_deferrable_load(trip):
                success_count += 1
            else:
                failed_trip_ids.append(trip_id)

        _LOGGER.info(
            "Published %d/%d deferrable loads for vehicle %s",
            success_count,
            len(trips),
            self.vehicle_id,
        )

        # EC-020 FIX: Rollback failed trips. If any trip failed to publish,
        # remove its cache entry and index assignment to prevent inconsistent state.
        if failed_trip_ids:
            _LOGGER.warning(
                "EC-020: Rolling back %d failed trips: %s",
                len(failed_trip_ids),
                failed_trip_ids,
            )
            for failed_id in failed_trip_ids:
                self._cached_per_trip_params.pop(failed_id, None)
                # Release the index that was assigned to the failed trip
                if failed_id in self._index_map:
                    idx = self._index_map.pop(failed_id)
                    self._available_indices.append(idx)
                    self._available_indices.sort()
                    self._published_trips = [
                        t for t in self._published_trips if t.get("id") != failed_id
                    ]

        # CRITICAL FIX: Populate per-trip cache after publishing all trips
        # async_publish_deferrable_load only calls publish_deferrable_load which
        # publishes the trip but doesn't populate _cached_per_trip_params.
        # This loop ensures per-trip params are cached for coordinator retrieval.
        coordinator = self._get_coordinator()

        # Get SOC once before loop for consistency
        soc_current = await self._get_current_soc()
        if soc_current is None:
            soc_current = 50.0

        # Inject presence_monitor if not already injected
        if self._presence_monitor is None and coordinator is not None:
            trip_manager = getattr(coordinator, "_trip_manager", None)
            if trip_manager and hasattr(trip_manager, "vehicle_controller"):
                vc = trip_manager.vehicle_controller
                if vc and hasattr(vc, "_presence_monitor"):
                    self._presence_monitor = vc._presence_monitor

        hora_regreso = None
        if self._presence_monitor:
            try:
                hora_regreso = await self._presence_monitor.async_get_hora_regreso()
            except Exception:
                hora_regreso = None

        _LOGGER.debug(
            "DEBUG async_publish_all: hora_regreso=%s, vehicle_id=%s, trips_count=%d",
            hora_regreso, self.vehicle_id, len(trips),
        )

        # Batch compute charging windows for ALL trips at once (fixes sequential trip offset bug)
        trip_deadlines = []
        for trip in trips:
            trip_id = trip.get("id")
            if not trip_id:
                continue
            deadline_dt = self._calculate_deadline_from_trip(trip)
            if deadline_dt:
                trip_deadlines.append((trip_id, deadline_dt, trip))

        # Sort by deadline to ensure correct sequential chaining
        # (calculate_multi_trip_charging_windows expects trips ordered by departure time)
        trip_deadlines.sort(key=lambda x: x[1])

        batch_charging_windows = {}
        enriched_windows_map: Dict[str, Dict[str, Any]] = {}
        if trip_deadlines:
            windows = calculate_multi_trip_charging_windows(
                trips=[(dl, trip) for _, dl, trip in trip_deadlines],
                soc_actual=soc_current,
                hora_regreso=hora_regreso,
                charging_power_kw=charging_power_kw,
                battery_capacity_kwh=self._battery_cap.get_capacity(self.hass),
                return_buffer_hours=RETURN_BUFFER_HOURS,
                safety_margin_percent=self._safety_margin_percent,
                now=dt_util.now(),
            )
            for i, (trip_id, _, _) in enumerate(trip_deadlines):
                if i < len(windows):
                    batch_charging_windows[trip_id] = windows[i]

        # T2.0: Propagate charging deficit backward across trips
        # Collect def_total_hours from charging decisions and propagate excess to
        # earlier trips with spare capacity. This replaces the capping approach.
        if batch_charging_windows:
            # First pass: collect def_total_hours using the same sequential SOC
            # projection used later for cache population, so propagation hours
            # are consistent with per-trip scheduling decisions.
            trip_def_total_hours: Dict[str, float] = {}
            ordered_trip_ids: List[str] = []
            projected_soc = soc_current
            for trip_id, _, trip in trip_deadlines:
                if trip_id not in batch_charging_windows:
                    continue
                decision = determine_charging_need(
                    trip, projected_soc, self._battery_cap.get_capacity(self.hass),
                    charging_power_kw, self._safety_margin_percent,
                )
                trip_def_total_hours[trip_id] = decision.def_total_hours
                ordered_trip_ids.append(trip_id)
                projected_soc = getattr(
                    decision, "projected_soc", projected_soc,
                )

            # Run propagation on batch windows in the same order they were computed.
            window_list = [batch_charging_windows[tid] for tid in ordered_trip_ids]
            def_total_hours_list = [
                trip_def_total_hours.get(
                    tid, batch_charging_windows[tid].get("horas_carga_necesarias", 0.0)
                )
                for tid in ordered_trip_ids
            ]
            enriched_windows = calculate_hours_deficit_propagation(
                window_list, def_total_hours_list,
            )

            # enriched_windows is now in the same order as ordered_trip_ids.
            for trip_id, enriched in zip(ordered_trip_ids, enriched_windows):
                enriched_windows_map[trip_id] = enriched

        _LOGGER.debug(
            "DEBUG async_publish_all_deferrable_loads: batch computed %d charging windows, propagation applied %d",
            len(batch_charging_windows), len(enriched_windows_map),
        )

        # T2.1: Propagate SOC sequentially between trips
        # Each trip's SOC projection considers: previous SOC + charging - consumption
        projected_soc = soc_current

        # Publish each trip and populate per-trip cache with projected SOC
        # CRITICAL FIX: Iterate over trip_deadlines (chronological order), not trips (creation order)
        # This ensures cache is populated in deadline order, which affects SOC propagation
        # FALLBACK: If trip_deadlines is empty (e.g., all trips have invalid deadlines), use original trips order
        trips_to_process = trip_deadlines if trip_deadlines else [(None, None, trip) for trip in trips]

        for item in trips_to_process:
            if trip_deadlines:
                # Unpack (trip_id, deadline_dt, trip) from trip_deadlines
                trip_id, deadline_dt, trip = item
            else:
                # Fallback: unpack (None, None, trip) from original trips
                trip_id = trip.get("id")
                deadline_dt = None
                if not trip_id:  # pragma: no cover - defensive: skip invalid trips
                    continue

            # Get batch-computed inicio_ventana and fin_ventana for this trip
            batch_window = batch_charging_windows.get(trip_id)
            pre_computed_inicio = batch_window.get("inicio_ventana") if batch_window else None
            pre_computed_fin = batch_window.get("fin_ventana") if batch_window else None

            # Get adjusted hours from propagation (if available)
            adjusted_hours = None
            if trip_id in enriched_windows_map:
                adjusted_hours = enriched_windows_map[trip_id].get("adjusted_def_total_hours")

            # Use projected SOC for this trip (considers previous trips' charging/consumption)

            # T062/T063: Compute dynamic SOC cap for this trip
            now = dt_util.now()
            soc_cap = None
            if deadline_dt is not None:
                t_hours = (deadline_dt - now).total_seconds() / 3600.0
                if t_hours > 0:
                    real_cap = self._battery_cap.get_capacity(self.hass)
                    t_base = getattr(self, "_t_base", DEFAULT_T_BASE)
                    soc_cap = calculate_dynamic_soc_limit(
                        t_hours=t_hours,
                        soc_post_trip=projected_soc,
                        battery_capacity_kwh=real_cap,
                        t_base=t_base,
                    )

            await self._populate_per_trip_cache_entry(
                trip, trip_id, charging_power_kw, self._battery_cap.get_capacity(self.hass),
                self._safety_margin_percent, projected_soc, hora_regreso,
                pre_computed_inicio_ventana=pre_computed_inicio,
                pre_computed_fin_ventana=pre_computed_fin,
                adjusted_def_total_hours=adjusted_hours,
                soc_cap=soc_cap,
            )
            
            # Update projected SOC for next trip
            # 1. Add SOC gained from charging this trip
            if trip_id in batch_charging_windows:
                window = batch_charging_windows[trip_id]
                ventana_horas = window.get("ventana_horas", 0)
                # Get charging decision from cache
                cached_params = self._cached_per_trip_params.get(trip_id, {})
                def_total_hours = cached_params.get("def_total_hours", 0)
                
                # Calculate SOC gained: min(hours available, hours needed) * power / capacity * 100
                horas_carga = min(def_total_hours, ventana_horas) if ventana_horas > 0 else 0
                kwh_cargados = horas_carga * charging_power_kw
                soc_ganado = (kwh_cargados / self._battery_cap.get_capacity(self.hass)) * 100 if self._battery_cap.get_capacity(self.hass) > 0 else 0
            else:
                soc_ganado = 0
            
            # 2. Subtract SOC consumed by this trip
            trip_kwh = trip.get("kwh", 0.0)
            soc_consumido = (trip_kwh / self._battery_cap.get_capacity(self.hass)) * 100 if self._battery_cap.get_capacity(self.hass) > 0 else 0
            
            # 3. Update projected SOC
            projected_soc = projected_soc + soc_ganado - soc_consumido
            # Clamp to valid range
            projected_soc = max(0.0, min(100.0, projected_soc))
            
            _LOGGER.debug(
                "SOC propagation: trip=%s, soc_start=%.1f%%, charged=%.2f%%, consumed=%.2f%%, soc_end=%.1f%%",
                trip_id, projected_soc - soc_ganado + soc_consumido, soc_ganado, soc_consumido, projected_soc,
            )

        # Calculate aggregated power profile and schedule for all trips
        power_profile = self._calculate_power_profile_from_trips(
            trips, charging_power_kw,
            soc_current=soc_current,
            battery_capacity_kwh=self._battery_cap.get_capacity(self.hass),
            safety_margin_percent=self._safety_margin_percent,
        )

        # T062/T063: Aggregate capped per-trip power profiles to reflect SOC caps
        # Each trip's cached power_profile_watts already accounts for the SOC cap.
        # Sum them element-wise to get the final aggregated profile.
        capped_profile = [0.0] * 168
        profile_trip_count = 0
        for trip in trips:
            trip_id = trip.get("id")
            if trip_id and trip_id in self._cached_per_trip_params:
                trip_profile = self._cached_per_trip_params[trip_id].get("power_profile_watts")
                if trip_profile:
                    capped_profile = [
                        capped_profile[i] + trip_profile[i]
                        for i in range(min(168, len(capped_profile), len(trip_profile)))
                    ]
                    profile_trip_count += 1

        if profile_trip_count > 0:
            power_profile = capped_profile

        deferrables_schedule = self._generate_schedule_from_trips(
            trips, charging_power_kw
        )

        # DEBUG: Log power profile and trips (debug level)
        _LOGGER.debug(
            "DEBUG async_publish_all_deferrable_loads: calculated power_profile=%s, non_zero=%d",
            power_profile[:10] if power_profile else [],
            sum(1 for x in power_profile if x > 0) if power_profile else 0
        )
        _LOGGER.debug(
            "DEBUG async_publish_all_deferrable_loads: trips for profile calculation: count=%d, trip_ids=%s",
            len(trips),
            [t.get("id") for t in trips]
        )

        # Populate cache for coordinator retrieval
        self._cached_power_profile = power_profile
        self._cached_deferrables_schedule = deferrables_schedule
        self._cached_emhass_status = EMHASS_STATE_READY

        _LOGGER.info(
            "Populated EMHASS cache: power_profile_length=%d, non_zero=%d, schedule_length=%d, status=%s",
            len(power_profile),
            sum(1 for x in power_profile if x > 0),
            len(deferrables_schedule),
            EMHASS_STATE_READY,
        )

        return success_count == len(trips)

    def get_assigned_index(self, trip_id: str) -> Optional[int]:
        """Get the EMHASS index assigned to a trip."""
        return self._index_map.get(trip_id)

    def get_all_assigned_indices(self) -> Dict[str, int]:
        """Get all trip-index mappings."""
        return self._index_map.copy()

    def get_available_indices(self) -> List[int]:
        """
        Get list of available indices, excluding those in soft-delete cooldown.

        Returns:
            List of available EMHASS indices
        """
        # Clean up expired cooldown indices first
        now = datetime.now(timezone.utc)
        expired = [
            idx
            for idx, released_time in self._released_indices.items()
            if (now - _ensure_aware(released_time)).total_seconds() >= self._index_cooldown_hours * 3600
        ]
        for idx in expired:
            del self._released_indices[idx]
            self._available_indices.append(idx)

        if expired:
            self._available_indices.sort()

        return self._available_indices

    def calculate_deferrable_parameters(
        self,
        trip: Dict[str, Any],
        charging_power_kw: float,
    ) -> Dict[str, Any]:
        """
        Calculate deferrable load parameters from trip data.

        Delegates to the pure function from calculations.py.

        Args:
            trip: Trip dictionary with kwh, deadline, etc.
            charging_power_kw: Charging power in kW

        Returns:
            Dictionary with calculated deferrable parameters:
            - total_energy_kwh: Energy needed in kWh
            - power_watts: Charging power in watts
            - total_hours: Hours needed to charge
            - end_timestep: End timestep for EMHASS
            - start_timestep: Start timestep for EMHASS
        """
        return calc_deferrable_parameters(trip, charging_power_kw)

    async def publish_deferrable_loads(
        self,
        trips: Optional[List[Dict[str, Any]]] = None,
        charging_power_kw: Optional[float] = None,
    ) -> bool:
        """
        Publish multiple trips as deferrable loads to EMHASS.

        This method:
        1. Calculates deferrable parameters for each trip
        2. Updates the template sensor with power_profile_watts and deferrables_schedule
        3. Ensures power profile: 0W = no charging, positive values = charging power

        Args:
            trips: List of trip dictionaries
            charging_power_kw: Charging power in kW (defaults to self.charging_power)

        Returns:
            True if all trips published successfully
        """
        # CRITICAL FIX: Skip if shutting down - prevents republish during deletion.
        # This blocks presence_monitor callbacks that could trigger publish_deferrable_loads()
        # during deletion and cause stale trips to reappear.
        if self._shutting_down:
            _LOGGER.debug(
                "Skipping publish_deferrable_loads for %s - shutting down",
                self.vehicle_id,
            )
            return True

        if charging_power_kw is None:
            charging_power_kw = self._charging_power_kw

        # CRITICAL FIX: Clear ALL cached per-trip params when trips is empty
        # This handles cascade deletion (no trips) vs incremental update (has trips).
        # Without this, _cached_per_trip_params retains stale data from deleted trips,
        # causing EmhassDeferrableLoadSensor's extra_state_attributes to still show
        # old trips in def_total_hours_array after integration deletion.
        # Handle both [] and None (called as publish_deferrable_loads() without args)
        # NOTE: This cache clear happens BEFORE _shutting_down check to ensure
        # stale data is cleaned even during shutdown.
        if not trips:
            self._cached_per_trip_params.clear()
            self._cached_power_profile = []
            self._cached_deferrables_schedule = []
            self._published_trips = []
            self._cached_emhass_status = EMHASS_STATE_READY
            # Return early - no trips to process, cache is cleared
            # Coordinator refresh is NOT triggered for empty list (no EMHASS data to publish)
            return True

        # Enrich recurring trips: compute datetime from dia_semana + hora
        enriched_trips: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        for trip in trips:
            if (
                trip.get("tipo") == TRIP_TYPE_RECURRING
                and not trip.get("datetime")
            ):
                computed_dt = calculate_trip_time(
                    trip_tipo=TRIP_TYPE_RECURRING,
                    hora=trip.get("hora"),
                    dia_semana=trip.get("dia_semana"),
                    datetime_str=None,
                    reference_dt=now,
                )
                if computed_dt is None:
                    _LOGGER.warning(
                        "Skipping recurring trip %s: cannot compute datetime",
                        trip.get("id", "unknown"),
                    )
                    continue
                enriched = {**trip, "datetime": computed_dt.isoformat()}
                enriched_trips.append(enriched)
            else:
                enriched_trips.append(trip)
        trips = enriched_trips

        # FR-3.1: Store trips for reactive republish when charging power changes
        self._published_trips = list(trips)

        # Get SOC ONCE before any calculations (not per-trip) for consistency
        soc_current = await self._get_current_soc()
        if soc_current is None:
            soc_current = 50.0

        _LOGGER.info(
            "Publishing %d deferrable loads for vehicle %s with %s kW charging power, SOC=%.1f%%",
            len(trips),
            self.vehicle_id,
            charging_power_kw,
            soc_current,
        )

        # Calculate power profile for all trips (SOC-aware)
        # 0W = no charging, positive values = charging power
        power_profile = self._calculate_power_profile_from_trips(
            trips, charging_power_kw,
            soc_current=soc_current,
            battery_capacity_kwh=self._battery_cap.get_capacity(self.hass),
            safety_margin_percent=self._safety_margin_percent,
        )

        # Generate schedule
        deferrables_schedule = self._generate_schedule_from_trips(
            trips, charging_power_kw
        )

        # PHASE 3 (3.4): Cache computed values for coordinator retrieval
        self._cached_power_profile = power_profile
        self._cached_deferrables_schedule = deferrables_schedule
        self._cached_emhass_status = EMHASS_STATE_READY

        # PHASE 3 (3.2): Get coordinator early for presence_monitor injection
        # This must happen before the cache loop so we can inject presence_monitor
        coordinator = self._get_coordinator()

        # FR-3.1: Cache per-trip EMHASS params for coordinator retrieval
        # This enables per-trip sensors to access EMHASS parameters via coordinator.data

        # FIX for task 2.15: Clear stale cache entries before republish
        # When trips are deleted, their entries remain in _cached_per_trip_params
        # Compute current trip IDs from published trips
        current_trip_ids = {trip.get("id") for trip in trips if trip.get("id")}
        stale_ids = set(self._cached_per_trip_params.keys()) - current_trip_ids
        for stale_id in stale_ids:  # pragma: no cover - edge case: stale cache entries
            del self._cached_per_trip_params[stale_id]
            _LOGGER.debug("Cleared stale cache entry for trip %s", stale_id)

        # FR-4: Cache per-trip EMHASS params with proper charging window computation
        # Get hora_regreso ONCE before the loop for consistency
        hora_regreso = None
        if self._presence_monitor is None and coordinator is not None:
            trip_manager = getattr(coordinator, "_trip_manager", None)
            if trip_manager and hasattr(trip_manager, "vehicle_controller"):
                vc = trip_manager.vehicle_controller
                if vc and hasattr(vc, "_presence_monitor"):
                    self._presence_monitor = vc._presence_monitor

        if self._presence_monitor:
            try:
                hora_regreso = await self._presence_monitor.async_get_hora_regreso()
            except Exception:
                hora_regreso = None

        # Populate per-trip cache for each trip
        for trip in trips:
            trip_id = trip.get("id")
            if not trip_id:  # pragma: no cover - defensive: skip invalid trips
                continue
            await self._populate_per_trip_cache_entry(
                trip, trip_id, charging_power_kw, self._battery_cap.get_capacity(self.hass),
                self._safety_margin_percent, soc_current, hora_regreso
            )

        # PHASE 3 (3.2): Trigger coordinator refresh to propagate EMHASS data
        # Use async_refresh() for immediate update (not debounced async_request_refresh)
        if coordinator is not None:
            await coordinator.async_refresh()
            _LOGGER.debug(
                "Triggered coordinator refresh for EMHASS data update for %s",
                self.vehicle_id,
            )
        else:
            _LOGGER.warning(
                "No coordinator found for %s, EMHASS data update delayed",
                self.vehicle_id,
            )

        _LOGGER.info(
            "Published deferrable loads for %s: %d trips, profile length: %d",
            self.vehicle_id,
            len(trips),
            len(power_profile),
        )

        return True

    async def async_verify_shell_command_integration(self) -> Dict[str, Any]:
        """
        Verify that the EMHASS shell command integration is working.

        This method does NOT execute shell commands - it only verifies that:
        1. Our deferrable load sensors exist and contain data
        2. EMHASS response sensors are available to receive our data

        Returns:
            Dictionary with verification results:
            - is_configured: Whether shell command is likely configured
            - deferrable_sensor_exists: Whether our sensor exists
            - deferrable_sensor_has_data: Whether sensor has valid data
            - emhass_response_sensors: List of available EMHASS response sensors
            - errors: List of any issues found
        """
        result: Dict[str, Any] = {
            "is_configured": False,
            "deferrable_sensor_exists": False,
            "deferrable_sensor_has_data": False,
            "emhass_response_sensors": [],
            "errors": [],
        }

        # Check our deferrable sensor exists
        sensor_id = f"sensor.emhass_perfil_diferible_{self.entry_id}"
        deferrable_sensor = self.hass.states.get(sensor_id)

        if deferrable_sensor is None:
            result["errors"].append(
                f"Deferrable sensor {sensor_id} not found. "
                "Please configure the shell command in configuration.yaml"
            )
            return result

        result["deferrable_sensor_exists"] = True

        # Check sensor has valid data
        attrs = deferrable_sensor.attributes
        if not attrs or "power_profile_watts" not in attrs:
            result["errors"].append(
                f"Deferrable sensor {sensor_id} missing power_profile_watts attribute"
            )
            return result

        profile = attrs.get("power_profile_watts", [])
        if not profile or len(profile) == 0:
            result["errors"].append(
                f"Deferrable sensor {sensor_id} has empty power profile"
            )
            return result

        result["deferrable_sensor_has_data"] = True

        # Check for EMHASS response sensors (these are created by user's shell command)
        # Common EMHASS response sensor patterns
        response_sensor_patterns = [
            "sensor.emhass_",
            "sensor.p_deferrable",
            "sensor.emhass_opt",
        ]

        # Get all states and filter for EMHASS sensors
        all_states = self.hass.states.async_all()
        emhass_sensors = [
            state.entity_id
            for state in all_states
            if any(pattern in state.entity_id for pattern in response_sensor_patterns)
        ]

        result["emhass_response_sensors"] = emhass_sensors

        # If we have published trips, check if EMHASS sensors acknowledge them
        if self._index_map:
            result["is_configured"] = len(emhass_sensors) > 0

            if not emhass_sensors:
                result["errors"].append(
                    "No EMHASS response sensors found. "
                    "Verify shell command in configuration.yaml. "
                    "Should use curl to POST to EMHASS API."
                )

        _LOGGER.info(
            "EMHASS integration verification for %s: %s",
            self.vehicle_id,
            "configured" if result["is_configured"] else "not configured",
        )

        return result

    async def async_check_emhass_response_sensors(
        self, trip_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Check if EMHASS response sensors include our deferrable loads.

        This method monitors the EMHASS response sensors to verify they
        contain our deferrable load configurations.

        Args:
            trip_ids: Optional list of trip IDs to check. If None, checks all trips.

        Returns:
            Dictionary with check results:
            - all_trips_verified: Whether all trips are in EMHASS sensors
            - verified_trips: List of trip IDs found in EMHASS
            - missing_trips: List of trip IDs not found
            - sensor_values: Current values from EMHASS sensors
        """
        result: Dict[str, Any] = {
            "all_trips_verified": False,
            "verified_trips": [],
            "missing_trips": [],
            "sensor_values": {},
        }

        # Get trips to check
        if trip_ids is None:
            trip_ids = list(self._index_map.keys())

        if not trip_ids:
            result["all_trips_verified"] = True
            return result

        # Get all EMHASS-related sensors using hass.states.get directly
        # This is more reliable than async_all() in test environments
        emhass_states: Dict[str, Any] = {}

        # Check our config sensors directly
        for trip_id in trip_ids:
            index = self._index_map.get(trip_id)
            if index is None:
                result["missing_trips"].append(trip_id)
                continue

            # Check for config sensor (our published data)
            config_sensor = f"sensor.emhass_deferrable_load_config_{index}"
            config_state = self.hass.states.get(config_sensor)

            if config_state:
                emhass_states[config_sensor] = config_state

                if config_state.state == EMHASS_STATE_ACTIVE:
                    result["verified_trips"].append(trip_id)
                    continue

            # Also check if EMHASS has picked up the load (in response sensors)
            # EMHASS typically creates sensors like p_deferrable0, p_deferrable1, etc.
            # Get all states and check for trip_id in attributes
            all_states = self.hass.states.async_all()
            found = False
            for state in all_states:
                if state.entity_id == config_sensor:
                    continue  # Already checked
                attrs: Dict[str, Any] = state.attributes or {}
                if attrs.get("trip_id") == trip_id:
                    result["verified_trips"].append(trip_id)
                    found = True
                    break

            if not found:
                result["missing_trips"].append(trip_id)

        # Collect sensor values for our config sensors
        result["sensor_values"] = {
            entity_id: {
                "state": state.state,
                "attributes": dict(state.attributes) if state.attributes else {},
            }
            for entity_id, state in emhass_states.items()
        }

        result["all_trips_verified"] = len(result["missing_trips"]) == 0

        _LOGGER.debug(
            "EMHASS response check for %s: %d/%d trips verified",
            self.vehicle_id,
            len(result["verified_trips"]),
            len(trip_ids),
        )

        return result

    async def async_get_integration_status(self) -> Dict[str, Any]:
        """
        Get overall EMHASS integration status.

        Returns:
            Dictionary with integration status:
            - status: overall status (ok, warning, error)
            - message: human-readable status message
            - details: detailed information
        """
        details = {}

        # Verify integration
        verification = await self.async_verify_shell_command_integration()
        details["verification"] = verification

        # Check response sensors
        response_check = await self.async_check_emhass_response_sensors()
        details["response_check"] = response_check

        # Determine overall status
        if not verification["deferrable_sensor_exists"]:
            status = EMHASS_STATE_ERROR
            message = "Deferrable sensor not found. Configure shell command."
        elif not verification["deferrable_sensor_has_data"]:
            status = "warning"
            message = "Deferrable sensor has no data. Add trips to publish."
        elif not verification["is_configured"]:
            status = "warning"
            message = "Shell command may not be configured."
        elif not response_check["all_trips_verified"]:
            status = "warning"
            missing = len(response_check["missing_trips"])
            message = f"EMHASS not responding to {missing} trip(s)."
        else:
            status = EMHASS_STATE_READY
            message = "EMHASS integration working correctly."

        return {
            "status": status,
            "message": message,
            "vehicle_id": self.vehicle_id,
            "details": details,
        }

    async def async_notify_error(
        self,
        error_type: str,
        message: str,
        trip_id: Optional[str] = None,
    ) -> bool:
        """
        Send notification about EMHASS integration error.

        This method:
        - Logs the error at appropriate HA level (WARNING or ERROR)
        - Sends notification via configured notification service
        - Updates dashboard status sensor
        - Stores error for later reference

        Args:
            error_type: Type of error (emhass_unavailable, sensor_missing, etc.)
            message: Human-readable error message
            trip_id: Optional trip ID related to the error

        Returns:
            True if notification sent successfully, False otherwise
        """
        # Store error for reference
        self._last_error = message
        self._last_error_time = datetime.now()

        # Log at appropriate level based on error type
        if error_type in ["emhass_unavailable", "critical"]:
            _LOGGER.error(
                "EMHASS error for vehicle %s [%s]: %s%s",
                self.vehicle_id,
                error_type,
                message,
                f" (trip: {trip_id})" if trip_id else "",
            )
        else:
            _LOGGER.warning(
                "EMHASS warning for vehicle %s [%s]: %s%s",
                self.vehicle_id,
                error_type,
                message,
                f" (trip: {trip_id})" if trip_id else "",
            )

        # Update dashboard status sensor
        await self._async_update_error_status(error_type, message, trip_id)

        # Send notification if configured
        return await self._async_send_error_notification(error_type, message, trip_id)

    async def _async_update_error_status(
        self,
        error_type: str,
        message: str,
        trip_id: Optional[str] = None,
    ) -> None:
        """Update dashboard status sensor with error information."""
        attributes = {
            "power_profile_watts": [0.0] * 168,
            "deferrables_schedule": [],
            "vehicle_id": self.vehicle_id,
            "trips_count": 0,
            "emhass_status": EMHASS_STATE_ERROR,
            "error_type": error_type,
            "error_message": message,
            "error_time": datetime.now().isoformat(),
            # FR-1.2: Add entry_id for orphan detection (matches publish_deferrable_loads)
            "entry_id": self.entry_id,
        }

        if trip_id:
            attributes["error_trip_id"] = trip_id

        # PHASE 3 REMOVED (3.1): Remove dual-writing path - data via coordinator
        #     sensor_id,
        #     EMHASS_STATE_ERROR,
        #     attributes,
        # )

        _LOGGER.debug(
            "Updated dashboard status for vehicle %s: error=%s",
            self.vehicle_id,
            error_type,
        )

    async def _async_send_error_notification(
        self,
        error_type: str,
        message: str,
        trip_id: Optional[str] = None,
    ) -> bool:
        """
        Send error notification via configured notification service.

        Args:
            error_type: Type of error
            message: Error message to send
            trip_id: Optional trip ID

        Returns:
            True if notification sent successfully
        """
        if not self.notification_service:
            _LOGGER.debug(
                "No notification service for %s, skipping",
                self.vehicle_id,
            )
            return False

        # Build notification message
        title = f"⚠️ EV Trip Planner - EMHASS Error: {self.vehicle_id}"

        # Detailed message based on error type
        if error_type == "emhass_unavailable":
            body = (
                "EMHASS no está disponible.\n\n"
                f"Mensaje: {message}\n\n"
                "El viaje se ha guardado pero NO tiene carga diferible en EMHASS. "
                "Revisión manual requerida."
            )
        elif error_type == "sensor_missing":
            body = (
                "Sensor EMHASS no encontrado.\n\n"
                f"Mensaje: {message}\n\n"
                "Verifica shell command en configuration.yaml."
            )
        elif error_type == "shell_command_failure":
            body = (
                "Error en shell command de EMHASS.\n\n"
                f"Mensaje: {message}\n\n"
                "EMHASS maneja este error."
            )
        else:
            body = f"Error: {message}"

        if trip_id:
            body += f"\n\nViaje afectado: {trip_id}"

        body += "\n\nConsulta el panel de control para más detalles."

        return await self._async_call_notification_service(title, body)

    async def _async_call_notification_service(
        self,
        title: str,
        message: str,
    ) -> bool:
        """
        Call the configured notification service.

        Args:
            title: Notification title
            message: Notification body

        Returns:
            True if notification sent successfully
        """
        if not self.notification_service:
            return False

        try:
            domain, service = self.notification_service.split(".", 1)
            await self.hass.services.async_call(
                domain,
                service,
                {
                    "title": title,
                    "message": message,
                    "notification_id": f"ev_trip_planner_emhass_{self.vehicle_id}",
                },
            )
            _LOGGER.info(
                "Error notification sent for vehicle %s: %s",
                self.vehicle_id,
                title,
            )
            return True
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Failed to send error notification for vehicle %s: %s",
                self.vehicle_id,
                err,
            )
            return False

    async def async_handle_emhass_unavailable(
        self,
        reason: str,
        trip_id: Optional[str] = None,
    ) -> bool:
        """
        Handle EMHASS API unavailability.

        When EMHASS is unavailable:
        - Trip is saved but has no deferrable load in EMHASS
        - User is notified via dashboard and notifications
        - Operation continues (trip is still managed)

        Args:
            reason: Why EMHASS is unavailable
            trip_id: Optional trip ID that was being published

        Returns:
            True if error handled successfully
        """
        message = (
            f"EMHASS API no disponible: {reason}. "
            "El viaje se ha guardado sin carga diferible - revisión manual requerida."
        )

        _LOGGER.warning(
            "EMHASS unavailable for vehicle %s: %s%s",
            self.vehicle_id,
            reason,
            f" (trip: {trip_id})" if trip_id else "",
        )

        return await self.async_notify_error(
            error_type="emhass_unavailable",
            message=message,
            trip_id=trip_id,
        )

    async def async_handle_sensor_error(
        self,
        sensor_id: str,
        error_details: str,
        trip_id: Optional[str] = None,
    ) -> bool:
        """
        Handle sensor-related errors.

        Args:
            sensor_id: The sensor that has an error
            error_details: Details about the error
            trip_id: Optional trip ID

        Returns:
            True if error handled successfully
        """
        message = f"Sensor {sensor_id}: {error_details}"

        return await self.async_notify_error(
            error_type="sensor_missing",
            message=message,
            trip_id=trip_id,
        )

    async def async_handle_shell_command_failure(
        self,
        trip_id: Optional[str] = None,
    ) -> bool:
        """
        Handle shell command failure.

        Note: Shell command failures are handled by EMHASS itself.
        We only verify sensors and notify the user.

        Args:
            trip_id: Optional trip ID

        Returns:
            True if error handled successfully
        """
        message = (
            "El shell command de EMHASS ha fallado. "
            "EMHASS maneja este error. Verifica los sensores de respuesta de EMHASS "
            "para confirmar que las cargas diferibles están activas."
        )

        _LOGGER.warning(
            "Shell command failure for vehicle %s%s",
            self.vehicle_id,
            f" (trip: {trip_id})" if trip_id else "",
        )

        return await self.async_notify_error(
            error_type="shell_command_failure",
            message=message,
            trip_id=trip_id,
        )

    def get_last_error(self) -> Optional[Dict[str, Any]]:
        """
        Get the last error that occurred.

        Returns:
            Dict with error info or None if no errors
        """
        if not self._last_error:
            return None

        error_time = (
            self._last_error_time.isoformat() if self._last_error_time else None
        )
        return {
            "message": self._last_error,
            "time": error_time,
        }

    async def async_clear_error(self) -> None:
        """Clear the last error and restore normal status."""
        self._last_error = None
        self._last_error_time = None

        # Restore normal status
        sensor_id = f"sensor.emhass_perfil_diferible_{self.entry_id}"
        current_state = self.hass.states.get(sensor_id)

        if current_state:
            # Keep existing data but clear error
            attributes = dict(current_state.attributes)
            attributes.pop("error_type", None)
            attributes.pop("error_message", None)
            attributes.pop("error_time", None)
            attributes.pop("error_trip_id", None)
            attributes["emhass_status"] = EMHASS_STATE_READY

            # PHASE 3 REMOVED (3.1): Remove dual-writing path
            #     sensor_id,
            #     current_state.state,
            #     attributes,
            # )

        _LOGGER.info("Cleared error status for vehicle %s", self.vehicle_id)

    async def async_cleanup_vehicle_indices(self) -> None:
        """Clean up all EMHASS indices for this vehicle when it is deleted.

        This is a HARD cleanup - immediately releases all indices without cooldown
        since the vehicle is being deleted. Clears all deferrable load sensors.

        Called during vehicle deletion cascade to ensure no orphaned indices remain.

        Cleanup process:
        - Iterates through all trip indices and removes both state machine entities
          AND entity registry entries in a single loop for efficiency.
        - Removes the main vehicle sensor (emhass_perfil_diferible_{entry_id}).
        - Clears all internal mappings (_index_map, _published_entity_ids, etc.).

        FR-1.1: Cleans up both state entities AND entity registry entries.
        """
        # CRITICAL FIX: Set shutdown flag FIRST to prevent any update/republish
        # callbacks from interfering with cleanup. This blocks:
        # - _handle_config_entry_update reloading trips from trip_manager
        # - update_charging_power republishing with stale _published_trips
        # - Any presence_monitor callbacks triggering publish_deferrable_loads
        self._shutting_down = True
        _LOGGER.warning(
            "DEBUG EMHASS async_cleanup_vehicle_indices START: vehicle_id=%s, _shutting_down=True, _cached_per_trip_params=%d entries, _published_trips=%d, _index_map=%d entries",
            self.vehicle_id,
            len(self._cached_per_trip_params),
            len(self._published_trips),
            len(self._index_map),
        )

        from homeassistant.helpers import entity_registry as er

        # Clear all trip-to-index mappings immediately
        assigned_trips = list(self._index_map.keys())

        # Get registry for cleanup
        registry = er.async_get(self.hass)

        # FR-1.1: Consolidated cleanup - remove both state and registry entries
        # together. Iterate through all trip indices and clean up state machine
        # and entity registry
        for trip_id in assigned_trips:
            emhass_index = self._index_map.get(trip_id)
            if emhass_index is not None:
                config_sensor_id = self._get_config_sensor_id(emhass_index)
                # Remove from state machine
                try:
                    self.hass.states.async_remove(config_sensor_id)
                except HomeAssistantError as err:
                    _LOGGER.warning(
                        "Failed to remove sensor %s during vehicle cleanup: %s",
                        config_sensor_id,
                        err,
                    )
                # Remove from entity registry
                try:
                    registry.async_remove(config_sensor_id)
                except Exception as err:  # Entity may not exist or already removed
                    _LOGGER.debug(
                        "Registry async_remove failed for %s: %s",
                        config_sensor_id,
                        err,
                    )

        # Clear the main vehicle sensor from registry
        try:
            main_sensor_id = f"sensor.emhass_perfil_diferible_{self.entry_id}"
            registry.async_remove(main_sensor_id)
        except Exception as err:  # Entity may not exist or already removed
            _LOGGER.debug(
                "Registry async_remove failed for %s: %s",
                main_sensor_id,
                err,
            )

        # Hard reset: clear all mappings and released indices
        self._published_entity_ids.clear()
        self._index_map.clear()
        self._released_indices.clear()
        self._available_indices = list(range(self.max_deferrable_loads))

        # CRITICAL FIX: Clear cached EMHASS data so sensor shows empty state after deletion
        # _cached_per_trip_params drives per_trip_emhass_params in coordinator.data,
        # which EmhassDeferrableLoadSensor reads to build def_total_hours_array.
        # Without this, stale cache entries cause the sensor to still show deleted trips.
        self._cached_per_trip_params.clear()
        self._cached_power_profile = []
        self._cached_deferrables_schedule = []
        self._cached_emhass_status = None
        self._published_trips = []

        # CRITICAL FIX: After clearing cached EMHASS data, directly update coordinator.data
        # AND trigger refresh so that coordinator.data["per_trip_emhass_params"] reflects
        # the cleared cache. Without this direct update, the debounced async_refresh
        # might not run before the E2E test reads the sensor state, leaving stale data.
        coordinator = self._get_coordinator()
        if coordinator is not None:
            try:
                # Directly update coordinator.data to ensure sensor sees empty state
                # without waiting for the debounced _async_update_data to run
                # Handle case where coordinator.data might be None before first refresh
                if coordinator.data is not None:
                    coordinator.data = {
                        **coordinator.data,
                        "per_trip_emhass_params": {},
                        "emhass_power_profile": [],
                        "emhass_deferrables_schedule": [],
                        "emhass_status": EMHASS_STATE_READY,
                    }
                else:
                    coordinator.data = {
                        "per_trip_emhass_params": {},
                        "emhass_power_profile": [],
                        "emhass_deferrables_schedule": [],
                        "emhass_status": EMHASS_STATE_READY,
                    }
                _LOGGER.warning(
                    "DEBUG async_cleanup_vehicle_indices: Directly set coordinator.data "
                    "per_trip_emhass_params={} for %s",
                    self.vehicle_id,
                )
            except Exception as err:  # pragma: no cover
                _LOGGER.debug(
                    "Failed to directly update coordinator.data during cleanup: %s",
                    err,
                )
            # Do NOT call coordinator.async_refresh() here - it can cause the removed
            # entity to be re-added to hass.states. We already set coordinator.data directly.

        # Clear ALL EMHASS sensors from hass.states that belong to this vehicle
        # Search more broadly - check for any entity with "emhass_perfil_diferible" in entity_id
        # OR any entity that has our vehicle_id in its entity_id and was created by our domain
        removed_any = False
        _LOGGER.warning(
            "DEBUG async_cleanup_vehicle_indices: Searching for EMHASS sensors in hass.states. "
            "vehicle_id=%s, total entities=%d",
            self.vehicle_id,
            len(list(self.hass.states.async_entity_ids())),
        )
        for entity_id in list(self.hass.states.async_entity_ids()):
            should_remove = False
            # Check multiple conditions for matching
            if "emhass_perfil_diferible" in entity_id:
                # This is an EMHASS sensor - check if it belongs to us
                # Primary check: vehicle_id in entity_id (maintained for backwards compatibility)
                if self.vehicle_id and self.vehicle_id in entity_id:
                    should_remove = True
                # Secondary check: entry_id in entity_id (correct matching for EMHASS sensors)
                # EMHASS sensors are created with entity_id based on entry_id, not vehicle_id
                # Fixes bug where cleanup failed when vehicle_id != entry_id
                elif self.entry_id and self.entry_id in entity_id:
                    should_remove = True
            if should_remove:
                try:
                    _LOGGER.warning("DEBUG async_cleanup_vehicle_indices: Removing sensor %s from hass.states", entity_id)
                    self.hass.states.async_remove(entity_id)
                    removed_any = True
                except HomeAssistantError as err:
                    _LOGGER.warning(
                        "Failed to remove vehicle sensor %s during cleanup: %s",
                        entity_id,
                        err,
                    )
        if not removed_any:
            _LOGGER.warning(
                "DEBUG async_cleanup_vehicle_indices: No EMHASS sensor found in hass.states for vehicle_id=%s",
                self.vehicle_id,
            )

        # FINAL SAFEGUARD: If any EMHASS sensors still exist in hass.states after our cleanup,
        # directly set their state to empty to ensure def_total_hours_array = [].
        # This handles cases where the entity was re-added after removal.
        for entity_id in list(self.hass.states.async_entity_ids()):
            if "emhass_perfil_diferible" in entity_id and (self.vehicle_id and self.vehicle_id in entity_id):
                try:
                    # Directly set the state with empty attributes
                    # This forces def_total_hours_array to be empty
                    self.hass.states.async_set(
                        entity_id,
                        "ready",  # Keep a valid state
                        attributes={
                            "def_total_hours_array": [],
                            "per_trip_emhass_params": {},
                            "power_profile_watts": [],
                            "deferrables_schedule": [],
                            "emhass_status": EMHASS_STATE_READY,
                            "vehicle_id": self.vehicle_id,
                        }
                    )
                    _LOGGER.warning(
                        "DEBUG async_cleanup_vehicle_indices: Force-set empty state for %s",
                        entity_id,
                    )
                except Exception as err:
                    _LOGGER.warning(
                        "Failed to force-set empty state for %s: %s",
                        entity_id,
                        err,
                    )

        # CRITICAL FIX: After force-setting state on ANY existing EMHASS entities,
        # ALSO update coordinator.data ONE MORE TIME to ensure def_total_hours_array=[]
        # This handles the case where HA recreates the entity from Entity Registry
        # with OLD attributes - our updated coordinator.data will override on next refresh.
        coordinator = self._get_coordinator()
        if coordinator is not None and coordinator.data is not None:
            try:
                coordinator.data = {
                    **coordinator.data,
                    "per_trip_emhass_params": {},
                    "emhass_power_profile": [],
                    "emhass_deferrables_schedule": [],
                    "emhass_status": EMHASS_STATE_READY,
                }
                _LOGGER.warning(
                    "DEBUG async_cleanup_vehicle_indices: Reset coordinator.data keys for %s",
                    self.vehicle_id,
                )
                # Force immediate refresh so coordinator.data is propagated to sensors
                # before HA can restore entities with old attributes.
                # async_request_refresh() is NOT debounced (unlike async_refresh()).
                try:
                    await coordinator.async_request_refresh()
                    _LOGGER.warning(
                        "DEBUG async_cleanup_vehicle_indices: Triggered async_request_refresh for %s",
                        self.vehicle_id,
                    )
                except Exception as err:
                    _LOGGER.debug(
                        "async_request_refresh failed: %s (this is OK if coordinator is shutting down)",
                        err,
                    )
            except Exception as err:  # pragma: no cover
                _LOGGER.debug(
                    "Failed to reset coordinator.data keys during cleanup: %s",
                    err,
                )

        # Persist the cleared state
        await self.async_save()

        _LOGGER.info(
            "Cleaned up all EMHASS indices for vehicle %s. Released %d trip indices.",
            self.vehicle_id,
            len(assigned_trips),
        )

    def verify_cleanup(self) -> dict[str, Any]:
        """Verify cleanup state for testing.

        Returns dict with cleanup status:
        - state_clean: True if no EMHASS sensors in state machine
        - registry_clean: True if no EMHASS sensors in entity registry
        - mappings_cleared: True if _index_map is empty
        - published_ids_count: Number of published entity IDs (should be 0)

        Used in tests to verify cleanup completed successfully.
        """
        from homeassistant.helpers import entity_registry as er

        registry = er.async_get(self.hass)

        # Check state machine for EMHASS sensors (both main and per-trip config sensors)
        state_clean = True
        for state in self.hass.states.async_all("sensor"):
            entity_id = state.entity_id
            # Check for main sensor pattern
            if entity_id.startswith("sensor.emhass_perfil_diferible_"):
                if state.attributes and state.attributes.get("entry_id") == self.entry_id:
                    state_clean = False
                    break
            # Check for per-trip config sensor pattern
            if entity_id.startswith("sensor.emhass_deferrable_load_config_"):
                if state.attributes and state.attributes.get("entry_id") == self.entry_id:
                    state_clean = False
                    break

        # Check entity registry for EMHASS sensors (both main and per-trip config sensors)
        registry_clean = True
        for entity_entry in registry.entities.values():
            if entity_entry.domain == "sensor" and entity_entry.unique_id:
                # Check for main sensor pattern
                if entity_entry.unique_id.startswith(
                    f"emhass_perfil_diferible_{self.entry_id}"
                ):
                    registry_clean = False
                    break
                # Check for per-trip config sensor pattern
                if entity_entry.unique_id.startswith(
                    f"emhass_deferrable_load_config_{self.entry_id}"
                ):
                    registry_clean = False
                    break

        return {
            "state_clean": state_clean,
            "registry_clean": registry_clean,
            "mappings_cleared": len(self._index_map) == 0,
            # Track how many entity IDs were published (for monitoring)
            "published_ids_count": len(self._published_entity_ids),
        }

    def setup_config_entry_listener(self) -> None:
        """
        Subscribe to config entry updates to trigger republish when charging power changes.

        FR-3.1: When entry.data changes (e.g., charging_power_kw), we need to republish
        sensor attributes with the new values.
        """
        # Retrieve config_entry from entry_id since __init__ may receive a dict
        self.config_entry = self.hass.config_entries.async_get_entry(self.entry_id)
        if not self.config_entry:
            _LOGGER.warning(
                "Config entry %s not found for listener setup",
                self.entry_id,
            )
            return

        # Use ConfigEntry.add_update_listener pattern per HA best practices
        self._config_entry_listener = (
            self.config_entry.async_on_unload(
                self.config_entry.add_update_listener(self._handle_config_entry_update)
            )
        )

    async def _handle_config_entry_update(self, hass: HomeAssistant, config_entry) -> None:
        """
        Handle config entry update events.

        Detects changes to charging_power, t_base, and SOH sensor.
        FR-3, AC-1.3: Reload trips from trip_manager if _published_trips is empty.
        T064: Compare t_base and SOH sensor changes to trigger republish.
        """
        # CRITICAL FIX: Skip if shutting down - prevents re-publish during deletion
        shutting_down = getattr(self, "_shutting_down", False)
        _LOGGER.warning(
            "DEBUG _handle_config_entry_update START: vehicle_id=%s, _shutting_down=%s, _published_trips=%d, _cached_per_trip_params=%d",
            self.vehicle_id,
            shutting_down,
            len(self._published_trips),
            len(getattr(self, "_cached_per_trip_params", {})),
        )
        if shutting_down:
            _LOGGER.warning(
                "DEBUG _handle_config_entry_update: SKIPPING - shutting down, returning early"
            )
            return

        # T064: Compare current config values against stored baseline to detect changes
        cur_options = dict(getattr(config_entry, "options", {}) or {})
        changed_params = []
        new_charging_power = cur_options.get(CONF_CHARGING_POWER)
        if new_charging_power is not None and new_charging_power != self._stored_charging_power_kw:
            changed_params.append("charging_power")
        new_t_base = cur_options.get(CONF_T_BASE, DEFAULT_T_BASE)
        if new_t_base != self._stored_t_base:
            changed_params.append("t_base")
        new_soh = cur_options.get(CONF_SOH_SENSOR, DEFAULT_SOH_SENSOR)
        if new_soh != self._stored_soh_sensor:
            changed_params.append("soh_sensor")

        _LOGGER.info(
            "Config entry updated for vehicle %s, changed params: %s (t_base %s→%s, SOH %s→%s)",
            self.vehicle_id,
            changed_params,
            self._stored_t_base,
            new_t_base,
            self._stored_soh_sensor,
            new_soh,
        )

        # FR-3, AC-1.3: If no published trips, reload from trip_manager
        if not self._published_trips:
            coordinator = self._get_coordinator()
            if coordinator is not None and hasattr(coordinator, "_trip_manager"):
                trip_manager = coordinator._trip_manager
                if trip_manager is not None:
                    all_trips = trip_manager.get_all_trips()
                    if all_trips:
                        # Flatten dict: {"recurring": [...], "punctual": [...]} → list of trips
                        all_trips_list = (
                            all_trips.get("recurring", []) + all_trips.get("punctual", [])
                        )
                        _LOGGER.info(
                            "Reloading %d trips from trip_manager for republish",
                            len(all_trips_list),
                        )
                        self._published_trips = all_trips_list

        await self.update_charging_power()

    async def update_charging_power(self) -> None:
        """
        Update charging power and republish sensor attributes if changed.

        FR-3.1/FR-3.2: Called when config entry is updated. Compares new power with
        stored value and republishes only if power actually changed.
        """
        # CRITICAL FIX: Skip if shutting down - prevents republish during deletion
        if self._shutting_down:
            _LOGGER.debug(
                "Skipping update_charging_power for %s - shutting down",
                self.vehicle_id,
            )
            return

        # Get current entry to fetch updated charging_power_kw
        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        if not entry:
            _LOGGER.warning("Config entry %s not found", self.entry_id)
            return

        # FR-1, AC-1.1: Read from options first, fallback to data
        # Use `is None` check (NOT `or`) to correctly handle `charging_power_kw=0` edge case
        new_power = entry.options.get("charging_power_kw")
        if new_power is None:
            new_power = entry.data.get("charging_power_kw")
        if new_power is None:
            _LOGGER.warning("charging_power_kw not found in config entry")
            return

        # Only republish if power actually changed
        if new_power == self._charging_power_kw:
            _LOGGER.debug("Charging power unchanged, skipping republish")
            return

        _LOGGER.info(
            "Charging power changed from %s to %s kW, republishing sensor attributes",
            self._charging_power_kw,
            new_power,
        )

        # Update internal power value
        self._charging_power_kw = new_power

        # FR-3.1: Republish with stored trips and new charging power
        # This recalculates power_profile_watts with the updated charging power
        await self.publish_deferrable_loads(self._published_trips, new_power)

    def _calculate_power_profile_from_trips(
        self,
        trips: List[Dict[str, Any]],
        charging_power_kw: float,
        planning_horizon_hours: int = 168,
        soc_current: Optional[float] = None,
        battery_capacity_kwh: Optional[float] = None,
        safety_margin_percent: float = DEFAULT_SAFETY_MARGIN,
    ) -> List[float]:
        """
        Calculate power profile from trips.
 
        Delegates to the pure function from calculations.py.
 
        Args:
            trips: List of trip dictionaries
            charging_power_kw: Charging power in kW
            planning_horizon_hours: Number of hours in the profile
            soc_current: Current SOC percentage (optional, for SOC-aware charging)
            battery_capacity_kwh: Battery capacity in kWh (optional, for SOC-aware charging)
            safety_margin_percent: Safety margin percentage (optional, for SOC-aware charging)
 
        Returns:
            List of power values in watts
        """
        return calculate_power_profile_from_trips(
            trips, charging_power_kw, horizon=planning_horizon_hours,
            reference_dt=dt_util.now(),
            soc_current=soc_current,
            battery_capacity_kwh=battery_capacity_kwh,
            safety_margin_percent=safety_margin_percent,
            tz=getattr(self, 'hass', None) and self.hass.config.time_zone,
        )

    def _generate_schedule_from_trips(
        self,
        trips: List[Dict[str, Any]],
        charging_power_kw: float,
    ) -> List[Dict[str, Any]]:
        """
        Generate deferrables schedule from trips.

        Delegates to the pure function from calculations.py.

        Format:
            [{"date": "2026-03-17T14:00:00+01:00", "p_deferrable0": "0.0"}, ...]

        Args:
            trips: List of trip dictionaries
            charging_power_kw: Charging power in kW

        Returns:
            List of schedule dictionaries
        """
        return generate_deferrable_schedule_from_trips(
            trips, charging_power_kw, reference_dt=dt_util.now(),
        )

    async def _get_current_soc(self) -> float | None:
        """Get current SOC from configured sensor.

        Component 1 helper for per-trip params cache.

        Returns:
            SOC percentage as float, or None if sensor unavailable.
        """
        # Use stored dict for soc_sensor access (works for dict, ConfigEntry, MockConfigEntry)
        entry_data = getattr(self, "_entry_dict", None)
        if not entry_data:  # pragma: no cover - defensive: entry data should always exist
            _LOGGER.warning("No entry data available for %s", self.vehicle_id)
            return None

        soc_sensor = entry_data.get("soc_sensor") if entry_data else None
        if not soc_sensor:  # pragma: no cover - defensive: soc_sensor always configured
            _LOGGER.warning("soc_sensor not configured for %s", self.vehicle_id)
            return None

        state = self.hass.states.get(soc_sensor)
        if state is None:  # pragma: no cover - defensive: sensor always exists
            _LOGGER.warning("SOC sensor %s not found", soc_sensor)
            return None

        try:
            return float(state.state)
        except (ValueError, TypeError) as e:  # pragma: no cover - defensive: invalid value
            _LOGGER.warning(
                "SOC sensor %s has invalid value: %s (error: %s)",
                soc_sensor,
                state.state,
                e,
            )
            return None

    async def _get_hora_regreso(self) -> datetime | None:
        """Get return time from presence_monitor.

        Component 1 helper for per-trip params cache.

        Returns:
            datetime of expected return time, or None if unavailable.
        """
        if self._presence_monitor is None:
            _LOGGER.warning("No presence_monitor configured for %s", self.vehicle_id)
            return None

        # Real API: async_get_hora_regreso() (not get_return_time)
        return await self._presence_monitor.async_get_hora_regreso()
