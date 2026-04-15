"""TDD: ConfigEntryNotReady properly propagates from async_setup_entry.

Test: Verifies that when coordinator.async_config_entry_first_refresh()
raises ConfigEntryNotReady, the exception propagates to the caller in
async_setup_entry (not caught/swallowed).

Currently FAILS because ConfigEntryNotReady may be caught or not properly re-raised.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryNotReady, ConfigEntryState


class FakeEntry:
    """Minimal ConfigEntry substitute for testing."""

    def __init__(self, entry_id: str, data: dict[str, Any]) -> None:
        self.entry_id = entry_id
        self.data = data
        self.version = 1
        self.minor_version = 1
        self.state = ConfigEntryState.SETUP_IN_PROGRESS

        class FakeRuntimeData:
            def __init__(self):
                self.trip_manager = None
                self.coordinator = None
                self.sensor_async_add_entities = None
        self.runtime_data = FakeRuntimeData()

    @property
    def unique_id(self) -> str:
        return self.entry_id


@pytest.mark.asyncio
async def test_config_entry_not_ready_propagates_from_async_setup_entry():
    """ConfigEntryNotReady from first refresh should propagate from async_setup_entry.

    This test FAILS in RED state because async_setup_entry may catch
    ConfigEntryNotReady and not properly re-raise it.
    """
    from custom_components.ev_trip_planner import async_setup_entry

    # Create mock hass
    mock_hass = MagicMock()
    mock_hass.config_entries = MagicMock()
    mock_hass.data = {}

    # Create entry with SETUP_IN_PROGRESS state
    entry = FakeEntry(
        entry_id="test_entry",
        data={"vehicle_name": "TestVehicle"},
    )

    # Create mock trip_manager
    mock_trip_manager = MagicMock()
    mock_trip_manager.async_get_recurring_trips = AsyncMock(return_value=[])
    mock_trip_manager.async_get_punctual_trips = AsyncMock(return_value=[])
    mock_trip_manager.async_get_kwh_needed_today = AsyncMock(return_value=0.0)
    mock_trip_manager.async_get_hours_needed_today = AsyncMock(return_value=0)
    mock_trip_manager.async_get_next_trip = AsyncMock(return_value=None)
    mock_trip_manager.async_setup = AsyncMock()

    # Create a mock coordinator that raises ConfigEntryNotReady
    mock_coordinator = MagicMock()
    mock_coordinator.async_config_entry_first_refresh = AsyncMock(
        side_effect=ConfigEntryNotReady("First refresh failed")
    )
    mock_coordinator.async_refresh = AsyncMock()

    # Patch TripPlannerCoordinator class to return our mock coordinator
    with patch(
        'custom_components.ev_trip_planner.TripPlannerCoordinator',
        return_value=mock_coordinator
    ):
        # Set up runtime_data with the failing coordinator
        entry.runtime_data.coordinator = mock_coordinator
        entry.runtime_data.trip_manager = mock_trip_manager

        # EXPECTED: ConfigEntryNotReady should propagate from async_setup_entry
        # ACTUAL (RED): ConfigEntryNotReady may be caught and not re-raised
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(mock_hass, entry)
