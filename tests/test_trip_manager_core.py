"""Core tests for TripManager covering CRUD and state transitions (Storage API)."""

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
    hass = MagicMock()
    return hass


@pytest.mark.asyncio
async def test_async_setup_initializes_empty_storage(mock_hass, vehicle_id):
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=None)
    mock_store.async_save = AsyncMock()

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        await manager.async_setup()

    mock_store.async_load.assert_called_once()
    mock_store.async_save.assert_called_once_with([])


@pytest.mark.asyncio
async def test_async_setup_loads_existing_and_does_not_save(mock_hass, vehicle_id):
    existing = [{"id": "rec_lun_old", "tipo": "recurrente"}]
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=existing)
    mock_store.async_save = AsyncMock()

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        await manager.async_setup()

    mock_store.async_load.assert_called_once()
    mock_store.async_save.assert_not_called()


@pytest.mark.asyncio
async def test_async_load_trips_empty_returns_list(mock_hass, vehicle_id):
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=None)

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        trips = await manager._async_load_trips()
        assert trips == []


@pytest.mark.asyncio
async def test_async_load_trips_with_data(mock_hass, vehicle_id):
    sample = [
        {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
        },
        {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
        },
    ]
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=sample)

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        trips = await manager._async_load_trips()
        assert len(trips) == 2
        assert trips[0]["tipo"] == "recurrente"
        assert trips[1]["tipo"] == "puntual"


@pytest.mark.asyncio
# Removed: invalid JSON test no longer applies with Storage API


@pytest.mark.asyncio
async def test_async_save_trips_calls_store_save(mock_hass, vehicle_id):
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=[])
    mock_store.async_save = AsyncMock()

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        trips = [{"id": "rec_lun_abc", "tipo": "recurrente", "dia_semana": "lunes"}]
        await manager._async_save_trips(trips)

    mock_store.async_save.assert_called_once_with(trips)


@pytest.mark.asyncio
async def test_add_recurring_trip_happy_path(mock_hass, vehicle_id):
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=[])
    mock_store.async_save = AsyncMock()

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        trip_id = await manager.async_add_recurring_trip(
            dia_semana="lunes", hora="09:00", km=24.0, kwh=3.6, descripcion="Trabajo"
        )

    assert trip_id.startswith("rec_lun_")
    assert mock_store.async_save.called
    saved_trips = mock_store.async_save.call_args[0][0]
    assert len(saved_trips) == 1
    assert saved_trips[0]["id"] == trip_id


@pytest.mark.asyncio
async def test_update_trip_updates_fields(mock_hass, vehicle_id):
    initial = [
        {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
        },
        {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "estado": TRIP_STATUS_PENDING,
        },
    ]
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=initial)
    mock_store.async_save = AsyncMock()

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        ok = await manager.async_update_trip("rec_lun_12345678", {"hora": "10:00", "km": 30.0})

    assert ok is True
    saved = mock_store.async_save.call_args[0][0]
    assert any(t["id"] == "rec_lun_12345678" and t["hora"] == "10:00" and t["km"] == 30.0 for t in saved)


@pytest.mark.asyncio
async def test_update_trip_not_found_returns_false(mock_hass, vehicle_id):
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=[])
    mock_store.async_save = AsyncMock()

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        ok = await manager.async_update_trip("does_not_exist", {"hora": "10:00"})
    assert ok is False
    mock_store.async_save.assert_not_called()


@pytest.mark.asyncio
async def test_delete_trip_removes_entry(mock_hass, vehicle_id):
    initial = [
        {"id": "rec_lun_12345678", "tipo": "recurrente"},
        {"id": "pun_20251119_87654321", "tipo": "puntual"},
    ]
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=initial)
    mock_store.async_save = AsyncMock()

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        ok = await manager.async_delete_trip("rec_lun_12345678")
    assert ok is True
    saved = mock_store.async_save.call_args[0][0]
    assert all(t["id"] != "rec_lun_12345678" for t in saved)


