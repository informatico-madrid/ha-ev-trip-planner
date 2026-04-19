"""Coordinator for EV Trip Planner integration.

Provides TripPlannerCoordinator which manages the data update cycle for all
EV Trip Planner sensors, reading from TripManager and exposing data via
coordinator.data for CoordinatorEntity-based sensors.

Phase 1: Defines full data contract with EMHASS keys as None placeholders.
Phase 3: EMHASS keys are populated from emhass_adapter computation results.
"""

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_VEHICLE_NAME, DOMAIN
from .emhass_adapter import EMHASSAdapter
from .trip_manager import TripManager

_LOGGER = logging.getLogger(__name__)


class TripPlannerCoordinator(DataUpdateCoordinator):
    """Coordinator for EV Trip Planner data updates.

    This coordinator holds the canonical view of all EV Trip Planner data,
    reading from TripManager on each refresh cycle and exposing it via
    coordinator.data for all sensors to consume via CoordinatorEntity pattern.

    Data contract (Phase 1 - EMHASS keys as None):
        {
            "recurring_trips": dict of trip_id -> trip_data,
            "punctual_trips": dict of trip_id -> trip_data,
            "kwh_today": float,
            "hours_today": float,
            "next_trip": dict or None,
            "emhass_power_profile": None,      # populated in Phase 3
            "emhass_deferrables_schedule": None,  # populated in Phase 3
            "emhass_status": None,             # "ready" | "computing" | None
        }
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        trip_manager: TripManager,
        emhass_adapter: EMHASSAdapter | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: HomeAssistant instance.
            entry: ConfigEntry for this vehicle/device.
            trip_manager: TripManager instance for this vehicle.
            emhass_adapter: Optional EMHASSAdapter instance for EMHASS data.
            logger: Optional logger instance for DataUpdateCoordinator.
        """
        super().__init__(
            hass,
            logger=logger or _LOGGER,
            name=f"{DOMAIN} ({entry.entry_id})",
            update_interval=timedelta(seconds=30),
        )
        self._trip_manager = trip_manager
        self._entry = entry
        self._emhass_adapter = emhass_adapter
        self._vehicle_id = (
            self._entry.data.get(CONF_VEHICLE_NAME, "unknown")
            .lower()
            .replace(" ", "_")
        )

    @property
    def vehicle_id(self) -> str:
        """Return normalized vehicle_id from config entry.

        Returns:
            Normalized vehicle_id (lowercase, spaces replaced with underscores),
            or "unknown" if CONF_VEHICLE_NAME is missing from entry.data.
        """
        return self._vehicle_id

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest data from TripManager and build coordinator.data dict.

        This method is called by DataUpdateCoordinator on each refresh cycle.
        It reads current state from TripManager and builds the full data dict
        with all keys defined in the contract.

        Returns:
            Full data dict with EMHASS keys as None (Phase 1).
        """
        # E2E-DEBUG-CRITICAL: Log when _async_update_data is called
        _LOGGER.warning(
            "E2E-DEBUG coordinator _async_update_data called for vehicle %s",
            self._vehicle_id,
        )
        # E2E-DEBUG-CRITICAL: Log current trips from trip_manager
        _LOGGER.warning(
            "E2E-DEBUG coordinator _async_update_data: trip_manager trips before EMHASS fetch"
        )
        # Get recurring trips as list, convert to dict keyed by trip_id
        recurring_list = await self._trip_manager.async_get_recurring_trips()
        recurring_trips = {
            trip["id"]: trip
            for trip in recurring_list
            if "id" in trip
        }

        # Get punctual trips as list, convert to dict keyed by trip_id
        punctual_list = await self._trip_manager.async_get_punctual_trips()
        punctual_trips = {
            trip["id"]: trip
            for trip in punctual_list
            if "id" in trip
        }

        # Get today's energy and hours needs
        kwh_today = await self._trip_manager.async_get_kwh_needed_today()
        hours_today = float(
            await self._trip_manager.async_get_hours_needed_today()
        )

        # Get next scheduled trip
        next_trip = await self._trip_manager.async_get_next_trip()

        # PHASE 3 (3.4): Get EMHASS data from emhass_adapter if available
        if self._emhass_adapter is not None:
            emhass_data = (
                self._emhass_adapter.get_cached_optimization_results()
            )
            per_trip_params = emhass_data.get("per_trip_emhass_params", {})
            # DEBUG: Log cache state when reading
            _LOGGER.warning(
                "DEBUG coordinator _async_update_data: per_trip_emhass_params has %d entries, "
                "emhass_power_profile non_zero=%d for vehicle %s",
                len(per_trip_params),
                sum(1 for x in emhass_data.get("emhass_power_profile", []) if x > 0) if emhass_data.get("emhass_power_profile") else 0,
                self._vehicle_id,
            )
        else:
            emhass_data = {
                "emhass_power_profile": None,
                "emhass_deferrables_schedule": None,
                "emhass_status": None,
            }

        # E2E-DEBUG-CRITICAL: Log complete returned coordinator.data structure
        _LOGGER.warning(
            "E2E-DEBUG coordinator _async_update_data: returning data with keys=%s",
            list({"recurring_trips": recurring_trips, "punctual_trips": punctual_trips, "kwh_today": kwh_today, "hours_today": hours_today, "next_trip": next_trip, **emhass_data}.keys()),
        )
        _LOGGER.warning(
            "E2E-DEBUG coordinator _async_update_data: returning per_trip_emhass_params=%s",
            emhass_data.get("per_trip_emhass_params", "NOT_IN_DICT"),
        )

        return {
            "recurring_trips": recurring_trips,
            "punctual_trips": punctual_trips,
            "kwh_today": kwh_today,
            "hours_today": hours_today,
            "next_trip": next_trip,
            **emhass_data,
        }

    async def async_refresh_trips(self) -> None:
        """Refresh trip data from TripManager.

        This method is called by service handlers after trip CRUD operations
        to trigger an immediate refresh of the coordinator data.
        """
        await self.async_refresh()
