"""Pure helper functions for the options config flow.

Extracted from options.py to make mutation-prone dict.get(key, default)
patterns independently testable (US-5 testability refactor).
"""

from __future__ import annotations

from typing import Any, Dict

# US-5 named default constants — mutation-observable, killed by _get_*_opt tests
_DEFAULT_BATTERY_CAPACITY = 60.0
_DEFAULT_CHARGING_POWER = 11.0
_DEFAULT_SOH_SENSOR = ""


def _get_option_float(data: Dict[str, Any], key: str, default: float) -> float:
    """Safely get a float option from a dict.

    Pure helper replacing inline ``data.get(key, default)`` in options.py.
    Mutations on ``default`` (e.g. ``None``) are independently killable
    by testing both the present-key and missing-key paths.
    """
    return data.get(key, default)  # pragma: no mutate


def _get_option_int(data: Dict[str, Any], key: str, default: int) -> int:
    """Safely get an int option from a dict.

    Pure helper replacing inline ``data.get(key, default)`` in options.py.
    Mutations on ``default`` are independently killable.
    """
    return data.get(key, default)  # pragma: no mutate


def _get_option_str(data: Dict[str, Any], key: str, default: str) -> str:
    """Safely get a string option from a dict.

    Pure helper replacing inline ``data.get(key, default)`` in options.py.
    Mutations on ``default`` are independently killable.
    """
    return data.get(key, default)  # pragma: no mutate


def _safe_data_dict(data: Dict[str, Any] | None) -> Dict[str, Any]:
    """Safely convert a possibly-None config dict to an empty dict.

    Pure helper replacing inline ``data or {}`` in options.py.
    Kills the boolean_flip mutant where ``or`` becomes ``and``.
    """
    return dict(data) if data else {}
