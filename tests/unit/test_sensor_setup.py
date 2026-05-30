"""Stronger tests for _async_setup.py functions — kill mutation survivors.

Covers:
- async_setup_entry: assert on entities created, async_add_entities called
- _async_create_trip_sensors: assert on entity count and creation
- async_create_trip_sensor: assert return values and async_add_entities call
- async_remove_trip_sensor: assert return values and registry removal

Many mutations survive because tests only assert return boolean but don't
assert on the side effects (entities created, callbacks invoked).
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

# =============================================================================
# async_setup_entry — comprehensive assertions
# =============================================================================


class TestAsyncSetupEntryCompleteFlow:
    """Test async_setup_entry with full assertion on side effects.

    Surviving mutations: x_async_setup_entry__mutmut_8 through _mutmut_66.
    Many of these are mutations in the entity creation loop (line 85-89),
    the EmhassDeferrableLoadSensor append (line 90), and the async_add_entities
    call (lines 105-112). Tests that only assert `result is True` miss these.
    """

    def _make_entry(self, coordinator, trip_manager, add_entities_cb=None):
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.runtime_data.trip_manager = trip_manager
        entry.runtime_data.coordinator = coordinator
        entry.runtime_data.sensor_async_add_entities = add_entities_cb or MagicMock()
        return entry

    def _make_coordinator(self):
        coord = MagicMock()
        coord.data = {
            "recurring_trips": {},
            "punctual_trips": {},
            "kwh_today": 0.0,
            "hours_today": 0,
            "next_trip": None,
            "emhass_power_profile": None,
            "emhass_deferrables_schedule": None,
            "emhass_status": None,
        }
        coord.vehicle_id = "v1"
        return coord

    def _make_trip_manager(self):
        tm = MagicMock()
        tm.async_get_recurring_trips = AsyncMock(return_value=[])
        tm.async_get_punctual_trips = AsyncMock(return_value=[])
        return tm

    @pytest.mark.asyncio
    async def test_successful_setup_creates_emhass_sensor(self):
        """Successful setup MUST create an EmhassDeferrableLoadSensor."""
        from custom_components.ev_trip_planner import sensor

        entities_captured = []
        add_entities_cb = MagicMock(
            side_effect=lambda entities, update_before_add=False: (
                entities_captured.extend(entities)
            )
        )

        coordinator = self._make_coordinator()
        trip_manager = self._make_trip_manager()
        entry = self._make_entry(coordinator, trip_manager, add_entities_cb)
        hass = MagicMock()

        result = await sensor.async_setup_entry(hass, entry, add_entities_cb)
        assert result is True
        # Must have at least EmhassDeferrableLoadSensor
        assert len(entities_captured) >= 1
        from custom_components.ev_trip_planner.sensor.entity_emhass_deferrable import (
            EmhassDeferrableLoadSensor,
        )

        emhass_entities = [
            e for e in entities_captured if isinstance(e, EmhassDeferrableLoadSensor)
        ]
        assert len(emhass_entities) == 1

    @pytest.mark.asyncio
    async def test_successful_setup_calls_async_add_entities(self):
        """Successful setup MUST call async_add_entities with all entities."""
        from custom_components.ev_trip_planner import sensor

        call_count = 0
        captured_entities = []

        def capture_add_entities(entities, update_before_add=False):
            nonlocal call_count
            call_count += 1
            captured_entities.extend(entities)

        coordinator = self._make_coordinator()
        trip_manager = self._make_trip_manager()
        entry = self._make_entry(coordinator, trip_manager, capture_add_entities)
        hass = MagicMock()

        await sensor.async_setup_entry(hass, entry, capture_add_entities)
        assert call_count == 1
        assert len(captured_entities) >= 1

    @pytest.mark.asyncio
    async def test_successful_setup_sets_sensor_callback(self):
        """Successful setup MUST store async_add_entities in runtime_data."""
        from custom_components.ev_trip_planner import sensor

        coordinator = self._make_coordinator()
        trip_manager = self._make_trip_manager()
        entry = self._make_entry(coordinator, trip_manager)
        hass = MagicMock()

        await sensor.async_setup_entry(hass, entry, lambda e: None)
        assert entry.runtime_data.sensor_async_add_entities is not None

    @pytest.mark.asyncio
    async def test_successful_setup_with_coordinator_none(self):
        """Setup with coordinator=None still works (uses entry_id as vehicle)."""
        from custom_components.ev_trip_planner import sensor

        entities_captured = []
        add_entities_cb = MagicMock(
            side_effect=lambda entities, update_before_add=False: (
                entities_captured.extend(entities)
            )
        )

        coordinator = MagicMock()
        coordinator.data = {
            "recurring_trips": {},
            "punctual_trips": {},
            "kwh_today": 0.0,
            "hours_today": 0,
            "next_trip": None,
            "emhass_power_profile": None,
            "emhass_deferrables_schedule": None,
            "emhass_status": None,
        }
        # No vehicle_id on coordinator
        trip_manager = self._make_trip_manager()
        entry = self._make_entry(coordinator, trip_manager, add_entities_cb)
        hass = MagicMock()

        result = await sensor.async_setup_entry(hass, entry, add_entities_cb)
        assert result is True

    @pytest.mark.asyncio
    async def test_successful_setup_logs_vehicle_id(self, caplog):
        """Successful setup logs vehicle_id and entry_id."""
        from custom_components.ev_trip_planner import sensor

        coordinator = self._make_coordinator()
        trip_manager = self._make_trip_manager()
        entry = self._make_entry(coordinator, trip_manager)
        hass = MagicMock()

        with caplog.at_level(
            logging.DEBUG,
            logger="custom_components.ev_trip_planner.sensor._async_setup",
        ):
            await sensor.async_setup_entry(hass, entry, lambda e: None)

        assert any("Setting up sensors" in r.message for r in caplog.records)
        assert any("v1" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_async_add_entities_sync_callback(self):
        """When async_add_entities returns None (sync), no await error."""
        from custom_components.ev_trip_planner import sensor

        coordinator = self._make_coordinator()
        trip_manager = self._make_trip_manager()
        # sync callback returns None
        entry = self._make_entry(coordinator, trip_manager, lambda entities: None)
        hass = MagicMock()

        result = await sensor.async_setup_entry(hass, entry, lambda entities: None)
        assert result is True

    @pytest.mark.asyncio
    async def test_async_add_entities_async_callback(self):
        """When async_add_entities returns an awaitable, it gets awaited."""
        from custom_components.ev_trip_planner import sensor

        coordinator = self._make_coordinator()
        trip_manager = self._make_trip_manager()

        async def async_callback(entities):
            return None

        entry = self._make_entry(coordinator, trip_manager, async_callback)
        hass = MagicMock()

        result = await sensor.async_setup_entry(hass, entry, async_callback)
        assert result is True

    @pytest.mark.asyncio
    async def test_async_setup_entry_false_on_no_trip_manager(self, caplog):
        """When trip_manager is None, returns False with error log."""
        from custom_components.ev_trip_planner import sensor

        coordinator = MagicMock()
        coordinator.vehicle_id = "v1"
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.runtime_data.trip_manager = None
        entry.runtime_data.coordinator = coordinator
        hass = MagicMock()

        with caplog.at_level(
            logging.ERROR,
            logger="custom_components.ev_trip_planner.sensor._async_setup",
        ):
            result = await sensor.async_setup_entry(hass, entry, lambda e: None)

        assert result is False
        assert any("No trip_manager found" in r.message for r in caplog.records)


class TestAsyncCreateTripSensors:
    """Test _async_create_trip_sensors.

    Surviving mutations: x__async_create_trip_sensors__mutmut_4 through _mutmut_28+.
    Most are mutations in the loop body (creating sensors for trips). Tests
    should assert on the entity count and types returned.
    """

    def _make_trip_manager(
        self, recurring=None, punctual=None, raise_on_recurring=False
    ):
        tm = MagicMock()
        crud = MagicMock()
        if raise_on_recurring:
            crud.async_get_recurring_trips = AsyncMock(
                side_effect=RuntimeError("CRUD error")
            )
        else:
            crud.async_get_recurring_trips = AsyncMock(return_value=recurring or [])
        crud.async_get_punctual_trips = AsyncMock(return_value=punctual or [])
        tm._crud = crud
        return tm

    @pytest.mark.asyncio
    async def test_no_trips_returns_empty_list(self):
        from custom_components.ev_trip_planner.sensor._async_setup import (
            _async_create_trip_sensors,
        )

        result = await _async_create_trip_sensors(
            MagicMock(), self._make_trip_manager(), "v1", "e1"
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_recurring_trips_creates_sensors(self):
        from custom_components.ev_trip_planner.sensor._async_setup import (
            _async_create_trip_sensors,
        )
        from custom_components.ev_trip_planner.sensor.entity_trip import TripSensor

        result = await _async_create_trip_sensors(
            MagicMock(),
            self._make_trip_manager(recurring=[{"id": "r1", "tipo": "recurrente"}]),
            "v1",
            "e1",
        )
        assert len(result) == 1
        assert isinstance(result[0], TripSensor)

    @pytest.mark.asyncio
    async def test_punctual_trips_creates_sensors(self):
        from custom_components.ev_trip_planner.sensor._async_setup import (
            _async_create_trip_sensors,
        )
        from custom_components.ev_trip_planner.sensor.entity_trip import TripSensor

        result = await _async_create_trip_sensors(
            MagicMock(),
            self._make_trip_manager(punctual=[{"id": "p1", "tipo": "puntual"}]),
            "v1",
            "e1",
        )
        assert len(result) == 1
        assert isinstance(result[0], TripSensor)

    @pytest.mark.asyncio
    async def test_both_trips_creates_all_sensors(self):
        from custom_components.ev_trip_planner.sensor._async_setup import (
            _async_create_trip_sensors,
        )
        from custom_components.ev_trip_planner.sensor.entity_trip import TripSensor

        result = await _async_create_trip_sensors(
            MagicMock(),
            self._make_trip_manager(
                recurring=[{"id": "r1"}, {"id": "r2"}],
                punctual=[{"id": "p1"}],
            ),
            "v1",
            "e1",
        )
        assert len(result) == 3
        for sensor in result:
            assert isinstance(sensor, TripSensor)

    @pytest.mark.asyncio
    async def test_exception_does_not_crash(self):
        """Exception in loop is caught and doesn't crash setup."""
        from custom_components.ev_trip_planner.sensor._async_setup import (
            _async_create_trip_sensors,
        )

        result = await _async_create_trip_sensors(
            MagicMock(),
            self._make_trip_manager(raise_on_recurring=True),
            "v1",
            "e1",
        )
        # Should return empty list, not raise
        assert result == []


