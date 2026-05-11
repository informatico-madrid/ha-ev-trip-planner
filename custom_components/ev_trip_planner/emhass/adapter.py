"""EMHASS adapter — facade delegating to sub-components."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .error_handler import ErrorHandler
from .index_manager import IndexManager
from .load_publisher import LoadPublisher


class EMHASSAdapter:
    """Facade for EMHASS operations delegating to sub-components.

    Composes IndexManager, LoadPublisher, and ErrorHandler to provide
    a unified interface while maintaining single responsibility per component.
    """

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Initialize the EMHASS adapter facade.

        Args:
            hass: HomeAssistant instance.
            entry: ConfigEntry for the integration.
        """
        self.hass = hass
        self._entry = entry

        # Sub-component initialization
        vehicle_id = entry.entry_id if hasattr(entry, "entry_id") else "unknown"
        self._index_manager = IndexManager()
        self._load_publisher = LoadPublisher(
            hass=hass,
            vehicle_id=vehicle_id,
        )
        self._error_handler = ErrorHandler(hass=hass)

    async def async_load(self) -> None:
        """Load adapter state from storage."""
        await self._index_manager.async_load_index()

    async def async_save(self) -> None:
        """Save adapter state to storage."""
        await self._index_manager.async_save_index()

    async def async_assign_index_to_trip(self, trip_id: str) -> Optional[int]:
        """Assign an index to a trip."""
        try:
            return await self._index_manager.async_assign_index_to_trip(trip_id)
        except Exception as err:
            self._error_handler.handle_error("assign_index", err, {"trip_id": trip_id})
            return None

    async def async_release_trip_index(self, trip_id: str) -> bool:
        """Release an index for a trip."""
        try:
            result = await self._index_manager.async_release_index(trip_id)
            if result is None:
                self._error_handler.handle_index_error(trip_id, "release")
                return False
            return True
        except Exception as err:
            self._error_handler.handle_error("release_index", err, {"trip_id": trip_id})
            return False

    async def async_publish_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """Publish a trip as a deferrable load."""
        try:
            return await self._load_publisher.publish(trip)
        except Exception as err:
            self._error_handler.handle_error("publish", err, {"trip": trip.get("id")})
            return False

    async def async_remove_deferrable_load(self, trip_id: str) -> bool:
        """Remove a deferrable load."""
        try:
            return await self._load_publisher.remove(trip_id)
        except Exception as err:
            self._error_handler.handle_error("remove", err, {"trip_id": trip_id})
            return False

    async def async_update_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """Update an existing deferrable load."""
        try:
            return await self._load_publisher.update(trip)
        except Exception as err:
            self._error_handler.handle_error("update", err, {"trip": trip.get("id")})
            return False

    def get_assigned_index(self, trip_id: str) -> Optional[int]:
        """Get the assigned index for a trip."""
        return self._index_manager._index_map.get(trip_id)

    def get_all_assigned_indices(self) -> Dict[str, int]:
        """Get all assigned indices."""
        return dict(self._index_manager._index_map)

    def get_available_indices(self) -> List[int]:
        """Get list of available indices."""
        if not self._index_manager._index_map:
            return [0]
        max_idx = max(self._index_manager._index_map.values())
        return list(range(max_idx + 1))

    async def async_notify_error(
        self,
        error_message: str,
        trip_id: Optional[str] = None,
    ) -> None:
        """Notify about an EMHASS error."""
        self._error_handler.handle_error("notify", Exception(error_message), {"trip_id": trip_id})
