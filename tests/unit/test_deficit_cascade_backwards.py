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

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.calculations import (
    calculate_hours_deficit_propagation,
)
from custom_components.ev_trip_planner.const import (
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_VEHICLE_NAME,
)
from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter

# ===================================================================
# Shared invariant helper
# ===================================================================


def _assert_emhass_invariant(results):
    """Every window must charge no more than its available timeframe.
    A zero-timeframe window must charge exactly 0h.
    Violating this is precisely what makes EMHASS reject the optimization."""
    for r in results:
        ventana = r["ventana_horas"]
        adjusted = r["adjusted_def_total_hours"]
        if ventana == 0:
            assert adjusted == 0.0, (
                f"zero-timeframe window must charge 0h, got {adjusted}"
            )
        else:
            assert adjusted <= ventana, (
                f"adjusted {adjusted} exceeds timeframe {ventana}"
            )


# ===================================================================
# Pure function tests: algorithm correctness
# ===================================================================


class TestDeficitCascadeBackwards:
    """Verify cascading deficit propagates backwards through ALL windows in chain."""

    def test_two_trips_cascade_to_first(self):
        """T3 deficit origin charges ceil(window)=4h, cascades through T2 → T1 absorbs it.

        New algorithm: only the FIRST trip with own deficit is the origin.
        Origin charges ceil(window) if window > 0, deficit cascades backwards.
        Trips after origin are unchanged.

        T1: window=10h, needs=2h → spare=8h
        T2: window=4h, needs=4h → spare=0h (passes through)
        T3: window=4h, needs=6h → deficit=2h (ORIGIN, adjusted=ceil(4)=4)
        """
        windows = [
            {"ventana_horas": 10, "horas_carga_necesarias": 2},
            {"ventana_horas": 4, "horas_carga_necesarias": 4},
            {"ventana_horas": 4, "horas_carga_necesarias": 6},
        ]
        results = calculate_hours_deficit_propagation(windows)

        # T3: deficit origin — charges ceil(window)=4h
        assert results[2]["deficit_hours_propagated"] == 0.0
        assert results[2]["deficit_hours_to_propagate"] == 2.0
        assert results[2]["adjusted_def_total_hours"] == 4.0

        # T2: zero spare, passes deficit through unchanged
        assert results[1]["deficit_hours_propagated"] == 0.0
        assert results[1]["deficit_hours_to_propagate"] == 2.0
        assert results[1]["adjusted_def_total_hours"] == 4.0

        # T1: absorbs all 2h from carrier
        assert results[0]["deficit_hours_propagated"] == 2.0
        assert results[0]["deficit_hours_to_propagate"] == 0.0
        assert results[0]["adjusted_def_total_hours"] == 4.0

        _assert_emhass_invariant(results)

    def test_four_trips_chain_cascade(self):
        """4-trip chain: ALL trips with deficit contribute to the carrier.

        T1: window=10h, needs=2h → spare=8h — absorbs accumulated carrier
        T2: window=4h,  needs=5h → deficit=1h (charges ceil(4)=4h, carrier+=1)
        T3: window=4h,  needs=4h → spare=0h, passes carrier unchanged
        T4: window=4h,  needs=6h → deficit=2h (charges ceil(4)=4h, carrier+=2)

        Backward pass (last→first):
          i=3 T4: own_deficit=2, adjusted=4, carrier=2
          i=2 T3: own_deficit=0, spare=0, absorbed=0, carrier=2, adjusted=4
          i=1 T2: own_deficit=1, absorbed=0 (spare=0), adjusted=4, carrier+=1=3
          i=0 T1: spare=8, absorbed=3, carrier=0, adjusted=2+3=5
        """
        windows = [
            {"ventana_horas": 10, "horas_carga_necesarias": 2},
            {"ventana_horas": 4, "horas_carga_necesarias": 5},
            {"ventana_horas": 4, "horas_carga_necesarias": 4},
            {"ventana_horas": 4, "horas_carga_necesarias": 6},
        ]
        results = calculate_hours_deficit_propagation(windows)

        # T4: insufficient — charges ceil(4)=4, carrier=2
        assert results[3]["deficit_hours_propagated"] == 0.0
        assert results[3]["deficit_hours_to_propagate"] == 2.0
        assert results[3]["adjusted_def_total_hours"] == 4.0

        # T3: spare=0, passes carrier through
        assert results[2]["deficit_hours_propagated"] == 0.0
        assert results[2]["deficit_hours_to_propagate"] == 2.0
        assert results[2]["adjusted_def_total_hours"] == 4.0

        # T2: insufficient — charges ceil(4)=4, carrier+=1=3
        assert results[1]["deficit_hours_propagated"] == 0.0
        assert results[1]["deficit_hours_to_propagate"] == 3.0
        assert results[1]["adjusted_def_total_hours"] == 4.0

        # T1: spare=8, absorbs carrier=3 → adjusted=5
        assert results[0]["deficit_hours_propagated"] == 3.0
        assert results[0]["deficit_hours_to_propagate"] == 0.0
        assert results[0]["adjusted_def_total_hours"] == 5.0

        _assert_emhass_invariant(results)

    def test_first_trip_also_has_deficit(self):
        """All 3 trips are insufficient — carrier accumulates, first trip absorbs what fits.

        T1: window=2h, needs=3h → deficit=1h (charges ceil(2)=2h, carrier+=1)
        T2: window=4h, needs=5h → deficit=1h (charges ceil(4)=4h, carrier+=1)
        T3: window=4h, needs=6h → deficit=2h (charges ceil(4)=4h, carrier+=2)

        Backward pass (last→first):
          i=2 T3: own_deficit=2, adjusted=4, carrier=2
          i=1 T2: own_deficit=1, spare=0, absorbed=0, adjusted=4, carrier+=1=3
          i=0 T1: own_deficit=1, spare=0, absorbed=0, adjusted=2, carrier+=1=4
          No trip has spare → carrier=4 remains unabsorbed.
        """
        windows = [
            {"ventana_horas": 2, "horas_carga_necesarias": 3},
            {"ventana_horas": 4, "horas_carga_necesarias": 5},
            {"ventana_horas": 4, "horas_carga_necesarias": 6},
        ]
        results = calculate_hours_deficit_propagation(windows)

        # T3: charges ceil(4)=4h, carrier=2
        assert results[2]["deficit_hours_propagated"] == 0.0
        assert results[2]["deficit_hours_to_propagate"] == 2.0
        assert results[2]["adjusted_def_total_hours"] == 4.0

        # T2: no spare, charges ceil(4)=4h, carrier=3
        assert results[1]["deficit_hours_propagated"] == 0.0
        assert results[1]["deficit_hours_to_propagate"] == 3.0
        assert results[1]["adjusted_def_total_hours"] == 4.0

        # T1: no spare, charges ceil(2)=2h, carrier=4 (unabsorbed — no earlier trip)
        assert results[0]["deficit_hours_propagated"] == 0.0
        assert results[0]["deficit_hours_to_propagate"] == 4.0
        assert results[0]["adjusted_def_total_hours"] == 2.0

        _assert_emhass_invariant(results)

    def test_five_windows_second_and_fourth_collapsed_both_propagate(self):
        """Production bug reproduction: 5 trips; windows index 1 (2nd) and 3 (4th)
        have 0h available but need 2h. BOTH must zero out and propagate backwards
        to the immediately previous window with spare capacity.

        W0: ventana=106, needs=5 → absorbs W1's 2h          → 7
        W1: ventana=0,   needs=2 → collapsed, zeroed         → 0
        W2: ventana=16,  needs=2 → absorbs W3's 2h           → 4
        W3: ventana=0,   needs=2 → collapsed, zeroed         → 0  <-- BUG: stays 2
        W4: ventana=16,  needs=2 → unaffected                → 2

        Production incident:
          def_start_timestep: [0, 108, 112, 132, 136]
          def_end_timestep:   [106, 108, 128, 132, 152]
          def_total_hours:    [7, 0, 2, 2, 2]  ← W3 kept 2h with 0h timeframe
        """
        windows = [
            {"ventana_horas": 106, "horas_carga_necesarias": 5},
            {"ventana_horas": 0, "horas_carga_necesarias": 2},
            {"ventana_horas": 16, "horas_carga_necesarias": 2},
            {"ventana_horas": 0, "horas_carga_necesarias": 2},
            {"ventana_horas": 16, "horas_carga_necesarias": 2},
        ]
        results = calculate_hours_deficit_propagation(windows)
        adjusted = [r["adjusted_def_total_hours"] for r in results]

        assert adjusted[3] == 0.0, f"W3 (collapsed) must be 0h, got {adjusted[3]}"
        assert adjusted == [7.0, 0.0, 4.0, 0.0, 2.0]
        assert results[2]["deficit_hours_propagated"] == 2.0
        assert results[0]["deficit_hours_propagated"] == 2.0
        _assert_emhass_invariant(results)

    def test_consecutive_collapsed_windows_accumulate_to_earlier(self):
        """Edge case: two adjacent zero-timeframe windows — the deficit of BOTH
        must accumulate and propagate to the first window with spare capacity.

        W0: ventana=20, needs=2 → absorbs W2's 2h + W1's 2h = 4h → 6
        W1: ventana=0,  needs=2 → collapsed, zeroed              → 0
        W2: ventana=0,  needs=2 → collapsed, zeroed              → 0
        """
        windows = [
            {"ventana_horas": 20, "horas_carga_necesarias": 2},
            {"ventana_horas": 0, "horas_carga_necesarias": 2},
            {"ventana_horas": 0, "horas_carga_necesarias": 2},
        ]
        results = calculate_hours_deficit_propagation(windows)
        adjusted = [r["adjusted_def_total_hours"] for r in results]

        assert adjusted == [6.0, 0.0, 0.0]
        assert results[0]["deficit_hours_propagated"] == 4.0
        assert results[1]["deficit_hours_to_propagate"] == 4.0
        _assert_emhass_invariant(results)


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
                print(
                    f"    window: ventana_horas={w.get('ventana_horas')}, "
                    f"horas_carga={w.get('horas_carga_necesarias')}"
                )
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
                "p_deferrable_matrix": [
                    [3600.0 if 100 <= i < 102 else 0.0 for i in range(168)]
                ],  # BUG: 2h charging at slots 100-101 BEFORE cascade
            },
        }

        adapter._run_window_pipeline()

        # Trip C: origin zeroed out (zero window cannot charge)
        assert adapter._cached_per_trip_params["trip_c"]["def_total_hours"] == 0
        # Trip B: absorbs 2h from trip C
        assert adapter._cached_per_trip_params["trip_b"]["def_total_hours"] == 4
        # Trip A: SOC cap ramp reduces it (ventana=37h, needs=2h, slack=35, k=24 →
        # H_allowed=2/(1+35/24)≈0.81 → ceil→1). Deficit carrier=0 at this point.
        assert adapter._cached_per_trip_params["trip_a"]["def_total_hours"] == 1

        # p_deferrable_matrix must be recalculated after deficit propagation.
        # Origin trip_c with def_total=0 must have all-zeros matrix.
        trip_c_matrix = adapter._cached_per_trip_params["trip_c"].get(
            "p_deferrable_matrix", []
        )
        assert len(trip_c_matrix) > 0, "trip_c should have p_deferrable_matrix"
        trip_c_row = trip_c_matrix[0]
        assert all(v == 0 for v in trip_c_row), (
            f"trip_c p_deferrable_matrix should be all zeros (origin with def_total=0), "
            f"got non-zero values at indices {[i for i, v in enumerate(trip_c_row) if v != 0]}"
        )

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

        adapter._run_window_pipeline()

        # After cascade: all def_total_hours must be int (via math.ceil), not float
        for tid in ["trip_a", "trip_b", "trip_c"]:
            c = adapter._cached_per_trip_params[tid]
            assert isinstance(c["def_total_hours"], int), (
                f"{tid}: def_total_hours={c['def_total_hours']} is {type(c['def_total_hours'])}, "
                "expected int (math.ceil). Float values like 2.0 indicate round() instead of ceil()."
            )

        # Trip_b absorbed 2h: int=4
        assert adapter._cached_per_trip_params["trip_b"]["def_total_hours"] == 4
        # Trip_c keeps its original: int=0 (CORRECT - zero window has zero charging hours)
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

        with patch.object(
            adapter, "_get_current_soc", new_callable=AsyncMock
        ) as mock_soc:
            mock_soc.return_value = 10.0
            with patch.object(
                adapter, "_get_hora_regreso", new_callable=AsyncMock
            ) as mock_hora:
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
            {
                "id": "trip_1",
                "tipo": "puntual",
                "datetime": (now + timedelta(hours=22)).isoformat(),
                "kwh": 5.0,
            },
            {
                "id": "trip_2",
                "tipo": "puntual",
                "datetime": (now + timedelta(hours=8)).isoformat(),
                "kwh": 18.0,
            },
            {
                "id": "trip_3",
                "tipo": "puntual",
                "datetime": (now + timedelta(hours=2)).isoformat(),
                "kwh": 20.0,
            },
        ]
        hora_regreso = now - timedelta(hours=2)

        with patch.object(
            adapter, "_get_current_soc", new_callable=AsyncMock
        ) as mock_soc:
            mock_soc.return_value = 10.0
            with patch.object(
                adapter, "_get_hora_regreso", new_callable=AsyncMock
            ) as mock_hora:
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
        assert (
            trip_3["def_end_timestep"]
            < trip_2["def_end_timestep"]
            < trip_1["def_end_timestep"]
        )

        # def_start_timestep order must still match departure order
        assert (
            trip_3["def_start_timestep"]
            < trip_2["def_start_timestep"]
            < trip_1["def_start_timestep"]
        )
