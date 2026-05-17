"""Tests for uncovered services/_handler_factories.py paths.

Lines 74-87: make_add_recurring_handler body
Lines 99-111: make_add_punctual_handler body
Lines 132-149, 160-161: make_trip_update_handler body
Lines 177-183: make_trip_update_handler sensor update path
Lines 200-208: make_edit_trip_handler body
Lines 241-249: make_pause_recurring_handler body
Lines 261-269: make_resume_recurring_handler body
Lines 281-289: make_complete_punctual_handler body
Lines 301-309: make_cancel_punctual_handler body
Lines 382-401: make_import_weekly_pattern_handler body
Lines 486-490: make_trip_list_handler error path
Lines 508-568: make_trip_get_handler body
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


def _make_call(data: dict[str, Any]):
    """Create a mock ServiceCall."""
    call = MagicMock()
    call.data = data
    return call


def _make_manager():
    """Create a mock TripManager."""
    mgr = MagicMock()
    mgr._crud = MagicMock()
    mgr._crud.async_add_recurring_trip = AsyncMock()
    mgr._crud.async_add_punctual_trip = AsyncMock()
    mgr._crud.async_update_trip = AsyncMock()
    mgr._crud.async_delete_trip = AsyncMock()
    mgr._crud.async_get_recurring_trips = AsyncMock(return_value=[])
    mgr._crud.async_get_punctual_trips = AsyncMock(return_value=[])
    mgr._lifecycle = MagicMock()
    mgr._lifecycle.async_pause_recurring_trip = AsyncMock()
    mgr._lifecycle.async_resume_recurring_trip = AsyncMock()
    mgr._lifecycle.async_complete_punctual_trip = AsyncMock()
    mgr._lifecycle.async_cancel_punctual_trip = AsyncMock()
    mgr._lifecycle.async_delete_all_trips = AsyncMock()
    return mgr


class TestAddRecurringTrip:
    """Test make_add_recurring_handler (lines 74-87)."""

    @pytest.mark.asyncio
    async def test_add_recurring_calls_crud_and_refreshes(self):
        """Lines 74-87: Handler adds trip and refreshes coordinator."""
        hass = MagicMock()
        handler = make_add_recurring_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                call = _make_call({
                    "vehicle_id": "test_vehicle",
                    "dia_semana": "lunes",
                    "hora": "08:00",
                    "km": 30.0,
                    "kwh": 5.0,
                    "descripcion": "Test trip",
                })
                await handler(call)

        mgr._crud.async_add_recurring_trip.assert_called_once()
        coordinator.async_refresh_trips.assert_called_once()


class TestAddPunctualTrip:
    """Test make_add_punctual_handler (lines 99-111)."""

    @pytest.mark.asyncio
    async def test_add_punctual_calls_crud_and_refreshes(self):
        """Lines 99-111: Handler adds punctual trip and refreshes coordinator."""
        hass = MagicMock()
        handler = make_add_punctual_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                call = _make_call({
                    "vehicle_id": "test_vehicle",
                    "datetime": "2026-05-20T08:00:00+00:00",
                    "km": 30.0,
                    "kwh": 5.0,
                })
                await handler(call)

        mgr._crud.async_add_punctual_trip.assert_called_once()
        coordinator.async_refresh_trips.assert_called_once()


class TestDeleteTrip:
    """Test make_delete_trip_handler."""

    @pytest.mark.asyncio
    async def test_delete_trip_calls_crud_and_refreshes(self):
        """Lines 215-231: Handler deletes trip and refreshes coordinator."""
        hass = MagicMock()
        handler = make_delete_trip_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                call = _make_call({
                    "vehicle_id": "test_vehicle",
                    "trip_id": "123",
                })
                await handler(call)

        mgr._crud.async_delete_trip.assert_called_once()
        coordinator.async_refresh_trips.assert_called_once()


class TestPauseRecurring:
    """Test make_pause_recurring_handler."""

    @pytest.mark.asyncio
    async def test_pause_recurring_calls_lifecycle_and_refreshes(self):
        """Lines 237-252: Handler pauses recurring trip and refreshes."""
        hass = MagicMock()
        handler = make_pause_recurring_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                call = _make_call({
                    "vehicle_id": "test_vehicle",
                    "trip_id": "123",
                })
                await handler(call)

        mgr._lifecycle.async_pause_recurring_trip.assert_called_once()
        coordinator.async_refresh_trips.assert_called_once()


class TestResumeRecurring:
    """Test make_resume_recurring_handler."""

    @pytest.mark.asyncio
    async def test_resume_recurring_calls_lifecycle_and_refreshes(self):
        """Lines 257-272: Handler resumes recurring trip and refreshes."""
        hass = MagicMock()
        handler = make_resume_recurring_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                call = _make_call({
                    "vehicle_id": "test_vehicle",
                    "trip_id": "123",
                })
                await handler(call)

        mgr._lifecycle.async_resume_recurring_trip.assert_called_once()
        coordinator.async_refresh_trips.assert_called_once()


class TestCompletePunctual:
    """Test make_complete_punctual_handler."""

    @pytest.mark.asyncio
    async def test_complete_punctual_calls_lifecycle_and_refreshes(self):
        """Lines 277-292: Handler completes punctual trip and refreshes."""
        hass = MagicMock()
        handler = make_complete_punctual_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                call = _make_call({
                    "vehicle_id": "test_vehicle",
                    "trip_id": "123",
                })
                await handler(call)

        mgr._lifecycle.async_complete_punctual_trip.assert_called_once()
        coordinator.async_refresh_trips.assert_called_once()


class TestCancelPunctual:
    """Test make_cancel_punctual_handler."""

    @pytest.mark.asyncio
    async def test_cancel_punctual_calls_lifecycle_and_refreshes(self):
        """Lines 297-312: Handler cancels punctual trip and refreshes."""
        hass = MagicMock()
        handler = make_cancel_punctual_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                call = _make_call({
                    "vehicle_id": "test_vehicle",
                    "trip_id": "123",
                })
                await handler(call)

        mgr._lifecycle.async_cancel_punctual_trip.assert_called_once()
        coordinator.async_refresh_trips.assert_called_once()


class TestImportWeeklyPattern:
    """Test make_import_weekly_pattern_handler."""

    @pytest.mark.asyncio
    async def test_import_clears_existing_and_imports_pattern(self):
        """Lines 378-410: Handler clears existing and imports new pattern."""
        hass = MagicMock()
        handler = make_import_weekly_pattern_handler(hass)

        mgr = _make_manager()
        mgr._crud.async_get_recurring_trips = AsyncMock(return_value=[{"id": "old_trip"}])
        mgr._crud.async_delete_trip = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._ensure_setup",
                new=AsyncMock(),
            ):
                call = _make_call({
                    "vehicle_id": "test_vehicle",
                    "clear_existing": True,
                    "pattern": {
                        "1": [{"hora": "08:00", "km": 30.0, "kwh": 5.0}],
                    },
                })
                await handler(call)

        mgr._crud.async_delete_trip.assert_called_once()
        mgr._crud.async_add_recurring_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_skips_clear_on_exception(self):
        """Lines 390-393: Exception during get_recurring_trips → existing=[] (skips clear)."""
        hass = MagicMock()
        handler = make_import_weekly_pattern_handler(hass)

        mgr = _make_manager()
        mgr._crud.async_get_recurring_trips = AsyncMock(side_effect=Exception("DB error"))
        mgr._crud.async_delete_trip = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._ensure_setup",
                new=AsyncMock(),
            ):
                call = _make_call({
                    "vehicle_id": "test_vehicle",
                    "clear_existing": True,
                    "pattern": {
                        "1": [{"hora": "08:00", "km": 30.0, "kwh": 5.0}],
                    },
                })
                await handler(call)

        # Should NOT call delete_trip since existing=[] after exception
        mgr._crud.async_delete_trip.assert_not_called()
        mgr._crud.async_add_recurring_trip.assert_called_once()


class TestTripList:
    """Test make_trip_list_handler."""

    @pytest.mark.asyncio
    async def test_trip_list_returns_all_trips(self):
        """Lines 415-498: Handler returns all recurring and punctual trips."""
        hass = MagicMock()
        handler = make_trip_list_handler(hass)

        mgr = _make_manager()
        mgr._crud.async_get_recurring_trips = AsyncMock(
            return_value=[{"id": "r1", "tipo": "recurrente"}]
        )
        mgr._crud.async_get_punctual_trips = AsyncMock(
            return_value=[{"id": "p1", "tipo": "puntual"}]
        )

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            call = _make_call({"vehicle_id": "test_vehicle"})
            result = await handler(call)

        assert result["vehicle_id"] == "test_vehicle"
        assert len(result["recurring_trips"]) == 1
        assert len(result["punctual_trips"]) == 1
        assert result["total_trips"] == 2

    @pytest.mark.asyncio
    async def test_trip_list_returns_error_on_exception(self):
        """Lines 486-496: Handler returns error dict on exception."""
        hass = MagicMock()
        handler = make_trip_list_handler(hass)

        mgr = _make_manager()
        # Make async_get_recurring_trips raise so it's caught by handler's try/except
        mgr._crud.async_get_recurring_trips = AsyncMock(
            side_effect=Exception("DB error")
        )

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            call = _make_call({"vehicle_id": "test_vehicle"})
            result = await handler(call)

        assert "error" in result
        assert result["recurring_trips"] == []


class TestTripGet:
    """Test make_trip_get_handler."""

    @pytest.mark.asyncio
    async def test_trip_get_finds_trip_in_recurring(self):
        """Lines 504-575: Handler finds trip in recurring list."""
        hass = MagicMock()
        handler = make_trip_get_handler(hass)

        mgr = _make_manager()
        mgr._crud.async_get_recurring_trips = AsyncMock(
            return_value=[{"id": "123", "tipo": "recurrente", "activo": True}]
        )
        mgr._crud.async_get_punctual_trips = AsyncMock(return_value=[])

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            call = _make_call({"vehicle_id": "test_vehicle", "trip_id": "123"})
            result = await handler(call)

        assert result["found"] is True
        assert result["trip"]["id"] == "123"

    @pytest.mark.asyncio
    async def test_trip_get_not_found(self):
        """Lines 552-559: Handler returns not found when trip doesn't exist."""
        hass = MagicMock()
        handler = make_trip_get_handler(hass)

        mgr = _make_manager()
        mgr._crud.async_get_recurring_trips = AsyncMock(return_value=[])
        mgr._crud.async_get_punctual_trips = AsyncMock(return_value=[])

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            call = _make_call({"vehicle_id": "test_vehicle", "trip_id": "999"})
            result = await handler(call)

        assert result["found"] is False
        assert "error" in result


