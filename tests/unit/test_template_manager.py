"""Tests for dashboard/template_manager.py uncovered code paths."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml


class TestCallAsyncExecutorSync:
    """Test _call_async_executor_sync."""

    def test_sync_func(self):
        """Sync function returns result directly."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            _call_async_executor_sync,
        )
        result = _call_async_executor_sync(None, lambda x: x * 2, 5)
        assert result == 10


class TestAwaitExecutorResult:
    """Test _await_executor_result."""

    @pytest.mark.asyncio
    async def test_sync_value(self):
        """Sync value passed through."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            _await_executor_result,
        )
        result = await _await_executor_result(42)
        assert result == 42


class TestReadFileContent:
    """Test _read_file_content."""

    def test_read_existing(self, tmp_path):
        """Read existing file."""
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            _read_file_content,
        )
        assert _read_file_content(str(f)) == "hello world"

    def test_read_nonexistent(self):
        """Non-existent file raises FileNotFoundError."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            _read_file_content,
        )
        with pytest.raises(FileNotFoundError):
            _read_file_content("/nonexistent/path/file.txt")


class TestWriteFileContent:
    """Test _write_file_content."""

    def test_write_new(self, tmp_path):
        """Write to new file."""
        f = tmp_path / "new.yaml"
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            _write_file_content,
        )
        _write_file_content(str(f), "key: value")
        assert f.read_text() == "key: value"


class TestCheckPathExists:
    """Test _check_path_exists."""

    def test_exists_true(self, tmp_path):
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            _check_path_exists,
        )
        f = tmp_path / "exists"
        f.write_text("x")
        assert _check_path_exists(str(f)) is True

    def test_exists_false(self):
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            _check_path_exists,
        )
        assert _check_path_exists("/nonexistent/path") is False


class TestCreateDirectory:
    """Test _create_directory."""

    def test_creates_dir(self, tmp_path):
        target = tmp_path / "newdir"
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            _create_directory,
        )
        _create_directory(str(target))
        assert target.is_dir()


class TestLoadTemplate:
    """Test load_template."""

    @pytest.mark.asyncio
    async def test_template_exception(self):
        """Exception during load → returns None."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            load_template,
        )
        with patch(
            "custom_components.ev_trip_planner.dashboard.template_manager.os.path.exists",
            return_value=True,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard.template_manager._read_file_content",
                side_effect=RuntimeError("read fails"),
            ):
                result = await load_template(
                    MagicMock(), "v1", "V1", False
                )
                assert result is None


class TestSaveLovelaceDashboard:
    """Test save_lovelace_dashboard paths."""

    @pytest.mark.asyncio
    async def test_views_empty_falls_back_to_yaml(self):
        """Empty views → DashboardError caught → YAML fallback attempted."""
        from custom_components.ev_trip_planner.dashboard import DashboardImportResult
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_lovelace_dashboard,
        )
        hass = MagicMock()
        hass.services.has_service.return_value = True

        with patch(
            "custom_components.ev_trip_planner.dashboard.template_manager.save_yaml_fallback",
            new=AsyncMock(
                return_value=DashboardImportResult(
                    success=False, vehicle_id="v1", vehicle_name="V1"
                )
            ),
        ):
            result = await save_lovelace_dashboard(
                hass, {"title": "T", "views": []}, "v1", "V1"
            )
            assert result.success is False

    @pytest.mark.asyncio
    async def test_lovelace_save_success(self):
        """lovelace.save service available → saves via service."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_lovelace_dashboard,
        )
        hass = MagicMock()
        hass.services.has_service.return_value = True
        hass.services.async_call = AsyncMock()

        config = {
            "title": "Test Dashboard",
            "views": [{"path": "v1", "title": "Test View", "cards": []}],
        }
        result = await save_lovelace_dashboard(hass, config, "v1", "V1")
        assert result.success is True
        assert result.storage_method == "lovelace_save_service"


class TestVerifyStoragePermissions:
    """Test verify_storage_permissions."""

    @pytest.mark.asyncio
    async def test_storage_available(self):
        """Storage available → returns True."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            verify_storage_permissions,
        )
        hass = MagicMock()
        mock_store_instance = MagicMock()
        mock_store_instance.async_load = AsyncMock(return_value=None)

        class MockStore:
            def __new__(cls, *args, **kwargs):
                return mock_store_instance

        with patch(
            "homeassistant.helpers.storage.Store",
            MockStore,
        ):
            result = await verify_storage_permissions(hass, "v1")
            assert result is True

    @pytest.mark.asyncio
    async def test_storage_unavailable(self):
        """Storage unavailable → returns False."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            verify_storage_permissions,
        )
        hass = MagicMock()

        class FailingStore:
            def __new__(cls, *args, **kwargs):
                raise OSError("storage unavailable")

        with patch(
            "homeassistant.helpers.storage.Store",
            FailingStore,
        ):
            result = await verify_storage_permissions(hass, "v1")
            assert result is False


