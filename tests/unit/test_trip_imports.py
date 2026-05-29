"""Verify that the trip package re-exports TripManager."""

from custom_components.ev_trip_planner.trip.manager import TripManager


def test_trip_manager_import():
    assert TripManager is not None
