"""Tests for dashboard.py validation and error paths.

Covers dashboard.py validation branches that return error results.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# Dashboard validation error paths
# =============================================================================

class TestDashboardImportValidation:
    """Tests for dashboard import validation branches."""

    @pytest.mark.asyncio
    async def test_import_with_empty_vehicle_id_returns_error(self):
        """Returns error when vehicle_id is empty string."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        # Mock Lovelace as available
        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            result = await import_dashboard(
                mock_hass,
                vehicle_id="",  # Empty
                vehicle_name="Test Vehicle",
            )

        assert result.success is False
        assert result.error_details.get("validation") == "invalid_vehicle_id"

    @pytest.mark.asyncio
    async def test_import_with_none_vehicle_id_returns_error(self):
        """Returns error when vehicle_id is None."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            result = await import_dashboard(
                mock_hass,
                vehicle_id=None,  # None
                vehicle_name="Test Vehicle",
            )

        assert result.success is False
        assert result.error_details.get("validation") == "invalid_vehicle_id"

    @pytest.mark.asyncio
    async def test_import_with_non_string_vehicle_id_returns_error(self):
        """Returns error when vehicle_id is not a string."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            result = await import_dashboard(
                mock_hass,
                vehicle_id=12345,  # Not a string
                vehicle_name="Test Vehicle",
            )

        assert result.success is False
        assert result.error_details.get("validation") == "invalid_vehicle_id"

    @pytest.mark.asyncio
    async def test_import_with_empty_vehicle_name_returns_error(self):
        """Returns error when vehicle_name is empty."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            result = await import_dashboard(
                mock_hass,
                vehicle_id="test_vehicle",
                vehicle_name="",  # Empty
            )

        assert result.success is False
        assert result.error_details.get("validation") == "invalid_vehicle_name"

    @pytest.mark.asyncio
    async def test_import_with_none_vehicle_name_returns_error(self):
        """Returns error when vehicle_name is None."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            result = await import_dashboard(
                mock_hass,
                vehicle_id="test_vehicle",
                vehicle_name=None,  # None
            )

        assert result.success is False
        assert result.error_details.get("validation") == "invalid_vehicle_name"

    @pytest.mark.asyncio
    async def test_import_when_lovelace_not_available_returns_error(self):
        """Returns error when Lovelace is not available."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=False,
        ):
            result = await import_dashboard(
                mock_hass,
                vehicle_id="test_vehicle",
                vehicle_name="Test Vehicle",
            )

        assert result.success is False
        assert "Lovelace" in result.error


# =============================================================================
# Dashboard template loading error paths
# =============================================================================

class TestDashboardTemplateLoading:
    """Tests for dashboard template loading branches."""

    @pytest.mark.asyncio
    async def test_template_load_returns_none_when_not_found(self):
        """Returns None when template not found."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard._load_dashboard_template",
                return_value=None,
            ):
                result = await import_dashboard(
                    mock_hass,
                    vehicle_id="test_vehicle",
                    vehicle_name="Test Vehicle",
                )

        assert result.success is False
        assert "Failed to load" in result.error

    @pytest.mark.asyncio
    async def test_template_load_raises_dashboardnotfound_error(self):
        """Propagates DashboardNotFoundError from template loading."""
        from custom_components.ev_trip_planner.dashboard import (
            import_dashboard,
            DashboardNotFoundError,
        )

        mock_hass = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard._load_dashboard_template",
                side_effect=DashboardNotFoundError(
                    "test.yaml", ["path1", "path2"]
                ),
            ):
                result = await import_dashboard(
                    mock_hass,
                    vehicle_id="test_vehicle",
                    vehicle_name="Test Vehicle",
                )

        assert result.success is False
        assert "Template not found" in result.error


# =============================================================================
# Dashboard storage error paths
# =============================================================================

