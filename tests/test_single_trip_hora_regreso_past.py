"""Regression test: single-trip charging window when car is already home.

Bug: For a single future trip where the car is already home, the charging
window start (inicio_ventana) may not start from now, wasting solar energy.

Root cause: When the car was always home (no off→on transition detected),
the caller passes hora_regreso=None to calculate_multi_trip_charging_windows.
The code fell to: window_start = trip_departure_time - timedelta(hours=6)
giving def_start_timestep ~67 instead of 0.

Fix: In the else branch (hora_regreso is None), default to now.
"""

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.ev_trip_planner.calculations import (
    calculate_multi_trip_charging_windows,
)


class TestSingleTripHoraRegresoPast:
    """Tests for single-trip charging window when car is already home."""

    def test_single_trip_past_hora_regreso_starts_charging_from_now(self):
        """Car returned home 2h ago (sensor detected return) -> charging from now."""
        now = datetime.now(timezone.utc)
        hora_regreso = now - timedelta(hours=2)
        trip_deadline = now + timedelta(hours=96)

        trip = {
            "id": "rec_1_7wezae",
            "kwh": 7.0,
            "datetime": trip_deadline.isoformat(),
            "descripcion": "Llevar al cole",
        }

        results = calculate_multi_trip_charging_windows(
            trips=[(trip_deadline, trip)],
            soc_actual=30.0,
            hora_regreso=hora_regreso,
            charging_power_kw=3.4,
            battery_capacity_kwh=50.0,
        )

        result = results[0]

        assert result["inicio_ventana"] >= now, \
            f"Charging window should start from now (car is home), " \
            f"not from past hora_regreso. inicio_ventana={result['inicio_ventana']}, " \
            f"now={now}, hora_regreso={hora_regreso}"

        assert result["ventana_horas"] == pytest.approx(102.0, abs=0.02), \
            f"ventana_horas={result['ventana_horas']:.2f}h should be close to 102h"

    def test_single_trip_hora_regreso_none_starts_charging_from_now(self):
        """Car was always home -> hora_regreso is None -> should start from now.

        This is the REAL bug scenario observed in production:
        - Car was already home when HA started (no off->on transition)
        - hora_regreso was never recorded -> None
        - Calculations used: departure - 6h -> timestep 67+
        - Should use: now -> timestep 0
        """
        now = datetime.now(timezone.utc)
        trip_deadline = now + timedelta(hours=96)

        trip = {
            "id": "rec_1_7wezae",
            "kwh": 7.0,
            "datetime": trip_deadline.isoformat(),
            "descripcion": "Llevar al cole",
        }

        results = calculate_multi_trip_charging_windows(
            trips=[(trip_deadline, trip)],
            soc_actual=30.0,
            hora_regreso=None,  # The bug case: no return event ever recorded
            charging_power_kw=3.4,
            battery_capacity_kwh=50.0,
        )

        result = results[0]

        # Key assertion: window should start from now, not from departure - 6h
        assert result["inicio_ventana"] >= now, \
            f"Charging window should start from now when hora_regreso is None. " \
            f"got inicio_ventana={result['inicio_ventana']} " \
            f"(now={now}, departure={trip_deadline})"

        assert result["ventana_horas"] == pytest.approx(102.0, abs=0.02), \
            f"ventana_horas={result['ventana_horas']:.2f}h should be ~102h " \
            f"(96h to departure + 6h duration, start from now)"

    def test_single_trip_hora_regreso_future_doesnt_charge_yet(self):
        """Car hasn't returned yet -> charging starts when car returns."""
        now = datetime.now(timezone.utc)
        hora_regreso = now + timedelta(hours=4)  # Car returns in 4h
        trip_deadline = now + timedelta(hours=96)

        trip = {
            "id": "rec_1_7wezae",
            "kwh": 7.0,
            "datetime": trip_deadline.isoformat(),
            "descripcion": "Llevar al cole",
        }

        results = calculate_multi_trip_charging_windows(
            trips=[(trip_deadline, trip)],
            soc_actual=30.0,
            hora_regreso=hora_regreso,
            charging_power_kw=3.4,
            battery_capacity_kwh=50.0,
        )

        result = results[0]

        assert result["inicio_ventana"] >= hora_regreso, \
            f"Window should start from hora_regreso (car not home yet). " \
            f"inicio_ventana={result['inicio_ventana']}, hora_regreso={hora_regreso}"

        assert result["ventana_horas"] == 98.0, \
            f"ventana_horas={result['ventana_horas']:.1f}h should be 98h " \
            f"((96h + 6h duration) - 4h waiting for return)"
