"""Tests for uncovered index_manager.py paths (lines 40, 55-56, 80)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.ev_trip_planner.emhass.index_manager import IndexManager


class TestIsIndexInCooldownNumericTimestamp:
    """Test _is_index_in_cooldown with numeric timestamp (line 40)."""

    def test_numeric_timestamp_pre_computed_hours(self):
        """Line 40: Numeric timestamp (pre-computed remaining hours) path."""
        mgr = IndexManager()
        # Manually add a released index with numeric timestamp
        mgr._released_indices.append(
            {
                "index": 5,
                "timestamp": 2.0,  # Pre-computed remaining hours (numeric)
            }
        )
        # With 2 hours remaining, index 5 should be in cooldown
        result = mgr._is_index_in_cooldown(5)
        assert result is True

    def test_numeric_timestamp_expired(self):
        """Numeric timestamp that has expired should not be in cooldown."""
        mgr = IndexManager()
        mgr._released_indices.append(
            {
                "index": 5,
                "timestamp": 0.0,  # Expired (0 hours remaining)
            }
        )
        result = mgr._is_index_in_cooldown(5)
        assert result is False


class TestPruneExpiredCooldownNumeric:
    """Test _prune_expired_cooldown with numeric timestamps (lines 55-56)."""

    def test_numeric_timestamp_kept(self):
        """Line 55-56: Numeric timestamp should be kept (all numeric timestamps kept)."""
        mgr = IndexManager()
        mgr._released_indices = [
            {"index": 1, "timestamp": datetime.now(timezone.utc)},
            {"index": 2, "timestamp": 100.0},  # Numeric: keep all
            {"index": 3, "timestamp": 0.5},  # Numeric: keep all
        ]
        mgr._prune_expired_cooldown()
        # All numeric timestamps should be kept
        assert len(mgr._released_indices) == 3

    def test_mixed_timestamps(self):
        """Mixed datetime and numeric timestamps."""
        mgr = IndexManager()
        # Use a recent datetime that hasn't expired yet (within cooldown)
        recent_dt = datetime.now(timezone.utc) - timedelta(hours=1)
        mgr._released_indices = [
            {"index": 1, "timestamp": recent_dt},  # Recent datetime: kept
            {"index": 2, "timestamp": 100.0},  # Numeric: always kept
        ]
        mgr._prune_expired_cooldown()
        # Both should be kept (recent datetime + numeric)
        assert len(mgr._released_indices) == 2


class TestAssignIndexSkipsCooldown:
    """Test async_assign_index_to_trip skips cooldown indices (line 80)."""

    @pytest.mark.asyncio
    async def test_assign_skips_cooldown_index(self):
        """Line 80: When next_idx is in cooldown, advance to next available."""
        mgr = IndexManager()
        # Add a released index in cooldown
        mgr._released_indices.append(
            {
                "index": 0,
                "timestamp": datetime.now(timezone.utc),
            }
        )
        # Assign first trip - should skip index 0 and give index 1
        result = await mgr.async_assign_index_to_trip("trip_001")
        assert result == 1

    @pytest.mark.asyncio
    async def test_assign_skips_multiple_cooldown_indices(self):
        """Multiple cooldown indices should all be skipped."""
        mgr = IndexManager()
        # Add multiple released indices in cooldown
        mgr._released_indices = [
            {"index": 0, "timestamp": datetime.now(timezone.utc)},
            {"index": 1, "timestamp": datetime.now(timezone.utc)},
            {"index": 2, "timestamp": datetime.now(timezone.utc)},
        ]
        # Assign first trip - should skip 0, 1, 2 and give index 3
        result = await mgr.async_assign_index_to_trip("trip_001")
        assert result == 3
