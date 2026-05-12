"""Coverage tests for dashboard/importer.py and re-exported helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.ev_trip_planner.dashboard import DashboardImportResult
from custom_components.ev_trip_planner.dashboard.importer import (
    _await_executor_result,
    _call_async_executor_sync,
    _check_path_exists,
    _create_directory,
    _load_dashboard_template,
    _read_file_content,
    _save_dashboard_yaml_fallback,
    _save_lovelace_dashboard,
    _validate_dashboard_config,
    _verify_storage_permissions,
    dashboard_exists,
    dashboard_path,
    import_dashboard,
    is_lovelace_available,
    _write_file_content,
)


class TestCallAsyncExecutorSync:
    """Test _call_async_executor_sync edge cases."""

    @pytest.mark.asyncio
    async def test_sync_func_no_async_method(self):
        """When async_add_executor_job is not async, func is called directly."""

        def my_func(x):
            return x * 2

        mock_hass = MagicMock()
        mock_hass.config.components = set()
        mock_hass.async_add_executor_job = my_func
        result = _call_async_executor_sync(mock_hass, my_func, 7)
        assert result == 14

    @pytest.mark.asyncio
    async def test_mock_hass_no_async_method(self):
        """MagicMock without async_add_executor_job calls func directly."""
        result = _call_async_executor_sync(
            MagicMock(), lambda a, b: a + b, 5, 3
        )
        assert result == 8


class TestAwaitExecutorResult:
    """Test _await_executor_result edge cases."""

    @pytest.mark.asyncio
    async def test_returns_direct_result(self):
        """Non-coroutine result is returned directly."""
        result = await _await_executor_result(42)
        assert result == 42

    @pytest.mark.asyncio
    async def test_awaits_coroutine(self):
        """Coroutine result is awaited."""

        async def coro():
            return "hello"

        result = await _await_executor_result(coro())
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        """Dict result from coroutine unwraps correctly."""

        async def coro():
            return {"success": True}

        result = await _await_executor_result(coro())
        assert result == {"success": True}


class TestDashboardExists:
    """Test dashboard_exists edge cases."""

    def test_returns_false_for_empty_vehicle_id(self):
        """Returns False for empty vehicle ID (placeholder implementation)."""
        assert dashboard_exists("") is False

    def test_returns_false_for_nonexistent(self):
        """Returns False for non-existent vehicle (placeholder always returns False)."""
        assert dashboard_exists("nonexistent_vehicle_xyz") is False


class TestDashboardPath:
    """Test dashboard_path edge cases."""

    def test_standard_path_format(self):
        """Returns standard path format with vehicle_id."""
        path = dashboard_path("my_vehicle")
        assert "ev-trip-planner-my_vehicle" in path
        assert path.endswith(".yaml")

    def test_path_with_special_vehicle_id(self):
        """Handles vehicle IDs with underscores."""
        path = dashboard_path("vehicle_01")
        assert path.endswith(".yaml")
        assert "vehicle_01" in path


class TestValidateDashboardConfig:
    """Test _validate_dashboard_config edge cases."""

    def test_valid_config_with_all_fields(self):
        """Config with title, views with path/title/cards passes."""
        config = {
            "title": "Test",
            "views": [
                {
                    "path": "test_vehicle",
                    "title": "Test",
                    "cards": [],
                }
            ],
        }
        _validate_dashboard_config(config, "test_vehicle")

    def test_rejects_empty_views(self):
        """Empty views list raises DashboardValidationError."""
        from custom_components.ev_trip_planner.dashboard import (
            DashboardValidationError,
        )

        config = {"title": "Test", "views": []}
        with pytest.raises(DashboardValidationError):
            _validate_dashboard_config(config, "test_vehicle")

    def test_rejects_missing_title(self):
        """Missing title raises DashboardValidationError."""
        from custom_components.ev_trip_planner.dashboard import (
            DashboardValidationError,
        )

        config = {"views": [{"path": "v", "title": "T", "cards": []}]}
        with pytest.raises(DashboardValidationError):
            _validate_dashboard_config(config, "test_vehicle")

    def test_rejects_missing_views(self):
        """Missing views raises DashboardValidationError."""
        from custom_components.ev_trip_planner.dashboard import (
            DashboardValidationError,
        )

        config = {"title": "Test"}
        with pytest.raises(DashboardValidationError):
            _validate_dashboard_config(config, "test_vehicle")

    def test_rejects_missing_view_path(self):
        """View without path raises DashboardValidationError."""
        from custom_components.ev_trip_planner.dashboard import (
            DashboardValidationError,
        )

        config = {
            "title": "Test",
            "views": [{"title": "Test", "cards": []}],
        }
        with pytest.raises(DashboardValidationError):
            _validate_dashboard_config(config, "test_vehicle")


class TestSaveDashboardYamlFallback:
    """Test _save_dashboard_yaml_fallback edge cases."""

    @pytest.mark.asyncio
    async def test_returns_failed_when_storage_unavailable(self):
        """Failed storage returns DashboardImportResult with success=False."""
        mock_hass = MagicMock()
        mock_hass.config.components = set()
        config = {"title": "Test", "views": [{"path": "v", "title": "T", "cards": []}]}

        with patch(
            "custom_components.ev_trip_planner.dashboard.importer._save_yaml",
            return_value=DashboardImportResult(
                success=False,
                vehicle_id="test_vehicle",
                vehicle_name="Test Vehicle",
                error="storage unavailable",
            ),
        ):
            result = await _save_dashboard_yaml_fallback(
                mock_hass, config, "test_vehicle", "Test Vehicle"
            )
            assert isinstance(result, DashboardImportResult)
            assert result.success is False


class TestLoadDashboardTemplate:
    """Test _load_dashboard_template edge cases."""

    @pytest.mark.asyncio
    async def test_returns_none_on_missing_template(self):
        """Missing template returns None."""
        mock_hass = MagicMock()
        mock_hass.config.components = set()

        with patch(
            "custom_components.ev_trip_planner.dashboard.importer._load_template",
            return_value=None,
        ):
            result = await _load_dashboard_template(
                mock_hass, "vehicle", "Vehicle", False
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_config_with_charts(self):
        """With charts=True, delegates to _load_template."""
        mock_hass = MagicMock()
        mock_hass.config.components = set()
        expected_config = {"title": "Test", "views": [{"path": "v", "title": "T", "cards": []}]}

        with patch(
            "custom_components.ev_trip_planner.dashboard.importer._load_template",
            return_value=expected_config,
        ):
            result = await _load_dashboard_template(
                mock_hass, "vehicle", "Vehicle", True
            )
            assert result == expected_config


class TestSaveLovelaceDashboard:
    """Test _save_lovelace_dashboard edge cases."""

    @pytest.mark.asyncio
    async def test_returns_failed_when_storage_unavailable(self):
        """Fails when storage API is unavailable."""
        mock_hass = MagicMock()
        mock_hass.config.components = set()
        config = {"title": "Test", "views": [{"path": "v", "title": "T", "cards": []}]}

        with patch(
            "custom_components.ev_trip_planner.dashboard.importer._save_lovelace",
            return_value=DashboardImportResult(
                success=False,
                vehicle_id="test",
                vehicle_name="Test",
                error="storage unavailable",
            ),
        ):
            result = await _save_lovelace_dashboard(
                mock_hass, config, "test_vehicle", "Test Vehicle"
            )
            assert isinstance(result, DashboardImportResult)
            assert result.success is False


class TestWriteFileContent:
    """Test _write_file_content (re-exported from template_manager)."""

    def test_writes_content(self, tmp_path):
        """Writes content to file."""
        target = tmp_path / "test.yaml"
        _write_file_content(str(target), "key: value")
        assert target.exists()
        assert "key: value" in target.read_text()

    def test_overwrites_existing(self, tmp_path):
        """Overwrites existing file content."""
        target = tmp_path / "test.yaml"
        target.write_text("old")
        _write_file_content(str(target), "new")
        assert target.read_text() == "new"


class TestCheckPathExists:
    """Test _check_path_exists (re-exported from template_manager)."""

    def test_exists_true(self, tmp_path):
        """Returns True for existing file."""
        f = tmp_path / "exists"
        f.write_text("x")
        assert _check_path_exists(str(f)) is True

    def test_exists_false(self):
        """Returns False for missing file."""
        assert _check_path_exists("/nonexistent/file") is False


class TestCreateDirectory:
    """Test _create_directory (re-exported from template_manager)."""

    def test_creates_directory(self, tmp_path):
        """Creates a single directory."""
        target = tmp_path / "newdir"
        _create_directory(str(target))
        assert target.is_dir()

    def test_existing_no_error(self, tmp_path):
        """No error when directory already exists."""
        _create_directory(str(tmp_path))


class TestReadFileContent:
    """Test _read_file_content (re-exported from template_manager)."""

    def test_reads_existing_file(self, tmp_path):
        """Reads content from existing file."""
        f = tmp_path / "readme.txt"
        f.write_text("hello world")
        result = _read_file_content(str(f))
        assert result == "hello world"

    def test_raises_on_missing_file(self):
        """Raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            _read_file_content("/nonexistent/file.txt")


