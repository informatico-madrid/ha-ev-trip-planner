"""Execution tests for services/dashboard_helpers.py.

Covers create_dashboard_input_helpers, async_register_static_paths.
The panel and dashboard import functions use local `from ..` imports
that cannot be patched in unit tests; they are covered via integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.services.dashboard_helpers import (
    async_register_static_paths,
    create_dashboard_input_helpers,
)


class TestCreateDashboardInputHelpers:
    """Test create_dashboard_input_helpers helper."""

    @pytest.mark.asyncio
    async def test_create_input_helpers_success(self):
        """All input entity creation calls succeed."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()

        result = await create_dashboard_input_helpers(hass, "test_vehicle")

        assert result.success is True
        assert result.vehicle_id == "test_vehicle"
        assert hass.services.async_call.call_count == 15

    @pytest.mark.asyncio
    async def test_create_input_helpers_already_exist(self):
        """Service calls that already exist should log debug, not raise."""
        hass = MagicMock()
        hass.services = MagicMock()
        call_count = [0]

        async def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] > 10:
                raise Exception("Service already exists")
            return None

        hass.services.async_call = AsyncMock(side_effect=side_effect)

        result = await create_dashboard_input_helpers(hass, "test_vehicle")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_create_input_helpers_first_call_fails(self):
        """If the very first service call fails, the function continues
        (each service call is in its own try/except)."""
        hass = MagicMock()
        hass.services = MagicMock()

        async def side_effect(*args, **kwargs):
            raise Exception("First call failed")

        hass.services.async_call = AsyncMock(side_effect=side_effect)

        result = await create_dashboard_input_helpers(hass, "test_vehicle")

        # Each service call is in its own try/except, so first failure
        # does not prevent others from being attempted
        assert result.success is True
        assert hass.services.async_call.call_count == 15

    @pytest.mark.asyncio
    async def test_create_input_helpers_entity_names(self):
        """Each created entity should have the correct vehicle_id in name."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()

        await create_dashboard_input_helpers(hass, "my_car")

        for call in hass.services.async_call.call_args_list:
            args_list = call[0]
            if len(args_list) > 2:
                data = args_list[2]
                assert "my_car" in data.get("name", "")

    @pytest.mark.asyncio
    async def test_create_input_helpers_all_service_types(self):
        """All five service types should be called: input_select,
        input_datetime, input_number, input_text."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()

        await create_dashboard_input_helpers(hass, "vehicle_1")

        services_used = set()
        for call in hass.services.async_call.call_args_list:
            services_used.add(call[0][0])

        assert "input_select" in services_used
        assert "input_datetime" in services_used
        assert "input_number" in services_used
        assert "input_text" in services_used


class TestAsyncRegisterStaticPaths:
    """Test async_register_static_paths helper."""

    @pytest.mark.asyncio
    async def test_register_static_paths_no_files(self):
        """When static files don't exist, no paths registered."""
        with patch(
            "custom_components.ev_trip_planner.services.dashboard_helpers.Path.exists"
        ) as mock_exists:
            mock_exists.return_value = False
            hass = MagicMock()
            hass.http = MagicMock()
            hass.http.async_register_static_paths = AsyncMock()

            await async_register_static_paths(hass)

            hass.http.async_register_static_paths.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_static_paths_hass_http_none(self):
        """When hass.http is None, logs warning but does not raise."""
        with patch(
            "custom_components.ev_trip_planner.services.dashboard_helpers.Path.exists"
        ) as mock_exists:
            mock_exists.return_value = True
            hass = MagicMock()
            hass.http = None

            await async_register_static_paths(hass)

    @pytest.mark.asyncio
    async def test_register_static_paths_with_files(self):
        """When static files exist, paths are registered via hass.http."""
        with patch(
            "custom_components.ev_trip_planner.services.dashboard_helpers.Path.exists"
        ) as mock_exists:
            mock_exists.return_value = True
            hass = MagicMock()
            hass.http = MagicMock()
            hass.http.async_register_static_paths = AsyncMock()

            await async_register_static_paths(hass)

            hass.http.async_register_static_paths.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_static_paths_all_files_exist(self):
        """When all three static files exist, all paths are registered."""
        with patch(
            "custom_components.ev_trip_planner.services.dashboard_helpers.Path.exists"
        ) as mock_exists:
            mock_exists.return_value = True
            hass = MagicMock()
            hass.http = MagicMock()
            hass.http.async_register_static_paths = AsyncMock()

            await async_register_static_paths(hass)

            # Called with a list of 3 static path entries
            call_args = hass.http.async_register_static_paths.call_args[0][0]
            assert len(call_args) == 3
