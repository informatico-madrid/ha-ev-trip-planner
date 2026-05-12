"""Unit test fixtures — mocks that don't need HA framework."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def trip_manager_no_entry_id(mock_hass):
    """Return a TripManager instance WITHOUT entry_id for pure function tests.

    This fixture provides a TripManager without entry_id for tests that don't
    depend on coordinator refresh or config entry lookup.

    Usage:
        async def test_calculation(trip_manager_no_entry_id):
            tm = trip_manager_no_entry_id
            result = await tm.async_get_kwh_needed_today()
    """
    return TripManager(mock_hass, "test_vehicle")


# ---------------------------------------------------------------------------
# Dashboard test fixtures (moved from inline class fixtures in test_dashboard.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance for dashboard import tests.

    This fixture provides a full mock with lovelace support, storage, services,
    and async_add_executor_job. Used by TestDashboardImport tests.
    """

    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.components = ["lovelace"]

    # Mock storage
    hass.storage = MagicMock()
    hass.storage.async_read = AsyncMock(
        return_value={"data": {"config": {"views": []}}}
    )
    hass.storage.async_write_dict = AsyncMock(return_value=True)

    # Mock services
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    # Mock async_add_executor_job for non-blocking I/O
    async def mock_executor_job(func, *args):
        """Mock executor job that runs function synchronously."""
        return func(*args)

    hass.async_add_executor_job = mock_executor_job

    return hass


@pytest.fixture
def mock_hass_container():
    """Create a mock HomeAssistant instance simulating Container environment.

    Container environment characteristics:
    - hass.services.has_service returns False for lovelace.save
    - hass.storage is not available (None or no async_write_dict)
    """
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


@pytest.fixture
def mock_hass_with_storage():
    """Create a mock HomeAssistant with storage support.

    Provides storage with async_read_dict and async_write_dict.
    Used by trip_manager tests in TestDashboardDataSync.
    """
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"

    # Mock storage API
    hass.storage = MagicMock()
    hass.storage.async_read_dict = AsyncMock(return_value={})
    hass.storage.async_write_dict = AsyncMock()

    return hass


@pytest.fixture
def mock_hass_with_vehicle(tmp_path):
    """Create a mock HA instance with a vehicle configured.

    Provides lovelace+sensor components, storage with pre-existing views,
    and services. Config dir is backed by tmp_path.
    """
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = str(tmp_path / "config")
    hass.config.components = ["lovelace", "sensor"]

    # Create config directory
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Mock storage API (Supervisor environment)
    hass.storage = MagicMock()
    hass.storage.async_read = AsyncMock(
        return_value={
            "data": {
                "views": [
                    {"path": "existing-dashboard", "title": "Existing", "cards": []}
                ]
            }
        }
    )
    hass.storage.async_write_dict = AsyncMock(return_value=True)

    # Mock services
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    return hass


@pytest.fixture
def mock_hass_with_notification():
    """Create a mock HomeAssistant with notification service.

    Provides storage, services with notification support, and states mock
    for sensor operations. Used by TestEMHASSErrorNotifications tests.
    """
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"

    # Mock storage API
    hass.storage = MagicMock()
    hass.storage.async_read_dict = AsyncMock(return_value={})
    hass.storage.async_write_dict = AsyncMock()

    # Mock services with notification service
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    # Mock states for sensor
    hass.states = MagicMock()
    hass.states.async_set = MagicMock()
    hass.states.get = MagicMock(return_value=None)

    return hass


@pytest.fixture
def trip_manager(mock_hass_with_storage):
    """Create a TripManager instance for dashboard tests.

    Depends on mock_hass_with_storage which is provided by the conftest fixture.
    Used by TestCRUDOperationsViaDashboard and TestDashboardDataSync tests.
    """
    manager = TripManager(mock_hass_with_storage, "test_vehicle")
    return manager


# ============================================================================
# test_charging_window.py - mock_hass with config_entries + storage
# ============================================================================


