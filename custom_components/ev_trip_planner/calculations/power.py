"""Power profile calculation functions extracted from calculations_orig.py.

Extracted from the legacy calculations.py god module as part of the
SOLID decomposition (Spec 3). These functions handle pure power
profile calculations for EMHASS integration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..const import DEFAULT_SAFETY_MARGIN
from ..utils import calcular_energia_kwh
from ._helpers import _ensure_aware
from .core import calculate_trip_time
from .deficit import (
    calculate_next_recurring_datetime,
    determine_charging_need,
)
from .windows import calculate_charging_window_pure, calculate_energy_needed

_LOGGER = logging.getLogger(__name__)


def _normalize_trip_fields(trip: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return canonical trip dict with 'day'/'time' keys, or None for invalid trips."""
    day = trip.get("day") or trip.get("dia_semana")
    time_str = trip.get("time") or trip.get("hora")
    return {"day": day, "time": time_str} if day is not None and time_str is not None else None


def _resolve_deadline(
    trip: Dict[str, Any],
    now: datetime,
    tz: Any,
) -> Optional[datetime]:
    """Resolve a trip to a deadline datetime, or None if invalid/past."""
    deadline = trip.get("datetime")
    if deadline is not None:
        if isinstance(deadline, str):
            try:
                return _ensure_aware(datetime.fromisoformat(deadline))
            except ValueError:
                _LOGGER.debug(
                    "DEBUG calculate_power_profile: trip %s has invalid datetime, skipping",
                    trip.get("id"),
                )
                return None
        return _ensure_aware(deadline)

    canon = _normalize_trip_fields(trip)
    if canon is None:
        _LOGGER.debug(
            "DEBUG calculate_power_profile: trip %s has no datetime or day/time fields, skipping",
            trip.get("id"),
        )
        return None

    deadline_dt = calculate_next_recurring_datetime(canon["day"], canon["time"], now, tz=tz)
    if deadline_dt is None:
        _LOGGER.debug(
            "DEBUG calculate_power_profile: trip %s has invalid day/time, skipping",
            trip.get("id"),
        )
        return None
    return _ensure_aware(deadline_dt)


def _resolve_energy_for_trip(
    trip: Dict[str, Any],
    soc_current: Optional[float],
    battery_capacity_kwh: Optional[float],
    power_kw: float,
    safety_margin_percent: float,
) -> float:
    """Return kwh needed for a trip, SOC-aware or backward-compatible."""
    if soc_current is not None and battery_capacity_kwh is not None:
        return determine_charging_need(
            trip, soc_current, battery_capacity_kwh, power_kw, safety_margin_percent
        ).kwh_needed

    if "kwh" in trip:
        return float(trip.get("kwh", 0))

    distance_km = float(trip.get("km", 0))
    return calcular_energia_kwh(distance_km, 0.15)


def _compute_charging_hours(
    kwh: float,
    power_kw: float,
    horizon: int,
    horas_hasta_viaje: int,
) -> Tuple[int, int]:
    """Compute (hora_inicio_carga, hora_fin) for a single trip."""
    total_hours = kwh / power_kw if power_kw > 0 else 0
    horas_necesarias = int(total_hours) + (1 if total_hours % 1 > 0 else 0)
    if horas_necesarias == 0:
        horas_necesarias = 1

    hora_inicio_carga = max(0, horas_hasta_viaje - horas_necesarias)
    hora_fin = min(horas_hasta_viaje, horizon)
    return hora_inicio_carga, hora_fin


def _populate_profile_slice(
    power_profile: List[float],
    hora_inicio: int,
    hora_fin: int,
    horizon: int,
    charging_power_watts: float,
) -> None:
    """Set power watts for the charging window hours in profile."""
    for h in range(hora_inicio, hora_fin):
        if 0 <= h < horizon:
            power_profile[h] = charging_power_watts


