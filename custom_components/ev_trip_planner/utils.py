"""Utility functions for the EV Trip Planner integration.

This module provides helper functions for trip ID generation and other
common operations used throughout the integration.
"""

from __future__ import annotations

import random
import string
from datetime import date, datetime
from typing import Any, Literal

# Day abbreviations in Spanish (3-letter format for IDs)
DAY_ABBREVIATIONS: dict[str, str] = {
    "lunes": "lun",
    "martes": "mar",
    "miercoles": "mie",
    "jueves": "jue",
    "viernes": "vie",
    "sabado": "sab",
    "domingo": "dom",
    # English fallbacks
    "monday": "lun",
    "tuesday": "mar",
    "wednesday": "mie",
    "thursday": "jue",
    "friday": "vie",
    "saturday": "sab",
    "sunday": "dom",
}

# All possible day names (both Spanish and English)
ALL_DAYS = set(DAY_ABBREVIATIONS.keys())


def generate_random_suffix(length: int = 6) -> str:
    """Generate a random alphanumeric suffix for trip IDs.

    Args:
        length: Number of random characters to generate. Default is 6.

    Returns:
        A random lowercase string of alphanumeric characters.
    """
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def generate_trip_id(
    trip_type: Literal["recurrente", "puntual"],
    day_or_date: str | date | None = None,
) -> str:
    """Generate a unique trip ID with the specified format.

    Formats:
        - Recurrent: `rec_{day}_{random}` (e.g., `rec_lun_abc123`)
        - Punctual: `pun_{date}_{random}` (e.g., `pun_20251119_abc123`)

    Args:
        trip_type: The type of trip - "recurrente" or "puntual" (Spanish).
                   Also accepts "punctual" (English) for compatibility.
        day_or_date: For recurrent trips: day name (e.g., "lunes", "monday").
                    For punctual trips: date string (YYYYMMDD) or date object.

    Returns:
        A uniquely formatted trip ID string.

    Examples:
        >>> generate_trip_id("recurrente", "lunes")
        'rec_lun_abc123'
        >>> generate_trip_id("puntual", "20251119")  # Spanish (production)
        'pun_20251119_abc123'
        >>> generate_trip_id("punctual", "20251119")  # English (compatibility)
        'pun_20251119_xyz789'
        >>> generate_trip_id("puntual", date(2025, 11, 19))
        'pun_20251119_abc123'
    """
    random_suffix = generate_random_suffix()

    if trip_type == "recurrente":
        # Handle day input - normalize to Spanish abbreviation
        day_input = (str(day_or_date) if isinstance(day_or_date, date) else day_or_date or "lunes").lower()

        # Check if it's a known day name and get Spanish abbreviation
        if day_input in DAY_ABBREVIATIONS:
            day_abbr = DAY_ABBREVIATIONS[day_input]
        else:
            # Fallback: use first 3 chars of input
            day_abbr = day_input[:3]

        return f"rec_{day_abbr}_{random_suffix}"

    elif trip_type in ("puntual", "punctual"):
        # Handle date input - convert to YYYYMMDD format
        if isinstance(day_or_date, date):
            date_str = day_or_date.strftime("%Y%m%d")
        elif isinstance(day_or_date, str):
            # Try to parse the date string
            try:
                # Try ISO format first
                parsed = datetime.fromisoformat(day_or_date.replace("Z", "+00:00"))
                date_str = parsed.strftime("%Y%m%d")
            except ValueError:
                # Assume it's already YYYYMMDD
                date_str = day_or_date.replace("-", "").replace("/", "")
        else:
            # Default to today
            date_str = datetime.now().strftime("%Y%m%d")

        return f"pun_{date_str}_{random_suffix}"

    # Fallback for unknown types
    return f"trip_{random_suffix}"


def is_valid_trip_id(trip_id: str) -> bool:
    """Check if a trip ID follows the expected format.

    Args:
        trip_id: The trip ID to validate.

    Returns:
        True if the trip ID matches the expected format, False otherwise.
    """
    if not trip_id:
        return False

    # Check for recurrent format: rec_{day}_{random}
    if trip_id.startswith("rec_"):
        parts = trip_id.split("_")
        return len(parts) == 3 and len(parts[2]) >= 4

    # Check for punctual format: pun_{date}_{random}
    if trip_id.startswith("pun_"):
        parts = trip_id.split("_")
        return len(parts) == 3 and len(parts[1]) == 8 and len(parts[2]) >= 4

    return False


def validate_hora(hora: str) -> None:
    """Validate a time string in HH:MM format.

    Args:
        hora: A time string in HH:MM format (00:00-23:59).

    Raises:
        ValueError: If the time format is invalid, hour is out of range (0-23),
                    or minute is out of range (0-59).
    """
    if not isinstance(hora, str) or len(hora) != 5 or hora[2] != ":":
        raise ValueError("Invalid time format: expected HH:MM")

    hour_str, minute_str = hora.split(":", 1)

    if not hour_str.isdigit() or not minute_str.isdigit():
        raise ValueError("Invalid time format: expected HH:MM")

    hour = int(hour_str)
    minute = int(minute_str)

    if hour > 23:
        raise ValueError(f"Invalid hour: {hour} (must be 0-23)")

    if minute > 59:
        raise ValueError(f"Invalid minute: {minute} (must be 0-59)")


def get_trip_time(trip: dict[str, Any]) -> datetime | None:
    """Extract time from a trip dict.

    Args:
        trip: A trip dictionary containing 'hora' key.

    Returns:
        A datetime object with the time, or None if hora is missing/empty.
    """
    hora = trip.get("hora")
    if not hora:
        return None
    try:
        return datetime.strptime(hora, "%H:%M")
    except (ValueError, TypeError):
        return None