@pytest.fixture
def mock_hass_charging_window():
    hass = MagicMock()
    hass.data = {}

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_001"
    mock_entry.data = {
        "vehicle_name": "tesla_model_3",
        "battery_capacity": 75.0,
        "consumption": 0.15,
        "charging_power": 11.0,
    }
    mock_entry.runtime_data = MagicMock()

    def _async_entries(domain=None):
        return [mock_entry]

    def _async_get_entry(entry_id):
        if entry_id == "test_entry_001":
            return mock_entry
        return None

    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = _async_entries
    hass.config_entries.async_get_entry = _async_get_entry

    hass.storage = MagicMock()
    hass.storage.async_read = AsyncMock(return_value=None)
    hass.storage.async_write_dict = AsyncMock()

    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    return hass


# ============================================================================
# test_deferrable_load_sensors.py - mock_hass with config_entries
# ============================================================================


@pytest.fixture
def mock_hass_deferrable():
    hass = Mock()
    hass.data = {}

    mock_entry = Mock()
    mock_entry.data = {
        "vehicle_name": "test_vehicle",
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "planning_horizon_days": 7,
    }
    mock_entry.entry_id = "test_entry_id"

    hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

    def _async_entries(domain=None):
        return [mock_entry]

    hass.config_entries.async_entries = _async_entries

    return hass


# ============================================================================
# test_entity_registry.py - mock_hass with entity registry
# ============================================================================


@pytest.fixture
def mock_hass_entity_registry(config_entry):
    from custom_components.ev_trip_planner.const import DOMAIN

    hass = MagicMock()

    class MockRegistry:
        def __init__(self, hass_mock):
            self.hass_mock = hass_mock
            self.entries = {}
            self.entities = self

        def async_get(self, hass_instance=None):
            return self

        def async_get_or_create(self, *args, **kwargs):
            suggested_object_id = kwargs.get("suggested_object_id", "unknown")
            unique_id = kwargs.get("unique_id", "")
            entity_id = f"sensor.{suggested_object_id}"
            entry = _MockRegistryEntry(entity_id, unique_id, config_entry.entry_id)
            self.entries[entity_id] = entry
            return entry

        def async_entries_for_config_entry(self, entry_id):
            return [e for e in self.entries.values() if e.config_entry_id == entry_id]

        def async_remove(self, entity_id):
            return True

    hass.data = {DOMAIN: {}}
    hass.data[DOMAIN]["entity_registry"] = MockRegistry(hass)

    return hass


class _MockRegistryEntry:
    def __init__(self, entity_id, unique_id, config_entry_id):
        self.entity_id = entity_id
        self.unique_id = unique_id
        self.config_entry_id = config_entry_id


@pytest.fixture
def mock_hass_entity_registry_full(config_entry):
    """Create a full mock HomeAssistant with entity registry, trip_manager, coordinator.

    This is the comprehensive fixture that replaces inline mock_hass fixtures
    in test_entity_registry.py. Provides full HA mock with entity registry,
    trip_manager, coordinator, and config_entries setup.
    """
    from custom_components.ev_trip_planner.const import DOMAIN

    hass = MagicMock()

    class MockRegistry:
        """Mock entity registry that tracks entities."""

        def __init__(self, hass_mock):
            self.hass_mock = hass_mock
            self.entries = {}
            self.entities = self

        def async_get(self, hass_instance=None):
            return self

        def async_get_or_create(self, *args, **kwargs):
            suggested_object_id = kwargs.get("suggested_object_id", "unknown")
            unique_id = kwargs.get("unique_id", "")
            entity_id = f"sensor.{suggested_object_id}"
            entry = _MockRegistryEntry(entity_id, unique_id, config_entry.entry_id)
            self.entries[entity_id] = entry
            return entry

        def async_entries_for_config_entry(self, entry_id):
            return [e for e in self.entries.values() if e.config_entry_id == entry_id]

        def get_entries_for_config_entry_id(self, entry_id):
            return [e for e in self.entries.values() if e.config_entry_id == entry_id]

        def async_remove(self, entity_id):
            if entity_id in self.entries:
                del self.entries[entity_id]

    mock_registry = MockRegistry(hass)
    hass.entity_registry = mock_registry

    tm = MagicMock()
    # New composition architecture: CRUD methods are on _crud sub-object
    tm._crud = MagicMock()
    tm._crud.async_get_recurring_trips = AsyncMock(return_value=[])
    tm._crud.async_get_punctual_trips = AsyncMock(return_value=[])
    # Lifecycle methods are on _lifecycle sub-object
    tm._lifecycle = MagicMock()
    tm._lifecycle.async_delete_all_trips = AsyncMock()
    tm._recurring_trips = []
    tm._punctual_trips = []

    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.trip_manager = tm
    coordinator.async_config_entry_first_refresh = AsyncMock()

    namespace = f"{DOMAIN}_{config_entry.entry_id}"
    hass.data = {
        f"{DOMAIN}_runtime_data": {
            namespace: {
                "trip_manager": tm,
                "coordinator": coordinator,
                "config": config_entry.data,
            }
        }
    }

    config_entry.runtime_data.trip_manager = tm
    config_entry.runtime_data.coordinator = coordinator

    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_entries = MagicMock(return_value=[config_entry])
    hass.config_entries.async_get_entry = MagicMock(return_value=config_entry)

    return hass


