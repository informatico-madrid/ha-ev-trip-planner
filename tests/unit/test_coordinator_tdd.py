"""Tests for recurring trip rotation in publish_deferrable_loads.

Tests the coordinator's hourly timer triggering rotation of recurring trips,
multiple independent rotations, rotation without EMHASS adapter, and
prevention of infinite loops between rotation and coordinator refresh.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest


def _next_weekday_from_now(weekday_iso: int) -> str:
    """Get the next occurrence of a weekday from now.

    Args:
        weekday_iso: ISO weekday (1=Monday, 7=Sunday)

    Returns:
        Date string in YYYY-MM-DD format for the next occurrence.
    """
    now = datetime.now()
    days_ahead = (weekday_iso - now.isoweekday()) % 7
    if days_ahead == 0:
        days_ahead = 7  # Always go to next week to ensure it's future
    target = now + timedelta(days=days_ahead)
    return target.strftime("%Y-%m-%d")


def _past_datetime_for_weekday(weekday_iso: int, weeks_ago: int = 2) -> str:
    """Get a past datetime string for a given weekday.

    Args:
        weekday_iso: ISO weekday (1=Monday, 7=Sunday)
        weeks_ago: How many weeks in the past

    Returns:
        ISO datetime string for the past occurrence.
    """
    now = datetime.now()
    days_back = (now.isoweekday() - weekday_iso) % 7 + (7 * weeks_ago)
    if days_back == 0:
        days_back = 7
    target = now - timedelta(days=days_back)
    return target.strftime("%Y-%m-%dT08:00:00")


class TestCoordinatorTdd:
    """Tests for coordinator recurring trip rotation."""

    @pytest.mark.asyncio
    async def test_hourly_timer_rotates_recurring_trips(
        self, trip_manager_with_entry_id
    ):
        """Hourly timer triggers rotation of recurring trips.

        Verifies that the hourly timer in __init__.py calls
        publish_deferrable_loads() which rotates recurring trips.
        """
        # Arrange - Create a recurring trip that should rotate (past Monday)
        # Use a dynamically computed past Monday
        past_monday = _past_datetime_for_weekday(1)  # 1=Monday
        _next_monday = _next_weekday_from_now(1)  # noqa: F841 — next Monday reference

        recurring_trip = {
            "id": "rec_test_1",
            "tipo": "recurring",
            "dia_semana": "lunes",
            "hora": "08:00",
            "datetime": past_monday,
            "km": 50.0,
            "kwh": 7.5,
            "activo": True,
        }

        # Act - Simulate hourly refresh by calling publish_deferrable_loads
        await trip_manager_with_entry_id.publish_deferrable_loads([recurring_trip])

        # Assert - Trip datetime should be updated to a future Monday
        rotated_dt = recurring_trip["datetime"]
        rotated_date = (
            datetime.fromisoformat(rotated_dt.replace("Z", "+00:00"))
            if "T" in rotated_dt
            else datetime.fromisoformat(rotated_dt)
        )
        now = datetime.now(timezone.utc) if rotated_date.tzinfo else datetime.now()
        assert (
            rotated_date > now
        ), f"Rotated datetime should be in the future, got {rotated_dt}"
        # Verify it's a Monday (ISO weekday 1)
        assert (
            rotated_date.isoweekday() == 1
        ), f"Rotated datetime should be a Monday, got weekday {rotated_date.isoweekday()} ({rotated_dt})"

    @pytest.mark.asyncio
    async def test_multiple_recurring_trips_rotate_independently(
        self, trip_manager_with_entry_id
    ):
        """Multiple recurring trips rotate independently.

        Verifies that each recurring trip is rotated based on its own
        schedule, not affecting other trips.
        """
        # Arrange - Create multiple recurring trips with past datetimes
        past_monday = _past_datetime_for_weekday(1)
        past_wednesday = _past_datetime_for_weekday(3)
        past_friday = _past_datetime_for_weekday(5)

        trips = [
            {
                "id": "rec_mon_1",
                "tipo": "recurring",
                "dia_semana": "lunes",
                "hora": "08:00",
                "datetime": past_monday,
                "km": 50.0,
                "kwh": 7.5,
                "activo": True,
            },
            {
                "id": "rec_wed_1",
                "tipo": "recurring",
                "dia_semana": "miercoles",
                "hora": "18:00",
                "datetime": past_wednesday,
                "km": 80.0,
                "kwh": 12.0,
                "activo": True,
            },
            {
                "id": "rec_fri_1",
                "tipo": "recurring",
                "dia_semana": "viernes",
                "hora": "07:30",
                "datetime": past_friday,
                "km": 40.0,
                "kwh": 6.0,
                "activo": True,
            },
        ]

        # Act - Call publish_deferrable_loads
        await trip_manager_with_entry_id.publish_deferrable_loads(trips)

        # Assert - All trips should be rotated to future dates on correct weekdays
        expected_weekdays = {
            "rec_mon_1": 1,  # Monday
            "rec_wed_1": 3,  # Wednesday
            "rec_fri_1": 5,  # Friday
        }
        for trip in trips:
            rotated_dt = trip["datetime"]
            rotated_date = (
                datetime.fromisoformat(rotated_dt.replace("Z", "+00:00"))
                if "T" in rotated_dt
                else datetime.fromisoformat(rotated_dt)
            )
            now = datetime.now(timezone.utc) if rotated_date.tzinfo else datetime.now()
            assert (
                rotated_date > now
            ), f"{trip['id']} should be rotated to future, got {rotated_dt}"
            expected_wd = expected_weekdays[trip["id"]]
            assert (
                rotated_date.isoweekday() == expected_wd
            ), f"{trip['id']} should be on weekday {expected_wd}, got {rotated_date.isoweekday()} ({rotated_dt})"

    @pytest.mark.asyncio
    async def test_rotation_without_emhass_adapter(
        self, trip_manager_no_entry_id
    ):
        """Rotation works even without EMHASS adapter.

        Verifies that recurring trip rotation works when emhass_adapter
        is None (e.g., before EMHASS is configured).
        """
        # Arrange - Create a recurring trip with past datetime
        past_monday = _past_datetime_for_weekday(1)
        recurring_trip = {
            "id": "rec_no_emhass_1",
            "tipo": "recurring",
            "dia_semana": "lunes",
            "hora": "08:00",
            "datetime": past_monday,
            "km": 50.0,
            "kwh": 7.5,
            "activo": True,
        }
        original_datetime = recurring_trip["datetime"]

        # Act - Call publish_deferrable_loads (should not early return when no emhass_adapter)
        await trip_manager_no_entry_id.publish_deferrable_loads([recurring_trip])

        # Assert - Trip should still be rotated even without emhass_adapter
        assert (
            recurring_trip["datetime"] != original_datetime
        ), f"Rotation should work without emhass_adapter, got {recurring_trip['datetime']}"
        rotated_dt = recurring_trip["datetime"]
        rotated_date = (
            datetime.fromisoformat(rotated_dt.replace("Z", "+00:00"))
            if "T" in rotated_dt
            else datetime.fromisoformat(rotated_dt)
        )
        now = datetime.now(timezone.utc) if rotated_date.tzinfo else datetime.now()
        assert (
            rotated_date > now
        ), f"Rotated datetime should be future Monday, got {rotated_dt}"
        assert (
            rotated_date.isoweekday() == 1
        ), f"Rotated datetime should be a Monday, got weekday {rotated_date.isoweekday()} ({rotated_dt})"

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="T3.3 (auto-complete punctual trips) not implemented yet - pending Plan v3 scope extension"
    )
    async def test_punctual_trip_auto_complete_past_deadline(
        self, trip_manager_with_entry_id
    ):
        """Punctual trips with past deadline marked inactive.

        Verifies that T3.3 (auto-complete punctual trips) marks
        trips with past deadlines as inactive.

        NOTE: This test is SKIPPED because T3.3 is not in Plan v3 scope.
        When T3.3 is implemented, remove the skip marker.
        """
        # Arrange - Create a punctual trip with past deadline
        past_trip = {
            "id": "punct_past_1",
            "tipo": "punctual",
            "datetime": _past_datetime_for_weekday(1),
            "km": 100.0,
            "kwh": 20.0,
            "activo": True,
            "estado": "pendiente",
        }

        # Act - Call publish_deferrable_loads
        await trip_manager_with_entry_id.publish_deferrable_loads([past_trip])

        # Assert - Trip with past deadline should be marked inactive
        assert (
            past_trip.get("activo") is False or past_trip.get("estado") == "completado"
        ), f"Past punctual trip should be marked inactive, got activo={past_trip.get('activo')}, estado={past_trip.get('estado')}"

    @pytest.mark.asyncio
    async def test_no_infinite_loop_in_rotation(
        self, trip_manager_with_entry_id
    ):
        """No infinite loop in rotation logic.

        Verifies that calling publish_deferrable_loads() does NOT
        trigger coordinator refresh (which would cause infinite loop).

        The rotation code is placed BEFORE the coordinator refresh logic
        to avoid the infinite loop issue.
        """
        # Arrange - Create a recurring trip
        past_monday = _past_datetime_for_weekday(1)
        recurring_trip = {
            "id": "rec_loop_test_1",
            "tipo": "recurring",
            "dia_semana": "lunes",
            "hora": "08:00",
            "datetime": past_monday,
            "km": 50.0,
            "kwh": 7.5,
            "activo": True,
        }

        # Mock coordinator to track if refresh is called
        mock_coordinator = MagicMock()
        trip_manager_with_entry_id._coordinator = mock_coordinator  # Set coordinator

        # Act - Call publish_deferrable_loads
        # This should rotate the trip but NOT call coordinator.async_refresh()
        # because rotation happens BEFORE coordinator refresh logic
        await trip_manager_with_entry_id.publish_deferrable_loads([recurring_trip])

        # Assert - Coordinator refresh should NOT be called
        # (rotation happens before coordinator refresh logic to avoid infinite loop)
        assert (
            not mock_coordinator.async_refresh.called
        ), "publish_deferrable_loads should not call coordinator.async_refresh"
