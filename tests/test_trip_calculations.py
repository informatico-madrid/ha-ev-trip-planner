"""Tests for trip calculation logic - Milestone 2."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.util import dt as dt_util


@pytest.fixture
def mock_hass():
    """
    Fixture que crea un mock funcional de Home Assistant con storage simulado en memoria.
    
    ## PROBLEMA RESUELTO:
    
    El fixture anterior usaba una única Future con resultado None, lo que causaba:
    - "No trips found for vehicle test_vehicle" (async_load() siempre devolvía None)
    - RuntimeWarning: coroutine 'Store._async_load' was never awaited
    
    ## SOLUCIÓN: Storage simulado en memoria
    
    Creamos un diccionario interno `_storage` que simula el almacenamiento persistente.
    Cada vez que se llama a `Store.async_load()`, devuelve los datos guardados.
    Cada vez que se llama a `Store.async_save(data)`, actualiza el diccionario.
    
    ## IMPLEMENTACIÓN:
    
    1. `hass._storage = {}` - Diccionario interno para simular persistencia
    2. `hass.async_create_task` - Devuelve Future awaitable con .done()
    3. `hass.async_add_executor_job` - Para storage.async_save()
    4. Patch de `Store.async_load` para que lea de `hass._storage`
    5. Patch de `Store.async_save` para que escriba en `hass._storage`
    
    ## USO EN TESTS:
    
    ```python
    def test_algo(mock_hass):
        # Los datos se persisten automáticamente entre llamadas
        await mgr.async_add_recurring_trip(...)  # Guarda en storage
        trips = await mgr.async_get_all_trips()  # Lee desde storage
    ```
    """
    hass = MagicMock()
    hass.data = {}
    hass._storage = {}  # Simulación de almacenamiento persistente
    
    # CRÍTICO: asyncio.Future es awaitable y tiene .done()
    future = asyncio.Future()
    future.set_result(None)
    
    hass.async_create_task = lambda *args, **kwargs: future
    hass.async_add_executor_job = lambda *args, **kwargs: future
    
    # Patch de Store para usar nuestro storage simulado
    from homeassistant.helpers.storage import Store
    
    original_init = Store.__init__
    original_async_load = Store.async_load
    original_async_save = Store.async_save
    
    def patched_init(self, hass, version, key, private=False):
        """Patch de Store.__init__ que acepta el argumento 'private' (nuevo en HA)."""
        original_init(self, hass, version, key, private)
        self._mock_key = key
    
    async def patched_async_load(self):
        """Lee desde el storage simulado en memoria."""
        await hass.async_create_task(None)  # Simula async
        return hass._storage.get(getattr(self, '_mock_key', ''), [])
    
    async def patched_async_save(self, data):
        """Guarda en el storage simulado en memoria."""
        await hass.async_add_executor_job(lambda: None)  # Simula async
        hass._storage[getattr(self, '_mock_key', '')] = data
    
    Store.__init__ = patched_init
    Store.async_load = patched_async_load
    Store.async_save = patched_async_save
    
    return hass


@pytest.mark.asyncio
async def test_expand_recurring_trips_next_7_days(mock_hass):
    """Test that recurring trips expand to concrete dates for next 7 days."""
    from custom_components.ev_trip_planner.trip_manager import TripManager
    
    # Create mock TripManager with a recurring trip
    mgr = TripManager(mock_hass, vehicle_id="test_vehicle")
    
    # Add a recurring trip (Monday 08:00)
    await mgr.async_add_recurring_trip(
        dia_semana="lunes",
        hora="08:00",
        km=25,
        kwh=3.75,
        descripcion="Trabajo"
    )
    
    # Expand for next 7 days
    expanded = await mgr.async_expand_recurring_trips(days=7)
    
    # Should have at least 1 Monday in next 7 days
    assert len(expanded) >= 1
    assert expanded[0]["descripcion"] == "Trabajo"
    assert "datetime" in expanded[0]
    assert expanded[0]["datetime"].hour == 8
    assert expanded[0]["datetime"].minute == 0


@pytest.mark.asyncio
async def test_get_next_trip_with_mixed_trips(mock_hass):
    """Test that next trip is correctly identified with mixed recurring and punctual trips."""
    from custom_components.ev_trip_planner.trip_manager import TripManager
    
    mgr = TripManager(mock_hass, vehicle_id="test_vehicle")
    
    # Get current day of week in Spanish
    day_map = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
    today_weekday = datetime.now().weekday()
    today_spanish = day_map[today_weekday]
    
    # Add recurring trip for today at 23:00 (future time to ensure it's after current time)
    await mgr.async_add_recurring_trip(
        dia_semana=today_spanish,
        hora="23:00",
        km=25,
        kwh=3.75,
        descripcion="Trabajo"
    )
    
    # Add punctual trip for tomorrow at 14:00
    tomorrow = datetime.now() + timedelta(days=1)
    await mgr.async_add_punctual_trip(
        datetime_str=tomorrow.strftime("%Y-%m-%dT14:00:00"),
        km=50,
        kwh=7.5,
        descripcion="Viaje largo"
    )
    
    # Get next trip - should be today's recurring trip
    next_trip = await mgr.async_get_next_trip()
    
    assert next_trip is not None
    assert next_trip["descripcion"] == "Trabajo"
    assert next_trip["datetime"].hour == 23


@pytest.mark.asyncio
async def test_get_next_trip_empty_returns_none(mock_hass):
    """Test that next trip returns None when no trips exist."""
    from custom_components.ev_trip_planner.trip_manager import TripManager
    
    mgr = TripManager(mock_hass, vehicle_id="test_vehicle")
    
    # No trips added
    next_trip = await mgr.async_get_next_trip()
    
    assert next_trip is None


@pytest.mark.asyncio
async def test_get_kwh_needed_today_multiple_trips(mock_hass):
    """Test that kWh needed today sums correctly with multiple trips."""
    from custom_components.ev_trip_planner.trip_manager import TripManager

    mgr = TripManager(mock_hass, vehicle_id="test_vehicle")
    
    # Get current day of week in Spanish
    day_map = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
    today_weekday = datetime.now().weekday()
    today_spanish = day_map[today_weekday]
    
    # Add two trips for today
    await mgr.async_add_recurring_trip(
        dia_semana=today_spanish,
        hora="08:00",
        km=25,
        kwh=3.75,
        descripcion="Trabajo"
    )
    
    await mgr.async_add_punctual_trip(
        datetime_str=datetime.now().strftime("%Y-%m-%dT14:00:00"),
        km=50,
        kwh=7.5,
        descripcion="Compras"
    )
    
    # Get kWh needed today
    kwh_today = await mgr.async_get_kwh_needed_today()
    
    assert kwh_today == 11.25  # 3.75 + 7.5


@pytest.mark.asyncio
async def test_get_kwh_needed_today_no_trips_returns_zero(mock_hass):
    """Test that kWh needed today returns 0 when no trips exist."""
    from custom_components.ev_trip_planner.trip_manager import TripManager

    mgr = TripManager(mock_hass, vehicle_id="test_vehicle")
    
    # No trips added
    kwh_today = await mgr.async_get_kwh_needed_today()
    
    assert kwh_today == 0.0


@pytest.mark.asyncio
async def test_get_hours_needed_today_rounds_up(mock_hass):
    """Test that hours needed today rounds up correctly."""
    from custom_components.ev_trip_planner.trip_manager import TripManager

    mgr = TripManager(mock_hass, vehicle_id="test_vehicle")
    
    # Get current day of week in Spanish
    day_map = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
    today_weekday = datetime.now().weekday()
    today_spanish = day_map[today_weekday]
    
    # Add trip requiring 11.25 kWh for today
    await mgr.async_add_recurring_trip(
        dia_semana=today_spanish,
        hora="08:00",
        km=25,
        kwh=11.25,
        descripcion="Trabajo"
    )
    
    # Calculate hours needed with 3.6kW charging
    hours = await mgr.async_get_hours_needed_today(charging_power_kw=3.6)
    
    # ceil(11.25 / 3.6) = ceil(3.125) = 4
    assert hours == 4


@pytest.mark.asyncio
async def test_timezone_handling_uses_local_time(mock_hass):
    """Test that timezone handling uses local time correctly."""
    from custom_components.ev_trip_planner.trip_manager import TripManager

    mgr = TripManager(mock_hass, vehicle_id="test_vehicle")
    
    # Add trip at 08:00
    await mgr.async_add_recurring_trip(
        dia_semana="lunes",
        hora="08:00",
        km=25,
        kwh=3.75,
        descripcion="Trabajo"
    )
    
    # Get expanded trips
    expanded = await mgr.async_expand_recurring_trips(days=7)
    
    # Verify time is local (not UTC)
    trip_time = expanded[0]["datetime"]
    assert trip_time.hour == 8
    assert trip_time.minute == 0
    # Should be in local timezone (CET/CEST)
    assert trip_time.tzinfo is not None


@pytest.mark.asyncio
async def test_combine_recurring_and_punctual_trips(mock_hass):
    """Test that recurring and punctual trips are combined and sorted correctly."""
    from custom_components.ev_trip_planner.trip_manager import TripManager

    mgr = TripManager(mock_hass, vehicle_id="test_vehicle")
    
    # Add punctual trip for tomorrow
    tomorrow = datetime.now() + timedelta(days=1)
    await mgr.async_add_punctual_trip(
        datetime_str=tomorrow.strftime("%Y-%m-%dT14:00:00"),
        km=50,
        kwh=7.5,
        descripcion="Viaje largo"
    )
    
    # Add recurring trip for today
    await mgr.async_add_recurring_trip(
        dia_semana="lunes",
        hora="08:00",
        km=25,
        kwh=3.75,
        descripcion="Trabajo"
    )
    
    # Get all trips expanded
    all_trips = await mgr.async_get_all_trips_expanded()
    
    # Should have at least 2 trips
    assert len(all_trips) >= 2
    
    # Should be sorted by datetime
    for i in range(len(all_trips) - 1):
        assert all_trips[i]["datetime"] <= all_trips[i + 1]["datetime"]