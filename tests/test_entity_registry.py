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
async def test_two_vehicles_no_unique_id_collision():
    """Test that unique_ids from two different vehicles are globally unique.

    This test FAILS because TripSensor unique_id format is `trip_{trip_id}`
    without a vehicle prefix. If two vehicles both have a trip with id "1",
    both will create sensors with unique_id="trip_1", causing a collision.

    After Phase 1-3 refactoring, unique_ids should be globally unique:
      _attr_unique_id = f"{DOMAIN}_{vehicle_id}_{trip_id}"
    """
    from custom_components.ev_trip_planner.const import DOMAIN
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
            suggested_object_id = kwargs.get('suggested_object_id', 'unknown')
            unique_id = kwargs.get('unique_id', '')
            entity_id = f"sensor.{suggested_object_id}"
            config_entry_id = kwargs.get('config_entry', kwargs.get('config_entry_id', ''))
            entry = MockRegistryEntry(entity_id, unique_id, config_entry_id)
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

    def create_mock_hass(entry):
        """Create a mock hass for a specific entry."""
        hass = MagicMock()
        mock_registry = MockRegistry()
        hass.entity_registry = mock_registry

        # Create mock trip_manager with a trip that has id="1"
        tm = MagicMock()
        tm.async_get_recurring_trips = AsyncMock(return_value=[])
        # Both vehicles have a trip with id="1" - this is the collision
        tm.async_get_punctual_trips = AsyncMock(return_value=[
            {
                "id": "1",
                "tipo": "punctual",
                "descripcion": "Trip to work",
                "km": 25.0,
                "kwh": 5.0,
                "datetime": "2024-01-15T08:00:00",
                "estado": "pendiente",
            }
        ])
        tm.async_delete_all_trips = AsyncMock()

        coordinator = MagicMock()
        coordinator.data = {}
        coordinator.trip_manager = tm
        coordinator.async_config_entry_first_refresh = AsyncMock()

        namespace = f"{DOMAIN}_{entry.entry_id}"
        hass.data = {
            f"{DOMAIN}_runtime_data": {
                namespace: {
                    "trip_manager": tm,
                    "coordinator": coordinator,
                    "config": entry.data,
                }
            }
        }

        hass.config_entries = MagicMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        hass.config_entries.async_entries = MagicMock(return_value=[entry])

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
        getattr(e, '_attr_unique_id', None)
        for e in entities_a
        if type(e).__name__ == 'TripSensor'
    ]
    trip_sensor_unique_ids_b = [
        getattr(e, '_attr_unique_id', None)
        for e in entities_b
        if type(e).__name__ == 'TripSensor'
    ]

    # Combine TripSensor unique_ids from both vehicles
    all_trip_sensor_unique_ids = trip_sensor_unique_ids_a + trip_sensor_unique_ids_b

    # Verify we have exactly 1 TripSensor from each vehicle
    assert len(trip_sensor_unique_ids_a) == 1, f"Expected 1 TripSensor from vehicle A, got {len(trip_sensor_unique_ids_a)}"
    assert len(trip_sensor_unique_ids_b) == 1, f"Expected 1 TripSensor from vehicle B, got {len(trip_sensor_unique_ids_b)}"

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


