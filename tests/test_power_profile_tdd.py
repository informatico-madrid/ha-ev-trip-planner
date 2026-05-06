"""Tests TDD para corrección del perfil de carga inteligente.

Este archivo contiene los tests que deben pasar para la corrección del problema
de generación de perfiles de carga que distribuía uniformemente la energía.

Milestone 4: Perfil de Carga Inteligente
"""

import pytest
from datetime import timedelta

from homeassistant.util import dt as dt_util

# Importar desde el módulo local
from custom_components.ev_trip_planner.trip_manager import TripManager
from custom_components.ev_trip_planner.const import DOMAIN


class TestCalcularEnergiaNecesaria:
    """Tests para el cálculo de energía necesaria considerando SOC actual."""

    pytestmark = pytest.mark.asyncio

    async def test_calcular_energia_necesaria_soc_alto(self, hass):
        """Test: SOC alto (80%), no necesita carga."""
        # Datos de prueba
        trip = {"kwh": 15.0}  # Viaje necesita 15kWh
        vehicle_config = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "soc_current": 80.0,  # 80% = 40kWh
        }

        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")

        # Resultado esperado (sin buffer hardcodeado)
        # energia_objetivo = 15kWh (solo energía del viaje)
        # energia_actual = 40kWh
        # energia_necesaria = max(0, 15 - 40) = 0kWh
        # horas_carga = 0 / 3.6 = 0h

        resultado = await trip_manager.async_calcular_energia_necesaria(
            trip, vehicle_config
        )

        assert resultado["energia_necesaria_kwh"] == 0.0
        assert resultado["horas_carga_necesarias"] == 0.0
        assert resultado["alerta_tiempo_insuficiente"] is False

    async def test_calcular_energia_necesaria_soc_medio(self, hass):
        """Test: SOC medio (40%), no necesita carga (energía suficiente)."""
        # Datos de prueba
        trip = {"kwh": 15.0}  # Viaje necesita 15kWh
        vehicle_config = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "soc_current": 40.0,  # 40% = 20kWh
        }

        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")

        # Resultado esperado (sin buffer hardcodeado)
        # energia_objetivo = 15kWh (solo energía del viaje)
        # energia_actual = 20kWh
        # energia_necesaria = max(0, 15 - 20) = 0kWh
        # horas_carga = 0 / 3.6 = 0h

        resultado = await trip_manager.async_calcular_energia_necesaria(
            trip, vehicle_config
        )

        assert resultado["energia_necesaria_kwh"] == 0.0
        assert resultado["horas_carga_necesarias"] == 0.0
        assert resultado["alerta_tiempo_insuficiente"] is False

    async def test_calcular_energia_necesaria_soc_bajo(self, hass):
        """Test: SOC bajo (20%), necesita carga parcial."""
        # Datos de prueba
        trip = {"kwh": 15.0}  # Viaje necesita 15kWh
        vehicle_config = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "soc_current": 20.0,  # 20% = 10kWh
        }

        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")

        # Resultado esperado (con safety_margin=10% por defecto)
        # energia_objetivo = 15kWh (solo energía del viaje)
        # energia_actual = 10kWh
        # energia_necesaria raw = max(0, 15 - 10) = 5kWh
        # With safety_margin=10%: energia_final = 5 * 1.10 = 5.5kWh
        # horas_carga = 5.5 / 3.6 = 1.53h

        resultado = await trip_manager.async_calcular_energia_necesaria(
            trip, vehicle_config
        )

        assert resultado["energia_necesaria_kwh"] == 5.5
        assert resultado["horas_carga_necesarias"] == round(5.5 / 3.6, 2)
        assert resultado["alerta_tiempo_insuficiente"] is False

    async def test_calcular_energia_necesaria_tiempo_insuficiente(self, hass):
        """Test: Alerta cuando horas_carga > horas_disponibles."""
        # Datos de prueba
        deadline = dt_util.now() + timedelta(hours=5)  # Solo 5h disponibles
        trip = {
            "kwh": 30.0,  # Viaje grande: 30kWh
            "datetime": deadline,
        }
        vehicle_config = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "soc_current": 20.0,  # 20% = 10kWh
        }

        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")

        # Resultado esperado (con safety_margin=10% por defecto)
        # energia_objetivo = 30kWh (solo energía del viaje)
        # energia_actual = 10kWh
        # energia_necesaria raw = max(0, 30 - 10) = 20kWh
        # With safety_margin=10%: energia_final = 20 * 1.10 = 22kWh
        # horas_carga = 22 / 3.6 = 6.11h
        # horas_disponibles = 5h
        # alerta = True (6.11 > 5)

        resultado = await trip_manager.async_calcular_energia_necesaria(
            trip, vehicle_config
        )

        assert resultado["energia_necesaria_kwh"] == 22.0
        assert resultado["horas_carga_necesarias"] == round(22.0 / 3.6, 2)
        assert resultado["alerta_tiempo_insuficiente"] is True
        assert resultado["horas_disponibles"] == 5.0