def calculate_power_profile_from_trips(
    trips: List[Dict[str, Any]],
    power_kw: float,
    horizon: int = 168,
    reference_dt: Optional[datetime] = None,
    soc_current: Optional[float] = None,
    battery_capacity_kwh: Optional[float] = None,
    safety_margin_percent: float = DEFAULT_SAFETY_MARGIN,
    tz: Optional[Any] = None,
) -> List[float]:
    """Calculate power profile from trips (pure version).

    Each trip creates a charging window before its deadline.
    Power is distributed across the hours leading up to the deadline.

    Args:
        trips: List of trip dicts with 'datetime' and 'kwh' or 'km' keys.
               Recurring trips use 'day' (0=Sunday, 6=Saturday) and 'time' (HH:MM).
               Trips without datetime or day/time are skipped.
        power_kw: Charging power in kilowatts.
        horizon: Number of hours in the profile (default 168 = 1 week).
        reference_dt: Reference datetime for computing positions (default datetime.now()).
        tz: Optional timezone for interpreting recurring trip times as local.
            Passed to calculate_next_recurring_datetime.

    Returns:
        List of power values in watts (one per hour, 0 = no charging).
    """
    if reference_dt is None:
        reference_dt = datetime.now(timezone.utc)

    power_profile = [0.0] * horizon
    now = _ensure_aware(reference_dt)
    charging_power_watts = power_kw * 1000
    _LOGGER.debug("Processing %d trips, power_kw=%.2f", len(trips), power_kw)

    for trip in trips:
        deadline_dt = _resolve_deadline(trip, now, tz)
        if deadline_dt is None:
            continue

        kwh = _resolve_energy_for_trip(
            trip, soc_current, battery_capacity_kwh, power_kw, safety_margin_percent
        )
        if kwh <= 0:
            continue

        delta = deadline_dt - now
        horas_hasta_viaje = int(delta.total_seconds() / 3600)
        if horas_hasta_viaje < 0:
            continue

        hora_inicio, hora_fin = _compute_charging_hours(
            kwh, power_kw, horizon, horas_hasta_viaje,
        )
        _populate_profile_slice(
            power_profile, hora_inicio, hora_fin,
            horizon, charging_power_watts,
        )

    _LOGGER.debug("Final profile non_zero=%d", sum(1 for x in power_profile if x > 0))
    return power_profile


def calculate_power_profile(
    all_trips: List[Dict[str, Any]],
    battery_capacity_kwh: float,
    soc_current: float,
    charging_power_kw: float,
    hora_regreso: Optional[datetime],
    planning_horizon_days: int,
    reference_dt: datetime,
    safety_margin_percent: float = DEFAULT_SAFETY_MARGIN,
) -> List[float]:
    """Calculate power profile for EMHASS from trip list.

    This is the pure core of async_generate_power_profile. It:
    1. Sorts trips by deadline (earliest first)
    2. For each trip, calculates the charging window
    3. Distributes charging power across the available window hours

    Args:
        all_trips: List of trip dicts with 'tipo', 'hora', 'dia_semana',
                   'datetime', 'kwh' or 'km', 'activo', 'estado'
        battery_capacity_kwh: Battery capacity in kWh
        soc_current: Current SOC in percentage
        charging_power_kw: Charging power in kW
        hora_regreso: Return time (start of first charging window)
        planning_horizon_days: Number of days in the profile
        reference_dt: Reference datetime for computing relative positions
        safety_margin_percent: Safety margin percentage for energy calculations

    Returns:
        List of power values in watts (one per hour, 0 = no charging).
    """
    profile_length = planning_horizon_days * 24
    power_profile = [0.0] * profile_length

    reference_dt, hora_regreso = _normalize_datetimes(reference_dt, hora_regreso)

    if not all_trips:
        return power_profile

    trips_with_deadlines = _assign_deadlines(all_trips, reference_dt)
    if not trips_with_deadlines:
        return power_profile

    _assign_priority_indices(trips_with_deadlines)

    charging_power_watts = charging_power_kw * 1000

    for trip_departure_time, _, trip in trips_with_deadlines:
        _try_populate_window(
            trip, trip_departure_time, battery_capacity_kwh, soc_current,
            charging_power_kw, hora_regreso, reference_dt, power_profile,
            profile_length, charging_power_watts,
            safety_margin_percent,
        )

    return power_profile


def _normalize_datetimes(
    reference_dt: datetime, hora_regreso: Optional[datetime],
) -> tuple:
    """Normalize datetime inputs to UTC-aware."""
    if getattr(reference_dt, "tzinfo", None) is None:
        reference_dt = reference_dt.replace(tzinfo=timezone.utc)
    if hora_regreso is not None and getattr(hora_regreso, "tzinfo", None) is None:
        hora_regreso = hora_regreso.replace(tzinfo=timezone.utc)
    return reference_dt, hora_regreso


