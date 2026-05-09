"""TDD Gap G-09.1: RED failing test for entity registry migration in async_migrate_entry.

This test documents that async_migrate_entry ONLY updates config_entry.data (e.g., battery_capacity field rename)
but does NOT migrate entity registry unique_ids from old format (without vehicle_id) to new format (with vehicle_id).

After G-09.2 implements async_migrate_entries, this test should pass.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.helpers.entity_registry import callback


class MockRegistryEntry:
    """Minimal mock entity registry entry."""

    def __init__(
        self,
        entity_id: str,
        unique_id: str,
        config_entry_id: str,
        id: str | None = None,
    ):
        self.entity_id = entity_id
        self.unique_id = unique_id
        self.config_entry_id = config_entry_id
        self.id = id or unique_id  # Default to unique_id if no internal id provided


class MockEntities:
    """Mock entities collection for entity registry."""

    def __init__(self, registry):
        self._registry = registry

    def get_entry(self, entry_id: str) -> MockRegistryEntry | None:
        """Return entry by internal id."""
        return self._registry._entities.get(entry_id)

    def get_entries_for_config_entry_id(
        self, config_entry_id: str
    ) -> list[MockRegistryEntry]:
        """Return entries for a config entry."""
        return [
            entry
            for entry in self._registry._entities.values()
            if entry.config_entry_id == config_entry_id
        ]


class MockRegistry:
    """Mock entity registry that tracks old-format unique_ids."""

    def __init__(self):
        self.entries: dict[str, MockRegistryEntry] = {}  # keyed by entity_id
        self._entities = {}  # keyed by internal id (for get_entry)
        self.entities = MockEntities(self)

    def async_get(self, hass_instance=None):
        return self

    def async_entries_for_config_entry(
        self, config_entry_id: str
    ) -> list[MockRegistryEntry]:
        """Return entries for a config entry (legacy method)."""
        return [
            entry
            for entry in self._entities.values()
            if entry.config_entry_id == config_entry_id
        ]

    def async_get_or_create(self, *args, **kwargs):
        unique_id = kwargs.get("unique_id", "")
        entity_id = kwargs.get("suggested_object_id", "unknown")
        config_entry_id = kwargs.get("config_entry", "")
        # Generate a unique internal id based on entity_id
        internal_id = f"{config_entry_id}_{entity_id}"
        entry = MockRegistryEntry(
            f"sensor.{entity_id}", unique_id, config_entry_id, id=internal_id
        )
        self.entries[f"sensor.{entity_id}"] = entry
        self._entities[internal_id] = entry
        return entry

    @callback
    def async_update_entity(self, entity_id: str, **kwargs) -> None:
        """Update an entity entry."""
        if entity_id in self.entries:
            entry = self.entries[entity_id]
            if "new_unique_id" in kwargs:
                entry.unique_id = kwargs["new_unique_id"]


class FakeRuntimeData:
    """Minimal runtime data."""

    def __init__(self):
        self.trip_manager = MagicMock()
        self.coordinator = MagicMock()
        self.sensor_async_add_entities = None


class FakeConfigEntry:
    """Minimal ConfigEntry substitute for testing migration."""

    def __init__(
        self,
        entry_id: str,
        data: dict[str, Any],
        version: int,
        minor_version: int,
    ):
        self.entry_id = entry_id
        self.data = data
        self.version = version
        self.minor_version = minor_version
        self.runtime_data = FakeRuntimeData()

    @property
    def unique_id(self) -> str:
        return self.entry_id


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant."""
    hass = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_registry(mock_hass):
    """Create and register a mock entity registry."""
    registry = MockRegistry()
    mock_hass.data["entity_registry"] = registry
    return registry


@pytest.mark.asyncio
async def test_migrate_entry_version2_entity_registry(mock_hass, mock_registry):
    """Test that async_migrate_entry migrates old-format entity unique_ids.

    OLD format (version 1): unique_id = "ev_trip_planner_{description_key}"
    e.g., "ev_trip_planner_kwh_today" (no vehicle_id)

    NEW format (version 2): unique_id = "ev_trip_planner_{vehicle_id}_{description_key}"
    e.g., "ev_trip_planner_chispi_kwh_today" (with vehicle_id)

    The vehicle_id comes from entry.data["vehicle_name"].

    This test FAILS today because async_migrate_entry only renames battery_capacity -> battery_capacity_kwh
    in config_entry.data, but does NOT call async_migrate_entries to update entity registry unique_ids.
    """
    from custom_components.ev_trip_planner import async_migrate_entry
    from custom_components.ev_trip_planner.const import DOMAIN

    # Create a version 1 config entry with old format unique_ids in the registry
    entry = FakeConfigEntry(
        entry_id="test_migrate_001",
        data={
            "vehicle_name": "chispi",  # vehicle_id extracted from data
            "battery_capacity": 50.0,  # Old field name (to be migrated)
        },
        version=1,  # Old version (will migrate to 2)
        minor_version=1,
    )

    # Pre-populate entity registry with OLD-format entities (no vehicle_id in unique_id)
    old_unique_ids = [
        f"{DOMAIN}_kwh_today",
        f"{DOMAIN}_hours_today",
        f"{DOMAIN}_recurring_trips_count",
    ]

    for unique_id in old_unique_ids:
        mock_registry.async_get_or_create(
            config_entry=entry.entry_id,
            unique_id=unique_id,
            suggested_object_id=unique_id.replace(f"{DOMAIN}_", ""),
        )

    # Verify pre-condition: entities have OLD format unique_ids
    registered = mock_registry.async_entries_for_config_entry(entry.entry_id)
    assert len(registered) == 3
    for entity in registered:
        assert (
            entity.unique_id in old_unique_ids
        ), f"Expected old format, got {entity.unique_id}"

    # Migrate
    await async_migrate_entry(mock_hass, entry)

    # Verify: entity unique_ids should be migrated to NEW format (with vehicle_id)
    migrated = mock_registry.async_entries_for_config_entry(entry.entry_id)
    assert len(migrated) == 3

    for entity in migrated:
        # New format includes vehicle_id: "ev_trip_planner_chispi_kwh_today"
        assert f"{DOMAIN}_chispi_" in entity.unique_id, (
            f"Migration FAILED: expected unique_id with vehicle_id 'chispi', "
            f"got '{entity.unique_id}' — async_migrate_entry did NOT call "
            f"async_migrate_entries to update entity registry"
        )
        # Verify no old-format unique_ids remain
        for old_uid in old_unique_ids:
            assert (
                entity.unique_id != old_uid
            ), f"Migration FAILED: old unique_id '{old_uid}' still exists as '{entity.unique_id}'"