class TestVerifyStoragePermissions:
    """Test _verify_storage_permissions edge cases."""

    @pytest.mark.asyncio
    async def test_returns_false_when_storage_unavailable(self):
        """Returns False when HA storage Store creation fails."""
        mock_hass = MagicMock()
        mock_hass.config.components = set()

        with patch(
            "custom_components.ev_trip_planner.dashboard.importer._verify_storage",
            return_value=False,
        ):
            result = await _verify_storage_permissions(mock_hass, "test_vehicle")
            assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_storage_available(self):
        """Returns True when storage is available."""
        mock_hass = MagicMock()
        mock_hass.config.components = set()

        with patch(
            "custom_components.ev_trip_planner.dashboard.importer._verify_storage",
            return_value=True,
        ):
            result = await _verify_storage_permissions(mock_hass, "test_vehicle")
            assert result is True


class TestIsLovelaceAvailable:
    """Test is_lovelace_available edge cases."""

    def test_returns_true_when_lovelace_present(self):
        """Returns True when lovelace is in components."""
        hass = MagicMock()
        hass.config.components = {"lovelace", "sensor"}
        assert is_lovelace_available(hass) is True

    def test_returns_false_when_lovelace_absent(self):
        """Returns False when lovelace is not in components."""
        hass = MagicMock()
        hass.config.components = {"sensor", "binary_sensor"}
        hass.services.has_service = MagicMock(return_value=False)
        assert is_lovelace_available(hass) is False

    def test_returns_true_when_lovelace_service_present(self):
        """Returns True when lovelace import service exists."""
        hass = MagicMock()
        hass.config.components = {"sensor"}  # No lovelace in components
        hass.services.has_service = MagicMock(return_value=True)
        assert is_lovelace_available(hass) is True


