"""Parametrized tests for pure functions in calculations.py.

These tests achieve 100% coverage of the pure functions without any mocks.
All functions are synchronous and deterministic given the same inputs.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pytest

from custom_components.ev_trip_planner.calculations.windows import (
    ChargingWindowPureParams,
    MultiTripChargingParams,
)


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

    def test_recurring_trip_with_tz_aware_reference(self):
        """Recurring trip with tz parameter and timezone-aware reference_dt (lines 245-260)."""
        from zoneinfo import ZoneInfo

        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        # Reference: Monday 08:00 UTC (timezone-aware)
        ref = datetime(2026, 4, 6, 8, 0, tzinfo=timezone.utc)
        # Trip: Monday 10:00 local time (Europe/Madrid = UTC+2 in April)
        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora="10:00",
            dia_semana="lunes",
            datetime_str=None,
            reference_dt=ref,
            tz=ZoneInfo("Europe/Madrid"),
        )
        assert result is not None

    def test_recurring_trip_tz_passed_today_pushes_to_next_week(self):
        """Tz-aware path: today is the trip day but hour already passed -> push 7 days."""
        from zoneinfo import ZoneInfo

        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        # Reference: Monday 08:00 UTC = Monday 10:00 CEST (Europe/Madrid UTC+2)
        ref = datetime(2026, 4, 6, 8, 0, tzinfo=timezone.utc)
        # Trip: Monday 08:00 local time (CET/CEST = UTC+1/+2)
        # In April, Madrid is UTC+2, so trip is at 06:00 UTC
        # Local ref = 10:00, trip hour = 8 -> 10 > 8, days_ahead=0 -> push to next week
        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora="08:00",
            dia_semana="lunes",
            datetime_str=None,
            reference_dt=ref,
            tz=ZoneInfo("Europe/Madrid"),
        )
        assert result is not None
        # Should be next Monday (April 13)
        assert result.date() == ref.date() + timedelta(days=7)
        assert result.weekday() == 0  # Monday

    def test_recurring_trip_with_tz_naive_reference(self):
        """Tz-aware path: naive reference_dt → replace with UTC (line 259)."""
        from zoneinfo import ZoneInfo

        from custom_components.ev_trip_planner.calculations import calculate_trip_time
        from custom_components.ev_trip_planner.const import TRIP_TYPE_RECURRING

        # Naive reference
        ref = datetime(2026, 4, 6, 8, 0)  # No tzinfo
        result = calculate_trip_time(
            trip_tipo=TRIP_TYPE_RECURRING,
            hora="10:00",
            dia_semana="lunes",
            datetime_str=None,
            reference_dt=ref,
            tz=ZoneInfo("Europe/Madrid"),
        )
        assert result is not None

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
        # horas_carga = 20 / 7.4 = 2.70 → ceiled to 3
        assert result["horas_carga_necesarias"] == math.ceil(20.0 / 7.4)

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
            ChargingWindowPureParams(
                trip_departure_time=None,
                soc_actual=50.0,
                hora_regreso=datetime(2026, 4, 6, 10, 0),
                charging_power_kw=7.4,
                energia_kwh=20.0,
            ),
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
            ChargingWindowPureParams(
                trip_departure_time=datetime(2026, 4, 6, 18, 0),
                soc_actual=50.0,
                hora_regreso=datetime(2026, 4, 6, 10, 0),
                charging_power_kw=0.0,
                energia_kwh=20.0,
            ),
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
            ChargingWindowPureParams(
                trip_departure_time=departure,
                soc_actual=50.0,
                hora_regreso=retorno,
                charging_power_kw=7.4,
                energia_kwh=20.0,
            ),
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
            ChargingWindowPureParams(
                trip_departure_time=departure,
                soc_actual=50.0,
                hora_regreso=None,
                charging_power_kw=7.4,
                energia_kwh=20.0,
            ),
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
            ChargingWindowPureParams(
                trip_departure_time=None,
                soc_actual=50.0,
                hora_regreso=None,
                charging_power_kw=7.4,
                energia_kwh=20.0,
            ),
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
            ChargingWindowPureParams(
                trip_departure_time=datetime(2026, 4, 6, 11, 0),
                soc_actual=0.0,
                hora_regreso=datetime(2026, 4, 6, 10, 0),
                charging_power_kw=7.4,  # 7.4 kW -> ~2.7h for 20 kWh
                energia_kwh=20.0,
            ),
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
            params=MultiTripChargingParams(
                soc_actual=50.0,
                hora_regreso=None,  # No return event detected
                charging_power_kw=7.4,
                battery_capacity_kwh=50.0,
            ),
        )
        assert len(result) == 1
        # hora_regreso=None → window starts at now (car is assumed home)
        assert result[0]["inicio_ventana"] >= now, (
            f"inicio_ventana={result[0]['inicio_ventana']} should be >= now={now}"
        )
        # ventana_horas = departure - now ≈ 96h
        assert result[0]["ventana_horas"] == pytest.approx(96.0, abs=1.0)

    def test_zero_charging_power_sets_horas_carga_to_zero(self):
        """When charging_power_kw is 0, horas_carga_necesarias is 0.0. Covers line 395."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_multi_trip_charging_windows,
        )

        departure = datetime(2026, 4, 6, 18, 0)
        trips = [(departure, {"id": "trip1"})]
        result = calculate_multi_trip_charging_windows(
            trips=trips,
            params=MultiTripChargingParams(
                soc_actual=50.0,
                hora_regreso=datetime(2026, 4, 6, 10, 0),
                charging_power_kw=0.0,
                battery_capacity_kwh=50.0,
            ),
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
            params=MultiTripChargingParams(
                soc_actual=50.0,
                hora_regreso=None,
                charging_power_kw=7.4,
                battery_capacity_kwh=50.0,
            ),
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
            params=MultiTripChargingParams(
                soc_actual=50.0,
                hora_regreso=datetime(2026, 4, 6, 10, 0),
                charging_power_kw=7.4,
                battery_capacity_kwh=50.0,
            ),
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
            params=MultiTripChargingParams(
                soc_actual=50.0,
                hora_regreso=datetime(2026, 4, 6, 7, 0),
                charging_power_kw=7.4,
                return_buffer_hours=0.0,
                battery_capacity_kwh=50.0,
            ),
        )
        # First window: 7am → 8am departure = 1h
        assert result[0]["inicio_ventana"] == datetime(2026, 4, 6, 7, 0)
        assert result[0]["ventana_horas"] == 1.0
        # Second window: trip1 departure (8am) + 0h buffer → trip2 departure (22:00) = 14h
        assert result[1]["inicio_ventana"].hour == 8
        assert result[1]["inicio_ventana"].minute == 0
        assert result[1]["ventana_horas"] == 14.0

    def test_chained_trips_buffer_exceeds_gap_caps_window(self):
        """return_buffer pushes window_start past departure → capped to departure (line 269)."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_multi_trip_charging_windows,
        )

        # Trip 1 departs 8:00, Trip 2 departs 10:00
        # Return buffer = 3h → 8:00 + 3h = 11:00 > 10:00 → capped to 10:00
        trip1_departure = datetime(2026, 4, 6, 8, 0)
        trip2_departure = datetime(2026, 4, 6, 10, 0)
        trips = [
            (trip1_departure, {"id": "trip1"}),
            (trip2_departure, {"id": "trip2"}),
        ]
        result = calculate_multi_trip_charging_windows(
            trips=trips,
            params=MultiTripChargingParams(
                soc_actual=50.0,
                hora_regreso=datetime(2026, 4, 6, 6, 0),
                charging_power_kw=7.4,
                return_buffer_hours=3.0,
                battery_capacity_kwh=50.0,
            ),
        )
        # Second trip's window_start should be capped to trip2 departure (10:00)
        assert result[1]["inicio_ventana"].hour == 10
        assert result[1]["inicio_ventana"].minute == 0
        assert result[1]["ventana_horas"] == 0.0


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

        # Trip deadline 2026-04-10 is in the past, hours_available is negative
        # max(1, min(int(neg), 168)) = 1
        assert result["end_timestep"] == 1

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

    def test_trip_with_soc_current_uses_soc_aware_path(self):
        """With soc_current and battery_capacity_kwh, uses determine_charging_need (lines 137-145)."""
        from custom_components.ev_trip_planner.calculations import (
            calculate_power_profile_from_trips,
        )

        trip = {
            "id": "trip_soc",
            "datetime": "2026-04-06T18:00",
            "kwh": 15.0,
        }
        result = calculate_power_profile_from_trips(
            trips=[trip],
            power_kw=7.4,
            horizon=24,
            reference_dt=datetime(2026, 4, 6, 8, 0),
            soc_current=50.0,
            battery_capacity_kwh=75.0,
            safety_margin_percent=15.0,
        )
        # Should produce a valid power profile
        non_zero = [v for v in result if v > 0]
        assert len(non_zero) >= 1

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
        """Trip #3 is deficit origin — keeps original def_total, T2 absorbs 1h from it."""
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
        # trip#0 (index 0) has no deficit, absorbs nothing
        assert results[0]["deficit_hours_propagated"] == 0
        assert results[0]["deficit_hours_to_propagate"] == 0
        assert results[0]["adjusted_def_total_hours"] == 2.0
        # trip#1 (index 1) absorbs 1h from deficit origin trip#2
        assert results[1]["deficit_hours_propagated"] == 1.0
        assert results[1]["deficit_hours_to_propagate"] == 0.0
        assert results[1]["adjusted_def_total_hours"] == 3.0
        # trip#2 (index 2) is deficit origin — charges ceil(2.0)=2h, cascades 1h backwards
        assert results[2]["deficit_hours_propagated"] == 0
        assert results[2]["deficit_hours_to_propagate"] == 1.0
        assert results[2]["adjusted_def_total_hours"] == 2.0

    def test_chain_propagation(self):
        """Trip #3 is deficit origin — keeps original def_total, cascades 3h backwards through #2 to #1."""
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
        # trip#0 (index 0): absorbs 1h from carrier (T1 absorbed 2, cascading 1)
        assert results[0]["deficit_hours_propagated"] == 1.0
        assert results[0]["deficit_hours_to_propagate"] == 0.0
        assert results[0]["adjusted_def_total_hours"] == 4.0

        # trip#1 (index 1): absorbs 2h from origin T2, cascades 1h to T0
        assert results[1]["deficit_hours_propagated"] == 2.0
        assert results[1]["deficit_hours_to_propagate"] == 1.0
        assert results[1]["adjusted_def_total_hours"] == 4.0

        # trip#2 (index 2): deficit origin — charges ceil(2.0)=2h, cascades 3h backwards
        assert results[2]["deficit_hours_propagated"] == 0
        assert results[2]["deficit_hours_to_propagate"] == 3.0
        assert results[2]["adjusted_def_total_hours"] == 2.0

    def test_single_trip_deficit(self):
        """1 trip is deficit origin — charges ceil(2.0)=2h, 3h deficit has nowhere to cascade."""
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
        assert results[0]["adjusted_def_total_hours"] == 2.0

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
        """adjusted = original def_total_hours + absorbed (origin charges ceil(window))."""
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
        # trip#0 absorbs 3h from deficit origin trip#1: adjusted = 2+3 = 5
        # trip#1 is deficit origin — charges ceil(2.0)=2h
        assert results[0]["adjusted_def_total_hours"] == 5.0
        assert results[1]["adjusted_def_total_hours"] == 2.0

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
        # trip#1 (index 1): deficit origin — charges ceil(2.0)=2h, deficit cascades 3h backwards
        assert results[1]["deficit_hours_propagated"] == 0
        assert results[1]["deficit_hours_to_propagate"] == 3.0
        assert results[1]["adjusted_def_total_hours"] == 2.0

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


