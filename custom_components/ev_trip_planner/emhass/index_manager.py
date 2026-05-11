"""Manages trip_id to EMHASS index mapping."""

from __future__ import annotations

from typing import Optional


class IndexManager:
    """Manages the trip_id -> emhass_index mapping."""

    def __init__(self) -> None:
        self._index_map: dict[str, int] = {}
        self._index_cooldown_hours: int = 24

    async def async_assign_index_to_trip(self, trip_id: str) -> Optional[int]:
        """Assign an available index to a trip.

        If trip_id already has an index, returns it.
        Otherwise assigns the next available index (max + 1, or 0 if empty).
        """
        if trip_id in self._index_map:
            return self._index_map[trip_id]

        if self._index_map:
            assigned_index = max(self._index_map.values()) + 1
        else:
            assigned_index = 0

        self._index_map[trip_id] = assigned_index
        return assigned_index

    async def async_release_index(self, trip_id: str) -> Optional[int]:
        """Release an index for a trip.

        Returns the released index, or None if trip not found.
        """
        if trip_id not in self._index_map:
            return None

        released_index = self._index_map.pop(trip_id)
        return released_index

    async def async_load_index(self) -> None:
        """Load index map from storage. Called during EMHASSAdapter initialization."""
        pass

    async def async_save_index(self) -> None:
        """Save index map to storage. Called after index changes."""
        pass
