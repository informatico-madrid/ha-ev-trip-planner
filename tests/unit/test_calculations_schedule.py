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


# =============================================================================
# US-5 Log Constant Tests (calculations.schedule)
# =============================================================================


def test_log_constants_defined_in_schedule_module() -> None:
    """Log string constants must exist as module-level attributes."""
    from custom_components.ev_trip_planner.calculations import schedule

    assert hasattr(schedule, "_LOG_CALC_ERROR")


def test_log_constants_are_non_empty_strings() -> None:
    """Log constants must be non-empty strings (mutation target: None/string change)."""
    from custom_components.ev_trip_planner.calculations import schedule

    val = getattr(schedule, "_LOG_CALC_ERROR")
    assert isinstance(val, str)
    assert len(val) > 0


def test_log_calc_error_format() -> None:
    """_LOG_CALC_ERROR must accept %s placeholder for error message."""
    from custom_components.ev_trip_planner.calculations.schedule import (
        _LOG_CALC_ERROR,
    )

    assert isinstance(_LOG_CALC_ERROR, str)
    assert "%s" in _LOG_CALC_ERROR
    formatted = _LOG_CALC_ERROR % "test error"
    assert isinstance(formatted, str)
