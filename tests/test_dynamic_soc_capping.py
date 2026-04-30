"""Unit tests for the dynamic SOC capping algorithm.

Tests the pure function `calculate_dynamic_soc_limit()` which computes a
degradation-aware SOC upper bound from idle hours, post-trip SOC, and
battery parameters.

Formula reference:
    risk = t_hours * (soc_post_trip - 35) / 65
    If risk <= 0: return 100.0
    limit = 35 + 65 * (1 / (1 + risk / t_base))

TDD: These tests are written BEFORE implementation.
Scenario A (T011) covers commute-first then large trip.
Scenario B (T012) covers large trip drain then commutes.
"""

from __future__ import annotations

import math

import pytest


class TestDynamicSOCCapping:
    """Test suite for dynamic SOC capping algorithm (User Story 1).

    Each test class covers one verified scenario from spec.md.
    """

    # ------------------------------------------------------------------
    # Scenario A: Commute first, then large trip (battery=30kWh)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "t_hours,soc_post_trip,battery_capacity_kwh,t_base,expected",
        [
            pytest.param(
                22,
                41,
                30,
                24.0,
                94.93,
                id="Scenario A main: 22h idle, 41% post-trip, 30kWh, t_base=24",
            ),
            # T3: commute after drain, 48h idle
            pytest.param(
                48,
                41,
                30,
                24.0,
                89.93,
                id="Scenario A T3: 48h idle, 41% post-trip -> 89.9%",
            ),
            # T4: semi-large, post-trip 10% -> risk negative -> 100%
            pytest.param(
                22,
                10,
                30,
                24.0,
                100.0,
                id="Scenario A T4: post-trip 10%, risk negative -> 100%",
            ),
        ],
    )
    def test_scenario_a_commute_then_large_trip(
        self,
        t_hours: float,
        soc_post_trip: float,
        battery_capacity_kwh: float,
        t_base: float,
        expected: float,
    ) -> None:
        """Scenario A: commute first, then large trip.

        Small trips at 41% SOC + 22h idle -> limit ~94.9%, need 61% -> OK
        Large trip draining to 0% -> risk negative -> 100% allowed
        Long idle (48h) with 41% post-trip -> tighter cap ~89.9%
        Post-trip below 35% (sweet spot) -> no degradation risk -> 100%
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_dynamic_soc_limit,
        )

        result = calculate_dynamic_soc_limit(
            t_hours, soc_post_trip, battery_capacity_kwh, t_base=t_base
        )
        assert result == pytest.approx(expected, rel=0.01)

    # ------------------------------------------------------------------
    # Scenario B: Large trip drain first, then commutes
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "t_hours,soc_post_trip,battery_capacity_kwh,t_base,expected",
        [
            # Main Scenario B: 8h idle, 0% post-trip -> large trip drain -> 100%
            pytest.param(
                8,
                0,
                30,
                24.0,
                100.0,
                id="Scenario B main: 8h idle, 0% post-trip -> 100%",
            ),
        ],
    )
    def test_scenario_b_large_drain_first(
        self,
        t_hours: float,
        soc_post_trip: float,
        battery_capacity_kwh: float,
        t_base: float,
        expected: float,
    ) -> None:
        """Scenario B: large trip drain first, then commutes.

        Large trip draining battery to 0% -> negative risk -> 100% SOC allowed.
        After this trip, subsequent commutes will see ~94.9% cap.
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_dynamic_soc_limit,
        )

        result = calculate_dynamic_soc_limit(
            t_hours, soc_post_trip, battery_capacity_kwh, t_base=t_base
        )
        assert result == pytest.approx(expected, rel=0.01)
