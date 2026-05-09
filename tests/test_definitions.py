"""Tests for sensor definitions."""

from custom_components.ev_trip_planner.definitions import (
    TRIP_SENSORS,
    TripSensorEntityDescription,
    default_attrs_fn,
)


def test_entity_description_has_exists_fn() -> None:
    """Test that TripSensorEntityDescription has exists_fn callable field defaulting to lambda _: True."""
    desc = TripSensorEntityDescription(key="test_sensor")

    # Verify exists_fn exists and is callable
    assert hasattr(
        desc, "exists_fn"
    ), "TripSensorEntityDescription should have exists_fn field"
    assert callable(desc.exists_fn), "exists_fn should be callable"

    # Verify default behavior - should return True for any input
    assert desc.exists_fn({}) is True
    assert desc.exists_fn({"some": "data"}) is True
    assert desc.exists_fn(None) is True


def test_entity_description_has_restore_field() -> None:
    """Test that TripSensorEntityDescription has restore: bool field defaulting to False."""
    desc = TripSensorEntityDescription(key="test_sensor")

    # Verify restore field exists
    assert hasattr(
        desc, "restore"
    ), "TripSensorEntityDescription should have restore field"

    # Verify default is False
    assert desc.restore is False, "restore should default to False"


def test_entity_description_exists_fn_and_restore_fields() -> None:
    """Test combined existence of both exists_fn and restore fields."""
    desc = TripSensorEntityDescription(key="test_sensor")

    # Both fields should exist
    assert hasattr(
        desc, "exists_fn"
    ), "TripSensorEntityDescription should have exists_fn field"
    assert hasattr(
        desc, "restore"
    ), "TripSensorEntityDescription should have restore field"

    # defaults: exists_fn returns True, restore is False
    assert desc.exists_fn({"test": "data"}) is True
    assert desc.restore is False


# --- Tests for default_attrs_fn (mutation killing) ---


def test_default_attrs_fn_with_full_data():
    """Test default_attrs_fn returns correct recurring and punctual trips from data."""
    trip1 = {"id": "trip1", "name": "Morning"}
    trip2 = {"id": "trip2", "name": "Evening"}
    trip3 = {"id": "trip3", "name": "Weekend"}
    data = {
        "recurring_trips": {"t1": trip1, "t2": trip2},
        "punctual_trips": {"t3": trip3},
    }
    result = default_attrs_fn(data)

    # Must use exact key "recurring_trips" — kills mutmut_4,8,9
    assert result["recurring_trips"] == [trip1, trip2]
    # Must use exact key "punctual_trips" — kills mutmut_13,17,18
    assert result["punctual_trips"] == [trip3]


def test_default_attrs_fn_recurring_trips_key_case_sensitive():
    """Test that recurring_trips key is case-sensitive — kills mutmut_9 (RECURRING_TRIPS)."""
    data = {"recurring_trips": {"a": {"id": "a"}}, "punctual_trips": {}}
    result = default_attrs_fn(data)
    assert len(result["recurring_trips"]) == 1
    assert result["recurring_trips"][0] == {"id": "a"}


def test_default_attrs_fn_punctual_trips_key_case_sensitive():
    """Test that punctual_trips key is case-sensitive — kills mutmut_18 (PUNCTUAL_TRIPS)."""
    data = {"recurring_trips": {}, "punctual_trips": {"b": {"id": "b"}}}
    result = default_attrs_fn(data)
    assert len(result["punctual_trips"]) == 1
    assert result["punctual_trips"][0] == {"id": "b"}


def test_default_attrs_fn_missing_recurring_key_uses_default():
    """Test default {} is used when recurring_trips missing — kills mutmut_5,7 (None/empty default)."""
    data = {"punctual_trips": {}}
    result = default_attrs_fn(data)
    # With default {}, .values() returns empty list
    assert result["recurring_trips"] == []


def test_default_attrs_fn_missing_punctual_key_uses_default():
    """Test default {} is used when punctual_trips missing — kills mutmut_14,16 (None/empty default)."""
    data = {"recurring_trips": {}}
    result = default_attrs_fn(data)
    assert result["punctual_trips"] == []


def test_default_attrs_fn_with_none_data():
    """Test default_attrs_fn with None data returns empty lists."""
    result = default_attrs_fn(None)
    assert result["recurring_trips"] == []
    assert result["punctual_trips"] == []


def test_default_attrs_fn_returns_both_keys():
    """Test that result has exactly recurring_trips and punctual_trips keys."""
    result = default_attrs_fn({"recurring_trips": {}, "punctual_trips": {}})
    assert set(result.keys()) == {"recurring_trips", "punctual_trips"}


def test_default_attrs_fn_values_not_transformed():
    """Test that .values() returns actual trip dicts, not keys or transformed data."""
    trip_a = {"id": "a", "destination": "Madrid"}
    trip_b = {"id": "b", "destination": "Barcelona"}
    data = {"recurring_trips": {"key_a": trip_a}, "punctual_trips": {"key_b": trip_b}}
    result = default_attrs_fn(data)
    assert trip_a in result["recurring_trips"]
    assert trip_b in result["punctual_trips"]


def test_trip_sensors_count():
    """Test TRIP_SENSORS has expected number of entries."""
    assert len(TRIP_SENSORS) == 7


def test_trip_sensors_keys():
    """Test TRIP_SENSORS contains expected sensor keys."""
    keys = [s.key for s in TRIP_SENSORS]
    assert "recurring_trips_count" in keys
    assert "punctual_trips_count" in keys
    assert "trips_list" in keys
    assert "kwh_needed_today" in keys
    assert "hours_needed_today" in keys
    assert "next_trip" in keys
    assert "next_deadline" in keys
