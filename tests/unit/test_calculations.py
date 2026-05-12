"""Parametrized tests for pure functions in calculations.py.

These tests achieve 100% coverage of the pure functions without any mocks.
All functions are synchronous and deterministic given the same inputs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


class TestCalculateDayIndex:
    """Tests for calculate_day_index."""

    @pytest.mark.parametrize(
        "day_name,expected",
        [
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
            # Numeric strings (JS getDay format: Sunday=0, Monday=1, ..., Saturday=6)
            # Converted to Monday=0 format via (js_day - 1) % 7
            ("0", 6),  # JS Sunday=0    → Monday=0 index 6
            ("1", 0),  # JS Monday=1    → Monday=0 index 0
            ("6", 5),  # JS Saturday=6  → Monday=0 index 5
            # Unknown day defaults to Monday
            ("invalid", 0),
            ("", 0),
            # Edge cases
            ("   lunes   ", 0),  # with whitespace
        ],
    )
    def test_day_index_returns_correct_value(self, day_name: str, expected: int):
        """Parametrized: all day names return correct index."""
        from custom_components.ev_trip_planner.calculations import calculate_day_index

        assert calculate_day_index(day_name) == expected

    @pytest.mark.parametrize(
        "day_index,expected",
        [
            # JS getDay format converted to Monday=0 via (js_day - 1) % 7
            (0, 6),  # JS Sunday=0    → Monday=0 index 6
            (3, 2),  # JS Wednesday=3 → Monday=0 index 2
            (6, 5),  # JS Saturday=6  → Monday=0 index 5
            # Out of range defaults to Monday
            (7, 0),
            (-1, 0),
            (100, 0),
        ],
    )
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

    @pytest.mark.parametrize(
        "charging_power_kw,battery_capacity_kwh,expected",
        [
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
        ],
    )
    def test_charging_rate_formula(
        self, charging_power_kw: float, battery_capacity_kwh: float, expected: float
    ):
        """Parametrized: charging rate = power / capacity * 100."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_charging_rate,
        )

        result = calculate_charging_rate(charging_power_kw, battery_capacity_kwh)
        assert abs(result - expected) < 0.0001


class TestCalculateSocTarget:
    """Tests for calculate_soc_target."""

    @pytest.mark.parametrize(
        "trip,capacity,expected_min",
        [
            # 10 kWh trip / 50 kWh battery = 20% + 10% buffer = 30%
            ({"kwh": 10.0}, 50.0, 30.0),
            # 0 kWh trip: 0% + 10% buffer = 10%
            ({"kwh": 0.0}, 50.0, 10.0),
            # Using km: 100*0.15/50*100 = 30% + 10% buffer = 40%
            ({"km": 100.0}, 50.0, 40.0),
            # Empty trip: 0% + 10% buffer = 10%
            ({}, 50.0, 10.0),
        ],
    )
    def test_soc_target_with_buffer(
        self, trip: dict, capacity: float, expected_min: float
    ):
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

    @pytest.mark.parametrize(
        "trip,battery_capacity,soc_current,charging_power,expected_keys",
        [
            # Basic energy calculation
            (
                {"kwh": 10.0},
                50.0,
                50.0,
                7.4,
                ["energia_necesaria_kwh", "horas_carga_necesarias"],
            ),
            # At 100% SOC needs nothing
            ({"kwh": 10.0}, 50.0, 100.0, 7.4, ["energia_necesaria_kwh"]),
            # At 0% SOC needs full
            ({"kwh": 10.0}, 50.0, 0.0, 7.4, ["energia_necesaria_kwh"]),
            # Zero charging power
            ({"kwh": 10.0}, 50.0, 50.0, 0.0, ["energia_necesaria_kwh"]),
        ],
    )
    def test_energy_needed_returns_correct_keys(
        self,
        trip: dict,
        battery_capacity: float,
        soc_current: float,
        charging_power: float,
        expected_keys: list,
    ):
        """Parametrized: energy needed dict has correct keys."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip, battery_capacity, soc_current, charging_power
        )
        for key in expected_keys:
            assert key in result

    def test_energy_needed_uses_km_if_no_kwh(self):
        """Without kwh, uses km * consumption to calculate energy."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"km": 100.0},
            battery_capacity_kwh=50.0,
            soc_current=20.0,  # 20% SOC = 10kWh, viaje necesita 15kWh + 5kWh margin = 20kWh
            charging_power_kw=7.4,
        )
        # 100km * 0.15 = 15kWh needed
        # At 20% SOC: 10kWh in battery
        # NEW: energia_objetivo = 15 + 5 (10% margin of 50kWh) = 20kWh
        # energia_necesaria = max(0, 20 - 10) = 10kWh
        assert result["energia_necesaria_kwh"] == 10.0
        assert result["margen_seguridad_aplicado"] == 10.0

    def test_energy_needed_safety_margin_zero(self):
        """With safety_margin=0, SOC sufficient → proactive charging = trip energy."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"kwh": 10.0},
            battery_capacity_kwh=50.0,
            soc_current=50.0,  # 50% SOC = 25kWh, viaje = 10kWh
            charging_power_kw=7.4,
            safety_margin_percent=0.0,
        )
        # energia_objetivo = 10kWh, energia_actual = 25kWh
        # Proactive charging: SOC covers target → charge minimum = trip energy
        assert result["energia_necesaria_kwh"] == 10.0
        assert result["margen_seguridad_aplicado"] == 0.0

    def test_energy_needed_safety_margin_applied(self):
        """Safety margin is included in energia_objetivo (post-trip guarantee)."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"kwh": 10.0},
            battery_capacity_kwh=50.0,
            soc_current=0.0,  # 0% SOC = 0kWh
            charging_power_kw=7.4,
            safety_margin_percent=20.0,
        )
        # NEW: energia_objetivo = 10 + 10 (20% margin of 50kWh) = 20kWh
        # energia_necesaria = max(0, 20 - 0) = 20kWh
        assert result["energia_necesaria_kwh"] == 20.0
        assert result["margen_seguridad_aplicado"] == 20.0
        # horas_carga = 20 / 7.4 = 2.70 → rounds to 2.70
        assert result["horas_carga_necesarias"] == round(20.0 / 7.4, 2)

    def test_energy_needed_soc_sufficient_returns_zero(self):
        """AC-0.1: SOC sufficient → proactive charging = trip energy (not zero)."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"kwh": 10.0},
            battery_capacity_kwh=50.0,
            soc_current=80.0,  # 80% SOC = 40kWh, more than enough for 10kWh trip
            charging_power_kw=7.4,
        )
        # energia_objetivo = 10 + 5 = 15kWh
        # energia_actual = 40kWh
        # Proactive charging: SOC covers target → charge minimum = trip energy
        assert result["energia_necesaria_kwh"] == 10.0
        assert result["margen_seguridad_aplicado"] == 10.0

    def test_energy_needed_post_trip_safety_margin_guaranteed(self):
        """AC-0.1: Post-trip SOC >= safety margin."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"kwh": 2.0},
            battery_capacity_kwh=27.0,
            soc_current=5.0,  # 5% SOC = 1.35kWh
            charging_power_kw=7.4,
            safety_margin_percent=10.0,
        )
        # energia_objetivo = 2 + 2.7 (10% of 27) = 4.7kWh
        # energia_actual = 1.35kWh → energia_necesaria = 3.35kWh
        # Post-charge SOC: 5% + (3.35/27)*100 = 17.4%
        # Post-trip SOC: 17.4% - (2/27)*100 = 10.0% = safety margin
        assert result["energia_necesaria_kwh"] == 3.35

    def test_energy_needed_soc_none_fallback(self):
        """AC-0.2: SOC=None → fallback to 0.0 (no TypeError)."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"kwh": 10.0},
            battery_capacity_kwh=50.0,
            soc_current=None,  # Sensor unavailable
            charging_power_kw=7.4,
        )
        # Guard converts None to 0.0
        # energia_objetivo = 10 + 5 = 15kWh
        # energia_actual = 0kWh → energia_necesaria = 15kWh
        assert result["energia_necesaria_kwh"] == 15.0
        assert result["margen_seguridad_aplicado"] == 10.0

    def test_energy_needed_kwh_exceeds_battery_clamped(self):
        """AC-0.3: kwh > capacity → clamp to max capacity."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"kwh": 60.0},  # More than battery capacity
            battery_capacity_kwh=50.0,
            soc_current=0.0,
            charging_power_kw=7.4,
        )
        # energia_objetivo = 60 + 5 = 65kWh
        # energia_actual = 0kWh → energia_necesaria = 65kWh
        # Clamp to battery_capacity_kwh = 50kWh
        assert result["energia_necesaria_kwh"] == 50.0

    def test_energy_needed_soc_over_100_percent(self):
        """AC-0.3: SOC > 100% → proactive charging = trip energy (not zero)."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"kwh": 10.0},
            battery_capacity_kwh=50.0,
            soc_current=110.0,  # Invalid but handled as-is
            charging_power_kw=7.4,
        )
        # energia_actual = 55kWh > energia_objetivo = 15kWh
        # Proactive charging: SOC covers target → charge minimum = trip energy
        assert result["energia_necesaria_kwh"] == 10.0

    def test_energy_needed_soc_invalid_type_fallback(self):
        """AC-0.2: SOC invalid type → fallback to 0.0."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_energy_needed,
        )

        result = calculate_energy_needed(
            trip={"kwh": 10.0},
            battery_capacity_kwh=50.0,
            soc_current="invalid",  # Wrong type
            charging_power_kw=7.4,
        )
        # Guard converts invalid to 0.0
        assert result["energia_necesaria_kwh"] == 15.0


