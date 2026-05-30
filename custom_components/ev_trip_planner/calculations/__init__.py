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

# Re-export from decomposed sub-modules
# Override legacy implementations with newly decomposed ones from sub-modules.
# These take precedence — the solid-refactored versions replace the legacy ones.
from .core import (
    DAYS_OF_WEEK,
    DEFAULT_T_BASE,
    SOH_CACHE_TTL_SECONDS,
    BatteryCapacity,
    calculate_charging_rate,
    calculate_day_index,
    calculate_dynamic_soc_limit,
    calculate_trip_time,
    compute_safe_delta,
)

# Deficit functions extracted to their own module.
from .deficit import (
    ChargingDecision,
    calculate_energy_needed,
    calculate_hours_deficit_propagation,
    determine_charging_need,
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

# Window functions extracted to their own module.
from .windows import (
    calculate_charging_window_pure,
    calculate_multi_trip_charging_windows,
)

# Window transformation pipeline (SOC cap + deficit composition).
from .window_pipeline import (
    PipelineContext,
    WindowTransform,
    apply_deficit_transform,
    apply_soc_cap_transform,
    run_window_pipeline,
)

__all__ = [
    "BatteryCapacity",
    "calculate_charging_rate",
    "calculate_charging_window_pure",
    "calculate_day_index",
    "calculate_deferrable_parameters",
    "calculate_dynamic_soc_limit",
    "calculate_energy_needed",
    "calculate_hours_deficit_propagation",
    "calculate_multi_trip_charging_windows",
    "calculate_power_profile",
    "calculate_power_profile_from_trips",
    "calculate_trip_time",
    "ChargingDecision",
    "compute_safe_delta",
    "DAYS_OF_WEEK",
    "determine_charging_need",
    "generate_deferrable_schedule_from_trips",
    "DEFAULT_T_BASE",
    "SOH_CACHE_TTL_SECONDS",
    "PipelineContext",
    "WindowTransform",
    "apply_deficit_transform",
    "apply_soc_cap_transform",
    "run_window_pipeline",
]
