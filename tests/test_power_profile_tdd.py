"""Tests TDD para corrección del perfil de carga inteligente.

Este archivo contiene los tests que deben pasar para la corrección del problema
de generación de perfiles de carga que distribuía uniformemente la energía.

Milestone 4: Perfil de Carga Inteligente
"""

import pytest
from datetime import datetime, timedelta

from homeassistant.util import dt as dt_util
from homeassistant.core import HomeAssistant

# Importar desde el módulo local
from custom_components.ev_trip_planner.trip_manager import TripManager
from custom_components.ev_trip_planner.const import DOMAIN


pytestmark = pytest.mark.asyncio


class TestCalcularEnergiaNecesaria:
    """Tests para el cálculo de energía necesaria considerando SOC actual."""
    
    async def test_calcular_energia_necesaria_soc_alto(self, hass):
        """Test: SOC alto (80%), no necesita carga."""
        # Datos de prueba
        trip = {"kwh": 15.0}  # Viaje necesita 30% = 15kWh
        vehicle_config = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "soc_current": 80.0  # 80% = 40kWh
        }
        
        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")
        
        # Resultado esperado
        # energia_objetivo = 15 + 20 = 35kWh
        # energia_actual = 40kWh
        # energia_necesaria = max(0, 35 - 40) = 0kWh
        # horas_carga = 0 / 3.6 = 0h
        
        resultado = await trip_manager.async_calcular_energia_necesaria(trip, vehicle_config)
        
        assert resultado["energia_necesaria_kwh"] == 0.0
        assert resultado["horas_carga_necesarias"] == 0.0
        assert resultado["alerta_tiempo_insuficiente"] is False
    
    async def test_calcular_energia_necesaria_soc_medio(self, hass):
        """Test: SOC medio (40%), necesita carga parcial."""
        # Datos de prueba
        trip = {"kwh": 15.0}  # Viaje necesita 30% = 15kWh
        vehicle_config = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "soc_current": 40.0  # 40% = 20kWh
        }
        
        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")
        
        # Resultado esperado
        # energia_objetivo = 15 + 20 = 35kWh
        # energia_actual = 20kWh
        # energia_necesaria = 35 - 20 = 15kWh
        # horas_carga = 15 / 3.6 = 4.17h
        
        resultado = await trip_manager.async_calcular_energia_necesaria(trip, vehicle_config)
        
        assert resultado["energia_necesaria_kwh"] == 15.0
        assert resultado["horas_carga_necesarias"] == 4.17
        assert resultado["alerta_tiempo_insuficiente"] is False
    
    async def test_calcular_energia_necesaria_soc_bajo(self, hass):
        """Test: SOC bajo (20%), necesita carga completa."""
        # Datos de prueba
        trip = {"kwh": 15.0}  # Viaje necesita 30% = 15kWh
        vehicle_config = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "soc_current": 20.0  # 20% = 10kWh
        }
        
        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")
        
        # Resultado esperado
        # energia_objetivo = 15 + 20 = 35kWh
        # energia_actual = 10kWh
        # energia_necesaria = 35 - 10 = 25kWh
        # horas_carga = 25 / 3.6 = 6.94h
        
        resultado = await trip_manager.async_calcular_energia_necesaria(trip, vehicle_config)
        
        assert resultado["energia_necesaria_kwh"] == 25.0
        assert resultado["horas_carga_necesarias"] == 6.94
        assert resultado["alerta_tiempo_insuficiente"] is False
    
    async def test_calcular_energia_necesaria_tiempo_insuficiente(self, hass):
        """Test: Alerta cuando horas_carga > horas_disponibles."""
        # Datos de prueba
        deadline = dt_util.now() + timedelta(hours=5)  # Solo 5h disponibles
        trip = {
            "kwh": 30.0,  # Viaje grande: 60% = 30kWh
            "datetime": deadline
        }
        vehicle_config = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "soc_current": 20.0  # Necesita 45kWh = 12.5h
        }
        
        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")
        
        # Resultado esperado
        # energia_objetivo = 30 + 20 = 50kWh
        # energia_actual = 10kWh
        # energia_necesaria = 40kWh
        # horas_carga = 40 / 3.6 = 11.11h
        # horas_disponibles = 5h
        # alerta = True
        
        resultado = await trip_manager.async_calcular_energia_necesaria(trip, vehicle_config)
        
        assert resultado["energia_necesaria_kwh"] == 40.0
        assert resultado["horas_carga_necesarias"] == 11.11
        assert resultado["alerta_tiempo_insuficiente"] is True
        assert resultado["horas_disponibles"] == 5.0


