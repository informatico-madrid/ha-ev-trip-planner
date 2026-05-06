"""Tests for trip calculation logic - Milestone 2."""

import pytest
import asyncio
from datetime import datetime, timedelta
from freezegun import freeze_time
from unittest.mock import MagicMock


from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def mock_hass():
    """Fixture que crea un mock funcional de Home Assistant con storage simulado en memoria."""
    # Storage simulado en memoria - compartido entre todas las instancias de Store
    _storage_data = {}

    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()

    # Mock config entry con vehicle_name y charging_power_kw (para que async_entries lo encuentre)
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_id"
    mock_entry.data = {"vehicle_name": "test_vehicle", "charging_power_kw": 3.6}
    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    # Future lista para simulate async
    future = asyncio.Future()
    future.set_result(None)

    async def mock_async_create_task(*args, **kwargs):
        return future

    async def mock_async_add_executor_job(*args, **kwargs):
        return future

    hass.async_create_task = mock_async_create_task
    hass.async_add_executor_job = mock_async_add_executor_job

    # Patch de Store para usar storage en memoria
    from homeassistant.helpers.storage import Store

    async def mock_async_load(self):
        key = getattr(self, "_mock_key", None)
        if key is None:
            return []
        await asyncio.sleep(0)  # Simula async
        return _storage_data.get(key, [])

    async def mock_async_save(self, data):
        key = getattr(self, "_mock_key", None)
        if key is not None:
            await asyncio.sleep(0)  # Simula async
            _storage_data[key] = data

    def mock_init(self, hass, version, key, private=False):
        self._mock_key = key
        original_store_init(self, hass, version, key, private)

    # Guardar el original
    original_store_init = Store.__init__

    # Aplicar patches
    Store.__init__ = mock_init
    Store.async_load = mock_async_load
    Store.async_save = mock_async_save

    yield hass

    # Cleanup - restaurar original
    Store.__init__ = original_store_init


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
            dia_semana=today_spanish, hora="12:00", km=25, kwh=3.75, descripcion="Trabajo"
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
            dia_semana=today_spanish, hora="08:00", km=25, kwh=11.25, descripcion="Trabajo"
        )

        # Calculate hours needed (uses default charging power from mock config)
        hours = await mgr.async_get_hours_needed_today()

        # ceil(11.25 / 3.6) = ceil(3.125) = 4
        assert hours == 4
