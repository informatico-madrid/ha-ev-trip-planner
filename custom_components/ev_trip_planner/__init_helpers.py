"""Pure helper functions for __init__ module (US-5 testability refactor).

Extracted from _hourly_refresh_callback to enable independent mutation testing.
These helpers are pure functions — no HA framework dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["CacheReport", "validate_runtime_fields", "build_cache_report"]


@dataclass(frozen=True)
class CacheReport:
    """Immutable cache state snapshot."""

    per_trip_count: int
    power_nonzero: int


def validate_runtime_fields(runtime_data: Any) -> bool:
    """Validate that all required runtime_data fields are present.

    Returns True if all fields (trip_manager, emhass_adapter, coordinator)
    are non-None. Returns False otherwise.

    US-5: extracted from _hourly_refresh_callback for mutation testability.
    """
    if runtime_data is None:
        return False
    if runtime_data.trip_manager is None:
        return False
    if runtime_data.emhass_adapter is None:
        return False
    if runtime_data.coordinator is None:
        return False
    return True


def build_cache_report(adapter: Any) -> CacheReport:  # pragma: no mutate  # EQ-033
    """Extract cache state from EMHASS adapter into an immutable report.

    Pure function: takes an adapter, returns a CacheReport with per_trip
    count and power_nonzero count.

    US-5: extracted from _hourly_refresh_callback for mutation testability.
    """
    pre_cache = adapter.get_cached_optimization_results()
    per_trip = pre_cache.get("per_trip_emhass_params") or {}
    power_profile = pre_cache.get("emhass_power_profile") or []
    return CacheReport(
        per_trip_count=len(per_trip),
        power_nonzero=sum(1 for x in power_profile if x > 0),
    )
