"""Tests for TripEmhassSensor class."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_VEHICLE_NAME,
)
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter


@pytest.mark.asyncio
async def test_trip_emhass_sensor_native_value(mock_store, hass: HomeAssistant):
    """TripEmhassSensor.native_value returns emhass_index from per_trip_emhass_params.

    This is the RED test for task 1.23:
    - Create stub coordinator.data with per_trip_emhass_params
    - Trip has emhass_index=2
    - Sensor.native_value should return 2
    - Current: TripEmhassSensor class does not exist yet
    - Test must FAIL to confirm the feature doesn't exist
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Mock coordinator.async_refresh
        mock_coordinator = MagicMock()
        mock_coordinator.async_refresh = AsyncMock()
        adapter._get_coordinator = MagicMock(return_value=mock_coordinator)

        # Mock async_publish_deferrable_load
        adapter.async_publish_deferrable_load = AsyncMock(return_value=True)

        # Mock _update_error_status
        adapter._update_error_status = MagicMock()

        # Mock _index_map
        adapter._index_map = {"trip_001": 2}

        # Publish the trip
        trip = {
            "trip_id": "trip_001",
            "kwh": 7.4,
            "hora": "09:00",
            "datetime": datetime(2026, 4, 11, 20, 0, 0).isoformat(),
        }
        await adapter.publish_deferrable_loads([trip])

        # Get cached results (this is what coordinator.data will have)
        cached_results = adapter.get_cached_optimization_results()

        # Create mock coordinator with this data
        mock_coordinator = MagicMock()
        mock_coordinator.data = cached_results

        # Import and create the sensor (this should fail because class doesn't exist)
        from custom_components.ev_trip_planner.sensor import TripEmhassSensor

        sensor = TripEmhassSensor(mock_coordinator, "test_vehicle", "trip_001")

        # This should return the emhass_index from per_trip_emhass_params
        assert sensor.native_value == 2, (
            f"Sensor native_value should be emhass_index=2, got {sensor.native_value}"
        )
