"""Additional coverage tests for trip_manager error paths."""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def mock_hass_with_storage():
    """Create a mock hass with storage for testing error paths."""
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


@pytest.mark.asyncio
async def test_async_setup_handles_cancelled_error(mock_hass_with_storage):
    """async_setup handles CancelledError during storage load."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

    # Make storage async_read raise CancelledError
    mock_hass_with_storage.storage.async_read = AsyncMock(
        side_effect=asyncio.CancelledError
    )

    # Should not raise - CancelledError is caught and treated as empty state
    await trip_manager.async_setup()

    assert trip_manager._trips == {}
    assert trip_manager._recurring_trips == {}
    assert trip_manager._punctual_trips == {}
    assert trip_manager._last_update is None


@pytest.mark.asyncio
async def test_async_setup_handles_generic_exception(mock_hass_with_storage):
    """async_setup handles generic Exception during storage load."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

    # Make storage async_read raise a generic exception
    mock_hass_with_storage.storage.async_read = AsyncMock(
        side_effect=ValueError("Storage corrupted")
    )

    # Should not raise - exception is caught and treated as empty state
    await trip_manager.async_setup()

    assert trip_manager._trips == {}
    assert trip_manager._recurring_trips == {}
    assert trip_manager._punctual_trips == {}
    assert trip_manager._last_update is None


@pytest.mark.asyncio
async def test_async_save_trips_handles_exception(mock_hass_with_storage):
    """async_save_trips handles exceptions during save gracefully."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
    await trip_manager.async_setup()

    # Make storage async_write_dict raise an exception
    mock_hass_with_storage.storage.async_write_dict = AsyncMock(
        side_effect=Exception("Disk full")
    )

    # Should not raise - exception is caught and logged
    await trip_manager.async_save_trips()

    # Data should still be intact
    assert trip_manager._trips == {}


@pytest.mark.asyncio
async def test_async_save_trips_yaml_fallback_also_fails(mock_hass_with_storage):
    """async_save_trips falls back to YAML and catches that error too."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
    await trip_manager.async_setup()

    # Make both HA storage AND YAML fallback fail
    mock_hass_with_storage.storage.async_write_dict = AsyncMock(
        side_effect=Exception("HA storage failed")
    )

    # Patch Path to raise on mkdir
    with patch(
        "pathlib.Path.mkdir",
        side_effect=Exception("mkdir failed"),
    ):
        # Should not raise - both failures caught
        await trip_manager.async_save_trips()


@pytest.mark.asyncio
async def test_set_and_get_emhass_adapter(mock_hass_with_storage):
    """TripManager set_emhass_adapter and get_emhass_adapter work correctly."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

    mock_adapter = MagicMock()
    trip_manager.set_emhass_adapter(mock_adapter)

    assert trip_manager.get_emhass_adapter() is mock_adapter


@pytest.mark.asyncio
async def test_async_generate_deferrables_schedule_returns_list(mock_hass_with_storage):
    """Test async_generate_deferrables_schedule returns a list of deferrable dicts."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

    result = await trip_manager.async_generate_deferrables_schedule()

    # Result is a list of deferrable load dicts (one per time slot)
    assert isinstance(result, list)
    assert len(result) > 0
    # Each entry should have a 'date' key
    assert "date" in result[0]


@pytest.mark.asyncio
async def test_async_generate_power_profile_with_presence_monitor(mock_hass_with_storage):
    """async_generate_power_profile uses presence_monitor for hora_regreso."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
    await trip_manager.async_setup()

    # Set up presence_monitor mock
    mock_presence = MagicMock()
    mock_presence.async_get_hora_regreso = AsyncMock(
        return_value=datetime(2025, 1, 15, 18, 0)
    )
    trip_manager.vehicle_controller._presence_monitor = mock_presence

    # Should use presence_monitor's hora_regreso
    result = await trip_manager.async_generate_power_profile(
        charging_power_kw=3.6,
        planning_horizon_days=1,
    )

    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_async_generate_power_profile_no_presence_monitor(mock_hass_with_storage):
    """async_generate_power_profile handles missing presence_monitor gracefully."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
    await trip_manager.async_setup()

    # No presence_monitor set
    trip_manager.vehicle_controller._presence_monitor = None

    # Should not raise - presence_monitor is None
    result = await trip_manager.async_generate_power_profile(
        charging_power_kw=3.6,
        planning_horizon_days=1,
    )

    assert isinstance(result, list)
