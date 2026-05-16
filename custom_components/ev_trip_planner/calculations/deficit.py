"""Deficit and scheduling calculation functions extracted from calculations_orig.py.

Extracted from the legacy calculations.py god module as part of the
SOLID decomposition (Spec 3). These functions handle SOC deficit
propagation, charging decisions, and recurring datetime calculations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..const import DEFAULT_SAFETY_MARGIN
from . import _helpers
from . import _helpers
from .core import calculate_soc_target, calculate_trip_time
from .windows import calculate_energy_needed

# =============================================================================
# CHARGING DECISION
# =============================================================================


@dataclass
class ChargingDecision:
    """Immutable charging decision for a single trip.

    Encapsulates the decision logic for whether and how much to charge,
    extracted from EMHASSAdapter._populate_per_trip_cache_entry for SOLID SRP.
    """

    trip_id: str
    kwh_needed: float  # Energy to charge (0 = no charge needed)
    def_total_hours: int  # Hours of charging needed
    power_watts: float  # Charging power (0 = no charge)
    needs_charging: bool  # Whether charging is needed


def determine_charging_need(
    trip: Dict[str, Any],
    soc_current: float,
    battery_capacity_kwh: float,
    charging_power_kw: float,
    safety_margin_percent: float = DEFAULT_SAFETY_MARGIN,
) -> ChargingDecision:
    """Pure function: determine if and how much to charge for a trip.

    Uses calculate_energy_needed() internally (which guarantees post-trip safety margin).

    Args:
        trip: Dictionary with trip data (kwh or km, datetime, tipo, etc.)
        soc_current: Current SOC in percentage (0-100)
        battery_capacity_kwh: Battery capacity in kWh
        charging_power_kw: Charging power in kW
        safety_margin_percent: Safety margin percentage (default from const)

    Returns:
        ChargingDecision with kwh_needed=0 if SOC is sufficient.
    """
    trip_id = trip.get("id", "unknown")

    energia_info = calculate_energy_needed(
        trip,
        battery_capacity_kwh,
        soc_current,
        charging_power_kw,
        safety_margin_percent=safety_margin_percent,
    )
    kwh_needed = energia_info["energia_necesaria_kwh"]

    needs_charging = kwh_needed > 0

    if needs_charging:
        total_hours = (
            int(math.ceil(kwh_needed / charging_power_kw))
            if charging_power_kw > 0
            else 0
        )
        power_watts = _helpers.kw_to_watts(charging_power_kw)
    else:
        total_hours = 0
        power_watts = 0.0

    return ChargingDecision(
        trip_id=trip_id,
        kwh_needed=kwh_needed,
        def_total_hours=total_hours,
        power_watts=power_watts,
        needs_charging=needs_charging,
    )


# Re-export the original functions for import path compatibility.
# These are delegated to the windows module implementations.
__all__ = [
    "ChargingDecision",
    "calculate_deficit_propagation",
    "calculate_energy_needed",
    "calculate_hours_deficit_propagation",
    "calculate_next_recurring_datetime",
    "calculate_soc_at_trip_starts",
    "determine_charging_need",
]


# =============================================================================
# PURE: Deficit propagation (core of calcular_hitos_soc)
# =============================================================================


def _compute_adjusted_soc(
    original_idx: int,
    soc_objetivo_base: float,
    deficits: List[float],
    soc_caps: Optional[List[float]],
) -> float:
    """Compute the final adjusted SOC target for a single trip.

    Adjusts the base SOC target by accumulated deficits, then applies
    any SOC cap constraint for this trip.
    """
    soc_objetivo_ajustado = soc_objetivo_base + deficits[original_idx]

    if soc_caps is not None and original_idx < len(soc_caps):
        return min(soc_objetivo_ajustado, soc_caps[original_idx])
    return soc_objetivo_ajustado


def _get_soc_objetivo_base(
    original_idx: int,
    trip: Dict[str, Any],
    soc_targets: Optional[List[float]],
    battery_capacity_kwh: float,
) -> float:
    """Get the base SOC target for a trip (from soc_targets or calculated)."""
    if soc_targets and original_idx < len(soc_targets):
        return soc_targets[original_idx]
    return calculate_soc_target(trip, battery_capacity_kwh)


def _propagate_deficits(
    ordered_to_idx: Dict[int, int],
    N: int,
    soc_data: List[Dict[str, Any]],
    windows: List[Dict[str, Any]],
    trips: List[Dict[str, Any]],
    soc_targets: Optional[List[float]],
    soc_caps: Optional[List[float]],
    tasa_carga_soc: float,
    battery_capacity_kwh: float,
    deficits: List[float],
) -> None:
    """Reverse pass: detect deficits and propagate to previous trips.

    Iterates trips in reverse order (last to first). For each trip,
    if the SOC after charging is below the target, the deficit is
    propagated to the previous trip.
    """
    for ordered_idx in range(N - 1, -1, -1):
        original_idx = ordered_to_idx.get(ordered_idx)
        if original_idx is None:
            continue

        soc_data_item = soc_data[ordered_idx]
        ventana = windows[ordered_idx]
        trip = trips[original_idx]

        soc_objetivo_base = _get_soc_objetivo_base(
            original_idx, trip, soc_targets, battery_capacity_kwh
        )
        soc_objetivo_final = _compute_adjusted_soc(
            original_idx, soc_objetivo_base, deficits, soc_caps
        )
        capacidad_carga = tasa_carga_soc * ventana["ventana_horas"]

        if soc_data_item["soc_inicio"] + capacidad_carga < soc_objetivo_final:
            deficit = soc_objetivo_final - (soc_data_item["soc_inicio"] + capacidad_carga)

            if ordered_idx > 0:
                prev_idx = ordered_to_idx.get(ordered_idx - 1)
                if prev_idx is not None:
                    deficits[prev_idx] += deficit

            deficits[original_idx] += deficit


def _build_milestone(
    original_idx: int,
    trip: Dict[str, Any],
    soc_data_item: Dict[str, Any],
    ventana: Dict[str, Any],
    soc_objetivo_final: float,
    deficits: List[float],
    soc_caps: Optional[List[float]],
    kwh_necesarios: float,
) -> Dict[str, Any]:
    """Build a single SOC milestone result dict."""
    return {
        "trip_id": trip.get("id", f"trip_{original_idx}"),
        "soc_objetivo": round(soc_objetivo_final, 2),
        "soc_cap_raw": (
            round(soc_caps[original_idx], 2)
            if soc_caps is not None and original_idx < len(soc_caps)
            else 100.0
        ),
        "kwh_necesarios": round(max(0.0, kwh_necesarios), 3),
        "deficit_acumulado": round(deficits[original_idx], 2),
        "ventana_carga": {
            "ventana_horas": ventana["ventana_horas"],
            "kwh_necesarios": ventana["kwh_necesarios"],
            "horas_carga_necesarias": ventana["horas_carga_necesarias"],
            "inicio_ventana": ventana["inicio_ventana"],
            "fin_ventana": ventana["fin_ventana"],
            "es_suficiente": ventana["es_suficiente"],
        },
    }


def _compute_trip_trip_time(
    trip: Dict[str, Any],
    trip_times: Optional[List[Optional[datetime]]],
    reference_dt: datetime,
) -> Optional[datetime]:
    """Resolve a trip's departure time from various datetime formats."""
    if trip_times is not None:
        idx = int(trip.get("emhass_index", 0))
        if idx < len(trip_times) and trip_times[idx] is not None:
            return trip_times[idx]

    trip_tipo = trip.get("tipo")
    hora = trip.get("hora")
    dia_semana = trip.get("dia_semana")
    datetime_str = trip.get("datetime")

    if trip_tipo is None:
        return None
    return calculate_trip_time(trip_tipo, hora, dia_semana, datetime_str, reference_dt)


