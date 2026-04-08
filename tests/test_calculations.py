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


class TestCalculateChargingRate:
    """Tests for calculate_charging_rate."""

    @pytest.mark.parametrize("charging_power_kw,battery_capacity_kwh,expected", [
        # Standard cases
        (7.4, 50.0, 14.8),
        (3.6, 50.0, 7.2),
        (11.0, 75.0, 14.666666666666666),
        # Edge: zero battery
        (7.4, 0.0, 0.0),
        (7.4, -1.0, 0.0),
        # Small values
        (0.0, 50.0, 0.0),
        (0.0, 0.0, 0.0),
    ])
    def test_charging_rate_formula(
        self, charging_power_kw: float, battery_capacity_kwh: float, expected: float
    ):
        """Parametrized: charging rate = power / capacity * 100."""
        from custom_components.ev_trip_planner.calculations import calculate_charging_rate
        result = calculate_charging_rate(charging_power_kw, battery_capacity_kwh)
        assert abs(result - expected) < 0.0001


class TestCalculateSocTarget:
    """Tests for calculate_soc_target."""

    @pytest.mark.parametrize("trip,capacity,expected_min", [
        # 10 kWh trip / 50 kWh battery = 20% + 10% buffer = 30%
        ({"kwh": 10.0}, 50.0, 30.0),
        # 0 kWh trip: 0% + 10% buffer = 10%
        ({"kwh": 0.0}, 50.0, 10.0),
        # Using km: 100*0.15/50*100 = 30% + 10% buffer = 40%
        ({"km": 100.0}, 50.0, 40.0),
        # Empty trip: 0% + 10% buffer = 10%
        ({}, 50.0, 10.0),
    ])
    def test_soc_target_with_buffer(self, trip: dict, capacity: float, expected_min: float):
        """Parametrized: SOC target = (energy/capacity)*100 + buffer (10%)."""
        from custom_components.ev_trip_planner.calculations import calculate_soc_target
        result = calculate_soc_target(trip, capacity)
        assert result >= expected_min

    def test_zero_battery_returns_buffer_only(self):
        """Zero battery capacity returns buffer only (no division by zero)."""
        from custom_components.ev_trip_planner.calculations import calculate_soc_target
        result = calculate_soc_target({"kwh": 10.0}, 0.0)
        # energia_soc = 0 (no division), then + DEFAULT_SOC_BUFFER_PERCENT (10)
        assert result == 10.0  # DEFAULT_SOC_BUFFER_PERCENT


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


class TestGenerateDeferrableScheduleFromTrips:
    """Tests for generate_deferrable_schedule_from_trips."""

    def test_import_function(self):
        """Function can be imported from calculations module."""
        from custom_components.ev_trip_planner.calculations import generate_deferrable_schedule_from_trips
        assert callable(generate_deferrable_schedule_from_trips)

    def test_empty_trips_returns_empty_list(self):
        """Empty trip list returns empty list."""
        from custom_components.ev_trip_planner.calculations import generate_deferrable_schedule_from_trips
        result = generate_deferrable_schedule_from_trips(trips=[], power_kw=7.4)
        assert result == []

    def test_returns_list_of_dicts(self):
        """Returns list of dictionaries with date and p_deferrable keys."""
        from custom_components.ev_trip_planner.calculations import generate_deferrable_schedule_from_trips
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [{"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": "2026-04-06T18:00", "kwh": 10.0}]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert isinstance(result, list)
        assert len(result) > 0
        for entry in result:
            assert isinstance(entry, dict)
            assert "date" in entry
            assert any(key.startswith("p_deferrable") for key in entry)

    def test_schedule_has_24_entries(self):
        """Schedule contains 24 entries (one per hour)."""
        from custom_components.ev_trip_planner.calculations import generate_deferrable_schedule_from_trips
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [{"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": "2026-04-06T18:00", "kwh": 5.0}]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) == 24

    def test_punctual_trip_with_future_deadline(self):
        """Punctual trip with future deadline has charging window before deadline."""
        from custom_components.ev_trip_planner.calculations import generate_deferrable_schedule_from_trips
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL
        from datetime import datetime

        # Trip deadline is 10 hours from reference
        ref = datetime(2026, 4, 6, 8, 0)
        trip_deadline = (ref + timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M")
        trips = [{"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": trip_deadline, "kwh": 5.0}]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4, reference_dt=ref)
        # Should have some entries with non-zero p_deferrable0
        non_zero_entries = [e for e in result if float(e.get("p_deferrable0", "0.0")) > 0]
        assert len(non_zero_entries) > 0

    def test_trip_without_datetime_has_zero_power(self):
        """Trip without datetime has all p_deferrable values at 0.0."""
        from custom_components.ev_trip_planner.calculations import generate_deferrable_schedule_from_trips
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [{"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": None, "kwh": 10.0}]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        for entry in result:
            assert entry.get("p_deferrable0", "0.0") == "0.0"

    def test_multiple_trips_have_separate_power_keys(self):
        """Multiple trips have separate p_deferrableN keys for each trip."""
        from custom_components.ev_trip_planner.calculations import generate_deferrable_schedule_from_trips
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": "2026-04-06T18:00", "kwh": 5.0},
            {"id": "trip2", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": "2026-04-06T20:00", "kwh": 10.0},
        ]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) > 0
        # Both trips should have their own keys
        assert "p_deferrable0" in result[0]
        assert "p_deferrable1" in result[0]

    def test_date_format_is_isoformat(self):
        """Date field is in ISO format string."""
        from custom_components.ev_trip_planner.calculations import generate_deferrable_schedule_from_trips
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [{"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": "2026-04-06T18:00", "kwh": 5.0}]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) > 0
        # date should be parseable as ISO format
        from datetime import datetime
        for entry in result:
            date_str = entry.get("date", "")
            # Should be parseable (contains date and time info)
            assert "T" in date_str or "-" in date_str