class TestDashboardStorage:
    """Tests for dashboard storage branches."""

    @pytest.mark.asyncio
    async def test_storage_api_failure_falls_back_to_yaml(self):
        """When storage API fails, falls back to YAML."""
        from custom_components.ev_trip_planner.dashboard import (
            DashboardImportResult,
            import_dashboard,
        )

        mock_hass = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard._load_dashboard_template",
                return_value={"views": [{"title": "Test"}]},
            ):
                with patch(
                    "custom_components.ev_trip_planner.dashboard._validate_dashboard_config",
                ):
                    with patch(
                        "custom_components.ev_trip_planner.dashboard._save_lovelace_dashboard",
                        return_value=False,
                    ):
                        with patch(
                            "custom_components.ev_trip_planner.dashboard._save_dashboard_yaml_fallback",
                            return_value=DashboardImportResult(
                                success=True,
                                vehicle_id="test_vehicle",
                                vehicle_name="Test Vehicle",
                                dashboard_type="simple",
                                storage_method="yaml_fallback",
                            ),
                        ):
                            result = await import_dashboard(
                                mock_hass,
                                vehicle_id="test_vehicle",
                                vehicle_name="Test Vehicle",
                            )

        assert result.success is True
        assert result.storage_method == "yaml_fallback"

    @pytest.mark.asyncio
    async def test_save_lovelace_storage_result_object_false_triggers_yaml_fallback(self):
        """Regression test (RED): When _save_lovelace_dashboard returns a
        DashboardImportResult with success=False, import_dashboard must not
        treat it as truthy and must fall back to YAML.

        This test intentionally asserts the correct behavior; it should FAIL
        with the current code (bug: object truthiness treated as success).
        """
        from custom_components.ev_trip_planner.dashboard import (
            DashboardImportResult,
            import_dashboard,
        )

        mock_hass = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard._load_dashboard_template",
                return_value={"views": [{"title": "Test"}]},
            ):
                with patch(
                    "custom_components.ev_trip_planner.dashboard._validate_dashboard_config",
                ):
                    # _save_lovelace_dashboard returns a DashboardImportResult(success=False)
                    with patch(
                        "custom_components.ev_trip_planner.dashboard._save_lovelace_dashboard",
                        return_value=DashboardImportResult(
                            success=False,
                            vehicle_id="test_vehicle",
                            vehicle_name="Test Vehicle",
                            dashboard_type="simple",
                            storage_method="storage_api",
                        ),
                    ):
                        # YAML fallback succeeds
                        with patch(
                            "custom_components.ev_trip_planner.dashboard._save_dashboard_yaml_fallback",
                            return_value=DashboardImportResult(
                                success=True,
                                vehicle_id="test_vehicle",
                                vehicle_name="Test Vehicle",
                                dashboard_type="simple",
                                storage_method="yaml_fallback",
                            ),
                        ):
                            result = await import_dashboard(
                                mock_hass,
                                vehicle_id="test_vehicle",
                                vehicle_name="Test Vehicle",
                            )

        # Expected correct behavior: fallback to YAML and success
        assert result.success is True
        assert result.storage_method == "yaml_fallback"

    @pytest.mark.asyncio
    async def test_yaml_write_failure_returns_error(self):
        """When YAML write fails, returns error result with write_failure."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard._load_dashboard_template",
                return_value={
                    "title": "Test Dashboard",
                    "views": [
                        {
                            "title": "Test View",
                            "path": "test_view",
                            "cards": [{"type": "markdown", "content": "test"}],
                        }
                    ],
                },
            ):
                with patch(
                    "custom_components.ev_trip_planner.dashboard._validate_dashboard_config",
                ):
                    with patch(
                        "custom_components.ev_trip_planner.dashboard._save_lovelace_dashboard",
                        return_value=False,
                    ):
                        # Mock _write_file_content to raise an exception
                        # This simulates the YAML write failing
                        with patch(
                            "custom_components.ev_trip_planner.dashboard._write_file_content",
                            side_effect=Exception("YAML write failed"),
                        ):
                            result = await import_dashboard(
                                mock_hass,
                                vehicle_id="test_vehicle",
                                vehicle_name="Test Vehicle",
                            )

        # The fallback should handle the error and return success=False
        # with the appropriate error message
        assert result.success is False
        # When YAML write fails, the error is "All import methods failed"
        # because both storage API and YAML fallback failed
        assert result.error == "All import methods failed"

    @pytest.mark.asyncio
    async def test_template_load_exception_returns_error(self):
        """When template loading raises generic exception, returns error result."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard._load_dashboard_template",
                side_effect=RuntimeError("Template file corrupted"),
            ):
                result = await import_dashboard(
                    mock_hass,
                    vehicle_id="test_vehicle",
                    vehicle_name="Test Vehicle",
                )

        assert result.success is False
        assert "Unexpected error loading template" in result.error
        assert result.storage_method == "none"

    @pytest.mark.asyncio
    async def test_validation_error_missing_title(self):
        """When validation finds missing title, returns error."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        # Template without title - validation should fail
        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard._load_dashboard_template",
                return_value={"views": [{"title": "Test"}]},  # Missing title
            ):
                result = await import_dashboard(
                    mock_hass,
                    vehicle_id="test_vehicle",
                    vehicle_name="Test Vehicle",
                )

        assert result.success is False
        assert "title" in result.error.lower()
        assert result.storage_method == "none"

    @pytest.mark.asyncio
    async def test_validation_error_missing_views(self):
        """When validation finds missing views, returns error."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        # Template without views - validation should fail
        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard._load_dashboard_template",
                return_value={"title": "Test Dashboard"},  # Missing views
            ):
                result = await import_dashboard(
                    mock_hass,
                    vehicle_id="test_vehicle",
                    vehicle_name="Test Vehicle",
                )

        assert result.success is False
        assert "views" in result.error.lower()
        assert result.storage_method == "none"

    @pytest.mark.asyncio
    async def test_validation_error_empty_views(self):
        """When validation finds empty views list, returns error."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        # Template with empty views - validation should fail
        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard._load_dashboard_template",
                return_value={"title": "Test Dashboard", "views": []},
            ):
                result = await import_dashboard(
                    mock_hass,
                    vehicle_id="test_vehicle",
                    vehicle_name="Test Vehicle",
                )

        assert result.success is False
        assert "empty" in result.error.lower() or "views" in result.error.lower()
        assert result.storage_method == "none"

    @pytest.mark.asyncio
    async def test_validation_error_view_missing_path(self):
        """When validation finds view missing path, returns error."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        # Template with view missing path - validation should fail
        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard._load_dashboard_template",
                return_value={
                    "title": "Test Dashboard",
                    "views": [{"title": "Test View"}],  # Missing path
                },
            ):
                result = await import_dashboard(
                    mock_hass,
                    vehicle_id="test_vehicle",
                    vehicle_name="Test Vehicle",
                )

        assert result.success is False
        assert "path" in result.error.lower()
        assert result.storage_method == "none"

    @pytest.mark.asyncio
    async def test_validation_error_view_missing_cards(self):
        """When validation finds view missing cards, returns error."""
        from custom_components.ev_trip_planner.dashboard import import_dashboard

        mock_hass = MagicMock()

        # Template with view missing cards - validation should fail
        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard._load_dashboard_template",
                return_value={
                    "title": "Test Dashboard",
                    "views": [{"title": "Test View", "path": "test"}],
                },
            ):
                result = await import_dashboard(
                    mock_hass,
                    vehicle_id="test_vehicle",
                    vehicle_name="Test Vehicle",
                )

        assert result.success is False
        assert "cards" in result.error.lower()
        assert result.storage_method == "none"

    @pytest.mark.asyncio
    async def test_storage_api_exception_falls_back_to_yaml(self):
        """When storage API raises exception, falls back to YAML."""
        from custom_components.ev_trip_planner.dashboard import (
            DashboardImportResult,
            import_dashboard,
        )

        mock_hass = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.dashboard.is_lovelace_available",
            return_value=True,
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard._load_dashboard_template",
                return_value={
                    "title": "Test Dashboard",
                    "views": [
                        {
                            "title": "Test View",
                            "path": "test_view",
                            "cards": [{"type": "markdown", "content": "test"}],
                        }
                    ],
                },
            ):
                with patch(
                    "custom_components.ev_trip_planner.dashboard._validate_dashboard_config",
                ):
                    with patch(
                        "custom_components.ev_trip_planner.dashboard._save_lovelace_dashboard",
                        side_effect=Exception("Storage API error"),
                    ):
                        # YAML fallback succeeds
                        with patch(
                            "custom_components.ev_trip_planner.dashboard._save_dashboard_yaml_fallback",
                            return_value=DashboardImportResult(
                                success=True,
                                vehicle_id="test_vehicle",
                                vehicle_name="Test Vehicle",
                                dashboard_type="simple",
                                storage_method="yaml_fallback",
                            ),
                        ):
                            result = await import_dashboard(
                                mock_hass,
                                vehicle_id="test_vehicle",
                                vehicle_name="Test Vehicle",
                            )

        # Should fall back to YAML and succeed
        assert result.success is True
        assert result.storage_method == "yaml_fallback"