class TestImportDashboard:
    """Test import_dashboard integration coverage."""

    @pytest.mark.asyncio
    async def test_fails_when_no_lovelace(self):
        """Fails when Lovelace is not available."""
        mock_hass = MagicMock()
        mock_hass.config.components = set()  # No lovelace

        result = await import_dashboard(
            mock_hass, "v1", "V1", False
        )
        assert isinstance(result, DashboardImportResult)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_fails_when_template_returns_none(self):
        """Fails when template loading returns None."""
        mock_hass = MagicMock()
        mock_hass.config.components = {"lovelace"}

        with patch(
            "custom_components.ev_trip_planner.dashboard.importer._load_template",
            return_value=None,
        ):
            result = await import_dashboard(
                mock_hass, "v1", "V1", False
            )
            assert isinstance(result, DashboardImportResult)
            assert result.success is False

    @pytest.mark.asyncio
    async def test_fails_on_validation_error(self):
        """Fails when template config fails validation."""

        mock_hass = MagicMock()
        mock_hass.config.components = {"lovelace"}

        # Return a config that will fail validation (empty views)
        bad_config = {"title": "Test", "views": []}

        with patch(
            "custom_components.ev_trip_planner.dashboard.importer._load_template",
            return_value=bad_config,
        ):
            result = await import_dashboard(
                mock_hass, "v1", "V1", False
            )
            assert isinstance(result, DashboardImportResult)
            assert result.success is False

    @pytest.mark.asyncio
    async def test_successful_via_yaml_fallback(self):
        """Successful YAML fallback returns success=True."""
        mock_hass = MagicMock()
        mock_hass.config.components = {"lovelace"}

        good_config = {
            "title": "Test",
            "views": [{"path": "v1", "title": "Test", "cards": []}],
        }

        with patch(
            "custom_components.ev_trip_planner.dashboard.importer._load_template",
            return_value=good_config,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard.importer._save_lovelace",
                return_value=DashboardImportResult(
                    success=False,
                    vehicle_id="v1",
                    vehicle_name="V1",
                ),
            ):
                with patch(
                    "custom_components.ev_trip_planner.dashboard.importer._save_yaml",
                    return_value=DashboardImportResult(
                        success=True,
                        vehicle_id="v1",
                        vehicle_name="V1",
                    ),
                ):
                    result = await import_dashboard(
                        mock_hass, "v1", "V1", False
                    )
                    assert isinstance(result, DashboardImportResult)
                    assert result.success is True

    @pytest.mark.asyncio
    async def test_fails_when_all_methods_fail(self):
        """Fails when both storage API and YAML fallback fail."""
        mock_hass = MagicMock()
        mock_hass.config.components = {"lovelace"}

        good_config = {
            "title": "Test",
            "views": [{"path": "v1", "title": "Test", "cards": []}],
        }

        with patch(
            "custom_components.ev_trip_planner.dashboard.importer._load_template",
            return_value=good_config,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard.importer._save_lovelace",
                return_value=DashboardImportResult(
                    success=False,
                    vehicle_id="v1",
                    vehicle_name="V1",
                ),
            ):
                with patch(
                    "custom_components.ev_trip_planner.dashboard.importer._save_yaml",
                    return_value=DashboardImportResult(
                        success=False,
                        vehicle_id="v1",
                        vehicle_name="V1",
                    ),
                ):
                    result = await import_dashboard(
                        mock_hass, "v1", "V1", False
                    )
                    assert isinstance(result, DashboardImportResult)
                    assert result.success is False

    @pytest.mark.asyncio
    async def test_fails_with_invalid_vehicle_id(self):
        """Fails with empty vehicle_id."""
        mock_hass = MagicMock()
        mock_hass.config.components = {"lovelace"}

        result = await import_dashboard(
            mock_hass, "", "V1", False
        )
        assert isinstance(result, DashboardImportResult)
        assert result.success is False
        assert result.error_details.get("validation") == "invalid_vehicle_id"

    @pytest.mark.asyncio
    async def test_successful_via_storage_api(self):
        """Successful storage API returns success=True."""
        mock_hass = MagicMock()
        mock_hass.config.components = {"lovelace"}

        good_config = {
            "title": "Test",
            "views": [{"path": "v1", "title": "Test", "cards": []}],
        }

        with patch(
            "custom_components.ev_trip_planner.dashboard.importer._load_template",
            return_value=good_config,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard.importer._save_lovelace",
                return_value=DashboardImportResult(
                    success=True,
                    vehicle_id="v1",
                    vehicle_name="V1",
                ),
            ):
                result = await import_dashboard(
                    mock_hass, "v1", "V1", False
                )
                assert isinstance(result, DashboardImportResult)
                assert result.success is True
