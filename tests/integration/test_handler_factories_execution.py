"""Tests that actually execute handler factory closures.

These tests call the handlers with mock ServiceCall objects to exercise
the handler logic paths, not just check that factories return async functions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import ServiceCall
from homeassistant.helpers import storage as ha_storage
from voluptuous import Invalid

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
    trip_create_schema,
    trip_id_schema,
    trip_update_schema,
)

# --- Mock fixtures ---


class _MockStore:
    """Minimal Store mock for patching."""

    def __init__(self, hass, version, key, *, private=None):
        pass

    async def async_load(self):
        return None

    async def async_save(self, data):
        return True


@pytest.fixture(autouse=True)
def mock_store():
    with patch.object(ha_storage, "Store", _MockStore):
        yield


class _MockConfigEntry:
    """Minimal config entry."""

    def __init__(self, vehicle_name="test_vehicle"):
        self.entry_id = "entry_1"
        self.data = {"vehicle_name": vehicle_name}
        self.unique_id = vehicle_name


def _build_hass(vehicle_name="test_vehicle", manager_cfg=None):
    """Build a mock hass with a config entry and optional manager."""
    from custom_components.ev_trip_planner.__init__ import EVTripRuntimeData

    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()

    entry = _MockConfigEntry(vehicle_name)
    coordinator = MagicMock()
    coordinator.async_refresh_trips = AsyncMock()

    manager: MagicMock = AsyncMock()
    if manager_cfg:
        for method_name, cfg in manager_cfg.items():
            mock_obj = AsyncMock(
                return_value=cfg.get("return_value"),
                side_effect=cfg.get("side_effect"),
            )
            # Handle dot-separated paths like "_crud.async_add_recurring_trip"
            parts = method_name.split(".", 1)
            if len(parts) == 2:
                parent, attr = parts
                setattr(getattr(manager, parent), attr, mock_obj)
            else:
                setattr(manager, method_name, mock_obj)
    # Ensure async_setup exists
    manager.async_setup = AsyncMock(return_value=None)

    entry.runtime_data = EVTripRuntimeData(
        coordinator=coordinator,
        trip_manager=manager,
    )

    hass.config_entries.async_entries = MagicMock(return_value=[entry])
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)
    return hass, entry, manager, coordinator


class TestAddRecurringHandler:
    """Test add_recurring_trip handler execution."""

    @pytest.mark.asyncio
    async def test_add_recurring_handler_basic(self):
        """Handler adds a recurring trip and refreshes coordinator."""
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_add_recurring_trip": {"return_value": "rec_lun_123"},
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
        }
        await handler(call)

        mgr._crud.async_add_recurring_trip.assert_called_once_with(
            dia_semana="lunes", hora="09:00", km=24.0, kwh=3.6, descripcion=""
        )
        coord.async_refresh_trips.assert_called_once()


class TestAddPunctualHandler:
    """Test add_punctual_trip handler execution."""

    @pytest.mark.asyncio
    async def test_add_punctual_handler_basic(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_add_punctual_trip": {"return_value": "pun_123"},
            }
        )

        handler_fn = make_add_punctual_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "datetime": "2025-12-01T10:00:00",
            "km": 100,
            "kwh": 15,
        }
        await handler_fn(call)

        mgr._crud.async_add_punctual_trip.assert_called_once()
        coord.async_refresh_trips.assert_called_once()


class TestTripUpdateHandler:
    """Test trip_update handler execution."""

    @pytest.mark.asyncio
    async def test_trip_update_basic(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_update_trip": {"return_value": True},
                "_crud.async_get_recurring_trips": {
                    "return_value": [
                        {
                            "id": "rec_lun_1",
                            "dia_semana": "lunes",
                            "hora": "09:00",
                            "km": 24,
                            "kwh": 3.6,
                        }
                    ]
                },
            }
        )

        handler = make_trip_update_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_lun_1",
            "km": 30,
        }
        await handler(call)

        mgr._crud.async_update_trip.assert_called_once()
        coord.async_refresh_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_trip_update_with_updates_object(self):
        """Handler accepts 'updates' object format."""
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_update_trip": {"return_value": True},
            }
        )

        handler = make_trip_update_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_1",
            "type": "recurrente",
            "updates": {"dia_semana": "martes", "hora": "10:00"},
        }
        await handler(call)

        mgr._crud.async_update_trip.assert_called_once_with(
            "rec_1", {"dia_semana": "martes", "hora": "10:00"}
        )

    @pytest.mark.asyncio
    async def test_trip_update_with_alternative_fields(self):
        """Handler maps day_of_week/time/datetime to dia_semana/hora."""
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_update_trip": {"return_value": True},
            }
        )

        handler = make_trip_update_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_1",
            "day_of_week": "martes",
            "time": "11:00",
            "datetime": "2025-12-01T12:00",
        }
        await handler(call)

        mgr._crud.async_update_trip.assert_called_once_with(
            "rec_1",
            {"dia_semana": "martes", "hora": "11:00", "datetime": "2025-12-01T12:00"},
        )

    @pytest.mark.asyncio
    async def test_trip_update_with_kwh_descripcion_fields(self):
        """Handler applies kwh, descripcion, description fields in data path."""
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_update_trip": {"return_value": True},
                "_crud.async_get_recurring_trips": {
                    "return_value": [{"id": "rec_1", "dia_semana": "lunes"}]
                },
                "_crud.async_get_punctual_trips": {"return_value": []},
            }
        )

        handler = make_trip_update_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_1",
            "km": 30,
            "kwh": 5.0,
            "descripcion": "mi descripcion",
        }
        await handler(call)

        # Called with km as float + kwh as float + descripcion
        call_args = mgr._crud.async_update_trip.call_args
        updates = call_args[0][1]
        assert updates["km"] == 30.0
        assert updates["kwh"] == 5.0
        assert updates["descripcion"] == "mi descripcion"

    @pytest.mark.asyncio
    async def test_trip_update_with_description_field(self):
        """Handler maps 'description' -> 'descripcion' in data path."""
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_update_trip": {"return_value": True},
                "_crud.async_get_punctual_trips": {"return_value": []},
            }
        )

        handler = make_trip_update_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "pun_1",
            "description": "english description",
        }
        await handler(call)

        call_args = mgr._crud.async_update_trip.call_args
        updates = call_args[0][1]
        assert updates["descripcion"] == "english description"

    @pytest.mark.asyncio
    async def test_trip_update_entry_not_found(self):
        """Handler returns early when vehicle entry not found."""
        # Build hass with NO config entries so _find_entry_by_vehicle returns None
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_update_handler,
        )

        hass = MagicMock()
        hass.data = {}
        hass.config_entries = MagicMock()
        hass.config_entries.async_entries.return_value = []

        handler = make_trip_update_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "unknown", "trip_id": "rec_1", "km": 30}
        # Should not raise, just log and return
        await handler(call)

    @pytest.mark.asyncio
    async def test_trip_update_sensor_match(self):
        """Handler updates sensor when trip found in recurring list."""
        from unittest.mock import AsyncMock, patch

        trip_data = {
            "id": "rec_1",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24,
            "kwh": 3.6,
        }
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_update_trip": {"return_value": True},
                "_crud.async_get_recurring_trips": {"return_value": [trip_data]},
            }
        )

        handler = make_trip_update_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_1",
            "dia_semana": "martes",  # triggers recurrente path
        }

        mock_update_sensor = AsyncMock()
        with patch(
            "custom_components.ev_trip_planner.sensor.async_update_trip_sensor",
            mock_update_sensor,
        ):
            await handler(call)

        # Sensor update should be called with the matching trip
        mock_update_sensor.assert_called_once()
        sensor_arg = mock_update_sensor.call_args[0][2]
        assert sensor_arg["id"] == "rec_1"

    @pytest.mark.asyncio
    async def test_trip_update_sensor_exception(self):
        """Handler catches sensor update exception and continues."""
        from unittest.mock import AsyncMock, patch

        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_update_trip": {"return_value": True},
                "_crud.async_get_recurring_trips": {
                    "return_value": [{"id": "rec_1", "dia_semana": "lunes"}]
                },
            }
        )

        handler = make_trip_update_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "trip_id": "rec_1",
            "dia_semana": "martes",
        }

        with patch(
            "custom_components.ev_trip_planner.sensor.async_update_trip_sensor",
            AsyncMock(side_effect=RuntimeError("sensor fail")),
        ):
            # Should not raise — exception is caught and logged
            await handler(call)

        # Manager update should still have been called
        mgr._crud.async_update_trip.assert_called_once()


class TestEditTripHandler:
    """Test edit_trip (deprecated alias) handler execution."""

    @pytest.mark.asyncio
    async def test_edit_trip_handler(self):
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
            "updates": {"km": 50},
        }
        await handler(call)

        mgr._crud.async_update_trip.assert_called_once_with("rec_1", {"km": 50})
        coord.async_refresh_trips.assert_called_once()


class TestDeleteTripHandler:
    """Test delete_trip handler execution."""

    @pytest.mark.asyncio
    async def test_delete_trip_handler(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_delete_trip": {"return_value": True},
            }
        )

        handler = make_delete_trip_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "rec_1"}
        await handler(call)

        mgr._crud.async_delete_trip.assert_called_once_with("rec_1")
        coord.async_refresh_trips.assert_called_once()


class TestPauseResumeHandlers:
    """Test pause/resume recurring handler execution."""

    @pytest.mark.asyncio
    async def test_pause_recurring_handler(self):
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

        mgr._lifecycle.async_pause_recurring_trip.assert_called_once_with("rec_1")
        coord.async_refresh_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_recurring_handler(self):
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

        mgr._lifecycle.async_resume_recurring_trip.assert_called_once_with("rec_1")
        coord.async_refresh_trips.assert_called_once()


class TestCompleteCancelPunctualHandlers:
    """Test complete/cancel punctual handler execution."""

    @pytest.mark.asyncio
    async def test_complete_punctual_handler(self):
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

        mgr._lifecycle.async_complete_punctual_trip.assert_called_once_with("pun_1")
        coord.async_refresh_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_punctual_handler(self):
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

        mgr._lifecycle.async_cancel_punctual_trip.assert_called_once_with("pun_1")
        coord.async_refresh_trips.assert_called_once()


class TestTripCreateHandler:
    """Test trip_create (unified) handler execution."""

    @pytest.mark.asyncio
    async def test_trip_create_recurring(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_add_recurring_trip": {"return_value": "rec_1"},
            }
        )

        handler = make_trip_create_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "type": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24,
            "kwh": 3.6,
        }
        await handler(call)

        mgr._crud.async_add_recurring_trip.assert_called_once()
        coord.async_refresh_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_trip_create_punctual(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_add_punctual_trip": {"return_value": "pun_1"},
            }
        )

        handler = make_trip_create_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "type": "puntual",
            "datetime": "2025-12-01T10:00",
            "km": 100,
            "kwh": 15,
        }
        await handler(call)

        mgr._crud.async_add_punctual_trip.assert_called_once()
        coord.async_refresh_trips.assert_called_once()

    @pytest.mark.asyncio
    async def test_trip_create_invalid_type(self):
        """Invalid trip type → logs error and returns early."""
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

        # Should NOT call any trip methods
        assert not mgr.method_calls
        # Should NOT refresh coordinator
        assert not coord.method_calls


class TestTripListHandler:
    """Test trip_list handler execution."""

    @pytest.mark.asyncio
    async def test_trip_list_no_trips(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_get_recurring_trips": {"return_value": []},
                "_crud.async_get_punctual_trips": {"return_value": []},
            }
        )

        handler = make_trip_list_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle"}
        result = await handler(call)

        assert result["vehicle_id"] == "test_vehicle"
        assert result["total_trips"] == 0
        assert result["recurring_trips"] == []
        assert result["punctual_trips"] == []

    @pytest.mark.asyncio
    async def test_trip_list_with_trips(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_get_recurring_trips": {
                    "return_value": [
                        {"id": "rec_1", "tipo": "recurrente", "activo": True},
                    ],
                },
                "_crud.async_get_punctual_trips": {
                    "return_value": [
                        {"id": "pun_1", "tipo": "puntual", "estado": "pendiente"},
                    ],
                },
            }
        )

        handler = make_trip_list_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle"}
        result = await handler(call)

        assert result["total_trips"] == 2
        assert len(result["recurring_trips"]) == 1
        assert len(result["punctual_trips"]) == 1

    @pytest.mark.asyncio
    async def test_trip_list_error(self):
        """Manager error → returns empty list with error message."""
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_get_recurring_trips": {
                    "side_effect": RuntimeError("storage error")
                },
                "_crud.async_get_punctual_trips": {"return_value": []},
            }
        )

        handler = make_trip_list_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle"}
        result = await handler(call)

        assert result["error"] is not None
        assert result["total_trips"] == 0


class TestTripGetHandler:
    """Test trip_get handler execution."""

    @pytest.mark.asyncio
    async def test_trip_get_found(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_get_recurring_trips": {
                    "return_value": [
                        {"id": "rec_1", "tipo": "recurrente", "dia_semana": "lunes"},
                    ],
                },
                "_crud.async_get_punctual_trips": {"return_value": []},
            }
        )

        handler = make_trip_get_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "rec_1"}
        result = await handler(call)

        assert result["found"] is True
        assert result["trip"]["id"] == "rec_1"

    @pytest.mark.asyncio
    async def test_trip_get_not_found(self):
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_get_recurring_trips": {"return_value": []},
                "_crud.async_get_punctual_trips": {"return_value": []},
            }
        )

        handler = make_trip_get_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "rec_999"}
        result = await handler(call)

        assert result["found"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_trip_get_punctual(self):
        """Search includes punctual trips."""
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_get_recurring_trips": {"return_value": []},
                "_crud.async_get_punctual_trips": {
                    "return_value": [
                        {"id": "pun_1", "tipo": "puntual", "datetime": "2025-12-01"},
                    ],
                },
            }
        )

        handler = make_trip_get_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "pun_1"}
        result = await handler(call)

        assert result["found"] is True
        assert result["trip"]["tipo"] == "puntual"

    @pytest.mark.asyncio
    async def test_trip_get_error(self):
        """Manager error → returns not found with error message."""
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "_crud.async_get_recurring_trips": {
                    "side_effect": RuntimeError("fail")
                },
            }
        )

        handler = make_trip_get_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {"vehicle_id": "test_vehicle", "trip_id": "rec_1"}
        result = await handler(call)

        assert result["found"] is False
        assert result["error"] is not None


class TestImportWeeklyPatternHandler:
    """Test import_from_weekly_pattern handler execution."""

    @pytest.mark.asyncio
    async def test_import_with_clear_existing(self):
        """Handler clears existing then imports new patterns."""
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_get_recurring_trips": {
                    "return_value": [
                        {
                            "id": "old_rec",
                            "dia_semana": "lunes",
                            "hora": "08:00",
                            "km": 10,
                            "kwh": 1.5,
                        }
                    ],
                },
                "_crud.async_delete_trip": {"return_value": True},
                "_crud.async_add_recurring_trip": {"return_value": "new_rec_1"},
            }
        )

        handler = make_import_weekly_pattern_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "clear_existing": True,
            "pattern": {
                "lunes": [{"hora": "09:00", "km": 24, "kwh": 3.6}],
                "martes": [{"hora": "10:00", "km": 30, "kwh": 4.5}],
            },
        }
        await handler(call)

        # Should delete old trips
        assert mgr._crud.async_delete_trip.called
        # Should add new trips
        assert mgr._crud.async_add_recurring_trip.call_count == 2

    @pytest.mark.asyncio
    async def test_import_without_clear_existing(self):
        """Handler skips clearing when clear_existing=False."""
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
            "pattern": {"lunes": [{"hora": "09:00", "km": 24, "kwh": 3.6}]},
        }
        await handler(call)

        # Should NOT delete existing
        assert not mgr._crud.async_delete_trip.called
        # Should add new trips
        mgr._crud.async_add_recurring_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_clear_fails_continues(self):
        """Clearing existing fails → continues with import."""
        hass, entry, mgr, coord = _build_hass(
            manager_cfg={
                "async_setup": {"return_value": None},
                "_crud.async_get_recurring_trips": {
                    "side_effect": RuntimeError("clear fail")
                },
                "_crud.async_add_recurring_trip": {"return_value": "new_rec"},
            }
        )

        handler = make_import_weekly_pattern_handler(hass)
        call = MagicMock(spec=ServiceCall)
        call.data = {
            "vehicle_id": "test_vehicle",
            "clear_existing": True,
            "pattern": {"lunes": [{"hora": "09:00", "km": 24, "kwh": 3.6}]},
        }
        await handler(call)

        # Should have added despite clear failure
        mgr._crud.async_add_recurring_trip.assert_called_once()


class TestSchemas:
    """Test schema definitions."""

    def test_trip_id_schema_valid(self):
        """Valid trip_id data passes schema."""
        data = {"vehicle_id": "test", "trip_id": "rec_1"}
        result = trip_id_schema(data)
        assert result == data

    def test_trip_update_schema_basic(self):
        """Valid update data passes schema."""
        data = {
            "vehicle_id": "test",
            "trip_id": "rec_1",
            "type": "recurrente",
            "km": 24,
        }
        result = trip_update_schema(data)
        assert result["km"] == 24.0

    def test_trip_update_schema_invalid_type(self):
        """Invalid type fails schema."""
        with pytest.raises(Invalid):
            trip_update_schema(
                {
                    "vehicle_id": "test",
                    "trip_id": "rec_1",
                    "type": "invalid",
                }
            )

    def test_trip_create_schema_valid(self):
        """Valid create data passes schema."""
        data = {"vehicle_id": "test", "type": "puntual", "km": 100, "kwh": 15}
        result = trip_create_schema(data)
        assert result["descripcion"] == ""

    def test_trip_create_schema_recurring(self):
        """Recurring create passes schema."""
        data = {"vehicle_id": "test", "type": "recurrente", "km": 24, "kwh": 3.6}
        result = trip_create_schema(data)
        assert result["type"] == "recurrente"
