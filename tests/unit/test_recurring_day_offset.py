"""Tests for recurring trip day offset handling and timezone interpretation.

Bug 1: Frontend stores dia_semana as JS getDay() format (Sunday=0, Friday=5),
       but calculate_day_index() must interpret those numeric strings correctly
       so recurring trips are scheduled on the intended day.

Bug 2: calculate_trip_time() must treat hora as local time rather than UTC.
       For UTC+2 users, this avoids adding an incorrect ~2 hour offset to the
       calculated deadline.

These tests verify the corrected behavior for both issues. Bug 1 is validated
first because an incorrect day index can mask the timezone handling outcome.
"""

from datetime import datetime, timedelta, timezone

import pytest

# =============================================================================
# Shared test fixtures
# =============================================================================

# Friday April 24, 2026 at 09:15 UTC = 11:15 local (UTC+2)
FRIDAY_09_15_UTC = datetime(2026, 4, 24, 9, 15, tzinfo=timezone.utc)

# User timezone: UTC+2 (CEST - Central European Summer Time)
USER_TZ = timezone(timedelta(hours=2))

# Trip: Friday at 13:30 local time, stored as dia_semana="5" (JS getDay format)
# In UTC+2: 13:30 local = 11:30 UTC
FRIDAY_TRIP_JS_FORMAT = {
    "id": "rec_vie_test",
    "tipo": "recurrente",
    "dia_semana": "5",  # Friday in JS getDay() format (panel.js stores this)
    "hora": "13:30",  # Local time
    "kwh": 7.0,
    "km": 30,
    "activo": True,
}

BATTERY_CAPACITY_KWH = 30.0
CHARGING_POWER_KW = 3.3
SOC_CURRENT = 20.0


# =============================================================================
# Bug 1: Day format mismatch (~24h offset)
# =============================================================================


