"""Tests for EV Trip Planner integration __init__.py."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner import (
    is_lovelace_available,
    import_dashboard,
    TripPlannerCoordinator,
)


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.config = Mock()
    hass.config.components = []
    hass.services = Mock()
    hass.services.has_service = Mock(return_value=False)
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

        assert result is False

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

        assert result is True
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

        assert result is True

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
        """Test dashboard import handles exception."""
        mock_hass.config.components = ["lovelace", "core"]
        mock_hass.services.has_service = Mock(side_effect=Exception("Test error"))

        result = await import_dashboard(
            mock_hass,
            vehicle_id="test_vehicle",
            vehicle_name="Test Vehicle",
            use_charts=False,
        )

        assert result is False


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