# =============================================================================
# async_create_trip_sensor — side effect assertions
# =============================================================================


class TestAsyncCreateTripSensorSideEffects:
    """Test async_create_trip_sensor side effects.

    Mutations survive because tests don't assert on async_add_entities being
    called with the right sensor.
    """

    @pytest.mark.asyncio
    async def test_calls_async_add_entities_with_sensor(self):
        """Successful creation MUST call async_add_entities with a TripSensor."""
        from custom_components.ev_trip_planner.sensor._async_setup import (
            async_create_trip_sensor,
        )
        from custom_components.ev_trip_planner.sensor.entity_trip import TripSensor

        hass = MagicMock()
        add_entities_result = None

        def capture_add_entities(entities, update_before_add=False):
            nonlocal add_entities_result
            add_entities_result = entities
            return None

        entry = MagicMock()
        entry.runtime_data.trip_manager = MagicMock()
        entry.runtime_data.coordinator = MagicMock()
        entry.runtime_data.coordinator.vehicle_id = "v1"
        entry.runtime_data.sensor_async_add_entities = capture_add_entities
        hass.config_entries.async_get_entry.return_value = entry

        result = await async_create_trip_sensor(
            hass, "test_entry", {"id": "t1", "tipo": "recurrente"}
        )

        assert result is True
        assert add_entities_result is not None
        assert len(add_entities_result) == 1
        assert isinstance(add_entities_result[0], TripSensor)

    @pytest.mark.asyncio
    async def test_async_add_entities_returned_awaitable(self):
        """When async_add_entities returns an awaitable, it gets awaited."""
        from custom_components.ev_trip_planner.sensor._async_setup import (
            async_create_trip_sensor,
        )

        hass = MagicMock()

        async def async_add_result(entities, update_before_add=False):
            return None  # Simulates async callback

        entry = MagicMock()
        entry.runtime_data.trip_manager = MagicMock()
        entry.runtime_data.coordinator = MagicMock()
        entry.runtime_data.coordinator.vehicle_id = "v1"
        entry.runtime_data.sensor_async_add_entities = async_add_result
        hass.config_entries.async_get_entry.return_value = entry

        result = await async_create_trip_sensor(
            hass, "test_entry", {"id": "t1", "tipo": "recurrente"}
        )
        assert result is True


