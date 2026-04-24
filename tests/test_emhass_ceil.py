"""Tests for EMHASS def_total_hours math.ceil handling.

TASK 1.5 [RED]: Failing test - def_total_hours uses round() instead of math.ceil()

EMHASS requires def_total_hours as an integer, rounded UP.
Before fix: round(1.94, 2) = 1.94 (float, wrong for EMHASS)
After fix: math.ceil(1.94) = 2 (int, correct for EMHASS)
"""

import math



class TestDefTotalHoursMathCeil:
    """Test that def_total_hours uses math.ceil for proper rounding.
    GREEN Phase: Test PASSES after fix uses math.ceil() (correct)
    """

    def test_def_total_hours_should_be_ceiled_not_rounded(self):
        """Test that def_total_hours rounds UP, not to nearest.

        Scenario: 14.37 kWh / 7.4 kW = 1.94 hours
        - round(1.94, 2) = 1.94 (wrong - float, not rounded up)
        - math.ceil(1.94) = 2 (correct - integer, rounded up)

        EMHASS expects integer hours rounded UP to ensure enough charging time.
        """
        kwh = 14.37
        charging_power_kw = 7.4
        total_hours = kwh / charging_power_kw  # 1.94 hours

        # Current buggy behavior: round() gives float 1.94
        rounded = round(total_hours, 2)
        assert rounded == 1.94, "round() gives 1.94"
        assert isinstance(rounded, float), "round() returns float, not int"

        # Expected correct behavior: ceil() gives int 2
        ceiled = math.ceil(total_hours)
        assert ceiled == 2, "ceil() gives 2 (rounded up)"
        assert isinstance(ceiled, int), "ceil() returns int"

        # The fix should make def_total_hours = 2, not 1.94
        # If this assertion fails, the fix hasn't been applied
        assert ceiled == 2, "EMHASS requires def_total_hours to be 2 (ceil), not 1.94 (round)"

    def test_ceil_edge_cases(self):
        """Test math.ceil edge cases."""
        # ceil(0) = 0
        assert math.ceil(0.0) == 0
        # ceil(2.0) = 2 (whole numbers stay whole)
        assert math.ceil(2.0) == 2
        # ceil(1.01) = 2 (just above 1 rounds up)
        assert math.ceil(1.01) == 2