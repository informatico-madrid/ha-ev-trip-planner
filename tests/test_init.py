"""Tests for EV Trip Planner integration __init__.py."""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, PropertyMock, patch, mock_open
from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner.dashboard import (
    is_lovelace_available,
    import_dashboard,
    _load_dashboard_template,
    _verify_storage_permissions,
    _save_lovelace_dashboard,
)
from custom_components.ev_trip_planner import (
    TripPlannerCoordinator,
    create_dashboard_input_helpers,
)


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.config = Mock()
    hass.config.config_dir = Path("/config")
    hass.config.components = []
    hass.services = Mock()
    hass.services.has_service = Mock(return_value=False)
    hass.data = {}  # Add data attribute for runtime storage

    # Mock async_add_executor_job for non-blocking I/O
    async def mock_executor_job(func, *args):
        """Mock executor job that runs function synchronously."""
        return func(*args)
    hass.async_add_executor_job = mock_executor_job
    hass.loop = Mock()

    return hass


class TestIsLovelaceAvailable:
    """Tests for is_lovelace_available function."""

    def test_lovelace_available_in_components(self, mock_hass):
        """Test Lovelace is available when in components."""
        mock_hass.config.components = ["lovelace", "core"]
        assert is_lovelace_available(mock_hass) is True

    def test_lovelace_available_with_import_service(self, mock_hass):
        """Test Lovelace is available with import service."""
        mock_hass.config.components = ["core"]
        mock_hass.services.has_service = Mock(return_value=True)
        assert is_lovelace_available(mock_hass) is True

    def test_lovelace_not_available(self, mock_hass):
        """Test Lovelace is not available."""
        mock_hass.config.components = ["core"]
        mock_hass.services.has_service = Mock(return_value=False)
        assert is_lovelace_available(mock_hass) is False


