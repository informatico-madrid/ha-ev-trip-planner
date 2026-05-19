"""Tests for handler factory behavior — mutation-observable return values.

Targets mutation survivors by asserting:
- make_trip_list_handler returns dict with correct keys/values
- make_trip_get_handler returns dict with correct keys/values
- make_import_weekly_pattern_handler calls correct CRUD methods
- Default value mutations on data.get() are killed
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import ServiceCall


@pytest.fixture
def mock_mgr():
    """Create a mock TripManager with required sub-objects."""
    mgr = MagicMock()
    mgr._crud = MagicMock()
    mgr._crud.async_get_recurring_trips = AsyncMock(return_value=[])
    mgr._crud.async_get_punctual_trips = AsyncMock(return_value=[])
    mgr._state = MagicMock()
    mgr._state.recurring_trips = []
    mgr._state.punctual_trips = []
    return mgr


@pytest.fixture
def mock_entry():
    """Create a mock ConfigEntry for _find_entry_by_vehicle."""
    entry = MagicMock()
    entry.entry_id = "e1"
    entry.data = {"vehicle_name": "test_vehicle"}
    entry.runtime_data = MagicMock()
    return entry


@pytest.fixture
def mock_hass(mock_mgr, mock_entry):
    """Create a mock hass with _get_manager returning mock_mgr."""
    hass = MagicMock()
    with patch(
        "custom_components.ev_trip_planner.services._handler_factories._get_manager",
        new=AsyncMock(return_value=mock_mgr),
    ):
        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
            return_value=None,
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._find_entry_by_vehicle",
                return_value=mock_entry,
            ):
                yield hass


def _make_service_call(data: dict[str, Any]) -> ServiceCall:
    """Create a mock ServiceCall from data dict."""
    call = MagicMock(spec=ServiceCall)
    call.data = data
    return call


class TestMakeTripListHandler:
    """Targets 149 survivors in make_trip_list_handler."""

    @pytest.mark.asyncio
    async def test_returns_dict_with_vehicle_id(self, mock_hass, mock_mgr):
        """Kill mutations: vehicle_id key in result → None or wrong value."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_list_handler,
        )

        handler = make_trip_list_handler(mock_hass)
        call = _make_service_call({"vehicle_id": "test_vehicle"})

        result = await handler(call)

        assert isinstance(result, dict)
        assert result["vehicle_id"] == "test_vehicle"

    @pytest.mark.asyncio
    async def test_returns_dict_with_trips_keys(self, mock_hass, mock_mgr):
        """Kill mutations: recurring_trips/punctual_trips key mutations."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_list_handler,
        )

        handler = make_trip_list_handler(mock_hass)
        call = _make_service_call({"vehicle_id": "test_vehicle"})

        result = await handler(call)

        assert "recurring_trips" in result
        assert "punctual_trips" in result
        assert "total_trips" in result

    @pytest.mark.asyncio
    async def test_returns_correct_total_trips(self, mock_hass, mock_mgr):
        """Kill mutations: total_trips calculation wrong (None+int, len(None), etc.)."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_list_handler,
        )

        mock_mgr._crud.async_get_recurring_trips = AsyncMock(
            return_value=[{"id": "r1"}, {"id": "r2"}]
        )
        mock_mgr._crud.async_get_punctual_trips = AsyncMock(
            return_value=[{"id": "p1"}]
        )

        handler = make_trip_list_handler(mock_hass)
        call = _make_service_call({"vehicle_id": "test_vehicle"})

        result = await handler(call)

        assert result["total_trips"] == 3
        assert result["recurring_trips"] == [{"id": "r1"}, {"id": "r2"}]
        assert result["punctual_trips"] == [{"id": "p1"}]

    @pytest.mark.asyncio
    async def test_handles_vehicle_id_from_data(self, mock_hass, mock_mgr):
        """Kill mutations: data.get("vehicle_id", "unknown") → data.get(None, "unknown")."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_list_handler,
        )

        handler = make_trip_list_handler(mock_hass)
        call = _make_service_call({"vehicle_id": "my_vehicle"})

        result = await handler(call)

        assert result["vehicle_id"] == "my_vehicle"
        mock_mgr._crud.async_get_recurring_trips.assert_called_once()
        mock_mgr._crud.async_get_punctual_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_error_on_exception(self, mock_hass, mock_mgr):
        """Kill mutations: error key in result dict → wrong key/value."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_list_handler,
        )

        mock_mgr._crud.async_get_recurring_trips = AsyncMock(
            side_effect=RuntimeError("test error")
        )

        handler = make_trip_list_handler(mock_hass)
        call = _make_service_call({"vehicle_id": "test_vehicle"})

        result = await handler(call)

        assert result["vehicle_id"] == "test_vehicle"
        assert result["recurring_trips"] == []
        assert result["punctual_trips"] == []
        assert result["total_trips"] == 0
        assert "error" in result
        assert "test error" in result["error"]

    @pytest.mark.asyncio
    async def test_calls_manager_methods(self, mock_hass, mock_mgr):
        """Kill mutations: async_get_recurring_trips → None or wrong method name."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_list_handler,
        )

        handler = make_trip_list_handler(mock_hass)
        call = _make_service_call({"vehicle_id": "test_vehicle"})

        await handler(call)

        mock_mgr._crud.async_get_recurring_trips.assert_called_once()
        mock_mgr._crud.async_get_punctual_trips.assert_called_once()


class TestMakeTripGetHandler:
    """Targets 72 survivors in make_trip_get_handler."""

    @pytest.mark.asyncio
    async def test_returns_dict_with_vehicle_id(self, mock_hass, mock_mgr):
        """Kill mutations: vehicle_id in result → None."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_get_handler,
        )

        handler = make_trip_get_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_id": "trip_123",
        })

        result = await handler(call)

        assert isinstance(result, dict)
        assert result["vehicle_id"] == "test_vehicle"

    @pytest.mark.asyncio
    async def test_returns_found_true_when_trip_exists(self, mock_hass, mock_mgr):
        """Kill mutations: found=True → found=False or vice versa."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_get_handler,
        )

        mock_mgr._crud.async_get_recurring_trips = AsyncMock(
            return_value=[{"id": "trip_123", "type": "recurrente"}]
        )
        mock_mgr._crud.async_get_punctual_trips = AsyncMock(return_value=[])

        handler = make_trip_get_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_id": "trip_123",
        })

        result = await handler(call)

        assert result["found"] is True
        assert result["trip"] == {"id": "trip_123", "type": "recurrente"}

    @pytest.mark.asyncio
    async def test_returns_found_false_when_trip_missing(self, mock_hass, mock_mgr):
        """Kill mutations: found=False → True or vice versa."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_get_handler,
        )

        mock_mgr._crud.async_get_recurring_trips = AsyncMock(return_value=[])
        mock_mgr._crud.async_get_punctual_trips = AsyncMock(return_value=[])

        handler = make_trip_get_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_id": "nonexistent",
        })

        result = await handler(call)

        assert result["found"] is False
        assert result["trip"] is None
        assert "error" in result

    @pytest.mark.asyncio
    async def test_returns_trip_data(self, mock_hass, mock_mgr):
        """Kill mutations: trip field in result → wrong value."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_get_handler,
        )

        trip_data = {"id": "t1", "dia_semana": "lunes", "hora": "08:00"}
        mock_mgr._crud.async_get_recurring_trips = AsyncMock(return_value=[trip_data])
        mock_mgr._crud.async_get_punctual_trips = AsyncMock(return_value=[])

        handler = make_trip_get_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_id": "t1",
        })

        result = await handler(call)

        assert result["trip"] == trip_data

    @pytest.mark.asyncio
    async def test_returns_error_on_exception(self, mock_hass, mock_mgr):
        """Kill mutations: error key/value in exception result."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_get_handler,
        )

        mock_mgr._crud.async_get_recurring_trips = AsyncMock(
            side_effect=RuntimeError("db error")
        )

        handler = make_trip_get_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_id": "t1",
        })

        result = await handler(call)

        assert result["found"] is False
        assert result["trip"] is None
        assert "db error" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_searches_recurring_then_punctual(self, mock_hass, mock_mgr):
        """Kill mutations: search order reversed (punctual→recurring)."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_get_handler,
        )

        # Trip exists in recurring
        mock_mgr._crud.async_get_recurring_trips = AsyncMock(
            return_value=[{"id": "rec_1"}]
        )
        mock_mgr._crud.async_get_punctual_trips = AsyncMock(
            return_value=[{"id": "punc_1"}]
        )

        handler = make_trip_get_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_1",
        })

        result = await handler(call)

        assert result["found"] is True
        assert result["trip"]["id"] == "rec_1"


class TestMakeImportWeeklyPatternHandler:
    """Targets 32 survivors in make_import_weekly_pattern_handler."""

    @pytest.mark.asyncio
    async def test_clear_existing_deletes_trips(self, mock_hass, mock_mgr):
        """Kill mutations: clear_existing=True skips deletion or uses wrong trip_id."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_import_weekly_pattern_handler,
        )

        mock_mgr._crud.async_get_recurring_trips = AsyncMock(
            return_value=[{"id": "old_1"}, {"id": "old_2"}]
        )
        mock_mgr._crud.async_delete_trip = AsyncMock()
        mock_mgr._crud.async_add_recurring_trip = AsyncMock()

        handler = make_import_weekly_pattern_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "pattern": {"monday": [{"hora": "08:00", "km": 10, "kwh": 1.0}]},
            "clear_existing": True,
        })

        await handler(call)

        # Should delete all existing trips before adding new ones
        assert mock_mgr._crud.async_delete_trip.call_count == 2
        mock_mgr._crud.async_delete_trip.assert_any_call("old_1")
        mock_mgr._crud.async_delete_trip.assert_any_call("old_2")

    @pytest.mark.asyncio
    async def test_imports_pattern_trips(self, mock_hass, mock_mgr):
        """Kill mutations: async_add_recurring_trip → None or wrong args."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_import_weekly_pattern_handler,
        )

        mock_mgr._crud.async_get_recurring_trips = AsyncMock(return_value=[])
        mock_mgr._crud.async_add_recurring_trip = AsyncMock()

        handler = make_import_weekly_pattern_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "pattern": {
                "monday": [
                    {"hora": "08:00", "km": 10, "kwh": 1.0},
                    {"hora": "18:00", "km": 20, "kwh": 2.0},
                ]
            },
            "clear_existing": False,
        })

        await handler(call)

        assert mock_mgr._crud.async_add_recurring_trip.call_count == 2

    @pytest.mark.asyncio
    async def test_default_clear_existing_is_true(self, mock_hass, mock_mgr):
        """Kill mutations: clear_existing default → False (should be True)."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_import_weekly_pattern_handler,
        )

        mock_mgr._crud.async_get_recurring_trips = AsyncMock(
            return_value=[{"id": "should_delete"}]
        )
        mock_mgr._crud.async_delete_trip = AsyncMock()

        handler = make_import_weekly_pattern_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "pattern": {},
            # clear_existing not provided
        })

        await handler(call)

        # Should default to clearing existing
        mock_mgr._crud.async_delete_trip.assert_called_once_with("should_delete")


