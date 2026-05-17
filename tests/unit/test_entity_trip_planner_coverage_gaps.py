"""Tests for uncovered entity_trip_planner.py paths (lines 66-72)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.sensor.entity_trip_planner import TripPlannerSensor


class TestAsyncAddedToHass:
    """Test async_added_to_hass restore branch (lines 66-72)."""

    @pytest.mark.asyncio
    async def test_async_added_to_hass_restores_state_when_restore_true_and_data_none(
        self,
    ):
        """Lines 67-72: restore=True + coordinator.data=None → restore from last_state."""
        coordinator = MagicMock()
        coordinator.data = None  # No data yet

        entity_desc = MagicMock()
        entity_desc.restore = True  # This sensor restores state
        entity_desc.key = "test_sensor"
        entity_desc.value_fn = lambda d: None
        entity_desc.attrs_fn = lambda d: {}

        sensor = TripPlannerSensor(coordinator, "test_vehicle", entity_desc)

        # Mock last_state that was saved from previous run
        last_state = MagicMock()
        last_state.state = "restored_value"
        sensor.async_get_last_state = AsyncMock(return_value=last_state)

        await sensor.async_added_to_hass()

        # Verify state was restored
        assert sensor._attr_native_value == "restored_value"

    @pytest.mark.asyncio
    async def test_async_added_to_hass_skips_restore_when_restore_false(self):
        """Line 67: restore=False → does NOT restore, even if last_state exists."""
        coordinator = MagicMock()
        coordinator.data = None

        entity_desc = MagicMock()
        entity_desc.restore = False  # Don't restore
        entity_desc.key = "test_sensor"
        entity_desc.value_fn = lambda d: None
        entity_desc.attrs_fn = lambda d: {}

        sensor = TripPlannerSensor(coordinator, "test_vehicle", entity_desc)

        last_state = MagicMock()
        last_state.state = "should_not_restore"
        sensor.async_get_last_state = AsyncMock(return_value=last_state)

        await sensor.async_added_to_hass()

        # Value should NOT be set (restore=False)
        assert not hasattr(sensor, "_attr_native_value") or sensor._attr_native_value is None

    @pytest.mark.asyncio
    async def test_async_added_to_hass_skips_restore_when_coordinator_has_data(self):
        """Line 68: restore=True but coordinator.data is not None → no restore."""
        coordinator = MagicMock()
        coordinator.data = {"some": "data"}  # Data exists, no need to restore

        entity_desc = MagicMock()
        entity_desc.restore = True
        entity_desc.key = "test_sensor"
        entity_desc.value_fn = lambda d: None
        entity_desc.attrs_fn = lambda d: {}

        sensor = TripPlannerSensor(coordinator, "test_vehicle", entity_desc)

        last_state = MagicMock()
        last_state.state = "should_not_restore"
        sensor.async_get_last_state = AsyncMock(return_value=last_state)

        await sensor.async_added_to_hass()

        # Value should NOT be overwritten since coordinator has data
        assert not hasattr(sensor, "_attr_native_value") or sensor._attr_native_value is None

    @pytest.mark.asyncio
    async def test_async_added_to_hass_skips_when_no_last_state(self):
        """Line 70-72: last_state is None → no restore."""
        coordinator = MagicMock()
        coordinator.data = None

        entity_desc = MagicMock()
        entity_desc.restore = True
        entity_desc.key = "test_sensor"
        entity_desc.value_fn = lambda d: None
        entity_desc.attrs_fn = lambda d: {}

        sensor = TripPlannerSensor(coordinator, "test_vehicle", entity_desc)

        sensor.async_get_last_state = AsyncMock(return_value=None)

        await sensor.async_added_to_hass()

        # Value should NOT be set since last_state is None
        assert not hasattr(sensor, "_attr_native_value") or sensor._attr_native_value is None