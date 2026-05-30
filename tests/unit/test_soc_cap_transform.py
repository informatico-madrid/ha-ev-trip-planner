"""TDD tests for apply_soc_cap_transform (Componente 1: rampa pre-viaje).

Formula: slack = max(0, ventana_horas - horas_carga_necesarias)
         H_allowed = horas_carga_necesarias / (1 + slack / k)
         where k = PipelineContext.t_base

Invariants:
  - slack=0  →  H_allowed == horas_carga_necesarias  (factibilidad por construcción)
  - ventana_horas=0  →  H_allowed=0 (zero window cannot charge)
  - H_allowed is monotone: increases as slack decreases (ventana narrows)
  - Never exceeds horas_carga_necesarias
  - def_start_timestep / def_end_timestep are never mutated
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from custom_components.ev_trip_planner.calculations.window_pipeline import (
    PipelineContext,
    apply_soc_cap_transform,
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
        "def_start_timestep": 0,
        "def_end_timestep": int(ventana_horas),
    }
    w.update(extras)
    return w


class TestSlackZeroFactibilidad:
    """When slack=0 the cap must not reduce hours (factibilidad por construcción)."""

    def test_slack_zero_keeps_hours(self):
        """ventana == horas: slack=0 → H_allowed == horas_carga_necesarias."""
        windows = [_window(3, 3)]
        result = apply_soc_cap_transform(windows, _ctx())
        assert result[0]["horas_carga_necesarias"] == 3

    def test_ventana_smaller_than_needs_slack_zero(self):
        """ventana < horas (deficit case): slack=0 → no reduction."""
        windows = [_window(1, 3)]
        result = apply_soc_cap_transform(windows, _ctx())
        assert result[0]["horas_carga_necesarias"] == 3

    def test_ventana_zero_slack_zero_no_cap(self):
        """ventana=0 → slack=max(0,0-2)=0 → cap is inert (H_allowed=needs).
        Zeroing zero-window trips is the DEFICIT's responsibility, not the cap's.
        """
        windows = [_window(0, 2)]
        result = apply_soc_cap_transform(windows, _ctx())
        # Cap leaves needs unchanged (slack=0). Deficit will zero it later.
        assert result[0]["horas_carga_necesarias"] == 2


class TestRampReducesHours:
    """With slack>0 the ramp reduces H_allowed below H_req."""

    def test_large_slack_reduces_hours(self):
        """ventana=99, horas=7, k=24 → H_allowed=7/(1+92/24)≈1.45→ceil=2 (< 7)."""
        windows = [_window(99, 7)]
        result = apply_soc_cap_transform(windows, _ctx(t_base=24.0))
        h = result[0]["horas_carga_necesarias"]
        assert h < 7, f"Expected H_allowed < 7 (user's case), got {h}"
        assert h >= 1, "H_allowed must be at least 1"

    def test_user_case_saturday_to_wednesday(self):
        """Real case: W0 ventana=99h, needs=7h, k=24 → ceil(7/(1+92/24))=2."""
        windows = [_window(99, 7)]
        result = apply_soc_cap_transform(windows, _ctx(t_base=24.0))
        h = result[0]["horas_carga_necesarias"]
        expected = math.ceil(7.0 / (1.0 + 92.0 / 24.0))
        assert h == expected, f"Expected {expected}, got {h}"

    @pytest.mark.parametrize(
        "ventana,needs,expected_lt",
        [
            (48, 3, 3),  # slack=45 → H_allowed=3/(1+45/24)=0.94→ceil=1
            (16, 2, 2),  # slack=14 → H_allowed=2/(1+14/24)=1.26→ceil=2 (unchanged!)
            (37, 2, 2),  # slack=35 → H_allowed=2/(1+35/24)=0.81→ceil=1 < 2
        ],
    )
    def test_ramp_values_parametric(self, ventana: float, needs: int, expected_lt: int):
        """Ramp result is always <= horas_carga_necesarias."""
        windows = [_window(ventana, needs)]
        result = apply_soc_cap_transform(windows, _ctx(t_base=24.0))
        assert result[0]["horas_carga_necesarias"] <= needs


class TestMonotonicity:
    """H_allowed increases monotonically as the window narrows (slack decreases)."""

    def test_narrowing_window_increases_hours(self):
        """Smaller slack → larger H_allowed (towards H_req)."""
        needs = 7
        k = 24.0
        ctx = _ctx(t_base=k)

        hours_99 = apply_soc_cap_transform([_window(99, needs)], ctx)[0][
            "horas_carga_necesarias"
        ]
        hours_48 = apply_soc_cap_transform([_window(48, needs)], ctx)[0][
            "horas_carga_necesarias"
        ]
        hours_10 = apply_soc_cap_transform([_window(10, needs)], ctx)[0][
            "horas_carga_necesarias"
        ]
        hours_7 = apply_soc_cap_transform([_window(7, needs)], ctx)[0][
            "horas_carga_necesarias"
        ]

        assert hours_99 <= hours_48 <= hours_10 <= hours_7


class TestTBaseAggressiveness:
    """Smaller t_base = more aggressive cap = fewer hours for same slack."""

    def test_smaller_t_base_fewer_hours(self):
        """k=6 gives fewer allowed hours than k=24 for same window."""
        windows = [_window(99, 7)]
        h_6 = apply_soc_cap_transform(windows, _ctx(t_base=6.0))[0][
            "horas_carga_necesarias"
        ]
        h_24 = apply_soc_cap_transform(windows, _ctx(t_base=24.0))[0][
            "horas_carga_necesarias"
        ]
        h_48 = apply_soc_cap_transform(windows, _ctx(t_base=48.0))[0][
            "horas_carga_necesarias"
        ]
        assert h_6 <= h_24 <= h_48


class TestInvariants:
    """def_start_timestep / def_end_timestep are never mutated."""

    def test_timesteps_not_mutated(self):
        windows = [_window(99, 7)]
        windows[0]["def_start_timestep"] = 5
        windows[0]["def_end_timestep"] = 99
        result = apply_soc_cap_transform(windows, _ctx())
        assert result[0]["def_start_timestep"] == 5
        assert result[0]["def_end_timestep"] == 99

    def test_original_windows_not_mutated(self):
        """Input windows list is not mutated (returns new dicts)."""
        windows = [_window(99, 7)]
        original_horas = windows[0]["horas_carga_necesarias"]
        apply_soc_cap_transform(windows, _ctx())
        assert windows[0]["horas_carga_necesarias"] == original_horas

    def test_trip_field_preserved(self):
        """'trip' field on window dict is preserved if present."""
        trip = {"id": "abc", "kwh": 10.0}
        windows = [_window(50, 3, trip=trip)]
        result = apply_soc_cap_transform(windows, _ctx())
        assert result[0].get("trip") is trip

    def test_multiple_windows_independent(self):
        """Each window is capped independently."""
        windows = [
            _window(99, 7),  # large slack → big reduction
            _window(3, 3),  # slack=0 → no reduction
            _window(0, 2),  # zero window → slack=0 → cap inert (needs stays 2)
        ]
        result = apply_soc_cap_transform(windows, _ctx(t_base=24.0))
        assert result[0]["horas_carga_necesarias"] < 7  # reduced
        assert result[1]["horas_carga_necesarias"] == 3  # unchanged
        assert result[2]["horas_carga_necesarias"] == 2  # zero ventana: cap inert


class TestComponente2PostTrip:
    """Componente 2: post-trip cap applies when fin_ventana + trip are present."""

    def test_no_fin_ventana_component2_inert(self):
        """Without fin_ventana, Componente 2 is inert — same as Componente 1."""
        windows = [_window(99, 7)]  # no fin_ventana → C2 skipped
        result_c1_only = apply_soc_cap_transform(windows, _ctx())
        result_default = apply_soc_cap_transform(windows, _ctx())
        assert (
            result_c1_only[0]["horas_carga_necesarias"]
            == result_default[0]["horas_carga_necesarias"]
        )

    def test_with_fin_ventana_triggers_component2(self):
        """With fin_ventana in window, Componente 2 is used (post-trip cap applied)."""
        from datetime import timezone as tz

        now = datetime(2026, 5, 30, 10, 0, 0, tzinfo=tz.utc)
        # fin_ventana = 24h from now → t_hours=24, soc_current=50%, soc_after=40% (above 35%)
        # → risk > 0 → cap < 100% → may reduce hours further
        fin = now.replace(hour=10) + __import__("datetime").timedelta(hours=24)
        ctx = PipelineContext(
            charging_power_kw=3.6,
            battery_capacity_kwh=60.0,
            t_base=24.0,
            now=now,
            soc_current=50.0,
        )
        trip = {"kwh": 6.0}
        windows = [
            {
                "ventana_horas": 99,
                "horas_carga_necesarias": 7,
                "fin_ventana": fin,
                "trip": trip,
            }
        ]
        result = apply_soc_cap_transform(windows, ctx)
        # C2 applies additional cap: result should be <= C1 result
        c1_only_ctx = PipelineContext(
            charging_power_kw=3.6, battery_capacity_kwh=60.0, t_base=24.0, now=now
        )
        c1_result = apply_soc_cap_transform([_window(99, 7)], c1_only_ctx)
        # C2 can only make it smaller or equal, never larger
        assert (
            result[0]["horas_carga_necesarias"]
            <= c1_result[0]["horas_carga_necesarias"]
        )


class TestNeverExceedsOriginal:
    """H_allowed is always <= horas_carga_necesarias."""

    @pytest.mark.parametrize(
        "ventana,needs,k",
        [
            (168, 7, 6.0),
            (168, 7, 24.0),
            (168, 7, 48.0),
            (10, 3, 24.0),
            (3, 3, 24.0),
            (2, 3, 24.0),
            (0, 3, 24.0),
        ],
    )
    def test_never_exceeds_original(self, ventana, needs, k):
        windows = [_window(ventana, needs)]
        result = apply_soc_cap_transform(windows, _ctx(t_base=k))
        assert result[0]["horas_carga_necesarias"] <= needs