class TestEditTrip:
    """Test make_edit_trip_handler (lines 200-208)."""

    @pytest.mark.asyncio
    async def test_edit_trip_calls_update_and_refreshes(self):
        """Lines 200-208: Handler updates trip and refreshes coordinator."""
        hass = MagicMock()
        handler = make_edit_trip_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                with patch(
                    "custom_components.ev_trip_planner.services._handler_factories._ensure_setup",
                    new=AsyncMock(),
                ):
                    call = _make_call({
                        "vehicle_id": "test_vehicle",
                        "trip_id": "123",
                        "updates": {"km": 40.0},
                    })
                    await handler(call)

        mgr._crud.async_update_trip.assert_called_once()
        coordinator.async_refresh_trips.assert_called_once()


class TestTripUpdateDescripcion:
    """Test make_trip_update_handler descripcion branches."""

    @pytest.mark.asyncio
    async def test_trip_update_with_descripcion_field(self):
        """Line 147: Handler maps 'descripcion' to updates dict."""
        hass = MagicMock()
        handler = make_trip_update_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()
        entry = MagicMock()
        entry.entry_id = "entry_1"

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                with patch(
                    "custom_components.ev_trip_planner.services._handler_factories._ensure_setup",
                    new=AsyncMock(),
                ):
                    with patch(
                        "custom_components.ev_trip_planner.services._handler_factories._find_entry_by_vehicle",
                        return_value=entry,
                    ):
                        call = _make_call({
                            "vehicle_id": "test_vehicle",
                            "trip_id": "123",
                            "descripcion": "Test description",
                        })
                        await handler(call)

        # Verify descripcion was set in updates
        call_args = mgr._crud.async_update_trip.call_args
        updates = call_args[0][1] if call_args else {}
        assert updates.get("descripcion") == "Test description"

    @pytest.mark.asyncio
    async def test_trip_update_with_description_english_field(self):
        """Line 149: Handler maps 'description' (English) to descripcion."""
        hass = MagicMock()
        handler = make_trip_update_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()
        entry = MagicMock()
        entry.entry_id = "entry_1"

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                with patch(
                    "custom_components.ev_trip_planner.services._handler_factories._ensure_setup",
                    new=AsyncMock(),
                ):
                    with patch(
                        "custom_components.ev_trip_planner.services._handler_factories._find_entry_by_vehicle",
                        return_value=entry,
                    ):
                        call = _make_call({
                            "vehicle_id": "test_vehicle",
                            "trip_id": "123",
                            "description": "English description",
                        })
                        await handler(call)

        # Verify description was mapped to descripcion in updates
        call_args = mgr._crud.async_update_trip.call_args
        updates = call_args[0][1] if call_args else {}
        assert updates.get("descripcion") == "English description"


