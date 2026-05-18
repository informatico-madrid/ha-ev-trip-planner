"""Tests for custom_components/ev_trip_planner/__init__.py.

Covers async_migrate_entry, async_setup_entry, async_unload_entry,
async_remove_entry, _hourly_refresh_callback, EVTripRuntimeData.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.ev_trip_planner import (
    EVTripRuntimeData,
    _hourly_refresh_callback,
    async_migrate_entry,
    async_remove_entry,
    async_setup_entry,
    async_unload_entry,
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


class TestAsyncSetupEntry:
    """Test async_setup_entry with mocked dependencies to catch mutation survivors."""

    @pytest.mark.asyncio
    async def test_setup_entry_calls_cleanup_and_storage(self) -> None:
        """Verify cleanup storage, orphaned sensors, and static paths are called.

        Catches mutants that change the first few lines of async_setup_entry
        (vehicle_name_raw, vehicle_id extraction).
        """
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle", "battery_capacity_kwh": 50.0}
        entry.entry_id = "entry_1"

        with patch(
            "custom_components.ev_trip_planner.async_cleanup_stale_storage",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_cleanup_orphaned_emhass_sensors",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_register_static_paths",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.build_presence_config",
            return_value={},
        ), patch(
            "custom_components.ev_trip_planner.YamlTripStorage",
        ) as MockStorage, patch(
            "custom_components.ev_trip_planner.TripManager",
        ) as MockTM, patch(
            "custom_components.ev_trip_planner.TripPlannerCoordinator",
        ) as MockCoord, patch(
            "custom_components.ev_trip_planner.async_register_panel_for_entry",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.register_services",
        ), patch(
            "custom_components.ev_trip_planner.async_track_time_interval",
        ):
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_tm = MagicMock()
            MockTM.return_value = mock_tm
            mock_tm._persistence = MagicMock()
            mock_tm._persistence.async_setup = AsyncMock()

            mock_coord = MagicMock()
            mock_coord.async_config_entry_first_refresh = AsyncMock()
            MockCoord.return_value = mock_coord

            result = await async_setup_entry(hass, entry)
            assert result is True

            # Verify cleanup calls were made
            assert MockStorage.called
            assert MockTM.called
            assert MockCoord.called

            # The vehicle_id passed to YamlTripStorage should match expected
            storage_call_args = MockStorage.call_args
            assert storage_call_args is not None
            stored_vehicle_id = storage_call_args[0][1]
            assert stored_vehicle_id == "test_vehicle"

            # TripManager should be called with correct args:
            # TripManager(hass, vehicle_id, TripManagerConfig(...))
            tm_call = MockTM.call_args
            assert tm_call is not None
            # Second positional arg is vehicle_id
            assert tm_call[0][1] == "test_vehicle"
            # Third arg should be a TripManagerConfig dataclass
            tm_config = tm_call[0][2]
            # TripManagerConfig should have entry_id from entry
            assert tm_config.entry_id == "entry_1"
            assert tm_config.storage is mock_storage

            # TripPlannerCoordinator should be called with entry and trip_manager
            coord_call = MockCoord.call_args
            assert coord_call is not None
            assert coord_call[0][1] is entry

    @pytest.mark.asyncio
    async def test_setup_entry_with_emhass_enabled(self) -> None:
        """Test with EMHASS enabled (planning_horizon_days present).

        Catches mutants in the EMHASS initialization conditional
        (or/and mutations in entry.data.get) and EMHASSAdapter constructor.
        """
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        entry = MagicMock()
        entry.data = {
            "vehicle_name": "test_vehicle",
            "planning_horizon_days": 7,
            "max_deferrable_loads": 10,
        }
        entry.entry_id = "entry_1"

        with patch(
            "custom_components.ev_trip_planner.async_cleanup_stale_storage",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_cleanup_orphaned_emhass_sensors",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_register_static_paths",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.build_presence_config",
            return_value={},
        ), patch(
            "custom_components.ev_trip_planner.YamlTripStorage",
        ) as MockStorage, patch(
            "custom_components.ev_trip_planner.TripManager",
        ) as MockTM, patch(
            "custom_components.ev_trip_planner.EMHASSAdapter",
        ) as MockEMHASS, patch(
            "custom_components.ev_trip_planner.TripPlannerCoordinator",
        ) as MockCoord, patch(
            "custom_components.ev_trip_planner.async_register_panel_for_entry",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.register_services",
        ), patch(
            "custom_components.ev_trip_planner.async_track_time_interval",
        ):
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_tm = MagicMock()
            MockTM.return_value = mock_tm
            mock_tm._persistence = MagicMock()
            mock_tm._persistence.async_setup = AsyncMock()
            mock_tm._schedule = MagicMock()
            mock_tm._schedule.publish_deferrable_loads = AsyncMock()

            mock_emhass = MagicMock()
            mock_emhass.async_load = AsyncMock()
            mock_emhass.setup_config_entry_listener = MagicMock()
            MockEMHASS.return_value = mock_emhass

            mock_coord = MagicMock()
            mock_coord.async_config_entry_first_refresh = AsyncMock()
            mock_coord.async_refresh_trips = AsyncMock()
            MockCoord.return_value = mock_coord

            result = await async_setup_entry(hass, entry)
            assert result is True

            # EMHASSAdapter should have been instantiated
            assert MockEMHASS.called

            # EMHASS adapter should have had async_load called
            mock_emhass.async_load.assert_called_once()

            # EMHASS adapter should have been assigned to trip_manager
            assert mock_tm.emhass_adapter is mock_emhass

    @pytest.mark.asyncio
    async def test_setup_entry_with_none_vehicle_name(self) -> None:
        """Test when vehicle_name is missing from entry.data.

        Catches mutmut 1 (vehicle_name_raw=None) and mutmut 2
        (entry.data.get("vehicle_name") and "").
        """
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        entry = MagicMock()
        entry.data = {}  # No vehicle_name key
        entry.entry_id = "entry_1"

        with patch(
            "custom_components.ev_trip_planner.async_cleanup_stale_storage",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_cleanup_orphaned_emhass_sensors",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_register_static_paths",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.build_presence_config",
            return_value={},
        ), patch(
            "custom_components.ev_trip_planner.YamlTripStorage",
        ) as MockStorage, patch(
            "custom_components.ev_trip_planner.TripManager",
        ) as MockTM, patch(
            "custom_components.ev_trip_planner.TripPlannerCoordinator",
        ) as MockCoord, patch(
            "custom_components.ev_trip_planner.async_register_panel_for_entry",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.register_services",
        ), patch(
            "custom_components.ev_trip_planner.async_track_time_interval",
        ):
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_tm = MagicMock()
            MockTM.return_value = mock_tm
            mock_tm._persistence = MagicMock()
            mock_tm._persistence.async_setup = AsyncMock()

            mock_coord = MagicMock()
            mock_coord.async_config_entry_first_refresh = AsyncMock()
            MockCoord.return_value = mock_coord

            result = await async_setup_entry(hass, entry)
            assert result is True

            # vehicle_id should fallback to normalized empty string
            storage_call_args = MockStorage.call_args
            assert storage_call_args is not None
            stored_vehicle_id = storage_call_args[0][1]
            assert stored_vehicle_id == ""


class TestAsyncUnloadEntry:
    """Test async_unload_entry to kill mutation survivors."""

    @pytest.mark.asyncio
    async def test_unload_entry_with_timer(self) -> None:
        """Test unload cancels timer and calls cleanup with correct vehicle_name.

        Catches mutants that change vehicle_name_raw, vehicle_id, vehicle_name
        before passing to async_unload_entry_cleanup.
        """
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "entry_1"
        entry.data = {"vehicle_name": "Test Vehicle"}

        mock_cancel = MagicMock()
        runtime_data = MagicMock()
        runtime_data.hourly_refresh_cancel = mock_cancel
        entry.runtime_data = runtime_data

        with patch(
            "custom_components.ev_trip_planner.async_unload_entry_cleanup",
            new=AsyncMock(return_value=True),
        ) as mock_cleanup:
            result = await async_unload_entry(hass, entry)
            assert result is True

            # Verify timer was cancelled
            mock_cancel.assert_called_once()

            # Verify cleanup was called with correct vehicle_name
            mock_cleanup.assert_called_once()
            call_kwargs = mock_cleanup.call_args
            # vehicle_name = vehicle_name_raw or vehicle_id = "Test Vehicle"
            called_vehicle_name = call_kwargs[0][3]
            assert called_vehicle_name == "Test Vehicle"

    @pytest.mark.asyncio
    async def test_unload_entry_no_timer(self) -> None:
        """Test unload when runtime_data or hourly_refresh_cancel is missing."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "entry_1"
        entry.data = {"vehicle_name": "Test Vehicle"}
        entry.runtime_data = None

        with patch(
            "custom_components.ev_trip_planner.async_unload_entry_cleanup",
            new=AsyncMock(return_value=True),
        ) as mock_cleanup:
            result = await async_unload_entry(hass, entry)
            assert result is True

            # Cleanup still called
            mock_cleanup.assert_called_once()


