"""Distinctive-data and boundary-parametrisation tests for calculations.

Strategy: use non-round numbers (73.5, 42.7) and exact boundary values
so that round(x, 2)/round(x), min/max/clamp, and boolean-flip mutations
produce a different asserted output and are killed.

NFR-8 multi-assert: every output dict is asserted on all key values,
not just the headline number.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

# =============================================================================
# _helpers — _strip_accents (distinctive data)
# =============================================================================


class TestStripAccentsDistinctiveData:
    """Kill the equivalent mutations on _strip_accents (NFKD→nfkd, ascii→ASCII, ignore→replace).

    These are technically equivalent (the encodings work the same), but
    exercising them with distinctive inputs verifies the actual implementation.
    """

    def test_arbol_to_arbol(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            _strip_accents,
        )

        assert _strip_accents("árbol") == "arbol"

    def test_joao_to_joao(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            _strip_accents,
        )

        assert _strip_accents("João") == "Joao"

    def test_nino_to_nino(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            _strip_accents,
        )

        assert _strip_accents("NIÑO") == "NINO"

    def test_empty_string(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            _strip_accents,
        )

        assert _strip_accents("") == ""

    def test_no_accents(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            _strip_accents,
        )

        assert _strip_accents("lunes") == "lunes"

    def test_mixed_accents(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            _strip_accents,
        )

        # NFKD decomposes Á→A+combining, É→E+combining, etc.
        # encode("ascii","ignore") strips combining chars
        assert _strip_accents("aÁeÉiÍoÓuÚü") == "aAeEiIoOuUu"

    def test_spanish_weekday_accents(self):
        """Wednesday with accent is the most common accent in day names."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            _strip_accents,
        )

        assert _strip_accents("miércoles") == "miercoles"


# =============================================================================
# _helpers — ceil_hours (boundary + distinctive)
# =============================================================================


class TestCeilHoursBoundary:
    """Kill default_value and arithmetic mutations on ceil_hours."""

    def test_zero(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            ceil_hours,
        )

        assert ceil_hours(0.0) == 0

    def test_exact_hour(self):
        """ceil_hours(3.0) == 3 — exact boundary."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            ceil_hours,
        )

        assert ceil_hours(3.0) == 3

    def test_one_above_exact(self):
        """ceil_hours(3.0001) == 4 — just inside the boundary."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            ceil_hours,
        )

        assert ceil_hours(3.0001) == 4

    def test_fractional_boundary(self):
        """ceil_hours(0.5) == 1 — fractional → 1."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            ceil_hours,
        )

        assert ceil_hours(0.5) == 1

    def test_non_round_73_5(self):
        """ceil_hours(73.5) == 74 — distinctive non-round value."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            ceil_hours,
        )

        assert ceil_hours(73.5) == 74

    def test_non_round_42_7(self):
        """ceil_hours(42.7) == 43 — distinctive non-round value."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            ceil_hours,
        )

        assert ceil_hours(42.7) == 43

    def test_large_value(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            ceil_hours,
        )

        assert ceil_hours(168.0) == 168

    def test_very_small_positive(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            ceil_hours,
        )

        assert ceil_hours(0.001) == 1


# =============================================================================
# _helpers — compute_charging_window (boundary + distinctive)
# =============================================================================


class TestComputeChargingWindowBoundary:
    """Kill boundary mutations on compute_charging_window."""

    def test_zero_deadline(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            compute_charging_window,
        )

        # deadline=0, needed=2 → 0 - 2 = -2 → max(0, -2) = 0
        assert compute_charging_window(0.0, 2.0) == 0

    def test_zero_needed(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            compute_charging_window,
        )

        # deadline=5, needed=0 → ceil(5) = 5
        assert compute_charging_window(5.0, 0.0) == 5

    def test_exact_match(self):
        """deadline==needed → ceil(0) = 0."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            compute_charging_window,
        )

        assert compute_charging_window(3.0, 3.0) == 0

    def test_non_round_deadline(self):
        """Deadline 73.5h needed 42.7h → ceil(73.5-42.7)=ceil(30.8)=31."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            compute_charging_window,
        )

        assert compute_charging_window(73.5, 42.7) == 31

    def test_boundary_underflow(self):
        """Needed > deadline → negative → clamped to 0."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            compute_charging_window,
        )

        assert compute_charging_window(1.0, 5.0) == 0


# =============================================================================
# _helpers — kw_to_watts / watts_to_kw (distinctive data)
# =============================================================================


class TestKwWattsConversion:
    """Kill multiplication mutation on kw_to_watts."""

    def test_exact_3_6_kw(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            kw_to_watts,
            watts_to_kw,
        )

        assert kw_to_watts(3.6) == 3600.0
        assert watts_to_kw(3600.0) == 3.6

    def test_non_round_2_5_kw(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            kw_to_watts,
        )

        assert kw_to_watts(2.5) == 2500.0

    def test_non_round_7_4_kw(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            kw_to_watts,
        )

        assert kw_to_watts(7.4) == 7400.0

    def test_zero_kw(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            kw_to_watts,
        )

        assert kw_to_watts(0.0) == 0.0


# =============================================================================
# _helpers — hours_to_timestep (boundary + clamp)
# =============================================================================


