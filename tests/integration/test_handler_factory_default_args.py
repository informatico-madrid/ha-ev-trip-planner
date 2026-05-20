"""Integration tests targeting remove_arg and string_mutate survivors in _handler_factories.

These tests deliberately omit optional fields from service call data to exercise
the default-value paths in handler code. Mutations that remove .get() defaults
(data.get("key", "default") -> data.get("key", )) or remove dict keys
(str(item.get("key", "")) -> str(item.get(""))) become visible when the key
is absent and the default is actually needed.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import ServiceCall

from custom_components.ev_trip_planner.services._handler_factories import (
    make_add_punctual_handler,
    make_add_recurring_handler,
    make_cancel_punctual_handler,
    make_complete_punctual_handler,
    make_delete_trip_handler,
    make_edit_trip_handler,
    make_import_weekly_pattern_handler,
    make_pause_recurring_handler,
    make_resume_recurring_handler,
    make_trip_create_handler,
    make_trip_get_handler,
    make_trip_list_handler,
    make_trip_update_handler,
)

from tests.integration.conftest import _build_hass

logger = logging.getLogger(__name__)


class _NullStore:
    """Minimal Store mock that returns None on load."""

    def __init__(self, *a, **kw):
        pass

    async def async_load(self):
        return None

    async def async_save(self, data):
        return True


@pytest.fixture(autouse=True)
def null_store():
    with patch("homeassistant.helpers.storage.Store", _NullStore):
        yield


class TestTripUpdateRemoveArgMutations:
    """Test make_trip_update_handler remove_arg mutations.

    Survivors in this handler include:
    - data.get("type", "recurrente") -> data.get("type", ) — remove_arg
    - data.get("vehicle_id", "unknown") variants
    """

    @pytest.mark.asyncio
    async def test_update_without_type_field_exercises_default(self):
        """Handler without 'type' field uses default 'recurrente' path.

        Mutation data.get("type", "recurrente") -> data.get("type", ) would
        set trip_type = None, causing the recurrente vs puntual branch to
        follow a wrong path and query wrong trip lists.
        """
        trip_data = {"id": "rec_1", "dia_semana": "lunes", "hora": "09:00"}
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_update_trip": {"return_value": True},
                "_crud.async_get_recurring_trips": {"return_value": [trip_data]},
                "_crud.async_get_punctual_trips": {"return_value": []},
            }
        )

        handler = make_trip_update_handler(hass)
        # Deliberately omit 'type' — handler must use default
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_1",
            "dia_semana": "martes",  # triggers recurrente branch
            # NOTE: 'type' is intentionally omitted
        }
        result = await handler(call)

        # Should succeed — handler found trip via default 'recurrente' path
        mgr._crud.async_update_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_with_explicit_type(self):
        """Handler with explicit 'type' field uses that value."""
        trip_data = {"id": "pun_1", "datetime": "2025-12-01"}
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_update_trip": {"return_value": True},
                "_crud.async_get_punctual_trips": {"return_value": [trip_data]},
                "_crud.async_get_recurring_trips": {"return_value": []},
            }
        )

        handler = make_trip_update_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "pun_1",
            "type": "puntual",
            "dia_semana": "martes",
        }
        await handler(call)

        mgr._crud.async_update_trip.assert_called_once()


class TestTripListRemoveArgMutations:
    """Test make_trip_list_handler remove_arg mutations.

    Survivors include:
    - data.get("vehicle_id", "unknown") -> data.get("vehicle_id", ) — remove_arg
    - len(mgr._state.punctual_trips) — remove_arg on len
    - str(item.get("descripcion", "")) — not in this handler
    """

    @pytest.mark.asyncio
    async def test_list_without_vehicle_id_exercises_default(self):
        """Handler without 'vehicle_id' uses default 'unknown'.

        Mutation: data.get("vehicle_id", "unknown") -> data.get("vehicle_id", )
        changes vehicle_id from "unknown" to None.
        """
        # Need a matching config entry so "unknown" vehicle_id resolves
        from tests.integration.conftest import _MockConfigEntry
        from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

        hass = MagicMock()
        hass.data = {}
        hass.config_entries = MagicMock()
        entry = _MockConfigEntry("unknown")
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()
        entry.runtime_data = EVTripRuntimeData(
            coordinator=coordinator, trip_manager=AsyncMock()
        )
        hass.config_entries.async_entries = MagicMock(return_value=[entry])
        hass.config_entries.async_get_entry = MagicMock(return_value=entry)

        handler = make_trip_list_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {}  # No vehicle_id — handler uses default
        result = await handler(call)

        assert "vehicle_id" in result
        assert result["total_trips"] == 0

    @pytest.mark.asyncio
    async def test_list_with_trips_exercises_len_mutations(self):
        """Handler with trips exercises len(mgr._state.punctual_trips).

        Mutation: len(mgr._state.punctual_trips) -> len(mgr._state.punctual_trips, )
        is a remove_arg on len() which would crash at runtime, killing this test.
        """
        recurring = [{"id": "rec_1", "tipo": "recurrente", "activo": True}]
        punctual = [{"id": "pun_1", "tipo": "puntual", "estado": "pendiente"}]
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_get_recurring_trips": {"return_value": recurring},
                "_crud.async_get_punctual_trips": {"return_value": punctual},
            }
        )

        handler = make_trip_list_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle"}
        result = await handler(call)

        assert result["total_trips"] == 2
        assert len(result["recurring_trips"]) == 1
        assert len(result["punctual_trips"]) == 1


class TestTripGetRemoveArgMutations:
    """Test make_trip_get_handler remove_arg mutations."""

    @pytest.mark.asyncio
    async def test_get_without_trip_id_exercises_default(self):
        """Handler without trip_id uses default 'unknown' and returns not found.

        Mutation: data.get("trip_id", "unknown") -> data.get("trip_id", )
        changes trip_id from "unknown" to None.
        """
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_get_recurring_trips": {"return_value": []},
                "_crud.async_get_punctual_trips": {"return_value": []},
            }
        )

        handler = make_trip_get_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle"}  # No trip_id — uses default
        result = await handler(call)

        assert "vehicle_id" in result
        assert "found" in result
        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_get_with_both_ids(self):
        """Handler with both vehicle_id and trip_id finds the trip."""
        trip_data = {"id": "rec_1", "tipo": "recurrente", "dia_semana": "lunes"}
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_get_recurring_trips": {"return_value": [trip_data]},
                "_crud.async_get_punctual_trips": {"return_value": []},
            }
        )

        handler = make_trip_get_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "rec_1"}
        result = await handler(call)

        assert result["found"] is True
        assert result["trip"]["id"] == "rec_1"


class TestImportWeeklyPatternRemoveArgMutations:
    """Test make_import_weekly_pattern_handler remove_arg mutations.

    Survivors include:
    - str(item.get("descripcion", "")) -> str(item.get("")) — remove_arg
    """

    @pytest.mark.asyncio
    async def test_import_with_descripcion_field(self):
        """Handler passes descripcion field to async_add_recurring_trip."""
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_add_recurring_trip": {"return_value": "new_rec"},
            }
        )

        handler = make_import_weekly_pattern_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "clear_existing": False,
            "pattern": {
                "lunes": [
                    {
                        "hora": "09:00",
                        "km": 24,
                        "kwh": 3.6,
                        "descripcion": "mi ruta",
                    }
                ]
            },
        }
        await handler(call)

        call_args = mgr._crud.async_add_recurring_trip.call_args
        assert call_args[1]["descripcion"] == "mi ruta"

    @pytest.mark.asyncio
    async def test_import_without_descripcion_exercises_default(self):
        """Handler without descripcion uses default empty string.

        Mutation: str(item.get("descripcion", "")) -> str(item.get(""))
        changes the key from "descripcion" to "", which would return "" anyway
        but changes the code path in the mutated version.
        """
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_add_recurring_trip": {"return_value": "new_rec"},
            }
        )

        handler = make_import_weekly_pattern_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "clear_existing": False,
            "pattern": {
                "lunes": [{"hora": "09:00", "km": 24, "kwh": 3.6}]
                # No descripcion — handler uses default ""
            },
        }
        await handler(call)

        call_args = mgr._crud.async_add_recurring_trip.call_args
        assert call_args[1]["descripcion"] == ""

    @pytest.mark.asyncio
    async def test_import_clear_existing_exercises_delete_path(self):
        """Handler with clear_existing=True deletes old trips before importing."""
        old_trip = {
            "id": "old_rec",
            "dia_semana": "lunes",
            "hora": "08:00",
            "km": 10,
            "kwh": 1.5,
        }
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_get_recurring_trips": {"return_value": [old_trip]},
                "_crud.async_delete_trip": {"return_value": True},
                "_crud.async_add_recurring_trip": {"return_value": "new_rec"},
            }
        )

        handler = make_import_weekly_pattern_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "clear_existing": True,
            "pattern": {
                "lunes": [{"hora": "09:00", "km": 24, "kwh": 3.6}]
            },
        }
        await handler(call)

        assert mgr._crud.async_delete_trip.called
        assert mgr._crud.async_add_recurring_trip.called


class TestLifecycleHandlerRemoveArgMutations:
    """Test lifecycle handler factories for remove_arg mutations.

    These handlers use data["trip_id"] (direct access) but the mutation
    targets are on data.get() calls within the handler body.
    """

    @pytest.mark.asyncio
    async def test_pause_exercises_handler_path(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_lifecycle.async_pause_recurring_trip": {"return_value": True},
            }
        )
        handler = make_pause_recurring_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "rec_1"}
        await handler(call)
        mgr._lifecycle.async_pause_recurring_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_exercises_handler_path(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_lifecycle.async_resume_recurring_trip": {"return_value": True},
            }
        )
        handler = make_resume_recurring_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "rec_1"}
        await handler(call)
        mgr._lifecycle.async_resume_recurring_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_exercises_handler_path(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_lifecycle.async_complete_punctual_trip": {"return_value": True},
            }
        )
        handler = make_complete_punctual_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "pun_1"}
        await handler(call)
        mgr._lifecycle.async_complete_punctual_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_exercises_handler_path(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_lifecycle.async_cancel_punctual_trip": {"return_value": True},
            }
        )
        handler = make_cancel_punctual_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "pun_1"}
        await handler(call)
        mgr._lifecycle.async_cancel_punctual_trip.assert_called_once()


class TestTripCreateRemoveArgMutations:
    """Test make_trip_create_handler remove_arg mutations."""

    @pytest.mark.asyncio
    async def test_create_recurring_without_type_uses_default(self):
        """Handler without 'type' uses default 'recurrente' path.

        Mutation: data.get("type", data.get("trip_type", "recurrente"))
        -> data.get("type", data.get("trip_type", )) cascades remove_arg.
        """
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_add_recurring_trip": {"return_value": "rec_1"},
            }
        )

        handler = make_trip_create_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24,
            "kwh": 3.6,
        }
        await handler(call)

        mgr._crud.async_add_recurring_trip.assert_called_once()
        # Should use default 'recurrente'
        call_args = mgr._crud.async_add_recurring_trip.call_args
        assert call_args[1]["dia_semana"] == "lunes"

    @pytest.mark.asyncio
    async def test_create_punctual_without_type_uses_fallback(self):
        """Handler without 'type' defaults to 'recurrente' (nested default).

        The code is: data.get("type", data.get("trip_type", "recurrente"))
        When no type is provided, it falls through to "recurrente".
        This exercises the nested data.get() remove_arg mutation chain.
        """
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_add_recurring_trip": {"return_value": "rec_1"},
            }
        )

        handler = make_trip_create_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24,
            "kwh": 3.6,
        }
        await handler(call)

        # Should use default "recurrente" path
        mgr._crud.async_add_recurring_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_invalid_type_returns_early(self):
        """Handler with explicit invalid type returns without calling CRUD."""
        hass, entry, mgr, coord = _build_hass()
        handler = make_trip_create_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "type": "invalid",
            "km": 10,
            "kwh": 1,
        }
        await handler(call)
        assert not mgr.method_calls


class TestAddHandlerRemoveArgMutations:
    """Test add_recurring and add_punctual handler remove_arg mutations."""

    @pytest.mark.asyncio
    async def test_add_recurring_with_descripcion(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_add_recurring_trip": {"return_value": "rec_1"},
            }
        )
        handler = make_add_recurring_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24,
            "kwh": 3.6,
            "descripcion": "ruta matutina",
        }
        await handler(call)
        call_args = mgr._crud.async_add_recurring_trip.call_args
        assert call_args[1]["descripcion"] == "ruta matutina"

    @pytest.mark.asyncio
    async def test_add_recurring_without_descripcion_exercises_default(self):
        """Handler without descripcion uses default empty string.

        Mutation: str(data.get("descripcion", "")) -> str(data.get(""))
        changes key from "descripcion" to "", which in the mutated code
        still returns "" but is a different code path.
        """
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_add_recurring_trip": {"return_value": "rec_1"},
            }
        )
        handler = make_add_recurring_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24,
            "kwh": 3.6,
            # No descripcion — handler uses default ""
        }
        await handler(call)
        call_args = mgr._crud.async_add_recurring_trip.call_args
        assert call_args[1]["descripcion"] == ""

    @pytest.mark.asyncio
    async def test_add_punctual_with_descripcion(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_add_punctual_trip": {"return_value": "pun_1"},
            }
        )
        handler = make_add_punctual_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "datetime": "2025-12-01T10:00",
            "km": 100,
            "kwh": 15,
            "descripcion": "cita doctor",
        }
        await handler(call)
        call_args = mgr._crud.async_add_punctual_trip.call_args
        assert call_args[1]["descripcion"] == "cita doctor"

    @pytest.mark.asyncio
    async def test_add_punctual_without_descripcion_exercises_default(self):
        """Handler without descripcion uses default empty string."""
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_add_punctual_trip": {"return_value": "pun_1"},
            }
        )
        handler = make_add_punctual_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "datetime": "2025-12-01T10:00",
            "km": 100,
            "kwh": 15,
            # No descripcion
        }
        await handler(call)
        call_args = mgr._crud.async_add_punctual_trip.call_args
        assert call_args[1]["descripcion"] == ""

    @pytest.mark.asyncio
    async def test_edit_with_updates(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_update_trip": {"return_value": True},
            }
        )
        handler = make_edit_trip_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_1",
            "updates": {"km": 50, "descripcion": "actualizado"},
        }
        await handler(call)
        call_args = mgr._crud.async_update_trip.call_args
        # edit_trip passes: async_update_trip(trip_id, dict(updates))
        assert call_args[0][0] == "rec_1"
        updates = call_args[0][1]
        assert updates["km"] == 50
        assert updates["descripcion"] == "actualizado"
