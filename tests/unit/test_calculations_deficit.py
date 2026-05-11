"""Test that calculations.deficit exports deficit/scheduling functions.

During SOLID decomposition, deficit functions must be re-exported
from calculations.deficit so callers can use:
    from custom_components.ev_trip_planner.calculations.deficit import (
        calculate_deficit_propagation,
        calculate_next_recurring_datetime,
        determine_charging_need,
        ChargingDecision,
        calculate_energy_needed,
    )

This test verifies the import path exists before implementation.
"""

from __future__ import annotations



class TestDeficitModuleExports:
    """Verify calculations.deficit re-exports deficit functions."""

    def test_calculate_deficit_propagation_importable(self):
        """calculate_deficit_propagation must be importable from calculations.deficit."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_deficit_propagation,
        )

        assert callable(calculate_deficit_propagation)

    def test_calculate_next_recurring_datetime_importable(self):
        """calculate_next_recurring_datetime must be importable from calculations.deficit."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_next_recurring_datetime,
        )

        assert callable(calculate_next_recurring_datetime)

    def test_determine_charging_need_importable(self):
        """determine_charging_need must be importable from calculations.deficit."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            determine_charging_need,
        )

        assert callable(determine_charging_need)

    def test_charging_decision_importable(self):
        """ChargingDecision must be importable from calculations.deficit."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            ChargingDecision,
        )

        assert ChargingDecision is not None

    def test_calculate_energy_needed_importable(self):
        """calculate_energy_needed must be importable from calculations.deficit."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_energy_needed,
        )

        assert callable(calculate_energy_needed)
