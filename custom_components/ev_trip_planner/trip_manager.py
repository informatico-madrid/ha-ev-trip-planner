"""Backward-compat shim: re-export TripManager from new trip package."""

from custom_components.ev_trip_planner.trip import TripManager

__all__ = ["TripManager"]