# =============================================================================
# Dashboard errors
# =============================================================================

class TestDashboardErrors:
    """Tests for DashboardError classes."""

    def test_dashboard_error_with_details(self):
        """DashboardError stores details dict."""
        from custom_components.ev_trip_planner.dashboard import DashboardError

        error = DashboardError("Test error", details={"key": "value"})

        assert error.message == "Test error"
        assert error.details == {"key": "value"}

    def test_dashboard_error_without_details(self):
        """DashboardError defaults details to empty dict."""
        from custom_components.ev_trip_planner.dashboard import DashboardError

        error = DashboardError("Test error")

        assert error.message == "Test error"
        assert error.details == {}

    def test_dashboard_storage_error(self):
        """DashboardStorageError stores storage_method and error."""
        from custom_components.ev_trip_planner.dashboard import DashboardStorageError

        error = DashboardStorageError("storage_api", "Failed to write")

        assert error.message == "Dashboard storage failed for storage_api: Failed to write"
        assert error.details["storage_method"] == "storage_api"
        assert error.details["error"] == "Failed to write"
        assert error.details["error_type"] == "storage_error"

    def test_dashboard_import_result_str_repr_success(self):
        """__str__ returns success string."""
        from custom_components.ev_trip_planner.dashboard import DashboardImportResult

        result = DashboardImportResult(
            success=True,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            dashboard_type="simple",
            storage_method="storage_api",
        )

        s = str(result)
        assert "SUCCESS" in s
        assert "Test Vehicle" in s
        assert "test_vehicle" in s

    def test_dashboard_import_result_str_repr_failure(self):
        """__str__ returns failure string with error details."""
        from custom_components.ev_trip_planner.dashboard import DashboardImportResult

        result = DashboardImportResult(
            success=False,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            error="Template not found",
            error_details={"validation": "invalid_vehicle_id"},
            dashboard_type="simple",
            storage_method="unknown",
        )

        s = str(result)
        assert "FAILED" in s
        assert "Error: Template not found" in s
        assert "Details:" in s

    def test_dashboard_import_result_to_dict(self):
        """DashboardImportResult.to_dict returns correct structure."""
        from custom_components.ev_trip_planner.dashboard import DashboardImportResult

        result = DashboardImportResult(
            success=True,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            dashboard_type="simple",
            storage_method="storage_api",
        )

        d = result.to_dict()
        assert d["success"] is True
        assert d["vehicle_id"] == "test_vehicle"
        assert d["dashboard_type"] == "simple"
        assert d["storage_method"] == "storage_api"


