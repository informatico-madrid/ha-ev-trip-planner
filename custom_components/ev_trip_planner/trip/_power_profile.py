"""Power profile generation for EMHASS charging optimization.

Migrated from _power_profile_mixin.py. Plain class (no inheritance).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry

from .state import TripManagerState

_LOGGER = logging.getLogger(__name__)


class PowerProfile:
    """Power profile generation for TripManager."""

    def __init__(self, state: TripManagerState) -> None:
        """Initialize with shared state."""
        self._state = state

    # CC-N-ACCEPTED: cc=12 — config source fallback chain (parameter →
    # config entry → defaults), SOC sensor fallback, and dual trip gathering
    # (active recurring + pending punctual). Each branch is a distinct
    # data source with independent error recovery.
    async def async_generate_power_profile(
        self,
        charging_power_kw: float = 3.6,
        planning_horizon_days: int = 7,
        vehicle_config: Optional[Dict[str, Any]] = None,
        hora_regreso: Optional[datetime] = None,
    ) -> List[float]:
        """Genera el perfil de potencia para EMHASS."""
        from ..calculations import calculate_power_profile

        await self._state._persistence._load_trips()

        battery_capacity: float = 50.0
        soc_current: Optional[float] = None
        safety_margin_percent: float = 10.0

        if vehicle_config:
            battery_capacity = vehicle_config.get("battery_capacity_kwh", 50.0)
            soc_current = vehicle_config.get("soc_current")
            safety_margin_percent = vehicle_config.get("safety_margin_percent", 10.0)
        else:
            try:
                config_entry: Optional[ConfigEntry[Any]] = None
                entry_id = self._state.entry_id
                if entry_id:
                    config_entry = self._state.hass.config_entries.async_get_entry(
                        entry_id
                    )
                else:
                    config_entry = self._state.hass.config_entries.async_get_entry(
                        self._state.vehicle_id
                    )

                if config_entry is not None and config_entry.data is not None:
                    battery_capacity = config_entry.data.get(
                        "battery_capacity_kwh", 50.0
                    )
                    soc_current = config_entry.data.get("soc_current")
                    safety_margin_percent = config_entry.data.get(
                        "safety_margin_percent", 10.0
                    )
            except Exception:
                battery_capacity = 50.0
                soc_current = 50.0
                safety_margin_percent = 10.0

        # Obtain current SOC from sensor if not provided in vehicle_config
        if soc_current is None:
            try:
                soc_current = await self._state._soc.async_get_vehicle_soc(
                    self._state.vehicle_id
                )
            except Exception:
                soc_current = 50.0

        # Gather all active trips for the power profile
        all_trips: List[Dict[str, Any]] = []
        for trip in self._state.recurring_trips.values():
            if trip.get("activo", True):
                all_trips.append(trip)
        for trip in self._state.punctual_trips.values():
            if trip.get("estado") == "pendiente":
                all_trips.append(trip)

        return calculate_power_profile(
            all_trips=all_trips,
            battery_capacity_kwh=battery_capacity,
            soc_current=soc_current or 50.0,
            charging_power_kw=charging_power_kw,
            hora_regreso=hora_regreso,
            planning_horizon_days=planning_horizon_days,
            reference_dt=datetime.now(timezone.utc),
            safety_margin_percent=safety_margin_percent,
        )
