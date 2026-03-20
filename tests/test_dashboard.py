"""Tests for EV Trip Planner Dashboard YAML structure."""

import pytest
import yaml
from pathlib import Path

# Path to the dashboard templates
DASHBOARD_DIR = (
    Path(__file__).parent.parent
    / "custom_components"
    / "ev_trip_planner"
    / "dashboard"
)


class TestDashboardYAMLSructure:
    """Tests for dashboard YAML file structure."""

    def test_dashboard_directory_exists(self):
        """Test that the dashboard directory exists."""
        assert DASHBOARD_DIR.exists(), "Dashboard directory should exist"
        assert DASHBOARD_DIR.is_dir(), "Dashboard path should be a directory"

    def test_full_dashboard_yaml_exists(self):
        """Test that ev-trip-planner-full.yaml exists."""
        full_path = DASHBOARD_DIR / "ev-trip-planner-full.yaml"
        assert full_path.exists(), "ev-trip-planner-full.yaml should exist"

    def test_simple_dashboard_yaml_exists(self):
        """Test that ev-trip-planner-simple.yaml exists."""
        simple_path = DASHBOARD_DIR / "ev-trip-planner-simple.yaml"
        assert simple_path.exists(), "ev-trip-planner-simple.yaml should exist"

    def test_vehicle_dashboard_yaml_exists(self):
        """Test that ev-trip-planner-{vehicle_id}.yaml exists."""
        vehicle_path = DASHBOARD_DIR / "ev-trip-planner-{vehicle_id}.yaml"
        assert vehicle_path.exists(), "ev-trip-planner-{vehicle_id}.yaml should exist"


class TestFullDashboardYAML:
    """Tests for ev-trip-planner-full.yaml structure."""

    @pytest.fixture
    def full_dashboard(self):
        """Load the full dashboard YAML."""
        full_path = DASHBOARD_DIR / "ev-trip-planner-full.yaml"
        with open(full_path, "r") as f:
            return yaml.safe_load(f)

    def test_full_dashboard_has_title(self, full_dashboard):
        """Test full dashboard has title with vehicle_name variable."""
        assert "title" in full_dashboard
        assert "vehicle_name" in full_dashboard["title"]

    def test_full_dashboard_has_views(self, full_dashboard):
        """Test full dashboard has views list."""
        assert "views" in full_dashboard
        assert isinstance(full_dashboard["views"], list)
        assert len(full_dashboard["views"]) > 0

    def test_full_dashboard_first_view_has_title(self, full_dashboard):
        """Test first view has title."""
        first_view = full_dashboard["views"][0]
        assert "title" in first_view
        assert "vehicle_name" in first_view["title"]

    def test_full_dashboard_first_view_has_path(self, full_dashboard):
        """Test first view has path with vehicle_id variable."""
        first_view = full_dashboard["views"][0]
        assert "path" in first_view
        assert "vehicle_id" in first_view["path"]

    def test_full_dashboard_first_view_has_cards(self, full_dashboard):
        """Test first view has cards list."""
        first_view = full_dashboard["views"][0]
        assert "cards" in first_view
        assert isinstance(first_view["cards"], list)
        assert len(first_view["cards"]) > 0

    def test_full_dashboard_has_crud_view(self, full_dashboard):
        """Test full dashboard has CRUD view."""
        crud_view = None
        for view in full_dashboard["views"]:
            if "crud" in view.get("path", ""):
                crud_view = view
                break

        assert crud_view is not None, "Dashboard should have a CRUD view"
        assert "cards" in crud_view
        assert len(crud_view["cards"]) > 0

    def test_full_dashboard_has_recurring_trips_card(self, full_dashboard):
        """Test full dashboard has recurring trips card."""
        first_view = full_dashboard["views"][0]
        has_recurring = False
        for card in first_view.get("cards", []):
            if card.get("type") == "markdown":
                title = card.get("title", "")
                if "Recurrentes" in title or "Recurring" in title:
                    has_recurring = True
                    break
        assert has_recurring, "Dashboard should have a recurring trips card"

    def test_full_dashboard_has_punctual_trips_card(self, full_dashboard):
        """Test full dashboard has punctual trips card."""
        first_view = full_dashboard["views"][0]
        has_punctual = False
        for card in first_view.get("cards", []):
            if card.get("type") == "markdown":
                title = card.get("title", "")
                if "Puntuales" in title or "Punctual" in title:
                    has_punctual = True
                    break
        assert has_punctual, "Dashboard should have a punctual trips card"

    def test_full_dashboard_has_button_cards(self, full_dashboard):
        """Test full dashboard has button cards for CRUD operations."""
        # Look for button-card types in the CRUD view
        has_button_cards = False
        for view in full_dashboard.get("views", []):
            if "crud" in view.get("path", ""):
                for card in view.get("cards", []):
                    if card.get("type") == "custom:button-card":
                        has_button_cards = True
                        break
                break
        assert has_button_cards, (
            "Dashboard should have button cards for CRUD operations"
        )


