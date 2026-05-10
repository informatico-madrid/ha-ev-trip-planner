"""Integration test fixtures — HA framework fixtures."""

from __future__ import annotations

import asyncio
import inspect
import logging
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from homeassistant.core import CoreState

from custom_components.ev_trip_planner.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def enable_custom_integrations():
    """Enable custom integrations for testing.

    This fixture allows Home Assistant to load custom integrations during tests.
    Required per project coding guidelines for integration tests.
    """
    return True


@pytest.fixture
def hass():
    """
    Fixture to provide a working HomeAssistant instance for tests.

    This creates a minimal mock hass instance that avoids compatibility issues
    with pytest-homeassistant-custom-component.
    """
    hass_inst = MagicMock()

    hass_inst.config = MagicMock()
    hass_inst.config.config_dir = "/tmp/test_config"
    hass_inst.config.time_zone = "UTC"
    hass_inst.config.latitude = 40.0
    hass_inst.config.longitude = -3.0
    hass_inst.config.elevation = 0

    hass_inst.states = MagicMock()
    hass_inst._states_dict = {}

    def _mock_states_get(entity_id):
        result = hass_inst._states_dict.get(entity_id, None)
        return result

    def _mock_states_set(entity_id, state, attributes=None):
        state_obj = MagicMock()
        state_obj.state = state
        state_obj.attributes = attributes or {}
        hass_inst._states_dict[entity_id] = state_obj
        return True

    def _mock_states_async_set(entity_id, state, attributes=None):
        _mock_states_set(entity_id, state, attributes)
        return True

    def _mock_states_async_remove(entity_id):
        hass_inst._states_dict.pop(entity_id, None)
        return True

    hass_inst.states.get = _mock_states_get
    hass_inst.states.set = _mock_states_set
    hass_inst.states.async_set = _mock_states_async_set
    hass_inst.states.async_remove = _mock_states_async_remove

    hass_inst.services = MagicMock()
    hass_inst.services.async_call = AsyncMock()
    hass_inst.services.has_service = MagicMock(return_value=True)

    def _mock_async_run_hass_job(job, *args, **kwargs):
        if job is None:
            return None

        job_target = None
        job_args = args or ()
        job_kwargs = kwargs or {}

        if hasattr(job, "target"):
            job_target = job.target
            if hasattr(job, "args"):
                job_args = job.args or ()
            if hasattr(job, "kwargs"):
                job_kwargs = job.kwargs or {}
        else:
            job_target = job

        if job_target is None:
            return None

        sig = inspect.signature(job_target)
        valid_params = set(sig.parameters.keys())
        filtered_kwargs = {k: v for k, v in job_kwargs.items() if k in valid_params}

        try:
            if asyncio.iscoroutinefunction(job_target):
                coro = job_target(*job_args, **filtered_kwargs)
                if asyncio.iscoroutine(coro):
                    return coro
                return asyncio.ensure_future(coro)
            else:
                async def _wrapper():
                    return job_target(*job_args, **filtered_kwargs)

                return asyncio.ensure_future(_wrapper())
        except Exception as e:
            _LOGGER.error("Error in mock_async_run_hass_job: %s", e, exc_info=True)
            raise

    hass_inst.async_run_hass_job = _mock_async_run_hass_job

    yield hass_inst


# FIX: Mock frame reporting for HA 2026.3+ compatibility
# DataUpdateCoordinator in HA 2026.3+ requires frame helper to be set up
# This autouse fixture mocks the frame.report_usage to bypass the check
@pytest.fixture(autouse=True)
def mock_frame_reporting():
    """Mock frame reporting to avoid 'Frame helper not set up' error."""
    with patch("homeassistant.helpers.frame.report_usage", return_value=None):
        yield


@pytest.fixture
def mock_input_text_entity():
    """Return a mocked input_text entity with empty trips."""
    state = MagicMock()
    state.state = "[]"
    return state


@pytest.fixture
def mock_input_text_entity_with_trips():
    """Return a mocked input_text entity with sample trips."""
    state = MagicMock()
    state.state = """[
        {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24,
            "kwh": 3.6,
            "descripcion": "Trabajo",
            "activo": true,
            "creado": "2025-11-18T10:00:00"
        },
        {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "km": 110,
            "kwh": 16.5,
            "descripcion": "Viaje a Toledo",
            "estado": "pendiente",
            "creado": "2025-11-18T10:30:00"
        }
    ]"""
    return state


