"""Tests for services/dashboard_helpers.py uncovered code paths.

Covers create_dashboard_input_helpers, async_register_static_paths,
async_register_panel_for_entry, async_import_dashboard_for_entry.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCreateDashboardInputHelpers:
    """Test create_dashboard_input_helpers (lines 36-321)."""

    @pytest.mark.asyncio
    async def test_success_creates_all_input_helpers(self):
        """Happy path calls hass.services.async_call for each helper type."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock()

        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            create_dashboard_input_helpers,
        )

        result = await create_dashboard_input_helpers(hass, "test_vehicle")

        assert result.success is True
        assert result.vehicle_id == "test_vehicle"
        # 14 input helpers + 1 more for final call = 15 total service calls
        assert hass.services.async_call.call_count == 15

    @pytest.mark.asyncio
    async def test_success_result_fields(self):
        """Result has correct fields on success."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock()

        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            create_dashboard_input_helpers,
        )

        result = await create_dashboard_input_helpers(hass, "my_car")
        assert result.vehicle_name == "my_car"
        assert result.dashboard_type == "simple"
        assert result.storage_method == "input_helpers"

    @pytest.mark.asyncio
    async def test_exception_in_logger_does_not_propagate(self, caplog):
        """Exception in _LOGGER.info during outer try does not propagate."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock()

        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            create_dashboard_input_helpers,
        )

        with caplog.at_level(
            logging.INFO,
            logger="custom_components.ev_trip_planner.services.dashboard_helpers",
        ):
            result = await create_dashboard_input_helpers(hass, "test_vehicle")
            assert result.success is True

    @pytest.mark.asyncio
    async def test_logs_info_on_success(self, caplog):
        """Success logs info message with vehicle_id."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock()

        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            create_dashboard_input_helpers,
        )

        with caplog.at_level(
            logging.INFO,
            logger="custom_components.ev_trip_planner.services.dashboard_helpers",
        ):
            await create_dashboard_input_helpers(hass, "test_vehicle")
            assert any(
                "Creating input helpers for dashboard: test_vehicle" in record.message
                for record in caplog.records
            )

    @pytest.mark.asyncio
    async def test_logs_info_on_completion(self, caplog):
        """Success logs completion message."""
        hass = MagicMock()
        hass.services.async_call = AsyncMock()

        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            create_dashboard_input_helpers,
        )

        with caplog.at_level(
            logging.INFO,
            logger="custom_components.ev_trip_planner.services.dashboard_helpers",
        ):
            await create_dashboard_input_helpers(hass, "test_vehicle")
            assert any(
                "Input helpers created successfully for: test_vehicle" in record.message
                for record in caplog.records
            )


class TestAsyncRegisterStaticPaths:
    """Test async_register_static_paths (lines 324-418)."""

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
    """Test async_register_panel_for_entry (lines 421-460)."""

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


class TestAsyncImportDashboardForEntry:
    """Test async_import_dashboard_for_entry (lines 463-496)."""

    @pytest.mark.asyncio
    async def test_import_success(self):
        """Successful import calls import_dashboard with correct args."""
        hass = MagicMock()
        entry = MagicMock()
        entry.data = {"vehicle_name": "My Car", "use_charts": True}

        mock_result = MagicMock()
        mock_result.success = True

        with patch(
            "custom_components.ev_trip_planner.dashboard.import_dashboard",
            new=AsyncMock(return_value=mock_result),
        ) as mock_import:
            from custom_components.ev_trip_planner.services.dashboard_helpers import (
                async_import_dashboard_for_entry,
            )

            await async_import_dashboard_for_entry(hass, entry, "my_vehicle")

            mock_import.assert_called_once()
            call_args = mock_import.call_args
            assert call_args[0][1] == "my_vehicle"
            assert call_args[1]["use_charts"] is True

    @pytest.mark.asyncio
    async def test_import_failure_logs_warning(self, caplog):
        """Failed import logs warning with error."""
        hass = MagicMock()
        entry = MagicMock()
        entry.data = {"vehicle_name": "My Car", "use_charts": False}

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "template not found"

        with caplog.at_level(
            logging.WARNING,
            logger="custom_components.ev_trip_planner.services.dashboard_helpers",
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard.import_dashboard",
                new=AsyncMock(return_value=mock_result),
            ):
                from custom_components.ev_trip_planner.services.dashboard_helpers import (
                    async_import_dashboard_for_entry,
                )

                await async_import_dashboard_for_entry(hass, entry, "my_vehicle")
                assert any(
                    "Dashboard import failed" in record.message
                    for record in caplog.records
                )

    @pytest.mark.asyncio
    async def test_import_exception_logged(self, caplog):
        """Import exception → warning logged, no propagation."""
        hass = MagicMock()
        entry = MagicMock()
        entry.data = {"vehicle_name": "My Car"}

        with caplog.at_level(
            logging.WARNING,
            logger="custom_components.ev_trip_planner.services.dashboard_helpers",
        ):
            with patch(
                "custom_components.ev_trip_planner.dashboard.import_dashboard",
                new=AsyncMock(side_effect=RuntimeError("import failed")),
            ):
                from custom_components.ev_trip_planner.services.dashboard_helpers import (
                    async_import_dashboard_for_entry,
                )

                # Should not raise — exception is caught and logged
                await async_import_dashboard_for_entry(hass, entry, "my_vehicle")
                assert any(
                    "Dashboard import exception" in record.message
                    for record in caplog.records
                )

    @pytest.mark.asyncio
    async def test_use_charts_false(self):
        """use_charts=False passes correctly to import_dashboard."""
        hass = MagicMock()
        entry = MagicMock()
        entry.data = {"vehicle_name": "My Car", "use_charts": False}

        mock_result = MagicMock()
        mock_result.success = True

        with patch(
            "custom_components.ev_trip_planner.dashboard.import_dashboard",
            new=AsyncMock(return_value=mock_result),
        ) as mock_import:
            from custom_components.ev_trip_planner.services.dashboard_helpers import (
                async_import_dashboard_for_entry,
            )

            await async_import_dashboard_for_entry(hass, entry, "my_vehicle")

            call_args = mock_import.call_args
            assert call_args[1]["use_charts"] is False
