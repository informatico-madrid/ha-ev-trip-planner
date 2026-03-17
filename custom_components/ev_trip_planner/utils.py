"""Utility functions for the EV Trip Planner integration.

This module provides helper functions for trip ID generation and other
common operations used throughout the integration.
"""

from __future__ import annotations

import random
import string
from datetime import date, datetime
from typing import Literal

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
    trip_type: Literal["recurrente", "punctual"],
    day_or_date: str | date | None = None,
) -> str:
    """Generate a unique trip ID with the specified format.

    Formats:
        - Recurrent: `rec_{day}_{random}` (e.g., `rec_lun_abc123`)
        - Punctual: `pun_{date}_{random}` (e.g., `pun_20251119_abc123`)

    Args:
        trip_type: The type of trip - "recurrente" or "punctual".
        day_or_date: For recurrent trips: day name (e.g., "lunes", "monday").
                    For punctual trips: date string (YYYYMMDD) or date object.

    Returns:
        A uniquely formatted trip ID string.

    Examples:
        >>> generate_trip_id("recurrente", "lunes")
        'rec_lun_abc123'
        >>> generate_trip_id("punctual", "20251119")
        'pun_20251119_abc123'
        >>> generate_trip_id("punctual", date(2025, 11, 19))
        'pun_20251119_xyz789'
    """
    random_suffix = generate_random_suffix()

    if trip_type == "recurrente":
        # Handle day input - normalize to Spanish abbreviation
        day_input = (day_or_date or "lunes").lower()

        # Check if it's a known day name and get Spanish abbreviation
        if day_input in DAY_ABBREVIATIONS:
            day_abbr = DAY_ABBREVIATIONS[day_input]
        else:
            # Fallback: use first 3 chars of input
            day_abbr = day_input[:3]

        return f"rec_{day_abbr}_{random_suffix}"

    elif trip_type == "punctual":
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
