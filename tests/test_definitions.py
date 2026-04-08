"""Tests for sensor definitions."""

from custom_components.ev_trip_planner.definitions import TripSensorEntityDescription


def test_entity_description_has_exists_fn() -> None:
    """Test that TripSensorEntityDescription has exists_fn callable field defaulting to lambda _: True."""
    desc = TripSensorEntityDescription(key="test_sensor")

    # Verify exists_fn exists and is callable
    assert hasattr(desc, "exists_fn"), "TripSensorEntityDescription should have exists_fn field"
    assert callable(desc.exists_fn), "exists_fn should be callable"

    # Verify default behavior - should return True for any input
    assert desc.exists_fn({}) is True
    assert desc.exists_fn({"some": "data"}) is True
    assert desc.exists_fn(None) is True


def test_entity_description_has_restore_field() -> None:
    """Test that TripSensorEntityDescription has restore: bool field defaulting to False."""
    desc = TripSensorEntityDescription(key="test_sensor")

    # Verify restore field exists
    assert hasattr(desc, "restore"), "TripSensorEntityDescription should have restore field"

    # Verify default is False
    assert desc.restore is False, "restore should default to False"


def test_entity_description_exists_fn_and_restore_fields() -> None:
    """Test combined existence of both exists_fn and restore fields."""
    desc = TripSensorEntityDescription(key="test_sensor")

    # Both fields should exist
    assert hasattr(desc, "exists_fn"), "TripSensorEntityDescription should have exists_fn field"
    assert hasattr(desc, "restore"), "TripSensorEntityDescription should have restore field"

    # defaults: exists_fn returns True, restore is False
    assert desc.exists_fn({"test": "data"}) is True
    assert desc.restore is False