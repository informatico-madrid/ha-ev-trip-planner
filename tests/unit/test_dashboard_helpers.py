"""Tests for services/dashboard_helpers.py uncovered code paths.

Covers async_register_static_paths, async_register_panel_for_entry.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAsyncRegisterStaticPaths:
    """Test async_register_static_paths (lines 357-421)."""

    @pytest.mark.asyncio
    async def test_no_static_files_no_http(self, caplog):
        """No frontend files and hass.http is None → logs warning."""
        hass = MagicMock()
        hass.http = None

        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            async_register_static_paths,
        )

        def make_mock_file():
            mock = MagicMock()
            mock.exists.return_value = False

            def mock_truediv(path):
                return mock

            mock.__truediv__ = mock_truediv
            return mock

        with patch(
            "custom_components.ev_trip_planner.services.dashboard_helpers.Path"
        ) as mock_path_cls:
            mock_component_dir = MagicMock(spec=Path)
            mock_path_cls.return_value = mock_component_dir
            mock_component_dir.__truediv__ = MagicMock(
                side_effect=lambda p: make_mock_file()
            )

            await async_register_static_paths(hass)

        assert any("hass.http is None" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_files_exist_registers_paths(self):
        """Static files exist and hass.http is set → registers paths."""
        hass = MagicMock()
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            async_register_static_paths,
        )

        def make_mock_file(exists=True):
            mock = MagicMock()
            mock.exists.return_value = exists

            def mock_truediv(path):
                return mock

            mock.__truediv__ = mock_truediv
            return mock

        with patch(
            "custom_components.ev_trip_planner.services.dashboard_helpers.Path"
        ) as mock_path_cls:
            mock_component_dir = MagicMock(spec=Path)
            mock_path_cls.return_value = mock_component_dir

            mock_js = make_mock_file(True)
            mock_lit = make_mock_file(True)
            mock_css = make_mock_file(True)

            def mock_truediv_side_effect(path):
                if "panel.js" in path:
                    return mock_js
                elif "lit-bundle" in path:
                    return mock_lit
                elif "panel.css" in path:
                    return mock_css
                return make_mock_file(False)

            mock_component_dir.__truediv__ = MagicMock(
                side_effect=mock_truediv_side_effect
            )
            mock_path_cls.return_value = mock_component_dir

            await async_register_static_paths(hass)

        hass.http.async_register_static_paths.assert_called_once()

    @pytest.mark.asyncio
    async def test_hass_http_none_no_register(self, caplog):
        """hass.http is None → no paths registered, warning logged."""
        hass = MagicMock()
        hass.http = None

        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            async_register_static_paths,
        )

        def make_mock_file(exists=True):
            mock = MagicMock()
            mock.exists.return_value = exists

            def mock_truediv(path):
                return mock

            mock.__truediv__ = mock_truediv
            return mock

        with patch(
            "custom_components.ev_trip_planner.services.dashboard_helpers.Path"
        ) as mock_path_cls:
            mock_component_dir = MagicMock(spec=Path)
            mock_path_cls.return_value = mock_component_dir
            mock_component_dir.__truediv__ = MagicMock(
                side_effect=lambda p: make_mock_file(True)
            )

            await async_register_static_paths(hass)

        assert any("hass.http is None" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_static_path_count(self):
        """Three static paths (js, lit, css) → 3 paths registered."""
        hass = MagicMock()
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            async_register_static_paths,
        )

        def make_mock_file(exists=True):
            mock = MagicMock()
            mock.exists.return_value = exists

            def mock_truediv(path):
                return mock

            mock.__truediv__ = mock_truediv
            return mock

        with patch(
            "custom_components.ev_trip_planner.services.dashboard_helpers.Path"
        ) as mock_path_cls:
            mock_component_dir = MagicMock(spec=Path)
            mock_path_cls.return_value = mock_component_dir
            mock_component_dir.__truediv__ = MagicMock(
                side_effect=lambda p: make_mock_file(True)
            )

            await async_register_static_paths(hass)

        call_args = hass.http.async_register_static_paths.call_args
        paths = call_args[0][0]
        assert len(paths) == 3


class TestAsyncRegisterPanelForEntry:
    """Test async_register_panel_for_entry (lines 429-468)."""

    @pytest.mark.asyncio
    async def test_panel_registered_success(self):
        """Panel returns True → returns True."""
        hass = MagicMock()
        entry = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.panel.async_register_panel",
            new=AsyncMock(return_value=True),
        ):
            from custom_components.ev_trip_planner.services.dashboard_helpers import (
                async_register_panel_for_entry,
            )

            result = await async_register_panel_for_entry(
                hass, entry, "my_vehicle", "My Vehicle"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_panel_returns_false(self):
        """Panel returns False → returns False and logs error."""
        hass = MagicMock()
        entry = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.panel.async_register_panel",
            new=AsyncMock(return_value=False),
        ):
            from custom_components.ev_trip_planner.services.dashboard_helpers import (
                async_register_panel_for_entry,
            )

            result = await async_register_panel_for_entry(
                hass, entry, "my_vehicle", "My Vehicle"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_panel_raises_exception(self):
        """Panel raises → logs error and returns False."""
        hass = MagicMock()
        entry = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.panel.async_register_panel",
            new=AsyncMock(side_effect=RuntimeError("panel error")),
        ):
            from custom_components.ev_trip_planner.services.dashboard_helpers import (
                async_register_panel_for_entry,
            )

            result = await async_register_panel_for_entry(
                hass, entry, "my_vehicle", "My Vehicle"
            )
            assert result is False