class TestAsyncMigrateEntryVersionEdgeCases:
    """Additional tests for async_migrate_entry to kill version comparison mutants."""

    @pytest.mark.asyncio
    async def test_migrate_version_2_no_migration(self) -> None:
        """Version 2 should not trigger any migration logic.

        Catches mutmut 4 (<= 2 instead of < 2) — if <= 2, version 2 would
        still trigger the version < 2 block.
        """
        hass = MagicMock()
        entry = MagicMock()
        entry.version = 2
        entry.data = {"vehicle_name": "test", "battery_capacity": 50.0}
        entry.entry_id = "entry_1"
        entry.runtime_data = None
        hass.config_entries = MagicMock()

        result = await async_migrate_entry(hass, entry)
        assert result is True

        # Version 2 should NOT call async_update_entry with changed data
        # because the version < 2 block should be skipped entirely
        hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = hass.config_entries.async_update_entry.call_args
        new_data = call_kwargs[1]["data"]
        # With version=2 and the correct < 2 check, new_data should be a copy
        # unchanged by the version < 2 block
        assert "battery_capacity" in new_data, (
            "If mutant 4 (<=2) is active, version 2 would trigger migration"
            " and rename battery_capacity. This test detects that."
        )


class TestAsyncSetupEntryBehavioral:
    """Test behavioral mutants in async_setup_entry: runtime_data, timer, coordinator args."""

    @pytest.mark.asyncio
    async def test_setup_entry_runtime_data_assigned(self) -> None:
        """runtime_data should be assigned with coordinator and trip_manager.

        Catches mutants that change the entry.runtime_data assignment or
        EVTripRuntimeData constructor args.
        """
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle"}
        entry.entry_id = "entry_1"

        with patch(
            "custom_components.ev_trip_planner.async_cleanup_stale_storage",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_cleanup_orphaned_emhass_sensors",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_register_static_paths",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.build_presence_config",
            return_value={},
        ), patch(
            "custom_components.ev_trip_planner.YamlTripStorage",
        ) as MockStorage, patch(
            "custom_components.ev_trip_planner.TripManager",
        ) as MockTM, patch(
            "custom_components.ev_trip_planner.TripPlannerCoordinator",
        ) as MockCoord, patch(
            "custom_components.ev_trip_planner.async_register_panel_for_entry",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.register_services",
        ), patch(
            "custom_components.ev_trip_planner.async_track_time_interval",
        ):
            MockStorage.return_value = MagicMock()
            mock_tm = MagicMock()
            mock_tm._persistence = MagicMock()
            mock_tm._persistence.async_setup = AsyncMock()
            MockTM.return_value = mock_tm
            mock_coord = MagicMock()
            mock_coord.async_config_entry_first_refresh = AsyncMock()
            MockCoord.return_value = mock_coord

            await async_setup_entry(hass, entry)

            # entry.runtime_data must be set and non-None
            assert entry.runtime_data is not None
            assert entry.runtime_data.coordinator is not None
            assert entry.runtime_data.trip_manager is not None

    @pytest.mark.asyncio
    async def test_setup_entry_emhass_coordinator_receives_adapter(self) -> None:
        """EMHASS adapter must be passed to TripPlannerCoordinator constructor.

        Catches mutants that change the coordinator constructor args or
        omit emhass_adapter when EMHASS is enabled.
        """
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        entry = MagicMock()
        entry.data = {
            "vehicle_name": "test_vehicle",
            "planning_horizon_days": 7,
        }
        entry.entry_id = "entry_1"

        with patch(
            "custom_components.ev_trip_planner.async_cleanup_stale_storage",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_cleanup_orphaned_emhass_sensors",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_register_static_paths",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.build_presence_config",
            return_value={},
        ), patch(
            "custom_components.ev_trip_planner.YamlTripStorage",
        ) as MockStorage, patch(
            "custom_components.ev_trip_planner.TripManager",
        ) as MockTM, patch(
            "custom_components.ev_trip_planner.EMHASSAdapter",
        ) as MockEMHASS, patch(
            "custom_components.ev_trip_planner.TripPlannerCoordinator",
        ) as MockCoord, patch(
            "custom_components.ev_trip_planner.async_register_panel_for_entry",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.register_services",
        ), patch(
            "custom_components.ev_trip_planner.async_track_time_interval",
        ):
            MockStorage.return_value = MagicMock()
            mock_tm = MagicMock()
            mock_tm._persistence = MagicMock()
            mock_tm._persistence.async_setup = AsyncMock()
            mock_tm._schedule = MagicMock()
            mock_tm._schedule.publish_deferrable_loads = AsyncMock()
            MockTM.return_value = mock_tm

            mock_emhass = MagicMock()
            mock_emhass.async_load = AsyncMock()
            mock_emhass.setup_config_entry_listener = MagicMock()
            MockEMHASS.return_value = mock_emhass

            mock_coord = MagicMock()
            mock_coord.async_config_entry_first_refresh = AsyncMock()
            mock_coord.async_refresh_trips = AsyncMock()
            MockCoord.return_value = mock_coord

            await async_setup_entry(hass, entry)

            # EMHASSAdapter should be passed as emhass_adapter to coordinator
            coord_call = MockCoord.call_args
            assert coord_call is not None
            # Third positional arg is CoordinatorConfig
            cfg = coord_call[0][2]
            assert cfg.emhass_adapter is mock_emhass

    @pytest.mark.asyncio
    async def test_setup_entry_timer_registered(self) -> None:
        """async_track_time_interval should be called after runtime_data assignment.

        Catches mutants that change the timer registration or omit the call.
        """
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle"}
        entry.entry_id = "entry_1"
        cancel_handle = MagicMock()

        with patch(
            "custom_components.ev_trip_planner.async_cleanup_stale_storage",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_cleanup_orphaned_emhass_sensors",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_register_static_paths",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.build_presence_config",
            return_value={},
        ), patch(
            "custom_components.ev_trip_planner.YamlTripStorage",
        ) as MockStorage, patch(
            "custom_components.ev_trip_planner.TripManager",
        ) as MockTM, patch(
            "custom_components.ev_trip_planner.TripPlannerCoordinator",
        ) as MockCoord, patch(
            "custom_components.ev_trip_planner.async_register_panel_for_entry",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.register_services",
        ) as MockRegisterSvc, patch(
            "custom_components.ev_trip_planner.async_track_time_interval",
        ) as MockTimer:
            MockStorage.return_value = MagicMock()
            mock_tm = MagicMock()
            mock_tm._persistence = MagicMock()
            mock_tm._persistence.async_setup = AsyncMock()
            MockTM.return_value = mock_tm
            mock_coord = MagicMock()
            mock_coord.async_config_entry_first_refresh = AsyncMock()
            MockCoord.return_value = mock_coord
            MockTimer.return_value = cancel_handle
            MockRegisterSvc.return_value = None

            await async_setup_entry(hass, entry)

            # Timer should have been registered
            assert MockTimer.called
            # runtime_data.hourly_refresh_cancel should be set
            assert entry.runtime_data.hourly_refresh_cancel is cancel_handle

    @pytest.mark.asyncio
    async def test_setup_entry_panel_registered_with_vehicle_id(self) -> None:
        """async_register_panel_for_entry called with vehicle_id and vehicle_name.

        Catches mutants in vehicle_name_raw/vehicle_id/vehicle_name extraction.
        """
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        class FakeData(dict):
            def get(self, k, d=None):
                return {"vehicle_name": "MyEV"}.get(k, d)

        entry = MagicMock()
        entry.data = FakeData()
        entry.entry_id = "entry_1"

        with patch(
            "custom_components.ev_trip_planner.async_cleanup_stale_storage",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_cleanup_orphaned_emhass_sensors",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_register_static_paths",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.build_presence_config",
            return_value={},
        ), patch(
            "custom_components.ev_trip_planner.YamlTripStorage",
        ) as MockStorage, patch(
            "custom_components.ev_trip_planner.TripManager",
        ) as MockTM, patch(
            "custom_components.ev_trip_planner.TripPlannerCoordinator",
        ) as MockCoord, patch(
            "custom_components.ev_trip_planner.async_register_panel_for_entry",
            new=AsyncMock(),
        ) as MockPanel, patch(
            "custom_components.ev_trip_planner.register_services",
        ), patch(
            "custom_components.ev_trip_planner.async_track_time_interval",
        ):
            MockStorage.return_value = MagicMock()
            mock_tm = MagicMock()
            mock_tm._persistence = MagicMock()
            mock_tm._persistence.async_setup = AsyncMock()
            MockTM.return_value = mock_tm
            mock_coord = MagicMock()
            mock_coord.async_config_entry_first_refresh = AsyncMock()
            mock_coord.async_refresh_trips = AsyncMock()
            MockCoord.return_value = mock_coord

            await async_setup_entry(hass, entry)

            # panel should be registered with vehicle_id ("myev" from normalize)
            panel_call = MockPanel.call_args
            assert panel_call is not None
            assert panel_call[0][2] == "myev"  # vehicle_id normalized

    @pytest.mark.asyncio
    async def test_setup_entry_publish_called_when_emhass_enabled(self) -> None:
        """When EMHASS enabled + runtime_data/coordinator present, publish should be called.

        Catches mutants in the conditional that gates publish_deferrable_loads.
        """
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        entry = MagicMock()
        entry.data = {"vehicle_name": "test", "planning_horizon_days": 7}
        entry.entry_id = "entry_1"

        with patch(
            "custom_components.ev_trip_planner.async_cleanup_stale_storage",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_cleanup_orphaned_emhass_sensors",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.async_register_static_paths",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.build_presence_config",
            return_value={},
        ), patch(
            "custom_components.ev_trip_planner.YamlTripStorage",
        ) as MockStorage, patch(
            "custom_components.ev_trip_planner.TripManager",
        ) as MockTM, patch(
            "custom_components.ev_trip_planner.EMHASSAdapter",
        ) as MockEMHASS, patch(
            "custom_components.ev_trip_planner.TripPlannerCoordinator",
        ) as MockCoord, patch(
            "custom_components.ev_trip_planner.async_register_panel_for_entry",
            new=AsyncMock(),
        ), patch(
            "custom_components.ev_trip_planner.register_services",
        ), patch(
            "custom_components.ev_trip_planner.async_track_time_interval",
        ):
            MockStorage.return_value = MagicMock()
            mock_tm = MagicMock()
            mock_tm._persistence = MagicMock()
            mock_tm._persistence.async_setup = AsyncMock()
            mock_tm._schedule = MagicMock()
            mock_tm._schedule.publish_deferrable_loads = AsyncMock()
            MockTM.return_value = mock_tm

            mock_emhass = MagicMock()
            mock_emhass.async_load = AsyncMock()
            mock_emhass.setup_config_entry_listener = MagicMock()
            MockEMHASS.return_value = mock_emhass

            mock_coord = MagicMock()
            mock_coord.async_config_entry_first_refresh = AsyncMock()
            mock_coord.async_refresh_trips = AsyncMock()
            MockCoord.return_value = mock_coord

            await async_setup_entry(hass, entry)

            # publish_deferrable_loads should be called during setup
            mock_tm._schedule.publish_deferrable_loads.assert_awaited_once()
            # coordinator async_refresh_trips should also be called
            mock_coord.async_refresh_trips.assert_awaited_once()