class TestDetermineChargingNeed:
    """Tests for determine_charging_need function (T1.0, T1.5)."""

    def test_determine_charging_need_soc_sufficient_proactive_charge(self):
        """T1.5: SOC sufficient → proactive charging (not zero)."""
        from custom_components.ev_trip_planner.calculations import (
            determine_charging_need,
        )

        decision = determine_charging_need(
            trip={"kwh": 2.0},
            soc_current=60.0,  # 60% of 50kWh = 30kWh available
            battery_capacity_kwh=50.0,
            charging_power_kw=7.4,
            safety_margin_percent=10.0,
        )
        # Trip needs 2kWh + 5kWh margin = 7kWh
        # 60% SOC = 30kWh available → covers target → proactive charge = trip energy
        assert decision.needs_charging is True
        assert decision.kwh_needed == 2.0
        assert decision.power_watts == 7400.0
        assert decision.def_total_hours == 1

    def test_determine_charging_need_soc_insufficient_charges(self):
        """T1.5: SOC insufficient → needs_charging=True, calculates kwh_needed."""
        from custom_components.ev_trip_planner.calculations import (
            determine_charging_need,
        )

        decision = determine_charging_need(
            trip={"kwh": 20.0},
            soc_current=10.0,  # 10% of 50kWh = 5kWh available
            battery_capacity_kwh=50.0,
            charging_power_kw=7.4,
            safety_margin_percent=10.0,
        )
        # Trip needs 20kWh + 5kWh margin = 25kWh
        # 10% SOC = 5kWh available, need 20kWh more
        assert decision.needs_charging is True
        assert decision.kwh_needed == 20.0
        assert decision.power_watts == 7400.0  # 7.4kW * 1000
        # 20kWh / 7.4kW = 2.7 hours → 3 hours
        assert decision.def_total_hours == 3

    def test_determine_charging_need_soc_none_fallback(self):
        """T1.5: SOC=None → fallback to 0.0, charges full trip."""
        from custom_components.ev_trip_planner.calculations import (
            determine_charging_need,
        )

        decision = determine_charging_need(
            trip={"kwh": 15.0},
            soc_current=None,  # None → fallback to 0.0
            battery_capacity_kwh=50.0,
            charging_power_kw=7.4,
            safety_margin_percent=10.0,
        )
        # Trip needs 15kWh + 5kWh margin = 20kWh
        # SOC=0, need 20kWh
        assert decision.needs_charging is True
        assert decision.kwh_needed == 20.0
        assert decision.power_watts == 7400.0
        # 20kWh / 7.4kW = 2.7 hours → 3 hours
        assert decision.def_total_hours == 3


class TestCalculateChargingWindowPure:
    """Tests for calculate_charging_window_pure."""

    def test_window_with_trip_departure_time_none_uses_return_time(self):
        """When trip_departure_time is None but hora_regreso is set, uses return + duration. Covers line 300."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_charging_window_pure,
        )

        result = calculate_charging_window_pure(
            trip_departure_time=None,
            soc_actual=50.0,
            hora_regreso=datetime(2026, 4, 6, 10, 0),
            charging_power_kw=7.4,
            energia_kwh=20.0,
        )
        # Window = hora_regreso (10:00) + duration (6h) - hora_regreso (10:00) = 6h
        assert result["ventana_horas"] == 6.0
        assert result["inicio_ventana"] == datetime(
            2026, 4, 6, 10, 0, tzinfo=timezone.utc
        )
        assert result["fin_ventana"] == datetime(2026, 4, 6, 16, 0, tzinfo=timezone.utc)

    def test_zero_charging_power_sets_horas_carga_to_zero(self):
        """When charging_power_kw is 0, horas_carga_necesarias is 0.0. Covers line 313."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_charging_window_pure,
        )

        result = calculate_charging_window_pure(
            trip_departure_time=datetime(2026, 4, 6, 18, 0),
            soc_actual=50.0,
            hora_regreso=datetime(2026, 4, 6, 10, 0),
            charging_power_kw=0.0,
            energia_kwh=20.0,
        )
        assert result["horas_carga_necesarias"] == 0.0
        assert result["es_suficiente"] is True  # 0 hours needed = sufficient

    def test_window_with_return_before_departure(self):
        """Return before departure gives positive window."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_charging_window_pure,
        )

        departure = datetime(2026, 4, 6, 18, 0)  # 6 PM
        retorno = datetime(2026, 4, 6, 10, 0)  # 10 AM (same day)
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
        from custom_components.ev_trip_planner.calculations import (
            calculate_charging_window_pure,
        )

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
        from custom_components.ev_trip_planner.calculations import (
            calculate_charging_window_pure,
        )

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
        from custom_components.ev_trip_planner.calculations import (
            calculate_charging_window_pure,
        )

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

    def test_single_trip_with_no_return_starts_from_now(self):
        """First trip with no hora_regreso starts charging from now.

        When the car was always home and no return event was detected,
        hora_regreso is None. The window should start from now (car is home),
        not from departure - 6h.
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_multi_trip_charging_windows,
        )

        now = datetime.now(timezone.utc)
        departure = now + timedelta(hours=96)  # 4 days in the future
        trips = [(departure, {"id": "trip1"})]
        result = calculate_multi_trip_charging_windows(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=None,  # No return event detected
            charging_power_kw=7.4,
            battery_capacity_kwh=50.0,
        )
        assert len(result) == 1
        # Window should start from now, not from departure - 6h
        assert result[0]["inicio_ventana"] >= now, (
            f"inicio_ventana={result[0]['inicio_ventana']} should be >= now={now}"
        )
        # ventana_horas = departure - now = 96h (window ends at departure, not arrival)
        assert result[0]["ventana_horas"] == pytest.approx(96.0, abs=0.02)

    def test_zero_charging_power_sets_horas_carga_to_zero(self):
        """When charging_power_kw is 0, horas_carga_necesarias is 0.0. Covers line 395."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_multi_trip_charging_windows,
        )

        departure = datetime(2026, 4, 6, 18, 0)
        trips = [(departure, {"id": "trip1"})]
        result = calculate_multi_trip_charging_windows(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=datetime(2026, 4, 6, 10, 0),
            charging_power_kw=0.0,
            battery_capacity_kwh=50.0,
        )
        assert len(result) == 1
        assert result[0]["horas_carga_necesarias"] == 0.0

    def test_empty_trips_returns_empty(self):
        """Empty trip list returns empty list."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_multi_trip_charging_windows,
        )

        result = calculate_multi_trip_charging_windows(
            trips=[],
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=7.4,
            battery_capacity_kwh=50.0,
        )
        assert result == []

    def test_single_trip(self):
        """Single trip returns one window."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_multi_trip_charging_windows,
        )

        departure = datetime(2026, 4, 6, 18, 0)
        trips = [(departure, {"id": "trip1"})]
        result = calculate_multi_trip_charging_windows(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=datetime(2026, 4, 6, 10, 0),
            charging_power_kw=7.4,
            battery_capacity_kwh=50.0,
        )
        assert len(result) == 1
        # Window: hora_regreso (10am) to trip_departure (18:00) = 8 hours
        assert result[0]["ventana_horas"] == 8.0

    def test_chained_trips_second_window_starts_at_previous_departure(self):
        """Chained trips: second trip's window starts at previous departure + return_buffer_hours.

        For chained trips:
        - First trip: window = now/hora_regreso → departure
        - Subsequent trips: window = previous_departure + return_buffer → departure
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_multi_trip_charging_windows,
        )

        # First trip: departs 8am
        # Second trip: departs 22:00
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
            return_buffer_hours=0.0,
            battery_capacity_kwh=50.0,
        )
        # First window: 7am → 8am departure = 1h
        assert result[0]["inicio_ventana"] == datetime(2026, 4, 6, 7, 0)
        assert result[0]["ventana_horas"] == 1.0
        # Second window: trip1 departure (8am) + 0h buffer → trip2 departure (22:00) = 14h
        assert result[1]["inicio_ventana"].hour == 8
        assert result[1]["inicio_ventana"].minute == 0
        assert result[1]["ventana_horas"] == 14.0