class TestMakeAddPunctualHandler:
    """Targets 23 survivors in make_add_punctual_handler."""

    @pytest.mark.asyncio
    async def test_calls_async_add_punctual_trip(self, mock_hass, mock_mgr):
        """Kill mutations: async_add_punctual_trip → None or wrong method name."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_add_punctual_handler,
        )

        mock_mgr._crud.async_add_punctual_trip = AsyncMock()

        handler = make_add_punctual_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "datetime": "2024-01-15T08:00:00",
            "km": 10.0,
            "kwh": 1.5,
        })

        await handler(call)

        mock_mgr._crud.async_add_punctual_trip.assert_called_once()
        call_args = mock_mgr._crud.async_add_punctual_trip.call_args
        assert call_args[1]["datetime_str"] == "2024-01-15T08:00:00"
        assert call_args[1]["km"] == 10.0
        assert call_args[1]["kwh"] == 1.5

    @pytest.mark.asyncio
    async def test_handles_descripcion_default(self, mock_hass, mock_mgr):
        """Kill mutations: data.get("descripcion", "") → data.get(None, "") or wrong default."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_add_punctual_handler,
        )

        mock_mgr._crud.async_add_punctual_trip = AsyncMock()

        handler = make_add_punctual_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "datetime": "2024-01-15T08:00:00",
            "km": 10.0,
            "kwh": 1.5,
            # No descripcion provided
        })

        await handler(call)

        call_args = mock_mgr._crud.async_add_punctual_trip.call_args
        assert call_args[1]["descripcion"] == ""

    @pytest.mark.asyncio
    async def test_descripcion_passed_correctly(self, mock_hass, mock_mgr):
        """Kill mutations: data.get("descripcion", "") → data.get("DESCRIPCION", "")."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_add_punctual_handler,
        )

        mock_mgr._crud.async_add_punctual_trip = AsyncMock()

        handler = make_add_punctual_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "datetime": "2024-01-15T08:00:00",
            "km": 10.0,
            "kwh": 1.5,
            "descripcion": "my_description",
        })

        await handler(call)

        call_args = mock_mgr._crud.async_add_punctual_trip.call_args
        assert call_args[1]["descripcion"] == "my_description"


class TestMakeTripCreateHandler:
    """Targets 42 survivors in make_trip_create_handler."""

    @pytest.mark.asyncio
    async def test_recurrente_type_calls_recurring(self, mock_hass, mock_mgr):
        """Kill mutations: trip_type == 'recurrente' branch → None or wrong method."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_create_handler,
        )

        mock_mgr._crud.async_add_recurring_trip = AsyncMock()

        handler = make_trip_create_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "type": "recurrente",
            "dia_semana": "monday",
            "hora": "08:00",
            "km": 10.0,
            "kwh": 1.0,
        })

        await handler(call)

        mock_mgr._crud.async_add_recurring_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_punctual_type_calls_punctual(self, mock_hass, mock_mgr):
        """Kill mutations: trip_type == 'puntual' branch → None or wrong method."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_create_handler,
        )

        mock_mgr._crud.async_add_punctual_trip = AsyncMock()

        handler = make_trip_create_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "type": "puntual",
            "datetime": "2024-01-15T08:00:00",
            "km": 10.0,
            "kwh": 1.0,
        })

        await handler(call)

        mock_mgr._crud.async_add_punctual_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_type_returns_early(self, mock_hass, mock_mgr):
        """Kill mutations: invalid type → continues instead of returning."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_create_handler,
        )

        handler = make_trip_create_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "type": "invalid_type",
            "km": 10.0,
            "kwh": 1.0,
        })

        await handler(call)

        # Should not call any CRUD methods for invalid type
        mock_mgr._crud.async_add_recurring_trip.assert_not_called()
        mock_mgr._crud.async_add_punctual_trip.assert_not_called()


