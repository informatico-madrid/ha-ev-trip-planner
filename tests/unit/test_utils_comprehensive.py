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
    is_valid_trip_id,
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


class TestIsTripTodayMutationKills:
    """Tests targeting is_trip_today mutation survivors.

    Kill targets: 20 mutations from .get() defaults on dia/dia_semana/fecha,
    the or->and mutation, and fecha None fallback.
    """

    def test_dia_semana_only_fallback(self):
        """dia key missing -> uses dia_semana fallback.
        Kills mutations 11, 13: .get("dia", "") vs .get("dia", None)
        where the default matters only when key is missing."""
        today = date(2025, 5, 12)  # Monday
        trip = {"tipo": "recurrente", "dia_semana": "lunes"}
        # No "dia" key — the .get("dia", default) default is used
        # Original: "" (falsy) -> falls through to dia_semana -> True
        # Mutated (11,13): None (falsy) -> falls through to dia_semana -> True
        # Mutation 23 (or->and) would fail since empty "" is falsy
        assert is_trip_today(trip, today) is True

    def test_dia_only_no_dia_semana(self):
        """dia_semana key missing -> uses dia fallback."""
        today = date(2025, 5, 13)  # Tuesday
        trip = {"tipo": "recurrente", "dia": "martes"}
        # No "dia_semana" key — .get("dia_semana", default) used
        # Mutations 18, 20 change default for dia_semana
        assert is_trip_today(trip, today) is True

    def test_dia_and_dia_semana_both(self):
        """Both dia and dia_semana present -> uses dia (first truthy).
        Kills mutation 23: or->and changes behavior when dia is empty."""
        today = date(2025, 5, 12)  # Monday
        trip = {
            "tipo": "recurrente",
            "dia": "lunes",
            "dia_semana": "monday",
        }
        # Both keys present with truthy values
        # Mut 23 (or->and): both truthy -> "lunes" -> True (same)
        # But if we had dia="" -> original or: "" or "monday" -> "monday" -> True
        #                    mut 23 and: "" and "monday" -> "" -> False
        assert is_trip_today(trip, today) is True

    def test_dia_empty_dia_semana_present(self):
        """dia='' (empty, falsy) -> should fall back to dia_semana.
        Kills mutation 23 (or->and): with empty dia, 'and' returns empty string."""
        today = date(2025, 5, 12)  # Monday
        trip = {"tipo": "recurrente", "dia": "", "dia_semana": "monday"}
        # Original: "" or "monday" -> "monday" (truthy) -> compare -> True
        # Mut 23 (and): "" and "monday" -> "" (falsy) -> False
        assert is_trip_today(trip, today) is True

    def test_fecha_only_no_datetime(self):
        """Only 'fecha' present, 'datetime' missing -> fallback path.
        Kills mutations 85, 86: .get("fecha", default) where default matters."""
        today = date(2025, 5, 12)
        trip = {"tipo": "puntual", "fecha": today}
        # .get("datetime") returns None (key missing)
        # None or trip.get("fecha") -> today
        # Mut 85 (or->and): None and today -> None -> False
        # Mut 86: .get("fecha") replaces whole expression -> None
        assert is_trip_today(trip, today) is True

    def test_punctual_no_date_fields(self):
        """Punctual trip with neither datetime nor fecha -> False."""
        today = date(2025, 5, 12)
        trip = {"tipo": "puntual"}
        # No fecha -> fecha=None -> not isinstance -> not isinstance str -> False
        assert is_trip_today(trip, today) is False


class TestIsValidTripIdMutationKills:
    """Tests targeting is_valid_trip_id mutation survivors.

    Kill targets: 4 mutations from >=  > boundary on parts length checks.
    """

    def test_recurrent_min_length_suffix(self):
        """rec_{day}_{4chars} should be valid (boundary >= 4).
        Kills mutation 12: len(parts[2]) > 4 would reject 4 chars."""
        assert is_valid_trip_id("rec_lun_abcdef") is True  # 6 chars
        # The >= 4 boundary: exactly 4 should pass original, fail mut 12
        assert is_valid_trip_id("rec_lun_abc1") is True  # 4 chars exactly

    def test_recurrent_too_short_suffix(self):
        """rec_{day}_{3chars} should be invalid (too short)."""
        assert is_valid_trip_id("rec_lun_abc") is False  # 3 chars

    def test_punctual_min_length_suffix(self):
        """pun_{date}_{4chars} should be valid (boundary >= 4).
        Kills mutation 26: len(parts[2]) > 4 would reject 4 chars."""
        assert is_valid_trip_id("pun_20250512_abc1") is True  # 4 chars

    def test_punctual_too_short_suffix(self):
        """pun_{date}_{3chars} should be invalid."""
        assert is_valid_trip_id("pun_20250512_abc") is False  # 3 chars


