"""Test that calculations.deficit exports live functions.

Verifies:
- determine_charging_need
- ChargingDecision
- calculate_energy_needed
- calculate_hours_deficit_propagation
"""

from __future__ import annotations


class TestDeficitModuleExports:
    """Verify calculations.deficit re-exports live functions."""

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

    def test_calculate_hours_deficit_propagation_importable(self):
        """calculate_hours_deficit_propagation must be importable."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_hours_deficit_propagation,
        )

        assert callable(calculate_hours_deficit_propagation)

    def test_determine_charging_need_no_charging_needed(self):
        """Determine charging need when trip has zero energy → kwh_needed=0."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            determine_charging_need,
        )

        result = determine_charging_need(
            trip={"kwh": 0.0},
            soc_current=95.0,
            battery_capacity_kwh=75.0,
            charging_power_kw=3.6,
        )
        assert result is not None
        assert result.kwh_needed == 0.0
        assert result.needs_charging is False
        assert result.def_total_hours == 0
        assert result.power_watts == 0.0

    def test_determine_charging_need_charging_needed(self):
        """Determine charging need when SOC is low → kwh_needed>0, power>0."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            determine_charging_need,
        )

        result = determine_charging_need(
            trip={"kwh": 10.0, "tipo": "punctual"},
            soc_current=30.0,
            battery_capacity_kwh=75.0,
            charging_power_kw=3.6,
        )
        assert result is not None
        assert result.needs_charging is True
        assert result.kwh_needed > 0
        assert result.def_total_hours > 0
        assert result.power_watts > 0

    def test_calculate_energy_needed_no_charging(self):
        """No charging needed → kwh_needed=0 (line 52-53, kwh branch with high SOC)."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"kwh": 0, "tipo": "punctual"},
            battery_capacity_kwh=75.0,
            soc_current=95.0,
            charging_power_kw=3.6,
        )
        assert result["energia_necesaria_kwh"] == 0.0