class TestTripUpdateWithUpdatesDict:
    """Test make_trip_update_handler with updates dict (line 130)."""

    @pytest.mark.asyncio
    async def test_trip_update_with_updates_dict(self):
        """Line 130: Handler uses updates dict directly when 'updates' key present."""
        hass = MagicMock()
        handler = make_trip_update_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()
        entry = MagicMock()
        entry.entry_id = "entry_1"

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                with patch(
                    "custom_components.ev_trip_planner.services._handler_factories._ensure_setup",
                    new=AsyncMock(),
                ):
                    with patch(
                        "custom_components.ev_trip_planner.services._handler_factories._find_entry_by_vehicle",
                        return_value=entry,
                    ):
                        call = _make_call({
                            "vehicle_id": "test_vehicle",
                            "trip_id": "123",
                            "updates": {"km": 50.0, "dia_semana": "martes"},
                        })
                        await handler(call)

        # Verify updates dict was passed directly
        mgr._crud.async_update_trip.assert_called_once()
        call_args = mgr._crud.async_update_trip.call_args
        updates = call_args[0][1] if call_args else {}
        assert updates["km"] == 50.0
        assert updates["dia_semana"] == "martes"


class TestTripUpdateSensorUpdate:
    """Test make_trip_update_handler sensor update path (lines 177-183)."""

    @pytest.mark.asyncio
    async def test_trip_update_calls_async_update_trip_sensor(self):
        """Lines 177-183: Handler calls async_update_trip_sensor when trip found."""
        hass = MagicMock()
        handler = make_trip_update_handler(hass)

        mgr = _make_manager()
        mgr._crud.async_update_trip = AsyncMock()
        mgr._crud.async_get_recurring_trips = AsyncMock(return_value=[
            {"id": "123", "dia_semana": "lunes", "hora": "08:00", "km": 30.0, "kwh": 5.0}
        ])

        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()
        entry = MagicMock()
        entry.entry_id = "entry_1"

        mock_async_update = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                with patch(
                    "custom_components.ev_trip_planner.services._handler_factories._ensure_setup",
                    new=AsyncMock(),
                ):
                    with patch(
                        "custom_components.ev_trip_planner.services._handler_factories._find_entry_by_vehicle",
                        return_value=entry,
                    ):
                        with patch(
                            "custom_components.ev_trip_planner.sensor.async_update_trip_sensor",
                            mock_async_update,
                        ):
                            call = _make_call({
                                "vehicle_id": "test_vehicle",
                                "trip_id": "123",
                                "dia_semana": "lunes",
                                "hora": "09:00",
                                "km": 35.0,
                            })
                            await handler(call)

        mock_async_update.assert_called_once()
        call_args = mock_async_update.call_args
        assert call_args[0][0] is hass
        assert call_args[0][1] == "entry_1"