# ============================================================================
# Config Flow Testing Fixtures
# ============================================================================


@pytest.fixture
def mock_entity_registry():
    """Return a mock entity registry for entity selection in config flow."""
    from unittest.mock import MagicMock

    registry = MagicMock()
    registry._entities = {}

    def _get_entity(entity_id):
        """Get entity from registry."""
        return registry._entities.get(entity_id)

    def _entities_for_domain(domain):
        """Get all entities for a specific domain."""
        return [
            entity
            for entity_id, entity in registry._entities.items()
            if entity_id.startswith(f"{domain}.")
        ]

    def _async_get_entity(entity_id):
        """Async get entity from registry."""
        return _get_entity(entity_id)

    registry.get = _get_entity
    registry.entities_for_domain = _entities_for_domain
    registry.async_get = _async_get_entity

    default_entities = {
        "sensor.ovms_soc": MagicMock(
            entity_id="sensor.ovms_soc",
            domain="sensor",
            original_name="OVMS SOC",
            capabilities={"state_class": "measurement", "unit_of_measurement": "%"},
        ),
        "sensor.ovms_consumption": MagicMock(
            entity_id="sensor.ovms_consumption",
            domain="sensor",
            original_name="OVMS Consumption",
            capabilities={
                "state_class": "measurement",
                "unit_of_measurement": "kWh/100km",
            },
        ),
        "binary_sensor.home_presence": MagicMock(
            entity_id="binary_sensor.home_presence",
            domain="binary_sensor",
            original_name="Home Presence",
            capabilities={"device_class": "presence"},
        ),
        "binary_sensor.vehicle_plugged": MagicMock(
            entity_id="binary_sensor.vehicle_plugged",
            domain="binary_sensor",
            original_name="Vehicle Plugged",
            capabilities={"device_class": "plug"},
        ),
        "binary_sensor.charging_status": MagicMock(
            entity_id="binary_sensor.charging_status",
            domain="binary_sensor",
            original_name="Charging Status",
            capabilities={"device_class": "battery_charging"},
        ),
        "switch.ev_charger": MagicMock(
            entity_id="switch.ev_charger",
            domain="switch",
            original_name="EV Charger",
            capabilities=None,
        ),
    }

    for entity_id, entity in default_entities.items():
        registry._entities[entity_id] = entity

    yield registry


@pytest.fixture
def mock_device_registry():
    """Return a mock device registry for device selection in config flow."""
    from unittest.mock import MagicMock

    registry = MagicMock()
    registry._devices = {}

    def _get_device(device_id):
        """Get device from registry."""
        return registry._devices.get(device_id)

    def _devices_for_config_entry(config_entry_id):
        """Get all devices for a specific config entry."""
        return [
            device
            for device in registry._devices.values()
            if config_entry_id in device.config_entries
        ]

    def _async_get_device(device_id):
        """Async get device from registry."""
        return _get_device(device_id)

    registry.get = _get_device
    registry.devices_for_config_entry = _devices_for_config_entry
    registry.async_get = _async_get_device

    default_device = MagicMock(
        device_id="device_123",
        name="Test Vehicle",
        config_entries={"config_entry_123"},
        manufacturer="Tesla",
        model="Model 3",
    )
    registry._devices["device_123"] = default_device

    yield registry


@pytest.fixture
def mock_config_entries():
    """Return a mock config entries manager."""
    from unittest.mock import MagicMock

    entries_manager = MagicMock()
    entries_manager._entries = {}

    def _get_entry(entry_id):
        """Get config entry by ID."""
        return entries_manager._entries.get(entry_id)

    def _async_entries():
        """Get all config entries."""
        return list(entries_manager._entries.values())

    entries_manager.get_entry = _get_entry
    entries_manager.async_entries = _async_entries

    default_entry = MagicMock()
    default_entry.entry_id = "config_entry_123"
    default_entry.data = {
        "vehicle_name": "test_vehicle",
        "soc_sensor": "sensor.ovms_soc",
        "battery_capacity_kwh": 60.0,
        "charging_power_kw": 11.0,
        "kwh_per_km": 0.15,
        "safety_margin_percent": 10,
    }
    default_entry.options = {}
    entries_manager._entries["config_entry_123"] = default_entry

    yield entries_manager