# ============================================================================
# test_full_user_journey.py - mock_hass with config_entries + storage
# ============================================================================


@pytest.fixture
def mock_hass_full_journey():
    """Mock hass for full user journey tests.

    Provides config_entries, storage, loop, and services registry for service
    registration/verification tests.
    """
    hass = MagicMock()

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_001"
    mock_entry.unique_id = "test_entry_001"
    mock_entry.data = {
        "vehicle_name": "tesla_model_3",
        "battery_capacity_kwh": 75.0,
        "consumption_kwh_per_km": 0.15,
        "charging_power_kw": 11.0,
    }
    mock_entry.runtime_data = MagicMock()
    mock_entry.runtime_data.trip_manager = None
    mock_entry.runtime_data.coordinator = MagicMock()
    mock_entry.runtime_data.coordinator.async_refresh_trips = AsyncMock()

    def _async_entries(domain=None):
        return [mock_entry]

    def _async_get_entry(entry_id):
        if entry_id in ("test_entry_001", "test_vehicle"):
            return mock_entry
        return None

    hass.config_entries.async_entries = _async_entries
    hass.config_entries.async_get_entry = _async_get_entry

    mock_loop = MagicMock()
    mock_loop.create_future = MagicMock(return_value=None)
    hass.loop = mock_loop

    hass.storage = MagicMock()
    hass.storage.async_read = AsyncMock(return_value=None)
    hass.storage.async_write_dict = AsyncMock(return_value=True)

    hass.config.config_dir = "/tmp/test_config"

    # Services registry for register_services
    services_registry = {}

    class MockServiceCall:
        def __init__(self, domain, service, data, blocking, return_response):
            self.domain = domain
            self.service = service
            self.data = data
            self.blocking = blocking
            self.return_response = return_response

    class Services:
        def async_register(
            self, domain, name, handler, schema=None, supports_response=None
        ):
            if domain == "ev_trip_planner":
                services_registry[name] = handler

        async def async_call(
            self, domain, service, data=None, blocking=True, return_response=False
        ):
            if domain == "ev_trip_planner" and service in services_registry:
                call = MockServiceCall(domain, service, data, blocking, return_response)
                return await services_registry[service](call)
            return None

        def async_services(self):
            return {"ev_trip_planner": list(services_registry.keys())}

    hass.services = Services()

    return hass


# ============================================================================
# test_panel.py - panel-specific mock fixtures
# ============================================================================


@pytest.fixture
def mock_hass_panel():
    """Create a mock HA instance for panel tests.

    Provides a simple MagicMock with data=dict and panel_custom in components.
    Used by TestAsyncRegisterPanel tests in test_panel.py.
    """
    hass = MagicMock()
    hass.data = {}
    hass.config.components = {"panel_custom"}
    return hass