def _assign_deadlines(
    all_trips: List[Dict[str, Any]], reference_dt: datetime,
) -> List[tuple]:
    """Assign trip deadlines and return non-empty list of (deadline, idx, trip)."""
    trips_with_deadlines: List[tuple] = []
    for trip in all_trips:
        trip_tipo = trip.get("tipo")
        if trip_tipo is None:
            continue
        trip_time = calculate_trip_time(
            trip_tipo, trip.get("hora"),
            trip.get("dia_semana"), trip.get("datetime"),
            reference_dt,
        )
        if trip_time:
            trips_with_deadlines.append((trip_time, len(trips_with_deadlines), trip))
    return trips_with_deadlines


def _assign_priority_indices(trips_with_deadlines: List[tuple]) -> None:
    """Assign priority index and sort by deadline ascending."""
    trips_with_deadlines.sort(key=lambda x: x[0])
    for ordered_idx, (_, original_idx, trip) in enumerate(trips_with_deadlines):
        trip["_trip_index"] = ordered_idx


def _compute_window_position(
    reference_dt: datetime, ventana_info: Dict[str, Any],
) -> Optional[Tuple[int, int, int]]:
    """Compute charging window position relative to reference time.

    Returns (hora_inicio_carga, horas_necesarias, horas_hasta_fin) or
    None if window already ended.
    """
    inicio_ventana = ventana_info["inicio_ventana"]
    fin_ventana = ventana_info["fin_ventana"]

    delta_inicio = inicio_ventana - reference_dt
    horas_desde_ahora = int(delta_inicio.total_seconds() / 3600)
    hora_inicio_carga = max(0, horas_desde_ahora)

    horas_necesarias = ventana_info.get("horas_carga_necesarias", 0)
    if horas_necesarias == 0:
        horas_necesarias = 1

    delta_fin = fin_ventana - reference_dt
    horas_hasta_fin = int(delta_fin.total_seconds() / 3600)

    if horas_hasta_fin < 0:
        return None

    return hora_inicio_carga, horas_necesarias, horas_hasta_fin


def _populate_profile(
    power_profile: List[float],
    hora_inicio: int,
    horas_necesarias: int,
    horas_hasta_fin: int,
    profile_length: int,
    charging_power_watts: float,
) -> None:
    """Populate power profile hours for a charging window."""
    # horas_necesarias can be float from ventana_info
    for h in range(hora_inicio, min(int(hora_inicio + horas_necesarias), horas_hasta_fin, profile_length)):
        if 0 <= h < profile_length:
            power_profile[h] = charging_power_watts


def _try_populate_window(
    trip: Dict[str, Any],
    trip_departure_time: datetime,
    battery_capacity_kwh: float,
    soc_current: float,
    charging_power_kw: float,
    hora_regreso: Optional[datetime],
    reference_dt: datetime,
    power_profile: List[float],
    profile_length: int,
    charging_power_watts: float,
    safety_margin_percent: float,
) -> None:
    """Calculate energy and window for a single trip, populate profile if feasible."""
    energia_info = calculate_energy_needed(
        trip, battery_capacity_kwh, soc_current, charging_power_kw,
        safety_margin_percent=safety_margin_percent,
    )
    energia_kwh = energia_info["energia_necesaria_kwh"]

    if energia_kwh <= 0:
        return

    ventana_info = calculate_charging_window_pure(
        trip_departure_time=trip_departure_time,
        soc_actual=soc_current,
        hora_regreso=hora_regreso,
        charging_power_kw=charging_power_kw,
        energia_kwh=energia_kwh,
        duration_hours=6.0,
    )

    if not ventana_info.get("es_suficiente", False):
        return

    pos = _compute_window_position(reference_dt, ventana_info)
    if pos is None:
        return

    hora_inicio, horas_necesarias, horas_hasta_fin = pos
    _populate_profile(
        power_profile, hora_inicio, horas_necesarias,
        horas_hasta_fin, profile_length, charging_power_watts,
    )