@pytest.fixture
def mock_flow_manager():
    """Return a mock flow manager for config flow testing."""
    from unittest.mock import MagicMock

    flow_manager = MagicMock()
    flow_manager._flow_init = False

    async def _async_init():
        flow_manager._flow_init = True

    flow_manager.async_init = _async_init

    yield flow_manager


@pytest.fixture
def mock_er_async_get(mock_entity_registry):
    """Patch er.async_get to return mock_entity_registry."""
    from unittest.mock import patch

    from homeassistant.helpers import entity_registry as er

    with patch.object(er, "async_get", return_value=mock_entity_registry):
        yield mock_entity_registry


@pytest.fixture
def mock_hass_with_entity_registry(
    hass, mock_entity_registry, mock_device_registry, mock_config_entries
):
    """Return a mock hass instance with entity and device registries."""
    hass.data = {"entity_registry": mock_entity_registry}
    hass.data["device_registry"] = mock_device_registry
    hass.data["config_entries"] = mock_config_entries

    hass._states_dict = {
        "sensor.ovms_soc": MagicMock(
            state="75",
            attributes={"unit_of_measurement": "%", "device_class": "battery"},
        ),
        "sensor.ovms_consumption": MagicMock(
            state="15.0",
            attributes={"unit_of_measurement": "kWh/100km"},
        ),
        "binary_sensor.home_presence": MagicMock(
            state="on",
            attributes={"device_class": "presence"},
        ),
        "binary_sensor.vehicle_plugged": MagicMock(
            state="on",
            attributes={"device_class": "plug"},
        ),
        "binary_sensor.charging_status": MagicMock(
            state="on",
            attributes={"device_class": "battery_charging"},
        ),
        "switch.ev_charger": MagicMock(
            state="off",
            attributes={},
        ),
    }

    def _mock_states_get(entity_id):
        result = hass._states_dict.get(entity_id, None)
        return result

    hass.states.get = _mock_states_get

    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    def _mock_has_service(domain, service):
        if domain == "notify":
            return service in [
                "notify.mobile_app",
                "notify.persistent_notification",
                "notify.alexa_media",
                "notify.alexa_media_living_room",
                "notify.alexa_media_bedroom",
                "notify.google_assistant",
                "notify.telegram",
            ]
        return True

    hass.services.has_service = _mock_has_service

    def _mock_async_services():
        return {
            "notify": {
                "mobile_app": MagicMock(),
                "persistent_notification": MagicMock(),
                "alexa_media": MagicMock(),
                "alexa_media_living_room": MagicMock(),
                "alexa_media_bedroom": MagicMock(),
                "google_assistant": MagicMock(),
                "telegram": MagicMock(),
            }
        }

    hass.services.async_services = MagicMock(return_value=_mock_async_services())

    return hass


@pytest.fixture
def mock_store_class():
    """Fixture to patch the Store class for testing."""
    from unittest.mock import patch

    from homeassistant.helpers import storage as ha_storage

    class MockStore:
        def __init__(self, hass, version, key, *, private=None):
            self.hass = hass
            self.version = version
            self.key = key
            self._storage = {}

        async def async_load(self):
            return self._storage.get("data")

        async def async_save(self, data):
            self._storage["data"] = data
            return True

    with patch.object(ha_storage, "Store", MockStore):
        yield MockStore


# ============================================================================
# Services Core — mock_hass helper and fixtures
# ============================================================================


class _ServicesRegistry:
    """Minimal services registry for mock hass in test_services_core tests."""

    def __init__(self):
        self.registry = {}

    def async_register(
        self, domain, name, handler, schema=None, supports_response=None
    ):
        if domain == DOMAIN:
            self.registry[name] = handler


