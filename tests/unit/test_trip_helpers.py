"""Tests for trip/_helpers.py — pure helper functions for trip data extraction.

These tests kill mutations on the helper functions themselves by asserting
on exact return values. Without these tests, mutmut can mutate the default
values inside get_str, get_number, get_bool, get_dict, get_trip_datetime,
and get_trip_id, and the mutants would survive because the helpers were
never independently tested.
"""

from __future__ import annotations

import pytest


class TestGetStr:
    """Tests for get_str helper."""

    def test_existing_key_returns_value(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_str({"key": "value"}, "key") == "value"

    def test_missing_key_returns_default_empty_string(self):
        assert (
            pytest.importorskip(
                "custom_components.ev_trip_planner.trip._helpers"
            ).get_str({}, "missing")
            == ""
        )

    def test_missing_key_returns_custom_default(self):
        helpers = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        )
        assert helpers.get_str({}, "key", "fallback") == "fallback"

    def test_none_value_stringified(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_str({"key": None}, "key") == "None"

    def test_numeric_value_stringified(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_str({"key": 42}, "key") == "42"


class TestGetDict:
    """Tests for get_dict helper."""

    def test_existing_key_returns_value(self):
        data = {"key": {"nested": True}}
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_dict({"key": data}, "key") == data

    def test_missing_key_returns_empty_dict(self):
        assert (
            pytest.importorskip(
                "custom_components.ev_trip_planner.trip._helpers"
            ).get_dict({}, "missing")
            == {}
        )

    def test_none_value_returns_empty_dict(self):
        assert (
            pytest.importorskip(
                "custom_components.ev_trip_planner.trip._helpers"
            ).get_dict({"key": None}, "key")
            == {}
        )

    def test_custom_default_on_missing(self):
        helpers = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        )
        default = {"default": True}
        result = helpers.get_dict({}, "missing", default)
        assert result is default

    def test_custom_default_on_none_value(self):
        helpers = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        )
        default = {"default": True}
        result = helpers.get_dict({"key": None}, "key", default)
        assert result is default


class TestGetNumber:
    """Tests for get_number helper."""

    def test_existing_key_returns_float(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_number({"key": 3.5}, "key") == 3.5

    def test_missing_key_returns_default(self):
        assert (
            pytest.importorskip(
                "custom_components.ev_trip_planner.trip._helpers"
            ).get_number({}, "missing", 5.0)
            == 5.0
        )

    def test_zero_value(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_number({"key": 0}, "key") == 0.0

    def test_negative_value(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_number({"key": -10.5}, "key") == -10.5

    def test_string_number(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_number({"key": "42.5"}, "key") == 42.5


class TestGetBool:
    """Tests for get_bool helper."""

    def test_true_value(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_bool({"key": True}, "key") is True

    def test_false_value(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_bool({"key": False}, "key") is False

    def test_missing_key_returns_true_default(self):
        assert (
            pytest.importorskip(
                "custom_components.ev_trip_planner.trip._helpers"
            ).get_bool({}, "missing")
            is True
        )

    def test_missing_key_custom_default(self):
        assert (
            pytest.importorskip(
                "custom_components.ev_trip_planner.trip._helpers"
            ).get_bool({}, "missing", False)
            is False
        )

    def test_empty_string_is_false(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_bool({"key": ""}, "key") is False

    def test_nonzero_string_is_true(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_bool({"key": "yes"}, "key") is True


class TestGetVehicleId:
    """Tests for get_vehicle_id helper."""

    def test_existing_vehicle_id(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_vehicle_id({"vehicle_id": "my-car"}) == "my-car"

    def test_missing_vehicle_id_default(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_vehicle_id({}) == "unknown"

    def test_custom_default(self):
        assert (
            pytest.importorskip(
                "custom_components.ev_trip_planner.trip._helpers"
            ).get_vehicle_id({}, "default")
            == "default"
        )


class TestGetTripDatetime:
    """Tests for get_trip_datetime helper."""

    def test_datetime_key(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_trip_datetime({"datetime": "2025-06-15T10:30:00"}) == "2025-06-15T10:30:00"

    def test_datetime_str_key(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_trip_datetime({"datetime_str": "2025-06-15T10:30:00"}) == (
            "2025-06-15T10:30:00"
        )

    def test_datetime_str_fallback_to_datetime(self):
        assert (
            pytest.importorskip(
                "custom_components.ev_trip_planner.trip._helpers"
            ).get_trip_datetime({"datetime_str": "", "datetime": "2025-06-15"})
            == "2025-06-15"
        )

    def test_empty_both_keys(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_trip_datetime({}) == ""

    def test_falsy_datetime_str_fallback(self):
        assert (
            pytest.importorskip(
                "custom_components.ev_trip_planner.trip._helpers"
            ).get_trip_datetime({"datetime_str": None, "datetime": "2025-06-15"})
            == "2025-06-15"
        )


class TestGetTripId:
    """Tests for get_trip_id helper."""

    def test_existing_trip_id(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_trip_id({"id": "trip-monday-commute-7am"}) == "trip-monday-commute-7am"

    def test_missing_id(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_trip_id({}) == ""

    def test_none_id(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_trip_id({"id": None}) == ""

    def test_empty_string_id(self):
        assert pytest.importorskip(
            "custom_components.ev_trip_planner.trip._helpers"
        ).get_trip_id({"id": ""}) == ""
