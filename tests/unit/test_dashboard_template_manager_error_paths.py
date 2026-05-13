"""Tests for uncovered error paths in dashboard template_manager.

Targets lines not covered by existing tests to push coverage >=80%.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.dashboard.template_manager import (
    DashboardConfig,
    DashboardImportResult,
    save_yaml_fallback,
    validate_config,
    verify_storage_permissions,
)


class TestValidateConfigErrorDetails:
    """Test validate_config error message contents."""

    def test_missing_title_error(self) -> None:
        """Title missing should raise DashboardValidationError."""
        with pytest.raises(Exception) as exc_info:
            validate_config({"views": [{"path": "p", "title": "t", "cards": []}]}, "v1")
        assert "title" in str(exc_info.value).lower()

    def test_missing_views_error(self) -> None:
        """Views missing should raise DashboardValidationError."""
        with pytest.raises(Exception) as exc_info:
            validate_config({"title": "T"}, "v1")
        assert "views" in str(exc_info.value).lower()

    def test_views_not_list_error(self) -> None:
        """Views must be a list."""
        with pytest.raises(Exception) as exc_info:
            validate_config({"title": "T", "views": {"not": "a list"}}, "v1")
        assert "views" in str(exc_info.value).lower()

    def test_empty_views_error(self) -> None:
        """Empty views list should raise."""
        with pytest.raises(Exception) as exc_info:
            validate_config({"title": "T", "views": []}, "v1")
        assert "empty" in str(exc_info.value).lower()

    def test_view_missing_path_error(self) -> None:
        """View without path field."""
        config: DashboardConfig = {
            "title": "T",
            "views": [{"title": "V", "cards": []}],
        }
        with pytest.raises(Exception) as exc_info:
            validate_config(config, "v1")
        assert "path" in str(exc_info.value).lower()

    def test_view_missing_title_error(self) -> None:
        """View without title field."""
        config: DashboardConfig = {
            "title": "T",
            "views": [{"path": "v", "cards": []}],
        }
        with pytest.raises(Exception) as exc_info:
            validate_config(config, "v1")
        assert "title" in str(exc_info.value).lower()

    def test_view_missing_cards_error(self) -> None:
        """View without cards field."""
        config: DashboardConfig = {
            "title": "T",
            "views": [{"path": "v", "title": "V"}],
        }
        with pytest.raises(Exception) as exc_info:
            validate_config(config, "v1")
        assert "cards" in str(exc_info.value).lower()

    def test_view_not_dict_error(self) -> None:
        """View must be a dict, not a string."""
        config: DashboardConfig = {
            "title": "T",
            "views": ["not_a_dict"],
        }
        with pytest.raises(Exception) as exc_info:
            validate_config(config, "v1")
        assert "dict" in str(exc_info.value).lower()

    def test_vehicle_id_in_view_path_no_warning(self, caplog: pytest.LogCaptureFixture) -> (
        None
    ):
        """When vehicle_id is in view path, no warning."""
        caplog.set_level("WARNING")
        config: DashboardConfig = {
            "title": "T",
            "views": [{"path": "vehicle/v1/trips", "title": "V", "cards": []}],
        }
        validate_config(config, "v1")
        assert not any("not found in any view path" in r.message for r in caplog.records)

    def test_vehicle_id_not_in_view_path_warns(self, caplog: pytest.LogCaptureFixture) -> (
        None
    ):
        """When vehicle_id is NOT in view path, a warning is logged."""
        caplog.set_level("WARNING")
        config: DashboardConfig = {
            "title": "T",
            "views": [{"path": "other/vehicle/v2/trips", "title": "V", "cards": []}],
        }
        validate_config(config, "v1")
        assert any("not found in any view path" in r.message for r in caplog.records)


class TestSaveYamlFallbackValidation:
    """Test save_yaml_fallback validation error paths."""

    @pytest.mark.asyncio
    async def test_empty_dashboard_config(self) -> None:
        """Empty config returns failure."""
        hass = MagicMock()
        result = await save_yaml_fallback(hass, {}, "v1", "Test")
        assert result.success is False
        assert result.storage_method == "yaml_fallback"
        assert result.error == "Invalid dashboard config"

    @pytest.mark.asyncio
    async def test_none_dashboard_config(self) -> None:
        """None config returns failure."""
        hass = MagicMock()
        result = await save_yaml_fallback(hass, None, "v1", "Test")  # type: ignore[arg-type]
        assert result.success is False
        assert result.storage_method == "yaml_fallback"

    @pytest.mark.asyncio
    async def test_missing_title_in_config(self) -> None:
        """Config without title returns failure."""
        hass = MagicMock()
        config: DashboardConfig = {"views": [{"path": "v", "title": "V", "cards": []}]}
        result = await save_yaml_fallback(hass, config, "v1", "Test")
        assert result.success is False
        assert result.error == "Invalid dashboard config"

    @pytest.mark.asyncio
    async def test_missing_views_in_config(self) -> None:
        """Config without views returns failure."""
        hass = MagicMock()
        config: DashboardConfig = {"title": "T"}
        result = await save_yaml_fallback(hass, config, "v1", "Test")
        assert result.success is False
        assert result.error == "Invalid dashboard config"

    @pytest.mark.asyncio
    async def test_views_not_a_list(self) -> None:
        """Views that is not a list fails."""
        hass = MagicMock()
        config: DashboardConfig = {"title": "T", "views": "not_list"}
        result = await save_yaml_fallback(hass, config, "v1", "Test")
        assert result.success is False
        assert result.error == "Invalid dashboard config"

    @pytest.mark.asyncio
    async def test_empty_views_list(self) -> None:
        """Empty views list fails."""
        hass = MagicMock()
        config: DashboardConfig = {"title": "T", "views": []}
        result = await save_yaml_fallback(hass, config, "v1", "Test")
        assert result.success is False
        assert result.error == "Invalid dashboard config"

    @pytest.mark.asyncio
    async def test_view_missing_path(self) -> None:
        """View without path fails."""
        hass = MagicMock()
        config: DashboardConfig = {"title": "T", "views": [{"title": "V", "cards": []}]}
        result = await save_yaml_fallback(hass, config, "v1", "Test")
        assert result.success is False
        assert result.error == "Invalid dashboard config"

    @pytest.mark.asyncio
    async def test_view_missing_title(self) -> None:
        """View without title fails."""
        hass = MagicMock()
        config: DashboardConfig = {"title": "T", "views": [{"path": "v", "cards": []}]}
        result = await save_yaml_fallback(hass, config, "v1", "Test")
        assert result.success is False
        assert result.error == "Invalid dashboard config"

    @pytest.mark.asyncio
    async def test_view_missing_cards(self) -> None:
        """View without cards fails."""
        hass = MagicMock()
        config: DashboardConfig = {"title": "T", "views": [{"path": "v", "title": "V"}]}
        result = await save_yaml_fallback(hass, config, "v1", "Test")
        assert result.success is False
        assert result.error == "Invalid dashboard config"

    @pytest.mark.asyncio
    async def test_view_not_dict(self) -> None:
        """View that is not a dict fails."""
        hass = MagicMock()
        config: DashboardConfig = {"title": "T", "views": ["not_a_dict"]}
        result = await save_yaml_fallback(hass, config, "v1", "Test")
        assert result.success is False
        assert result.error == "Invalid dashboard config"

    @pytest.mark.asyncio
    async def test_no_config_directory(self) -> None:
        """hass.config.config_dir None returns failure."""
        hass = MagicMock()
        hass.config.config_dir = None
        config: DashboardConfig = {
            "title": "T",
            "views": [{"path": "v", "title": "V", "cards": []}],
        }
        result = await save_yaml_fallback(hass, config, "v1", "Test")
        assert result.success is False
        assert result.error == "Invalid dashboard config"


class TestVerifyStoragePermissions:
    """Test verify_storage_permissions error paths."""

    @pytest.mark.asyncio
    async def test_storage_unavailable_logs_warning(self, caplog: pytest.LogCaptureFixture) -> (
        None
    ):
        """When store fails to load, a warning is logged."""
        caplog.set_level("WARNING")
        hass = MagicMock()
        from homeassistant.helpers import storage as ha_storage

        with patch.object(ha_storage, "Store") as MockStore:
            mock_store = AsyncMock()
            mock_store.async_load.side_effect = OSError("storage unavailable")
            MockStore.return_value = mock_store
            result = await verify_storage_permissions(hass, "v1")
            assert result is False
            assert any("not available" in r.message for r in caplog.records)