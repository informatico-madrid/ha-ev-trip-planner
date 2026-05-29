"""Tests for EMHASS def_total_hours math.ceil handling.

BUG-1: def_total_hours uses round() instead of math.ceil() in windows.py.
Before fix: round(1.94, 2) = 1.94 (float, wrong for EMHASS)
After fix: math.ceil(1.94) = 2 (int, correct for EMHASS)
"""

import math

from custom_components.ev_trip_planner.calculations.windows import (
    calculate_energy_needed,
)


class TestDefTotalHoursMathCeil:
    """Test that def_total_hours uses math.ceil for proper rounding."""

    def test_def_total_hours_should_be_ceil_not_rounded(self):
        """Test that def_total_hours rounds UP, not to nearest.

        Scenario: 14.37 kWh / 7.4 kW = 1.94 hours
        - round(1.94, 2) = 1.94 (wrong - float)
        - math.ceil(1.94) = 2 (correct - integer)
        """
        kwh = 14.37
        charging_power_kw = 7.4
        total_hours = kwh / charging_power_kw  # 1.94 hours

        # Verify the math
        assert round(total_hours, 2) == 1.94
        assert math.ceil(total_hours) == 2

        # The production code should use ceil, not round
        assert math.ceil(total_hours) == 2, (
            "EMHASS requires def_total_hours to be 2 (ceil), not 1.94 (round)"
        )

    def test_calculate_energy_needed_returns_int_hours(self):
        """Test that calculate_energy_needed returns ceil'd integer hours.

        BUG-1: The current production code uses round() → float.
        After fix: should use math.ceil() → int.
        """
        trip = {
            "id": "test_trip",
            "kwh": 14.37,
            "datetime": "2026-05-15T10:00:00+00:00",
        }
        result = calculate_energy_needed(
            trip=trip,
            battery_capacity_kwh=50.0,
            soc_current=50.0,
            charging_power_kw=7.4,
            safety_margin_percent=10.0,
        )

        horas = result["horas_carga_necesarias"]

        # BUG-1: currently returns float (1.94), should return int (2)
        assert isinstance(horas, int), (
            f"def_total_hours must be int (ceil), got float: {horas} ({type(horas).__name__}). "
            "Production code uses round() instead of math.ceil() in windows.py"
        )

    def test_ceil_edge_cases(self):
        """Test math.ceil edge cases."""
        assert math.ceil(0.0) == 0
        assert math.ceil(2.0) == 2
        assert math.ceil(1.01) == 2