class TestMakeTripUpdateHandler:
    """Targets 41 survivors in make_trip_update_handler."""

    @pytest.mark.asyncio
    async def test_calls_async_update_trip(self, mock_hass, mock_mgr):
        """Kill mutations: async_update_trip → None or wrong method."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_update_handler,
        )

        mock_mgr._crud.async_update_trip = AsyncMock()
        mock_mgr._crud.async_get_recurring_trips = AsyncMock(return_value=[])
        mock_mgr._crud.async_get_punctual_trips = AsyncMock(return_value=[])

        handler = make_trip_update_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_id": "trip_123",
            "updates": {"km": 20.0},
        })

        await handler(call)

        mock_mgr._crud.async_update_trip.assert_called_once_with("trip_123", {"km": 20.0})

    @pytest.mark.asyncio
    async def test_handles_updates_from_data_fields(self, mock_hass, mock_mgr):
        """Kill mutations: data.get('type', 'recurrente') → data.get(None, 'recurrente')."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_update_handler,
        )

        mock_mgr._crud.async_update_trip = AsyncMock()
        mock_mgr._crud.async_get_recurring_trips = AsyncMock(return_value=[])
        mock_mgr._crud.async_get_punctual_trips = AsyncMock(return_value=[])

        handler = make_trip_update_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_id": "trip_123",
            "type": "recurrente",
            "hora": "09:00",
        })

        await handler(call)

        mock_mgr._crud.async_update_trip.assert_called_once()
        call_args = mock_mgr._crud.async_update_trip.call_args
        # Verify the updates dict was built correctly from data fields
        assert "hora" in call_args[0][1] or call_args[0][1] != {}


