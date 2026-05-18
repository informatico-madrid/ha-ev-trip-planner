"""Comprehensive tests for utils.py uncovered functions.

Covers validate_hora, get_trip_time, get_day_index, sanitize_recurring_trips,
is_trip_today, normalize_vehicle_id, calcular_energia_kwh.
"""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.ev_trip_planner.utils import (
    calcular_energia_kwh,
    get_day_index,
    get_trip_time,
    is_trip_today,
    normalize_vehicle_id,
    sanitize_recurring_trips,
    validate_hora,
)


class TestValidateHora:
    """Test validate_hora time validation."""

    def test_valid_hora(self):
        """Valid time does not raise."""
        validate_hora("12:30")

    def test_valid_hora_range(self):
        """Valid edge times do not raise."""
        validate_hora("00:00")
        validate_hora("23:59")

    def test_invalid_format_no_colon(self):
        """Missing colon raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_hora("1230")

    def test_invalid_format_wrong_length(self):
        """Wrong length raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_hora("1:30")

    def test_invalid_format_non_digit_hour(self):
        """Non-digit hour raises ValueError (line 161)."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_hora("ab:30")

    def test_invalid_format_non_digit_minute(self):
        """Non-digit minute raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_hora("12:ab")

    def test_invalid_hour_too_large(self):
        """Hour > 23 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid hour"):
            validate_hora("25:00")

    def test_invalid_minute_too_large(self):
        """Minute > 59 raises ValueError (line 170)."""
        with pytest.raises(ValueError, match="Invalid minute"):
            validate_hora("12:60")

    def test_not_string(self):
        """Non-string input raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_hora(1234)  # type: ignore[arg-type]


class TestGetTripTime:
    """Test get_trip_time."""

    def test_get_trip_time_valid(self):
        """Valid hora returns datetime."""
        result = get_trip_time({"hora": "14:30"})
        assert result is not None
        assert result.hour == 14
        assert result.minute == 30

    def test_get_trip_time_missing_hora(self):
        """Missing hora returns None (line 182-183)."""
        result = get_trip_time({})
        assert result is None

    def test_get_trip_time_empty_hora(self):
        """Empty hora returns None."""
        result = get_trip_time({"hora": ""})
        assert result is None

    def test_get_trip_time_invalid_format(self):
        """Invalid hora format returns None (line 187-188)."""
        result = get_trip_time({"hora": "not-a-time"})
        assert result is None


class TestGetDayIndex:
    """Test get_day_index."""

    def test_spanish_days(self):
        """All Spanish day names return correct index."""
        assert get_day_index("lunes") == 0
        assert get_day_index("martes") == 1
        assert get_day_index("miercoles") == 2
        assert get_day_index("jueves") == 3
        assert get_day_index("viernes") == 4
        assert get_day_index("sabado") == 5
        assert get_day_index("domingo") == 6

    def test_english_days(self):
        """All English day names return correct index."""
        assert get_day_index("monday") == 0
        assert get_day_index("tuesday") == 1
        assert get_day_index("wednesday") == 2
        assert get_day_index("thursday") == 3
        assert get_day_index("friday") == 4
        assert get_day_index("saturday") == 5
        assert get_day_index("sunday") == 6

    def test_case_insensitive(self):
        """Day names are case insensitive."""
        assert get_day_index("LUNES") == 0
        assert get_day_index("Monday") == 0

    def test_empty_raises(self):
        """Empty day name raises ValueError (line 203-204)."""
        with pytest.raises(ValueError, match="Day name cannot be empty"):
            get_day_index("")

    def test_unknown_raises(self):
        """Unknown day name raises ValueError (line 220)."""
        with pytest.raises(ValueError, match="Unknown day name"):
            get_day_index("flyday")


class TestSanitizeRecurringTrips:
    """Test sanitize_recurring_trips."""

    def test_all_valid(self):
        """All valid trips kept."""
        trips = {
            "rec_1": {"hora": "09:00"},
            "rec_2": {"hora": "14:30"},
        }
        result = sanitize_recurring_trips(trips)
        assert result == trips

    def test_invalid_filtered(self):
        """Invalid hora trips filtered out (lines 238-239)."""
        trips = {
            "rec_1": {"hora": "09:00"},
            "rec_2": {"hora": "25:00"},
        }
        result = sanitize_recurring_trips(trips)
        assert "rec_1" in result
        assert "rec_2" not in result

    def test_empty_dict(self):
        """Empty dict returns empty dict."""
        assert sanitize_recurring_trips({}) == {}


