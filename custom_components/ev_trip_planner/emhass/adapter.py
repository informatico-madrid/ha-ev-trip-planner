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
        self.vehicle_id = entry.entry_id if hasattr(entry, "entry_id") else "unknown"
        self.entry_id = getattr(entry, "entry_id", "unknown")

        # Sub-component initialization
        self._index_manager = IndexManager()
        self._load_publisher = LoadPublisher(
            hass=hass,
            vehicle_id=self.vehicle_id,
        )
        self._error_handler = ErrorHandler(hass=hass)

        # State attributes (used by callers and tests)
        self._published_trips: list[Dict[str, Any]] = []
        self._cached_per_trip_params: Dict[str, Any] = {}
        self._cached_power_profile: List[Any] | None = None
        self._cached_deferrables_schedule: List[Any] | None = None
        self._cached_emhass_status: str | None = None
        self._config_entry_listener = None
        self._shutting_down = False
        self._charging_power_kw: float | None = None
        self._stored_charging_power_kw: float | None = None
        self._stored_t_base: float | None = None
        self._stored_soh_sensor: str | None = None

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

    def get_cached_optimization_results(self) -> Dict[str, Any]:
        """Return cached optimization results for coordinator retrieval.

        Returns:
            Dict with emhass_power_profile, emhass_deferrables_schedule,
            emhass_status, and per_trip_emhass_params keys.
        """
        return {
            "emhass_power_profile": self._cached_power_profile,
            "emhass_deferrables_schedule": self._cached_deferrables_schedule,
            "emhass_status": self._cached_emhass_status,
            "per_trip_emhass_params": self._cached_per_trip_params,
        }

    async def update_charging_power(self, force: bool = False) -> None:
        """Update charging power and republish sensor attributes if changed.

        Args:
            force: If True, skip the unchanged-power early-return and always
                   republish.
        """
        if self._shutting_down:
            return

        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        if not entry:
            return

        new_power = entry.options.get("charging_power_kw")
        if new_power is None:
            new_power = entry.data.get("charging_power_kw")
        if new_power is None:
            return

        if not force and new_power == self._charging_power_kw:
            return

        self._charging_power_kw = new_power
        self._stored_charging_power_kw = new_power

    def setup_config_entry_listener(self) -> None:
        """Subscribe to config entry updates to trigger republish when charging power changes."""
        self.config_entry = self.hass.config_entries.async_get_entry(self.entry_id)
        if not self.config_entry:
            return
        self._config_entry_listener = self.config_entry.async_on_unload(
            self.config_entry.add_update_listener(self._handle_config_entry_update)
        )

    async def _handle_config_entry_update(
        self, hass: HomeAssistant, config_entry: ConfigEntry
    ) -> None:
        """Handle config entry update events."""
        if self._shutting_down:
            return

        cur_options = dict(getattr(config_entry, "options", {}) or {})
        new_charging_power = cur_options.get("charging_power_kw")
        if new_charging_power is not None:
            self._stored_charging_power_kw = new_charging_power
            self._charging_power_kw = new_charging_power

    async def async_publish_all_deferrable_loads(
        self, trips: List[Dict[str, Any]], charging_power: float | None = None
    ) -> bool:
        """Publish all trips as deferrable loads.

        Args:
            trips: List of trip dictionaries to publish.
            charging_power: Optional charging power override.

        Returns:
            True if all trips were published successfully.
        """
        if not trips or self._shutting_down:
            return False

        if charging_power is not None:
            self._load_publisher.charging_power_kw = charging_power

        success = True
        self._published_trips = list(trips)
        self._cached_per_trip_params = {}
        self._cached_power_profile = []
        self._cached_deferrables_schedule = []

        for trip in trips:
            trip_success = await self.async_publish_deferrable_load(trip)
            if not trip_success:
                success = False

        return success

    async def async_cleanup_vehicle_indices(self) -> None:
        """Clean up all indices for this vehicle."""
        indices_to_release = list(self._index_manager._index_map.keys())
        for trip_id in indices_to_release:
            self._index_manager.release_index(trip_id)
        self._published_trips = []
        self._cached_per_trip_params = {}
        self._cached_power_profile = []
        self._cached_deferrables_schedule = []

    async def async_save_trips(self) -> None:
        """Save trips to storage."""
        await self._index_manager.async_save_index()

    def calculate_deferrable_parameters(self, trips: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate deferrable parameters from trips.

        Args:
            trips: List of trip dictionaries.

        Returns:
            Dict with calculated parameters.
        """
        return {}
