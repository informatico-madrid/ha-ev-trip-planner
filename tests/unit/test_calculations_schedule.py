"""Test that calculations.schedule exports schedule functions.

During SOLID decomposition, schedule functions must be re-exported
from calculations.schedule so callers can use:
    from custom_components.ev_trip_planner.calculations.schedule import (
        generate_deferrable_schedule_from_trips,
        calculate_deferrable_parameters,
    )

This test verifies the import path exists before implementation.
"""

from __future__ import annotations



class TestScheduleModuleExports:
    """Verify calculations.schedule re-exports schedule functions."""

    def test_generate_deferrable_schedule_from_trips_importable(self):
        """generate_deferrable_schedule_from_trips must be importable from calculations.schedule."""
        from custom_components.ev_trip_planner.calculations.schedule import (
            generate_deferrable_schedule_from_trips,
        )

        assert callable(generate_deferrable_schedule_from_trips)

    def test_calculate_deferrable_parameters_importable(self):
        """calculate_deferrable_parameters must be importable from calculations.schedule."""
        from custom_components.ev_trip_planner.calculations.schedule import (
            calculate_deferrable_parameters,
        )

        assert callable(calculate_deferrable_parameters)
