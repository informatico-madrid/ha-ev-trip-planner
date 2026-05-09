"""Test fixtures for ev_trip_planner."""

from __future__ import annotations

import asyncio
import inspect
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_LOGGER = logging.getLogger(__name__)


def _make_mock_datetime_fixture(default_dt: datetime):
    """Factory that creates a fixture with a hardcoded default datetime."""

    @pytest.fixture
    def mock_dt_fixture(request):
        """Mock datetime.now(timezone.utc) for deterministic deadline calculations.

        Accepts an optional datetime parameter. When used without parameters,
        defaults to the provided fixed datetime.

        Example usage:
            async def test_something(mock_datetime_2026_05_04_monday_0800_utc):
                pass
        """
        if hasattr(request, "param") and request.param is not None:
            fixed_now = request.param
        else:
            fixed_now = default_dt

        # Save real datetime class for isinstance checks
        real_datetime = datetime

        class MockDatetime(real_datetime):
            """Subclass of datetime that overrides .now() to return a fixed value."""

            @classmethod
            def now(cls, tz=None):
                return fixed_now.replace(tzinfo=tz or timezone.utc)

        with (
            patch(
                "custom_components.ev_trip_planner.emhass_adapter.datetime",
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


# Note: pytest-homeassistant-custom-component is not available
# The auto_enable_custom_integrations fixture is commented out
# Tests that require it should use the hass fixture instead
# @pytest.fixture(autouse=True)
# def auto_enable_custom_integrations(enable_custom_integrations):
#     """Enable custom integrations in all tests."""
#     yield


@pytest.fixture
def hass():
    """Fixture to provide a minimal mock HomeAssistant instance.

    This creates a mock hass instance that avoids compatibility issues
    with pytest-homeassistant-custom-component. Both unit and integration tests
    use this fixture for state/service mocking.
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
        except Exception as e:
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
def mock_hass():
    """Fixture to provide a mock Home Assistant instance.

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


@pytest.fixture
def sample_notification_config():
    """Return a sample notification configuration for testing."""
    return {
        "notification_service": "notify.mobile_app",
        "notification_devices": ["device_123"],
    }


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
    """
    from custom_components.ev_trip_planner.trip_manager import TripManager

    return TripManager(
        mock_hass, "test_vehicle", entry_id="test_entry_123", storage=mock_store
    )
