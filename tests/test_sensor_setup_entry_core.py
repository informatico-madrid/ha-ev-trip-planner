"""TDD: setup de sensores vía async_setup_entry."""

from __future__ import annotations

from typing import List
from unittest.mock import AsyncMock, MagicMock

import pytest


class FakeEntry:
    def __init__(self, entry_id: str, data: dict) -> None:
        self.entry_id = entry_id
        self.data = data


@pytest.mark.asyncio
async def test_async_setup_entry_creates_three_sensors():
    from custom_components.ev_trip_planner.sensor import async_setup_entry

    hass = MagicMock()
    # Seed shared TripManager in hass.data like real setup_entry does
    tm = MagicMock()
    tm.async_get_all_trips = AsyncMock(return_value=[])
    hass.data = {"ev_trip_planner": {"eid123": {"trip_manager": tm, "config": {}}}}

    entry = FakeEntry(
        entry_id="eid123",
        data={"vehicle_name": "Chispitas"},
    )

    created: List = []

    def add_entities(ents):
        created.extend(ents)

    await async_setup_entry(hass, entry, add_entities)

    assert len(created) == 3
    uids = {getattr(e, "unique_id", None) for e in created}
    assert uids == {
        "eid123_trips_list",
        "eid123_recurring_trips_count",
        "eid123_punctual_trips_count",
    }
