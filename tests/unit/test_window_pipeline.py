"""TDD tests for apply_deficit_transform and run_window_pipeline.

Fase 2: apply_deficit_transform must produce identical output to
calling calculate_hours_deficit_propagation directly (thin wrapper).

Fase 3: run_window_pipeline must compose cap→deficit in the correct order,
preserving all invariants across the combined transformation.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from custom_components.ev_trip_planner.calculations.deficit import (
    calculate_hours_deficit_propagation,
)
from custom_components.ev_trip_planner.calculations.window_pipeline import (
    PipelineContext,
    apply_deficit_transform,
    apply_soc_cap_transform,
    run_window_pipeline,
)


def _ctx(t_base: float = 24.0) -> PipelineContext:
    return PipelineContext(
        charging_power_kw=3.6,
        battery_capacity_kwh=60.0,
        t_base=t_base,
        now=datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
    )


def _window(ventana_horas: float, horas_carga: int, **extras) -> dict:
    w = {
        "ventana_horas": ventana_horas,
        "horas_carga_necesarias": horas_carga,
    }
    w.update(extras)
    return w


# ---------------------------------------------------------------------------
# Fase 2: apply_deficit_transform
# ---------------------------------------------------------------------------


class TestApplyDeficitTransformMatchesPureFunction:
    """apply_deficit_transform is a thin wrapper — results must match direct call."""

    def test_single_window_no_deficit(self):
        """One window, no deficit: adjusted == original."""
        windows = [_window(10, 3)]
        ctx = _ctx()

        via_transform = apply_deficit_transform(windows, ctx)
        via_direct = calculate_hours_deficit_propagation(windows)

        assert (
            via_transform[0]["adjusted_def_total_hours"]
            == via_direct[0]["adjusted_def_total_hours"]
        )

    def test_two_windows_deficit_propagates(self):
        """Zero-window trip propagates its deficit to the earlier window."""
        windows = [
            _window(37, 2),
            _window(0, 2),
        ]
        ctx = _ctx()

        via_transform = apply_deficit_transform(windows, ctx)
        via_direct = calculate_hours_deficit_propagation(windows)

        for i in range(2):
            assert (
                via_transform[i]["adjusted_def_total_hours"]
                == via_direct[i]["adjusted_def_total_hours"]
            )

    def test_three_windows_matches_direct(self):
        """Three-window chain with mixed deficits."""
        windows = [
            _window(37, 2),
            _window(16, 2),
            _window(0, 2),
        ]
        ctx = _ctx()

        via_transform = apply_deficit_transform(windows, ctx)
        via_direct = calculate_hours_deficit_propagation(windows)

        for i in range(3):
            assert (
                via_transform[i]["adjusted_def_total_hours"]
                == via_direct[i]["adjusted_def_total_hours"]
            ), (
                f"Window {i}: transform={via_transform[i]['adjusted_def_total_hours']} vs direct={via_direct[i]['adjusted_def_total_hours']}"
            )

    def test_empty_windows(self):
        """Empty input returns empty output."""
        assert apply_deficit_transform([], _ctx()) == []


# ---------------------------------------------------------------------------
# Fase 3: run_window_pipeline
# ---------------------------------------------------------------------------


class TestRunWindowPipelineOrder:
    """SOC cap runs first; deficit propagation runs on capped values."""

    def test_cap_then_deficit_order(self):
        """Pipeline applies cap first (reduces needs), then deficit propagates."""
        # trip_a: large window (slack=35, k=24) → cap reduces needs 2→1
        # trip_b: zero window (slack=0) → cap leaves at 2, deficit zeroes it
        windows = [
            _window(37, 2),  # trip_a: slack=35 → H_allowed=2/(1+35/24)=0.81→ceil=1
            _window(0, 2),  # trip_b: zero window, deficit origin
        ]
        ctx = _ctx(t_base=24.0)
        result = run_window_pipeline(windows, ctx)

        # trip_b zeroed by zero window
        assert result[1]["adjusted_def_total_hours"] == 0
        # trip_a: absorbs deficit from trip_b IF spare available
        # After cap, trip_a needs=1. spare = max(0, 37-1) = 36.
        # trip_b deficit=2. trip_a absorbs 2. adjusted = 1+2 = 3.
        assert result[0]["adjusted_def_total_hours"] == 3

    def test_deficit_uses_capped_needs(self):
        """Deficit's spare calculation uses the SOC-capped horas_carga, not original."""
        # If cap were NOT applied, trip_a original needs=2 → spare=35
        # With cap, trip_a needs=1 → spare=36 (slightly different)
        # Either way, spare absorbs deficit. Key: pipeline runs cap first.
        windows = [
            _window(37, 2),
            _window(0, 2),
        ]
        result_pipeline = run_window_pipeline(windows, _ctx())
        # After pipeline: trip_a adjusted = 1(capped) + 2(absorbed) = 3
        a = result_pipeline[0]["adjusted_def_total_hours"]
        assert a == 3

    def test_deficit_alone_conserves_hours(self):
        """Deficit-only step conserves hours (+ unabsorbed carrier == original)."""
        windows = [
            _window(10, 3),
            _window(5, 2),
        ]
        total_original = sum(w["horas_carga_necesarias"] for w in windows)
        # Use only deficit (no SOC cap reduction)
        result = run_window_pipeline(
            windows, _ctx(), transforms=[apply_deficit_transform]
        )

        total_adjusted = sum(r["adjusted_def_total_hours"] for r in result)
        unabsorbed_carrier = result[0].get("deficit_hours_to_propagate", 0.0)

        assert math.isclose(
            total_adjusted + unabsorbed_carrier, total_original, abs_tol=0.1
        ), (
            f"Deficit alone: adjusted={total_adjusted} carrier={unabsorbed_carrier} original={total_original}"
        )

    def test_soc_cap_reduces_total_hours(self):
        """SOC cap intentionally reduces total hours when slack is large."""
        windows = [
            _window(99, 7),  # large slack → big reduction
            _window(16, 2),
        ]
        total_original = sum(w["horas_carga_necesarias"] for w in windows)
        result = run_window_pipeline(windows, _ctx(t_base=24.0))
        total_adjusted = sum(r["adjusted_def_total_hours"] for r in result)
        assert total_adjusted < total_original, (
            f"SOC cap should reduce total hours from {total_original} to less, got {total_adjusted}"
        )