@pytest.fixture
def mock_hass_panel_with_mapping(mock_frontend_module):
    from custom_components.ev_trip_planner.const import DOMAIN

    hass = MagicMock()
    mapping_key = f"{DOMAIN}_vehicle_panel_mapping"
    hass.data = {
        mapping_key: {
            "test_vehicle": "ev-trip-planner-test_vehicle",
        }
    }
    return hass


# ============================================================================
# test_propagate_charge_integration.py - mock_hass with config + config_dir + services
# ============================================================================


@pytest.fixture
def mock_hass_propagate():
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    return hass


# ============================================================================
# test_sensor_aggregation.py - mock_hass with config + config_dir + services
# ============================================================================


@pytest.fixture
def mock_hass_sensor_agg():
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    return hass


# ============================================================================
# test_sensor_exists_fn.py - mock_hass with states.async_set
# ============================================================================


@pytest.fixture
def mock_hass_sensor_exists():
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    hass.states.async_set = MagicMock()
    return hass


# ============================================================================
# test_soc_cap_aggregation_ceil.py - mock_hass with config + config_dir + services
# ============================================================================


@pytest.fixture
def mock_hass_soc_cap():
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    hass.states.async_set = MagicMock()
    return hass


# ============================================================================
# test_soc_milestone.py - mock_hass with config_entries + config_dir
# ============================================================================


@pytest.fixture
def mock_hass_soc_milestone():
    hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    hass.config.config_dir = "/tmp/test_config"
    return hass


# ============================================================================
# test_trip_crud.py - mock_hass_storage and mock_hass_no_storage
# ============================================================================


@pytest.fixture
def mock_hass_storage():
    """Mock hass with storage (Supervisor environment)."""
    hass = MagicMock()

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_config_entry_123"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    hass.storage = MagicMock()
    hass.storage.async_read = MagicMock(return_value=None)
    hass.storage.async_write_dict = MagicMock()

    hass.config.config_dir = "/tmp/test_config"

    return hass


@pytest.fixture
def mock_hass_no_storage():
    """Mock hass WITHOUT storage (Container environment)."""
    hass = MagicMock()

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_config_entry_123"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    hass.storage = None
    hass.config.config_dir = "/tmp/test_config_no_storage"

    return hass


# ============================================================================
# test_trip_manager_core.py (unit) - mock_hass, mock_hass_no_storage, mock_hass_with_storage
# ============================================================================


@pytest.fixture
def mock_hass_no_storage_tm():
    """Mock hass WITH storage for testing.

    The production code requires hass.storage to use HA Store API.
    """
    hass = MagicMock()

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    mock_loop = MagicMock()
    mock_loop.create_future = MagicMock(return_value=None)
    hass.loop = mock_loop

    hass.storage = MagicMock()
    hass.storage.async_read = AsyncMock(return_value=None)
    hass.storage.async_write_dict = AsyncMock(return_value=True)

    return hass


@pytest.fixture
def mock_hass_no_entry_tm():
    """Mock hass WITHOUT storage (Container environment)."""
    hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    hass.config.config_dir = "/tmp/test_config"
    return hass


@pytest.fixture
def mock_hass_with_storage_tm():
    """Mock hass with storage for testing error paths."""
    hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    mock_loop = MagicMock()
    mock_loop.create_future = MagicMock(return_value=None)
    hass.loop = mock_loop

    hass.storage = MagicMock()
    hass.storage.async_read = AsyncMock(return_value=None)
    hass.storage.async_write_dict = AsyncMock(return_value=True)

    return hass


# ============================================================================
# test_trip_manager_emhass_sensors.py - mock_hass + mock_hass_with_charging_power
# ============================================================================


@pytest.fixture
def mock_hass_emhass():
    hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_vehicle"
    mock_entry.data = {}
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    hass.data = {}
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    return hass


