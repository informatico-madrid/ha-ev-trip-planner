"""Test that multi-trip window_start uses previous_departure (not previous_arrival).

BUG-002: The previous code incorrectly calculated window_start for trip N as:
    previous_arrival + return_buffer_hours
  where previous_arrival = previous_trip.departure + duration_hours (default 6h)

This meant window_start was 6 hours later than needed. The correct formula is:
    previous_departure + return_buffer_hours (default 4h)

The difference: 6h (duration_hours) of wasted charging window per chained trip.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.ev_trip_planner.calculations import (
    calculate_multi_trip_charging_windows,
)


def _make_trip(dt: datetime, km: float = 50.0, kwh: float = 10.0) -> dict:
    """Return a minimal trip dict compatible with calculate_energy_needed."""
    return {
        "km": km,
        "kwh": kwh,
        "descripcion": "test",
    }


class TestPreviousArrivalInvariant:
    """Verify that multi-trip window start uses previous_departure + return_buffer_hours."""

    def test_trip1_window_starts_at_previous_departure_plus_buffer(self):
        """Trip 2 window_start must be trip1_departure + return_buffer_hours (NOT arrival).

        With the bug, window_start was trip1_arrival + return_buffer_hours
        = trip1_departure + duration_hours + return_buffer_hours
        = departure + 6h + 4h = departure + 10h

        The fix: window_start = trip1_departure + return_buffer_hours
        = departure + 4h

        Test uses trip1_departure=18:00, trip2_departure=00:00 next day
        so that window_start=22:00 (correct) < trip2_departure=00:00
        and window_start=04:00 (buggy) > trip2_departure, making the
        bug easily detectable.
        """
        now = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
        trip1_departure = datetime(2026, 5, 10, 18, 0, 0, tzinfo=timezone.utc)
        trip2_departure = datetime(2026, 5, 11, 0, 0, 0, tzinfo=timezone.utc)
        return_buffer_hours = 4.0

        trips = [
            (trip1_departure, _make_trip(trip1_departure)),
            (trip2_departure, _make_trip(trip2_departure)),
        ]

        results = calculate_multi_trip_charging_windows(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=7.4,
            battery_capacity_kwh=75.0,
            return_buffer_hours=return_buffer_hours,
            now=now,
        )

        assert len(results) == 2

        # Trip 1: window starts from now
        assert results[0]["inicio_ventana"] == now
        assert results[0]["fin_ventana"] == trip1_departure

        # Trip 2: window starts at trip1_departure + return_buffer_hours = 22:00
        expected_start_correct = trip1_departure + timedelta(hours=return_buffer_hours)
        expected_horas = 2.0  # 00:00 - 22:00 = 2h

        assert results[1]["inicio_ventana"] == expected_start_correct, (
            f"Expected window_start={expected_start_correct}, "
            f"got {results[1]['inicio_ventana']}. "
            f"Window should start at previous_departure + return_buffer_hours "
            f"(= {expected_start_correct}), not at previous_arrival + return_buffer_hours "
            f"(= trip1_departure + 6h + 4h = {trip1_departure + timedelta(hours=10)})"
        )
        assert results[1]["fin_ventana"] == trip2_departure
        assert results[1]["ventana_horas"] == pytest.approx(expected_horas, rel=1e-2), (
            f"ventana_horas={results[1]['ventana_horas']:.2f}h, expected {expected_horas}h"
        )

    def test_window_start_not_delayed_by_duration_hours(self):
        """Verify the 6h delay bug is fixed: window_start should NOT include duration_hours."""
        now = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
        trip1_departure = datetime(2026, 5, 10, 18, 0, 0, tzinfo=timezone.utc)
        trip2_departure = datetime(2026, 5, 11, 0, 0, 0, tzinfo=timezone.utc)

        # duration=6h, return_buffer=4h
        # With bug: window_start = (18:00 + 6h) + 4h = 04:00 next day
        # Without bug: window_start = 18:00 + 4h = 22:00 same day
        trips = [
            (trip1_departure, _make_trip(trip1_departure)),
            (trip2_departure, _make_trip(trip2_departure)),
        ]

        results = calculate_multi_trip_charging_windows(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=7.4,
            battery_capacity_kwh=75.0,
            return_buffer_hours=4.0,
            now=now,
        )

        # The window_start for trip 2 should NOT be delayed by an extra 6h
        expected_start_correct = trip1_departure + timedelta(hours=4)  # 22:00

        assert results[1]["inicio_ventana"] == expected_start_correct, (
            f"Window start should be 22:00 (departure + 4h buffer), "
            f"not 04:00 (departure + 6h duration + 4h buffer). "
            f"Got {results[1]['inicio_ventana']}"
        )

    def test_three_trips_chaining_invariant(self):
        """Verify window_start for trips 2 and 3 both use previous_departure + buffer."""
        now = datetime(2026, 5, 10, 8, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 5, 10, 14, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 5, 10, 20, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 5, 11, 2, 0, 0, tzinfo=timezone.utc)

        trips = [
            (t1, _make_trip(t1)),
            (t2, _make_trip(t2)),
            (t3, _make_trip(t3)),
        ]

        results = calculate_multi_trip_charging_windows(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=7.4,
            battery_capacity_kwh=75.0,
            return_buffer_hours=4.0,
            now=now,
        )

        assert len(results) == 3

        # Trip 1: starts from now
        assert results[0]["inicio_ventana"] == now
        assert results[0]["fin_ventana"] == t1

        # Trip 2: starts at t1 + 4h
        assert results[1]["inicio_ventana"] == t1 + timedelta(hours=4)
        assert results[1]["fin_ventana"] == t2

        # Trip 3: starts at t2 + 4h (NOT t2 + 6h + 4h)
        assert results[2]["inicio_ventana"] == t2 + timedelta(hours=4)
        assert results[2]["fin_ventana"] == t3

        # ventana_horas should reflect correct window size
        # Trip 2: t1 + 4h = 18:00 to t2 = 20:00 => 2h
        assert results[1]["ventana_horas"] == pytest.approx(2.0, rel=1e-2)
        # Trip 3: t2 + 4h = 00:00 to t3 = 02:00 => 2h
        assert results[2]["ventana_horas"] == pytest.approx(2.0, rel=1e-2)
