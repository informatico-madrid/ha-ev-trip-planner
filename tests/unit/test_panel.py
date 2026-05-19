"""Tests for panel registration and management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner import panel
from custom_components.ev_trip_planner.panel import (
    build_frontend_url_path,
    build_module_url,
    build_panel_config,
    build_panel_kwargs,
)


# --- Pure function tests ---


class TestBuildFrontendUrlPath:
    """Tests for the extracted build_frontend_url_path function."""

    def test_build_url_path(self):
        """Test URL path construction from vehicle_id."""
        assert build_frontend_url_path("my_car") == "ev-trip-planner-my_car"

    def test_build_url_path_with_special_chars(self):
        """Test URL path with underscores in vehicle_id."""
        assert build_frontend_url_path("vehicle_1") == "ev-trip-planner-vehicle_1"

    def test_build_url_path_is_unique(self):
        """Different vehicle_ids produce different paths."""
        p1 = build_frontend_url_path("car_a")
        p2 = build_frontend_url_path("car_b")
        assert p1 != p2
        assert "car_a" in p1
        assert "car_b" in p2


class TestBuildPanelConfig:
    """Tests for the extracted build_panel_config function."""

    def test_build_config_has_vehicle_id_key(self):
        """Test that config dict has 'vehicle_id' key."""
        config = build_panel_config("test_vehicle")
        assert "vehicle_id" in config
        assert config["vehicle_id"] == "test_vehicle"

    def test_build_config_rejects_wrong_key(self):
        """Mutated config with different key name is detected."""
        config = build_panel_config("test_vehicle")
        assert "VEHICLE_ID" not in config

    def test_build_config_is_dict(self):
        """Test that result is a dict."""
        config = build_panel_config("v1")
        assert isinstance(config, dict)


class TestBuildModuleUrl:
    """Tests for the extracted build_module_url function."""

    def test_build_module_url_format(self):
        """Test URL has correct path and query param structure."""
        url = build_module_url("test_vehicle")
        assert "/ev-trip-planner/panel.js" in url
        assert "?t=" in url

    def test_build_module_url_contains_cache_bust(self):
        """Test URL contains cache-busting component."""
        url = build_module_url("test_vehicle")
        # cache_bust format: 3.0.11-{timestamp}-{hash}
        assert "3.0.11-" in url

    def test_build_module_url_is_unique_per_vehicle(self):
        """Different vehicle_ids produce different URLs."""
        u1 = build_module_url("car_a")
        u2 = build_module_url("car_b")
        assert u1 != u2


class TestBuildPanelKwargs:
    """Tests for the extracted build_panel_kwargs function."""

    def test_build_kwargs_contains_expected_keys(self):
        """Test all expected keys are present."""
        kwargs = build_panel_kwargs(
            "path", "Vehicle", "url", {"vehicle_id": "v1"}
        )
        expected_keys = {
            "frontend_url_path",
            "webcomponent_name",
            "module_url",
            "sidebar_title",
            "sidebar_icon",
            "config",
            "require_admin",
            "embed_iframe",
        }
        assert set(kwargs.keys()) == expected_keys

    def test_build_kwargs_sidebar_title(self):
        """Test sidebar_title is set correctly."""
        kwargs = build_panel_kwargs("path", "My Car", "url", {})
        assert kwargs["sidebar_title"] == "My Car"

    def test_build_kwargs_config_dict(self):
        """Test config dict is passed through correctly."""
        config = {"vehicle_id": "test_v"}
        kwargs = build_panel_kwargs("path", "V", "url", config)
        assert kwargs["config"] == config

    def test_build_kwargs_require_admin_false(self):
        """Test require_admin defaults to False."""
        kwargs = build_panel_kwargs("p", "V", "u", {})
        assert kwargs["require_admin"] is False

    def test_build_kwargs_embed_iframe_false(self):
        """Test embed_iframe defaults to False."""
        kwargs = build_panel_kwargs("p", "V", "u", {})
        assert kwargs["embed_iframe"] is False


# --- Fixture definitions (previously conftest) ---


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


class TestAsyncRegisterPanel:
    """Tests for async_register_panel function."""

    @pytest.mark.asyncio
    async def test_register_panel_success(
        self, mock_hass_panel, mock_panel_module, mock_frontend_module
    ):
        """Test successful panel registration."""
        vehicle_id = "test_vehicle"
        vehicle_name = "Test Vehicle"

        # Ensure hass.config.components is properly mocked
        mock_hass_panel.config.components = {"panel_custom"}

        # Call the function
        result = await panel.async_register_panel(
            mock_hass_panel,
            vehicle_id,
            vehicle_name,
        )

        # Verify success
        assert result is True
        mock_panel_module.async_register_panel.assert_called_once()

        # Verify mapping stored
        assert panel.VEHICLE_PANEL_MAPPING_KEY in mock_hass_panel.data
        mapping = mock_hass_panel.data[panel.VEHICLE_PANEL_MAPPING_KEY]
        assert vehicle_id in mapping

    @pytest.mark.asyncio
    async def test_register_panel_url_path_stored_correctly(
        self, mock_hass_panel, mock_panel_module, mock_frontend_module
    ):
        """Mutating frontend_url_path to None would store None in mapping.

        This test asserts that the stored URL path matches the expected pattern.
        Catches mutations that replace frontend_url_path with None or wrong value.
        """
        vehicle_id = "test_vehicle"
        expected_path = f"ev-trip-planner-{vehicle_id}"

        mock_hass_panel.config.components = {"panel_custom"}

        await panel.async_register_panel(
            mock_hass_panel, vehicle_id, "Test Vehicle"
        )

        mapping = mock_hass_panel.data[panel.VEHICLE_PANEL_MAPPING_KEY]
        assert mapping[vehicle_id] == expected_path

    @pytest.mark.asyncio
    async def test_register_panel_config_has_vehicle_id_key(
        self, mock_hass_panel, mock_panel_module, mock_frontend_module
    ):
        """Mutating config key to 'VEHICLE_ID' would break panel operation.

        Assert the config dict passed to the framework has 'vehicle_id' key.
        Catches string prefix mutations on the dict key.
        """
        vehicle_id = "test_vehicle"
        mock_hass_panel.config.components = {"panel_custom"}

        await panel.async_register_panel(
            mock_hass_panel, vehicle_id, "Test Vehicle"
        )

        call_kwargs = mock_panel_module.async_register_panel.call_args.kwargs
        config = call_kwargs["config"]
        assert "vehicle_id" in config
        assert config["vehicle_id"] == vehicle_id
        assert "VEHICLE_ID" not in config

    @pytest.mark.asyncio
    async def test_register_panel_sidebar_title_passed_correctly(
        self, mock_hass_panel, mock_panel_module, mock_frontend_module
    ):
        """Mutating sidebar_title to None would show blank in sidebar.

        Assert the sidebar_title arg passed to framework is the vehicle name.
        Catches mutations that replace vehicle_name with None.
        """
        mock_hass_panel.config.components = {"panel_custom"}

        await panel.async_register_panel(
            mock_hass_panel, "v1", "My Electric Car"
        )

        call_kwargs = mock_panel_module.async_register_panel.call_args.kwargs
        assert call_kwargs["sidebar_title"] == "My Electric Car"

    @pytest.mark.asyncio
    async def test_register_panel_module_url_passed_to_framework(
        self, mock_hass_panel, mock_panel_module, mock_frontend_module
    ):
        """Mutating module_url to None or wrong string would break panel loading.

        Assert the module_url arg passed to framework contains expected path.
        Catches string mutations in the URL construction.
        """
        mock_hass_panel.config.components = {"panel_custom"}

        await panel.async_register_panel(
            mock_hass_panel, "test_vehicle", "Test Vehicle"
        )

        call_kwargs = mock_panel_module.async_register_panel.call_args.kwargs
        module_url = call_kwargs["module_url"]
        assert "/ev-trip-planner/panel.js" in module_url
        assert "?t=" in module_url

    @pytest.mark.asyncio
    async def test_register_panel_multiple_vehicles(
        self, mock_hass_panel, mock_panel_module, mock_frontend_module
    ):
        """Test registering panels for multiple vehicles."""
        # Register first vehicle
        result1 = await panel.async_register_panel(
            mock_hass_panel,
            "vehicle_1",
            "Vehicle 1",
        )
        assert result1 is True

        # Register second vehicle
        result2 = await panel.async_register_panel(
            mock_hass_panel,
            "vehicle_2",
            "Vehicle 2",
        )
        assert result2 is True

        # Verify both mappings exist
        mapping = mock_hass_panel.data[panel.VEHICLE_PANEL_MAPPING_KEY]
        assert len(mapping) == 2
        assert "vehicle_1" in mapping
        assert "vehicle_2" in mapping

    @pytest.mark.asyncio
    async def test_register_panel_exception(
        self, mock_hass_panel, mock_panel_module, mock_frontend_module
    ):
        """Test handling of exceptions during registration."""
        mock_hass_panel.config.components = {"panel_custom"}

        async def raise_error(*args, **kwargs):
            raise Exception("Test error")

        mock_panel_module.async_register_panel.side_effect = raise_error

        result = await panel.async_register_panel(
            mock_hass_panel,
            "test_vehicle",
            "Test Vehicle",
        )

        assert result is False


class TestAsyncUnregisterPanel:
    """Tests for async_unregister_panel function."""

    @pytest.mark.asyncio
    async def test_unregister_panel_success(
        self, mock_hass_panel_with_mapping, mock_frontend_module
    ):
        """Test successful panel unregistration."""
        vehicle_id = "test_vehicle"

        result = await panel.async_unregister_panel(
            mock_hass_panel_with_mapping,
            vehicle_id,
        )

        assert result is True
        mock_frontend_module.async_remove_panel.assert_called_once()

        mapping = mock_hass_panel_with_mapping.data[panel.VEHICLE_PANEL_MAPPING_KEY]
        assert vehicle_id not in mapping

    @pytest.mark.asyncio
    async def test_unregister_panel_passes_url_path_to_remove(
        self, mock_hass_panel_with_mapping, mock_frontend_module
    ):
        """Mutating frontend_url_path to None in remove_fn call would remove wrong panel.

        Assert the framework call receives the correct URL path.
        Catches mutations that replace frontend_url_path with None.
        """
        vehicle_id = "test_vehicle"
        expected_path = f"ev-trip-planner-{vehicle_id}"

        await panel.async_unregister_panel(
            mock_hass_panel_with_mapping, vehicle_id
        )

        call_args = mock_frontend_module.async_remove_panel.call_args
        # The call is: remove_fn(hass, frontend_url_path)
        assert call_args.args[1] == expected_path

    @pytest.mark.asyncio
    async def test_unregister_panel_exception(
        self, mock_hass_panel_with_mapping, mock_frontend_module
    ):
        """Test handling of exceptions during unregistration."""

        async def raise_error(*args, **kwargs):
            raise Exception("Test error")

        mock_frontend_module.async_remove_panel.side_effect = raise_error

        result = await panel.async_unregister_panel(
            mock_hass_panel_with_mapping,
            "test_vehicle",
        )

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

        assert mock_panel_module.async_register_panel.call_count == 2

    @pytest.mark.asyncio
    async def test_register_all_panels_empty_list(
        self, mock_panel_module, mock_frontend_module
    ):
        """Test registering panels with empty vehicle list."""
        hass = MagicMock()
        hass.config.components = {"panel_custom"}

        await panel.async_register_all_panels(hass, [])

        mock_panel_module.async_register_panel.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_all_panels_uses_vehicle_name(
        self, mock_panel_module, mock_frontend_module
    ):
        """Mutating vehicle_name to None or default would affect sidebar display.

        Assert the vehicle name is correctly extracted and passed through.
        Catches mutations on the vehicle.get("name", ...) chain.
        """
        mock_panel_module.async_register_panel = AsyncMock()
        hass = MagicMock()
        hass.config.components = {"panel_custom"}

        vehicles = [
            {"vehicle_id": "v1", "name": "My Tesla"},
        ]

        await panel.async_register_all_panels(hass, vehicles)

        call_kwargs = mock_panel_module.async_register_panel.call_args.kwargs
        assert call_kwargs["sidebar_title"] == "My Tesla"

    @pytest.mark.asyncio
    async def test_register_all_panels_uses_fallback_name(
        self, mock_panel_module, mock_frontend_module
    ):
        """Test that fallback name works when 'name' key is missing."""
        mock_panel_module.async_register_panel = AsyncMock()
        hass = MagicMock()
        hass.config.components = {"panel_custom"}

        vehicles = [
            {"vehicle_id": "v1"},  # No 'name' key
        ]

        await panel.async_register_all_panels(hass, vehicles)

        call_kwargs = mock_panel_module.async_register_panel.call_args.kwargs
        # Fallback: vehicle.get("vehicle_id", "Unknown")
        assert call_kwargs["sidebar_title"] == "v1"
