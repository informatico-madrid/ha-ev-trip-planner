"""
Test que reproduce el bug de propagación de déficit en SOC 100%.

El bug ocurre cuando:
1. Hay múltiples viajes
2. Algunos viajes necesitan más carga de la disponible en su ventana
3. El sistema propaga el déficit a viajes anteriores
4. Los viajes anteriores al 100% SOC absorben el déficit incorrectamente

Reproduce el escenario exacto reportado por el usuario.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import math

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.calculations import calculate_energy_needed


class TestSOC100DeficitPropagationBug:
    """Test que reproduce el bug de propagación de déficit en SOC 100%."""

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

    async def test_soc_100_no_debe_absorber_deficit_propagado(self):
        """
        Test que reproduce el bug exacto reportado por el usuario.

        Escenario:
        - Coche al 100% SOC (50 kWh disponibles)
        - Viaje 1: 30 kWh en 2 horas (necesita carga si SOC fuera bajo)
        - Viaje 2: 40 kWh en 1 hora (imposible, ventana muy pequeña)
        - Viaje 3: 20 kWh en 6 horas (puede absorber déficit de Viaje 2)

        Bug esperado:
        - Viaje 1 (30 kWh) al 100% SOC debería tener 0 horas
        - Pero el sistema le asigna horas porque absorbe el déficit de Viaje 2

        Comportamiento correcto:
        - Viaje 1: def_total_hours = 0 (porque SOC 100% > 30kWh + 10% = 33kWh)
        - Viaje 2: def_total_hours = 0 (ventana imposible, no se puede cargar)
        - Viaje 3: def_total_hours = calculado normalmente (no absorbe porque Viaje 2=0)
        """
        # Crear escenario que cause propagación de déficit
        trips = [
            {
                "id": "viaje_1",  # Este viaje absorberá el déficit incorrectamente
                "tipo": "punctual",
                "datetime": (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat(),
                "kwh": 30.0,  # Necesita 30 kWh + 10% = 33 kWh
                "descripcion": "Viaje que absorberá déficit"
            },
            {
                "id": "viaje_2",  # Este viaje tiene ventana imposible
                "tipo": "punctual",
                "datetime": (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),  # Solo 12 horas
                "kwh": 40.0,  # Necesita 40 kWh + 10% = 44 kWh
                "descripcion": "Viaje con ventana imposible"
            },
            {
                "id": "viaje_3",  # Este viaje normalmente absorbería el déficit
                "tipo": "punctual",
                "datetime": (datetime.now(timezone.utc) + timedelta(hours=72)).isoformat(),
                "kwh": 20.0,  # Necesita 20 kWh + 10% = 22 kWh
                "descripcion": "Viaje normal"
            }
        ]

        # Configuración
        battery_capacity = 50.0
        soc_current = 100.0  # SOC al 100% - ¡ESTO DEBERÍA PREVENIR CARGA!
        charging_power_kw = 3.4
        safety_margin = 10.0

        # Verificar cálculos individuales (todos deberían ser 0 con SOC 100%)
        print("=== CÁLCULOS INDIVIDUALES (sin propagación) ===")
        individual_results = []
        for trip in trips:
            energy_info = calculate_energy_needed(
                trip=trip,
                battery_capacity_kwh=battery_capacity,
                soc_current=soc_current,
                charging_power_kw=charging_power_kw,
                safety_margin_percent=safety_margin
            )
            individual_results.append({
                "trip_id": trip["id"],
                "kwh": trip["kwh"],
                "energia_necesaria": energy_info["energia_necesaria_kwh"],
                "horas_carga": energy_info["horas_carga_necesarias"]
            })
            print(f"{trip['id']} ({trip['kwh']} kWh): "
                  f"Energía = {energy_info['energia_necesaria_kwh']} kWh, "
                  f"Horas = {energy_info['horas_carga_necesarias']}")

        # Todos los cálculos individuales deberían ser 0 porque SOC 100% > energía necesaria
        for result in individual_results:
            assert result["energia_necesaria"] == 0, \
                f"Viaje {result['trip_id']} con SOC 100% debe tener 0 energía necesaria"

        # Simular el EMHAdapter
        adapter = EMHASSAdapter(self.mock_hass, self.mock_entry)

        # Mockear almacenamiento
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

        # Publicar viajes en orden (esto causa propagación de déficit)
        print("\n=== PUBLICANDO VIAJES (con propagación de déficit) ===")
        for i, trip in enumerate(trips):
            print(f"Publicando {trip['id']} ({trip['kwh']} kWh)...")
            result = await adapter.async_publish_deferrable_load(trip)
            print(f"Resultado: {result}")

        # Intentar activar propagación de déficit publicando todos juntos
        print("\n=== INTENTANDO ACTIVAR PROPAGACIÓN CON PUBLISH_ALL ===")
        result_all = await adapter.async_publish_all_deferrable_loads(trips)
        print(f"Publish all resultado: {result_all}")

        # Obtener parámetros de caché (esto es lo que se envía a EMHASS)
        per_trip_params = getattr(adapter, "_cached_per_trip_params", {})

        print("\n=== VERIFICACIÓN FINAL (BUG ESPERADO) ===")

        # Verificar cada viaje en el caché
        for trip in trips:
            trip_id = trip["id"]
            if trip_id in per_trip_params:
                params = per_trip_params[trip_id]
                def_hours = params.get('def_total_hours', 0)
                power_nom = params.get('P_deferrable_nom', 0.0)

                print(f"{trip_id} ({trip['kwh']} kWh): "
                      f"def_total_hours = {def_hours}, "
                      f"P_deferrable_nom = {power_nom}")

                # BUG: Viaje 1 (30 kWh) con SOC 100% debería tener 0 horas
                # pero probablemente tendrá >0 porque absorbió el déficit de Viaje 2
                if trip_id == "viaje_1":
                    if def_hours > 0:
                        print(f"❌ BUG CONFIRMADO: {trip_id} tiene {def_hours} horas a pesar de SOC 100%")
                        # El test fallará aquí, confirmando el bug
                        assert def_hours == 0, \
                            f"BUG: Viaje {trip_id} con SOC 100% no puede tener horas de carga, pero tiene {def_hours}"
                    else:
                        print(f"✅ {trip_id} correctamente tiene 0 horas")

        # Forzar el test a fallar si no detectamos el bug
        # El bug se manifiesta cuando Viaje 1 (SOC 100%) tiene >0 horas
        viaje_1_params = per_trip_params.get("viaje_1", {})
        viaje_1_def_hours = viaje_1_params.get('def_total_hours', 0)

        if viaje_1_def_hours > 0:
            print(f"\n🔥 BUG DETECTADO: Viaje 1 al 100% SOC tiene {viaje_1_def_hours} horas")
            print("   Esto confirma que la propagación de déficit ignora el SOC 100%")
            pytest.fail(f"Bug confirmado: SOC 100% aún muestra carga ({viaje_1_def_hours} horas)")
        else:
            print(f"\n⚠️  No se reprodujo el bug en esta ejecución")
            print("   Puede que se necesite un escenario más específico")

    async def test_soc_100_recurrent_with_deficit_propagation(self):
        """
        Test con viajes recurrentes que reproduce el bug reportado por el usuario.

        El usuario reportó:
        - number_of_deferrable_loads: 5
        - def_total_hours: [2, 0, 0, 0, 0] ← El primer viaje tiene 2 horas
        - P_deferrable_nom: [3400.0, 3400.0, 3400.0, 3400.0, 3400.0] ← Todos 3.4kW

        Con SOC 100%, el primer viaje NO debería tener 2 horas.
        """
        # Crear 5 viajes recurrentes como los del usuario
        trips = [
            {
                "id": "primer_viaje",  # Este debería absorber déficit
                "tipo": "recurring",
                "dia_semana": "1",  # Martes
                "hora": "09:00",
                "kwh": 30.0,  # El viaje que causa el bug
                "descripcion": "Primer viaje con SOC 100%"
            },
            {
                "id": "segundo_viaje",  # Este tiene ventana pequeña
                "tipo": "recurring",
                "dia_semana": "1",  # Martes (misma día)
                "hora": "10:00",  # Solo 1 hora después
                "kwh": 45.0,  # Mucho carga en ventana pequeña
                "descripcion": "Viaje con ventana pequeña"
            },
            {
                "id": "tercer_viaje",
                "tipo": "recurring",
                "dia_semana": "2",  # Miércoles
                "hora": "14:00",
                "kwh": 15.0,
                "descripcion": "Viaje normal"
            },
            {
                "id": "cuarto_viaje",
                "tipo": "recurring",
                "dia_semana": "3",  # Jueves
                "hora": "18:00",
                "kwh": 20.0,
                "descripcion": "Viaje normal"
            },
            {
                "id": "quinto_viaje",
                "tipo": "recurring",
                "dia_semana": "4",  # Viernes
                "hora": "08:00",
                "kwh": 25.0,
                "descripcion": "Viaje normal"
            }
        ]

        # Configuración con SOC 100%
        battery_capacity = 50.0
        soc_current = 100.0  # SOC al 100%
        charging_power_kw = 3.4
        safety_margin = 10.0

        # Crear adapter
        adapter = EMHASSAdapter(self.mock_hass, self.mock_entry)
        mock_store = AsyncMock()
        mock_store.async_save = AsyncMock()
        adapter._store = mock_store
        adapter._presence_monitor = None

        # Mockear SOC al 100%
        async def mock_get_current_soc():
            return 100.0

        adapter._get_current_soc = mock_get_current_soc

        async def mock_get_hora_regreso():
            return None

        adapter._get_hora_regreso = mock_get_hora_regreso

        # Publicar todos los viajes
        print("=== PUBLICANDO 5 VIAJES RECURRENTES ===")
        for trip in trips:
            result = await adapter.async_publish_deferrable_load(trip)
            print(f"{trip['id']}: {result}")

        # Intentar activar propagación de déficit con publish_all
        print("\n=== INTENTANDO ACTIVAR PROPAGACIÓN CON PUBLISH_ALL ===")
        result_all = await adapter.async_publish_all_deferrable_loads(trips)
        print(f"Publish all resultado: {result_all}")

        # Verificar parámetros del primer viaje (el que tiene el bug)
        per_trip_params = getattr(adapter, "_cached_per_trip_params", {})
        primer_viaje_params = per_trip_params.get("primer_viaje", {})

        print(f"\n=== PRIMER VIAJE (BUG ESPERADO) ===")
        print(f"def_total_hours: {primer_viaje_params.get('def_total_hours', 'NOT_FOUND')}")
        print(f"P_deferrable_nom: {primer_viaje_params.get('P_deferrable_nom', 'NOT_FOUND')}")

        # El bug: primer viaje al 100% SOC debería tener 0 horas pero tendrá >0
        def_hours = primer_viaje_params.get('def_total_hours', 0)
        power_nom = primer_viaje_params.get('P_deferrable_nom', 0.0)

        if def_hours > 0:
            print(f"❌ BUG CONFIRMADO: primer viaje tiene {def_hours} horas con SOC 100%")
            print(f"   P_deferrable_nom: {power_nom} W (debería ser 0.0)")
            # Esto fallará, confirmando el bug
            assert def_hours == 0, f"Bug: primer viaje al 100% SOC no puede tener {def_hours} horas"
            assert power_nom == 0.0, f"Bug: primer viaje al 100% SOC no puede tener {power_nom} W"
        else:
            print("✅ Primer viaje correctamente tiene 0 horas")
            print("   Bug no reproducido en este escenario")


if __name__ == "__main__":
    # Ejecutar los tests
    pytest.main([__file__, "-v", "-s"])