"""Tests for services.py additional coverage."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest


class TestAsyncCleanupOrphanedEMHASSSensors:
    """Tests for async_cleanup_orphaned_emhass_sensors."""

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_sensors_handles_error(self):
        """async_cleanup_orphaned_emhass_sensors handles errors gracefully."""
        from custom_components.ev_trip_planner.services import async_cleanup_orphaned_emhass_sensors

        mock_hass = MagicMock()

        # Mock entity_registry to raise an error
        with patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            side_effect=Exception("Test error"),
        ):
            # Should not raise
            await async_cleanup_orphaned_emhass_sensors(mock_hass)


class TestAsyncImportDashboardForEntry:
    """Tests for async_import_dashboard_for_entry."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock hass instance."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.data = {}
        return hass

    @pytest.mark.asyncio
    async def test_import_dashboard_success(self, mock_hass):
        """async_import_dashboard_for_entry handles successful import."""
        from custom_components.ev_trip_planner.services import async_import_dashboard_for_entry

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {"vehicle_name": "Test Vehicle", "use_charts": False}

        mock_result = MagicMock()
        mock_result.success = True

        with patch(
            "custom_components.ev_trip_planner.dashboard.import_dashboard",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            # Should not raise
            await async_import_dashboard_for_entry(
                mock_hass, mock_entry, "test_vehicle"
            )

    @pytest.mark.asyncio
    async def test_import_dashboard_failure(self, mock_hass):
        """async_import_dashboard_for_entry handles failed import."""
        from custom_components.ev_trip_planner.services import async_import_dashboard_for_entry

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {"vehicle_name": "Test Vehicle", "use_charts": False}

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Template not found"

        with patch(
            "custom_components.ev_trip_planner.dashboard.import_dashboard",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            # Should not raise - just logs warning
            await async_import_dashboard_for_entry(
                mock_hass, mock_entry, "test_vehicle"
            )


class TestBuildPresenceConfig:
    """Additional tests for build_presence_config."""

    def test_build_presence_config_with_missing_keys(self):
        """build_presence_config handles missing keys gracefully."""
        from custom_components.ev_trip_planner.services import build_presence_config

        mock_entry = MagicMock()
        mock_entry.data = {
            "home_sensor": "sensor.home",
            # Other keys missing
        }

        result = build_presence_config(mock_entry)

        assert result["home_sensor"] == "sensor.home"
        assert result["plugged_sensor"] is None
        assert result["charging_sensor"] is None


class TestGetEmhassAdapter:
    """Tests for _get_emhass_adapter."""

    def test_get_emhass_adapter_returns_none(self):
        """_get_emhass_adapter always returns None."""
        from custom_components.ev_trip_planner.services import _get_emhass_adapter

        mock_hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_1"
        mock_entry.data = {"vehicle_name": "Test Vehicle"}

        mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

        result = _get_emhass_adapter(mock_hass, "test_vehicle")

        # Always returns None by design
        assert result is None
