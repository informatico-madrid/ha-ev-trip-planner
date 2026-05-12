"""Factory functions for creating test doubles with sensible defaults."""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

from tests.helpers.constants import (
    TEST_CONFIG,
    TEST_COORDINATOR_DATA,
    TEST_ENTRY_ID,
    TEST_TRIPS,
    TEST_VEHICLE_ID,
)


def create_mock_trip_manager(hass=None, vehicle_id: str = TEST_VEHICLE_ID) -> MagicMock:
    """Create a spec'd MagicMock for TripManager.

    AC-D1.2: Must use MagicMock(spec=TripManager) with async methods
    configured individually - NOT AsyncMock without spec.

    T048: Includes all async stubs (async_get_kwh_needed_today,
    async_get_hours_needed_today, async_get_next_trip) with defaults.
    """
    from custom_components.ev_trip_planner.trip import TripManager

    mock = MagicMock(spec=TripManager)
    mock.async_setup = AsyncMock(return_value=None)
    mock.async_get_recurring_trips = AsyncMock(return_value=TEST_TRIPS["recurring"])
    mock.async_get_punctual_trips = AsyncMock(return_value=TEST_TRIPS["punctual"])
    mock._get_all_trips = MagicMock(return_value=TEST_TRIPS)
    mock.async_add_recurring_trip = AsyncMock(return_value=None)
    mock.async_add_punctual_trip = AsyncMock(return_value=None)
    mock.async_save_trips = AsyncMock(return_value=None)
    mock.async_delete_trip = AsyncMock(return_value=None)
    mock.publish_deferrable_loads = AsyncMock(return_value=None)
    # T048: async stubs for deterministic datetime-based calculations
    mock.async_get_kwh_needed_today = AsyncMock(return_value=0.0)
    mock.async_get_hours_needed_today = AsyncMock(return_value=0.0)
    mock.async_get_next_trip = AsyncMock(return_value=None)
    # T048: seed attributes required by tests
    mock.hass = hass
    mock.vehicle_id = vehicle_id
    mock._emhass_adapter = None
    mock._trips = {}
    mock._recurring_trips = {}
    mock._punctual_trips = {}
    return mock


def create_mock_coordinator(hass=None, entry=None, trip_manager=None) -> MagicMock:
    """Create a spec'd MagicMock for TripPlannerCoordinator."""
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator

    mock = MagicMock(spec=TripPlannerCoordinator)
    mock.data = dict(TEST_COORDINATOR_DATA)
    mock.hass = hass
    mock._trip_manager = trip_manager or create_mock_trip_manager(hass)
    mock.async_config_entry_first_refresh = AsyncMock(return_value=None)
    return mock


def create_mock_ev_config_entry(
    hass=None, data: Dict[str, Any] = None, entry_id: str = TEST_ENTRY_ID
):
    """Create a MockConfigEntry for testing."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    config_entry = MockConfigEntry(
        entry_id=entry_id,
        domain="ev_trip_planner",
        data=data if data is not None else TEST_CONFIG,
        version=1,
    )
    if hass:
        config_entry.add_to_hass(hass)
    return config_entry


async def setup_mock_ev_config_entry(hass, config_entry=None, trip_manager=None):
    """Set up full mock integration entry with HA boundary patches INSIDE.

    AC-D1.5: Patches at HA boundary go inside this factory function,
    NOT in conftest.py Layer 3 directly.
    """
    from unittest.mock import patch

    config_entry = config_entry or create_mock_ev_config_entry(hass)
    manager = trip_manager or create_mock_trip_manager(hass)

    with patch(
        "custom_components.ev_trip_planner.TripManager",
        return_value=manager,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    return config_entry, manager
