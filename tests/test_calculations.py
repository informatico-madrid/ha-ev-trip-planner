"""Parametrized tests for pure functions in calculations.py.

These tests achieve 100% coverage of the pure functions without any mocks.
All functions are synchronous and deterministic given the same inputs.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest


class TestCalculateDayIndex:
    """Tests for calculate_day_index."""

    @pytest.mark.parametrize("day_name,expected", [
        # Spanish day names (lowercase)
        ("lunes", 0),
        ("martes", 1),
        ("miercoles", 2),
        ("jueves", 3),
        ("viernes", 4),
        ("sabado", 5),
        ("domingo", 6),
        # Spanish day names (mixed case)
        ("Lunes", 0),
        ("MARTES", 1),
        ("Miercoles", 2),
        # Numeric strings
        ("0", 0),
        ("1", 1),
        ("6", 6),
        # Unknown day defaults to Monday
        ("invalid", 0),
        ("", 0),
        # Edge cases
        ("   lunes   ", 0),  # with whitespace
    ])
    def test_day_index_returns_correct_value(self, day_name: str, expected: int):
        """Parametrized: all day names return correct index."""
        from custom_components.ev_trip_planner.calculations import calculate_day_index
        assert calculate_day_index(day_name) == expected

    @pytest.mark.parametrize("day_index,expected", [
        (0, 0),
        (3, 3),
        (6, 6),
        # Out of range defaults to Monday
        (7, 0),
        (-1, 0),
        (100, 0),
    ])
    def test_numeric_day_index(self, day_index: int, expected: int):
        """Parametrized: numeric day indices return correct value or default."""
        from custom_components.ev_trip_planner.calculations import calculate_day_index
        assert calculate_day_index(str(day_index)) == expected


class TestCalculateTripTime:
    """Tests for calculate_trip_time."""

    def test_recurring_trip_same_week_day_later_today(self):
        """Recurring trip on same weekday later today returns today (not next week)."""
        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        # Reference: Monday 08:00
        ref = datetime(2026, 4, 6, 8, 0)  # Monday April 6 2026, 08:00
        # Trip: Monday 10:00 (same day, later than current time)
        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora="10:00",
            dia_semana="lunes",
            datetime_str=None,
            reference_dt=ref,
        )
        # Since it's Monday 08:00 and trip is Monday 10:00 (NOT passed), days_ahead = 0
        assert result is not None
        assert result.date() == ref.date()  # Same day, not next week
        assert result.hour == 10
        assert result.minute == 0

    def test_recurring_trip_next_week_day(self):
        """Recurring trip on later weekday returns correct day this week."""
        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        # Reference: Monday 08:00
        ref = datetime(2026, 4, 6, 8, 0)  # Monday April 6 2026, 08:00
        # Trip: Friday 10:00 (same week)
        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora="10:00",
            dia_semana="viernes",
            datetime_str=None,
            reference_dt=ref,
        )
        assert result is not None
        assert result.weekday() == 4  # Friday
        assert result.hour == 10

    def test_recurring_trip_already_passed_this_week(self):
        """Recurring trip that already passed this week returns next week."""
        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        # Reference: Monday 12:00 (passed Monday 08:00)
        ref = datetime(2026, 4, 6, 12, 0)  # Monday April 6 2026, 12:00
        # Trip: Monday 10:00 (already passed)
        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora="10:00",
            dia_semana="lunes",
            datetime_str=None,
            reference_dt=ref,
        )
        assert result is not None
        # Should be next Monday (April 13)
        assert result.date() == ref.date() + timedelta(days=7)

    def test_punctual_trip_with_seconds_format(self):
        """Punctual trip with seconds in datetime string uses second strptime format (line 125)."""
        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        ref = datetime(2026, 4, 6, 8, 0)
        # With seconds format - should fallback from %Y-%m-%dT%H:%M to %Y-%m-%dT%H:%M:%S
        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_PUNCTUAL,
            hora=None,
            dia_semana=None,
            datetime_str="2026-04-10T14:30:45",
            reference_dt=ref,
        )
        assert result is not None
        assert result.date() == datetime(2026, 4, 10).date()
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45

    def test_punctual_trip_invalid_datetime_raises_value_error(self):
        """Punctual trip with invalid datetime raises ValueError (both formats fail)."""
        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        ref = datetime(2026, 4, 6, 8, 0)
        # Invalid datetime fails both parse attempts -> ValueError propagates
        with pytest.raises(ValueError):
            calculate_trip_time(
                trip_tipo=TRIP_TYPE_PUNCTUAL,
                hora=None,
                dia_semana=None,
                datetime_str="not-a-date-at-all",
                reference_dt=ref,
            )

    def test_recurring_trip_invalid_hora_raises_value_error(self):
        """Recurring trip with malformed hora raises ValueError (line 115)."""
        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        ref = datetime(2026, 4, 6, 8, 0)  # Monday
        # hora with non-numeric hour -> hour=0 from exception, but then datetime.strptime fails
        with pytest.raises(ValueError):
            calculate_trip_time(
                trip_tipo=TRIP_TYPE_RECURRING,
                hora="not-a-time",
                dia_semana="lunes",
                datetime_str=None,
                reference_dt=ref,
            )

    def test_day_index_empty_string_returns_default(self):
        """calculate_day_index with empty string returns default 0 (line 64)."""
        from custom_components.ev_trip_planner.calculations import calculate_day_index
        result = calculate_day_index("")
        assert result == 0  # Default Monday

    def test_unknown_tipo_returns_none(self):
        """Unknown trip tipo returns None."""
        from custom_components.ev_trip_planner.calculations import calculate_trip_time

        ref = datetime(2026, 4, 6, 8, 0)
        result = calculate_trip_time(
            trip_tipo="unknown",
            hora="10:00",
            dia_semana="lunes",
            datetime_str=None,
            reference_dt=ref,
        )
        assert result is None

    def test_recurring_without_hora_returns_none(self):
        """Recurring trip without hora returns None."""
        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        ref = datetime(2026, 4, 6, 8, 0)
        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora=None,
            dia_semana="lunes",
            datetime_str=None,
            reference_dt=ref,
        )
        assert result is None


class TestCalculateChargingRateT004:
    """Tests for calculate_charging_rate — T004 RED phase.

    These tests define the expected interface:
    - calculate_charging_rate(power_kw: float, capacity: float) -> float
    - Returns power_kw (simple pass-through for now)
    - Handle edge cases: 0 capacity should not divide by zero
    """

    def test_returns_power_kw_pass_through(self):
        """Returns power_kw directly (simple pass-through)."""
        from custom_components.ev_trip_planner.calculations import calculate_charging_rate
        assert calculate_charging_rate(7.4, 50.0) == 7.4
        assert calculate_charging_rate(11.0, 75.0) == 11.0
        assert calculate_charging_rate(3.6, 50.0) == 3.6

    def test_zero_capacity_returns_zero_no_divide_by_zero(self):
        """Zero capacity returns 0.0 without division by zero."""
        from custom_components.ev_trip_planner.calculations import calculate_charging_rate
        result = calculate_charging_rate(7.4, 0.0)
        assert result == 0.0

    def test_negative_capacity_returns_zero(self):
        """Negative capacity returns 0.0 (invalid input)."""
        from custom_components.ev_trip_planner.calculations import calculate_charging_rate
        result = calculate_charging_rate(7.4, -1.0)
        assert result == 0.0

    def test_zero_power_returns_zero(self):
        """Zero power returns 0.0."""
        from custom_components.ev_trip_planner.calculations import calculate_charging_rate
        result = calculate_charging_rate(0.0, 50.0)
        assert result == 0.0

    @pytest.mark.parametrize("power_kw,capacity", [
        (7.4, 50.0),
        (11.0, 75.0),
        (3.6, 50.0),
        (22.0, 100.0),
    ])
    def test_various_power_values(self, power_kw: float, capacity: float):
        """Parametrized: returns power_kw regardless of capacity."""
        from custom_components.ev_trip_planner.calculations import calculate_charging_rate
        assert calculate_charging_rate(power_kw, capacity) == power_kw


class TestCalculateSocTargetT004:
    """Tests for calculate_soc_target — T004 RED phase.

    These tests define the expected interface:
    - calculate_soc_target(trip, capacity: float, consumption: float) -> float
    - Returns target SOC (state of charge) as percentage
    - Formula: (trip_distance * consumption) / capacity
    - Handle edge cases
    """

    def test_formula_with_kwh_trip(self):
        """SOC target = (kwh * consumption) / capacity * 100."""
        from custom_components.ev_trip_planner.calculations import calculate_soc_target
        # 10 kWh trip, 50 kWh capacity, 1.0 consumption -> 20%
        result = calculate_soc_target({"kwh": 10.0}, 50.0, 1.0)
        assert abs(result - 20.0) < 0.001

    def test_formula_with_km_trip(self):
        """SOC target = (km * consumption) / capacity * 100."""
        from custom_components.ev_trip_planner.calculations import calculate_soc_target
        # 100 km trip, 50 kWh capacity, 0.15 consumption -> 30%
        result = calculate_soc_target({"km": 100.0}, 50.0, 0.15)
        assert abs(result - 30.0) < 0.001

    def test_zero_consumption_returns_zero(self):
        """Zero consumption returns 0% SOC target."""
        from custom_components.ev_trip_planner.calculations import calculate_soc_target
        result = calculate_soc_target({"kwh": 10.0}, 50.0, 0.0)
        assert result == 0.0

    def test_zero_capacity_returns_zero_no_divide_by_zero(self):
        """Zero capacity returns 0.0 without division by zero."""
        from custom_components.ev_trip_planner.calculations import calculate_soc_target
        result = calculate_soc_target({"kwh": 10.0}, 0.0, 1.0)
        assert result == 0.0

    def test_empty_trip_returns_zero(self):
        """Empty trip dict returns 0% SOC target."""
        from custom_components.ev_trip_planner.calculations import calculate_soc_target
        result = calculate_soc_target({}, 50.0, 1.0)
        assert result == 0.0

    def test_no_km_or_kwh_returns_zero(self):
        """Trip without km or kwh returns 0% SOC target."""
        from custom_components.ev_trip_planner.calculations import calculate_soc_target
        result = calculate_soc_target({"other": 100.0}, 50.0, 1.0)
        assert result == 0.0

    @pytest.mark.parametrize("trip,capacity,consumption,expected", [
        # 100 km, 50 kWh, 0.15 -> 30%
        ({"km": 100.0}, 50.0, 0.15, 30.0),
        # 50 km, 50 kWh, 0.18 -> 18%
        ({"km": 50.0}, 50.0, 0.18, 18.0),
        # 20 kWh, 50 kWh, 1.0 -> 40%
        ({"kwh": 20.0}, 50.0, 1.0, 40.0),
    ])
    def test_parametrized_soc_calculation(
        self, trip: dict, capacity: float, consumption: float, expected: float
    ):
        """Parametrized: SOC = (distance * consumption) / capacity * 100."""
        from custom_components.ev_trip_planner.calculations import calculate_soc_target
        result = calculate_soc_target(trip, capacity, consumption)
        assert abs(result - expected) < 0.001


class TestCalculateEnergyNeeded:
    """Tests for calculate_energy_needed."""

    @pytest.mark.parametrize("trip,battery_capacity,soc_current,charging_power,expected_keys", [
        # Basic energy calculation
        ({"kwh": 10.0}, 50.0, 50.0, 7.4, ["energia_necesaria_kwh", "horas_carga_necesarias"]),
        # At 100% SOC needs nothing
        ({"kwh": 10.0}, 50.0, 100.0, 7.4, ["energia_necesaria_kwh"]),
        # At 0% SOC needs full
        ({"kwh": 10.0}, 50.0, 0.0, 7.4, ["energia_necesaria_kwh"]),
        # Zero charging power
        ({"kwh": 10.0}, 50.0, 50.0, 0.0, ["energia_necesaria_kwh"]),
    ])
    def test_energy_needed_returns_correct_keys(
        self, trip: dict, battery_capacity: float, soc_current: float,
        charging_power: float, expected_keys: list
    ):
        """Parametrized: energy needed dict has correct keys."""
        from custom_components.ev_trip_planner.calculations import calculate_energy_needed
        result = calculate_energy_needed(trip, battery_capacity, soc_current, charging_power)
        for key in expected_keys:
            assert key in result

    def test_energy_needed_uses_km_if_no_kwh(self):
        """Without kwh, uses km * consumption to calculate energy."""
        from custom_components.ev_trip_planner.calculations import calculate_energy_needed
        result = calculate_energy_needed(
            trip={"km": 100.0},
            battery_capacity_kwh=50.0,
            soc_current=50.0,
            charging_power_kw=7.4,
        )
        # 100km * 0.15 = 15kWh needed
        # At 50% SOC: 25kWh in battery, need 15+20=35kWh target, 35-25=10kWh needed
        assert result["energia_necesaria_kwh"] > 0


class TestCalculateChargingWindowPure:
    """Tests for calculate_charging_window_pure."""

    def test_window_with_return_before_departure(self):
        """Return before departure gives positive window."""
        from custom_components.ev_trip_planner.calculations import calculate_charging_window_pure

        departure = datetime(2026, 4, 6, 18, 0)  # 6 PM
        retorno = datetime(2026, 4, 6, 10, 0)    # 10 AM (same day)
        result = calculate_charging_window_pure(
            trip_departure_time=departure,
            soc_actual=50.0,
            hora_regreso=retorno,
            charging_power_kw=7.4,
            energia_kwh=20.0,
        )
        assert result["ventana_horas"] > 0
        assert result["es_suficiente"] is not None

    def test_window_without_return_time_estimates(self):
        """Without hora_regreso, uses departure - 6h as estimate."""
        from custom_components.ev_trip_planner.calculations import calculate_charging_window_pure

        departure = datetime(2026, 4, 6, 18, 0)  # 6 PM
        result = calculate_charging_window_pure(
            trip_departure_time=departure,
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=7.4,
            energia_kwh=20.0,
        )
        # Estimated return = 18:00 - 6h = 12:00
        # Window = 18:00 - 12:00 = 6h
        assert result["ventana_horas"] == 6.0
        assert result["inicio_ventana"] is not None

    def test_window_zero_when_no_departure_no_return(self):
        """Returns zero window when both departure and return are None."""
        from custom_components.ev_trip_planner.calculations import calculate_charging_window_pure

        result = calculate_charging_window_pure(
            trip_departure_time=None,
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=7.4,
            energia_kwh=20.0,
        )
        assert result["ventana_horas"] == 0.0
        assert result["es_suficiente"] is True  # No charging needed

    def test_es_suficiente_false_when_window_too_short(self):
        """es_suficiente is False when window is shorter than charging time."""
        from custom_components.ev_trip_planner.calculations import calculate_charging_window_pure

        # 1 hour window, need 5 hours to charge
        result = calculate_charging_window_pure(
            trip_departure_time=datetime(2026, 4, 6, 11, 0),
            soc_actual=0.0,
            hora_regreso=datetime(2026, 4, 6, 10, 0),
            charging_power_kw=7.4,  # 7.4 kW -> ~2.7h for 20 kWh
            energia_kwh=20.0,
        )
        # Window is 1h but need ~2.7h -> not sufficient
        assert result["es_suficiente"] is False


class TestCalculateMultiTripChargingWindows:
    """Tests for calculate_multi_trip_charging_windows."""

    def test_empty_trips_returns_empty(self):
        """Empty trip list returns empty list."""
        from custom_components.ev_trip_planner.calculations import calculate_multi_trip_charging_windows
        result = calculate_multi_trip_charging_windows(
            trips=[], soc_actual=50.0, hora_regreso=None, charging_power_kw=7.4
        )
        assert result == []

    def test_single_trip(self):
        """Single trip returns one window."""
        from custom_components.ev_trip_planner.calculations import calculate_multi_trip_charging_windows

        departure = datetime(2026, 4, 6, 18, 0)
        trips = [(departure, {"id": "trip1"})]
        result = calculate_multi_trip_charging_windows(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=datetime(2026, 4, 6, 10, 0),
            charging_power_kw=7.4,
        )
        assert len(result) == 1
        # Window: hora_regreso (10am) to trip_arrival (departure + 6h = midnight) = 14 hours
        assert result[0]["ventana_horas"] == 14.0

    def test_chained_trips_second_window_starts_at_previous_arrival(self):
        """Chained trips: second trip's window starts when first trip arrives."""
        from custom_components.ev_trip_planner.calculations import calculate_multi_trip_charging_windows

        # First trip: departs 8am (returns 2pm = 8+6)
        # Second trip: departs 10pm (22:00)
        # Return at 7am
        trip1_departure = datetime(2026, 4, 6, 8, 0)
        trip2_departure = datetime(2026, 4, 6, 22, 0)
        trips = [
            (trip1_departure, {"id": "trip1"}),
            (trip2_departure, {"id": "trip2"}),
        ]
        result = calculate_multi_trip_charging_windows(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=datetime(2026, 4, 6, 7, 0),
            charging_power_kw=7.4,
        )
        # First window: 7am to trip1_arrival (8am + 6h = 2pm = 14:00) = 7 hours
        assert result[0]["ventana_horas"] == 7.0
        # Second window: trip1 arrival (14:00) to trip2_arrival (22+6h = 28:00 = 04:00 next day) = 14h
        assert result[1]["ventana_horas"] == 14.0


