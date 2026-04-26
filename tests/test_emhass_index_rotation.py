"""
Test que reproduce el bug donde los índices EMHASS no se rotan
según el orden cronológico de los viajes.

Bug reportado:
- 5 viajes recurrentes en días diferentes
- El primer viaje cronológico (Miércoles) está en el índice 1
- El último viaje cronológico (Domingo) está en el índice 0
- def_start_timestep: [120, 0, 79, 90, 100]
- El índice 0 tiene def_start=120 (incorrecto, debería ser 0 para el primer viaje)

El problema: emhass_index se asigna por orden de CREACIÓN de viajes,
no por orden CRONOLÓGICO.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter


class TestEMHASSIndexRotation:
    """Test que EMHASS indices se asignan en orden cronológico."""

    def setup_method(self):
        """Configuración inicial para cada test."""
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

        self.mock_hass = MagicMock()
        self.mock_hass.data = {}

        self.mock_soc_sensor = MagicMock()
        self.mock_soc_sensor.state = 50.0  # 50% SOC
        self.mock_hass.states.get.return_value = self.mock_soc_sensor

    @pytest.mark.asyncio
    async def test_emhass_indices_ordered_by_deadline_not_creation(self):
        """
        Test que los índices EMHASS se asignan en orden cronológico,
        no en orden de creación de viajes.

        Escenario:
        - 5 viajes recurrentes
        - Miércoles 29/04 16:40 (PRÓXIMO - 71 horas desde ahora)
        - Jueves 30/04 09:40
        - Jueves 30/04 13:40
        - Viernes 01/05 09:40
        - Domingo 03/05 09:40 (ÚLTIMO - más de 160 horas desde ahora)

        Esperado:
        - Índice 0: Miércoles (primer viaje cronológico)
        - Índice 1: Jueves 09:40
        - Índice 2: Jueves 13:40
        - Índice 3: Viernes
        - Índice 4: Domingo

        Bug actual:
        - Índice 0: Domingo (creado primero, incorrecto)
        - Índice 1: Miércoles (segundo, incorrecto)
        ...
        """
        now = datetime.now(timezone.utc)

        # Crear 5 viajes en orden CRONOLÓGICO (Miércoles → Domingo)
        trips_chronological = [
            {
                "id": "trip_wednesday",
                "tipo": "recurring",
                "dia_semana": "3",  # Miércoles
                "hora": "16:40",
                "kwh": 7.0,
                "descripcion": "Miércoles 16:40 - PRIMER VIAJE",
            },
            {
                "id": "trip_thursday_1",
                "tipo": "recurring",
                "dia_semana": "4",  # Jueves
                "hora": "09:40",
                "kwh": 7.0,
                "descripcion": "Jueves 09:40",
            },
            {
                "id": "trip_thursday_2",
                "tipo": "recurring",
                "dia_semana": "4",  # Jueves
                "hora": "13:40",
                "kwh": 7.0,
                "descripcion": "Jueves 13:40",
            },
            {
                "id": "trip_friday",
                "tipo": "recurring",
                "dia_semana": "5",  # Viernes
                "hora": "09:40",
                "kwh": 7.0,
                "descripcion": "Viernes 09:40",
            },
            {
                "id": "trip_sunday",
                "tipo": "recurring",
                "dia_semana": "0",  # Domingo
                "hora": "09:40",
                "kwh": 7.0,
                "descripcion": "Domingo 09:40 - ÚLTIMO VIAJE",
            },
        ]

        # Crear adapter
        adapter = EMHASSAdapter(self.mock_hass, self.mock_entry)
        mock_store = AsyncMock()
        mock_store.async_save = AsyncMock()
        adapter._store = mock_store
        adapter._presence_monitor = None

        # Mockear SOC
        async def mock_get_current_soc():
            return 50.0

        adapter._get_current_soc = mock_get_current_soc

        async def mock_get_hora_regreso():
            return None

        adapter._get_hora_regreso = mock_get_hora_regreso

        # Publicar todos los viajes
        result = await adapter.async_publish_all_deferrable_loads(trips_chronological)
        assert result is True

        # Obtener parámetros de caché
        per_trip_params = adapter._cached_per_trip_params

        print("\n=== VERIFICACIÓN DE ÍNDICES EMHASS ===")

        # Verificar que los índices están asignados en orden cronológico
        expected_indices = {
            "trip_wednesday": 0,     # PRIMER viaje cronológico
            "trip_thursday_1": 1,
            "trip_thursday_2": 2,
            "trip_friday": 3,
            "trip_sunday": 4,        # ÚLTIMO viaje cronológico
        }

        bugs_detectados = []

        for trip_id, expected_index in expected_indices.items():
            if trip_id in per_trip_params:
                params = per_trip_params[trip_id]
                actual_index = params.get("emhass_index", -1)
                def_start = params.get("def_start_timestep", -1)
                def_end = params.get("def_end_timestep", -1)

                print(f"{trip_id}:")
                print(f"  Índice esperado: {expected_index}")
                print(f"  Índice actual: {actual_index}")
                print(f"  def_start_timestep: {def_start}")
                print(f"  def_end_timestep: {def_end}")
                print("")

                # BUG: Verificar que el índice coincide con el orden cronológico
                if actual_index != expected_index:
                    print(f"❌ BUG: Índice incorrecto para {trip_id}")
                    print(f"   Esperado índice {expected_index} (orden cronológico)")
                    print(f"   Actual índice {actual_index} (orden de creación)")
                    bugs_detectados.append({
                        'trip_id': trip_id,
                        'expected_index': expected_index,
                        'actual_index': actual_index,
                        'def_start': def_start,
                        'def_end': def_end,
                    })

        # Verificar específicamente que el primer viaje cronológico tiene índice 0
        first_trip = "trip_wednesday"
        if first_trip in per_trip_params:
            first_params = per_trip_params[first_trip]
            first_index = first_params.get("emhass_index", -1)
            first_def_start = first_params.get("def_start_timestep", -1)

            # El primer viaje debe tener índice 0
            if first_index != 0:
                print(f"❌ BUG CRÍTICO: Primer viaje cronológico tiene índice {first_index} en lugar de 0")
                bugs_detectados.append({
                    'trip_id': first_trip,
                    'bug': 'first_trip_not_index_0',
                    'expected_index': 0,
                    'actual_index': first_index,
                })

            # El primer viaje debe tener def_start_timestep cercano a 71 (horas hasta Miércoles 16:40)
            # Si tiene def_start=120 (5 días), significa que está mal posicionado
            if first_def_start > 100:  # Más de 100 horas = más de 4 días
                print(f"❌ BUG CRÍTICO: Primer viaje tiene def_start={first_def_start} (debería ser ~71)")
                bugs_detectados.append({
                    'trip_id': first_trip,
                    'bug': 'first_trip_wrong_start',
                    'expected_start': '< 100',
                    'actual_start': first_def_start,
                })

        if bugs_detectados:
            print(f"\n=== BUGS CONFIRMADOS: {len(bugs_detectados)} ===")
            for bug in bugs_detectados:
                print(f"- {bug}")

            pytest.fail(
                f"Bugs detectados: los índices EMHASS no están en orden cronológico. "
                f"Total bugs: {len(bugs_detectados)}"
            )
        else:
            print("\n✅ Todos los índices están correctos")

    @pytest.mark.asyncio
    async def test_emhass_arrays_ordered_by_index(self):
        """
        Test que los arrays EMHASS (def_start_timestep_array, etc.)
        están en orden de índice EMHASS, no en orden de creación.

        Este test verifica que cuando se construyen los arrays en el sensor,
        se ordenan correctamente por emhass_index ascendente.
        """
        # Este test verificaría el código en sensor.py líneas 277-287
        # Por ahora solo documentamos el comportamiento esperado

        # Esperado: active_trips_sorted.sort(key=lambda x: x.get("emhass_index", 0))
        # Resultado: Arrays en orden [índice 0, índice 1, índice 2, ...]
        #
        # PERO si emhass_index se asignó por orden de creación,
        # entonces los arrays quedan en orden de creación, no cronológico.

        # Pendiente: Implementar este test cuando entendamos mejor
        # la relación entre _index_map y el ordenamiento de trips
        pass


if __name__ == "__main__":
    # Ejecutar el test
    pytest.main([__file__, "-v", "-s"])
