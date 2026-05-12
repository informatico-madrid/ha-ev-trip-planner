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

    def test_calculate_power_profile_soc_aware(self):
        """calculate_power_profile with SOC-aware charging decision."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.power import (
            calculate_power_profile,
        )

        result = calculate_power_profile(
            all_trips=[{"id": "t1", "kwh": 10.0, "tipo": "punctual"}],
            battery_capacity_kwh=75.0,
            soc_current=50.0,
            charging_power_kw=3.6,
            hora_regreso=datetime(2099, 1, 1, 18, 0, 0, tzinfo=timezone.utc),
            planning_horizon_days=7,
            reference_dt=datetime(2099, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            safety_margin_percent=10.0,
        )
        assert isinstance(result, list)
        assert len(result) == 168  # 7 days * 24 hours