class TestGenerarPerfilPotencia:
    """Tests para la generación del perfil de potencia."""
    
    async def test_generar_perfil_potencia_maxima(self, hass):
        """Test: Perfil solo contiene 0W o max_power (3600W)."""
        from unittest.mock import AsyncMock, patch
        
        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")
        
        # Mock _async_load_trips para evitar warnings del Store
        trip_manager._async_load_trips = AsyncMock(return_value=[])
        
        # Generar perfil
        profile = await trip_manager.async_generate_power_profile(
            charging_power_kw=3.6,
            planning_horizon_days=7
        )
        
        # Validaciones
        assert len(profile) == 7 * 24  # 168 horas
        assert all(p == 0.0 or p == 3600.0 for p in profile)  # Solo 0W o 3600W
    
    async def test_generar_perfil_multiples_viajes(self, hass):
        """Test: Perfil con múltiples viajes se acumula correctamente."""
        from unittest.mock import AsyncMock
        
        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")
        
        # Mock _async_load_trips para evitar warnings del Store
        trip_manager._async_load_trips = AsyncMock(return_value=[])
        
        # Generar perfil
        profile = await trip_manager.async_generate_power_profile(
            charging_power_kw=3.6,
            planning_horizon_days=7
        )
        
        # Validaciones
        assert len(profile) == 168
        assert all(p == 0.0 or p == 3600.0 for p in profile)
    
    async def test_generar_perfil_sin_viajes(self, hass):
        """Test: Perfil vacío (todos ceros) cuando no hay viajes."""
        from unittest.mock import AsyncMock
        
        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")
        
        # Mock _async_load_trips para evitar warnings del Store
        trip_manager._async_load_trips = AsyncMock(return_value=[])
        
        # Generar perfil
        profile = await trip_manager.async_generate_power_profile(
            charging_power_kw=3.6,
            planning_horizon_days=7
        )
        
        # Validaciones
        assert len(profile) == 168
        assert all(p == 0.0 for p in profile)  # Todos ceros


class TestGetVehicleSOC:
    """Tests para obtener el SOC del vehículo."""
    
    async def test_get_vehicle_soc_sensor_no_disponible(self, hass):
        """Test: Manejar sensor SOC unavailable."""
        # Simular sensor unavailable
        # Configurar vehículo con sensor que no existe
        hass.data[DOMAIN] = {
            "test_vehicle": {
                "soc_sensor": "sensor.soc_no_existe"
            }
        }
        
        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")
        
        soc = await trip_manager.async_get_vehicle_soc("test_vehicle")
        
        # Debe retornar 0.0 y loggear warning
        assert soc == 0.0
    
    async def test_get_vehicle_soc_sensor_valido(self):
        """Test: Obtener SOC válido desde sensor."""
        from unittest.mock import MagicMock
        
        # Crear hass mock completamente nuevo para evitar problemas con el fixture
        hass = MagicMock()
        hass.data = {DOMAIN: {"test_vehicle": {"soc_sensor": "sensor.soc_valido"}}}
        
        # Crear un mock para el sensor con estado 65.0
        mock_state = MagicMock()
        mock_state.state = "65.0"
        
        # Mock para hass.states.get
        hass.states.get = MagicMock(return_value=mock_state)
        
        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")
        
        # Obtener SOC
        soc = await trip_manager.async_get_vehicle_soc("test_vehicle")
        
        # Debe retornar 65.0
        assert soc == 65.0
    
    async def test_get_vehicle_soc_sensor_no_configurado(self, hass):
        """Test: Manejar vehículo sin sensor SOC configurado."""
        # Vehículo sin soc_sensor en configuración
        hass.data[DOMAIN] = {
            "test_vehicle": {}
        }

        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")

        soc = await trip_manager.async_get_vehicle_soc("test_vehicle")

        # Debe retornar 0.0 y loggear warning
        assert soc == 0.0


class TestCalcularEnergiaKwh:
    """Tests for the energy calculation utility function."""

    def test_calcular_energia_kwh_basic(self):
        """Test basic energy calculation: 100km * 0.15 kWh/km = 15kWh."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        result = calcular_energia_kwh(100.0, 0.15)
        assert result == 15.0

    def test_calcular_energia_kwh_precision(self):
        """Test precision to 3 decimal places."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        # 50km * 0.123 kWh/km = 6.15 kWh
        result = calcular_energia_kwh(50.0, 0.123)
        assert result == 6.15

    def test_calcular_energia_kwh_zero_distance(self):
        """Test zero distance returns 0 energy."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        result = calcular_energia_kwh(0.0, 0.15)
        assert result == 0.0

    def test_calcular_energia_kwh_zero_consumption(self):
        """Test zero consumption returns 0 energy."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        result = calcular_energia_kwh(100.0, 0.0)
        assert result == 0.0

    def test_calcular_energia_kwh_negative_distance_raises(self):
        """Test negative distance raises ValueError."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        with pytest.raises(ValueError, match="Distance cannot be negative"):
            calcular_energia_kwh(-10.0, 0.15)

    def test_calcular_energia_kwh_negative_consumption_raises(self):
        """Test negative consumption raises ValueError."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        with pytest.raises(ValueError, match="Consumption cannot be negative"):
            calcular_energia_kwh(100.0, -0.15)

    def test_calcular_energia_kwh_with_trip_km(self):
        """Test energy calculation using km from trip data."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        # 25km trip * 0.18 kWh/km = 4.5 kWh
        trip_km = 25.0
        consumption = 0.18
        result = calcular_energia_kwh(trip_km, consumption)
        assert result == 4.5