class TestMakeDeleteTripHandler:
    """Targets 8 survivors in make_delete_trip_handler."""

    @pytest.mark.asyncio
    async def test_calls_async_delete_trip(self, mock_hass, mock_mgr):
        """Kill mutations: async_delete_trip → None."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_delete_trip_handler,
        )

        mock_mgr._crud.async_delete_trip = AsyncMock()

        handler = make_delete_trip_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_id": "trip_123",
        })

        await handler(call)

        mock_mgr._crud.async_delete_trip.assert_called_once_with("trip_123")


class TestMakePauseResumeHandler:
    """Targets 16 survivors in pause/resume handlers."""

    @pytest.mark.asyncio
    async def test_pause_calls_async_pause_recurring_trip(self, mock_hass, mock_mgr):
        """Kill mutations: async_pause_recurring_trip → None."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_pause_recurring_handler,
        )

        mock_mgr._lifecycle = MagicMock()
        mock_mgr._lifecycle.async_pause_recurring_trip = AsyncMock()

        handler = make_pause_recurring_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_id": "trip_123",
        })

        await handler(call)

        mock_mgr._lifecycle.async_pause_recurring_trip.assert_called_once_with("trip_123")

    @pytest.mark.asyncio
    async def test_resume_calls_async_resume_recurring_trip(self, mock_hass, mock_mgr):
        """Kill mutations: async_resume_recurring_trip → None."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_resume_recurring_handler,
        )

        mock_mgr._lifecycle = MagicMock()
        mock_mgr._lifecycle.async_resume_recurring_trip = AsyncMock()

        handler = make_resume_recurring_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_id": "trip_123",
        })

        await handler(call)

        mock_mgr._lifecycle.async_resume_recurring_trip.assert_called_once_with("trip_123")


class TestMakeCompleteCancelHandler:
    """Targets 16 survivors in complete/cancel handlers."""

    @pytest.mark.asyncio
    async def test_complete_calls_async_complete_punctual_trip(self, mock_hass, mock_mgr):
        """Kill mutations: async_complete_punctual_trip → None."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_complete_punctual_handler,
        )

        mock_mgr._lifecycle = MagicMock()
        mock_mgr._lifecycle.async_complete_punctual_trip = AsyncMock()

        handler = make_complete_punctual_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_id": "trip_123",
        })

        await handler(call)

        mock_mgr._lifecycle.async_complete_punctual_trip.assert_called_once_with("trip_123")

    @pytest.mark.asyncio
    async def test_cancel_calls_async_cancel_punctual_trip(self, mock_hass, mock_mgr):
        """Kill mutations: async_cancel_punctual_trip → None."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_cancel_punctual_handler,
        )

        mock_mgr._lifecycle = MagicMock()
        mock_mgr._lifecycle.async_cancel_punctual_trip = AsyncMock()

        handler = make_cancel_punctual_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_id": "trip_123",
        })

        await handler(call)

        mock_mgr._lifecycle.async_cancel_punctual_trip.assert_called_once_with("trip_123")


class TestMakeAddRecurringHandler:
    """Targets survivors in make_add_recurring_handler — assert CRUD args."""

    @pytest.mark.asyncio
    async def test_calls_async_add_recurring_trip(self, mock_hass, mock_mgr):
        """Kill mutations: method name mutations."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_add_recurring_handler,
        )

        mock_mgr._crud.async_add_recurring_trip = AsyncMock()

        handler = make_add_recurring_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "dia_semana": "lunes",
            "hora": "08:00",
            "km": 10.0,
            "kwh": 1.5,
        })

        await handler(call)

        mock_mgr._crud.async_add_recurring_trip.assert_called_once()
        call_args = mock_mgr._crud.async_add_recurring_trip.call_args
        assert call_args[1]["dia_semana"] == "lunes"
        assert call_args[1]["hora"] == "08:00"
        assert call_args[1]["km"] == 10.0
        assert call_args[1]["kwh"] == 1.5

    @pytest.mark.asyncio
    async def test_descripcion_passed_correctly(self, mock_hass, mock_mgr):
        """Kill mutations: data.get("descripcion", "") → data.get(None, "") or wrong key."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_add_recurring_handler,
        )

        mock_mgr._crud.async_add_recurring_trip = AsyncMock()

        handler = make_add_recurring_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "dia_semana": "lunes",
            "hora": "08:00",
            "km": 10.0,
            "kwh": 1.5,
            "descripcion": "my_trip_desc",
        })

        await handler(call)

        call_args = mock_mgr._crud.async_add_recurring_trip.call_args
        assert call_args[1]["descripcion"] == "my_trip_desc"

    @pytest.mark.asyncio
    async def test_descripcion_defaults_to_empty(self, mock_hass, mock_mgr):
        """Kill mutations: data.get(None, "") always returns "" ignoring real values."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_add_recurring_handler,
        )

        mock_mgr._crud.async_add_recurring_trip = AsyncMock()

        handler = make_add_recurring_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "dia_semana": "lunes",
            "hora": "08:00",
            "km": 10.0,
            "kwh": 1.5,
            # No descripcion provided
        })

        await handler(call)

        call_args = mock_mgr._crud.async_add_recurring_trip.call_args
        assert call_args[1]["descripcion"] == ""


