"""Test fixtures for ev_trip_planner."""

from __future__ import annotations

import asyncio
import inspect
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def hass(tmp_path):
    """Fixture to provide a minimal mock HomeAssistant instance.

    This creates a mock hass instance that avoids compatibility issues
    with pytest-homeassistant-custom-component. Both unit and integration tests
    use this fixture for state/service mocking.
    """
    hass_inst = MagicMock()

    hass_inst.config = MagicMock()
    hass_inst.config.config_dir = str(tmp_path)
    hass_inst.config.time_zone = "UTC"
    hass_inst.config.latitude = 40.0
    hass_inst.config.longitude = -3.0
    hass_inst.config.elevation = 0

    hass_inst.states = MagicMock()
    hass_inst._states_dict = {}

    def _mock_states_get(entity_id):
        return hass_inst._states_dict.get(entity_id, None)

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
        except Exception:
            raise

    hass_inst.async_run_hass_job = _mock_async_run_hass_job

    yield hass_inst


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
def mock_hass(tmp_path):
    """Fixture to provide a mock Home Assistant instance.

    This is needed for EMHASSAdapter initialization and other tests
    that require a hass object with basic configuration.
    """
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = str(tmp_path)
    hass.config.time_zone = "UTC"
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    yield hass


@pytest.fixture
def vehicle_id():
    """Return a sample vehicle ID."""
    return "chispitas"


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