def _build_services_hass(manager_config=None):
    """Build a mock hass with Services registry and a config entry.

    Args:
        manager_config: dict mapping method names to config dicts with
            "return_value" or "side_effect" keys.
    """
    from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

    hass = MagicMock()
    hass.data = {}
    hass.services = _ServicesRegistry()
    hass.config_entries = MagicMock()

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_test"
    mock_entry.data = {"vehicle_name": "test_vehicle"}
    mock_coordinator = MagicMock()
    mock_coordinator.async_refresh_trips = AsyncMock()

    mock_manager = MagicMock()
    if manager_config:
        for method_name, cfg in manager_config.items():
            if "return_value" in cfg:
                setattr(mock_manager, method_name, AsyncMock(return_value=cfg["return_value"]))
            if "side_effect" in cfg:
                setattr(mock_manager, method_name, AsyncMock(side_effect=cfg["side_effect"]))
    mock_entry.runtime_data = EVTripRuntimeData(
        coordinator=mock_coordinator,
        trip_manager=mock_manager,
    )
    mock_entry.runtime_data.trip_manager = mock_manager

    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    return hass


@pytest.fixture
def mock_hass_get_error():
    """Manager raises RuntimeError on async_get_recurring_trips."""
    return _build_services_hass({
        "async_get_recurring_trips": {"side_effect": RuntimeError("Storage error")},
        "async_get_punctual_trips": {"return_value": []},
    })


@pytest.fixture
def mock_hass_list_error():
    """Manager raises on both get methods."""
    return _build_services_hass({
        "async_get_recurring_trips": {"side_effect": RuntimeError("Storage corrupted")},
        "async_get_punctual_trips": {"side_effect": RuntimeError("Storage corrupted")},
    })


@pytest.fixture
def mock_hass_invalid_type():
    """Manager configured for invalid trip_type test."""
    return _build_services_hass({
        "async_add_recurring_trip": {"return_value": "rec_lun_abc12345"},
        "async_add_punctual_trip": {"return_value": "pun_20251119_abc12345"},
    })


@pytest.fixture
def mock_hass_update_sensor_error():
    """Manager configured for sensor update error test."""
    return _build_services_hass({
        "async_setup": {"return_value": None},
        "async_update_trip": {"return_value": True},
        "async_get_recurring_trips": {"return_value": [{"id": "rec_lun_abc", "dia_semana": "lunes", "hora": "09:00"}]},
    })


@pytest.fixture
def mock_hass_delete_not_found_v1():
    """async_delete_trip returns None (for TestHandleDeleteTripNotFound)."""
    return _build_services_hass({
        "async_setup": {"return_value": None},
        "async_delete_trip": {"return_value": None},
    })


@pytest.fixture
def mock_hass_get_not_found():
    """Trip not found in search (both get methods return [])."""
    return _build_services_hass({
        "async_get_recurring_trips": {"return_value": []},
        "async_get_punctual_trips": {"return_value": []},
    })


@pytest.fixture
def mock_hass_import_error():
    """async_get_recurring_trips raises during import."""
    return _build_services_hass({
        "async_get_recurring_trips": {"side_effect": RuntimeError("Storage error during clear")},
        "async_add_recurring_trip": {"return_value": "rec_lun_new"},
    })


@pytest.fixture
def mock_hass_delete_not_found_v2():
    """async_delete_trip returns False (for TestHandleTripDelete)."""
    return _build_services_hass({
        "async_delete_trip": {"return_value": False},
    })


@pytest.fixture
def mock_hass_create_manager_error():
    """Manager async_setup raises during creation."""
    return _build_services_hass({
        "async_setup": {"side_effect": RuntimeError("Setup failed")},
        "async_add_recurring_trip": {"return_value": "rec_lun_abc"},
    })


@pytest.fixture
def mock_hass_manager_setup_error():
    """trip_manager is None in runtime_data so _get_manager creates a new one.

    The new manager's async_setup raises, exercising the error path in
    _get_manager where the factory catches the exception and logs it.
    """
    from custom_components.ev_trip_planner.trip_manager import TripManager

    hass = _build_services_hass()
    # Override: set trip_manager to None so _get_manager enters the "create new" path
    mock_entry = hass.config_entries.async_get_entry("entry_test")
    mock_entry.runtime_data.trip_manager = None

    # Patch TripManager so async_setup raises when _get_manager creates one
    with patch.object(
        TripManager,
        "async_setup",
        side_effect=RuntimeError("Storage read failed"),
    ):
        yield hass


