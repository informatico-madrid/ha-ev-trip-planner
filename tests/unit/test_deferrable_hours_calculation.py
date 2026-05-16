"""
Test que reproduce el bug donde def_total_hours marca 0 pero P_deferrable tiene carga.

El bug ocurre cuando:
1. SOC inicial no es 100% (ej: 50%)
2. Hay múltiples viajes que consumen SOC progresivamente
3. Los últimos viajes SÍ necesitan carga (se ve en P_deferrable)
4. PERO def_total_hours marca 0 (incorrecto)
5. Y P_deferrable_nom también marca 0 (por el fix anterior que depende de total_hours)

Este es un bug diferente al de SOC 100%.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.calculations import calculate_energy_needed
from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter


class TestDeferrableHoursCalculation:
    """Test que reproduce el bug donde def_total_hours no coincide con P_deferrable."""

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
            "safety_margin_percent": 10.0,
        }
        self.mock_entry.entry_id = "test_entry"

        # Mock del Home Assistant
        self.mock_hass = MagicMock()
        self.mock_hass.data = {}

        # Mock del sensor SOC (al 50% - NO 100%)
        self.mock_soc_sensor = MagicMock()
        self.mock_soc_sensor.state = (
            50.0  # 50% SOC - suficiente para algunos viajes pero no todos
        )
        self.mock_hass.states.get.return_value = self.mock_soc_sensor

    async def test_def_total_hours_must_match_power_profile(self):
        """
        Test que reproduce el bug reportado por el usuario.

        Escenario:
        - SOC inicial: 50% (25 kWh disponibles)
        - 5 viajes recurrentes que consumen energía progresivamente
        - Los primeros viajes pueden no necesitar carga
        - Los últimos viajes SÍ necesitan carga (SOC bajo después de viajes anteriores)
        - PERO def_total_hours marca 0 para todos (incorrecto)

        Lo que debería pasar:
        - def_total_hours debería reflejar las horas de carga que SÍ están en P_deferrable
        - P_deferrable_nom debería coincidir con P_deferrable (si hay 3400.0 en perfil, nominal debe ser 3400.0)
        """
        # Crear 5 viajes recurrentes
        trips = [
            {
                "id": "viaje_1",
                "tipo": "recurring",
                "dia_semana": "1",  # Martes
                "hora": "09:00",
                "kwh": 10.0,  # Viaje pequeño
                "descripcion": "Viaje 1",
            },
            {
                "id": "viaje_2",
                "tipo": "recurring",
                "dia_semana": "2",  # Miércoles
                "hora": "14:00",
                "kwh": 10.0,  # Viaje pequeño
                "descripcion": "Viaje 2",
            },
            {
                "id": "viaje_3",
                "tipo": "recurring",
                "dia_semana": "3",  # Jueves
                "hora": "18:00",
                "kwh": 10.0,  # Viaje pequeño
                "descripcion": "Viaje 3",
            },
            {
                "id": "viaje_4",
                "tipo": "recurring",
                "dia_semana": "4",  # Viernes
                "hora": "08:00",
                "kwh": 10.0,  # Viaje pequeño
                "descripcion": "Viaje 4",
            },
            {
                "id": "viaje_5",
                "tipo": "recurring",
                "dia_semana": "5",  # Sábado
                "hora": "10:00",
                "kwh": 10.0,  # Viaje pequeño
                "descripcion": "Viaje 5",
            },
        ]

        # Configuración con SOC 50% (no 100%)
        battery_capacity = 50.0
        soc_current = 50.0  # 50% SOC = 25 kWh disponibles
        charging_power_kw = 3.4
        safety_margin = 10.0

        print("=== ESCENARIO: SOC 50% con múltiples viajes ===")
        print(
            f"SOC inicial: {soc_current}% ({battery_capacity * soc_current / 100} kWh)"
        )
        print(f"Consumo total de todos los viajes: {sum(t['kwh'] for t in trips)} kWh")
        print(
            f"Energía disponible sin cargar: {battery_capacity * soc_current / 100} kWh"
        )
        print("")

        # Verificar cálculos individuales
        print("=== CÁLCULOS INDIVIDUALES (sin propagación SOC) ===")
        for i, trip in enumerate(trips):
            energy_info = calculate_energy_needed(
                trip=trip,
                battery_capacity_kwh=battery_capacity,
                soc_current=soc_current,  # Todos usan el mismo SOC inicial
                charging_power_kw=charging_power_kw,
                safety_margin_percent=safety_margin,
            )
            print(
                f"{trip['id']} ({trip['kwh']} kWh): "
                f"Energía = {energy_info['energia_necesaria_kwh']} kWh, "
                f"Horas = {energy_info['horas_carga_necesarias']}"
            )
        print("")

        # Crear adapter
        adapter = EMHASSAdapter(self.mock_hass, self.mock_entry)
        mock_store = AsyncMock()
        mock_store.async_save = AsyncMock()
        adapter._store = mock_store
        adapter._presence_monitor = None

        # Mockear SOC al 50%
        async def mock_get_current_soc():
            return 50.0

        adapter._get_current_soc = mock_get_current_soc

        async def mock_get_hora_regreso():
            return None

        adapter._get_hora_regreso = mock_get_hora_regreso

        # Publicar todos los viajes
        print("=== PUBLICANDO TODOS LOS VIAJES ===")
        result = await adapter.async_publish_all_deferrable_loads(trips)
        print(f"Resultado: {result}")
        print("")

        # Obtener parámetros de caché
        per_trip_params = getattr(adapter, "_cached_per_trip_params", {})

        print("=== VERIFICACIÓN DEL BUG (debe fallar) ===")

        for trip in trips:
            trip_id = trip["id"]
            if trip_id in per_trip_params:
                params = per_trip_params[trip_id]
                def_hours = params.get("def_total_hours", 0)
                power_watts = params.get("power_watts", 0.0)

                print(f"{trip_id} ({trip['kwh']} kWh):")
                print(f"  def_total_hours = {def_hours}")
                print(f"  power_watts = {power_watts} W")
                print("")

                # En SOLID API: def_total_hours y power_watts deben ser > 0
                # cuando hay un viaje con energía que cargar
                if trip["kwh"] > 0:
                    assert def_hours > 0, (
                        f"Trip {trip_id}: requiere {trip['kwh']} kWh "
                        f"pero def_total_hours = {def_hours} (debería ser > 0)"
                    )
                    assert power_watts > 0, (
                        f"Trip {trip_id}: requiere {trip['kwh']} kWh "
                        f"pero power_watts = {power_watts} W (debería ser > 0)"
                    )
                else:
                    assert def_hours == 0, (
                        f"Trip {trip_id}: sin energía necesaria "
                        f"pero def_total_hours = {def_hours} (debería ser 0)"
                    )
                    assert power_watts == 0.0, (
                        f"Trip {trip_id}: sin energía necesaria "
                        f"pero power_watts = {power_watts} W (debería ser 0.0)"
                    )


if __name__ == "__main__":
    # Ejecutar el test
    pytest.main([__file__, "-v", "-s"])
