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
def enable_custom_integrations():
    """Enable custom integrations for testing."""
    return True


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

        # Mock publish_deferrable_loads to avoid needing real trips
        adapter.publish_deferrable_loads = AsyncMock(return_value=True)

        # Execute: Call update_charging_power
        # This simulates what happens when config entry is updated
        await adapter.update_charging_power()

        # Verify: Power was updated
        assert adapter._charging_power_kw == 7.4  # Power was updated
        # Verify: publish_deferrable_loads was called because power changed
        adapter.publish_deferrable_loads.assert_called_once()


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

        # Mock publish_deferrable_loads to track calls
        adapter.publish_deferrable_loads = AsyncMock()

        # Execute: Call update_charging_power with no change
        await adapter.update_charging_power()

        # Verify: Power remains unchanged
        assert adapter._charging_power_kw == 7.4
        # Verify: publish_deferrable_loads NOT called because power unchanged
        adapter.publish_deferrable_loads.assert_not_called()


@pytest.mark.asyncio
async def test_config_listener_setup(mock_hass: HomeAssistant, mock_store):
    """Test that config entry listener is properly set up.

    setup_config_entry_listener() should:
    1. Retrieve config_entry via async_get_entry
    2. Store listener handle on adapter via config_entry.add_update_listener
    3. Register _handle_config_entry_update callback
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    # Create mock unsubscribe function
    mock_unsubscribe = MagicMock()

    # Create mock config entry
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_id_123"
    mock_entry.data = config
    mock_entry.async_on_unload = MagicMock(return_value=mock_unsubscribe)
    mock_entry.add_update_listener = MagicMock(return_value=mock_unsubscribe)

    with patch('custom_components.ev_trip_planner.emhass_adapter.Store', return_value=mock_store):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"

        # Mock async_get_entry to return our mock_entry
        mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Set up listener
        adapter.setup_config_entry_listener()

        # Verify: Listener handle stored (returned by async_on_unload)
        assert hasattr(adapter, '_config_entry_listener')
        assert adapter._config_entry_listener is mock_unsubscribe

        # Verify: async_get_entry was called with entry_id
        mock_hass.config_entries.async_get_entry.assert_called_once_with("test_entry_id_123")

        # Verify: add_update_listener was called with the handler
        mock_entry.add_update_listener.assert_called_once()


@pytest.mark.asyncio
async def test_handle_config_entry_update_triggers_republish(mock_hass: HomeAssistant, mock_store):
    """Test that _handle_config_entry_update calls update_charging_power.

    The new pattern uses ConfigEntry.add_update_listener which passes
    (hass, config_entry) to the handler, so no entry_id filtering is needed.
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

        # Create mock config entry (passed by HA's add_update_listener)
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id_123"

        # Execute: Handle config entry update
        await adapter._handle_config_entry_update(mock_hass, mock_entry)

        # Verify: update_charging_power was called
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
