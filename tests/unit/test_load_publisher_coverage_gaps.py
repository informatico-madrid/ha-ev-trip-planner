"""Tests for uncovered load_publisher.py paths (lines 264, 268)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

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


class TestCalculateDeadlineNumericDay:
    """Test _calculate_deadline with numeric day values (lines 264, 268)."""

    def test_numeric_day_0_is_sunday(self):
        """Line 264: Day '0' should map to Sunday (6)."""
        pub, _ = _make_publisher()
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        trip = {
            "tipo": "recurrente",
            "dia_semana": "0",
            "hora": "09:00",
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "datetime.datetime",
                type(
                    "MockDatetime",
                    (),
                    {
                        "now": lambda *a, **k: now,
                        "fromisoformat": datetime.fromisoformat,
                        "timezone": timezone,
                    },
                )(),
            )
            result = pub._calculate_deadline(trip)
        assert result is not None
        assert result.weekday() == 6  # Sunday

    def test_numeric_day_7_is_sunday(self):
        """Line 264: Day '7' should map to Sunday (6)."""
        pub, _ = _make_publisher()
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        trip = {
            "tipo": "recurrente",
            "dia_semana": "7",
            "hora": "09:00",
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "datetime.datetime",
                type(
                    "MockDatetime",
                    (),
                    {
                        "now": lambda *a, **k: now,
                        "fromisoformat": datetime.fromisoformat,
                        "timezone": timezone,
                    },
                )(),
            )
            result = pub._calculate_deadline(trip)
        assert result is not None
        assert result.weekday() == 6  # Sunday

    def test_numeric_day_1_is_monday(self):
        """Line 266: Day '1' should map to Monday (0)."""
        pub, _ = _make_publisher()
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        trip = {
            "tipo": "recurrente",
            "dia_semana": "1",
            "hora": "09:00",
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "datetime.datetime",
                type(
                    "MockDatetime",
                    (),
                    {
                        "now": lambda *a, **k: now,
                        "fromisoformat": datetime.fromisoformat,
                        "timezone": timezone,
                    },
                )(),
            )
            result = pub._calculate_deadline(trip)
        assert result is not None
        assert result.weekday() == 0  # Monday

    def test_numeric_day_6_is_saturday(self):
        """Line 266: Day '6' should map to Saturday (5)."""
        pub, _ = _make_publisher()
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        trip = {
            "tipo": "recurrente",
            "dia_semana": "6",
            "hora": "09:00",
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "datetime.datetime",
                type(
                    "MockDatetime",
                    (),
                    {
                        "now": lambda *a, **k: now,
                        "fromisoformat": datetime.fromisoformat,
                        "timezone": timezone,
                    },
                )(),
            )
            result = pub._calculate_deadline(trip)
        assert result is not None
        assert result.weekday() == 5  # Saturday

    def test_numeric_day_9_returns_none(self):
        """Line 268: Invalid numeric day (>7) should return None."""
        pub, _ = _make_publisher()
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        trip = {
            "tipo": "recurrente",
            "dia_semana": "9",
            "hora": "09:00",
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "datetime.datetime",
                type(
                    "MockDatetime",
                    (),
                    {
                        "now": lambda *a, **k: now,
                        "fromisoformat": datetime.fromisoformat,
                        "timezone": timezone,
                    },
                )(),
            )
            result = pub._calculate_deadline(trip)
        assert result is None

    def test_numeric_day_negative(self):
        """Negative numeric day should return None."""
        pub, _ = _make_publisher()
        now = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        trip = {
            "tipo": "recurrente",
            "dia_semana": "-1",
            "hora": "09:00",
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "datetime.datetime",
                type(
                    "MockDatetime",
                    (),
                    {
                        "now": lambda *a, **k: now,
                        "fromisoformat": datetime.fromisoformat,
                        "timezone": timezone,
                    },
                )(),
            )
            result = pub._calculate_deadline(trip)
        assert result is None


class TestPublishSocUnavailable:
    """Test publish() returns False when SOC sensor is unavailable."""

    @pytest.mark.asyncio
    async def test_publish_returns_false_when_soc_sensor_not_configured(self):
        """Lines 322-323: _soc_sensor not set → _get_current_soc returns None → publish returns False."""
        hass = MagicMock()
        idx_mgr = MagicMock()
        config = LoadPublisherConfig(
            charging_power_kw=3.6,
            battery_capacity_kwh=75.0,
            index_manager=idx_mgr,
        )
        publisher = LoadPublisher(hass, "test_vehicle", config)
        publisher._soc_sensor = None

        trip = {
            "id": "trip_1",
            "kwh": 10.0,
            "datetime": "2026-05-20T08:00:00+00:00",
        }
        publisher._index_manager.assign_index = MagicMock(return_value=1)

        result = await publisher.publish(trip)

        assert result is False
        publisher._index_manager.assign_index.assert_called_once_with("trip_1")

    @pytest.mark.asyncio
    async def test_publish_returns_false_when_soc_sensor_state_missing(self):
        """Lines 324-326: hass.states.get returns None → _get_current_soc returns None."""
        hass = MagicMock()
        hass.states.get.return_value = None
        idx_mgr = MagicMock()
        config = LoadPublisherConfig(
            charging_power_kw=3.6,
            battery_capacity_kwh=75.0,
            index_manager=idx_mgr,
        )
        publisher = LoadPublisher(hass, "test_vehicle", config)
        publisher._soc_sensor = "sensor.soc"

        trip = {
            "id": "trip_1",
            "kwh": 10.0,
            "datetime": "2026-05-20T08:00:00+00:00",
        }
        publisher._index_manager.assign_index = MagicMock(return_value=2)

        result = await publisher.publish(trip)

        assert result is False

    @pytest.mark.asyncio
    async def test_publish_returns_false_when_soc_sensor_state_invalid(self):
        """Lines 327-330: state.state can't be float → ValueError/TypeError → _get_current_soc returns None."""
        hass = MagicMock()
        mock_state = MagicMock()
        mock_state.state = "unknown"
        hass.states.get.return_value = mock_state
        idx_mgr = MagicMock()
        config = LoadPublisherConfig(
            charging_power_kw=3.6,
            battery_capacity_kwh=75.0,
            index_manager=idx_mgr,
        )
        publisher = LoadPublisher(hass, "test_vehicle", config)
        publisher._soc_sensor = "sensor.invalid"

        trip = {
            "id": "trip_1",
            "kwh": 10.0,
            "datetime": "2026-05-20T08:00:00+00:00",
        }
        publisher._index_manager.assign_index = MagicMock(return_value=3)

        result = await publisher.publish(trip)

        assert result is False