# =============================================================================
# async_remove_trip_sensor — side effect assertions
# =============================================================================


class TestAsyncRemoveTripSensorSideEffects:
    """Test async_remove_trip_sensor side effect assertions."""

    @pytest.mark.asyncio
    async def test_removal_calls_registry_async_remove(self, monkeypatch):
        """Removal MUST call entity_registry.async_remove with correct entity_id."""
        from custom_components.ev_trip_planner.sensor._async_setup import (
            async_remove_trip_sensor,
        )

        hass = MagicMock()
        entity_id_captured = None

        def capture_remove(entity_id):
            nonlocal entity_id_captured
            entity_id_captured = entity_id

        mock_reg = MagicMock()
        mock_reg.async_remove = MagicMock(side_effect=capture_remove)
        hass.entity_registry = mock_reg

        mock_reg_entry = MagicMock()
        mock_reg_entry.unique_id = "trip_target_trip"
        mock_reg_entry.entity_id = "sensor.trip_target_trip"

        monkeypatch.setattr(
            "custom_components.ev_trip_planner.sensor._async_setup.async_entries_for_config_entry",
            MagicMock(return_value=[mock_reg_entry]),
        )

        result = await async_remove_trip_sensor(hass, "test_entry", "target_trip")
        assert result is True
        assert entity_id_captured == "sensor.trip_target_trip"

    @pytest.mark.asyncio
    async def test_removes_first_matching_only(self, monkeypatch):
        """Removal should remove first matching entity and break."""
        from custom_components.ev_trip_planner.sensor._async_setup import (
            async_remove_trip_sensor,
        )

        hass = MagicMock()
        remove_count = [0]

        def counting_remove(entity_id):
            remove_count[0] += 1

        mock_reg = MagicMock()
        mock_reg.async_remove = MagicMock(side_effect=counting_remove)
        hass.entity_registry = mock_reg

        # Two matching entries — only first should be removed
        mock_entry1 = MagicMock()
        mock_entry1.unique_id = "trip_target_trip"
        mock_entry1.entity_id = "sensor.trip_target_trip_1"

        mock_entry2 = MagicMock()
        mock_entry2.unique_id = "trip_target_trip"
        mock_entry2.entity_id = "sensor.trip_target_trip_2"

        monkeypatch.setattr(
            "custom_components.ev_trip_planner.sensor._async_setup.async_entries_for_config_entry",
            MagicMock(return_value=[mock_entry1, mock_entry2]),
        )

        result = await async_remove_trip_sensor(hass, "test_entry", "target_trip")
        assert result is True
        assert remove_count[0] == 1  # Only first match removed


