"""EMHASS sync helpers.

Migrated from _emhass_sync_mixin.py. Plain class (no inheritance).
All methods are private (prefixed with _).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from .state import TripManagerState

_LOGGER = logging.getLogger(__name__)

_RECALC_FIELDS = {
    "km",
    "kwh",
    "datetime",
    "hora",
    "dia_semana",
    "descripcion",
}


class EMHASSSync:
    """EMHASS sync helpers used by trip-CRUD operations.

    All public methods are private to this class — TripManager accesses
    them via state-level references rather than direct calls.
    """

    def __init__(self, state: TripManagerState) -> None:
        """Initialize with shared state."""
        self._state = state

    # ── All private helpers ──────────────────────────────────────

    async def _async_sync_trip_to_emhass(
        self, trip_id: str, old_trip: Dict[str, Any], updates: Dict[str, Any]
    ) -> None:
        """Sync trip changes to EMHASS adapter."""
        state = self._state
        adapter = state.emhass_adapter
        if not adapter:
            return

        try:
            is_active = True
            if trip_id in state.recurring_trips:
                is_active = state.recurring_trips[trip_id].get("activo", True)
            elif trip_id in state.punctual_trips:
                is_active = state.punctual_trips[trip_id].get("estado") == "pendiente"

            if not is_active:
                await self._async_remove_trip_from_emhass(trip_id)
                _LOGGER.info("Trip %s is inactive, removed from EMHASS", trip_id)
                return

            trip = None
            if trip_id in state.recurring_trips:
                trip = state.recurring_trips[trip_id]
            elif trip_id in state.punctual_trips:
                trip = state.punctual_trips[trip_id]

            if not trip:
                await self._async_remove_trip_from_emhass(trip_id)
                return

            changed_fields = set(updates.keys())
            needs_recalculate = bool(changed_fields & _RECALC_FIELDS)

            if needs_recalculate:
                await adapter.async_update_deferrable_load(trip)
                await state._schedule.publish_deferrable_loads()
                _LOGGER.info(
                    "Trip %s updated in EMHASS (recalculated): fields=%s",
                    trip_id,
                    changed_fields,
                )
            else:
                await adapter.async_update_deferrable_load(trip)
                _LOGGER.debug(
                    "Trip %s updated in EMHASS (attributes): fields=%s",
                    trip_id,
                    changed_fields,
                )
        except Exception as err:
            _LOGGER.error("Error syncing trip %s to EMHASS: %s", trip_id, err)

    async def _async_remove_trip_from_emhass(self, trip_id: str) -> None:
        """Remove a trip from EMHASS deferrable loads."""
        state = self._state
        adapter = state.emhass_adapter
        if not adapter:
            return
        try:
            await adapter.async_remove_deferrable_load(trip_id)
            await state._schedule.publish_deferrable_loads()
            _LOGGER.info("Trip %s removed from EMHASS", trip_id)
        except Exception as err:
            _LOGGER.error("Error removing trip %s from EMHASS: %s", trip_id, err)

    async def _async_publish_new_trip_to_emhass(self, trip: Dict[str, Any]) -> None:
        """Publish a new trip to EMHASS as a deferrable load."""
        state = self._state
        adapter = state.emhass_adapter
        if not adapter:
            return
        try:
            await adapter.async_publish_deferrable_load(trip)
            await state._schedule.publish_deferrable_loads()
            _LOGGER.info("Published new trip %s to EMHASS", trip.get("id"))
        except Exception as err:
            _LOGGER.error("Error publishing trip %s to EMHASS: %s", trip.get("id"), err)

    async def _get_all_active_trips(self) -> List[Dict[str, Any]]:
        """Get all active trips for EMHASS publishing."""
        state = self._state
        all_trips: List[Dict[str, Any]] = []
        for trip in state.recurring_trips.values():
            if trip.get("activo", True):
                all_trips.append(trip)
        for trip in state.punctual_trips.values():
            if trip.get("estado") == "pendiente":
                all_trips.append(trip)
        return all_trips
