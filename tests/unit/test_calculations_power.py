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


# =============================================================================
# US-5 Log Constant Tests (calculations.power)
# =============================================================================


def test_log_constants_defined_in_power_module() -> None:
    """Log string constants must exist as module-level attributes."""
    from custom_components.ev_trip_planner.calculations import power

    assert hasattr(power, "_LOG_PROCESSING_TRIPS")
    assert hasattr(power, "_LOG_PROFILE_NON_ZERO")


def test_log_constants_are_non_empty_strings() -> None:
    """Log constants must be non-empty strings (mutation target: None/string change)."""
    from custom_components.ev_trip_planner.calculations import power

    for attr in (
        "_LOG_PROCESSING_TRIPS",
        "_LOG_PROFILE_NON_ZERO",
    ):
        val = getattr(power, attr)
        assert isinstance(val, str)
        assert len(val) > 0


def test_log_processing_trips_format() -> None:
    """_LOG_PROCESSING_TRIPS must accept %d placeholders."""
    from custom_components.ev_trip_planner.calculations.power import (
        _LOG_PROCESSING_TRIPS,
    )

    assert isinstance(_LOG_PROCESSING_TRIPS, str)
    assert "%d" in _LOG_PROCESSING_TRIPS
    assert "%.2f" in _LOG_PROCESSING_TRIPS
    formatted = _LOG_PROCESSING_TRIPS % (5, 3.60)
    assert isinstance(formatted, str)


def test_log_profile_non_zero_format() -> None:
    """_LOG_PROFILE_NON_ZERO must accept %d placeholder."""
    from custom_components.ev_trip_planner.calculations.power import (
        _LOG_PROFILE_NON_ZERO,
    )

    assert isinstance(_LOG_PROFILE_NON_ZERO, str)
    assert "%d" in _LOG_PROFILE_NON_ZERO
    formatted = _LOG_PROFILE_NON_ZERO % 42
    assert isinstance(formatted, str)
