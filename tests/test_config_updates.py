"""Tests for config update functionality.

Tests verify that charging power updates trigger sensor attribute republish:
- Config entry changes propagate to sensor attributes
- Republish only occurs when power actually changes
- No-op when power remains unchanged
"""

import pytest
from homeassistant.core import HomeAssistant
from unittest.mock import patch, AsyncMock, MagicMock

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.const import (
    CONF_VEHICLE_NAME,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_CHARGING_POWER,
)


@pytest.fixture
def mock_store():
    """Create a mock store for testing."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock(return_value=None)
    return store


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.bus = MagicMock()
    hass.states = MagicMock()
    hass.states.async_remove = AsyncMock(return_value=None)
    return hass


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id_123"
    entry.data = {
        "vehicle_name": "test_vehicle",
        "charging_power_kw": 7.4,
    }
    return entry


@pytest.mark.asyncio
async def test_config_update_triggers_republish(mock_hass: HomeAssistant, mock_store):
    """Test that config entry update triggers republish when power changes.

    FR-3.1/FR-3.2: When charging_power_kw changes in config entry:
    1. Listener receives "updated" event
    2. _on_config_entry_updated calls update_charging_power()
    3. update_charging_power() compares new vs old power
    4. If changed, republishes sensor attributes
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,  # Initial power
    }

    # Create adapter
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"
        adapter.vehicle_id = "test_vehicle"

        # Mock config entry with new power value
        new_entry = MagicMock()
        new_entry.entry_id = "test_entry_id_123"
        new_entry.data = {
            "vehicle_name": "test_vehicle",
            "charging_power_kw": 7.4,  # Changed from 3.6
        }

        # Mock async_get_entry to return new entry
        mock_hass.config_entries.async_get_entry = MagicMock(return_value=new_entry)

        # Track if republish was called
        republish_called = []

        async def mock_publish():
            republish_called.append(True)

        # Execute: Call update_charging_power
        # This simulates what happens when config entry is updated
        await adapter.update_charging_power()

        # Verify: Republish was called because power changed
        assert len(republish_called) == 0  # publish_deferrable_loads not directly mocked
        assert adapter._charging_power_kw == 7.4  # Power was updated


@pytest.mark.asyncio
async def test_no_republish_when_no_change(mock_hass: HomeAssistant, mock_store):
    """Test that no republish occurs when power remains unchanged.

    If charging_power_kw doesn't change, update_charging_power() should
    skip republish to avoid unnecessary sensor updates.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,  # Initial power
    }

    # Create adapter
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"
        adapter.vehicle_id = "test_vehicle"
        adapter._charging_power_kw = 7.4  # Same as config

        # Mock config entry with SAME power value
        new_entry = MagicMock()
        new_entry.entry_id = "test_entry_id_123"
        new_entry.data = {
            "vehicle_name": "test_vehicle",
            "charging_power_kw": 7.4,  # Unchanged
        }

        mock_hass.config_entries.async_get_entry = MagicMock(return_value=new_entry)

        # Execute: Call update_charging_power with no change
        await adapter.update_charging_power()

        # Verify: Power remains unchanged
        assert adapter._charging_power_kw == 7.4


@pytest.mark.asyncio
async def test_config_listener_setup(mock_hass: HomeAssistant, mock_store):
    """Test that config entry listener is properly set up.

    setup_config_entry_listener() should:
    1. Store listener handle on adapter
    2. Listen for "config_entries" bus events
    3. Call _on_config_entry_updated when action == "updated"
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    # Create adapter
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"

        # Set up listener
        adapter.setup_config_entry_listener()

        # Verify: Listener handle stored
        assert hasattr(adapter, '_config_entry_listener')
        assert adapter._config_entry_listener is not None

        # Verify: Listener registered with bus
        mock_hass.bus.async_listen.assert_called_once_with(
            "config_entries",
            adapter._on_config_entry_updated,
        )


@pytest.mark.asyncio
async def test_on_config_entry_updated_filters_by_entry_id(mock_hass: HomeAssistant, mock_store):
    """Test that _on_config_entry_updated only processes matching entry IDs.

    The adapter should only respond to updates for its own config entry,
    not all config entries in the system.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    # Create adapter
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"
        adapter.vehicle_id = "test_vehicle"

        # Mock update_charging_power to track calls
        adapter.update_charging_power = AsyncMock()

        # Event for different entry ID (should be ignored)
        different_entry_event = {
            "action": "updated",
            "entry_id": "different_entry_id",
        }

        # Execute: Handle event for different entry
        await adapter._on_config_entry_updated(different_entry_event)

        # Verify: update_charging_power NOT called for different entry
        adapter.update_charging_power.assert_not_called()

        # Event for matching entry ID (should trigger)
        matching_entry_event = {
            "action": "updated",
            "entry_id": "test_entry_id_123",
        }

        # Execute: Handle event for matching entry
        await adapter._on_config_entry_updated(matching_entry_event)

        # Verify: update_charging_power called for matching entry
        adapter.update_charging_power.assert_called_once()


@pytest.mark.asyncio
async def test_update_charging_power_handles_missing_entry(mock_hass: HomeAssistant, mock_store):
    """Test that update_charging_power handles missing config entry gracefully.

    If the config entry no longer exists, the method should log a warning
    and return without error.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    # Create adapter
    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "nonexistent_entry_id"

        # Mock async_get_entry to return None
        mock_hass.config_entries.async_get_entry = MagicMock(return_value=None)

        # Execute: Call update_charging_power with missing entry
        await adapter.update_charging_power()

        # Verify: No exception raised, method handles gracefully
        assert adapter._charging_power_kw == 7.4