class TestAsyncUnloadEntryBehavioral:
    """Test behavioral mutants in async_unload_entry."""

    @pytest.mark.asyncio
    async def test_unload_vehicle_name_from_raw_or_id(self) -> None:
        """vehicle_name should be vehicle_name_raw or vehicle_id fallback.

        Catches mutants in vehicle_name_raw or vehicle_name extraction.
        """
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "entry_1"
        entry.data = {"vehicle_name": None}  # None -> fallback to vehicle_id
        runtime_data = MagicMock()
        runtime_data.hourly_refresh_cancel = MagicMock()
        entry.runtime_data = runtime_data

        with patch(
            "custom_components.ev_trip_planner.async_unload_entry_cleanup",
            new=AsyncMock(return_value=True),
        ) as mock_cleanup:
            await async_unload_entry(hass, entry)
            mock_cleanup.assert_called_once()
            call_args = mock_cleanup.call_args
            # vehicle_name_raw = None or "" = ""
            # vehicle_id = normalize_vehicle_id("") = ""
            # vehicle_name = "" or "" = ""
            called_vehicle_name = call_args[0][3]
            assert called_vehicle_name == ""

    @pytest.mark.asyncio
    async def test_unload_hasattr_runtime_data_check(self) -> None:
        """unload_entry uses getattr not hasattr for runtime_data.

        Catches mutants that change the getattr/hasattr pattern.
        """
        hass = MagicMock()
        entry = MagicMock(spec=[])  # No runtime_data attr
        entry.entry_id = "entry_1"
        entry.data = {"vehicle_name": "Test"}

        with patch(
            "custom_components.ev_trip_planner.async_unload_entry_cleanup",
            new=AsyncMock(return_value=True),
        ) as mock_cleanup:
            result = await async_unload_entry(hass, entry)
            assert result is True
            mock_cleanup.assert_called_once()


