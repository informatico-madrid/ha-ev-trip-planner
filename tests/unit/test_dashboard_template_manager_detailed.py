"""Detailed tests for dashboard/template_manager.py.

Covers validate_config edge cases, file I/O helpers, and DashboardConfig type.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from custom_components.ev_trip_planner.dashboard.template_manager import (
    DashboardConfig,
    _check_path_exists,
    _create_directory,
    _read_file_content,
    _write_file_content,
    validate_config,
)

from custom_components.ev_trip_planner.dashboard import (
    DashboardValidationError,
)


# ---------------------------------------------------------------------------
# DashboardConfig type alias
# ---------------------------------------------------------------------------


class TestDashboardConfigType:
    """Test DashboardConfig is dict[str, Any]."""

    def test_is_dict(self):
        """DashboardConfig is a plain dict."""
        config: DashboardConfig = {"title": "test", "views": []}
        assert isinstance(config, dict)

    def test_can_add_arbitrary_keys(self):
        """DashboardConfig accepts any string key."""
        config: DashboardConfig = {"custom_key": 42}
        assert config["custom_key"] == 42


# ---------------------------------------------------------------------------
# validate_config — happy path
# ---------------------------------------------------------------------------


class TestValidateConfigHappyPath:
    """Tests for valid dashboard configurations."""

    def test_valid_minimal_config(self):
        """A config with title, views (one valid view) passes validation."""
        config: DashboardConfig = {
            "title": "Test",
            "views": [
                {
                    "path": "test-path",
                    "title": "Test View",
                    "cards": [],
                }
            ],
        }
        # Should not raise
        validate_config(config, "test-vehicle")

    def test_valid_multi_view_config(self):
        """Config with multiple views passes validation."""
        config: DashboardConfig = {
            "title": "Multi",
            "views": [
                {"path": "p1", "title": "V1", "cards": []},
                {"path": "p2", "title": "V2", "cards": []},
            ],
        }
        validate_config(config, "vehicle")

    def test_valid_view_with_cards(self):
        """View with non-empty cards list is valid."""
        config: DashboardConfig = {
            "title": "T",
            "views": [{"path": "p", "title": "V", "cards": [{"type": "text"}]}],
        }
        validate_config(config, "v")


# ---------------------------------------------------------------------------
# validate_config — error paths
# ---------------------------------------------------------------------------


class TestValidateConfigErrors:
    """Tests for validation error paths."""

    def test_not_a_dict(self):
        """Non-dict config raises DashboardValidationError."""
        with pytest.raises(DashboardValidationError):
            validate_config("not a dict", "v")

    def test_missing_title(self):
        """Config without 'title' raises."""
        with pytest.raises(DashboardValidationError) as exc_info:
            validate_config({"views": []}, "v")
        assert "missing" in str(exc_info.value.message).lower() or "title" in str(
            exc_info.value.message
        ).lower()

    def test_missing_views(self):
        """Config without 'views' raises."""
        with pytest.raises(DashboardValidationError):
            validate_config({"title": "T"}, "v")

    def test_views_not_list(self):
        """views value that is not a list raises."""
        with pytest.raises(DashboardValidationError):
            validate_config({"title": "T", "views": "not a list"}, "v")

    def test_empty_views_list(self):
        """Empty views list raises DashboardValidationError."""
        with pytest.raises(DashboardValidationError):
            validate_config({"title": "T", "views": []}, "v")

    def test_view_not_dict(self):
        """A view element that is not a dict raises."""
        with pytest.raises(DashboardValidationError):
            validate_config({"title": "T", "views": ["string"]}, "v")

    def test_view_missing_path(self):
        """View missing 'path' raises with index in error."""
        with pytest.raises(DashboardValidationError) as exc_info:
            validate_config(
                {"title": "T", "views": [{"title": "V", "cards": []}]}, "v"
            )
        assert "index 0" in str(exc_info.value.message)

    def test_view_missing_title(self):
        """View missing 'title' raises with index in error."""
        with pytest.raises(DashboardValidationError) as exc_info:
            validate_config(
                {"title": "T", "views": [{"path": "p", "cards": []}]}, "v"
            )
        assert "index 0" in str(exc_info.value.message)

    def test_view_missing_cards(self):
        """View missing 'cards' raises with index in error."""
        with pytest.raises(DashboardValidationError) as exc_info:
            validate_config(
                {"title": "T", "views": [{"path": "p", "title": "V"}]}, "v"
            )
        assert "index 0" in str(exc_info.value.message)

    def test_view_index_in_error_message(self):
        """Error message includes the zero-based index of the bad view."""
        with pytest.raises(DashboardValidationError) as exc_info:
            validate_config(
                {
                    "title": "T",
                    "views": [{"path": "p", "title": "V", "cards": []}, {"cards": []}],
                },
                "v",
            )
        assert "index 1" in str(exc_info.value.message)


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------


class TestReadFileContent:
    """Tests for _read_file_content."""

    def test_read_existing_file(self, tmp_path: Path):
        """Read an existing file returns its content."""
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        result = _read_file_content(str(f))
        assert result == "hello world"

    def test_read_file_raises_on_missing(self, tmp_path: Path):
        """Reading a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _read_file_content(str(tmp_path / "nope.txt"))


