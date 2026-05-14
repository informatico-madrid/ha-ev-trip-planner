"""Core trip CRUD operations.

Migrated from _crud_mixin.py. Plain class (no inheritance) owning
add/update/delete/read for trips.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..const import TRIP_TYPE_PUNCTUAL, TRIP_TYPE_RECURRING
from ..utils import generate_trip_id, validate_hora
from ._sensor_callbacks import SensorEvent, emit
from .state import TripManagerState

_LOGGER = logging.getLogger(__name__)

_RECURRENT_RELEVANT_FIELDS = frozenset(
    {
        "dia_semana",
        "hora",
        "km",
        "kwh",
        "descripcion",
        "activo",
        "tipo",
        "id",
    }
)
_PUNCTUAL_RELEVANT_FIELDS = frozenset(
    {
        "datetime",
        "km",
        "kwh",
        "descripcion",
        "activo",
        "tipo",
        "id",
    }
)


class TripCRUD:
    """Core trip CRUD operations."""

    def __init__(self, state: TripManagerState) -> None:
        """Initialize with shared state."""
        self._state = state

    # ── Read accessors ───────────────────────────────────────────

    async def async_get_recurring_trips(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de viajes recurrentes."""
        return list(self._state.recurring_trips.values())

    async def async_get_punctual_trips(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de viajes puntuales."""
        return list(self._state.punctual_trips.values())

    # ── Add ──────────────────────────────────────────────────────

    async def async_add_recurring_trip(self, **kwargs: Any) -> None:
        """Añade un nuevo viaje recurrente y sincroniza con EMHASS."""
        state = self._state
        _LOGGER.debug(
            "Adding recurring trip for vehicle %s: dia_semana=%s, hora=%s, km=%.1f, kwh=%.2f",
            state.vehicle_id,
            kwargs.get("dia_semana"),
            kwargs.get("hora"),
            kwargs.get("km", 0),
            kwargs.get("kwh", 0),
        )
        validate_hora(kwargs.get("hora", ""))

        trip_id = kwargs.get("trip_id") or generate_trip_id(
            "recurrente", kwargs.get("dia_semana", "lunes")
        )
        state.recurring_trips[trip_id] = {
            "id": trip_id,
            "tipo": TRIP_TYPE_RECURRING,
            "dia_semana": kwargs["dia_semana"],
            "hora": kwargs["hora"],
            "km": kwargs["km"],
            "kwh": kwargs["kwh"],
            "descripcion": kwargs.get("descripcion", ""),
            "activo": True,
        }
        await state.async_save_trips()
        _LOGGER.info(
            "Added recurring trip %s for vehicle %s", trip_id, state.vehicle_id
        )

        entry_id = state.entry_id or ""
        emit(
            SensorEvent(
                "trip_created_recurring",
                state.hass,
                entry_id,
                trip_data=state.recurring_trips[trip_id],
                trip_id=trip_id,
                vehicle_id=state.vehicle_id,
            )
        )
        emit(
            SensorEvent(
                "trip_sensor_created_emhass",
                state.hass,
                entry_id,
                trip_id=trip_id,
                vehicle_id=state.vehicle_id,
            )
        )

        if state.emhass_adapter:
            await state._emhass_sync._async_publish_new_trip_to_emhass(
                state.recurring_trips[trip_id]
            )

    async def async_add_punctual_trip(self, **kwargs: Any) -> None:
        """Añade un nuevo viaje puntual y sincroniza con EMHASS."""
        state = self._state
        _LOGGER.debug(
            "Adding punctual trip for vehicle %s: datetime=%s, km=%.1f, kwh=%.2f",
            state.vehicle_id,
            kwargs.get("datetime_str", kwargs.get("datetime", "")),
            kwargs.get("km", 0),
            kwargs.get("kwh", 0),
        )
        datetime_str = kwargs.get("datetime_str", kwargs.get("datetime", ""))
        date_part = datetime_str.split("T")[0].replace("-", "") if datetime_str else ""
        trip_id = kwargs.get("trip_id") or generate_trip_id("punctual", date_part)
        state.punctual_trips[trip_id] = {
            "id": trip_id,
            "tipo": TRIP_TYPE_PUNCTUAL,
            "datetime": datetime_str,
            "km": kwargs["km"],
            "kwh": kwargs["kwh"],
            "descripcion": kwargs.get("descripcion", ""),
            "estado": "pendiente",
        }
        await state.async_save_trips()
        _LOGGER.info("Added punctual trip %s for vehicle %s", trip_id, state.vehicle_id)

        entry_id = state.entry_id or ""
        emit(
            SensorEvent(
                "trip_created_punctual",
                state.hass,
                entry_id,
                trip_data=state.punctual_trips[trip_id],
                trip_id=trip_id,
                vehicle_id=state.vehicle_id,
            )
        )
        emit(
            SensorEvent(
                "trip_sensor_created_emhass",
                state.hass,
                entry_id,
                trip_id=trip_id,
                vehicle_id=state.vehicle_id,
            )
        )

        if state.emhass_adapter:
            await state._emhass_sync._async_publish_new_trip_to_emhass(
                state.punctual_trips[trip_id]
            )

    # ── Update ───────────────────────────────────────────────────

    # CC-N-ACCEPTED: cc=11 — trip type dispatch (recurring vs punctual) with
    # different field sets, save, emit, EMHASS sync. Branching is domain
    # logic: each trip type has distinct relevant fields and sync requirements.
    async def async_update_trip(self, trip_id: str, updates: Dict[str, Any]) -> None:
        """Actualiza un viaje existente y sincroniza con EMHASS."""
        state = self._state
        _LOGGER.debug(
            "Updating trip %s for vehicle %s: updates=%s",
            trip_id,
            state.vehicle_id,
            updates,
        )

        old_trip: Dict[str, Any] | None = None
        trip_type: str | None = None
        if trip_id in state.recurring_trips:
            old_trip = state.recurring_trips[trip_id].copy()
            trip_type = "recurring"
            filtered = {
                k: v for k, v in updates.items() if k in _RECURRENT_RELEVANT_FIELDS
            }
            state.recurring_trips[trip_id].update(filtered)
        elif trip_id in state.punctual_trips:
            old_trip = state.punctual_trips[trip_id].copy()
            trip_type = "punctual"
            filtered = {
                k: v for k, v in updates.items() if k in _PUNCTUAL_RELEVANT_FIELDS
            }
            state.punctual_trips[trip_id].update(filtered)
        else:
            _LOGGER.warning(
                "Trip %s not found for update in vehicle %s", trip_id, state.vehicle_id
            )
            return

        await state.async_save_trips()
        _LOGGER.info(
            "Updated %s trip %s for vehicle %s", trip_type, trip_id, state.vehicle_id
        )

        trip_data = state.recurring_trips.get(trip_id) or state.punctual_trips.get(
            trip_id
        )
        if trip_data:
            emit(
                SensorEvent(
                    "trip_sensor_updated",
                    state.hass,
                    state.entry_id or "",
                    trip_data=trip_data,
                )
            )

        if state.emhass_adapter:
            await state._emhass_sync._async_sync_trip_to_emhass(
                trip_id, old_trip, updates
            )

    # ── Delete ───────────────────────────────────────────────────

    async def async_delete_trip(self, trip_id: str) -> None:
        """Elimina un viaje existente y sincroniza con EMHASS."""
        state = self._state
        _LOGGER.debug("Deleting trip %s from vehicle %s", trip_id, state.vehicle_id)

        if trip_id not in state.recurring_trips and trip_id not in state.punctual_trips:
            _LOGGER.warning(
                "Trip %s not found for deletion in vehicle %s",
                trip_id,
                state.vehicle_id,
            )
            return

        if trip_id in state.recurring_trips:
            del state.recurring_trips[trip_id]
        else:
            del state.punctual_trips[trip_id]

        await state.async_save_trips()
        _LOGGER.info("Deleted trip %s from vehicle %s", trip_id, state.vehicle_id)

        entry_id = state.entry_id or ""
        emit(SensorEvent("trip_removed", state.hass, entry_id, trip_id=trip_id))
        emit(
            SensorEvent(
                "trip_sensor_removed_emhass",
                state.hass,
                entry_id,
                trip_id=trip_id,
                vehicle_id=state.vehicle_id,
            )
        )

        if state.emhass_adapter:
            await state._emhass_sync._async_remove_trip_from_emhass(trip_id)
