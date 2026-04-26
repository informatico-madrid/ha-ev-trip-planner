"""
Test de integración para el bug SOC 100% que aún programa carga en sensores.

Este test verifica que cuando un coche está al 100% SOC:
1. def_total_hours debe ser [0, 0, 0, 0, 0] (no [2, 0, 0, 0, 0])
2. P_deferrable_nom debe ser [0.0, 0.0, 0.0, 0.0, 0.0] (no [3400.0, 3400.0, 3400.0, 3400.0, 3400.0])
3. P_deferrable debe tener solo 0.0 en todas las horas para todos los viajes

Reproduce el comportamiento exacto reportado por el usuario.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.calculations import calculate_energy_needed


class TestSOC100ChargingBugSensores:
    """Test que reproduce el bug de carga cuando SOC está al 100% en los sensores."""

    def setup_method(self):
        """Configuración inicial para cada test."""
        # Mock de la entrada de configuración
        self.mock_entry = MagicMock()
        self.mock_entry.data = {
            "soc_sensor": "sensor.ev_battery_soc",
            "charging_power_kw": 3.4,
            "battery_capacity_kwh": 50.0,
            "planning_horizon_days": 7,
            "max_deferrable_loads": 5,
            "safety_margin_percent": 10.0
        }
        self.mock_entry.entry_id = "test_entry"

        # Mock del Home Assistant
        self.mock_hass = MagicMock()
        self.mock_hass.data = {}

        # Mock del sensor SOC (al 100%)
        self.mock_soc_sensor = MagicMock()
        self.mock_soc_sensor.state = 100.0  # ¡100% SOC!
        self.mock_hass.states.get.return_value = self.mock_soc_sensor

    async def test_soc_100_deberia_tener_0_horas_en_todos_sensores(self):
        """
        Test principal que reproduce el bug reportado por el usuario:

        El usuario reportó:
        - number_of_deferrable_loads: 5
        - def_total_hours: [2, 0, 0, 0, 0] ← ¡Esto debería ser [0, 0, 0, 0, 0]!
        - P_deferrable_nom: [3400.0, 3400.0, 3400.0, 3400.0, 3400.0] ← ¡Esto debería ser [0.0, 0.0, 0.0, 0.0, 0.0]!

        Condiciones:
        - Coche al 100% SOC
        - 5 viajes recurrentes
        - Viaje 1: 30kWh (el que causa el bug)
        - Batería de 50 kWh
        - Margen de seguridad del 10%

        Resultado esperado:
        def_total_hours: [0, 0, 0, 0, 0]
        P_deferrable_nom: [0.0, 0.0, 0.0, 0.0, 0.0]
        """
        # Crear 5 viajes recurrentes como reporta el usuario
        trips = [
            {
                "id": "viaje_1",
                "tipo": "recurring",
                "dia_semana": "1",  # Martes
                "hora": "09:00",
                "kwh": 30.0,  # El viaje que causa el bug
                "descripcion": "Viaje largo"
            },
            {
                "id": "viaje_2",
                "tipo": "recurring",
                "dia_semana": "2",  # Miércoles
                "hora": "14:00",
                "kwh": 15.0,
                "descripcion": "Viaje medio"
            },
            {
                "id": "viaje_3",
                "tipo": "recurring",
                "dia_semana": "3",  # Jueves
                "hora": "18:00",
                "kwh": 20.0,
                "descripcion": "Viaje tarde"
            },
            {
                "id": "viaje_4",
                "tipo": "recurring",
                "dia_semana": "4",  # Viernes
                "hora": "08:00",
                "kwh": 25.0,
                "descripcion": "Viaje temprano"
            },
            {
                "id": "viaje_5",
                "tipo": "recurring",
                "dia_semana": "5",  # Sábado
                "hora": "10:00",
                "kwh": 10.0,
                "descripcion": "Viaje corto"
            }
        ]

        # Configuración
        battery_capacity = 50.0
        soc_current = 100.0  # SOC al 100% - ¡ESTO DEBERÍA EVITAR CARGA!
        charging_power_kw = 3.4
        safety_margin = 10.0

        # Calcular energía necesaria para cada viaje individualmente
        print("=== CÁLCULO INDIVIDUAL DE CADA VIAJE ===")
        for i, trip in enumerate(trips):
            energy_info = calculate_energy_needed(
                trip=trip,
                battery_capacity_kwh=battery_capacity,
                soc_current=soc_current,
                charging_power_kw=charging_power_kw,
                safety_margin_percent=safety_margin
            )
            print(f"Viaje {i+1} ({trip['kwh']} kWh): "
                  f"Energía necesaria = {energy_info['energia_necesaria_kwh']} kWh, "
                  f"Horas de carga = {energy_info['horas_carga_necesarias']}")

        # El cálculo individual muestra que todos los viajes deberían tener 0 horas
        # porque con SOC 100% (50 kWh) y cualquier viaje ≤ 50 kWh + 10% = 55 kWh,
        # no se necesita carga adicional.

        # Ahora vamos a simular lo que el EMHAdapter haría con estos viajes
        adapter = EMHASSAdapter(self.mock_hass, self.mock_entry)

        # Mockear el almacenamiento
        mock_store = AsyncMock()
        mock_store.async_save = AsyncMock()
        adapter._store = mock_store

        # Mockear presencia monitor
        adapter._presence_monitor = None

        # Mockear _get_current_soc para que devuelva 100%
        async def mock_get_current_soc():
            return 100.0

        adapter._get_current_soc = mock_get_current_soc

        # Mockear _get_hora_regreso
        async def mock_get_hora_regreso():
            return None

        adapter._get_hora_regreso = mock_get_hora_regreso

        # Publicar todos los viajes
        print("\n=== PUBLICANDO TODOS LOS VIAJES ===")
        for trip in trips:
            result = await adapter.async_publish_deferrable_load(trip)
            print(f"Viaje {trip['id']}:Publicado = {result}")

        # Verificar los parámetros en caché (esto es lo que se envía a EMHASS)
        per_trip_params = getattr(adapter, "_cached_per_trip_params", {})

        print("\n=== VERIFICANDO PARÁMETROS EN CACHÉ (LO QUE SE ENVÍA A EMHASS) ===")

        # Verificar cada viaje
        for i, trip in enumerate(trips):
            trip_id = trip["id"]
            if trip_id in per_trip_params:
                params = per_trip_params[trip_id]
                print(f"Viaje {i+1} ({trip['kwh']} kWh):")
                print(f"  def_total_hours: {params.get('def_total_hours', 'NOT_FOUND')}")
                print(f"  P_deferrable_nom: {params.get('P_deferrable_nom', 'NOT_FOUND')}")

                # ESTAS SON LAS ASERCIONES QUE DEBERÍAN FALLAR POR EL BUG
                # Con SOC 100%, TODOS los viajes deben tener 0 horas y 0W
                assert params.get('def_total_hours') == 0, \
                    f"Viaje {trip['kwh']}kWh con SOC 100% debe tener def_total_hours=0, pero tiene {params.get('def_total_hours')}"

                assert params.get('P_deferrable_nom') == 0.0, \
                    f"Viaje {trip['kwh']}kWh con SOC 100% debe tener P_deferrable_nom=0.0, pero tiene {params.get('P_deferrable_nom')}"
            else:
                print(f"Viaje {i+1} ({trip['kwh']} kWh): NO ENCONTRADO EN CACHÉ")

        # El test fallará porque el bug hace que el primer viaje muestre:
        # def_total_hours: 2 (en lugar de 0)
        # P_deferrable_nom: 3400.0 (en lugar de 0.0)

        print("\n❌ BUG CONFIRMADO: El test fallará porque los sensores muestran carga innecesaria")
        print("   def_total_hours debería ser [0, 0, 0, 0, 0] pero será [2, 0, 0, 0, 0]")
        print("   P_deferrable_nom debería ser [0.0, 0.0, 0.0, 0.0, 0.0] pero será [3400.0, 3400.0, 3400.0, 3400.0, 3400.0]")

        # Forzamos el test a fallar para mostrar el bug
        pytest.fail("Bug confirmado: SOC 100% aún muestra carga en sensores EMHASS")


if __name__ == "__main__":
    # Ejecutar el test
    pytest.main([__file__, "-v", "-s"])