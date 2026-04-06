"""TDD Phase 0: Characterization tests for entity registry unique_id.

These tests document the BROKEN behavior that will be fixed in later phases.
Today they FAIL because sensors do not have unique_id set in the entity registry.

After all phases complete, these tests should PASS.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er


class FakeEntry:
    """Minimal ConfigEntry substitute for testing."""

    def __init__(self, entry_id: str, data: dict[str, Any]) -> None:
        self.entry_id = entry_id
        self.data = data
        self.version = 1
        self.minor_version = 1

    @property
    def unique_id(self) -> str:
        return self.entry_id


@pytest.fixture
def config_entry():
    """Create a test ConfigEntry."""
    return FakeEntry(
        entry_id="test_entry_001",
        data={
            "vehicle_name": "Chispitas",
        },
    )


@pytest.fixture
def mock_hass(config_entry):
    """Create a mock HomeAssistant with entity registry."""
    from custom_components.ev_trip_planner.const import DOMAIN

    hass = MagicMock()

    # Track registered entities - this is what should be cleared on unload
    registered_entities: dict[str, dict] = {}

    class MockRegistry:
        """Mock entity registry that tracks entities."""

        def __init__(self):
            self.entries = {}

        def async_get(self, hass_instance=None):
            return self

        def async_get_or_create(self, *args, **kwargs):
            # Create a mock entry and store it
            suggested_object_id = kwargs.get('suggested_object_id', 'unknown')
            unique_id = kwargs.get('unique_id', '')
            entity_id = f"sensor.{suggested_object_id}"
            entry = MockRegistryEntry(entity_id, unique_id, config_entry.entry_id)
            self.entries[entity_id] = entry
            return entry

        def async_entries_for_config_entry(self, entry_id):
            return [e for e in self.entries.values() if e.config_entry_id == entry_id]

        def async_remove(self, entity_id):
            if entity_id in self.entries:
                del self.entries[entity_id]

    class MockRegistryEntry:
        def __init__(self, entity_id, unique_id, config_entry_id):
            self.entity_id = entity_id
            self.unique_id = unique_id
            self.config_entry_id = config_entry_id

    # Create mock registry
    mock_registry = MockRegistry()
    hass.entity_registry = mock_registry

    # Mock hass.data for runtime storage
    tm = MagicMock()
    tm.async_get_recurring_trips = AsyncMock(return_value=[])
    tm.async_get_punctual_trips = AsyncMock(return_value=[])
    tm.async_delete_all_trips = AsyncMock()
    tm._recurring_trips = []
    tm._punctual_trips = []

    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.trip_manager = tm
    coordinator.async_config_entry_first_refresh = AsyncMock()

    namespace = f"{DOMAIN}_{config_entry.entry_id}"
    hass.data = {
        f"{DOMAIN}_runtime_data": {
            namespace: {
                "trip_manager": tm,
                "coordinator": coordinator,
                "config": config_entry.data,
            }
        }
    }

    # Make async_unload_entry work
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_entries = MagicMock(return_value=[config_entry])

    return hass


@pytest.mark.asyncio
async def test_sensor_unique_id_exists_after_setup(mock_hass, config_entry):
    """Test that all sensors have unique_id set after async_setup_entry.

    This test FAILS today because the current sensor classes do NOT set unique_id.
    Only EmhassDeferrableLoadSensor has unique_id hardcoded.

    After Phase 1-5 refactoring, sensors should get unique_id like:
      _attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}"
    """
    from custom_components.ev_trip_planner.sensor import async_setup_entry

    created_entities = []

    def capture_async_add_entities(entities, update_before_add=True):
        created_entities.extend(entities)

    # Run the actual async_setup_entry
    result = await async_setup_entry(mock_hass, config_entry, capture_async_add_entities)
    assert result is True, "async_setup_entry should succeed"

    # At least 8 sensors should be created (7 TripPlanner + 1 EMHASS)
    assert len(created_entities) >= 8, (
        f"Expected >= 8 sensors, got {len(created_entities)}: "
        f"{[(type(e).__name__, getattr(e, '_attr_unique_id', 'NO_UNIQUE_ID')) for e in created_entities]}"
    )

    # Check each entity has a unique_id set
    missing_unique_id = []
    for entity in created_entities:
        uid = getattr(entity, "_attr_unique_id", None)
        if uid is None:
            missing_unique_id.append(type(entity).__name__)

    assert not missing_unique_id, (
        f"The following sensor types lack unique_id: {missing_unique_id}. "
        f"All sensors must have _attr_unique_id set."
    )

    # Verify the entity registry also has entries with unique_id
    registry = mock_hass.entity_registry
    entries = registry.async_entries_for_config_entry(config_entry.entry_id)

    # At least 8 registry entries should exist
    assert len(entries) >= 8, (
        f"Expected >= 8 registry entries, got {len(entries)}"
    )

    # Every registry entry must have a unique_id
    registry_missing_uid = []
    for entry in entries:
        if entry.unique_id is None:
            registry_missing_uid.append(entry.entity_id)

    assert not registry_missing_uid, (
        f"The following registry entries lack unique_id: {registry_missing_uid}"
    )


@pytest.mark.asyncio
async def test_sensor_removed_after_unload(mock_hass, config_entry):
    """Test that all sensors are removed from entity registry after async_unload_entry.

    This test FAILS today because async_unload_entry does NOT clean up the entity
    registry. Sensors become orphaned zombies - they remain in the registry after
    the entry is unloaded.

    After Phase 2 fix, the entity registry should have 0 entries for this config
    entry after unload.
    """
    from custom_components.ev_trip_planner import async_unload_entry
    from custom_components.ev_trip_planner.const import DOMAIN

    # Manually register 8 sensors in the entity registry before the test
    # (simulating what async_setup_entry does)
    registry = mock_hass.entity_registry
    for i in range(8):
        entity_id = f"sensor.test_entity_{i}"
        registry.async_get_or_create(
            domain="sensor",
            platform="ev_trip_planner",
            unique_id=f"test_unique_id_{i}",
            suggested_object_id=f"test_entity_{i}",
            config_entry=config_entry,
        )

    # Verify 8 entities are registered before unload
    entries_before = registry.async_entries_for_config_entry(config_entry.entry_id)
    assert len(entries_before) == 8, (
        f"Expected 8 sensors registered before unload, got {len(entries_before)}"
    )

    # Now unload the entry via the integration's unload function
    unload_ok = await async_unload_entry(mock_hass, config_entry)
    assert unload_ok is True, "async_unload_entry should succeed"

    # Get entries for this config entry AFTER unload
    entries_after = registry.async_entries_for_config_entry(config_entry.entry_id)

    # This FAILS: orphaned sensors remain in the registry after unload
    # because async_unload_entry does NOT call entity_registry.async_clear_config_entry()
    assert len(entries_after) == 0, (
        f"Expected 0 registry entries after unload, but found {len(entries_after)} "
        f"orphaned sensors still in registry. Sensors should be cleaned up during unload."
    )
