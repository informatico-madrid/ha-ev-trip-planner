"""Coverage tests for sensor.py uncovered error paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSensorRestoreBranch:
    """Tests for sensor.py lines 94-99: restore branch when data is None."""

    @pytest.fixture
    def mock_coordinator_with_last_state(self):
        """Create a mock coordinator with None data and last state available."""
        coordinator = MagicMock()
        coordinator.data = None  # Simulates HA restart before first refresh
        return coordinator

    @pytest.mark.asyncio
    async def test_async_added_to_hass_restores_state_when_data_none(self, mock_coordinator_with_last_state):
        """When restore=True and coordinator.data is None, sensor should restore from last_state."""
        from custom_components.ev_trip_planner.definitions import (
            TripSensorEntityDescription,
        )
        from custom_components.ev_trip_planner.sensor import TripPlannerSensor

        # Create entity description with restore=True
        desc = TripSensorEntityDescription(
            key="test_restore_sensor",
            restore=True,
            value_fn=lambda data: data.get("kwh_today", 0.0) if data else 0.0,
            attrs_fn=lambda data: {},
        )

        # Create sensor
        sensor = TripPlannerSensor(
            coordinator=mock_coordinator_with_last_state,
            vehicle_id="test_vehicle",
            entity_description=desc,
        )

        # Mock async_get_last_state to return a state
        mock_last_state = MagicMock()
        mock_last_state.state = "42.5"

        with patch.object(sensor, "async_get_last_state", new_callable=AsyncMock, return_value=mock_last_state):
            await sensor.async_added_to_hass()

            # Verify _attr_native_value was restored
            assert sensor._attr_native_value == "42.5"

    @pytest.mark.asyncio
    async def test_async_added_to_hass_no_restore_when_last_state_none(self, mock_coordinator_with_last_state):
        """When restore=True but last_state is None, _attr_native_value should remain default."""
        from custom_components.ev_trip_planner.definitions import (
            TripSensorEntityDescription,
        )
        from custom_components.ev_trip_planner.sensor import TripPlannerSensor

        desc = TripSensorEntityDescription(
            key="test_restore_sensor",
            restore=True,
            value_fn=lambda data: data.get("kwh_today", 0.0) if data else 0.0,
            attrs_fn=lambda data: {},
        )

        sensor = TripPlannerSensor(
            coordinator=mock_coordinator_with_last_state,
            vehicle_id="test_vehicle",
            entity_description=desc,
        )

        with patch.object(sensor, "async_get_last_state", new_callable=AsyncMock, return_value=None):
            await sensor.async_added_to_hass()

            # _attr_native_value should remain as initial value (not set from None)
            assert sensor._attr_native_value is None or sensor._attr_native_value == 0.0


class TestSensorAsyncUpdateTripSensor:
    """Tests for sensor.py lines 532-543: async_update_trip_sensor branches."""

    @pytest.fixture
    def mock_hass_and_coordinator(self):
        """Create mock hass and coordinator."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.config_entries = MagicMock()
        coordinator = MagicMock()
        coordinator.data = None
        return hass, coordinator

    @pytest.mark.asyncio
    async def test_async_update_trip_sensor_punctual(self, mock_hass_and_coordinator):
        """async_update_trip_sensor with punctual trip finds existing entity and returns True."""
        from custom_components.ev_trip_planner.sensor import async_update_trip_sensor

        hass, coordinator = mock_hass_and_coordinator

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.runtime_data = MagicMock()
        mock_entry.runtime_data.coordinator = coordinator
        mock_entry.runtime_data.trip_manager = MagicMock()

        mock_reg_entry = MagicMock()
        mock_reg_entry.unique_id = "test_vehicle_trip_pun_123"
        mock_reg_entry.entity_id = "sensor.test_vehicle_punctual_trip"

        # hass.entity_registry is tried first
        mock_registry = MagicMock()
        mock_registry.async_entries_for_config_entry = MagicMock(
            return_value=[mock_reg_entry]
        )
        hass.entity_registry = mock_registry

        trip_data = {
            "id": "pun_123",
            "type": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "km": 110.0,
            "kwh": 16.5,
            "descripcion": "Viaje",
        }
        result = await async_update_trip_sensor(hass, "test_entry", trip_data)

        assert result is True
        mock_registry.async_entries_for_config_entry.assert_called_with("test_entry")

    @pytest.mark.asyncio
    async def test_async_update_trip_sensor_recurring(self, mock_hass_and_coordinator):
        """async_update_trip_sensor with recurring trip finds existing entity and returns True."""
        from custom_components.ev_trip_planner.sensor import async_update_trip_sensor

        hass, coordinator = mock_hass_and_coordinator

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.runtime_data = MagicMock()
        mock_entry.runtime_data.coordinator = coordinator
        mock_entry.runtime_data.trip_manager = MagicMock()

        mock_reg_entry = MagicMock()
        mock_reg_entry.unique_id = "test_vehicle_trip_rec_lun_abc"
        mock_reg_entry.entity_id = "sensor.test_vehicle_recurring_trip"

        mock_registry = MagicMock()
        mock_registry.async_entries_for_config_entry = MagicMock(
            return_value=[mock_reg_entry]
        )
        hass.entity_registry = mock_registry

        trip_data = {
            "id": "rec_lun_abc",
            "type": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 25.0,
            "kwh": 3.75,
            "descripcion": "Trabajo",
        }
        result = await async_update_trip_sensor(hass, "test_entry", trip_data)

        assert result is True
        mock_registry.async_entries_for_config_entry.assert_called_with("test_entry")
