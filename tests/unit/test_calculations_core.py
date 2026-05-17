"""Test that calculations.core re-exports core types and functions.

This test verifies that calculations.core exposes the public API
required by other modules after the SOLID decomposition.

Types under test:
    - BatteryCapacity
    - DEFAULT_T_BASE

Functions under test:
    - calculate_dynamic_soc_limit
    - calculate_day_index
    - calculate_trip_time
    - calculate_charging_rate
    - calculate_soc_target

See: FR-1.1, Design §3.6 (calculations functional decomposition)
"""

from __future__ import annotations


def test_core_re_exports_types():
    """BatteryCapacity and DEFAULT_T_BASE must be accessible from calculations.core."""
    from custom_components.ev_trip_planner.calculations.core import (
        DEFAULT_T_BASE,
        BatteryCapacity,
    )

    assert BatteryCapacity is not None
    assert DEFAULT_T_BASE is not None


def test_core_re_exports_functions():
    """Core calculation functions must be accessible from calculations.core."""
    from custom_components.ev_trip_planner.calculations.core import (
        calculate_charging_rate,
        calculate_day_index,
        calculate_dynamic_soc_limit,
        calculate_soc_target,
        calculate_trip_time,
    )

    assert callable(calculate_charging_rate)
    assert callable(calculate_day_index)
    assert callable(calculate_dynamic_soc_limit)
    assert callable(calculate_soc_target)
    assert callable(calculate_trip_time)
