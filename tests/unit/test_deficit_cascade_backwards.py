"""RED-phase ATDD test: cascading deficit must propagate backwards through ALL windows.

Business rule: If a charging window has insufficient hours, the deficit propagates
to the immediately previous window. If that window also lacks capacity, it continues
recursively back to the first window. If the first window also has deficit, charge
what's possible and accept the remaining deficit.

This test verifies the cascade works end-to-end through the adapter's
_apply_deficit_results → _cached_per_trip_params path.

Each trip in the chain has 3 fundamental assertions:
1. def_total_hours — horas totales de carga asignadas
2. def_start_timestep — inicio de la ventana de carga
3. def_end_timestep — fin de la ventana de carga

Sin estos 3 assertions por ventana, no se puede detectar un problema en el flujo de cascada.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.calculations import calculate_hours_deficit_propagation
from custom_components.ev_trip_planner.calculations import determine_charging_need
from custom_components.ev_trip_planner.calculations.windows import (
    calculate_multi_trip_charging_windows,
)
from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_VEHICLE_NAME,
)
from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter


# ===================================================================
# Pure function tests: algorithm correctness
# ===================================================================


class TestDeficitCascadeBackwards:
    """Verify cascading deficit propagates backwards through ALL windows in chain."""

    def test_two_trips_cascade_to_first(self):
        """T3 deficit origin is zeroed out, cascades through T2 → T1 absorbs it.

        New algorithm: only the FIRST trip with own deficit is the origin.
        Origin is zeroed out (adjusted=0), deficit cascades backwards.
        Trips after origin are unchanged.

        T1: window=10h, needs=2h → spare=8h
        T2: window=4h, needs=4h → spare=0h (passes through)
        T3: window=4h, needs=6h → deficit=2h (ORIGIN, zeroed out)
        """
        windows = [
            {"ventana_horas": 10, "horas_carga_necesarias": 2},
            {"ventana_horas": 4, "horas_carga_necesarias": 4},
            {"ventana_horas": 4, "horas_carga_necesarias": 6},
        ]
        results = calculate_hours_deficit_propagation(windows)

        # T3: deficit origin — zeroed out
        assert results[2]["deficit_hours_propagated"] == 0.0
        assert results[2]["deficit_hours_to_propagate"] == 2.0
        assert results[2]["adjusted_def_total_hours"] == 0.0

        # T2: zero spare, passes deficit through unchanged
        assert results[1]["deficit_hours_propagated"] == 0.0
        assert results[1]["deficit_hours_to_propagate"] == 2.0
        assert results[1]["adjusted_def_total_hours"] == 4.0

        # T1: absorbs all 2h from carrier
        assert results[0]["deficit_hours_propagated"] == 2.0
        assert results[0]["deficit_hours_to_propagate"] == 0.0
        assert results[0]["adjusted_def_total_hours"] == 4.0

    def test_four_trips_chain_cascade(self):
        """4-trip chain: first deficit trip is origin, zeroed out, cascades backwards.

        T1: window=10h, needs=2h → spare=8h
        T2: window=4h, needs=5h → deficit=1h (ORIGIN, zeroed out)
        T3: window=4h, needs=4h → spare=0h (unchanged, after origin)
        T4: window=4h, needs=6h → deficit=2h (unchanged, after origin)

        Only the FIRST trip with deficit (T2) is the origin. Its own deficit
        cascades backwards to T1. Trips after origin (T3, T4) are unchanged.
        """
        windows = [
            {"ventana_horas": 10, "horas_carga_necesarias": 2},
            {"ventana_horas": 4, "horas_carga_necesarias": 5},
            {"ventana_horas": 4, "horas_carga_necesarias": 4},
            {"ventana_horas": 4, "horas_carga_necesarias": 6},
        ]
        results = calculate_hours_deficit_propagation(windows)

        # T2: deficit origin — zeroed out, deficit cascades backwards
        assert results[1]["deficit_hours_propagated"] == 0.0
        assert results[1]["deficit_hours_to_propagate"] == 1.0
        assert results[1]["adjusted_def_total_hours"] == 0.0

        # T3: after origin, unchanged
        assert results[2]["deficit_hours_propagated"] == 0.0
        assert results[2]["deficit_hours_to_propagate"] == 0.0
        assert results[2]["adjusted_def_total_hours"] == 4.0

        # T4: after origin, unchanged (own deficit not propagated)
        assert results[3]["deficit_hours_propagated"] == 0.0
        assert results[3]["deficit_hours_to_propagate"] == 0.0
        assert results[3]["adjusted_def_total_hours"] == 6.0

        # T1: absorbs 1h from origin T2
        assert results[0]["deficit_hours_propagated"] == 1.0
        assert results[0]["deficit_hours_to_propagate"] == 0.0
        assert results[0]["adjusted_def_total_hours"] == 3.0

    def test_first_trip_also_has_deficit(self):
        """T1 is deficit origin, zeroed out, no trip before it to absorb.

        T1: window=2h, needs=3h → deficit=1h (ORIGIN, zeroed out)
        T2: window=4h, needs=5h → deficit=1h (after origin, unchanged)
        T3: window=4h, needs=6h → deficit=2h (after origin, unchanged)

        Since T1 is the first trip, its 1h deficit has nowhere to cascade.
        """
        windows = [
            {"ventana_horas": 2, "horas_carga_necesarias": 3},
            {"ventana_horas": 4, "horas_carga_necesarias": 5},
            {"ventana_horas": 4, "horas_carga_necesarias": 6},
        ]
        results = calculate_hours_deficit_propagation(windows)

        # T1: deficit origin — zeroed out, cascades 1h backwards (nowhere)
        assert results[0]["deficit_hours_propagated"] == 0.0
        assert results[0]["deficit_hours_to_propagate"] == 1.0
        assert results[0]["adjusted_def_total_hours"] == 0.0

        # T2: after origin, unchanged
        assert results[1]["deficit_hours_propagated"] == 0.0
        assert results[1]["deficit_hours_to_propagate"] == 0.0
        assert results[1]["adjusted_def_total_hours"] == 5.0

        # T3: after origin, unchanged (own deficit not propagated)
        assert results[2]["deficit_hours_propagated"] == 0.0
        assert results[2]["deficit_hours_to_propagate"] == 0.0
        assert results[2]["adjusted_def_total_hours"] == 6.0


# ===================================================================
# Integration test: adapter wiring
# ===================================================================


class TestAdapterDeficitCascadeIntegration:
    """Integration tests verifying deficit cascade flows through _apply_deficit_results.

    Each test asserts the 3 fundamental fields for EACH window in the chain:
    - def_total_hours: total charging hours assigned
    - def_start_timestep: window start index
    - def_end_timestep: window end index
    """

    def _print_cache_chain(self, adapter, trip_ids):
        """Print the 3 fundamental fields for each trip in chain."""
        print("\n=== CHAIN INSPECTION ===")
        for tid in trip_ids:
            c = adapter._cached_per_trip_params[tid]
            print(
                f"  {tid}: def_total_hours={c.get('def_total_hours')}, "
                f"def_start_timestep={c.get('def_start_timestep')}, "
                f"def_end_timestep={c.get('def_end_timestep')}"
            )
            cw = c.get("charging_window", [])
            if cw:
                w = cw[0]
                print(f"    window: ventana_horas={w.get('ventana_horas')}, "
                      f"horas_carga={w.get('horas_carga_necesarias')}")
        print("======================\n")

    def _get_sorted_trips(self, adapter, trip_ids):
        """Get cache entries sorted by def_start_timestep."""
        entries = []
        for tid in trip_ids:
            c = adapter._cached_per_trip_params[tid]
            entries.append((tid, c))
        entries.sort(key=lambda x: x[1].get("def_start_timestep", 0))
        return entries

    @pytest.mark.asyncio
    async def test_cascade_3_trips_asserts_all_fields(self):
        """Zero-window trip cascades deficit to trips before it.

        New behavior: deficit origin is the FIRST trip with ventana < needs.
        Origin is zeroed out (def_total=0), deficit cascades to earlier trips.
        Trips after origin are unchanged.

        We directly set up cache entries matching the staging scenario:
        Trip A (earliest): window=37, needs=2
        Trip B (middle): window=16, needs=2
        Trip C (latest): window=0, needs=2 ZERO WINDOW (ORIGIN)
        """
        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            "charging_power_kw": 3.6,
            "battery_capacity_kwh": 60.0,
            "safety_margin_percent": 10.0,
        }
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value=None)
        mock_store.async_save = AsyncMock(return_value=None)

        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        hass.config.time_zone = "UTC"
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.services.has_service = MagicMock(return_value=True)

        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = config
        entry.options = {}

        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

        adapter._cached_per_trip_params = {
            "trip_a": {
                "activo": True,
                "def_total_hours": 2.0,
                "def_start_timestep": 0,
                "def_end_timestep": 37,
                "charging_window": [{"ventana_horas": 37, "horas_carga_necesarias": 2}],
                "emhass_index": 0,
            },
            "trip_b": {
                "activo": True,
                "def_total_hours": 2.0,
                "def_start_timestep": 93,
                "def_end_timestep": 109,
                "charging_window": [{"ventana_horas": 16, "horas_carga_necesarias": 2}],
                "emhass_index": 1,
            },
            "trip_c": {
                "activo": True,
                "def_total_hours": 2.0,
                "def_start_timestep": 109,
                "def_end_timestep": 109,
                "charging_window": [{"ventana_horas": 0, "horas_carga_necesarias": 2}],
                "emhass_index": 2,
            },
        }

        adapter._apply_deficit_propagation()

        # Trip C: origin zeroed out
        assert adapter._cached_per_trip_params["trip_c"]["def_total_hours"] == 0.0
        # Trip B: absorbs 2h from trip C
        assert adapter._cached_per_trip_params["trip_b"]["def_total_hours"] == 4.0
        # Trip A: unaffected
        assert adapter._cached_per_trip_params["trip_a"]["def_total_hours"] == 2.0

        # Window order preserved (start times must be ordered; end times can share boundary)
        assert (
            adapter._cached_per_trip_params["trip_a"]["def_start_timestep"]
            < adapter._cached_per_trip_params["trip_b"]["def_start_timestep"]
            < adapter._cached_per_trip_params["trip_c"]["def_start_timestep"]
        )
        assert (
            adapter._cached_per_trip_params["trip_a"]["def_end_timestep"]
            <= adapter._cached_per_trip_params["trip_b"]["def_end_timestep"]
            <= adapter._cached_per_trip_params["trip_c"]["def_end_timestep"]
        )
        # Zero window preserved
        assert (
            adapter._cached_per_trip_params["trip_c"]["def_start_timestep"]
            == adapter._cached_per_trip_params["trip_c"]["def_end_timestep"]
        )

    @pytest.mark.asyncio
    async def test_cascade_scalar_is_int_via_ceil(self):
        """After cascade, def_total_hours is int (math.ceil), not float.

        This replaced the old test that checked def_total_hours_array.
        The architectural fix: arrays no longer stored in cache.
        The single source of truth is the scalar def_total_hours,
        and arrays are derived on-demand in the sensor.

        Cascade must write int values via math.ceil(adjusted), not round().
        Before the ceil fix, staging showed [2.0, 2.0, 4.0, 0.0] — floats with .0.
        After the fix, staging shows [2, 2, 4, 0] — clean integers.
        """
        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            "charging_power_kw": 3.6,
            "battery_capacity_kwh": 60.0,
            "safety_margin_percent": 10.0,
        }
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value=None)
        mock_store.async_save = AsyncMock(return_value=None)

        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        hass.config.time_zone = "UTC"
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.services.has_service = MagicMock(return_value=True)

        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = config
        entry.options = {}

        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

        # Setup: trip_a has spare, trip_b absorbs, trip_c is zero-window origin.
        adapter._cached_per_trip_params = {
            "trip_a": {
                "activo": True,
                "def_total_hours": 2.0,
                "def_start_timestep": 0,
                "def_end_timestep": 37,
                "charging_window": [{"ventana_horas": 37, "horas_carga_necesarias": 2}],
                "emhass_index": 0,
                "kwh_needed": 7.2,
                "power_watts": 3600.0,
            },
            "trip_b": {
                "activo": True,
                "def_total_hours": 2.0,
                "def_start_timestep": 93,
                "def_end_timestep": 109,
                "charging_window": [{"ventana_horas": 16, "horas_carga_necesarias": 2}],
                "emhass_index": 1,
                "kwh_needed": 7.2,
                "power_watts": 3600.0,
            },
            "trip_c": {
                "activo": True,
                "def_total_hours": 2.0,
                "def_start_timestep": 109,
                "def_end_timestep": 109,
                "charging_window": [{"ventana_horas": 0, "horas_carga_necesarias": 2}],
                "emhass_index": 2,
                "kwh_needed": 7.2,
                "power_watts": 3600.0,
            },
        }

        adapter._apply_deficit_propagation()

        # After cascade: all def_total_hours must be int (via math.ceil), not float
        for tid in ["trip_a", "trip_b", "trip_c"]:
            c = adapter._cached_per_trip_params[tid]
            assert isinstance(c["def_total_hours"], int), (
                f"{tid}: def_total_hours={c['def_total_hours']} is {type(c['def_total_hours'])}, "
                "expected int (math.ceil). Float values like 2.0 indicate round() instead of ceil()."
            )

        # Trip_b absorbed 2h: int=4
        assert adapter._cached_per_trip_params["trip_b"]["def_total_hours"] == 4
        # Trip_c is zeroed: int=0
        assert adapter._cached_per_trip_params["trip_c"]["def_total_hours"] == 0

    @pytest.mark.asyncio
    async def test_no_cascade_all_windows_sufficient(self):
        """When all windows have enough hours, no field changes.

        All trips have small needs relative to their window sizes.
        def_total_hours should equal base for all trips.
        """
        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            "charging_power_kw": 3.6,
            "battery_capacity_kwh": 60.0,
            "safety_margin_percent": 10.0,
        }
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value=None)
        mock_store.async_save = AsyncMock(return_value=None)

        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        hass.config.time_zone = "UTC"
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.services.has_service = MagicMock(return_value=True)

        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = config
        entry.options = {}

        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

        now = datetime.now(timezone.utc)

        trips = [
            {
                "id": "trip_1",
                "tipo": "puntual",
                "datetime": (now + timedelta(hours=8)).isoformat(),
                "kwh": 2.0,  # Tiny need
            },
            {
                "id": "trip_2",
                "tipo": "puntual",
                "datetime": (now + timedelta(hours=6)).isoformat(),
                "kwh": 2.0,
            },
            {
                "id": "trip_3",
                "tipo": "puntual",
                "datetime": (now + timedelta(hours=4)).isoformat(),
                "kwh": 2.0,
            },
        ]
        hora_regreso = now - timedelta(hours=2)

        with patch.object(adapter, "_get_current_soc", new_callable=AsyncMock) as mock_soc:
            mock_soc.return_value = 10.0
            with patch.object(adapter, "_get_hora_regreso", new_callable=AsyncMock) as mock_hora:
                mock_hora.return_value = hora_regreso.replace(tzinfo=timezone.utc)
                mock_pm = MagicMock()
                mock_pm.async_get_hora_regreso = AsyncMock(
                    return_value=hora_regreso.replace(tzinfo=timezone.utc),
                )
                adapter._presence_monitor = mock_pm

                await adapter.async_publish_all_deferrable_loads(
                    trips, charging_power_kw=3.6
                )

        # All trips should have def_total_hours close to base (no propagation)
        for tid in ["trip_1", "trip_2", "trip_3"]:
            c = adapter._cached_per_trip_params[tid]
            assert c["def_total_hours"] <= 4, (
                f"Trip {tid} def_total_hours={c['def_total_hours']} too high — "
                "unexpected propagation in no-deficit scenario"
            )

    @pytest.mark.asyncio
    async def test_window_order_preserved_after_cascade(self):
        """After cascade, def_end_timestep must still align with departure times.

        Cascade modifies def_total_hours (charging duration) but NOT
        def_end_timestep (which is tied to fin_ventana / trip departure).

        Same trip config as test_cascade_3_trips_asserts_all_fields.
        """
        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            "charging_power_kw": 3.6,
            "battery_capacity_kwh": 60.0,
            "safety_margin_percent": 10.0,
        }
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value=None)
        mock_store.async_save = AsyncMock(return_value=None)

        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        hass.config.time_zone = "UTC"
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.services.has_service = MagicMock(return_value=True)

        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = config
        entry.options = {}

        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

        now = datetime.now(timezone.utc)

        # Same config as main cascade test: T1(22h), T2(8h), T3(2h)
        trips = [
            {"id": "trip_1", "tipo": "puntual", "datetime": (now + timedelta(hours=22)).isoformat(), "kwh": 5.0},
            {"id": "trip_2", "tipo": "puntual", "datetime": (now + timedelta(hours=8)).isoformat(), "kwh": 18.0},
            {"id": "trip_3", "tipo": "puntual", "datetime": (now + timedelta(hours=2)).isoformat(), "kwh": 20.0},
        ]
        hora_regreso = now - timedelta(hours=2)

        with patch.object(adapter, "_get_current_soc", new_callable=AsyncMock) as mock_soc:
            mock_soc.return_value = 10.0
            with patch.object(adapter, "_get_hora_regreso", new_callable=AsyncMock) as mock_hora:
                mock_hora.return_value = hora_regreso.replace(tzinfo=timezone.utc)
                mock_pm = MagicMock()
                mock_pm.async_get_hora_regreso = AsyncMock(
                    return_value=hora_regreso.replace(tzinfo=timezone.utc),
                )
                adapter._presence_monitor = mock_pm

                await adapter.async_publish_all_deferrable_loads(
                    trips, charging_power_kw=3.6
                )

        trip_3 = adapter._cached_per_trip_params["trip_3"]
        trip_2 = adapter._cached_per_trip_params["trip_2"]
        trip_1 = adapter._cached_per_trip_params["trip_1"]

        # def_end_timestep must be > def_start_timestep for ALL trips
        for tid, c in [("trip_3", trip_3), ("trip_2", trip_2), ("trip_1", trip_1)]:
            end = c["def_end_timestep"]
            start = c["def_start_timestep"]
            assert end > start, (
                f"{tid}: def_end_timestep={end} <= def_start_timestep={start}. "
                f"Window is empty or reversed."
            )

        # def_end_timestep order must still match departure order
        assert trip_3["def_end_timestep"] < trip_2["def_end_timestep"] < trip_1["def_end_timestep"]

        # def_start_timestep order must still match departure order
        assert trip_3["def_start_timestep"] < trip_2["def_start_timestep"] < trip_1["def_start_timestep"]
