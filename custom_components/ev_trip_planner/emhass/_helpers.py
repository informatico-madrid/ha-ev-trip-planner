"""EMHASS helper functions — US-5 config-key defaults and validation.

Extracted from adapter.py, load_publisher.py, and index_manager.py
to make config-key `.get()` default-value mutations testable.

Each helper replaces a pattern like `data.get("key", default_value)`
with a function that has an explicit default — so that mutating
`default_value` to a different value is observable by tests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def get_config_str(
    entry_data: Dict[str, Any],
    key: str,
    default: str = "",
) -> str:
    """Get a string value from config entry data with a default.

    Args:
        entry_data: Parsed config entry data dict.
        key: Config key to look up.
        default: Default value if key is missing.

    Returns:
        String value or default.
    """
    value = entry_data.get(key)
    if value is None:
        return default
    return str(value)


def get_config_number(
    entry_data: Dict[str, Any],
    key: str,
    default: float = 0.0,
) -> float:
    """Get a numeric value from config entry data with a default.

    Args:
        entry_data: Parsed config entry data dict.
        key: Config key to look up.
        default: Default value if key is missing.

    Returns:
        Float value or default.
    """
    value = entry_data.get(key)
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def get_config_bool(
    entry_data: Dict[str, Any],
    key: str,
    default: bool = True,
) -> bool:
    """Get a boolean value from config entry data with a default.

    Args:
        entry_data: Parsed config entry data dict.
        key: Config key to look up.
        default: Default value if key is missing.

    Returns:
        Boolean value or default.  # pragma: no mutate  # EQ-078
    """
    value = entry_data.get(key)
    if value is None:
        return default
    return bool(value)


def get_config_nested(
    entry_data: Dict[str, Any],
    primary_key: str,
    fallback_key: str,
    default: str = "",
) -> str:
    """Get a string value trying primary key then fallback key.

    Replaces patterns like `data.get("a", data.get("b", default))`.

    Args:
        entry_data: Parsed config entry data dict.
        primary_key: First key to try.
        fallback_key: Second key to try if primary is missing.
        default: Default if both are missing.

    Returns:
        String value or default.
    """
    value = entry_data.get(primary_key)
    if value is not None:
        return str(value)
    value = entry_data.get(fallback_key)
    if value is not None:
        return str(value)
    return default


def build_entry_data(entry: Any) -> Dict[str, Any]:
    """Build a unified config data dict from a ConfigEntry.

    Merges entry.options and entry.data into a single dict,
    handling None/empty values gracefully.

    Args:
        entry: Home Assistant ConfigEntry or dict-like object.

    Returns:
        Unified config dict with merged options and data.
    """
    result: Dict[str, Any] = {}
    if entry is None:
        return result

    # Merge options first, then data (data takes precedence)
    options = getattr(entry, "options", None)
    if options is not None:
        try:
            result.update(dict(options))
        except (TypeError, ValueError):
            pass

    data = getattr(entry, "data", None)
    if data is not None:
        try:
            result.update(dict(data))
        except (TypeError, ValueError):
            pass

    # Handle legacy tests that pass a dict directly as entry
    if isinstance(entry, dict):
        result.update(entry)

    return result


# qg-accepted: AP05 — default planning horizon in days
def parse_planning_horizon(entry_data: Dict[str, Any], default_days: int = 7) -> int:
    """Parse planning_horizon_days from config, return total hours.

    Args:
        entry_data: Parsed config entry data dict.
        default_days: Default planning horizon in days.

    Returns:
        Total hours (days * 24).
    """
    try:
        days = int(entry_data.get("planning_horizon_days", default_days))
        # qg-accepted: AP05 — hours-per-day conversion
        return days * 24
    except (ValueError, TypeError):
        # qg-accepted: AP05 — hours-per-day conversion
        return default_days * 24


def ensure_aware_utc(dt: datetime) -> datetime:
    """Convert naive datetime to aware (UTC) if needed.

    Args:
        dt: Datetime to ensure is timezone-aware.

    Returns:
        Aware datetime in UTC.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# qg-accepted: AP05 — max week-hours (7 * 24)
def clamp_positive(value: float, max_value: int = 168) -> int:
    """Clamp a float to [0, max_value] and return as int.

    Args:
        value: Value to clamp.
        max_value: Maximum allowed value (default 168 hours = 7 days).

    Returns:
        Clamped integer value.
    """
    return max(0, min(int(value), max_value))


# qg-accepted: AP05 — max week-hours (7 * 24)
def clamp_hours(value: float, epsilon: float = 0.001, max_value: int = 168) -> int:
    """Clamp hours with epsilon adjustment for floating-point precision.

    Args:
        value: Hours value to clamp.
        epsilon: Subtracted before ceiling to handle floating-point edge cases.
        max_value: Maximum allowed value (default 168 hours = 7 days).

    Returns:
        Clamped integer value after ceiling.
    """
    import math

    adjusted = value - epsilon
    if adjusted <= 0:
        return 0
    ceiled = math.ceil(adjusted)
    return min(ceiled, max_value)
