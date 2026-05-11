"""Test that calculations.power exports power profile functions.

BUG-003: During SOLID decomposition, power profile functions must be
re-exported from calculations.power so callers can use:
    from custom_components.ev_trip_planner.calculations.power import (
        calculate_power_profile_from_trips,
        calculate_power_profile,
    )

This test verifies the import path exists before implementation.
"""

from __future__ import annotations



class TestPowerModuleExports:
    """Verify calculations.power re-exports power profile functions."""

    def test_calculate_power_profile_from_trips_importable(self):
        """calculate_power_profile_from_trips must be importable from calculations.power."""
        from custom_components.ev_trip_planner.calculations.power import (
            calculate_power_profile_from_trips,
        )

        assert callable(calculate_power_profile_from_trips)

    def test_calculate_power_profile_importable(self):
        """calculate_power_profile must be importable from calculations.power."""
        from custom_components.ev_trip_planner.calculations.power import (
            calculate_power_profile,
        )

        assert callable(calculate_power_profile)