@pytest.fixture
def mock_hass_emhass_charging(mock_hass_emhass):
    """Mock hass with charging power configured."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_vehicle"
    mock_entry.data = {"charging_power": 11.0}
    mock_hass_emhass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    return mock_hass_emhass


# Alias for test_trip_manager_emhass_sensors which uses this name
@pytest.fixture
def mock_hass_with_charging_power(mock_hass_emhass_charging):
    """Alias for mock_hass_emhass_charging."""
    return mock_hass_emhass_charging


# ============================================================================
# test_yaml_trip_storage.py - class-level mock_hass (simple)
# ============================================================================


@pytest.fixture
def mock_hass_yaml():
    """Mock hass with config for yaml trip storage tests."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = Path("/tmp/test_config")
    return hass


# ============================================================================
# test_panel.py - mock_panel_module and mock_frontend_module fixtures
# ============================================================================


@pytest.fixture
def mock_panel_module():
    """Create a mock panel_custom module."""
    from unittest.mock import AsyncMock

    with patch("custom_components.ev_trip_planner.panel.panel_custom") as mock:
        mock.async_register_panel = AsyncMock()
        yield mock


@pytest.fixture
def mock_frontend_module():
    """Create a mock frontend module."""
    from unittest.mock import AsyncMock

    with patch("custom_components.ev_trip_planner.panel.frontend") as mock:
        mock.async_register_built_in_panel = AsyncMock()
        mock.async_remove_panel = AsyncMock()
        yield mock


# ============================================================================
# test_entity_registry.py - FakeEntry and config_entry fixtures
# ============================================================================


class FakeConfigEntry:
    """Minimal ConfigEntry substitute for testing."""

    def __init__(self, entry_id="test_entry_001", data=None):
        self.entry_id = entry_id
        self.data = data or {}
        self.version = 1
        self.minor_version = 1

        class FakeRuntimeData:
            def __init__(self):
                self.trip_manager = None
                self.coordinator = None
                self.sensor_async_add_entities = None

        self.runtime_data = FakeRuntimeData()

    @property
    def unique_id(self):
        return self.entry_id


@pytest.fixture
def config_entry():
    """Create a test ConfigEntry."""
    return FakeConfigEntry(
        entry_id="test_entry_001",
        data={"vehicle_name": "Chispitas"},
    )


# --- Shared datetime fixture ---


def _make_mock_datetime_fixture(default_dt: datetime):
    """Factory that creates a fixture with a hardcoded default datetime."""

    @pytest.fixture
    def mock_dt_fixture(request):
        """Mock datetime.now(timezone.utc) for deterministic deadline calculations."""
        if hasattr(request, "param") and request.param is not None:
            fixed_now = request.param
        else:
            fixed_now = default_dt

        real_datetime = datetime

        class MockDatetime(real_datetime):
            """Subclass of datetime that overrides .now() to return a fixed value."""

            @classmethod
            def now(cls, tz=None):
                return fixed_now.replace(tzinfo=tz or timezone.utc)

        with (
            patch(
                "custom_components.ev_trip_planner.emhass.adapter.datetime",
                MockDatetime,
            ),
            patch(
                "custom_components.ev_trip_planner.calculations.datetime", MockDatetime
            ),
            patch("homeassistant.util.dt.utcnow", return_value=fixed_now),
            patch("homeassistant.util.dt.now", return_value=fixed_now),
        ):
            yield fixed_now

    return mock_dt_fixture


mock_datetime_2026_05_04_monday_0800_utc = _make_mock_datetime_fixture(
    datetime(2026, 5, 4, 8, 0, 0, tzinfo=timezone.utc)
)


# --- TripManager fixtures (for unit tests only) ---


@pytest.fixture
def trip_manager_with_entry_id(mock_hass, mock_store):
    """Return a TripManager instance with entry_id for EMHASS-dependent tests."""
    from custom_components.ev_trip_planner.trip_manager import TripManager

    return TripManager(
        mock_hass, "test_vehicle", entry_id="test_entry_123", storage=mock_store
    )


@pytest.fixture
def sample_notification_config():
    """Return a sample notification configuration for testing."""
    return {
        "notification_service": "notify.mobile_app",
        "notification_devices": ["device_123"],
    }
