"""EMHASS Load Publisher — handles publishing load data to EMHASS."""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from ..calculations import (
    BatteryCapacity,
    calculate_energy_needed,
    calculate_multi_trip_charging_windows,
)
from ..const import DEFAULT_SAFETY_MARGIN
from .index_manager import IndexManager

_LOGGER = logging.getLogger(__name__)


class LoadPublisher:
    """Handles publishing load data to EMHASS.

    Extracted from EMHASSAdapter to follow Single Responsibility Principle.
    Manages the lifecycle of deferrable loads: publish, update, and remove.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        vehicle_id: str,
        charging_power_kw: float = 3.6,
        battery_capacity_kwh: float = 50.0,
        safety_margin_percent: float = DEFAULT_SAFETY_MARGIN,
        max_deferrable_loads: int = 50,
        index_manager: IndexManager | None = None,
    ):
        """Initialize load publisher.

        Args:
            hass: HomeAssistant instance.
            vehicle_id: Vehicle identifier.
            charging_power_kw: Charging power in kilowatts.
            battery_capacity_kwh: Battery capacity in kWh.
            safety_margin_percent: Safety margin percentage.
            max_deferrable_loads: Maximum number of deferrable loads.
            index_manager: Optional shared IndexManager. If not provided,
                creates an internal IndexManager.
        """
        self.hass = hass
        self.vehicle_id = vehicle_id
        self.charging_power_kw = charging_power_kw
        self.battery_capacity_kwh = battery_capacity_kwh
        self.safety_margin_percent = safety_margin_percent
        self._battery_cap = BatteryCapacity(
            nominal_capacity_kwh=battery_capacity_kwh,
            soh_sensor_entity_id=None,
        )
        self._index_manager = index_manager or IndexManager(
            max_deferrable_loads=max_deferrable_loads,
            cooldown_hours=0,
        )

    async def publish(self, trip: Dict[str, Any]) -> bool:
        """Publish a trip as a deferrable load.

        Args:
            trip: Trip dictionary with kwh, deadline, etc.

        Returns:
            True if successful, False otherwise.
        """
        trip_id = trip.get("id")
        if not trip_id:
            _LOGGER.error("Trip missing ID")
            return False

        # Assign index to trip
        emhass_index = self._index_manager.assign_index(trip_id)
        if emhass_index is None:
            return False

        # Calculate deadline
        deadline_dt = self._calculate_deadline(trip)
        if deadline_dt is None:
            _LOGGER.error("Trip %s has no valid deadline", trip_id)
            self._index_manager.release_index(trip_id)
            return False

        # Calculate hours available
        now = datetime.now(timezone.utc)
        hours_available = (deadline_dt - now).total_seconds() / 3600

        if hours_available <= 0:
            _LOGGER.warning(
                "Trip deadline in past: %s (hours_available=%.2f)",
                trip_id,
                hours_available,
            )
            self._index_manager.release_index(trip_id)
            return False

        # Calculate charging window
        soc_current = await self._get_current_soc()
        if soc_current is None:
            soc_current = 50.0

        charging_windows = self._calculate_charging_windows(
            deadline_dt, trip, soc_current
        )

        if charging_windows and charging_windows[0].get("inicio_ventana"):
            inicio = charging_windows[0]["inicio_ventana"]
            delta_hours = (self._ensure_aware(inicio) - now).total_seconds() / 3600
            _ = max(0, min(int(delta_hours), 168))

        if (
            charging_windows
            and len(charging_windows) > 0
            and charging_windows[0].get("fin_ventana")
        ):
            fin = charging_windows[0]["fin_ventana"]
            if isinstance(fin, datetime):
                delta_hours_end = (self._ensure_aware(fin) - now).total_seconds() / 3600
                _ = max(0, min(math.ceil(delta_hours_end - 0.001), 168))

        # Calculate energy parameters
        energia_info = calculate_energy_needed(
            trip,
            self._battery_cap.get_capacity(self.hass),
            soc_current,
            self.charging_power_kw,
            safety_margin_percent=self.safety_margin_percent,
        )

        total_hours = energia_info["horas_carga_necesarias"]
        _ = energia_info["energia_necesaria_kwh"]

        if total_hours > 0:
            power_watts = self.charging_power_kw * 1000
        else:
            power_watts = 0.0

        _LOGGER.info(
            "Published deferrable load for trip %s (index %d): %s hours, %s W",
            trip_id,
            emhass_index,
            round(total_hours, 2),
            round(power_watts, 0),
        )

        return True

    async def update(self, trip: Dict[str, Any]) -> bool:
        """Update an existing deferrable load with new parameters.

        Args:
            trip: Updated trip dictionary.

        Returns:
            True if successful, False otherwise.
        """
        return await self.publish(trip)

    async def remove(self, trip_id: str) -> bool:
        """Remove a deferrable load.

        Args:
            trip_id: The trip identifier to remove.

        Returns:
            True if successful, False otherwise.
        """
        success = self._index_manager.release_index(trip_id)

        if success:
            _LOGGER.info("Removed deferrable load for trip %s", trip_id)
        else:
            _LOGGER.warning("Failed to remove deferrable load for trip %s", trip_id)

        return success

    def _calculate_deadline(self, trip: Dict[str, Any]) -> Optional[datetime]:
        """Calculate deadline datetime from trip data.

        Args:
            trip: Trip dictionary with either "datetime" (punctual) or
                  "dia_semana"/"hora" (recurring).

        Returns:
            Calculated deadline, or None if trip is invalid.
        """
        deadline = trip.get("datetime")
        if deadline:
            if isinstance(deadline, str):
                dt = datetime.fromisoformat(deadline)
                return self._ensure_aware(dt)
            return self._ensure_aware(deadline)

        trip_type = trip.get("tipo", "")
        is_recurring = trip_type in ("recurrente", "recurring")

        if is_recurring:
            day = trip.get("day") or trip.get("dia_semana")
            time_str = trip.get("time") or trip.get("hora")

            if day is not None and time_str is not None:
                now = datetime.now(timezone.utc)
                days_map = {
                    "domingo": 6,
                    "sunday": 6,
                    "lunes": 0,
                    "monday": 0,
                    "martes": 1,
                    "tuesday": 1,
                    "miércoles": 2,
                    "miercoles": 2,
                    "wednesday": 2,
                    "jueves": 3,
                    "thursday": 3,
                    "viernes": 4,
                    "friday": 4,
                    "sabado": 5,
                    "saturday": 5,
                }
                day_str = str(day).lower()
                # Support numeric day: '1'→Monday(0), '2'→Tuesday(1), ..., '7'→Sunday(6)
                if day_str.isdigit():
                    n = int(day_str)
                    target_day = n - 1 if 1 <= n <= 7 else None
                else:
                    target_day = days_map.get(day_str)
                if target_day is not None:
                    now_day = now.weekday()
                    delta_days = (target_day - now_day) % 7
                    if delta_days == 0:
                        delta_days = 7

                    parts = time_str.split(":")
                    hour = int(parts[0]) if len(parts) > 0 else 0
                    minute = int(parts[1]) if len(parts) > 1 else 0

                    deadline = now.replace(
                        hour=hour, minute=minute, second=0, microsecond=0
                    )
                    from datetime import timedelta

                    deadline += timedelta(days=delta_days)
                    return self._ensure_aware(deadline)

        return None

    async def _get_current_soc(self) -> Optional[float]:
        """Get current battery SOC.

        Returns:
            SOC percentage or None if unavailable.
        """
        return None

    def _calculate_charging_windows(
        self,
        deadline_dt: datetime,
        trip: Dict[str, Any],
        soc_current: float,
    ) -> List[Dict[str, Any]]:
        """Calculate charging windows for a trip.

        Args:
            deadline_dt: Deadline datetime.
            trip: Trip dictionary.
            soc_current: Current SOC percentage.

        Returns:
            List of charging window dictionaries.
        """
        return calculate_multi_trip_charging_windows(
            trips=[(deadline_dt, trip)],
            soc_actual=soc_current,
            hora_regreso=None,
            charging_power_kw=self.charging_power_kw,
            battery_capacity_kwh=self._battery_cap.get_capacity(self.hass),
            duration_hours=6.0,
            safety_margin_percent=self.safety_margin_percent,
            now=dt_util.now(),
        )

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        """Convert naive datetime to aware (UTC) if needed."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
