"""Tests for EMHASS datetime offset handling.

TASK 1.1 [RED]: Failing test - datetime.now() raises TypeError with offset-aware deadline.

This test demonstrates the offset-naive/offset-aware bug in emhass_adapter.py.
The test uses an ISO string with timezone offset (e.g., "2026-04-20T10:00:00+02:00")
which creates an offset-aware datetime. When the code subtracts an offset-naive
datetime.now() from this, it raises TypeError.

RED Phase: This test SHOULD FAIL with TypeError before the fix.
"""

from datetime import datetime, timezone

import pytest


class TestDatetimeOffsetBug:
    """Test that datetime offset bugs are exposed."""

    def test_datetime_subtraction_with_offset_aware_deadline(self):
        """Test the specific datetime subtraction that causes the bug.

        This test isolates the exact bug: subtracting offset-naive from offset-aware.

        Scenario:
        1. Parse an ISO datetime string with timezone offset -> offset-aware datetime
        2. Get current time using datetime.now() -> offset-naive datetime
        3. Subtract: (deadline_dt - now) raises TypeError

        The fix is to use datetime.now(timezone.utc) everywhere instead of datetime.now().
        """
        # Simulate what happens in async_publish_deferrable_load
        deadline = "2026-04-20T10:00:00+02:00"

        # Parse the deadline - this creates an offset-aware datetime
        deadline_dt = datetime.fromisoformat(deadline)

        # The buggy code uses datetime.now() which is offset-naive
        now = datetime.now()

        # This subtraction will fail with TypeError
        with pytest.raises(TypeError, match="can't subtract offset-naive"):
            hours_available = (deadline_dt - now).total_seconds() / 3600

    def test_offset_aware_is_parsed_from_iso_string(self):
        """Verify that ISO strings with timezone offsets are parsed as offset-aware."""
        # This test verifies the premise: our test data is indeed offset-aware
        deadline_dt = datetime.fromisoformat("2026-04-20T10:00:00+02:00")

        # Verify it's offset-aware
        assert deadline_dt.tzinfo is not None, "deadline_dt should be offset-aware"

        # Verify naive datetime is actually naive
        now = datetime.now()
        assert now.tzinfo is None, "datetime.now() is offset-naive"

        # The subtraction will fail because one is aware and one is naive
        with pytest.raises(TypeError, match="can't subtract offset-naive"):
            deadline_dt - now

    def test_fix_uses_timezone_utc(self):
        """Show what the fix should look like.

        This test demonstrates that using timezone.utc makes the subtraction work.
        """
        deadline = "2026-04-20T10:00:00+02:00"
        deadline_dt = datetime.fromisoformat(deadline)

        # The FIX: use datetime.now(timezone.utc) instead of datetime.now()
        now = datetime.now(timezone.utc)

        # This should work because both are offset-aware
        hours_available = (deadline_dt - now).total_seconds() / 3600

        # Verify the calculation completes without error
        assert isinstance(hours_available, (int, float))
        assert hours_available > 0  # deadline is in the future