def get_day_index(day_name: str) -> int:
    """Convert a day name to its index (lunes/monday=0 through domingo/sunday=6).

    Args:
        day_name: The name of the day in Spanish or English.

    Returns:
        The day index (0=Monday/lunes, 6=Sunday/domingo).

    Raises:
        ValueError: If the day name is not recognized.
    """
    if not day_name:
        raise ValueError("Day name cannot be empty")
    day_lower = day_name.lower()
    if day_lower in ("lunes", "monday"):
        return 0
    if day_lower in ("martes", "tuesday"):
        return 1
    if day_lower in ("miercoles", "wednesday"):
        return 2
    if day_lower in ("jueves", "thursday"):
        return 3
    if day_lower in ("viernes", "friday"):
        return 4
    if day_lower in ("sabado", "saturday"):
        return 5
    if day_lower in ("domingo", "sunday"):
        return 6
    raise ValueError(f"Unknown day name: {day_name}")


def sanitize_recurring_trips(trips: dict[str, Any]) -> dict[str, Any]:
    """Filter out recurring trips with invalid hora from a dict of trips.

    Args:
        trips: Dictionary of recurring trips keyed by trip ID.

    Returns:
        Dictionary containing only trips with valid hora.
    """
    sanitized: dict[str, Any] = {}
    for trip_id, trip in trips.items():
        hora = trip.get("hora", "")
        try:
            validate_hora(hora)
            sanitized[trip_id] = trip
        except ValueError:
            pass  # Skip invalid trips
    return sanitized


def is_trip_today(trip: dict[str, Any], today: date) -> bool:
    """Check if a trip is scheduled for today.

    Args:
        trip: A trip dictionary containing:
            - tipo: "recurrente", "puntual", or "punctual"
            - dia / dia_semana: For recurring trips, the day name
              (e.g., "lunes", "monday"). Both keys are checked.
            - datetime / fecha: For punctual trips, the date (date object or
              string in YYYYMMDD, ISO, or slash-separated format). Both keys
              are checked.
        today: The date to check against.

    Returns:
        True if the trip is scheduled for today, False otherwise.
    """
    trip_type = trip.get("tipo")

    if trip_type == "recurrente":
        # Recurring trip: check if today's day name matches the trip's day
        # Support both 'dia' (legacy/test format) and 'dia_semana' (production format)
        trip_day = trip.get("dia", "") or trip.get("dia_semana", "")
        trip_day = trip_day.lower()
        today_day = today.strftime("%A").lower()  # Full English day name

        # Normalize trip day to English using DAY_ABBREVIATIONS mapping
        # DAY_ABBREVIATIONS maps both Spanish and English days to Spanish abbreviations
        # We need to find the English day that maps to the same abbreviation
        if trip_day in DAY_ABBREVIATIONS:
            trip_abbr = DAY_ABBREVIATIONS[trip_day]
            # Find English day that has the same abbreviation
            for eng_day, esp_abbr in DAY_ABBREVIATIONS.items():
                if esp_abbr == trip_abbr and eng_day in (
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ):
                    return eng_day == today_day
        return False

    elif trip_type in ("puntual", "punctual"):
        # Punctual trip: check if the trip's date matches today
        # Support both 'datetime' (TripManager format) and 'fecha' (legacy/test format)
        # Also support both 'puntual' (Spanish) and 'punctual' (English) trip types
        fecha = trip.get("datetime") or trip.get("fecha")

        if isinstance(fecha, date):
            return fecha == today
        elif isinstance(fecha, str):
            # Extract date portion from ISO datetime string (format: "YYYY-MM-DDTHH:MM" or "YYYY-MM-DDTHH:MM:SS")
            date_str = fecha.split("T")[0] if "T" in fecha else fecha
            # Normalize string date to YYYYMMDD for comparison
            normalized = date_str.replace("-", "").replace("/", "")
            today_str = today.strftime("%Y%m%d")
            return normalized == today_str

    return False


def normalize_vehicle_id(vehicle_name: str) -> str:
    """Normalize vehicle name to vehicle_id format.

    Converts a vehicle name (possibly with spaces and mixed case) into a
    normalized vehicle_id suitable for use in storage keys and identifiers.

    Args:
        vehicle_name: The raw vehicle name from config entry (e.g., "Test Vehicle").

    Returns:
        Normalized vehicle_id (lowercase, spaces replaced with underscores,
        e.g., "test_vehicle"). Returns empty string if vehicle_name is None or empty.

    Examples:
        >>> normalize_vehicle_id("Test Vehicle")
        'test_vehicle'
        >>> normalize_vehicle_id("My Tesla Model 3")
        'my_tesla_model_3'
        >>> normalize_vehicle_id(None)
        ''
        >>> normalize_vehicle_id("")
        ''
    """
    if not vehicle_name:
        return ""
    return vehicle_name.lower().replace(" ", "_")


def calcular_energia_kwh(
    distance_km: float,
    consumption_kwh_per_km: float,
) -> float:
    """Calculate energy needed for a trip in kWh.

    Args:
        distance_km: Distance of the trip in kilometers.
        consumption_kwh_per_km: Energy consumption in kWh per kilometer.

    Returns:
        Energy needed in kWh, rounded to 3 decimal places.

    Raises:
        ValueError: If distance_km or consumption_kwh_per_km is negative.
    """
    if distance_km < 0:
        raise ValueError("Distance cannot be negative")
    if consumption_kwh_per_km < 0:
        raise ValueError("Consumption cannot be negative")

    energy_kwh = distance_km * consumption_kwh_per_km
    return round(energy_kwh, 3)
