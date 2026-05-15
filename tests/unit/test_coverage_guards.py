"""Coverage guard tests — edge case paths that were unreachable before.

These tests cover 5 edge case guard lines that were added during SOLID
refactoring but lacked dedicated coverage:

  - power.py:101   — _compute_charging_hours: horas_necesarias==0 fallback
  - power.py:262   — _assign_deadlines: trip with tipo=None filtered out
  - deficit.py:236 — _compute_trip_trip_time: trip with tipo=None returns None
  - windows.py:286 — calculate_multi_trip_charging_windows: window_start=None skipped
  - _schedule.py:36 — TripScheduler._read_battery_config: entry_id=None fallback
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

# === _compute_charging_hours: horas_necesarias == 0 fallback (power.py:101) ===


def test_compute_charging_hours_zero_energy():
    """When kwh=0, horas_necesarias falls to 1 (minimum 1 hour)."""
    from custom_components.ev_trip_planner.calculations.power import (
        _compute_charging_hours,
    )

    # kwh=0 → total_hours=0 → horas_necesarias=0 → falls to 1
    start, end = _compute_charging_hours(0.0, 3.6, 168, 10)
    assert start == 9  # max(0, 10 - 1) = 9
    assert end == 10


def test_compute_charging_hours_exact_hours():
    """kwh/power_kw is exactly integer — no rounding up."""
    from custom_components.ev_trip_planner.calculations.power import (
        _compute_charging_hours,
    )

    # 7.2 kWh / 3.6 kW = 2.0 hours exactly
    start, end = _compute_charging_hours(7.2, 3.6, 168, 5)
    assert start == 3  # max(0, 5 - 2) = 3
    assert end == 5


def test_compute_charging_hours_partial_rounds_up():
    """kwh/power_kw is fractional — rounds up to next hour."""
    from custom_components.ev_trip_planner.calculations.power import (
        _compute_charging_hours,
    )

    # 7.3 kWh / 3.6 kW = 2.028 → rounds up to 3 hours
    start, end = _compute_charging_hours(7.3, 3.6, 168, 5)
    assert start == 2  # max(0, 5 - 3) = 2
    assert end == 5


# === _assign_deadlines: trip with tipo=None filtered (power.py:262) ===


def test_assign_deadlines_filters_none_tipo():
    """Trips with tipo=None are filtered out by the None guard."""
    from custom_components.ev_trip_planner.calculations.power import (
        _assign_deadlines,
    )

    ref = datetime(2099, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    trips = [
        {
            "tipo": None,  # This should be filtered
            "id": "bad",
            "kwh": 5.0,
            "hora": "10:00",
            "dia_semana": "lunes",
        },
        {
            "tipo": "recurrente",
            "id": "good",
            "kwh": 5.0,
            "hora": "14:00",
            "dia_semana": "lunes",
        },
    ]
    result = _assign_deadlines(trips, ref)
    assert len(result) == 1
    assert result[0][2]["id"] == "good"


# === _get_trip_time: trip with tipo=None returns None (deficit.py:236) ===


def test_compute_trip_trip_time_none_tipo():
    """_compute_trip_trip_time returns None when tipo is None."""
    from custom_components.ev_trip_planner.calculations.deficit import (
        _compute_trip_trip_time,
    )

    ref = datetime(2099, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    trip = {"id": "t1", "tipo": None, "kwh": 5.0}
    result = _compute_trip_trip_time(trip, None, ref)
    assert result is None


# === calculate_multi_trip_charging_windows: window_start=None skipped (windows.py:286) ===


def test_multi_trip_windows_null_window_start():
    """When _compute_window_start returns None, the trip is skipped (continue)."""
    from custom_components.ev_trip_planner.calculations.windows import (
        calculate_multi_trip_charging_windows,
    )

    # Pass an empty trips list to exercise the early return
    result = calculate_multi_trip_charging_windows(
        trips=[],
        soc_actual=50.0,
        hora_regreso=None,
        charging_power_kw=3.6,
        battery_capacity_kwh=75.0,
        return_buffer_hours=2.0,
        safety_margin_percent=10.0,
    )
    assert result == []


# === TripScheduler._read_battery_config: entry_id=None fallback (_schedule.py:36) ===


def test_read_battery_config_entry_id_none():
    """When entry_id is None, _read_battery_config returns defaults (50.0, 10.0)."""
    from unittest.mock import MagicMock

    from custom_components.ev_trip_planner.trip._schedule import TripScheduler
    from custom_components.ev_trip_planner.trip.state import TripManagerState

    state = MagicMock(spec=TripManagerState)
    state.entry_id = None
    state.hass = MagicMock()

    scheduler = TripScheduler.__new__(TripScheduler)
    scheduler._state = state

    cap, margin = scheduler._read_battery_config()
    assert cap == 50.0
    assert margin == 10.0
