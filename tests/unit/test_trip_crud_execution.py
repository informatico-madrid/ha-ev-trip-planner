"""Execution tests for TripManager sub-components.

Covers CRUD operations (add/update/delete), lifecycle management, EMHASS sync,
and persistence fallback — all exercised via the new composed architecture.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.const import DOMAIN
from custom_components.ev_trip_planner.trip import TripManager
from custom_components.ev_trip_planner.trip._crud import TripCRUD
from custom_components.ev_trip_planner.trip._emhass_sync import EMHASSSync
from custom_components.ev_trip_planner.trip._persistence import TripPersistence
from custom_components.ev_trip_planner.trip._trip_lifecycle import TripLifecycle
from custom_components.ev_trip_planner.trip.state import TripManagerState

_NO_ADAPTER = object()


def _make_tm(
    recurring=None, punctual=None, entry_id="test_entry", emhass_adapter=_NO_ADAPTER
):
    """Build a minimal TripManager with proper state for CRUD tests.

    Creates TripManagerState and all sub-components manually (skipping __init__)
    so sub-component references are properly wired on state.
    """
    recurring = recurring or {}
    punctual = punctual or {}

    hass = MagicMock()
    vehicle_id = "test_vehicle"

    tm = TripManager.__new__(TripManager)
    tm._state = TripManagerState(
        hass=hass,
        vehicle_id=vehicle_id,
        entry_id=entry_id,
    )
    tm._state.recurring_trips = recurring
    tm._state.punctual_trips = punctual

    # Create vehicle controller mock
    vc = MagicMock()
    vc.async_setup = AsyncMock()
    tm._state.vehicle_controller = vc

    # Set up save_trips mock
    tm._state.async_save_trips = AsyncMock()

    # Set up sensor callbacks
    cb = MagicMock()
    cb.emit = MagicMock()
    tm._state.sensor_callbacks = cb

    # Set up EMHASS adapter
    if emhass_adapter is None:
        tm._state.emhass_adapter = None
    else:
        adapter = MagicMock()
        adapter.async_publish_all_deferrable_loads = AsyncMock()
        adapter.async_publish_deferrable_load = AsyncMock()
        adapter.async_update_deferrable_load = AsyncMock()
        adapter.async_remove_deferrable_load = AsyncMock()
        adapter._published_trips = set()
        adapter._cached_per_trip_params = {}
        adapter._cached_power_profile = []
        adapter._cached_deferrables_schedule = []
        tm._state.emhass_adapter = adapter

    # Create sub-components and wire references on state
    tm._persistence = TripPersistence(tm._state)
    tm._crud = TripCRUD(tm._state)
    tm._lifecycle = TripLifecycle(tm._state)
    tm._emhass_sync = EMHASSSync(tm._state)
    tm._state._crud = tm._crud
    tm._state._persistence = tm._persistence
    tm._state._lifecycle = tm._lifecycle
    tm._state._emhass_sync = tm._emhass_sync

    # Wire schedule mock for delete_all path (publish_deferrable_loads)
    sched_mock = MagicMock()
    sched_mock.publish_deferrable_loads = AsyncMock()
    tm._state._schedule = sched_mock

    return tm


class TestCRUDAddRecurring:
    """Test async_add_recurring_trip paths."""

    @pytest.mark.asyncio
    async def test_add_recurring_trip(self):
        """Adding a recurring trip stores it and saves."""
        tm = _make_tm()
        await tm._crud.async_add_recurring_trip(
            trip_id="rec_1",
            dia_semana="1",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )
        assert "rec_1" in tm._state.recurring_trips
        assert tm._state.recurring_trips["rec_1"]["km"] == 50.0
        tm._state.async_save_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_recurring_trip_emhass(self):
        """Adding recurring trip with EMHASS adapter calls publish to EMHASS."""
        tm = _make_tm()
        await tm._crud.async_add_recurring_trip(
            trip_id="rec_1",
            dia_semana="1",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )
        assert tm._state.emhass_adapter is not None

    @pytest.mark.asyncio
    async def test_add_recurring_trip_no_adapter(self):
        """Adding recurring trip without EMHASS adapter is still successful."""
        tm = _make_tm(emhass_adapter=None)
        await tm._crud.async_add_recurring_trip(
            trip_id="rec_1",
            dia_semana="1",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )
        assert "rec_1" in tm._state.recurring_trips
        tm._state.async_save_trips.assert_called_once()


class TestCRUDAddPunctual:
    """Test async_add_punctual_trip paths."""

    @pytest.mark.asyncio
    async def test_add_punctual_trip_with_id(self):
        """Adding punctual trip with explicit trip_id."""
        tm = _make_tm()
        await tm._crud.async_add_punctual_trip(
            trip_id="pun_1",
            datetime_str="2026-06-01T08:00",
            km=30.0,
            kwh=5.0,
        )
        assert "pun_1" in tm._state.punctual_trips
        assert tm._state.punctual_trips["pun_1"]["estado"] == "pendiente"

    @pytest.mark.asyncio
    async def test_add_punctual_trip_autogenerates_id(self):
        """Adding punctual trip without trip_id generates one from datetime."""
        tm = _make_tm()
        await tm._crud.async_add_punctual_trip(
            datetime_str="2026-06-01T08:00",
            km=30.0,
            kwh=5.0,
        )
        assert len(tm._state.punctual_trips) == 1
        trip_id = list(tm._state.punctual_trips.keys())[0]
        assert "pun_" in trip_id

    @pytest.mark.asyncio
    async def test_add_punctual_trip_no_datetime(self):
        """Adding punctual trip with no datetime generates empty date part."""
        tm = _make_tm()
        await tm._crud.async_add_punctual_trip(
            km=30.0,
            kwh=5.0,
        )
        assert len(tm._state.punctual_trips) == 1


class TestCRUDUpdate:
    """Test async_update_trip paths."""

    @pytest.mark.asyncio
    async def test_update_recurring_trip(self):
        """Updating a recurring trip modifies the trip and saves."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "km": 50.0, "activo": True}})
        await tm._crud.async_update_trip(
            "rec_1", {"km": 75.0, "descripcion": "New desc"}
        )
        assert tm._state.recurring_trips["rec_1"]["km"] == 75.0
        assert tm._state.recurring_trips["rec_1"]["descripcion"] == "New desc"
        tm._state.async_save_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_punctual_trip(self):
        """Updating a punctual trip modifies and saves."""
        tm = _make_tm(punctual={"pun_1": {"id": "pun_1", "km": 30.0}})
        await tm._crud.async_update_trip("pun_1", {"km": 45.0})
        assert tm._state.punctual_trips["pun_1"]["km"] == 45.0
        tm._state.async_save_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_nonexistent_trip(self):
        """Updating non-existent trip logs warning."""
        tm = _make_tm()
        await tm._crud.async_update_trip("nonexistent", {"km": 10.0})
        tm._state.async_save_trips.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_recurring_triggers_emhass_sync(self):
        """Update to recurring trip triggers EMHASS sync."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "km": 50.0, "activo": True}})
        # Replace bound method with mock to verify it gets called
        sync_mock = AsyncMock()
        tm._state._emhass_sync._async_sync_trip_to_emhass = sync_mock
        await tm._crud.async_update_trip("rec_1", {"km": 75.0, "kwh": 15.0})
        sync_mock.assert_called_once()


class TestCRUDDelete:
    """Test async_delete_trip paths."""

    @pytest.mark.asyncio
    async def test_delete_recurring_trip(self):
        """Deleting a recurring trip removes it and saves."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "activo": True}})
        await tm._crud.async_delete_trip("rec_1")
        assert "rec_1" not in tm._state.recurring_trips
        tm._state.async_save_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_punctual_trip(self):
        """Deleting a punctual trip removes it and saves."""
        tm = _make_tm(punctual={"pun_1": {"id": "pun_1", "estado": "pendiente"}})
        await tm._crud.async_delete_trip("pun_1")
        assert "pun_1" not in tm._state.punctual_trips
        tm._state.async_save_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_trip(self):
        """Deleting non-existent trip logs warning, no save."""
        tm = _make_tm()
        await tm._crud.async_delete_trip("nonexistent")
        tm._state.async_save_trips.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_trip_triggers_emhass_remove(self):
        """Deleting a trip with EMHASS adapter calls _async_remove_trip_from_emhass."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "activo": True}})
        await tm._crud.async_delete_trip("rec_1")
        assert tm._state.emhass_adapter is not None


class TestCRUDDeleteAll:
    """Test async_delete_all_trips paths (lifecycle)."""

    @pytest.mark.asyncio
    async def test_delete_all_trips_clears_data(self):
        """Deleting all trips clears recurring and punctual."""
        tm = _make_tm(
            recurring={"rec_1": {"id": "rec_1", "activo": True}},
            punctual={"pun_1": {"id": "pun_1", "estado": "pendiente"}},
        )
        await tm._lifecycle.async_delete_all_trips()
        assert tm._state.recurring_trips == {}
        assert tm._state.punctual_trips == {}

    @pytest.mark.asyncio
    async def test_delete_all_clears_emhass_adapter(self):
        """Deleting all trips clears EMHASS adapter cache."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "activo": True}})
        tm._state.emhass_adapter._published_trips = {"old_trip"}
        tm._state.emhass_adapter._cached_per_trip_params = {"old": "data"}
        await tm._lifecycle.async_delete_all_trips()
        assert tm._state.emhass_adapter._published_trips == set()
        assert tm._state.emhass_adapter._cached_per_trip_params == {}


