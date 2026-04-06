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
    hass = MagicMock()

    # Mock the entity registry
    registry_entries: list = []
    registry = MagicMock()
    registry_entries_for_config_entry = []

    def async_entries_for_config_entry(entry_id):
        return [e for e in registry_entries if e.config_entry_id == entry_id]

    registry.async_entries_for_config_entry = async_entries_for_config_entry
    registry.async_get = MagicMock(return_value=registry)
    registry.entries = {}

    def mock_async_get(hass_instance):
        return registry

    # Patch entity_registry.async_get at module level
    hass.entity_registry = MagicMock()
    hass.entity_registry.async_get = mock_async_get
    hass.entity_registry.async_entries_for_config_entry = async_entries_for_config_entry
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[config_entry])

    # Seed trip_manager and coordinator in hass.data
    tm = MagicMock()
    tm.async_get_recurring_trips = AsyncMock(return_value=[])
    tm.async_get_punctual_trips = AsyncMock(return_value=[])
    tm._recurring_trips = []
    tm._punctual_trips = []

    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.trip_manager = tm
    coordinator.async_config_entry_first_refresh = AsyncMock()

    # Mirror the namespace pattern used in __init__.py: f"{DOMAIN}_{entry_id}"
    from custom_components.ev_trip_planner.const import DOMAIN

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
    registry = er.async_get(mock_hass)
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
