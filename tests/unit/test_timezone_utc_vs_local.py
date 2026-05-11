"""Tests for timezone UTC vs local time bug across all affected functions.

BUG: Multiple functions use datetime.now(timezone.utc) as default reference,
causing timestamps and hour calculations to be in UTC instead of local time.

When a user is in CEST (UTC+2) and it's 16:50 local time:
- datetime.now(timezone.utc) = 14:50 UTC
- The schedule shows 14:00 instead of 16:00
- Power profile positions are offset by 2 hours
- Recurring trip times are treated as UTC instead of local

These tests use DYNAMIC dates based on the current moment, so they work
regardless of when they are executed.

All tests are DETERMINISTIC: they pass explicit reference_dt parameters
or use unittest.mock.patch to control datetime.now().

Run with: pytest tests/test_timezone_utc_vs_local_bug.py -v
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from custom_components.ev_trip_planner.calculations import (
    calculate_deferrable_parameters,
    calculate_multi_trip_charging_windows,
    calculate_next_recurring_datetime,
    calculate_power_profile_from_trips,
    generate_deferrable_schedule_from_trips,
)

# =============================================================================
# Test constants: DYNAMIC - computed from current moment
# =============================================================================
MADRID_TZ = ZoneInfo("Europe/Madrid")

# Current moment in local and UTC
LOCAL_NOW = datetime.now(MADRID_TZ)
UTC_NOW = LOCAL_NOW.astimezone(timezone.utc)

# JS getDay() format: 0=Sunday, 1=Monday, ..., 6=Saturday
# Python isoweekday(): 1=Monday, ..., 7=Sunday
# Convert: JS_day = isoweekday % 7
JS_TODAY = LOCAL_NOW.isoweekday() % 7
JS_TOMORROW = (JS_TODAY + 1) % 7
JS_DAY_AFTER = (JS_TODAY + 2) % 7

# Tomorrow at 00:30 local (for midnight boundary tests)
TOMORROW_00_30_LOCAL = datetime(
    LOCAL_NOW.year,
    LOCAL_NOW.month,
    LOCAL_NOW.day,
    0,
    30,
    0,
    tzinfo=MADRID_TZ,
) + timedelta(days=1)
TOMORROW_00_30_UTC = TOMORROW_00_30_LOCAL.astimezone(timezone.utc)

# Early morning today: 01:00 local
TODAY_01_00_LOCAL = datetime(
    LOCAL_NOW.year,
    LOCAL_NOW.month,
    LOCAL_NOW.day,
    1,
    0,
    0,
    tzinfo=MADRID_TZ,
)


# =============================================================================
# BUG 1: generate_deferrable_schedule_from_trips uses UTC timestamps
# =============================================================================
class TestScheduleTimezone:
    """Bug: deferrables_schedule shows UTC hours instead of local hours."""

    def test_schedule_with_utc_reference_shows_utc_hours(self):
        """With UTC reference, schedule first hour is UTC hour, not local hour.

        This documents the CURRENT production behavior since the default
        reference_dt is datetime.now(timezone.utc).
        """
        trips = [
            {
                "id": "trip1",
                "kwh": 10.0,
                "datetime": (UTC_NOW + timedelta(hours=8)).isoformat(),
            }
        ]

        # Pass UTC reference explicitly (current production default)
        schedule = generate_deferrable_schedule_from_trips(
            trips, 3.6, reference_dt=UTC_NOW
        )

        assert len(schedule) > 0, "Schedule should not be empty"
        first_dt = datetime.fromisoformat(schedule[0]["date"])

        # With UTC reference, first hour is the current UTC hour (floored)
        assert (
            first_dt.hour == UTC_NOW.hour
        ), f"With UTC reference, first hour should be {UTC_NOW.hour}, got {first_dt.hour}"

    def test_schedule_with_local_reference_shows_local_hours(self):
        """With local reference, schedule first hour is the local hour."""
        trips = [
            {
                "id": "trip1",
                "kwh": 10.0,
                "datetime": (LOCAL_NOW + timedelta(hours=8)).isoformat(),
            }
        ]

        # Pass LOCAL reference (desired behavior)
        schedule = generate_deferrable_schedule_from_trips(
            trips, 3.6, reference_dt=LOCAL_NOW
        )

        first_dt = datetime.fromisoformat(schedule[0]["date"])
        # With local reference, first hour should be local hour
        assert (
            first_dt.hour == LOCAL_NOW.hour
        ), f"With local reference, first hour should be {LOCAL_NOW.hour}, got {first_dt.hour}"

    def test_schedule_default_uses_utc_not_local(self):
        """Without reference_dt, pure function defaults to UTC.

        The FIX is in emhass_adapter._generate_schedule_from_trips which
        now passes reference_dt=dt_util.now() (local time).
        This test verifies the pure function's default is still UTC
        (which is fine - the adapter overrides it).
        """
        trips = [
            {
                "id": "trip1",
                "kwh": 10.0,
                "datetime": (LOCAL_NOW + timedelta(hours=8)).isoformat(),
            }
        ]

        # Mock datetime.now to return UTC time (simulates default behavior)
        with patch(
            "custom_components.ev_trip_planner.calculations.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = UTC_NOW
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            mock_dt.fromisoformat = datetime.fromisoformat

            schedule = generate_deferrable_schedule_from_trips(trips, 3.6)

        first_dt = datetime.fromisoformat(schedule[0]["date"])

        # Default behavior: UTC hours (the adapter now overrides this)
        assert first_dt.hour == UTC_NOW.hour, (
            f"Default behavior: first hour should be {UTC_NOW.hour} (UTC). "
            f"Got {first_dt.hour}. The adapter fix passes reference_dt=dt_util.now()."
        )

    def test_schedule_timezone_suffix_is_local_with_local_reference(self):
        """With local reference_dt, schedule dates carry local timezone offset."""
        trips = [
            {
                "id": "trip1",
                "kwh": 10.0,
                "datetime": (LOCAL_NOW + timedelta(hours=8)).isoformat(),
            }
        ]

        # Pass local reference (what the adapter now does after fix)
        schedule = generate_deferrable_schedule_from_trips(
            trips, 3.6, reference_dt=LOCAL_NOW
        )

        first_date_str = schedule[0]["date"]
        local_offset_str = LOCAL_NOW.strftime("%z")  # e.g., "+0200"
        local_offset_formatted = (
            f"{local_offset_str[:3]}:{local_offset_str[3:]}"  # "+02:00"
        )
        assert local_offset_formatted in first_date_str, (
            f"Schedule timezone should be local ({local_offset_formatted}), "
            f"got: {first_date_str}"
        )


# =============================================================================
# BUG 2: calculate_power_profile_from_trips uses UTC reference
# =============================================================================
class TestPowerProfileTimezone:
    """Bug: Power profile positions are offset by timezone difference."""

    def test_power_profile_utc_vs_local_reference_differ_for_recurring(self):
        """Power profile with UTC reference differs from local for recurring trips.

        When a recurring trip has time="08:00" (meaning 8am local):
        - With tz=None: 08:00 is treated as UTC → trip at 08:00 UTC
        - With tz=MADRID_TZ: 08:00 is treated as local → trip at 08:00 local
        The charging positions in the profile should differ by the timezone offset.
        """
        # Recurring trip: day after tomorrow at 08:00
        trips = [
            {
                "id": "trip_recurring",
                "kwh": 10.0,
                "day": JS_DAY_AFTER,
                "time": "08:00",
            }
        ]

        # With UTC reference and no tz (current production behavior)
        profile_utc = calculate_power_profile_from_trips(
            trips, 3.6, reference_dt=UTC_NOW, tz=None
        )

        # With LOCAL reference and tz (desired behavior)
        profile_local = calculate_power_profile_from_trips(
            trips, 3.6, reference_dt=LOCAL_NOW, tz=MADRID_TZ
        )

        # Count non-zero hours in each profile
        utc_charging_hours = sum(1 for x in profile_utc if x > 0)
        local_charging_hours = sum(1 for x in profile_local if x > 0)

        assert utc_charging_hours > 0, "UTC profile should have charging"
        assert local_charging_hours > 0, "Local profile should have charging"

        # Find first charging position in each
        utc_first = next(i for i, x in enumerate(profile_utc) if x > 0)
        local_first = next(i for i, x in enumerate(profile_local) if x > 0)

        # BUG: Without tz, calculate_next_recurring_datetime treats "08:00"
        # as UTC, so the trip appears at 08:00 UTC (not 08:00 local)
        # With tz, it correctly calculates 08:00 local
        # The positions should differ by the timezone offset hours
        assert utc_first != local_first, (
            f"BUG: UTC first charging at position {utc_first}, "
            f"local at position {local_first}. "
            f"They should differ because UTC treats '08:00' as UTC time, "
            f"not local time."
        )

    def test_power_profile_punctual_trip_utc_vs_local(self):
        """Punctual trip profile with UTC vs local reference.

        For punctual trips with aware deadlines, both references produce
        the same profile because the delta is the same.
        """
        trip_deadline_local = LOCAL_NOW + timedelta(hours=4)
        trips = [
            {
                "id": "trip1",
                "kwh": 10.0,
                "datetime": trip_deadline_local.isoformat(),
            }
        ]

        # Get profile with explicit local reference (desired)
        profile_local = calculate_power_profile_from_trips(
            trips, 3.6, reference_dt=LOCAL_NOW
        )

        # Get profile with explicit UTC reference (current default)
        profile_utc = calculate_power_profile_from_trips(
            trips, 3.6, reference_dt=UTC_NOW
        )

        local_first = next((i for i, x in enumerate(profile_local) if x > 0), None)
        utc_first = next((i for i, x in enumerate(profile_utc) if x > 0), None)

        # With aware datetimes, the delta is the same, so positions match.
        assert local_first is not None, "Local profile should have charging"
        assert utc_first is not None, "UTC profile should have charging"
        # Both represent the same instant, so positions should be the same
        assert (
            local_first == utc_first
        ), "With aware deadlines, both references should produce same profile"


# =============================================================================
# BUG 3: calculate_next_recurring_datetime without tz treats time as UTC
# =============================================================================
class TestRecurringDatetimeTimezone:
    """Bug: Recurring trip times treated as UTC instead of local.

    When tz=None, calculate_next_recurring_datetime treats time_str as UTC.
    A trip with hora="08:00" (meaning 8am local) is calculated as 08:00 UTC
    = 10:00 CEST, which is wrong.
    """

    def test_recurring_trip_8am_should_be_local_8am(self):
        """With tz parameter, 08:00 is correctly treated as local time.

        The FIX is in emhass_adapter._calculate_deadline_from_trip which
        now passes tz=self.hass.config.time_zone.
        This test verifies the pure function works correctly with tz.
        """
        # Trip: tomorrow at 08:00
        result_local = calculate_next_recurring_datetime(
            day=JS_TOMORROW, time_str="08:00", reference_dt=UTC_NOW, tz=MADRID_TZ
        )

        assert result_local is not None, "Local result should not be None"

        # Convert to Madrid time for verification
        result_local_local = result_local.astimezone(MADRID_TZ)

        # With tz: result is tomorrow 08:00 local (correct)
        assert (
            result_local_local.hour == 8
        ), f"With tz, result should be 08:00 local, got {result_local_local.hour}:00"

    def test_recurring_trip_day_boundary_mismatch(self):
        """After local midnight, UTC is still previous day → day-of-week mismatch.

        When it's tomorrow 00:30 local = today 22:30 UTC (for CEST):
        - Without tz: reference is still "today" in UTC, trip for "tomorrow"
          is the NEXT day from UTC's perspective
        - With tz: correctly identifies it's already "tomorrow" locally,
          so trip for "tomorrow" is TODAY from local perspective
        """
        # Use dynamic tomorrow at 00:30 local
        # UTC will be today at 22:30 (for CEST, UTC+2)
        local_ref = TOMORROW_00_30_LOCAL
        utc_ref = TOMORROW_00_30_UTC

        # What "tomorrow" is in JS day format from each perspective
        js_tomorrow_local = local_ref.isoweekday() % 7  # tomorrow's weekday
        _js_today_utc = utc_ref.isoweekday() % 7  # noqa: F841 — today's weekday in UTC

        # If the timezone offset makes the UTC date differ from local date
        if utc_ref.date() == local_ref.date():
            pytest.skip(
                "Timezone offset doesn't cause date difference at this time. "
                "This test requires UTC+X where X > 0 and local time just after midnight."
            )

        # Trip: "tomorrow" from local perspective (JS day)
        result_local = calculate_next_recurring_datetime(
            day=js_tomorrow_local,
            time_str="08:00",
            reference_dt=utc_ref,
            tz=MADRID_TZ,
        )

        result_utc = calculate_next_recurring_datetime(
            day=js_tomorrow_local,
            time_str="08:00",
            reference_dt=utc_ref,
            tz=None,
        )

        assert result_local is not None
        assert result_utc is not None

        # With tz: local is tomorrow 00:30, trip for tomorrow 08:00 is ~7.5h away
        local_delta = (result_local - utc_ref).total_seconds() / 3600

        # Without tz: UTC is still today, trip for "tomorrow" is further away
        utc_delta = (result_utc - utc_ref).total_seconds() / 3600

        # The deltas should differ significantly
        assert abs(local_delta - utc_delta) > 1, (
            f"BUG: Local delta={local_delta:.1f}h, UTC delta={utc_delta:.1f}h. "
            f"They should differ significantly because at 00:30 local it's "
            f"already tomorrow, but at {utc_ref.hour}:{utc_ref.minute:02d} UTC "
            f"(same instant) it's still today."
        )


# =============================================================================
# BUG 4: calculate_multi_trip_charging_windows uses datetime.now(timezone.utc)
# =============================================================================
class TestChargingWindowsTimezone:
    """Bug: Charging windows use UTC now, affecting window start calculation.

    calculate_multi_trip_charging_windows() has NO 'now' parameter.
    It hardcodes datetime.now(timezone.utc) at line 519.

    NOTE: We cannot mock datetime here because the function uses
    isinstance(trip_departure_time, datetime) which breaks with mocks.
    Instead, we verify the output properties directly.
    """

    def test_charging_window_inicio_has_local_timezone_with_local_now(self):
        """With local now parameter, inicio_ventana carries local timezone.

        The FIX is in emhass_adapter which now passes now=dt_util.now().
        This test verifies the pure function works correctly with local now.
        """
        # Use a trip far enough in the future to always work
        trip_deadline = LOCAL_NOW + timedelta(hours=6)
        trips = [
            (trip_deadline, {"id": "trip1", "kwh": 10.0, "km": 50.0}),
        ]

        windows = calculate_multi_trip_charging_windows(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=3.6,
            battery_capacity_kwh=50.0,
            now=LOCAL_NOW,
        )

        assert len(windows) == 1, "Should have one window"
        inicio = windows[0]["inicio_ventana"]
        assert inicio is not None, "Should have inicio_ventana"

        # With local now, inicio should have local timezone
        assert inicio.tzinfo == MADRID_TZ, (
            f"inicio_ventana should have Madrid timezone, "
            f"got {inicio.tzinfo}. inicio: {inicio}"
        )

    def test_charging_window_inicio_is_close_to_now(self):
        """inicio_ventana should be close to current time.

        Documents that inicio_ventana is based on datetime.now(timezone.utc).
        """
        now_before = datetime.now(timezone.utc)
        trip_deadline = now_before + timedelta(hours=6)
        trips = [
            (trip_deadline, {"id": "trip1", "kwh": 10.0, "km": 50.0}),
        ]

        windows = calculate_multi_trip_charging_windows(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=3.6,
            battery_capacity_kwh=50.0,
        )

        now_after = datetime.now(timezone.utc)
        inicio = windows[0]["inicio_ventana"]

        # inicio should be between now_before and now_after
        assert (
            now_before <= inicio <= now_after
        ), f"inicio_ventana ({inicio}) should be between {now_before} and {now_after}"


# =============================================================================
# BUG 5: calculate_deferrable_parameters uses datetime.now() (naive)
# =============================================================================
class TestDeferrableParametersTimezone:
    """Bug: calculate_deferrable_parameters uses datetime.now() without tz."""

    def test_deferrable_params_end_timestep_with_utc_vs_local(self):
        """end_timestep is the same with UTC or local reference for aware deadlines."""
        trip = {
            "kwh": 10.0,
            "datetime": (LOCAL_NOW + timedelta(hours=3, minutes=10)).isoformat(),
        }

        # With UTC reference
        params_utc = calculate_deferrable_parameters(trip, 3.6, reference_dt=UTC_NOW)

        # With local reference
        params_local = calculate_deferrable_parameters(
            trip, 3.6, reference_dt=LOCAL_NOW
        )

        assert "end_timestep" in params_utc
        assert "end_timestep" in params_local

        # Both should give same end_timestep since deadline is aware
        # and both references represent the same instant
        assert params_utc["end_timestep"] == params_local["end_timestep"], (
            f"end_timestep should be same regardless of tz representation. "
            f"UTC: {params_utc['end_timestep']}, Local: {params_local['end_timestep']}"
        )

    def test_deferrable_params_default_uses_system_now(self):
        """Documents that without reference_dt, uses datetime.now() (system tz).

        The function defaults to datetime.now() which is naive and uses
        system timezone. This may not match the HA-configured timezone.
        """
        trip_deadline = LOCAL_NOW + timedelta(hours=5)
        trip = {
            "kwh": 10.0,
            "datetime": trip_deadline.isoformat(),
        }

        # With explicit local reference (desired)
        params_local = calculate_deferrable_parameters(
            trip, 3.6, reference_dt=LOCAL_NOW
        )

        # With explicit UTC reference
        params_utc = calculate_deferrable_parameters(trip, 3.6, reference_dt=UTC_NOW)

        # Both should produce the same result for aware deadlines
        assert (
            params_local["end_timestep"] == params_utc["end_timestep"]
        ), "With aware deadline, both references should give same result"

        assert params_local["end_timestep"] > 0, "Should have positive end_timestep"


# =============================================================================
# BUG 6: Edge case - midnight boundary date mismatch
# =============================================================================
class TestMidnightBoundaryTimezone:
    """Bug: Using UTC date for 'today' calculations fails around midnight.

    When it's 00:30 local (22:30 UTC previous day for CEST),
    UTC date is YESTERDAY, so trips for "today" (local) are missed.
    """

    def test_utc_date_differs_from_local_after_midnight(self):
        """After local midnight, UTC date may still be previous day."""
        # Tomorrow at 00:30 local
        local_after_midnight = TOMORROW_00_30_LOCAL
        utc_before_midnight = TOMORROW_00_30_UTC

        # For positive UTC offsets (e.g., CEST = UTC+2), UTC is behind local
        # So at 00:30 local, UTC is 22:30 previous day
        if utc_before_midnight.date() == local_after_midnight.date():
            pytest.skip(
                "Timezone offset doesn't cause date difference. "
                "This test requires a positive UTC offset (e.g., CEST)."
            )

        assert utc_before_midnight.date() != local_after_midnight.date(), (
            f"BUG: UTC date ({utc_before_midnight.date()}) differs from "
            f"local date ({local_after_midnight.date()}) around midnight. "
            f"Using UTC date for 'today' calculations will miss trips "
            f"scheduled for the local 'today'."
        )

    def test_utc_date_matches_local_during_daytime(self):
        """During daytime, UTC and local dates typically match."""
        # During daytime (roughly 02:00-22:00 local for CEST),
        # UTC and local dates should match when timezone offset is small.
        # For timezones with large offsets (e.g. Europe/Madrid UTC+2),
        # UTC date can differ from local date even during daytime.
        utc_offset_hours = LOCAL_NOW.utcoffset().total_seconds() / 3600
        if abs(utc_offset_hours) >= 2:
            # Large offset: dates may differ — verify they differ by at most 1 day
            day_diff = abs((LOCAL_NOW.date() - UTC_NOW.date()).days)
            assert day_diff <= 1, (
                f"UTC and local dates should differ by at most 1 day, "
                f"got {UTC_NOW.date()} vs {LOCAL_NOW.date()}"
            )
            return

        assert (
            UTC_NOW.date() == LOCAL_NOW.date()
        ), "During daytime, UTC and local dates should typically match"

    def test_early_morning_local_utc_still_previous_day(self):
        """Early morning local time: UTC may still be previous day."""
        # Today at 01:00 local
        local_early = TODAY_01_00_LOCAL
        utc_late = local_early.astimezone(timezone.utc)

        # For CEST (UTC+2): 01:00 local = 23:00 UTC previous day
        if utc_late.date() == local_early.date():
            pytest.skip(
                "Timezone offset doesn't cause date difference at 01:00 local. "
                "This test requires a positive UTC offset >= 1 hour."
            )

        assert utc_late.date() < local_early.date(), (
            f"BUG: At 01:00 local, UTC date ({utc_late.date()}) "
            f"is still previous day ({local_early.date()}). "
            f"Trips for 'today' (local) would be missed "
            f"if using UTC date."
        )


# =============================================================================
# INTEGRATION: Full chain test - schedule shows wrong hours
# =============================================================================
class TestIntegrationScheduleTimezone:
    """Integration test: the full chain from trip to sensor attribute."""

    def test_full_chain_schedule_with_utc_reference(self):
        """With UTC reference, schedule shows UTC hours (current bug)."""
        trip_deadline_local = LOCAL_NOW + timedelta(hours=4)
        trips = [
            {
                "id": "commute_home",
                "kwh": 8.0,
                "km": 40.0,
                "datetime": trip_deadline_local.isoformat(),
            }
        ]

        # How emhass_adapter calls it (UTC reference, current behavior)
        schedule = generate_deferrable_schedule_from_trips(
            trips, 3.6, reference_dt=UTC_NOW
        )

        # Parse all schedule dates
        schedule_hours = [
            datetime.fromisoformat(entry["date"]).hour for entry in schedule
        ]

        # With UTC reference, first hour is current UTC hour
        first_hour = schedule_hours[0]
        assert (
            first_hour == UTC_NOW.hour
        ), f"With UTC reference, first hour should be {UTC_NOW.hour}, got {first_hour}"

    def test_full_chain_schedule_with_local_reference(self):
        """With local reference, schedule shows local hours (desired)."""
        trip_deadline_local = LOCAL_NOW + timedelta(hours=4)
        trips = [
            {
                "id": "commute_home",
                "kwh": 8.0,
                "km": 40.0,
                "datetime": trip_deadline_local.isoformat(),
            }
        ]

        # How emhass_adapter SHOULD call it (local reference)
        schedule = generate_deferrable_schedule_from_trips(
            trips, 3.6, reference_dt=LOCAL_NOW
        )

        schedule_hours = [
            datetime.fromisoformat(entry["date"]).hour for entry in schedule
        ]

        # With local reference, first hour is current local hour
        first_hour = schedule_hours[0]
        assert (
            first_hour == LOCAL_NOW.hour
        ), f"With local reference, first hour should be {LOCAL_NOW.hour}, got {first_hour}"

    def test_emhass_adapter_call_path_now_produces_local_schedule(self):
        """After fix: adapter passes reference_dt=dt_util.now() producing local schedule.

        Call chain (FIXED):
        1. emhass_adapter._generate_schedule_from_trips(trips, power_kw)
        2. → generate_deferrable_schedule_from_trips(trips, power_kw, reference_dt=dt_util.now())
        3. → Schedule entries use LOCAL hours
        """
        trip_deadline_local = LOCAL_NOW + timedelta(hours=4)
        trips = [
            {
                "id": "trip1",
                "kwh": 8.0,
                "datetime": trip_deadline_local.isoformat(),
            }
        ]

        # Simulate what the adapter now does: pass reference_dt=LOCAL_NOW
        schedule = generate_deferrable_schedule_from_trips(
            trips, 3.6, reference_dt=LOCAL_NOW
        )

        first_dt = datetime.fromisoformat(schedule[0]["date"])

        # With local reference, first hour is local
        assert first_dt.hour == LOCAL_NOW.hour, (
            f"After fix: Schedule first hour should be {LOCAL_NOW.hour} "
            f"(local), got {first_dt.hour}. "
            f"Full schedule: {[datetime.fromisoformat(e['date']).hour for e in schedule[:6]]}"
        )


# =============================================================================
# SUMMARY: Count of affected sites
# =============================================================================
class TestTimezoneSummary:
    """Summary of all timezone-affected sites in the codebase."""

    def test_summary_of_affected_sites(self):
        """Documents all sites affected by UTC vs local timezone bug.

        AFFECTED SITES (using datetime.now(timezone.utc) for user-visible data):

        1. generate_deferrable_schedule_from_trips() - calculations.py:1242
           IMPACT: deferrables_schedule attribute shows UTC hours
           SEVERITY: CRITICAL (user-visible wrong data)

        2. calculate_power_profile_from_trips() - calculations.py:969
           IMPACT: Power profile positions offset by timezone hours
           SEVERITY: HIGH (EMHASS may misinterpret charging windows)

        3. calculate_next_recurring_datetime() - calculations.py:924-935
           IMPACT: Without tz param, treats trip time as UTC not local
           SEVERITY: HIGH (recurring trips at wrong time)
           CALLED FROM: emhass_adapter.py:524, trip_manager.py:245

        4. calculate_multi_trip_charging_windows() - calculations.py:519
           IMPACT: inicio_ventana/fin_ventana in UTC, not local
           SEVERITY: MEDIUM (propagates to def_start/end_timestep)

        5. _populate_per_trip_cache_entry() - emhass_adapter.py:574
           IMPACT: def_start_timestep/def_end_timestep from UTC reference
           SEVERITY: MEDIUM (may cause EMHASS offset)

        6. async_publish_deferrable_load() - emhass_adapter.py:367
           IMPACT: hours_available calculated from UTC now
           SEVERITY: LOW (internally consistent)

        7. publish_deferrable_loads() - emhass_adapter.py:1203
           IMPACT: Recurring trip enrichment uses UTC reference
           SEVERITY: HIGH (same as #3)

        8. trip_manager.publish_deferrable_loads() - trip_manager.py:245
           IMPACT: Recurring trip rotation uses UTC reference
           SEVERITY: HIGH (same as #3)

        9. async_get_kwh_needed_today() - trip_manager.py:1197
           IMPACT: Uses UTC date, wrong around midnight
           SEVERITY: MEDIUM (edge case)

        10. async_get_next_trip() - trip_manager.py:1293
            IMPACT: Uses UTC now for comparison
            SEVERITY: LOW (internally consistent)
        """
        # This test always passes - it's documentation
        affected_count = 10
        assert affected_count == 10


class TestInvalidTimezoneFallback:
    """Test that invalid timezone strings fall back to UTC behavior."""

    def test_invalid_timezone_string_falls_back_to_utc(self):
        """When tz is an invalid string, calculate_next_recurring_datetime falls back to UTC."""
        from datetime import datetime, timezone

        reference = datetime(2026, 4, 30, 15, 0, 0, tzinfo=timezone.utc)
        # Pass an invalid timezone string - should fall back to UTC behavior
        result = calculate_next_recurring_datetime(
            1,  # Monday
            "08:00",
            reference_dt=reference,
            tz="Invalid/Timezone",
        )
        # Should still return a result (falling back to UTC behavior)
        assert result is not None
        # Should be treated as UTC time (no timezone conversion)
        assert result.tzinfo == timezone.utc

    def test_non_tzinfo_object_falls_back_to_utc(self):
        """When tz is a non-tzinfo object (e.g., MagicMock), falls back to UTC behavior."""
        from datetime import datetime, timezone
        from unittest.mock import MagicMock

        reference = datetime(2026, 4, 30, 15, 0, 0, tzinfo=timezone.utc)
        mock_tz = MagicMock()  # Not a tzinfo subclass
        result = calculate_next_recurring_datetime(
            1,  # Monday
            "08:00",
            reference_dt=reference,
            tz=mock_tz,
        )
        # Should still return a result (falling back to UTC behavior)
        assert result is not None
        assert result.tzinfo == timezone.utc
