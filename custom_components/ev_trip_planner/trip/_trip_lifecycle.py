"""Trip lifecycle operations.

Migrated from _trip_lifecycle_mixin.py. Plain class (no inheritance).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .state import TripManagerState

_LOGGER = logging.getLogger(__name__)


class TripLifecycle:
    """Bulk deletion, pause/resume, complete/cancel, sensor refresh."""

    def __init__(self, state: TripManagerState) -> None:
        """Initialize with shared state."""
        self._state = state

    # ── Public API ───────────────────────────────────────────────

    async def async_delete_all_trips(self) -> None:
        """Deletes all recurring and punctual trips for cascade deletion."""
        state = self._state

        state._trips = {}
        state.recurring_trips = {}
        state.punctual_trips = {}
        await state.async_save_trips()

        adapter = state.emhass_adapter
        if adapter:
            adapter._published_trips = set()
            adapter._cached_per_trip_params.clear()
            adapter._cached_power_profile = []
            adapter._cached_deferrables_schedule = []

        if adapter:
            await state._schedule.publish_deferrable_loads([])
            adapter._published_trips = set()
            adapter._cached_per_trip_params.clear()
            adapter._cached_power_profile = []
            adapter._cached_deferrables_schedule = []

        try:
            config_entries = state.hass.config_entries
            entry = config_entries.async_get_entry(state.entry_id or "")
            if entry and hasattr(entry, "runtime_data") and entry.runtime_data:
                coordinator = getattr(entry.runtime_data, "coordinator", None)
                if coordinator is not None:
                    existing_data = coordinator.data or {}
                    coordinator.data = {
                        **existing_data,
                        "per_trip_emhass_params": {},
                        "emhass_power_profile": [],
                        "emhass_deferrables_schedule": [],
                    }
                    await coordinator.async_refresh()
        except Exception as err:
            _LOGGER.warning("Coordinator cleanup during delete_all: %s", err)

        _LOGGER.info("Deleted all trips for vehicle %s", state.vehicle_id)

    async def async_pause_recurring_trip(self, trip_id: str) -> None:
        """Pausa un viaje recurrente."""
        state = self._state
        if trip_id in state.recurring_trips:
            state.recurring_trips[trip_id]["activo"] = False
            await state.async_save_trips()
            _LOGGER.info(
                "Paused recurring trip %s for vehicle %s", trip_id, state.vehicle_id
            )
        else:
            _LOGGER.warning(
                "Recurring trip %s not found for pause in vehicle %s",
                trip_id,
                state.vehicle_id,
            )

    async def async_resume_recurring_trip(self, trip_id: str) -> None:
        """Reanuda un viaje recurrente."""
        state = self._state
        if trip_id in state.recurring_trips:
            state.recurring_trips[trip_id]["activo"] = True
            await state.async_save_trips()
            _LOGGER.info(
                "Resumed recurring trip %s for vehicle %s", trip_id, state.vehicle_id
            )
        else:
            _LOGGER.warning(
                "Recurring trip %s not found for resume in vehicle %s",
                trip_id,
                state.vehicle_id,
            )

    async def async_complete_punctual_trip(self, trip_id: str) -> None:
        """Marca un viaje puntual como completado."""
        state = self._state
        if trip_id in state.punctual_trips:
            state.punctual_trips[trip_id]["estado"] = "completado"
            await state.async_save_trips()
            _LOGGER.info(
                "Completed punctual trip %s for vehicle %s", trip_id, state.vehicle_id
            )
        else:
            _LOGGER.warning(
                "Punctual trip %s not found for completion in vehicle %s",
                trip_id,
                state.vehicle_id,
            )

    async def async_cancel_punctual_trip(self, trip_id: str) -> None:
        """Cancela un viaje puntual."""
        state = self._state
        if trip_id in state.punctual_trips:
            del state.punctual_trips[trip_id]
            await state.async_save_trips()
            _LOGGER.info(
                "Cancelled punctual trip %s for vehicle %s", trip_id, state.vehicle_id
            )
            if state.emhass_adapter:
                await state._emhass_sync._async_remove_trip_from_emhass(trip_id)
        else:
            _LOGGER.warning(
                "Punctual trip %s not found for cancellation in vehicle %s",
                trip_id,
                state.vehicle_id,
            )

    async def async_update_trip_sensor(
        self, trip_id: str
    ) -> None:  # pragma: no cover reason=ha-entity-registry
        """Update the Home Assistant sensor entity for an updated trip."""
        state = self._state
        try:
            from homeassistant.helpers import entity_registry as er

            registry = er.async_get(state.hass)
            entity_id = f"sensor.trip_{trip_id}"
            existing_entry = registry.async_get(entity_id)

            if existing_entry is None:
                return

            trip_data: Dict[str, Any] | None = None
            trip_type: str | None = None
            if trip_id in state.recurring_trips:
                trip_data = state.recurring_trips[trip_id]
                trip_type = "recurring"
            elif trip_id in state.punctual_trips:
                trip_data = state.punctual_trips[trip_id]
                trip_type = "punctual"

            if trip_data is None:
                _LOGGER.warning(
                    "Trip %s not found for sensor update in vehicle %s",
                    trip_id,
                    state.vehicle_id,
                )
                return

            state_attributes = {
                "trip_id": trip_id,
                "trip_type": trip_type,
                "descripcion": trip_data.get("descripcion", ""),
                "km": trip_data.get("km", 0.0),
                "kwh": trip_data.get("kwh", 0.0),
                "fecha_hora": trip_data.get("datetime", trip_data.get("hora", "")),
                "activo": trip_data.get("activo", True),
                "estado": trip_data.get("estado", "pendiente"),
            }

            native_value = (
                trip_data.get("estado", "pendiente")
                if trip_type == "punctual"
                else "recurrente"
            )

            state.hass.states.async_set(
                entity_id, native_value, attributes=state_attributes
            )
        except Exception as err:  # pragma: no cover reason=ha-entity-registry
            _LOGGER.error(
                "Error updating trip sensor for trip %s: %s",
                trip_id,
                err,
                exc_info=True,
            )
