"""Tests for EMHASS soft delete index stability."""

import pytest
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from unittest.mock import patch

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.const import (
    CONF_VEHICLE_NAME,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_CHARGING_POWER,
    CONF_INDEX_COOLDOWN_HOURS,
)


@pytest.mark.asyncio
async def test_released_index_not_immediately_available(
    hass: HomeAssistant, mock_store
):
    """Verify released index goes to _released_indices, not back to _available_indices."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Assign an index to a trip
        index = await adapter.async_assign_index_to_trip("trip_001")
        assert index == 0
        assert 0 not in adapter._available_indices

        # Release the index
        await adapter.async_release_trip_index("trip_001")

        # Verify index is NOT in available_indices (soft delete)
        assert 0 not in adapter._available_indices

        # Verify index is in _released_indices with timestamp
        assert 0 in adapter._released_indices
        assert isinstance(adapter._released_indices[0], datetime)


@pytest.mark.asyncio
async def test_released_index_available_after_cooldown(hass: HomeAssistant, mock_store):
    """Verify index moves from _released_indices to _available_indices after cooldown expires."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_INDEX_COOLDOWN_HOURS: 1,  # 1 hour cooldown for faster test
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Assign and release an index
        index = await adapter.async_assign_index_to_trip("trip_001")
        assert index == 0
        await adapter.async_release_trip_index("trip_001")

        # Verify index is in released_indices
        assert 0 in adapter._released_indices
        assert 0 not in adapter._available_indices

        # Verify get_available_indices() does NOT return it yet (cooldown not expired)
        available = adapter.get_available_indices()
        assert 0 not in available

        # Simulate time passing: manually set release time to 2 hours ago
        adapter._released_indices[0] = datetime.now() - timedelta(hours=2)

        # Now get_available_indices() should return the expired index
        available = adapter.get_available_indices()
        assert 0 in available

        # Verify index is no longer in released_indices
        assert 0 not in adapter._released_indices


@pytest.mark.asyncio
async def test_new_trip_gets_next_available_index(hass: HomeAssistant, mock_store):
    """Verify new trips don't reuse released indices still in cooldown."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 10,
        CONF_CHARGING_POWER: 7.4,
        CONF_INDEX_COOLDOWN_HOURS: 24,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Assign indices to three trips
        idx1 = await adapter.async_assign_index_to_trip("trip_001")
        idx2 = await adapter.async_assign_index_to_trip("trip_002")
        idx3 = await adapter.async_assign_index_to_trip("trip_003")

        assert idx1 == 0
        assert idx2 == 1
        assert idx3 == 2

        # Release trip_002 (index 1)
        await adapter.async_release_trip_index("trip_002")

        # Verify index 1 is in released_indices
        assert 1 in adapter._released_indices
        assert 1 not in adapter._available_indices

        # Assign a new trip - should get index 3, NOT 1 (still in cooldown)
        new_idx = await adapter.async_assign_index_to_trip("trip_004")
        assert new_idx == 3, (
            "New trip should get next available index, not recently released one"
        )

        # Verify index 1 is still in released_indices
        assert 1 in adapter._released_indices


@pytest.mark.asyncio
async def test_multiple_indices_released_cooldown_handled_correctly(
    hass: HomeAssistant, mock_store
):
    """Verify independent cooldown timers for multiple released indices."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
        CONF_INDEX_COOLDOWN_HOURS: 1,  # 1 hour cooldown
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, config)
        await adapter.async_load()

        # Assign and release multiple indices
        idx1 = await adapter.async_assign_index_to_trip("trip_001")
        idx2 = await adapter.async_assign_index_to_trip("trip_002")
        idx3 = await adapter.async_assign_index_to_trip("trip_003")

        # Release all three
        await adapter.async_release_trip_index("trip_001")
        await adapter.async_release_trip_index("trip_002")
        await adapter.async_release_trip_index("trip_003")

        # All three should be in released_indices
        assert idx1 in adapter._released_indices
        assert idx2 in adapter._released_indices
        assert idx3 in adapter._released_indices

        # Simulate idx1's cooldown expiring (2 hours ago)
        adapter._released_indices[idx1] = datetime.now() - timedelta(hours=2)

        # Call get_available_indices() - only idx1 should be reclaimed
        available = adapter.get_available_indices()
        assert idx1 in available, "idx1 cooldown expired, should be available"
        assert idx2 not in available, "idx2 still in cooldown"
        assert idx3 not in available, "idx3 still in cooldown"

        # Now simulate idx2's cooldown expiring
        adapter._released_indices[idx2] = datetime.now() - timedelta(hours=2)

        # Both idx1 and idx2 should be available now
        available = adapter.get_available_indices()
        assert idx1 in available
        assert idx2 in available, "idx2 cooldown expired, should be available"
        assert idx3 not in available, "idx3 still in cooldown"

        # Simulate idx3's cooldown expiring
        adapter._released_indices[idx3] = datetime.now() - timedelta(hours=2)

        # All should be available now
        available = adapter.get_available_indices()
        assert idx1 in available
        assert idx2 in available
        assert idx3 in available, "idx3 cooldown expired, should be available"
