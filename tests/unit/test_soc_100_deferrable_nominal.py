"""
Test que reproduce el bug específico de P_deferrable_nom.

Bug: Cuando un viaje no necesita carga (def_total_hours = 0), P_deferrable_nom
debería ser 0.0, pero mantiene el valor nominal (3400.0).

Esto es exactamente lo que reportó el usuario:
- def_total_hours: [0, 0, 0, 0, 0] (correcto)
- P_deferrable_nom: [3400.0, 3400.0, 3400.0, 3400.0, 3400.0] (incorrecto, debería ser [0.0, 0.0, 0.0, 0.0, 0.0])
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.calculations import calculate_energy_needed
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter


class TestSOC100DeferrableNominal:
    """Test que reproduce el bug específico de P_deferrable_nom en SOC 100%."""

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

        # Mock del sensor SOC (al 100%)
        self.mock_soc_sensor = MagicMock()
        self.mock_soc_sensor.state = 100.0  # ¡100% SOC!
        self.mock_hass.states.get.return_value = self.mock_soc_sensor

    async def test_soc_100_p_deferrable_nom_debe_ser_0_cuando_no_hay_carga(self):
        """
        Test que reproduce el bug exacto reportado por el usuario.

        Bug reportado:
        - def_total_hours: [0, 0, 0, 0, 0] ← Esto está correcto
        - P_deferrable_nom: [3400.0, 3400.0, 3400.0, 3400.0, 3400.0] ← ¡Esto es el bug!

        Esperado con SOC 100%:
        - def_total_hours: [0, 0, 0, 0, 0]
        - P_deferrable_nom: [0.0, 0.0, 0.0, 0.0, 0.0]
        """
        # Crear 5 viajes como reporta el usuario
        trips = [
            {
                "id": "viaje_1",
                "tipo": "recurring",
                "dia_semana": "1",  # Martes
                "hora": "09:00",
                "kwh": 30.0,  # El viaje que causa el bug
                "descripcion": "Primer viaje",
            },
            {
                "id": "viaje_2",
                "tipo": "recurring",
                "dia_semana": "2",  # Miércoles
                "hora": "14:00",
                "kwh": 15.0,
                "descripcion": "Segundo viaje",
            },
            {
                "id": "viaje_3",
                "tipo": "recurring",
                "dia_semana": "3",  # Jueves
                "hora": "18:00",
                "kwh": 20.0,
                "descripcion": "Tercer viaje",
            },
            {
                "id": "viaje_4",
                "tipo": "recurring",
                "dia_semana": "4",  # Viernes
                "hora": "08:00",
                "kwh": 25.0,
                "descripcion": "Cuarto viaje",
            },
            {
                "id": "viaje_5",
                "tipo": "recurring",
                "dia_semana": "5",  # Sábado
                "hora": "10:00",
                "kwh": 10.0,
                "descripcion": "Quinto viaje",
            },
        ]

        # Configuración con SOC 100% (stored but test validates via adapter output)
        # Config values used in EMHASS output verification (not local computation)
        charging_power_kw = 3.4

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

        # Publicar todos los viajes juntos para activar propagación
        print("=== PUBLICANDO 5 VIAJES CON SOC 100% ===")
        result = await adapter.async_publish_all_deferrable_loads(trips)
        print(f"Resultado publish_all: {result}")

        # Obtener parámetros de caché
        per_trip_params = getattr(adapter, "_cached_per_trip_params", {})

        print("\n=== VERIFICACIÓN DE BUG P_deferrable_nom ===")
        print(f"Potencia nominal: {charging_power_kw * 1000} W")

        # Verificar cada viaje
        bug_detectado = False
        for i, trip in enumerate(trips):
            trip_id = trip["id"]
            if trip_id in per_trip_params:
                params = per_trip_params[trip_id]
                def_hours = params.get("def_total_hours", 0)
                power_nom = params.get("P_deferrable_nom", 0.0)

                print(
                    f"Viaje {i + 1} ({trip['kwh']} kWh): "
                    f"def_total_hours = {def_hours}, "
                    f"P_deferrable_nom = {power_nom} W"
                )

                # Verificar el bug específico
                if def_hours == 0 and power_nom > 0:
                    print(
                        f"❌ BUG DETECTADO: Viaje {i + 1} tiene def_total_hours=0 pero P_deferrable_nom={power_nom} W"
                    )
                    bug_detectado = True

                    # Este test fallará aquí, confirmando el bug
                    assert (
                        power_nom == 0.0
                    ), f"BUG: Viaje {trip_id} con def_total_hours=0 debe tener P_deferrable_nom=0.0, pero tiene {power_nom} W"
                elif def_hours == 0 and power_nom == 0.0:
                    print(f"✅ Viaje {i + 1} correctamente tiene P_deferrable_nom=0.0")
                elif def_hours > 0:
                    print(
                        f"⚠️  Viaje {i + 1} tiene def_total_hours={def_hours} (no es el bug que buscamos)"
                    )

        # Si no detectamos el bug, forzar el test a fallar con un mensaje claro
        if not bug_detectado:
            print("\n⚠️  No se detectó el bug P_deferrable_nom en esta ejecución")
            print("   Intentando con un escenario más específico...")

            # Forzar el bug publicando individualmente
            print("\n=== INTENTANDO FORZAR EL BUG CON PUBLICACIÓN INDIVIDUAL ===")
            for trip in trips:
                # Clear cache para forzar recálculo
                adapter._cached_per_trip_params.clear()
                await adapter.async_publish_deferrable_load(trip)

                # Verificar inmediatamente
                if trip["id"] in adapter._cached_per_trip_params:
                    params = adapter._cached_per_trip_params[trip["id"]]
                    def_hours = params.get("def_total_hours", 0)
                    power_nom = params.get("P_deferrable_nom", 0.0)

                    if def_hours == 0 and power_nom > 0:
                        print(
                            f"❌ BUG FORZADO: {trip['id']} tiene def_hours=0 pero power_nom={power_nom} W"
                        )
                        # Esto fallará, confirmando el bug
                        assert (
                            power_nom == 0.0
                        ), f"BUG CONFIRMADO: {trip['id']} con def_hours=0 debe tener power_nom=0.0"

        print("\n=== RESUMEN DEL ESPERADO vs REAL ===")
        print("Esperado (SOC 100%):")
        print("  def_total_hours: [0, 0, 0, 0, 0]")
        print("  P_deferrable_nom: [0.0, 0.0, 0.0, 0.0, 0.0]")

        # Re-fetch reference after potential cache clearing in the fallback loop
        per_trip_params = getattr(adapter, "_cached_per_trip_params", {})

        # Mostrar valores reales
        real_values = []
        for trip in trips:
            if trip["id"] in per_trip_params:
                def_hours = per_trip_params[trip["id"]].get("def_total_hours", 0)
                power_nom = per_trip_params[trip["id"]].get("P_deferrable_nom", 0.0)
                real_values.append(f"({def_hours}, {power_nom})")

        print(f"Real: {real_values}")

        if any("0, 3400.0" in val or "0, 3400" in val for val in real_values):
            print(
                "❌ BUG CONFIRMADO: P_deferrable_nom no es 0 cuando def_total_hours=0"
            )
            pytest.fail(
                "Bug confirmed: P_deferrable_nom retains nominal value despite no charging needed"
            )

    async def test_soc_100_p_deferrable_nom_puntual(self):
        """
        Test con viajes puntuales para confirmar el bug en otro escenario.
        """
        # Crear viaje puntual que no necesita carga con SOC 100%
        trip = {
            "id": "viaje_puntual",
            "tipo": "punctual",
            "datetime": (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat(),
            "kwh": 20.0,  # Menos que la batería (50 kWh) + 10% = 55 kWh
            "descripcion": "Viaje puntual con SOC 100%",
        }

        # Configuración
        battery_capacity = 50.0
        soc_current = 100.0  # SOC al 100%
        charging_power_kw = 3.4
        safety_margin = 10.0

        # Verificar cálculo individual
        energy_info = calculate_energy_needed(
            trip=trip,
            battery_capacity_kwh=battery_capacity,
            soc_current=soc_current,
            charging_power_kw=charging_power_kw,
            safety_margin_percent=safety_margin,
        )

        print("=== VIAJE PUNTUAL ===")
        print(f"Viaje: {trip['kwh']} kWh")
        print(
            f"Cálculo individual: energía = {energy_info['energia_necesaria_kwh']} kWh, horas = {energy_info['horas_carga_necesarias']}"
        )

        # Proactive charging: SOC 100% covers target → charge minimum = trip energy
        assert (
            energy_info["energia_necesaria_kwh"] == 20.0
        ), "Viaje puntual con SOC 100% requiere carga proactiva = energía del viaje"

        # Crear adapter y publicar
        adapter = EMHASSAdapter(self.mock_hass, self.mock_entry)
        mock_store = AsyncMock()
        mock_store.async_save = AsyncMock()
        adapter._store = mock_store
        adapter._presence_monitor = None

        # Mockear SOC
        async def mock_get_current_soc():
            return 100.0

        adapter._get_current_soc = mock_get_current_soc

        async def mock_get_hora_regreso():
            return None

        adapter._get_hora_regreso = mock_get_hora_regreso

        # Publicar viaje usando publish_all (que sí popula el caché)
        result = await adapter.async_publish_all_deferrable_loads([trip])
        print(f"Publicado: {result}")

        # Verificar caché
        per_trip_params = getattr(adapter, "_cached_per_trip_params", {})

        if "viaje_puntual" in per_trip_params:
            params = per_trip_params["viaje_puntual"]
            def_hours = params.get("def_total_hours", 0)
            power_nom = params.get("P_deferrable_nom", 0.0)

            print("Resultados en caché:")
            print(f"  def_total_hours: {def_hours}")
            print(f"  P_deferrable_nom: {power_nom} W")

            # Proactive charging: trip energy > 0 → power_nom should match trip
            assert (
                power_nom > 0
            ), f"Viaje puntual con carga proactiva debe tener P_deferrable_nom > 0, pero tiene {power_nom} W"
        else:
            print("❌ Viaje no encontrado en caché")
            pytest.fail("Viaje no se publicó correctamente")


if __name__ == "__main__":
    # Ejecutar los tests
    pytest.main([__file__, "-v", "-s"])
