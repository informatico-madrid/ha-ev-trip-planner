"""Re-export all public symbols from the legacy calculations.py module.

During the SOLID decomposition, the legacy calculations.py module file
is replaced by a calculations/ package directory. This __init__.py
re-exports every public name so that existing import paths continue
to work without changes.

Once the stub sub-modules are populated with their own implementations,
this file will be updated to import from them instead.
"""

from __future__ import annotations

# Import all public symbols from the legacy module file (now _orig).
# These imports are temporary -- sub-modules will take ownership later.
from custom_components.ev_trip_planner.calculations_orig import (
    # 16 names from __all__
    BatteryCapacity,
    calculate_charging_rate,
    calculate_charging_window_pure,
    calculate_day_index,
    calculate_deferrable_parameters,
    calculate_deficit_propagation,
    calculate_dynamic_soc_limit,
    calculate_energy_needed,
    calculate_hours_deficit_propagation,
    calculate_multi_trip_charging_windows,
    calculate_power_profile,
    calculate_power_profile_from_trips,
    calculate_soc_at_trip_starts,
    calculate_soc_target,
    ChargingDecision,
    DAYS_OF_WEEK,
    determine_charging_need,
    generate_deferrable_schedule_from_trips,
    calculate_trip_time,
    # Additional names used by downstream callers
    calculate_next_recurring_datetime,
    DEFAULT_T_BASE,
    SOH_CACHE_TTL_SECONDS,
)

# Override legacy implementations with newly decomposed ones from sub-modules.
# These take precedence — the solid-refactored versions replace the legacy ones.
from .core import (
    BatteryCapacity,
    DEFAULT_T_BASE,
    calculate_charging_rate,
    calculate_day_index,
    calculate_dynamic_soc_limit,
    calculate_soc_target,
    calculate_trip_time,
)

# Re-export datetime/timezone/timedelta for test mocking (tests patch calculations.datetime).
# These are used internally by calculations_orig.py functions that call datetime.now().
from datetime import datetime, timedelta, timezone  # noqa: F401

__all__ = [
    "BatteryCapacity",
    "calculate_charging_rate",
    "calculate_charging_window_pure",
    "calculate_day_index",
    "calculate_deferrable_parameters",
    "calculate_deficit_propagation",
    "calculate_dynamic_soc_limit",
    "calculate_energy_needed",
    "calculate_hours_deficit_propagation",
    "calculate_multi_trip_charging_windows",
    "calculate_power_profile",
    "calculate_power_profile_from_trips",
    "calculate_soc_at_trip_starts",
    "calculate_soc_target",
    "ChargingDecision",
    "DAYS_OF_WEEK",
    "determine_charging_need",
    "generate_deferrable_schedule_from_trips",
    "calculate_trip_time",
    "calculate_next_recurring_datetime",
    "DEFAULT_T_BASE",
    "SOH_CACHE_TTL_SECONDS",
]
