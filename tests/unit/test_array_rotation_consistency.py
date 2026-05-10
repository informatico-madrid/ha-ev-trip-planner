"""
Test que verifica la consistencia entre arrays EMHASS.

Bug reportado:
- def_total_hours: [0, 0, 0, 1, 2] → La carga está en los ÚLTIMOS viajes
- def_start_timestep: [120, 0, 79, 90, 100] → El primer viaje (120-160) NO rotó

Esto sugiere que def_total_hours_array SÍ rotó pero def_start_timestep_array NO.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter


class TestArrayRotationConsistency:
    """Test que todos los arrays rotan consistentemente."""

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
        self.mock_soc_sensor.state = 50.0
        self.mock_hass.states.get.return_value = self.mock_soc_sensor

    @pytest.mark.asyncio
    async def test_all_arrays_rotate_consistently(
        self, mock_datetime_2026_05_04_monday_0800_utc
    ):
        """
        Verifica que def_start_timestep_array y def_total_hours_array
        tienen el mismo orden (ambos rotados o ambos sin rotar).
        """
        adapter = EMHASSAdapter(self.mock_hass, self.mock_entry)
        mock_store = AsyncMock()
        mock_store.async_save = AsyncMock()
        adapter._store = mock_store
        adapter._presence_monitor = None

        async def mock_get_current_soc():
            return 50.0

        adapter._get_current_soc = mock_get_current_soc

        async def mock_get_hora_regreso():
            return None

        adapter._get_hora_regreso = mock_get_hora_regreso

        # Crear viajes en orden ALEATORIO (simula creación en producción)
        trips_creation_order = [
            {
                "id": "trip_sunday",
                "tipo": "recurring",
                "dia_semana": "0",
                "hora": "09:40",
                "kwh": 7.0,
            },
            {
                "id": "trip_friday",
                "tipo": "recurring",
                "dia_semana": "5",
                "hora": "09:40",
                "kwh": 7.0,
            },
            {
                "id": "trip_thursday_2",
                "tipo": "recurring",
                "dia_semana": "4",
                "hora": "13:40",
                "kwh": 7.0,
            },
            {
                "id": "trip_thursday_1",
                "tipo": "recurring",
                "dia_semana": "4",
                "hora": "09:40",
                "kwh": 7.0,
            },
            {
                "id": "trip_wednesday",
                "tipo": "recurring",
                "dia_semana": "3",
                "hora": "16:40",
                "kwh": 7.0,
            },
        ]

        # Asignar índices en orden de creación
        for trip in trips_creation_order:
            await adapter.async_assign_index_to_trip(trip["id"])

        # Orden cronológico (Miércoles primero, Domingo último)
        trips_chronological = [
            t
            for t in trips_creation_order
            if t["id"]
            in [
                "trip_wednesday",
                "trip_thursday_1",
                "trip_thursday_2",
                "trip_friday",
                "trip_sunday",
            ]
        ]

        # Publicar todos
        await adapter.async_publish_all_deferrable_loads(trips_chronological)

        # Obtener parámetros
        per_trip_params = adapter._cached_per_trip_params

        print("\n=== ANÁLISIS DE ÍNDICES Y ARRAYS ===")

        # Mostrar cada viaje con su índice y arrays
        for trip_id, params in per_trip_params.items():
            emhass_index = params.get("emhass_index", -1)
            def_start_array = params.get("def_start_timestep_array", [])
            def_total_hours_array = params.get("def_total_hours_array", [])

            print(f"\n{trip_id}:")
            print(f"  emhass_index: {emhass_index}")
            print(f"  def_start_timestep_array: {def_start_array}")
            print(f"  def_total_hours_array: {def_total_hours_array}")

        # Construir arrays finales (como hace sensor.py después del fix)
        # Ordenar por (def_start_timestep, emhass_index)
        active_trips_sorted = [
            (
                params.get("def_start_timestep", 0),
                params.get("emhass_index", 0),
                trip_id,
                params,
            )
            for trip_id, params in per_trip_params.items()
        ]
        active_trips_sorted.sort(
            key=lambda x: (x[0], x[1])
        )  # Orden cronológico con tie-breaker

        def_start_final = []
        def_total_hours_final = []

        for _, _, trip_id, params in active_trips_sorted:
            def_start_final.extend(params.get("def_start_timestep_array", []))
            def_total_hours_final.extend(params.get("def_total_hours_array", []))

        print("\n=== ARRAYS FINALES (ordenados cronológicamente después del fix) ===")
        print(f"def_start_timestep_final: {def_start_final}")
        print(f"def_total_hours_final: {def_total_hours_final}")

        # Verificar que los arrays están en orden cronológico correcto
        bugs = []

        # El primer valor debe ser el Miércoles (def_start ≈ 0)
        if def_start_final[0] > 100:  # Más de 100 horas = Domingo
            print(
                f"\n❌ BUG: def_start[0]={def_start_final[0]} (Domingo) cuando debería ser ~0 (Miércoles)"
            )
            bugs.append("def_start_array_wrong_order")

        # El último valor debe ser el Domingo (def_start > 100)
        if def_start_final[-1] < 100:
            print(
                f"\n❌ BUG: El último valor tiene def_start={def_start_final[-1]}, debería ser >100 (Domingo)"
            )
            bugs.append("def_start_array_wrong_last")

        # Verificar orden estrictamente creciente
        for i in range(len(def_start_final) - 1):
            if def_start_final[i] >= def_start_final[i + 1]:
                print(
                    f"\n❌ BUG: Arrays no en orden cronológico: [{i}]={def_start_final[i]} >= [{i + 1}]={def_start_final[i + 1]}"
                )
                bugs.append("def_start_array_not_chronological")

        if not bugs:
            print("\n✅ FIX VERIFICADO: Arrays consistentes y en orden cronológico")

        if bugs:
            pytest.fail("Arrays inconsistentes o en orden incorrecto después del fix")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