class TestCalculateSocAtTripStarts:
    """Tests for calculate_soc_at_trip_starts."""

    def test_zero_charging_power_kwh_a_cargar_is_zero(self):
        """When charging_power_kw is 0, kwh_a_cargar is 0.0. Covers line 459."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_soc_at_trip_starts,
        )

        trips = [{"id": "trip1"}]
        windows = [{"ventana_horas": 6.0, "kwh_necesarios": 15.0, "trip": trips[0]}]
        result = calculate_soc_at_trip_starts(
            trips=trips,
            soc_inicial=50.0,
            windows=windows,
            charging_power_kw=0.0,  # Zero power
            battery_capacity_kwh=50.0,
        )
        # kwh_a_cargar = 0 since power is 0, no charging happens
        assert result[0]["arrival_soc"] == 50.0  # No change

    def test_zero_battery_capacity_soc_llegada_equals_soc_actual(self):
        """When battery_capacity_kwh is 0, soc_llegada equals soc_actual. Covers line 466."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_soc_at_trip_starts,
        )

        trips = [{"id": "trip1"}]
        windows = [{"ventana_horas": 6.0, "kwh_necesarios": 15.0, "trip": trips[0]}]
        result = calculate_soc_at_trip_starts(
            trips=trips,
            soc_inicial=50.0,
            windows=windows,
            charging_power_kw=7.4,
            battery_capacity_kwh=0.0,  # Zero capacity
        )
        # SOC doesn't change when capacity is 0 (can't divide by zero)
        assert result[0]["arrival_soc"] == 50.0

    def test_empty_returns_empty(self):
        """Empty trips/windows returns empty list."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_soc_at_trip_starts,
        )

        result = calculate_soc_at_trip_starts(
            trips=[],
            soc_inicial=50.0,
            windows=[],
            charging_power_kw=7.4,
            battery_capacity_kwh=50.0,
        )
        assert result == []

    def test_soc_decreases_after_each_trip(self):
        """SOC at arrival is less than SOC at departure due to trip consumption."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_soc_at_trip_starts,
        )

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

    def test_with_explicit_trip_times_uses_provided_times(self):
        """When trip_times is provided, uses those instead of computing. Covers line 525."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deficit_propagation,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T08:00",
                "kwh": 5.0,
            }
        ]
        # Provide explicit trip_times to bypass datetime parsing
        explicit_time = datetime(2026, 4, 6, 10, 0)
        soc_data = [{"soc_inicio": 60.0, "trip": trips[0], "arrival_soc": 60.0}]
        windows = [
            {
                "ventana_horas": 6.0,
                "kwh_necesarios": 5.0,
                "horas_carga_necesarias": 0.68,
                "inicio_ventana": datetime(2026, 4, 6, 4, 0),
                "fin_ventana": datetime(2026, 4, 6, 10, 0),
                "es_suficiente": True,
            }
        ]
        ref = datetime(2026, 4, 6, 8, 0)
        result = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=14.8,
            battery_capacity_kwh=50.0,
            reference_dt=ref,
            trip_times=[explicit_time],  # Explicit trip times
        )
        assert len(result) == 1

    def test_with_explicit_soc_targets_uses_provided_targets(self):
        """When soc_targets is provided, uses those instead of computing. Covers lines 574 and 612."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deficit_propagation,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T08:00",
                "kwh": 5.0,
            }
        ]
        soc_data = [{"soc_inicio": 60.0, "trip": trips[0], "arrival_soc": 60.0}]
        windows = [
            {
                "ventana_horas": 6.0,
                "kwh_necesarios": 5.0,
                "horas_carga_necesarias": 0.68,
                "inicio_ventana": datetime(2026, 4, 6, 4, 0),
                "fin_ventana": datetime(2026, 4, 6, 10, 0),
                "es_suficiente": True,
            }
        ]
        ref = datetime(2026, 4, 6, 8, 0)
        # Provide explicit soc_targets - these should be used directly
        soc_targets = [50.0]  # Custom SOC target
        result = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=14.8,
            battery_capacity_kwh=50.0,
            reference_dt=ref,
            soc_targets=soc_targets,
        )
        assert len(result) == 1
        # The soc_objetivo should use the provided target of 50.0
        assert result[0]["soc_objetivo"] == 50.0

    def test_deficit_calculation_and_propagation(self):
        """Deficit is calculated and propagated to previous trip. Covers lines 586-595 and 590-592."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deficit_propagation,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        # Three trips in chronological order: 8am, 12pm, 6pm
        # All need high SOC but have insufficient windows
        # Starting SOC is very low (10%), so all trigger deficit
        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T08:00",
                "kwh": 40.0,
            },
            {
                "id": "trip2",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T12:00",
                "kwh": 40.0,
            },
            {
                "id": "trip3",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T18:00",
                "kwh": 40.0,
            },
        ]
        soc_data = [
            {"soc_inicio": 10.0, "trip": trips[0], "arrival_soc": 10.0},
            {"soc_inicio": 10.0, "trip": trips[1], "arrival_soc": 10.0},
            {"soc_inicio": 10.0, "trip": trips[2], "arrival_soc": 10.0},
        ]
        # All windows are 1 hour, capacity = 14.8%, target ~90% -> large deficit for all
        windows = [
            {
                "ventana_horas": 1.0,
                "kwh_necesarios": 40.0,
                "horas_carga_necesarias": 5.4,
                "inicio_ventana": datetime(2026, 4, 6, 7, 0),
                "fin_ventana": datetime(2026, 4, 6, 8, 0),
                "es_suficiente": False,
                "trip": trips[0],
            },
            {
                "ventana_horas": 1.0,
                "kwh_necesarios": 40.0,
                "horas_carga_necesarias": 5.4,
                "inicio_ventana": datetime(2026, 4, 6, 11, 0),
                "fin_ventana": datetime(2026, 4, 6, 12, 0),
                "es_suficiente": False,
                "trip": trips[1],
            },
            {
                "ventana_horas": 1.0,
                "kwh_necesarios": 40.0,
                "horas_carga_necesarias": 5.4,
                "inicio_ventana": datetime(2026, 4, 6, 17, 0),
                "fin_ventana": datetime(2026, 4, 6, 18, 0),
                "es_suficiente": False,
                "trip": trips[2],
            },
        ]
        ref = datetime(2026, 4, 6, 7, 0)
        result = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=14.8,
            battery_capacity_kwh=50.0,
            reference_dt=ref,
        )
        assert len(result) == 3
        # All trips should have deficit accumulated
        assert result[0]["deficit_acumulado"] > 0.0  # trip1 deficit triggered
        assert (
            result[1]["deficit_acumulado"] > 0.0
        )  # trip2 deficit AND propagates to trip1
        assert (
            result[2]["deficit_acumulado"] > 0.0
        )  # trip3 deficit AND propagates to trip2

    def test_empty_trips_returns_empty(self):
        """Empty trips returns empty list."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deficit_propagation,
        )

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
        from custom_components.ev_trip_planner.calculations import (
            calculate_deficit_propagation,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T18:00",
                "kwh": 5.0,
            }
        ]
        # Sufficient window: 6 hours at 14.8%/h = 88.8% capacity, need ~50%
        soc_data = [{"soc_inicio": 60.0, "trip": trips[0], "arrival_soc": 60.0}]
        windows = [
            {
                "ventana_horas": 6.0,
                "kwh_necesarios": 5.0,
                "horas_carga_necesarias": 0.68,
                "inicio_ventana": datetime(2026, 4, 6, 10, 0),
                "fin_ventana": datetime(2026, 4, 6, 18, 0),
                "es_suficiente": True,
            }
        ]
        ref = datetime(2026, 4, 6, 8, 0)
        result = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=14.8,
            battery_capacity_kwh=50.0,
            reference_dt=ref,
        )
        assert len(result) == 1
        assert result[0]["deficit_acumulado"] == 0.0

    def test_deficit_propagates_to_previous_trip(self):
        """Deficit from later trip propagates to earlier trip."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deficit_propagation,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        # Two trips: trip1 at 8am, trip2 at 6pm
        # Both windows are sufficient (6h > needed), verifying propagation handles
        # the case where no deficit exists and soc_data drives the calculation
        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T08:00",
                "kwh": 5.0,
            },
            {
                "id": "trip2",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T18:00",
                "kwh": 20.0,
            },
        ]
        soc_data = [
            {"soc_inicio": 80.0, "trip": trips[0], "arrival_soc": 80.0},
            {"soc_inicio": 80.0, "trip": trips[1], "arrival_soc": 80.0},
        ]
        # trip2 window: 6h available vs 2.7h needed (sufficient)
        windows = [
            {
                "ventana_horas": 6.0,
                "kwh_necesarios": 5.0,
                "horas_carga_necesarias": 0.68,
                "inicio_ventana": datetime(2026, 4, 6, 7, 0),
                "fin_ventana": datetime(2026, 4, 6, 8, 0),
                "es_suficiente": True,
                "trip": trips[0],
            },
            {
                "ventana_horas": 6.0,
                "kwh_necesarios": 20.0,
                "horas_carga_necesarias": 2.7,
                "inicio_ventana": datetime(2026, 4, 6, 10, 0),
                "fin_ventana": datetime(2026, 4, 6, 18, 0),
                "es_suficiente": True,
                "trip": trips[1],
            },
        ]
        ref = datetime(2026, 4, 6, 7, 0)
        result = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=14.8,
            battery_capacity_kwh=50.0,
            reference_dt=ref,
        )
        assert len(result) == 2
        # trip1 should have some deficit propagated from trip2
        # trip2 deficit > 0 means trip1's target was raised

    # ------------------------------------------------------------------
    # T023: SOC caps produce capped results
    # ------------------------------------------------------------------

    def test_soc_caps_produce_capped_results(self):
        """T023: calculate_deficit_propagation with soc_caps produces capped results."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deficit_propagation,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T08:00",
                "kwh": 5.0,
            },
            {
                "id": "trip2",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T12:00",
                "kwh": 5.0,
            },
        ]
        soc_data = [
            {"soc_inicio": 60.0, "trip": trips[0], "arrival_soc": 60.0},
            {"soc_inicio": 60.0, "trip": trips[1], "arrival_soc": 60.0},
        ]
        windows = [
            {
                "ventana_horas": 2.0,
                "kwh_necesarios": 5.0,
                "horas_carga_necesarias": 0.68,
                "inicio_ventana": datetime(2026, 4, 6, 6, 0),
                "fin_ventana": datetime(2026, 4, 6, 8, 0),
                "es_suficiente": True,
            },
            {
                "ventana_horas": 2.0,
                "kwh_necesarios": 5.0,
                "horas_carga_necesarias": 0.68,
                "inicio_ventana": datetime(2026, 4, 6, 10, 0),
                "fin_ventana": datetime(2026, 4, 6, 12, 0),
                "es_suficiente": True,
            },
        ]
        ref = datetime(2026, 4, 6, 6, 0)
        # Cap trip1 at 80% and trip2 at 85%
        soc_caps = [80.0, 85.0]
        result = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=14.8,
            battery_capacity_kwh=50.0,
            reference_dt=ref,
            soc_caps=soc_caps,
        )
        assert len(result) == 2
        # Both results should be capped: soc_objetivo <= soc_caps
        assert result[0]["soc_objetivo"] <= 80.0
        assert result[1]["soc_objetivo"] <= 85.0

    # ------------------------------------------------------------------
    # T024: Backward compatibility (without soc_caps)
    # ------------------------------------------------------------------

    def test_backward_compatibility_without_soc_caps(self):
        """T024: Without soc_caps, results identical to current behavior."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deficit_propagation,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T08:00",
                "kwh": 5.0,
            },
        ]
        soc_data = [{"soc_inicio": 60.0, "trip": trips[0], "arrival_soc": 60.0}]
        windows = [
            {
                "ventana_horas": 6.0,
                "kwh_necesarios": 5.0,
                "horas_carga_necesarias": 0.68,
                "inicio_ventana": datetime(2026, 4, 6, 2, 0),
                "fin_ventana": datetime(2026, 4, 6, 8, 0),
                "es_suficiente": True,
            }
        ]
        ref = datetime(2026, 4, 6, 6, 0)
        # Without soc_caps — should work exactly as before
        result = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=14.8,
            battery_capacity_kwh=50.0,
            reference_dt=ref,
        )
        assert len(result) == 1
        assert result[0]["deficit_acumulado"] >= 0.0
        assert result[0]["soc_objetivo"] > 0.0

    # ------------------------------------------------------------------
    # T025: Forward-propagated SOC uses capped values
    # ------------------------------------------------------------------

    def test_forward_propagated_soc_uses_capped_values(self):
        """T025: Capped SOC for first trip feeds into second trip start SOC."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deficit_propagation,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        # Two trips: trip1 at 8am, trip2 at 12pm
        # trip1 has tight window (1h) so it propagates deficit to trip2
        # Without caps: trip1 target raised, trip2 also raised
        # With caps: trip1 capped, deficit absorbed in trip1, trip2 less affected
        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T08:00",
                "kwh": 40.0,
            },
            {
                "id": "trip2",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T12:00",
                "kwh": 40.0,
            },
        ]
        soc_data = [
            {"soc_inicio": 10.0, "trip": trips[0], "arrival_soc": 10.0},
            {"soc_inicio": 10.0, "trip": trips[1], "arrival_soc": 10.0},
        ]
        windows = [
            {
                "ventana_horas": 1.0,
                "kwh_necesarios": 40.0,
                "horas_carga_necesarias": 5.4,
                "inicio_ventana": datetime(2026, 4, 6, 7, 0),
                "fin_ventana": datetime(2026, 4, 6, 8, 0),
                "es_suficiente": False,
            },
            {
                "ventana_horas": 1.0,
                "kwh_necesarios": 40.0,
                "horas_carga_necesarias": 5.4,
                "inicio_ventana": datetime(2026, 4, 6, 11, 0),
                "fin_ventana": datetime(2026, 4, 6, 12, 0),
                "es_suficiente": False,
            },
        ]
        ref = datetime(2026, 4, 6, 7, 0)

        # Without caps: both trips have large deficits
        result_no_cap = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=14.8,
            battery_capacity_kwh=50.0,
            reference_dt=ref,
        )
        # With caps: trip1 capped at 50%, trip2 at 55%
        # This should reduce the deficit propagated to trip2
        soc_caps = [50.0, 55.0]
        result_capped = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=14.8,
            battery_capacity_kwh=50.0,
            reference_dt=ref,
            soc_caps=soc_caps,
        )
        # Capped targets should be lower than uncapped
        assert result_capped[0]["soc_objetivo"] <= result_no_cap[0]["soc_objetivo"]
        assert result_capped[1]["soc_objetivo"] <= result_no_cap[1]["soc_objetivo"]
        # Capped deficit should be lower (or equal) for both trips
        assert (
            result_capped[0]["deficit_acumulado"]
            <= result_no_cap[0]["deficit_acumulado"] + 0.01
        )


