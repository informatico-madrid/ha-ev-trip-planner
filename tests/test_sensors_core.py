"""Pruebas TDD de sensores (Fase 1C)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    return hass


def _sample_trips():
    return [
        {"id": "rec_lun_1", "tipo": "recurrente", "dia_semana": "lunes"},
        {"id": "rec_mar_2", "tipo": "recurrente", "dia_semana": "martes"},
        {"id": "pun_20251119_3", "tipo": "puntual", "datetime": "2025-11-19T15:00:00"},
    ]


class FakeCoordinator:
    def __init__(self, trips_list):
        # El coordinator real devuelve un dict con claves recurring_trips y punctual_trips
        self.data = {
            "recurring_trips": [t for t in trips_list if t.get("tipo") == "recurrente"],
            "punctual_trips": [t for t in trips_list if t.get("tipo") == "puntual"],
        }


@pytest.mark.asyncio
async def test_recurring_and_punctual_counts(mock_hass):
    from custom_components.ev_trip_planner.sensor import (
        RecurringTripsCountSensor,
        PunctualTripsCountSensor,
    )

    coord = FakeCoordinator(_sample_trips())
    rec = RecurringTripsCountSensor(vehicle_id="chispitas", coordinator=coord)  # type: ignore[arg-type]
    pun = PunctualTripsCountSensor(vehicle_id="chispitas", coordinator=coord)  # type: ignore[arg-type]

    assert rec.native_value == 2
    assert pun.native_value == 1


@pytest.mark.asyncio
async def test_trips_list_sensor_attributes(mock_hass):
    from custom_components.ev_trip_planner.sensor import TripsListSensor

    coord = FakeCoordinator(_sample_trips())
    s = TripsListSensor(vehicle_id="chispitas", coordinator=coord)  # type: ignore[arg-type]

    # Valor nativo: total
    assert s.native_value == 3
    # Atributos: listas separadas
    attrs = s.extra_state_attributes
    assert isinstance(attrs, dict)
    assert isinstance(attrs.get("recurring_trips"), list)
    assert isinstance(attrs.get("punctual_trips"), list)
    assert len(attrs["recurring_trips"]) == 2
    assert len(attrs["punctual_trips"]) == 1
    assert any(t["tipo"] == "recurrente" for t in attrs["recurring_trips"])  # sanity