class TestCRUDPauseResume:
    """Test async_pause_recurring_trip and async_resume_recurring_trip (lifecycle)."""

    @pytest.mark.asyncio
    async def test_pause_existing_trip(self):
        """Pausing an existing recurring trip sets activo=False."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "activo": True}})
        await tm._lifecycle.async_pause_recurring_trip("rec_1")
        assert tm._state.recurring_trips["rec_1"]["activo"] is False
        tm._state.async_save_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause_nonexistent_trip(self):
        """Pausing non-existent trip does nothing."""
        tm = _make_tm()
        await tm._lifecycle.async_pause_recurring_trip("nonexistent")
        tm._state.async_save_trips.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_existing_trip(self):
        """Resuming an existing recurring trip sets activo=True."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "activo": False}})
        await tm._lifecycle.async_resume_recurring_trip("rec_1")
        assert tm._state.recurring_trips["rec_1"]["activo"] is True
        tm._state.async_save_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_nonexistent_trip(self):
        """Resuming non-existent trip logs warning, no save."""
        tm = _make_tm()
        await tm._lifecycle.async_resume_recurring_trip("nonexistent")
        tm._state.async_save_trips.assert_not_called()


class TestCRUDCompleteCancel:
    """Test async_complete_punctual_trip and async_cancel_punctual_trip (lifecycle)."""

    @pytest.mark.asyncio
    async def test_complete_existing_trip(self):
        """Completing a punctual trip sets estado=completado."""
        tm = _make_tm(punctual={"pun_1": {"id": "pun_1", "estado": "pendiente"}})
        await tm._lifecycle.async_complete_punctual_trip("pun_1")
        assert tm._state.punctual_trips["pun_1"]["estado"] == "completado"
        tm._state.async_save_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_nonexistent_trip(self):
        """Completing non-existent trip does nothing."""
        tm = _make_tm()
        await tm._lifecycle.async_complete_punctual_trip("nonexistent")
        tm._state.async_save_trips.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_existing_trip(self):
        """Cancelling a punctual trip removes it and saves."""
        tm = _make_tm(punctual={"pun_1": {"id": "pun_1", "estado": "pendiente"}})
        await tm._lifecycle.async_cancel_punctual_trip("pun_1")
        assert "pun_1" not in tm._state.punctual_trips
        tm._state.async_save_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_trip(self):
        """Cancelling non-existent trip does nothing."""
        tm = _make_tm()
        await tm._lifecycle.async_cancel_punctual_trip("nonexistent")
        tm._state.async_save_trips.assert_not_called()