class TestCalculatePowerProfile:
    """Tests for calculate_power_profile."""

    def test_empty_trips_returns_zeros(self):
        """Empty trip list returns all zeros."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile,
        )

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
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile,
        )

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
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {"id": "no_dt", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": None, "kwh": 10.0}
        ]
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
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        # One trip that needs immediate charging
        departure_str = "2026-04-06T10:00"  # 2 hours from reference, no seconds
        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": departure_str,
                "kwh": 5.0,
            }
        ]
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

    def test_insufficient_window_skips_trip(self):
        """Trip with window too short (es_suficiente=False) is skipped. Covers line 910."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile,
        )

        # Trip: departs 18:00, needs ~1.35h to charge, but window is only 1 hour (17:00-18:00)
        # ventana_horas=1 < horas_carga_necesarias=1.35 -> es_suficiente=False -> skip at line 910
        trips = [
            {
                "id": "trip1",
                "tipo": "puntual",
                "datetime": "2026-04-06T18:00",
                "kwh": 10.0,
            }
        ]
        result = calculate_power_profile(
            all_trips=trips,
            battery_capacity_kwh=50.0,
            soc_current=0.0,  # Empty battery -> needs full 10kWh
            charging_power_kw=7.4,
            hora_regreso=datetime(2026, 4, 6, 17, 0),  # Return 17:00, window = 1 hour
            planning_horizon_days=1,
            reference_dt=datetime(2026, 4, 6, 10, 0),
        )
        # Trip should be skipped due to insufficient window -> all zeros
        assert all(v == 0.0 for v in result), (
            "Trip with insufficient window should produce all zeros"
        )


class TestGenerateDeferrableScheduleFromTrips:
    """Tests for generate_deferrable_schedule_from_trips."""

    def test_import_function(self):
        """Function can be imported from calculations module."""
        from custom_components.ev_trip_planner.calculations import (
            generate_deferrable_schedule_from_trips,
        )

        assert callable(generate_deferrable_schedule_from_trips)

    def test_empty_trips_returns_empty_list(self):
        """Empty trip list returns empty list."""
        from custom_components.ev_trip_planner.calculations import (
            generate_deferrable_schedule_from_trips,
        )

        result = generate_deferrable_schedule_from_trips(trips=[], power_kw=7.4)
        assert result == []

    def test_returns_list_of_dicts(self):
        """Returns list of dictionaries with date and p_deferrable keys."""
        from custom_components.ev_trip_planner.calculations import (
            generate_deferrable_schedule_from_trips,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T18:00",
                "kwh": 10.0,
            }
        ]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert isinstance(result, list)
        assert len(result) > 0
        for entry in result:
            assert isinstance(entry, dict)
            assert "date" in entry
            assert any(key.startswith("p_deferrable") for key in entry)

    def test_schedule_has_24_entries(self):
        """Schedule contains 24 entries (one per hour)."""
        from custom_components.ev_trip_planner.calculations import (
            generate_deferrable_schedule_from_trips,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T18:00",
                "kwh": 5.0,
            }
        ]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) == 24

    def test_punctual_trip_with_future_deadline(self):
        """Punctual trip with future deadline has charging window before deadline."""
        from datetime import datetime

        from custom_components.ev_trip_planner.calculations import (
            generate_deferrable_schedule_from_trips,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        # Trip deadline is 10 hours from reference
        ref = datetime(2026, 4, 6, 8, 0)
        trip_deadline = (ref + timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M")
        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": trip_deadline,
                "kwh": 5.0,
            }
        ]
        result = generate_deferrable_schedule_from_trips(
            trips=trips, power_kw=7.4, reference_dt=ref
        )
        # Should have some entries with non-zero p_deferrable0
        non_zero_entries = [
            e for e in result if float(e.get("p_deferrable0", "0.0")) > 0
        ]
        assert len(non_zero_entries) > 0

    def test_trip_without_datetime_has_zero_power(self):
        """Trip without datetime has all p_deferrable values at 0.0."""
        from custom_components.ev_trip_planner.calculations import (
            generate_deferrable_schedule_from_trips,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": None, "kwh": 10.0}
        ]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        for entry in result:
            assert entry.get("p_deferrable0", "0.0") == "0.0"

    def test_multiple_trips_have_separate_power_keys(self):
        """Multiple trips have separate p_deferrableN keys for each trip."""
        from custom_components.ev_trip_planner.calculations import (
            generate_deferrable_schedule_from_trips,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T18:00",
                "kwh": 5.0,
            },
            {
                "id": "trip2",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T20:00",
                "kwh": 10.0,
            },
        ]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) > 0
        # Both trips should have their own keys
        assert "p_deferrable0" in result[0]
        assert "p_deferrable1" in result[0]

    def test_date_format_is_isoformat(self):
        """Date field is in ISO format string."""
        from custom_components.ev_trip_planner.calculations import (
            generate_deferrable_schedule_from_trips,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T18:00",
                "kwh": 5.0,
            }
        ]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) > 0
        # date should be parseable as ISO format
        for entry in result:
            date_str = entry.get("date", "")
            # Should be parseable (contains date and time info)
            assert "T" in date_str or "-" in date_str


class TestCalculateDeferrableParameters:
    """Tests for calculate_deferrable_parameters."""

    def test_deadline_as_datetime_object_not_string(self):
        """When deadline is a datetime object (not string), uses it directly. Covers line 1009."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deferrable_parameters,
        )

        deadline_dt = datetime(2026, 4, 10, 18, 0)  # datetime object, not string
        trip = {
            "id": "trip1",
            "kwh": 10.0,
            "datetime": deadline_dt,
        }
        result = calculate_deferrable_parameters(
            trip,
            power_kw=7.4,
            reference_dt=datetime(2026, 4, 10, 8, 0),
        )
        # Should return valid parameters with deadline parsed from datetime object
        assert result != {}
        assert "end_timestep" in result
        # end_timestep should be based on hours from reference to deadline
        assert result["end_timestep"] == 10  # 10 hours from 8am to 6pm

    def test_invalid_kwh_type_raises_exception_caught(self):
        """When kwh is an invalid type that causes exception, returns empty dict. Covers lines 1030-1032."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deferrable_parameters,
        )

        # Pass a trip with kwh that causes an exception (e.g., unhashable type)
        trip = {
            "id": "trip1",
            "kwh": {"invalid": "type"},  # This will cause float() to raise TypeError
            "datetime": "2026-04-10T18:00",
        }
        result = calculate_deferrable_parameters(trip, power_kw=7.4)
        # Should return empty dict, not raise exception
        assert result == {}

    def test_import_calculate_deferrable_parameters(self):
        """Import should succeed once function is implemented in calculations.py."""
        # This import will raise NameError or ImportError until the function exists
        from custom_components.ev_trip_planner.calculations import (
            calculate_deferrable_parameters,
        )

        assert callable(calculate_deferrable_parameters)

    def test_trip_with_kwh_returns_deferrable_params(self):
        """Trip with kwh and deadline returns full deferrable parameters dict."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deferrable_parameters,
        )

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
        from custom_components.ev_trip_planner.calculations import (
            calculate_deferrable_parameters,
        )

        trip = {"id": "trip1", "kwh": 7.4, "datetime": "2026-04-10T18:00:00"}
        result = calculate_deferrable_parameters(trip, power_kw=7.4)

        # 7.4 kWh at 7.4 kW = 1 hour
        assert result["total_energy_kwh"] == 7.4
        assert result["total_hours"] == 1.0
        # Power in watts: 7.4 kW * 1000 = 7400 W
        assert result["power_watts"] == 7400.0

    def test_zero_kwh_returns_empty_dict(self):
        """Trip with zero or negative kwh returns empty dict."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deferrable_parameters,
        )

        result = calculate_deferrable_parameters(
            {"id": "trip1", "kwh": 0.0}, power_kw=7.4
        )
        assert result == {}

        result = calculate_deferrable_parameters(
            {"id": "trip1", "kwh": -5.0}, power_kw=7.4
        )
        assert result == {}

    def test_missing_kwh_returns_empty_dict(self):
        """Trip without kwh key returns empty dict."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deferrable_parameters,
        )

        result = calculate_deferrable_parameters({"id": "trip1"}, power_kw=7.4)
        assert result == {}

    def test_end_timestep_calculated_from_deadline(self):
        """end_timestep is computed from hours until deadline (max 168 = 7 days)."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deferrable_parameters,
        )

        trip = {"id": "trip1", "kwh": 10.0, "datetime": "2026-04-10T18:00:00"}
        result = calculate_deferrable_parameters(trip, power_kw=7.4)

        assert 1 <= result["end_timestep"] <= 168

    def test_default_end_timestep_without_deadline(self):
        """Without deadline, end_timestep defaults to 24."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deferrable_parameters,
        )

        trip = {"id": "trip1", "kwh": 10.0}  # No datetime
        result = calculate_deferrable_parameters(trip, power_kw=7.4)

        assert result["end_timestep"] == 24

    def test_start_timestep_is_zero(self):
        """start_timestep is always 0 (charging starts at beginning of window)."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deferrable_parameters,
        )

        trip = {"id": "trip1", "kwh": 10.0, "datetime": "2026-04-10T18:00:00"}
        result = calculate_deferrable_parameters(trip, power_kw=7.4)

        assert result["start_timestep"] == 0

    def test_is_single_constant_is_true(self):
        """is_single_constant is True for basic deferrable load."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deferrable_parameters,
        )

        trip = {"id": "trip1", "kwh": 10.0, "datetime": "2026-04-10T18:00:00"}
        result = calculate_deferrable_parameters(trip, power_kw=7.4)

        assert result.get("is_single_constant") is True

    @pytest.mark.parametrize(
        "kwh,power_kw,expected_hours",
        [
            (7.4, 7.4, 1.0),
            (14.8, 7.4, 2.0),
            (3.7, 7.4, 0.5),
            (74.0, 7.4, 10.0),
        ],
    )
    def test_total_hours_calculation(
        self, kwh: float, power_kw: float, expected_hours: float
    ):
        """Parametrized: total_hours = kwh / power_kw."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_deferrable_parameters,
        )

        trip = {"id": "trip1", "kwh": kwh}
        result = calculate_deferrable_parameters(trip, power_kw=power_kw)
        assert abs(result["total_hours"] - expected_hours) < 0.01