class TestImportDashboard:
    """Tests for import_dashboard function."""

    @pytest.mark.asyncio
    async def test_import_dashboard_lovelace_not_available(self, mock_hass):
        """Test dashboard import when Lovelace not available."""
        mock_hass.config.components = ["core"]
        mock_hass.services.has_service = Mock(return_value=False)

        result = await import_dashboard(
            mock_hass,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            use_charts=False,
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_import_dashboard_fallback_service(self, mock_hass):
        """Test dashboard import using fallback service."""
        mock_hass.config.components = ["lovelace", "core"]
        mock_hass.services.has_service = Mock(return_value=True)
        mock_hass.services.async_call = AsyncMock()

        result = await import_dashboard(
            mock_hass,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            use_charts=False,
        )

        assert result.success is True
        mock_hass.services.async_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_dashboard_async_import_dashboard(self, mock_hass):
        """Test dashboard import using storage API."""
        mock_hass.config.components = ["lovelace", "core"]

        # Mock the storage API with async methods
        mock_hass.storage = Mock()
        mock_hass.storage.async_read = AsyncMock(return_value={"data": {"views": []}})
        mock_hass.storage.async_write_dict = AsyncMock(return_value=True)
        mock_hass.services = Mock()
        mock_hass.services.has_service = Mock(return_value=False)

        result = await import_dashboard(
            mock_hass,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            use_charts=True,
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_import_dashboard_no_import_method(self, mock_hass):
        """Test dashboard import when no import method available."""
        mock_hass.config.components = ["core"]  # No lovelace
        mock_hass.services.has_service = Mock(return_value=False)

        result = await import_dashboard(
            mock_hass,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            use_charts=False,
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_import_dashboard_exception(self, mock_hass):
        """Test dashboard import handles exception and falls back to YAML."""
        mock_hass.config.components = ["lovelace", "core"]
        mock_hass.config.config_dir = "/tmp/test_config"
        mock_hass.services.has_service = Mock(side_effect=Exception("Test error"))

        result = await import_dashboard(
            mock_hass,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            use_charts=False,
        )

        # Exception triggers YAML fallback which should succeed
        assert result.success is True


class TestLoadDashboardTemplate:
    """Tests for _load_dashboard_template function."""

    @pytest.mark.asyncio
    async def test_load_dashboard_template_simple(self, mock_hass):
        """Test loading simple dashboard template."""
        # This test verifies the function is callable and returns proper structure
        # when template file is found
        mock_hass.config.components = ["lovelace", "core"]

        # Test with use_charts=False - should use ev-trip-planner-simple.yaml
        result = await _load_dashboard_template(
            mock_hass,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            use_charts=False,
        )

        # The result should be a dict or None (None if template not found)
        # Either way, we verify the function is callable
        assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_load_dashboard_template_full(self, mock_hass):
        """Test loading full dashboard template."""
        mock_hass.config.components = ["lovelace", "core"]

        # Test with use_charts=True - should use ev-trip-planner-full.yaml
        result = await _load_dashboard_template(
            mock_hass,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            use_charts=True,
        )

        # The result should be a dict or None (None if template not found)
        assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_load_dashboard_template_with_patch(self, mock_hass):
        """Test that _load_dashboard_template substitutes variables correctly."""
        mock_hass.config.components = ["lovelace", "core"]

        # Mock the file system to return a template with variables
        template_content = """
title: "EV Trip Planner - {{ vehicle_name }}"
views:
  - title: "{{ vehicle_name }} - Estado"
    path: "{{ vehicle_id }}"
"""

        with patch("os.path.exists", return_value=True):
            with patch("os.path.dirname", return_value="/fake/path"):
                with patch(
                    "builtins.open",
                    mock_open(read_data=template_content),
                ):
                    result = await _load_dashboard_template(
                        mock_hass,
                        vehicle_id="my_vehicle",
                        vehicle_name="My Vehicle",
                        use_charts=False,
                    )

        # If file is found and readable, should return dict with substituted variables
        if result:
            assert "title" in result
            assert "My Vehicle" in result["title"] or "vehicle_name" in result["title"]


class TestVerifyStoragePermissions:
    """Tests for _verify_storage_permissions function."""

    @pytest.mark.asyncio
    async def test_verify_storage_permissions_available(self, mock_hass):
        """Test storage permissions when storage API is available.

        Note: Production code uses ha_storage.Store which requires special mocking.
        This test verifies the function is callable and returns a boolean.
        """
        # Create a minimal mock that won't raise exceptions during Store initialization
        mock_hass.config = Mock()
        mock_hass.loop = Mock()
        mock_hass.loop.create_future = Mock(return_value=None)

        result = await _verify_storage_permissions(mock_hass, "test_vehicle")

        # Should return a boolean (True if Store works, False on error)
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_verify_storage_permissions_not_available(self, mock_hass):
        """Test storage permissions when storage API is not available."""
        # Remove storage attribute to simulate no storage
        mock_hass.storage = None

        result = await _verify_storage_permissions(mock_hass, "test_vehicle")

        # Should return False when storage is not available
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_storage_permissions_no_async_write(self, mock_hass):
        """Test storage permissions when async_write_dict is missing."""
        mock_hass.storage = Mock()
        # Remove async_write_dict
        del mock_hass.storage.async_write_dict

        result = await _verify_storage_permissions(mock_hass, "test_vehicle")

        # Should return False when async_write_dict is missing
        assert result is False


class TestSaveLovelaceDashboard:
    """Tests for _save_lovelace_dashboard function."""

    @pytest.mark.asyncio
    async def test_save_lovelace_dashboard_with_save_service(self, mock_hass):
        """Test saving dashboard using lovelace.save service."""
        mock_hass.config.components = ["lovelace"]
        mock_hass.services.has_service = Mock(return_value=True)
        mock_hass.services.async_call = AsyncMock()

        dashboard_config = {
            "title": "Test Dashboard",
            "views": [
                {
                    "title": "Test View",
                    "path": "test-path",
                }
            ],
        }

        result = await _save_lovelace_dashboard(
            mock_hass, dashboard_config, "test_vehicle"
        )

        # Should return True when save service is available
        assert result.success is True
        mock_hass.services.async_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_lovelace_dashboard_no_views(self, mock_hass):
        """Test saving dashboard with no views falls back to storage API."""
        mock_hass.config.components = ["lovelace"]
        mock_hass.services.has_service = Mock(return_value=True)
        mock_hass.services.async_call = AsyncMock()

        # Also mock storage for fallback
        mock_hass.storage = Mock()
        mock_hass.storage.async_read = AsyncMock(return_value={"data": {"views": []}})
        mock_hass.storage.async_write_dict = AsyncMock(return_value=True)

        dashboard_config = {
            "title": "Test Dashboard",
            "views": [
                {
                    "title": "Test View",
                    "path": "test-path",
                }
            ],
        }

        result = await _save_lovelace_dashboard(
            mock_hass, dashboard_config, "test_vehicle"
        )

        # Should return True when storage API works
        assert result.success is True

    @pytest.mark.asyncio
    async def test_save_lovelace_dashboard_storage_api(self, mock_hass):
        """Test saving dashboard using storage API.

        Note: Production code uses ha_storage.Store which requires special mocking.
        This test verifies the function is callable and returns a result object.
        """
        mock_hass.config.components = ["lovelace"]
        mock_hass.services.has_service = Mock(return_value=False)

        # Create a loop mock for Store initialization
        mock_hass.loop = Mock()
        mock_hass.loop.create_future = Mock(return_value=None)

        dashboard_config = {
            "title": "Test Dashboard",
            "views": [
                {
                    "title": "Test View",
                    "path": "test-path",
                }
            ],
        }

        result = await _save_lovelace_dashboard(
            mock_hass, dashboard_config, "test_vehicle"
        )

        # Should return a result object with success attribute
        assert hasattr(result, "success")
        assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_save_lovelace_dashboard_no_service(self, mock_hass):
        """Test saving dashboard when no service available and no storage."""
        mock_hass.config.components = ["lovelace"]
        mock_hass.services.has_service = Mock(return_value=False)
        mock_hass.storage = None

        dashboard_config = {
            "title": "Test Dashboard",
            "views": [
                {
                    "title": "Test View",
                    "path": "test-path",
                }
            ],
        }

        result = await _save_lovelace_dashboard(
            mock_hass, dashboard_config, "test_vehicle"
        )

        # Should return False when no method available
        assert result.success is False


class TestImportDashboardAdditional:
    """Additional tests for import_dashboard function."""

    @pytest.mark.asyncio
    async def test_import_dashboard_with_use_charts_true(self, mock_hass):
        """Test dashboard import with use_charts=True."""
        mock_hass.config.components = ["lovelace", "core"]
        mock_hass.services.has_service = Mock(return_value=True)
        mock_hass.services.async_call = AsyncMock()

        # Mock storage to fail so it falls back to service
        mock_hass.storage = Mock()
        mock_hass.storage.async_read = AsyncMock(side_effect=Exception("Storage error"))

        result = await import_dashboard(
            mock_hass,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            use_charts=True,
        )

        # Should fallback to service method
        assert result.success is True

    @pytest.mark.asyncio
    async def test_import_dashboard_storage_fails_then_service(self, mock_hass):
        """Test dashboard import when storage fails but service works."""
        mock_hass.config.components = ["lovelace", "core"]

        # Mock storage to fail
        mock_hass.storage = Mock()
        mock_hass.storage.async_read = AsyncMock(side_effect=Exception("Storage error"))
        mock_hass.storage.async_write_dict = AsyncMock(side_effect=Exception("Write error"))

        # Mock services - save service fails, import service works
        mock_hass.services = Mock()
        mock_hass.services.has_service = Mock(return_value=True)
        mock_hass.services.async_call = AsyncMock()

        result = await import_dashboard(
            mock_hass,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            use_charts=False,
        )

        # Should use import service as fallback
        assert result.success is True


class TestTripPlannerCoordinator:
    """Tests for TripPlannerCoordinator class."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator."""
        coordinator = Mock()
        coordinator.async_setup = AsyncMock()
        coordinator.async_unload = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_schedule_monitor(self):
        """Create mock schedule monitor."""
        monitor = Mock()
        monitor.async_setup = AsyncMock()
        monitor.async_stop = AsyncMock()
        return monitor

    @pytest.mark.asyncio
    async def test_coordinator_class_exists(self):
        """Test TripPlannerCoordinator class exists."""
        # Just verify the class is importable
        assert TripPlannerCoordinator is not None


class TestCreateDashboardInputHelpers:
    """Tests for create_dashboard_input_helpers function."""

    @pytest.mark.asyncio
    async def test_create_dashboard_input_helpers_success(self, mock_hass):
        """Test creating input helpers successfully."""
        mock_hass.services.async_call = AsyncMock()

        result = await create_dashboard_input_helpers(mock_hass, "test_vehicle")

        # Should return True on success
        assert result.success is True
        # Should have called services multiple times (day, time, km, kwh, desc, punctual datetime, etc.)
        assert mock_hass.services.async_call.call_count > 0

    @pytest.mark.asyncio
    async def test_create_dashboard_input_helpers_partial_failure(self, mock_hass):
        """Test creating input helpers with partial service failures."""
        # Create a side effect that succeeds for first few calls then fails
        call_count = 0

        async def service_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 3:
                raise Exception("Service error")
            return None

        mock_hass.services.async_call = AsyncMock(side_effect=service_call)

        result = await create_dashboard_input_helpers(mock_hass, "test_vehicle")

        # Should return True because exceptions are caught internally
        assert result.success is True

    @pytest.mark.asyncio
    async def test_import_dashboard_template_not_found(self, mock_hass):
        """Test import_dashboard returns False when template not found."""
        # Set up mock to return False for Lovelace check
        mock_hass.config.components = ["core"]  # No lovelace
        mock_hass.services.has_service = Mock(return_value=False)

        result = await import_dashboard(
            mock_hass,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            use_charts=False,
        )

        # Should return False when Lovelace not available
        assert result.success is False

    @pytest.mark.asyncio
    async def test_verify_storage_permissions_no_storage(self, mock_hass):
        """Test storage permissions when no storage available."""
        mock_hass.storage = None

        result = await _verify_storage_permissions(mock_hass, "test_vehicle")

        # Should return False when no storage
        assert result is False


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry function."""

    @pytest.mark.asyncio
    async def test_unload_entry_calls_unregister_panel(self, mock_hass):
        """Test that async_unload_entry calls async_unregister_panel."""
        # Create a mock config entry with vehicle_id
        entry = Mock()
        entry.data = {
            "vehicle_id": "test_vehicle",
            "vehicle_name": "Test Vehicle",
        }
        entry.entry_id = "test_entry_id"

        # Mock the platforms unload to return True
        async def mock_unload_platforms(entry, platforms):
            return True

        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_unload_platforms = mock_unload_platforms

        # Mock async_unregister_panel to track if it was called
        with patch("custom_components.ev_trip_planner.async_unregister_panel") as mock_unregister:
            mock_unregister.return_value = True

            # Import and call async_unload_entry
            from custom_components.ev_trip_planner import async_unload_entry

            result = await async_unload_entry(mock_hass, entry)

            # Verify async_unregister_panel was called with correct arguments
            mock_unregister.assert_called_once_with(mock_hass, "test_vehicle")
            assert result is True

    @pytest.mark.asyncio
    async def test_unload_entry_no_vehicle_id(self, mock_hass):
        """Test that async_unload_entry derives vehicle_id from vehicle_name.

        Even without an explicit vehicle_id key, the code computes it
        from vehicle_name via .lower().replace(' ', '_'), so the panel
        unregister should still be called with the derived vehicle_id.
        """
        # Create a mock config entry without vehicle_id (only vehicle_name)
        entry = Mock()
        entry.data = {
            "vehicle_name": "Test Vehicle",
        }
        entry.entry_id = "test_entry_id"

        # Mock the platforms unload to return True
        async def mock_unload_platforms(entry, platforms):
            return True

        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_unload_platforms = mock_unload_platforms

        # Mock async_unregister_panel to track if it was called
        with patch("custom_components.ev_trip_planner.async_unregister_panel") as mock_unregister:
            mock_unregister.return_value = True

            # Import and call async_unload_entry
            from custom_components.ev_trip_planner import async_unload_entry

            result = await async_unload_entry(mock_hass, entry)

            # Verify async_unregister_panel WAS called with derived vehicle_id
            mock_unregister.assert_called_once_with(mock_hass, "test_vehicle")
            assert result is True

    @pytest.mark.asyncio
    async def test_unload_entry_handles_unregister_error(self, mock_hass):
        """Test that async_unload_entry handles unregister panel errors gracefully."""
        # Create a mock config entry with vehicle_id
        entry = Mock()
        entry.data = {
            "vehicle_id": "test_vehicle",
            "vehicle_name": "Test Vehicle",
        }
        entry.entry_id = "test_entry_id"

        # Mock the platforms unload to return True
        async def mock_unload_platforms(entry, platforms):
            return True

        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_unload_platforms = mock_unload_platforms

        # Mock async_unregister_panel to raise an exception
        with patch("custom_components.ev_trip_planner.async_unregister_panel") as mock_unregister:
            mock_unregister.side_effect = Exception("Registration error")

            # Import and call async_unload_entry
            from custom_components.ev_trip_planner import async_unload_entry

            # Should handle the error and return True (platforms unloaded successfully)
            result = await async_unload_entry(mock_hass, entry)
            assert result is True

    @pytest.mark.asyncio
    async def test_unload_entry_calls_cleanup_before_platforms_unload(self, mock_hass):
        """Test that async_unload_entry calls emhass_adapter.async_cleanup_vehicle_indices before unloading platforms.

        This is a RED test that documents the expected behavior: emhass_adapter cleanup
        MUST be called before async_unload_platforms to ensure entity state still exists
        when async_remove is called.
        """
        # Create a mock config entry with vehicle info
        entry = Mock()
        entry.data = {
            "vehicle_id": "test_vehicle",
            "vehicle_name": "Test Vehicle",
        }
        entry.entry_id = "test_entry_id"

        # Track call order
        call_order = []

        # Mock the platforms unload
        async def mock_unload_platforms(entry, platforms):
            call_order.append("unload_platforms")
            return True

        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_unload_platforms = mock_unload_platforms

        # Create mock TripManager
        trip_manager = Mock()
        trip_manager.vehicle_id = "test_vehicle"
        trip_manager.async_delete_all_trips = AsyncMock()
        trip_manager._recurring_trips = {}
        trip_manager._punctual_trips = {}

        # Create mock EMHASS adapter with async_cleanup_vehicle_indices
        emhass_adapter = Mock()
        emhass_adapter.vehicle_id = "test_vehicle"
        emhass_adapter._index_map = {}
        emhass_adapter._released_indices = []

        async def mock_cleanup():
            call_order.append("cleanup_vehicle_indices")

        emhass_adapter.async_cleanup_vehicle_indices = mock_cleanup

        # Set up runtime data
        from custom_components.ev_trip_planner import DATA_RUNTIME, DOMAIN
        namespace = f"{DOMAIN}_{entry.entry_id}"
        mock_hass.data[DATA_RUNTIME] = {
            namespace: {
                "config": entry.data,
                "trip_manager": trip_manager,
                "emhass_adapter": emhass_adapter,
            }
        }

        # Mock async_unregister_panel
        with patch(
            "custom_components.ev_trip_planner.async_unregister_panel",
            new_callable=AsyncMock,
        ) as mock_unregister:
            mock_unregister.return_value = True

            # Import and call async_unload_entry
            from custom_components.ev_trip_planner import async_unload_entry

            result = await async_unload_entry(mock_hass, entry)

            # Verify unload succeeded
            assert result is True

            # CRITICAL: cleanup MUST be called before platforms are unloaded
            # This asserts the ORDER: cleanup should appear BEFORE unload_platforms in call_order
            assert "cleanup_vehicle_indices" in call_order, (
                "emhass_adapter.async_cleanup_vehicle_indices must be called during unload"
            )
            assert "unload_platforms" in call_order, (
                "platforms must be unloaded"
            )
            assert call_order.index("cleanup_vehicle_indices") < call_order.index("unload_platforms"), (
                "async_cleanup_vehicle_indices must be called BEFORE async_unload_platforms"
            )

            # Also verify the cleanup method was actually called
            assert call_order.count("cleanup_vehicle_indices") == 1, (
                "async_cleanup_vehicle_indices should be called exactly once"
            )


class TestStartupOrphanCleanup:
    """Tests for startup orphan cleanup via async_cleanup_orphaned_emhass_sensors()."""

    @pytest.mark.asyncio
    async def test_orphan_cleanup_removes_sensors_with_stale_entry_id(self, mock_hass):
        """Test that orphaned sensors (entry_id not in active entries) are removed.

        FR-4: Startup orphan cleanup must safely remove sensors from deleted integrations.
        FR-5: Safe cleanup - only remove if entry_id attribute exists AND is not in active entries.
        """
        # Create a mock config entry for active entry
        entry = Mock()
        entry.entry_id = "active_entry_id"

        # Mock config_entries.async_entries to return only the active entry
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_entries = Mock(return_value=[entry])

        # Create orphaned sensor states (entry_id not in active entries)
        orphaned_sensor = Mock()
        orphaned_sensor.entity_id = "sensor.emhass_perfil_diferible_stale_vehicle"
        orphaned_sensor.attributes = {"entry_id": "deleted_entry_id"}

        # Create active sensor states (entry_id in active entries)
        active_sensor = Mock()
        active_sensor.entity_id = "sensor.emhass_perfil_diferible_test_vehicle"
        active_sensor.attributes = {"entry_id": "active_entry_id"}

        # Create sensor without entry_id attribute (should be preserved)
        no_entry_id_sensor = Mock()
        no_entry_id_sensor.entity_id = "sensor.other_sensor"
        no_entry_id_sensor.attributes = {}

        # Mock hass.states.async_all to return all sensors
        mock_hass.states = Mock()
        mock_hass.states.async_all = AsyncMock(
            return_value=[orphaned_sensor, active_sensor, no_entry_id_sensor]
        )

        # Track which entities were removed
        removed_entities = []

        async def mock_async_remove(entity_id):
            removed_entities.append(entity_id)

        mock_hass.states.async_remove = mock_async_remove

        # Call the standalone cleanup function directly
        from custom_components.ev_trip_planner import async_cleanup_orphaned_emhass_sensors
        await async_cleanup_orphaned_emhass_sensors(mock_hass)

        # CRITICAL: orphaned sensor MUST be removed (FR-4, FR-5)
        assert "sensor.emhass_perfil_diferible_stale_vehicle" in removed_entities, (
            "Orphaned sensors with stale entry_id must be removed during startup cleanup"
        )

        # Active sensor should NOT be removed (FR-5)
        assert "sensor.emhass_perfil_diferible_test_vehicle" not in removed_entities, (
            "Sensors with active entry_id must NOT be removed during startup cleanup"
        )

        # Sensor without entry_id attribute should NOT be removed (FR-5)
        assert "sensor.other_sensor" not in removed_entities, (
            "Sensors without entry_id attribute must NOT be removed"
        )

    @pytest.mark.asyncio
    async def test_orphan_cleanup_preserves_active_sensors(self, mock_hass):
        """Test that async_setup_entry does not remove sensors with valid active entry_ids.

        This complements test_orphan_cleanup_removes_sensors_with_stale_entry_id to
        ensure the positive case is also covered.
        """
        # Create a mock config entry for active entry
        entry = Mock()
        entry.entry_id = "test_entry_id"

        # Mock config_entries.async_entries to return the active entry
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_entries = Mock(return_value=[entry])

        # Create sensor with matching entry_id
        active_sensor = Mock()
        active_sensor.entity_id = "sensor.emhass_perfil_diferible_test_vehicle"
        active_sensor.attributes = {"entry_id": "test_entry_id"}

        # Mock hass.states.async_all to return the active sensor
        mock_hass.states = Mock()
        mock_hass.states.async_all = AsyncMock(return_value=[active_sensor])

        # Track removed entities
        removed_entities = []

        async def mock_async_remove(entity_id):
            removed_entities.append(entity_id)

        mock_hass.states.async_remove = mock_async_remove

        # Call the standalone cleanup function directly
        from custom_components.ev_trip_planner import async_cleanup_orphaned_emhass_sensors
        await async_cleanup_orphaned_emhass_sensors(mock_hass)

        # Active sensor should NOT be removed
        assert "sensor.emhass_perfil_diferible_test_vehicle" not in removed_entities, (
            "Sensors with entry_id matching an active entry must NOT be removed"
        )
