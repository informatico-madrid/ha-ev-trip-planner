"""Simple tests for trip_manager module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.ev_trip_planner.const import (
    DOMAIN,
    TRIP_TYPE_PUNCTUAL,
    TRIP_TYPE_RECURRING,
)
from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def vehicle_id():
    """Return a sample vehicle ID."""
    return "chispitas"


@pytest.mark.asyncio
async def test_initialization(hass, vehicle_id):
    """Test TripManager initialization."""
    manager = TripManager(hass, vehicle_id)

    assert manager.hass == hass
    assert manager.vehicle_id == vehicle_id
    # Storage API: ensure key is namespaced correctly
    assert manager._store.key == f"ev_trip_planner.{vehicle_id}.trips"


@pytest.mark.asyncio
async def test_generate_recurring_trip_id(hass, vehicle_id):
    """Test generating ID for recurring trip."""
    manager = TripManager(hass, vehicle_id)

    trip_data = {"dia_semana": "lunes"}
    trip_id = manager._generate_trip_id(TRIP_TYPE_RECURRING, trip_data)

    assert trip_id.startswith("rec_lun_")
    assert len(trip_id) == 16  # rec_lun_xxxxxxxx


@pytest.mark.asyncio
async def test_generate_punctual_trip_id(hass, vehicle_id):
    """Test generating ID for punctual trip."""
    manager = TripManager(hass, vehicle_id)

    trip_data = {"datetime": "2025-11-19T15:00:00"}
    trip_id = manager._generate_trip_id(TRIP_TYPE_PUNCTUAL, trip_data)

    assert trip_id.startswith("pun_20251119_")
    assert len(trip_id) == 21  # pun_20251119_xxxxxxxx


@pytest.mark.asyncio
async def test_add_recurring_trip_invalid_day(hass, vehicle_id):
    """Test adding recurring trip with invalid day."""
    manager = TripManager(hass, vehicle_id)

    with pytest.raises(ValueError, match="Invalid day of week"):
        await manager.async_add_recurring_trip(
            dia_semana="invalid_day",
            hora="09:00",
            km=24.0,
            kwh=3.6,
            descripcion="Trabajo",
        )


@pytest.mark.asyncio
async def test_add_punctual_trip_invalid_datetime(hass, vehicle_id):
    """Test adding punctual trip with invalid datetime."""
    manager = TripManager(hass, vehicle_id)

    with pytest.raises(ValueError, match="Invalid datetime format"):
        await manager.async_add_punctual_trip(
            datetime_str="invalid-datetime",
            km=110.0,
            kwh=16.5,
            descripcion="Viaje a Toledo",
        )