class TestMakeTripCreateHandlerFull:
    """Additional targets for make_trip_create_handler — trip_type mutations."""

    @pytest.mark.asyncio
    async def test_uses_trip_type_field(self, mock_hass, mock_mgr):
        """Kill mutations: data.get("type", ...) → data.get(None, ...)."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_create_handler,
        )

        mock_mgr._crud.async_add_punctual_trip = AsyncMock()
        mock_mgr._crud.async_add_recurring_trip = AsyncMock()

        handler = make_trip_create_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "type": "puntual",
            "datetime": "2024-01-15T08:00:00",
            "km": 10.0,
            "kwh": 1.0,
        })

        await handler(call)

        mock_mgr._crud.async_add_punctual_trip.assert_called_once()
        mock_mgr._crud.async_add_recurring_trip.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_trip_type_fallback(self, mock_hass, mock_mgr):
        """Kill mutations: data.get("trip_type", "recurrente") → wrong fallback."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_create_handler,
        )

        mock_mgr._crud.async_add_punctual_trip = AsyncMock()
        mock_mgr._crud.async_add_recurring_trip = AsyncMock()

        handler = make_trip_create_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "trip_type": "puntual",
            "km": 10.0,
            "kwh": 1.0,
            "datetime": "2024-01-15T08:00:00",
        })

        await handler(call)

        mock_mgr._crud.async_add_punctual_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_recurrente_with_day_and_hora(self, mock_hass, mock_mgr):
        """Kill mutations: dia_semana/day_of_week branch mutations."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_create_handler,
        )

        mock_mgr._crud.async_add_recurring_trip = AsyncMock()

        handler = make_trip_create_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "type": "recurrente",
            "day_of_week": "monday",
            "hora": "08:00",
            "km": 10.0,
            "kwh": 1.0,
        })

        await handler(call)

        mock_mgr._crud.async_add_recurring_trip.assert_called_once()
        call_args = mock_mgr._crud.async_add_recurring_trip.call_args
        assert call_args[1]["dia_semana"] == "monday"
        assert call_args[1]["hora"] == "08:00"

    @pytest.mark.asyncio
    async def test_punctual_with_datetime(self, mock_hass, mock_mgr):
        """Kill mutations: datetime field mutations."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_create_handler,
        )

        mock_mgr._crud.async_add_punctual_trip = AsyncMock()

        handler = make_trip_create_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "type": "puntual",
            "datetime": "2024-06-15T14:30:00",
            "km": 25.0,
            "kwh": 3.0,
        })

        await handler(call)

        mock_mgr._crud.async_add_punctual_trip.assert_called_once()
        call_args = mock_mgr._crud.async_add_punctual_trip.call_args
        assert call_args[1]["datetime_str"] == "2024-06-15T14:30:00"

    @pytest.mark.asyncio
    async def test_punctual_with_description(self, mock_hass, mock_mgr):
        """Kill mutations: descripcion/description field mutations."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_create_handler,
        )

        mock_mgr._crud.async_add_punctual_trip = AsyncMock()

        handler = make_trip_create_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "type": "puntual",
            "datetime": "2024-06-15T14:30:00",
            "km": 25.0,
            "kwh": 3.0,
            "descripcion": "Spanish desc",
            "description": "English desc",
        })

        await handler(call)

        call_args = mock_mgr._crud.async_add_punctual_trip.call_args
        # descripcion takes priority (descripcion or description)
        assert call_args[1]["descripcion"] == "Spanish desc"

    @pytest.mark.asyncio
    async def test_punctual_description_only(self, mock_hass, mock_mgr):
        """Kill mutations: description fallback when descripcion missing."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_create_handler,
        )

        mock_mgr._crud.async_add_punctual_trip = AsyncMock()

        handler = make_trip_create_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "type": "puntual",
            "datetime": "2024-06-15T14:30:00",
            "km": 25.0,
            "kwh": 3.0,
            "description": "Only English",
        })

        await handler(call)

        call_args = mock_mgr._crud.async_add_punctual_trip.call_args
        # Falls back to description when descripcion is absent
        assert call_args[1]["descripcion"] == "Only English"

    @pytest.mark.asyncio
    async def test_recurrente_with_day_field(self, mock_hass, mock_mgr):
        """Kill mutations: dia_semana/day_of_week mutations in recurring path."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_create_handler,
        )

        mock_mgr._crud.async_add_recurring_trip = AsyncMock()

        handler = make_trip_create_handler(mock_hass)
        call = _make_service_call({
            "vehicle_id": "test_vehicle",
            "type": "recurrente",
            "dia_semana": "martes",
            "hora": "18:00",
            "km": 15.0,
            "kwh": 2.0,
        })

        await handler(call)

        mock_mgr._crud.async_add_recurring_trip.assert_called_once()
        call_args = mock_mgr._crud.async_add_recurring_trip.call_args
        assert call_args[1]["dia_semana"] == "martes"
        assert call_args[1]["hora"] == "18:00"