@pytest.fixture
def mock_hass_manager_setup_ok():
    """trip_manager is None but async_setup succeeds, exercising line 752.

    _get_manager creates a new manager and calls async_setup successfully,
    covering the log line after async_setup returns.
    """
    from custom_components.ev_trip_planner.trip_manager import TripManager

    hass = _build_services_hass()
    # Override: set trip_manager to None so _get_manager enters the "create new" path
    mock_entry = hass.config_entries.async_get_entry("entry_test")
    mock_entry.runtime_data.trip_manager = None

    # Patch TripManager so async_setup succeeds
    with patch.object(TripManager, "async_setup", return_value=None):
        yield hass


@pytest.fixture
def mock_hass_update_km_kwh():
    """Manager configured for km/kwh update."""
    return _build_services_hass({
        "async_update_trip": {"return_value": True},
        "async_get_recurring_trips": {"return_value": [{"id": "rec_lun_abc", "dia_semana": "lunes", "hora": "09:00", "km": 24.0, "kwh": 3.6}]},
        "async_setup": {"return_value": None},
    })


@pytest.fixture
def mock_hass_recurrente_success():
    """Manager configured for recurrente success."""
    return _build_services_hass({
        "async_add_recurring_trip": {"return_value": "rec_lun_abc12345"},
        "async_setup": {"return_value": None},
    })


@pytest.fixture
def mock_hass_puntual_success():
    """Manager configured for puntual success."""
    return _build_services_hass({
        "async_add_punctual_trip": {"return_value": "pun_20251119_abc12345"},
        "async_setup": {"return_value": None},
    })


@pytest.fixture
def mock_hass_english_fields():
    """Manager configured for English fields."""
    return _build_services_hass({
        "async_add_recurring_trip": {"return_value": "rec_lun_abc12345"},
        "async_setup": {"return_value": None},
    })


@pytest.fixture
def mock_hass_list_with_trips():
    """Hass with existing trips."""
    return _build_services_hass({
        "async_get_recurring_trips": {"return_value": [{"id": "rec_lun_1", "tipo": "recurrente", "activo": True}, {"id": "rec_mar_1", "tipo": "recurrente", "activo": True}]},
        "async_get_punctual_trips": {"return_value": [{"id": "pun_20251119_1", "tipo": "puntual", "estado": "pendiente"}]},
        "async_setup": {"return_value": None},
    })


@pytest.fixture
def mock_hass_none_data_entry():
    """Entry with None data (special case, needs custom build)."""
    from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

    class Services:
        def __init__(self):
            self.registry = {}

        def async_register(
            self, domain, name, handler, schema=None, supports_response=None
        ):
            if domain == DOMAIN:
                self.registry[name] = handler

    hass = MagicMock()
    hass.data = {}
    hass.services = Services()
    hass.config_entries = MagicMock()

    mock_entry_valid = MagicMock()
    mock_entry_valid.entry_id = "entry_valid"
    mock_entry_valid.data = {"vehicle_name": "valid_vehicle"}
    mock_coordinator = MagicMock()
    mock_manager = MagicMock()
    mock_manager.async_get_recurring_trips = AsyncMock(return_value=[])
    mock_manager.async_get_punctual_trips = AsyncMock(return_value=[])
    mock_entry_valid.runtime_data = EVTripRuntimeData(
        coordinator=mock_coordinator,
        trip_manager=mock_manager,
    )

    mock_entry_none = MagicMock()
    mock_entry_none.entry_id = "entry_none"
    mock_entry_none.data = None

    hass.config_entries.async_entries = MagicMock(
        return_value=[mock_entry_none, mock_entry_valid]
    )
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry_valid)

    return hass


@pytest.fixture
def mock_hass_update_with_updates():
    """Old 'updates' object format."""
    return _build_services_hass({
        "async_update_trip": {"return_value": True},
        "async_get_recurring_trips": {"return_value": [{"id": "rec_lun_abc", "dia_semana": "lunes", "hora": "09:00"}]},
        "async_setup": {"return_value": None},
    })


