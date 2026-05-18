"""Tests for panel registration and management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner import panel


@pytest.fixture
def mock_panel_module():
    """Create a mock panel_custom module."""
    with patch("custom_components.ev_trip_planner.panel.panel_custom") as mock:
        mock.async_register_panel = AsyncMock()
        yield mock


@pytest.fixture
def mock_frontend_module():
    """Create a mock frontend module."""
    with patch("custom_components.ev_trip_planner.panel.frontend") as mock:
        mock.async_register_built_in_panel = AsyncMock()
        mock.async_remove_panel = AsyncMock()
        yield mock


@pytest.fixture
def mock_hass(mock_panel_module):
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.config.components = {"panel_custom"}  # Simulate panel_custom is available
    return hass


class TestAsyncRegisterPanel:
    """Tests for async_register_panel function."""

    @pytest.mark.asyncio
    async def test_register_panel_success(
        self, mock_hass, mock_panel_module, mock_frontend_module
    ):
        """Test successful panel registration."""
        vehicle_id = "test_vehicle"
        vehicle_name = "Test Vehicle"

        # Ensure hass.config.components is properly mocked
        mock_hass.config.components = {"panel_custom"}

        # Call the function
        result = await panel.async_register_panel(
            mock_hass,
            vehicle_id,
            vehicle_name,
        )

        # Verify success
        assert result is True
        mock_panel_module.async_register_panel.assert_called_once()

        # Verify mapping stored
        assert panel.VEHICLE_PANEL_MAPPING_KEY in mock_hass.data
        mapping = mock_hass.data[panel.VEHICLE_PANEL_MAPPING_KEY]
        assert vehicle_id in mapping

    @pytest.mark.asyncio
    async def test_register_panel_multiple_vehicles(
        self, mock_hass, mock_panel_module, mock_frontend_module
    ):
        """Test registering panels for multiple vehicles."""
        # Register first vehicle
        result1 = await panel.async_register_panel(
            mock_hass,
            "vehicle_1",
            "Vehicle 1",
        )
        assert result1 is True

        # Register second vehicle
        result2 = await panel.async_register_panel(
            mock_hass,
            "vehicle_2",
            "Vehicle 2",
        )
        assert result2 is True

        # Verify both mappings exist
        mapping = mock_hass.data[panel.VEHICLE_PANEL_MAPPING_KEY]
        assert len(mapping) == 2
        assert "vehicle_1" in mapping
        assert "vehicle_2" in mapping

    @pytest.mark.asyncio
    async def test_register_panel_exception(
        self, mock_hass, mock_panel_module, mock_frontend_module
    ):
        """Test handling of exceptions during registration."""
        # Ensure hass.config.components is properly mocked
        mock_hass.config.components = {"panel_custom"}

        # Mock exception - make it async
        async def raise_error(*args, **kwargs):
            raise Exception("Test error")

        mock_panel_module.async_register_panel.side_effect = raise_error

        result = await panel.async_register_panel(
            mock_hass,
            "test_vehicle",
            "Test Vehicle",
        )

        # Verify failure is handled
        assert result is False


class TestAsyncUnregisterPanel:
    """Tests for async_unregister_panel function."""

    @pytest.fixture
    def mock_hass_with_mapping(self, mock_frontend_module):
        """Create a mock HA with existing panel mapping."""
        hass = MagicMock()
        hass.data = {
            panel.VEHICLE_PANEL_MAPPING_KEY: {
                "test_vehicle": "ev-trip-planner-test_vehicle",
            }
        }
        return hass

    @pytest.mark.asyncio
    async def test_unregister_panel_success(
        self, mock_hass_with_mapping, mock_frontend_module
    ):
        """Test successful panel unregistration."""
        vehicle_id = "test_vehicle"

        result = await panel.async_unregister_panel(
            mock_hass_with_mapping,
            vehicle_id,
        )

        # Verify success
        assert result is True
        mock_frontend_module.async_remove_panel.assert_called_once()

        # Verify mapping removed
        mapping = mock_hass_with_mapping.data[panel.VEHICLE_PANEL_MAPPING_KEY]
        assert vehicle_id not in mapping

    @pytest.mark.asyncio
    async def test_unregister_panel_exception(
        self, mock_hass_with_mapping, mock_frontend_module
    ):
        """Test handling of exceptions during unregistration."""

        # Mock exception - make it async
        async def raise_error(*args, **kwargs):
            raise Exception("Test error")

        mock_frontend_module.async_remove_panel.side_effect = raise_error

        result = await panel.async_unregister_panel(
            mock_hass_with_mapping,
            "test_vehicle",
        )

        # Verify failure is handled
        assert result is False


class TestGetVehiclePanelUrlPath:
    """Tests for get_vehicle_panel_url_path function."""

    def test_get_existing_url_path(self):
        """Test getting URL path for existing vehicle."""
        hass = MagicMock()
        hass.data = {
            panel.VEHICLE_PANEL_MAPPING_KEY: {
                "vehicle_1": "ev-trip-planner-vehicle_1",
            }
        }

        url_path = panel.get_vehicle_panel_url_path(hass, "vehicle_1")
        assert url_path == "ev-trip-planner-vehicle_1"

    def test_get_nonexistent_url_path(self):
        """Test getting URL path for non-existent vehicle."""
        hass = MagicMock()
        hass.data = {
            panel.VEHICLE_PANEL_MAPPING_KEY: {
                "vehicle_1": "ev-trip-planner-vehicle_1",
            }
        }

        url_path = panel.get_vehicle_panel_url_path(hass, "nonexistent")
        assert url_path is None

    def test_get_url_path_no_mapping(self):
        """Test getting URL path when no mapping exists."""
        hass = MagicMock()
        hass.data = {}

        url_path = panel.get_vehicle_panel_url_path(hass, "vehicle_1")
        assert url_path is None


class TestGetAllPanelMappings:
    """Tests for get_all_panel_mappings function."""

    def test_get_all_mappings(self):
        """Test getting all panel mappings."""
        hass = MagicMock()
        mapping = {
            "vehicle_1": "ev-trip-planner-vehicle_1",
            "vehicle_2": "ev-trip-planner-vehicle_2",
        }
        hass.data = {panel.VEHICLE_PANEL_MAPPING_KEY: mapping}

        result = panel.get_all_panel_mappings(hass)
        assert result == mapping

    def test_get_all_mappings_empty(self):
        """Test getting all mappings when none exist."""
        hass = MagicMock()
        hass.data = {}

        result = panel.get_all_panel_mappings(hass)
        assert result == {}


class TestAsyncRegisterAllPanels:
    """Tests for async_register_all_panels function."""

    @pytest.mark.asyncio
    async def test_register_all_panels(self, mock_panel_module, mock_frontend_module):
        """Test registering panels for all vehicles."""
        hass = MagicMock()
        hass.config.components = {"panel_custom"}

        vehicles = [
            {"vehicle_id": "vehicle_1", "name": "Vehicle 1"},
            {"vehicle_id": "vehicle_2", "name": "Vehicle 2"},
        ]

        await panel.async_register_all_panels(hass, vehicles)

        # Verify both panels registered - check that the function was called for each vehicle
        # The panel module internally iterates through vehicles and calls async_register_panel
        assert mock_panel_module.async_register_panel.call_count == 2

    @pytest.mark.asyncio
    async def test_register_all_panels_empty_list(
        self, mock_panel_module, mock_frontend_module
    ):
        """Test registering panels with empty vehicle list."""
        hass = MagicMock()
        hass.config.components = {"panel_custom"}

        await panel.async_register_all_panels(hass, [])

        # Verify no panels registered
        mock_panel_module.async_register_panel.assert_not_called()
