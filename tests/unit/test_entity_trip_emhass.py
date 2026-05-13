"""Tests for sensor/entity_trip_emhass.py uncovered code paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.coordinator import (
    CoordinatorConfig,
    TripPlannerCoordinator,
)
from custom_components.ev_trip_planner.sensor.entity_trip_emhass import (
    TripEmhassSensor,
    TRIP_EMHASS_ATTR_KEYS,
)


@pytest.fixture(autouse=True)
def mock_frame_reporting():
    """Mock frame reporting to avoid 'Frame helper not set up' error."""
    with patch("homeassistant.helpers.frame.report_usage", return_value=None):
        yield


def _make_mock_hass():
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return hass


def _make_trip_manager():
    tm = MagicMock()
    tm._crud.async_get_recurring_trips = AsyncMock(return_value=[])
    return tm


def _make_coordinator():
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
    tm._crud.async_get_recurring_trips = AsyncMock(return_value=[])
    tm._crud.async_get_punctual_trips = AsyncMock(return_value=[])
    tm._soc_query.async_get_kwh_needed_today = AsyncMock(return_value=12.5)
    tm._soc_query.async_get_hours_needed_today = AsyncMock(return_value=2.0)
    tm._navigator.async_get_next_trip = AsyncMock(return_value=None)
    config = CoordinatorConfig(emhass_adapter=None)
    coord = TripPlannerCoordinator(
        hass=hass, entry=entry, trip_manager=tm, config=config,
    )
    return coord


def _make_sensor(coord, trip_id="rec_1"):
    return TripEmhassSensor(coord, "test_vehicle", trip_id)


class TestTripEmhassSensorExists:
    """TripEmhassSensor must be importable and have required methods."""

    def test_importable(self):
        from custom_components.ev_trip_planner.sensor.entity_trip_emhass import (
            TripEmhassSensor,
        )
        assert TripEmhassSensor is not None

    def test_has_native_value_property(self):
        assert hasattr(TripEmhassSensor, "native_value")

    def test_has_extra_state_attributes(self):
        assert hasattr(TripEmhassSensor, "extra_state_attributes")

    def test_has_device_info(self):
        assert hasattr(TripEmhassSensor, "device_info")

    def test_has_zeroed_attributes(self):
        assert hasattr(TripEmhassSensor, "_zeroed_attributes")


class TestTripEmhassSensorNativeValue:
    """Test native_value property."""

    def test_coordinator_data_none(self):
        """Coordinator data is None → returns -1."""
        coord = MagicMock()
        coord.data = None
        sensor = TripEmhassSensor(coord, "test_vehicle", "t1")
        assert sensor.native_value == -1

    def test_trip_not_found(self):
        """Trip not in params → returns -1."""
        coord = _make_coordinator()
        coord.data = {"per_trip_emhass_params": {}}
        sensor = _make_sensor(coord, "nonexistent")
        assert sensor.native_value == -1

    def test_trip_found_no_emhass_index(self):
        """Trip found but no emhass_index → returns -1."""
        coord = _make_coordinator()
        coord.data = {"per_trip_emhass_params": {"t1": {"kwh_needed": 5.0}}}
        sensor = _make_sensor(coord, "t1")
        assert sensor.native_value == -1

    def test_trip_found_with_emhass_index(self):
        """Trip found with emhass_index → returns it."""
        coord = _make_coordinator()
        coord.data = {"per_trip_emhass_params": {"t1": {"emhass_index": 3}}}
        sensor = _make_sensor(coord, "t1")
        assert sensor.native_value == 3

    def test_emhass_index_none_returns_minus_one(self):
        """emhass_index is None → returns -1."""
        coord = _make_coordinator()
        coord.data = {"per_trip_emhass_params": {"t1": {"emhass_index": None}}}
        sensor = _make_sensor(coord, "t1")
        assert sensor.native_value == -1


class TestTripEmhassSensorAttributes:
    """Test extra_state_attributes property."""

    def test_coordinator_data_none(self):
        """Coordinator data is None → zeroed attributes."""
        coord = MagicMock()
        coord.data = None
        sensor = TripEmhassSensor(coord, "test_vehicle", "t1")
        attrs = sensor.extra_state_attributes
        assert attrs["def_total_hours"] == 0.0
        assert attrs["emhass_index"] == -1
        assert attrs["kwh_needed"] == 0.0
        assert attrs["power_profile_watts"] == []

    def test_trip_not_found(self):
        """Trip not found → zeroed attributes."""
        coord = _make_coordinator()
        coord.data = {"per_trip_emhass_params": {}}
        sensor = _make_sensor(coord, "nonexistent")
        attrs = sensor.extra_state_attributes
        assert attrs["emhass_index"] == -1
        assert attrs["trip_id"] == "nonexistent"

    def test_trip_found_filters_keys(self):
        """Only 9 documented keys returned (line 112)."""
        coord = _make_coordinator()
        coord.data = {
            "per_trip_emhass_params": {
                "t1": {
                    "emhass_index": 2,
                    "kwh_needed": 5.0,
                    "def_total_hours": 2.0,
                    "P_deferrable_nom": 3600,
                    "def_start_timestep": 10,
                    "def_end_timestep": 24,
                    "power_profile_watts": [100, 200, 300],
                    "trip_id": "t1",
                    "deadline": "2026-05-15T09:00:00",
                    "activo": True,  # Should be filtered out
                    "_array": [1, 2, 3],  # Should be filtered out
                }
            }
        }
        sensor = _make_sensor(coord, "t1")
        attrs = sensor.extra_state_attributes
        assert attrs["emhass_index"] == 2
        assert attrs["kwh_needed"] == 5.0
        assert attrs["def_total_hours"] == 2.0
        assert attrs["P_deferrable_nom"] == 3600
        assert attrs["def_start_timestep"] == 10
        assert attrs["def_end_timestep"] == 24
        assert attrs["power_profile_watts"] == [100, 200, 300]
        assert attrs["trip_id"] == "t1"
        assert attrs["deadline"] == "2026-05-15T09:00:00"
        assert "activo" not in attrs
        assert "_array" not in attrs


class TestTripEmhassSensorDeviceInfo:
    """Test device_info property (line 145)."""

    def test_device_info_returns_info(self):
        """Returns DeviceInfo with correct identifiers."""
        coord = _make_coordinator()
        sensor = TripEmhassSensor(coord, "my_vehicle", "t1")
        info = sensor.device_info
        assert info is not None
        assert isinstance(info, dict)
        from custom_components.ev_trip_planner.const import DOMAIN
        assert DOMAIN in str(info.get("identifiers", set()))
        assert "my_vehicle" in str(info.get("identifiers", set()))


class TestZeroedAttributes:
    """Test _zeroed_attributes helper."""

    def test_zeroed_returns_all_keys(self):
        """Returns all 9 keys with zero/default values."""
        coord = _make_coordinator()
        sensor = TripEmhassSensor(coord, "test_vehicle", "t1")
        attrs = sensor._zeroed_attributes()
        assert attrs["def_total_hours"] == 0.0
        assert attrs["P_deferrable_nom"] == 0.0
        assert attrs["def_start_timestep"] == 0
        assert attrs["def_end_timestep"] == 24
        assert attrs["power_profile_watts"] == []
        assert attrs["trip_id"] == "t1"
        assert attrs["emhass_index"] == -1
        assert attrs["kwh_needed"] == 0.0
        assert attrs["deadline"] is None


class TestTRIP_EMHASS_ATTR_KEYS:
    """Test exported constants."""

    def test_has_nine_keys(self):
        assert len(TRIP_EMHASS_ATTR_KEYS) == 9

    def test_contains_expected_keys(self):
        expected = {
            "def_total_hours",
            "P_deferrable_nom",
            "def_start_timestep",
            "def_end_timestep",
            "power_profile_watts",
            "trip_id",
            "emhass_index",
            "kwh_needed",
            "deadline",
        }
        assert TRIP_EMHASS_ATTR_KEYS == expected
