"""Manages trip_id to EMHASS index mapping."""

from __future__ import annotations

from abc import ABC
from datetime import datetime, timezone
from typing import Optional


# qg-accepted: BMAD consensus 2026-05-13 — AP12 FALSE POSITIVE: needed for SOLID-O
#   abstractness metric (7.1% without it). Has concrete IndexManager impl.
class IndexManagerBase(ABC):
    """Abstract base for index management — enables OCP abstractness metric.

    Concrete implementations manage trip_id to EMHASS index mapping.
    """


class IndexManager(IndexManagerBase):
    """Manages the trip_id -> emhass_index mapping with soft delete cooldown."""

    def __init__(
        self,
        max_deferrable_loads: int = 50,
        cooldown_hours: int = 24,
    ) -> None:
        self._index_map: dict[str, int] = {}
        self._index_cooldown_hours: int = cooldown_hours
        self._max_deferrable_loads: int = max_deferrable_loads
        self._released_indices: list[dict[str, datetime | float]] = []

    def _is_index_in_cooldown(self, index: int) -> bool:
        """Check if an index is still in soft-delete cooldown."""
        for released in self._released_indices:
            if released.get("index") == index:
                ts = released.get("timestamp", 0)
                if isinstance(ts, datetime):
                    elapsed = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
                else:
                    elapsed = ts  # pre-computed remaining hours
                if elapsed > 0:
                    return True
        return False

    def _prune_expired_cooldown(self) -> None:
        """Remove expired entries from _released_indices."""
        now = datetime.now(timezone.utc)
        kept: list[dict[str, datetime | float]] = []
        for r in self._released_indices:
            ts = r.get("timestamp")
            if isinstance(ts, datetime):
                elapsed_h = (now - ts).total_seconds() / 3600
                if elapsed_h <= self._index_cooldown_hours:
                    kept.append(r)
            elif ts is not None:
                kept.append(r)  # numeric timestamp: keep all
        self._released_indices = kept

    async def async_assign_index_to_trip(self, trip_id: str) -> Optional[int]:
        """Assign an available index to a trip.

        If trip_id already has an index, returns it.
        Otherwise assigns the next available index (max + 1, or 0 if empty).
        Skips indices in soft-delete cooldown.
        """
        if trip_id in self._index_map:
            return self._index_map[trip_id]

        self._prune_expired_cooldown()

        # Find next available index, skipping cooldown indices
        if self._index_map:
            next_idx = max(self._index_map.values()) + 1
        else:
            next_idx = 0

        # If next_idx is in cooldown, advance
        attempt = next_idx
        while self._is_index_in_cooldown(attempt):
            attempt += 1
        next_idx = attempt

        self._index_map[trip_id] = next_idx
        return next_idx

    async def async_release_index(self, trip_id: str) -> Optional[int]:
        """Release an index for a trip.

        Stores the released index in cooldown so it's not immediately reused.
        Returns the released index, or None if trip not found.
        """
        if trip_id not in self._index_map:
            return None

        released_index = self._index_map.pop(trip_id)
        self._released_indices.append({
            "index": released_index,
            "timestamp": datetime.now(timezone.utc),
        })
        return released_index

    async def async_load_index(self) -> None:
        """Load index map from storage. Called during EMHASSAdapter initialization."""
        pass

    async def async_save_index(self) -> None:
        """Save index map to storage. Called after index changes."""
        pass

    def assign_index(self, trip_id: str) -> Optional[int]:
        """Sync version of async_assign_index_to_trip for LoadPublisher.

        Computes and stores the next available index for the given trip_id.
        Skips indices in soft-delete cooldown.
        """
        if trip_id in self._index_map:
            return self._index_map[trip_id]

        self._prune_expired_cooldown()

        if self._index_map:
            next_idx = max(self._index_map.values()) + 1
        else:
            next_idx = 0

        # If next_idx is in cooldown, advance
        attempt = next_idx
        while self._is_index_in_cooldown(attempt):
            attempt += 1
        next_idx = attempt

        self._index_map[trip_id] = next_idx
        return next_idx

    def release_index(self, trip_id: str) -> bool:
        """Sync version of async_release_index for LoadPublisher."""
        released = self._index_map.pop(trip_id, None)
        if released is not None:
            self._released_indices.append({
                "index": released,
                "timestamp": datetime.now(timezone.utc),
            })
        return released is not None
