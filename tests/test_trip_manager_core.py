"""Core tests for TripManager covering CRUD and state transitions (hass.data API)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.const import (
    TRIP_STATUS_CANCELLED,
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_PENDING,
)
from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def vehicle_id() -> str:
    return "chispitas"


@pytest.fixture
def mock_hass():
    """Create a mock hass with config_entries, data, and storage."""
    hass = MagicMock()
    # Mock config_entries
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    # Mock hass.data with proper namespace (legacy)
    hass.data = {}
    # Mock hass.storage for persistence (new implementation)
    hass.storage = MagicMock()
    hass.storage.async_read = AsyncMock(return_value=None)
    hass.storage.async_write_dict = AsyncMock(return_value=True)
    return hass


@pytest.mark.asyncio
async def test_async_setup_initializes_empty_storage(mock_hass, vehicle_id):
    """Test that async_setup initializes with empty trips when no data exists."""
    # Ensure namespace doesn't exist in hass.data
    namespace = f"ev_trip_planner_test_entry_123"
    assert namespace not in mock_hass.data

    manager = TripManager(mock_hass, vehicle_id)
    await manager.async_setup()

    # After setup, trips should be empty
    assert manager._trips == {}
    assert manager._recurring_trips == {}
    assert manager._punctual_trips == {}


@pytest.mark.asyncio
async def test_async_setup_loads_existing_and_does_not_save(mock_hass, vehicle_id):
    """Test that async_setup loads existing trips from hass.storage."""
    # Pre-populate hass.storage with trips (new persistence mechanism)
    existing_trips = {
        "rec_lun_123": {
            "id": "rec_lun_123",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00"
        }
    }
    storage_key = f"ev_trip_planner_{vehicle_id}"
    mock_hass.storage.async_read = AsyncMock(
        return_value={
            "data": {
                "trips": existing_trips,
                "recurring_trips": existing_trips,
                "punctual_trips": {}
            }
        }
    )

    manager = TripManager(mock_hass, vehicle_id)
    await manager.async_setup()

    # Should have loaded the existing trips
    assert "rec_lun_123" in manager._recurring_trips


@pytest.mark.asyncio
async def test_async_load_trips_empty_returns_list(mock_hass, vehicle_id):
    """Test that _load_trips returns empty when no data exists."""
    manager = TripManager(mock_hass, vehicle_id)
    await manager._load_trips()

    assert manager._trips == {}
    assert manager._recurring_trips == {}
    assert manager._punctual_trips == {}


@pytest.mark.asyncio
async def test_async_load_trips_with_data(mock_hass, vehicle_id):
    """Test that _load_trips loads data from hass.storage."""
    # Pre-populate hass.storage with trips
    existing_recurring = {
        "rec_lun_123": {
            "id": "rec_lun_123",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
        },
    }
    existing_punctual = {
        "pun_20251119_123": {
            "id": "pun_20251119_123",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
        },
    }
    storage_key = f"ev_trip_planner_{vehicle_id}"
    mock_hass.storage.async_read = AsyncMock(
        return_value={
            "data": {
                "trips": {**existing_recurring, **existing_punctual},
                "recurring_trips": existing_recurring,
                "punctual_trips": existing_punctual
            }
        }
    )

    manager = TripManager(mock_hass, vehicle_id)
    await manager._load_trips()

    assert len(manager._recurring_trips) == 1
    assert len(manager._punctual_trips) == 1
    assert "rec_lun_123" in manager._recurring_trips
    assert "pun_20251119_123" in manager._punctual_trips


@pytest.mark.asyncio
async def test_async_save_trips_calls_store_save(mock_hass, vehicle_id):
    """Test that async_save_trips saves to hass.storage."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_abc": {
            "id": "rec_lun_abc",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00"
        }
    }

    await manager.async_save_trips()

    # Check data was saved to hass.storage.async_write_dict
    storage_key = f"ev_trip_planner_{vehicle_id}"
    mock_hass.storage.async_write_dict.assert_called_once()
    call_args = mock_hass.storage.async_write_dict.call_args
    assert call_args[0][0] == storage_key
    assert "rec_lun_abc" in call_args[0][1]["data"]["recurring_trips"]


@pytest.mark.asyncio
async def test_add_recurring_trip_happy_path(mock_hass, vehicle_id):
    """Test adding a recurring trip."""
    manager = TripManager(mock_hass, vehicle_id)
    await manager.async_add_recurring_trip(
        dia_semana="lunes", hora="09:00", km=24.0, kwh=3.6, descripcion="Trabajo"
    )

    # Should have added a trip (check that there's at least one trip)
    assert len(manager._recurring_trips) == 1
    trip_id = list(manager._recurring_trips.keys())[0]
    assert trip_id.startswith("rec_lun_")
    saved_trip = manager._recurring_trips[trip_id]
    assert saved_trip["dia_semana"] == "lunes"
    assert saved_trip["hora"] == "09:00"