class TestIsTripToday:
    """Test is_trip_today."""

    def test_recurrent_monday_today(self):
        """Recurring trip on Monday when today is Monday returns True."""
        today = date(2025, 5, 12)  # Monday
        trip = {"tipo": "recurrente", "dia_semana": "lunes"}
        assert is_trip_today(trip, today) is True

    def test_recurrent_monday_spanish_name(self):
        """Recurring trip with Spanish day when today is Tuesday returns False."""
        today = date(2025, 5, 13)  # Tuesday
        trip = {"tipo": "recurrente", "dia_semana": "lunes"}
        assert is_trip_today(trip, today) is False

    def test_recurrent_english_day(self):
        """Recurring trip with English day name."""
        today = date(2025, 5, 12)  # Monday
        trip = {"tipo": "recurrente", "dia_semana": "monday"}
        assert is_trip_today(trip, today) is True

    def test_recurrent_legacy_dia_key(self):
        """Recurring trip with legacy 'dia' key."""
        today = date(2025, 5, 12)  # Monday
        trip = {"tipo": "recurrente", "dia": "lunes"}
        assert is_trip_today(trip, today) is True

    def test_punctual_today_date_obj(self):
        """Punctual trip with date object matching today returns True."""
        today = date(2025, 5, 12)
        trip = {"tipo": "puntual", "datetime": today}
        assert is_trip_today(trip, today) is True

    def test_punctual_today_iso_string(self):
        """Punctual trip with ISO datetime string matching today returns True."""
        today = date(2025, 5, 12)
        trip = {"tipo": "puntual", "datetime": "2025-05-12T10:00:00"}
        assert is_trip_today(trip, today) is True

    def test_punctual_today_yyyymmdd_string(self):
        """Punctual trip with YYYYMMDD string matching today returns True."""
        today = date(2025, 5, 12)
        trip = {"tipo": "puntual", "datetime": "20250512"}
        assert is_trip_today(trip, today) is True

    def test_punctual_today_legacy_fecha_key(self):
        """Punctual trip with legacy 'fecha' key."""
        today = date(2025, 5, 12)
        trip = {"tipo": "puntual", "fecha": "20250512"}
        assert is_trip_today(trip, today) is True

    def test_punctual_not_today(self):
        """Punctual trip on different date returns False."""
        today = date(2025, 5, 12)
        trip = {"tipo": "puntual", "datetime": "20250513"}
        assert is_trip_today(trip, today) is False

    def test_unknown_trip_day_returns_false(self):
        """Recurring trip with unknown day returns False (line 285)."""
        today = date(2025, 5, 12)
        trip = {"tipo": "recurrente", "dia_semana": "flyday"}
        assert is_trip_today(trip, today) is False

    def test_no_datetime_no_dia(self):
        """Punctual trip without datetime returns False."""
        today = date(2025, 5, 12)
        trip = {"tipo": "puntual"}
        assert is_trip_today(trip, today) is False


class TestNormalizeVehicleId:
    """Test normalize_vehicle_id."""

    def test_simple_name(self):
        """Simple name normalized."""
        assert normalize_vehicle_id("TestVehicle") == "testvehicle"

    def test_spaced_name(self):
        """Spaced name normalized with underscores."""
        assert normalize_vehicle_id("Test Vehicle") == "test_vehicle"

    def test_none_returns_empty(self):
        """None returns empty string (line 330)."""
        assert normalize_vehicle_id(None) == ""

    def test_empty_returns_empty(self):
        """Empty string returns empty string."""
        assert normalize_vehicle_id("") == ""

    def test_multiple_spaces(self):
        """Multiple spaces replaced with underscores."""
        assert normalize_vehicle_id("My Tesla Model 3") == "my_tesla_model_3"

    def test_case_normalized(self):
        """Uppercase converted to lowercase."""
        assert normalize_vehicle_id("MY VEHICLE") == "my_vehicle"


class TestCalcularEnergiaKwh:
    """Test calcular_energia_kwh."""

    def test_basic_calculation(self):
        """Basic kWh calculation."""
        result = calcular_energia_kwh(100, 0.2)
        assert result == 20.0

    def test_rounding(self):
        """Result rounded to 3 decimal places."""
        result = calcular_energia_kwh(100, 0.123456)
        assert result == 12.346

    def test_zero_distance(self):
        """Zero distance returns 0."""
        assert calcular_energia_kwh(0, 0.2) == 0.0

    def test_zero_consumption(self):
        """Zero consumption returns 0."""
        assert calcular_energia_kwh(100, 0) == 0.0

    def test_negative_distance_raises(self):
        """Negative distance raises ValueError (line 351)."""
        with pytest.raises(ValueError, match="Distance cannot be negative"):
            calcular_energia_kwh(-10, 0.2)

    def test_negative_consumption_raises(self):
        """Negative consumption raises ValueError (line 353)."""
        with pytest.raises(ValueError, match="Consumption cannot be negative"):
            calcular_energia_kwh(100, -0.2)
