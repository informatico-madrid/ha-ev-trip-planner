"""Integration test: BUG - day index calculation has off-by-one error.

Problem: The system shows the wrong trip as "next" on Saturday.
Expected: Saturday trip (rec_6_c4ngiu, día 6, 11:50) should be TODAY
Actual: Something else is shown, or the calculation is wrong

This test file explores the bug by testing calculate_trip_time directly.
"""

from datetime import datetime, timezone

from custom_components.ev_trip_planner.calculations.core import (
    calculate_trip_time,
)
from custom_components.ev_trip_planner.calculations.deficit import (
    calculate_next_recurring_datetime,
)
from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING


class TestSaturdayTripBug:
    """Test that Saturday trips are correctly identified as today's trip."""

    def test_saturday_trip_should_be_today_on_saturday(self):
        """BUG REPRODUCTION: On Saturday, the Saturday trip should be TODAY.

        Staging has trip rec_6_c4ngiu with dia_semana="6" (Saturday), hora="11:50".
        When today is Saturday 2026-05-16 at 09:26, the next occurrence should be
        TODAY at 11:50, NOT in 6 days.
        """
        # Reference: Saturday 2026-05-16 09:26 UTC
        # (user reported issue at ~09:26 on Saturday)
        saturday_morning = datetime(2026, 5, 16, 9, 26, 0, tzinfo=timezone.utc)

        # Trip: Saturday, 11:50 - day stored as JS getDay() format (6=Saturday)
        # Note: calculate_next_recurring_datetime expects JS getDay() format (0=Sunday)
        day_js = 6  # Saturday in JS getDay()
        time_str = "11:50"

        result = calculate_next_recurring_datetime(
            day=day_js,
            time_str=time_str,
            reference_dt=saturday_morning,
            tz=None,  # UTC
        )

        # The result should be TODAY (Saturday) at 11:50
        # NOT Saturday next week
        expected = datetime(2026, 5, 16, 11, 50, 0, tzinfo=timezone.utc)

        # Calculate days difference
        days_diff = (result.date() - saturday_morning.date()).days

        assert result == expected, (
            f"Saturday trip at 11:50 should be TODAY (May 16) at 11:50 UTC, "
            f"but got {result}. Days ahead: {days_diff}"
        )
        assert days_diff == 0, (
            f"BUG: Saturday trip shows {days_diff} days ahead instead of 0! "
            f"Expected today, got {result.date()} ({(result - saturday_morning)} after reference)"
        )

    def test_calculate_trip_time_with_staging_data(self):
        """Test calculate_trip_time with the actual staging trip data.

        This is the function that _trip_navigator uses to get trip times.
        """
        # Saturday 2026-05-16 09:26 UTC
        saturday_morning = datetime(2026, 5, 16, 9, 26, 0, tzinfo=timezone.utc)

        # rec_6_c4ngiu: día_semana="6" (Saturday in JS getDay), hora="11:50"
        trip = {
            "tipo": TRIP_TYPE_RECURRING,
            "dia_semana": "6",
            "hora": "11:50",
        }

        result = calculate_trip_time(
            trip_tipo=trip["tipo"],
            hora=trip["hora"],
            dia_semana=trip["dia_semana"],
            datetime_str=None,
            reference_dt=saturday_morning,
            tz=None,
        )

        expected = datetime(2026, 5, 16, 11, 50, 0, tzinfo=timezone.utc)

        assert result == expected, (
            f"calculate_trip_time returned {result}, expected {expected}"
        )
        assert result.date() == saturday_morning.date(), (
            f"BUG: Trip should be today ({saturday_morning.date()}) but got {result.date()}"
        )

    def test_staging_trips_order_on_saturday(self):
        """Simulate what _trip_navigator would return on Saturday.

        With 5 trips on days 1,3,4,5,6 - on Saturday (day 6), the next trip
        should be the Saturday trip (day 6), not day 1 (next Monday).
        """
        saturday = datetime(2026, 5, 16, 9, 26, 0, tzinfo=timezone.utc)

        # All 5 staging trips
        trips = [
            {
                "id": "rec_5_xeqnmt",
                "tipo": TRIP_TYPE_RECURRING,
                "dia_semana": "1",
                "hora": "09:30",
            },
            {
                "id": "rec_1_fy4pfk",
                "tipo": TRIP_TYPE_RECURRING,
                "dia_semana": "3",
                "hora": "13:40",
            },
            {
                "id": "rec_2_6hgwk6",
                "tipo": TRIP_TYPE_RECURRING,
                "dia_semana": "4",
                "hora": "09:40",
            },
            {
                "id": "rec_2_gh62hm",
                "tipo": TRIP_TYPE_RECURRING,
                "dia_semana": "5",
                "hora": "09:40",
            },
            {
                "id": "rec_6_c4ngiu",
                "tipo": TRIP_TYPE_RECURRING,
                "dia_semana": "6",
                "hora": "11:50",
            },
        ]

        # Calculate next trip (simplified _trip_navigator logic)
        next_trip = None
        for trip in trips:
            trip_time = calculate_trip_time(
                trip["tipo"],
                trip["hora"],
                trip["dia_semana"],
                None,
                saturday,
                None,
            )
            if trip_time and trip_time > saturday:
                if next_trip is None or trip_time < next_trip["time"]:
                    next_trip = {"time": trip_time, "trip": trip}

        assert next_trip is not None, "Should have found a next trip"
        assert next_trip["trip"]["id"] == "rec_6_c4ngiu", (
            f"BUG: Next trip should be Saturday's trip (rec_6_c4ngiu) but got {next_trip['trip']['id']}"
        )
        assert next_trip["time"].date() == saturday.date(), (
            f"BUG: Next trip should be TODAY ({saturday.date()}) but got {next_trip['time'].date()}"
        )
