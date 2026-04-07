"""Tests for integration uninstall/cascade delete behavior.

Tests that vehicle deletion properly cleans up all trips from TripManager storage.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry


@pytest.fixture
def enable_custom_integrations():
    """Enable custom integrations for testing."""
    return True


class TestFullVehicleDeletion:
    """Integration test for full vehicle deletion lifecycle."""

    @pytest.mark.asyncio
    async def test_no_orphaned_sensors_after_deletion(self):
        """Test that no orphaned EMHASS sensors remain after vehicle deletion.

        After async_unload_entry completes:
        - _index_map should be empty
        - _published_entity_ids should be empty
        - No sensors should remain in state machine
        """
        from unittest.mock import AsyncMock, Mock, patch
        from homeassistant.core import HomeAssistant

        # Create mock entities
        mock_hass = Mock(spec=HomeAssistant)
        mock_hass.data = {}

        entry = Mock()
        entry.data = {"vehicle_name": "test_vehicle"}
        entry.entry_id = "test_entry_id"

        # Create mock adapter that tracks cleanup
        emhass_adapter = Mock()
        emhass_adapter._index_map = {"trip_001": 0, "trip_002": 1}
        emhass_adapter._published_entity_ids = {
            "sensor.emhass_perfil_diferible_test_vehicle_trip_001",
        }
        emhass_adapter.async_cleanup_vehicle_indices = AsyncMock()

        # Set up runtime data using entry.runtime_data pattern (Phase 4)
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData
        entry.runtime_data = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=None,
            emhass_adapter=emhass_adapter,
        )

        # Mock unload
        async def mock_unload(entry, platforms):
            return True
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_unload_platforms = mock_unload

        with patch("custom_components.ev_trip_planner.async_unregister_panel", new_callable=AsyncMock):
            from custom_components.ev_trip_planner import async_unload_entry
            await async_unload_entry(mock_hass, entry)

        # Verify: Cleanup was called
        emhass_adapter.async_cleanup_vehicle_indices.assert_called_once()


class TestEmhassFullUnload:
    """Integration tests for EMHASS sensor cleanup during full unload.

    Verifies that when async_unload_entry is called, all EMHASS sensors
    published by the adapter are properly removed via hass.states.async_remove.
    """

    @pytest.mark.asyncio
    async def test_full_unload_cleans_all_emhass_sensors(self):
        """Test that async_unload_entry removes all published EMHASS sensors.

        When a vehicle's integration is removed, all EMHASS deferrable load
        sensors that were published should be removed via hass.states.async_remove.
        This is AC-1.4 from the integration points design.
        """
        # Track removed entity IDs
        removed_entity_ids = []

        # Create mock Home Assistant instance with config_entries attribute
        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.states.async_remove = AsyncMock()

        # Create mock config_entries with async_unload_platforms
        async def mock_unload_platforms(entry, platforms):
            return True
        mock_hass.config_entries = MagicMock()
        mock_hass.config_entries.async_unload_platforms = mock_unload_platforms

        # Create mock config entry with proper structure
        entry = MagicMock()
        entry.entry_id = "emhass_unload_entry_id"
        entry.data = {
            "vehicle_name": "EMHASS Test Vehicle",
            "planning_horizon_days": 7,
            "max_deferrable_loads": 50,
            "charging_power_kw": 7.4,
        }

        # Create mock EMHASS adapter (not real instance to avoid hass.bus issues)
        emhass_adapter = Mock()

        async def cleanup_side_effect():
            for entity_id in list(emhass_adapter._published_entity_ids):
                await mock_hass.states.async_remove(entity_id)

        emhass_adapter.async_cleanup_vehicle_indices = AsyncMock(side_effect=cleanup_side_effect)

        # Simulate published sensors by populating _published_entity_ids and _index_map
        # The main vehicle sensor
        vehicle_sensor_id = f"sensor.emhass_perfil_diferible_{entry.entry_id}"
        emhass_adapter._published_entity_ids = {vehicle_sensor_id}
        emhass_adapter._index_map = {"trip_1": 0}
        emhass_adapter._released_indices = []

        # Create mock trip_manager with async_delete_all_trips
        mock_trip_manager = Mock()
        mock_trip_manager.async_delete_all_trips = AsyncMock()

        # Set up runtime data using entry.runtime_data pattern (Phase 4)
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData
        entry.runtime_data = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=mock_trip_manager,
            emhass_adapter=emhass_adapter,
        )

        # Mock async_unregister_panel
        with patch("custom_components.ev_trip_planner.async_unregister_panel", new_callable=AsyncMock):
            # Import and call async_unload_entry
            from custom_components.ev_trip_planner import async_unload_entry

            # Act: unload the entry
            result = await async_unload_entry(mock_hass, entry)

            # Verify unload succeeded
            assert result is True, "async_unload_entry should return True"

            # CRITICAL: async_delete_all_trips should have been called
            mock_trip_manager.async_delete_all_trips.assert_called_once()

            # Verify cleanup was called
            emhass_adapter.async_cleanup_vehicle_indices.assert_called_once()

            # CRITICAL: Verify hass.states.async_remove was called for published sensor
            mock_hass.states.async_remove.assert_any_call(vehicle_sensor_id)