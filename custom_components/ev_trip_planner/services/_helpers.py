"""Pure helper functions for service call data extraction.

These helpers extract common patterns from service handler code so that
their mutations are independently killable via unit tests. Each function
is pure (no side effects) and fully testable without a HomeAssistant runtime.
"""

from __future__ import annotations

from typing import Any


def get_str(data: dict[str, Any], key: str, default: str = "") -> str:
    """Extract a string value from service call data with a default.

    Equivalent to: str(data.get(key, default))

    The default value is intentionally kept as a parameter so that
    mutations on it (remove_arg, string_mutate) are independently killable.
    """
    return str(data.get(key, default))


def get_str_fallback(
    data: dict[str, Any],
    primary: str,
    fallback: str,
    default: str = "",
) -> str:
    """Extract a string from service call data, falling back to a second key.

    Equivalent to: data.get(primary) or data.get(fallback, default)

    Used for bilingual fields where the primary key (e.g. "descripcion")
    may be absent and an English fallback (e.g. "description") is used.
    """
    value = data.get(primary)
    if value:
        return str(value)
    return str(data.get(fallback, default))


def get_str_nested(
    data: dict[str, Any],
    primary: str,
    fallback: str,
    default: str = "",
) -> str:
    """Extract a string with a nested fallback key.

    Equivalent to: data.get(primary, data.get(fallback, default))

    Used when the caller may send the field under different key names
    and the fallback is itself a data.get() call.
    """
    if primary in data and data[primary] is not None:
        return str(data[primary])
    if fallback in data and data[fallback] is not None:
        return str(data[fallback])
    return str(default)


def get_vehicle_id(data: dict[str, Any]) -> str:
    """Extract vehicle_id with the standard 'unknown' default.

    Equivalent to: data.get("vehicle_id", "unknown")
    """
    return str(data.get("vehicle_id", "unknown"))


def get_bool(data: dict[str, Any], key: str, default: bool = True) -> bool:
    """Extract a boolean value from service call data with a default.

    Equivalent to: bool(data.get(key, default))

    Used for flags like clear_existing that default to True.
    """
    return bool(data.get(key, default))


def get_optional_str(data: dict[str, Any], key: str, default: str | None = None) -> str | None:
    """Extract an optional string value from service call data.

    Returns None if the key is absent or its value is None,
    otherwise returns the string representation of the value.

    Used for optional fields like datetime where None is a valid
    and distinct sentinel from the empty string.
    """
    value = data.get(key)
    if value is None:
        return default
    return str(value)


def get_or(data: dict[str, Any], primary: str, fallback: str) -> str | None:
    """Extract a string from service call data, falling back to a second key.

    Returns data[primary] if truthy, else data[fallback] if present, else None.

    Used for bilingual/multi-key fields where the caller may send the field
    under different key names (e.g. "dia_semana" / "day_of_week").

    This is intentionally pure so that mutations on the primary/fallback
    key resolution are independently killable.
    """
    value = data.get(primary)
    if value:
        return str(value) if not isinstance(value, str) else value
    return data.get(fallback)


__all__: list[str] = [
    "get_bool",
    "get_optional_str",
    "get_or",
    "get_str",
    "get_str_fallback",
    "get_str_nested",
    "get_vehicle_id",
]