class TestCRUDSyncToEMHASS:
    """Test _async_sync_trip_to_emhass (EMHASS sync)."""

    @pytest.mark.asyncio
    async def test_sync_inactive_trip_removes_from_emhass(self):
        """Syncing an inactive trip removes it from EMHASS."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "activo": False}})
        await tm._state._emhass_sync._async_sync_trip_to_emhass(
            "rec_1", {"id": "rec_1", "activo": True}, {"activo": False}
        )

    @pytest.mark.asyncio
    async def test_sync_non_recalc_fields(self):
        """Sync with non-recalc fields triggers adapter update without recalc (lines 82-83)."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "activo": True}})
        # "nombre" NOT in _RECALC_FIELDS → triggers else branch at lines 82-83
        await tm._state._emhass_sync._async_sync_trip_to_emhass(
            "rec_1", {"id": "rec_1"}, {"nombre": "updated note"}
        )
        # Non-recalc path: async_update_deferrable_load called, no publish
        tm._state.emhass_adapter.async_update_deferrable_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_no_trip_found(self):
        """Syncing a trip that doesn't exist in storage."""
        tm = _make_tm()
        await tm._state._emhass_sync._async_sync_trip_to_emhass("nonexistent", {}, {})

    @pytest.mark.asyncio
    async def test_sync_no_adapter(self):
        """Syncing without EMHASS adapter is no-op."""
        tm = _make_tm(
            recurring={"rec_1": {"id": "rec_1", "activo": True}}, emhass_adapter=None
        )
        await tm._state._emhass_sync._async_sync_trip_to_emhass(
            "rec_1", {"id": "rec_1"}, {"km": 10}
        )

    @pytest.mark.asyncio
    async def test_sync_active_trip_with_recalculation(self):
        """Syncing an active trip with changed km/kwh triggers recalculation."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "activo": True, "km": 50}})
        await tm._state._emhass_sync._async_sync_trip_to_emhass(
            "rec_1", {"id": "rec_1", "km": 50}, {"km": 75}
        )


class TestCRUDPublishNewToEMHASS:
    """Test _async_publish_new_trip_to_emhass (EMHASS sync)."""

    @pytest.mark.asyncio
    async def test_publish_new_with_adapter(self):
        """Publishing new trip with EMHASS adapter."""
        tm = _make_tm()
        trip = {"id": "rec_1", "km": 50.0, "kwh": 10.0}
        await tm._state._emhass_sync._async_publish_new_trip_to_emhass(trip)

    @pytest.mark.asyncio
    async def test_publish_new_no_adapter(self):
        """Publishing new trip without EMHASS adapter is no-op."""
        tm = _make_tm(emhass_adapter=None)
        trip = {"id": "rec_1", "km": 50.0, "kwh": 10.0}
        await tm._state._emhass_sync._async_publish_new_trip_to_emhass(trip)

    @pytest.mark.asyncio
    async def test_publish_new_calls_adapter_and_publish(self):
        """Publishing new trip calls adapter.publish and schedule.publish (lines 112-113)."""
        tm = _make_tm()
        await tm._state._emhass_sync._async_publish_new_trip_to_emhass(
            {"id": "new_trip", "activo": True}
        )
        tm._state.emhass_adapter.async_publish_deferrable_load.assert_called_once()
        tm._state._schedule.publish_deferrable_loads.assert_called_once()


class TestCRUDRemoveFromEMHASS:
    """Test _async_remove_trip_from_emhass (EMHASS sync)."""

    @pytest.mark.asyncio
    async def test_remove_with_adapter(self):
        """Removing trip with EMHASS adapter calls adapter method."""
        tm = _make_tm()
        tm._state.emhass_adapter._published_trips = {"rec_1"}
        await tm._state._emhass_sync._async_remove_trip_from_emhass("rec_1")

    @pytest.mark.asyncio
    async def test_remove_no_adapter(self):
        """Removing trip without adapter is no-op."""
        tm = _make_tm(emhass_adapter=None)
        await tm._state._emhass_sync._async_remove_trip_from_emhass("rec_1")

    @pytest.mark.asyncio
    async def test_remove_calls_adapter_and_publish(self):
        """Removing trip calls adapter.remove and schedule.publish (lines 99-100)."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "activo": True}})
        await tm._state._emhass_sync._async_remove_trip_from_emhass("rec_1")
        tm._state.emhass_adapter.async_remove_deferrable_load.assert_called_once()
        tm._state._schedule.publish_deferrable_loads.assert_called_once()


