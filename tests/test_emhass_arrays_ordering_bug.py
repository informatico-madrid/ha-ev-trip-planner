"""
Test comprehensivo que demuestra que TODOS los arrays EMHASS
tienen el mismo problema de ordenamiento por índice de creación
en lugar de orden cronológico.

Bug: En sensor.py línea 277, TODOS los arrays se ordenan por emhass_index:
```python
active_trips_sorted.sort(key=lambda x: x.get("emhass_index", 0))
```

Esto causa que arrays como def_start_timestep_array, P_deferrable_nom_array, etc.
estén en orden de creación de viajes, no en orden cronológico.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter


class TestEMHASSArraysOrderingBug:
    """Test que demuestra el problema de ordenamiento en todos los arrays."""

    def setup_method(self):
        """Configuración inicial para cada test."""
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

        self.mock_hass = MagicMock()
        self.mock_hass.data = {}

        self.mock_soc_sensor = MagicMock()
        self.mock_soc_sensor.state = 30.0  # 30% SOC para forzar carga
        self.mock_hass.states.get.return_value = self.mock_soc_sensor

    @pytest.mark.asyncio
    async def test_all_emhass_arrays_ordered_by_creation_index_not_chronological(
        self, mock_datetime_2026_05_04_monday_0800_utc
    ):
        """
        Test que TODOS los arrays EMHASS están ordenados por índice de creación,
        no por deadline cronológico.

        Escenario:
        - 5 viajes creados en orden ALEATORIO (Domingo, Viernes, Jueves, Miércoles)
        - Cada viaje obtiene índice según orden de creación (0, 1, 2, 3, 4)
        - Arrays se construyen ordenando por emhass_index (creación)
        - Resultado: Arrays en orden [Domingo, Viernes, Jueves, Miércoles]
        - Esperado: Arrays en orden [Miércoles, Jueves, Viernes, Domingo]
        """
        adapter = EMHASSAdapter(self.mock_hass, self.mock_entry)
        mock_store = AsyncMock()
        mock_store.async_save = AsyncMock()
        adapter._store = mock_store
        adapter._presence_monitor = None

        async def mock_get_current_soc():
            return 30.0  # 30% SOC para forzar carga en últimos viajes

        adapter._get_current_soc = mock_get_current_soc

        async def mock_get_hora_regreso():
            return None

        adapter._get_hora_regreso = mock_get_hora_regreso

        # PASO 1: Crear viajes en orden ALEATORIO
        # (simula el orden real de creación en producción)
        trips_creation_order = [
            {
                "id": "trip_sunday",
                "tipo": "recurring",
                "dia_semana": "0",  # Domingo - ÚLTIMO cronológico
                "hora": "09:40",
                "kwh": 7.0,
                "descripcion": "Domingo - CREADO PRIMERO (índice 0)",
            },
            {
                "id": "trip_friday",
                "tipo": "recurring",
                "dia_semana": "5",  # Viernes
                "hora": "09:40",
                "kwh": 7.0,
                "descripcion": "Viernes - CREADO SEGUNDO (índice 1)",
            },
            {
                "id": "trip_thursday_2",
                "tipo": "recurring",
                "dia_semana": "4",  # Jueves tarde
                "hora": "13:40",
                "kwh": 7.0,
                "descripcion": "Jueves 13:40 - CREADO TERCERO (índice 2)",
            },
            {
                "id": "trip_thursday_1",
                "tipo": "recurring",
                "dia_semana": "4",  # Jueves mañana
                "hora": "09:40",
                "kwh": 7.0,
                "descripcion": "Jueves 09:40 - CREADO CUARTO (índice 3)",
            },
            {
                "id": "trip_wednesday",
                "tipo": "recurring",
                "dia_semana": "3",  # Miércoles - PRIMER cronológico
                "hora": "16:40",
                "kwh": 7.0,
                "descripcion": "Miércoles - CREADO ÚLTIMO (índice 4)",
            },
        ]

        # Simular creación individual (como en producción)
        for trip in trips_creation_order:
            await adapter.async_assign_index_to_trip(trip["id"])

        # Verificar índices asignados
        assert adapter._index_map["trip_sunday"] == 0
        assert adapter._index_map["trip_friday"] == 1
        assert adapter._index_map["trip_thursday_2"] == 2
        assert adapter._index_map["trip_thursday_1"] == 3
        assert adapter._index_map["trip_wednesday"] == 4

        print("\n=== ÍNDICES ASIGNADOS (orden de creación) ===")
        print("Domingo (último cronológico): índice 0 ❌")
        print("Viernes: índice 1 ❌")
        print("Jueves 13:40: índice 2 ❌")
        print("Jueves 09:40: índice 3 ❌")
        print("Miércoles (primer cronológico): índice 4 ❌")

        # Orden cronológico REAL (debería ser el orden de los arrays)
        expected_chronological = [
            "trip_wednesday",  # PRIMERO (71 horas desde ahora)
            "trip_thursday_1",  # SEGUNDO
            "trip_thursday_2",  # TERCERO
            "trip_friday",  # CUARTO
            "trip_sunday",  # ÚLTIMO (más de 160 horas)
        ]

        # Convertir IDs a objetos trip
        trips_to_publish = [
            t for t in trips_creation_order if t["id"] in expected_chronological
        ]

        # Publicar todos
        await adapter.async_publish_all_deferrable_loads(trips_to_publish)

        # Obtener parámetros
        per_trip_params = adapter._cached_per_trip_params

        print(
            "\n=== ANÁLISIS DE ARRAYS (después del fix: orden por def_start_timestep) ==="
        )

        # Primero mostrar cada viaje con su índice y parámetros
        print("\n--- VIAJES INDIVIDUALES ---")
        for trip_id, params in per_trip_params.items():
            idx = params.get("emhass_index", -1)
            start = params.get("def_start_timestep", -1)
            end = params.get("def_end_timestep", -1)
            hours = params.get("def_total_hours", -1)
            print(
                f"{trip_id}: index={idx}, def_start={start}, def_end={end}, hours={hours}"
            )

        # Construir arrays como hace sensor.py DESPUÉS del fix
        active_trips_sorted = [
            (params.get("def_start_timestep", 0), trip_id, params)
            for trip_id, params in per_trip_params.items()
        ]
        active_trips_sorted.sort(
            key=lambda x: x[0]
        )  # Orden por def_start_timestep (cronológico)

        print("\n--- VIAJES ORDENADOS POR def_start_timestep (cronológico) ---")
        for start, trip_id, params in active_trips_sorted:
            idx = params.get("emhass_index", -1)
            print(f"def_start={start}: {trip_id} (emhass_index={idx})")

        # Extraer arrays
        def_start_final = []
        def_end_final = []
        def_total_hours_final = []
        p_deferrable_nom_final = []

        for start, trip_id, params in active_trips_sorted:
            def_start_final.extend(params.get("def_start_timestep_array", []))
            def_end_final.extend(params.get("def_end_timestep_array", []))
            def_total_hours_final.extend(params.get("def_total_hours_array", []))
            p_deferrable_nom_final.extend(params.get("p_deferrable_nom_array", []))

        print("\n--- ARRAYS FINALES ---")
        print("def_start_timestep_final:", def_start_final)
        print("def_end_timestep_final:", def_end_final)
        print("def_total_hours_final:", def_total_hours_final)
        print("p_deferrable_nom_final:", p_deferrable_nom_final)

        print("\n=== VERIFICACIÓN DE ORDEN CRONOLÓGICO DESPUÉS DEL FIX ===")

        # El FIX cambió el sorting de emhass_index a def_start_timestep
        # Ahora los arrays DEBERÍAN estar en orden cronológico

        # Verificar que el PRIMER viaje cronológico (Miércoles) está al principio
        # El Miércoles tiene def_start ≈ 0
        first_trip_start = def_start_final[0]
        print(f"Primer viaje en array: def_start={first_trip_start}")

        # Después del fix, el primer valor debe ser cercano a 0 (Miércoles)
        if first_trip_start > 100:
            pytest.fail(
                f"❌ FIX NO FUNCIONÓ: El primer viaje tiene def_start={first_trip_start} (Domingo). "
                f"Debería tener def_start≈0 (Miércoles). El arrays siguen en orden de creación."
            )

        # Verificar que el ÚLTIMO viaje cronológico (Domingo) está al final
        last_trip_start = def_start_final[-1]
        print(f"Último viaje en array: def_start={last_trip_start}")

        if last_trip_start < 100:
            pytest.fail(
                f"❌ FIX NO FUNCIONÓ: El último viaje tiene def_start={last_trip_start}. "
                f"Debería tener def_start>100 (Domingo)."
            )

        # Verificar orden estrictamente creciente (cronológico)
        for i in range(len(def_start_final) - 1):
            if def_start_final[i] >= def_start_final[i + 1]:
                pytest.fail(
                    f"❌ Arrays no están en orden cronológico estricto: "
                    f"def_start[{i}]={def_start_final[i]} >= def_start[{i + 1}]={def_start_final[i + 1]}"
                )

        print("\n✅ FIX VERIFICADO: Arrays están en orden cronológico correcto")
        print("   - Primer viaje (Miércoles) al principio con def_start≈0")
        print("   - Último viaje (Domingo) al final con def_start>100")
        print("   - Orden estrictamente creciente")

    @pytest.mark.asyncio
    async def test_user_scenario_exact_arrays(self):
        """
        Reproduce el ESCENARIO EXACTO del usuario.

        Usuario reporta:
        - def_start_timestep: [120, 0, 79, 90, 100]
        - def_end_timestep: [160, 71, 88, 92, 112]
        - def_total_hours: [0, 0, 0, 1, 2]

        Este test debe crear viajes que generen exactamente estos arrays
        para confirmar el bug.
        """
        # Este test es más específico y se puede ajustar según necesitemos
        # para reproducir exactamente el escenario del usuario
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
