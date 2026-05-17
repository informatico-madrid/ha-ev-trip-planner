"""Tests for uncovered services/dashboard_helpers.py paths (lines 28-41)."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.ev_trip_planner.services.dashboard_helpers import (
    _register_static_paths_legacy,
)


class TestRegisterStaticPathsLegacy:
    """Test _register_static_paths_legacy branches (lines 28-41)."""

    def test_tuple_path_spec_calls_register(self):
        """Lines 30-32: Tuple path_spec calls hass.http.register_static_path."""
        hass = MagicMock()
        static_paths = [
            ("/api/ev_trip_planner/test_vehicle", "/path/to/file.js", None),
        ]

        _register_static_paths_legacy(hass, static_paths, "test_context")

        hass.http.register_static_path.assert_called_once_with(
            "/api/ev_trip_planner/test_vehicle", "/path/to/file.js"
        )

    def test_object_path_spec_calls_register(self):
        """Lines 33-36: Object path_spec calls hass.http.register_static_path."""
        hass = MagicMock()
        mock_path_spec = MagicMock()
        mock_path_spec.url_path = "/api/ev_trip_planner/custom_path"
        mock_path_spec.path = "/path/to/custom.js"
        static_paths = [mock_path_spec]

        _register_static_paths_legacy(hass, static_paths, "test_context")

        hass.http.register_static_path.assert_called_once_with(
            "/api/ev_trip_planner/custom_path", "/path/to/custom.js"
        )

    def test_already_registered_continues(self):
        """Lines 37-40: RuntimeError with 'already registered' continues silently."""
        hass = MagicMock()
        hass.http.register_static_path.side_effect = RuntimeError(
            "Static path already registered"
        )
        static_paths = [("/existing", "/path.js", None)]

        # Should not raise — 'already registered' is caught and continued
        _register_static_paths_legacy(hass, static_paths, "test_context")

        # Called once, then caught and continued
        assert hass.http.register_static_path.call_count == 1

    def test_other_runtime_error_raises(self):
        """Line 40: RuntimeError without 'already registered' re-raises."""
        hass = MagicMock()
        hass.http.register_static_path.side_effect = RuntimeError(
            "Some other error"
        )
        static_paths = [("/new", "/path.js", None)]

        with __import__("pytest").raises(RuntimeError):
            _register_static_paths_legacy(hass, static_paths, "test_context")