@pytest.fixture
def mock_hass_removal():
    """Mock hass for async_remove_entry_cleanup tests (returns tuple)."""
    hass = MagicMock()
    hass.data = {"storage": {}}
    hass.config.config_dir = "/tmp/test_config"

    mock_trip_manager = MagicMock()
    mock_trip_manager.async_delete_all_trips = AsyncMock()

    mock_emhass_adapter = MagicMock()
    mock_emhass_adapter.async_cleanup_vehicle_indices = AsyncMock()
    mock_emhass_adapter._config_entry_listener = MagicMock()

    mock_runtime_data = MagicMock()
    mock_runtime_data.trip_manager = mock_trip_manager
    mock_runtime_data.emhass_adapter = mock_emhass_adapter

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_test"
    mock_entry.data = {"vehicle_name": "Test Vehicle"}
    mock_entry.runtime_data = mock_runtime_data

    return hass, mock_entry


# ============================================================================
# test_init.py — mock_hass fixture
# ============================================================================


class _ServicesRegistry:
    """Minimal services registry for mock hass in test services tests."""

    def __init__(self):
        self.registry = {}

    def async_register(
        self, domain, name, handler, schema=None, supports_response=None
    ):
        if domain == DOMAIN:
            self.registry[name] = handler


@pytest.fixture
def mock_hass():
    """Create mock HomeAssistant for test_init.py and test_services_core.py tests.

    This fixture provides a comprehensive mock hass that covers all test_init.py use cases:
    - hass.data = {} or {"ev_trip_planner": {}}
    - hass.config.config_dir = "/tmp/test_config"
    - hass.config_entries with all needed methods
    - hass.services with Services.registry for service registration tests

    Tests that need specific configurations can override/add attributes directly.
    """
    hass = MagicMock()
    hass.data = {}
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.components = []
    hass.services = _ServicesRegistry()
    hass.services.async_call = AsyncMock()

    # Config entries with all needed methods
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    # Create a mock entry with proper data dict so .get() returns real values
    mock_entry = MagicMock()
    mock_entry.data = {
        "vehicle_name": "test_vehicle",
        "charging_power_kw": 3.6,
        "battery_capacity_kwh": 50.0,
        "safety_margin_percent": 10.0,
    }

    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    # Mock async_add_executor_job for non-blocking I/O
    async def mock_executor_job(func, *args):
        return func(*args)
    hass.async_add_executor_job = mock_executor_job
    hass.loop = MagicMock()
    hass.loop.time.return_value = 0.0

    return hass


# ============================================================================
# test_config_updates.py - mock_hass fixture
# ============================================================================


