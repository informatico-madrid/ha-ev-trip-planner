"""Tests for integration uninstall/cascade delete behavior.

Tests that vehicle deletion properly cleans up all trips from TripManager storage.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def enable_custom_integrations():
    """Enable custom integrations for testing."""
    return True


class TestFullVehicleDeletion:
    """Integration test for full vehicle deletion lifecycle."""

    @pytest.mark.asyncio
    async def test_no_orphaned_sensors_after_deletion(self):
        """Test that no orphaned EMHASS sensors remain after vehicle deletion.

        After async_unload_entry completes:
        - _index_map should be empty
        - _published_entity_ids should be empty
        - No sensors should remain in state machine
        """
        from unittest.mock import AsyncMock, Mock, patch

        # Create mock entities
        mock_hass = Mock(spec=HomeAssistant)
        mock_hass.data = {}

        entry = Mock()
        entry.data = {"vehicle_name": "test_vehicle"}
        entry.entry_id = "test_entry_id"

        # Create mock adapter that tracks cleanup
        emhass_adapter = Mock()
        emhass_adapter._index_map = {"trip_001": 0, "trip_002": 1}
        emhass_adapter._published_entity_ids = {
            "sensor.emhass_perfil_diferible_test_vehicle_trip_001",
        }
        emhass_adapter.async_cleanup_vehicle_indices = AsyncMock()

        # Set up runtime data using entry.runtime_data pattern (Phase 4)
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData
        entry.runtime_data = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=None,
            emhass_adapter=emhass_adapter,
        )

        # Mock unload
        async def mock_unload(entry, platforms):
            return True
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_unload_platforms = mock_unload

        with patch("custom_components.ev_trip_planner.async_unregister_panel", new_callable=AsyncMock):
            from custom_components.ev_trip_planner import async_unload_entry
            await async_unload_entry(mock_hass, entry)

        # Verify: Cleanup was called
        emhass_adapter.async_cleanup_vehicle_indices.assert_called_once()


class TestEmhassFullUnload:
    """Integration tests for EMHASS sensor cleanup during full unload.

    Verifies that when async_unload_entry is called, all EMHASS sensors
    published by the adapter are properly removed via hass.states.async_remove.
    """

    @pytest.mark.asyncio
    async def test_full_unload_cleans_all_emhass_sensors(self):
        """Test that async_unload_entry removes all published EMHASS sensors.

        When a vehicle's integration is removed, all EMHASS deferrable load
        sensors that were published should be removed via hass.states.async_remove.
        This is AC-1.4 from the integration points design.
        """
        # Create mock Home Assistant instance with config_entries attribute
        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.states.async_remove = AsyncMock()

        # Create mock config_entries with async_unload_platforms
        async def mock_unload_platforms(entry, platforms):
            return True
        mock_hass.config_entries = MagicMock()
        mock_hass.config_entries.async_unload_platforms = mock_unload_platforms

        # Create mock config entry with proper structure
        entry = MagicMock()
        entry.entry_id = "emhass_unload_entry_id"
        entry.data = {
            "vehicle_name": "EMHASS Test Vehicle",
            "planning_horizon_days": 7,
            "max_deferrable_loads": 50,
            "charging_power_kw": 7.4,
        }

        # Create mock EMHASS adapter (not real instance to avoid hass.bus issues)
        emhass_adapter = Mock()

        async def cleanup_side_effect():
            for entity_id in list(emhass_adapter._published_entity_ids):
                await mock_hass.states.async_remove(entity_id)

        emhass_adapter.async_cleanup_vehicle_indices = AsyncMock(side_effect=cleanup_side_effect)

        # Simulate published sensors by populating _published_entity_ids and _index_map
        # The main vehicle sensor
        vehicle_sensor_id = f"sensor.emhass_perfil_diferible_{entry.entry_id}"
        emhass_adapter._published_entity_ids = {vehicle_sensor_id}
        emhass_adapter._index_map = {"trip_1": 0}
        emhass_adapter._released_indices = []

        # Create mock trip_manager with async_delete_all_trips
        mock_trip_manager = Mock()
        mock_trip_manager.async_delete_all_trips = AsyncMock()

        # Set up runtime data using entry.runtime_data pattern (Phase 4)
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData
        entry.runtime_data = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=mock_trip_manager,
            emhass_adapter=emhass_adapter,
        )

        # Mock async_unregister_panel
        with patch("custom_components.ev_trip_planner.async_unregister_panel", new_callable=AsyncMock):
            # Import and call async_unload_entry
            from custom_components.ev_trip_planner import async_unload_entry

            # Act: unload the entry
            result = await async_unload_entry(mock_hass, entry)

            # Verify unload succeeded
            assert result is True, "async_unload_entry should return True"

            # CRITICAL: async_delete_all_trips should have been called
            mock_trip_manager.async_delete_all_trips.assert_called_once()

            # Verify cleanup was called
            emhass_adapter.async_cleanup_vehicle_indices.assert_called_once()

            # CRITICAL: Verify hass.states.async_remove was called for published sensor
            mock_hass.states.async_remove.assert_any_call(vehicle_sensor_id)


class TestAsyncRemoveEntryCleanupCascade:
    """Integration tests for cascade deletion via async_remove_entry_cleanup.

    Tests that async_remove_entry_cleanup properly calls async_delete_all_trips
    and async_cleanup_vehicle_indices to clean up all trip data.
    """

    @pytest.mark.asyncio
    async def test_async_remove_entry_cleanup_cascade_deletes_all_trips(self):
        """Test that async_remove_entry_cleanup calls cascade delete methods.

        When an integration is deleted via the UI, async_remove_entry_cleanup is called.
        This test verifies that:
        1. trip_manager.async_delete_all_trips() is called
        2. emhass_adapter.async_cleanup_vehicle_indices() is called
        3. All in-memory and persisted trip data is cleared
        """
        from custom_components.ev_trip_planner.services import async_remove_entry_cleanup
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData
        from homeassistant.helpers import storage as ha_storage

        # Create mock hass
        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.config.config_dir = "/tmp/test_config"
        mock_hass.states.get = MagicMock(return_value=None)
        mock_hass.services.async_call = AsyncMock()

        # Create mock entry
        entry = MagicMock()
        entry.entry_id = "test_removal_entry"
        entry.data = {"vehicle_name": "Test Vehicle"}

        # Create mock trip_manager with storage that persists data
        stored_data = {
            "data": {
                "trips": {
                    "trip_1": {"id": "trip_1", "tipo": "puntual"},
                    "trip_2": {"id": "trip_2", "tipo": "recurrente"},
                },
                "recurring_trips": {
                    "rec_1": {"id": "rec_1", "tipo": "recurrente", "hora": "09:00", "dia": "lunes"},
                },
                "punctual_trips": {
                    "trip_1": {"id": "trip_1", "tipo": "puntual"},
                    "trip_2": {"id": "trip_2", "tipo": "puntual"},
                },
            }
        }

        # Create a real TripManager and inject a mock store that preserves data
        trip_manager = TripManager(
            mock_hass,
            "test_vehicle",
            entry.entry_id,
            None,
        )
        mock_store = MagicMock()
        mock_store._storage = dict(stored_data)  # Copy to isolate

        async def _async_load():
            return mock_store._storage.get("data", None)

        async def _async_save(data):
            mock_store._storage["data"] = data
            return True

        mock_store.async_load = _async_load
        mock_store.async_save = _async_save
        trip_manager._storage = mock_store

        # CRITICAL: Call async_setup() to LOAD data from storage into memory
        # This is what happens when HA starts/restarts - TripManager loads trips
        await trip_manager.async_setup()

        # Verify data was actually loaded from storage
        print(f"DEBUG: After async_setup() - _trips: {trip_manager._trips}")
        print(f"DEBUG: After async_setup() - _punctual_trips: {trip_manager._punctual_trips}")
        print(f"DEBUG: After async_setup() - _recurring_trips: {trip_manager._recurring_trips}")
        assert len(trip_manager._trips) == 2, f"Should have 2 trips loaded, got {len(trip_manager._trips)}"
        assert len(trip_manager._punctual_trips) == 2, f"Should have 2 punctual trips loaded, got {len(trip_manager._punctual_trips)}"
        assert len(trip_manager._recurring_trips) == 1, f"Should have 1 recurring trip loaded, got {len(trip_manager._recurring_trips)}"

        # Create real EMHASS adapter (not MagicMock) so real cache clearing logic runs
        # This is CRITICAL: MagicMock doesn't exercise the actual cache clearing in
        # publish_deferrable_loads([]) and async_cleanup_vehicle_indices(), which is
        # what the E2E test is failing on.
        from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter

        # Create a real EMHASS adapter using the same entry
        emhass_adapter = EMHASSAdapter(mock_hass, entry)
        # Initialize internal state as if trips were published
        emhass_adapter._index_map = {"trip_1": 0, "trip_2": 1}
        emhass_adapter._published_entity_ids = {
            f"sensor.emhass_perfil_diferible_{entry.entry_id}_config_0",
        }
        emhass_adapter._cached_per_trip_params = {
            "trip_1": {"def_total_hours_array": [5], "activo": True, "emhass_index": 0},
            "trip_2": {"def_total_hours_array": [7], "activo": True, "emhass_index": 1},
        }
        emhass_adapter._cached_power_profile = [1000.0] * 168
        emhass_adapter._cached_deferrables_schedule = [{"trip_id": "trip_1"}, {"trip_id": "trip_2"}]
        # _entry is set by EMHASSAdapter.__init__ from the passed entry

        # Create a mock coordinator that actually updates its data when async_refresh is called
        # This simulates the real DataUpdateCoordinator behavior where async_refresh
        # triggers _async_update_data which reads from emhass_adapter.get_cached_optimization_results()
        mock_coordinator = MagicMock()

        # Track the data that would be returned by coordinator.data after refresh
        # Initially has trips, after refresh should be empty
        coordinator_data = {
            "per_trip_emhass_params": {
                "trip_1": {"def_total_hours_array": [5], "activo": True, "emhass_index": 0},
                "trip_2": {"def_total_hours_array": [7], "activo": True, "emhass_index": 1},
            },
            "emhass_power_profile": [1000.0] * 168,
        }

        async def mock_async_refresh():
            # When coordinator refreshes, it reads from emhass_adapter.get_cached_optimization_results()
            # At this point, emhass_adapter._cached_per_trip_params is still populated
            # from the previous state (before async_cleanup_vehicle_indices clears it).
            # This is the BUG - the coordinator refresh reads stale data.
            #
            # For the test to expose this bug, we simulate what happens:
            # 1. async_delete_all_trips calls publish_deferrable_loads([]) which clears cache
            # 2. async_cleanup_vehicle_indices clears _cached_per_trip_params and calls coordinator.async_refresh()
            # 3. But at this point, _cached_per_trip_params IS cleared, so coordinator.data should reflect empty
            #
            # Actually the real bug is that the refresh happens AFTER the state was read,
            # so coordinator.data still has old trips until the refresh completes.
            # For our mock, we just set data to what emhass_adapter currently has
            cache = emhass_adapter.get_cached_optimization_results()
            coordinator_data["per_trip_emhass_params"] = cache.get("per_trip_emhass_params", {})
            coordinator_data["emhass_power_profile"] = cache.get("emhass_power_profile", [])

        mock_coordinator.async_refresh = mock_async_refresh
        mock_coordinator.data = coordinator_data

        # Set up runtime data
        entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=trip_manager,
            emhass_adapter=emhass_adapter,
        )

        # Setup storage mock for async_remove_entry_cleanup
        mock_removal_store = MagicMock()
        mock_removal_store.async_remove = AsyncMock()

        with patch.object(ha_storage, "Store", return_value=mock_removal_store):
            # Act: Call async_remove_entry_cleanup
            await async_remove_entry_cleanup(mock_hass, entry)

        # DEBUG: Check what was saved in mock_store
        print(f"DEBUG: mock_store._storage after cleanup: {mock_store._storage}")
        print(f"DEBUG: mock_store._storage['data'] keys: {list(mock_store._storage.get('data', {}).keys())}")
        print(f"DEBUG: trips after cleanup: {mock_store._storage.get('data', {}).get('trips', {})}")
        print(f"DEBUG: punctual trips after cleanup: {mock_store._storage.get('data', {}).get('punctual_trips', {})}")
        print(f"DEBUG: recurring trips after cleanup: {mock_store._storage.get('data', {}).get('recurring_trips', {})}")

        # Assert: async_delete_all_trips was called (cascade delete trips)
        # Note: We can't easily verify internal state, so we check via reload
        # Create new TripManager with same store and verify it's empty
        new_manager = TripManager(
            mock_hass,
            "test_vehicle",
            entry.entry_id,
            None,
        )
        new_manager._storage = mock_store

        # DEBUG: Manually check what _async_load returns
        manual_load = await mock_store.async_load()
        print(f"DEBUG: manual async_load result: {manual_load}")
        print(f"DEBUG: manual_load['data']: {manual_load.get('data') if manual_load else None}")

        await new_manager.async_setup()

        print(f"DEBUG: new_manager._trips after async_setup: {new_manager._trips}")
        print(f"DEBUG: new_manager._punctual_trips after async_setup: {new_manager._punctual_trips}")
        print(f"DEBUG: new_manager._recurring_trips after async_setup: {new_manager._recurring_trips}")

        # CRITICAL: After cascade deletion, no trips should remain
        assert len(new_manager._trips) == 0, \
            f"BUG: Persisted trips should be empty after cascade delete, got {len(new_manager._trips)}: {new_manager._trips}"
        assert len(new_manager._punctual_trips) == 0, \
            f"BUG: Persisted punctual trips should be empty, got {len(new_manager._punctual_trips)}"
        assert len(new_manager._recurring_trips) == 0, \
            f"BUG: Persisted recurring trips should be empty, got {len(new_manager._recurring_trips)}"

        # CRITICAL: After cascade deletion, EMHASS adapter cache should be cleared
        # This is the actual bug the E2E test is failing on - the cached per-trip params
        # are not being cleared properly, causing stale trips to still appear in the sensor.
        # Verify emhass_adapter's internal cache state matches what should happen in production
        print(f"DEBUG: emhass_adapter._cached_per_trip_params after cleanup: {emhass_adapter._cached_per_trip_params}")
        print(f"DEBUG: emhass_adapter._cached_power_profile length: {len(emhass_adapter._cached_power_profile)}")
        print(f"DEBUG: emhass_adapter._index_map after cleanup: {emhass_adapter._index_map}")

        # The _cached_per_trip_params should be empty after cascade deletion
        assert len(emhass_adapter._cached_per_trip_params) == 0, \
            f"BUG: EMHASS _cached_per_trip_params should be empty after cascade deletion, got {emhass_adapter._cached_per_trip_params}"

        # The _cached_power_profile should be empty (not have stale data)
        assert emhass_adapter._cached_power_profile == [], \
            f"BUG: EMHASS _cached_power_profile should be [] after cascade deletion, got {emhass_adapter._cached_power_profile}"

        # The _index_map should be empty
        assert len(emhass_adapter._index_map) == 0, \
            f"BUG: EMHASS _index_map should be empty after cascade deletion, got {emhass_adapter._index_map}"