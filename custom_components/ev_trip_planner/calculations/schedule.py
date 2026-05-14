"""Deferrable schedule calculation functions extracted from calculations_orig.py.

Extracted from the legacy calculations.py god module as part of the
SOLID decomposition (Spec 3). These functions handle pure deferrable
load schedule calculations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

_LOGGER = logging.getLogger(__name__)


def generate_deferrable_schedule_from_trips(
    trips: List[Dict[str, Any]],
    power_kw: float,
    reference_dt: datetime | None = None,
) -> List[Dict[str, Any]]:
    """Generate deferrable load schedule from trips (pure function version).

    This is the pure version of EMHASSAdapter._generate_schedule_from_trips.
    It generates a 24-hour schedule with charging windows before each trip's
    deadline.

    Format:
        [{"date": "2026-03-17T14:00:00+01:00", "p_deferrable0": "0.0"}, ...]

    Args:
        trips: List of trip dictionaries (must contain 'datetime' and 'kwh')
        power_kw: Charging power in kW
        reference_dt: Reference datetime for calculations (defaults to datetime.now()).
            For deterministic tests, pass a fixed datetime.

    Returns:
        List of schedule dictionaries with 'date' and 'p_deferrable{N}' keys.
        Returns empty list if trips is empty.
    """
    if not trips:
        return []

    now = _normalize_reference_dt(reference_dt)
    schedule: List[Dict[str, Any]] = []

    for hour_offset in range(24):
        schedule_time = _compute_schedule_time(now, hour_offset)
        entry: Dict[str, Any] = {"date": schedule_time.isoformat()}

        for idx, trip in enumerate(trips):
            power_key = f"p_deferrable{idx}"
            entry[power_key] = _compute_trip_power(
                trip, power_kw, now, hour_offset,
            )

        schedule.append(entry)

    return schedule


def _normalize_reference_dt(
    reference_dt: datetime | None,
) -> datetime:
    """Normalize reference datetime to UTC-aware."""
    if reference_dt is not None:
        if getattr(reference_dt, "tzinfo", None) is None:
            return reference_dt.replace(tzinfo=timezone.utc)
        return reference_dt
    return datetime.now(timezone.utc)


def _compute_schedule_time(now: datetime, hour_offset: int) -> datetime:
    """Compute schedule time for a given hour offset."""
    schedule_time = now.replace(minute=0, second=0, microsecond=0)
    schedule_time = schedule_time.replace(hour=(now.hour + hour_offset) % 24)
    days_to_add = (now.hour + hour_offset) // 24
    if days_to_add > 0:
        schedule_time = schedule_time + timedelta(days=days_to_add)
    return schedule_time


def _compute_trip_power(
    trip: Dict[str, Any],
    power_kw: float,
    now: datetime,
    hour_offset: int,
) -> str:
    """Compute power string for a single trip at a given hour offset."""
    kwh = float(trip.get("kwh", 0))
    if kwh <= 0:
        return "0.0"

    deadline = trip.get("datetime")
    if not deadline:
        return "0.0"

    deadline_dt = _parse_deadline(deadline)
    if deadline_dt is None:
        return "0.0"

    delta = deadline_dt - now
    horas_hasta_viaje = int(delta.total_seconds() / 3600)
    if horas_hasta_viaje < 0:
        return "0.0"

    return _check_charging_window(power_kw, kwh, horas_hasta_viaje, hour_offset)


def _parse_deadline(deadline: Any) -> Optional[datetime]:
    """Parse deadline value to UTC-aware datetime, or None if invalid."""
    if isinstance(deadline, str):
        try:
            deadline_dt = datetime.fromisoformat(deadline)
            if getattr(deadline_dt, "tzinfo", None) is None:
                deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
            return deadline_dt
        except ValueError:
            return None
    else:
        deadline_dt = deadline
        if getattr(deadline_dt, "tzinfo", None) is None:
            deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
        return deadline_dt


def _check_charging_window(
    power_kw: float,
    kwh: float,
    horas_hasta_viaje: int,
    hour_offset: int,
) -> str:
    """Check if current hour is within the charging window.

    Returns the power string if charging, "0.0" otherwise.
    """
    total_hours = kwh / power_kw if power_kw > 0 else 0
    horas_necesarias = int(total_hours) + (1 if total_hours % 1 > 0 else 0)
    hora_inicio_carga = max(0, horas_hasta_viaje - horas_necesarias)

    if hora_inicio_carga <= hour_offset < horas_hasta_viaje:
        return str(int(power_kw * 1000))
    return "0.0"


def calculate_deferrable_parameters(
    trip: Dict[str, Any],
    power_kw: float,
    reference_dt: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Calculate deferrable load parameters from trip data.

    Pure function version extracted from EMHASSAdapter.calculate_deferrable_parameters.

    Args:
        trip: Trip dictionary with kwh, datetime (deadline), etc.
        power_kw: Charging power in kW

    Returns:
        Dictionary with calculated deferrable parameters:
        - total_energy_kwh: Energy needed in kWh
        - power_watts: Charging power in watts
        - total_hours: Hours needed to charge
        - end_timestep: End timestep for EMHASS (1-168, or 24 if no deadline)
        - start_timestep: Start timestep for EMHASS (always 0)
        - is_semi_continuous: Always False
        - minimum_power: Always 0.0
        - operating_hours: Always 0
        - startup_penalty: Always 0.0
        - is_single_constant: Always True

        Returns empty dict if kwh <= 0 or kwh is missing.
    """
    try:
        kwh_value = trip.get("kwh")
        if kwh_value is None:
            return {}
        kwh = float(kwh_value)
        if kwh <= 0:
            return {}

        deadline = trip.get("datetime")

        # Calculate hours needed to charge
        total_hours = kwh / power_kw if power_kw > 0 else 0.0

        # Power in watts (positive value = charging)
        power_watts = power_kw * 1000

        # Calculate available time until deadline
        if deadline:
            now = (
                reference_dt if reference_dt is not None else datetime.now(timezone.utc)
            )
            if isinstance(deadline, str):
                deadline_dt = datetime.fromisoformat(deadline)
            else:
                deadline_dt = deadline

            # Ensure deadline is timezone-aware for consistent arithmetic
            if deadline_dt.tzinfo is None and now.tzinfo is not None:
                deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)

            hours_available = (deadline_dt - now).total_seconds() / 3600
            end_timestep = max(1, min(int(hours_available), 168))  # Max 7 days
        else:
            # Default to 24 hours if no deadline
            end_timestep = 24

        return {
            "total_energy_kwh": round(kwh, 3),
            "power_watts": round(power_watts, 0),
            "total_hours": round(total_hours, 2),
            "end_timestep": end_timestep,
            "start_timestep": 0,
            "is_semi_continuous": False,
            "minimum_power": 0.0,
            "operating_hours": 0,
            "startup_penalty": 0.0,
            "is_single_constant": True,
        }

    except Exception as err:
        _LOGGER.error("Error calculating deferrable parameters: %s", err)
        return {}
