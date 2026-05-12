"""Power profile mixin for TripManager — extracted from trip_manager.py.

Contains the `async_generate_power_profile` method that generates the power
profile for EMHASS charging optimization.

This mixin uses composition: it receives a `TripManagerState` instance
in `__init__` and accesses all shared state through `self._state.xxx`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry

from ..const import DOMAIN

from .state import TripManagerState

_LOGGER = logging.getLogger(__name__)


class _PowerProfileMixin:
    """Mixin providing power profile generation for TripManager.

    Uses composition — receives TripManagerState in __init__ and stores it
    as self._state. All shared state access goes through self._state.xxx.
    """

    def __init__(self, state: TripManagerState) -> None:
        """Initialize the power profile mixin with shared state."""
        self._state = state

    async def async_generate_power_profile(
        self,
        charging_power_kw: float = 3.6,
        planning_horizon_days: int = 7,
        vehicle_config: Optional[Dict[str, Any]] = None,
        hora_regreso: Optional[datetime] = None,
    ) -> List[float]:
        """Genera el perfil de potencia para EMHASS.

        Args:
            charging_power_kw: Potencia de carga en kW
            planning_horizon_days: Días de horizonte de planificación
            vehicle_config: Optional configuration dict with battery_capacity_kwh,
                          charging_power_kw, soc_current
            hora_regreso: Optional actual return time. If None, reads from
                         presence_monitor.async_get_hora_regreso()

        Returns:
            Lista de valores de potencia en watts (0 = no cargar, positivo = cargar)
        """
        from ..calculations import calculate_power_profile

        # Cargar viajes
        await self._state._load_trips()

        # Obtener configuración del vehículo
        if vehicle_config:
            battery_capacity = vehicle_config.get("battery_capacity_kwh", 50.0)
            soc_current = vehicle_config.get("soc_current")
            safety_margin_percent = vehicle_config.get("safety_margin_percent", 10.0)
        else:
            try:
                # Lookup by real config entry id when available; fall back to
                # legacy behaviour using vehicle_id for backward compatibility.
                config_entry: Optional[ConfigEntry[Any]] = None
                entry_id = self._state.entry_id
                if entry_id:
                    config_entry = self._state.hass.config_entries.async_get_entry(entry_id)
                else:
                    config_entry = self._state.hass.config_entries.async_get_entry(
                        self._state.vehicle_id
                    )

                # If direct lookup failed, scan entries by vehicle_name (tests
                # and older setups may rely on that behaviour).
                if config_entry is None:
                    try:
                        entries = self._state.hass.config_entries.async_entries(DOMAIN)
                        for e in entries:
                            if not getattr(e, "data", None):
                                continue
                            name = e.data.get("vehicle_name")
                            if (
                                name
                                and name.lower().replace(" ", "_") == self._state.vehicle_id
                            ):
                                config_entry = e
                                break
                    except Exception:
                        config_entry = None

                if config_entry is not None and config_entry.data is not None:
                    battery_capacity = config_entry.data.get(
                        "battery_capacity_kwh", 50.0
                    )
                    safety_margin_percent = config_entry.data.get(
                        "safety_margin_percent", 10.0
                    )
                else:
                    battery_capacity = 50.0
                    safety_margin_percent = 10.0
            except Exception:
                battery_capacity = 50.0
                safety_margin_percent = 10.0
            soc_current = None

        # Obtener SOC actual - only fetch if not provided in vehicle_config
        if soc_current is None:
            soc_current = await self._state.async_get_vehicle_soc(self._state.vehicle_id)

        # Obtener hora_regreso si no fue proporcionada
        if (
            hora_regreso is None
            and self._state.vehicle_controller
            and self._state.vehicle_controller._presence_monitor
        ):
            hora_regreso = (
                await self._state.vehicle_controller._presence_monitor.async_get_hora_regreso()
            )

        # Obtener todos los viajes pendientes
        all_trips = []
        for trip in self._state.recurring_trips.values():
            if trip.get("activo", True):
                all_trips.append(trip)
        for trip in self._state.punctual_trips.values():
            if (
                trip.get("estado") == "pendiente"
            ):  # pragma: no cover  # HA storage I/O - estado filter for pending trips
                all_trips.append(
                    trip
                )  # pragma: no cover  # HA storage I/O - appending pending trips to list

        # Delegate pure power profile calculation to calculations.py
        return calculate_power_profile(
            all_trips=all_trips,
            battery_capacity_kwh=battery_capacity,
            soc_current=soc_current,
            charging_power_kw=charging_power_kw,
            hora_regreso=hora_regreso,
            planning_horizon_days=planning_horizon_days,
            reference_dt=datetime.now(timezone.utc),
            safety_margin_percent=safety_margin_percent,
        )
