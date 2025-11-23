"""Tests TDD para sensores de cálculo (PASO 5 - FASE RED).

Objetivo: Definir especificaciones para 4 nuevos sensores:
1. NextTripSensor - Descripción del próximo viaje
2. NextDeadlineSensor - Fecha/hora del próximo viaje
3. KwhTodaySensor - Suma de kWh necesarios hoy
4. HoursTodaySensor - Horas de carga requeridas (redondeo)

Todos los tests deben FALLAR inicialmente (funciones no implementadas).
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import asyncio


@pytest.fixture
def mock_hass():
    """Fixture con storage simulado en memoria (reutilizado de test_trip_calculations)."""
    hass = MagicMock()
    hass.data = {}
    hass._storage = {}  # Simulación de persistencia
    
    future = asyncio.Future()
    future.set_result(None)
    
    hass.async_create_task = lambda *args, **kwargs: future
    hass.async_add_executor_job = lambda *args, **kwargs: future
    
    # Patch de Store para usar storage simulado
    from homeassistant.helpers.storage import Store
    
    async def patched_async_load(self):
        await hass.async_create_task(None)
        return hass._storage.get(getattr(self, '_mock_key', ''), [])
    
    async def patched_async_save(self, data):
        await hass.async_add_executor_job(lambda: None)
        hass._storage[getattr(self, '_mock_key', '')] = data
    
    Store.async_load = patched_async_load
    Store.async_save = patched_async_save
    
    return hass


@pytest.fixture
def mock_coordinator():
    """Fixture con coordinator simulado."""
    coordinator = MagicMock()
    coordinator.data = {}
    
    # Mock trip_manager con métodos async
    trip_manager = MagicMock()
    
    # Configurar async_get_next_trip para devolver un viaje de prueba
    async def mock_get_next_trip():
        from datetime import datetime
        return {
            "descripcion": "Trabajo",
            "datetime": datetime(2025, 12, 25, 8, 0, 0)
        }
    
    # Configurar otros métodos async
    async def mock_get_kwh_needed_today():
        return 5.5
    
    async def mock_get_hours_needed_today():
        return 2
    
    trip_manager.async_get_next_trip = mock_get_next_trip
    trip_manager.async_get_kwh_needed_today = mock_get_kwh_needed_today
    trip_manager.async_get_hours_needed_today = mock_get_hours_needed_today
    
    coordinator.trip_manager = trip_manager
    return coordinator


@pytest.fixture
def sample_trips():
    """Fixture con datos de viajes de prueba."""
    return {
        "recurring_trips": [
            {
                "id": "rec_lun_abc123",
                "tipo": "recurring",
                "dia_semana": "lunes",
                "hora": "08:00",
                "kwh": 5.5,
                "descripcion": "Trabajo",
                "activo": True,
            }
        ],
        "punctual_trips": [
            {
                "id": "pun_20251122_def456",
                "tipo": "punctual",
                "datetime": "2025-11-22T18:00:00",
                "kwh": 12.0,
                "descripcion": "Viaje largo",
                "estado": "pending",
            }
        ],
    }


class TestNextTripSensor:
    """Test para NextTripSensor - muestra descripción del próximo viaje."""
    
    def test_sensor_exists_and_has_correct_name(self, mock_coordinator):
        """El sensor debe existir con nombre correcto."""
        from custom_components.ev_trip_planner.sensor import NextTripSensor
        
        sensor = NextTripSensor("chispitas", mock_coordinator)
        assert sensor.name == "chispitas next trip"
    
    def test_sensor_shows_next_trip_description(self, mock_coordinator, sample_trips):
        """El sensor debe mostrar la descripción del próximo viaje."""
        from custom_components.ev_trip_planner.sensor import NextTripSensor
        
        # FIX: Configurar coordinator.data con el formato correcto (con next_trip)
        mock_coordinator.data = {
            "recurring_trips": sample_trips["recurring_trips"],
            "punctual_trips": sample_trips["punctual_trips"],
            "next_trip": {
                "descripcion": "Trabajo",
                "datetime": datetime(2025, 12, 25, 8, 0, 0)
            },
            "kwh_today": 5.5,
            "hours_today": 2
        }
        
        sensor = NextTripSensor("chispitas", mock_coordinator)
        
        # FIX: No llamar a async_update, leer directamente desde coordinator.data
        value = sensor.native_value
        
        assert value == "Trabajo"
    
    def test_sensor_shows_no_trip_when_empty(self, mock_coordinator):
        """El sensor debe mostrar 'No trips' cuando no hay viajes."""
        from custom_components.ev_trip_planner.sensor import NextTripSensor
        
        mock_coordinator.data = {"recurring_trips": [], "punctual_trips": []}
        sensor = NextTripSensor("chispitas", mock_coordinator)
        
        assert sensor.native_value == "No trips"


class TestNextDeadlineSensor:
    """Test para NextDeadlineSensor - muestra fecha/hora del próximo viaje."""
    
    def test_sensor_exists_and_has_correct_name(self, mock_coordinator):
        """El sensor debe existir con nombre correcto."""
        from custom_components.ev_trip_planner.sensor import NextDeadlineSensor
        
        sensor = NextDeadlineSensor("chispitas", mock_coordinator)
        assert sensor.name == "chispitas next deadline"
    
    def test_sensor_shows_datetime_object(self, mock_coordinator, sample_trips):
        """El sensor debe devolver un objeto datetime para el próximo viaje."""
        from custom_components.ev_trip_planner.sensor import NextDeadlineSensor
        
        # FIX: Configurar coordinator.data con el formato correcto (con next_trip)
        test_datetime = datetime(2025, 12, 25, 8, 0, 0)
        mock_coordinator.data = {
            "recurring_trips": sample_trips["recurring_trips"],
            "punctual_trips": sample_trips["punctual_trips"],
            "next_trip": {
                "descripcion": "Trabajo",
                "datetime": test_datetime
            },
            "kwh_today": 5.5,
            "hours_today": 2
        }
        
        sensor = NextDeadlineSensor("chispitas", mock_coordinator)
        
        # FIX: No llamar a async_update, leer directamente desde coordinator.data
        value = sensor.native_value
        
        assert isinstance(value, datetime)
        assert value == test_datetime
    
    def test_sensor_shows_none_when_no_trips(self, mock_coordinator):
        """El sensor debe devolver None cuando no hay viajes."""
        from custom_components.ev_trip_planner.sensor import NextDeadlineSensor
        
        mock_coordinator.data = {"recurring_trips": [], "punctual_trips": []}
        sensor = NextDeadlineSensor("chispitas", mock_coordinator)
        
        assert sensor.native_value is None


class TestKwhTodaySensor:
    """Test para KwhTodaySensor - muestra suma de kWh necesarios hoy."""
    
    def test_sensor_exists_and_has_correct_name(self, mock_coordinator):
        """El sensor debe existir con nombre correcto."""
        from custom_components.ev_trip_planner.sensor import KwhTodaySensor
        
        sensor = KwhTodaySensor("chispitas", mock_coordinator)
        assert sensor.name == "chispitas kwh today"
    
    def test_sensor_shows_sum_of_kwh_for_today(self, mock_coordinator, sample_trips):
        """El sensor debe sumar correctamente los kWh de los viajes de hoy."""
        from custom_components.ev_trip_planner.sensor import KwhTodaySensor
        
        mock_coordinator.data = sample_trips
        sensor = KwhTodaySensor("chispitas", mock_coordinator)
        
        # Si hoy es lunes, debería ser 5.5 (Trabajo)
        # Si no es lunes, debería ser 0.0
        value = sensor.native_value
        assert value in [5.5, 0.0]
    
    def test_sensor_shows_zero_when_no_trips_today(self, mock_coordinator):
        """El sensor debe mostrar 0.0 cuando no hay viajes hoy."""
        from custom_components.ev_trip_planner.sensor import KwhTodaySensor
        
        mock_coordinator.data = {"recurring_trips": [], "punctual_trips": []}
        sensor = KwhTodaySensor("chispitas", mock_coordinator)
        
        assert sensor.native_value == 0.0


class TestHoursTodaySensor:
    """Test para HoursTodaySensor - muestra horas de carga requeridas (redondeo)."""
    
    def test_sensor_exists_and_has_correct_name(self, mock_coordinator):
        """El sensor debe existir con nombre correcto."""
        from custom_components.ev_trip_planner.sensor import HoursTodaySensor
        
        sensor = HoursTodaySensor("chispitas", mock_coordinator)
        assert sensor.name == "chispitas hours today"
    
    def test_sensor_shows_integer_hours(self, mock_coordinator, sample_trips):
        """El sensor debe devolver un entero (redondeo hacia arriba)."""
        from custom_components.ev_trip_planner.sensor import HoursTodaySensor
        
        mock_coordinator.data = sample_trips
        sensor = HoursTodaySensor("chispitas", mock_coordinator)
        
        # Si hoy es lunes: ceil(5.5 / 3.6) = ceil(1.53) = 2
        # Si no es lunes: 0
        value = sensor.native_value
        assert value in [2, 0]
        assert isinstance(value, int)
    
    def test_sensor_shows_zero_when_no_trips(self, mock_coordinator):
        """El sensor debe mostrar 0 cuando no hay viajes."""
        from custom_components.ev_trip_planner.sensor import HoursTodaySensor
        
        mock_coordinator.data = {"recurring_trips": [], "punctual_trips": []}
        sensor = HoursTodaySensor("chispitas", mock_coordinator)
        
        assert sensor.native_value == 0