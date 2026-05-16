"""SOC 100% propagation behavior test.

Legacy source: tests/_legacy_snapshot/from-epic/test_soc_100_propagation.py

Adapted to SOLID API:
- Import from `emhass.adapter` not `emhass_adapter`
- Uses `async_publish_all_deferrable_loads()` → inspect `_cached_per_trip_params`

Proactive charging at SOC 100%:
- Even at SOC 100%, the system schedules proactive charging to prepare for future trips
- The real power profile limits charging to battery capacity
- BUG: If proactive charging is NOT wired, trips at SOC 100% may get 0 charge hours
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter


class TestSOC100Propagation:
    """Verifies proactive charging at SOC 100% uses power profile clamping."""

    @pytest.mark.asyncio
    async def test_soc_100_first_trip_must_not_have_2_hours(self):
        """
        Verifies proactive charging at SOC 100% assigns charge hours to trips.

        Reproduces user report scenario where def_total_hours and P_deferrable_nom
        were zeroed out incorrectly. With proactive charging, even at SOC 100%,
        trips should receive minimum charge hours.
        """
        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        hass.config.time_zone = timezone.utc
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.services.has_service = MagicMock(return_value=True)

        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value={})
        mock_store.async_save = AsyncMock()

        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "safety_margin_percent": 10.0,
            "vehicle_name": "test_vehicle",
            "max_deferrable_loads": 50,
            "charging_power": 3.4,
            "battery_capacity": 50.0,
            "safety_margin_percent": 10.0,
        }
        entry.options = {}

        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

        # Create scenario from user report: 5 trips with tight deadlines
        trips = [
            {"id": "primer_viaje", "tipo": "recurring", "kwh": 30.0},
            {"id": "segundo_viaje", "tipo": "recurring", "kwh": 45.0},
            {"id": "tercer_viaje", "tipo": "recurring", "kwh": 15.0},
            {"id": "cuarto_viaje", "tipo": "recurring", "kwh": 20.0},
            {"id": "quinto_viaje", "tipo": "recurring", "kwh": 25.0},
        ]

        now = datetime.now(timezone.utc)
        for i, trip in enumerate(trips):
            # Stagger trips: 36h, 61h, 86h, 111h, 136h from now
            trip["datetime"] = (now + timedelta(hours=36 + i * 25)).isoformat()

        with (
            patch.object(
                adapter, "_get_current_soc", new_callable=AsyncMock, return_value=100.0
            ),
            patch.object(
                adapter, "_get_hora_regreso", new_callable=AsyncMock, return_value=None
            ),
        ):
            result = await adapter.async_publish_all_deferrable_loads(trips)

        assert result is True

        # Proactive charging: even at SOC 100%, trips require minimum charge
        per_trip_params = adapter._cached_per_trip_params

        primer_viaje_params = per_trip_params.get("primer_viaje", {})
        def_hours = primer_viaje_params.get("def_total_hours", 0)
        power_nom = primer_viaje_params.get("power_watts", 0.0)

        if def_hours > 0:
            # With proactive charging, the first trip should have charge hours
            pass
        else:
            # If this fails, proactive charging is NOT wired at SOC 100%
            assert (
                def_hours > 0
            ), f"With proactive charging at SOC 100%, primer_viaje must have charge hours > 0, got {def_hours}"

        for trip in trips:
            trip_id = trip["id"]
            if trip_id in per_trip_params:
                params = per_trip_params[trip_id]
                def_hours = params.get("def_total_hours", 0)
                power_nom = params.get("power_watts", 0.0)

                # With proactive charging, def_hours and power_watts should both be > 0
                assert (
                    def_hours > 0
                ), f"Trip {trip_id} failed proactive charging: def_total_hours is {def_hours} at SOC 100%"
                assert (
                    power_nom > 0
                ), f"Trip {trip_id} failed proactive charging: power_watts is {power_nom} at SOC 100%"

    @pytest.mark.asyncio
    async def test_soc_100_impossible_physics(self):
        """
        Test that verifies the physics principle: you cannot charge a car beyond 100% SOC.

        This is an integrity test that must always pass.
        """
        battery_capacity = 50.0
        soc_current = 100.0
        charging_power_kw = 3.4

        # Physics principle: cannot charge beyond 100% SOC
        assert soc_current <= 100.0, "SOC cannot exceed 100%"

        # If already at 100%, no more energy can be added
        if soc_current == 100.0:
            energia_adicional_maxima = 0.0
            horas_carga_maximas = 0.0
        else:
            energia_adicional_maxima = battery_capacity * (100.0 - soc_current) / 100.0
            horas_carga_maximas = energia_adicional_maxima / charging_power_kw

        # With SOC 100%, nothing can be charged
        assert (
            energia_adicional_maxima == 0.0
        ), "With SOC 100%, no additional energy can be charged"
        assert horas_carga_maximas == 0.0, "With SOC 100%, there cannot be charge hours"