@pytest.mark.asyncio
async def test_update_trip_updates_fields(mock_hass, vehicle_id):
    """Test updating a trip."""
    # Pre-populate with a trip
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_12345678": {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
        },
    }
    manager._punctual_trips = {
        "pun_20251119_87654321": {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "estado": TRIP_STATUS_PENDING,
        },
    }

    await manager.async_update_trip("rec_lun_12345678", {"hora": "10:00", "km": 30.0})

    # Check the update was applied
    assert manager._recurring_trips["rec_lun_12345678"]["hora"] == "10:00"
    assert manager._recurring_trips["rec_lun_12345678"]["km"] == 30.0


@pytest.mark.asyncio
async def test_update_trip_not_found_returns_false(mock_hass, vehicle_id):
    """Test updating a non-existent trip - no error should occur."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}

    # Should not raise, just do nothing
    await manager.async_update_trip("does_not_exist", {"hora": "10:00"})


@pytest.mark.asyncio
async def test_delete_trip_removes_entry(mock_hass, vehicle_id):
    """Test deleting a trip."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_12345678": {"id": "rec_lun_12345678", "tipo": "recurrente"},
    }
    manager._punctual_trips = {
        "pun_20251119_87654321": {"id": "pun_20251119_87654321", "tipo": "puntual"},
    }

    await manager.async_delete_trip("rec_lun_12345678")

    assert "rec_lun_12345678" not in manager._recurring_trips
    assert "pun_20251119_87654321" in manager._punctual_trips


@pytest.mark.asyncio
async def test_delete_trip_not_found_returns_false(mock_hass, vehicle_id):
    """Test deleting a non-existent trip - no error should occur."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}

    # Should not raise, just do nothing
    await manager.async_delete_trip("does_not_exist")


@pytest.mark.asyncio
async def test_pause_and_complete_trips(mock_hass, vehicle_id):
    """Test pausing and completing trips."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_12345678": {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "activo": True,
            "dia_semana": "lunes",
            "hora": "09:00",
        },
    }
    manager._punctual_trips = {
        "pun_20251119_87654321": {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "estado": TRIP_STATUS_PENDING,
        },
    }

    await manager.async_pause_recurring_trip("rec_lun_12345678")
    assert manager._recurring_trips["rec_lun_12345678"]["activo"] is False

    await manager.async_complete_punctual_trip("pun_20251119_87654321")
    assert manager._punctual_trips["pun_20251119_87654321"]["estado"] == TRIP_STATUS_COMPLETED


@pytest.mark.asyncio
async def test_resume_and_cancel_trips(mock_hass, vehicle_id):
    """Test resuming and canceling trips."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_12345678": {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "activo": False,
            "dia_semana": "lunes",
            "hora": "09:00",
        },
    }
    manager._punctual_trips = {
        "pun_20251119_87654321": {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "estado": TRIP_STATUS_PENDING,
        },
    }

    await manager.async_resume_recurring_trip("rec_lun_12345678")
    assert manager._recurring_trips["rec_lun_12345678"]["activo"] is True

    # Cancel removes the trip from the dictionary
    await manager.async_cancel_punctual_trip("pun_20251119_87654321")
    assert "pun_20251119_87654321" not in manager._punctual_trips


@pytest.mark.asyncio
async def test_getters_and_not_found(mock_hass, vehicle_id):
    """Test getter methods."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_12345678": {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00"
        },
    }
    manager._punctual_trips = {
        "pun_20251119_87654321": {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00"
        },
    }

    rec_trips = await manager.async_get_recurring_trips()
    pun_trips = await manager.async_get_punctual_trips()

    assert len(rec_trips) == 1 and rec_trips[0]["tipo"] == "recurrente"
    assert len(pun_trips) == 1 and pun_trips[0]["tipo"] == "puntual"


@pytest.mark.asyncio
async def test_add_punctual_trip_happy_path(mock_hass, vehicle_id):
    """Test adding a punctual trip."""
    manager = TripManager(mock_hass, vehicle_id)
    await manager.async_add_punctual_trip(
        datetime="2025-11-19T15:00:00", km=110.0, kwh=16.5, descripcion="Viaje"
    )

    # Should have added a trip
    assert len(manager._punctual_trips) == 1
    trip_id = list(manager._punctual_trips.keys())[0]
    assert trip_id.startswith("pun_") or trip_id.startswith("trip_")
    saved_trip = manager._punctual_trips[trip_id]
    assert saved_trip["km"] == 110.0


@pytest.mark.asyncio
async def test_add_recurring_trip_accepts_valid_hour_formats(mock_hass, vehicle_id):
    """Test that async_add_recurring_trip accepts valid hour formats."""
    manager = TripManager(mock_hass, vehicle_id)

    # Test valid hour formats
    valid_times = ["00:00", "09:00", "12:30", "16:45", "23:59"]

    for time_str in valid_times:
        await manager.async_add_recurring_trip(
            dia_semana="lunes", hora=time_str, km=24.0, kwh=3.6, descripcion="Trabajo"
        )

    # Should have saved all valid trips
    assert len(manager._recurring_trips) == len(valid_times)