class TestDayFormatMismatch:
    """Bug 1: calculate_day_index interprets JS getDay format as Monday=0 format.

    Frontend stores: dia_semana="5" → Friday (JS: Sunday=0, Monday=1, ..., Friday=5)
    Backend reads:  calculate_day_index("5") → 5 → Saturday (Monday=0: ..., Friday=4, Saturday=5)

    Result: Trip scheduled for Saturday instead of Friday → ~24h offset.
    """

    def test_calculate_day_index_maps_friday(self):
        """calculate_day_index("5") should return Friday index, not Saturday.

        JS getDay format: Sunday=0, Monday=1, Tuesday=2, Wednesday=3, Thursday=4, Friday=5, Saturday=6
        DAYS_OF_WEEK format: Monday=0, Tuesday=1, ..., Friday=4, Saturday=5, Sunday=6

        Currently: calculate_day_index("5") = 5 = Saturday (WRONG)
        Expected:  calculate_day_index("5") = 4 = Friday (CORRECT)
        """
        from custom_components.ev_trip_planner.calculations import calculate_day_index

        result = calculate_day_index("5")
        # "5" is Friday in JS getDay format → should map to Friday = 4 in Monday=0 format
        assert result == 4, (
            f"Expected Friday=4 (Monday=0 format), got {result}. "
            f"JS getDay Friday=5 is being interpreted as Saturday=5 in DAYS_OF_WEEK!"
        )

    @pytest.mark.parametrize(
        "js_day,expected_day_name,expected_monday0_index",
        [
            ("0", "domingo", 6),  # JS Sunday=0 → Monday=0 index 6
            ("1", "lunes", 0),  # JS Monday=1 → Monday=0 index 0
            ("2", "martes", 1),  # JS Tuesday=2 → Monday=0 index 1
            ("3", "miercoles", 2),  # JS Wednesday=3 → Monday=0 index 2
            ("4", "jueves", 3),  # JS Thursday=4 → Monday=0 index 3
            ("5", "viernes", 4),  # JS Friday=5 → Monday=0 index 4
            ("6", "sabado", 5),  # JS Saturday=6 → Monday=0 index 5
        ],
    )
    def test_calculate_day_index_all_js_getday_values(
        self, js_day: str, expected_day_name: str, expected_monday0_index: int
    ):
        """All JS getDay() values must map to correct Monday=0 indices."""
        from custom_components.ev_trip_planner.calculations import (
            DAYS_OF_WEEK,
            calculate_day_index,
        )

        result = calculate_day_index(js_day)
        assert result == expected_monday0_index, (
            f"JS getDay '{js_day}' ({expected_day_name}) should map to "
            f"Monday=0 index {expected_monday0_index}, got {result} "
            f"({DAYS_OF_WEEK[result] if result < len(DAYS_OF_WEEK) else 'out of range'})"
        )

    def test_trip_time_friday_scheduled_today(self):
        """Friday recurring trip must be scheduled for today (Friday), not tomorrow (Saturday).

        This is the core Bug 1 test: with dia_semana="5" (JS format Friday),
        calculate_trip_time should return a deadline TODAY (within 24 hours),
        not tomorrow (~24-28 hours away).
        """
        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora="13:30",
            dia_semana="5",  # Friday in JS getDay format
            datetime_str=None,
            reference_dt=FRIDAY_09_15_UTC,
        )

        assert (
            result is not None
        ), "calculate_trip_time returned None for valid recurring trip"

        hours_until = (result - FRIDAY_09_15_UTC).total_seconds() / 3600

        # Key assertion: trip must be within 24 hours (today, Friday)
        # Bug 1 causes it to be ~28 hours (tomorrow, Saturday)
        assert hours_until <= 24, (
            f"Friday trip scheduled {hours_until:.1f}h away (>24h = next day!). "
            f"Bug 1: dia_semana='5' interpreted as Saturday instead of Friday. "
            f"Deadline: {result.isoformat()}, Now: {FRIDAY_09_15_UTC.isoformat()}"
        )

    def test_trip_time_friday_is_friday(self):
        """The computed deadline must be a Friday (weekday=4 in Monday=0)."""
        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora="13:30",
            dia_semana="5",  # Friday in JS getDay format
            datetime_str=None,
            reference_dt=FRIDAY_09_15_UTC,
        )

        assert result is not None
        # Monday=0, Friday=4, Saturday=5
        assert result.weekday() == 4, (
            f"Expected Friday (weekday=4), got weekday={result.weekday()}. "
            f"Date: {result.date()}, {result.strftime('%A')}"
        )

    def test_power_profile_friday_within_window(self):
        """Power profile for Friday trip must have non-zero values within first 24 hours.

        Bug 1 causes the profile to have values at indices ~26-27 instead of ~1-3.
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        profile = calculate_power_profile_from_trips(
            trips=[FRIDAY_TRIP_JS_FORMAT],
            power_kw=CHARGING_POWER_KW,
            reference_dt=FRIDAY_09_15_UTC,
            soc_current=SOC_CURRENT,
            battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        )

        non_zero_indices = [i for i, v in enumerate(profile) if v > 0]

        assert len(non_zero_indices) > 0, "Power profile has no non-zero values!"

        # All non-zero values must be within the first 24 hours
        max_index = max(non_zero_indices)
        assert max_index < 24, (
            f"Charging scheduled at hour {max_index} (>24h = next day!). "
            f"Bug 1: trip scheduled for Saturday instead of Friday. "
            f"Non-zero indices: {non_zero_indices}"
        )


# =============================================================================
# Bug 2: Timezone offset (~2h for UTC+2)
# =============================================================================


class TestTimezoneOffset:
    """Bug 2: calculate_trip_time treats hora as UTC instead of local time.

    The user sets hora="13:30" meaning 13:30 local time (e.g., UTC+2 = 11:30 UTC).
    But calculate_trip_time creates deadline at 13:30 UTC (2 hours late).

    This test class will only reveal failures AFTER Bug 1 is fixed.
    With Bug 1 present, the trip is already 24h late, masking the 2h timezone offset.
    """

    def test_trip_time_friday_deadline_approximately_correct(self):
        """Deadline must be approximately 2-3 hours from now (not 4-5).

        Now: 09:15 UTC (11:15 local UTC+2)
        Trip: 13:30 local = 11:30 UTC
        Expected hours_until: ~2.25h
        Bug 2 hours_until: ~4.25h (treats 13:30 as UTC)
        """
        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora="13:30",
            dia_semana="5",  # Friday in JS format
            datetime_str=None,
            reference_dt=FRIDAY_09_15_UTC,
            tz=USER_TZ,  # Interpret hora as local time (UTC+2)
        )

        assert result is not None
        hours_until = (result - FRIDAY_09_15_UTC).total_seconds() / 3600

        # With Bug 2: hours_until ≈ 4.25 (13:30 UTC - 09:15 UTC)
        # Without Bug 2: hours_until ≈ 2.25 (11:30 UTC - 09:15 UTC)
        # We allow some tolerance but it should be < 3.5 hours
        assert hours_until < 3.5, (
            f"Deadline {hours_until:.2f}h away, expected ~2.25h. "
            f"Bug 2: hora '13:30' treated as UTC instead of local time. "
            f"Deadline: {result.isoformat()}"
        )

    def test_power_profile_friday_correct_positions(self):
        """P_deferrable must have charging at correct hour positions.

        Expected (both bugs fixed):
            Now: 09:15 UTC, Deadline: ~11:30 UTC
            horas_hasta_viaje ≈ 2, horas_necesarias ≈ 2-3
            Charging at indices 0-1 or 1-2 (within first 3 hours)

        With Bug 2 only (Bug 1 fixed):
            Now: 09:15 UTC, Deadline: 13:30 UTC (wrong)
            horas_hasta_viaje ≈ 4, horas_necesarias ≈ 2-3
            Charging at indices 1-3 or 2-3 (shifted ~2 hours late)
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        profile = calculate_power_profile_from_trips(
            trips=[FRIDAY_TRIP_JS_FORMAT],
            power_kw=CHARGING_POWER_KW,
            reference_dt=FRIDAY_09_15_UTC,
            soc_current=SOC_CURRENT,
            battery_capacity_kwh=BATTERY_CAPACITY_KWH,
            tz=USER_TZ,  # Interpret hora as local time (UTC+2)
        )

        non_zero_indices = [i for i, v in enumerate(profile) if v > 0]
        assert len(non_zero_indices) > 0, "Power profile has no non-zero values!"

        # The last non-zero index should be within the first 3 hours
        # (deadline is ~2.25h away, charging needs ~2-3 hours)
        max_index = max(non_zero_indices)

        # With Bug 2: max_index ≈ 3-4 (deadline at 13:30 UTC, ~4h away)
        # Without Bug 2: max_index ≈ 2 (deadline at 11:30 UTC, ~2h away)
        assert max_index <= 2, (
            f"Last charging hour at index {max_index}, expected ≤ 2. "
            f"Bug 2: hora treated as UTC, shifting charging window ~2h late. "
            f"Non-zero indices: {non_zero_indices}"
        )

    def test_power_profile_charging_pattern(self):
        """P_deferrable must match expected pattern: [3300, 3300, 0, 0, ...].

        With tz=UTC+2, hora="13:30" local → deadline 11:30 UTC.
        Now: 09:15 UTC → horas_hasta_viaje = int(2.25) = 2.
        horas_necesarias = ceil(4.0/3.3) = 2.
        Charging at indices [0, 1] (last 2 hours before deadline).
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        profile = calculate_power_profile_from_trips(
            trips=[FRIDAY_TRIP_JS_FORMAT],
            power_kw=CHARGING_POWER_KW,
            reference_dt=FRIDAY_09_15_UTC,
            soc_current=SOC_CURRENT,
            battery_capacity_kwh=BATTERY_CAPACITY_KWH,
            tz=USER_TZ,  # Interpret hora as local time (UTC+2)
        )

        charging_power_w = CHARGING_POWER_KW * 1000  # 3300W

        # Expected pattern: [3300, 3300, 0, 0, ...]
        # (charging at hours 0 and 1, the last 2 hours before deadline at hour 2)
        assert (
            profile[0] == charging_power_w
        ), f"Hour 0 should be {charging_power_w}W, got {profile[0]}"
        assert (
            profile[1] == charging_power_w
        ), f"Hour 1 should be {charging_power_w}W, got {profile[1]}"
        assert (
            profile[2] == 0.0
        ), f"Hour 2 should be 0 (past deadline), got {profile[2]}"
        assert (
            profile[3] == 0.0
        ), f"Hour 3 should be 0 (past deadline), got {profile[3]}"

    def test_def_end_timestep_within_window(self):
        """def_end_timestep must be 2 (end of charging window at hour 2).

        The charging window is 11:00-13:30 local (09:00-11:30 UTC).
        def_end_timestep = int(hours_available) = int(2.25) = 2.

        With Bug 2: def_end_timestep ≈ 4-5 (deadline at 13:30 UTC, ~4.25h away).
        """
        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora="13:30",
            dia_semana="5",
            datetime_str=None,
            reference_dt=FRIDAY_09_15_UTC,
            tz=USER_TZ,  # Interpret hora as local time (UTC+2)
        )

        assert result is not None
        hours_available = (result - FRIDAY_09_15_UTC).total_seconds() / 3600
        def_end_timestep = int(max(0, hours_available))

        # Expected: ~2.25 hours → def_end_timestep = 2
        # Bug 2: ~4.25 hours → def_end_timestep = 4
        assert def_end_timestep == 2, (
            f"def_end_timestep={def_end_timestep}, expected 2. "
            f"hours_available={hours_available:.2f}h. "
            f"Bug 2: deadline computed at wrong timezone."
        )


class TestCalculateNextRecurringDatetimeTz:
    """Tests for calculate_next_recurring_datetime with tz parameter.

    Tests the branch where tz is not None and time has passed (days_ahead == 0
    but candidate_local < local_ref), causing days_ahead to become 7.
    """

    def test_time_passed_same_day_pushes_to_next_week(self):
        """When tz is provided and trip time has passed today, next week is returned.

        Scenario: Reference is Friday 23:00 local (UTC+2 = 21:00 UTC).
        Trip: Friday 22:00 local = 20:00 UTC (already passed).
        Expected: Next Friday (7 days ahead).
        """
        from datetime import datetime, timedelta, timezone

        from custom_components.ev_trip_planner.calculations import (
            calculate_next_recurring_datetime,
        )

        TZ_UTC_PLUS_2 = timezone(timedelta(hours=2))
        # Friday April 24, 2026 at 23:00 local = 21:00 UTC
        ref_local = datetime(2026, 4, 24, 23, 0, 0, tzinfo=TZ_UTC_PLUS_2)
        # Trip: Friday 22:00 local = 20:00 UTC (already passed)
        # Day=5 means Friday (JS getDay format: 0=Sun, 5=Fri)

        result = calculate_next_recurring_datetime(
            day=5,  # Friday in JS getDay format
            time_str="22:00",
            reference_dt=ref_local,
            tz=TZ_UTC_PLUS_2,
        )

        assert result is not None
        # Should be next Friday (7 days) since 22:00 local already passed
        expected = datetime(
            2026, 5, 1, 20, 0, 0, tzinfo=timezone.utc
        )  # May 1 20:00 UTC
        assert result == expected, (
            f"Expected next Friday 20:00 UTC, got {result}. "
            f"days_ahead should be 7 when trip time already passed."
        )


class TestCalculateTripTimeTz:
    """Tests for calculate_trip_time with tz parameter (line 146 coverage).

    The tz branch in calculate_trip_time was not covered by existing tests
    because calculate_power_profile_from_trips calls calculate_next_recurring_datetime
    (not calculate_trip_time) for recurring trips.
    """

    def test_trip_time_with_tz_covers_line_146(self):
        """Test calculate_trip_time with tz parameter covers line 146 (local_now).

        Scenario: Reference is Friday 09:15 UTC = 11:15 local (UTC+2).
        Trip: Friday 13:30 local.
        Result should be Friday 13:30 local converted to UTC.
        """
        from datetime import datetime, timedelta, timezone

        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        TZ_UTC_PLUS_2 = timezone(timedelta(hours=2))
        # Friday 09:15 UTC = 11:15 local (UTC+2)
        ref_utc = datetime(2026, 4, 24, 9, 15, 0, tzinfo=timezone.utc)

        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora="13:30",
            dia_semana="5",  # Friday in JS getDay format
            datetime_str=None,
            reference_dt=ref_utc,
            tz=TZ_UTC_PLUS_2,  # This triggers the tz branch (line 146)
        )

        assert result is not None
        # 13:30 local (UTC+2) = 11:30 UTC
        expected = datetime(2026, 4, 24, 11, 30, 0, tzinfo=timezone.utc)
        assert result == expected, (
            f"Expected Friday 11:30 UTC, got {result}. "
            f"hora '13:30' should be interpreted as local time (UTC+2)."
        )

    def test_trip_time_with_tz_time_passed_pushes_to_next_week(self):
        """Test calculate_trip_time with tz where local time has already passed.

        Scenario: Reference is Friday 14:00 UTC = 16:00 local (UTC+2).
        Trip: Friday 13:30 local (already passed).
        Result should be next Friday (7 days ahead).
        """
        from datetime import datetime, timedelta, timezone

        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        TZ_UTC_PLUS_2 = timezone(timedelta(hours=2))
        # Friday 14:00 UTC = 16:00 local (UTC+2) - trip time (13:30) has passed
        ref_utc = datetime(2026, 4, 24, 14, 0, 0, tzinfo=timezone.utc)

        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora="13:30",
            dia_semana="5",  # Friday in JS getDay format
            datetime_str=None,
            reference_dt=ref_utc,
            tz=TZ_UTC_PLUS_2,  # This triggers the tz branch with time-passed subbranch
        )

        assert result is not None
        # Next Friday: April 24 + 7 days = May 1
        # 13:30 local (UTC+2) = 11:30 UTC
        expected = datetime(2026, 5, 1, 11, 30, 0, tzinfo=timezone.utc)
        assert result == expected, (
            f"Expected next Friday 11:30 UTC, got {result}. "
            f"When local time has passed, should push to next week."
        )


# =============================================================================
# Integration: Full flow test (both bugs)
# =============================================================================


class TestIntegrationBothFixes:
    """Integration test: both bugs must be fixed for correct sensor output.

    Simulates the exact user scenario:
    - Friday 11:15 local (09:15 UTC)
    - Recurring trip: Friday 13:30 local, dia_semana="5" (JS format)
    - Battery: 30 kWh, SOC: 20%, Charging: 3.3 kW
    - Trip: 30 km, 7 kWh

    Expected sensor output:
        number_of_deferrable_loads: 1
        def_total_hours: [2]
        P_deferrable_nom: [3300.0]
        def_start_timestep: [0]
        def_end_timestep: [2]
        P_deferrable: [[3300.0, 3300.0, 0.0, 0.0, 0.0, ...]]
    """

    def test_full_output_correct(self):
        """End-to-end: sensor attributes match expected values."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
            calculate_trip_time,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        # Step 1: Calculate deadline (enrichment path)
        deadline = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora="13:30",
            dia_semana="5",
            datetime_str=None,
            reference_dt=FRIDAY_09_15_UTC,
            tz=USER_TZ,  # Interpret hora as local time (UTC+2)
        )
        assert deadline is not None, "Deadline calculation failed"

        # Step 2: Calculate def_end_timestep
        hours_available = (deadline - FRIDAY_09_15_UTC).total_seconds() / 3600
        def_end_timestep = int(max(0, hours_available))

        # Step 3: Calculate power profile
        profile = calculate_power_profile_from_trips(
            trips=[FRIDAY_TRIP_JS_FORMAT],
            power_kw=CHARGING_POWER_KW,
            reference_dt=FRIDAY_09_15_UTC,
            soc_current=SOC_CURRENT,
            battery_capacity_kwh=BATTERY_CAPACITY_KWH,
            tz=USER_TZ,  # Interpret hora as local time (UTC+2)
        )

        # Step 4: Assert all sensor values
        charging_power_w = CHARGING_POWER_KW * 1000  # 3300W

        # def_end_timestep must be 2 (not 29 from Bug 1, not 4-5 from Bug 2)
        assert def_end_timestep == 2, f"def_end_timestep={def_end_timestep}, expected 2"

        # P_deferrable must have exactly 2 non-zero values at positions 0 and 1
        # (horas_hasta_viaje=2, horas_necesarias=2, charging fills [0, 2))
        non_zero = [i for i, v in enumerate(profile) if v > 0]
        assert non_zero == [0, 1], f"Expected non-zero at [0, 1], got {non_zero}"

        # All non-zero values must equal charging power
        for idx in non_zero:
            assert (
                profile[idx] == charging_power_w
            ), f"profile[{idx}]={profile[idx]}, expected {charging_power_w}"

        # Verify first few hours match expected pattern
        expected_start = [charging_power_w, charging_power_w, 0.0, 0.0, 0.0]
        actual_start = profile[:5]
        assert (
            actual_start == expected_start
        ), f"Profile start: {actual_start}, expected: {expected_start}"
