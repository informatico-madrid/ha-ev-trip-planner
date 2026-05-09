"""Unit test fixtures — mocks that don't need HA framework."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.ev_trip_planner.trip_manager import TripManager

import pytest


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
