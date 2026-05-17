"""Tests for custom_components/ev_trip_planner/__init__.py.

Covers async_migrate_entry, async_setup_entry, async_unload_entry,
async_remove_entry, _hourly_refresh_callback, EVTripRuntimeData.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.ev_trip_planner import (
    EVTripRuntimeData,
    async_migrate_entry,
    async_remove_entry,
    _hourly_refresh_callback,
)


class TestEVTripRuntimeData:
    """Test EVTripRuntimeData dataclass."""

    def test_runtime_data_basic(self) -> None:
        """RuntimeData should be instantiable with minimal args."""
        coord = MagicMock()
        rt = EVTripRuntimeData(coordinator=coord)
        assert rt.coordinator is coord
        assert rt.trip_manager is None
        assert rt.sensor_async_add_entities is None
        assert rt.emhass_adapter is None
        assert rt.hourly_refresh_cancel is None

    def test_runtime_data_full(self) -> None:
        """RuntimeData with all fields."""
        coord = MagicMock()
        mgr = MagicMock()
        cancel = MagicMock()
        emhass = MagicMock()
        rt = EVTripRuntimeData(
            coordinator=coord,
            trip_manager=mgr,
            emhass_adapter=emhass,
            hourly_refresh_cancel=cancel,
        )
        assert rt.trip_manager is mgr
        assert rt.emhass_adapter is emhass
        assert rt.hourly_refresh_cancel is cancel


class TestAsyncMigrateEntry:
    """Test async_migrate_entry."""

    @pytest.mark.asyncio
    async def test_migrate_no_change_version_2(self) -> None:
        """Entry version 2 should not be modified."""
        hass = MagicMock()
        entry = MagicMock()
        entry.version = 2
        entry.data = {"vehicle_name": "test"}
        entry.entry_id = "entry_1"
        entry.runtime_data = None

        result = await async_migrate_entry(hass, entry)
        assert result is True

    @pytest.mark.asyncio
    async def test_migrate_battery_capacity_rename(self) -> None:
        """Version 1 should rename battery_capacity -> battery_capacity_kwh."""
        hass = MagicMock()
        entry = MagicMock()
        entry.version = 1
        entry.data = {"vehicle_name": "test", "battery_capacity": 60}
        entry.entry_id = "entry_1"
        entry.runtime_data = None  # MagicMock auto-creates truthy mock
        hass.config_entries = MagicMock()

        result = await async_migrate_entry(hass, entry)
        assert result is True
        # The code calls async_update_entry(entry, data=new_data, version=2)
        # new_data has the renamed field. entry.data is also updated by HA.
        hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = hass.config_entries.async_update_entry.call_args
        new_data = call_kwargs[1]["data"]
        assert "battery_capacity" not in new_data
        assert new_data["battery_capacity_kwh"] == 60

    @pytest.mark.asyncio
    async def test_migrate_no_rename_needed(self) -> None:
        """Version 1 without battery_capacity should skip rename but still migrate."""
        hass = MagicMock()
        entry = MagicMock()
        entry.version = 1
        entry.data = {"vehicle_name": "test"}
        entry.entry_id = "entry_1"
        entry.runtime_data = None
        hass.config_entries = MagicMock()

        result = await async_migrate_entry(hass, entry)
        assert result is True
        hass.config_entries.async_update_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_migrate_entity_registry_migration(self) -> None:
        """Migration should migrate entity registry unique_ids."""
        hass = MagicMock()
        entry = MagicMock()
        entry.version = 1
        entry.data = {"vehicle_name": "test"}
        entry.entry_id = "entry_1"
        entry.runtime_data = None
        hass.config_entries = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.async_migrate_entries",
            new=AsyncMock(),
        ) as mock_migrate:
            result = await async_migrate_entry(hass, entry)
            assert result is True
            mock_migrate.assert_called_once()

    @pytest.mark.asyncio
    async def test_migrate_emhass_charging_power_update(self) -> None:
        """Migration should update charging power if emhass_adapter exists."""
        hass = MagicMock()
        entry = MagicMock()
        entry.version = 1
        entry.data = {"vehicle_name": "test", "battery_capacity": 60}
        entry.entry_id = "entry_1"
        entry.runtime_data = None
        hass.config_entries = MagicMock()

        emhass_adapter = MagicMock()
        emhass_adapter.update_charging_power = AsyncMock()

        runtime_data = MagicMock()
        runtime_data.emhass_adapter = emhass_adapter
        entry.runtime_data = runtime_data

        with patch(
            "custom_components.ev_trip_planner.async_migrate_entries",
            new=AsyncMock(),
        ):
            result = await async_migrate_entry(hass, entry)
            assert result is True
            emhass_adapter.update_charging_power.assert_called_once()


class TestAsyncRemoveEntry:
    """Test async_remove_entry."""

    @pytest.mark.asyncio
    async def test_async_remove_entry(self) -> None:
        """Should delegate to async_remove_entry_cleanup."""
        hass = MagicMock()
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "entry_1"

        with patch(
            "custom_components.ev_trip_planner.async_remove_entry_cleanup",
            new=AsyncMock(),
        ) as mock_cleanup:
            await async_remove_entry(hass, entry)
            mock_cleanup.assert_called_once_with(hass, entry)


class TestHourlyRefreshCallback:
    """Test _hourly_refresh_callback early return paths."""

    @pytest.mark.asyncio
    async def test_callback_runtime_data_none(self) -> None:
        """Lines 83-85: runtime_data is None returns early."""
        await _hourly_refresh_callback(None, None)

    @pytest.mark.asyncio
    async def test_callback_coordinator_none(self) -> None:
        """Lines 92-94: coordinator is None returns early."""
        runtime_data = EVTripRuntimeData(
            trip_manager=MagicMock(),
            emhass_adapter=MagicMock(),
            coordinator=None,
        )
        await _hourly_refresh_callback(None, runtime_data)

    @pytest.mark.asyncio
    async def test_callback_publish_exception(self) -> None:
        """Lines 109-116: publish_deferrable_loads raises Exception."""
        schedule = MagicMock()
        schedule.publish_deferrable_loads = AsyncMock(
            side_effect=RuntimeError("publish failed")
        )
        runtime_data = EVTripRuntimeData(
            trip_manager=MagicMock(),
            emhass_adapter=MagicMock(),
            coordinator=MagicMock(),
        )
        runtime_data.trip_manager._schedule = schedule
        runtime_data.emhass_adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {},
            "emhass_power_profile": [0, 100, 0],
        }
        await _hourly_refresh_callback(None, runtime_data)

    @pytest.mark.asyncio
    async def test_callback_post_cache_loop(self) -> None:
        """Line 126: post_cache per-trip debug log loop with params."""
        schedule = MagicMock()
        schedule.publish_deferrable_loads = AsyncMock()
        coord = MagicMock()
        coord.async_refresh_trips = AsyncMock()
        runtime_data = EVTripRuntimeData(
            trip_manager=MagicMock(),
            emhass_adapter=MagicMock(),
            coordinator=coord,
        )
        runtime_data.trip_manager._schedule = schedule
        runtime_data.emhass_adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {
                "trip_001": {
                    "def_start_timestep_array": [0, 1],
                    "def_end_timestep_array": [2, 3],
                    "def_total_hours_array": [4, 5],
                }
            },
            "emhass_power_profile": [0, 100, 0],
        }
        await _hourly_refresh_callback(None, runtime_data)

    @pytest.mark.asyncio
    async def test_callback_publish_cancelled(self) -> None:
        """Lines 114-116: publish_deferrable_loads raises BaseException (cancelled)."""
        schedule = MagicMock()
        # CancelledError is a BaseException (not Exception), catches at line 114
        schedule.publish_deferrable_loads = AsyncMock(
            side_effect=asyncio.CancelledError("task cancelled")
        )
        runtime_data = EVTripRuntimeData(
            trip_manager=MagicMock(),
            emhass_adapter=MagicMock(),
            coordinator=MagicMock(),
        )
        runtime_data.trip_manager._schedule = schedule
        runtime_data.emhass_adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {},
            "emhass_power_profile": [0, 100, 0],
        }
        await _hourly_refresh_callback(None, runtime_data)

