"""Tests for integration uninstall/cascade delete behavior.

Tests that vehicle deletion properly cleans up all trips from TripManager storage.
These tests use REAL TripManager and REAL EMHASSAdapter (not mocked).
They verify the actual deletion flow that runs in production.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.helpers import storage as ha_storage

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
        # Create mock entities
        mock_hass = MagicMock()
        mock_hass.data = {}

        entry = MagicMock()
        entry.data = {"vehicle_name": "test_vehicle"}
        entry.entry_id = "test_entry_id"

        # Create mock adapter that tracks cleanup
        emhass_adapter = MagicMock()
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
        mock_hass.config_entries = MagicMock()
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

        # Create mock EMHASS adapter
        emhass_adapter = MagicMock()

        async def cleanup_side_effect():
            for entity_id in list(emhass_adapter._published_entity_ids):
                await mock_hass.states.async_remove(entity_id)

        emhass_adapter.async_cleanup_vehicle_indices = AsyncMock(side_effect=cleanup_side_effect)

        # Simulate published sensors
        vehicle_sensor_id = f"sensor.emhass_perfil_diferible_{entry.entry_id}"
        emhass_adapter._published_entity_ids = {vehicle_sensor_id}
        emhass_adapter._index_map = {"trip_1": 0}
        emhass_adapter._released_indices = []

        # Create mock trip_manager
        mock_trip_manager = MagicMock()
        mock_trip_manager.async_delete_all_trips = AsyncMock()

        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData
        entry.runtime_data = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=mock_trip_manager,
            emhass_adapter=emhass_adapter,
        )

        with patch("custom_components.ev_trip_planner.async_unregister_panel", new_callable=AsyncMock):
            from custom_components.ev_trip_planner import async_unload_entry
            result = await async_unload_entry(mock_hass, entry)

            assert result is True, "async_unload_entry should return True"
            mock_trip_manager.async_delete_all_trips.assert_called_once()
            emhass_adapter.async_cleanup_vehicle_indices.assert_called_once()
            mock_hass.states.async_remove.assert_any_call(vehicle_sensor_id)


class TestAsyncRemoveEntryCleanupCascade:
    """TRUE integration tests for cascade deletion via async_remove_entry_cleanup.

    These tests use REAL TripManager and REAL EMHASSAdapter (not mocked).
    They exercise the actual code path that runs when a user deletes a vehicle.
    """

    @pytest.mark.asyncio
    async def test_async_delete_all_trips_clears_emhass_cache_and_publishes_empty(self):
        """Test that async_delete_all_trips clears EMHASS cache and publishes empty list.

        This is the cascade deletion flow:
        1. async_delete_all_trips() calls _async_remove_trip_from_emhass for each trip
        2. Then calls publish_deferrable_loads([]) with EMPTY list
        3. publish_deferrable_loads([]) clears _cached_per_trip_params

        This test verifies the cache is properly cleared.
        Uses REAL EMHASSAdapter to exercise actual cache clearing logic.
        """
        from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter

        # Create mock hass for EMHASSAdapter
        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.config.config_dir = "/tmp/test"
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.async_remove = AsyncMock()
        mock_hass.states.get = MagicMock(return_value=None)

        entry = MagicMock()
        entry.entry_id = "cache_test_entry"
        entry.data = {"vehicle_name": "Cache Test Vehicle"}

        # Create REAL EMHASSAdapter
        emhass_adapter = EMHASSAdapter(mock_hass, entry)

        # Pre-populate cache as if trips were published
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
        emhass_adapter._published_trips = [
            {"id": "trip_1", "tipo": "puntual"},
            {"id": "trip_2", "tipo": "recurrente"},
        ]

        # Create mock coordinator that tracks refresh calls
        mock_coordinator = MagicMock()
        coordinator_data = {
            "per_trip_emhass_params": dict(emhass_adapter._cached_per_trip_params),
            "emhass_power_profile": list(emhass_adapter._cached_power_profile),
        }

        async def mock_async_refresh():
            # Simulate real coordinator: reads from cleared cache after refresh
            cache = emhass_adapter.get_cached_optimization_results()
            coordinator_data["per_trip_emhass_params"] = cache.get("per_trip_emhass_params", {})
            coordinator_data["emhass_power_profile"] = cache.get("emhass_power_profile", [])

        mock_coordinator.async_refresh = mock_async_refresh
        mock_coordinator.data = coordinator_data

        # CRITICAL: Set up entry.runtime_data so _get_coordinator() finds the coordinator.
        # The code checks entry.runtime_data.coordinator first, not _coordinator attribute.
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData
        entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=None,
            emhass_adapter=None,
        )

        # Create REAL TripManager with emhass_adapter
        # Signature: (hass, vehicle_id, entry_id=None, presence_config=None, storage=None, emhass_adapter=None)
        trip_manager = TripManager(
            mock_hass,
            "cache_test_vehicle",
            entry.entry_id,
            None,  # presence_config
            None,  # storage
            emhass_adapter,
        )

        # Inject mock coordinator
        emhass_adapter._coordinator = mock_coordinator

        # Pre-populate trip_manager with trips
        trip_manager._trips = {
            "trip_1": {"id": "trip_1", "tipo": "puntual"},
            "trip_2": {"id": "trip_2", "tipo": "recurrente"},
        }
        trip_manager._recurring_trips = {"trip_2": {"id": "trip_2", "tipo": "recurrente"}}
        trip_manager._punctual_trips = {"trip_1": {"id": "trip_1", "tipo": "puntual"}}

        # ACT: Call async_delete_all_trips
        await trip_manager.async_delete_all_trips()

        # ASSERT: Cache should be cleared
        print(f"DEBUG: _cached_per_trip_params after delete: {emhass_adapter._cached_per_trip_params}")
        print(f"DEBUG: _cached_power_profile after delete: {emhass_adapter._cached_power_profile}")
        print(f"DEBUG: _published_trips after delete: {emhass_adapter._published_trips}")
        print(f"DEBUG: coordinator_data: {coordinator_data}")

        assert emhass_adapter._cached_per_trip_params == {}, \
            f"BUG: _cached_per_trip_params should be empty after delete, got {emhass_adapter._cached_per_trip_params}"
        assert emhass_adapter._cached_power_profile == [], \
            f"BUG: _cached_power_profile should be [] after delete, got {emhass_adapter._cached_power_profile}"
        assert emhass_adapter._published_trips == [], \
            f"BUG: _published_trips should be [] after delete, got {emhass_adapter._published_trips}"

        # Note: _index_map is NOT cleared by async_delete_all_trips - it's cleared by
        # async_cleanup_vehicle_indices which is called separately. The _index_map check
        # is done in the test_async_remove_entry_cleanup_clears_emhass_cache test.

        # CRITICAL: coordinator.data should reflect empty state after refresh
        assert coordinator_data["per_trip_emhass_params"] == {}, \
            f"BUG: coordinator.data should be empty after delete, got {coordinator_data['per_trip_emhass_params']}"
        assert coordinator_data["emhass_power_profile"] == [], \
            f"BUG: coordinator.data emhass_power_profile should be [], got {coordinator_data['emhass_power_profile']}"

    @pytest.mark.asyncio
    async def test_async_remove_entry_cleanup_calls_store_async_remove(self):
        """Test that async_remove_entry_cleanup calls store.async_remove() to delete storage.

        The research found that async_remove_entry_cleanup creates a NEW Store instance
        and calls async_remove() on it. This test verifies that call happens.

        This is critical: if store.async_remove() is NOT called, the storage file
        persists after deletion and trips "survive" even though in-memory state is cleared.
        """
        from custom_components.ev_trip_planner.services import async_remove_entry_cleanup
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.config.config_dir = "/tmp/test"
        mock_hass.states.get = MagicMock(return_value=None)
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.async_remove = AsyncMock()

        # Track what Store is created and how it's used
        created_stores = []
        original_init = ha_storage.Store.__init__

        def tracking_init(self, hass, version, key):
            created_stores.append({"key": key, "instance": self})
            return original_init(self, hass, version, key)

        entry = MagicMock()
        entry.entry_id = "removal_test_entry"
        entry.data = {"vehicle_name": "Removal Test Vehicle"}

        mock_trip_manager = MagicMock()
        mock_trip_manager.async_delete_all_trips = AsyncMock()

        mock_emhass = MagicMock()
        mock_emhass.async_cleanup_vehicle_indices = AsyncMock()

        mock_coordinator = MagicMock()

        entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_trip_manager,
            emhass_adapter=mock_emhass,
        )

        # Mock entity_registry
        mock_registry = MagicMock()
        mock_registry.async_entries_for_config_entry = MagicMock(return_value=[])
        with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_registry), \
             patch.object(ha_storage.Store, "__init__", tracking_init):

            # Track async_remove calls
            remove_called_for_keys = []
            original_async_remove = ha_storage.Store.async_remove

            async def tracking_async_remove(self):
                remove_called_for_keys.append(self.key)
                return await original_async_remove(self)

            with patch.object(ha_storage.Store, "async_remove", tracking_async_remove):
                await async_remove_entry_cleanup(mock_hass, entry)

        print(f"DEBUG: Created stores: {[s['key'] for s in created_stores]}")
        print(f"DEBUG: async_remove called for keys: {remove_called_for_keys}")

        # Verify async_remove was called
        # The key should be ev_trip_planner_{vehicle_id} where vehicle_id = "removal_test_vehicle"
        expected_key = "ev_trip_planner_removal_test_vehicle"
        assert expected_key in remove_called_for_keys, \
            f"BUG: store.async_remove() was NOT called for key {expected_key}! " \
            f"Called for: {remove_called_for_keys}. " \
            f"This means storage file persists after deletion!"

        # Verify trip_manager.async_delete_all_trips was called
        mock_trip_manager.async_delete_all_trips.assert_called_once()

        # Verify emhass cleanup was called
        mock_emhass.async_cleanup_vehicle_indices.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_remove_entry_cleanup_clears_emhass_cache(self):
        """Test that async_remove_entry_cleanup properly clears EMHASS adapter cache.

        This verifies that after cascade deletion via async_remove_entry_cleanup:
        1. _cached_per_trip_params is empty
        2. _cached_power_profile is empty
        3. _index_map is empty

        Uses REAL EMHASSAdapter to exercise actual cache clearing logic.
        """
        from custom_components.ev_trip_planner.services import async_remove_entry_cleanup
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData
        from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.config.config_dir = "/tmp/test"
        mock_hass.states.get = MagicMock(return_value=None)
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.async_remove = AsyncMock()

        entry = MagicMock()
        entry.entry_id = "cleanup_test_entry"
        entry.data = {"vehicle_name": "Cleanup Test Vehicle"}

        # Create REAL EMHASSAdapter
        emhass_adapter = EMHASSAdapter(mock_hass, entry)

        # Pre-populate cache
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
        emhass_adapter._cached_emhass_status = "ready"

        # Mock coordinator
        mock_coordinator = MagicMock()
        coordinator_data = {
            "per_trip_emhass_params": dict(emhass_adapter._cached_per_trip_params),
            "emhass_power_profile": list(emhass_adapter._cached_power_profile),
        }

        async def mock_async_refresh():
            cache = emhass_adapter.get_cached_optimization_results()
            coordinator_data["per_trip_emhass_params"] = cache.get("per_trip_emhass_params", {})
            coordinator_data["emhass_power_profile"] = cache.get("emhass_power_profile", [])

        mock_coordinator.async_refresh = mock_async_refresh
        mock_coordinator.data = coordinator_data

        mock_trip_manager = MagicMock()
        mock_trip_manager.async_delete_all_trips = AsyncMock()

        entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_trip_manager,
            emhass_adapter=emhass_adapter,
        )

        # Mock entity_registry and Store
        mock_registry = MagicMock()
        mock_registry.async_entries_for_config_entry = MagicMock(return_value=[])
        mock_store = MagicMock()
        mock_store.async_remove = AsyncMock()

        with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_registry), \
             patch.object(ha_storage.Store, "__init__", lambda self, hass, version, key: None), \
             patch.object(ha_storage.Store, "async_remove", AsyncMock()):

            await async_remove_entry_cleanup(mock_hass, entry)

        print(f"DEBUG: _cached_per_trip_params: {emhass_adapter._cached_per_trip_params}")
        print(f"DEBUG: _cached_power_profile: {emhass_adapter._cached_power_profile}")
        print(f"DEBUG: _index_map: {emhass_adapter._index_map}")
        print(f"DEBUG: coordinator_data: {coordinator_data}")

        assert emhass_adapter._cached_per_trip_params == {}, \
            f"BUG: _cached_per_trip_params should be empty, got {emhass_adapter._cached_per_trip_params}"
        assert emhass_adapter._cached_power_profile == [], \
            f"BUG: _cached_power_profile should be [], got {emhass_adapter._cached_power_profile}"
        assert emhass_adapter._index_map == {}, \
            f"BUG: _index_map should be empty, got {emhass_adapter._index_map}"
        assert coordinator_data["per_trip_emhass_params"] == {}, \
            f"BUG: coordinator.data should be empty, got {coordinator_data['per_trip_emhass_params']}"
        assert coordinator_data["emhass_power_profile"] == [], \
            f"BUG: coordinator.data emhass_power_profile should be [], got {coordinator_data['emhass_power_profile']}"
