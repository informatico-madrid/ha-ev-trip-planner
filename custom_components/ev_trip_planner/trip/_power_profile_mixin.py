"""Power profile mixin for TripManager — extracted from trip_manager.py.

Contains the `async_generate_power_profile` method that generates the power
profile for EMHASS charging optimization.

The mixin reads shared state from `self` (inherited via MRO):
- `self._trips`, `self._recurring_trips`, `self._punctual_trips`
- `self.hass`, `self.vehicle_controller`
- `self._entry_id`
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class _PowerProfileMixin:
    """Mixin providing power profile generation for TripManager.

    This mixin encapsulates power profile generation logic. The host class
    (TripManager) provides shared state access via MRO:
    self.hass, self._trips, self._recurring_trips, self._punctual_trips,
    self.vehicle_controller, self._entry_id.
    """

    def __init__(self) -> None:
        """Initialize the power profile mixin (no state to initialize)."""

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
        await self._load_trips()

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
                entry_id = getattr(self, "_entry_id", None)
                if entry_id:
                    config_entry = self.hass.config_entries.async_get_entry(entry_id)
                else:
                    config_entry = self.hass.config_entries.async_get_entry(
                        self.vehicle_id
                    )

                # If direct lookup failed, scan entries by vehicle_name (tests
                # and older setups may rely on that behaviour).
                if config_entry is None:
                    try:
                        entries = self.hass.config_entries.async_entries(DOMAIN)
                        for e in entries:
                            if not getattr(e, "data", None):
                                continue
                            name = e.data.get("vehicle_name")
                            if (
                                name
                                and name.lower().replace(" ", "_") == self.vehicle_id
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
            soc_current = await self.async_get_vehicle_soc(self.vehicle_id)

        # Obtener hora_regreso si no fue proporcionada
        if (
            hora_regreso is None
            and self.vehicle_controller
            and self.vehicle_controller._presence_monitor
        ):
            hora_regreso = (
                await self.vehicle_controller._presence_monitor.async_get_hora_regreso()
            )

        # Obtener todos los viajes pendientes
        all_trips = []
        for trip in self._recurring_trips.values():
            if trip.get("activo", True):
                all_trips.append(trip)
        for trip in self._punctual_trips.values():
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