# =============================================================================
# Dashboard helper functions
# =============================================================================

class TestDashboardHelpers:
    """Tests for dashboard helper functions."""

    @pytest.mark.asyncio
    async def test_await_executor_result_with_coro(self):
        """_await_executor_result awaits coroutine objects."""
        from custom_components.ev_trip_planner.dashboard import _await_executor_result

        async def dummy():
            return 42

        result = await _await_executor_result(dummy())
        assert result == 42

    @pytest.mark.asyncio
    async def test_await_executor_result_with_direct_value(self):
        """_await_executor_result returns non-awaitable values directly."""
        from custom_components.ev_trip_planner.dashboard import _await_executor_result

        result = await _await_executor_result(42)
        assert result == 42


class TestCallAsyncExecutorSync:
    """Tests for _call_async_executor_sync helper function."""

    def test_call_async_executor_sync_without_attr(self):
        """_call_async_executor_sync falls back when hass has no async_add_executor_job."""
        from unittest.mock import MagicMock
        from custom_components.ev_trip_planner.dashboard import _call_async_executor_sync

        # Create mock hass without async_add_executor_job
        hass = MagicMock(spec=[])
        if hasattr(hass, "async_add_executor_job"):
            del hass.async_add_executor_job

        def dummy_func(a, b):
            return a + b

        result = _call_async_executor_sync(hass, dummy_func, 2, 3)
        assert result == 5