@pytest.mark.asyncio
async def test_trip_sensor_created_in_registry_after_add(mock_hass, config_entry):
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
    from custom_components.ev_trip_planner import DATA_RUNTIME
    from custom_components.ev_trip_planner.const import DOMAIN
    from custom_components.ev_trip_planner.sensor import async_create_trip_sensor
    from custom_components.ev_trip_planner.sensor import async_setup_entry

    # Track entities created during async_setup_entry
    setup_entities = []

    def capture_async_add_entities(entities, update_before_add=True):
        setup_entities.extend(entities)

    # Run async_setup_entry to set up the initial 8 sensors
    result = await async_setup_entry(mock_hass, config_entry, capture_async_add_entities)
    assert result is True, "async_setup_entry should succeed"

    # Verify initial sensors are set up
    initial_count = len(setup_entities)
    assert initial_count >= 8, f"Expected >= 8 initial sensors, got {initial_count}"

    # Get the namespace used by the integration
    namespace = f"{DOMAIN}_{config_entry.entry_id}"

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

    # Call async_create_trip_sensor - this creates the object but does NOT
    # register it with the entity registry (the bug!)
    create_result = await async_create_trip_sensor(
        mock_hass, config_entry.entry_id, trip_data
    )
    assert create_result is True, "async_create_trip_sensor should succeed"

    # The sensor object IS stored in hass.data (verify this)
    runtime_data = mock_hass.data.get(DATA_RUNTIME, {})
    namespace_data = runtime_data.get(namespace, {})
    trip_sensors_dict = namespace_data.get("trip_sensors", {})
    assert "test_trip_001" in trip_sensors_dict, (
        "Trip sensor object should exist in hass.data trip_sensors dict"
    )

    # BUT the sensor is NOT in the entity registry (this is the bug!)
    # Check the entity registry for a TripSensor with this trip_id
    registry = mock_hass.entity_registry
    all_entries = registry.entries

    # Find any registry entry whose unique_id contains our trip_id
    matching_entries = [
        entry for entry in all_entries.values()
        if "test_trip_001" in entry.unique_id
    ]

    # This FAILS: async_create_trip_sensor never calls async_add_entities(),
    # so the entity is not registered in the entity registry
    assert len(matching_entries) > 0, (
        f"Expected TripSensor with trip_id 'test_trip_001' to appear in entity registry "
        f"after async_create_trip_sensor(), but no matching entry found. "
        f"Available entries: {[(e.entity_id, e.unique_id) for e in all_entries.values()]}. "
        f"The sensor object exists in hass.data but is invisible to HA because "
        f"async_create_trip_sensor() never calls async_add_entities()."
    )


@pytest.mark.asyncio
async def test_trip_sensor_removed_from_registry_after_delete(mock_hass, config_entry):
    """Test that TripSensor is removed from entity registry after delete_trip service.

    This test FAILS today because async_remove_trip_sensor() only deletes from dict
    (del trip_sensors[trip_id]), never calls entity_registry.async_remove(),
    leaving zombie entries in the registry.

    After Phase 2 fix, the entity registry should have 0 entries for this trip.
    """
    from custom_components.ev_trip_planner import DATA_RUNTIME
    from custom_components.ev_trip_planner.const import DOMAIN
    from custom_components.ev_trip_planner.sensor import async_create_trip_sensor
    from custom_components.ev_trip_planner.sensor import async_remove_trip_sensor

    # Set up the namespace and trip_sensors dict in hass.data
    namespace = f"{DOMAIN}_{config_entry.entry_id}"
    if DATA_RUNTIME not in mock_hass.data:
        mock_hass.data[DATA_RUNTIME] = {}
    if namespace not in mock_hass.data[DATA_RUNTIME]:
        mock_hass.data[DATA_RUNTIME][namespace] = {}
    mock_hass.data[DATA_RUNTIME][namespace]["trip_sensors"] = {}

    # Create a trip sensor via async_create_trip_sensor
    trip_data = {
        "id": "trip_001",
        "tipo": "recurrente",
        "descripcion": "Work commute",
        "km": 25.5,
        "kwh": 4.2,
    }

    await async_create_trip_sensor(
        hass=mock_hass,
        entry_id=config_entry.entry_id,
        trip_data=trip_data,
    )

    # Manually register the trip sensor in the entity registry
    # (simulating what should happen during proper sensor creation in a real HA setup)
    registry = mock_hass.entity_registry
    registry.async_get_or_create(
        domain="sensor",
        platform="ev_trip_planner",
        unique_id=f"trip_trip_001",
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
        hass=mock_hass,
        entry_id=config_entry.entry_id,
        trip_id="trip_001",
    )

    # Verify the sensor was removed from the trip_sensors dict
    namespace_data = mock_hass.data[DATA_RUNTIME].get(namespace, {})
    trip_sensors = namespace_data.get("trip_sensors", {})
    assert "trip_001" not in trip_sensors, "Sensor should be removed from trip_sensors dict"

    # This FAILS: the entity registry entry still exists (zombie)
    # because async_remove_trip_sensor does NOT call entity_registry.async_remove()
    entries_after = registry.async_entries_for_config_entry(config_entry.entry_id)
    trip_entries_after = [e for e in entries_after if "trip_001" in e.unique_id]
    assert len(trip_entries_after) == 0, (
        f"Expected 0 trip sensor entries in registry after delete, but found {len(trip_entries_after)} "
        f"zombie entries. async_remove_trip_sensor() only deletes from trip_sensors dict, "
        f"never calls entity_registry.async_remove()."
    )