def calculate_deficit_propagation(
    trips: List[Dict[str, Any]],
    soc_data: List[Dict[str, Any]],
    windows: List[Dict[str, Any]],
    tasa_carga_soc: float,
    battery_capacity_kwh: float,
    reference_dt: datetime,
    trip_times: Optional[List[Optional[datetime]]] = None,
    soc_targets: Optional[List[float]] = None,
    soc_caps: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    """Calculate SOC milestones with backward deficit propagation.

    This is the pure core of calcular_hitos_soc. It implements the
    deficit detection and propagation algorithm:
    1. Sorts trips by departure time (earliest first)
    2. Iterates in REVERSE order (last trip to first)
    3. For each trip: if soc_inicio + capacidad_carga < soc_objetivo,
       the deficit is propagated to the previous trip
    4. Returns adjusted SOC targets and accumulated deficits

    Args:
        trips: List of trip dicts (unsorted or sorted by caller)
        soc_data: List of soc_inicio data dicts (one per trip, in departure order)
        windows: List of charging windows (one per trip, in departure order)
        tasa_carga_soc: Charging rate in % SOC/hour
        battery_capacity_kwh: Battery capacity in kWh
        reference_dt: Reference datetime for trip time calculations

    Returns:
        List of SOCMilestoneResult dicts with soc_objetivo adjusted and
        deficit_acumulado for each trip.
    """
    if not trips or not soc_data or not windows:
        return []

    # Sort trips by departure time and create bidirectional index mapping
    sorted_trips_with_times: List[Tuple[datetime, int, Dict[str, Any]]] = []
    for idx, trip in enumerate(trips):
        trip_time = _compute_trip_trip_time(trip, trip_times, reference_dt)
        if trip_time:
            sorted_trips_with_times.append((trip_time, idx, trip))

    if not sorted_trips_with_times:
        return []

    sorted_trips_with_times.sort(key=lambda x: x[0])

    ordered_to_idx: Dict[int, int] = {}
    for ordered_idx, (_, original_idx, _) in enumerate(sorted_trips_with_times):
        ordered_to_idx[ordered_idx] = original_idx

    # Phase 1: Reverse pass — detect and propagate deficits
    deficits = [0.0] * len(trips)
    _propagate_deficits(
        ordered_to_idx, len(trips), soc_data, windows, trips,
        soc_targets, soc_caps, tasa_carga_soc, battery_capacity_kwh, deficits,
    )

    # Phase 2: Forward pass — build results with accumulated deficits
    results: List[Dict[str, Any]] = []
    for ordered_idx in range(len(trips)):
        original_idx = ordered_to_idx.get(ordered_idx)
        if original_idx is None:
            continue

        trip = trips[original_idx]
        soc_data_item = soc_data[ordered_idx]
        ventana = windows[ordered_idx]

        soc_objetivo_base = _get_soc_objetivo_base(
            original_idx, trip, soc_targets, battery_capacity_kwh
        )
        soc_objetivo_final = _compute_adjusted_soc(
            original_idx, soc_objetivo_base, deficits, soc_caps
        )
        soc_inicio = soc_data_item.get("soc_inicio", 0.0)
        kwh_necesarios = (soc_objetivo_final - soc_inicio) * battery_capacity_kwh / 100

        results.append(
            _build_milestone(
                original_idx, trip, soc_data_item, ventana,
                soc_objetivo_final, deficits, soc_caps, kwh_necesarios,
            )
        )

    return results


# =============================================================================
# PURE: Hours deficit propagation
# =============================================================================


def calculate_hours_deficit_propagation(
    windows: List[Dict[str, Any]],
    def_total_hours: List[float] | None = None,
) -> List[Dict[str, Any]]:
    """Walk backward from last trip to first, propagating unmet charging hours to earlier trips with spare capacity.

    For each trip (last to first):
    1. Calculate own deficit: hours needed minus hours available in window
    2. Calculate spare capacity: available hours minus assigned def_total_hours
    3. Absorb deficit from carrier using available spare
    4. Propagate remaining deficit forward to previous trip

    Args:
        windows: List of window dicts from calculate_multi_trip_charging_windows().
            Must contain: ventana_horas, horas_carga_necesarias.
        def_total_hours: Optional list of total charging hours per trip.
            If None, defaults to horas_carga_necesarias from each window.

    Returns:
        List of enriched window dicts with additional keys:
        - deficit_hours_propagated: hours absorbed from next trip (float, 2dp)
        - deficit_hours_to_propagate: remaining deficit (float, 2dp)
        - adjusted_def_total_hours: original def_total_hours + absorbed (float, 2dp)
    """
    if not windows:
        return []

    N = len(windows)
    defaults = [w["horas_carga_necesarias"] for w in windows]
    if def_total_hours is None:
        def_total_hours = defaults

    results: List[Dict[str, Any]] = [{} for _ in range(N)]
    deficit_carrier: float = 0.0

    for i in range(N - 1, -1, -1):
        ventana = windows[i]["ventana_horas"]
        horas_carga = windows[i]["horas_carga_necesarias"]
        original_def_total = def_total_hours[i]
        spare = max(0.0, ventana - original_def_total)

        absorbed = min(deficit_carrier, spare)
        deficit_carrier -= absorbed

        own_deficit = max(0.0, horas_carga - ventana)
        deficit_carrier += own_deficit

        result = dict(windows[i])
        result["deficit_hours_propagated"] = round(absorbed, 2)
        result["deficit_hours_to_propagate"] = round(deficit_carrier, 2)
        result["adjusted_def_total_hours"] = round(original_def_total + absorbed, 2)
        results[i] = result

    return results


# =============================================================================
# PURE: SOC at start of trips
# =============================================================================


def calculate_soc_at_trip_starts(
    trips: List[Dict[str, Any]],
    soc_inicial: float,
    windows: List[Dict[str, Any]],
    charging_power_kw: float,
    battery_capacity_kwh: float,
) -> List[Dict[str, Any]]:
    """Calculate SOC at the start of each trip in a chain.

    Args:
        trips: List of trip dicts (in departure time order)
        soc_inicial: Initial SOC at start of chain
        windows: List of charging windows (from calculate_multi_trip_charging_windows)
        charging_power_kw: Charging power in kW
        battery_capacity_kwh: Battery capacity in kWh

    Returns:
        List of dicts with soc_inicio, trip, arrival_soc for each trip.
    """
    if not trips or not windows:
        return []

    results = []
    soc_actual = soc_inicial

    for idx, ventana in enumerate(windows):
        trip = ventana.get("trip", trips[idx]) if idx < len(trips) else trips[-1]
        ventana_horas = ventana["ventana_horas"]
        kwh_necesarios = ventana["kwh_necesarios"]

        soc_inicio = soc_actual

        if charging_power_kw > 0 and ventana_horas > 0:
            kwh_disponibles = charging_power_kw * ventana_horas
            kwh_a_cargar = min(kwh_necesarios, kwh_disponibles)
        else:
            kwh_a_cargar = 0.0

        if battery_capacity_kwh > 0:
            soc_llegada = soc_actual + (kwh_a_cargar / battery_capacity_kwh * 100)
            soc_llegada = min(100.0, soc_llegada)
        else:
            soc_llegada = soc_actual

        results.append(
            {
                "soc_inicio": round(soc_inicio, 2),
                "trip": trip,
                "arrival_soc": round(soc_llegada, 2),
            }
        )

        soc_actual = soc_llegada

    return results


# =============================================================================
# PURE: Next recurring datetime
# =============================================================================


def _parse_day(day: int | str) -> Optional[int]:
    """Parse day of week to int, return None if invalid."""
    if day is None:
        return None
    try:
        return int(day)
    except (ValueError, TypeError):
        return None


def _parse_time(time_str: str) -> Optional[Tuple[int, int]]:
    """Parse HH:MM time string to (hour, minute) tuple."""
    if time_str is None:
        return None
    try:
        parts = time_str.split(":")
        return (int(parts[0]), int(parts[1]))
    except (ValueError, AttributeError):
        return None


def _resolve_tz(tz: Any) -> Any:
    """Normalize timezone parameter to a tzinfo instance or None."""
    if tz is None:
        return None
    if isinstance(tz, str):
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(tz)
        except (ImportError, Exception):
            return None
    if not isinstance(tz, timezone):
        import datetime as _dt
        if not isinstance(tz, _dt.tzinfo):
            return None
    return tz


def _compute_next_with_tz(
    day: int,
    hour: int,
    minute: int,
    reference_dt: datetime,
    tz: Any,
) -> datetime:
    """Compute next occurrence when a timezone is provided."""
    aware_ref = (
        reference_dt if reference_dt.tzinfo is not None
        else reference_dt.replace(tzinfo=timezone.utc)
    )
    local_ref = aware_ref.astimezone(tz)
    local_date = local_ref.date()
    candidate_local = datetime(
        local_date.year, local_date.month, local_date.day,
        hour, minute, 0, 0, tzinfo=tz,
    )
    current_day = local_ref.isoweekday() % 7
    days_ahead = (day - current_day) % 7
    if days_ahead == 0 and candidate_local < local_ref:
        days_ahead = 7
    result_local = candidate_local + timedelta(days=days_ahead)
    return result_local.astimezone(timezone.utc)


def _compute_next_naive(
    day: int,
    hour: int,
    minute: int,
    reference_dt: datetime,
) -> datetime:
    """Compute next occurrence without timezone (backward compat)."""
    candidate = reference_dt.replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    current_day = (reference_dt.weekday() + 1) % 7
    days_ahead = (day - current_day) % 7
    if days_ahead == 0 and candidate < reference_dt:
        days_ahead = 7
    return candidate + timedelta(days=days_ahead)


def calculate_next_recurring_datetime(
    day: int | str,
    time_str: str,
    reference_dt: Optional[datetime] = None,
    tz: Optional[Any] = None,
) -> Optional[datetime]:
    """Calculate the next occurrence of a recurring trip.

    Args:
        day: Day of week (0=Sunday, 6=Saturday) - JavaScript getDay() format.
             Can be int or string (will be converted to int).
        time_str: Time in HH:MM format (local time if tz is provided).
        reference_dt: Reference datetime for calculation (default datetime.now()).
        tz: Optional timezone for interpreting time_str as local time.
            If provided, time_str is treated as local time and result is UTC.
            If None (default), time_str is treated as UTC (backward compat).

    Returns:
        datetime of next occurrence, or None if inputs are invalid.
    """
    if reference_dt is None:
        reference_dt = datetime.now()

    parsed_day = _parse_day(day)
    parsed_time = _parse_time(time_str)
    if parsed_day is None or parsed_time is None:
        return None

    hour, minute = parsed_time
    resolved_tz = _resolve_tz(tz)

    if resolved_tz is not None:
        return _compute_next_with_tz(parsed_day, hour, minute, reference_dt, resolved_tz)
    return _compute_next_naive(parsed_day, hour, minute, reference_dt)