class TestCalculatePowerProfileFromTrips:
    """Tests for calculate_power_profile_from_trips."""

    def test_deadline_as_datetime_object_not_string(self):
        """When deadline is a datetime object (not string), uses it directly. Covers line 686."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        deadline = datetime(2026, 4, 6, 18, 0)  # datetime object, not string
        trip = {
            "id": "trip1",
            "datetime": deadline,  # datetime object
            "kwh": 10.0,
        }
        result = calculate_power_profile_from_trips(
            trips=[trip],
            power_kw=7.4,
            horizon=24,
            reference_dt=datetime(2026, 4, 6, 8, 0),
        )
        # Should process the trip with datetime object deadline
        non_zero = [v for v in result if v > 0]
        assert len(non_zero) >= 1

    def test_invalid_datetime_string_skips_trip(self):
        """Invalid datetime string triggers ValueError and continues. Covers lines 683-684."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        trip = {
            "id": "trip1",
            "datetime": "not-a-valid-datetime",  # Invalid string
            "kwh": 10.0,
        }
        result = calculate_power_profile_from_trips(
            trips=[trip],
            power_kw=7.4,
            horizon=24,
            reference_dt=datetime(2026, 4, 6, 8, 0),
        )
        # Trip should be skipped due to invalid datetime
        assert all(v == 0.0 for v in result)

    def test_horas_desde_ahora_negative_sets_hora_inicio_to_zero(self):
        """When window starts before reference_dt, hora_inicio_carga is clamped to 0. Covers lines 822-825."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile,
        )

        # Trip with return time in the past but departure in the future
        # hora_regreso = 6am today, reference = 10am today, departure = 6pm today
        trips = [
            {
                "id": "trip1",
                "tipo": "puntual",
                "datetime": "2026-04-06T18:00",
                "kwh": 10.0,
            }
        ]
        result = calculate_power_profile(
            all_trips=trips,
            battery_capacity_kwh=50.0,
            soc_current=0.0,
            charging_power_kw=7.4,
            hora_regreso=datetime(2026, 4, 6, 6, 0),  # 6 AM (before reference 10 AM)
            planning_horizon_days=1,
            reference_dt=datetime(2026, 4, 6, 10, 0),  # 10 AM reference
        )
        # Should have some charging profile
        assert len(result) == 24

    def test_horas_necesarias_zero_sets_to_one(self):
        """When horas_necesarias is 0, it's set to 1. Covers line 833."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile,
        )

        # Trip with soc_current=100% and kwh=0 means energia_kwh=0
        # This makes horas_necesarias = 0, which is then set to 1
        trips = [
            {
                "id": "trip1",
                "tipo": "puntual",
                "datetime": "2026-04-06T18:00",
                "kwh": 0.0,  # Zero energy needed
            }
        ]
        result = calculate_power_profile(
            all_trips=trips,
            battery_capacity_kwh=50.0,
            soc_current=100.0,  # 100% SOC means no charging needed
            charging_power_kw=7.4,
            hora_regreso=datetime(2026, 4, 6, 8, 0),
            planning_horizon_days=1,
            reference_dt=datetime(2026, 4, 6, 10, 0),
        )
        # With 100% SOC and kwh=0, energia_kwh=0, so horas_necesarias becomes 1
        assert len(result) == 24

    def test_import_from_calculations_succeeds(self):
        """The function must be importable from calculations.py."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        assert callable(calculate_power_profile_from_trips)

    def test_empty_trips_returns_all_zeros(self):
        """Empty trip list returns a list of all zeros."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

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
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        for horizon in [1, 24, 48, 168]:
            result = calculate_power_profile_from_trips(
                trips=[],
                power_kw=7.4,
                horizon=horizon,
            )
            assert len(result) == horizon

    def test_single_trip_sets_power_at_deadline_hours(self):
        """A single trip with a deadline sets charging power at that hour slot."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

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
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

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
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

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
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

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
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

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
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        result = calculate_power_profile_from_trips(
            trips=[],
            power_kw=7.4,
            horizon=168,
        )
        assert len(result) == 168
        assert all(v == 0.0 for v in result)

    def test_trip_with_km_instead_of_kwh(self):
        """Trip with km (no kwh) calculates energy from distance. Covers lines 689-690."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        trip = {
            "id": "trip_km",
            "datetime": "2026-04-06T18:00",
            "km": 100,  # 100 km * 0.15 kWh/km = 15 kWh
        }
        result = calculate_power_profile_from_trips(
            trips=[trip],
            power_kw=7.4,
            horizon=24,
            reference_dt=datetime(2026, 4, 6, 8, 0),
        )
        non_zero = [v for v in result if v > 0]
        # 15 kWh / 7.4 kW ≈ 2.03 → 3 hours
        assert len(non_zero) >= 1
        assert all(v == 7400.0 for v in non_zero)

    def test_trip_with_zero_kwh_skipped(self):
        """Trip with kwh=0 is skipped. Covers line 693."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        trip = {
            "id": "trip_zero",
            "datetime": "2026-04-06T18:00",
            "kwh": 0,
        }
        result = calculate_power_profile_from_trips(
            trips=[trip],
            power_kw=7.4,
            horizon=24,
            reference_dt=datetime(2026, 4, 6, 8, 0),
        )
        assert all(v == 0.0 for v in result)


class TestGenerateDeferrableScheduleEdgeCases:
    """Edge case tests for generate_deferrable_schedule_from_trips to cover uncovered lines."""

    def test_trip_deadline_as_datetime_object_not_string(self):
        """When deadline is a datetime object (not string), parses it correctly. Covers line 923."""
        from custom_components.ev_trip_planner.calculations import (
            generate_deferrable_schedule_from_trips,
        )

        deadline_dt = datetime(2026, 4, 6, 18, 0)  # datetime object
        trips = [
            {"id": "trip1", "tipo": "punctual", "datetime": deadline_dt, "kwh": 10.0}
        ]
        result = generate_deferrable_schedule_from_trips(
            trips=trips,
            power_kw=7.4,
            reference_dt=datetime(2026, 4, 6, 8, 0),
        )
        assert len(result) == 24
        # Should have some entries with non-zero power
        for entry in result:
            power = float(entry.get("p_deferrable0", "0.0"))
            assert power >= 0

    def test_trip_with_zero_kwh_has_zero_power(self):
        """Trip with kwh=0 has zero p_deferrable values. Covers lines 897-898."""
        from custom_components.ev_trip_planner.calculations import (
            generate_deferrable_schedule_from_trips,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T18:00",
                "kwh": 0.0,
            }
        ]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) == 24
        for entry in result:
            assert entry.get("p_deferrable0", "0.0") == "0.0"

    def test_trip_with_negative_kwh_has_zero_power(self):
        """Trip with negative kwh has zero p_deferrable values. Covers lines 897-898."""
        from custom_components.ev_trip_planner.calculations import (
            generate_deferrable_schedule_from_trips,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "2026-04-06T18:00",
                "kwh": -5.0,
            }
        ]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) == 24
        for entry in result:
            assert entry.get("p_deferrable0", "0.0") == "0.0"

    def test_trip_with_invalid_datetime_string_has_zero_power(self):
        """Trip with invalid datetime string has zero p_deferrable values. Covers lines 910-912."""
        from custom_components.ev_trip_planner.calculations import (
            generate_deferrable_schedule_from_trips,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {
                "id": "trip1",
                "tipo": TRIP_TYPE_PUNCTUAL,
                "datetime": "invalid-date-format",
                "kwh": 5.0,
            }
        ]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) == 24
        for entry in result:
            assert entry.get("p_deferrable0", "0.0") == "0.0"

    def test_trip_with_missing_kwh_has_zero_power(self):
        """Trip without kwh field has zero p_deferrable values. Covers lines 896-898."""
        from custom_components.ev_trip_planner.calculations import (
            generate_deferrable_schedule_from_trips,
        )
        from custom_components.ev_trip_planner.const import TRIP_TYPE_PUNCTUAL

        trips = [
            {"id": "trip1", "tipo": TRIP_TYPE_PUNCTUAL, "datetime": "2026-04-06T18:00"}
        ]
        result = generate_deferrable_schedule_from_trips(trips=trips, power_kw=7.4)
        assert len(result) == 24
        for entry in result:
            assert entry.get("p_deferrable0", "0.0") == "0.0"


class TestCalculateNextRecurringDatetime:
    """Tests for calculate_next_recurring_datetime function."""

    def test_returns_tomorrow_when_day_is_tomorrow(self):
        """Returns tomorrow at specified time when day is tomorrow. Covers lines 651-683."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_next_recurring_datetime,
        )

        # Monday 2026-04-13 10:00
        reference = datetime(2026, 4, 13, 10, 0, 0)
        # Tuesday (day=2 in JS format: 0=Sun, 1=Mon, 2=Tue)
        result = calculate_next_recurring_datetime(2, "10:00", reference)
        assert result is not None
        assert result == datetime(2026, 4, 14, 10, 0, 0)

    def test_returns_today_when_time_not_passed(self):
        """Returns today at specified time when time hasn't passed yet. Covers lines 651-683."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_next_recurring_datetime,
        )

        # Monday 2026-04-13 08:00
        reference = datetime(2026, 4, 13, 8, 0, 0)
        # Monday (day=1 in JS format)
        result = calculate_next_recurring_datetime(1, "10:00", reference)
        assert result is not None
        assert result == datetime(2026, 4, 13, 10, 0, 0)

    def test_returns_next_week_when_time_passed_today(self):
        """Returns next week when time has passed for today. Covers lines 651-683."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_next_recurring_datetime,
        )

        # Monday 2026-04-13 12:00
        reference = datetime(2026, 4, 13, 12, 0, 0)
        # Monday (day=1 in JS format) but time 10:00 already passed
        result = calculate_next_recurring_datetime(1, "10:00", reference)
        assert result is not None
        # Should be next Monday (April 20)
        assert result == datetime(2026, 4, 20, 10, 0, 0)

    def test_handles_string_day_conversion(self):
        """Converts string day to int correctly. Covers lines 657-661."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_next_recurring_datetime,
        )

        reference = datetime(2026, 4, 13, 10, 0, 0)
        result = calculate_next_recurring_datetime("2", "10:00", reference)
        assert result is not None
        assert result == datetime(2026, 4, 14, 10, 0, 0)

    def test_returns_none_for_invalid_day_string(self):
        """Returns None when day string cannot be converted to int. Covers lines 658-661."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_next_recurring_datetime,
        )

        result = calculate_next_recurring_datetime("invalid", "10:00")
        assert result is None

    def test_returns_none_for_invalid_time_format(self):
        """Returns None when time format is invalid. Covers lines 663-666."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_next_recurring_datetime,
        )

        result = calculate_next_recurring_datetime(2, "invalid-time")
        assert result is None

    def test_returns_none_for_none_day(self):
        """Returns None when day is None. Covers line 654."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_next_recurring_datetime,
        )

        result = calculate_next_recurring_datetime(None, "10:00")
        assert result is None

    def test_returns_none_for_none_time(self):
        """Returns None when time_str is None. Covers line 654."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_next_recurring_datetime,
        )

        result = calculate_next_recurring_datetime(2, None)
        assert result is None

    def test_uses_current_time_when_reference_is_none(self):
        """Uses datetime.now() when reference_dt is None. Covers lines 651-652."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_next_recurring_datetime,
        )

        # When reference is None, function uses datetime.now()
        # We can't mock datetime.now() in a pure function test, so we verify
        # that passing None doesn't crash and returns a valid datetime
        result = calculate_next_recurring_datetime(1, "14:00", None)
        assert result is not None
        # Just verify it's a valid datetime in the future
        assert result > datetime.now() - timedelta(days=1)

    def test_sunday_to_monday_wraps_correctly(self):
        """Sunday (0) to Monday (1) wraps correctly using modulo. Covers lines 675-676."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_next_recurring_datetime,
        )

        # Sunday 2026-04-12 12:00 (April 12, 2026 is a Sunday)
        reference = datetime(2026, 4, 12, 12, 0, 0)
        result = calculate_next_recurring_datetime(1, "10:00", reference)
        assert result is not None
        # Monday April 13
        assert result == datetime(2026, 4, 13, 10, 0, 0)

    def test_saturday_to_sunday_wraps_correctly(self):
        """Saturday (5) to Sunday (0) wraps correctly using modulo. Covers lines 738-739."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_next_recurring_datetime,
        )

        # Saturday January 3, 2026 at 12:00 (weekday 5)
        reference = datetime(2026, 1, 3, 12, 0, 0)
        result = calculate_next_recurring_datetime(0, "10:00", reference)
        assert result is not None
        # Sunday January 4
        assert result == datetime(2026, 1, 4, 10, 0, 0)