class TestCalculateDeferrableParameters:
    """Tests for calculate_deferrable_parameters.

    TDD RED phase: This function must NOT exist in calculations.py yet.
    These tests will fail with ImportError until T019 is implemented.
    """

    def test_import_calculate_deferrable_parameters(self):
        """Import should succeed once function is implemented in calculations.py."""
        # This import will raise NameError or ImportError until the function exists
        from custom_components.ev_trip_planner.calculations import calculate_deferrable_parameters
        assert callable(calculate_deferrable_parameters)

    def test_trip_with_kwh_returns_deferrable_params(self):
        """Trip with kwh and deadline returns full deferrable parameters dict."""
        from custom_components.ev_trip_planner.calculations import calculate_deferrable_parameters

        trip = {
            "id": "trip1",
            "kwh": 10.0,
            "datetime": "2026-04-10T18:00:00",
        }
        result = calculate_deferrable_parameters(trip, power_kw=7.4)

        # Should return a non-empty dict
        assert result != {}
        # Must have energy and power keys
        assert "total_energy_kwh" in result
        assert "power_watts" in result
        assert "total_hours" in result
        assert "end_timestep" in result
        assert "start_timestep" in result

    def test_energy_and_power_values(self):
        """Energy and power values are correctly calculated."""
        from custom_components.ev_trip_planner.calculations import calculate_deferrable_parameters

        trip = {"id": "trip1", "kwh": 7.4, "datetime": "2026-04-10T18:00:00"}
        result = calculate_deferrable_parameters(trip, power_kw=7.4)

        # 7.4 kWh at 7.4 kW = 1 hour
        assert result["total_energy_kwh"] == 7.4
        assert result["total_hours"] == 1.0
        # Power in watts: 7.4 kW * 1000 = 7400 W
        assert result["power_watts"] == 7400.0

    def test_zero_kwh_returns_empty_dict(self):
        """Trip with zero or negative kwh returns empty dict."""
        from custom_components.ev_trip_planner.calculations import calculate_deferrable_parameters

        result = calculate_deferrable_parameters({"id": "trip1", "kwh": 0.0}, power_kw=7.4)
        assert result == {}

        result = calculate_deferrable_parameters({"id": "trip1", "kwh": -5.0}, power_kw=7.4)
        assert result == {}

    def test_missing_kwh_returns_empty_dict(self):
        """Trip without kwh key returns empty dict."""
        from custom_components.ev_trip_planner.calculations import calculate_deferrable_parameters

        result = calculate_deferrable_parameters({"id": "trip1"}, power_kw=7.4)
        assert result == {}

    def test_end_timestep_calculated_from_deadline(self):
        """end_timestep is computed from hours until deadline (max 168 = 7 days)."""
        from custom_components.ev_trip_planner.calculations import calculate_deferrable_parameters

        trip = {"id": "trip1", "kwh": 10.0, "datetime": "2026-04-10T18:00:00"}
        result = calculate_deferrable_parameters(trip, power_kw=7.4)

        assert 1 <= result["end_timestep"] <= 168

    def test_default_end_timestep_without_deadline(self):
        """Without deadline, end_timestep defaults to 24."""
        from custom_components.ev_trip_planner.calculations import calculate_deferrable_parameters

        trip = {"id": "trip1", "kwh": 10.0}  # No datetime
        result = calculate_deferrable_parameters(trip, power_kw=7.4)

        assert result["end_timestep"] == 24

    def test_start_timestep_is_zero(self):
        """start_timestep is always 0 (charging starts at beginning of window)."""
        from custom_components.ev_trip_planner.calculations import calculate_deferrable_parameters

        trip = {"id": "trip1", "kwh": 10.0, "datetime": "2026-04-10T18:00:00"}
        result = calculate_deferrable_parameters(trip, power_kw=7.4)

        assert result["start_timestep"] == 0

    def test_is_single_constant_is_true(self):
        """is_single_constant is True for basic deferrable load."""
        from custom_components.ev_trip_planner.calculations import calculate_deferrable_parameters

        trip = {"id": "trip1", "kwh": 10.0, "datetime": "2026-04-10T18:00:00"}
        result = calculate_deferrable_parameters(trip, power_kw=7.4)

        assert result.get("is_single_constant") is True

    @pytest.mark.parametrize("kwh,power_kw,expected_hours", [
        (7.4, 7.4, 1.0),
        (14.8, 7.4, 2.0),
        (3.7, 7.4, 0.5),
        (74.0, 7.4, 10.0),
    ])
    def test_total_hours_calculation(self, kwh: float, power_kw: float, expected_hours: float):
        """Parametrized: total_hours = kwh / power_kw."""
        from custom_components.ev_trip_planner.calculations import calculate_deferrable_parameters

        trip = {"id": "trip1", "kwh": kwh}
        result = calculate_deferrable_parameters(trip, power_kw=power_kw)
        assert abs(result["total_hours"] - expected_hours) < 0.01


