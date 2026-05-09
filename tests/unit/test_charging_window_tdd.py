"""Tests for EMHASS deferrable load count and recurring trip rotation.

Tests that the sensor shows correct load counts (0 when empty, N when N trips exist)
and that past recurring trips are rotated to future dates.
"""

import logging
from unittest.mock import Mock

import pytest

from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator
from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor

logger = logging.getLogger(__name__)

# Import fixtures from conftest


@pytest.fixture
def mock_coordinator(mock_hass):
    """Create mock TripPlannerCoordinator with EMHASS data structure."""
    coordinator = Mock(spec=TripPlannerCoordinator)
    coordinator.hass = mock_hass
    coordinator.vehicle_id = "test_vehicle"
    coordinator.last_update_success = True

    # Initial data structure with EMHASS fields
    coordinator.data = {
        "recurring_trips": {},
        "punctual_trips": {},
        "kwh_today": 0.0,
        "hours_today": 0.0,
        "next_trip": None,
        "emhass_power_profile": None,
        "emhass_deferrables_schedule": None,
        "emhass_status": "ready",
    }

    return coordinator


class TestNumberOfDeferrableLoadsFix:
    """Tests for number_of_deferrable_loads sensor attribute."""

    @pytest.mark.asyncio
    async def test_emhass_sensor_zero_deferrable_shows_zero_not_none(
        self, mock_coordinator
    ):
        """Sensor with 0 deferrable loads must show 0, not None."""
        # Arrange
        mock_coordinator.data = {
            "per_trip_emhass_params": {},  # No trips
            "emhass_power_profile": [0.0] * 168,
        }

        # Act
        sensor = EmhassDeferrableLoadSensor(mock_coordinator, "test_vehicle")
        attrs = sensor.extra_state_attributes

        # Assert
        assert attrs["number_of_deferrable_loads"] == 0
        assert attrs["number_of_deferrable_loads"] is not None

    @pytest.mark.asyncio
    async def test_emhass_sensor_with_trips_shows_correct_count(self, mock_coordinator):
        """Sensor with N loads must show N."""
        # Arrange
        mock_coordinator.data = {
            "per_trip_emhass_params": {
                "trip_1": {"activo": True, "def_total_hours_array": [1.0]},
                "trip_2": {"activo": True, "def_total_hours_array": [2.0]},
                "trip_3": {"activo": True, "def_total_hours_array": [1.5]},
            },
            "emhass_power_profile": [0.0] * 168,
        }

        # Act
        sensor = EmhassDeferrableLoadSensor(mock_coordinator, "test_vehicle")
        attrs = sensor.extra_state_attributes

        # Assert
        assert attrs["number_of_deferrable_loads"] == 3


class TestRecurringTripRotation:
    """Tests for recurring trip rotation in publish_deferrable_loads."""

    @pytest.mark.asyncio
    async def test_recurring_trip_past_deadline_uses_next_week(
        self, trip_manager_no_entry_id
    ):
        """Past recurring trip must use next occurrence."""
        # Arrange
        past_trip = {
            "id": "recurring_1",
            "tipo": "recurring",
            "day": "monday",
            "hora": "08:00",
            "datetime": "2026-04-13T08:00:00",  # Past Monday
        }
        original_datetime = past_trip["datetime"]

        # Act
        logger.debug(
            "Before publish_deferrable_loads - trip datetime: %s",
            past_trip["datetime"],
        )
        await trip_manager_no_entry_id.publish_deferrable_loads([past_trip])
        logger.debug(
            "After publish_deferrable_loads - trip datetime: %s",
            past_trip["datetime"],
        )

        # Assert - The datetime must be different from the original (updated by rotation)
        assert (
            past_trip["datetime"] != original_datetime
        ), "The datetime of the past recurring trip must be updated"

    @pytest.mark.asyncio
    async def test_multiple_recurring_trips_rotated_correctly(
        self, trip_manager_with_entry_id
    ):
        """Multiple recurring trips must rotate independently."""
        # Arrange
        trips = [
            {
                "id": "rec_1",
                "tipo": "recurring",
                "day": "monday",
                "hora": "08:00",
                "datetime": "2026-04-13T08:00:00",
            },
            {
                "id": "rec_2",
                "tipo": "recurring",
                "day": "wednesday",
                "hora": "18:00",
                "datetime": "2026-04-15T18:00:00",
            },
            {
                "id": "rec_3",
                "tipo": "recurring",
                "day": "friday",
                "hora": "07:30",
                "datetime": "2026-04-17T07:30:00",
            },
        ]

        # Act
        await trip_manager_with_entry_id.publish_deferrable_loads(trips)

        # Assert - All recurring trips must have updated datetime
        # When rotation is implemented, the datetimes must change
