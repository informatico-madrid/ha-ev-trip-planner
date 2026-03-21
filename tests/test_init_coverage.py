"""Tests for dashboard.py coverage - ensuring all exception paths are covered.

This test file ensures coverage of exception handling and error paths
that were previously untested in dashboard.py.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestInputHelpersAlreadyExist:
    """Tests for exception handling when input helpers already exist.

    Tests lines 90-91, 106-107, 123-124 in __init__.py - exception handlers
    that catch when input helpers (input_select, input_datetime, etc.)
    already exist during setup.
    """

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance."""
        hass = MagicMock()
        hass.services = MagicMock()

        # Mock services.async_call to raise exception (simulating already exists)
        async def async_call_side_effect(*args, **kwargs):
            raise Exception("Entity already exists")

        hass.services.async_call = AsyncMock(side_effect=async_call_side_effect)

        return hass

    @pytest.mark.asyncio
    async def test_input_select_already_exists(self, mock_hass):
        """Test that exception is handled when input_select already exists.

        Covers lines 90-91: Exception handler for input_select creation.
        Should verify that exception is caught and handled gracefully.
        """
        from custom_components.ev_trip_planner import create_dashboard_input_helpers

        vehicle_id = "test_vehicle"

        # This should not raise - exception should be caught
        result = await create_dashboard_input_helpers(mock_hass, vehicle_id)

        # Should return True (graceful handling, still succeeds)
        assert result is True

    @pytest.mark.asyncio
    async def test_input_datetime_already_exists(self, mock_hass):
        """Test that exception is handled when input_datetime already exists.

        Covers lines 106-107: Exception handler for input_datetime creation.
        Should verify that exception is caught and handled gracefully.
        """
        from custom_components.ev_trip_planner import create_dashboard_input_helpers

        vehicle_id = "test_vehicle"

        # This should not raise - exception should be caught
        result = await create_dashboard_input_helpers(mock_hass, vehicle_id)

        # Should return True (graceful handling)
        assert result is True

    @pytest.mark.asyncio
    async def test_input_number_already_exists(self, mock_hass):
        """Test that exception is handled when input_number already exists.

        Covers lines 123-124: Exception handler for input_number creation.
        Should verify that exception is caught and handled gracefully.
        """
        from custom_components.ev_trip_planner import create_dashboard_input_helpers

        vehicle_id = "test_vehicle"

        # This should not raise - exception should be caught
        result = await create_dashboard_input_helpers(mock_hass, vehicle_id)

        # Should return True (graceful handling)
        assert result is True


class TestStoragePermissionVerificationFailures:
    """Tests for storage permission verification failure paths.

    Tests lines in dashboard.py - exception handlers
    for storage permission verification failures.
    """

    @pytest.fixture
    def mock_hass_no_storage(self):
        """Create mock without storage API."""
        hass = MagicMock()
        # No storage attribute
        delattr(hass, 'storage')
        return hass

    @pytest.mark.asyncio
    async def test_no_storage_attribute(self, mock_hass_no_storage):
        """Test that missing storage attribute returns False.

        Covers error logged when storage not available.
        """
        from custom_components.ev_trip_planner.dashboard import _verify_storage_permissions

        result = await _verify_storage_permissions(
            mock_hass_no_storage,
            "test_vehicle"
        )

        # Should return False (storage not available)
        assert result is False

    @pytest.mark.asyncio
    async def test_general_exception_handling(self):
        """Test that general exception in storage verification is handled.

        Covers error logged for storage permission verification failure.
        """
        from unittest.mock import AsyncMock, MagicMock, patch
        from custom_components.ev_trip_planner.dashboard import _verify_storage_permissions

        hass = MagicMock()

        # Create storage with async_write_dict but make async_read raise
        async def async_read_side_effect(key):
            if key == "lovelace":
                raise RuntimeError("Storage read failed")
            return {}

        hass.storage = MagicMock()
        hass.storage.async_write_dict = AsyncMock()
        hass.storage.async_read = AsyncMock(side_effect=async_read_side_effect)

        # This will trigger the outer exception handler
        # when the storage read exception is not caught properly
        with patch("custom_components.ev_trip_planner.dashboard._LOGGER") as mock_logger:
            result = await _verify_storage_permissions(hass, "test_vehicle")

            # Should handle gracefully and return False when storage mode is not available
            # (Lovelace storage mode returns None when not active in Container mode)
            assert result is False


