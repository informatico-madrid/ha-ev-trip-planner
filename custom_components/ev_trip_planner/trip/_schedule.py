"""Schedule mixin for TripManager — extracted from trip_manager.py.

Migrated from _schedule_mixin.py. Plain class (no inheritance).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util

from .state import TripManagerState

_LOGGER = logging.getLogger(__name__)


class TripScheduler:
    """Mixin providing schedule generation for TripManager."""

    def __init__(self, state: TripManagerState) -> None:
        """Initialize the schedule mixin with shared state."""
        self._state = state

    async def async_generate_deferrables_schedule(
        self,
        charging_power_kw: float = 3.6,
        planning_horizon_days: int = 7,
    ) -> List[Dict[str, Any]]:
        """Genera el calendario de cargas diferibles para EMHASS."""
        await self._state._persistence._load_trips()

        try:
            _config_entry: Optional[ConfigEntry[Any]] = None
            entry_id = self._state.entry_id
            if entry_id:
                _config_entry = self._state.hass.config_entries.async_get_entry(
                    entry_id
                )
            else:
                _config_entry = self._state.hass.config_entries.async_get_entry(
                    self._state.vehicle_id
                )

            if _config_entry is not None and _config_entry.data is not None:
                _config_entry.data.get("battery_capacity_kwh", 50.0)
        except Exception:
            pass

        soc_current = await self._state._soc.async_get_vehicle_soc(
            self._state.vehicle_id
        )

        all_trips: List[Dict[str, Any]] = []
        for trip in self._state.recurring_trips.values():
            if trip.get("activo", True):
                all_trips.append(trip)
        for trip in self._state.punctual_trips.values():
            if trip.get("estado") == "pendiente":
                all_trips.append(trip)

        now = datetime.now(timezone.utc)
        for trip in all_trips:
            trip_time = self._state._soc._get_trip_time(trip)
            if trip_time:
                trip["_deadline"] = trip_time
                delta = trip_time - now
                trip["_hours_until_deadline"] = max(0, delta.total_seconds() / 3600)
            else:
                trip["_deadline"] = datetime.max
                trip["_hours_until_deadline"] = float("inf")

        all_trips.sort(key=lambda t: t.get("_hours_until_deadline", float("inf")))

        trip_indices: Dict[str, int] = {}
        for idx, trip in enumerate(all_trips):
            trip_id = trip.get("id", f"trip_{idx}")
            trip_indices[trip_id] = idx

        num_trips = len(all_trips)
        profile_length = planning_horizon_days * 24

        power_profiles: List[List[float]] = [
            [0.0] * profile_length for _ in range(num_trips)
        ]

        battery_capacity = 50.0
        safety_margin_percent = 10.0
        try:
            config_entry: Optional[ConfigEntry[Any]] = None
            entry_id = self._state.entry_id
            if entry_id:
                config_entry = self._state.hass.config_entries.async_get_entry(entry_id)
            else:
                config_entry = self._state.hass.config_entries.async_get_entry(
                    self._state.vehicle_id
                )

            if config_entry is not None and config_entry.data is not None:
                battery_capacity = config_entry.data.get("battery_capacity_kwh", 50.0)
                safety_margin_percent = config_entry.data.get(
                    "safety_margin_percent", 10.0
                )
        except Exception:
            pass

        for idx, trip in enumerate(all_trips):
            vehicle_config = {
                "battery_capacity_kwh": battery_capacity,
                "charging_power_kw": charging_power_kw,
                "soc_current": soc_current,
                "safety_margin_percent": safety_margin_percent,
            }
            energia_info = await self._state._soc.async_calcular_energia_necesaria(
                trip, vehicle_config
            )
            energia_kwh = energia_info["energia_necesaria_kwh"]
            horas_carga = energia_info["horas_carga_necesarias"]

            if energia_kwh <= 0:
                continue

            charging_power_watts = charging_power_kw * 1000
            horas_necesarias = int(horas_carga) + (1 if horas_carga % 1 > 0 else 0)

            trip_time = self._state._soc._get_trip_time(trip)
            if not trip_time:
                continue

            delta = trip_time - now
            horas_hasta_viaje = int(delta.total_seconds() / 3600)

            if horas_hasta_viaje < 0:
                continue

            hora_inicio_carga = max(0, horas_hasta_viaje - horas_necesarias)

            for h in range(
                int(hora_inicio_carga), min(int(horas_hasta_viaje), profile_length)
            ):
                power_profiles[idx][h] = charging_power_watts

        schedule = []
        now_dt = dt_util.now()

        for day in range(planning_horizon_days):
            for hour in range(24):
                timestamp = now_dt + timedelta(days=day, hours=hour)
                profile_idx = day * 24 + hour

                entry = {"date": timestamp.isoformat()}

                for trip_idx in range(num_trips):
                    power = (
                        power_profiles[trip_idx][profile_idx]
                        if profile_idx < len(power_profiles[trip_idx])
                        else 0.0
                    )
                    entry[f"p_deferrable{trip_idx}"] = f"{power:.1f}"

                if num_trips == 0:
                    entry["p_deferrable0"] = "0.0"

                schedule.append(entry)

        return schedule

    async def publish_deferrable_loads(
        self, trips: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Publishes all active trips as deferrable loads to EMHASS."""
        if trips is None:
            await self._state._persistence._load_trips()
            trips = []
            for trip in self._state.recurring_trips.values():
                if trip.get("activo", True):
                    trips.append(trip)
            for trip in self._state.punctual_trips.values():
                if trip.get("estado") == "pendiente":
                    trips.append(trip)

        adapter = self._state.emhass_adapter
        if adapter and hasattr(adapter, "async_publish_all_deferrable_loads"):
            try:
                await adapter.async_publish_all_deferrable_loads(trips)
            except Exception:
                _LOGGER.exception("Error publishing deferrable loads to EMHASS")
