"""Private helper functions for the calculations package.

Extracted from the legacy calculations.py god module as part of the
SOLID decomposition (Spec 3). These helpers are intentionally private
(not in __all__) and imported only within the package.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .core import calculate_trip_time

_LOGGER = logging.getLogger(__name__)


def _ensure_aware(dt: datetime) -> datetime:
    """Convert naive datetime to aware (UTC) if needed."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def kw_to_watts(kw: float) -> float:
    """Convert kilowatts to watts."""
    return kw * 1000


def watts_to_kw(watts: float) -> float:
    """Convert watts to kilowatts."""
    return watts / 1000


def ceil_hours(hours: float) -> int:
    """Ceiling of hours to whole hours: any fraction = 1 full hour.

    Per business rules: charging hours always round up (any fraction = full hour).
    """
    return int(hours) + (1 if hours % 1 > 0 else 0)


def hours_to_timestep(hours: float, horizon: int) -> int:
    """Convert hours to a timestep index clamped to the planning horizon."""
    return max(0, min(ceil_hours(hours), horizon))


def compute_hours_until(deadline: datetime, now: datetime) -> float:
    """Compute hours between `now` and `deadline`.

    Both datetimes must be timezone-aware. Returns the difference in hours
    as a float (may be negative if deadline is in the past).
    """
    return (deadline - now).total_seconds() / 3600


def compute_charging_window(deadline_hours: float, needed_hours: float) -> int:
    """Compute the start hour for a charging window.

    Returns the latest hour (rounded up to whole hours) from which charging
    should begin to fully charge before the trip deadline.
    Clamped to >= 0.
    """
    return max(0, ceil_hours(deadline_hours - needed_hours))


def normalize_trip_fields(trip: Dict[str, Any]) -> Dict[str, Any] | None:
    """Return canonical trip dict with 'day'/'time' keys, or None for invalid trips.

    Trip dicts may use either the canonical ('day', 'time') or legacy
    ('dia_semana', 'hora') key names. This helper normalizes to canonical.

    Args:
        trip: Trip dictionary with deadline info.

    Returns:
        Dict with 'day' and 'time' keys, or None if insufficient data.
    """
    day = trip.get("day") if "day" in trip else trip.get("dia_semana")
    time_str = trip.get("time") if "time" in trip else trip.get("hora")
    return {"day": day, "time": time_str} if day is not None and time_str is not None else None


def _strip_accents(s: str) -> str:
    """Remove diacritical marks: 'miércoles' → 'miercoles'."""
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _is_valid_day(day) -> bool:
    """Check if a day value is a valid day name or numeric (0-6)."""
    if day is None:
        return False
    day_str = str(day).lower().strip()
    if day_str.isdigit():
        return 0 <= int(day_str) <= 6
    # Valid day names in Spanish and English
    normalized = _strip_accents(day_str)
    valid_names = {
        "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    }
    return normalized in valid_names


def resolve_trip_deadline(
    trip: Dict[str, Any],
    now: datetime,
    tz: Any = None,
) -> datetime | None:
    """Resolve a trip to a deadline datetime, or None if invalid.

    Handles both punctual trips (has 'datetime' key) and recurring trips
    (has 'day'/'time' or 'dia_semana'/'hora' keys). Uses the appropriate
    calculation function for each type.

    Args:
        trip: Trip dictionary with deadline info.
        now: Current datetime for computing recurring trips.
        tz: Optional timezone for interpreting recurring trip times as local.

    Returns:
        Timezone-aware deadline datetime, or None if trip is invalid/past.
    """
    deadline = trip.get("datetime")
    if deadline is not None:
        if isinstance(deadline, str):
            try:
                return _ensure_aware(datetime.fromisoformat(deadline))
            except ValueError:
                _LOGGER.debug(
                    "resolve_trip_deadline: trip %s has invalid datetime, skipping",
                    trip.get("id"),
                )
                return None
        return _ensure_aware(deadline)

    canon = normalize_trip_fields(trip)
    if canon is None:
        _LOGGER.debug(
            "resolve_trip_deadline: trip %s has no datetime or day/time fields, skipping",
            trip.get("id"),
        )
        return None

    # Validate day value — reject invalid days silently (no defaulting to Monday)
    day_raw = canon["day"]
    if not _is_valid_day(day_raw):
        _LOGGER.warning(
            "resolve_trip_deadline: trip %s has invalid day value '%s', skipping",
            trip.get("id"),
            day_raw,
        )
        return None

    # Normalize day to string for calculate_trip_time (handles int→str)
    day_str = str(day_raw) if day_raw is not None else None

    tipo = trip.get("tipo", "")
    if tipo == "recurrente" or tipo == "recurring":
        result = calculate_trip_time(
            trip_tipo=tipo,
            hora=canon["time"],
            dia_semana=day_str,
            datetime_str=None,
            reference_dt=now,
            tz=tz,
        )
    else:
        # Fallback: treat as recurring with day/time
        result = calculate_trip_time(
            trip_tipo="recurrente",
            hora=canon["time"],
            dia_semana=day_str,
            datetime_str=None,
            reference_dt=now,
            tz=tz,
        )

    if result is None:
        _LOGGER.debug(
            "resolve_trip_deadline: trip %s has invalid day/time, skipping",
            trip.get("id"),
        )
        return None

    return _ensure_aware(result)

