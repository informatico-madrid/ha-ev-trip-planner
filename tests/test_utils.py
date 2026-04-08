"""Tests for utils module - trip ID generation and validation."""

import pytest
from datetime import date

from custom_components.ev_trip_planner.utils import (
    generate_trip_id,
    generate_random_suffix,
    is_valid_trip_id,
    calcular_energia_kwh,
    validate_hora,
    sanitize_recurring_trips,
    get_trip_time,
    get_day_index,
    is_trip_today,
)


class TestValidateHora:
    """Tests for validate_hora function."""

    def test_valid_hhmm_format_passes(self):
        """Test valid HH:MM format passes without error."""
        validate_hora("09:30")

    def test_valid_boundary_0000(self):
        """Test boundary value 00:00 is valid."""
        validate_hora("00:00")

    def test_valid_boundary_2359(self):
        """Test boundary value 23:59 is valid."""
        validate_hora("23:59")

    def test_valid_midday(self):
        """Test valid midday time."""
        validate_hora("12:00")

    def test_valid_midnight(self):
        """Test valid midnight time."""
        validate_hora("00:00")

    def test_invalid_hour_25(self):
        """Test invalid hour 25:00 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid hour"):
            validate_hora("25:00")

    def test_invalid_hour_24(self):
        """Test invalid hour 24:00 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid hour"):
            validate_hora("24:00")

    def test_invalid_minute_60(self):
        """Test invalid minute 12:60 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid minute"):
            validate_hora("12:60")

    def test_invalid_minute_61(self):
        """Test invalid minute 12:61 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid minute"):
            validate_hora("12:61")

    def test_invalid_format_abc(self):
        """Test invalid alphabetic string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_hora("abc")

    def test_invalid_format_empty(self):
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_hora("")

    def test_invalid_format_incomplete(self):
        """Test incomplete time raises ValueError."""
        with pytest.raises(ValueError):
            validate_hora("9:30")

    def test_invalid_format_no_colon(self):
        """Test time without colon raises ValueError."""
        with pytest.raises(ValueError):
            validate_hora("0930")


class TestGenerateTripId:
    """Tests for generate_trip_id function."""

    def test_generate_recurrente_with_spanish_day(self):
        """Test recurrent trip ID with Spanish day name."""
        trip_id = generate_trip_id("recurrente", "lunes")
        assert trip_id.startswith("rec_lun_")
        assert len(trip_id) > 8  # rec_lun_ + 6 char suffix

    def test_generate_recurrente_with_english_day(self):
        """Test recurrent trip ID with English day name."""
        trip_id = generate_trip_id("recurrente", "monday")
        assert trip_id.startswith("rec_lun_")

    def test_generate_recurrente_with_unknown_day(self):
        """Test recurrent trip ID with unknown day - uses fallback."""
        trip_id = generate_trip_id("recurrente", "randomday")
        assert trip_id.startswith("rec_ran_")  # First 3 chars

    def test_generate_recurrente_with_none_day(self):
        """Test recurrent trip ID with None day - uses default."""
        trip_id = generate_trip_id("recurrente", None)
        assert trip_id.startswith("rec_lun_")  # Default to "lunes"

    def test_generate_recurrente_with_all_spanish_days(self):
        """Test recurrent trip ID with all Spanish day names."""
        days = ["martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
        expected = ["mar", "mie", "jue", "vie", "sab", "dom"]
        for day, exp in zip(days, expected):
            trip_id = generate_trip_id("recurrente", day)
            assert trip_id.startswith(f"rec_{exp}_")

    def test_generate_punctual_with_string_date(self):
        """Test punctual trip ID with YYYYMMDD string."""
        trip_id = generate_trip_id("punctual", "20251119")
        assert trip_id.startswith("pun_20251119_")

    def test_generate_punctual_with_date_object(self):
        """Test punctual trip ID with date object."""
        trip_id = generate_trip_id("punctual", date(2025, 11, 19))
        assert trip_id.startswith("pun_20251119_")

    def test_generate_punctual_with_iso_date_string(self):
        """Test punctual trip ID with ISO format date string."""
        trip_id = generate_trip_id("punctual", "2025-11-19")
        assert trip_id.startswith("pun_20251119_")

    def test_generate_punctual_with_slash_date_string(self):
        """Test punctual trip ID with slash format date string."""
        trip_id = generate_trip_id("punctual", "2025/11/19")
        assert trip_id.startswith("pun_20251119_")

    def test_generate_punctual_with_none_date(self):
        """Test punctual trip ID with None date - uses today."""
        trip_id = generate_trip_id("punctual", None)
        assert trip_id.startswith("pun_")

    def test_generate_unknown_type_fallback(self):
        """Test unknown trip type returns fallback format."""
        trip_id = generate_trip_id("unknown_type", None)
        assert trip_id.startswith("trip_")


class TestGenerateRandomSuffix:
    """Tests for generate_random_suffix function."""

    def test_default_length(self):
        """Test default suffix length is 6."""
        suffix = generate_random_suffix()
        assert len(suffix) == 6

    def test_custom_length(self):
        """Test custom suffix length."""
        suffix = generate_random_suffix(10)
        assert len(suffix) == 10

    def test_alphanumeric(self):
        """Test suffix is alphanumeric lowercase."""
        suffix = generate_random_suffix()
        assert suffix.isalnum()
        assert suffix.islower()


class TestIsValidTripId:
    """Tests for is_valid_trip_id function."""

    def test_valid_rec_trip_id(self):
        """Test valid recurrent trip ID."""
        assert is_valid_trip_id("rec_lun_abc123") is True

    def test_valid_pun_trip_id(self):
        """Test valid punctual trip ID."""
        assert is_valid_trip_id("pun_20251119_abc123") is True

    def test_invalid_empty(self):
        """Test empty string is invalid."""
        assert is_valid_trip_id("") is False

    def test_invalid_none(self):
        """Test None is invalid."""
        assert is_valid_trip_id(None) is False

    def test_invalid_rec_short_suffix(self):
        """Test recurrent ID with short suffix is invalid."""
        assert is_valid_trip_id("rec_lun_ab") is False

    def test_invalid_pun_short_suffix(self):
        """Test punctual ID with short suffix is invalid."""
        assert is_valid_trip_id("pun_20251119_ab") is False

    def test_invalid_pun_wrong_date_length(self):
        """Test punctual ID with wrong date length is invalid."""
        assert is_valid_trip_id("pun_2025111_abc123") is False

    def test_invalid_wrong_format(self):
        """Test wrong format is invalid."""
        assert is_valid_trip_id("invalid_format") is False

    def test_invalid_too_many_parts(self):
        """Test too many parts is invalid."""
        assert is_valid_trip_id("rec_lun_abc_123") is False


class TestCalcularEnergiaKwh:
    """Tests for calcular_energia_kwh function."""

    def test_calcular_energia_kwh_basic(self):
        """Test basic energy calculation."""
        energy = calcular_energia_kwh(100, 0.15)
        assert energy == 15.0

    def test_calcular_energia_kwh_precision(self):
        """Test energy calculation with precision."""
        energy = calcular_energia_kwh(100, 0.175)
        assert energy == 17.5

    def test_calcular_energia_kwh_zero_distance(self):
        """Test zero distance returns zero energy."""
        energy = calcular_energia_kwh(0, 0.15)
        assert energy == 0.0

    def test_calcular_energia_kwh_zero_consumption(self):
        """Test zero consumption returns zero energy."""
        energy = calcular_energia_kwh(100, 0)
        assert energy == 0.0

    def test_calcular_energia_kwh_negative_distance_raises(self):
        """Test negative distance raises ValueError."""
        with pytest.raises(ValueError, match="Distance cannot be negative"):
            calcular_energia_kwh(-10, 0.15)

    def test_calcular_energia_kwh_negative_consumption_raises(self):
        """Test negative consumption raises ValueError."""
        with pytest.raises(ValueError, match="Consumption cannot be negative"):
            calcular_energia_kwh(100, -0.15)

    def test_calcular_energia_kwh_with_trip_km(self):
        """Test with realistic trip values."""
        # 50km trip at 0.18 kWh/km
        energy = calcular_energia_kwh(50, 0.18)
        assert energy == 9.0


class TestSanitizeRecurringTrips:
    """Tests for sanitize_recurring_trips function."""

    def test_filters_trips_with_invalid_hora(self):
        """Test that trips with invalid hora entries are filtered out."""
        trips = {
            "rec_lun_abc123": {"hora": "09:30", "dia": "lunes"},
            "rec_mar_xyz789": {"hora": "25:00", "dia": "martes"},
        }
        result = sanitize_recurring_trips(trips)
        assert "rec_lun_abc123" in result
        assert "rec_mar_xyz789" not in result

    def test_keeps_trips_with_valid_hora(self):
        """Test that trips with valid hora are kept."""
        trips = {
            "rec_lun_abc123": {"hora": "09:30", "dia": "lunes"},
            "rec_mar_xyz789": {"hora": "14:45", "dia": "martes"},
        }
        result = sanitize_recurring_trips(trips)
        assert len(result) == 2
        assert "rec_lun_abc123" in result
        assert "rec_mar_xyz789" in result

    def test_filters_invalid_minute_format(self):
        """Test that trips with invalid minute values are filtered out."""
        trips = {
            "rec_lun_abc123": {"hora": "09:30", "dia": "lunes"},
            "rec_mar_xyz789": {"hora": "09:60", "dia": "martes"},
        }
        result = sanitize_recurring_trips(trips)
        assert "rec_lun_abc123" in result
        assert "rec_mar_xyz789" not in result

    def test_filters_invalid_format(self):
        """Test that trips with invalid time format are filtered out."""
        trips = {
            "rec_lun_abc123": {"hora": "09:30", "dia": "lunes"},
            "rec_mar_xyz789": {"hora": "invalid", "dia": "martes"},
        }
        result = sanitize_recurring_trips(trips)
        assert "rec_lun_abc123" in result
        assert "rec_mar_xyz789" not in result

    def test_returns_empty_dict_for_all_invalid(self):
        """Test that empty dict is returned when all trips have invalid hora."""
        trips = {
            "rec_lun_abc123": {"hora": "25:00", "dia": "lunes"},
            "rec_mar_xyz789": {"hora": "invalid", "dia": "martes"},
        }
        result = sanitize_recurring_trips(trips)
        assert result == {}

    def test_returns_empty_dict_for_empty_input(self):
        """Test that empty dict is returned for empty input."""
        result = sanitize_recurring_trips({})
        assert result == {}

    def test_preserves_trip_data_for_valid_entries(self):
        """Test that valid trip data is preserved in output."""
        trips = {
            "rec_lun_abc123": {
                "hora": "09:30",
                "dia": "lunes",
                "destino": "work",
                "consumo": 0.18,
            },
        }
        result = sanitize_recurring_trips(trips)
        assert result["rec_lun_abc123"]["destino"] == "work"
        assert result["rec_lun_abc123"]["consumo"] == 0.18


class TestGetTripTime:
    """Tests for get_trip_time function."""

    def test_extracts_datetime_from_trip_with_hora(self):
        """Test extracting datetime from trip dict with hora field."""
        trip = {"hora": "09:30", "dia": "lunes"}
        result = get_trip_time(trip)
        assert result is not None
        assert result.hour == 9
        assert result.minute == 30

    def test_returns_none_when_hora_missing(self):
        """Test that None is returned when hora key is missing."""
        trip = {"dia": "lunes", "destino": "work"}
        result = get_trip_time(trip)
        assert result is None

    def test_returns_none_for_empty_trip(self):
        """Test that None is returned for empty trip dict."""
        result = get_trip_time({})
        assert result is None

    def test_extracts_time_from_trip_with_additional_fields(self):
        """Test extracting time from trip with multiple fields."""
        trip = {
            "hora": "14:45",
            "dia": "martes",
            "destino": "airport",
            "consumo": 0.15,
        }
        result = get_trip_time(trip)
        assert result is not None
        assert result.hour == 14
        assert result.minute == 45

    def test_returns_none_when_hora_is_none(self):
        """Test that None is returned when hora is explicitly None."""
        trip = {"hora": None, "dia": "lunes"}
        result = get_trip_time(trip)
        assert result is None

    def test_returns_none_when_hora_is_empty_string(self):
        """Test that None is returned when hora is empty string."""
        trip = {"hora": "", "dia": "lunes"}
        result = get_trip_time(trip)
        assert result is None

    def test_boundary_0000(self):
        """Test extracting midnight (00:00)."""
        trip = {"hora": "00:00"}
        result = get_trip_time(trip)
        assert result is not None
        assert result.hour == 0
        assert result.minute == 0

    def test_boundary_2359(self):
        """Test extracting last minute of day (23:59)."""
        trip = {"hora": "23:59"}
        result = get_trip_time(trip)
        assert result is not None
        assert result.hour == 23
        assert result.minute == 59


class TestGetDayIndex:
    """Tests for get_day_index function."""

    def test_lunes_returns_0(self):
        """Test that 'lunes' (Monday) returns 0."""
        assert get_day_index("lunes") == 0

    def test_monday_returns_0(self):
        """Test that 'monday' returns 0."""
        assert get_day_index("monday") == 0

    def test_lunes_uppercase(self):
        """Test that 'LUNES' returns 0 (case insensitive)."""
        assert get_day_index("LUNES") == 0

    def test_lunes_mixed_case(self):
        """Test that 'Lunes' returns 0 (case insensitive)."""
        assert get_day_index("Lunes") == 0

    def test_martes_returns_1(self):
        """Test that 'martes' (Tuesday) returns 1."""
        assert get_day_index("martes") == 1

    def test_tuesday_returns_1(self):
        """Test that 'tuesday' returns 1."""
        assert get_day_index("tuesday") == 1

    def test_miercoles_returns_2(self):
        """Test that 'miercoles' (Wednesday) returns 2."""
        assert get_day_index("miercoles") == 2

    def test_wednesday_returns_2(self):
        """Test that 'wednesday' returns 2."""
        assert get_day_index("wednesday") == 2

    def test_jueves_returns_3(self):
        """Test that 'jueves' (Thursday) returns 3."""
        assert get_day_index("jueves") == 3

    def test_thursday_returns_3(self):
        """Test that 'thursday' returns 3."""
        assert get_day_index("thursday") == 3

    def test_viernes_returns_4(self):
        """Test that 'viernes' (Friday) returns 4."""
        assert get_day_index("viernes") == 4

    def test_friday_returns_4(self):
        """Test that 'friday' returns 4."""
        assert get_day_index("friday") == 4

    def test_sabado_returns_5(self):
        """Test that 'sabado' (Saturday) returns 5."""
        assert get_day_index("sabado") == 5

    def test_saturday_returns_5(self):
        """Test that 'saturday' returns 5."""
        assert get_day_index("saturday") == 5

    def test_domingo_returns_6(self):
        """Test that 'domingo' (Sunday) returns 6."""
        assert get_day_index("domingo") == 6

    def test_sunday_returns_6(self):
        """Test that 'sunday' returns 6."""
        assert get_day_index("sunday") == 6

    def test_invalid_day_name_raises(self):
        """Test that invalid day name raises ValueError."""
        with pytest.raises(ValueError):
            get_day_index("invalidday")

    def test_empty_string_raises(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            get_day_index("")

    def test_numbers_raises(self):
        """Test that numeric string raises ValueError."""
        with pytest.raises(ValueError):
            get_day_index("123")


class TestIsTripToday:
    """Tests for is_trip_today function.

    Tests recurring trips (with day names) and punctual trips (with date).
    """

    # === Recurring trips (day-based) ===

    def test_recurring_trip_lunes_returns_true_when_today_is_monday(self):
        """Test recurring trip on 'lunes' returns True when today is Monday."""
        # Using a fixed Monday date (2026-04-06 was a Monday)
        monday = date(2026, 4, 6)
        trip = {"tipo": "recurrente", "dia": "lunes", "hora": "09:30"}
        assert is_trip_today(trip, monday) is True

    def test_recurring_trip_martes_returns_true_when_today_is_tuesday(self):
        """Test recurring trip on 'martes' returns True when today is Tuesday."""
        # 2026-04-07 was a Tuesday
        tuesday = date(2026, 4, 7)
        trip = {"tipo": "recurrente", "dia": "martes", "hora": "09:30"}
        assert is_trip_today(trip, tuesday) is True

    def test_recurring_trip_miercoles_returns_true_when_today_is_wednesday(self):
        """Test recurring trip on 'miercoles' returns True when today is Wednesday."""
        # 2026-04-08 was a Wednesday
        wednesday = date(2026, 4, 8)
        trip = {"tipo": "recurrente", "dia": "miercoles", "hora": "09:30"}
        assert is_trip_today(trip, wednesday) is True

    def test_recurring_trip_jueves_returns_true_when_today_is_thursday(self):
        """Test recurring trip on 'jueves' returns True when today is Thursday."""
        # 2026-04-09 was a Thursday
        thursday = date(2026, 4, 9)
        trip = {"tipo": "recurrente", "dia": "jueves", "hora": "09:30"}
        assert is_trip_today(trip, thursday) is True

    def test_recurring_trip_viernes_returns_true_when_today_is_friday(self):
        """Test recurring trip on 'viernes' returns True when today is Friday."""
        # 2026-04-10 was a Friday
        friday = date(2026, 4, 10)
        trip = {"tipo": "recurrente", "dia": "viernes", "hora": "09:30"}
        assert is_trip_today(trip, friday) is True

    def test_recurring_trip_sabado_returns_true_when_today_is_saturday(self):
        """Test recurring trip on 'sabado' returns True when today is Saturday."""
        # 2026-04-11 was a Saturday
        saturday = date(2026, 4, 11)
        trip = {"tipo": "recurrente", "dia": "sabado", "hora": "09:30"}
        assert is_trip_today(trip, saturday) is True

    def test_recurring_trip_domingo_returns_true_when_today_is_sunday(self):
        """Test recurring trip on 'domingo' returns True when today is Sunday."""
        # 2026-04-12 was a Sunday
        sunday = date(2026, 4, 12)
        trip = {"tipo": "recurrente", "dia": "domingo", "hora": "09:30"}
        assert is_trip_today(trip, sunday) is True

    def test_recurring_trip_monday_returns_true_when_today_is_monday(self):
        """Test recurring trip on 'monday' (English) returns True when today is Monday."""
        monday = date(2026, 4, 6)
        trip = {"tipo": "recurrente", "dia": "monday", "hora": "09:30"}
        assert is_trip_today(trip, monday) is True

    def test_recurring_trip_tuesday_returns_true_when_today_is_tuesday(self):
        """Test recurring trip on 'tuesday' (English) returns True when today is Tuesday."""
        tuesday = date(2026, 4, 7)
        trip = {"tipo": "recurrente", "dia": "tuesday", "hora": "09:30"}
        assert is_trip_today(trip, tuesday) is True

    def test_recurring_trip_wednesday_returns_true_when_today_is_wednesday(self):
        """Test recurring trip on 'wednesday' (English) returns True when today is Wednesday."""
        wednesday = date(2026, 4, 8)
        trip = {"tipo": "recurrente", "dia": "wednesday", "hora": "09:30"}
        assert is_trip_today(trip, wednesday) is True

    def test_recurring_trip_thursday_returns_true_when_today_is_thursday(self):
        """Test recurring trip on 'thursday' (English) returns True when today is Thursday."""
        thursday = date(2026, 4, 9)
        trip = {"tipo": "recurrente", "dia": "thursday", "hora": "09:30"}
        assert is_trip_today(trip, thursday) is True

    def test_recurring_trip_friday_returns_true_when_today_is_friday(self):
        """Test recurring trip on 'friday' (English) returns True when today is Friday."""
        friday = date(2026, 4, 10)
        trip = {"tipo": "recurrente", "dia": "friday", "hora": "09:30"}
        assert is_trip_today(trip, friday) is True

    def test_recurring_trip_saturday_returns_true_when_today_is_saturday(self):
        """Test recurring trip on 'saturday' (English) returns True when today is Saturday."""
        saturday = date(2026, 4, 11)
        trip = {"tipo": "recurrente", "dia": "saturday", "hora": "09:30"}
        assert is_trip_today(trip, saturday) is True

    def test_recurring_trip_sunday_returns_true_when_today_is_sunday(self):
        """Test recurring trip on 'sunday' (English) returns True when today is Sunday."""
        sunday = date(2026, 4, 12)
        trip = {"tipo": "recurrente", "dia": "sunday", "hora": "09:30"}
        assert is_trip_today(trip, sunday) is True

    def test_recurring_trip_lunes_returns_false_when_today_is_tuesday(self):
        """Test recurring trip on 'lunes' returns False when today is Tuesday."""
        tuesday = date(2026, 4, 7)
        trip = {"tipo": "recurrente", "dia": "lunes", "hora": "09:30"}
        assert is_trip_today(trip, tuesday) is False

    def test_recurring_trip_monday_returns_false_when_today_is_friday(self):
        """Test recurring trip on 'monday' returns False when today is Friday."""
        friday = date(2026, 4, 10)
        trip = {"tipo": "recurrente", "dia": "monday", "hora": "09:30"}
        assert is_trip_today(trip, friday) is False

    def test_recurring_trip_case_insensitive(self):
        """Test recurring trip day matching is case insensitive."""
        monday = date(2026, 4, 6)
        trip_lower = {"tipo": "recurrente", "dia": "lunes", "hora": "09:30"}
        trip_upper = {"tipo": "recurrente", "dia": "LUNES", "hora": "09:30"}
        trip_mixed = {"tipo": "recurrente", "dia": "Lunes", "hora": "09:30"}
        assert is_trip_today(trip_lower, monday) is True
        assert is_trip_today(trip_upper, monday) is True
        assert is_trip_today(trip_mixed, monday) is True

    # === Punctual trips (date-based) ===

    def test_punctual_trip_returns_true_when_date_matches(self):
        """Test punctual trip returns True when date matches today."""
        trip_date = date(2026, 4, 8)
        today = date(2026, 4, 8)
        trip = {"tipo": "punctual", "fecha": trip_date, "hora": "09:30"}
        assert is_trip_today(trip, today) is True

    def test_punctual_trip_returns_false_when_date_does_not_match(self):
        """Test punctual trip returns False when date does not match today."""
        trip_date = date(2026, 4, 8)
        today = date(2026, 4, 7)
        trip = {"tipo": "punctual", "fecha": trip_date, "hora": "09:30"}
        assert is_trip_today(trip, today) is False

    def test_punctual_trip_with_date_string(self):
        """Test punctual trip with date string in YYYYMMDD format."""
        today = date(2026, 4, 8)
        trip = {"tipo": "punctual", "fecha": "20260408", "hora": "09:30"}
        assert is_trip_today(trip, today) is True

    def test_punctual_trip_with_iso_date_string(self):
        """Test punctual trip with ISO date string (YYYY-MM-DD)."""
        today = date(2026, 4, 8)
        trip = {"tipo": "punctual", "fecha": "2026-04-08", "hora": "09:30"}
        assert is_trip_today(trip, today) is True

    def test_punctual_trip_with_slash_date_string(self):
        """Test punctual trip with slash date string (YYYY/MM/DD)."""
        today = date(2026, 4, 8)
        trip = {"tipo": "punctual", "fecha": "2026/04/08", "hora": "09:30"}
        assert is_trip_today(trip, today) is True

    # === Returns bool ===

    def test_returns_bool_true(self):
        """Test that True is returned (not truthy value)."""
        monday = date(2026, 4, 6)
        trip = {"tipo": "recurrente", "dia": "lunes", "hora": "09:30"}
        result = is_trip_today(trip, monday)
        assert result is True
        assert isinstance(result, bool)

    def test_returns_bool_false(self):
        """Test that False is returned (not falsy value)."""
        tuesday = date(2026, 4, 7)
        trip = {"tipo": "recurrente", "dia": "lunes", "hora": "09:30"}
        result = is_trip_today(trip, tuesday)
        assert result is False
        assert isinstance(result, bool)
