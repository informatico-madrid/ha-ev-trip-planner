"""Tests for trip calculation logic - Milestone 2."""

from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.mark.asyncio
async def test_get_next_trip_with_mixed_trips(mock_hass):
    """Test that next trip is correctly identified with mixed recurring and punctual trips."""

    mgr = TripManager(mock_hass, vehicle_id="test_vehicle")

    # Get day of week in Spanish - use day AFTER tomorrow to ensure it's always in future
    day_map = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
    # Use day after tomorrow to avoid time-dependent failures near midnight
    future_day_offset = 2  # day after tomorrow
    future_date = datetime.now() + timedelta(days=future_day_offset)
    future_weekday = future_date.weekday()
    future_day_spanish = day_map[future_weekday]

    # Add recurring trip for day after tomorrow at 14:00 (guaranteed in future)
    await mgr.async_add_recurring_trip(
        dia_semana=future_day_spanish,
        hora="14:00",
        km=25,
        kwh=3.75,
        descripcion="Trabajo",
    )

    # Add punctual trip for tomorrow at 14:00 (closer than recurring trip)
    tomorrow = datetime.now() + timedelta(days=1)
    await mgr.async_add_punctual_trip(
        datetime_str=tomorrow.strftime("%Y-%m-%dT14:00"),
        km=50,
        kwh=7.5,
        descripcion="Viaje largo",
    )

    # Get next trip - should be tomorrow's punctual trip (closer in time)
    next_trip = await mgr.async_get_next_trip()

    assert next_trip is not None
    assert next_trip["descripcion"] == "Viaje largo"


@pytest.mark.asyncio
async def test_get_next_trip_empty_returns_none(mock_hass):
    """Test that next trip returns None when no trips exist."""

    mgr = TripManager(mock_hass, vehicle_id="test_vehicle")

    # No trips added
    next_trip = await mgr.async_get_next_trip()

    assert next_trip is None


@pytest.mark.asyncio
async def test_get_kwh_needed_today_multiple_trips(mock_hass):
    """Test that kWh needed today sums correctly with multiple trips."""

    mgr = TripManager(mock_hass, vehicle_id="test_vehicle")

    # Get current day of week in Spanish
    day_map = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
    frozen_time = datetime(2025, 5, 5, 10, 0, 0)  # Monday = "lunes"
    with freeze_time(frozen_time):
        today_weekday = frozen_time.weekday()
        today_spanish = day_map[today_weekday]

        # Add two trips for today
        await mgr.async_add_recurring_trip(
            dia_semana=today_spanish,
            hora="12:00",
            km=25,
            kwh=3.75,
            descripcion="Trabajo",
        )

        await mgr.async_add_punctual_trip(
            datetime_str=frozen_time.strftime("%Y-%m-%dT14:00"),
            km=50,
            kwh=7.5,
            descripcion="Compras",
        )

        # Get kWh needed today (must be inside freeze_time so datetime.now() matches)
        kwh_today = await mgr.async_get_kwh_needed_today()

        assert kwh_today == 11.25  # 3.75 + 7.5


@pytest.mark.asyncio
async def test_get_kwh_needed_today_no_trips_returns_zero(mock_hass):
    """Test that kWh needed today returns 0 when no trips exist."""

    mgr = TripManager(mock_hass, vehicle_id="test_vehicle")

    # No trips added
    kwh_today = await mgr.async_get_kwh_needed_today()

    assert kwh_today == 0.0


@pytest.mark.asyncio
async def test_get_hours_needed_today_rounds_up(mock_hass):
    """Test that hours needed today rounds up correctly."""

    mgr = TripManager(mock_hass, vehicle_id="test_vehicle")

    # Get current day of week in Spanish
    day_map = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
    frozen_time = datetime(2025, 5, 5, 10, 0, 0)  # Monday = "lunes"
    today_weekday = frozen_time.weekday()
    today_spanish = day_map[today_weekday]

    with freeze_time(frozen_time):
        # Add trip requiring 11.25 kWh for today
        await mgr.async_add_recurring_trip(
            dia_semana=today_spanish,
            hora="08:00",
            km=25,
            kwh=11.25,
            descripcion="Trabajo",
        )

        # Calculate hours needed (uses default charging power from mock config)
        hours = await mgr.async_get_hours_needed_today()

        # ceil(11.25 / 3.6) = ceil(3.125) = 4
        assert hours == 4
