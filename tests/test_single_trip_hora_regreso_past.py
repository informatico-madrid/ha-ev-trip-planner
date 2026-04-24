"""Regression test: single-trip charging window when hora_regreso is in the past.

Bug: For a single future trip where the car is already home, the charging
window start (inicio_ventana) uses hora_regreso instead of now. This wastes
solar energy because charging doesn't start until the car's last return,
not from the current moment.

Scenario (real user case):
  - Friday 24 Apr: car is at home (hora_regreso ~16:00 UTC, already past)
  - Monday 27 Apr 16:54 UTC: recurring trip "Llevar al cole"
  - Energy needed: 7 kWh

Expected: charging window = [now, departure] → def_start_timestep = 0
          The car should charge from now until the trip, using all available solar.

Actual (bug): inicio_ventana = hora_regreso (past)
          This inflates ventana_horas and creates inconsistency between
          the window calculation and the EMHASS timestep schedule.

This test expects the CORRECT behavior. It FAILS with the current code,
and will PASS after the fix: inicio_ventana = max(hora_regreso, now)
"""

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.ev_trip_planner.calculations import (
    calculate_multi_trip_charging_windows,
)


class TestSingleTripHoraRegresoPast:
    """Tests for single-trip charging window when car is already home."""

    def test_single_trip_past_hora_regreso_starts_charging_from_now(self):
        """Car returned home 2h ago, trip in 96h → charging window starts NOW.

        This is the core bug. When the car is already home (hora_regreso in the past),
        inicio_ventana should be max(hora_regreso, now) = now, not hora_regreso.

        FAILS NOW (bug): inicio_ventana = hora_regreso (past) → window starts in the past
        PASSES AFTER FIX: inicio_ventana >= now
        """
        now = datetime.now(timezone.utc)
        hora_regreso = now - timedelta(hours=2)  # Car returned 2h ago
        trip_deadline = now + timedelta(hours=96)  # Trip on Monday 16:54

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

        # FIX: When car is already home, charging should start from now
        assert result["inicio_ventana"] >= now, \
            f"Charging window should start from now (car is home), " \
            f"not from past hora_regreso. inicio_ventana={result['inicio_ventana']}, " \
            f"now={now}, hora_regreso={hora_regreso}"

        # ventana_horas = (departure + duration) - now = 96 + 6 = 102h
        # The key fix is inicio_ventana = now, not hora_regreso (past)
        # Before fix: ventana_horas = 104h (102 + 2h past hora_regreso)
        assert result["ventana_horas"] == 102.0, \
            f"ventana_horas={result['ventana_horas']:.1f}h should be 102h " \
            f"((96h to departure + 6h duration) - 0h since now=start)"