class TestTripGetException:
    """Test make_trip_get_handler exception path (lines 560-568)."""

    @pytest.mark.asyncio
    async def test_trip_get_returns_error_on_manager_exception(self):
        """Lines 560-573: Handler returns error dict when manager raises."""
        hass = MagicMock()
        handler = make_trip_get_handler(hass)

        mgr = _make_manager()
        mgr._crud.async_get_recurring_trips = AsyncMock(
            side_effect=RuntimeError("Database connection failed")
        )

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            call = _make_call({"vehicle_id": "test_vehicle", "trip_id": "123"})
            result = await handler(call)

        assert result["found"] is False
        assert result["trip"] is None
        assert "error" in result
        assert "Database connection failed" in result["error"]


class TestTripCreate:
    """Test make_trip_create_handler branches (lines 320-372)."""

    @pytest.mark.asyncio
    async def test_trip_create_recurrente(self):
        """Lines 326-343: Handler creates recurring trip correctly."""
        hass = MagicMock()
        handler = make_trip_create_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                call = _make_call({
                    "vehicle_id": "test_vehicle",
                    "type": "recurrente",
                    "dia_semana": "lunes",
                    "hora": "08:00",
                    "km": 30.0,
                    "kwh": 5.0,
                    "descripcion": "Recurring test",
                })
                await handler(call)

        mgr._crud.async_add_recurring_trip.assert_called_once()
        call_kwargs = mgr._crud.async_add_recurring_trip.call_args[1]
        assert call_kwargs["dia_semana"] == "lunes"
        assert call_kwargs["hora"] == "08:00"
        assert call_kwargs["km"] == 30.0
        assert call_kwargs["kwh"] == 5.0
        assert call_kwargs["descripcion"] == "Recurring test"

    @pytest.mark.asyncio
    async def test_trip_create_puntual(self):
        """Lines 344-358: Handler creates punctual trip correctly."""
        hass = MagicMock()
        handler = make_trip_create_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                call = _make_call({
                    "vehicle_id": "test_vehicle",
                    "type": "puntual",
                    "datetime": "2026-05-20T08:00:00+00:00",
                    "km": 25.0,
                    "kwh": 4.0,
                    "description": "Punctual test",
                })
                await handler(call)

        mgr._crud.async_add_punctual_trip.assert_called_once()
        call_kwargs = mgr._crud.async_add_punctual_trip.call_args[1]
        assert call_kwargs["datetime_str"] == "2026-05-20T08:00:00+00:00"
        assert call_kwargs["km"] == 25.0
        assert call_kwargs["kwh"] == 4.0
        assert call_kwargs["descripcion"] == "Punctual test"

    @pytest.mark.asyncio
    async def test_trip_create_invalid_type_returns_early(self):
        """Lines 359-365: Handler logs error and returns for invalid type."""
        hass = MagicMock()
        handler = make_trip_create_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                call = _make_call({
                    "vehicle_id": "test_vehicle",
                    "type": "invalid_type",
                    "km": 30.0,
                    "kwh": 5.0,
                })
                await handler(call)

        # No trip should be created
        mgr._crud.async_add_recurring_trip.assert_not_called()
        mgr._crud.async_add_punctual_trip.assert_not_called()
        # But coordinator should NOT be refreshed since it returned early
        coordinator.async_refresh_trips.assert_not_called()


