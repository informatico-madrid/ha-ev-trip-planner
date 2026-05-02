"""Tests for vehicle_id vs entry_id mismatch in sensor cleanup.

These tests verify that async_cleanup_vehicle_indices correctly handles the case
where vehicle_id differs from entry_id (the sensor entity_id is based on entry_id,
not vehicle_id).

Bug: The cleanup code searches for sensors by looking for vehicle_id in entity_id,
but sensors are created with entity_id based on entry_id (e.g., sensor.emhass_perfil_diferible_{entry_id}).
When vehicle_id != entry_id, cleanup fails to find and remove sensors.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_VEHICLE_NAME,
)
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter


@pytest.fixture
def mock_hass():
    """Create a mock hass instance."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    return hass


@pytest.fixture
def mock_store():
    """Create a mock Store for testing."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock()
    return store


class TestVehicleIdVsEntryIdCleanup:
    """Tests demonstrating the vehicle_id vs entry_id cleanup problem.

    The EMHASS sensor entity_id is: sensor.emhass_perfil_diferible_{entry_id}
    But the cleanup code checks: vehicle_id in entity_id

    When vehicle_id != entry_id, the cleanup fails to find the sensor.
    """

    @pytest.mark.asyncio
    async def test_cleanup_fails_when_vehicle_id_differs_from_entry_id(
        self, hass, mock_store
    ):
        """Demonstrate bug: cleanup fails to remove sensor when vehicle_id != entry_id.

        This test SHOULD FAIL with the current code because:
        - sensor entity_id is: sensor.emhass_perfil_diferible_entry_abc123
        - cleanup checks: "mi_coche" in entity_id → FALSE
        - result: sensor NOT removed (bug!)

        After fix: should also check entry_id in entity_id, so cleanup succeeds.
        """
        # Scenario: vehicle_id is "mi_coche" but entry_id is "entry_abc123"
        vehicle_id = "mi_coche"
        entry_id = "entry_abc123"
        sensor_entity_id = f"sensor.emhass_perfil_diferible_{entry_id}"

        config = {
            CONF_VEHICLE_NAME: vehicle_id,
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, config)
            adapter._loaded = True
            # Directly set entry_id since __init__ sets it from config (vehicle_name)
            adapter.entry_id = entry_id

            # Setup coordinator
            coordinator = MagicMock()
            coordinator.data = {"per_trip_emhass_params": {}}
            coordinator.async_request_refresh = AsyncMock()

            runtime_data = MagicMock()
            runtime_data.coordinator = coordinator

            # Mock entry with DIFFERENT entry_id than vehicle_id
            entry = MagicMock()
            entry.entry_id = entry_id
            entry.runtime_data = runtime_data
            adapter._entry = entry

            # Simulate sensor exists in hass.states (created with entry_id-based entity_id)
            # Entity ID is: sensor.emhass_perfil_diferible_entry_abc123
            hass.states.async_entity_ids = MagicMock(
                side_effect=[
                    [sensor_entity_id],  # log
                    [sensor_entity_id],  # first loop
                    [sensor_entity_id],  # force-set loop
                ]
            )
            hass.states.async_remove = AsyncMock()

            mock_registry = MagicMock()
            with patch(
                "homeassistant.helpers.entity_registry.async_get",
                return_value=mock_registry,
            ):
                await adapter.async_cleanup_vehicle_indices()

            # BUG: async_remove was NOT called because cleanup searched for vehicle_id in entity_id
            # but entity_id contains entry_id, not vehicle_id
            # This assertion demonstrates the bug - it should FAIL with current code
            assert hass.states.async_remove.called, (
                f"BUG: Cleanup failed to remove sensor {sensor_entity_id} "
                f"because vehicle_id='{vehicle_id}' not found in entity_id. "
                f"Expected cleanup to also check entry_id='{entry_id}'."
            )

    @pytest.mark.asyncio
    async def test_cleanup_succeeds_when_vehicle_id_matches_entry_id(
        self, hass, mock_store
    ):
        """Verify cleanup works when vehicle_id == entry_id (the working case)."""
        # Scenario: vehicle_id equals entry_id (the common/test case)
        vehicle_id = "test_vehicle"
        entry_id = "test_vehicle"  # Same!
        sensor_entity_id = f"sensor.emhass_perfil_diferible_{entry_id}"

        config = {
            CONF_VEHICLE_NAME: vehicle_id,
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, config)
            adapter._loaded = True

            coordinator = MagicMock()
            coordinator.data = {"per_trip_emhass_params": {}}
            coordinator.async_request_refresh = AsyncMock()

            runtime_data = MagicMock()
            runtime_data.coordinator = coordinator

            entry = MagicMock()
            entry.entry_id = entry_id
            entry.runtime_data = runtime_data
            adapter._entry = entry

            hass.states.async_entity_ids = MagicMock(
                side_effect=[
                    [sensor_entity_id],
                    [sensor_entity_id],
                    [sensor_entity_id],
                ]
            )
            hass.states.async_remove = AsyncMock()

            mock_registry = MagicMock()
            with patch(
                "homeassistant.helpers.entity_registry.async_get",
                return_value=mock_registry,
            ):
                await adapter.async_cleanup_vehicle_indices()

            # This works because vehicle_id == entry_id
            assert hass.states.async_remove.called

    @pytest.mark.asyncio
    async def test_cleanup_dangerous_fallback_test_vehicle_removed(
        self, hass, mock_store
    ):
        """Verify dangerous fallback 'test_vehicle' was removed.

        The old fallback at line 1805-1806 was DANGEROUS because it removed
        ANY sensor with "test_vehicle" in entity_id, even if it belonged to
        a DIFFERENT vehicle/entry.

        After the fix: the fallback is removed and replaced with entry_id check.
        This test verifies the dangerous fallback no longer works.
        """
        # Scenario: Vehicle "mi_coche" with entry_id "entry_xyz"
        # Sensor entity_id contains "test_vehicle" substring but NOT our vehicle_id or entry_id
        vehicle_id = "mi_coche"
        entry_id = "entry_xyz"
        # Entity ID with "test_vehicle" substring but NOT our vehicle_id or entry_id
        sensor_entity_id = "sensor.emhass_perfil_diferible_test_vehicle_other"

        config = {
            CONF_VEHICLE_NAME: vehicle_id,
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, config)
            adapter._loaded = True

            coordinator = MagicMock()
            coordinator.data = {"per_trip_emhass_params": {}}
            coordinator.async_request_refresh = AsyncMock()

            runtime_data = MagicMock()
            runtime_data.coordinator = coordinator

            entry = MagicMock()
            entry.entry_id = entry_id
            entry.runtime_data = runtime_data
            adapter._entry = entry

            hass.states.async_entity_ids = MagicMock(
                side_effect=[
                    [sensor_entity_id],
                    [sensor_entity_id],
                    [sensor_entity_id],
                ]
            )
            hass.states.async_remove = AsyncMock()

            mock_registry = MagicMock()
            with patch(
                "homeassistant.helpers.entity_registry.async_get",
                return_value=mock_registry,
            ):
                await adapter.async_cleanup_vehicle_indices()

            # After fix: sensor should NOT be removed because:
            # - vehicle_id "mi_coche" NOT in entity_id
            # - entry_id "entry_xyz" NOT in entity_id
            # - dangerous fallback "test_vehicle" was removed
            assert not hass.states.async_remove.called, (
                "DANGEROUS FALLBACK STILL EXISTS: sensor was incorrectly removed. "
                "The 'test_vehicle' fallback should have been removed."
            )
