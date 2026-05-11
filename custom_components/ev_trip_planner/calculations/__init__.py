"""Re-export all public symbols from the legacy calculations.py module.

During the SOLID decomposition, the legacy calculations.py module file
is replaced by a calculations/ package directory. This __init__.py
re-exports every public name so that existing import paths continue
to work without changes.

Once the stub sub-modules are populated with their own implementations,
this file will be updated to import from them instead.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone  # noqa: F401

# Import all public symbols from the legacy module file (now _orig).
# These imports are temporary -- sub-modules will take ownership later.
from custom_components.ev_trip_planner.calculations_orig import (
    DAYS_OF_WEEK,
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

# Window functions extracted to their own module.
from .windows import (
    calculate_charging_window_pure,
    calculate_multi_trip_charging_windows,
)

# Power profile functions extracted to their own module.
from .power import (
    calculate_power_profile,
    calculate_power_profile_from_trips,
)

# Deferrable schedule functions extracted to their own module.
from .schedule import (
    calculate_deferrable_parameters,
    generate_deferrable_schedule_from_trips,
)

# Deficit functions extracted to their own module.
from .deficit import (
    ChargingDecision,
    calculate_deficit_propagation,
    calculate_energy_needed,
    calculate_hours_deficit_propagation,
    calculate_next_recurring_datetime,
    calculate_soc_at_trip_starts,
    determine_charging_need,
)

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
