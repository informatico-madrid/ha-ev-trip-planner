"""Test fixtures for ev_trip_planner."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def enable_custom_integrations():
    """Enable custom integrations for testing.

    This fixture allows Home Assistant to load custom integrations during tests.
    Required per project coding guidelines for integration tests.
    """
    return True


# FIX: Mock frame reporting for HA 2026.3+ compatibility
# DataUpdateCoordinator in HA 2026.3+ requires frame helper to be set up
# This autouse fixture mocks the frame.report_usage to bypass the check
@pytest.fixture(autouse=True)
def mock_frame_reporting():
    """Mock frame reporting to avoid 'Frame helper not set up' error."""
    with patch("homeassistant.helpers.frame.report_usage", return_value=None):
        yield


# Note: pytest-homeassistant-custom-component is not available
# The auto_enable_custom_integrations fixture is commented out
# Tests that require it should use the hass fixture instead
# @pytest.fixture(autouse=True)
# def auto_enable_custom_integrations(enable_custom_integrations):
#     """Enable custom integrations in all tests."""
#     yield


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


@pytest.fixture
def vehicle_id():
    """Return a sample vehicle ID."""
    return "chispitas"


@pytest.fixture
def hass():
    """
    Fixture to provide a working HomeAssistant instance for tests.

    This creates a minimal mock hass instance that avoids compatibility issues
    with pytest-homeassistant-custom-component.
    """
    # Create a mock hass instance instead of real HomeAssistant
    hass = MagicMock()

    # Mock the config attributes
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"
    hass.config.latitude = 40.0
    hass.config.longitude = -3.0
    hass.config.elevation = 0

    # Mock states - use a dictionary to simulate state storage
    hass.states = MagicMock()
    hass._states_dict = {}  # Internal storage for states

    def _mock_states_get(entity_id):
        """Get state from storage."""
        result = hass._states_dict.get(entity_id, None)
        print(f"DEBUG: hass.states.get('{entity_id}') -> {result}")
        return result

    def _mock_states_set(entity_id, state, attributes=None):
        """Synchronous set for states."""
        from unittest.mock import MagicMock

        state_obj = MagicMock()
        state_obj.state = state
        state_obj.attributes = attributes or {}
        hass._states_dict[entity_id] = state_obj
        print(f"DEBUG: hass.states.set('{entity_id}', '{state}', {attributes})")
        return True

    def _mock_states_async_set(entity_id, state, attributes=None):
        """Mock for StateMachine.async_set — @callback decorator, NOT async def."""
        print(f"DEBUG: hass.states.async_set('{entity_id}', '{state}', {attributes})")
        _mock_states_set(entity_id, state, attributes)
        return True

    def _mock_states_async_remove(entity_id):
        """Mock for StateMachine.async_remove — @callback decorator, NOT async def."""
        hass._states_dict.pop(entity_id, None)
        return True

    hass.states.get = _mock_states_get
    hass.states.set = _mock_states_set
    hass.states.async_set = _mock_states_async_set
    hass.states.async_remove = _mock_states_async_remove

    # Mock services
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    # FIX: Añadir async_run_hass_job para el debounce del coordinator
    # El debounce llama a hass.async_run_hass_job(self._job) y espera el resultado
    # Necesitamos que devuelva una tarea/coroutine, no un MagicMock
    import asyncio

    def _mock_async_run_hass_job(job, *args, **kwargs):
        """Mock async_run_hass_job for debounce - devuelve una tarea real."""
        if job is None:
            return None

        # Extraer la función del HassJob
        job_target = None
        job_args = args or []
        job_kwargs = kwargs or {}

        # Si job tiene target (es un HassJob)
        if hasattr(job, "target"):
            job_target = job.target
            # Si el job ya tiene args/kwargs incorporados
            if hasattr(job, "args"):
                job_args = job.args
            if hasattr(job, "kwargs"):
                job_kwargs = job.kwargs
        else:
            # Si es una función directa
            job_target = job

        if job_target is None:
            return None

        # Filtrar kwargs: solo pasar argumentos válidos
        import inspect

        sig = inspect.signature(job_target)
        valid_params = set(sig.parameters.keys())

        # Para async_refresh, los únicos parámetros válidos son self y log_failures
        # Filtramos cualquier kwarg que no esté en la signature
        filtered_kwargs = {k: v for k, v in job_kwargs.items() if k in valid_params}

        # Crear y devolver una tarea que ejecute la función
        try:
            if asyncio.iscoroutinefunction(job_target):
                coro = job_target(*job_args, **filtered_kwargs)
                if asyncio.iscoroutine(coro):
                    return coro
                return asyncio.ensure_future(coro)
            else:
                # Para funciones síncronas, envolver en coroutine
                async def _wrapper():
                    return job_target(*job_args, **filtered_kwargs)

                return asyncio.ensure_future(_wrapper())
        except Exception as e:
            _LOGGER.error("Error in mock_async_run_hass_job: %s", e, exc_info=True)
            raise

    hass.async_run_hass_job = _mock_async_run_hass_job

    yield hass


@pytest.fixture
def mock_hass():
    """
    Fixture to provide a mock Home Assistant instance.

    This is needed for EMHASSAdapter initialization and other tests
    that require a hass object with basic configuration.
    """
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    yield hass


@pytest.fixture
def mock_store():
    """
    Fixture to provide a mock Store instance with async methods.

    This is needed because Store.async_load() and Store.async_save()
    are async methods that need to be mocked with AsyncMock, not MagicMock.

    This implementation also provides data persistence between calls.
    """
    store = MagicMock()
    store._storage = {}  # Internal storage for data persistence

    async def _async_load():
        return store._storage.get("data", None)

    async def _async_save(data):
        store._storage["data"] = data
        return True

    store.async_load = _async_load
    store.async_save = _async_save

    yield store


@pytest.fixture
def mock_store_class():
    """
    Fixture to patch the Store class for testing.

    This properly mocks homeassistant.helpers.storage.Store so tests
    don't hit the real HA Store implementation which requires special
    internal state.
    """
    from homeassistant.helpers import storage as ha_storage
    from unittest.mock import patch

    # Create a proper mock Store class
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

    # Add some default entities
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
            if device.config_entries.get(config_entry_id)
        ]

    def _async_get_device(device_id):
        """Async get device from registry."""
        return _get_device(device_id)

    registry.get = _get_device
    registry.devices_for_config_entry = _devices_for_config_entry
    registry.async_get = _async_get_device

    # Add a default device
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

    # Add a default config entry
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
        """Initialize the flow manager."""
        flow_manager._flow_init = True

    flow_manager.async_init = _async_init

    yield flow_manager


@pytest.fixture
def mock_er_async_get(mock_entity_registry):
    """Patch er.async_get to return mock_entity_registry."""
    from homeassistant.helpers import entity_registry as er
    from unittest.mock import patch

    with patch.object(er, "async_get", return_value=mock_entity_registry):
        yield mock_entity_registry


@pytest.fixture
def mock_hass_with_entity_registry(
    hass, mock_entity_registry, mock_device_registry, mock_config_entries
):
    """
    Return a mock hass instance with entity and device registries.

    This extends the basic hass fixture with additional registries needed
    for config flow testing.
    """
    # Add entity registry
    hass.data = {"entity_registry": mock_entity_registry}

    # Add device registry
    hass.data["device_registry"] = mock_device_registry

    # Add config entries
    hass.data["config_entries"] = mock_config_entries

    # Add mock states for common config flow entities
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

    # Update the states.get method
    def _mock_states_get(entity_id):
        result = hass._states_dict.get(entity_id, None)
        return result

    hass.states.get = _mock_states_get

    # Add mock services for notifications
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    # Mock notify services - including Nabu Casa devices
    def _mock_has_service(domain, service):
        if domain == "notify":
            # Return True for all mock notify services
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

    # Mock async_services to return available notify services (for selector)
    def _mock_async_services():
        return {
            "notify": {
                "mobile_app": MagicMock(),
                "persistent_notification": MagicMock(),
                # Nabu Casa Alexa Media devices
                "alexa_media": MagicMock(),
                "alexa_media_living_room": MagicMock(),
                "alexa_media_bedroom": MagicMock(),
                # Other notify services
                "google_assistant": MagicMock(),
                "telegram": MagicMock(),
            }
        }

    hass.services.async_services = MagicMock(return_value=_mock_async_services())

    return hass


@pytest.fixture
def sample_vehicle_config():
    """Return a sample vehicle configuration for testing."""
    return {
        "vehicle_name": "test_vehicle",
        "soc_sensor": "sensor.ovms_soc",
        "battery_capacity_kwh": 60.0,
        "charging_power_kw": 11.0,
        "kwh_per_km": 0.15,
        "safety_margin_percent": 10,
        "range_sensor": "sensor.ovms_range",
        "charging_status_sensor": "binary_sensor.charging_status",
        "control_type": "none",
    }


@pytest.fixture
def sample_emhass_config():
    """Return a sample EMHASS configuration for testing."""
    return {
        "planning_horizon_days": 7,
        "max_deferrable_loads": 50,
        "planning_sensor_entity": None,
    }


@pytest.fixture
def sample_presence_config():
    """Return a sample presence detection configuration for testing."""
    return {
        "home_sensor": "binary_sensor.home_presence",
        "plugged_sensor": "binary_sensor.vehicle_plugged",
        "charging_sensor": "binary_sensor.charging_status",
    }


@pytest.fixture
def sample_notification_config():
    """Return a sample notification configuration for testing."""
    return {
        "notification_service": "notify.mobile_app",
        "notification_devices": ["device_123"],
    }


@pytest.fixture
def trip_manager_with_entry_id(mock_hass, mock_store):
    """Return a TripManager instance with entry_id for EMHASS-dependent tests.

    This fixture provides a consistent TripManager instance that has entry_id
    set, which is required for publish_deferrable_loads() to trigger coordinator
    refresh correctly.

    Usage:
        async def test_something(trip_manager_with_entry_id):
            tm = trip_manager_with_entry_id
            await tm.publish_deferrable_loads()
            # coordinator refresh will work because entry_id is set
    """
    from custom_components.ev_trip_planner.trip_manager import TripManager

    return TripManager(
        mock_hass, "test_vehicle", entry_id="test_entry_123", storage=mock_store
    )


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
    from custom_components.ev_trip_planner.trip_manager import TripManager

    return TripManager(mock_hass, "test_vehicle")