class TestSimpleDashboardYAML:
    """Tests for ev-trip-planner-simple.yaml structure."""

    @pytest.fixture
    def simple_dashboard(self):
        """Load the simple dashboard YAML."""
        simple_path = DASHBOARD_DIR / "ev-trip-planner-simple.yaml"
        with open(simple_path, "r") as f:
            return yaml.safe_load(f)

    def test_simple_dashboard_has_title(self, simple_dashboard):
        """Test simple dashboard has title with vehicle_name variable."""
        assert "title" in simple_dashboard
        assert "vehicle_name" in simple_dashboard["title"]

    def test_simple_dashboard_has_views(self, simple_dashboard):
        """Test simple dashboard has views list."""
        assert "views" in simple_dashboard
        assert isinstance(simple_dashboard["views"], list)
        assert len(simple_dashboard["views"]) > 0

    def test_simple_dashboard_first_view_has_cards(self, simple_dashboard):
        """Test first view has cards list."""
        first_view = simple_dashboard["views"][0]
        assert "cards" in first_view
        assert isinstance(first_view["cards"], list)
        assert len(first_view["cards"]) > 0

    def test_simple_dashboard_has_crud_view(self, simple_dashboard):
        """Test simple dashboard has CRUD view."""
        crud_view = None
        for view in simple_dashboard["views"]:
            if "crud" in view.get("path", ""):
                crud_view = view
                break

        assert crud_view is not None, "Dashboard should have a CRUD view"

    def test_simple_dashboard_uses_only_markdown_cards(self, simple_dashboard):
        """Test simple dashboard primarily uses markdown cards (no charts)."""
        first_view = simple_dashboard["views"][0]
        card_types = [card.get("type") for card in first_view.get("cards", [])]

        # Simple dashboard should use markdown cards primarily
        markdown_count = sum(1 for t in card_types if t == "markdown")
        assert markdown_count > 0, "Simple dashboard should have markdown cards"


class TestVehicleDashboardYAML:
    """Tests for ev-trip-planner-{vehicle_id}.yaml structure."""

    @pytest.fixture
    def vehicle_dashboard(self):
        """Load the vehicle-specific dashboard YAML."""
        vehicle_path = DASHBOARD_DIR / "ev-trip-planner-{vehicle_id}.yaml"
        with open(vehicle_path, "r") as f:
            return yaml.safe_load(f)

    def test_vehicle_dashboard_has_title(self, vehicle_dashboard):
        """Test vehicle dashboard has title."""
        assert "title" in vehicle_dashboard

    def test_vehicle_dashboard_has_views(self, vehicle_dashboard):
        """Test vehicle dashboard has views list."""
        assert "views" in vehicle_dashboard
        assert isinstance(vehicle_dashboard["views"], list)


