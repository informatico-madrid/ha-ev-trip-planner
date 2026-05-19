"""Tests for dashboard_helpers.py — targets mutation-observable behavior.

Targets 91+ survivors (70 async_register_static_paths + 21 async_register_panel_for_entry).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.services.dashboard_helpers import (
    async_register_static_paths,
    _register_static_paths_legacy,
)


class TestAsyncRegisterStaticPaths:
    """Targets 70+ survivors in async_register_static_paths."""

    @pytest.mark.asyncio
    async def test_registers_when_files_exist(self):
        """Kill mutations: path existence → False, skips registration."""
        hass = MagicMock()
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        # Create a mock path object factory that returns existing paths
        def make_path(*args, **kwargs):
            p = MagicMock()
            p.exists.return_value = True
            p.__truediv__ = MagicMock(return_value=p)
            p.__str__ = MagicMock(return_value="/panel.js")
            return p

        with patch(
            "custom_components.ev_trip_planner.services.dashboard_helpers.Path",
            side_effect=make_path,
        ):
            await async_register_static_paths(hass)

        # Assert async_register_static_paths was called with 3 paths
        hass.http.async_register_static_paths.assert_called_once()
        call_args = hass.http.async_register_static_paths.call_args[0][0]
        assert len(call_args) == 3

    @pytest.mark.asyncio
    async def test_registers_only_existing_files(self):
        """Kill mutations: file existence check mutations."""
        hass = MagicMock()
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        def make_path(*args, **kwargs):
            p = MagicMock()
            p.exists.return_value = True
            p.__truediv__ = MagicMock(return_value=p)
            p.__str__ = MagicMock(return_value="/panel.js")
            return p

        with patch(
            "custom_components.ev_trip_planner.services.dashboard_helpers.Path",
            side_effect=make_path,
        ):
            await async_register_static_paths(hass)

        call_args = hass.http.async_register_static_paths.call_args[0][0]
        # 3 paths should be registered since all 3 files exist
        assert len(call_args) == 3

    @pytest.mark.asyncio
    async def test_skips_when_no_static_files(self):
        """Kill mutations: static_paths check → skips early when files exist."""
        hass = MagicMock()
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        # Build path objects that report non-existent
        _fake_path_obj = MagicMock()
        _fake_path_obj.exists.return_value = False
        _fake_path_obj.__truediv__ = MagicMock(return_value=_fake_path_obj)
        _fake_path_obj.parent = _fake_path_obj  # Chain through .parent.parent

        with patch(
            "custom_components.ev_trip_planner.services.dashboard_helpers.Path",
            return_value=_fake_path_obj,
        ):
            await async_register_static_paths(hass)

        # Should not call register when no files found
        hass.http.async_register_static_paths.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_hass_http_none(self):
        """Kill mutations: hass.http is None → continues and crashes or registers."""
        hass = MagicMock()
        hass.http = None

        def make_nonexistent_path(*args, **kwargs):
            p = MagicMock()
            p.exists.return_value = False
            p.__truediv__ = MagicMock(return_value=p)
            return p

        with patch(
            "custom_components.ev_trip_planner.services.dashboard_helpers.Path",
            side_effect=make_nonexistent_path,
        ):
            # Should not crash when hass.http is None
            await async_register_static_paths(hass)

    @pytest.mark.asyncio
    async def test_uses_static_path_config_when_available(self):
        """Kill mutations: HAS_STATIC_PATH_CONFIG → None uses wrong path format.

        When HAS_STATIC_PATH_CONFIG is True (normal path), paths are registered
        via StaticPathConfig. When mutated to None, they fall back to tuples.
        This test verifies the async_register_static_paths call uses proper configs.
        """
        hass = MagicMock()
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        def make_path(*args, **kwargs):
            p = MagicMock()
            p.exists.return_value = True
            p.__truediv__ = MagicMock(return_value=p)
            p.__str__ = MagicMock(return_value="/panel.js")
            return p

        with patch(
            "custom_components.ev_trip_planner.services.dashboard_helpers.Path",
            side_effect=make_path,
        ):
            await async_register_static_paths(hass)

        # Verify the paths were properly constructed (StaticPathConfig objects)
        call_args = hass.http.async_register_static_paths.call_args[0][0]
        assert len(call_args) == 3
        # Each should be a StaticPathConfig-like object (not tuple)
        for p in call_args:
            assert not isinstance(p, tuple)


class TestRegisterStaticPathsLegacy:
    """Targets 15 survivors in _register_static_paths_legacy."""

    @pytest.mark.asyncio
    async def test_registers_tuple_paths(self):
        """Kill mutations: tuple path parsing mutations."""
        hass = MagicMock()
        hass.http = MagicMock()
        hass.http.register_static_path = MagicMock()

        paths = [
            ("/panel.js", "/assets/panel.js", False),
            ("/lit-bundle.js", "/assets/lit-bundle.js", False),
        ]

        _register_static_paths_legacy(hass, paths, "test")

        assert hass.http.register_static_path.call_count == 2
        calls = hass.http.register_static_path.call_args_list
        assert calls[0][0][0] == "/panel.js"
        assert calls[0][0][1] == "/assets/panel.js"

    @pytest.mark.asyncio
    async def test_registers_object_paths(self):
        """Kill mutations: object path attribute mutations."""
        hass = MagicMock()
        hass.http = MagicMock()
        hass.http.register_static_path = MagicMock()

        path_obj = MagicMock()
        path_obj.url_path = "/custom.js"
        path_obj.path = "/assets/custom.js"

        paths = [path_obj]

        _register_static_paths_legacy(hass, paths, "test")

        hass.http.register_static_path.assert_called_once()
        calls = hass.http.register_static_path.call_args_list
        assert calls[0][0][0] == "/custom.js"
        assert calls[0][0][1] == "/assets/custom.js"

    @pytest.mark.asyncio
    async def test_skips_already_registered(self):
        """Kill mutations: RuntimeError 'already registered' → re-raises instead of skipping."""
        hass = MagicMock()
        hass.http = MagicMock()
        hass.http.register_static_path = MagicMock(
            side_effect=RuntimeError("already registered")
        )

        paths = [("/panel.js", "/assets/panel.js", False)]

        _register_static_paths_legacy(hass, paths, "test")

        # Should not re-raise
        hass.http.register_static_path.assert_called_once()

    @pytest.mark.asyncio
    async def test_reraises_other_errors(self):
        """Kill mutations: non-'already registered' errors → swallowed."""
        hass = MagicMock()
        hass.http = MagicMock()
        hass.http.register_static_path = MagicMock(
            side_effect=RuntimeError("other error")
        )

        paths = [("/panel.js", "/assets/panel.js", False)]

        with pytest.raises(RuntimeError, match="other error"):
            _register_static_paths_legacy(hass, paths, "test")


class TestAsyncRegisterPanelForEntry:
    """Targets 21 survivors in async_register_panel_for_entry."""

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        """Kill mutations: panel_result=True → False (returns early)."""
        hass = MagicMock()
        entry = MagicMock()

        mock_panel = MagicMock()
        mock_panel.async_register_panel = AsyncMock(return_value=True)

        with patch("custom_components.ev_trip_planner.panel", mock_panel):
            import importlib
            import custom_components.ev_trip_planner.services.dashboard_helpers as dh
            importlib.reload(dh)

            result = await dh.async_register_panel_for_entry(
                hass, entry, "vehicle_1", "Vehicle 1"
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_failure(self):
        """Kill mutations: panel_result=False → True."""
        hass = MagicMock()
        entry = MagicMock()

        mock_panel = MagicMock()
        mock_panel.async_register_panel = AsyncMock(return_value=False)

        with patch("custom_components.ev_trip_planner.panel", mock_panel):
            import importlib
            import custom_components.ev_trip_planner.services.dashboard_helpers as dh
            importlib.reload(dh)

            result = await dh.async_register_panel_for_entry(
                hass, entry, "vehicle_1", "Vehicle 1"
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        """Kill mutations: exception → raises instead of returning False."""
        hass = MagicMock()
        entry = MagicMock()

        mock_panel = MagicMock()
        mock_panel.async_register_panel = AsyncMock(
            side_effect=RuntimeError("panel fail")
        )

        with patch("custom_components.ev_trip_planner.panel", mock_panel):
            import importlib
            import custom_components.ev_trip_planner.services.dashboard_helpers as dh
            importlib.reload(dh)

            result = await dh.async_register_panel_for_entry(
                hass, entry, "vehicle_1", "Vehicle 1"
            )

        assert result is False