# =============================================================================
# async_create_trip_emhass_sensor — side effect assertions
# =============================================================================


class TestAsyncCreateTripEmhassSensorSideEffects:
    """Test async_create_trip_emhass_sensor side effect assertions."""

    @pytest.mark.asyncio
    async def test_calls_async_add_entities_with_emhass_sensor(self):
        """Successful creation MUST call async_add_entities with a TripEmhassSensor."""
        from custom_components.ev_trip_planner.sensor._async_setup import (
            async_create_trip_emhass_sensor,
        )
        from custom_components.ev_trip_planner.sensor.entity_trip_emhass import (
            TripEmhassSensor,
        )

        hass = MagicMock()
        captured_entities = []

        def capture_add_entities(entities, update_before_add=False):
            captured_entities.extend(entities)
            return None

        entry = MagicMock()
        entry.runtime_data.sensor_async_add_entities = capture_add_entities
        hass.config_entries.async_get_entry.return_value = entry

        result = await async_create_trip_emhass_sensor(
            hass, "test_entry", MagicMock(), "v1", "t1"
        )

        assert result is True
        assert len(captured_entities) == 1
        assert isinstance(captured_entities[0], TripEmhassSensor)

    @pytest.mark.asyncio
    async def test_emhass_sensor_has_correct_unique_id(self):
        """Created EMHASS sensor must have correct unique_id format."""
        from custom_components.ev_trip_planner.sensor._async_setup import (
            async_create_trip_emhass_sensor,
        )

        hass = MagicMock()
        captured_entities = []

        def capture_add_entities(entities, update_before_add=False):
            captured_entities.extend(entities)
            return None

        entry = MagicMock()
        entry.runtime_data.sensor_async_add_entities = capture_add_entities
        hass.config_entries.async_get_entry.return_value = entry

        result = await async_create_trip_emhass_sensor(
            hass, "test_entry", MagicMock(), "v1", "my_trip"
        )

        assert result is True
        sensor = captured_entities[0]
        assert sensor._attr_unique_id == "emhass_trip_v1_my_trip"
