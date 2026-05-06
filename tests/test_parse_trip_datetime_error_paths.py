"""Tests for _parse_trip_datetime, covering both valid paths and error handling (T105).

Previously uncovered branches:
- parse_datetime returns None for invalid strings
- allow_none=True returns None on failure
- allow_none=False returns datetime.now() on failure
- parse_datetime raises Exception (defensive path)
- naive datetime gets UTC timezone
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def tm():
    """Create a minimal TripManager for _parse_trip_datetime tests."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return TripManager(hass, "test_vehicle")


class TestParseTripDateTimeValidPaths:
    """Valid paths that should always work."""

    def test_pass_through_datetime_with_tz(self, tm):
        dt = datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
        result = tm._parse_trip_datetime(dt)
        assert result == dt

    def test_naive_datetime_gets_utc_tz(self, tm):
        dt = datetime(2026, 5, 1, 10, 0, 0)  # No tzinfo
        result = tm._parse_trip_datetime(dt)
        assert result.tzinfo == timezone.utc
        assert result.year == 2026

    def test_iso_string_parses_correctly(self, tm):
        result = tm._parse_trip_datetime("2026-05-01T10:00:00+00:00")
        assert result.year == 2026
        assert result.month == 5
        assert result.day == 1
        assert result.hour == 10


class TestParseTripDateTimeErrorPaths:
    """Previously pragma: no cover branches - parse failures."""

    def test_invalid_datetime_string_returns_now_by_default(self, tm):
        """Invalid string → falls back to datetime.now() (allow_none=False default)."""
        result = tm._parse_trip_datetime("not-a-date")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_null_string_returns_now_by_default(self, tm):
        result = tm._parse_trip_datetime("null")
        assert isinstance(result, datetime)

    def test_empty_string_returns_now_by_default(self, tm):
        result = tm._parse_trip_datetime("")
        assert isinstance(result, datetime)

    def test_invalid_date_string_returns_now(self, tm):
        result = tm._parse_trip_datetime("2024-13-01")
        assert isinstance(result, datetime)

    def test_allow_none_true_returns_none_on_invalid(self, tm):
        """allow_none=True → None instead of datetime.now() on parse failure."""
        result = tm._parse_trip_datetime("not-a-date", allow_none=True)
        assert result is None

    def test_allow_none_true_returns_none_on_null(self, tm):
        result = tm._parse_trip_datetime("null", allow_none=True)
        assert result is None

    def test_allow_none_true_returns_none_on_empty(self, tm):
        result = tm._parse_trip_datetime("", allow_none=True)
        assert result is None

    def test_allow_none_true_still_parses_valid(self, tm):
        """allow_none=True should still parse valid strings correctly."""
        result = tm._parse_trip_datetime("2026-05-01T10:00:00+00:00", allow_none=True)
        assert result is not None
        assert result.year == 2026

    def test_parse_datetime_exception_returns_now_by_default(self, tm):
        """except Exception block: parse_datetime raises → fallback to now()."""
        from homeassistant.util import dt as dt_util

        with patch.object(dt_util, "parse_datetime", side_effect=ValueError("boom")):
            result = tm._parse_trip_datetime("some-string", allow_none=False)
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_parse_datetime_exception_returns_none_with_allow_none(self, tm):
        """except Exception block: parse_datetime raises → None when allow_none=True."""
        from homeassistant.util import dt as dt_util

        with patch.object(dt_util, "parse_datetime", side_effect=ValueError("boom")):
            result = tm._parse_trip_datetime("some-string", allow_none=True)
        assert result is None