class TestWriteFileContent:
    """Tests for _write_file_content."""

    def test_write_creates_file(self, tmp_path: Path):
        """Writing creates the file with correct content."""
        f = tmp_path / "out.txt"
        _write_file_content(str(f), "content")
        assert f.read_text(encoding="utf-8") == "content"

    def test_write_overwrites(self, tmp_path: Path):
        """Writing overwrites existing file."""
        f = tmp_path / "out.txt"
        f.write_text("old", encoding="utf-8")
        _write_file_content(str(f), "new")
        assert f.read_text(encoding="utf-8") == "new"


class TestCheckPathExists:
    """Tests for _check_path_exists."""

    def test_exists_true(self, tmp_path: Path):
        """_check_path_exists returns True for existing path."""
        assert _check_path_exists(str(tmp_path)) is True

    def test_exists_false(self, tmp_path: Path):
        """_check_path_exists returns False for non-existing path."""
        assert _check_path_exists(str(tmp_path / "nope")) is False

    def test_exists_file(self, tmp_path: Path):
        """_check_path_exists returns True for a file path."""
        f = tmp_path / "file.txt"
        f.write_text("x", encoding="utf-8")
        assert _check_path_exists(str(f)) is True


class TestCreateDirectory:
    """Tests for _create_directory."""

    def test_creates_directory(self, tmp_path: Path):
        """_create_directory creates the directory."""
        d = tmp_path / "subdir"
        _create_directory(str(d))
        assert d.is_dir()

    def test_create_existing_no_error(self, tmp_path: Path):
        """Creating an existing directory does not raise (exist_ok=True)."""
        d = tmp_path / "subdir"
        d.mkdir()
        _create_directory(str(d))  # should not raise
        assert d.is_dir()

    def test_creates_nested(self, tmp_path: Path):
        """_create_directory creates nested directories."""
        d = tmp_path / "a" / "b" / "c"
        _create_directory(str(d))
        assert d.is_dir()


# ---------------------------------------------------------------------------
# validate_config — vehicle_id in view paths
# ---------------------------------------------------------------------------


class TestValidateConfigVehicleId:
    """Tests for vehicle_id path matching in validate_config."""

    def test_vehicle_id_in_view_path_no_warning(self, caplog):
        """When vehicle_id is in view paths, no warning is logged."""
        config: DashboardConfig = {
            "title": "T",
            "views": [{"path": "my-vehicle-dashboard", "title": "V", "cards": []}],
        }
        validate_config(config, "my-vehicle")
        # No warning about vehicle_id not found
        assert not any(
            "Vehicle ID" in record.message for record in caplog.records
        )

    def test_vehicle_id_not_in_view_path_warns(self, caplog):
        """When vehicle_id is not in view paths, a warning is logged."""
        config: DashboardConfig = {
            "title": "T",
            "views": [{"path": "other-vehicle", "title": "V", "cards": []}],
        }
        validate_config(config, "my-vehicle")
        assert any(
            "Vehicle ID 'my-vehicle' not found in any view path" in record.message
            for record in caplog.records
        )