@pytest.mark.asyncio
async def test_delete_trip_not_found_returns_false(mock_hass, vehicle_id):
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=[])
    mock_store.async_save = AsyncMock()

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        ok = await manager.async_delete_trip("does_not_exist")
    assert ok is False
    mock_store.async_save.assert_not_called()


@pytest.mark.asyncio
async def test_pause_and_complete_trips(mock_hass, vehicle_id):
    initial = [
        {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "activo": True,
            "dia_semana": "lunes",
            "hora": "09:00",
        },
        {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "estado": TRIP_STATUS_PENDING,
        },
    ]
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=initial)
    mock_store.async_save = AsyncMock()

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        paused = await manager.async_pause_recurring_trip("rec_lun_12345678")
        assert paused is True
        saved_after_pause = mock_store.async_save.call_args[0][0]
        # Next call should see paused state
        mock_store.async_load = AsyncMock(return_value=saved_after_pause)
        completed = await manager.async_complete_punctual_trip("pun_20251119_87654321")
        assert completed is True
        saved_after_complete = mock_store.async_save.call_args[0][0]

    rec = next(t for t in saved_after_complete if t["id"] == "rec_lun_12345678")
    pun = next(t for t in saved_after_complete if t["id"] == "pun_20251119_87654321")
    assert rec["activo"] is False
    assert pun["estado"] == TRIP_STATUS_COMPLETED


@pytest.mark.asyncio
async def test_resume_and_cancel_trips(mock_hass, vehicle_id):
    initial = [
        {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "activo": False,
            "dia_semana": "lunes",
            "hora": "09:00",
        },
        {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "estado": TRIP_STATUS_PENDING,
        },
    ]
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=initial)
    mock_store.async_save = AsyncMock()

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        resumed = await manager.async_resume_recurring_trip("rec_lun_12345678")
        assert resumed is True
        saved_after_resume = mock_store.async_save.call_args[0][0]
        rec = next(t for t in saved_after_resume if t["id"] == "rec_lun_12345678")
        assert rec["activo"] is True

        # Now cancel punctual
        mock_store.async_load = AsyncMock(return_value=saved_after_resume)
        cancelled = await manager.async_cancel_punctual_trip("pun_20251119_87654321")
        assert cancelled is True
        saved_after_cancel = mock_store.async_save.call_args[0][0]
        pun = next(t for t in saved_after_cancel if t["id"] == "pun_20251119_87654321")
        assert pun["estado"] == TRIP_STATUS_CANCELLED


@pytest.mark.asyncio
async def test_getters_and_not_found(mock_hass, vehicle_id):
    initial = [
        {"id": "rec_lun_12345678", "tipo": "recurrente", "dia_semana": "lunes", "hora": "09:00"},
        {"id": "pun_20251119_87654321", "tipo": "puntual", "datetime": "2025-11-19T15:00:00"},
    ]
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=initial)

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        all_trips = await manager.async_get_all_trips()
        rec_trips = await manager.async_get_recurring_trips()
        pun_trips = await manager.async_get_punctual_trips()
        assert len(all_trips) == 2
        assert len(rec_trips) == 1 and rec_trips[0]["tipo"] == "recurrente"
        assert len(pun_trips) == 1 and pun_trips[0]["tipo"] == "puntual"

        # Not found path
        not_found = await manager.async_get_trip("does_not_exist")
        assert not_found is None


@pytest.mark.asyncio
async def test_add_punctual_trip_happy_path(mock_hass, vehicle_id):
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=[])
    mock_store.async_save = AsyncMock()

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store",
        return_value=mock_store,
    ):
        manager = TripManager(mock_hass, vehicle_id)
        trip_id = await manager.async_add_punctual_trip(
            datetime_str="2025-11-19T15:00:00", km=110.0, kwh=16.5, descripcion="Viaje"
        )
    assert trip_id.startswith("pun_20251119_")
    assert mock_store.async_save.called
    saved_trips = mock_store.async_save.call_args[0][0]
    assert any(t["id"] == trip_id for t in saved_trips)