class TestGetCurrentSoc:
    """Direct unit tests for _get_current_soc branches."""

    @pytest.mark.asyncio
    async def test_get_current_soc_no_sensor(self):
        """Line 322-323: No _soc_sensor → returns None immediately."""
        hass = MagicMock()
        idx_mgr = MagicMock()
        config = LoadPublisherConfig(
            charging_power_kw=3.6,
            battery_capacity_kwh=75.0,
            index_manager=idx_mgr,
        )
        publisher = LoadPublisher(hass, "test_vehicle", config)
        publisher._soc_sensor = None

        result = await publisher._get_current_soc()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_soc_sensor_not_in_hass(self):
        """Lines 324-326: Sensor entity not found in hass.states → returns None."""
        hass = MagicMock()
        hass.states.get.return_value = None
        idx_mgr = MagicMock()
        config = LoadPublisherConfig(
            charging_power_kw=3.6,
            battery_capacity_kwh=75.0,
            index_manager=idx_mgr,
        )
        publisher = LoadPublisher(hass, "test_vehicle", config)
        publisher._soc_sensor = "sensor.missing"

        result = await publisher._get_current_soc()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_soc_invalid_state_value(self):
        """Lines 327-330: State is not a valid number → ValueError → returns None."""
        hass = MagicMock()
        mock_state = MagicMock()
        mock_state.state = "not_a_number"
        hass.states.get.return_value = mock_state
        idx_mgr = MagicMock()
        config = LoadPublisherConfig(
            charging_power_kw=3.6,
            battery_capacity_kwh=75.0,
            index_manager=idx_mgr,
        )
        publisher = LoadPublisher(hass, "test_vehicle", config)
        publisher._soc_sensor = "sensor.invalid"

        result = await publisher._get_current_soc()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_soc_valid_state(self):
        """Valid SOC value from sensor state."""
        hass = MagicMock()
        mock_state = MagicMock()
        mock_state.state = "75.5"
        hass.states.get.return_value = mock_state
        idx_mgr = MagicMock()
        config = LoadPublisherConfig(
            charging_power_kw=3.6,
            battery_capacity_kwh=75.0,
            index_manager=idx_mgr,
        )
        publisher = LoadPublisher(hass, "test_vehicle", config)
        publisher._soc_sensor = "sensor.valid"

        result = await publisher._get_current_soc()

        assert result == 75.5
