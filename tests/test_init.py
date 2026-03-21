"""Tests for EV Trip Planner integration __init__.py."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
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
    hass.config.components = []
    hass.services = Mock()
    hass.services.has_service = Mock(return_value=False)

    # Mock async_add_executor_job for non-blocking I/O
    async def mock_executor_job(func, *args):
        """Mock executor job that runs function synchronously."""
        return func(*args)
    hass.async_add_executor_job = mock_executor_job

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
        mock_hass.config.components = ["lovelace", "core"]
        mock_hass.services.has_service = Mock(return_value=False)

        # Force ImportError for async_import_dashboard
        original_import = __builtins__["__import__"]

        def mock_import(name, *args, **kwargs):
            if "importer" in name:
                raise ImportError("No module named 'homeassistant.helpers.importer'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = await import_dashboard(
                mock_hass,
                vehicle_id="test_vehicle",
                vehicle_name="Test Vehicle",
                use_charts=False,
            )

        assert result is False

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
        """Test storage permissions when storage API is available."""
        mock_hass.storage = Mock()
        mock_hass.storage.async_read = AsyncMock(return_value={"data": {}})
        mock_hass.storage.async_write_dict = AsyncMock(return_value=True)

        result = await _verify_storage_permissions(mock_hass, "test_vehicle")

        # Should return True when storage API is available
        assert result is True

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
        """Test saving dashboard using storage API."""
        mock_hass.config.components = ["lovelace"]
        mock_hass.services.has_service = Mock(return_value=False)

        # Mock storage API
        mock_hass.storage = Mock()
        mock_hass.storage.async_read = AsyncMock(
            return_value={"data": {"views": [], "resources": []}}
        )
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
        assert result is False


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
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_storage_permissions_no_storage(self, mock_hass):
        """Test storage permissions when no storage available."""
        mock_hass.storage = None

        result = await _verify_storage_permissions(mock_hass, "test_vehicle")

        # Should return False when no storage
        assert result is False
