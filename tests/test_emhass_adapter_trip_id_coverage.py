"""Test for line 697 coverage: trip with falsy id in async_publish_all_deferrable_loads."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.const import (
    CONF_VEHICLE_NAME, CONF_MAX_DEFERRABLE_LOADS, CONF_CHARGING_POWER,
)


class MockConfigEntry:
    def __init__(self, vehicle_name, config):
        self.entry_id = f"{vehicle_name}_entry"
        self.domain = "ev_trip_planner"
        self.title = vehicle_name
        self.state = "loaded"
        self.data = config
        self.runtime_data = None


class MockRuntimeData:
    def __init__(self, coordinator):
        self.coordinator = coordinator


@pytest.fixture
def mock_coordinator():
    """Create a mock TripPlannerCoordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "recurring_trips": {},
        "punctual_trips": {},
        "kwh_today": 0.0,
        "hours_today": 0.0,
    }
    coordinator.async_refresh = AsyncMock()
    return coordinator


@pytest.mark.asyncio
async def test_async_publish_all_deferrable_loads_skips_trip_with_falsy_id(hass, mock_store, mock_coordinator):
    """Test that async_publish_all_deferrable_loads skips trips with falsy id (line 697).

    Line 697: `if not trip_id: continue` - should skip trips where trip_id is None,
    empty string, or other falsy values.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    entry = MockConfigEntry("test_vehicle", config)
    entry.runtime_data = MockRuntimeData(coordinator=mock_coordinator)

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

        adapter._charging_power_kw = 7.4

        trips = [
            {"id": None, "descripcion": "Trip with None ID", "kwh": 5.0, "hora": "09:00"},  # line 697
            {"id": "", "descripcion": "Trip with empty ID", "kwh": 5.0, "hora": "10:00"},   # line 697
            {"id": "valid_trip", "descripcion": "Valid trip", "kwh": 5.0, "hora": "11:00"},  # valid
        ]

        hass.states.async_set = AsyncMock()
        hass.states.async_get = MagicMock(return_value=MagicMock(state="50"))

        result = await adapter.async_publish_all_deferrable_loads(trips)

        # Should still return True (or partial success) since valid_trip was processed
        # The function should not raise, just skip the falsy id trips
        assert "valid_trip" in adapter._cached_per_trip_params


@pytest.mark.asyncio
async def test_async_publish_all_deferrable_loads_skips_trip_with_no_id_field(hass, mock_store, mock_coordinator):
    """Test that async_publish_all_deferrable_loads skips trips without id field (line 697).

    Line 697: `if not trip_id: continue` - should skip trips where trip.get("id") returns None.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    entry = MockConfigEntry("test_vehicle", config)
    entry.runtime_data = MockRuntimeData(coordinator=mock_coordinator)

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

        adapter._charging_power_kw = 7.4

        trips = [
            {"descripcion": "Trip without ID field", "kwh": 5.0, "hora": "09:00"},  # line 697
            {"id": "valid_trip", "descripcion": "Valid trip", "kwh": 5.0, "hora": "11:00"},  # valid
        ]

        hass.states.async_set = AsyncMock()
        hass.states.async_get = MagicMock(return_value=MagicMock(state="50"))

        result = await adapter.async_publish_all_deferrable_loads(trips)

        # The function should not raise, just skip the trip without id
        assert "valid_trip" in adapter._cached_per_trip_params