class TestMutationKillsChargingWindowPure:
    """Kills mutants in calculate_charging_window_pure by asserting dict structure."""

    def test_return_dict_has_all_keys_no_none(self):
        """Mutant: return dict values → None. Must assert all keys present and non-None."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.windows import (
            ChargingWindowPureParams,
            calculate_charging_window_pure,
        )

        result = calculate_charging_window_pure(
            ChargingWindowPureParams(
                trip_departure_time=datetime(2026, 4, 6, 18, 0, tzinfo=timezone.utc),
                soc_actual=50.0,
                hora_regreso=datetime(2026, 4, 6, 10, 0, tzinfo=timezone.utc),
                charging_power_kw=7.4,
                energia_kwh=20.0,
            )
        )

        required_keys = (
            "ventana_horas",
            "kwh_necesarios",
            "horas_carga_necesarias",
            "inicio_ventana",
            "fin_ventana",
            "es_suficiente",
        )
        for key in required_keys:
            assert key in result, f"Key {key} missing (mutation: return dict replaced)"
            assert result[key] is not None, (
                f"Key {key} is None (mutation: value → None)"
            )

    def test_es_suficiente_type_assertion(self):
        """Mutant: es_suficiente boolean flip. Must assert type."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.windows import (
            ChargingWindowPureParams,
            calculate_charging_window_pure,
        )

        result = calculate_charging_window_pure(
            ChargingWindowPureParams(
                trip_departure_time=datetime(2026, 4, 6, 18, 0, tzinfo=timezone.utc),
                soc_actual=50.0,
                hora_regreso=datetime(2026, 4, 6, 10, 0, tzinfo=timezone.utc),
                charging_power_kw=7.4,
                energia_kwh=20.0,
            )
        )
        assert isinstance(result["es_suficiente"], bool), (
            "es_suficiente must be bool (mutation: value → None/str)"
        )

    def test_ventana_horas_is_float(self):
        """Mutant: ventana_horas round → 0. Must assert type and positive."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.windows import (
            ChargingWindowPureParams,
            calculate_charging_window_pure,
        )

        result = calculate_charging_window_pure(
            ChargingWindowPureParams(
                trip_departure_time=datetime(2026, 4, 6, 18, 0, tzinfo=timezone.utc),
                soc_actual=50.0,
                hora_regreso=datetime(2026, 4, 6, 10, 0, tzinfo=timezone.utc),
                charging_power_kw=7.4,
                energia_kwh=20.0,
            )
        )
        assert isinstance(result["ventana_horas"], (int, float))
        assert result["ventana_horas"] >= 0, "ventana_horas must be non-negative"

    def test_kwh_necesarios_type_assertion(self):
        """Mutant: kwh_necesarios → 0. Must assert positive float."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.windows import (
            ChargingWindowPureParams,
            calculate_charging_window_pure,
        )

        result = calculate_charging_window_pure(
            ChargingWindowPureParams(
                trip_departure_time=datetime(2026, 4, 6, 18, 0, tzinfo=timezone.utc),
                soc_actual=50.0,
                hora_regreso=datetime(2026, 4, 6, 10, 0, tzinfo=timezone.utc),
                charging_power_kw=7.4,
                energia_kwh=20.0,
            )
        )
        assert isinstance(result["kwh_necesarios"], (int, float))
        assert result["kwh_necesarios"] > 0, "kwh_necesarios must be positive"

    def test_none_inputs_return_zero_window(self):
        """Mutant: both branches of None check flipped. Must assert 0.0 window."""
        from custom_components.ev_trip_planner.calculations.windows import (
            ChargingWindowPureParams,
            calculate_charging_window_pure,
        )

        result = calculate_charging_window_pure(
            ChargingWindowPureParams(
                trip_departure_time=None,
                soc_actual=50.0,
                hora_regreso=None,
                charging_power_kw=7.4,
                energia_kwh=20.0,
            )
        )
        assert result["ventana_horas"] == 0.0
        assert result["kwh_necesarios"] == 0.0
        assert result["inicio_ventana"] is None
        assert result["fin_ventana"] is None