class TestDashboardVariableSubstitution:
    """Tests for dashboard variable substitution."""

    def test_variable_substitution_full_dashboard(self):
        """Test variable substitution in full dashboard."""
        full_path = DASHBOARD_DIR / "ev-trip-planner-full.yaml"
        with open(full_path, "r") as f:
            content = f.read()

        # Check for variable placeholders
        assert "{{ vehicle_id }}" in content or "{{vehicle_id}}" in content, \
            "Full dashboard should contain vehicle_id placeholder"
        assert "{{ vehicle_name }}" in content or "{{vehicle_name}}" in content, \
            "Full dashboard should contain vehicle_name placeholder"

    def test_variable_substitution_simple_dashboard(self):
        """Test variable substitution in simple dashboard."""
        simple_path = DASHBOARD_DIR / "ev-trip-planner-simple.yaml"
        with open(simple_path, "r") as f:
            content = f.read()

        # Check for variable placeholders
        assert "{{ vehicle_id }}" in content or "{{vehicle_id}}" in content, \
            "Simple dashboard should contain vehicle_id placeholder"
        assert "{{ vehicle_name }}" in content or "{{vehicle_name}}" in content, \
            "Simple dashboard should contain vehicle_name placeholder"

    def test_variable_substitution_vehicle_dashboard(self):
        """Test variable substitution in vehicle dashboard."""
        vehicle_path = DASHBOARD_DIR / "ev-trip-planner-{vehicle_id}.yaml"
        with open(vehicle_path, "r") as f:
            content = f.read()

        # Check for variable placeholders
        assert "{{ vehicle_id }}" in content or "{{vehicle_id}}" in content, \
            "Vehicle dashboard should contain vehicle_id placeholder"
        assert "{{ vehicle_name }}" in content or "{{vehicle_name}}" in content, \
            "Vehicle dashboard should contain vehicle_name placeholder"


class TestDashboardCRUDOperations:
    """Tests for CRUD operation support in dashboards."""

    def test_full_dashboard_has_create_recurring_trip_button(self):
        """Test full dashboard has button to create recurring trips."""
        full_path = DASHBOARD_DIR / "ev-trip-planner-full.yaml"
        with open(full_path, "r") as f:
            content = f.read()

        assert "add_recurring_trip" in content, \
            "Full dashboard should have add_recurring_trip service call"

    def test_full_dashboard_has_create_punctual_trip_button(self):
        """Test full dashboard has button to create punctual trips."""
        full_path = DASHBOARD_DIR / "ev-trip-planner-full.yaml"
        with open(full_path, "r") as f:
            content = f.read()

        assert "add_punctual_trip" in content, \
            "Full dashboard should have add_punctual_trip service call"

    def test_full_dashboard_has_pause_resume_buttons(self):
        """Test full dashboard has pause and resume buttons."""
        full_path = DASHBOARD_DIR / "ev-trip-planner-full.yaml"
        with open(full_path, "r") as f:
            content = f.read()

        assert "pause_recurring_trip" in content, \
            "Full dashboard should have pause_recurring_trip service"
        assert "resume_recurring_trip" in content, \
            "Full dashboard should have resume_recurring_trip service"

    def test_full_dashboard_has_delete_button(self):
        """Test full dashboard has delete button."""
        full_path = DASHBOARD_DIR / "ev-trip-planner-full.yaml"
        with open(full_path, "r") as f:
            content = f.read()

        assert "delete_trip" in content, \
            "Full dashboard should have delete_trip service"

    def test_full_dashboard_has_complete_cancel_buttons(self):
        """Test full dashboard has complete and cancel buttons for punctual trips."""
        full_path = DASHBOARD_DIR / "ev-trip-planner-full.yaml"
        with open(full_path, "r") as f:
            content = f.read()

        assert "complete_punctual_trip" in content, \
            "Full dashboard should have complete_punctual_trip service"
        assert "cancel_punctual_trip" in content, \
            "Full dashboard should have cancel_punctual_trip service"

    def test_simple_dashboard_has_crud_services(self):
        """Test simple dashboard has CRUD services defined."""
        simple_path = DASHBOARD_DIR / "ev-trip-planner-simple.yaml"
        with open(simple_path, "r") as f:
            content = f.read()

        # Simple dashboard should mention available services
        assert "ev_trip_planner.add_recurring_trip" in content or \
               "add_recurring_trip" in content, \
            "Simple dashboard should reference add_recurring_trip service"


