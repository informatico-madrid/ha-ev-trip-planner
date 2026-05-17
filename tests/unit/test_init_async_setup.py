"""Tests for __init__.py uncovered code paths.

Covers _hourly_refresh_callback (76-80), EVTripRuntimeData all fields.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner import (
    EVTripRuntimeData,
    _hourly_refresh_callback,
)


class TestHourlyRefreshCallback:
    """Test _hourly_refresh_callback (lines 76-80)."""

    @pytest.mark.asyncio
    async def test_callback_calls_publish(self):
        """Callback calls publish_deferrable_loads on _schedule sub-object."""
        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock()
        adapter = MagicMock()
        adapter.get_cached_optimization_results = MagicMock(
            return_value={
                "per_trip_emhass_params": {},
                "emhass_power_profile": [],
            }
        )
        coord = MagicMock()
        coord.async_refresh_trips = AsyncMock()
        rt = EVTripRuntimeData(
            coordinator=coord,
            trip_manager=mgr,
            emhass_adapter=adapter,
        )
        await _hourly_refresh_callback(None, rt)
        mgr._schedule.publish_deferrable_loads.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_callback_no_manager(self):
        """Callback is no-op when trip_manager is None."""
        rt = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=None,
        )
        # Should not raise
        await _hourly_refresh_callback(None, rt)

    @pytest.mark.asyncio
    async def test_callback_exception_logged(self):
        """Callback logs warning on exception but doesn't propagate."""
        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock(
            side_effect=RuntimeError("publish failed")
        )
        rt = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=mgr,
        )
        # Should not raise — exception is caught and logged
        await _hourly_refresh_callback(None, rt)


class TestEVTripRuntimeDataFields:
    """Test EVTripRuntimeData with all fields set."""

    def test_full_runtime_data(self):
        """All fields are accessible."""
        coord = MagicMock()
        mgr = MagicMock()
        cancel = MagicMock()
        emhass = MagicMock()
        add_entities = MagicMock()
        rt = EVTripRuntimeData(
            coordinator=coord,
            trip_manager=mgr,
            sensor_async_add_entities=add_entities,
            emhass_adapter=emhass,
            hourly_refresh_cancel=cancel,
        )
        assert rt.coordinator is coord
        assert rt.trip_manager is mgr
        assert rt.sensor_async_add_entities is add_entities
        assert rt.emhass_adapter is emhass
        assert rt.hourly_refresh_cancel is cancel

    def test_runtime_data_partial(self):
        """Partial fields use defaults."""
        rt = EVTripRuntimeData(coordinator=MagicMock())
        assert rt.trip_manager is None
        assert rt.sensor_async_add_entities is None
        assert rt.emhass_adapter is None
        assert rt.hourly_refresh_cancel is None