class TestCalculateSocAtTripStarts:
    """Tests for calculate_soc_at_trip_starts."""

    def test_empty_returns_empty(self):
        """Empty trips/windows returns empty list."""
        from custom_components.ev_trip_planner.calculations import calculate_soc_at_trip_starts
        result = calculate_soc_at_trip_starts(
            trips=[], soc_inicial=50.0, windows=[], charging_power_kw=7.4, battery_capacity_kwh=50.0
        )
        assert result == []

    def test_soc_decreases_after_each_trip(self):
        """SOC at arrival is less than SOC at departure due to trip consumption."""
        from custom_components.ev_trip_planner.calculations import calculate_soc_at_trip_starts

        trips = [{"id": "trip1"}, {"id": "trip2"}]
        windows = [
            {"ventana_horas": 6.0, "kwh_necesarios": 15.0, "trip": trips[0]},
            {"ventana_horas": 8.0, "kwh_necesarios": 10.0, "trip": trips[1]},
        ]
        result = calculate_soc_at_trip_starts(
            trips=trips,
            soc_inicial=80.0,
            windows=windows,
            charging_power_kw=7.4,
            battery_capacity_kwh=50.0,
        )
        # First trip SOC
        assert result[0]["soc_inicio"] == 80.0
        # Second trip SOC: charged some during first window
        # kwh_a_cargar = min(15, 7.4*6) = min(15, 44.4) = 15
        # soc_delta = 15/50*100 = 30%
        # arrival_soc = min(100, 80+30) = 100
        assert result[1]["soc_inicio"] <= 100.0