class TestDashboardResponsiveness:
    """Tests for dashboard responsiveness."""

    def test_full_dashboard_has_column_config(self):
        """Test full dashboard has column configuration for responsiveness."""
        full_path = DASHBOARD_DIR / "ev-trip-planner-full.yaml"
        with open(full_path, "r") as f:
            content = f.read()

        # Check for column configuration
        assert "columns:" in content, \
            "Full dashboard should have column configuration"

    def test_full_dashboard_has_mobile_styles(self):
        """Test full dashboard has mobile-responsive styles."""
        full_path = DASHBOARD_DIR / "ev-trip-planner-full.yaml"
        with open(full_path, "r") as f:
            content = f.read()

        # Check for media queries or responsive styles
        assert "@media" in content or "max-width" in content, \
            "Full dashboard should have responsive CSS for mobile"


class TestDashboardRefreshInterval:
    """Tests for dashboard auto-refresh."""

    def test_full_dashboard_has_refresh_interval(self):
        """Test full dashboard has refresh interval configured."""
        full_path = DASHBOARD_DIR / "ev-trip-planner-full.yaml"
        with open(full_path, "r") as f:
            content = f.read()

        assert "refresh_interval" in content, \
            "Full dashboard should have refresh_interval configured"

    def test_simple_dashboard_has_refresh_interval(self):
        """Test simple dashboard has refresh interval configured."""
        simple_path = DASHBOARD_DIR / "ev-trip-planner-simple.yaml"
        with open(simple_path, "r") as f:
            content = f.read()

        assert "refresh_interval" in content, \
            "Simple dashboard should have refresh_interval configured"


