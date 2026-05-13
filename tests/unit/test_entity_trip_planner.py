"""Tests for sensor/entity_trip_planner.py uncovered code paths."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.ev_trip_planner.coordinator import (
    CoordinatorConfig,
    TripPlannerCoordinator,
)
from custom_components.ev_trip_planner.sensor.entity_trip_planner import (
    TripPlannerSensor,
)


@pytest.fixture(autouse=True)
def mock_frame_reporting():
    """Mock frame reporting to avoid 'Frame helper not set up' error."""
    with patch("homeassistant.helpers.frame.report_usage", return_value=None):
        yield


def _make_coordinator():
    """Create a minimal TripPlannerCoordinator for testing."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    hass.config_entries.async_entries = MagicMock(return_value=[])
    entry = MagicMock()
    entry.data = {
        "vehicle_name": "test_vehicle",
        "charging_power_kw": 7.0,
        "battery_capacity_kwh": 75.0,
    }
    tm = MagicMock()
    tm._crud.async_get_recurring_trips = MagicMock(return_value=[])
    tm._crud.async_get_punctual_trips = MagicMock(return_value=[])
    tm._soc_query.async_get_kwh_needed_today = MagicMock(return_value=0.0)
    tm._soc_query.async_get_hours_needed_today = MagicMock(return_value=0.0)
    tm._navigator.async_get_next_trip = MagicMock(return_value=None)
    config = CoordinatorConfig(emhass_adapter=None)
    return TripPlannerCoordinator(
        hass=hass, entry=entry, trip_manager=tm, config=config,
    )


def _make_sensor(coordinator, vehicle_id="test_vehicle", key="test_sensor"):
    """Create a TripPlannerSensor with given coordinator, vehicle_id and key."""
    from custom_components.ev_trip_planner.definitions import (
        TripSensorEntityDescription,
    )
    desc = TripSensorEntityDescription(key=key)
    return TripPlannerSensor(coordinator, vehicle_id, desc)


class TestTripPlannerSensorNativeValueNone:
    """Test native_value when coordinator.data is None (line 77-78)."""

    def test_coordinator_data_none(self):
        """Coordinator data is None -> returns None (line 78)."""
        coordinator = _make_coordinator()
        coordinator.data = None
        sensor = _make_sensor(coordinator)
        assert sensor.native_value is None


class TestTripPlannerSensorExtraStateAttributesNone:
    """Test extra_state_attributes when coordinator.data is None (line 85-86)."""

    def test_coordinator_data_none_returns_empty_dict(self):
        """Coordinator data is None -> returns {} (line 86)."""
        coordinator = _make_coordinator()
        coordinator.data = None
        sensor = _make_sensor(coordinator)
        assert sensor.extra_state_attributes == {}


class TestTripPlannerSensorDeviceInfo:
    """Test device_info property (line 93-101)."""

    def test_device_info_returns_correct_identifiers(self):
        """Returns DeviceInfo with DOMAIN and vehicle_id identifiers."""
        coordinator = _make_coordinator()
        sensor = _make_sensor(coordinator, vehicle_id="my_vehicle")
        info = sensor.device_info
        assert info is not None
        assert "identifiers" in info
        identifiers = info["identifiers"]
        assert isinstance(identifiers, set)
        from custom_components.ev_trip_planner.const import DOMAIN
        assert any(DOMAIN in item for item in identifiers)
        assert any("my_vehicle" in item for item in identifiers)

    def test_device_info_has_all_fields(self):
        """Device info includes name, manufacturer, model, sw_version."""
        coordinator = _make_coordinator()
        sensor = _make_sensor(coordinator, vehicle_id="v1")
        info = sensor.device_info
        assert info["name"] == "EV Trip Planner v1"
        assert info["manufacturer"] == "Home Assistant"
        assert info["model"] == "EV Trip Planner"
        assert info["sw_version"] == "2026.3.0"