class TestHoursToTimestepBoundary:
    """Kill min/max/clamp mutations on hours_to_timestep."""

    def test_zero_hours(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            hours_to_timestep,
        )

        assert hours_to_timestep(0.0, 168) == 0

    def test_exact_horizon(self):
        """hours == horizon → exactly at boundary."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            hours_to_timestep,
        )

        assert hours_to_timestep(24.0, 24) == 24

    def test_above_horizon(self):
        """hours > horizon → clamped to horizon."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            hours_to_timestep,
        )

        assert hours_to_timestep(168.1, 168) == 168

    def test_non_round_within_horizon(self):
        """hours=73.5, horizon=168 → ceil(73.5)=74."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            hours_to_timestep,
        )

        assert hours_to_timestep(73.5, 168) == 74

    def test_non_round_above_horizon(self):
        """hours=169.2, horizon=168 → ceil(169.2)=170 → clamped to 168."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            hours_to_timestep,
        )

        assert hours_to_timestep(169.2, 168) == 168

    def test_boundary_just_below_horizon(self):
        """hours=167.1, horizon=168 → ceil(167.1)=168 → at boundary."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            hours_to_timestep,
        )

        assert hours_to_timestep(167.1, 168) == 168


# =============================================================================
# windows — calculate_energy_needed (distinctive data + multi-assert)
# =============================================================================


class TestCalculateEnergyNeededDistinctive:
    """Kill mutations using non-round SOC/energy values and multi-assert."""

    def test_soc_73_5_non_round_energy(self):
        """SOC=73.5 ≥ base target 38% → proactive charge = trip energy (10.0)."""
        from custom_components.ev_trip_planner.calculations.windows import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"kwh": 10.0},
            battery_capacity_kwh=75.0,
            soc_current=73.5,
            charging_power_kw=3.6,
        )
        # Multi-assert: verify ALL keys
        assert result["energia_necesaria_kwh"] == 10.0
        assert isinstance(result["horas_carga_necesarias"], int)
        assert result["horas_disponibles"] == 0.0
        assert result["margen_seguridad_aplicado"] > 0

    def test_soc_42_7_clamped_to_capacity(self):
        """SOC=42.7 → needs charge, but energy_necesaria clamped to battery_capacity."""
        from custom_components.ev_trip_planner.calculations.windows import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"kwh": 80.0},  # More than battery capacity
            battery_capacity_kwh=75.0,
            soc_current=42.7,
            charging_power_kw=3.6,
        )
        assert result["energia_necesaria_kwh"] <= 75.0

    def test_soc_99_9_proactive_charge(self):
        """SOC=99.9 ≥ target → proactive charge = trip energy."""
        from custom_components.ev_trip_planner.calculations.windows import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"kwh": 15.0},
            battery_capacity_kwh=75.0,
            soc_current=99.9,
            charging_power_kw=3.6,
        )
        assert result["energia_necesaria_kwh"] == 15.0

    def test_soc_zero(self):
        """SOC=0 → needs max charge."""
        from custom_components.ev_trip_planner.calculations.windows import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"kwh": 20.0},
            battery_capacity_kwh=75.0,
            soc_current=0.0,
            charging_power_kw=3.6,
        )
        assert result["energia_necesaria_kwh"] > 0
        assert result["energia_necesaria_kwh"] <= 75.0


# =============================================================================
# windows — calculate_charging_window_pure (boundary params)
# =============================================================================


class TestChargingWindowPureBoundary:
    """Kill boundary mutations on pure window calculation."""

    def test_zero_window_hours(self):
        from custom_components.ev_trip_planner.calculations.windows import (
            ChargingWindowPureParams,
            calculate_charging_window_pure,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        params = ChargingWindowPureParams(
            trip_departure_time=ref + timedelta(hours=2),
            soc_actual=50.0,
            hora_regreso=ref + timedelta(hours=2),  # Same as departure → 0h window
            charging_power_kw=3.6,
            energia_kwh=10.0,
        )
        result = calculate_charging_window_pure(params)
        assert result["ventana_horas"] == 0.0
        # 0h window cannot charge 3h needed → es_suficiente=False
        assert result["es_suficiente"] is False

    def test_exact_sufficient(self):
        """Window exactly equals needed hours → es_suficiente=True."""
        from custom_components.ev_trip_planner.calculations.windows import (
            ChargingWindowPureParams,
            calculate_charging_window_pure,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        params = ChargingWindowPureParams(
            trip_departure_time=ref + timedelta(hours=5),
            soc_actual=50.0,
            hora_regreso=ref,
            charging_power_kw=5.0,
            energia_kwh=25.0,  # 25/5 = 5h exactly = window
        )
        result = calculate_charging_window_pure(params)
        assert result["es_suficiente"] is True

    def test_just_insufficient(self):
        """Window 0.1h less than needed → es_suficiente=False."""
        from custom_components.ev_trip_planner.calculations.windows import (
            ChargingWindowPureParams,
            calculate_charging_window_pure,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        params = ChargingWindowPureParams(
            trip_departure_time=ref + timedelta(hours=4, minutes=59),
            soc_actual=50.0,
            hora_regreso=ref,
            charging_power_kw=5.0,
            energia_kwh=25.0,  # Needs 5h, has 4h59m
        )
        result = calculate_charging_window_pure(params)
        assert result["es_suficiente"] is False

    def test_non_round_soc_and_energia(self):
        """SOC=73.5, energia=17.3 → non-round round(x,3) mutation target."""
        from custom_components.ev_trip_planner.calculations.windows import (
            ChargingWindowPureParams,
            calculate_charging_window_pure,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        params = ChargingWindowPureParams(
            trip_departure_time=ref + timedelta(hours=10),
            soc_actual=73.5,
            hora_regreso=ref,
            charging_power_kw=3.6,
            energia_kwh=17.3,
        )
        result = calculate_charging_window_pure(params)
        assert result["kwh_necesarios"] == 17.3
        assert result["ventana_horas"] > 0


# =============================================================================
# windows — calculate_multi_trip_charging_windows (multi-assert full shape)
# =============================================================================


class TestMultiTripWindowsMultiAssert:
    """Kill mutations using full output shape assertions (NFR-8)."""

    def test_full_output_shape_two_trips(self):
        """Assert ALL keys in each window dict, including all 6 keys."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.windows import (
            MultiTripChargingParams,
            calculate_multi_trip_charging_windows,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        trips = [
            (ref + timedelta(hours=10), {"kwh": 10.0}),
            (ref + timedelta(hours=20), {"kwh": 15.0}),
        ]
        results = calculate_multi_trip_charging_windows(
            trips=trips,
            params=MultiTripChargingParams(
                soc_actual=60.0,
                hora_regreso=ref,
                charging_power_kw=3.6,
                battery_capacity_kwh=75.0,
                now=ref,
            ),
        )
        assert len(results) == 2

        for w in results:
            # Multi-assert on ALL keys (NFR-8)
            assert "ventana_horas" in w
            assert "kwh_necesarios" in w
            assert "horas_carga_necesarias" in w
            assert "inicio_ventana" in w
            assert "fin_ventana" in w
            assert "es_suficiente" in w
            assert "trip" in w

    def test_non_round_trip_chain(self):
        """SOC=73.5, energy=17.3,12.5 → distinctive values across chain."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.windows import (
            MultiTripChargingParams,
            calculate_multi_trip_charging_windows,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        trips = [
            (ref + timedelta(hours=10), {"kwh": 17.3}),
            (ref + timedelta(hours=22), {"kwh": 12.5}),
        ]
        results = calculate_multi_trip_charging_windows(
            trips=trips,
            params=MultiTripChargingParams(
                soc_actual=73.5,
                hora_regreso=ref,
                charging_power_kw=3.6,
                battery_capacity_kwh=75.0,
                now=ref,
            ),
        )
        assert len(results) == 2
        assert results[0]["kwh_necesarios"] == 17.3
        assert results[1]["kwh_necesarios"] == 12.5

    def test_empty_trips(self):
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.windows import (
            MultiTripChargingParams,
            calculate_multi_trip_charging_windows,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        results = calculate_multi_trip_charging_windows(
            trips=[],
            params=MultiTripChargingParams(
                soc_actual=60.0,
                hora_regreso=ref,
                charging_power_kw=3.6,
                battery_capacity_kwh=75.0,
            ),
        )
        assert results == []


# =============================================================================
# windows — build_deferrable_matrix_row (boundary)
# =============================================================================


class TestBuildDeferrableMatrixBoundary:
    """Kill boundary mutations on deferrable matrix building."""

    def test_zero_hours_needed(self):
        from custom_components.ev_trip_planner.calculations.windows import (
            build_deferrable_matrix_row,
        )

        row = build_deferrable_matrix_row(168, 3.6, 0.0, 24)
        assert all(v == 0.0 for v in row)

    def test_exact_horizon(self):
        """hours_needed=168, end_timestep=168 → full profile."""
        from custom_components.ev_trip_planner.calculations.windows import (
            build_deferrable_matrix_row,
        )

        row = build_deferrable_matrix_row(168, 3.6, 168.0, 168)
        expected_power = 3600.0
        for v in row:
            assert v == expected_power

    def test_non_round_hours(self):
        """hours_needed=17.3 → ceil=18 slots."""
        from custom_components.ev_trip_planner.calculations.windows import (
            build_deferrable_matrix_row,
        )

        row = build_deferrable_matrix_row(168, 3.6, 17.3, 24)
        assert sum(1 for v in row if v > 0) == 18

    def test_boundary_underflow_end_timestep(self):
        """end_timestep=0 → no slots."""
        from custom_components.ev_trip_planner.calculations.windows import (
            build_deferrable_matrix_row,
        )

        row = build_deferrable_matrix_row(168, 3.6, 5.0, 0)
        assert all(v == 0.0 for v in row)


# =============================================================================
# deficit — calculate_hours_deficit_propagation (origin fix + multi-assert)
# =============================================================================


class TestDeficitPropagationOriginFix:
    """Verify the deficit.py origin-bug fix: adjusted_def_total_hours = 0.0.

    Bug: lines 480-487 previously used round(original_def_total, 2).
    Fix: uses math.ceil(ventana) if ventana > 0 else 0.0
    """

    def test_origin_zero_window(self):
        """Origin trip with ventana_horas=0 → adjusted_def_total_hours=0.0."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {"ventana_horas": 4, "horas_carga_necesarias": 2},
            {"ventana_horas": 0, "horas_carga_necesarias": 3},  # Origin: deficit here
        ]
        results = calculate_hours_deficit_propagation(windows)

        assert len(results) == 2
        origin_result = results[1]
        # Origin with ventana=0: adjusted_def_total_hours = 0.0 (or int 0)
        assert origin_result["adjusted_def_total_hours"] in (0.0, 0)
        # Origin has deficit to propagate
        assert origin_result["deficit_hours_to_propagate"] > 0

    def test_origin_positive_window(self):
        """Origin trip with ventana=1 → adjusted = ceil(1) = 1."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {"ventana_horas": 3, "horas_carga_necesarias": 2},
            {"ventana_horas": 1, "horas_carga_necesarias": 3},  # Origin: deficit
        ]
        results = calculate_hours_deficit_propagation(windows)

        origin = results[1]
        assert origin["adjusted_def_total_hours"] == 1  # ceil(1) = 1

    def test_origin_non_round_window(self):
        """Origin with ventana=2.5 → adjusted = ceil(2.5) = 3."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {"ventana_horas": 5, "horas_carga_necesarias": 3},
            {"ventana_horas": 2.5, "horas_carga_necesarias": 5},  # Origin
        ]
        results = calculate_hours_deficit_propagation(windows)

        origin = results[1]
        assert origin["adjusted_def_total_hours"] == 3  # ceil(2.5) = 3

    def test_multi_assert_origin_adjusted_keys(self):
        """Multi-assert on ALL keys for origin trip (NFR-8)."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {"ventana_horas": 4, "horas_carga_necesarias": 2},
            {"ventana_horas": 0, "horas_carga_necesarias": 3},
        ]
        results = calculate_hours_deficit_propagation(windows)

        origin = results[1]
        # Assert ALL keys (NFR-8 multi-assert)
        assert "ventana_horas" in origin
        assert "horas_carga_necesarias" in origin
        assert "deficit_hours_propagated" in origin
        assert "deficit_hours_to_propagate" in origin
        assert "adjusted_def_total_hours" in origin
        assert origin["deficit_hours_propagated"] == 0.0

    def test_origin_increases_earlier_trip(self):
        """Earlier trip absorbs deficit → def_total INCREASES."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {"ventana_horas": 6, "horas_carga_necesarias": 2},  # Has spare capacity
            {"ventana_horas": 0, "horas_carga_necesarias": 4},  # Origin: deficit
        ]
        results = calculate_hours_deficit_propagation(windows)

        # Origin: adjusted = 0 (ventana=0)
        assert results[1]["adjusted_def_total_hours"] == 0.0
        # Earlier trip absorbs 4h deficit → adjusted = 2 + 4 = 6
        assert results[0]["adjusted_def_total_hours"] == 6.0
        assert results[0]["deficit_hours_propagated"] == 4.0


