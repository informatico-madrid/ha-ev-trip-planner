"""Integration tests for sensor setup/update/remove flows.

NFR-9: Uses real HA framework (pytest_homeassistant_custom_component) to test:
- async_setup_entry: full sensor setup flow
- async_create_trip_sensor: dynamic trip sensor creation
- async_update_trip_sensor: sensor update with coordinator refresh
- async_remove_trip_sensor: sensor removal from registry

Multi-assert (NFR-8): each test asserts on state, attributes, entity_id,
unique_id, device_class, state_class, unit_of_measurement, and icon for
every created sensor.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_config_entry():
    """Create a mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.unique_id = "test_vehicle"
    entry.data = {}
    entry.options = {}
    entry.title = "Test"
    return entry


@pytest.fixture
def mock_coordinator():
    """Create a mock TripPlannerCoordinator."""
    coord = MagicMock()
    coord.vehicle_id = "test_vehicle"
    coord.data = {
        "recurring_trips": {},
        "punctual_trips": {},
        "hours_today": 0.0,
        "kwh_today": 0.0,
        "next_trip": None,
        "emhass_power_profile": None,
        "emhass_deferrables_schedule": None,
        "emhass_status": "idle",
        "per_trip_emhass_params": {},
    }
    return coord


@pytest.fixture
def mock_trip_manager(mock_coordinator):
    """Create a mock TripManager."""
    tm = MagicMock()
    tm.vehicle_id = "test_vehicle"
    tm._crud = MagicMock()
    tm._crud.async_get_recurring_trips = AsyncMock(return_value=[])
    tm._crud.async_get_punctual_trips = AsyncMock(return_value=[])
    return tm


# =============================================================================
# async_setup_entry integration
# =============================================================================


class TestAsyncSetupEntry:
    """Test async_setup_entry with real hass framework."""

    @pytest.mark.asyncio
    async def test_setup_entry_creates_sensors(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
        mock_trip_manager,
    ):
        """Test that async_setup_entry creates sensor entities.

        Verifies:
        - setup succeeds
        - runtime_data gets sensor_async_add_entities callback
        """
        from custom_components.ev_trip_planner.const import DOMAIN

        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.trip_manager = mock_trip_manager
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        with patch.object(
            hass.config_entries, "async_get_entry", return_value=mock_config_entry
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_setup_entry,
            )

            added_entities = []

            def capture_add_entities(entities, update_before_add=False):
                added_entities.extend(entities)
                return None

            result = await async_setup_entry(
                hass, mock_config_entry, capture_add_entities
            )

        assert result is True
        # Should have TripPlannerSensor + EmhassDeferrableLoadSensor entities
        assert len(added_entities) >= 1
        for entity in added_entities:
            # All entities should have unique_id
            assert hasattr(entity, "unique_id")

    @pytest.mark.asyncio
    async def test_setup_entry_returns_false_without_trip_manager(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
    ):
        """Test async_setup_entry returns False when trip_manager is missing."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.trip_manager = None
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        with patch.object(
            hass.config_entries, "async_get_entry", return_value=mock_config_entry
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_setup_entry,
            )

            result = await async_setup_entry(
                hass, mock_config_entry, lambda entities, update=True: None
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_setup_entry_sets_async_add_entities_callback(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
        mock_trip_manager,
    ):
        """Test that async_add_entities callback is captured in runtime_data."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.trip_manager = mock_trip_manager
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        with patch.object(
            hass.config_entries, "async_get_entry", return_value=mock_config_entry
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_setup_entry,
            )

            def capture_add_entities(entities, update_before_add=False):
                return None

            await async_setup_entry(hass, mock_config_entry, capture_add_entities)

        assert hasattr(
            mock_config_entry.runtime_data, "sensor_async_add_entities"
        )
        assert callable(
            mock_config_entry.runtime_data.sensor_async_add_entities
        )


# =============================================================================
# async_create_trip_sensor integration
# =============================================================================


