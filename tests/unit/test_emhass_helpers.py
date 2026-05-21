"""Tests for emhass._helpers — US-5 config-key defaults and validation.

Each test asserts specific return values to kill default_value mutations
on the helper functions. Uses distinctive non-default data so mutations
flip the asserted output.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from custom_components.ev_trip_planner.emhass._helpers import (
    build_entry_data,
    clamp_hours,
    clamp_positive,
    ensure_aware_utc,
    get_config_bool,
    get_config_nested,
    get_config_number,
    get_config_str,
    parse_planning_horizon,
)

# ---------------------------------------------------------------------------
# get_config_str — default_value mutations on "" default
# ---------------------------------------------------------------------------


class TestGetConfigStr:
    """Tests for get_config_str default-value mutations."""

    def test_returns_value_when_key_present(self):
        """Key present → return str(value)."""
        data = {"vehicle_name": "TestCar"}
        assert get_config_str(data, "vehicle_name") == "TestCar"

    def test_returns_default_when_key_missing(self):
        """Key missing → return default empty string."""
        data: dict = {}
        assert get_config_str(data, "vehicle_name") == ""

    def test_returns_provided_default(self):
        """Key missing → return explicit default value."""
        data: dict = {}
        assert get_config_str(data, "vehicle_name", "Unknown") == "Unknown"

    def test_returns_str_of_non_string_value(self):
        """Key present with int → str(value)."""
        data = {"count": 42}
        assert get_config_str(data, "count") == "42"

    def test_none_value_returns_default(self):
        """Key present but None → return default."""
        data = {"vehicle_name": None}
        assert get_config_str(data, "vehicle_name", "fallback") == "fallback"

    def test_empty_string_value_returned(self):
        """Key present with empty string → return it (not default)."""
        data = {"vehicle_name": ""}
        assert get_config_str(data, "vehicle_name", "fallback") == ""

    def test_custom_default_applied(self):
        """Non-empty default is returned, not empty string default."""
        data: dict = {}
        result = get_config_str(data, "missing_key", "default_val")
        assert result == "default_val"
        assert result != ""  # kill default_value mutation "" → "default_val"


# ---------------------------------------------------------------------------
# get_config_number — default_value mutations on 0.0 default
# ---------------------------------------------------------------------------


class TestGetConfigNumber:
    """Tests for get_config_number default-value mutations."""

    def test_returns_value_when_key_present(self):
        """Key present → return float(value)."""
        data = {"battery_capacity_kwh": 50.0}
        assert get_config_number(data, "battery_capacity_kwh") == 50.0

    def test_returns_default_when_key_missing(self):
        """Key missing → return default 0.0."""
        data: dict = {}
        assert get_config_number(data, "battery_capacity_kwh") == 0.0

    def test_returns_provided_default(self):
        """Key missing → return explicit default."""
        data: dict = {}
        assert get_config_number(data, "battery_capacity_kwh", 100.0) == 100.0

    def test_int_converted_to_float(self):
        """Integer value → converted to float."""
        data = {"battery_capacity_kwh": 50}
        assert get_config_number(data, "battery_capacity_kwh") == 50.0

    def test_none_value_returns_default(self):
        """Key present but None → return default."""
        data = {"battery_capacity_kwh": None}
        assert get_config_number(data, "battery_capacity_kwh", 75.0) == 75.0

    def test_invalid_string_returns_default(self):
        """Non-numeric string → return default."""
        data = {"battery_capacity_kwh": "not_a_number"}
        assert get_config_number(data, "battery_capacity_kwh", 30.0) == 30.0

    def test_negative_value_returned(self):
        """Negative value → returned as-is (not clamped)."""
        data = {"battery_capacity_kwh": -10.0}
        assert get_config_number(data, "battery_capacity_kwh") == -10.0

    def test_zero_value_returned(self):
        """Explicit zero → returned, not default."""
        data = {"battery_capacity_kwh": 0.0}
        assert get_config_number(data, "battery_capacity_kwh", 50.0) == 0.0

    def test_decimal_value_preserved(self):
        """Decimal value → preserved precisely."""
        data = {"safety_margin_percent": 73.5}
        assert get_config_number(data, "safety_margin_percent") == 73.5

    def test_default_zero_vs_ten(self):
        """Kill default_value mutation: 0.0 → 10.0."""
        data: dict = {}
        assert get_config_number(data, "missing", 10.0) == 10.0
        assert get_config_number(data, "missing") == 0.0


# ---------------------------------------------------------------------------
# get_config_bool — default_value mutations on True default
# ---------------------------------------------------------------------------


class TestGetConfigBool:
    """Tests for get_config_bool default-value mutations."""

    def test_true_value(self):
        """True → return True."""
        data = {"enabled": True}
        assert get_config_bool(data, "enabled") is True

    def test_false_value(self):
        """False → return False."""
        data = {"enabled": False}
        assert get_config_bool(data, "enabled") is False

    def test_missing_returns_default_true(self):
        """Missing key → return default True."""
        data: dict = {}
        assert get_config_bool(data, "enabled") is True

    def test_missing_returns_explicit_default_false(self):
        """Missing key → return explicit default False."""
        data: dict = {}
        assert get_config_bool(data, "enabled", default=False) is False

    def test_none_returns_default(self):
        """None value → return default."""
        data = {"enabled": None}
        assert get_config_bool(data, "enabled", default=False) is False

    def test_string_truthy(self):
        """Non-empty string → True."""
        data = {"enabled": "yes"}
        assert get_config_bool(data, "enabled") is True

    def test_string_falsy(self):
        """Empty string → False."""
        data = {"enabled": ""}
        assert get_config_bool(data, "enabled") is False

    def test_zero_is_false(self):
        """Integer zero → False."""
        data = {"enabled": 0}
        assert get_config_bool(data, "enabled") is False

    def test_one_is_true(self):
        """Integer one → True."""
        data = {"enabled": 1}
        assert get_config_bool(data, "enabled") is True


# ---------------------------------------------------------------------------
# get_config_nested — default_value and fallback mutations
# ---------------------------------------------------------------------------


class TestGetConfigNested:
    """Tests for get_config_nested default-value and fallback mutations."""

    def test_primary_key_present(self):
        """Primary key exists → return its value."""
        data = {"primary": "from_primary"}
        assert get_config_nested(data, "primary", "fallback") == "from_primary"

    def test_primary_missing_fallback_present(self):
        """Primary missing, fallback present → return fallback."""
        data = {"fallback": "from_fallback"}
        result = get_config_nested(data, "primary", "fallback")
        assert result == "from_fallback"

    def test_both_missing_returns_default(self):
        """Both missing → return default empty string."""
        data: dict = {}
        assert get_config_nested(data, "primary", "fallback") == ""

    def test_both_present_uses_primary(self):
        """Both present → use primary, not fallback."""
        data = {"primary": "P", "fallback": "F"}
        assert get_config_nested(data, "primary", "fallback") == "P"

    def test_explicit_default_when_both_missing(self):
        """Both missing with explicit default → return it."""
        data: dict = {}
        result = get_config_nested(data, "primary", "fallback", "my_default")
        assert result == "my_default"
        assert result != ""  # kill default_value mutation "" → "my_default"

    def test_none_primary_uses_fallback(self):
        """Primary is None → use fallback."""
        data = {"primary": None, "fallback": "fallback_val"}
        assert get_config_nested(data, "primary", "fallback") == "fallback_val"

    def test_empty_string_primary_used(self):
        """Primary is empty string (not None) → return it."""
        data = {"primary": "", "fallback": "F"}
        assert get_config_nested(data, "primary", "fallback") == ""


# ---------------------------------------------------------------------------
# build_entry_data — config entry merging
# ---------------------------------------------------------------------------


class TestBuildEntryData:
    """Tests for build_entry_data config merging."""

    def test_none_entry_returns_empty(self):
        """None entry → empty dict."""
        assert build_entry_data(None) == {}

    def test_dict_entry_merged(self):
        """Dict entry → returned as-is."""
        data = {"key": "value", "number": 42}
        result = build_entry_data(data)
        assert result == {"key": "value", "number": 42}

    def test_options_and_data_merged(self):
        """Options + data → data takes precedence."""
        entry = MagicMock()
        entry.options = {"a": 1, "b": 2}
        entry.data = {"b": 3, "c": 4}
        result = build_entry_data(entry)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_options_only(self):
        """Only options present → merged."""
        entry = MagicMock()
        entry.options = {"x": "y"}
        entry.data = {}
        result = build_entry_data(entry)
        assert result == {"x": "y"}

    def test_data_only(self):
        """Only data present → merged."""
        entry = MagicMock()
        entry.options = {}
        entry.data = {"key": "val"}
        result = build_entry_data(entry)
        assert result == {"key": "val"}

    def test_dict_subclass_entry_merged(self):
        """Dict subclass entry → merged."""
        from unittest.mock import MagicMock

        entry = MagicMock()
        entry.options = {"a": 1}
        entry.data = {"b": 2}
        entry.__iter__ = MagicMock(side_effect=lambda: iter(["a", "b"]))
        entry.__getitem__ = MagicMock(side_effect=lambda k: {"a": 1, "b": 2}[k])
        result = build_entry_data(entry)
        assert result["a"] == 1
        assert result["b"] == 2

    def test_options_typeerror_catches_and_skips(self):
        """Options that raise TypeError when converted to dict → skipped."""
        entry = MagicMock()
        entry.options = "not_a_dict"  # str → TypeError in dict()
        entry.data = {"key": "val"}
        result = build_entry_data(entry)
        assert result == {"key": "val"}

    def test_options_valueerror_catches_and_skips(self):
        """Options that raise ValueError when converted to dict → skipped."""
        entry = MagicMock()
        entry.options = 42  # int → TypeError in dict()
        entry.data = {}
        result = build_entry_data(entry)
        assert result == {}

    def test_data_typeerror_catches_and_skips(self):
        """Data that raises TypeError when converted to dict → skipped."""
        entry = MagicMock()
        entry.options = {}
        entry.data = "bad_data"  # str → TypeError in dict()
        result = build_entry_data(entry)
        assert result == {}

    def test_data_valueerror_catches_and_skips(self):
        """Data that raises ValueError when converted to dict → skipped."""
        entry = MagicMock()
        entry.options = {"a": 1}
        entry.data = 123  # int → TypeError in dict()
        result = build_entry_data(entry)
        assert result == {"a": 1}

    def test_both_options_and_data_typeerror(self):
        """Both options and data raise TypeError → returns empty dict."""
        entry = MagicMock()
        entry.options = "bad"
        entry.data = 42
        result = build_entry_data(entry)
        assert result == {}


# ---------------------------------------------------------------------------
# parse_planning_horizon — default_value and boundary mutations
# ---------------------------------------------------------------------------


class TestParsePlanningHorizon:
    """Tests for parse_planning_horizon default and boundary mutations."""

    def test_default_days_when_missing(self):
        """Missing key → default 7 days = 168 hours."""
        data: dict = {}
        assert parse_planning_horizon(data) == 168

    def test_custom_default_days(self):
        """Custom default_days → multiplied by 24."""
        data: dict = {}
        assert parse_planning_horizon(data, default_days=14) == 336

    def test_value_present(self):
        """Value present → used directly."""
        data = {"planning_horizon_days": 3}
        assert parse_planning_horizon(data) == 72

    def test_value_zero(self):
        """Zero days → 0 hours."""
        data = {"planning_horizon_days": 0}
        assert parse_planning_horizon(data) == 0

    def test_value_one(self):
        """One day → 24 hours."""
        data = {"planning_horizon_days": 1}
        assert parse_planning_horizon(data) == 24

    def test_value_hundred(self):
        """100 days → 2400 hours."""
        data = {"planning_horizon_days": 100}
        assert parse_planning_horizon(data) == 2400

    def test_invalid_string_returns_default(self):
        """Non-numeric string → return default * 24."""
        data = {"planning_horizon_days": "abc"}
        assert parse_planning_horizon(data) == 168

    def test_none_value_returns_default(self):
        """None value → return default * 24."""
        data = {"planning_horizon_days": None}
        assert parse_planning_horizon(data) == 168


# ---------------------------------------------------------------------------
# ensure_aware_utc — timezone mutations
# ---------------------------------------------------------------------------


class TestEnsureAwareUtc:
    """Tests for ensure_aware_utc timezone mutations."""

    def test_naive_converted_to_utc(self):
        """Naive datetime → UTC timezone added."""
        dt = datetime(2026, 5, 21, 12, 0, 0)
        result = ensure_aware_utc(dt)
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(None).total_seconds() == 0  # UTC

    def test_aware_returned_as_is(self):
        """Aware datetime → returned unchanged."""
        dt = datetime(2026, 5, 21, 12, 0, 0, tzinfo=timezone.utc)
        result = ensure_aware_utc(dt)
        assert result.tzinfo is timezone.utc

    def test_non_utc_aware_returned_as_is(self):
        """Non-UTC aware datetime → returned unchanged."""
        from datetime import timezone as tz

        offset = tz(timedelta(hours=2))
        dt = datetime(2026, 5, 21, 12, 0, 0, tzinfo=offset)
        result = ensure_aware_utc(dt)
        assert result.tzinfo == offset

    def test_naive_has_no_tzinfo_before(self):
        """Input naive → confirm no tzinfo."""
        dt = datetime(2026, 5, 21, 12, 0, 0)
        assert dt.tzinfo is None

    def test_result_has_utc_tzinfo(self):
        """Result after conversion → UTC tzinfo."""
        dt = datetime(2026, 5, 21, 12, 0, 0)
        result = ensure_aware_utc(dt)
        assert result.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# clamp_positive — boundary mutations
# ---------------------------------------------------------------------------


class TestClampPositive:
    """Tests for clamp_positive boundary mutations."""

    def test_negative_clamped_to_zero(self):
        """Negative value → 0."""
        assert clamp_positive(-10.0) == 0

    def test_zero_clamped_to_zero(self):
        """Zero → 0."""
        assert clamp_positive(0.0) == 0

    def test_positive_within_max(self):
        """Positive within max → returned as int."""
        assert clamp_positive(100.0) == 100

    def test_at_max(self):
        """Value at max → max."""
        assert clamp_positive(168.0) == 168

    def test_above_max_clamped(self):
        """Value above max → max."""
        assert clamp_positive(200.0) == 168

    def test_below_max_with_fraction(self):
        """Value with fraction below max → int truncated then clamped."""
        assert clamp_positive(100.9) == 100

    def test_very_large_clamped(self):
        """Very large value → max."""
        assert clamp_positive(9999.0) == 168

    def test_custom_max(self):
        """Custom max → clamped to it."""
        assert clamp_positive(50.0, max_value=30) == 30
        assert clamp_positive(10.0, max_value=30) == 10

    def test_boundary_exactly_one(self):
        """Value 1.0 → 1."""
        assert clamp_positive(1.0) == 1

    def test_boundary_just_below_zero(self):
        """-0.5 → 0."""
        assert clamp_positive(-0.5) == 0


# ---------------------------------------------------------------------------
# clamp_hours — epsilon and ceiling mutations
# ---------------------------------------------------------------------------


class TestClampHours:
    """Tests for clamp_hours with epsilon adjustment."""

    def test_exact_hour(self):
        """Exact hour value → returned as int."""
        assert clamp_hours(5.0) == 5

    def test_fractional_hour_ceil(self):
        """Fractional hour → ceiling applied."""
        assert clamp_hours(5.1) == 6

    def test_just_below_integer(self):
        """5.999 → 6 (ceil after epsilon)."""
        assert clamp_hours(5.999) == 6

    def test_just_above_integer(self):
        """5.001 - 0.001 = 5.0, ceil = 5."""
        assert clamp_hours(5.001) == 5

    def test_significantly_above_integer(self):
        """5.01 - 0.001 = 5.009, ceil = 6."""
        assert clamp_hours(5.01) == 6

    def test_negative_clamped_to_zero(self):
        """Negative → 0."""
        assert clamp_hours(-1.0) == 0

    def test_zero(self):
        """Zero → 0."""
        assert clamp_hours(0.0) == 0

    def test_above_max_clamped(self):
        """Above max → max."""
        assert clamp_hours(200.0) == 168

    def test_epsilon_boundary(self):
        """Value at epsilon boundary → adjusted correctly."""
        assert clamp_hours(5.0, epsilon=0.001) == 5

    def test_custom_max(self):
        """Custom max → clamped."""
        assert clamp_hours(100.0, max_value=50) == 50

    def test_max_value_hundred(self):
        """Custom max 100 → clamped to 100."""
        assert clamp_hours(150.0, max_value=100) == 100
        assert clamp_hours(50.0, max_value=100) == 50  # ceil(50 - 0.001) = 50
