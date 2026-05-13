"""Tests for save_lovelace_dashboard storage API paths in template_manager.

Targets uncovered lines in the save_lovelace_dashboard function (lines 329-520).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.dashboard.template_manager import (
    DashboardConfig,
    save_lovelace_dashboard,
)


class TestSaveLovelaceDashboardServiceAvailable:
    """Test save_lovelace_dashboard when lovelace.save service IS available."""

    @pytest.mark.asyncio
    async def test_save_via_lovelace_save_service(self) -> None:
        """When lovelace.save service is available, should use it."""
        hass = MagicMock()
        hass.services.has_service.return_value = True
        hass.services.async_call = AsyncMock()

        dashboard_config: DashboardConfig = {
            "title": "EV Trip Planner",
            "views": [{"path": "v1", "title": "Trip 1", "cards": []}],
        }
        result = await save_lovelace_dashboard(hass, dashboard_config, "v1", "Test")
        assert result.success is True
        assert result.storage_method == "lovelace_save_service"
        # Verify async_call was called with correct args
        hass.services.async_call.assert_called_once_with(
            "lovelace",
            "save",
            {
                "config": {
                    "title": "EV Trip Planner",
                    "views": dashboard_config["views"],
                }
            },
        )

    @pytest.mark.asyncio
    async def test_empty_views_raises_error(self) -> None:
        """Empty views should raise DashboardError, then YAML fallback."""
        hass = MagicMock()
        hass.services.has_service.return_value = True

        dashboard_config: DashboardConfig = {
            "title": "EV Trip Planner",
            "views": [],
        }
        result = await save_lovelace_dashboard(hass, dashboard_config, "v1", "Test")
        # Falls back to YAML since views are empty, which then fails (no config_dir)
        assert result.success is False
        assert result.storage_method == "yaml_fallback"


class TestSaveLovelaceDashboardStorageApi:
    """Test save_lovelace_dashboard when lovelace.save is NOT available."""

    @pytest.mark.asyncio
    async def test_storage_api_no_permission_falls_back_yaml(self) -> None:
        """Storage API available but no permission — YAML fallback."""
        hass = MagicMock()
        hass.services.has_service.return_value = False
        hass.config.config_dir = "/tmp/test"

        with patch(
            "custom_components.ev_trip_planner.dashboard.template_manager.verify_storage_permissions",
            return_value=False,
        ):
            dashboard_config: DashboardConfig = {
                "title": "EV Trip Planner",
                "views": [{"path": "v1", "title": "V", "cards": []}],
            }
            result = await save_lovelace_dashboard(hass, dashboard_config, "v1", "Test")
            # Falls back to YAML since storage permissions fail
            assert result.storage_method == "yaml_fallback"


class TestSaveLovelaceDashboardStorageApiWithStore:
    """Test save_lovelace_dashboard with real Store API mock."""

    @pytest.mark.asyncio
    async def test_storage_api_replaces_existing_view(self) -> None:
        """When existing view has same path, should replace."""
        hass = MagicMock()
        hass.services.has_service.return_value = False
        hass.config.config_dir = "/tmp/test"

        # Mock the store
        mock_store = AsyncMock()
        mock_store.async_load = AsyncMock(return_value={"data": {"views": []}})
        mock_store.async_save = AsyncMock()

        from homeassistant.helpers import storage as ha_storage

        with patch.object(ha_storage, "Store", return_value=mock_store):
            with patch(
                "custom_components.ev_trip_planner.dashboard.template_manager.verify_storage_permissions",
                return_value=True,
            ):
                dashboard_config: DashboardConfig = {
                    "title": "EV Trip Planner",
                    "views": [{"path": "v1", "title": "New View", "cards": []}],
                }
                result = await save_lovelace_dashboard(
                    hass, dashboard_config, "v1", "Test"
                )
                assert result.success is True
                assert result.storage_method == "storage_api"

    @pytest.mark.asyncio
    async def test_storage_api_appends_new_view(self) -> None:
        """When existing view has different path, should append."""
        hass = MagicMock()
        hass.services.has_service.return_value = False
        hass.config.config_dir = "/tmp/test"

        mock_store = AsyncMock()
        mock_store.async_load = AsyncMock(
            return_value={"data": {"views": [{"path": "other"}]}}
        )
        mock_store.async_save = AsyncMock()

        from homeassistant.helpers import storage as ha_storage

        with patch.object(ha_storage, "Store", return_value=mock_store):
            with patch(
                "custom_components.ev_trip_planner.dashboard.template_manager.verify_storage_permissions",
                return_value=True,
            ):
                dashboard_config: DashboardConfig = {
                    "title": "EV Trip Planner",
                    "views": [{"path": "v1", "title": "New View", "cards": []}],
                }
                result = await save_lovelace_dashboard(
                    hass, dashboard_config, "v1", "Test"
                )
                assert result.success is True
                assert result.storage_method == "storage_api"

    @pytest.mark.asyncio
    async def test_storage_api_no_views_in_config_raises(self) -> None:
        """Config with no views should raise DashboardError."""
        hass = MagicMock()
        hass.services.has_service.return_value = False
        hass.config.config_dir = "/tmp/test"

        # Track calls to store — first call is verify_storage_permissions Store, second is lovelace Store
        store_call_count = 0

        def create_store(*args, key="test", **kwargs):
            nonlocal store_call_count
            store_call_count += 1
            mock_s = AsyncMock()
            if store_call_count == 1:
                # First Store is for verify_storage_permissions test
                mock_s.async_load = AsyncMock(return_value=None)
                mock_s.async_save = AsyncMock()
            else:
                # Second Store is for lovelace config
                mock_s.async_load = AsyncMock(return_value={"data": {"views": []}})
                mock_s.async_save = AsyncMock()
            return mock_s

        from homeassistant.helpers import storage as ha_storage

        with patch.object(ha_storage, "Store", side_effect=create_store):
            with patch(
                "custom_components.ev_trip_planner.dashboard.template_manager.verify_storage_permissions",
                return_value=True,
            ):
                dashboard_config: DashboardConfig = {
                    "title": "EV Trip Planner",
                    "views": [],
                }
                result = await save_lovelace_dashboard(
                    hass, dashboard_config, "v1", "Test"
                )
                # DashboardError raised → falls back to YAML
                assert result.storage_method == "yaml_fallback"

    @pytest.mark.asyncio
    async def test_storage_error_falls_back_yaml(self) -> None:
        """Storage operation failure falls back to YAML."""
        hass = MagicMock()
        hass.services.has_service.return_value = False
        hass.config.config_dir = "/tmp/test"

        mock_store = AsyncMock()
        mock_store.async_load = AsyncMock(side_effect=OSError("storage error"))
        mock_store.async_save = AsyncMock()

        from homeassistant.helpers import storage as ha_storage

        with patch.object(ha_storage, "Store", return_value=mock_store):
            with patch(
                "custom_components.ev_trip_planner.dashboard.template_manager.verify_storage_permissions",
                return_value=True,
            ):
                dashboard_config: DashboardConfig = {
                    "title": "EV Trip Planner",
                    "views": [{"path": "v1", "title": "V", "cards": []}],
                }
                result = await save_lovelace_dashboard(
                    hass, dashboard_config, "v1", "Test"
                )
                assert result.storage_method == "yaml_fallback"