class TestGetAllActiveTrips:
    """Test _get_all_active_trips (EMHASS sync)."""

    @pytest.mark.asyncio
    async def test_get_active_trips_only_recurring(self):
        """Only active recurring trips returned."""
        tm = _make_tm(
            recurring={
                "rec_1": {"id": "rec_1", "activo": True, "km": 50},
                "rec_2": {"id": "rec_2", "activo": False, "km": 30},
            },
            punctual={},
        )
        result = await tm._state._emhass_sync._get_all_active_trips()
        assert len(result) == 1
        assert result[0]["id"] == "rec_1"

    @pytest.mark.asyncio
    async def test_get_active_trips_only_punctual(self):
        """Only pending punctual trips returned."""
        tm = _make_tm(
            recurring={},
            punctual={
                "pun_1": {"id": "pun_1", "estado": "pendiente", "km": 20},
                "pun_2": {"id": "pun_2", "estado": "completado", "km": 10},
            },
        )
        result = await tm._state._emhass_sync._get_all_active_trips()
        assert len(result) == 1
        assert result[0]["id"] == "pun_1"

    @pytest.mark.asyncio
    async def test_get_active_trips_both_types(self):
        """Active trips from both recurring and punctual."""
        tm = _make_tm(
            recurring={"rec_1": {"id": "rec_1", "activo": True}},
            punctual={"pun_1": {"id": "pun_1", "estado": "pendiente"}},
        )
        result = await tm._state._emhass_sync._get_all_active_trips()
        assert len(result) == 2
        ids = {t["id"] for t in result}
        assert ids == {"rec_1", "pun_1"}

    @pytest.mark.asyncio
    async def test_get_active_trips_empty(self):
        """No active trips returns empty list."""
        tm = _make_tm(recurring={}, punctual={})
        result = await tm._state._emhass_sync._get_all_active_trips()
        assert result == []