class TestRunWindowPipelineInvariants:
    """Pipeline must preserve ordering invariants from deficit."""

    def test_timesteps_preserved_through_pipeline(self):
        """def_start_timestep / def_end_timestep survive the full pipeline."""
        windows = [
            {**_window(37, 2), "def_start_timestep": 0, "def_end_timestep": 37},
            {**_window(0, 2), "def_start_timestep": 50, "def_end_timestep": 50},
        ]
        result = run_window_pipeline(windows, _ctx())
        assert result[0].get("def_start_timestep") == 0
        assert result[0].get("def_end_timestep") == 37
        assert result[1].get("def_start_timestep") == 50
        assert result[1].get("def_end_timestep") == 50

    def test_empty_pipeline(self):
        """Empty windows list handled gracefully."""
        assert run_window_pipeline([], _ctx()) == []


class TestRunWindowPipelineCustomTransforms:
    """Custom transforms list overrides defaults."""

    def test_cap_only_transform(self):
        """Using only cap transform skips deficit propagation."""
        windows = [
            _window(99, 7),
            _window(0, 2),
        ]
        # Only cap, no deficit propagation
        result = run_window_pipeline(
            windows, _ctx(), transforms=[apply_soc_cap_transform]
        )
        # Cap reduces first window; zero window is inert (slack=0), needs unchanged
        assert result[0]["horas_carga_necesarias"] < 7
        assert result[1]["horas_carga_necesarias"] == 2  # cap inert on zero-ventana


class TestUserScenarioSaturdayWednesday:
    """Real scenario: SOC 33%, 4 windows [7,0,2,2] hours, W0 spans 99h."""

    def test_w0_reduced_from_7_to_small(self):
        """W0 with slack=92h, k=24 → H_allowed < 7. EMHASS can't front-load all 7h."""
        windows = [
            _window(99, 7),  # W0: ventana 0→99, needs 7h (large trip Wednesday)
            _window(0, 0),  # W1: zero window (simultaneous trip)
            _window(16, 2),  # W2: 2h needed
            _window(20, 2),  # W3: 2h needed
        ]
        result = run_window_pipeline(windows, _ctx(t_base=24.0))

        w0_adjusted = result[0]["adjusted_def_total_hours"]
        assert w0_adjusted < 7, (
            f"W0 should be capped below 7h (was {w0_adjusted}); "
            "EMHASS must not be able to front-load all charging immediately"
        )

    def test_w0_capped_below_7_for_user_scenario(self):
        """W0 with 92h slack (k=24) is capped to < 7h — EMHASS can't front-load all charging."""
        windows = [
            _window(99, 7),  # W0: user's case, Sat SOC 33%, Wednesday trip
            _window(0, 0),  # W1: zero window (concurrent trip)
            _window(16, 2),  # W2
            _window(20, 2),  # W3
        ]
        result = run_window_pipeline(windows, _ctx(t_base=24.0))
        w0_adjusted = result[0]["adjusted_def_total_hours"]
        assert w0_adjusted < 7, (
            f"W0 should be capped below 7h (slack=92, k=24), got {w0_adjusted}"
        )
        # W2 and W3 near trips: relatively less slack, needs still satisfied
        assert result[2]["adjusted_def_total_hours"] > 0
        assert result[3]["adjusted_def_total_hours"] > 0
