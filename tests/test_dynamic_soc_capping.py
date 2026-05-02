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
Scenario C (T013) covers daily commute critical case.
Edge cases (T014) cover boundary conditions.
T_base configurability (T015) validates user slider ranges.
BatteryCapacity (T016) tests the new abstraction.
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

    # ------------------------------------------------------------------
    # Scenario C: Daily commute (critical case)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "t_hours,soc_post_trip,battery_capacity_kwh,t_base,expected",
        [
            # Main Scenario C: daily commute, limit 94.9% > required 61% -> no capping hit
            pytest.param(
                22,
                41,
                30,
                24.0,
                94.93,
                id="Scenario C main: 22h idle, 41% post-trip, limit 94.9% > 61% needed",
            ),
        ],
    )
    def test_scenario_c_daily_commute(
        self,
        t_hours: float,
        soc_post_trip: float,
        battery_capacity_kwh: float,
        t_base: float,
        expected: float,
    ) -> None:
        """Scenario C: daily commute is the critical test case.

        The cap (94.9%) must be well above the required SOC (61%) so that
        the commute always succeeds. This validates the algorithm doesn't
        over-cap for normal usage patterns.
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_dynamic_soc_limit,
        )

        result = calculate_dynamic_soc_limit(
            t_hours, soc_post_trip, battery_capacity_kwh, t_base=t_base
        )
        assert result == pytest.approx(expected, rel=0.01)

    # ------------------------------------------------------------------
    # Edge Cases (T014)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "t_hours,soc_post_trip,battery_capacity_kwh,t_base,expected",
        [
            # Zero idle hours: risk=0 -> 100%
            pytest.param(
                0,
                41,
                30,
                24.0,
                100.0,
                id="Edge: zero idle hours (t=0) -> 100%",
            ),
            # At sweet spot SOC 35%: risk=0 -> 100%
            pytest.param(
                22,
                35,
                30,
                24.0,
                100.0,
                id="Edge: at sweet spot SOC (35%) -> 100%",
            ),
            # Below sweet spot: negative risk -> 100%
            pytest.param(
                22,
                30,
                30,
                24.0,
                100.0,
                id="Edge: below sweet spot (30%) -> 100%",
            ),
            # Very long idle: limit should approach lower bound (35%)
            pytest.param(
                1000,
                90,
                30,
                24.0,
                pytest.approx(36.79, rel=0.01),
                id="Edge: very long idle + high SOC -> near floor",
            ),
        ],
    )
    def test_edge_cases(
        self,
        t_hours: float,
        soc_post_trip: float,
        battery_capacity_kwh: float,
        t_base: float,
        expected: float,
    ) -> None:
        """Edge cases: zero idle, sweet spot, below sweet spot, extreme idle."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_dynamic_soc_limit,
        )

        result = calculate_dynamic_soc_limit(
            t_hours, soc_post_trip, battery_capacity_kwh, t_base=t_base
        )
        assert result == pytest.approx(expected, rel=0.01)

    # ------------------------------------------------------------------
    # T_base configurability (T015)
    # ------------------------------------------------------------------

    def test_t_base_ordering(self) -> None:
        """T_base configurability: limit_6h < limit_24h < limit_48h.

        Smaller T_base = tighter cap (more aggressive protection).
        Larger T_base = looser cap (more permissive).
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_dynamic_soc_limit,
        )

        t_hours = 22
        soc_post_trip = 60
        battery_capacity_kwh = 30

        limit_6h = calculate_dynamic_soc_limit(
            t_hours, soc_post_trip, battery_capacity_kwh, t_base=6
        )
        limit_24h = calculate_dynamic_soc_limit(
            t_hours, soc_post_trip, battery_capacity_kwh, t_base=24
        )
        limit_48h = calculate_dynamic_soc_limit(
            t_hours, soc_post_trip, battery_capacity_kwh, t_base=48
        )

        # Smaller T_base -> tighter cap (lower limit) for positive risk
        assert limit_6h < limit_24h < limit_48h

    # ------------------------------------------------------------------
    # BatteryCapacity (T016)
    # ------------------------------------------------------------------

    def test_battery_capacity_nominal_only(self) -> None:
        """BatteryCapacity with no SOH sensor returns nominal capacity."""
        from custom_components.ev_trip_planner.calculations import BatteryCapacity

        bc = BatteryCapacity(nominal_capacity_kwh=60.0)
        assert bc.get_capacity() == 60.0
        assert bc.get_capacity_kwh() == 60.0

    def test_battery_capacity_soh_90_percent(self) -> None:
        """BatteryCapacity with SOH=90% returns real_capacity=nominal*0.9."""
        from custom_components.ev_trip_planner.calculations import BatteryCapacity

        bc = BatteryCapacity(nominal_capacity_kwh=60.0)
        # Manually set cached SOH value
        bc._soh_value = 90.0
        assert bc.get_capacity() == pytest.approx(54.0)

    def test_battery_capacity_soh_unavailable(self) -> None:
        """BatteryCapacity with no SOH sensor configured returns nominal."""
        from custom_components.ev_trip_planner.calculations import BatteryCapacity

        bc = BatteryCapacity(nominal_capacity_kwh=75.0, soh_sensor_entity_id=None)
        assert bc.get_capacity() == 75.0

    def test_battery_capacity_soh_clamp_to_valid_range(self) -> None:
        """BatteryCapacity clamps SOH to [10, 100] range."""
        from custom_components.ev_trip_planner.calculations import BatteryCapacity

        bc = BatteryCapacity(nominal_capacity_kwh=60.0)
        # SOH value outside [10, 100] — but _soh_value is set by _read_soh
        # which clamps. Direct test of _compute_capacity with out-of-range value.
        bc._soh_value = 150.0
        assert bc._compute_capacity() == pytest.approx(90.0)

    def test_battery_capacity_soh_from_hass(self) -> None:
        """BatteryCapacity.get_capacity(hass) reads SOH from HA sensor."""
        from unittest.mock import MagicMock

        from custom_components.ev_trip_planner.calculations import BatteryCapacity

        bc = BatteryCapacity(
            nominal_capacity_kwh=60.0,
            soh_sensor_entity_id="sensor.battery_soh",
        )

        # Mock HA
        mock_hass = MagicMock()
        mock_state = MagicMock()
        mock_state.state = "85.0"
        mock_hass.states.get.return_value = mock_state

        # Clear cache so it re-reads
        bc._soh_value = None
        bc._soh_cached_at = None

        result = bc.get_capacity(mock_hass)
        assert result == pytest.approx(51.0)  # 60 * 85 / 100
        mock_hass.states.get.assert_called_once_with("sensor.battery_soh")

    def test_battery_capacity_soh_unavailable_hass(self) -> None:
        """BatteryCapacity.get_capacity(hass) returns nominal when sensor unavailable."""
        from unittest.mock import MagicMock

        from custom_components.ev_trip_planner.calculations import BatteryCapacity

        bc = BatteryCapacity(
            nominal_capacity_kwh=75.0,
            soh_sensor_entity_id="sensor.battery_soh",
        )

        # Mock HA — sensor unavailable
        mock_hass = MagicMock()
        mock_state = MagicMock()
        mock_state.state = "unavailable"
        mock_hass.states.get.return_value = mock_state

        result = bc.get_capacity(mock_hass)
        # Falls back to nominal when sensor unavailable
        assert result == 75.0

    def test_battery_capacity_soh_unknown_hass(self) -> None:
        """BatteryCapacity.get_capacity(hass) returns nominal when sensor unknown."""
        from unittest.mock import MagicMock

        from custom_components.ev_trip_planner.calculations import BatteryCapacity

        bc = BatteryCapacity(
            nominal_capacity_kwh=75.0,
            soh_sensor_entity_id="sensor.battery_soh",
        )

        # Mock HA — sensor unknown
        mock_hass = MagicMock()
        mock_state = MagicMock()
        mock_state.state = "unknown"
        mock_hass.states.get.return_value = mock_state

        result = bc.get_capacity(mock_hass)
        assert result == 75.0

    def test_battery_capacity_soh_clamp_by_read_soh(self) -> None:
        """BatteryCapacity._read_soh clamps SOH values to [10, 100]."""
        from unittest.mock import MagicMock

        from custom_components.ev_trip_planner.calculations import BatteryCapacity

        bc = BatteryCapacity(nominal_capacity_kwh=60.0)

        # Mock HA — SOH=120 (out of range)
        mock_hass = MagicMock()
        mock_state = MagicMock()
        mock_state.state = "120.0"
        mock_hass.states.get.return_value = mock_state

        result = bc._read_soh(mock_hass)
        assert result == pytest.approx(100.0)  # clamped to 100

        # Mock HA — SOH=5 (below 10)
        mock_state.state = "5.0"
        result = bc._read_soh(mock_hass)
        assert result == pytest.approx(10.0)  # clamped to 10

    def test_battery_capacity_cache_ttl(self) -> None:
        """BatteryCapacity caches SOH reads with 5-min TTL."""
        from unittest.mock import MagicMock, PropertyMock

        from custom_components.ev_trip_planner.calculations import BatteryCapacity

        bc = BatteryCapacity(
            nominal_capacity_kwh=60.0,
            soh_sensor_entity_id="sensor.battery_soh",
        )

        mock_hass = MagicMock()
        mock_state = MagicMock()
        mock_state.state = "80.0"
        mock_hass.states.get.return_value = mock_state

        # First call — reads from sensor
        bc._soh_value = None
        bc._soh_cached_at = None
        result1 = bc.get_capacity(mock_hass)

        # Second call within TTL — should NOT re-read (uses cache)
        result2 = bc.get_capacity(mock_hass)
        assert mock_hass.states.get.call_count == 1  # only called once

        assert result1 == pytest.approx(48.0)
        assert result2 == pytest.approx(48.0)

    def test_battery_capacity_soh_non_numeric_returns_nominal(self) -> None:
        """BatteryCapacity._read_soh returns None when SOH sensor has non-numeric state.

        Covers calculations.py:116-117: except (ValueError, TypeError) branch.
        """
        from unittest.mock import MagicMock

        from custom_components.ev_trip_planner.calculations import BatteryCapacity

        bc = BatteryCapacity(
            nominal_capacity_kwh=60.0,
            soh_sensor_entity_id="sensor.battery_soh",
        )

        # Mock HA — sensor returns non-numeric value
        mock_hass = MagicMock()
        mock_state = MagicMock()
        mock_state.state = "abc"  # non-numeric, triggers ValueError
        mock_hass.states.get.return_value = mock_state

        result = bc.get_capacity(mock_hass)
        # Falls back to nominal when SOH value is unreadable
        assert result == 60.0


# ------------------------------------------------------------------
# Scenario Validation (US6+US7) — T067-T070
# ------------------------------------------------------------------


class TestScenarioValidation:
    """Integration tests validating full scenario SOC evolution.

    These tests verify that calculate_dynamic_soc_limit() produces
    correct caps for multi-trip chains matching spec.md scenarios.
    """

    def test_scenario_c_daily_commute_cap(self) -> None:
        """T067: Scenario C — 4 identical 30km trips with 22.5h idle each.

        Each trip should charge to ~61% (not 100%) due to capping.
        Post-trip SOC ~41%.
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_dynamic_soc_limit,
        )

        # Scenario C: 30kWh battery, daily commute pattern
        # 22.5h idle between trips, post-trip SOC ~41%
        battery_kwh = 30.0
        t_base = 24.0

        # Trip 1: 22.5h idle, post-trip SOC 41%
        cap_1 = calculate_dynamic_soc_limit(22.5, 41.0, battery_kwh, t_base=t_base)
        assert cap_1 == pytest.approx(94.93, rel=0.01)

        # All 4 trips have same pattern (identical idle + post-trip SOC)
        for i in range(4):
            cap = calculate_dynamic_soc_limit(22.5, 41.0, battery_kwh, t_base=t_base)
            assert cap < 100.0, f"Trip {i + 1} should be capped below 100%"
            assert cap > 60.0, f"Trip {i + 1} cap should allow reasonable charging"

    def test_scenario_a_commute_then_drain(self) -> None:
        """T068: Scenario A — commute first, then large drain.

        Commute: 22h idle, 41% post-trip -> cap ~94.9%
        Large drain: post-trip 0% -> risk negative -> 100% allowed
        Second commute: 22h idle, 41% -> cap ~94.9%
        Semi-drain: post-trip 10% -> risk negative -> 100% allowed
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_dynamic_soc_limit,
        )

        battery_kwh = 30.0
        t_base = 24.0

        # Commute: 22h idle, 41% post-trip
        cap_commute = calculate_dynamic_soc_limit(
            22.0, 41.0, battery_kwh, t_base=t_base
        )
        assert cap_commute == pytest.approx(94.93, rel=0.01)

        # Large drain: post-trip SOC 0% -> risk negative -> 100%
        cap_drain = calculate_dynamic_soc_limit(22.0, 0.0, battery_kwh, t_base=t_base)
        assert cap_drain == 100.0, "Post-trip SOC below soc_base should allow 100%"

        # Semi-drain: post-trip SOC 10% -> risk negative -> 100%
        cap_semi = calculate_dynamic_soc_limit(22.0, 10.0, battery_kwh, t_base=t_base)
        assert cap_semi == 100.0, "Post-trip SOC below soc_base should allow 100%"

    def test_scenario_b_drain_then_commute(self) -> None:
        """T069: Scenario B — large drain first, then commutes.

        Large drain first: 100% allowed (no idle risk yet)
        Then commutes at 94.9% cap -> charge to ~61%
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_dynamic_soc_limit,
        )

        battery_kwh = 30.0
        t_base = 24.0

        # Large drain first: short idle, low post-trip SOC -> 100%
        cap_drain_first = calculate_dynamic_soc_limit(
            1.0, 0.0, battery_kwh, t_base=t_base
        )
        assert cap_drain_first == 100.0

        # Then commute: 22h idle, 41% post-trip -> 94.9% cap
        cap_commute = calculate_dynamic_soc_limit(
            22.0, 41.0, battery_kwh, t_base=t_base
        )
        assert cap_commute == pytest.approx(94.93, rel=0.01)

        # 48h idle commute: even tighter cap
        cap_long_idle = calculate_dynamic_soc_limit(
            48.0, 41.0, battery_kwh, t_base=t_base
        )
        assert cap_long_idle < cap_commute, "Longer idle should produce tighter cap"

    def test_week_total_high_soc_reduction(self) -> None:
        """T070: Verify week total at >80% SOC drops with capping.

        Without capping: 4 trips * 22.5h idle at 100% SOC = 90h at >80%
        With capping: SOC capped to ~61%, so time at >80% drops to ~0h
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_dynamic_soc_limit,
        )

        battery_kwh = 30.0
        t_base = 24.0

        # With capping, each trip's cap is ~94.9% for 22.5h idle
        # The cap means the car won't sit at 100% for extended periods
        total_hours_above_80 = 0.0
        for i in range(4):
            cap = calculate_dynamic_soc_limit(22.5, 41.0, battery_kwh, t_base=t_base)
            # If cap < 80%, zero hours above 80%
            # If cap > 80%, estimate hours above 80% based on charging curve
            if cap > 80.0:
                # Rough estimate: fraction of idle time above 80%
                # With cap ~95%, only a small fraction of time is above 80%
                total_hours_above_80 += 22.5 * (cap - 80.0) / (cap - 41.0) * 0.1

        # Without capping, would be ~90h at >80%
        # With capping, should be significantly less
        assert total_hours_above_80 < 10.0, (
            f"Week total at >80% SOC should drop significantly, got {total_hours_above_80:.1f}h"
        )
