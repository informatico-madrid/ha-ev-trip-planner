"""Tests for sensor.py device_info and edge cases.

Covers uncovered lines in sensor.py device_info properties,
async_setup_entry error paths, and helper function edge cases.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


# =============================================================================
# sensor.py - device_info for different sensor types
# =============================================================================

class TestSensorDeviceInfo:
    """Tests for device_info properties on different sensor types."""

    def test_trip_planner_sensor_device_info(self):
        """TripPlannerSensor.device_info returns correct device info."""
        from custom_components.ev_trip_planner.sensor import TripPlannerSensor
        from custom_components.ev_trip_planner.definitions import TripSensorEntityDescription

        mock_coordinator = MagicMock()
        mock_coordinator.data = {"some_key": "value"}

        desc = TripSensorEntityDescription(
            key="test_key",
            name="Test Sensor",
            icon="mdi:car",
            native_unit_of_measurement=None,
            state_class=None,
            value_fn=lambda data: data.get("test_key") if data else None,
            attrs_fn=lambda data: {},
        )
        sensor = TripPlannerSensor(mock_coordinator, "my_vehicle", desc)

        device_info = sensor.device_info

        assert device_info["identifiers"] == {("ev_trip_planner", "my_vehicle")}
        assert "EV Trip Planner my_vehicle" in device_info["name"]
        assert device_info["manufacturer"] == "Home Assistant"
        assert device_info["model"] == "EV Trip Planner"

    def test_emhass_deferrable_load_sensor_device_info(self):
        """EmhassDeferrableLoadSensor.device_info uses entry_id for identifiers."""
        from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = {"emhass_status": "ready"}
        mock_coordinator.vehicle_id = "coordinator_vehicle"

        sensor = EmhassDeferrableLoadSensor(mock_coordinator, "entry_abc")

        device_info = sensor.device_info

        # identifiers use entry_id
        assert ("ev_trip_planner", "entry_abc") in device_info["identifiers"]
        # name uses vehicle_id from coordinator
        assert "EV Trip Planner coordinator_vehicle" in device_info["name"]

    def test_trip_sensor_device_info(self):
        """TripSensor.device_info includes both vehicle_id and trip_id."""
        from custom_components.ev_trip_planner.sensor import TripSensor

        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "recurring_trips": {},
            "punctual_trips": {
                "pun_1": {"id": "pun_1", "tipo": "puntual", "estado": "pendiente"}
            },
        }

        sensor = TripSensor(mock_coordinator, "vehicle_x", "pun_1")

        device_info = sensor.device_info

        assert ("ev_trip_planner", "vehicle_x_pun_1") in device_info["identifiers"]
        assert "Trip pun_1" in device_info["name"]
        assert device_info["via_device"] == ("ev_trip_planner", "vehicle_x")


# =============================================================================
# sensor.py - async_create_trip_sensor edge cases
# =============================================================================

class TestAsyncCreateTripSensor:
    """Tests for async_create_trip_sensor edge cases."""

    @pytest.mark.asyncio
    async def test_async_create_trip_sensor_with_punctual_trip(self):
        """Creates sensor for punctual trip."""
        from custom_components.ev_trip_planner.sensor import async_create_trip_sensor

        mock_hass = MagicMock()
        mock_add_entities = MagicMock()

        trip_data = {
            "id": "pun_123",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "km": 100.0,
            "kwh": 15.0,
            "descripcion": "Test",
            "estado": "pendiente",
        }

        # Should not raise
        await async_create_trip_sensor(
            mock_hass, "entry_xyz", trip_data, mock_add_entities
        )

    @pytest.mark.asyncio
    async def test_async_create_trip_sensor_with_recurring_trip(self):
        """Creates sensor for recurring trip."""
        from custom_components.ev_trip_planner.sensor import async_create_trip_sensor

        mock_hass = MagicMock()
        mock_add_entities = MagicMock()

        trip_data = {
            "id": "rec_lun_456",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
            "kwh": 3.6,
            "descripcion": "Trabajo",
            "activo": True,
        }

        await async_create_trip_sensor(
            mock_hass, "entry_xyz", trip_data, mock_add_entities
        )


# =============================================================================
# sensor.py - TripPlannerSensor native_value edge cases
# =============================================================================

class TestTripPlannerSensorNativeValue:
    """Tests for TripPlannerSensor.native_value edge cases."""

    def test_native_value_with_data(self):
        """native_value returns value from data when coordinator.data is present."""
        from custom_components.ev_trip_planner.sensor import TripPlannerSensor
        from custom_components.ev_trip_planner.definitions import TripSensorEntityDescription

        mock_coordinator = MagicMock()
        mock_coordinator.data = {"next_trip": {"id": "trip_next", "tipo": "puntual"}}

        desc = TripSensorEntityDescription(
            key="next_trip_type",
            name="Next Trip Type",
            icon="mdi:car",
            native_unit_of_measurement=None,
            state_class=None,
            value_fn=lambda data: (data.get("next_trip") or {}).get("tipo") if data else None,
            attrs_fn=lambda data: {},
        )
        sensor = TripPlannerSensor(mock_coordinator, "vehicle_1", desc)

        assert sensor.native_value == "puntual"

    def test_native_value_with_empty_data(self):
        """native_value handles empty data gracefully."""
        from custom_components.ev_trip_planner.sensor import TripPlannerSensor
        from custom_components.ev_trip_planner.definitions import TripSensorEntityDescription

        mock_coordinator = MagicMock()
        mock_coordinator.data = {}

        desc = TripSensorEntityDescription(
            key="next_trip_type",
            name="Next Trip Type",
            icon="mdi:car",
            native_unit_of_measurement=None,
            state_class=None,
            value_fn=lambda data: (data.get("next_trip") or {}).get("tipo") if data else "no_trip",
            attrs_fn=lambda data: {},
        )
        sensor = TripPlannerSensor(mock_coordinator, "vehicle_1", desc)

        assert sensor.native_value == "no_trip"


# =============================================================================
# sensor.py - async_setup_entry error handling
# =============================================================================

class TestAsyncSetupEntryErrorHandling:
    """Tests for async_setup_entry error handling."""

    @pytest.mark.asyncio
    async def test_setup_entry_without_trip_manager_returns_false(self):
        """async_setup_entry returns False when trip_manager is missing."""
        from custom_components.ev_trip_planner.sensor import async_setup_entry
        from unittest.mock import PropertyMock

        mock_hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_no_manager"
        mock_entry.data = {"vehicle_name": "Test Vehicle"}

        # runtime_data with no trip_manager
        mock_runtime_data = MagicMock()
        type(mock_runtime_data).trip_manager = PropertyMock(return_value=None)
        type(mock_runtime_data).coordinator = PropertyMock(return_value=MagicMock())
        mock_entry.runtime_data = mock_runtime_data

        result = await async_setup_entry(mock_hass, mock_entry, MagicMock())

        assert result is False


# =============================================================================
# sensor.py - _async_create_trip_sensors edge cases
# =============================================================================

class TestAsyncCreateTripSensors:
    """Tests for _async_create_trip_sensors helper."""

    @pytest.mark.asyncio
    async def test_create_trip_sensors_empty_recurring(self):
        """Handles empty recurring_trips dict."""
        from custom_components.ev_trip_planner.sensor import _async_create_trip_sensors

        mock_hass = MagicMock()
        mock_trip_manager = MagicMock()
        mock_trip_manager._recurring_trips = {}
        mock_trip_manager._punctual_trips = {}

        result = await _async_create_trip_sensors(
            mock_hass, mock_trip_manager, "vehicle_test", "entry_test"
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_create_trip_sensors_with_recurring_trips(self):
        """Creates sensors for recurring trips."""
        from custom_components.ev_trip_planner.sensor import _async_create_trip_sensors

        mock_hass = MagicMock()
        mock_trip_manager = MagicMock()
        mock_trip_manager._recurring_trips = {
            "rec_1": {"id": "rec_1", "tipo": "recurrente", "dia_semana": "lunes"}
        }
        mock_trip_manager._punctual_trips = {}

        result = await _async_create_trip_sensors(
            mock_hass, mock_trip_manager, "vehicle_test", "entry_test"
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_create_trip_sensors_with_punctual_trips(self):
        """Creates sensors for punctual trips."""
        from custom_components.ev_trip_planner.sensor import _async_create_trip_sensors

        mock_hass = MagicMock()
        mock_trip_manager = MagicMock()
        mock_trip_manager._recurring_trips = {}
        mock_trip_manager._punctual_trips = {
            "pun_1": {"id": "pun_1", "tipo": "puntual", "estado": "pendiente"}
        }

        result = await _async_create_trip_sensors(
            mock_hass, mock_trip_manager, "vehicle_test", "entry_test"
        )

        assert len(result) == 1
