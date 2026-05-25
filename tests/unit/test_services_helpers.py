"""Unit tests for _helpers.py pure data extraction functions.

These tests target the remove_arg and string_mutate survivors in
_handler_factories.py by independently testing the helper functions
that encapsulate the .get("key", "default") patterns.

Mutations that are killable by these tests:
- get_str: data.get(key, default) -> data.get(key, ) — test without key
- get_str: default value changes — string_mutate on "unknown" -> "UNKNOWN"
- get_str_fallback: first key missing, uses fallback — test with empty primary
- get_str_fallback: both keys missing, uses default — test omitting both keys
- get_str_nested: cascaded remove_arg on nested .get() — test omitting all keys
- get_vehicle_id: data.get("vehicle_id", "unknown") -> data.get("vehicle_id", )
"""

from __future__ import annotations

from custom_components.ev_trip_planner.services._helpers import (
    get_bool,
    get_optional_str,
    get_or,
    get_str,
    get_str_fallback,
    get_str_nested,
    get_vehicle_id,
)


class TestGetStr:
    """Test get_str helper — covers .get("key", "default") patterns."""

    def test_present_key_returns_value(self):
        assert get_str({"name": "hello"}, "name") == "hello"

    def test_missing_key_returns_default(self):
        """Mutation: data.get("key", default) -> data.get("key", )
        would return None instead of "", which str(None) = "None".
        """
        assert get_str({}, "key") == ""

    def test_missing_key_returns_custom_default(self):
        """Mutation on default: string_mutate could change "unknown" to "UNKNOWN"."""
        assert get_str({}, "vehicle_id", "unknown") == "unknown"

    def test_missing_key_default_becomes_none_killed(self):
        """When the default argument is removed, str(None) = "None", not "".

        Mutation: get_str(data, key, default)
          -> get_str(data, key)  — removes default parameter
        The function would return str(data.get(key, None)) = str(None) = "None".
        This test kills that mutation by asserting "".
        """
        result = get_str({}, "key", "")
        assert result == ""
        assert result != "None"

    def test_none_value_returns_none_str(self):
        """When key exists but value is None, dict.get() returns None (not default).
        str(None) produces 'None' — this is expected dict.get() semantics.
        """
        assert get_str({"key": None}, "key") == "None"

    def test_empty_string_returns_empty_string(self):
        """Empty string is a valid value, not falsy-fallback."""
        assert get_str({"key": ""}, "key") == ""

    def test_non_string_coerced(self):
        assert get_str({"count": 42}, "count") == "42"

    def test_fallback_default_not_overwritten(self):
        """Ensure the default is only used when key is absent."""
        assert get_str({"key": "actual"}, "key", "fallback") == "actual"


class TestGetStrFallback:
    """Test get_str_fallback — covers data.get(a) or data.get(b, default) patterns."""

    def test_primary_key_present_returns_it(self):
        result = get_str_fallback({"descripcion": "ruta"}, "descripcion", "description")
        assert result == "ruta"

    def test_primary_empty_uses_fallback(self):
        """Primary key exists but is empty string — falls back."""
        result = get_str_fallback(
            {"descripcion": "", "description": "fallback route"},
            "descripcion",
            "description",
        )
        assert result == "fallback route"

    def test_primary_none_uses_fallback(self):
        """Primary key is None — falls back."""
        result = get_str_fallback(
            {"descripcion": None, "description": "fallback route"},
            "descripcion",
            "description",
        )
        assert result == "fallback route"

    def test_both_missing_uses_default(self):
        """Both keys absent — returns default empty string.

        Mutation: get_str_fallback(data, primary, fallback, default)
          -> get_str_fallback(data, primary, fallback)  — removes default
        Would return str(data.get(fallback, None)) = "None" instead of "".
        """
        result = get_str_fallback({}, "descripcion", "description")
        assert result == ""
        assert result != "None"

    def test_both_missing_custom_default(self):
        result = get_str_fallback({}, "a", "b", "unknown")
        assert result == "unknown"

    def test_primary_present_skips_fallback(self):
        """Primary present — fallback value should not matter."""
        result = get_str_fallback(
            {"descripcion": "primary", "description": "fallback"},
            "descripcion",
            "description",
        )
        assert result == "primary"


class TestGetStrNested:
    """Test get_str_nested — covers nested data.get(a, data.get(b, default)) patterns."""

    def test_primary_present_returns_it(self):
        result = get_str_nested({"type": "recurrente"}, "type", "trip_type")
        assert result == "recurrente"

    def test_primary_absent_uses_trip_type(self):
        """Falls back to trip_type when type is absent."""
        result = get_str_nested(
            {"trip_type": "puntual"}, "type", "trip_type"
        )
        assert result == "puntual"

    def test_both_absent_returns_default(self):
        """Both keys absent — returns default.

        Mutation: cascaded remove_arg on nested .get() calls.
        data.get("type", data.get("trip_type", "recurrente"))
        becomes data.get("type", data.get("trip_type", ))
        which returns None instead of "recurrente".
        """
        result = get_str_nested({}, "type", "trip_type")
        assert result == ""
        assert result != "None"

    def test_primary_none_uses_trip_type(self):
        """Primary is None (key exists but value is None) — falls back."""
        result = get_str_nested({"type": None, "trip_type": "puntual"}, "type", "trip_type")
        assert result == "puntual"

    def test_both_none_returns_default(self):
        """Both keys exist but are None — returns default."""
        result = get_str_nested({"type": None, "trip_type": None}, "type", "trip_type")
        assert result == ""


