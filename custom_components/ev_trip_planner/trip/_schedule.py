"""Schedule mixin for TripManager — extracted from trip_manager.py.

Migrated from _schedule_mixin.py. Plain class (no inheritance).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from homeassistant.util import dt as dt_util

from ..calculations import _helpers
from .state import TripManagerState

_LOGGER = logging.getLogger(__name__)


# qg-accepted: BMAD consensus 2026-05-13 — FALSE POSITIVE: max_arity=6 proxy for
# high CC, not a true SRP violation. TripScheduler has exactly one responsibility:
# schedule generation via 5 private methods + 2 public methods. Method arity is high
# because schedule generation requires many parameters (charging_power_kw, planning_horizon,
# battery config, etc.) — extracting parameter objects would obscure the single responsibility.
class TripScheduler:
    """Mixin providing schedule generation for TripManager."""

    def __init__(self, state: TripManagerState) -> None:
        """Initialize the schedule mixin with shared state."""
        self._state = state

    def _read_battery_config(self) -> tuple[float, float]:
        """Return (battery_capacity_kwh, safety_margin_percent) from config entry."""
        try:
            entry_id = self._state.entry_id
            if entry_id is None:
                return 50.0, 10.0
            config_entry = self._state.hass.config_entries.async_get_entry(entry_id)
            if config_entry is not None and config_entry.data is not None:
                return (
                    config_entry.data.get("battery_capacity_kwh", 50.0),
                    config_entry.data.get("safety_margin_percent", 10.0),
                )
        except Exception:
            pass
        return 50.0, 10.0

    async def _load_active_trips(self) -> List[Dict[str, Any]]:
        """Load active trips, compute deadlines, and sort by urgency."""
        all_trips = await self._state._persistence._load_trips()
        all_trips = self._state.get_active_trips()

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
        return all_trips

    async def _build_power_profiles(
        self,
        trips: List[Dict[str, Any]],
        battery_capacity: float,
        safety_margin: float,
        charging_power_kw: float,
        planning_horizon_days: int,
    ) -> tuple[List[List[float]], int]:
        """Build per-trip power profile matrix. Returns (profiles, num_trips)."""
        num_trips = len(trips)
        profile_length = planning_horizon_days * 24
        charging_power_watts = _helpers.kw_to_watts(charging_power_kw)

        power_profiles: List[List[float]] = [
            [0.0] * profile_length for _ in range(num_trips)
        ]

        now = datetime.now(timezone.utc)

        for idx, trip in enumerate(trips):
            vehicle_config = {
                "battery_capacity_kwh": battery_capacity,
                "charging_power_kw": charging_power_kw,
                "soc_current": 0.0,
                "safety_margin_percent": safety_margin,
            }
            energia_info = await self._state._soc.async_calcular_energia_necesaria(
                trip, vehicle_config
            )
            energia_kwh = energia_info["energia_necesaria_kwh"]
            horas_carga = energia_info["horas_carga_necesarias"]

            if energia_kwh <= 0:
                continue

            horas_necesarias = _helpers.ceil_hours(horas_carga)
            trip_time = self._state._soc._get_trip_time(trip)
            if not trip_time:
                continue

            delta = trip_time - now
            horas_hasta_viaje = int(delta.total_seconds() / 3600)

            if horas_hasta_viaje < 0:
                continue

            hora_inicio_carga = _helpers.compute_charging_window(
                horas_hasta_viaje, horas_necesarias
            )

            for h in range(
                int(hora_inicio_carga), min(int(horas_hasta_viaje), profile_length)
            ):
                power_profiles[idx][h] = charging_power_watts

        return power_profiles, num_trips

    def _build_schedule_matrix(
        self,
        power_profiles: List[List[float]],
        num_trips: int,
        planning_horizon_days: int,
    ) -> List[Dict[str, Any]]:
        """Build the final weekly schedule from power profiles."""
        schedule = []
        now_dt = dt_util.now()

        for day in range(planning_horizon_days):
            for hour in range(24):
                timestamp = now_dt + timedelta(days=day, hours=hour)
                profile_idx = day * 24 + hour

                entry: Dict[str, Any] = {"date": timestamp.isoformat()}

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

    async def async_generate_deferrables_schedule(
        self,
        charging_power_kw: float = 3.6,
        planning_horizon_days: int = 7,
    ) -> List[Dict[str, Any]]:
        """Genera el calendario de cargas diferibles para EMHASS."""
        trips = await self._load_active_trips()
        battery_capacity, safety_margin = self._read_battery_config()
        power_profiles, num_trips = await self._build_power_profiles(
            trips,
            battery_capacity,
            safety_margin,
            charging_power_kw,
            planning_horizon_days,
        )
        schedule = self._build_schedule_matrix(
            power_profiles, num_trips, planning_horizon_days
        )
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