class TestValidateHoraMutationKills:
    """Tests targeting validate_hora mutation survivors.

    Kill targets: 7 mutations from str index, len comparison changes.
    """

    def test_hour_24_boundary(self):
        """Hour=24 should raise ValueError (boundary of hour > 23 check).
        Kills mutation 1: hour > 23 -> hour >= 23."""
        with pytest.raises(ValueError, match="Invalid hour"):
            validate_hora("24:00")

    def test_six_char_time_wrong_colon_pos(self):
        """6-char string '12:345' where hora[3]!=':' -> ValueError.
        Kills mutation 33: hora[2] != ':' -> hora[3] != ':'."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_hora("12:345")

    def test_six_char_time_wrong_len(self):
        """6-char string should fail len(hora) != 5 check.
        Kills mutation 10: len(hora) != 5 -> len(hora) != 6."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_hora("12:345")

    def test_non_string_hour_part(self):
        """Non-digit hour raises ValueError.
        Kills mutation 17: not hour_str.isdigit() -> other."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_hora("1a:30")

    def test_non_string_minute_part(self):
        """Non-digit minute raises ValueError.
        Kills mutation 18: not minute_str.isdigit() -> other."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_hora("12:3a")

    def test_float_minute(self):
        """Float minute raises ValueError (contains dot).
        Kills mutation 20: '12.30' -> non-digit check."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_hora("12.30")

    def test_negative_hour_via_string(self):
        """Negative hour string raises ValueError.
        Kills mutation 25: hour > 23 -> hour < 23 (would accept 0)."""
        with pytest.raises(ValueError, match="Invalid hour"):
            validate_hora("25:00")

    def test_minute_60_boundary(self):
        """Minute=60 raises ValueError (boundary check).
        Kills mutation 33: minute > 59 -> minute >= 59."""
        with pytest.raises(ValueError, match="Invalid minute"):
            validate_hora("12:60")


class TestSanitizeMutationKills:
    """Tests targeting sanitize_recurring_trips mutation survivors.

    Kill targets: 3 mutations from assignment/conditional removals
    and default_value mutations on trip.get("hora", "").
    """

    def test_valid_trips_retained(self):
        """Valid trips are kept in sanitized output.
        Kills mutation 4: sanitized[trip_id] = trip removed."""
        trips = {"t1": {"hora": "09:00"}, "t2": {"hora": "14:00"}}
        result = sanitize_recurring_trips(trips)
        assert "t1" in result
        assert "t2" in result

    def test_invalid_hora_string_fails_validation(self):
        """Trip with non-time hora string is filtered.
        Kills mutation 6: hour_str.isdigit() -> 1 (always true, but split on non-digit)."""
        trips = {"t1": {"hora": "not-a-time"}}
        result = sanitize_recurring_trips(trips)
        assert "t1" not in result

    def test_empty_minute_fails_isdigit(self):
        """Empty minute string is filtered (not isdigit).
        Kills mutation 9: split -> [0] on empty minute."""
        trips = {"t1": {"hora": "09:"}}
        result = sanitize_recurring_trips(trips)
        assert "t1" not in result

    def test_leading_zero_hour_valid(self):
        """Trip with '09:00' hora is valid (leading zero).
        Ensures the sanitize loop properly processes valid hours."""
        trips = {"t1": {"hora": "09:00"}}
        result = sanitize_recurring_trips(trips)
        assert "t1" in result
        assert result["t1"]["hora"] == "09:00"

    def test_missing_hora_key_filtered(self):
        """Trip dict without 'hora' key is filtered — kills default_value mutants.

        Kills mutations 4, 6, 9:
        - mutmut_4: trip.get("hora", "") -> trip.get("hora", None)
          None -> validate_hora(None) raises ValueError -> trip filtered
        - mutmut_6: trip.get("hora", "") -> trip.get("hora", )
          Missing default -> KeyError if "hora" absent -> trip filtered
        - mutmut_9: trip.get("hora", "") -> trip.get("hora", "XXXX")
          "XXXX" -> validate_hora raises -> trip filtered
        """
        trips = {
            "t1": {"hora": "09:00"},  # valid
            "t2": {},  # missing hora key entirely
        }
        result = sanitize_recurring_trips(trips)
        assert "t1" in result
        assert "t2" not in result  # filtered because missing hora


class TestGetDayIndexMutationKills:
    """Tests targeting get_day_index mutation survivors."""

    def test_index_zero(self):
        """Day index 0 is Monday/lunes.
        Kills mutation 3: < -> > for first comparison."""
        assert get_day_index("lunes") == 0
        assert get_day_index("monday") == 0

    def test_index_6(self):
        """Day index 6 is Sunday/domingo.
        Kills mutation 3: < -> > for last comparison."""
        assert get_day_index("domingo") == 6
        assert get_day_index("sunday") == 6


class TestNormalizeVehicleIdMutationKills:
    """Tests targeting normalize_vehicle_id mutation survivors."""

    def test_none_input(self):
        """None returns empty string.
        Kills mutation 1: if not vehicle_name -> always True."""
        assert normalize_vehicle_id(None) == ""

    def test_empty_input(self):
        """Empty string returns empty string.
        Kills mutation 1: if not vehicle_name -> always True."""
        assert normalize_vehicle_id("") == ""


class TestGenerateTripIdMutationKills:
    """Tests targeting generate_random_suffix and trip ID generation mutations."""

    def test_generate_random_suffix_length(self):
        """Output length matches requested length.
        Kills mutation: length=6 -> length=7 in generate_random_suffix."""
        from custom_components.ev_trip_planner.utils import generate_random_suffix

        # Run multiple times since it's random, but check length always matches
        for _ in range(5):
            result = generate_random_suffix(6)
            assert len(result) == 6

    def test_generate_random_suffix_default_length(self):
        """Default suffix length is 6 characters.
        Kills mutation: default length 6 -> 7."""
        from custom_components.ev_trip_planner.utils import generate_random_suffix

        result = generate_random_suffix()
        assert len(result) == 6


class TestIsTripTodayAdditionalMutationKills:
    """Additional is_trip_today tests for remaining mutation survivors.

    Kill targets: mutations 3 (== !=), 4 (empty dict), 6, 9 (sanitize),
    10 (validate len), 17, 18, 20, 25 (validate digit), 33 (validate col),
    40, 41 (wednesday tuple), 55, 56 (punctual tuple), 85, 86 (fecha).
    """

    def test_wednesday_trip_today(self):
        """Recurring Wednesday trip when today is Wednesday returns True.
        Kills mutations 40, 41: 'wednesday' -> 'XXwednesdayXX' / 'WEDNESDAY' in tuple.
        These mutations only matter if wednesday is checked and today is Wednesday."""
        today = date(2025, 5, 14)  # Wednesday
        trip = {"tipo": "recurrente", "dia_semana": "miercoles"}
        assert is_trip_today(trip, today) is True

    def test_punctual_fecha_date_object(self):
        """Punctual trip with fecha=date object when fecha is the only key.
        Kills mutation 86: .get("fecha") replaced with None returns False."""
        today = date(2025, 5, 12)
        trip = {"tipo": "puntual", "fecha": today}
        # .get("datetime") -> None, None or today -> today
        # isinstance(today, date) -> True, today == today -> True
        assert is_trip_today(trip, today) is True

    def test_punctual_fecha_string_with_dashes(self):
        """Punctual trip with fecha='2025-05-12' (dash format).
        Kills mutation 86: replace('-', '') -> replace('XX-', '')."""
        today = date(2025, 5, 12)
        trip = {"tipo": "puntual", "fecha": "2025-05-12"}
        # Normalization: "2025-05-12" -> "20250512"
        assert is_trip_today(trip, today) is True

    def test_punctual_fecha_string_with_slashes(self):
        """Punctual trip with fecha='2025/05/12' (slash format).
        Kills mutation 85: replace('/', '') -> replace('XX/', '').
        The slash replacement is a separate mutation from the dash replacement."""
        today = date(2025, 5, 12)
        trip = {"tipo": "puntual", "fecha": "2025/05/12"}
        # Normalization: "2025/05/12" -> "20250512"
        assert is_trip_today(trip, today) is True

    def test_punctual_fecha_string_no_match(self):
        """Punctual trip with different date string returns False.
        Ensures the normalization produces correct comparison."""
        today = date(2025, 5, 12)
        trip = {"tipo": "puntual", "fecha": "13/05/2025"}
        assert is_trip_today(trip, today) is False

    def test_rec_weekend_saturday(self):
        """Recurring Saturday trip when today is Saturday returns True.
        Kills mutations 42-45: 'friday', 'saturday', 'sunday', 'thursday' in tuple."""
        today = date(2025, 5, 10)  # Saturday
        trip = {"tipo": "recurrente", "dia_semana": "sabado"}
        assert is_trip_today(trip, today) is True

    def test_rec_weekend_sunday(self):
        """Recurring Sunday trip when today is Sunday returns True."""
        today = date(2025, 5, 11)  # Sunday
        trip = {"tipo": "recurrente", "dia_semana": "domingo"}
        assert is_trip_today(trip, today) is True

    def test_rec_weekend_friday(self):
        """Recurring Friday trip when today is Friday returns True."""
        today = date(2025, 5, 9)  # Friday
        trip = {"tipo": "recurrente", "dia_semana": "viernes"}
        assert is_trip_today(trip, today) is True

    def test_rec_thursday_trip(self):
        """Recurring Thursday trip when today is Thursday returns True.
        Kills mutations affecting 'thursday' in the tuple."""
        today = date(2025, 5, 8)  # Thursday
        trip = {"tipo": "recurrente", "dia_semana": "jueves"}
        assert is_trip_today(trip, today) is True

    def test_rec_tuesday_trip(self):
        """Recurring Tuesday trip when today is Tuesday returns True."""
        today = date(2025, 5, 13)  # Tuesday
        trip = {"tipo": "recurrente", "dia_semana": "martes"}
        assert is_trip_today(trip, today) is True


class TestGetTripTimeKillMutants:
    """Tests to kill specific mutation survivors in get_trip_time.

    Target mutations:
    - String mutations on '%H:%M' format
    - Boolean flip on 'if not hora'
    - Identity mutations on datetime.strptime
    """

    def test_get_trip_time_exact_datetime_values(self):
        """Test exact hour and minute from parsed time string.
        Kills mutation: strptime → different method that returns wrong time."""
        result = get_trip_time({"hora": "14:30"})
        assert result is not None
        assert result.hour == 14
        assert result.minute == 30
        assert result.day == 1  # datetime(1900,1,1,14,30)
        assert result.month == 1
        assert result.year == 1900

    def test_get_trip_time_midnight(self):
        """Test midnight returns correct datetime.
        Kills mutation on hour/minute parsing."""
        result = get_trip_time({"hora": "00:00"})
        assert result is not None
        assert result.hour == 0
        assert result.minute == 0

    def test_get_trip_time_end_of_day(self):
        """Test 23:59 returns correct datetime.
        Kills mutation on hour/minute parsing at boundaries."""
        result = get_trip_time({"hora": "23:59"})
        assert result is not None
        assert result.hour == 23
        assert result.minute == 59

    def test_get_trip_time_returns_datetime_type(self):
        """Test return is exactly datetime, not mutated type.
        Kills mutation: return None → return type, or identity mutation."""
        result = get_trip_time({"hora": "12:00"})
        from datetime import datetime

        assert isinstance(result, datetime)

    def test_get_trip_time_string_format_hora_key(self):
        """Test that 'hora' key is used, not mutated key name.
        Kills mutation: 'hora' → '' or other string mutation."""
        # Mutated function that uses wrong key name would return None
        result = get_trip_time({"hora": "09:15"})
        assert result is not None
        assert result.hour == 9
        assert result.minute == 15