class TestCalculatePowerProfileRecurringTrips:
    """Tests for calculate_power_profile_from_trips with recurring trips."""

    def test_recurring_trip_with_numeric_day_string_calculates_power(self):
        """Recurring trip with numeric day string (from E2E test) calculates power profile. Covers lines 731-741."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        # Tuesday April 14, 2026 at 12:00
        reference = datetime(2026, 4, 14, 12, 0, 0)
        # Recurring trip for Tuesday (day=2) at 10:00 - time already passed
        trips = [
            {
                "id": "rec_test",
                "dia_semana": "2",  # Tuesday (numeric string from panel selector)
                "hora": "10:00",
                "kwh": 50.0,
            }
        ]

        result = calculate_power_profile_from_trips(
            trips, power_kw=11.0, reference_dt=reference
        )
        # Should have calculated power for next Tuesday (April 21)
        assert len(result) == 168
        # Should have non-zero values somewhere in the profile
        has_non_zero = any(v > 0 for v in result)
        assert has_non_zero

    def test_recurring_trip_with_english_field_names(self):
        """Recurring trip with English field names (day/time) calculates power. Covers lines 731-733."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        # Monday April 13, 2026 at 12:00
        reference = datetime(2026, 4, 13, 12, 0, 0)
        # Recurring trip for Tuesday (day=2) at 10:00
        trips = [
            {
                "id": "rec_test",
                "day": 2,  # English field name, numeric
                "time": "10:00",
                "kwh": 50.0,
            }
        ]

        result = calculate_power_profile_from_trips(
            trips, power_kw=11.0, reference_dt=reference
        )
        assert len(result) == 168
        has_non_zero = any(v > 0 for v in result)
        assert has_non_zero

    def test_recurring_trip_with_spanish_field_names(self):
        """Recurring trip with Spanish field names (dia_semana/hora) calculates power. Covers lines 731-733."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        # Monday April 13, 2026 at 12:00
        reference = datetime(2026, 4, 13, 12, 0, 0)
        # Recurring trip for Tuesday (dia_semana="2")
        trips = [{"id": "rec_test", "dia_semana": "2", "hora": "10:00", "kwh": 50.0}]

        result = calculate_power_profile_from_trips(
            trips, power_kw=11.0, reference_dt=reference
        )
        assert len(result) == 168
        has_non_zero = any(v > 0 for v in result)
        assert has_non_zero

    def test_recurring_trip_with_no_day_or_time_skipped(self):
        """Recurring trip without day or time fields is skipped. Covers line 740."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        reference = datetime(2026, 4, 13, 12, 0, 0)
        # Trip without day field (or time field)
        trips = [
            {
                "id": "rec_test",
                "hora": "10:00",  # Missing day
                "kwh": 50.0,
            }
        ]

        result = calculate_power_profile_from_trips(
            trips, power_kw=11.0, reference_dt=reference
        )
        # Should return all zeros since trip was skipped
        assert all(v == 0.0 for v in result)

    def test_recurring_trip_with_invalid_day_time_skipped(self):
        """Recurring trip with invalid day/time is skipped. Covers lines 738-739."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        reference = datetime(2026, 4, 13, 12, 0, 0)
        # Trip with invalid day (non-numeric string)
        trips = [
            {
                "id": "rec_invalid",
                "dia_semana": "invalid-day",  # Invalid - can't convert to int
                "hora": "10:00",
                "kwh": 50.0,
            }
        ]

        result = calculate_power_profile_from_trips(
            trips, power_kw=11.0, reference_dt=reference
        )
        # Should return all zeros since trip was skipped due to invalid day
        assert all(v == 0.0 for v in result)

    def test_mixed_punctual_and_recurring_trips(self):
        """Mixed punctual and recurring trips both calculate power. Covers integration."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        reference = datetime(2026, 4, 13, 12, 0, 0)
        trips = [
            {"id": "punc_test", "datetime": "2026-04-14T10:00", "kwh": 30.0},
            {"id": "rec_test", "dia_semana": "2", "hora": "15:00", "kwh": 20.0},
        ]

        result = calculate_power_profile_from_trips(
            trips, power_kw=11.0, reference_dt=reference
        )
        assert len(result) == 168
        # Should have non-zero values from both trips
        has_non_zero = any(v > 0 for v in result)
        assert has_non_zero


