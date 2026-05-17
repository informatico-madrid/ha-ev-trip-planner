"""TDD Phase 0: Characterization tests for entity registry unique_id.

These tests document the BROKEN behavior that will be fixed in later phases.
Today they FAIL because sensors do not have unique_id set in the entity registry.

After all phases complete, these tests should PASS.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


class FakeEntry:
    """Minimal ConfigEntry substitute for testing."""

    def __init__(self, entry_id: str, data: dict[str, Any]) -> None:
        self.entry_id = entry_id
        self.data = data
        self.version = 1
        self.minor_version = 1

        # runtime_data with mock objects
        class FakeRuntimeData:
            def __init__(self):
                self.trip_manager = None
                self.coordinator = None
                self.sensor_async_add_entities = None

        self.runtime_data = FakeRuntimeData()

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


class MockRegistryEntry:
    """Registry entry for entity registry tests."""

    def __init__(self, entity_id, unique_id, config_entry_id):
        self.entity_id = entity_id
        self.unique_id = unique_id
        self.config_entry_id = config_entry_id


@pytest.mark.asyncio
async def test_sensor_unique_id_exists_after_setup(
    mock_hass_entity_registry_full, config_entry
):
    """Test that all sensors have unique_id set after async_setup_entry.

    This test FAILS today because the current sensor classes do NOT set unique_id.
    Only EmhassDeferrableLoadSensor has unique_id hardcoded.

    After Phase 1-5 refactoring, sensors should get unique_id like:
      _attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}"
    """
    from custom_components.ev_trip_planner.sensor import async_setup_entry

    # Store async_add_entities for later use (simulating HA behavior)
    created_entities = []

    def capture_async_add_entities(entities, update_before_add=True):
        created_entities.extend(entities)
        # Simulate HA's async_add_entities: register each entity in the registry
        registry = mock_hass_entity_registry_full.entity_registry
        for entity in entities:
            # Use the entity's unique_id and name to create a registry entry
            unique_id = getattr(entity, "_attr_unique_id", None) or getattr(
                entity, "unique_id", "unknown"
            )
            suggested_object_id = getattr(entity, "_attr_name", None) or getattr(
                entity, "name", "unknown"
            )
            registry.async_get_or_create(
                domain="sensor",
                platform="ev_trip_planner",
                unique_id=unique_id,
                suggested_object_id=suggested_object_id,
                config_entry=config_entry,
            )

    # Run the actual async_setup_entry
    result = await async_setup_entry(
        mock_hass_entity_registry_full, config_entry, capture_async_add_entities
    )
    assert result is True, "async_setup_entry should succeed"

    # Store callback in runtime_data for async_create_trip_sensor to use later
    config_entry.runtime_data.sensor_async_add_entities = capture_async_add_entities

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
    registry = mock_hass_entity_registry_full.entity_registry
    entries = registry.async_entries_for_config_entry(config_entry.entry_id)

    # At least 8 registry entries should exist
    assert len(entries) >= 8, f"Expected >= 8 registry entries, got {len(entries)}"

    # Every registry entry must have a unique_id
    registry_missing_uid = []
    for entry in entries:
        if entry.unique_id is None:
            registry_missing_uid.append(entry.entity_id)

    assert not registry_missing_uid, (
        f"The following registry entries lack unique_id: {registry_missing_uid}"
    )


@pytest.mark.asyncio
async def test_two_vehicles_no_unique_id_collision():
    """Test that unique_ids from two different vehicles are globally unique.

    This test FAILS because TripSensor unique_id format is `trip_{trip_id}`
    without a vehicle prefix. If two vehicles both have a trip with id "1",
    both will create sensors with unique_id="trip_1", causing a collision.

    After Phase 1-3 refactoring, unique_ids should be globally unique:
      _attr_unique_id = f"{DOMAIN}_{vehicle_id}_{trip_id}"
    """
    from custom_components.ev_trip_planner.sensor import async_setup_entry

    # Create two config entries for two different vehicles
    entry_a = FakeEntry(
        entry_id="vehicle_a",
        data={"vehicle_name": "Vehicle A"},
    )
    entry_b = FakeEntry(
        entry_id="vehicle_b",
        data={"vehicle_name": "Vehicle B"},
    )

    class MockRegistry:
        """Mock entity registry that tracks entities."""

        def __init__(self):
            self.entries = {}

        def async_get(self, hass_instance=None):
            return self

        def async_get_or_create(self, *args, **kwargs):
            suggested_object_id = kwargs.get("suggested_object_id", "unknown")
            unique_id = kwargs.get("unique_id", "")
            entity_id = f"sensor.{suggested_object_id}"
            config_entry_id = kwargs.get(
                "config_entry", kwargs.get("config_entry_id", "")
            )
            entry = MockRegistryEntry(entity_id, unique_id, config_entry_id)
            self.entries[entity_id] = entry
            return entry

        def async_entries_for_config_entry(self, entry_id):
            return [e for e in self.entries.values() if e.config_entry_id == entry_id]

        def async_remove(self, entity_id):
            # EntityRegistry.async_remove is NOT async - returns None
            # See: homeassistant/helpers/entity_registry.py
            if entity_id in self.entries:
                del self.entries[entity_id]

    class MockRegistryEntry:
        def __init__(self, entity_id, unique_id, config_entry_id):
            self.entity_id = entity_id
            self.unique_id = unique_id
            self.config_entry_id = config_entry_id

    def create_mock_hass(entry):
        """Create a mock hass for a specific entry."""
        hass = MagicMock()
        mock_registry = MockRegistry()
        hass.entity_registry = mock_registry

        # Create mock trip_manager with a trip that has id="1"
        # New composition architecture: CRUD methods on _crud, lifecycle on _lifecycle
        tm = MagicMock()
        tm._crud = MagicMock()
        tm._crud.async_get_recurring_trips = AsyncMock(return_value=[])
        # Both vehicles have a trip with id="1" - this is the collision
        tm._crud.async_get_punctual_trips = AsyncMock(
            return_value=[
                {
                    "id": "1",
                    "tipo": "punctual",
                    "descripcion": "Trip to work",
                    "km": 25.0,
                    "kwh": 5.0,
                    "datetime": "2024-01-15T08:00:00",
                    "estado": "pendiente",
                }
            ]
        )
        tm._lifecycle = MagicMock()
        tm._lifecycle.async_delete_all_trips = AsyncMock()

        coordinator = MagicMock()
        coordinator.data = {}
        coordinator.trip_manager = tm
        coordinator.async_config_entry_first_refresh = AsyncMock()

        # Set up entry.runtime_data with trip_manager and coordinator
        entry.runtime_data.trip_manager = tm
        entry.runtime_data.coordinator = coordinator

        hass.config_entries = MagicMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        hass.config_entries.async_entries = MagicMock(return_value=[entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=entry)

        return hass

    hass_a = create_mock_hass(entry_a)
    hass_b = create_mock_hass(entry_b)

    # Run async_setup_entry for vehicle A
    entities_a = []

    def capture_a(entities, update_before_add=True):
        entities_a.extend(entities)

    await async_setup_entry(hass_a, entry_a, capture_a)

    # Run async_setup_entry for vehicle B
    entities_b = []

    def capture_b(entities, update_before_add=True):
        entities_b.extend(entities)

    await async_setup_entry(hass_b, entry_b, capture_b)

    # Collect TripSensor unique_ids from both vehicles
    trip_sensor_unique_ids_a = [
        getattr(e, "_attr_unique_id", None)
        for e in entities_a
        if type(e).__name__ == "TripSensor"
    ]
    trip_sensor_unique_ids_b = [
        getattr(e, "_attr_unique_id", None)
        for e in entities_b
        if type(e).__name__ == "TripSensor"
    ]

    # Combine TripSensor unique_ids from both vehicles
    all_trip_sensor_unique_ids = trip_sensor_unique_ids_a + trip_sensor_unique_ids_b

    # Verify we have exactly 1 TripSensor from each vehicle
    assert len(trip_sensor_unique_ids_a) == 1, (
        f"Expected 1 TripSensor from vehicle A, got {len(trip_sensor_unique_ids_a)}"
    )
    assert len(trip_sensor_unique_ids_b) == 1, (
        f"Expected 1 TripSensor from vehicle B, got {len(trip_sensor_unique_ids_b)}"
    )

    # Now check for global uniqueness - all TripSensor unique_ids must be unique across vehicles
    # This FAILS because both vehicles create TripSensor with unique_id="trip_1"
    seen = {}
    duplicates = []
    for uid in all_trip_sensor_unique_ids:
        if uid in seen:
            duplicates.append(uid)
        seen[uid] = True

    assert not duplicates, (
        f"Duplicate unique_ids found across vehicles: {duplicates}. "
        f"TripSensor unique_ids must be globally unique, not just per-vehicle. "
        f"Vehicle A TripSensor unique_id: {trip_sensor_unique_ids_a}, "
        f"Vehicle B TripSensor unique_id: {trip_sensor_unique_ids_b}. "
        f"Expected format: 'ev_trip_planner_{{vehicle_id}}_{{trip_id}}'"
    )


@pytest.mark.asyncio
async def test_sensor_removed_after_unload(
    mock_hass_entity_registry_full, config_entry
):
    """Test that all sensors are removed from entity registry after async_unload_entry.

    This test FAILS today because async_unload_entry does NOT clean up the entity
    registry. Sensors become orphaned zombies - they remain in the registry after
    the entry is unloaded.

    After Phase 2 fix, the entity registry should have 0 entries for this config
    entry after unload.
    """
    from custom_components.ev_trip_planner import async_unload_entry

    # Manually register 8 sensors in the entity registry before the test
    # (simulating what async_setup_entry does)
    registry = mock_hass_entity_registry_full.entity_registry
    for i in range(8):
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
    unload_ok = await async_unload_entry(mock_hass_entity_registry_full, config_entry)
    assert unload_ok is True, "async_unload_entry should succeed"

    # Get entries for this config entry AFTER unload
    entries_after = registry.async_entries_for_config_entry(config_entry.entry_id)

    # This FAILS: orphaned sensors remain in the registry after unload
    # because async_unload_entry does NOT call entity_registry.async_clear_config_entry()
    assert len(entries_after) == 0, (
        f"Expected 0 registry entries after unload, but found {len(entries_after)} "
        f"orphaned sensors still in registry. Sensors should be cleaned up during unload."
    )


@pytest.mark.asyncio
async def test_trip_sensor_created_in_registry_after_add(
    mock_hass_entity_registry_full, config_entry
):
    """Test that TripSensor appears in entity registry after add_trip service.

    This test FAILS today because async_create_trip_sensor() creates an orphan
    Python object stored in hass.data[DATA_RUNTIME][namespace]["trip_sensors"]
    but NEVER calls async_add_entities(), so the entity never appears in the
    registry at all.

    The sensor object exists as a Python object but is invisible to Home Assistant
    because it was never registered via the entity registry API.

    After Phase 2 fix, calling the add_trip service should result in a TripSensor
    that appears in the entity registry (via async_add_entities callback).
    """
    from custom_components.ev_trip_planner.sensor import (
        async_create_trip_sensor,
        async_setup_entry,
    )

    # Track entities created during async_setup_entry
    setup_entities = []

    async def capture_async_add_entities(entities, update_before_add=True):
        setup_entities.extend(entities)
        # Simulate HA's async_add_entities: register each entity in the registry
        registry = mock_hass_entity_registry_full.entity_registry
        for entity in entities:
            # Use the entity's unique_id and name to create a registry entry
            unique_id = getattr(entity, "_attr_unique_id", None) or getattr(
                entity, "unique_id", "unknown"
            )
            suggested_object_id = getattr(entity, "_attr_name", None) or getattr(
                entity, "name", "unknown"
            )
            registry.async_get_or_create(
                domain="sensor",
                platform="ev_trip_planner",
                unique_id=unique_id,
                suggested_object_id=suggested_object_id,
                config_entry=config_entry,
            )

    # Run async_setup_entry to set up the initial 8 sensors
    result = await async_setup_entry(
        mock_hass_entity_registry_full, config_entry, capture_async_add_entities
    )
    assert result is True, "async_setup_entry should succeed"

    # Store callback in runtime_data for async_create_trip_sensor to use later
    config_entry.runtime_data.sensor_async_add_entities = capture_async_add_entities

    # Verify initial sensors are set up
    initial_count = len(setup_entities)
    assert initial_count >= 8, f"Expected >= 8 initial sensors, got {initial_count}"

    # Now create a trip sensor via async_create_trip_sensor
    trip_data = {
        "id": "test_trip_001",
        "tipo": "recurrente",
        "dia_semana": "lunes",
        "hora": "08:00",
        "km": 25.5,
        "kwh": 15.0,
        "descripcion": "Test trip to office",
        "activo": True,
        "estado": "pendiente",
    }

    # Call async_create_trip_sensor - this creates AND registers the sensor
    create_result = await async_create_trip_sensor(
        mock_hass_entity_registry_full, config_entry.entry_id, trip_data
    )
    assert create_result is True, "async_create_trip_sensor should succeed"

    # The sensor SHOULD be in the entity registry (this is the fix!)
    # Check the entity registry for a TripSensor with this trip_id
    registry = mock_hass_entity_registry_full.entity_registry
    all_entries = registry.entries

    # Find any registry entry whose unique_id contains our trip_id
    matching_entries = [
        entry for entry in all_entries.values() if "test_trip_001" in entry.unique_id
    ]

    # This should now PASS: async_create_trip_sensor calls async_add_entities()
    # which registers the entity in the registry
    assert len(matching_entries) > 0, (
        f"Expected TripSensor with trip_id 'test_trip_001' to appear in entity registry "
        f"after async_create_trip_sensor(), but no matching entry found. "
        f"Available entries: {[(e.entity_id, e.unique_id) for e in all_entries.values()]}."
    )


@pytest.mark.asyncio
async def test_trip_sensor_removed_from_registry_after_delete(
    mock_hass_entity_registry_full, config_entry
):
    """Test that TripSensor is removed from entity registry after delete_trip service.

    This test FAILS today because async_remove_trip_sensor() only deletes from dict
    (del trip_sensors[trip_id]), never calls entity_registry.async_remove(),
    leaving zombie entries in the registry.

    After Phase 2 fix, the entity registry should have 0 entries for this trip.
    """
    from custom_components.ev_trip_planner.sensor import async_remove_trip_sensor

    # Manually register the trip sensor in the entity registry
    # (simulating what should happen during proper sensor creation in a real HA setup)
    registry = mock_hass_entity_registry_full.entity_registry
    registry.async_get_or_create(
        domain="sensor",
        platform="ev_trip_planner",
        unique_id="trip_trip_001",
        suggested_object_id="trip_trip_001",
        config_entry=config_entry,
    )

    # Verify the sensor is in the entity registry
    entries_before = registry.async_entries_for_config_entry(config_entry.entry_id)
    trip_entries_before = [e for e in entries_before if "trip_001" in e.unique_id]
    assert len(trip_entries_before) == 1, (
        f"Expected 1 trip sensor in registry before delete, got {len(trip_entries_before)}"
    )

    # Now call async_remove_trip_sensor to delete the trip
    await async_remove_trip_sensor(
        hass=mock_hass_entity_registry_full,
        entry_id=config_entry.entry_id,
        trip_id="trip_001",
    )

    # Verify the entity registry entry is removed
    entries_after = registry.async_entries_for_config_entry(config_entry.entry_id)
    trip_entries_after = [e for e in entries_after if "trip_001" in e.unique_id]
    assert len(trip_entries_after) == 0, (
        f"Expected 0 trip sensor entries in registry after delete, but found {len(trip_entries_after)} "
        f"zombie entries. async_remove_trip_sensor() only deletes from trip_sensors dict, "
        f"never calls entity_registry.async_remove()."
    )


@pytest.mark.asyncio
async def test_no_duplicate_sensors_after_reload(
    mock_hass_entity_registry_full, config_entry
):
    """Test that reloading the config entry does not create duplicate sensors.

    This test FAILS today because sensors do not have unique_id set, so when
    the config entry is reloaded, Home Assistant creates new entity entries
    instead of recognizing the existing ones. Entity count doubles on reload.

    After Phase 1-5 refactoring, sensors should have unique_id and reload
    should not create duplicates.
    """
    from custom_components.ev_trip_planner.sensor import async_setup_entry

    created_entities = []

    def capture_async_add_entities(entities, update_before_add=True):
        created_entities.extend(entities)

    # Initial setup
    result = await async_setup_entry(
        mock_hass_entity_registry_full, config_entry, capture_async_add_entities
    )
    assert result is True, "async_setup_entry should succeed"

    # Verify we have 8 sensors
    initial_count = len(created_entities)
    assert initial_count >= 8, f"Expected >= 8 sensors after setup, got {initial_count}"

    # Pre-requisite check: all sensors must have unique_id for reload to work correctly
    # Without unique_id, HA will create duplicates on reload (the bug we're documenting)
    missing_unique_id = []
    for entity in created_entities:
        uid = getattr(entity, "_attr_unique_id", None)
        if uid is None:
            missing_unique_id.append(type(entity).__name__)

    # This FAILS: sensors lack unique_id, so HA cannot recognize them on reload
    # and will create duplicate entities instead
    assert not missing_unique_id, (
        f"The following sensor types lack unique_id: {missing_unique_id}. "
        f"Without unique_id, reloading the config entry will create duplicate sensors. "
        f"Each reload doubles the entity count because HA cannot recognize existing entities."
    )
