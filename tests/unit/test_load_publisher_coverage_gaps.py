"""Tests for uncovered load_publisher.py paths (lines 264, 268)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.ev_trip_planner.emhass.load_publisher import (
    LoadPublisher,
    LoadPublisherConfig,
)


def _make_publisher(max_deferrable_loads=10):
    """Create a LoadPublisher with index manager."""
    from custom_components.ev_trip_planner.emhass.index_manager import IndexManager

    hass = MagicMock()
    idx_mgr = IndexManager(max_deferrable_loads=max_deferrable_loads, cooldown_hours=0)
    config = LoadPublisherConfig(
        charging_power_kw=3.6,
        battery_capacity_kwh=75.0,
        index_manager=idx_mgr,
    )
    return LoadPublisher(hass, "test_vehicle", config), idx_mgr


from unittest.mock import MagicMock


class TestCalculateDeadlineNumericDay:
    """Test _calculate_deadline with numeric day values (lines 264, 268)."""

    def test_numeric_day_0_is_sunday(self):
        """Line 264: Day '0' should map to Sunday (6)."""
        pub, _ = _make_publisher()
        now = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        trip = {
            "tipo": "recurrente",
            "dia_semana": "0",
            "hora": "09:00",
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("datetime.datetime", type("MockDatetime", (), {
                "now": lambda *a, **k: now,
                "fromisoformat": datetime.fromisoformat,
                "timezone": timezone,
            })())
            result = pub._calculate_deadline(trip)
        assert result is not None
        assert result.weekday() == 6  # Sunday

    def test_numeric_day_7_is_sunday(self):
        """Line 264: Day '7' should map to Sunday (6)."""
        pub, _ = _make_publisher()
        now = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        trip = {
            "tipo": "recurrente",
            "dia_semana": "7",
            "hora": "09:00",
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("datetime.datetime", type("MockDatetime", (), {
                "now": lambda *a, **k: now,
                "fromisoformat": datetime.fromisoformat,
                "timezone": timezone,
            })())
            result = pub._calculate_deadline(trip)
        assert result is not None
        assert result.weekday() == 6  # Sunday

    def test_numeric_day_1_is_monday(self):
        """Line 266: Day '1' should map to Monday (0)."""
        pub, _ = _make_publisher()
        now = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        trip = {
            "tipo": "recurrente",
            "dia_semana": "1",
            "hora": "09:00",
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("datetime.datetime", type("MockDatetime", (), {
                "now": lambda *a, **k: now,
                "fromisoformat": datetime.fromisoformat,
                "timezone": timezone,
            })())
            result = pub._calculate_deadline(trip)
        assert result is not None
        assert result.weekday() == 0  # Monday

    def test_numeric_day_6_is_saturday(self):
        """Line 266: Day '6' should map to Saturday (5)."""
        pub, _ = _make_publisher()
        now = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        trip = {
            "tipo": "recurrente",
            "dia_semana": "6",
            "hora": "09:00",
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("datetime.datetime", type("MockDatetime", (), {
                "now": lambda *a, **k: now,
                "fromisoformat": datetime.fromisoformat,
                "timezone": timezone,
            })())
            result = pub._calculate_deadline(trip)
        assert result is not None
        assert result.weekday() == 5  # Saturday

    def test_numeric_day_9_returns_none(self):
        """Line 268: Invalid numeric day (>7) should return None."""
        pub, _ = _make_publisher()
        now = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        trip = {
            "tipo": "recurrente",
            "dia_semana": "9",
            "hora": "09:00",
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("datetime.datetime", type("MockDatetime", (), {
                "now": lambda *a, **k: now,
                "fromisoformat": datetime.fromisoformat,
                "timezone": timezone,
            })())
            result = pub._calculate_deadline(trip)
        assert result is None

    def test_numeric_day_negative(self):
        """Negative numeric day should return None."""
        pub, _ = _make_publisher()
        now = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        trip = {
            "tipo": "recurrente",
            "dia_semana": "-1",
            "hora": "09:00",
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("datetime.datetime", type("MockDatetime", (), {
                "now": lambda *a, **k: now,
                "fromisoformat": datetime.fromisoformat,
                "timezone": timezone,
            })())
            result = pub._calculate_deadline(trip)
        assert result is None