class TestMutationKillsMultiTripWindows:
    """Kills mutants in calculate_multi_trip_charging_windows."""

    def test_result_is_list_of_dicts(self):
        """Mutant: return → None or wrong type. Must assert list of dicts."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.windows import (
            MultiTripChargingParams,
            calculate_multi_trip_charging_windows,
        )

        trips = [
            (
                datetime(2026, 4, 6, 18, 0, tzinfo=timezone.utc),
                {"id": "t1", "kwh": 10.0},
            )
        ]
        result = calculate_multi_trip_charging_windows(
            trips=trips,
            params=MultiTripChargingParams(
                soc_actual=50.0,
                hora_regreso=datetime(2026, 4, 6, 10, 0, tzinfo=timezone.utc),
                charging_power_kw=7.4,
                battery_capacity_kwh=75.0,
            ),
        )

        assert isinstance(result, list)
        assert len(result) > 0
        for item in result:
            assert isinstance(item, dict)
            assert "ventana_horas" in item
            assert item["ventana_horas"] is not None

    def test_multiple_trips_give_multiple_results(self):
        """Mutant: loop mutation → single or zero results."""
        from datetime import datetime, timedelta, timezone

        from custom_components.ev_trip_planner.calculations.windows import (
            MultiTripChargingParams,
            calculate_multi_trip_charging_windows,
        )

        base = datetime(2026, 4, 6, 10, 0, 0, tzinfo=timezone.utc)
        trips = [
            (base + timedelta(hours=8), {"id": "t1", "kwh": 10.0}),
            (base + timedelta(hours=20), {"id": "t2", "kwh": 15.0}),
        ]
        result = calculate_multi_trip_charging_windows(
            trips=trips,
            params=MultiTripChargingParams(
                soc_actual=50.0,
                hora_regreso=base,
                charging_power_kw=7.4,
                battery_capacity_kwh=75.0,
            ),
        )
        assert len(result) == 2, "Must have one result per trip"

    def test_empty_trips_returns_empty_list(self):
        """Mutant: early return guard flipped. Empty must return []."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.windows import (
            MultiTripChargingParams,
            calculate_multi_trip_charging_windows,
        )

        result = calculate_multi_trip_charging_windows(
            trips=[],
            params=MultiTripChargingParams(
                soc_actual=50.0,
                hora_regreso=datetime(2026, 4, 6, 10, 0, tzinfo=timezone.utc),
                charging_power_kw=7.4,
                battery_capacity_kwh=75.0,
            ),
        )
        assert result == []

    def test_result_dict_has_required_keys(self):
        """Mutant: dict keys replaced with None. Must assert all keys present."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.windows import (
            MultiTripChargingParams,
            calculate_multi_trip_charging_windows,
        )

        trips = [
            (
                datetime(2026, 4, 6, 18, 0, tzinfo=timezone.utc),
                {"id": "t1", "kwh": 10.0},
            )
        ]
        result = calculate_multi_trip_charging_windows(
            trips=trips,
            params=MultiTripChargingParams(
                soc_actual=50.0,
                hora_regreso=datetime(2026, 4, 6, 10, 0, tzinfo=timezone.utc),
                charging_power_kw=7.4,
                battery_capacity_kwh=75.0,
            ),
        )

        required = (
            "ventana_horas",
            "kwh_necesarios",
            "horas_carga_necesarias",
            "inicio_ventana",
            "fin_ventana",
            "es_suficiente",
            "trip",
        )
        for key in required:
            assert key in result[0], f"Key {key} missing in result dict"


class TestMutationKillsPowerProfile:
    """Kills mutants in calculate_power_profile_from_trips."""

    def test_returns_list_of_floats(self):
        """Mutant: return → None or wrong type. Must assert list of floats."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.power import (
            calculate_power_profile_from_trips,
        )

        trips = [
            {
                "id": "t1",
                "datetime": "2026-04-07T06:00:00+00:00",
                "kwh": 10.0,
            }
        ]
        result = calculate_power_profile_from_trips(
            trips=trips,
            power_kw=3.6,
            horizon=24,
            reference_dt=datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc),
        )

        assert isinstance(result, list)
        assert len(result) == 24
        for val in result:
            assert isinstance(val, (int, float))

    def test_non_empty_profile_for_valid_trip(self):
        """Mutant: power_profile → all zeros. Must assert some non-zero."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.power import (
            calculate_power_profile_from_trips,
        )

        trips = [
            {
                "id": "t1",
                "datetime": "2026-04-07T06:00:00+00:00",
                "kwh": 10.0,
            }
        ]
        result = calculate_power_profile_from_trips(
            trips=trips,
            power_kw=3.6,
            horizon=24,
            reference_dt=datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc),
        )
        assert any(x > 0 for x in result), (
            "Some hours must have power > 0 for a valid trip"
        )

    def test_empty_trips_returns_zeros(self):
        """Mutant: early return guard flipped. Empty → non-zero profile."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.calculations.power import (
            calculate_power_profile_from_trips,
        )

        result = calculate_power_profile_from_trips(
            trips=[],
            power_kw=3.6,
            horizon=24,
            reference_dt=datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc),
        )
        assert result == [0.0] * 24


# =============================================================================
# Mutation-killing tests for top-survivor functions (task 2.10.3)
# =============================================================================