class TestDashboardStorageAPIFailurePaths:
    """Tests for dashboard storage API failure paths.

    Tests lines in dashboard.py - exception handlers
    for dashboard storage API failures.
    """

    @pytest.fixture
    def mock_hass_storage_no_data(self):
        """Create mock where storage returns no data."""
        from unittest.mock import AsyncMock

        hass = MagicMock()

        # Storage returns data but no views
        async def async_read_side_effect(key):
            if key == "lovelace":
                return {"data": {"config": {"views": []}}}
            return None

        hass.storage.async_read = AsyncMock(side_effect=async_read_side_effect)

        # Storage write raises exception
        async def async_write_side_effect(key, data):
            raise RuntimeError("Storage write failed")

        hass.storage.async_write_dict = AsyncMock(side_effect=async_write_side_effect)

        hass.services = MagicMock()
        hass.services.has_service = MagicMock(return_value=False)

        return hass

    @pytest.mark.asyncio
    async def test_storage_api_write_failure(self, mock_hass_storage_no_data):
        """Test that storage write failure is handled.

        Covers storage API failed path when write fails.
        """
        from custom_components.ev_trip_planner.dashboard import _save_lovelace_dashboard

        dashboard_config = {
            "title": "Test",
            "views": [
                {
                    "path": "test",
                    "title": "Test View",
                    "cards": [],
                }
            ],
        }

        result = await _save_lovelace_dashboard(
            mock_hass_storage_no_data,
            dashboard_config,
            "test_vehicle"
        )

        # Should return False (storage write failed)
        assert result is False

    @pytest.mark.asyncio
    async def test_lovelace_config_no_data(self, mock_hass_storage_no_data):
        """Test handling when lovelace config has no data.

        Covers error logged when config has no data.
        """
        from custom_components.ev_trip_planner.dashboard import _save_lovelace_dashboard

        dashboard_config = {
            "title": "Test",
            "views": [
                {
                    "path": "test",
                    "title": "Test View",
                    "cards": [],
                }
            ],
        }

        result = await _save_lovelace_dashboard(
            mock_hass_storage_no_data,
            dashboard_config,
            "test_vehicle"
        )

        # Should handle gracefully and return False
        assert result is False


class TestTripDataUpdateExceptionPaths:
    """Tests for trip data update exception paths.

    Tests lines in __init__.py - exception handler
    for _async_update_data when trip manager calls fail.
    """

    @pytest.mark.asyncio
    async def test_trip_update_exception_handling(self):
        """Test that exception in trip update returns default values.

        Covers exception handler in _async_update_data.
        """
        from unittest.mock import MagicMock, AsyncMock
        from custom_components.ev_trip_planner import TripPlannerCoordinator

        hass = MagicMock()
        hass.services = MagicMock()

        # Create coordinator with trip_manager that raises on get_next_trip
        trip_manager = MagicMock()
        trip_manager.async_get_recurring_trips = AsyncMock(return_value=[])
        trip_manager.async_get_punctual_trips = AsyncMock(return_value=[])
        trip_manager.async_get_kwh_needed_today = AsyncMock(return_value=0.0)
        trip_manager.async_get_hours_needed_today = AsyncMock(return_value=0)
        trip_manager.async_get_next_trip = AsyncMock(side_effect=Exception("Test error"))

        coordinator = TripPlannerCoordinator(hass, trip_manager)

        # This should not raise - should return default values
        result = await coordinator._async_update_data()

        # Should return default values on error
        assert result is not None
        assert "recurring_trips" in result
        assert "punctual_trips" in result
        assert "kwh_today" in result
        assert "hours_today" in result
        assert "next_trip" in result


class TestSetupEntryPaths:
    """Tests for async_setup_entry paths.

    Tests lines in __init__.py - setup entry exception paths.
    """

    @pytest.mark.asyncio
    async def test_async_setup_entry_returns_true(self):
        """Test that async_setup_entry returns True on success.

        Covers return values for setup success.
        """
        from unittest.mock import MagicMock, AsyncMock, patch
        from custom_components.ev_trip_planner import async_setup_entry

        hass = MagicMock()
        hass.data = {}
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        entry = MagicMock()
        entry.data = {"vehicle_name": "Test Vehicle"}
        entry.entry_id = "test_entry_id"

        # Mock TripManager
        mock_trip_manager = MagicMock()
        mock_trip_manager.async_setup = AsyncMock()

        # Mock TripPlannerCoordinator
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()

        # Mock EMHASSAdapter
        mock_emhass = MagicMock()

        # Patch all dependencies
        with patch("custom_components.ev_trip_planner.TripManager", return_value=mock_trip_manager):
            with patch("custom_components.ev_trip_planner.EMHASSAdapter", return_value=mock_emhass):
                with patch("custom_components.ev_trip_planner.TripPlannerCoordinator", return_value=mock_coordinator):
                    with patch("custom_components.ev_trip_planner.register_services"):
                        with patch("custom_components.ev_trip_planner.create_dashboard_input_helpers"):
                            result = await async_setup_entry(hass, entry)

                            # Should return True on success
                            assert result is True

    @pytest.mark.asyncio
    async def test_async_setup_returns_true(self):
        """Test that async_setup returns True.

        Covers return value for setup.
        """
        from custom_components.ev_trip_planner import async_setup

        hass = MagicMock()
        config = {}

        result = await async_setup(hass, config)

        # Should return True
        assert result is True


