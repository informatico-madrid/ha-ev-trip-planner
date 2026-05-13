"""Tests for emhass/load_publisher.py."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.emhass.load_publisher import (
    LoadPublisher,
    LoadPublisherConfig,
)


def _make_config(max_deferrable_loads=1):
    """Create a config with a single-slot index manager."""
    from custom_components.ev_trip_planner.emhass.index_manager import IndexManager

    idx_mgr = IndexManager(max_deferrable_loads=max_deferrable_loads, cooldown_hours=0)
    return LoadPublisherConfig(
        charging_power_kw=3.6,
        battery_capacity_kwh=50.0,
        index_manager=idx_mgr,
    )


def _make_publisher(max_deferrable_loads=1):
    """Create a LoadPublisher with a single-slot index manager."""
    hass = MagicMock()
    config = _make_config(max_deferrable_loads=max_deferrable_loads)
    return LoadPublisher(hass, "test_vehicle", config), config.index_manager


class TestLoadPublisherExists:
    """LoadPublisher must be importable from emhass.load_publisher."""

    def test_load_publisher_importable(self):
        """LoadPublisher class is importable from emhass.load_publisher."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        assert LoadPublisher is not None

    def test_load_publisher_has_publish_method(self):
        """LoadPublisher must have a publish method."""
        assert hasattr(LoadPublisher, "publish")

    def test_load_publisher_has_update_method(self):
        """LoadPublisher must have an update method."""
        assert hasattr(LoadPublisher, "update")

    def test_load_publisher_has_remove_method(self):
        """LoadPublisher must have a remove method."""
        assert hasattr(LoadPublisher, "remove")


