"""Integration test to confirm charging_power_kw bug.

BUG: When user changes charging_power_kw via Options flow, the new value
should propagate to the EMHASS sensor's power_profile_watts. Currently,
the sensor shows [11000] (11kW DEFAULT) instead of [3400] (3.4kW configured).

FLOW:
1. User changes options.charging_power_kw to 3.4 via Options flow
2. _handle_config_entry_update() updates adapter._charging_power_kw = 3.4
3. adapter.async_publish_deferrable_load() uses self._charging_power_kw for cache
4. BUT LoadPublisher.charging_power_kw is set at __init__ and NEVER updated
5. LoadPublisher.publish() uses self.charging_power_kw (11.0 default, not 3.4)

EXPECTED: power_profile_watts shows 3400W (3.4kW)
ACTUAL: power_profile_watts shows 11000W (11kW)
"""

import logging
from unittest.mock import MagicMock

import pytest

from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter


class MockConfigEntry:
    """Mock ConfigEntry for testing."""
    
    def __init__(self, entry_id="test_vehicle"):
        self.entry_id = entry_id
        self.data = {"vehicle_name": "test_vehicle"}
        self.options = {}


class MockHass:
    """Mock HomeAssistant for testing."""
    
    def __init__(self):
        self.states = MagicMock()
        self.config_entries = MagicMock()
        self.services = MagicMock()
        self.logger = logging.getLogger("test")


@pytest.fixture
def mock_hass():
    """Create mock hass."""
    hass = MockHass()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create mock config entry."""
    return MockConfigEntry()


@pytest.fixture
def adapter(mock_hass, mock_config_entry):
    """Create EMHASS adapter for testing."""
    adapter = EMHASSAdapter(hass=mock_hass, entry=mock_config_entry)
    return adapter


class TestChargingPowerKwPropagation:
    """Test that charging_power_kw properly propagates to LoadPublisher."""
    
    def test_load_publisher_initialized_with_default(self, adapter):
        """LoadPublisher is initialized with default charging_power_kw=3.6."""
        # Verify initial state - LoadPublisher has 3.6 (default)
        assert adapter._load_publisher.charging_power_kw == 3.6, \
            f"Expected 3.6, got {adapter._load_publisher.charging_power_kw}"
    
    @pytest.mark.asyncio
    async def test_update_charging_power_propagates_to_load_publisher(
        self, mock_hass, adapter
    ):
        """BUG: adapter._charging_power_kw updates but LoadPublisher doesn't."""
        # Simulate user changing options via Options flow
        new_power = 3.4
        mock_entry = MagicMock()
        mock_entry.options = {"charging_power_kw": new_power}
        mock_entry.data = {}
        
        # Call _handle_config_entry_update as would happen on options change
        await adapter._handle_config_entry_update(mock_hass, mock_entry)
        
        # adapter._charging_power_kw is updated correctly
        assert adapter._charging_power_kw == new_power, \
            f"Expected adapter._charging_power_kw={new_power}, got {adapter._charging_power_kw}"
        
        # FIXED: LoadPublisher.charging_power_kw IS NOW updated!
        # This is the fix - LoadPublisher gets the updated value
        assert adapter._load_publisher.charging_power_kw == new_power, \
            f"Expected LoadPublisher to have {new_power}, got {adapter._load_publisher.charging_power_kw}"
    
    @pytest.mark.asyncio
    async def test_publish_uses_adapter_charging_power_not_load_publisher(
        self, mock_hass, mock_config_entry
    ):
        """BUG: async_publish_deferrable_load passes adapter._charging_power_kw to cache
        BUT LoadPublisher.publish() uses its own self.charging_power_kw."""
        
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_config_entry)
        
        # Update charging_power_kw via options
        new_power = 3.4
        mock_entry = MagicMock()
        mock_entry.options = {"charging_power_kw": new_power}
        mock_entry.data = {}
        
        await adapter._handle_config_entry_update(mock_hass, mock_entry)
        
        # Check what adapter passes to cache
        cached_power = adapter._charging_power_kw or 3.6
        assert cached_power == new_power, \
            f"Cache should use {new_power}, got {cached_power}"
        
        # FIXED: LoadPublisher now gets updated power (3.4)
        publisher_power = adapter._load_publisher.charging_power_kw
        assert publisher_power == new_power, \
            f"Expected LoadPublisher to have {new_power}, got {publisher_power}"


class TestChargingPowerKwSensorIntegration:
    """Test that simulates the full flow to sensor."""
    
    @pytest.mark.asyncio
    async def test_power_profile_shows_correct_charging_power(
        self, mock_hass
    ):
        """Simulate full flow: options change -> adapter update -> sensor update."""
        
        # Setup: Create adapter with initial config
        entry = MockConfigEntry()
        adapter = EMHASSAdapter(hass=mock_hass, entry=entry)
        
        # Initial state - LoadPublisher has default 3.6kW
        initial_power = adapter._load_publisher.charging_power_kw
        print(f"Initial LoadPublisher.charging_power_kw = {initial_power}")
        
        # User changes options to 3.4kW via Options flow
        new_power = 3.4
        updated_entry = MagicMock()
        updated_entry.options = {"charging_power_kw": new_power}
        updated_entry.data = {}
        
        # This simulates what happens when user saves options
        await adapter._handle_config_entry_update(mock_hass, updated_entry)
        
        # Verify adapter state
        print(f"After options update: adapter._charging_power_kw = {adapter._charging_power_kw}")
        print(f"After options update: LoadPublisher.charging_power_kw = {adapter._load_publisher.charging_power_kw}")
        
        # FIXED: LoadPublisher is now 3.4 (same as user configured)
        # When async_publish_deferrable_load is called:
        # 1. Cache is populated with adapter._charging_power_kw (3.4) - CORRECT
        # 2. LoadPublisher.publish() uses self.charging_power_kw (3.4) - CORRECT!
        
        # Calculate what power_profile_watts would show:
        expected_power_watts = new_power * 1000  # 3400W
        actual_power_watts = adapter._load_publisher.charging_power_kw * 1000  # 3400W (FIXED!)
        
        assert expected_power_watts == 3400, f"Expected 3400W, got {expected_power_watts}"
        assert actual_power_watts == expected_power_watts, \
            f"Expected LoadPublisher to show {expected_power_watts}W, got {actual_power_watts}W"


if __name__ == "__main__":
    # Run test to confirm bug
    print("Running integration test to confirm charging_power_kw bug...")
    pytest.main([__file__, "-v", "-s"])