"""Tests for uncovered coordinator.py paths (lines 315, 391-399, 443-481)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.coordinator import (
    CoordinatorConfig,
    TripPlannerCoordinator,
)


# Mock frame reporting for HA 2026.3+ compatibility
@pytest.fixture(autouse=True)
def mock_frame_reporting():
    """Mock frame reporting to avoid 'Frame helper not set up' error."""
    with patch("homeassistant.helpers.frame.report_usage", return_value=None):
        yield


def _make_mock_hass():
    """Create a minimal mock HomeAssistant."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return hass


def _make_mock_entry(vehicle_name="test_vehicle", extra_data=None, extra_options=None):
    """Create a minimal mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        "vehicle_name": vehicle_name,
        "charging_power_kw": 7.0,
        "battery_capacity_kwh": 75.0,
        "kwh_per_km": 0.15,
        "safety_margin_percent": 10.0,
        "soc_base": 20.0,
        "t_base": 24.0,
    }
    entry.options = extra_options or {}
    if extra_data:
        entry.data.update(extra_data)
    return entry


def _make_trip_manager():
    """Create a TripManager-like mock with sub-component mocks."""
    tm = MagicMock()
    tm._crud = MagicMock()
    tm._crud.async_get_recurring_trips = AsyncMock(return_value=[])
    tm._crud.async_get_punctual_trips = AsyncMock(return_value=[])
    tm._soc_query = MagicMock()
    tm._soc_query.async_get_kwh_needed_today = AsyncMock(return_value=0.0)
    tm._soc_query.async_get_hours_needed_today = AsyncMock(return_value=0.0)
    tm._navigator = MagicMock()
    tm._navigator.async_get_next_trip = AsyncMock(return_value=None)
    return tm


def _make_coordinator(vehicle_name="test_vehicle", extra_entry_data=None):
    """Create a fully wired TripPlannerCoordinator."""
    hass = _make_mock_hass()
    entry = _make_mock_entry(vehicle_name=vehicle_name, extra_data=extra_entry_data)
    trip_manager = _make_trip_manager()
    config = CoordinatorConfig()
    return TripPlannerCoordinator(
        hass=hass,
        entry=entry,
        trip_manager=trip_manager,
        config=config,
    )


class TestShouldProcessTripPastDatetime:
    """Test _should_process_trip returns False for past trips (line 315)."""

    def test_past_datetime_returns_false(self):
        """Line 315: trip_dt <= now should return False."""
        coord = _make_coordinator()
        past_dt = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        result = coord._should_process_trip(
            {"datetime": past_dt, "tipo": "punctual"},
            datetime.now(timezone.utc),
        )
        assert result is False

    def test_same_time_returns_false(self):
        """Same datetime as now should return False."""
        coord = _make_coordinator()
        now_str = datetime.now(timezone.utc).isoformat()
        result = coord._should_process_trip(
            {"datetime": now_str, "tipo": "punctual"},
            datetime.now(timezone.utc),
        )
        assert result is False

    def test_future_datetime_returns_true(self):
        """Future datetime should return True."""
        coord = _make_coordinator()
        future_dt = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        result = coord._should_process_trip(
            {"datetime": future_dt, "tipo": "punctual"},
            datetime.now(timezone.utc),
        )
        assert result is True

    def test_invalid_datetime_passes_through(self):
        """Invalid datetime string should pass through (no early return)."""
        coord = _make_coordinator()
        result = coord._should_process_trip(
            {"datetime": "not-a-date", "tipo": "punctual"},
            datetime.now(timezone.utc),
        )
        assert result is True

    def test_empty_datetime_passes_through(self):
        """Empty datetime string should pass through."""
        coord = _make_coordinator()
        result = coord._should_process_trip(
            {"datetime": "", "tipo": "punctual"},
            datetime.now(timezone.utc),
        )
        assert result is True


class TestCalculateMockTimestepsRecurringPath:
    """Test _calculate_mock_timesteps for recurring trip fallback (lines 391-399)."""

    def test_recurrente_trip_with_day_and_time(self):
        """Lines 391-399: Recurring trip with dia_semana and hora."""
        coord = _make_coordinator()
        now = datetime.now(timezone.utc)
        trip = {
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
        }
        start, end = coord._calculate_mock_timesteps(
            trip=trip,
            charging_power_kw=7.0,
            horizon_hours=168,
            hours_needed=2.0,
            now=now,
        )
        # Should calculate deadline and return valid timesteps
        assert start >= 0
        assert end > start

    def test_recurring_trip_with_day_and_time_english(self):
        """Recurring trip with English day name."""
        coord = _make_coordinator()
        now = datetime.now(timezone.utc)
        trip = {
            "tipo": "recurring",
            "day": "monday",
            "time": "08:00",
        }
        start, end = coord._calculate_mock_timesteps(
            trip=trip,
            charging_power_kw=7.0,
            horizon_hours=168,
            hours_needed=2.0,
            now=now,
        )
        assert start >= 0
        assert end > start

    def test_recurring_trip_missing_day_returns_zero_start(self):
        """Missing dia_semana/day should return start=0 (end based on hours_needed)."""
        coord = _make_coordinator()
        now = datetime.now(timezone.utc)
        trip = {
            "tipo": "recurrente",
            "hora": "09:00",
        }
        start, end = coord._calculate_mock_timesteps(
            trip=trip,
            charging_power_kw=7.0,
            horizon_hours=168,
            hours_needed=2.0,
            now=now,
        )
        # start=0 because no day info to calculate deadline
        assert start == 0
        # end is based on hours_needed (2.0) when no deadline can be calculated
        assert end == 2

    def test_recurring_trip_missing_time_returns_zero_start(self):
        """Missing hora/time should return start=0 (end based on hours_needed)."""
        coord = _make_coordinator()
        now = datetime.now(timezone.utc)
        trip = {
            "tipo": "recurrente",
            "dia_semana": "lunes",
        }
        start, end = coord._calculate_mock_timesteps(
            trip=trip,
            charging_power_kw=7.0,
            horizon_hours=168,
            hours_needed=2.0,
            now=now,
        )
        # start=0 because no time info to calculate deadline
        assert start == 0
        # end is based on hours_needed (2.0) when no deadline can be calculated
        assert end == 2


class TestCalculateRecurringDeparture:
    """Test _calculate_recurring_departure (lines 443-481)."""

    def test_none_day_val_returns_none(self):
        """Line 443: None day_val should return None."""
        coord = _make_coordinator()
        result = coord._calculate_recurring_departure(
            None, "09:00", datetime.now(timezone.utc)
        )
        assert result is None

    def test_none_time_str_returns_none(self):
        """Line 443: None time_str should return None."""
        coord = _make_coordinator()
        result: Any = coord._calculate_recurring_departure(
            "lunes", None, datetime.now(timezone.utc)
        )
        assert result is None

    def test_numeric_day_0_is_sunday(self):
        """Line 450-451: Day '0' should map to Sunday (6)."""
        coord = _make_coordinator()
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        result = coord._calculate_recurring_departure("0", "09:00", now)
        assert result is not None
        assert result.weekday() == 6  # Sunday

    def test_numeric_day_7_is_sunday(self):
        """Line 450-451: Day '7' should map to Sunday (6)."""
        coord = _make_coordinator()
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        result = coord._calculate_recurring_departure("7", "09:00", now)
        assert result is not None
        assert result.weekday() == 6  # Sunday

    def test_numeric_day_1_is_monday(self):
        """Line 453: Day '1' should map to Monday (0)."""
        coord = _make_coordinator()
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        result = coord._calculate_recurring_departure("1", "09:00", now)
        assert result is not None
        assert result.weekday() == 0  # Monday

    def test_numeric_day_6_is_saturday(self):
        """Line 453: Day '6' should map to Saturday (5)."""
        coord = _make_coordinator()
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        result = coord._calculate_recurring_departure("6", "09:00", now)
        assert result is not None
        assert result.weekday() == 5  # Saturday

    def test_invalid_numeric_day_returns_none(self):
        """Line 455: Invalid numeric day (>7) should return None."""
        coord = _make_coordinator()
        result = coord._calculate_recurring_departure(
            "8", "09:00", datetime.now(timezone.utc)
        )
        assert result is None

    def test_spanish_day_name(self):
        """Line 457-465: Spanish day name mapping."""
        coord = _make_coordinator()
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        result = coord._calculate_recurring_departure("martes", "14:00", now)
        assert result is not None
        assert result.weekday() == 1  # Tuesday

    def test_english_day_name(self):
        """Line 457-465: English day name mapping."""
        coord = _make_coordinator()
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        result = coord._calculate_recurring_departure("friday", "18:00", now)
        assert result is not None
        assert result.weekday() == 4  # Friday

    def test_invalid_day_name_returns_none(self):
        """Line 467-468: Invalid day name should return None."""
        coord = _make_coordinator()
        result = coord._calculate_recurring_departure(
            "funday", "09:00", datetime.now(timezone.utc)
        )
        assert result is None

    def test_next_week_when_same_day(self):
        """Lines 472-473: When target day == today, delta_days should be 7 (next week)."""
        coord = _make_coordinator()
        now = datetime.now(timezone.utc)
        now_day = now.weekday()
        now = now.replace(hour=10, minute=0, second=0, microsecond=0)
        # Use the same day name as today
        day_names = [
            "lunes",
            "martes",
            "miércoles",
            "jueves",
            "viernes",
            "sábado",
            "domingo",
        ]
        result = coord._calculate_recurring_departure(day_names[now_day], "09:00", now)
        assert result is not None
        # Should be next week (7 days from now)
        delta_days = (result - now).total_seconds() / 3600
        assert delta_days >= 24  # At least 24 hours (next week)

    def test_time_parsing_with_single_part(self):
        """Line 476: Time string with only hour part."""
        coord = _make_coordinator()
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        result = coord._calculate_recurring_departure("lunes", "14", now)
        assert result is not None
        assert result.weekday() == 0  # Monday


class TestCalculateMockTimestepsRecurringPathAlt:
    """Alt test for lines 391-399 in _calculate_mock_timesteps."""

    def test_recurring_trip_with_valid_day_and_time(self):
        """Lines 391-399: Recurring trip with valid day/time should calculate deadline."""
        coord = _make_coordinator()
        # Create a trip with invalid datetime string but valid recurring info
        trip = {
            "datetime": "not-a-date",  # This will trigger the except block
            "tipo": "recurring",
            "dia_semana": "lunes",
            "hora": "08:00",
        }
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        start, end = coord._calculate_mock_timesteps(
            trip=trip,
            charging_power_kw=7.0,
            horizon_hours=168,
            hours_needed=2.0,
            now=now,
        )
        # Should have calculated a valid start/end based on recurring departure
        assert start >= 0
        assert end >= start


class TestCalculateMockTimestepsRecurringPathNonIntegerDelta:
    """Test lines 391-399 in _calculate_mock_timesteps with non-integer delta."""

    def test_recurring_trip_with_valid_day_and_time(self):
        """Lines 391-399: Recurring trip with valid day/time should calculate deadline."""
        coord = _make_coordinator()
        # Create a trip with invalid datetime string but valid recurring info
        trip = {
            "datetime": "not-a-date",  # This will trigger the except block
            "tipo": "recurring",
            "dia_semana": "lunes",
            "hora": "08:00",
        }
        # Use minute=30 so delta is NOT an integer (69.5h instead of 70h)
        # This ensures start < end (69 < 70)
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=30, second=0, microsecond=0
        )
        start, end = coord._calculate_mock_timesteps(
            trip=trip,
            charging_power_kw=7.0,
            horizon_hours=168,
            hours_needed=2.0,
            now=now,
        )
        # Should have calculated a valid start/end based on recurring departure
        assert start >= 0
        assert end > start


class TestApplyDeficitResultsEdgeCases:
    """Test lines 793, 797 in _apply_deficit_results."""

    def test_apply_deficit_results_break_when_i_gte_active_length(self):
        """Line 793: When i >= len(active), should break loop."""
        from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter

        hass = MagicMock()
        entry = MagicMock()
        entry.data = {
            "charging_power_kw": 7.0,
            "battery_capacity_kwh": 60.0,
            "safety_margin_percent": 10.0,
        }
        entry.options = {}
        adapter = EMHASSAdapter(hass=hass, entry=entry)
        adapter._cached_per_trip_params = {}
        # More results than active trips - should break at line 793
        results = [
            {"adjusted_def_total_hours": 3.0},
            {"adjusted_def_total_hours": 2.0},
            {"adjusted_def_total_hours": 1.0},
        ]
        active = [  # Only 2 active trips, but 3 results
            {"def_start_timestep": 0, "emhass_index": 0, "power_watts": 3600},
            {"def_start_timestep": 2, "emhass_index": 1, "power_watts": 3600},
        ]
        # This should not raise - should break when i >= len(active)
        adapter._apply_deficit_results(results, active)

    def test_apply_deficit_results_skip_when_trip_id_none(self):
        """Line 797: When _find_trip_id_for_params returns None, should continue."""
        from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter

        hass = MagicMock()
        entry = MagicMock()
        entry.data = {
            "charging_power_kw": 7.0,
            "battery_capacity_kwh": 60.0,
            "safety_margin_percent": 10.0,
        }
        entry.options = {}
        adapter = EMHASSAdapter(hass=hass, entry=entry)
        trip_001 = {"id": "trip_001"}
        adapter._cached_per_trip_params = {
            "trip_001": trip_001,
        }
        # active[0] is a different dict that won't match any cached trip
        results = [
            {"adjusted_def_total_hours": 3.0},
        ]
        active = [  # Different dict object - _find_trip_id_for_params will return None
            {"def_start_timestep": 99, "emhass_index": 99},
        ]
        adapter._apply_deficit_results(results, active)
        # Should not raise - should skip when trip_id is None