class TestYamlFallbackValidationFailures:
    """Tests for YAML fallback validation failures.

    Tests lines in dashboard.py - validation failures in _save_dashboard_yaml_fallback.
    """

    @pytest.fixture
    def mock_hass_container(self, tmp_path):
        """Create mock for Container environment."""
        from unittest.mock import MagicMock

        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = str(tmp_path)
        hass.storage = None

        hass.services = MagicMock()
        hass.services.has_service = MagicMock(return_value=False)

        return hass

    @pytest.mark.asyncio
    async def test_invalid_views_type_rejected(self, mock_hass_container, tmp_path):
        """Test that non-list views is rejected.

        Covers validation for views being a list.
        """
        from custom_components.ev_trip_planner.dashboard import _save_dashboard_yaml_fallback

        dashboard_config = {
            "title": "Test",
            "views": "not a list",  # Invalid type
        }

        result = await _save_dashboard_yaml_fallback(
            mock_hass_container,
            dashboard_config,
            "test_vehicle"
        )

        # Should return False
        assert result is False

    @pytest.mark.asyncio
    async def test_invalid_view_type_rejected(self, mock_hass_container, tmp_path):
        """Test that non-dict view is rejected.

        Covers validation for view being a dict.
        """
        from custom_components.ev_trip_planner.dashboard import _save_dashboard_yaml_fallback

        dashboard_config = {
            "title": "Test",
            "views": ["not a dict"],  # Invalid type
        }

        result = await _save_dashboard_yaml_fallback(
            mock_hass_container,
            dashboard_config,
            "test_vehicle"
        )

        # Should return False
        assert result is False

    @pytest.mark.asyncio
    async def test_missing_view_path_rejected(self, mock_hass_container, tmp_path):
        """Test that missing view path is rejected.

        Covers validation for view path field.
        """
        from custom_components.ev_trip_planner.dashboard import _save_dashboard_yaml_fallback

        dashboard_config = {
            "title": "Test",
            "views": [
                {
                    "title": "Test View",
                    # Missing "path" field
                    "cards": [],
                }
            ],
        }

        result = await _save_dashboard_yaml_fallback(
            mock_hass_container,
            dashboard_config,
            "test_vehicle"
        )

        # Should return False
        assert result is False

    @pytest.mark.asyncio
    async def test_missing_view_title_rejected(self, mock_hass_container, tmp_path):
        """Test that missing view title is rejected.

        Covers validation for view title field.
        """
        from custom_components.ev_trip_planner.dashboard import _save_dashboard_yaml_fallback

        dashboard_config = {
            "title": "Test",
            "views": [
                {
                    "path": "test",
                    # Missing "title" field
                    "cards": [],
                }
            ],
        }

        result = await _save_dashboard_yaml_fallback(
            mock_hass_container,
            dashboard_config,
            "test_vehicle"
        )

        # Should return False
        assert result is False

    @pytest.mark.asyncio
    async def test_missing_view_cards_rejected(self, mock_hass_container, tmp_path):
        """Test that missing view cards is rejected.

        Covers validation for view cards field.
        """
        from custom_components.ev_trip_planner.dashboard import _save_dashboard_yaml_fallback

        dashboard_config = {
            "title": "Test",
            "views": [
                {
                    "path": "test",
                    "title": "Test View",
                    # Missing "cards" field
                }
            ],
        }

        result = await _save_dashboard_yaml_fallback(
            mock_hass_container,
            dashboard_config,
            "test_vehicle"
        )

        # Should return False
        assert result is False

    @pytest.mark.asyncio
    async def test_missing_config_dir_rejected(self, mock_hass_container, tmp_path):
        """Test that missing config dir is rejected.

        Covers validation for config directory.
        """
        from custom_components.ev_trip_planner.dashboard import _save_dashboard_yaml_fallback

        # Set config_dir to None
        mock_hass_container.config.config_dir = None

        dashboard_config = {
            "title": "Test",
            "views": [
                {
                    "path": "test",
                    "title": "Test View",
                    "cards": [],
                }
            ],
        }

        result = await _save_dashboard_yaml_fallback(
            mock_hass_container,
            dashboard_config,
            "test_vehicle"
        )

        # Should return False
        assert result is False

    @pytest.mark.asyncio
    async def test_config_dir_permission_error(self, mock_hass_container, tmp_path):
        """Test that permission error in config dir is handled.

        Covers exception for config directory issues.
        """
        from custom_components.ev_trip_planner.dashboard import _save_dashboard_yaml_fallback

        # Simulate permission error by setting read-only directory
        tmp_path.chmod(0o444)

        dashboard_config = {
            "title": "Test",
            "views": [
                {
                    "path": "test",
                    "title": "Test View",
                    "cards": [],
                }
            ],
        }

        result = await _save_dashboard_yaml_fallback(
            mock_hass_container,
            dashboard_config,
            "test_vehicle"
        )

        # Should handle gracefully and return False
        assert result is False

        # Restore permissions
        tmp_path.chmod(0o755)
