"""Unit test fixtures — mocks that don't need HA framework."""

from __future__ import annotations

from custom_components.ev_trip_planner.trip_manager import TripManager

import pytest


@pytest.fixture
def trip_manager_no_entry_id(mock_hass):
    """Return a TripManager instance WITHOUT entry_id for pure function tests.

    This fixture provides a TripManager without entry_id for tests that don't
    depend on coordinator refresh or config entry lookup.

    Usage:
        async def test_calculation(trip_manager_no_entry_id):
            tm = trip_manager_no_entry_id
            result = await tm.async_get_kwh_needed_today()
    """
    return TripManager(mock_hass, "test_vehicle")
