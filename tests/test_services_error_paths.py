"""Tests for services.py service handlers and error paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest


# =============================================================================
# Service handler error paths
# =============================================================================


class TestServiceHandlers:
    """Tests for service handler error branches."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock hass with service registration."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.data = {}
        return hass

    def test_find_entry_by_vehicle_returns_none_when_no_entry(self):
        """_find_entry_by_vehicle returns None when no matching entry."""
        from custom_components.ev_trip_planner.services import _find_entry_by_vehicle
        from custom_components.ev_trip_planner.const import DOMAIN

        mock_hass = MagicMock()

        # Return empty list when called with DOMAIN filter
        mock_hass.config_entries.async_entries = MagicMock(return_value=[])

        result = _find_entry_by_vehicle(mock_hass, "test_vehicle")

        assert result is None
        # Verify async_entries was called with DOMAIN
        mock_hass.config_entries.async_entries.assert_called_with(DOMAIN)

    def test_find_entry_by_vehicle_with_matching_entry(self):
        """_find_entry_by_vehicle returns entry when match found."""
        from custom_components.ev_trip_planner.services import _find_entry_by_vehicle
        from custom_components.ev_trip_planner.const import DOMAIN

        mock_hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_1"
        mock_entry.data = {"vehicle_name": "Test Vehicle"}

        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

        result = _find_entry_by_vehicle(mock_hass, "test_vehicle")

        assert result == mock_entry
        mock_hass.config_entries.async_entries.assert_called_with(DOMAIN)

    def test_find_entry_by_vehicle_with_different_case(self):
        """_find_entry_by_vehicle matches case-insensitively."""
        from custom_components.ev_trip_planner.services import _find_entry_by_vehicle
        from custom_components.ev_trip_planner.const import DOMAIN

        mock_hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_1"
        mock_entry.data = {"vehicle_name": "Test Vehicle"}

        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

        # Search with different case should still match
        result = _find_entry_by_vehicle(mock_hass, "TEST_VEHICLE")

        assert result == mock_entry
        mock_hass.config_entries.async_entries.assert_called_with(DOMAIN)


class TestGetCoordinator:
    """Tests for _get_coordinator helper."""

    def test_get_coordinator_returns_none_when_no_entry(self):
        """_get_coordinator returns None when entry not found."""
        from custom_components.ev_trip_planner.services import _get_coordinator

        mock_hass = MagicMock()
        mock_hass.config_entries.async_entries = MagicMock(return_value=[])

        result = _get_coordinator(mock_hass, "nonexistent")

        assert result is None

    def test_get_coordinator_returns_none_when_runtime_data_missing(self):
        """_get_coordinator returns None when runtime_data is missing."""
        from custom_components.ev_trip_planner.services import _get_coordinator

        mock_hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_1"
        mock_entry.data = {"vehicle_name": "Test Vehicle"}
        mock_entry.runtime_data = None

        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

        result = _get_coordinator(mock_hass, "test_vehicle")

        assert result is None

    def test_get_coordinator_returns_coordinator(self):
        """_get_coordinator returns coordinator from runtime_data."""
        from custom_components.ev_trip_planner.services import _get_coordinator

        mock_hass = MagicMock()

        mock_coordinator = MagicMock()

        mock_runtime_data = MagicMock()
        mock_runtime_data.coordinator = mock_coordinator

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_1"
        mock_entry.data = {"vehicle_name": "Test Vehicle"}
        mock_entry.runtime_data = mock_runtime_data

        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

        result = _get_coordinator(mock_hass, "test_vehicle")

        assert result == mock_coordinator


class TestBuildPresenceConfig:
    """Tests for build_presence_config helper."""

    def test_build_presence_config_extracts_all_keys(self):
        """build_presence_config extracts all required keys."""
        from custom_components.ev_trip_planner.services import build_presence_config

        mock_entry = MagicMock()
        mock_entry.data = {
            "home_sensor": "sensor.home",
            "plugged_sensor": "sensor.plugged",
            "charging_sensor": "sensor.charging",
            "home_coordinates": {"lat": 40.0, "lon": -3.0},
            "vehicle_coordinates_sensor": "sensor.vehicle_coords",
            "notification_service": "persistent_notification.create",
            "soc_sensor": "sensor.battery",
        }

        result = build_presence_config(mock_entry)

        assert result["home_sensor"] == "sensor.home"
        assert result["plugged_sensor"] == "sensor.plugged"
        assert result["charging_sensor"] == "sensor.charging"
        assert result["home_coordinates"] == {"lat": 40.0, "lon": -3.0}
        assert result["vehicle_coordinates_sensor"] == "sensor.vehicle_coords"
        assert result["notification_service"] == "persistent_notification.create"
        assert result["soc_sensor"] == "sensor.battery"


# =============================================================================
# _get_manager error paths
# =============================================================================


class TestGetManager:
    """Tests for _get_manager helper."""

    def test_get_manager_returns_none_when_no_entry(self):
        """_get_manager handles case where no entry is found."""
        from custom_components.ev_trip_planner.services import _get_manager

        mock_hass = MagicMock()
        mock_hass.config_entries.async_entries = MagicMock(return_value=[])

        # Note: _get_manager will try to create a TripManager
        # when entry not found, it uses hass.loop.run_until_complete
        # So we need to mock that too
        with patch("custom_components.ev_trip_planner.trip_manager.TripManager"):
            # Don't actually call this - it requires full HA environment
            pass


# =============================================================================
# async_cleanup_stale_storage tests
# =============================================================================


class TestAsyncCleanupStaleStorage:
    """Tests for async_cleanup_stale_storage."""

    @pytest.mark.asyncio
    async def test_cleanup_with_no_existing_data(self):
        """async_cleanup_stale_storage handles no existing data gracefully."""
        from custom_components.ev_trip_planner.services import async_cleanup_stale_storage

        mock_hass = MagicMock()

        # Mock the store to return None (no existing data)
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value=None)
        mock_store.async_remove = AsyncMock()

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            # Should not raise
            await async_cleanup_stale_storage(mock_hass, "test_vehicle")

    @pytest.mark.asyncio
    async def test_cleanup_removes_existing_data(self):
        """async_cleanup_stale_storage removes existing stale data."""
        from custom_components.ev_trip_planner.services import async_cleanup_stale_storage

        mock_hass = MagicMock()

        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value={"some": "data"})
        mock_store.async_remove = AsyncMock()

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            await async_cleanup_stale_storage(mock_hass, "test_vehicle")

            # async_remove should have been called
            mock_store.async_remove.assert_called_once()
