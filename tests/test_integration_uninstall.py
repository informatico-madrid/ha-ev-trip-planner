"""Tests for integration uninstall/cascade delete behavior.

Tests that vehicle deletion properly cleans up all trips from TripManager storage.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry


class TestCascadeDelete:
    """Tests for cascade delete when vehicle is uninstalled."""

    @pytest.mark.asyncio
    async def test_unload_entry_calls_async_delete_all_trips(self):
        """Test that async_unload_entry calls async_delete_all_trips on trip_manager.

        When a vehicle's integration is removed (uninstalled), all trips stored in
        TripManager should be deleted to prevent orphaned data. This is AC-1 from
        the integration points design.
        """
        # Create mock Home Assistant instance
        mock_hass = Mock(spec=HomeAssistant)
        mock_hass.data = {}

        # Create mock config entry
        entry = Mock(spec=ConfigEntry)
        entry.data = {
            "vehicle_id": "test_vehicle",
            "vehicle_name": "Test Vehicle",
        }
        entry.entry_id = "test_entry_id"

        # Create mock trip_manager with async_delete_all_trips method
        mock_trip_manager = Mock()
        mock_trip_manager.async_delete_all_trips = AsyncMock()

        # Store trip_manager in runtime data (simulating async_setup_entry)
        namespace = "ev_trip_planner_test_entry_id"
        mock_hass.data["ev_trip_planner_runtime_data"] = {
            namespace: {
                "config": entry.data,
                "trip_manager": mock_trip_manager,
            }
        }

        # Mock platforms unload to return True
        async def mock_unload_platforms(entry, platforms):
            return True
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_unload_platforms = mock_unload_platforms

        # Mock async_unregister_panel
        with patch("custom_components.ev_trip_planner.async_unregister_panel", new_callable=AsyncMock) as mock_unregister:
            # Import and call async_unload_entry
            from custom_components.ev_trip_planner import async_unload_entry

            result = await async_unload_entry(mock_hass, entry)

            # Verify unload succeeded
            assert result is True

            # CRITICAL: async_delete_all_trips should have been called on the trip_manager
            mock_trip_manager.async_delete_all_trips.assert_called_once()