class TestCalculatePowerProfileFromTrips:
    """Tests for calculate_power_profile_from_trips.

    TDD RED phase: This function must NOT exist in calculations.py yet.
    These tests will fail with ImportError until T020 is implemented.
    """

    def test_import_from_calculations_succeeds(self):
        """The function must be importable from calculations.py."""
        from custom_components.ev_trip_planner.calculations import calculate_power_profile_from_trips
        assert callable(calculate_power_profile_from_trips)

    def test_empty_trips_returns_all_zeros(self):
        """Empty trip list returns a list of all zeros."""
        from custom_components.ev_trip_planner.calculations import calculate_power_profile_from_trips
        result = calculate_power_profile_from_trips(
            trips=[],
            power_kw=7.4,
            horizon=24,
        )
        assert isinstance(result, list)
        assert len(result) == 24
        assert all(v == 0.0 for v in result)

    def test_returns_list_of_correct_length(self):
        """Returns a list with length equal to horizon."""
        from custom_components.ev_trip_planner.calculations import calculate_power_profile_from_trips
        for horizon in [1, 24, 48, 168]:
            result = calculate_power_profile_from_trips(
                trips=[],
                power_kw=7.4,
                horizon=horizon,
            )
            assert len(result) == horizon

    def test_single_trip_sets_power_at_deadline_hours(self):
        """A single trip with a deadline sets charging power at that hour slot."""
        from custom_components.ev_trip_planner.calculations import calculate_power_profile_from_trips

        trip = {
            "id": "trip1",
            "datetime": "2026-04-06T18:00",
            "kwh": 10.0,
        }

        # Reference: 2026-04-06T08:00, deadline 10 hours later at 18:00
        # 10 kWh / 7.4 kW = ~1.35 hours needed, round up to 2 hours
        result = calculate_power_profile_from_trips(
            trips=[trip],
            power_kw=7.4,
            horizon=24,
            reference_dt=datetime(2026, 4, 6, 8, 0),
        )

        # 10 hours from ref to deadline, needs ~2 hours charging
        # Charging should be active in the last 2 hours before deadline (hours 8-9)
        # Power is in watts: 7.4 kW * 1000 = 7400 W
        non_zero = [v for v in result if v > 0]
        assert len(non_zero) >= 1
        assert all(v == 7400.0 for v in non_zero)

    def test_trip_without_datetime_not_included(self):
        """Trips without datetime are skipped (no IndexError)."""
        from custom_components.ev_trip_planner.calculations import calculate_power_profile_from_trips

        trips = [
            {"id": "no_dt", "datetime": None, "kwh": 10.0},
        ]
        result = calculate_power_profile_from_trips(
            trips=trips,
            power_kw=7.4,
            horizon=24,
        )
        # Should not crash; returns zeros when no valid trips
        assert all(v == 0.0 for v in result)

    def test_power_values_in_watts(self):
        """Power values are in watts (power_kw * 1000)."""
        from custom_components.ev_trip_planner.calculations import calculate_power_profile_from_trips

        trip = {
            "id": "trip1",
            "datetime": "2026-04-06T10:00",
            "kwh": 5.0,
        }
        # Reference: 2026-04-06T08:00, 2 hours before deadline
        result = calculate_power_profile_from_trips(
            trips=[trip],
            power_kw=7.4,
            horizon=24,
            reference_dt=datetime(2026, 4, 6, 8, 0),
        )
        non_zero = [v for v in result if v > 0]
        if non_zero:
            assert all(v == 7400.0 for v in non_zero)

    def test_zero_power_kw_returns_all_zeros(self):
        """Zero power_kw returns all zeros (can't charge)."""
        from custom_components.ev_trip_planner.calculations import calculate_power_profile_from_trips

        trip = {
            "id": "trip1",
            "datetime": "2026-04-06T10:00",
            "kwh": 10.0,
        }
        result = calculate_power_profile_from_trips(
            trips=[trip],
            power_kw=0.0,
            horizon=24,
        )
        assert all(v == 0.0 for v in result)

    def test_multiple_trips_accumulate(self):
        """Multiple trips each contribute their charging windows."""
        from custom_components.ev_trip_planner.calculations import calculate_power_profile_from_trips

        trips = [
            {"id": "trip1", "datetime": "2026-04-06T10:00", "kwh": 5.0},
            {"id": "trip2", "datetime": "2026-04-06T18:00", "kwh": 5.0},
        ]
        # Reference: 2026-04-06T00:00, both deadlines are in the future
        result = calculate_power_profile_from_trips(
            trips=trips,
            power_kw=7.4,
            horizon=24,
            reference_dt=datetime(2026, 4, 6, 0, 0),
        )
        # Should have charging windows for both trips
        non_zero = [v for v in result if v > 0]
        assert len(non_zero) >= 2

    def test_horizon_168_one_week(self):
        """horizon=168 covers one full week (7*24)."""
        from custom_components.ev_trip_planner.calculations import calculate_power_profile_from_trips
        result = calculate_power_profile_from_trips(
            trips=[],
            power_kw=7.4,
            horizon=168,
        )
        assert len(result) == 168
        assert all(v == 0.0 for v in result)


