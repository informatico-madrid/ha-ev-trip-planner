"""Detailed tests for dashboard/importer.py.

Covers is_lovelace_available, _call_async_executor_sync, dashboard_path,
and edge cases for importer helper functions.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.ev_trip_planner.dashboard.importer import (
    _call_async_executor_sync,
    _check_path_exists,
    _create_directory,
    _read_file_content,
    _write_file_content,
    dashboard_exists,
    dashboard_path,
)


# ---------------------------------------------------------------------------
# is_lovelace_available
# ---------------------------------------------------------------------------


class TestIsLovelaceAvailable:
    """Test is_lovelace_available function."""

    def test_lovelace_in_components(self):
        """Returns True when 'lovelace' is in hass.config.components."""
        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.components = ["lovelace"]
        hass.services = MagicMock()

        from custom_components.ev_trip_planner.dashboard.importer import (
            is_lovelace_available,
        )

        assert is_lovelace_available(hass) is True

    def test_lovelace_import_service(self):
        """Returns True when lovelace.import service exists."""
        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.components = []
        hass.services = MagicMock()
        hass.services.has_service.return_value = True

        from custom_components.ev_trip_planner.dashboard.importer import (
            is_lovelace_available,
        )

        assert is_lovelace_available(hass) is True

    def test_neither_lovelace_nor_service(self):
        """Returns False when no lovelace indicator."""
        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.components = ["sensor", "switch"]
        hass.services = MagicMock()
        hass.services.has_service.return_value = False

        from custom_components.ev_trip_planner.dashboard.importer import (
            is_lovelace_available,
        )

        assert is_lovelace_available(hass) is False


# ---------------------------------------------------------------------------
# _call_async_executor_sync
# ---------------------------------------------------------------------------


class TestCallAsyncExecutorSync:
    """Test _call_async_executor_sync helper."""

    def test_sync_fallback_no_async_method(self):
        """When hass has no async_add_executor_job, calls func directly."""
        hass = MagicMock()
        del hass.async_add_executor_job
        called = False

        def my_func(a, b):
            nonlocal called
            called = True
            return a + b

        result = _call_async_executor_sync(hass, my_func, 3, 4)
        assert called
        assert result == 7

    def test_sync_fallback_calls_func(self):
        """When async_add_executor_job exists but is not coroutine, calls func."""
        hass = MagicMock()
        # MagicMock.async_add_executor_job is not a coroutine function
        def my_func(x):
            return x * 2

        result = _call_async_executor_sync(hass, my_func, 5)
        # With MagicMock, async_add_executor_job exists but is not a coroutine
        # so it falls back to func(*args)
        assert result == 10

    def test_returns_func_result(self):
        """Result is the return value of func (not a coroutine)."""
        hass = MagicMock()

        def add(a, b):
            return a + b

        result = _call_async_executor_sync(hass, add, 10, 20)
        assert result == 30


# ---------------------------------------------------------------------------
# dashboard_exists
# ---------------------------------------------------------------------------


class TestDashboardExists:
    """Test dashboard_exists placeholder."""

    def test_returns_false(self):
        """Placeholder always returns False."""
        assert dashboard_exists("any-vehicle") is False

    def test_no_side_effects(self):
        """Does not raise or have side effects."""
        result = dashboard_exists("")
        assert result is False
        result = dashboard_exists("vehicle with spaces")
        assert result is False


# ---------------------------------------------------------------------------
# dashboard_path
# ---------------------------------------------------------------------------


class TestDashboardPath:
    """Test dashboard_path function."""

    def test_returns_correct_path(self):
        """Returns path with vehicle_id in filename."""
        path = dashboard_path("my-car")
        assert "my-car" in path
        assert path.endswith(".yaml")

    def test_path_format(self):
        """Path follows expected format."""
        path = dashboard_path("v1")
        expected = "config/dashboard/ev-trip-planner-v1.yaml"
        assert path == expected

    def test_different_vehicle_ids(self):
        """Different vehicle IDs produce different paths."""
        p1 = dashboard_path("car1")
        p2 = dashboard_path("car2")
        assert p1 != p2
        assert "car1" in p1
        assert "car2" in p2


# ---------------------------------------------------------------------------
# Wrapper helper re-exports
# ---------------------------------------------------------------------------


class TestHelperReExports:
    """Test that helper functions are importable and callable."""

    def test_check_path_exists_importable(self):
        """_check_path_exists is callable."""
        assert callable(_check_path_exists)

    def test_create_directory_importable(self):
        """_create_directory is callable."""
        assert callable(_create_directory)

    def test_read_file_content_importable(self):
        """_read_file_content is callable."""
        assert callable(_read_file_content)

    def test_write_file_content_importable(self):
        """_write_file_content is callable."""
        assert callable(_write_file_content)

    def test_check_path_exists_returns_bool(self):
        """_check_path_exists returns a boolean."""
        result = _check_path_exists("/tmp")
        assert isinstance(result, bool)

    def test_check_path_exists_false_for_nonexistent(self):
        """_check_path_exists returns False for nonexistent path."""
        result = _check_path_exists("/nonexistent/path/xyz123")
        assert result is False


class TestImporterPublicAPI:
    """Test that all importer public names are importable."""

    def test_import_dashboard_callable(self):
        """import_dashboard is importable and callable."""
        from custom_components.ev_trip_planner.dashboard.importer import (
            import_dashboard,
        )

        assert callable(import_dashboard)

    def test_is_lovelace_available_callable(self):
        """is_lovelace_available is importable and callable."""
        from custom_components.ev_trip_planner.dashboard.importer import (
            is_lovelace_available,
        )

        assert callable(is_lovelace_available)

    def test_await_executor_result_callable(self):
        """_await_executor_result is importable and async callable."""
        from custom_components.ev_trip_planner.dashboard.importer import (
            _await_executor_result,
        )

        assert callable(_await_executor_result)

    def test_validate_dashboard_config_callable(self):
        """_validate_dashboard_config is importable and callable."""
        from custom_components.ev_trip_planner.dashboard.importer import (
            _validate_dashboard_config,
        )

        assert callable(_validate_dashboard_config)

    def test_save_lovelace_dashboard_callable(self):
        """_save_lovelace_dashboard is importable."""
        from custom_components.ev_trip_planner.dashboard.importer import (
            _save_lovelace_dashboard,
        )

        assert callable(_save_lovelace_dashboard)
