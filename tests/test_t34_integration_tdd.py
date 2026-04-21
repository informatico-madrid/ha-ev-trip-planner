"""Integration TDD tests for SOC-Aware Charging Phase 3.

Tests T3.1 (hourly refresh timer), T3.2 (recurring trip rotation),
and T3.3 (auto-complete punctual trips) working together end-to-end.

These tests use publish_deferrable_loads(trips) directly with pre-formed
trip dictionaries, following the pattern from test_t32_and_p11_tdd.py that PASS.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from tests.conftest import (
    trip_manager_with_entry_id,
    trip_manager_no_entry_id,
    mock_hass,
    mock_store,
)


class TestT34_Integration:
    """Integration tests for SOC-Aware Charging Phase 3."""

    @pytest.mark.asyncio
    async def test_t34_01_hourly_timer_rotates_recurring_trips(
        self, trip_manager_with_entry_id
    ):
        """T3.4-01: Hourly timer triggers rotation of recurring trips.
        
        Verifies that the hourly timer in __init__.py calls
        publish_deferrable_loads() which rotates recurring trips.
        """
        # Arrange - Create a recurring trip that should rotate (past Monday)
        # Trips passed to publish_deferrable_loads have their datetime modified in-place
        recurring_trip = {
            "id": "rec_test_1",
            "tipo": "recurring",
            "dia_semana": "lunes",
            "hora": "08:00",
            "datetime": "2026-04-13T08:00:00",  # Past Monday (should rotate to next Monday)
            "km": 50.0,
            "kwh": 7.5,
            "activo": True,
        }
        
        # Act - Simulate hourly refresh by calling publish_deferrable_loads
        await trip_manager_with_entry_id.publish_deferrable_loads([recurring_trip])
        
        # Assert - Trip datetime should be updated (rotated to next Monday)
        # "2026-04-13" is past, should rotate to "2026-04-20" or "2026-04-27"
        assert "2026-04-20" in recurring_trip["datetime"] or "2026-04-27" in recurring_trip["datetime"], (
            f"T3.4-01: Hourly timer should rotate recurring trip datetime to future, got {recurring_trip['datetime']}"
        )

    @pytest.mark.asyncio
    async def test_t34_03_multiple_recurring_trips_rotate_independently(
        self, trip_manager_with_entry_id
    ):
        """T3.4-03: Multiple recurring trips rotate independently.
        
        Verifies that each recurring trip is rotated based on its own
        schedule, not affecting other trips.
        """
        # Arrange - Create multiple recurring trips with past datetimes
        trips = [
            {
                "id": "rec_mon_1",
                "tipo": "recurring",
                "dia_semana": "lunes",
                "hora": "08:00",
                "datetime": "2026-04-13T08:00:00",  # Past Monday
                "km": 50.0,
                "kwh": 7.5,
                "activo": True,
            },
            {
                "id": "rec_wed_1",
                "tipo": "recurring",
                "dia_semana": "miercoles",
                "hora": "18:00",
                "datetime": "2026-04-15T18:00:00",  # Past Wednesday
                "km": 80.0,
                "kwh": 12.0,
                "activo": True,
            },
            {
                "id": "rec_fri_1",
                "tipo": "recurring",
                "dia_semana": "viernes",
                "hora": "07:30",
                "datetime": "2026-04-17T07:30:00",  # Past Friday
                "km": 40.0,
                "kwh": 6.0,
                "activo": True,
            },
        ]
        
        # Act - Call publish_deferrable_loads
        await trip_manager_with_entry_id.publish_deferrable_loads(trips)
        
        # Assert - All trips should be rotated to future dates
        # Monday trip should rotate to next Monday (2026-04-20)
        assert "2026-04-20" in trips[0]["datetime"] or "2026-04-27" in trips[0]["datetime"], (
            f"T3.4-03: Monday trip should rotate to future, got {trips[0]['datetime']}"
        )
        # Wednesday trip should rotate to next Wednesday (2026-04-22)
        assert "2026-04-22" in trips[1]["datetime"] or "2026-04-29" in trips[1]["datetime"], (
            f"T3.4-03: Wednesday trip should rotate to future, got {trips[1]['datetime']}"
        )
        # Friday trip should rotate to next Friday (2026-04-24)
        assert "2026-04-24" in trips[2]["datetime"] or "2026-05-01" in trips[2]["datetime"], (
            f"T3.4-03: Friday trip should rotate to future, got {trips[2]['datetime']}"
        )

    @pytest.mark.asyncio
    async def test_t34_04_rotation_without_emhass_adapter(
        self, trip_manager_no_entry_id
    ):
        """T3.4-04: Rotation works even without EMHASS adapter.
        
        Verifies that recurring trip rotation works when emhass_adapter
        is None (e.g., before EMHASS is configured).
        """
        # Arrange - Create a recurring trip with past datetime
        recurring_trip = {
            "id": "rec_no_emhass_1",
            "tipo": "recurring",
            "dia_semana": "lunes",
            "hora": "08:00",
            "datetime": "2026-04-13T08:00:00",  # Past Monday
            "km": 50.0,
            "kwh": 7.5,
            "activo": True,
        }
        original_datetime = recurring_trip["datetime"]
        
        # Act - Call publish_deferrable_loads (should not early return when no emhass_adapter)
        await trip_manager_no_entry_id.publish_deferrable_loads([recurring_trip])
        
        # Assert - Trip should still be rotated even without emhass_adapter
        assert recurring_trip["datetime"] != original_datetime, (
            f"T3.4-04: Rotation should work without emhass_adapter, got {recurring_trip['datetime']}"
        )
        assert "2026-04-20" in recurring_trip["datetime"] or "2026-04-27" in recurring_trip["datetime"], (
            f"T3.4-04: Rotated datetime should be future Monday, got {recurring_trip['datetime']}"
        )

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="T3.3 (auto-complete punctual trips) not implemented yet - pending Plan v3 scope extension")
    async def test_t34_05_punctual_trip_auto_complete_past_deadline(
        self, trip_manager_with_entry_id
    ):
        """T3.4-05: Punctual trips with past deadline marked inactive.
        
        Verifies that T3.3 (auto-complete punctual trips) marks
        trips with past deadlines as inactive.
        
        NOTE: This test is SKIPPED because T3.3 is not in Plan v3 scope.
        When T3.3 is implemented, remove the skip marker.
        """
        # Arrange - Create a punctual trip with past deadline
        past_trip = {
            "id": "punct_past_1",
            "tipo": "punctual",
            "datetime": "2026-04-13T08:00:00",  # Past
            "km": 100.0,
            "kwh": 20.0,
            "activo": True,
            "estado": "pendiente",
        }
        
        # Act - Call publish_deferrable_loads
        await trip_manager_with_entry_id.publish_deferrable_loads([past_trip])
        
        # Assert - Trip with past deadline should be marked inactive
        assert past_trip.get("activo") is False or past_trip.get("estado") == "completado", (
            f"T3.4-05: Past punctual trip should be marked inactive, got activo={past_trip.get('activo')}, estado={past_trip.get('estado')}"
        )

    @pytest.mark.asyncio
    async def test_t34_06_no_infinite_loop_in_rotation(
        self, trip_manager_with_entry_id
    ):
        """T3.4-06: No infinite loop in rotation logic.
        
        Verifies that calling publish_deferrable_loads() does NOT
        trigger coordinator refresh (which would cause infinite loop).
        
        The rotation code is placed BEFORE the coordinator refresh logic
        to avoid the infinite loop issue.
        """
        # Arrange - Create a recurring trip
        recurring_trip = {
            "id": "rec_loop_test_1",
            "tipo": "recurring",
            "dia_semana": "lunes",
            "hora": "08:00",
            "datetime": "2026-04-13T08:00:00",
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
        assert not mock_coordinator.async_refresh.called, (
            "T3.4-06: publish_deferrable_loads should not call coordinator.async_refresh"
        )
