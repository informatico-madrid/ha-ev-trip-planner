"""Tests for uncovered code paths in sensor.py and services.py.

Covers:
- sensor.py: _format_window_time edge cases, None coordinator.data, EmhassDeferrableLoadSensor cleanup
- services.py: _find_entry_by_vehicle edge cases, _get_manager error paths
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


# =============================================================================
# sensor.py - _format_window_time tests
# =============================================================================

class TestFormatWindowTime:
    """Tests for _format_window_time function."""

    def test_format_window_time_with_none(self):
        """None input returns None."""
        from custom_components.ev_trip_planner.sensor import _format_window_time

        result = _format_window_time(None)
        assert result is None

    def test_format_window_time_with_datetime(self):
        """datetime object returns formatted time."""
        from custom_components.ev_trip_planner.sensor import _format_window_time

        dt = datetime(2025, 1, 15, 14, 30)
        result = _format_window_time(dt)
        assert result == "14:30"

    def test_format_window_time_with_iso_string(self):
        """ISO format string returns formatted time."""
        from custom_components.ev_trip_planner.sensor import _format_window_time

        result = _format_window_time("2025-01-15T14:30:00")
        assert result == "14:30"

    def test_format_window_time_with_invalid_string(self):
        """Invalid string returns None."""
        from custom_components.ev_trip_planner.sensor import _format_window_time

        result = _format_window_time("not-a-date")
        assert result is None

    def test_format_window_time_with_unsupported_type(self):
        """Unsupported type returns None."""
        from custom_components.ev_trip_planner.sensor import _format_window_time

        result = _format_window_time(12345)
        assert result is None


# =============================================================================
# sensor.py - TripPlannerSensor native_value / extra_state_attributes with None data
# =============================================================================

class TestTripPlannerSensorNoneData:
    """Tests for TripPlannerSensor when coordinator.data is None."""

    def test_native_value_returns_none_when_coordinator_data_is_none(self):
        """native_value returns None when coordinator.data is None."""
        from custom_components.ev_trip_planner.sensor import TripPlannerSensor
        from custom_components.ev_trip_planner.definitions import TripSensorEntityDescription

        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        desc = TripSensorEntityDescription(
            key="test_key",
            name="Test",
            icon="mdi:car",
            native_unit_of_measurement=None,
            state_class=None,
            value_fn=lambda data: data.get("test_key") if data else "default",
            attrs_fn=lambda data: {"test": "attr"} if data else {},
        )
        sensor = TripPlannerSensor(mock_coordinator, "test_vehicle", desc)

        assert sensor.native_value is None

    def test_extra_state_attributes_returns_empty_dict_when_coordinator_data_is_none(
        self,
    ):
        """extra_state_attributes returns {} when coordinator.data is None."""
        from custom_components.ev_trip_planner.sensor import TripPlannerSensor
        from custom_components.ev_trip_planner.definitions import TripSensorEntityDescription

        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        desc = TripSensorEntityDescription(
            key="test_key",
            name="Test",
            icon="mdi:car",
            native_unit_of_measurement=None,
            state_class=None,
            value_fn=lambda data: data.get("test_key") if data else "default",
            attrs_fn=lambda data: {"test": "attr"} if data else {},
        )
        sensor = TripPlannerSensor(mock_coordinator, "test_vehicle", desc)

        assert sensor.extra_state_attributes == {}


# =============================================================================
# sensor.py - EmhassDeferrableLoadSensor tests
# =============================================================================

class TestEmhassDeferrableLoadSensor:
    """Tests for EmhassDeferrableLoadSensor."""

    def test_native_value_returns_unknown_when_coordinator_data_is_none(self):
        """native_value returns 'unknown' when coordinator.data is None."""
        from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        sensor = EmhassDeferrableLoadSensor(mock_coordinator, "entry_123")
        assert sensor.native_value == "unknown"

    def test_extra_state_attributes_returns_empty_when_coordinator_data_is_none(self):
        """extra_state_attributes returns {} when coordinator.data is None."""
        from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        sensor = EmhassDeferrableLoadSensor(mock_coordinator, "entry_123")
        assert sensor.extra_state_attributes == {}

    def test_native_value_returns_status_from_coordinator_data(self):
        """native_value returns emhass_status from coordinator.data."""
        from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "emhass_status": "ready",
            "emhass_power_profile": [100, 200],
            "emhass_deferrables_schedule": {"foo": "bar"},
        }

        sensor = EmhassDeferrableLoadSensor(mock_coordinator, "entry_123")
        assert sensor.native_value == "ready"

    def test_extra_state_attributes_returns_all_emhass_fields(self):
        """extra_state_attributes returns all EMHASS fields from coordinator.data."""
        from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "emhass_status": "computing",
            "emhass_power_profile": [1, 2, 3],
            "emhass_deferrables_schedule": {"a": 1},
        }

        sensor = EmhassDeferrableLoadSensor(mock_coordinator, "entry_123")
        attrs = sensor.extra_state_attributes
        assert attrs["emhass_status"] == "computing"
        assert attrs["power_profile_watts"] == [1, 2, 3]
        assert attrs["deferrables_schedule"] == {"a": 1}

    def test_device_info_uses_vehicle_id_from_coordinator(self):
        """device_info uses vehicle_id from coordinator when available."""
        from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = {}
        mock_coordinator.vehicle_id = "coordinator_vehicle"

        sensor = EmhassDeferrableLoadSensor(mock_coordinator, "entry_123")
        info = sensor.device_info
        assert "EV Trip Planner coordinator_vehicle" in info["name"]


# =============================================================================
# sensor.py - TripSensor tests
# =============================================================================

class TestTripSensor:
    """Tests for TripSensor."""

    def test_get_trip_data_returns_empty_dict_when_coordinator_data_is_none(self):
        """_get_trip_data returns {} when coordinator.data is None."""
        from custom_components.ev_trip_planner.sensor import TripSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        sensor = TripSensor(mock_coordinator, "vehicle_1", "trip_1")
        result = sensor._get_trip_data()
        assert result == {}

    def test_get_trip_data_returns_empty_dict_when_trip_not_found(self):
        """_get_trip_data returns {} when trip not in recurring or punctual."""
        from custom_components.ev_trip_planner.sensor import TripSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": {},
            "punctual_trips": {},
        }

        sensor = TripSensor(mock_coordinator, "vehicle_1", "nonexistent_trip")
        result = sensor._get_trip_data()
        assert result == {}

    def test_get_trip_data_finds_trip_in_recurring(self):
        """_get_trip_data finds trip in recurring_trips."""
        from custom_components.ev_trip_planner.sensor import TripSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": {"rec_1": {"id": "rec_1", "tipo": "recurrente"}},
            "punctual_trips": {},
        }

        sensor = TripSensor(mock_coordinator, "vehicle_1", "rec_1")
        result = sensor._get_trip_data()
        assert result == {"id": "rec_1", "tipo": "recurrente"}

    def test_get_trip_data_finds_trip_in_punctual(self):
        """_get_trip_data finds trip in punctual_trips."""
        from custom_components.ev_trip_planner.sensor import TripSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": {},
            "punctual_trips": {"pun_1": {"id": "pun_1", "tipo": "puntual"}},
        }

        sensor = TripSensor(mock_coordinator, "vehicle_1", "pun_1")
        result = sensor._get_trip_data()
        assert result == {"id": "pun_1", "tipo": "puntual"}

    def test_native_value_returns_none_for_missing_trip(self):
        """native_value returns None when trip not found."""
        from custom_components.ev_trip_planner.sensor import TripSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": {},
            "punctual_trips": {},
        }

        sensor = TripSensor(mock_coordinator, "vehicle_1", "nonexistent")
        assert sensor.native_value is None

    def test_native_value_returns_recurrente_for_recurring_trip(self):
        """native_value returns 'recurrente' for recurring trip type."""
        from custom_components.ev_trip_planner.sensor import TripSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": {
                "rec_1": {"id": "rec_1", "tipo": "recurrente", "estado": "activo"}
            },
            "punctual_trips": {},
        }

        sensor = TripSensor(mock_coordinator, "vehicle_1", "rec_1")
        assert sensor.native_value == "recurrente"

    def test_native_value_returns_estado_for_punctual_trip(self):
        """native_value returns estado for punctual trip."""
        from custom_components.ev_trip_planner.sensor import TripSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": {},
            "punctual_trips": {
                "pun_1": {"id": "pun_1", "tipo": "puntual", "estado": "pendiente"}
            },
        }

        sensor = TripSensor(mock_coordinator, "vehicle_1", "pun_1")
        assert sensor.native_value == "pendiente"

    def test_extra_state_attributes_returns_empty_for_missing_trip(self):
        """extra_state_attributes returns {} when trip not found."""
        from custom_components.ev_trip_planner.sensor import TripSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": {},
            "punctual_trips": {},
        }

        sensor = TripSensor(mock_coordinator, "vehicle_1", "nonexistent")
        assert sensor.extra_state_attributes == {}

    def test_extra_state_attributes_returns_trip_data(self):
        """extra_state_attributes returns all trip fields."""
        from custom_components.ev_trip_planner.sensor import TripSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": {},
            "punctual_trips": {
                "pun_1": {
                    "id": "pun_1",
                    "tipo": "puntual",
                    "descripcion": "Test trip",
                    "km": 100.0,
                    "kwh": 15.0,
                    "datetime": "2025-01-15T10:00:00",
                    "activo": True,
                    "estado": "pendiente",
                }
            },
        }

        sensor = TripSensor(mock_coordinator, "vehicle_1", "pun_1")
        attrs = sensor.extra_state_attributes
        assert attrs["trip_id"] == "pun_1"
        assert attrs["trip_type"] == "puntual"
        assert attrs["descripcion"] == "Test trip"
        assert attrs["km"] == 100.0
        assert attrs["kwh"] == 15.0
        assert attrs["estado"] == "pendiente"


# =============================================================================
# services.py - _find_entry_by_vehicle edge cases
# =============================================================================

class TestFindEntryByVehicle:
    """Tests for _find_entry_by_vehicle helper."""

    def test_returns_none_when_no_entries_match(self):
        """Returns None when no config entries match the vehicle_id."""
        from custom_components.ev_trip_planner.services import _find_entry_by_vehicle

        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_entry.data = {"vehicle_name": "Chispitas"}
        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

        result = _find_entry_by_vehicle(mock_hass, "nonexistent_vehicle")
        assert result is None

    def test_returns_none_when_entry_data_is_none(self):
        """Returns None when an entry has None data (skipped)."""
        from custom_components.ev_trip_planner.services import _find_entry_by_vehicle

        mock_hass = MagicMock()
        mock_entry1 = MagicMock()
        mock_entry1.data = None
        mock_entry2 = MagicMock()
        mock_entry2.data = {"vehicle_name": "Chispitas"}
        mock_hass.config_entries.async_entries = MagicMock(
            return_value=[mock_entry1, mock_entry2]
        )

        result = _find_entry_by_vehicle(mock_hass, "chispitas")
        assert result == mock_entry2

    def test_returns_none_when_entry_data_missing_vehicle_name(self):
        """Returns None when entry has no vehicle_name key."""
        from custom_components.ev_trip_planner.services import _find_entry_by_vehicle

        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_entry.data = {}
        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

        result = _find_entry_by_vehicle(mock_hass, "some_vehicle")
        assert result is None

    def test_case_insensitive_match_with_spaces(self):
        """Match is case-insensitive and handles spaces in vehicle name."""
        from custom_components.ev_trip_planner.services import _find_entry_by_vehicle

        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_entry.data = {"vehicle_name": "Test Vehicle"}
        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

        # Should match "test_vehicle" -> "test vehicle" -> "Test Vehicle"
        result = _find_entry_by_vehicle(mock_hass, "test_vehicle")
        assert result == mock_entry


# =============================================================================
# services.py - _get_manager error paths
# =============================================================================

class TestGetManager:
    """Tests for _get_manager helper."""

    def test_raises_when_entry_not_found(self):
        """Raises ValueError when no config entry exists for vehicle."""
        from custom_components.ev_trip_planner.services import _get_manager

        mock_hass = MagicMock()
        mock_hass.config_entries.async_entries = MagicMock(return_value=[])

        with pytest.raises(ValueError, match="not found in config entries"):
            _get_manager(mock_hass, "unknown_vehicle")
