"""Pruebas de servicios de EV Trip Planner (TDD Fase 1B)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from custom_components.ev_trip_planner.const import DOMAIN
from custom_components.ev_trip_planner.__init__ import register_services


def _patch_trip_manager():
    """Patch TripManager constructor to return a mock with async methods."""
    manager = MagicMock()
    manager.async_setup = AsyncMock()
    manager.async_add_recurring_trip = AsyncMock(return_value="rec_lun_abc12345")
    manager.async_add_punctual_trip = AsyncMock(return_value="pun_20251119_abc12345")
    manager.async_update_trip = AsyncMock(return_value=True)
    manager.async_delete_trip = AsyncMock(return_value=True)
    manager.async_pause_recurring_trip = AsyncMock(return_value=True)
    manager.async_resume_recurring_trip = AsyncMock(return_value=True)
    manager.async_complete_punctual_trip = AsyncMock(return_value=True)
    manager.async_cancel_punctual_trip = AsyncMock(return_value=True)
    manager.async_get_recurring_trips = AsyncMock(
        return_value=[{"id": "rec_lun_old"}, {"id": "rec_mar_old"}]
    )

    return patch(
        "custom_components.ev_trip_planner.__init__.TripManager",
        return_value=manager,
    ), manager


@pytest.fixture
def mock_hass():
    class Services:
        def __init__(self):
            self.registry = {}

        def async_register(self, domain, name, handler, schema=None, supports_response=None):
            # Accept supports_response argument to match Home Assistant 2025.1+ API
            if domain == DOMAIN:
                self.registry[name] = handler

    hass = MagicMock()
    hass.data = {}
    hass.services = Services()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    return hass


def _setup_mock_config_entry(mock_hass, vehicle_id="chispitas"):
    """Set up a mock config entry for the given vehicle_id."""
    mock_entry = MagicMock()
    mock_entry.entry_id = f"entry_{vehicle_id}"
    mock_entry.data = {"vehicle_name": vehicle_id}
    # Include empty managers/coordinators dicts so the code doesn't fail
    namespace = f"ev_trip_planner_{mock_entry.entry_id}"
    mock_entry.runtime_data = {namespace: {"managers": {}, "coordinators": {}}}

    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    return mock_entry


@pytest.mark.asyncio
async def test_services_use_seeded_trip_manager_instance(mock_hass):
    """If a TripManager is seeded in hass.data[DATA_RUNTIME][namespace]['managers'], services reuse it."""
    from custom_components.ev_trip_planner import DOMAIN
    from custom_components.ev_trip_planner.__init__ import DATA_RUNTIME

    # Create a mock config entry with proper structure
    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_chispitas"
    mock_entry.data = {
        "vehicle_name": "chispitas",
    }

    # Set up runtime_data at the correct location (hass.data[DATA_RUNTIME][namespace])
    namespace = f"{DOMAIN}_{mock_entry.entry_id}"
    seeded = MagicMock()
    seeded.async_setup = AsyncMock()
    seeded.async_add_recurring_trip = AsyncMock(return_value="rec_lun_seeded")

    # Seed trip_manager directly at hass.data[DATA_RUNTIME][namespace] - this is where _get_manager looks
    mock_hass.data.setdefault(DATA_RUNTIME, {})[namespace] = {
        "trip_manager": seeded,
    }

    # Set up config_entries to find our entry
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    register_services(mock_hass)

    # Ensure no new TripManager is constructed by making constructor raise
    with patch(
        "custom_components.ev_trip_planner.__init__.TripManager",
        side_effect=AssertionError("Should not construct new TripManager"),
    ):
        handler = mock_hass.services.registry["add_recurring_trip"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "chispitas",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
            "kwh": 3.6,
            "descripcion": "Trabajo",
        }
        await handler(call)

    seeded.async_add_recurring_trip.assert_awaited_once()


@pytest.mark.asyncio
async def test_service_add_recurring_trip_routes_to_manager(mock_hass):
    _setup_mock_config_entry(mock_hass)
    register_services(mock_hass)

    p, mgr = _patch_trip_manager()
    with p:
        handler = mock_hass.services.registry["add_recurring_trip"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "chispitas",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
            "kwh": 3.6,
            "descripcion": "Trabajo",
        }
        await handler(call)

    mgr.async_add_recurring_trip.assert_awaited_once_with(
        dia_semana="lunes", hora="09:00", km=24.0, kwh=3.6, descripcion="Trabajo"
    )


@pytest.mark.asyncio
async def test_service_add_punctual_trip_routes_to_manager(mock_hass):
    _setup_mock_config_entry(mock_hass)
    register_services(mock_hass)

    p, mgr = _patch_trip_manager()
    with p:
        handler = mock_hass.services.registry["add_punctual_trip"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "chispitas",
            "datetime": "2025-11-19T15:00:00",
            "km": 110.0,
            "kwh": 16.5,
            "descripcion": "Viaje",
        }
        await handler(call)

    mgr.async_add_punctual_trip.assert_awaited_once_with(
        datetime_str="2025-11-19T15:00:00", km=110.0, kwh=16.5, descripcion="Viaje"
    )


@pytest.mark.asyncio
async def test_service_update_and_delete_trip(mock_hass):
    _setup_mock_config_entry(mock_hass)
    register_services(mock_hass)
    p, mgr = _patch_trip_manager()
    with p:
        edit_handler = mock_hass.services.registry["edit_trip"]
        del_handler = mock_hass.services.registry["delete_trip"]
        call = MagicMock()
        call.data = {"vehicle_id": "chispitas", "trip_id": "rec_lun_abc", "updates": {"hora": "10:00"}}
        await edit_handler(call)
        call2 = MagicMock()
        call2.data = {"vehicle_id": "chispitas", "trip_id": "rec_lun_abc"}
        await del_handler(call2)

    mgr.async_update_trip.assert_awaited_once_with("rec_lun_abc", {"hora": "10:00"})
    mgr.async_delete_trip.assert_awaited_once_with("rec_lun_abc")


@pytest.mark.asyncio
async def test_service_pause_resume_complete_cancel(mock_hass):
    _setup_mock_config_entry(mock_hass)
    register_services(mock_hass)
    p, mgr = _patch_trip_manager()
    with p:
        pause_h = mock_hass.services.registry["pause_recurring_trip"]
        resume_h = mock_hass.services.registry["resume_recurring_trip"]
        complete_h = mock_hass.services.registry["complete_punctual_trip"]
        cancel_h = mock_hass.services.registry["cancel_punctual_trip"]

        call1 = MagicMock()
        call1.data = {"vehicle_id": "chispitas", "trip_id": "rec_lun_abc"}
        call2 = MagicMock()
        call2.data = {"vehicle_id": "chispitas", "trip_id": "rec_lun_abc"}
        call3 = MagicMock()
        call3.data = {"vehicle_id": "chispitas", "trip_id": "pun_20251119_abc"}
        call4 = MagicMock()
        call4.data = {"vehicle_id": "chispitas", "trip_id": "pun_20251119_abc"}

        await pause_h(call1)
        await resume_h(call2)
        await complete_h(call3)
        await cancel_h(call4)

    mgr.async_pause_recurring_trip.assert_awaited_once_with("rec_lun_abc")
    mgr.async_resume_recurring_trip.assert_awaited_once_with("rec_lun_abc")
    mgr.async_complete_punctual_trip.assert_awaited_once_with("pun_20251119_abc")
    mgr.async_cancel_punctual_trip.assert_awaited_once_with("pun_20251119_abc")


@pytest.mark.asyncio
async def test_service_import_from_weekly_pattern_clears_and_adds(mock_hass):
    _setup_mock_config_entry(mock_hass)
    register_services(mock_hass)
    p, mgr = _patch_trip_manager()
    with p:
        handler = mock_hass.services.registry["import_from_weekly_pattern"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "chispitas",
            "clear_existing": True,
            "pattern": {
                "lunes": [
                    {"hora": "09:00", "km": 24, "kwh": 3.6, "descripcion": "Trabajo"},
                    {"hora": "18:00", "km": 24, "kwh": 3.6, "descripcion": "Vuelta"},
                ],
                "miercoles": [
                    {"hora": "20:00", "km": 10, "kwh": 1.5, "descripcion": "Gimnasio"}
                ],
            },
        }
        await handler(call)

    # Borró los existentes
    mgr.async_delete_trip.assert_any_await("rec_lun_old")
    mgr.async_delete_trip.assert_any_await("rec_mar_old")
    # Añadió 3 viajes nuevos (2 lunes, 1 miércoles)
    assert mgr.async_add_recurring_trip.await_count == 3


@pytest.mark.asyncio
async def test_service_import_from_weekly_pattern_no_clear(mock_hass):
    _setup_mock_config_entry(mock_hass)
    register_services(mock_hass)
    p, mgr = _patch_trip_manager()
    with p:
        handler = mock_hass.services.registry["import_from_weekly_pattern"]
        call = MagicMock()
        call.data = {
            "vehicle_id": "chispitas",
            "clear_existing": False,
            "pattern": {
                "viernes": [
                    {"hora": "12:00", "km": 50, "kwh": 7.5, "descripcion": "Comida"}
                ],
            },
        }
        await handler(call)

    # No se borran existentes
    mgr.async_delete_trip.assert_not_awaited()
    # Se añade 1 viaje
    mgr.async_add_recurring_trip.assert_awaited_once_with(
        dia_semana="viernes", hora="12:00", km=50.0, kwh=7.5, descripcion="Comida"
    )