class TestTripUpdateSensorException:
    """Test sensor update exception handling (lines 182-183)."""

    @pytest.mark.asyncio
    async def test_trip_update_continues_when_sensor_update_fails(self):
        """Lines 182-183: Handler continues when async_update_trip_sensor raises."""
        hass = MagicMock()
        handler = make_trip_update_handler(hass)

        mgr = _make_manager()
        mgr._crud.async_update_trip = AsyncMock()
        mgr._crud.async_get_recurring_trips = AsyncMock(return_value=[
            {"id": "123", "dia_semana": "lunes", "hora": "08:00", "km": 30.0, "kwh": 5.0}
        ])

        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()
        entry = MagicMock()
        entry.entry_id = "entry_1"

        mock_async_update = AsyncMock(side_effect=Exception("Sensor update failed"))

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                with patch(
                    "custom_components.ev_trip_planner.services._handler_factories._ensure_setup",
                    new=AsyncMock(),
                ):
                    with patch(
                        "custom_components.ev_trip_planner.services._handler_factories._find_entry_by_vehicle",
                        return_value=entry,
                    ):
                        with patch(
                            "custom_components.ev_trip_planner.sensor.async_update_trip_sensor",
                            mock_async_update,
                        ):
                            call = _make_call({
                                "vehicle_id": "test_vehicle",
                                "trip_id": "123",
                                "km": 35.0,
                            })
                            # Should NOT raise - exception is caught
                            await handler(call)

        # Update still happened despite sensor failure
        mgr._crud.async_update_trip.assert_called_once()
        # Coordinator refresh also still happened
        coordinator.async_refresh_trips.assert_called_once()