class TestGetVehicleId:
    """Test get_vehicle_id — covers data.get("vehicle_id", "unknown") pattern."""

    def test_present_vehicle_id(self):
        assert get_vehicle_id({"vehicle_id": "mi_auto"}) == "mi_auto"

    def test_missing_vehicle_id_returns_unknown(self):
        """Mutation: data.get("vehicle_id", "unknown") -> data.get("vehicle_id", )
        would return None instead of "unknown", breaking vehicle lookup.
        """
        assert get_vehicle_id({}) == "unknown"

    def test_missing_vehicle_id_not_none(self):
        """Ensure mutation that removes the default doesn't produce None."""
        result = get_vehicle_id({})
        assert result is not None
        assert result != "None"

    def test_empty_vehicle_id(self):
        assert get_vehicle_id({"vehicle_id": ""}) == ""


class TestGetBool:
    """Test get_bool — covers data.get("clear_existing", True) pattern."""

    def test_present_true(self):
        assert get_bool({"clear_existing": True}, "clear_existing") is True

    def test_present_false(self):
        assert get_bool({"clear_existing": False}, "clear_existing") is False

    def test_present_truthy_string(self):
        """String 'false' is truthy in Python — bool("false") is True."""
        # This is intentional — bool() only returns False for empty/falsy
        assert get_bool({"clear_existing": "false"}, "clear_existing") is True

    def test_missing_returns_default_true(self):
        """Mutation: data.get("clear_existing", True) -> data.get("clear_existing", )
        would return None, bool(None) = False instead of True.
        """
        assert get_bool({}, "clear_existing") is True

    def test_missing_custom_default_false(self):
        result = get_bool({}, "flag", False)
        assert result is False

    def test_none_value_returns_false(self):
        assert get_bool({"flag": None}, "flag") is False

    def test_empty_string_returns_false(self):
        assert get_bool({"flag": ""}, "flag") is False


class TestGetOptionalStr:
    """Test get_optional_str — covers data.get("datetime") pattern."""

    def test_present_string(self):
        assert get_optional_str({"datetime": "2026-01-01T10:00:00"}, "datetime") == "2026-01-01T10:00:00"

    def test_missing_returns_none(self):
        """Kill mutation: data.get("datetime") → data.get("datetime", "default")
        would return a string instead of None, changing control flow.
        """
        result = get_optional_str({}, "datetime")
        assert result is None

    def test_none_value_returns_default(self):
        """Explicit None is treated as missing."""
        assert get_optional_str({"datetime": None}, "datetime") is None

    def test_explicit_default_none(self):
        result = get_optional_str({}, "key")
        assert result is None

    def test_explicit_default_value(self):
        result = get_optional_str({}, "key", "fallback")
        assert result == "fallback"

    def test_non_string_value(self):
        """Integer value gets str()-ified."""
        result = get_optional_str({"count": 42}, "count")
        assert result == "42"

    def test_empty_string_returns_empty(self):
        """Empty string is a valid value, not None."""
        assert get_optional_str({"key": ""}, "key") == ""


class TestGetOr:
    """Test get_or — covers data.get("dia_semana") or data.get("day_of_week") pattern."""

    def test_primary_present(self):
        assert get_or({"dia_semana": "lunes"}, "dia_semana", "day_of_week") == "lunes"

    def test_primary_missing_fallback_used(self):
        """Kill mutation: removing fallback key lookup → returns None instead of fallback value."""
        assert get_or({"day_of_week": "monday"}, "dia_semana", "day_of_week") == "monday"

    def test_both_present_returns_primary(self):
        assert get_or({"dia_semana": "lunes", "day_of_week": "monday"}, "dia_semana", "day_of_week") == "lunes"

    def test_both_missing_returns_none(self):
        """Kill mutation: both key lookups removed → returns a non-None default."""
        result = get_or({}, "dia_semana", "day_of_week")
        assert result is None

    def test_primary_empty_uses_fallback(self):
        """Empty string is falsy → falls through to fallback."""
        assert get_or({"dia_semana": "", "day_of_week": "monday"}, "dia_semana", "day_of_week") == "monday"

    def test_primary_zero_uses_fallback(self):
        """Numeric zero is falsy → falls through to fallback."""
        assert get_or({"idx": 0, "index": 5}, "idx", "index") == 5

    def test_primary_int_fallback_missing(self):
        """Primary is an int, gets str()-ified (design: returns str)."""
        assert get_or({"idx": 42}, "idx", "index") == "42"
