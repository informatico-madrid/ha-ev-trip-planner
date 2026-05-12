"""Tests for trip_create and trip_update service handler branches.

Covers uncovered paths in handle_trip_create and handle_trip_update.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_trip_create_with_invalid_trip_type_logs_error():
    """handle_trip_create logs error and returns for invalid trip_type.

    This covers services.py lines 121-127 (invalid type branch).
    """
    from custom_components.ev_trip_planner.services import register_services

    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_chispitas"
    mock_entry.data = {"vehicle_name": "Chispitas"}
    mock_entry.unique_id = "chispitas_unique"

    mock_coordinator = MagicMock()
    mock_coordinator.async_refresh_trips = AsyncMock()
    mock_trip_manager = MagicMock()
    mock_trip_manager.async_setup = AsyncMock()

    # The handler factories call mgr._crud.X() and mgr._lifecycle.X()
    mock_trip_manager._crud = MagicMock()
    mock_trip_manager._crud.async_add_recurring_trip = AsyncMock(
        return_value="rec_lun_123"
    )
    mock_trip_manager._crud.async_add_punctual_trip = AsyncMock(
        return_value="pun_20251119_abc"
    )
    mock_trip_manager._lifecycle = MagicMock()
    mock_trip_manager._lifecycle.async_pause_recurring_trip = AsyncMock()
    mock_trip_manager._lifecycle.async_resume_recurring_trip = AsyncMock()
    mock_trip_manager._lifecycle.async_complete_punctual_trip = AsyncMock()
    mock_trip_manager._lifecycle.async_cancel_punctual_trip = AsyncMock()

    mock_runtime_data = MagicMock()
    mock_runtime_data.trip_manager = mock_trip_manager
    mock_runtime_data.coordinator = mock_coordinator
    mock_entry.runtime_data = mock_runtime_data

    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    class Services:
        registry = {}

        def async_register(
            self, domain, name, handler, schema=None, supports_response=None
        ):
            if domain == "ev_trip_planner":
                self.registry[name] = handler

    mock_hass.services = Services()

    register_services(mock_hass)

    handler = mock_hass.services.registry["trip_create"]
    call = MagicMock()
    call.data = {
        "vehicle_id": "chispitas",
        "type": "invalid_type",
        "km": 24.0,
        "kwh": 3.6,
    }

    # Should complete without raising - invalid type logs error and returns
    await handler(call)

    # Should NOT call any trip add methods since type is invalid
    mock_trip_manager._crud.async_add_recurring_trip.assert_not_awaited()
    mock_trip_manager._crud.async_add_punctual_trip.assert_not_awaited()


@pytest.mark.asyncio
async def test_trip_create_with_recurring_type_succeeds():
    """handle_trip_create creates a recurring trip when type='recurrente'.

    This covers the 'recurrente' branch in services.py.
    """
    from custom_components.ev_trip_planner.services import register_services

    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_chispitas"
    mock_entry.data = {"vehicle_name": "Chispitas"}
    mock_entry.unique_id = "chispitas_unique"

    mock_coordinator = MagicMock()
    mock_coordinator.async_refresh_trips = AsyncMock()
    mock_trip_manager = MagicMock()
    mock_trip_manager.async_setup = AsyncMock()
    mock_trip_manager._crud.async_add_recurring_trip = AsyncMock(
        return_value="rec_lun_123"
    )
    mock_trip_manager._crud.async_get_recurring_trips = AsyncMock(
        return_value=[
            {
                "id": "rec_lun_123",
                "dia_semana": "lunes",
                "hora": "09:00",
                "km": 24.0,
                "kwh": 3.6,
                "descripcion": "Trabajo",
            }
        ]
    )

    mock_runtime_data = MagicMock()
    mock_runtime_data.trip_manager = mock_trip_manager
    mock_runtime_data.coordinator = mock_coordinator
    mock_entry.runtime_data = mock_runtime_data

    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    class Services:
        registry = {}

        def async_register(
            self, domain, name, handler, schema=None, supports_response=None
        ):
            if domain == "ev_trip_planner":
                self.registry[name] = handler

    mock_hass.services = Services()

    register_services(mock_hass)

    handler = mock_hass.services.registry["trip_create"]
    call = MagicMock()
    call.data = {
        "vehicle_id": "chispitas",
        "type": "recurrente",
        "dia_semana": "lunes",
        "hora": "09:00",
        "km": 24.0,
        "kwh": 3.6,
        "descripcion": "Trabajo",
    }

    await handler(call)

    mock_trip_manager._crud.async_add_recurring_trip.assert_awaited_once_with(
        dia_semana="lunes",
        hora="09:00",
        km=24.0,
        kwh=3.6,
        descripcion="Trabajo",
    )


@pytest.mark.asyncio
async def test_trip_create_with_punctual_type_succeeds():
    """handle_trip_create creates a punctual trip when type='puntual'.

    This covers the 'puntual' branch in services.py.
    """
    from custom_components.ev_trip_planner.services import register_services

    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_chispitas"
    mock_entry.data = {"vehicle_name": "Chispitas"}
    mock_entry.unique_id = "chispitas_unique"

    mock_coordinator = MagicMock()
    mock_coordinator.async_refresh_trips = AsyncMock()
    mock_trip_manager = MagicMock()
    mock_trip_manager.async_setup = AsyncMock()
    mock_trip_manager._crud.async_add_punctual_trip = AsyncMock(
        return_value="pun_20251119_abc"
    )
    mock_trip_manager._crud.async_get_punctual_trips = AsyncMock(
        return_value=[
            {
                "id": "pun_20251119_abc",
                "datetime": "2025-11-19T15:00:00",
                "km": 110.0,
                "kwh": 16.5,
                "descripcion": "Viaje",
            }
        ]
    )

    mock_runtime_data = MagicMock()
    mock_runtime_data.trip_manager = mock_trip_manager
    mock_runtime_data.coordinator = mock_coordinator
    mock_entry.runtime_data = mock_runtime_data

    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    class Services:
        registry = {}

        def async_register(
            self, domain, name, handler, schema=None, supports_response=None
        ):
            if domain == "ev_trip_planner":
                self.registry[name] = handler

    mock_hass.services = Services()

    register_services(mock_hass)

    handler = mock_hass.services.registry["trip_create"]
    call = MagicMock()
    call.data = {
        "vehicle_id": "chispitas",
        "type": "puntual",
        "datetime": "2025-11-19T15:00:00",
        "km": 110.0,
        "kwh": 16.5,
        "descripcion": "Viaje",
    }

    await handler(call)

    mock_trip_manager._crud.async_add_punctual_trip.assert_awaited_once_with(
        datetime_str="2025-11-19T15:00:00",
        km=110.0,
        kwh=16.5,
        descripcion="Viaje",
    )