class TestGenerarPerfilPotencia:
    """Tests para la generación del perfil de potencia."""

    pytestmark = pytest.mark.asyncio

    async def test_generar_perfil_potencia_maxima(self, hass):
        """Test: Perfil solo contiene 0W o max_power (3600W)."""
        from unittest.mock import AsyncMock

        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")

        # Mock _async_load_trips para evitar warnings del Store
        trip_manager._async_load_trips = AsyncMock(return_value=[])

        # Generar perfil
        profile = await trip_manager.async_generate_power_profile(
            charging_power_kw=3.6, planning_horizon_days=7
        )

        # Validaciones
        assert len(profile) == 7 * 24  # 168 horas
        assert all(p == 0.0 or p == 3600.0 for p in profile)  # Solo 0W o 3600W

    async def test_generar_perfil_multiples_viajes(self, hass):
        """Test: Perfil con múltiples viajes se acumula correctamente."""
        from unittest.mock import AsyncMock

        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")

        # Mock _async_load_trips para devolver viajes reales
        trip_manager._async_load_trips = AsyncMock(
            return_value=[
                {
                    "id": "test1",
                    "tipo": "puntual",
                    "datetime": "2026-05-10T08:00",
                    "km": 50,
                    "kwh": 7.5,
                    "descripcion": "test trip",
                    "status": "pendiente",
                },
                {
                    "id": "test2",
                    "tipo": "puntual",
                    "datetime": "2026-05-10T18:00",
                    "km": 30,
                    "kwh": 4.5,
                    "descripcion": "test trip 2",
                    "status": "pendiente",
                },
            ]
        )

        # Generar perfil
        profile = await trip_manager.async_generate_power_profile(
            charging_power_kw=3.6, planning_horizon_days=7
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
            charging_power_kw=3.6, planning_horizon_days=7
        )

        # Validaciones
        assert len(profile) == 168
        assert all(p == 0.0 for p in profile)  # Todos ceros


class TestGetVehicleSOC:
    """Tests para obtener el SOC del vehículo."""

    pytestmark = pytest.mark.asyncio

    async def test_get_vehicle_soc_sensor_no_disponible(self, hass):
        """Test: Manejar sensor SOC unavailable."""
        # Simular sensor unavailable
        # Configurar vehículo con sensor que no existe
        hass.data[DOMAIN] = {"test_vehicle": {"soc_sensor": "sensor.soc_no_existe"}}

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

        # Configurar config_entries.async_entries para simular la nueva implementación
        mock_entry = MagicMock()
        mock_entry.data = {
            "vehicle_name": "test_vehicle",
            "soc_sensor": "sensor.soc_valido",
        }
        hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

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
        hass.data[DOMAIN] = {"test_vehicle": {}}

        # Crear TripManager para probar
        trip_manager = TripManager(hass, "test_vehicle")

        soc = await trip_manager.async_get_vehicle_soc("test_vehicle")

        # Debe retornar 0.0 y loggear warning
        assert soc == 0.0


class TestCalcularEnergiaKwh:
    """Pruebas para la función utilitaria de cálculo de energía."""

    def test_calcular_energia_kwh_basic(self):
        """Cálculo básico de energía: 100km * 0.15 kWh/km = 15kWh."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        result = calcular_energia_kwh(100.0, 0.15)
        assert result == 15.0

    def test_calcular_energia_kwh_precision(self):
        """Prueba precisión a 3 decimales."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        # 50km * 0.123 kWh/km = 6.15 kWh
        result = calcular_energia_kwh(50.0, 0.123)
        assert result == 6.15

    def test_calcular_energia_kwh_zero_distance(self):
        """Distancia cero devuelve 0 energía."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        result = calcular_energia_kwh(0.0, 0.15)
        assert result == 0.0

    def test_calcular_energia_kwh_zero_consumption(self):
        """Consumo cero devuelve 0 energía."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        result = calcular_energia_kwh(100.0, 0.0)
        assert result == 0.0

    def test_calcular_energia_kwh_negative_distance_raises(self):
        """Distancia negativa genera ValueError."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        with pytest.raises(ValueError, match="Distance cannot be negative"):
            calcular_energia_kwh(-10.0, 0.15)

    def test_calcular_energia_kwh_negative_consumption_raises(self):
        """Consumo negativo genera ValueError."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        with pytest.raises(ValueError, match="Consumption cannot be negative"):
            calcular_energia_kwh(100.0, -0.15)

    def test_calcular_energia_kwh_with_trip_km(self):
        """Cálculo de energía usando km desde datos del viaje."""
        from custom_components.ev_trip_planner.utils import calcular_energia_kwh

        # 25km trip * 0.18 kWh/km = 4.5 kWh
        trip_km = 25.0
        consumption = 0.18
        result = calcular_energia_kwh(trip_km, consumption)
        assert result == 4.5
