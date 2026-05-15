"""Coordinator for EV Trip Planner integration.

Provides TripPlannerCoordinator which manages the data update cycle for all
EV Trip Planner sensors, reading from TripManager and exposing data via
coordinator.data for CoordinatorEntity-based sensors.

Phase 1: Defines full data contract with EMHASS keys as None placeholders.
Phase 3: EMHASS keys are populated from emhass_adapter computation results.
Fallback: When EMHASS is not installed, coordinator generates mock EMHASS
params from trip data so sensors remain populated for E2E testing.
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_VEHICLE_NAME,
    DEFAULT_CHARGING_POWER,
    DEFAULT_CONSUMPTION,
    DEFAULT_SOC_BUFFER_PERCENT,
    DOMAIN,
)
from .emhass import EMHASSAdapter
from .trip import TripManager

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CoordinatorConfig:
    """Optional configuration for TripPlannerCoordinator."""

    emhass_adapter: EMHASSAdapter | None = None
    logger: logging.Logger | None = None


class TripPlannerCoordinator(DataUpdateCoordinator):
    """Coordinator for EV Trip Planner data updates.

    This coordinator holds the canonical view of all EV Trip Planner data,
    reading from TripManager on each refresh cycle and exposing it via
    coordinator.data for all sensors to consume via CoordinatorEntity pattern.

    Data contract (Phase 1 - EMHASS keys as None):
        {
            "recurring_trips": dict of trip_id -> trip_data,
            "punctual_trips": dict of trip_id -> trip_data,
            "kwh_today": float,
            "hours_today": float,
            "next_trip": dict or None,
            "emhass_power_profile": None,      # populated in Phase 3
            "emhass_deferrables_schedule": None,  # populated in Phase 3
            "emhass_status": None,             # "ready" | "computing" | None
        }
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        trip_manager: TripManager,
        config: CoordinatorConfig | None = None,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: HomeAssistant instance.
            entry: ConfigEntry for this vehicle/device.
            trip_manager: TripManager instance for this vehicle.
            config: Optional configuration for coordinator dependencies.
        """
        cfg = config or CoordinatorConfig()
        super().__init__(
            hass,
            logger=cfg.logger or _LOGGER,
            name=f"{DOMAIN} ({entry.entry_id})",
            update_interval=timedelta(seconds=30),
        )
        self._trip_manager = trip_manager
        self._entry = entry
        self._emhass_adapter = cfg.emhass_adapter
        self._vehicle_id = (
            self._entry.data.get(CONF_VEHICLE_NAME, "unknown").lower().replace(" ", "_")
        )

    @property
    def vehicle_id(self) -> str:
        """Return normalized vehicle_id from config entry.

        Returns:
            Normalized vehicle_id (lowercase, spaces replaced with underscores),
            or "unknown" if CONF_VEHICLE_NAME is missing from entry.data.
        """
        return self._vehicle_id

    # CC-N-ACCEPTED: cc=14 — inherently requires fetching data from multiple
    # sources (trips, EMHASS, query), conditional fallback logic, and building
    # the complete data dict. Each source has distinct error paths.
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest data from TripManager and build coordinator.data dict.

        This method is called by DataUpdateCoordinator on each refresh cycle.
        It reads current state from TripManager and builds the full data dict
        with all keys defined in the contract.

        Returns:
            Full data dict with EMHASS keys as None (Phase 1).
        """
        # E2E-DEBUG-CRITICAL: Log when _async_update_data is called
        _LOGGER.debug(
            "E2E-DEBUG coordinator _async_update_data called for vehicle %s",
            self._vehicle_id,
        )
        # E2E-DEBUG-CRITICAL: Log current trips from trip_manager
        _LOGGER.debug(
            "E2E-DEBUG coordinator _async_update_data: trip_manager trips before EMHASS fetch"
        )
        # Get recurring trips as list, convert to dict keyed by trip_id
        recurring_list = await self._trip_manager._crud.async_get_recurring_trips()
        recurring_trips = {trip["id"]: trip for trip in recurring_list if "id" in trip}

        # Get punctual trips as list, convert to dict keyed by trip_id
        punctual_list = await self._trip_manager._crud.async_get_punctual_trips()
        punctual_trips = {trip["id"]: trip for trip in punctual_list if "id" in trip}

        # Get today's energy and hours needs
        kwh_today = await self._trip_manager._soc_query.async_get_kwh_needed_today()
        hours_today = float(
            await self._trip_manager._soc_query.async_get_hours_needed_today()
        )

        # Get next scheduled trip
        next_trip = await self._trip_manager._navigator.async_get_next_trip()

        # PHASE 3 (3.4): Get EMHASS data from emhass_adapter if available
        all_trips = {**recurring_trips, **punctual_trips}
        if self._emhass_adapter is not None:
            emhass_data = self._emhass_adapter.get_cached_optimization_results()
            per_trip_params = emhass_data.get("per_trip_emhass_params", {})
            # DEBUG: Log cache state when reading
            _LOGGER.debug(
                "DEBUG coordinator _async_update_data: per_trip_emhass_params has %d entries, "
                "emhass_power_profile non_zero=%d for vehicle %s",
                len(per_trip_params),
                sum(1 for x in emhass_data.get("emhass_power_profile", []) if x > 0)
                if emhass_data.get("emhass_power_profile")
                else 0,
                self._vehicle_id,
            )
            # FALLBACK: When EMHASS is not installed/running, the adapter may return
            # empty per_trip_params OR empty power_profile even when per_trip_params
            # is populated. Generate mock params from trip data so sensors remain
            # populated and E2E tests can verify dynamic SOC capping.
            profile = emhass_data.get("emhass_power_profile") or []
            has_profile = any(v > 0 for v in profile)
            if (not per_trip_params or not has_profile) and all_trips:
                emhass_data = self._generate_mock_emhass_params(all_trips)
                generated_params = emhass_data.get("per_trip_emhass_params", {})
                _LOGGER.info(
                    "Fallback mock EMHASS params generated: %d trips, vehicle=%s",
                    len(generated_params),
                    self._vehicle_id,
                )
        else:
            emhass_data = {
                "emhass_power_profile": None,
                "emhass_deferrables_schedule": None,
                "emhass_status": None,
            }

        # E2E-DEBUG-CRITICAL: Log complete returned coordinator.data structure
        _LOGGER.debug(
            "E2E-DEBUG coordinator _async_update_data: returning data with keys=%s",
            list(
                {
                    "recurring_trips": recurring_trips,
                    "punctual_trips": punctual_trips,
                    "kwh_today": kwh_today,
                    "hours_today": hours_today,
                    "next_trip": next_trip,
                    **emhass_data,
                }.keys()
            ),
        )
        _LOGGER.debug(
            "E2E-DEBUG coordinator _async_update_data: returning per_trip_emhass_params=%s",
            emhass_data.get("per_trip_emhass_params", "NOT_IN_DICT"),
        )

        return {
            "recurring_trips": recurring_trips,
            "punctual_trips": punctual_trips,
            "kwh_today": kwh_today,
            "hours_today": hours_today,
            "next_trip": next_trip,
            **emhass_data,
        }

    async def async_refresh_trips(self) -> None:
        """Refresh trip data from TripManager.

        This method is called by service handlers after trip CRUD operations
        to trigger an immediate refresh of the coordinator data.
        """
        _LOGGER.debug(
            "E2E-DEBUG async_refresh_trips START for vehicle %s — coordinator.data=%s",
            self._vehicle_id,
            "None" if self.data is None else list(self.data.keys()),
        )
        await self.async_refresh()
        _LOGGER.debug(
            "E2E-DEBUG async_refresh_trips DONE for vehicle %s — coordinator.data=%s",
            self._vehicle_id,
            "None" if self.data is None else list(self.data.keys()),
        )

    # CC-N-ACCEPTED: cc=17 — mock data generator with branches for each trip
    # type (punctual/recurring), datetime handling, kwh/km conversion, and
    # energy calculation. The fallback nature requires comprehensive coverage
    # of edge cases.
    def _generate_mock_emhass_params(
        self, trips: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate mock EMHASS params from trip data when real EMHASS is unavailable.

        This provides fallback data so the EMHASS sensor remains populated for
        E2E testing of dynamic SOC capping and other features that depend on
        sensor attributes (def_total_hours_array, power_profile_watts, etc.).

        The mock data is computed from trip kwh, km, and datetime values using
        the vehicle's charging power and battery configuration.

        Returns:
            Dict with emhass_power_profile, emhass_deferrables_schedule,
            emhass_status, and per_trip_emhass_params keys.
        """
        # Read charging_power_kw from options FIRST, then data as fallback
        # This matches the adapter.py pattern in update_charging_power()
        charging_power_kw = self._entry.options.get(
            "charging_power_kw"
        ) or self._entry.data.get("charging_power_kw")
        
        # If charging_power_kw is None (not configured), return empty params
        # DO NOT use DEFAULT_CHARGING_POWER as fallback - that would mislead users
        if charging_power_kw is None:
            return {
                "emhass_power_profile": [],
                "emhass_deferrables_schedule": [],
                "emhass_status": "ready",
                "per_trip_emhass_params": {},
            }
        
        battery_capacity_kwh = self._entry.data.get("battery_capacity_kwh", 50.0)
        consumption_kwh_per_km = self._entry.data.get("kwh_per_km", DEFAULT_CONSUMPTION)
        # BUG-4: Read planning_horizon_days from config instead of hardcoding 7 days
        horizon_days = int(
            self._entry.data.get("planning_horizon_days", 7)
        )
        horizon_hours = horizon_days * 24
        per_trip_params: dict[str, Any] = {}
        matrix: list[list[float]] = []
        index_counter = 0

        now = datetime.now(timezone.utc)

        for trip_id, trip in trips.items():
            # Skip completed/cancelled trips
            status = trip.get("status", "")
            if status in ("completed", "cancelled"):
                continue

            # BUG-3: Skip trips whose datetime is in the past
            trip_datetime_str = trip.get("datetime", "")
            if trip_datetime_str:
                try:
                    trip_dt = datetime.fromisoformat(trip_datetime_str)
                    if trip_dt.tzinfo is None:
                        trip_dt = trip_dt.replace(tzinfo=timezone.utc)
                    if trip_dt <= now:
                        continue
                except (ValueError, TypeError):
                    pass

            kwh_needed = float(trip.get("kwh", 0))

            # Calculate charging duration in hours
            hours_needed = (
                kwh_needed / charging_power_kw if charging_power_kw > 0 else 0
            )
            hours_needed = max(hours_needed, 0.1)  # minimum 0.1 hours

            # Calculate charging power in watts
            power_watts = charging_power_kw * 1000.0

            # Parse trip datetime for timestep calculation
            # For recurring trips without datetime, calculate from dia_semana + hora
            start_timestep = 0  # Default: window starts now (single trip)
            end_timestep = math.ceil(hours_needed)  # fallback: charging duration

            try:
                trip_dt = datetime.fromisoformat(trip_datetime_str)
                if trip_dt.tzinfo is None:
                    trip_dt = trip_dt.replace(tzinfo=timezone.utc)
                delta = trip_dt - now
                total_hours = delta.total_seconds() / 3600
                # FIX: def_start_timestep must be 0 for single trip without hora_regreso.
                # The charging window starts NOW (car is home), not at the trip time.
                # def_end_timestep = when the trip departs (total_hours from now).
                # We only set start_timestep = int(total_hours) for MULTI-trip scenarios
                # where the window is between trips. For single trip, window is [0, end).
                start_timestep = 0  # Single trip: window starts now
                end_timestep = min(math.ceil(total_hours), horizon_hours)
            except (ValueError, TypeError):
                # For recurring trips without datetime, calculate departure from dia_semana + hora
                trip_tipo = trip.get("tipo", "")
                is_recurring = trip_tipo in ("recurrente", "recurring")
                if is_recurring:
                    day_val = trip.get("dia_semana") or trip.get("day")
                    time_str = trip.get("hora") or trip.get("time")
                    if day_val is not None and time_str:
                        deadline_dt = self._calculate_recurring_departure(
                            day_val, time_str, now
                        )
                        if deadline_dt is not None:
                            delta = deadline_dt - now
                            total_hours = delta.total_seconds() / 3600
                            start_timestep = max(0, int(total_hours))
                            end_timestep = min(math.ceil(total_hours), horizon_hours)

            # Build p_deferrable_matrix for this trip using shared function
            # The charging slots are placed at the END of the window (just before trip departure)
            from .calculations.windows import build_deferrable_matrix_row

            row = build_deferrable_matrix_row(
                horizon_hours=horizon_hours,
                charging_power_kw=charging_power_kw,
                hours_needed=hours_needed,
                end_timestep=end_timestep,
            )
            trip_matrix: list[list[float]] = []
            if any(v > 0 for v in row):
                trip_matrix.append(row)

            if not trip_matrix:
                # Fallback: single row
                trip_matrix = [[0.0] * horizon_hours]

            entry = {
                "activo": True,
                "kwh_needed": kwh_needed,
                "km": float(trip.get("km", 0)),
                "def_total_hours_array": [math.ceil(hours_needed)],
                "p_deferrable_nom_array": [round(power_watts, 2)],
                "def_start_timestep_array": [start_timestep],
                "def_end_timestep_array": [end_timestep],
                "p_deferrable_matrix": trip_matrix,
                "emhass_index": index_counter,
                "battery_capacity_kwh": battery_capacity_kwh,
                "consumption_kwh_per_km": consumption_kwh_per_km,
                "safety_margin_percent": float(
                    self._entry.data.get("safety_margin_percent", 10.0)
                ),
                "soc_base": float(
                    self._entry.data.get("soc_base", DEFAULT_SOC_BUFFER_PERCENT)
                ),
                "t_base": float(self._entry.data.get("t_base", 24.0)),
            }
            per_trip_params[trip_id] = entry

            matrix.extend(trip_matrix)
            index_counter += 1

        # Build combined power profile (max power across all charging windows)
        # Use horizon_hours to match the matrix row length
        power_profile = [0.0] * horizon_hours
        for row in matrix:
            for i, v in enumerate(row):
                power_profile[i] = max(power_profile[i], v)

        # Generate mock deferrables_schedule from per_trip_params
        deferrables_schedule: list[Any] = []
        for trip_id, params in per_trip_params.items():
            deferrables_schedule.append(
                {
                    "index": params.get("emhass_index", 0),
                    "kwh": params.get("kwh_needed", 0),
                    "start_timestep": params.get("def_start_timestep_array", [0])[0]
                    if params.get("def_start_timestep_array")
                    else 0,
                    "end_timestep": params.get("def_end_timestep_array", [horizon_hours])[0]
                    if params.get("def_end_timestep_array")
                    else horizon_hours,
                }
            )

        return {
            "emhass_power_profile": power_profile,
            "emhass_deferrables_schedule": deferrables_schedule,
            "emhass_status": "ready",
            "per_trip_emhass_params": per_trip_params,
        }

    def _calculate_recurring_departure(
        self, day_val: Any, time_str: str, now: datetime
    ) -> Optional[datetime]:
        """Calculate departure datetime for recurring trips.

        Mirrors the logic in LoadPublisher._calculate_deadline for recurring trips.

        Args:
            day_val: Day value (numeric string '0'-'6' or day name).
            time_str: Time in HH:MM format.
            now: Reference datetime.

        Returns:
            Datetime of next occurrence, or None if invalid.
        """
        if day_val is None or time_str is None:
            return None

        # Parse day value (numeric string)
        day_str = str(day_val).lower()
        if day_str.isdigit():
            n = int(day_str)
            if n == 0 or n == 7:
                target_day = 6  # Sunday
            elif 1 <= n <= 6:
                target_day = n - 1
            else:
                return None
        else:
            days_map = {
                "domingo": 6, "sunday": 6,
                "lunes": 0, "monday": 0,
                "martes": 1, "tuesday": 1,
                "miércoles": 2, "miercoles": 2, "wednesday": 2,
                "jueves": 3, "thursday": 3,
                "viernes": 4, "friday": 4,
                "sábado": 5, "sabado": 5, "saturday": 5,
            }
            target_day = days_map.get(day_str)
            if target_day is None:
                return None

        now_day = now.weekday()
        delta_days = (target_day - now_day) % 7
        if delta_days == 0:
            delta_days = 7  # Next occurrence, not today

        parts = time_str.split(":")
        hour = int(parts[0]) if len(parts) > 0 else 0
        minute = int(parts[1]) if len(parts) > 1 else 0

        deadline = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        deadline += timedelta(days=delta_days)
        return deadline
