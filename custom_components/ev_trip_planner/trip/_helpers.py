"""Pure helper functions for trip data extraction.

These helpers extract common patterns from trip CRUD/persistence/scheduling
code so that their mutations are independently killable via unit tests.
Each function is pure (no side effects) and fully testable without a
HomeAssistant runtime.
"""

from __future__ import annotations

from typing import Any


def get_str(data: dict[str, Any], key: str, default: str = "") -> str:
    """Extract a string value from trip data with a default.

    Equivalent to: str(data.get(key, default))
    """
    return str(data.get(key, default))


def get_dict(
    data: dict[str, Any], key: str, default: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Extract a dict value from trip/persistence data with a default.

    Equivalent to: data.get(key, default or {})
    """
    value = data.get(key)
    if value is None:
        return default if default is not None else {}
    return value


def get_number(data: dict[str, Any], key: str, default: float = 0.0) -> float:
    """Extract a numeric value from trip data with a default.

    Equivalent to: float(data.get(key, default))
    """
    return float(data.get(key, default))


def get_bool(data: dict[str, Any], key: str, default: bool = True) -> bool:
    """Extract a boolean flag from trip data with a default.

    Equivalent to: bool(data.get(key, default))
    """
    return bool(data.get(key, default))


def get_vehicle_id(data: dict[str, Any], default: str = "unknown") -> str:
    """Extract vehicle_id with the standard 'unknown' fallback."""
    return str(data.get("vehicle_id", default))


def get_trip_datetime(trip: dict[str, Any]) -> str:
    """Extract trip datetime, supporting both 'datetime' and 'datetime_str' keys.

    Equivalent to: trip.get("datetime_str", trip.get("datetime", ""))
    """
    return trip.get("datetime_str") or trip.get("datetime") or ""


def get_trip_id(trip: dict[str, Any]) -> str:
    """Extract trip_id with empty-string fallback."""
    return str(trip.get("id") or "")


__all__: list[str] = [
    "get_str",
    "get_dict",
    "get_number",
    "get_bool",
    "get_vehicle_id",
    "get_trip_datetime",
    "get_trip_id",
]