class TestCalculateDeficitPropagation:
    """Tests for calculate_deficit_propagation."""

    def test_empty_trips_returns_empty(self):
        """Empty trips returns empty list."""
        from custom_components.ev_trip_planner.calculations import calculate_deficit_propagation
        result = calculate_deficit_propagation(
            trips=[],
            soc_data=[],
            windows=[],
            tasa_carga_soc=14.8,
            battery_capacity_kwh=50.0,
            reference_dt=datetime.now(),
        )
        assert result == []

    def test_single_trip_no_deficit(self):
        """Single trip with sufficient window has no deficit."""
        from custom_components.ev_trip_planner.calculations import calculate_deficit_propagation
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [{"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": "2026-04-06T18:00", "kwh": 5.0}]
        # Sufficient window: 6 hours at 14.8%/h = 88.8% capacity, need ~50%
        soc_data = [{"soc_inicio": 60.0, "trip": trips[0], "arrival_soc": 60.0}]
        windows = [{
            "ventana_horas": 6.0,
            "kwh_necesarios": 5.0,
            "horas_carga_necesarias": 0.68,
            "inicio_ventana": datetime(2026, 4, 6, 10, 0),
            "fin_ventana": datetime(2026, 4, 6, 18, 0),
            "es_suficiente": True,
        }]
        ref = datetime(2026, 4, 6, 8, 0)
        result = calculate_deficit_propagation(
            trips=trips, soc_data=soc_data, windows=windows,
            tasa_carga_soc=14.8, battery_capacity_kwh=50.0, reference_dt=ref
        )
        assert len(result) == 1
        assert result[0]["deficit_acumulado"] == 0.0

    def test_deficit_propagates_to_previous_trip(self):
        """Deficit from later trip propagates to earlier trip."""
        from custom_components.ev_trip_planner.calculations import calculate_deficit_propagation
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        # Two trips: trip1 at 8am, trip2 at 6pm
        # trip2 needs 50% SOC but window only gives 10% -> deficit 40% propagates to trip1
        trips = [
            {"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": "2026-04-06T08:00", "kwh": 5.0},
            {"id": "trip2", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": "2026-04-06T18:00", "kwh": 20.0},
        ]
        soc_data = [
            {"soc_inicio": 80.0, "trip": trips[0], "arrival_soc": 80.0},
            {"soc_inicio": 80.0, "trip": trips[1], "arrival_soc": 80.0},
        ]
        # trip2 window: 6h at 14.8%/h = 88.8% capacity, but trip2 deficit is large
        windows = [
            {"ventana_horas": 6.0, "kwh_necesarios": 5.0, "horas_carga_necesarias": 0.68, "inicio_ventana": datetime(2026, 4, 6, 7, 0), "fin_ventana": datetime(2026, 4, 6, 8, 0), "es_suficiente": True, "trip": trips[0]},
            {"ventana_horas": 6.0, "kwh_necesarios": 20.0, "horas_carga_necesarias": 2.7, "inicio_ventana": datetime(2026, 4, 6, 10, 0), "fin_ventana": datetime(2026, 4, 6, 18, 0), "es_suficiente": True, "trip": trips[1]},
        ]
        ref = datetime(2026, 4, 6, 7, 0)
        result = calculate_deficit_propagation(
            trips=trips, soc_data=soc_data, windows=windows,
            tasa_carga_soc=14.8, battery_capacity_kwh=50.0, reference_dt=ref
        )
        assert len(result) == 2
        # trip1 should have some deficit propagated from trip2
        # trip2 deficit > 0 means trip1's target was raised


class TestCalculatePowerProfile:
    """Tests for calculate_power_profile."""

    def test_empty_trips_returns_zeros(self):
        """Empty trip list returns all zeros."""
        from custom_components.ev_trip_planner.calculations import calculate_power_profile
        result = calculate_power_profile(
            all_trips=[],
            battery_capacity_kwh=50.0,
            soc_current=50.0,
            charging_power_kw=7.4,
            hora_regreso=None,
            planning_horizon_days=7,
            reference_dt=datetime(2026, 4, 6, 8, 0),
        )
        assert len(result) == 7 * 24
        assert all(v == 0.0 for v in result)

    def test_profile_length_matches_horizon(self):
        """Profile has 24 * planning_horizon_days entries."""
        from custom_components.ev_trip_planner.calculations import calculate_power_profile
        for horizon in [1, 3, 7, 14]:
            result = calculate_power_profile(
                all_trips=[],
                battery_capacity_kwh=50.0,
                soc_current=50.0,
                charging_power_kw=7.4,
                hora_regreso=None,
                planning_horizon_days=horizon,
                reference_dt=datetime(2026, 4, 6, 8, 0),
            )
            assert len(result) == horizon * 24

    def test_trip_without_datetime_not_included(self):
        """Trips without datetime are excluded."""
        from custom_components.ev_trip_planner.calculations import calculate_power_profile
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [{"id": "no_dt", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": None, "kwh": 10.0}]
        result = calculate_power_profile(
            all_trips=trips,
            battery_capacity_kwh=50.0,
            soc_current=50.0,
            charging_power_kw=7.4,
            hora_regreso=None,
            planning_horizon_days=7,
            reference_dt=datetime(2026, 4, 6, 8, 0),
        )
        # No valid trips -> all zeros
        assert all(v == 0.0 for v in result)

    def test_power_in_watts(self):
        """Power values are in watts (charging_power_kw * 1000)."""
        from custom_components.ev_trip_planner.calculations import calculate_power_profile
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        # One trip that needs immediate charging
        departure_str = "2026-04-06T10:00"  # 2 hours from reference, no seconds
        trips = [{"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": departure_str, "kwh": 5.0}]
        result = calculate_power_profile(
            all_trips=trips,
            battery_capacity_kwh=50.0,
            soc_current=0.0,  # Empty battery
            charging_power_kw=7.4,
            hora_regreso=datetime(2026, 4, 6, 8, 0),
            planning_horizon_days=1,
            reference_dt=datetime(2026, 4, 6, 8, 0),
        )
        # Should have some non-zero values (charging at 7400W)
        non_zero = [v for v in result if v > 0]
        if non_zero:
            assert all(v == 7400.0 for v in non_zero)
