"""Tests for TripManager with Storage API (replacing input_text)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.const import (
    DOMAIN,
    TRIP_STATUS_PENDING,
    TRIP_TYPE_PUNCTUAL,
    TRIP_TYPE_RECURRING,
)
from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def vehicle_id() -> str:
    return "chispitas"


@pytest.fixture
def mock_store():
    """Mock Store instance."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock()
    return store


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    return hass


@pytest.mark.asyncio
async def test_async_setup_initializes_empty_storage(mock_hass, mock_store, vehicle_id):
    """Test async_setup creates empty storage if none exists."""
    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        await manager.async_setup()

        # Verify Store.async_load was called
        mock_store.async_load.assert_called_once()
        # Verify empty list was saved
        mock_store.async_save.assert_called_once_with([])


@pytest.mark.asyncio
async def test_async_setup_loads_existing_trips(mock_hass, mock_store, vehicle_id):
    """Test async_setup loads existing trips from storage."""
    existing_trips = [
        {
            "id": "rec_lun_test123",
            "tipo": "recurring",
            "dia_semana": "lunes",
            "hora": "09:00",
        }
    ]
    mock_store.async_load = AsyncMock(return_value=existing_trips)

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        await manager.async_setup()

        # Verify Store.async_load was called
        mock_store.async_load.assert_called_once()
        # Verify no save was called (data already exists)
        mock_store.async_save.assert_not_called()


@pytest.mark.asyncio
async def test_add_recurring_trip_saves_to_storage(mock_hass, mock_store, vehicle_id):
    """Test adding recurring trip saves to Store."""
    mock_store.async_load = AsyncMock(return_value=[])

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)

        trip_id = await manager.async_add_recurring_trip(
            dia_semana="lunes",
            hora="09:00",
            km=25,
            kwh=3.75,
            descripcion="Trabajo"
        )

        # Verify trip was created
        assert trip_id.startswith("rec_lun_")

        # Verify save was called with trip data
        assert mock_store.async_save.called
        saved_trips = mock_store.async_save.call_args[0][0]
        assert len(saved_trips) == 1
        assert saved_trips[0]["id"] == trip_id
        assert saved_trips[0]["dia_semana"] == "lunes"


@pytest.mark.asyncio
async def test_get_trips_loads_from_storage(mock_hass, mock_store, vehicle_id):
    """Test get methods load from Store."""
    stored_trips = [
        {
            "id": "rec_lun_test1",
            "tipo": TRIP_TYPE_RECURRING,
            "dia_semana": "lunes",
            "hora": "09:00",
            "activo": True,
        },
        {
            "id": "pun_test2",
            "tipo": TRIP_TYPE_PUNCTUAL,
            "fecha_hora": "2025-11-20T10:00:00",
            "estado": TRIP_STATUS_PENDING,
        },
    ]
    mock_store.async_load = AsyncMock(return_value=stored_trips)

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)

        # Get recurring trips
        recurring = await manager.async_get_recurring_trips()
        assert len(recurring) == 1
        assert recurring[0]["id"] == "rec_lun_test1"

        # Get punctual trips  
        punctual = await manager.async_get_punctual_trips()
        assert len(punctual) == 1
        assert punctual[0]["id"] == "pun_test2"


@pytest.mark.asyncio
async def test_delete_trip_saves_to_storage(mock_hass, mock_store, vehicle_id):
    """Test deleting trip updates Store."""
    initial_trips = [
        {"id": "rec_lun_test1", "tipo": "recurring", "dia_semana": "lunes"},
        {"id": "rec_mar_test2", "tipo": "recurring", "dia_semana": "martes"},
    ]
    mock_store.async_load = AsyncMock(return_value=initial_trips)

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)

        await manager.async_delete_trip("rec_lun_test1")

        # Verify save was called with reduced list
        assert mock_store.async_save.called
        saved_trips = mock_store.async_save.call_args[0][0]
        assert len(saved_trips) == 1
        assert saved_trips[0]["id"] == "rec_mar_test2"