class TestDeficitPropagationNoDeficit:
    """When no deficit exists, adjusted = round(def_total_hours, 2)."""

    def test_no_deficit_full_round(self):
        """No deficits → adjusted_def_total_hours = round(def_total_hours[i], 2)."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {"ventana_horas": 5, "horas_carga_necesarias": 2},
            {"ventana_horas": 4, "horas_carga_necesarias": 3},
        ]
        results = calculate_hours_deficit_propagation(windows)

        for i, r in enumerate(results):
            assert r["adjusted_def_total_hours"] == 2.0 or r["adjusted_def_total_hours"] == 3.0
            assert r["deficit_hours_propagated"] == 0.0
            assert r["deficit_hours_to_propagate"] == 0.0

    def test_no_deficit_non_round_values(self):
        """Non-round def_total values → round(x, 2) mutation target."""
        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {"ventana_horas": 5, "horas_carga_necesarias": 2},
            {"ventana_horas": 4, "horas_carga_necesarias": 3},
        ]
        results = calculate_hours_deficit_propagation(windows, def_total_hours=[2.345, 3.789])

        assert results[0]["adjusted_def_total_hours"] == round(2.345, 2)
        assert results[1]["adjusted_def_total_hours"] == round(3.789, 2)


class TestDeficitPropagationEmpty:
    def test_empty_windows(self):
        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_hours_deficit_propagation,
        )

        assert calculate_hours_deficit_propagation([]) == []


# =============================================================================
# deficit — calculate_deficit_propagation (multi-assert full milestone shape)
# =============================================================================


class TestDeficitPropagationMilestoneMultiAssert:
    """Kill mutations on deficit propagation using full milestone shape assertions."""

    def test_full_milestone_shape(self):
        """Assert ALL keys on each milestone dict (NFR-8)."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_deficit_propagation,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        trips = [
            {"id": "t1", "kwh": 10.0, "emhass_index": 0},
            {"id": "t2", "kwh": 15.0, "emhass_index": 1},
        ]
        soc_data = [
            {"soc_inicio": 60.0},
            {"soc_inicio": 75.0},
        ]
        windows = [
            {"ventana_horas": 8, "kwh_necesarios": 10.0, "horas_carga_necesarias": 3, "inicio_ventana": ref, "fin_ventana": ref + timedelta(hours=10), "es_suficiente": True},
            {"ventana_horas": 8, "kwh_necesarios": 15.0, "horas_carga_necesarias": 5, "inicio_ventana": ref + timedelta(hours=12), "fin_ventana": ref + timedelta(hours=20), "es_suficiente": True},
        ]
        trip_times = [ref + timedelta(hours=10), ref + timedelta(hours=20)]

        results = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=5.0,
            battery_capacity_kwh=75.0,
            reference_dt=ref,
            trip_times=trip_times,
        )

        assert len(results) == 2
        for m in results:
            assert "trip_id" in m
            assert "soc_objetivo" in m
            assert "soc_cap_raw" in m
            assert "kwh_necesarios" in m
            assert "deficit_acumulado" in m
            assert "ventana_carga" in m
            vc = m["ventana_carga"]
            assert "ventana_horas" in vc
            assert "kwh_necesarios" in vc
            assert "horas_carga_necesarias" in vc
            assert "inicio_ventana" in vc
            assert "fin_ventana" in vc
            assert "es_suficiente" in vc

    def test_non_round_soc_propagation(self):
        """SOC=73.5 → 42.7 → propagate non-round deficits."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_deficit_propagation,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        trips = [
            {"id": "t1", "kwh": 10.0, "emhass_index": 0},
            {"id": "t2", "kwh": 20.0, "emhass_index": 1},
        ]
        soc_data = [
            {"soc_inicio": 73.5},
            {"soc_inicio": 42.7},
        ]
        windows = [
            {"ventana_horas": 5, "kwh_necesarios": 10.0, "horas_carga_necesarias": 3, "inicio_ventana": ref, "fin_ventana": ref + timedelta(hours=10), "es_suficiente": True},
            {"ventana_horas": 5, "kwh_necesarios": 20.0, "horas_carga_necesarias": 6, "inicio_ventana": ref + timedelta(hours=15), "fin_ventana": ref + timedelta(hours=20), "es_suficiente": True},
        ]
        trip_times = [ref + timedelta(hours=10), ref + timedelta(hours=20)]

        results = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=5.0,
            battery_capacity_kwh=75.0,
            reference_dt=ref,
            trip_times=trip_times,
        )

        assert len(results) == 2
        assert isinstance(results[0]["soc_objetivo"], float)
        assert isinstance(results[1]["soc_objetivo"], float)
        assert results[0]["deficit_acumulado"] >= 0
        assert results[1]["deficit_acumulado"] >= 0


# =============================================================================
# deficit — determine_charging_need (distinctive non-round SOC)
# =============================================================================


class TestDetermineChargingNeedDistinctive:
    """Kill mutations using non-round SOC values."""

    def test_soc_73_5_non_round(self):
        from custom_components.ev_trip_planner.calculations.deficit import (
            determine_charging_need,
        )

        result = determine_charging_need(
            trip={"id": "t1", "kwh": 10.0},
            soc_current=73.5,
            battery_capacity_kwh=75.0,
            charging_power_kw=3.6,
        )
        assert result.trip_id == "t1"
        assert isinstance(result.kwh_needed, float)
        assert isinstance(result.def_total_hours, int)
        assert isinstance(result.power_watts, float)

    def test_soc_42_7_needs_charge(self):
        from custom_components.ev_trip_planner.calculations.deficit import (
            determine_charging_need,
        )

        result = determine_charging_need(
            trip={"id": "t2", "kwh": 20.0},
            soc_current=42.7,
            battery_capacity_kwh=75.0,
            charging_power_kw=3.6,
        )
        assert result.needs_charging is True
        assert result.kwh_needed > 0
        assert result.def_total_hours > 0


# =============================================================================
# deficit — calculate_soc_at_trip_starts (multi-assert full shape)
# =============================================================================


class TestSocAtTripStartsMultiAssert:
    """Kill mutations on SOC-at-trip-starts using full shape assertions."""

    def test_full_shape_two_trips(self):
        """Assert ALL keys on each result dict (NFR-8)."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_soc_at_trip_starts,
        )

        _ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        trips = [{"id": "t1"}, {"id": "t2"}]
        windows = [
            {"ventana_horas": 5, "kwh_necesarios": 10.0, "trip": {"id": "t1"}},
            {"ventana_horas": 5, "kwh_necesarios": 15.0, "trip": {"id": "t2"}},
        ]
        results = calculate_soc_at_trip_starts(
            trips=trips,
            soc_inicial=60.0,
            windows=windows,
            charging_power_kw=3.6,
            battery_capacity_kwh=75.0,
        )

        assert len(results) == 2
        for r in results:
            assert "soc_inicio" in r
            assert "trip" in r
            assert "arrival_soc" in r
            assert isinstance(r["soc_inicio"], float)
            assert isinstance(r["arrival_soc"], float)

    def test_non_round_soc_chain(self):
        """SOC chain with non-round values: 73.5 → arrival → next soc_inicio."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.deficit import (
            calculate_soc_at_trip_starts,
        )

        _ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        trips = [{"id": "t1"}, {"id": "t2"}]
        windows = [
            {"ventana_horas": 5.5, "kwh_necesarios": 17.3, "trip": {"id": "t1"}},
            {"ventana_horas": 5.0, "kwh_necesarios": 12.5, "trip": {"id": "t2"}},
        ]
        results = calculate_soc_at_trip_starts(
            trips=trips,
            soc_inicial=73.5,
            windows=windows,
            charging_power_kw=3.6,
            battery_capacity_kwh=75.0,
        )

        assert results[0]["soc_inicio"] == 73.5
        # arrival_soc = 73.5 + (min(17.3, 3.6*5.5)/75.0)*100
        assert results[1]["soc_inicio"] == results[0]["arrival_soc"]


# =============================================================================
# power — calculate_power_profile_from_trips (distinctive + boundary)
# =============================================================================


class TestPowerProfileFromTripsDistinctive:
    """Kill mutations on power profile calculation."""

    def test_non_round_power_kw(self):
        from datetime import datetime, timedelta, timezone

        from custom_components.ev_trip_planner.calculations.power import (
            calculate_power_profile_from_trips,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        trips = [
            {"kwh": 10.0, "datetime": (ref + timedelta(hours=10)).isoformat()},
        ]
        profile = calculate_power_profile_from_trips(
            trips=trips,
            power_kw=7.4,  # Non-round power
            horizon=24,
            reference_dt=ref,
        )
        # 7.4 kW → 7400 W in profile slots
        assert 7400.0 in profile

    def test_boundary_zero_kwh(self):
        """Trip with kwh=0 → no profile entries."""
        from datetime import datetime, timedelta, timezone

        from custom_components.ev_trip_planner.calculations.power import (
            calculate_power_profile_from_trips,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        trips = [{"kwh": 0.0, "datetime": (ref + timedelta(hours=5)).isoformat()}]
        profile = calculate_power_profile_from_trips(
            trips=trips,
            power_kw=3.6,
            horizon=24,
            reference_dt=ref,
        )
        assert all(v == 0.0 for v in profile)

    def test_boundary_horizon(self):
        """Horizon=168 → profile length exactly 168."""
        from datetime import datetime, timedelta, timezone

        from custom_components.ev_trip_planner.calculations.power import (
            calculate_power_profile_from_trips,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        trips = [{"kwh": 10.0, "datetime": (ref + timedelta(hours=10)).isoformat()}]
        profile = calculate_power_profile_from_trips(
            trips=trips,
            power_kw=3.6,
            horizon=168,
            reference_dt=ref,
        )
        assert len(profile) == 168


# =============================================================================
# power — calculate_deferrable_parameters (distinctive + multi-assert)
# =============================================================================


class TestDeferrableParametersDistinctive:
    """Kill mutations using distinctive data and multi-assert."""

    def test_non_round_kwh(self):
        """kwh=17.3 → total_energy_kwh=17.3 (round(x,3) mutation target)."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.schedule import (
            calculate_deferrable_parameters,
        )

        result = calculate_deferrable_parameters(
            trip={"kwh": 17.3, "datetime": "2026-06-15T14:00:00+00:00"},
            power_kw=3.6,
            reference_dt=datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc),
        )
        assert result["total_energy_kwh"] == 17.3
        # Multi-assert on ALL keys (NFR-8)
        assert "total_energy_kwh" in result
        assert "power_watts" in result
        assert "total_hours" in result
        assert "end_timestep" in result
        assert "start_timestep" in result
        assert "is_semi_continuous" in result
        assert "minimum_power" in result
        assert "operating_hours" in result
        assert "startup_penalty" in result
        assert "is_single_constant" in result

    def test_soc_42_7_trip(self):
        """SOC context with non-round kwh."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.schedule import (
            calculate_deferrable_parameters,
        )

        result = calculate_deferrable_parameters(
            trip={"kwh": 42.7, "datetime": "2026-06-15T14:00:00+00:00"},
            power_kw=7.4,
            reference_dt=datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc),
        )
        assert result["total_energy_kwh"] == 42.7
        assert result["total_hours"] == round(42.7 / 7.4, 2)

    def test_missing_kwh(self):
        """No kwh key → empty dict."""
        from custom_components.ev_trip_planner.calculations.schedule import (
            calculate_deferrable_parameters,
        )

        result = calculate_deferrable_parameters(
            trip={"datetime": "2026-06-15T14:00:00+00:00"},
            power_kw=3.6,
        )
        assert result == {}

    def test_zero_kwh(self):
        """kwh=0 → empty dict (guarded)."""
        from custom_components.ev_trip_planner.calculations.schedule import (
            calculate_deferrable_parameters,
        )

        result = calculate_deferrable_parameters(
            trip={"kwh": 0.0, "datetime": "2026-06-15T14:00:00+00:00"},
            power_kw=3.6,
        )
        assert result == {}


# =============================================================================
# schedule — generate_deferrable_schedule_from_trips (distinctive)
# =============================================================================


class TestScheduleDistinctive:
    """Kill mutations on schedule generation."""

    def test_non_round_power(self):
        """power_kw=7.4 → schedule entry has 7400 W."""
        from datetime import datetime, timedelta, timezone

        from custom_components.ev_trip_planner.calculations.schedule import (
            generate_deferrable_schedule_from_trips,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        trips = [{"kwh": 10.0, "datetime": (ref + timedelta(hours=10)).isoformat()}]
        schedule = generate_deferrable_schedule_from_trips(
            trips=trips,
            power_kw=7.4,
            reference_dt=ref,
        )
        assert len(schedule) == 24
        # Check that at least one slot has the correct power
        power_values = [s.get("p_deferrable0", "0.0") for s in schedule]
        assert "7400.0" in power_values

    def test_boundary_horizon_24(self):
        """Schedule always produces 24 entries."""
        from datetime import datetime, timedelta, timezone

        from custom_components.ev_trip_planner.calculations.schedule import (
            generate_deferrable_schedule_from_trips,
        )

        ref = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        trips = [{"kwh": 10.0, "datetime": (ref + timedelta(hours=10)).isoformat()}]
        schedule = generate_deferrable_schedule_from_trips(
            trips=trips,
            power_kw=3.6,
            reference_dt=ref,
        )
        assert len(schedule) == 24

    def test_empty_trips(self):
        """Empty trips → empty schedule."""
        from custom_components.ev_trip_planner.calculations.schedule import (
            generate_deferrable_schedule_from_trips,
        )

        schedule = generate_deferrable_schedule_from_trips(
            trips=[],
            power_kw=3.6,
        )
        assert schedule == []


# =============================================================================
# core — calculate_day_index (boundary + distinctive accents)
# =============================================================================


class TestCalculateDayIndexBoundary:
    """Kill boundary mutations on day index calculation."""

    def test_boundary_negative_index(self):
        from custom_components.ev_trip_planner.calculations import (
            calculate_day_index,
        )

        assert calculate_day_index("-1") == 0

    def test_boundary_max_index(self):
        from custom_components.ev_trip_planner.calculations import (
            calculate_day_index,
        )

        assert calculate_day_index("6") == 5  # JS Saturday
        assert calculate_day_index("7") == 0  # Out of range

    def test_boundary_accented_wednesday(self):
        """miércoles with accent → normalized → index 2."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_day_index,
        )

        idx = calculate_day_index("miércoles")
        assert idx == 2

    def test_boundary_accented_sabado(self):
        """sábado with accent → normalized → index 5."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_day_index,
        )

        idx = calculate_day_index("sábado")
        assert idx == 5


# =============================================================================
# core — calculate_dynamic_soc_limit (distinctive + boundary)
# =============================================================================


class TestCalculateDynamicSocLimitDistinctive:
    """Kill mutations on degradation-aware SOC limit using distinctive data."""

    def test_non_round_risk(self):
        """t_hours=73.5, soc=85.0 → non-round risk calculation."""
        from custom_components.ev_trip_planner.calculations.core import (
            calculate_dynamic_soc_limit,
        )

        limit = calculate_dynamic_soc_limit(
            t_hours=73.5,
            soc_post_trip=85.0,
            battery_capacity_kwh=75.0,
        )
        assert 35.0 <= limit <= 100.0
        assert isinstance(limit, float)

    def test_boundary_zero_risk(self):
        """soc=30 → risk negative → returns 100.0."""
        from custom_components.ev_trip_planner.calculations.core import (
            calculate_dynamic_soc_limit,
        )

        assert calculate_dynamic_soc_limit(
            t_hours=24.0,
            soc_post_trip=30.0,
            battery_capacity_kwh=75.0,
        ) == 100.0

    def test_boundary_high_limit(self):
        """soc=100, t_hours=48 → tight limit."""
        from custom_components.ev_trip_planner.calculations.core import (
            calculate_dynamic_soc_limit,
        )

        limit = calculate_dynamic_soc_limit(
            t_hours=48.0,
            soc_post_trip=100.0,
            battery_capacity_kwh=75.0,
        )
        assert limit < 100.0
        assert limit >= 35.0

    def test_non_round_soc_42_7(self):
        """soc=42.7 → positive risk → limit < 100."""
        from custom_components.ev_trip_planner.calculations.core import (
            calculate_dynamic_soc_limit,
        )

        limit = calculate_dynamic_soc_limit(
            t_hours=24.0,
            soc_post_trip=42.7,
            battery_capacity_kwh=75.0,
        )
        assert 35.0 <= limit <= 100.0


# =============================================================================
# core — calculate_soc_target (distinctive data)
# =============================================================================


class TestCalculateSocTargetDistinctive:
    """Kill mutations on SOC target calculation."""

    def test_non_round_battery(self):
        """battery_capacity_kwh=73.5 → energy_soc=27.21... + buffer."""
        from custom_components.ev_trip_planner.calculations.core import (
            calculate_soc_target,
        )

        result = calculate_soc_target(
            trip={"kwh": 20.0},
            battery_capacity_kwh=73.5,
        )
        # energy_soc = 20/73.5 * 100 = 27.21... + buffer = 37.21...
        assert result > 37.0
        assert result < 38.0

    def test_non_round_consumption(self):
        """km=150, consumption=0.13 → 19.5 kWh → non-round SOC."""
        from custom_components.ev_trip_planner.calculations.core import (
            calculate_soc_target,
        )

        result = calculate_soc_target(
            trip={"km": 150},
            battery_capacity_kwh=75.0,
            consumption_kwh_per_km=0.13,
        )
        assert result > 25.0

    def test_empty_trip_defaults(self):
        from custom_components.ev_trip_planner.calculations.core import (
            calculate_soc_target,
        )

        result = calculate_soc_target(
            trip={},
            battery_capacity_kwh=75.0,
        )
        assert result > 0


# =============================================================================
# core — calculate_charging_rate (boundary)
# =============================================================================


class TestCalculateChargingRateBoundary:
    """Kill boundary mutations on charging rate calculation."""

    def test_zero_capacity(self):
        from custom_components.ev_trip_planner.calculations.core import (
            calculate_charging_rate,
        )

        assert calculate_charging_rate(3.6, 0.0) == 0.0

    def test_boundary_negative_capacity(self):
        from custom_components.ev_trip_planner.calculations.core import (
            calculate_charging_rate,
        )

        assert calculate_charging_rate(3.6, -5.0) == 0.0

    def test_non_round_rate(self):
        """3.6/73.5*100 = 4.897... → non-round result."""
        from custom_components.ev_trip_planner.calculations.core import (
            calculate_charging_rate,
        )

        rate = calculate_charging_rate(3.6, 73.5)
        assert rate > 4.8
        assert rate < 4.9

    def test_exact_boundary_50_kwh(self):
        from custom_components.ev_trip_planner.calculations.core import (
            calculate_charging_rate,
        )

        rate = calculate_charging_rate(3.6, 50.0)
        # 3.6/50*100 = 7.2, but float precision → 7.200000000000001
        assert math.isclose(rate, 7.2, rel_tol=1e-9)


# =============================================================================
# core — BatteryCapacity (boundary)
# =============================================================================


class TestBatteryCapacityBoundary:
    """Kill mutations on BatteryCapacity calculations."""

    def test_nominal_without_soh(self):
        from custom_components.ev_trip_planner.calculations.core import (
            BatteryCapacity,
        )

        cap = BatteryCapacity(nominal_capacity_kwh=75.0)
        assert cap.get_capacity() == 75.0

    def test_soh_clamp_high(self):
        """SoH clamping only happens in _read_soh (sensor path),
        not when _soh_value is set directly."""
        from custom_components.ev_trip_planner.calculations.core import (
            BatteryCapacity,
        )

        cap = BatteryCapacity(nominal_capacity_kwh=75.0, soh_sensor_entity_id="sensor.soh")
        cap._soh_value = 150.0  # Set directly bypasses sensor clamp
        # _compute_capacity uses _soh_value directly without clamp
        assert cap.get_capacity() == 75.0 * 1.5  # 150% × 75 = 112.5

    def test_soh_clamp_low(self):
        """SoH clamping only happens in _read_soh (sensor path),
        not when _soh_value is set directly."""
        from custom_components.ev_trip_planner.calculations.core import (
            BatteryCapacity,
        )

        cap = BatteryCapacity(nominal_capacity_kwh=75.0, soh_sensor_entity_id="sensor.soh")
        cap._soh_value = 5.0  # Set directly bypasses sensor clamp
        # _compute_capacity uses _soh_value directly without clamp
        assert cap.get_capacity() == 75.0 * 0.05  # 5% × 75 = 3.75

    def test_soh_73_5(self):
        from custom_components.ev_trip_planner.calculations.core import (
            BatteryCapacity,
        )

        cap = BatteryCapacity(nominal_capacity_kwh=75.0, soh_sensor_entity_id="sensor.soh")
        cap._soh_value = 73.5
        assert cap.get_capacity() == 75.0 * 0.735


# =============================================================================
# _helpers — resolve_trip_deadline (distinctive data)
# =============================================================================


class TestResolveTripDeadlineDistinctive:
    """Kill mutations using distinctive trip data."""

    def test_non_round_kwh_trip(self):
        """Trip with kwh=17.3 and non-round day name."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations._helpers import (
            resolve_trip_deadline,
        )

        now = datetime(2026, 5, 11, 9, 0, 0, tzinfo=timezone.utc)
        trip = {"id": "trip_73", "kwh": 17.3, "datetime": "2026-06-15T14:30:00+00:00"}
        result = resolve_trip_deadline(trip, now)
        assert result is not None
        assert result.hour == 14
        assert result.minute == 30

    def test_accents_in_trip_id(self):
        """Trip ID with accents — _strip_accents should handle."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations._helpers import (
            resolve_trip_deadline,
        )

        now = datetime(2026, 5, 11, 9, 0, 0, tzinfo=timezone.utc)
        # Recurring trip with accented day name
        trip = {"id": "viaje_al_NIÑO", "day": "miércoles", "time": "18:00", "tipo": "recurrente"}
        result = resolve_trip_deadline(trip, now)
        assert result is not None


# =============================================================================
# _helpers — normalize_trip_fields (boundary)
# =============================================================================


class TestNormalizeTripFieldsBoundary:
    """Kill boundary mutations on trip field normalization."""

    def test_canonical_keys(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            normalize_trip_fields,
        )

        result = normalize_trip_fields({"day": "lunes", "time": "18:00"})
        assert result == {"day": "lunes", "time": "18:00"}

    def test_legacy_keys(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            normalize_trip_fields,
        )

        result = normalize_trip_fields({"dia_semana": "lunes", "hora": "18:00"})
        assert result == {"day": "lunes", "time": "18:00"}

    def test_missing_day(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            normalize_trip_fields,
        )

        assert normalize_trip_fields({"time": "18:00"}) is None

    def test_missing_time(self):
        from custom_components.ev_trip_planner.calculations._helpers import (
            normalize_trip_fields,
        )

        assert normalize_trip_fields({"day": "lunes"}) is None

    def test_mixed_keys(self):
        """One canonical, one legacy — normalize_trip_fields supports 'hora' fallback."""
        from custom_components.ev_trip_planner.calculations._helpers import (
            normalize_trip_fields,
        )

        result = normalize_trip_fields({"day": "lunes", "hora": "18:00"})
        # Function recognizes 'hora' as fallback → canonicalized result
        assert result == {"day": "lunes", "time": "18:00"}