@pytest.fixture
def mock_hass_config_updates():
    """Mock hass with config_entries, bus, states for config update tests."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.bus = MagicMock()
    hass.states = MagicMock()
    hass.states.async_remove = MagicMock(return_value=None)
    return hass


# ============================================================================
# test_functional_emhass_sensor_updates.py - mock_hass fixture
# ============================================================================


@pytest.fixture
def mock_hass_functional():
    """Mock hass with spec=HomeAssistant for functional sensor update tests."""
    from homeassistant.core import HomeAssistant
    hass = Mock(spec=HomeAssistant)
    hass.data = {}
    hass.states = Mock()
    hass.bus = Mock()
    hass.bus.async_listen = Mock()
    hass.state = CoreState.running
    hass.config = Mock()
    hass.config.config_dir = '/tmp/homeassistant'
    return hass


# ============================================================================
# test_migrate_entry.py - mock_hass fixture
# ============================================================================


@pytest.fixture
def mock_hass_migrate():
    """Minimal mock hass with data={} for migrate entry tests."""
    hass = MagicMock()
    hass.data = {}
    return hass


# ============================================================================
# test_presence_monitor.py / test_presence_monitor_soc.py - mock_hass fixture
# ============================================================================


@pytest.fixture
def mock_hass_presence():
    """Mock hass for presence_monitor tests (spec=HomeAssistant + bus + services)."""
    from homeassistant.core import HomeAssistant
    hass = Mock(spec=HomeAssistant)
    hass.data = {}
    hass.states = Mock()
    hass.states.async_set = MagicMock()
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    hass.bus = Mock()
    hass.bus.async_listen = Mock()

    async def _ahj(job, *_a, **_k):
        return None
    hass.async_run_hass_job = _ahj
    return hass


# ============================================================================
# test_sensor_integration.py - mock_hass_and_coordinator fixture
# ============================================================================


@pytest.fixture
def mock_hass_and_coordinator():
    """Mock hass and coordinator for sensor integration tests."""
    hass = MagicMock()
    hass.services = MagicMock()
    hass.config_entries = MagicMock()
    coordinator = MagicMock()
    coordinator.data = None
    return hass, coordinator


# ============================================================================
# test_trip_calculations.py - mock_hass fixture
# ============================================================================


@pytest.fixture
def mock_hass_trip_calculations():
    """Mock hass with spec=HomeAssistant for trip calculations tests."""
    from homeassistant.core import HomeAssistant
    hass = Mock(spec=HomeAssistant)
    hass.data = {}
    hass.states = Mock()
    return hass


# ============================================================================
# test_trip_manager_core.py (integration) - mock_hass fixture
# ============================================================================


@pytest.fixture
def mock_hass_trip_manager():
    """Mock hass with config_entries for integration trip_manager tests."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = 'test_entry_id'
    mock_entry.data = {'vehicle_name': 'test_vehicle', 'charging_power_kw': 3.6}
    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    hass.loop = MagicMock()
    hass.loop.time.return_value = 0.0
    return hass


# ============================================================================
# test_trip_manager_power_profile.py - mock_hass fixture
# ============================================================================


@pytest.fixture
def mock_hass_power_profile():
    """Mock hass with config_entries for power profile tests."""
    hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = 'test_vehicle'
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    return hass


# ============================================================================
# test_user_real_data_simple.py - mock_hass fixture
# ============================================================================


@pytest.fixture
def mock_hass_user_real_data():
    """Mock hass with config_entries and data.get() for user real data tests."""
    hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = 'test_entry_123'
    data_dict = {'vehicle_name': 'test_vehicle', 'charging_power_kw': 3.6}
    mock_entry.data = MagicMock()
    mock_entry.data.get = MagicMock(
        side_effect=lambda key, default=None: data_dict.get(key, default)
    )
    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    hass.data = {}
    hass.async_add_executor_job = AsyncMock(return_value=None)
    hass.config = MagicMock()
    hass.config.config_dir = '/tmp/test_config'
    hass.config.components = []
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    hass.loop = MagicMock()
    hass.loop.time.return_value = 0.0
    return hass


# ============================================================================
# test_trip_calculations.py - mock_hass fixture (with Store patching)
# ============================================================================


@pytest.fixture
def mock_hass_calc():
    """Mock hass with in-memory storage (patches Store class)."""
    _storage_data = {}

    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_id"
    mock_entry.data = {"vehicle_name": "test_vehicle", "charging_power_kw": 3.6}
    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    future = asyncio.Future()
    future.set_result(None)

    async def mock_async_create_task(*args, **kwargs):
        return future

    async def mock_async_add_executor_job(*args, **kwargs):
        return future

    hass.async_create_task = mock_async_create_task
    hass.async_add_executor_job = mock_async_add_executor_job

    from homeassistant.helpers.storage import Store

    async def mock_async_load(self):
        key = getattr(self, "_mock_key", None)
        if key is None:
            return []
        await asyncio.sleep(0)
        return _storage_data.get(key, [])

    async def mock_async_save(self, data):
        key = getattr(self, "_mock_key", None)
        if key is not None:
            await asyncio.sleep(0)
            _storage_data[key] = data

    def mock_init(self, hass_obj, version, key, private=False):
        self._mock_key = key
        original_store_init(self, hass_obj, version, key, private)

    original_store_init = Store.__init__
    original_async_load = Store.async_load
    original_async_save = Store.async_save

    Store.__init__ = mock_init
    Store.async_load = mock_async_load
    Store.async_save = mock_async_save

    yield hass

    Store.__init__ = original_store_init
    Store.async_load = original_async_load
    Store.async_save = original_async_save

