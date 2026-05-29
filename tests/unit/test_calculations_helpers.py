"""Tests for calculations/_helpers.py — private datetime helpers.

Phase 1, Task 1.11 [RED]: Verify that _ensure_aware and other private
datetime helpers from calculations_orig.py can be imported from
calculations._helpers after the functional decomposition split.
"""

from __future__ import annotations


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


# =============================================================================
# US-5 Log Constant Tests (calculations._helpers)
# =============================================================================


def test_log_constants_defined_in_helpers_module() -> None:
    """Log string constants must exist as module-level attributes."""
    from custom_components.ev_trip_planner.calculations import _helpers

    assert hasattr(_helpers, "_LOG_INVALID_DATETIME")
    assert hasattr(_helpers, "_LOG_NO_DATETIME_OR_DAY_TIME")
    assert hasattr(_helpers, "_LOG_INVALID_DAY")
    assert hasattr(_helpers, "_LOG_INVALID_DAY_TIME")


def test_log_constants_are_non_empty_strings() -> None:
    """Log constants must be non-empty strings (mutation target: None/string change)."""
    from custom_components.ev_trip_planner.calculations import _helpers

    for attr in (
        "_LOG_INVALID_DATETIME",
        "_LOG_NO_DATETIME_OR_DAY_TIME",
        "_LOG_INVALID_DAY",
        "_LOG_INVALID_DAY_TIME",
    ):
        val = getattr(_helpers, attr)
        assert isinstance(val, str)
        assert len(val) > 0


def test_log_invalid_datetime_format() -> None:
    """_LOG_INVALID_DATETIME must accept %s placeholder for trip id."""
    from custom_components.ev_trip_planner.calculations._helpers import (
        _LOG_INVALID_DATETIME,
    )

    assert isinstance(_LOG_INVALID_DATETIME, str)
    assert "%s" in _LOG_INVALID_DATETIME
    # Verify it formats correctly
    formatted = _LOG_INVALID_DATETIME % "test-trip"
    assert isinstance(formatted, str)
    assert len(formatted) > 0


def test_log_no_datetime_or_day_time_format() -> None:
    """_LOG_NO_DATETIME_OR_DAY_TIME must accept %s placeholder for trip id."""
    from custom_components.ev_trip_planner.calculations._helpers import (
        _LOG_NO_DATETIME_OR_DAY_TIME,
    )

    assert isinstance(_LOG_NO_DATETIME_OR_DAY_TIME, str)
    assert "%s" in _LOG_NO_DATETIME_OR_DAY_TIME
    formatted = _LOG_NO_DATETIME_OR_DAY_TIME % "test-trip"
    assert isinstance(formatted, str)


def test_log_invalid_day_format() -> None:
    """_LOG_INVALID_DAY must accept %s placeholders for trip id and day value."""
    from custom_components.ev_trip_planner.calculations._helpers import (
        _LOG_INVALID_DAY,
    )

    assert isinstance(_LOG_INVALID_DAY, str)
    assert _LOG_INVALID_DAY.count("%s") >= 2
    formatted = _LOG_INVALID_DAY % ("test-trip", "invalid")
    assert isinstance(formatted, str)


def test_log_invalid_day_time_format() -> None:
    """_LOG_INVALID_DAY_TIME must accept %s placeholder for trip id."""
    from custom_components.ev_trip_planner.calculations._helpers import (
        _LOG_INVALID_DAY_TIME,
    )

    assert isinstance(_LOG_INVALID_DAY_TIME, str)
    assert "%s" in _LOG_INVALID_DAY_TIME
    formatted = _LOG_INVALID_DAY_TIME % "test-trip"
    assert isinstance(formatted, str)


# =============================================================================
# Mutation-killing tests for resolve_trip_deadline (top survivor: 56)
# =============================================================================


def test_resolve_trip_deadline_returns_datetime_for_valid_iso_string() -> None:
    """Mutant: datetime.fromisoformat path skipped → returns None for valid date string."""
    from datetime import datetime, timezone

    from custom_components.ev_trip_planner.calculations._helpers import (
        resolve_trip_deadline,
    )

    now = datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)
    trip = {
        "id": "t1",
        "datetime": "2026-04-07T06:00:00+00:00",
    }
    result = resolve_trip_deadline(trip, now)
    assert result is not None
    assert isinstance(result, datetime)
    assert result.year == 2026
    assert result.month == 4
    assert result.day == 7
    assert result.hour == 6


def test_resolve_trip_deadline_returns_datetime_for_direct_datetime() -> None:
    """Mutant: direct datetime path flipped → returns None for valid datetime."""
    from datetime import datetime, timezone

    from custom_components.ev_trip_planner.calculations._helpers import (
        resolve_trip_deadline,
    )

    now = datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)
    trip = {
        "id": "t1",
        "datetime": datetime(2026, 4, 7, 6, 0, 0, tzinfo=timezone.utc),
    }
    result = resolve_trip_deadline(trip, now)
    assert result is not None
    assert isinstance(result, datetime)


def test_resolve_trip_deadline_returns_none_for_bad_date_string() -> None:
    """Mutant: ValueError path skipped → returns non-None for invalid date."""
    from datetime import datetime, timezone

    from custom_components.ev_trip_planner.calculations._helpers import (
        resolve_trip_deadline,
    )

    now = datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)
    trip = {
        "id": "t1",
        "datetime": "not-a-valid-date",
    }
    result = resolve_trip_deadline(trip, now)
    assert result is None


def test_resolve_trip_deadline_returns_none_for_no_datetime_no_day_time() -> None:
    """Mutant: normalize_trip_fields/None path flipped → returns datetime for missing fields."""
    from datetime import datetime, timezone

    from custom_components.ev_trip_planner.calculations._helpers import (
        resolve_trip_deadline,
    )

    now = datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)
    trip = {"id": "t1"}  # No datetime, day, time, dia_semana, or hora
    result = resolve_trip_deadline(trip, now)
    assert result is None


def test_resolve_trip_deadline_returns_none_for_invalid_day() -> None:
    """Mutant: _is_valid_day flipped → returns datetime for invalid day value."""
    from datetime import datetime, timezone

    from custom_components.ev_trip_planner.calculations._helpers import (
        resolve_trip_deadline,
    )

    now = datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)
    trip = {"id": "t1", "day": "notaday", "time": "18:00"}
    result = resolve_trip_deadline(trip, now)
    assert result is None


def test_resolve_trip_deadline_returns_datetime_for_recurring() -> None:
    """Mutant: tipo check flipped → falls through incorrectly and returns None."""
    from datetime import datetime, timezone

    from custom_components.ev_trip_planner.calculations._helpers import (
        resolve_trip_deadline,
    )

    now = datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)
    trip = {"id": "t1", "day": "1", "time": "18:00", "tipo": "recurrente"}
    result = resolve_trip_deadline(trip, now)
    assert result is not None
    assert isinstance(result, datetime)


def test_resolve_trip_deadline_returns_datetime_for_recurring_fallback() -> None:
    """Mutant: fallback path skipped → returns None for non-recurrent tipo with day/time."""
    from datetime import datetime, timezone

    from custom_components.ev_trip_planner.calculations._helpers import (
        resolve_trip_deadline,
    )

    now = datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)
    trip = {"id": "t1", "day": "1", "time": "18:00", "tipo": "punctual"}
    result = resolve_trip_deadline(trip, now)
    # Even with "punctual" tipo, should fall through to recurring fallback
    assert result is not None
    assert isinstance(result, datetime)