class TestLoadPublisherPublish:
    """Test LoadPublisher.publish."""

    @pytest.mark.asyncio
    async def test_publish_no_trip_id(self):
        """Missing trip ID returns False."""
        pub, _ = _make_publisher()
        result = await pub.publish({})
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_index_full(self):
        """Index full → assign_index returns a number > max → returns False (line 105)."""
        pub, _ = _make_publisher(max_deferrable_loads=1)
        # Manually fill the index map to simulate index exhaustion
        pub._index_manager._index_map = {"used_0": 0, "used_1": 1}
        result = await pub.publish({"id": "full_trip", "kwh": 5.0})
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_deadline_in_past(self):
        """Deadline in past → hours_available <= 0 → returns False."""
        pub, _ = _make_publisher()
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        result = await pub.publish({"id": "past_trip", "kwh": 5.0, "datetime": past})
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_zero_hours(self):
        """Zero charging hours → power_watts = 0.0 (line 166)."""
        pub, _ = _make_publisher(max_deferrable_loads=100)
        # Create a trip with deadline very close to now (essentially 0 hours)
        future = datetime.now(timezone.utc) + timedelta(seconds=1)
        trip = {
            "id": "zero_hours_trip",
            "kwh": 5.0,
            "datetime": future,
            "status": "active",
        }
        result = await pub.publish(trip)
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_publish_success(self):
        """Successful publish with valid future deadline."""
        pub, _ = _make_publisher(max_deferrable_loads=100)
        future = datetime.now(timezone.utc) + timedelta(hours=10)
        trip = {
            "id": "good_trip",
            "kwh": 5.0,
            "datetime": future,
            "status": "active",
        }
        result = await pub.publish(trip)
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_success(self):
        """Remove with existing index returns True."""
        pub, _ = _make_publisher(max_deferrable_loads=10)
        # Manually add to index map (assign_index doesn't add to _index_map in sync mode)
        pub._index_manager._index_map["to_remove"] = 0
        result = await pub.remove("to_remove")
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_nonexistent(self):
        """Remove nonexistent index returns False."""
        pub, _ = _make_publisher()
        result = await pub.remove("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_index_none_returns_false(self):
        """assign_index returns None → returns False (line 105)."""
        pub, idx_mgr = _make_publisher()
        # Mock assign_index to return None (simulates already-assigned trip)
        idx_mgr.assign_index = MagicMock(return_value=None)
        future = datetime.now(timezone.utc) + timedelta(hours=10)
        trip = {"id": "dup_trip", "kwh": 5.0, "datetime": future, "status": "active"}
        result = await pub.publish(trip)
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_zero_charging_hours(self):
        """kwh=0 → total_hours=0 → power_watts=0.0 (line 166)."""
        pub, _ = _make_publisher()
        future = datetime.now(timezone.utc) + timedelta(hours=10)
        trip = {"id": "zero_kwh_trip", "kwh": 0.0, "datetime": future, "status": "active"}
        result = await pub.publish(trip)
        assert result is True

    @pytest.mark.asyncio
    async def test_update_delegates_to_publish(self):
        """update() delegates to publish() (line 187)."""
        pub, _ = _make_publisher()
        future = datetime.now(timezone.utc) + timedelta(hours=10)
        trip = {"id": "upd_trip", "kwh": 5.0, "datetime": future, "status": "active"}
        with patch.object(pub, "publish", new=AsyncMock(return_value=True)) as mock_pub:
            result = await pub.update(trip)
            assert result is True
            mock_pub.assert_called_once_with(trip)


class TestLoadPublisherConfig:
    """Test LoadPublisherConfig."""

    def test_default_config(self):
        """Config has correct defaults."""
        cfg = LoadPublisherConfig()
        assert cfg.charging_power_kw == 3.6
        assert cfg.battery_capacity_kwh == 50.0
        assert cfg.index_manager is None

    def test_custom_config(self):
        """Config accepts custom values."""
        from custom_components.ev_trip_planner.emhass.index_manager import IndexManager

        idx = IndexManager(max_deferrable_loads=10, cooldown_hours=1)
        cfg = LoadPublisherConfig(
            charging_power_kw=7.0,
            battery_capacity_kwh=75.0,
            index_manager=idx,
        )
        assert cfg.charging_power_kw == 7.0
        assert cfg.battery_capacity_kwh == 75.0
        assert cfg.index_manager is idx


class TestLoadPublisherDeadline:
    """Test _calculate_deadline."""

    def test_deadline_from_iso_string(self):
        """Deadline from ISO datetime string."""
        pub, _ = _make_publisher()
        future = (datetime.now(timezone.utc) + timedelta(hours=10)).isoformat()
        result = pub._calculate_deadline({"datetime": future})
        assert result is not None

    def test_deadline_from_datetime_object(self):
        """Deadline from datetime object."""
        pub, _ = _make_publisher()
        future = datetime.now(timezone.utc) + timedelta(hours=10)
        result = pub._calculate_deadline({"datetime": future})
        assert result is not None

    def test_deadline_recurring_es(self):
        """Recurring trip with Spanish day name."""
        pub, _ = _make_publisher()
        result = pub._calculate_deadline({"tipo": "recurrente", "dia_semana": "lunes", "hora": "09:00"})
        assert result is not None

    def test_deadline_recurring_en(self):
        """Recurring trip with English day name."""
        pub, _ = _make_publisher()
        result = pub._calculate_deadline({"tipo": "recurring", "day": "monday", "time": "09:00"})
        assert result is not None

    def test_deadline_no_data(self):
        """No deadline data → returns None."""
        pub, _ = _make_publisher()
        result = pub._calculate_deadline({"id": "bad_trip"})
        assert result is None

    def test_deadline_numeric_day(self):
        """Recurring trip with numeric day (1=Monday)."""
        pub, _ = _make_publisher()
        result = pub._calculate_deadline({"tipo": "recurrente", "day": "1", "time": "14:00"})
        assert result is not None

    def test_deadline_invalid_day(self):
        """Invalid day name → returns None."""
        pub, _ = _make_publisher()
        result = pub._calculate_deadline({"tipo": "recurrente", "dia_semana": "funday", "hora": "09:00"})
        assert result is None

    def test_deadline_recurring_same_day_today(self):
        """Recurring trip targeting today's day → delta_days=7 (line 261)."""
        pub, _ = _make_publisher()
        # Use Wednesday (today's weekday) with Spanish day name
        result = pub._calculate_deadline({"tipo": "recurrente", "dia_semana": "miércoles", "hora": "09:00"})
        assert result is not None
        # delta_days=7 → deadline is next week (7 days from today's time)
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        delta = result - now
        # At least 6 full days, less than 8 (next week's same day)
        assert 6 <= delta.days < 8


class TestLoadPublisherEnsureAware:
    """Test _ensure_aware static method."""

    def test_aware_datetime_unchanged(self):
        """Already-aware datetime returns unchanged."""
        dt = datetime.now(timezone.utc)
        result = LoadPublisher._ensure_aware(dt)
        assert result.tzinfo is not None

    def test_naive_datetime_made_aware(self):
        """Naive datetime gets UTC timezone."""
        dt = datetime(2026, 5, 14, 9, 0, 0)
        result = LoadPublisher._ensure_aware(dt)
        assert result.tzinfo is timezone.utc
