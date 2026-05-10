"""Test that ventana_horas satisfies the time invariant: (fin_ventana - inicio_ventana) / 3600.

BUG-001: The current code calculates ventana_horas using trip_arrival
(departure + duration) instead of trip_departure (fin_ventana). This makes
ventana_horas systematically larger than the actual available window.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.ev_trip_planner.calculations import (
    calculate_multi_trip_charging_windows,
)


def _make_trip(dt: datetime, km: float = 50.0, kwh: float = 10.0) -> dict:
    """Return a minimal trip dict compatible with calculate_energy_needed."""
    return {
        "km": km,
        "kwh": kwh,
        "descripcion": "test",
    }


class TestVentanaHorasInvariant:
    """Verify that ventana_horas == (fin_ventana - inicio_ventana) / 3600."""

    def test_single_trip_invariant(self):
        """A single trip must have ventana_horas equal to fin_ventana - inicio_ventana."""
        now = datetime(2026, 5, 10, 18, 0, 0, tzinfo=timezone.utc)
        trip_departure = datetime(2026, 5, 10, 22, 0, 0, tzinfo=timezone.utc)

        trips = [
            (trip_departure, _make_trip(trip_departure)),
        ]

        results = calculate_multi_trip_charging_windows(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=7.4,
            battery_capacity_kwh=75.0,
            duration_hours=4.0,
            return_buffer_hours=1.0,
            now=now,
        )

        assert len(results) == 1
        w = results[0]

        inicio = w["inicio_ventana"]
        fin = w["fin_ventana"]

        expected_horas = (fin - inicio).total_seconds() / 3600

        assert w["ventana_horas"] == pytest.approx(expected_horas, rel=1e-2), (
            f"ventana_horas={w['ventana_horas']} but "
            f"(fin_ventana - inicio_ventana)/3600 = {expected_horas}"
        )

    def test_multi_trip_second_window_invariant(self):
        """Trip 2 ventana_horas must equal its own fin_ventana - inicio_ventana."""
        now = datetime(2026, 5, 10, 8, 0, 0, tzinfo=timezone.utc)
        trip1_departure = datetime(2026, 5, 10, 14, 0, 0, tzinfo=timezone.utc)
        trip2_departure = datetime(2026, 5, 10, 20, 0, 0, tzinfo=timezone.utc)

        trips = [
            (trip1_departure, _make_trip(trip1_departure)),
            (trip2_departure, _make_trip(trip2_departure)),
        ]

        results = calculate_multi_trip_charging_windows(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=7.4,
            battery_capacity_kwh=75.0,
            duration_hours=4.0,
            return_buffer_hours=1.0,
            now=now,
        )

        assert len(results) == 2

        for idx, w in enumerate(results):
            inicio = w["inicio_ventana"]
            fin = w["fin_ventana"]

            expected_horas = (fin - inicio).total_seconds() / 3600

            assert w["ventana_horas"] == pytest.approx(
                expected_horas, rel=1e-2
            ), (
                f"Trip {idx + 1}: ventana_horas={w['ventana_horas']} but "
                f"(fin_ventana - inicio_ventana)/3600 = {expected_horas}"
            )

    def test_multi_trip_with_hora_regreso_invariant(self):
        """With hora_regreso, both windows must satisfy the invariant."""
        now = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
        hora_regreso = datetime(2026, 5, 10, 10, 0, 0, tzinfo=timezone.utc)
        trip1_departure = datetime(2026, 5, 10, 14, 0, 0, tzinfo=timezone.utc)
        trip2_departure = datetime(2026, 5, 10, 20, 0, 0, tzinfo=timezone.utc)

        trips = [
            (trip1_departure, _make_trip(trip1_departure)),
            (trip2_departure, _make_trip(trip2_departure)),
        ]

        results = calculate_multi_trip_charging_windows(
            trips=trips,
            soc_actual=50.0,
            hora_regreso=hora_regreso,
            charging_power_kw=7.4,
            battery_capacity_kwh=75.0,
            duration_hours=4.0,
            return_buffer_hours=1.0,
            now=now,
        )

        assert len(results) == 2

        for idx, w in enumerate(results):
            inicio = w["inicio_ventana"]
            fin = w["fin_ventana"]

            expected_horas = (fin - inicio).total_seconds() / 3600

            assert w["ventana_horas"] == pytest.approx(
                expected_horas, rel=1e-2
            ), (
                f"Trip {idx + 1}: ventana_horas={w['ventana_horas']} but "
                f"(fin_ventana - inicio_ventana)/3600 = {expected_horas}"
            )
