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

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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

    async def test_partial_window_does_not_invent_a_full_hour_of_charge(self):
        """
        The first trip fits existing energy and has no complete charging slot.
        After its consumption and idle loss, one hour before the second trip
        preserves the reserve. A partial window cannot permit charging after
        departure merely because the duration was rounded up.
        """
        # Fixed reference time: Thursday 17:30 UTC
        ref_now = datetime(2026, 5, 21, 17, 30, 0, tzinfo=timezone.utc)

        # 2 trips: first has a tight window (~30 min from ref_now)
        trips = [
            {
                "id": "trip_a",
                "tipo": "recurring",
                "dia_semana": "4",  # Friday
                "hora": "18:00",
                "kwh": 10.0,
            },
            {
                "id": "trip_b",
                "tipo": "recurring",
                "dia_semana": "5",  # Saturday
                "hora": "08:00",
                "kwh": 10.0,
            },
        ]

        adapter = EMHASSAdapter(self.mock_hass, self.mock_entry)
        mock_store = AsyncMock()
        mock_store.async_save = AsyncMock()
        adapter._store = mock_store
        adapter._presence_monitor = None

        async def mock_get_current_soc():
            return 50.0

        adapter._get_current_soc = mock_get_current_soc
        adapter._get_hora_regreso = lambda: None

        with patch("homeassistant.util.dt.now", return_value=ref_now):
            await adapter.async_publish_all_deferrable_loads(trips)

        params = adapter._cached_per_trip_params

        # The half-hour window contains no complete slot; current SOC covers it.
        a = params.get("trip_a", {})
        a_def = a.get("def_total_hours", 0)
        print(f"trip_a: def_total_hours={a_def} power_watts={a.get('power_watts', 0)}")

        # The later trip needs only the amount missing after prior consumption.
        b = params.get("trip_b", {})
        b_def = b.get("def_total_hours", 0)
        print(f"trip_b: def_total_hours={b_def} power_watts={b.get('power_watts', 0)}")

        # Quantities must match physical slots and preserve both return reserves.
        assert a_def == 0
        assert a.get("power_watts", 0) == 0
        assert b_def == 1
        assert b.get("power_watts", 0) > 0, "trip_b: power_watts must be > 0"
        assert a["soc_after_trip"] >= 10
        assert b["soc_after_trip"] >= 10


if __name__ == "__main__":
    # Ejecutar el test
    pytest.main([__file__, "-v", "-s"])