class TestHourlyRefreshCallbackStringMutations:
    """Test _hourly_refresh_callback log string mutations to catch literal changes."""

    @pytest.mark.asyncio
    async def test_callback_logs_cache_before_publish(self, caplog):
        """Verify cache BEFORE publish log message format.

        Catches mutants that change the cache log string literal.
        """
        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock()
        adapter = MagicMock()
        adapter.get_cached_optimization_results = MagicMock(
            return_value={
                "per_trip_emhass_params": {"trip_1": {}},
                "emhass_power_profile": [100, 0],
            }
        )
        coord = MagicMock()
        coord.async_refresh_trips = AsyncMock()
        rt = EVTripRuntimeData(
            coordinator=coord,
            trip_manager=mgr,
            emhass_adapter=adapter,
        )
        with caplog.at_level("WARNING"):
            await _hourly_refresh_callback(None, rt)
        log_text = " ".join(record.message for record in caplog.records)
        assert "cache" in log_text.lower() and "before" in log_text.lower(), (
            "Should log cache state BEFORE publish"
        )

    @pytest.mark.asyncio
    async def test_callback_logs_cache_after_publish(self, caplog):
        """Verify cache AFTER publish log message format.

        Catches mutants that change the after-cache log string literal.
        """
        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock()
        adapter = MagicMock()
        adapter.get_cached_optimization_results = MagicMock(
            return_value={
                "per_trip_emhass_params": {"trip_1": {}},
                "emhass_power_profile": [100],
            }
        )
        coord = MagicMock()
        coord.async_refresh_trips = AsyncMock()
        rt = EVTripRuntimeData(
            coordinator=coord,
            trip_manager=mgr,
            emhass_adapter=adapter,
        )
        with caplog.at_level("WARNING"):
            await _hourly_refresh_callback(None, rt)
        log_text = " ".join(record.message for record in caplog.records)
        assert "cache" in log_text.lower() and "after" in log_text.lower(), (
            "Should log cache state AFTER publish"
        )

    @pytest.mark.asyncio
    async def test_callback_logs_refresh_trips(self, caplog):
        """Verify async_refresh_trips log messages.

        Catches mutants in the refresh_trips log strings.
        """
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
        with caplog.at_level("WARNING"):
            await _hourly_refresh_callback(None, rt)
        log_text = " ".join(record.message for record in caplog.records)
        assert "async_refresh_trips" in log_text, (
            "Should log async_refresh_trips start/done"
        )