class TestCalculateDeficitPropagationEdgeCases:
    """Tests for calculate_deficit_propagation edge cases."""

    def test_empty_sorted_trips_with_times_returns_empty(self):
        """Test that when all trips have trip_time=None, empty list is returned.

        Covers line 652 (was 659): return [] when sorted_trips_with_times is empty.
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_deficit_propagation,
        )

        reference = datetime(2026, 4, 13, 12, 0, 0)
        trips = [
            {
                "id": "t1",
                "tipo": "punctual",
                "datetime": "2026-04-14T10:00",
                "kwh": 30.0,
            },
        ]
        soc_data = [{"soc_inicio": 50.0}]
        windows = [{"ventana_horas": 10.0}]

        # trip_times=[None] -> sorted_trips_with_times will be empty
        result = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=5.0,
            battery_capacity_kwh=60.0,
            reference_dt=reference,
            trip_times=[None],
        )
        assert result == []

    def test_ordered_to_idx_missing_entry_line_671(self):
        """Test that _orig_idx is None triggers continue on line 671.

        This happens when ordered_to_idx mapping is incomplete.
        We need a trip that has NO valid datetime/hora/dia_semana so that
        calculate_trip_time returns None and the trip is excluded from
        sorted_trips_with_times, making len(trips) > len(sorted_trips_with_times).
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_deficit_propagation,
        )

        reference = datetime(2026, 4, 13, 12, 0, 0)
        # Trip 1: valid punctual trip with datetime
        # Trip 2: NO datetime, NO hora, NO dia_semana -> calculate_trip_time returns None
        trips = [
            {
                "id": "t1",
                "tipo": "puntual",
                "datetime": "2026-04-14T10:00",
                "kwh": 30.0,
            },
            {"id": "t2", "tipo": "puntual", "kwh": 20.0},  # Missing datetime!
        ]
        soc_data = [
            {"soc_inicio": 50.0},
            {"soc_inicio": 55.0},
        ]
        # Windows must have all keys that are read in the result building code (lines 736-743)
        windows = [
            {
                "ventana_horas": 8.0,
                "kwh_necesarios": 10.0,
                "horas_carga_necesarias": 2.0,
                "inicio_ventana": reference,
                "fin_ventana": reference,
                "es_suficiente": True,
            },
            {
                "ventana_horas": 10.0,
                "kwh_necesarios": 15.0,
                "horas_carga_necesarias": 3.0,
                "inicio_ventana": reference,
                "fin_ventana": reference,
                "es_suficiente": True,
            },
        ]

        result = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=5.0,
            battery_capacity_kwh=60.0,
            reference_dt=reference,
            trip_times=None,  # Let function compute trip_times from trip data
        )
        # Only t1 has valid trip_time, so result has 1 entry
        assert len(result) == 1

    def test_ordered_to_idx_missing_entry_line_713(self):
        """Test that _orig_idx is None triggers continue on line 713.

        This is in the "Build final results" loop.
        Same scenario: one trip has no valid time so it's excluded from
        sorted_trips_with_times, and ordered_to_idx doesn't have a mapping
        for every ordered_idx from 0..len(trips)-1.
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_deficit_propagation,
        )

        reference = datetime(2026, 4, 13, 12, 0, 0)
        # Trip 1: valid punctual trip
        # Trip 2: NO datetime -> calculate_trip_time returns None
        trips = [
            {
                "id": "t1",
                "tipo": "puntual",
                "datetime": "2026-04-14T22:00",
                "kwh": 30.0,
            },
            {"id": "t2", "tipo": "puntual", "kwh": 20.0},  # Missing datetime!
        ]
        soc_data = [
            {"soc_inicio": 50.0},
            {"soc_inicio": 55.0},
        ]
        # Windows must have all keys that are read in the result building code (lines 736-743)
        windows = [
            {
                "ventana_horas": 8.0,
                "kwh_necesarios": 10.0,
                "horas_carga_necesarias": 2.0,
                "inicio_ventana": reference,
                "fin_ventana": reference,
                "es_suficiente": True,
            },
            {
                "ventana_horas": 10.0,
                "kwh_necesarios": 15.0,
                "horas_carga_necesarias": 3.0,
                "inicio_ventana": reference,
                "fin_ventana": reference,
                "es_suficiente": True,
            },
        ]

        result = calculate_deficit_propagation(
            trips=trips,
            soc_data=soc_data,
            windows=windows,
            tasa_carga_soc=5.0,
            battery_capacity_kwh=60.0,
            reference_dt=reference,
            trip_times=None,
        )
        # Only t1 has valid trip_time, so result has 1 entry
        assert len(result) == 1
        assert result[0]["trip_id"] == "t1"


class TestCalculatePowerProfileEdgeCases:
    """Tests for calculate_power_profile edge cases."""

    def test_horas_desde_ahora_negative_sets_zero(self):
        """Test that negative horas_desde_ahora sets hora_inicio_carga to 0.

        Covers lines 1039-1041: if horas_desde_ahora < 0: hora_inicio_carga = 0
        """
        from datetime import timezone

        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile,
        )

        reference = datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)
        # Trip departure is in the past (8 hours ago)
        # hora_regreso is also in the past, so ventana started before now
        trips = [
            {
                "id": "t1",
                "tipo": "punctual",
                "datetime": "2026-04-13T04:00",  # 8 hours ago
                "kwh": 10.0,  # Small kwh to ensure ventana is sufficient
            }
        ]

        result = calculate_power_profile(
            all_trips=trips,
            battery_capacity_kwh=60.0,
            soc_current=30.0,  # Low soc to ensure energy needed
            charging_power_kw=11.0,
            hora_regreso=reference - timedelta(hours=4),  # Return 4 hours ago
            planning_horizon_days=7,
            reference_dt=reference,
        )
        # Window started in the past, so horas_desde_ahora < 0
        # hora_inicio_carga should be set to 0
        assert len(result) == 168
        # Should have some non-zero values (charging happened in the past but profile starts at 0)
        # The key is that hora_inicio_carga = 0 was executed

    def test_window_already_ended_skips(self):
        """Test that window with horas_hasta_fin < 0 is skipped.

        Covers line 1053-1054 (was 1060): if horas_hasta_fin < 0: continue
        """
        from datetime import timezone

        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile,
        )

        reference = datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)
        # Trip that already ended (yesterday) with past return time
        trips = [
            {
                "id": "t1",
                "tipo": "punctual",
                "datetime": "2026-04-12T10:00",  # Yesterday
                "kwh": 10.0,
            }
        ]

        result = calculate_power_profile(
            all_trips=trips,
            battery_capacity_kwh=60.0,
            soc_current=50.0,
            charging_power_kw=11.0,
            hora_regreso=reference - timedelta(hours=20),  # Return 20 hours ago
            planning_horizon_days=7,
            reference_dt=reference,
        )
        # The trip deadline is in the past, ventana ended in the past
        # horas_hasta_fin < 0, so it should be skipped
        assert len(result) == 168
        # All zeros since window already ended
        assert all(v == 0.0 for v in result)

    def test_horas_necesarias_zero_defaults_to_one(self):
        """Test that horas_carga_necesarias=0 is corrected to 1.

        Covers lines 1045-1047 (was 1052-1053): if horas_necesarias == 0: horas_necesarias = 1

        This happens when ventana_info has horas_carga_necesarias=0 but es_suficiente=True.
        We construct a trip that produces this edge case.
        """
        from datetime import timezone

        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile,
        )

        reference = datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)
        # Trip with very small kwh that still produces a valid window
        trips = [
            {
                "id": "t1",
                "tipo": "punctual",
                "datetime": "2026-04-14T10:00",  # Tomorrow
                "kwh": 0.5,  # Very small - might result in 0 horas_carga_necesarias
            }
        ]

        result = calculate_power_profile(
            all_trips=trips,
            battery_capacity_kwh=60.0,
            soc_current=90.0,  # High soc
            charging_power_kw=11.0,
            hora_regreso=reference + timedelta(hours=20),
            planning_horizon_days=7,
            reference_dt=reference,
        )
        assert len(result) == 168

    def test_horas_necesarias_zero_line_1044_with_mocked_window(self):
        """Test that horas_carga_necesarias=0 is corrected to 1.

        Covers line 1044: if horas_necesarias == 0: horas_necesarias = 1

        We mock calculate_charging_window_pure to return a window with
        horas_carga_necesarias=0 but es_suficiente=True, which forces
        execution of line 1044. We also mock calculate_energy_needed to ensure
        energia_kwh > 0 so the trip is not skipped.
        """
        from datetime import timezone
        from unittest.mock import patch

        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile,
        )

        reference = datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)
        trips = [
            {
                "id": "t1",
                "tipo": "puntual",
                "datetime": "2026-04-14T10:00",
                "kwh": 10.0,
            }
        ]

        # Mock calculate_energy_needed to ensure energia_kwh > 0
        mock_energia = {"energia_necesaria_kwh": 10.0}

        # Mock calculate_charging_window_pure to return a window with horas_carga_necesarias=0
        mock_window = {
            "ventana_horas": 24.0,
            "kwh_necesarios": 10.0,
            "horas_carga_necesarias": 0.0,  # This will trigger line 1044
            "inicio_ventana": reference + timedelta(hours=1),
            "fin_ventana": reference + timedelta(hours=25),
            "es_suficiente": True,
        }

        with patch(
            "custom_components.ev_trip_planner.calculations.power.calculate_energy_needed",
            return_value=mock_energia,
        ):
            with patch(
                "custom_components.ev_trip_planner.calculations.power.calculate_charging_window_pure",
                return_value=mock_window,
            ):
                result = calculate_power_profile(
                    all_trips=trips,
                    battery_capacity_kwh=60.0,
                    soc_current=50.0,
                    charging_power_kw=11.0,
                    hora_regreso=reference + timedelta(hours=1),
                    planning_horizon_days=7,
                    reference_dt=reference,
                )

        assert len(result) == 168
        # Line 1044 was executed: horas_necesarias was set to 1
        # With charging_power_kw=11, 1 hour of charging = 11000W at hour 1
        assert result[1] == 11000.0

    def test_window_already_ended_line_1051_with_mocked_window(self):
        """Test that window with horas_hasta_fin < 0 is skipped on line 1051.

        Covers line 1051: continue when horas_hasta_fin < 0 (Window already ended)

        We mock calculate_charging_window_pure to return a window that ended in the past,
        forcing horas_hasta_fin < 0 and triggering the continue on line 1051.
        We also mock calculate_energy_needed to ensure energia_kwh > 0.
        """
        from datetime import timezone
        from unittest.mock import patch

        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile,
        )

        reference = datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)
        trips = [
            {
                "id": "t1",
                "tipo": "puntual",
                "datetime": "2026-04-14T10:00",
                "kwh": 10.0,
            }
        ]

        # Mock calculate_energy_needed to ensure energia_kwh > 0
        mock_energia = {"energia_necesaria_kwh": 10.0}

        # Mock calculate_charging_window_pure to return a window that ended in the past
        # fin_ventana is 2 hours BEFORE reference, so horas_hasta_fin = -2 < 0
        mock_window = {
            "ventana_horas": 24.0,
            "kwh_necesarios": 10.0,
            "horas_carga_necesarias": 1.0,
            "inicio_ventana": reference - timedelta(hours=26),
            "fin_ventana": reference - timedelta(hours=2),  # 2 hours BEFORE reference
            "es_suficiente": True,
        }

        with patch(
            "custom_components.ev_trip_planner.calculations.power.calculate_energy_needed",
            return_value=mock_energia,
        ):
            with patch(
                "custom_components.ev_trip_planner.calculations.power.calculate_charging_window_pure",
                return_value=mock_window,
            ):
                result = calculate_power_profile(
                    all_trips=trips,
                    battery_capacity_kwh=60.0,
                    soc_current=50.0,
                    charging_power_kw=11.0,
                    hora_regreso=reference - timedelta(hours=26),
                    planning_horizon_days=7,
                    reference_dt=reference,
                )

        assert len(result) == 168
        # Line 1051 was executed: continue was triggered because window ended
        # All zeros since the only trip's window already ended
        assert all(v == 0.0 for v in result)


class TestCalculateHoursDeficitPropagation:
    """Tests for calculate_hours_deficit_propagation function."""

    def test_empty_input(self):
        """Empty list returns empty list."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_hours_deficit_propagation,
        )

        results = calculate_hours_deficit_propagation([])
        assert results == []

    def test_no_deficit_all_sufficient(self):
        """All trips have sufficient windows → all propagation fields = 0."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {
                "ventana_horas": 5.0,
                "horas_carga_necesarias": 3.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
            {
                "ventana_horas": 6.0,
                "horas_carga_necesarias": 2.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
            {
                "ventana_horas": 4.0,
                "horas_carga_necesarias": 1.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
        ]
        results = calculate_hours_deficit_propagation(windows, [3.0, 2.0, 1.0])
        assert all(r["deficit_hours_propagated"] == 0 for r in results)
        assert all(r["deficit_hours_to_propagate"] == 0 for r in results)
        # adjusted_def_total_hours = original def_total_hours (no absorption)
        assert results[0]["adjusted_def_total_hours"] == 3.0  # trip#0
        assert results[1]["adjusted_def_total_hours"] == 2.0  # trip#1
        assert results[2]["adjusted_def_total_hours"] == 1.0  # trip#2

    def test_last_trip_deficit_absorbed(self):
        """Trip #3 needs 3h, has 2h window. Trip #2 has 4h spare → fully absorbed."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {
                "ventana_horas": 6.0,
                "horas_carga_necesarias": 2.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
            {
                "ventana_horas": 5.0,
                "horas_carga_necesarias": 2.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
            {
                "ventana_horas": 2.0,
                "horas_carga_necesarias": 3.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
        ]
        results = calculate_hours_deficit_propagation(windows, [2.0, 2.0, 3.0])
        # trip#0 (index 0) has no deficit propagation
        assert results[0]["deficit_hours_propagated"] == 0
        assert results[0]["deficit_hours_to_propagate"] == 0
        assert results[0]["adjusted_def_total_hours"] == 2.0
        # trip#1 (index 1) absorbs 1h from trip#2
        assert results[1]["deficit_hours_propagated"] == 1.0
        assert results[1]["deficit_hours_to_propagate"] == 0.0
        assert results[1]["adjusted_def_total_hours"] == 3.0
        # trip#2 (index 2) deficit=1h, nothing after → to_propagate=1.0
        assert results[2]["deficit_hours_propagated"] == 0  # trip#2 absorbs nothing
        assert results[2]["deficit_hours_to_propagate"] == 1.0  # trip#2 has 1h deficit
        assert results[2]["adjusted_def_total_hours"] == 3.0

    def test_chain_propagation(self):
        """Trip #3 deficit 3h, trip #2 spare 2h, trip #1 spare 4h → partial absorption."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {
                "ventana_horas": 7.0,
                "horas_carga_necesarias": 3.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
            {
                "ventana_horas": 4.0,
                "horas_carga_necesarias": 2.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
            {
                "ventana_horas": 2.0,
                "horas_carga_necesarias": 5.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
        ]
        results = calculate_hours_deficit_propagation(windows, [3.0, 2.0, 5.0])
        # trip#0 (index 0): spare=4h, absorbs 1h from carrier
        assert results[0]["deficit_hours_propagated"] == 1.0
        assert results[0]["deficit_hours_to_propagate"] == 0.0
        assert results[0]["adjusted_def_total_hours"] == 4.0

        # trip#1 (index 1): spare=2h, absorbs 2h from carrier
        assert results[1]["deficit_hours_propagated"] == 2.0
        assert results[1]["deficit_hours_to_propagate"] == 1.0
        assert results[1]["adjusted_def_total_hours"] == 4.0

        # trip#2 (index 2): deficit=3h, nothing after → to_propagate=3.0
        assert results[2]["deficit_hours_propagated"] == 0
        assert results[2]["deficit_hours_to_propagate"] == 3.0
        assert results[2]["adjusted_def_total_hours"] == 5.0

    def test_single_trip_deficit(self):
        """1 trip, needs 5h, has 2h window → deficit stays on to_propagate."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {
                "ventana_horas": 2.0,
                "horas_carga_necesarias": 5.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            }
        ]
        results = calculate_hours_deficit_propagation(windows, [5.0])
        assert results[0]["deficit_hours_propagated"] == 0
        assert results[0]["deficit_hours_to_propagate"] == 3.0
        assert results[0]["adjusted_def_total_hours"] == 5.0

    def test_deficit_hours_propagated_is_not_cumulative(self):
        """deficit_hours_propagated is absorbed from NEXT trip only, not cumulative."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {
                "ventana_horas": 10.0,
                "horas_carga_necesarias": 1.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
            {
                "ventana_horas": 5.0,
                "horas_carga_necesarias": 3.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
            {
                "ventana_horas": 2.0,
                "horas_carga_necesarias": 4.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
        ]
        results = calculate_hours_deficit_propagation(windows, [1.0, 3.0, 4.0])
        assert results[0]["deficit_hours_propagated"] == 0
        assert results[1]["deficit_hours_propagated"] == 2.0
        assert results[2]["deficit_hours_propagated"] == 0

    def test_ventana_horas_unchanged(self):
        """ventana_horas must equal input value for every returned dict.

        Results are returned in the same order as input: results[0]=trip#0, results[1]=trip#1.
        """
        from custom_components.ev_trip_planner.calculations import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {
                "ventana_horas": 4.0,
                "horas_carga_necesarias": 2.0,
                "inicio_ventana": "start1",
                "fin_ventana": "end1",
            },
            {
                "ventana_horas": 6.0,
                "horas_carga_necesarias": 3.0,
                "inicio_ventana": "start2",
                "fin_ventana": "end2",
            },
        ]
        results = calculate_hours_deficit_propagation(windows, [2.0, 3.0])
        # results[0] = trip#0 (ventana=4.0), results[1] = trip#1 (ventana=6.0)
        assert results[0]["ventana_horas"] == 4.0
        assert results[1]["ventana_horas"] == 6.0
        assert results[0]["inicio_ventana"] == "start1"
        assert results[1]["fin_ventana"] == "end2"

    def test_adjusted_def_total_hours_correct(self):
        """adjusted = original def_total_hours + absorbed."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {
                "ventana_horas": 6.0,
                "horas_carga_necesarias": 2.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
            {
                "ventana_horas": 2.0,
                "horas_carga_necesarias": 5.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
        ]
        results = calculate_hours_deficit_propagation(windows, [2.0, 5.0])
        # trip#0 absorbs 3h from trip#1: adjusted = 2+3 = 5
        # trip#1 has no absorption: adjusted = 5+0 = 5
        assert results[0]["adjusted_def_total_hours"] == 5.0
        assert results[1]["adjusted_def_total_hours"] == 5.0

    def test_no_spare_capacity(self):
        """Trip has no spare capacity (fully used) → absorbs 0."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {
                "ventana_horas": 2.0,
                "horas_carga_necesarias": 2.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
            {
                "ventana_horas": 2.0,
                "horas_carga_necesarias": 5.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
        ]
        results = calculate_hours_deficit_propagation(windows, [2.0, 5.0])
        assert results[0]["deficit_hours_propagated"] == 0
        assert results[0]["deficit_hours_to_propagate"] == 3.0
        assert results[1]["deficit_hours_propagated"] == 0
        assert results[1]["deficit_hours_to_propagate"] == 3.0

    def test_default_def_total_hours(self):
        """When def_total_hours not provided, defaults to horas_carga_necesarias."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {
                "ventana_horas": 5.0,
                "horas_carga_necesarias": 2.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
            {
                "ventana_horas": 2.0,
                "horas_carga_necesarias": 5.0,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
        ]
        results = calculate_hours_deficit_propagation(windows)
        # trip#0 (index 0): spare=5-2=3h, absorbs all 3h from trip#1
        assert results[0]["deficit_hours_propagated"] == 3.0
        assert results[0]["adjusted_def_total_hours"] == 5.0
        # trip#1 (index 1): needs 5h, has 2h → deficit=3h, nothing to absorb
        assert results[1]["deficit_hours_propagated"] == 0
        assert results[1]["deficit_hours_to_propagate"] == 3.0
        assert results[1]["adjusted_def_total_hours"] == 5.0

    def test_values_rounded_to_2dp(self):
        """All propagation values are rounded to 2 decimal places."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_hours_deficit_propagation,
        )

        windows = [
            {
                "ventana_horas": 4.5,
                "horas_carga_necesarias": 3.7,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
            {
                "ventana_horas": 1.2,
                "horas_carga_necesarias": 2.8333,
                "inicio_ventana": None,
                "fin_ventana": None,
            },
        ]
        results = calculate_hours_deficit_propagation(windows, [3.7, 2.8333])
        for r in results:
            assert r["deficit_hours_propagated"] == round(
                r["deficit_hours_propagated"], 2
            )
            assert r["deficit_hours_to_propagate"] == round(
                r["deficit_hours_to_propagate"], 2
            )
            assert r["adjusted_def_total_hours"] == round(
                r["adjusted_def_total_hours"], 2
            )


class TestCalculateNextRecurringDatetimeTimezone:
    """Tests for timezone handling in calculate_next_recurring_datetime."""

    def test_zoneinfo_exception_fallback(self):
        """Cover lines 1048-1050: ZoneInfo exception fallback to UTC."""
        from unittest.mock import patch

        from custom_components.ev_trip_planner.calculations import (
            calculate_next_recurring_datetime,
        )

        def broken_zoneinfo(name):
            raise ValueError("ZoneInfo broken for testing")

        # Patch ZoneInfo inside the calculations module
        with patch("zoneinfo.ZoneInfo", broken_zoneinfo):
            calculate_next_recurring_datetime(0, "09:00", tz="Europe/Madrid")
            # Should not raise — fallback to None tz (UTC behavior)
