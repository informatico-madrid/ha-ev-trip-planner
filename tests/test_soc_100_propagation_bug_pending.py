"""
TEST QUE DEBE FALLAR - Bug de propagación de déficit en SOC 100%

Este test reproduce el escenario exacto donde el sistema de propagación de déficit
ignora el SOC 100% y asigna horas de carga incorrectamente.

El usuario reportó:
- number_of_deferrable_loads: 5
- def_total_hours: [2, 0, 0, 0, 0] ← Primer viaje tiene 2 horas con SOC 100%
- P_deferrable_nom: [3400.0, 3400.0, 3400.0, 3400.0, 3400.0]

CON SOC 100% EL PRIMER VIAJE NO PUEDE TENER 2 HORAS DE CARGA.

Este test FALLARÁ hasta que se arregle el bug de propagación de déficit.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.calculations import calculate_energy_needed


class TestSOC100PropagationBugPending:
    """Test que DEBE FALLAR por el bug de propagación de déficit en SOC 100%."""

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

    async def test_soc_100_first_trip_must_not_have_2_hours(self):
        """
        TEST QUE DEBE FALLAR - Reproduce el reporte exacto del usuario.

        El usuario reportó:
        def_total_hours: [2, 0, 0, 0, 0]
        P_deferrable_nom: [3400.0, 3400.0, 3400.0, 3400.0, 3400.0]

        CON SOC 100% EL PRIMER VIAJE NO PUEDE TENER 2 HORAS.

        Este test fallará hasta que se arregle el bug de propagación de déficit.
        """
        # Crear escenario EXACTO que causa propagación de déficit
        # El primer viaje (30 kWh) absorberá el déficit de viajes posteriores
        trips = [
            {
                "id": "primer_viaje",  # Este absorberá déficit INCORRECTAMENTE
                "tipo": "recurring",
                "dia_semana": "1",  # Martes
                "hora": "09:00",
                "kwh": 30.0,  # El viaje que causa el bug según usuario
                "descripcion": "Primer viaje al 100% SOC"
            },
            {
                "id": "segundo_viaje",  # Este tiene ventana pequeña, generará déficit
                "tipo": "recurring",
                "dia_semana": "1",  # Martes (misma día)
                "hora": "10:00",  # Solo 1 hora después
                "kwh": 45.0,  # Mucho carga en ventana muy pequeña
                "descripcion": "Viaje con ventana pequeña (genera déficit)"
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

        # Configuración con SOC 100% - EL ESTADO INICIAL NO CAMBIA
        battery_capacity = 50.0
        soc_current = 100.0  # SOC AL 100% - ¡ESTO NO DEBE CAMBIAR!
        charging_power_kw = 3.4
        safety_margin = 10.0

        print("=== ESCENARIO EXACTO DEL USUARIO ===")
        print(f"SOC inicial: {soc_current}%")
        print(f"Batería: {battery_capacity} kWh")
        print(f"Potencia: {charging_power_kw} kW")
        print("")

        # Verificar cálculos individuales (todos deberían ser 0)
        print("=== CÁLCULOS INDIVIDUALES (sin propagación) ===")
        for trip in trips:
            energy_info = calculate_energy_needed(
                trip=trip,
                battery_capacity_kwh=battery_capacity,
                soc_current=soc_current,
                charging_power_kw=charging_power_kw,
                safety_margin_percent=safety_margin
            )
            print(f"{trip['id']} ({trip['kwh']} kWh): "
                  f"Energía = {energy_info['energia_necesaria_kwh']} kWh, "
                  f"Horas = {energy_info['horas_carga_necesarias']}")

        print("")
        print("CONCLUSIONES INDIVIDUALES:")
        print("- Todos los viajes tienen 0 horas porque SOC 100% > energía necesaria")
        print("- El primer viaje (30 kWh): 100% SOC > 33 kWh (30 + 10%), así que 0 horas")
        print("")

        # Crear adapter
        adapter = EMHASSAdapter(self.mock_hass, self.mock_entry)
        mock_store = AsyncMock()
        mock_store.async_save = AsyncMock()
        adapter._store = mock_store
        adapter._presence_monitor = None

        # Mockear SOC AL 100% - ¡NO DEBE CAMBIAR!
        async def mock_get_current_soc():
            return 100.0  # ¡SIEMPRE 100%!

        adapter._get_current_soc = mock_get_current_soc

        async def mock_get_hora_regreso():
            return None

        adapter._get_hora_regreso = mock_get_hora_regreso

        # Publicar todos los juntos (esto activa propagación de déficit)
        print("=== PUBLICANDO TODOS LOS VIAJES (activa propagación de déficit) ===")
        result = await adapter.async_publish_all_deferrable_loads(trips)
        print(f"Resultado publish_all: {result}")
        print("")

        # Obtener parámetros de caché
        per_trip_params = getattr(adapter, "_cached_per_trip_params", {})

        print("=== VERIFICACIÓN FINAL (DEBE FALLAR) ===")
        print("Esperado (correcto con SOC 100%):")
        print("  def_total_hours: [0, 0, 0, 0, 0]")
        print("  P_deferrable_nom: [0.0, 0.0, 0.0, 0.0, 0.0]")
        print("")

        # Verificar el primer viaje (el que tiene el bug según usuario)
        primer_viaje_params = per_trip_params.get("primer_viaje", {})
        def_hours = primer_viaje_params.get('def_total_hours', 0)
        power_nom = primer_viaje_params.get('P_deferrable_nom', 0.0)

        print(f"Primer viaje (30 kWh, SOC 100%):")
        print(f"  def_total_hours = {def_hours}")
        print(f"  P_deferrable_nom = {power_nom} W")
        print("")

        # VERIFICAR BUG 1: El primer viaje NO puede tener >0 horas con SOC 100%
        if def_hours > 0:
            print("❌ BUG 1 CONFIRMADO: Primer viaje tiene horas de carga a pesar de SOC 100%")
            print(f"   Esto es IMPOSIBLE FÍSICAMENTE: no se puede cargar un coche al 100% SOC")
            print("")
            print("Este test fallará hasta que se arregle el bug de propagación de déficit")
            print("La propagación de déficit está ignorando el límite del 100% SOC")

            # Esto fallará, confirmando el bug
            assert def_hours == 0, \
                f"BUG CRÍTICO: Primer viaje al 100% SOC no puede tener {def_hours} horas. Es físicamente imposible."

            assert power_nom == 0.0, \
                f"BUG CRÍTICO: Primer viaje al 100% SOC no puede tener P_deferrable_nom={power_nom} W. Debe ser 0.0"
        else:
            print("✅ Primer viaje tiene 0 horas (correcto)")

        # Verificar TODOS los viajes - BUG 2
        print("")
        print("=== VERIFICACIÓN DE TODOS LOS VIAJES (BUG 2) ===")
        bug2_detectado = False

        for i, trip in enumerate(trips):
            trip_id = trip["id"]
            if trip_id in per_trip_params:
                params = per_trip_params[trip_id]
                def_hours = params.get('def_total_hours', 0)
                power_nom = params.get('P_deferrable_nom', 0.0)

                print(f"Viaje {i+1} ({trip['kwh']} kWh): "
                      f"def_total_hours = {def_hours}, P_deferrable_nom = {power_nom} W")

                # BUG 2: Si def_total_hours = 0, P_deferrable_nom DEBE ser 0.0
                if def_hours == 0 and power_nom > 0:
                    print(f"❌ BUG 2: Viaje tiene def_hours=0 pero P_deferrable_nom={power_nom} W (debe ser 0.0)")
                    bug2_detectado = True

        if bug2_detectado:
            print("")
            print("🔥 BUG 2 CONFIRMADO: P_deferrable_nom no es 0 cuando def_total_hours=0")
            print("   Esto causa que EMHASS tenga sensores con potencia a pesar de no needing carga")
            print("   Reportado por usuario: P_deferrable_nom: [3400.0, 3400.0, 3400.0, 3400.0, 3400.0]")
            print("   Debería ser: P_deferrable_nom: [0.0, 0.0, 0.0, 0.0, 0.0]")

            # Esto fallará, confirmando el bug 2
            pytest.fail("Bug confirmado: P_deferrable_nom mantiene valor nominal a pesar de no needing carga")
        else:
            print("")
            print("⚠️  No se detectó el Bug 2 en esta ejecución")

    def test_soc_100_impossible_physics(self):
        """
        Test que verifica el principio físico: no se puede cargar un coche al 100% SOC.

        Este es un test de integridad que siempre debe pasar.
        """
        battery_capacity = 50.0
        soc_current = 100.0
        charging_power_kw = 3.4

        # Con SOC 100%, la energía disponible es máxima
        energia_disponible = battery_capacity * (soc_current / 100.0)

        print(f"=== VERIFICACIÓN FÍSICA ===")
        print(f"Batería: {battery_capacity} kWh")
        print(f"SOC: {soc_current}%")
        print(f"Energía disponible: {energia_disponible} kWh")
        print(f"Potencia de carga: {charging_power_kw} kW")

        # Principio físico: no se puede cargar más allá del 100% SOC
        assert soc_current <= 100.0, "SOC no puede exceder 100%"

        # Si ya estamos al 100%, no se puede añadir más energía
        if soc_current == 100.0:
            energia_adicional_maxima = 0.0
            horas_carga_maximas = 0.0
        else:
            energia_adicional_maxima = battery_capacity * (100.0 - soc_current) / 100.0
            horas_carga_maximas = energia_adicional_maxima / charging_power_kw

        print(f"Energía adicional máxima posible: {energia_adicional_maxima} kWh")
        print(f"Horas de carga máximas posibles: {horas_carga_maximas}")

        # Con SOC 100%, no se puede cargar nada
        assert energia_adicional_maxima == 0.0, "Con SOC 100%, no se puede cargar energía adicional"
        assert horas_carga_maximas == 0.0, "Con SOC 100%, no puede haber horas de carga"

        print("✅ Principio físico verificado: SOC 100% = 0 horas de carga")


if __name__ == "__main__":
    # Este test DEBE fallar hasta que se arregle el bug
    pytest.main([__file__, "-v", "-s"])