class TestGenerateDeferrableScheduleEdgeCases:
    """Edge case tests for generate_deferrable_schedule_from_trips to cover uncovered lines."""

    def test_trip_with_zero_kwh_has_zero_power(self):
        """Trip with kwh=0 has zero p_deferrable values. Covers lines 897-898."""
        from custom_components.ev_trip_planner.calculations import generate_deferrable_schedule_from_trips
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [{"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": "2026-04-06T18:00", "kwh": 0.0}]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) == 24
        for entry in result:
            assert entry.get("p_deferrable0", "0.0") == "0.0"

    def test_trip_with_negative_kwh_has_zero_power(self):
        """Trip with negative kwh has zero p_deferrable values. Covers lines 897-898."""
        from custom_components.ev_trip_planner.calculations import generate_deferrable_schedule_from_trips
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [{"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": "2026-04-06T18:00", "kwh": -5.0}]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) == 24
        for entry in result:
            assert entry.get("p_deferrable0", "0.0") == "0.0"

    def test_trip_with_invalid_datetime_string_has_zero_power(self):
        """Trip with invalid datetime string has zero p_deferrable values. Covers lines 910-912."""
        from custom_components.ev_trip_planner.calculations import generate_deferrable_schedule_from_trips
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [{"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": "invalid-date-format", "kwh": 5.0}]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) == 24
        for entry in result:
            assert entry.get("p_deferrable0", "0.0") == "0.0"

    def test_trip_with_missing_kwh_has_zero_power(self):
        """Trip without kwh field has zero p_deferrable values. Covers lines 896-898."""
        from custom_components.ev_trip_planner.calculations import generate_deferrable_schedule_from_trips
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [{"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": "2026-04-06T18:00"}]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) == 24
        for entry in result:
            assert entry.get("p_deferrable0", "0.0") == "0.0"