class TestDashboardImport:
    """Tests for dashboard import functionality."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance for dashboard import tests."""
        from unittest.mock import MagicMock, AsyncMock

        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        hass.config.components = ["lovelace"]

        # Mock storage
        hass.storage = MagicMock()
        hass.storage.async_read = AsyncMock(return_value={
            "data": {"config": {"views": []}}
        })
        hass.storage.async_write_dict = AsyncMock(return_value=True)

        # Mock services
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.services.has_service = MagicMock(return_value=True)

        return hass

    @pytest.fixture
    def dashboard_module(self):
        """Import and return the ev_trip_planner module."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components"))
        from custom_components.ev_trip_planner import import_dashboard
        return import_dashboard

    @pytest.mark.asyncio
    async def test_import_dashboard_loads_template(self, mock_hass, dashboard_module):
        """Test that import_dashboard loads the YAML template correctly."""
        # This test verifies the template loading works
        from custom_components.ev_trip_planner import _load_dashboard_template

        result = await _load_dashboard_template(
            "test_vehicle",
            "Test Vehicle",
            use_charts=False
        )

        assert result is not None, "Template should load successfully"
        assert "title" in result, "Dashboard should have a title"
        assert "views" in result, "Dashboard should have views"

    @pytest.mark.asyncio
    async def test_import_dashboard_with_full_template(
        self, mock_hass, dashboard_module
    ):
        """Test that import_dashboard loads the full template correctly."""
        from custom_components.ev_trip_planner import _load_dashboard_template

        result = await _load_dashboard_template(
            "test_vehicle",
            "Test Vehicle",
            use_charts=True
        )

        assert result is not None, "Full template should load successfully"
        assert "title" in result, "Dashboard should have a title"
        assert "views" in result, "Dashboard should have views"

    @pytest.mark.asyncio
    async def test_import_dashboard_substitutes_vehicle_id(
        self, mock_hass, dashboard_module
    ):
        """Test that vehicle_id is substituted in the template."""
        from custom_components.ev_trip_planner import _load_dashboard_template

        vehicle_id = "my_tesla_123"

        result = await _load_dashboard_template(
            vehicle_id,
            "My Tesla",
            use_charts=False
        )

        assert result is not None
        # The template should have the vehicle_id in its paths/titles
        result_str = str(result)
        assert vehicle_id in result_str or "my_tesla" in result_str.lower(), \
            "Vehicle ID should be in the loaded template"

    @pytest.mark.asyncio
    async def test_import_dashboard_substitutes_vehicle_name(
        self, mock_hass, dashboard_module
    ):
        """Test that vehicle_name is substituted in the template."""
        from custom_components.ev_trip_planner import _load_dashboard_template

        vehicle_name = "Family EV"

        result = await _load_dashboard_template(
            "test_vehicle",
            vehicle_name,
            use_charts=False
        )

        assert result is not None
        # The template should have the vehicle_name in its titles
        result_str = str(result)
        assert vehicle_name in result_str or "family" in result_str.lower(), \
            "Vehicle name should be in the loaded template"

    def test_load_dashboard_template_returns_dict(self):
        """Test that _load_dashboard_template returns a valid dictionary."""
        import asyncio

        async def run_test():
            from custom_components.ev_trip_planner import _load_dashboard_template
            result = await _load_dashboard_template(
                "test_id",
                "Test Name",
                use_charts=False
            )
            return result

        result = asyncio.get_event_loop().run_until_complete(run_test())
        assert isinstance(result, dict), "Template should parse to a dictionary"

    def test_load_dashboard_template_has_views_list(self):
        """Test that loaded template has views as a list."""
        import asyncio

        async def run_test():
            from custom_components.ev_trip_planner import _load_dashboard_template
            result = await _load_dashboard_template(
                "test_id",
                "Test Name",
                use_charts=False
            )
            return result

        result = asyncio.get_event_loop().run_until_complete(run_test())
        assert "views" in result, "Dashboard should have views key"
        assert isinstance(result["views"], list), "Views should be a list"
        assert len(result["views"]) > 0, "Dashboard should have at least one view"

    def test_is_lovelace_available_with_lovelace_in_components(self):
        """Test is_lovelace_available returns True when lovelace is in components."""
        from unittest.mock import MagicMock
        from custom_components.ev_trip_planner import is_lovelace_available

        hass = MagicMock()
        hass.config.components = ["lovelace", "sensor"]

        assert is_lovelace_available(hass) is True

    def test_is_lovelace_available_without_lovelace(self):
        """Test is_lovelace_available returns False when lovelace is not available."""
        from unittest.mock import MagicMock
        from custom_components.ev_trip_planner import is_lovelace_available

        hass = MagicMock()
        hass.config.components = ["sensor", "automation"]
        hass.services.has_service = MagicMock(return_value=False)

        assert is_lovelace_available(hass) is False

    def test_is_lovelace_available_with_import_service(self):
        """Test is_lovelace_available returns True when import service exists."""
        from unittest.mock import MagicMock
        from custom_components.ev_trip_planner import is_lovelace_available

        hass = MagicMock()
        hass.config.components = []  # No lovelace in components
        hass.services.has_service = MagicMock(
            domain="lovelace", service="import", return_value=True
        )

        # Create a mock that returns True for the service check
        def has_service(domain, service):
            if domain == "lovelace" and service == "import":
                return True
            return False

        hass.services.has_service = has_service

        assert is_lovelace_available(hass) is True


class TestContainerEnvironment:
    """Tests for Home Assistant Container environment (P004).

    HA Container does not have:
    - hass.services.has_service("lovelace", "save") - service doesn't exist
    - hass.storage - Storage API not available

    This test should FAIL before the fix and PASS after the fix.
    """

    @pytest.fixture
    def mock_hass_container(self):
        """Create a mock HomeAssistant instance simulating Container environment.

        Container environment characteristics:
        - hass.services.has_service returns False for lovelace.save
        - hass.storage is not available (None or no async_write_dict)
        """
        from unittest.mock import MagicMock, AsyncMock

        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        hass.config.components = ["sensor"]  # No lovelace component

        # Container: NO storage API available
        hass.storage = None

        # Container: lovelace.save service does NOT exist
        def has_service(domain, service):
            if domain == "lovelace" and service == "save":
                return False
            return False

        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.services.has_service = has_service

        return hass

    @pytest.mark.asyncio
    async def test_container_environment_fallback(self, mock_hass_container):
        """Test that Container environment generates YAML file with instructions.

        In Container environment:
        - lovelace.save service is NOT available
        - hass.storage is NOT available
        - Should generate YAML file to config directory
        - Should return informative message for manual import
        """
        import sys
        sys.path.insert(
            0,
            str(Path(__file__).parent.parent / "custom_components")
        )

        from custom_components.ev_trip_planner import _save_lovelace_dashboard

        vehicle_id = "container_test_vehicle"

        # This test should FAIL before fix (returns False)
        # and PASS after fix (returns True or handles gracefully)
        result = await _save_lovelace_dashboard(
            mock_hass_container,
            {
                "title": "{{ vehicle_name }}",
                "views": [
                    {
                        "path": "{{ vehicle_id }}",
                        "title": "{{ vehicle_name }}",
                        "cards": [],
                    }
                ],
            },
            vehicle_id,
        )

        # Before fix: result will be False (storage not available)
        # After fix: result should be True (fallback implemented)
        assert result is True, (
            "Container environment should have fallback mechanism. "
            "Expected dashboard to be saved via YAML generation and "
            "manual import instructions."
        )


class TestDuplicateDashboardNameCollision:
    """Tests for duplicate dashboard name collision handling (P004).

    When importing a dashboard with a name that already exists,
    the system should append suffixes (-2-, -3-, etc.) to make it unique.
    """

    @pytest.fixture
    def mock_hass_container(self):
        """Create a mock HomeAssistant instance simulating Container environment."""
        from unittest.mock import MagicMock, AsyncMock

        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        hass.config.components = ["sensor"]  # No lovelace component

        # Container: NO storage API available
        hass.storage = None

        # Container: lovelace.save service does NOT exist
        def has_service(domain, service):
            if domain == "lovelace" and service == "save":
                return False
            return False

        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.services.has_service = has_service

        return hass

    @pytest.mark.asyncio
    async def test_duplicate_dashboard_name_appends_suffix(
        self, mock_hass_container, tmp_path
    ):
        """Test that duplicate dashboard names get -2- suffix.

        Test: Import dashboard when path already exists
        Expected: Should append suffix (-2-, -3-)
        """
        import sys

        sys.path.insert(
            0,
            str(Path(__file__).parent.parent / "custom_components")
        )

        from custom_components.ev_trip_planner import _save_dashboard_yaml_fallback

        # Create config directory
        config_dir = tmp_path / "test_config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create existing file to simulate collision
        existing_file = config_dir / "ev-trip-planner-vehicle1.yaml"
        existing_file.write_text("# existing dashboard")

        # Mock hass.config.config_dir
        mock_hass_container.config.config_dir = str(config_dir)

        dashboard_config = {
            "title": "Test Dashboard",
            "views": [
                {
                    "path": "vehicle1",
                    "title": "Vehicle 1",
                    "cards": [],
                }
            ],
        }

        # First import creates ev-trip-planner-vehicle1.yaml
        result1 = await _save_dashboard_yaml_fallback(
            mock_hass_container,
            dashboard_config,
            "vehicle1",
        )

        # Second import should create ev-trip-planner-vehicle1.yaml.2
        result2 = await _save_dashboard_yaml_fallback(
            mock_hass_container,
            dashboard_config,
            "vehicle1",
        )

        # Both should succeed
        assert result1 is True, "First import should succeed"
        assert result2 is True, "Second import should succeed with suffix"

        # Verify both files exist
        assert existing_file.exists(), "Original file should exist"
        assert (config_dir / "ev-trip-planner-vehicle1.yaml.2").exists(), \
            "Duplicate file with .2 suffix should be created"

    @pytest.mark.asyncio
    async def test_multiple_duplicate_dashboard_names_appends_progressive_suffixes(
        self, mock_hass_container, tmp_path
    ):
        """Test that multiple duplicate names get progressive suffixes (-2-, -3-, -4-).

        Test: Import dashboard with name collision multiple times
        Expected: Should append suffixes progressively
        """
        import sys

        sys.path.insert(
            0,
            str(Path(__file__).parent.parent / "custom_components")
        )

        from custom_components.ev_trip_planner import _save_dashboard_yaml_fallback

        # Create config directory
        config_dir = tmp_path / "test_config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Mock hass.config.config_dir
        mock_hass_container.config.config_dir = str(config_dir)

        dashboard_config = {
            "title": "Test Dashboard",
            "views": [
                {
                    "path": "vehicle1",
                    "title": "Vehicle 1",
                    "cards": [],
                }
            ],
        }

        # Import multiple times - should create .2, .3, .4, etc.
        results = []
        for i in range(5):
            result = await _save_dashboard_yaml_fallback(
                mock_hass_container,
                dashboard_config,
                "vehicle1",
            )
            results.append(result)

        # All imports should succeed
        assert all(results), f"All imports should succeed: {results}"

        # Verify all files exist with progressive suffixes
        assert (config_dir / "ev-trip-planner-vehicle1.yaml").exists()
        assert (config_dir / "ev-trip-planner-vehicle1.yaml.2").exists()
        assert (config_dir / "ev-trip-planner-vehicle1.yaml.3").exists()
        assert (config_dir / "ev-trip-planner-vehicle1.yaml.4").exists()
        assert (config_dir / "ev-trip-planner-vehicle1.yaml.5").exists()


class TestAllFailureModes:
    """Tests for all failure modes and robust error handling (T014c).

    This test class ensures NO partial failures - all error cases are handled
    gracefully and return appropriate error information.
    """

    @pytest.fixture
    def mock_hass_container(self):
        """Create a mock HomeAssistant instance simulating Container environment."""
        from unittest.mock import MagicMock, AsyncMock

        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        hass.config.components = ["sensor"]

        # Container: NO storage API available
        hass.storage = None

        # Container: lovelace.save service does NOT exist
        def has_service(domain, service):
            if domain == "lovelace" and service == "save":
                return False
            return False

        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.services.has_service = has_service

        return hass

    @pytest.mark.asyncio
    async def test_invalid_dashboard_config_rejected(self, mock_hass_container, tmp_path):
        """Test that invalid dashboard config (no views) is rejected gracefully.

        Expected: Returns False with error message, no partial file created.
        """
        import sys

        sys.path.insert(
            0,
            str(Path(__file__).parent.parent / "custom_components")
        )

        from custom_components.ev_trip_planner import _save_dashboard_yaml_fallback

        config_dir = tmp_path / "test_config"
        config_dir.mkdir(parents=True, exist_ok=True)

        mock_hass_container.config.config_dir = str(config_dir)

        # Invalid config: no views key
        invalid_config = {
            "title": "Test Dashboard",
            # Missing "views" key
        }

        result = await _save_dashboard_yaml_fallback(
            mock_hass_container,
            invalid_config,
            "test_vehicle",
        )

        # Should fail gracefully - no partial file created
        assert result is False, "Invalid config should return False"

        # No file should be created for invalid config
        expected_file = config_dir / "ev-trip-planner-test_vehicle.yaml"
        assert not expected_file.exists(), "No file should be created for invalid config"

    @pytest.mark.asyncio
    async def test_empty_dashboard_config_rejected(self, mock_hass_container, tmp_path):
        """Test that empty dashboard config is rejected gracefully.

        Expected: Returns False, no partial file created.
        """
        import sys

        sys.path.insert(
            0,
            str(Path(__file__).parent.parent / "custom_components")
        )

        from custom_components.ev_trip_planner import _save_dashboard_yaml_fallback

        config_dir = tmp_path / "test_config"
        config_dir.mkdir(parents=True, exist_ok=True)

        mock_hass_container.config.config_dir = str(config_dir)

        # Empty config
        empty_config = {}

        result = await _save_dashboard_yaml_fallback(
            mock_hass_container,
            empty_config,
            "test_vehicle",
        )

        assert result is False, "Empty config should return False"

        # No file should be created
        expected_file = config_dir / "ev-trip-planner-test_vehicle.yaml"
        assert not expected_file.exists(), "No file should be created for empty config"

    @pytest.mark.asyncio
    async def test_missing_title_fails_gracefully(self, mock_hass_container, tmp_path):
        """Test that dashboard without title is handled gracefully.

        Expected: Validation fails, no partial file created.
        """
        import sys

        sys.path.insert(
            0,
            str(Path(__file__).parent.parent / "custom_components")
        )

        from custom_components.ev_trip_planner import _save_dashboard_yaml_fallback

        config_dir = tmp_path / "test_config"
        config_dir.mkdir(parents=True, exist_ok=True)

        mock_hass_container.config.config_dir = str(config_dir)

        # Config without title
        no_title_config = {
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
            no_title_config,
            "test_vehicle",
        )

        assert result is False, "Config without title should return False"

    @pytest.mark.asyncio
    async def test_empty_views_list_rejected(self, mock_hass_container, tmp_path):
        """Test that dashboard with empty views list is rejected.

        Expected: Returns False, no partial file created.
        """
        import sys

        sys.path.insert(
            0,
            str(Path(__file__).parent.parent / "custom_components")
        )

        from custom_components.ev_trip_planner import _save_dashboard_yaml_fallback

        config_dir = tmp_path / "test_config"
        config_dir.mkdir(parents=True, exist_ok=True)

        mock_hass_container.config.config_dir = str(config_dir)

        # Config with empty views list
        empty_views_config = {
            "title": "Test Dashboard",
            "views": [],  # Empty views list
        }

        result = await _save_dashboard_yaml_fallback(
            mock_hass_container,
            empty_views_config,
            "test_vehicle",
        )

        assert result is False, "Empty views should return False"

    @pytest.mark.asyncio
    async def test_no_partial_failure_on_all_errors(self, mock_hass_container, tmp_path):
        """Test that NO partial failures occur - all errors handled cleanly.

        This is the core robustness test: verify that when errors occur,
        no partially-written files are left behind.
        """
        import sys

        sys.path.insert(
            0,
            str(Path(__file__).parent.parent / "custom_components")
        )

        from custom_components.ev_trip_planner import _save_dashboard_yaml_fallback

        config_dir = tmp_path / "test_config"
        config_dir.mkdir(parents=True, exist_ok=True)

        mock_hass_container.config.config_dir = str(config_dir)

        # Get initial file count
        initial_files = list(config_dir.glob("*.yaml"))

        # Attempt to save with various invalid configs
        invalid_configs = [
            {},  # Empty
            {"views": []},  # Empty views
            {"title": "No views"},  # Missing views
            {"views": [{}]},  # Empty view
            {"views": [{"path": "test"}]},  # Missing required view keys
        ]

        for config in invalid_configs:
            result = await _save_dashboard_yaml_fallback(
                mock_hass_container,
                config,
                "test_vehicle",
            )
            assert result is False, f"Invalid config should return False: {config}"

        # Final file count should still be initial (no partial files)
        final_files = list(config_dir.glob("*.yaml"))
        assert len(initial_files) == len(final_files), (
            "No partial files should be created when errors occur"
        )

    @pytest.mark.asyncio
    async def test_valid_config_succeeds(self, mock_hass_container, tmp_path):
        """Test that valid dashboard config is saved successfully.

        Expected: Returns True, file created.
        """
        import sys

        sys.path.insert(
            0,
            str(Path(__file__).parent.parent / "custom_components")
        )

        from custom_components.ev_trip_planner import _save_dashboard_yaml_fallback

        config_dir = tmp_path / "test_config"
        config_dir.mkdir(parents=True, exist_ok=True)

        mock_hass_container.config.config_dir = str(config_dir)

        # Valid config
        valid_config = {
            "title": "Test Dashboard",
            "views": [
                {
                    "path": "test-view",
                    "title": "Test View",
                    "cards": [
                        {
                            "type": "markdown",
                            "content": "Test content",
                        }
                    ],
                }
            ],
        }

        result = await _save_dashboard_yaml_fallback(
            mock_hass_container,
            valid_config,
            "test_vehicle",
        )

        assert result is True, "Valid config should return True"

        # File should be created
        expected_file = config_dir / "ev-trip-planner-test_vehicle.yaml"
        assert expected_file.exists(), "File should be created for valid config"

        # File should be valid YAML
        import yaml
        with open(expected_file, "r") as f:
            saved_config = yaml.safe_load(f)

        assert saved_config is not None, "Saved config should be valid YAML"
        assert saved_config.get("title") == "Test Dashboard"
