"""Tests for EMHASS index soft delete cooldown regression.

Legacy behavior: when a trip is released, its index goes to _released_indices
and becomes available only after CONF_INDEX_COOLDOWN_HOURS expires.

The SOLID refactor (Spec 3) extracted IndexManager as a separate component.
If IndexManager doesn't implement the cooldown logic, this is a regression.

Key method names in SOLID code:
- IndexManager.assign_index(trip_id) → int (was async_assign_index_to_trip)
- IndexManager.release_index(trip_id) → bool
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from custom_components.ev_trip_planner.emhass.index_manager import IndexManager


class TestIndexManagerCooldowndRegression:
    """Check if IndexManager still has soft delete cooldown logic."""

    def test_index_manager_assign_returns_increasing_indices(self):
        """IndexManager.assign_index() should return incrementing unique indices."""
        mgr = IndexManager(max_deferrable_loads=5)

        idx0 = mgr.assign_index("trip_0")
        idx1 = mgr.assign_index("trip_1")
        idx2 = mgr.assign_index("trip_2")

        assert idx0 == 0
        assert idx1 == 1
        assert idx2 == 2

    def test_index_manager_release_removes_index(self):
        """IndexManager.release_index() should remove the index mapping."""
        mgr = IndexManager(max_deferrable_loads=5)

        idx = mgr.assign_index("trip_0")
        assert idx == 0

        released = mgr.release_index("trip_0")
        assert released is True

        # After release, the mapping should be gone
        assert "trip_0" not in mgr._index_map

    def test_index_manager_reassign_after_release_gets_next(self):
        """After release and reassign, IndexManager should give next unused index.

        BUG CHECK: If IndexManager lost soft delete cooldown, it may reuse
        the released index immediately (returning 0 instead of 1).
        """
        mgr = IndexManager(max_deferrable_loads=5)

        idx0 = mgr.assign_index("trip_0")
        assert idx0 == 0

        # Release trip_0
        mgr.release_index("trip_0")

        # Assign trip_1 — should get index 1 (NOT 0 if cooldown is enforced)
        idx1 = mgr.assign_index("trip_1")

        # If soft delete cooldown is implemented: idx1 == 1 (index 0 in cooldown)
        # If soft delete cooldown was lost: idx1 == 0 (immediate reuse)
        assert idx1 == 1, (
            f"IndexManager.assign_index() returned {idx1} after releasing index 0. "
            "BUG: Index soft-delete cooldown lost in SOLID refactor. "
            "Released index 0 was immediately reused instead of being held in cooldown."
        )

    def test_index_manager_cooldown_hours_preserved(self):
        """IndexManager should store the cooldown_hours parameter."""
        mgr = IndexManager(max_deferrable_loads=50, cooldown_hours=12)
        assert mgr._index_cooldown_hours == 12

    def test_index_manager_cooldown_tracking_restored(self):
        """IndexManager HAS _released_indices — soft delete cooldown restored.

        REGRESSION: SOLID refactor removed _released_indices from IndexManager.
        FIX (BUG-7): _released_indices restored with cooldown logic so released
        indices are not immediately reused.
        """
        mgr = IndexManager(max_deferrable_loads=5, cooldown_hours=24)

        # IndexManager has _released_indices — confirmed by attribute check
        assert hasattr(mgr, "_released_indices"), (
            "IndexManager must have _released_indices for soft delete cooldown."
        )

        # Assign-release-assign cycle: without cooldown, the released index
        # would be immediately reused. With cooldown, it's skipped.
        idx0 = mgr.assign_index("trip_0")
        assert idx0 == 0
        mgr.release_index("trip_0")

        # With cooldown active, the released index 0 is skipped and 1 is assigned
        idx1 = mgr.assign_index("trip_1")
        assert idx1 == 1, (
            f"Cooldown should skip released index 0, got {idx1}."
        )