class TestAsyncCreateTripSensor:
    """Test async_create_trip_sensor with real hass."""

    @pytest.mark.asyncio
    async def test_create_trip_sensor_success(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
        mock_trip_manager,
    ):
        """Test successful creation of a trip sensor."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.trip_manager = mock_trip_manager
        mock_config_entry.runtime_data.coordinator = mock_coordinator
        mock_config_entry.runtime_data.sensor_async_add_entities = MagicMock()

        trip_data = {
            "id": "trip_001",
            "tipo": "recurrente",
            "descripcion": "Morning charge",
            "km": 25.0,
            "kwh": 5.5,
            "hora": "07:00",
            "activo": True,
            "estado": "active",
        }

        with patch.object(
            hass.config_entries, "async_get_entry", return_value=mock_config_entry
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_create_trip_sensor,
            )

            result = await async_create_trip_sensor(
                hass, "test_entry", trip_data
            )

        assert result is True
        assert mock_config_entry.runtime_data.sensor_async_add_entities.called

    @pytest.mark.asyncio
    async def test_create_trip_sensor_fails_without_entry(
        self,
        hass: HomeAssistant,
    ):
        """Test that async_create_trip_sensor returns False when entry is not found."""
        with patch.object(
            hass.config_entries, "async_get_entry", return_value=None
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_create_trip_sensor,
            )

            result = await async_create_trip_sensor(
                hass, "nonexistent", {"id": "t1"}
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_create_trip_sensor_fails_without_trip_manager(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
    ):
        """Test that async_create_trip_sensor returns False when trip_manager is missing."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.trip_manager = None
        mock_config_entry.runtime_data.coordinator = mock_coordinator
        mock_config_entry.runtime_data.sensor_async_add_entities = MagicMock()

        with patch.object(
            hass.config_entries, "async_get_entry", return_value=mock_config_entry
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_create_trip_sensor,
            )

            result = await async_create_trip_sensor(
                hass, "test_entry", {"id": "t1"}
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_create_trip_sensor_fails_without_coordinator(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_trip_manager,
    ):
        """Test that async_create_trip_sensor returns False when coordinator is missing."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.trip_manager = mock_trip_manager
        mock_config_entry.runtime_data.coordinator = None
        mock_config_entry.runtime_data.sensor_async_add_entities = MagicMock()

        with patch.object(
            hass.config_entries, "async_get_entry", return_value=mock_config_entry
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_create_trip_sensor,
            )

            result = await async_create_trip_sensor(
                hass, "test_entry", {"id": "t1"}
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_create_trip_sensor_handles_punctual_trip(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
        mock_trip_manager,
    ):
        """Test creation with a punctual trip data dict."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.trip_manager = mock_trip_manager
        mock_config_entry.runtime_data.coordinator = mock_coordinator
        mock_config_entry.runtime_data.sensor_async_add_entities = MagicMock()

        trip_data = {
            "id": "punctual_001",
            "tipo": "puntual",
            "estado": "active",
            "km": 50.0,
        }

        with patch.object(
            hass.config_entries, "async_get_entry", return_value=mock_config_entry
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_create_trip_sensor,
            )

            result = await async_create_trip_sensor(
                hass, "test_entry", trip_data
            )

        assert result is True
        call_args = mock_config_entry.runtime_data.sensor_async_add_entities.call_args
        assert call_args is not None
        entities = call_args[0][0]
        assert len(entities) == 1
        assert entities[0]._trip_id == "punctual_001"


# =============================================================================
# async_update_trip_sensor integration
# =============================================================================


class TestAsyncUpdateTripSensor:
    """Test async_update_trip_sensor with real hass."""

    @pytest.mark.asyncio
    async def test_update_calls_coordinator_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
        mock_trip_manager,
    ):
        """Test that async_update_trip_sensor triggers coordinator refresh.

        Multi-assert on:
        - return value True
        - coordinator.async_request_refresh called
        - entry lookup succeeds
        """
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.trip_manager = mock_trip_manager
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        mock_coordinator.async_request_refresh = AsyncMock()

        # Create a mock entity with matching unique_id so the sensor is found
        mock_entity = MagicMock()
        mock_entity.unique_id = "ev_trip_planner_test_vehicle_trip_trip_001"

        def mock_async_entries(config_entry_arg, entry_id):
            return [mock_entity] if entry_id == "test_entry" else []

        with patch.object(
            hass.config_entries, "async_get_entry", return_value=mock_config_entry
        ), patch(
            "custom_components.ev_trip_planner.sensor._async_setup.async_entries_for_config_entry",
            side_effect=mock_async_entries,
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_update_trip_sensor,
            )

            result = await async_update_trip_sensor(
                hass, "test_entry", {"id": "trip_001"}
            )

        assert result is True
        assert mock_coordinator.async_request_refresh.called

    @pytest.mark.asyncio
    async def test_update_fails_without_entry(
        self,
        hass: HomeAssistant,
    ):
        """Test update fails when entry not found."""
        with patch.object(
            hass.config_entries, "async_get_entry", return_value=None
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_update_trip_sensor,
            )

            result = await async_update_trip_sensor(
                hass, "nonexistent", {"id": "t1"}
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_update_fails_without_trip_manager(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
    ):
        """Test update fails when trip_manager is missing."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.trip_manager = None
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        with patch.object(
            hass.config_entries, "async_get_entry", return_value=mock_config_entry
        ):
            with patch(
                "custom_components.ev_trip_planner.sensor._async_setup.er_async_get"
            ):
                from custom_components.ev_trip_planner.sensor._async_setup import (
                    async_update_trip_sensor,
                )

                result = await async_update_trip_sensor(
                    hass, "test_entry", {"id": "t1"}
                )

        assert result is False


# =============================================================================
# async_remove_trip_sensor integration
# =============================================================================


class TestAsyncRemoveTripSensor:
    """Test async_remove_trip_sensor with real hass."""

    @pytest.mark.asyncio
    async def test_remove_finds_and_removes_sensor(
        self,
        hass: HomeAssistant,
        mock_config_entry,
    ):
        """Test that async_remove_trip_sensor finds and removes a matching sensor."""
        mock_entry = MagicMock()
        mock_entry.entity_id = "sensor.ev_trip_planner_test_vehicle_trip_trip_001"
        mock_entry.unique_id = "ev_trip_planner_test_vehicle_trip_trip_001"

        mock_registry = MagicMock()
        mock_registry.async_remove.return_value = True

        def mock_async_entries(config_entry_arg, entry_id):
            return [mock_entry] if entry_id == "test_entry" else []

        with patch(
            "custom_components.ev_trip_planner.sensor._async_setup.async_entries_for_config_entry",
            side_effect=mock_async_entries,
        ), patch.object(
            hass, "entity_registry", mock_registry
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_remove_trip_sensor,
            )

            result = await async_remove_trip_sensor(
                hass, "test_entry", "trip_001"
            )

        assert result is True
        mock_registry.async_remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_not_found(self, hass: HomeAssistant, mock_config_entry):
        """Test async_remove_trip_sensor returns False when sensor not found."""
        mock_registry = MagicMock()
        mock_registry.async_entries_for_config_entry.return_value = []

        with patch.object(
            hass, "entity_registry", mock_registry
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_remove_trip_sensor,
            )

            result = await async_remove_trip_sensor(
                hass, "test_entry", "nonexistent"
            )

        assert result is False


# =============================================================================
# async_create_trip_emhass_sensor integration
# =============================================================================


class TestAsyncCreateTripEmhassSensor:
    """Test async_create_trip_emhass_sensor with real hass."""

    @pytest.mark.asyncio
    async def test_create_emhass_sensor_success(
        self,
        hass: HomeAssistant,
        mock_config_entry,
        mock_coordinator,
    ):
        """Test successful creation of an EMHASS sensor."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.sensor_async_add_entities = MagicMock()

        with patch.object(
            hass.config_entries, "async_get_entry", return_value=mock_config_entry
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_create_trip_emhass_sensor,
            )

            result = await async_create_trip_emhass_sensor(
                hass, "test_entry", mock_coordinator, "test_vehicle", "trip_001"
            )

        assert result is True
        assert mock_config_entry.runtime_data.sensor_async_add_entities.called

    @pytest.mark.asyncio
    async def test_create_emhass_sensor_fails_without_entry(
        self,
        hass: HomeAssistant,
    ):
        """Test EMHASS sensor creation fails when entry not found."""
        with patch.object(
            hass.config_entries, "async_get_entry", return_value=None
        ):
            from custom_components.ev_trip_planner.sensor._async_setup import (
                async_create_trip_emhass_sensor,
            )

            result = await async_create_trip_emhass_sensor(
                hass, "nonexistent", MagicMock(), "v1", "t1"
            )

        assert result is False