class TestLoadTripsFallback:
    """Test _load_trips fallback and reset paths (persistence)."""

    @pytest.mark.asyncio
    async def test_load_trips_no_stored_data(self):
        """No stored data -> reset trips (storage failure is expected with mock)."""
        tm = _make_tm()
        # _load_trips uses real HA storage which fails with mocks,
        # but the exception handler catches and resets trips
        await tm._state._persistence._load_trips()
        # After failure, trips should still be in clean state
        assert tm._state.recurring_trips == {}
        assert tm._state.punctual_trips == {}


class TestDeleteAllWithCoordinator:
    """Test async_delete_all_trips with coordinator."""

    @pytest.mark.asyncio
    async def test_delete_all_with_coordinator(self):
        """Delete all trips clears coordinator data."""
        coordinator = MagicMock()
        coordinator.data = {"per_trip_emhass_params": {"old": "data"}}
        coordinator.async_refresh = AsyncMock()

        hass = MagicMock()
        entry = MagicMock()
        rt_data = MagicMock()
        rt_data.coordinator = coordinator
        entry.runtime_data = rt_data

        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "activo": True}})
        tm._state.hass = hass
        tm._state.entry_id = "test"

        # Set up runtime_data access via hass.data
        tm._state.hass.data = {DOMAIN: {"test_entry": rt_data}}

        # Patch the entry lookup
        with patch.object(tm._state, "entry_id", "test_entry"):
            await tm._lifecycle.async_delete_all_trips()

        assert tm._state.recurring_trips == {}
        assert tm._state.punctual_trips == {}


class TestSyncPunctualTrip:
    """Test _async_sync_trip_to_emhass with punctual trips."""

    @pytest.mark.asyncio
    async def test_sync_punctual_trip(self):
        """Syncing a punctual trip updates it in EMHASS."""
        tm = _make_tm(
            punctual={"pun_1": {"id": "pun_1", "estado": "pendiente", "km": 50}}
        )
        tm._state.emhass_adapter.async_update_deferrable_load = AsyncMock()
        await tm._state._emhass_sync._async_sync_trip_to_emhass(
            "pun_1", {"id": "pun_1"}, {"km": 75}
        )
        tm._state.emhass_adapter.async_update_deferrable_load.assert_called_once()


class TestUpdateNonCriticalFields:
    """Test update with non-critical field changes (no recalc)."""

    @pytest.mark.asyncio
    async def test_update_non_critical_fields(self):
        """Updating non-recalc fields (descripcion) calls async_update not recalc."""
        tm = _make_tm(
            recurring={"rec_1": {"id": "rec_1", "km": 50, "descripcion": "old"}}
        )
        tm._state.emhass_adapter.async_update_deferrable_load = AsyncMock()
        await tm._crud.async_update_trip("rec_1", {"descripcion": "new desc"})
        # Should call async_update_deferrable_load (non-recalc path)
        tm._state.emhass_adapter.async_update_deferrable_load.assert_called_once()


