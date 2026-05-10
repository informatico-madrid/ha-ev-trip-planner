"""Tests for calculations/_helpers.py — private datetime helpers.

Phase 1, Task 1.11 [RED]: Verify that _ensure_aware and other private
datetime helpers from calculations_orig.py can be imported from
calculations._helpers after the functional decomposition split.
"""

from __future__ import annotations

import pytest


def test_ensure_aware_exists_in_helpers_module() -> None:
    """_ensure_aware must be importable from calculations._helpers."""
    from custom_components.ev_trip_planner.calculations._helpers import (
        _ensure_aware,
    )

    assert callable(_ensure_aware)


def test_ensure_aware_converts_naive_to_aware_utc() -> None:
    """_ensure_aware should convert naive datetime to UTC-aware."""
    from datetime import datetime

    from custom_components.ev_trip_planner.calculations._helpers import (
        _ensure_aware,
    )

    naive = datetime(2026, 5, 10, 12, 0, 0)
    result = _ensure_aware(naive)
    assert result.tzinfo is not None
    assert result.year == 2026


def test_ensure_aware_leaves_aware_unchanged() -> None:
    """_ensure_aware should return aware datetimes unchanged."""
    from datetime import datetime, timezone

    from custom_components.ev_trip_planner.calculations._helpers import (
        _ensure_aware,
    )

    aware = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
    result = _ensure_aware(aware)
    assert result.tzinfo is not None