class TestSaveYamlFallback:
    """Test save_yaml_fallback edge cases."""

    @pytest.mark.asyncio
    async def test_empty_config(self):
        """Empty config returns failure result."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_yaml_fallback,
        )
        hass = MagicMock()
        result = await save_yaml_fallback(hass, None, "v1", "V1")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_missing_title(self):
        """Config missing title returns failure."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_yaml_fallback,
        )
        hass = MagicMock()
        result = await save_yaml_fallback(hass, {"views": []}, "v1", "V1")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_missing_views(self):
        """Config missing views returns failure."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_yaml_fallback,
        )
        hass = MagicMock()
        result = await save_yaml_fallback(hass, {"title": "T"}, "v1", "V1")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_views_not_list(self):
        """Views is not a list returns failure."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_yaml_fallback,
        )
        hass = MagicMock()
        result = await save_yaml_fallback(
            hass, {"title": "T", "views": "not list"}, "v1", "V1"
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_empty_views_list(self):
        """Empty views list returns failure."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_yaml_fallback,
        )
        hass = MagicMock()
        result = await save_yaml_fallback(
            hass, {"title": "T", "views": []}, "v1", "V1"
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_write_success(self, tmp_path):
        """Successful YAML write returns success=True."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_yaml_fallback,
        )
        hass = MagicMock()
        hass.config.config_dir = str(tmp_path)

        config = {
            "title": "Test",
            "views": [{"path": "v1", "title": "T", "cards": []}],
        }
        result = await save_yaml_fallback(hass, config, "v1", "Test Vehicle")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_no_config_dir(self, caplog):
        """No config_dir → failure."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_yaml_fallback,
        )
        hass = MagicMock()
        hass.config.config_dir = None
        result = await save_yaml_fallback(
            hass, {"title": "T", "views": []}, "v1", "V1"
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_view_not_dict(self):
        """View that's not a dict → failure."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_yaml_fallback,
        )
        hass = MagicMock()
        result = await save_yaml_fallback(
            hass, {"title": "T", "views": ["not a dict"]}, "v1", "V1"
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_view_missing_path(self):
        """View missing path → failure."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_yaml_fallback,
        )
        hass = MagicMock()
        result = await save_yaml_fallback(
            hass,
            {"title": "T", "views": [{"title": "T", "cards": []}]},
            "v1",
            "V1",
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_view_missing_title(self):
        """View missing title → failure."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_yaml_fallback,
        )
        hass = MagicMock()
        result = await save_yaml_fallback(
            hass,
            {"title": "T", "views": [{"path": "v", "cards": []}]},
            "v1",
            "V1",
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_view_missing_cards(self):
        """View missing cards → failure."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_yaml_fallback,
        )
        hass = MagicMock()
        result = await save_yaml_fallback(
            hass,
            {"title": "T", "views": [{"path": "v", "title": "T"}]},
            "v1",
            "V1",
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_duplicate_filename_increments(self, tmp_path):
        """Duplicate filename → appends counter."""
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            save_yaml_fallback,
        )
        hass = MagicMock()
        hass.config.config_dir = str(tmp_path)

        first_path = tmp_path / "ev-trip-planner-v1.yaml"
        first_path.write_text("old")

        config = {
            "title": "Test",
            "views": [{"path": "v1", "title": "T", "cards": []}],
        }
        result = await save_yaml_fallback(hass, config, "v1", "Test Vehicle")
        assert result.success is True
        assert (tmp_path / "ev-trip-planner-v1.yaml.2").exists()


class TestValidateConfig:
    """Test validate_config (standalone function in template_manager)."""

    def test_valid_config(self):
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            validate_config,
        )
        config = {
            "title": "Test",
            "views": [{"path": "v1", "title": "T", "cards": []}],
        }
        validate_config(config, "v1")

    def test_rejects_not_dict(self):
        from custom_components.ev_trip_planner.dashboard import DashboardValidationError
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            validate_config,
        )
        with pytest.raises(DashboardValidationError):
            validate_config("not a dict", "v1")

    def test_rejects_missing_title(self):
        from custom_components.ev_trip_planner.dashboard import DashboardValidationError
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            validate_config,
        )
        with pytest.raises(DashboardValidationError):
            validate_config({"views": []}, "v1")

    def test_rejects_missing_views(self):
        from custom_components.ev_trip_planner.dashboard import DashboardValidationError
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            validate_config,
        )
        with pytest.raises(DashboardValidationError):
            validate_config({"title": "T"}, "v1")

    def test_rejects_views_not_list(self):
        from custom_components.ev_trip_planner.dashboard import DashboardValidationError
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            validate_config,
        )
        with pytest.raises(DashboardValidationError):
            validate_config({"title": "T", "views": "not list"}, "v1")

    def test_rejects_empty_views(self):
        from custom_components.ev_trip_planner.dashboard import DashboardValidationError
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            validate_config,
        )
        with pytest.raises(DashboardValidationError):
            validate_config({"title": "T", "views": []}, "v1")

    def test_rejects_view_not_dict(self):
        from custom_components.ev_trip_planner.dashboard import DashboardValidationError
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            validate_config,
        )
        with pytest.raises(DashboardValidationError):
            validate_config({"title": "T", "views": ["not dict"]}, "v1")

    def test_rejects_view_missing_path(self):
        from custom_components.ev_trip_planner.dashboard import DashboardValidationError
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            validate_config,
        )
        with pytest.raises(DashboardValidationError):
            validate_config(
                {"title": "T", "views": [{"title": "T", "cards": []}]}, "v1"
            )

    def test_rejects_view_missing_title(self):
        from custom_components.ev_trip_planner.dashboard import DashboardValidationError
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            validate_config,
        )
        with pytest.raises(DashboardValidationError):
            validate_config(
                {"title": "T", "views": [{"path": "v", "cards": []}]}, "v1"
            )

    def test_rejects_view_missing_cards(self):
        from custom_components.ev_trip_planner.dashboard import DashboardValidationError
        from custom_components.ev_trip_planner.dashboard.template_manager import (
            validate_config,
        )
        with pytest.raises(DashboardValidationError):
            validate_config(
                {"title": "T", "views": [{"path": "v", "title": "T"}]}, "v1"
            )