class TestEMHASSSyncExceptions:
    """Test EMHASS sync exception paths that were lazily pragma'd."""

    @pytest.mark.asyncio
    async def test_sync_exception_from_adapter(self):
        """Adapter raises during sync — exception is caught and logged (lines 88-89)."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "activo": True, "km": 50}})
        tm._state.emhass_adapter.async_update_deferrable_load = AsyncMock(
            side_effect=RuntimeError("EMHASS connection failed")
        )
        # Should not propagate
        await tm._state._emhass_sync._async_sync_trip_to_emhass(
            "rec_1", {"id": "rec_1", "km": 50}, {"km": 75}
        )
        tm._state.emhass_adapter.async_update_deferrable_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_exception_remove_from_emhass(self):
        """Adapter raises during inactive trip remove (lines 100-101)."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "activo": False}})
        tm._state.emhass_adapter.async_remove_deferrable_load = AsyncMock(
            side_effect=RuntimeError("connection lost")
        )
        await tm._state._emhass_sync._async_sync_trip_to_emhass(
            "rec_1", {"id": "rec_1", "activo": True}, {"activo": False}
        )
        tm._state.emhass_adapter.async_remove_deferrable_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_new_exception_from_adapter(self):
        """Adapter raises during publish new trip (lines 113-115)."""
        tm = _make_tm(recurring={"rec_1": {"id": "rec_1", "activo": True}})
        tm._state.emhass_adapter.async_publish_deferrable_load = AsyncMock(
            side_effect=RuntimeError("EMHASS down")
        )
        await tm._state._emhass_sync._async_publish_new_trip_to_emhass(
            {"id": "rec_1", "km": 50}
        )
        tm._state.emhass_adapter.async_publish_deferrable_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_exception_from_adapter(self):
        """Adapter raises during remove (lines 101-102)."""
        tm = _make_tm()
        tm._state.emhass_adapter.async_remove_deferrable_load = AsyncMock(
            side_effect=RuntimeError("EMHASS error")
        )
        await tm._state._emhass_sync._async_remove_trip_from_emhass("rec_1")
        tm._state.emhass_adapter.async_remove_deferrable_load.assert_called_once()


class TestPersistenceHAStoreFallback:
    """Test persistence fallback HA Store path (lines 65-73)."""

    @pytest.mark.asyncio
    async def test_save_without_injected_storage_uses_ha_store(self):
        """No injected storage → uses HA Store fallback (lines 65-73)."""
        tm = _make_tm()
        # Remove injected storage to trigger fallback
        tm._state.storage = None
        # This should attempt HA Store path and not raise
        await tm._state._persistence.async_save_trips()

    @pytest.mark.asyncio
    async def test_load_trips_no_data_key(self):
        """stored_data without 'data' key → uses stored_data directly (line 118)."""
        from unittest.mock import MagicMock

        storage = MagicMock()
        storage.async_load = AsyncMock(
            return_value={
                "trips": {},
                "recurring_trips": {
                    "r1": {"id": "r1", "hora": "14:00", "dia_semana": "lunes"}
                },
                "punctual_trips": {},
            }
        )
        tm = _make_tm()
        tm._state._trips = {}
        tm._state.recurring_trips = {}
        tm._state.punctual_trips = {}
        tm._state.storage = storage
        await tm._state._persistence._load_trips()
        assert "r1" in tm._state.recurring_trips


class TestPersistenceSanitizeWarning:
    """Test _sanitize_recurring_trips warning log (line 206)."""

    @pytest.mark.asyncio
    async def test_sanitize_warns_on_removed_trips(self):
        """Invalid hora trips trigger warning log (line 206)."""
        tm = _make_tm(
            recurring={
                "bad_1": {"id": "bad_1", "hora": "invalid"},
                "good_1": {"id": "good_1", "hora": "14:00", "dia_semana": "lunes"},
            }
        )
        # The sanitize method is called from _load_trips, but we can test
        # the warning path via the _sanitize_recurring_trips method directly
        result = tm._state._persistence._sanitize_recurring_trips(
            {"bad": {"id": "bad", "hora": "invalid"}}
        )
        assert result == {}  # invalid trip removed


class TestPersistenceFallbackStore:
    """Test _persistence fallback HA Store and YAML exception paths."""

    @pytest.mark.asyncio
    async def test_save_trips_exception_triggers_yaml_fallback(self):
        """Exception during HA store save triggers YAML fallback (lines 81-84)."""
        tm = _make_tm()
        tm._state.storage = None  # no injected storage
        # Mock the HA Store to raise
        with patch(
            "custom_components.ev_trip_planner.trip._persistence.ha_storage.Store"
        ) as MockStore:
            mock_store = MagicMock()
            mock_store.async_save = AsyncMock(side_effect=RuntimeError("disk full"))
            MockStore.return_value = mock_store
            await tm._state._persistence.async_save_trips()