class TestTripCreateWithDayOfWeek:
    """Test day_of_week English mapping in trip create."""

    @pytest.mark.asyncio
    async def test_trip_create_recurrente_with_day_of_week(self):
        """Lines 327-328: Handler accepts 'day_of_week' and 'time' English params."""
        hass = MagicMock()
        handler = make_trip_create_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                call = _make_call({
                    "vehicle_id": "test_vehicle",
                    "type": "recurrente",
                    "day_of_week": "monday",
                    "time": "10:00",
                    "km": 40.0,
                    "kwh": 6.0,
                })
                await handler(call)

        mgr._crud.async_add_recurring_trip.assert_called_once()
        call_kwargs = mgr._crud.async_add_recurring_trip.call_args[1]
        assert call_kwargs["dia_semana"] == "monday"
        assert call_kwargs["hora"] == "10:00"
    """Test make_trip_update_handler branches."""

    @pytest.mark.asyncio
    async def test_trip_update_returns_early_when_entry_not_found(self):
        """Lines 158-161: Handler returns early when entry not found."""
        hass = MagicMock()
        handler = make_trip_update_handler(hass)

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._find_entry_by_vehicle",
            return_value=None,
        ):
            call = _make_call({
                "vehicle_id": "test_vehicle",
                "trip_id": "123",
                "km": 30.0,
            })
            await handler(call)

    @pytest.mark.asyncio
    async def test_trip_update_with_field_mappings(self):
        """Lines 132-149: Handler builds updates dict from field mappings."""
        hass = MagicMock()
        handler = make_trip_update_handler(hass)

        mgr = _make_manager()
        coordinator = MagicMock()
        coordinator.async_refresh_trips = AsyncMock()
        entry = MagicMock()
        entry.entry_id = "entry_1"

        with patch(
            "custom_components.ev_trip_planner.services._handler_factories._get_manager",
            new=AsyncMock(return_value=mgr),
        ):
            with patch(
                "custom_components.ev_trip_planner.services._handler_factories._get_coordinator",
                return_value=coordinator,
            ):
                with patch(
                    "custom_components.ev_trip_planner.services._handler_factories._ensure_setup",
                    new=AsyncMock(),
                ):
                    with patch(
                        "custom_components.ev_trip_planner.services._handler_factories._find_entry_by_vehicle",
                        return_value=entry,
                    ):
                        call = _make_call({
                            "vehicle_id": "test_vehicle",
                            "trip_id": "123",
                            "dia_semana": "lunes",
                            "hora": "09:00",
                            "km": 30.0,
                            "kwh": 5.0,
                        })
                        await handler(call)

        mgr._crud.async_update_trip.assert_called_once()