"""Verify that the trip package re-exports TripManager, CargaVentana, SOCMilestoneResult."""

from custom_components.ev_trip_planner.trip.manager import TripManager
from custom_components.ev_trip_planner.trip._types import (
    CargaVentana,
    SOCMilestoneResult,
)


def test_trip_manager_import():
    assert TripManager is not None


def test_carga_ventana_import():
    assert CargaVentana is not None


def test_soc_milestone_result_import():
    assert SOCMilestoneResult is not None
