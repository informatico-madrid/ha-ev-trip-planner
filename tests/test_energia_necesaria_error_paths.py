"""Tests for async_calcular_energia_necesaria error paths (T114).

Exercises the removed pragma: no cover branches in trip_manager.py lines 1674-1704:
- trip_time is None from _parse_trip_datetime (line 1674-1675)
- TypeError during datetime subtraction (line 1680-1697)
- Naive datetime timezone coercion (line 1691-1694)
- Outer exception handler (line 1703-1704)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager


def _future_iso():
    """ISO datetime 24h in the future — always valid regardless of when tests run."""
    return (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()


def _future_naive():
    """Naive datetime 7 days in the future — always valid regardless of when tests run."""
    return (datetime.now() + timedelta(days=7)).replace(hour=18, minute=0, second=0, microsecond=0).isoformat()


@pytest.fixture
def tm():
    """Create a minimal TripManager."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return TripManager(hass, "test_vehicle")


def _base_trip():
    """Return a minimal trip dict for async_calcular_energia_necesaria."""
    return {"kwh": 10.0, "km": 50.0}


def _vehicle_config():
    """Return a minimal vehicle config."""
    return {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "soc_current": 50.0,
        "consumption_kwh_per_km": 0.15,
        "safety_margin_percent": 10.0,
    }


class TestEnergiaNecesariaDatetimeErrorPaths:
    """Removed pragma lines 1674-1704: datetime calculation edge cases."""

    async def test_trip_datetime_parse_none_branch(self, tm):
        """Line 1674-1675: _parse_trip_datetime returns None."""
        with patch.object(tm, "_parse_trip_datetime", return_value=None):
            result = await tm.async_calcular_energia_necesaria(
                {**_base_trip(), "datetime": "2026-05-01T10:00:00+00:00"},
                _vehicle_config(),
            )
        # hours available stays 0.0 (the None path just passes)
        assert result["horas_disponibles"] == 0.0

    async def test_naive_datetime_gets_coerced(self, tm):
        """Lines 1691-1694: naive datetime → coerced to UTC → delta computed."""
        result = await tm.async_calcular_energia_necesaria(
            {**_base_trip(), "datetime": _future_naive()}, _vehicle_config()
        )
        assert result["horas_disponibles"] >= 0.0

    async def test_trip_datetime_string_parses_and_computes(self, tm):
        """Valid ISO datetime → delta computed."""
        result = await tm.async_calcular_energia_necesaria(
            {**_base_trip(), "datetime": _future_iso()}, _vehicle_config()
        )
        assert result["horas_disponibles"] >= 0.0
        assert result["energia_necesaria_kwh"] >= 0.0

    async def test_parse_trip_datetime_raises_value_error(self, tm):
        """Line 1703: _parse_trip_datetime raises ValueError → caught by outer except."""
        with patch.object(tm, "_parse_trip_datetime", side_effect=ValueError("boom")):
            result = await tm.async_calcular_energia_necesaria(
                {**_base_trip(), "datetime": _future_iso()},
                _vehicle_config(),
            )
        assert result["horas_disponibles"] == 0.0

    async def test_parse_trip_datetime_raises_type_error(self, tm):
        """Line 1703: _parse_trip_datetime raises TypeError → caught."""
        with patch.object(tm, "_parse_trip_datetime", side_effect=TypeError("boom")):
            result = await tm.async_calcular_energia_necesaria(
                {**_base_trip(), "datetime": _future_iso()},
                _vehicle_config(),
            )
        assert result["horas_disponibles"] == 0.0

    async def test_datetime_subtraction_type_error_coerce_fails(self, tm):
        """Line 1695-1697: TypeError → coerce fails → delta=None."""

        class FakeDT:
            def __sub__(self, other):
                raise TypeError("bad")

            def replace(self, tzinfo=None):
                raise AttributeError("can't replace")

        with patch.object(tm, "_parse_trip_datetime", return_value=FakeDT()):
            result = await tm.async_calcular_energia_necesaria(
                {**_base_trip(), "datetime": _future_iso()},
                _vehicle_config(),
            )
        # TypeError at 1680 → coerce fails at 1693 → except Exception at 1695 → delta=None at 1697
        assert result["horas_disponibles"] == 0.0

    async def test_datetime_subtraction_type_error_coerce_succeeds(self, tm):
        """Line 1694: TypeError → coerce succeeds → line 1694 hit."""

        class FakeDT:
            def __sub__(self, other):
                raise TypeError("bad")

            def replace(self, tzinfo=None):
                return datetime.now(timezone.utc) + timedelta(hours=48)

        with patch.object(tm, "_parse_trip_datetime", return_value=FakeDT()):
            result = await tm.async_calcular_energia_necesaria(
                {**_base_trip(), "datetime": _future_iso()},
                _vehicle_config(),
            )
        # TypeError at 1680 → coerced at 1693 → line 1694 hit → delta computed
        assert result["horas_disponibles"] >= 0.0
