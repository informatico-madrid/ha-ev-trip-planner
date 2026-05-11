"""Schedule mixin for TripManager — extracted from trip_manager.py.

Contains:
- async_generate_deferrables_schedule: generates charging schedule for EMHASS
- publish_deferrable_loads: publishes all active trips as deferrable loads to EMHASS

The mixin reads shared state from `self` (inherited via MRO):
- `self._trips`, `self._recurring_trips`, `self._punctual_trips`
- `self.hass`, `self.vehicle_id`, `self._emhass_adapter`
- `self.async_get_vehicle_soc`, `self.async_calcular_energia_necesaria`
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from ..const import DOMAIN

_UNSET = object()

_LOGGER = logging.getLogger(__name__)


class _ScheduleMixin:
    """Mixin providing schedule generation for TripManager.

    This mixin encapsulates deferrable schedule generation and EMHASS publishing.
    The host class (TripManager) provides shared state access via MRO:
    self.hass, self._trips, self._recurring_trips, self._punctual_trips,
    self.vehicle_id, self._emhass_adapter,
    self.async_get_vehicle_soc, self.async_calcular_energia_necesaria.
    """

    def __init__(self) -> None:
        """Initialize the schedule mixin (no state to initialize)."""

    async def async_generate_deferrables_schedule(
        self,
        charging_power_kw: float = 3.6,
        planning_horizon_days: int = 7,
    ) -> List[Dict[str, Any]]:
        """Genera el calendario de cargas diferibles para EMHASS.

        Maneja múltiples viajes con:
        - Index assignment: 0, 1, 2, ... por viaje (ordenados por prioridad)
        - Conflict detection: Múltiples viajes en la misma hora
        - Priority logic: Viajes más urgentes primero (deadline más cercano)

        Args:
            charging_power_kw: Potencia de carga en kW
            planning_horizon_days: Días de horizonte de planificación

        Returns:
            Lista de diccionarios con fecha y potencia por hora
            Formato: [{"date": "2026-03-17T14:00:00+01:00", "p_deferrable0": "0.0", "p_deferrable1": "0.0"}, ...]
        """
        # Cargar viajes
        await self._load_trips()

        # Obtener configuración
        try:
            _config_entry: Optional[ConfigEntry[Any]] = None
            entry_id = getattr(self, "_entry_id", None)
            if entry_id:
                _config_entry = self.hass.config_entries.async_get_entry(entry_id)
            else:
                _config_entry = self.hass.config_entries.async_get_entry(
                    self.vehicle_id
                )

            if _config_entry is not None and _config_entry.data is not None:
                _config_entry.data.get("battery_capacity_kwh", 50.0)
        except Exception:
            pass

        # Obtener SOC actual
        await self.async_get_vehicle_soc(self.vehicle_id)

        # Obtener todos los viajes pendientes
        all_trips = []
        for trip in self._recurring_trips.values():
            if trip.get("activo", True):
                all_trips.append(trip)
        for trip in self._punctual_trips.values():
            if trip.get("estado") == "pendiente":
                all_trips.append(trip)

        # Ordenar trips por deadline (urgentes primero)
        # Conflict detection: múltiples viajes en la misma hora
        # Priority logic: deadline más cercano = más urgente = índice menor
        now = datetime.now(timezone.utc)
        for trip in all_trips:
            trip_time = self._get_trip_time(trip)
            if trip_time:
                trip["_deadline"] = trip_time
                # Calcular horas hasta deadline
                delta = trip_time - now
                trip["_hours_until_deadline"] = max(0, delta.total_seconds() / 3600)
            else:
                trip["_deadline"] = datetime.max
                trip["_hours_until_deadline"] = float("inf")

        # Ordenar: primero los más urgentes (menor hours_until_deadline)
        all_trips.sort(key=lambda t: t.get("_hours_until_deadline", float("inf")))

        # Asignar índice a cada viaje (0, 1, 2, ...)
        # Índice 0 = mayor prioridad = deadline más cercano
        trip_indices = {}
        for idx, trip in enumerate(all_trips):
            trip_id = trip.get("id", f"trip_{idx}")
            trip_indices[trip_id] = idx

        # Generar power profiles para cada índice de viaje
        # Cada índice de viaje tiene su propio perfil de potencia
        num_trips = len(all_trips)
        profile_length = planning_horizon_days * 24

        # Inicializar perfiles para cada viaje
        power_profiles: List[List[float]] = [
            [0.0] * profile_length for _ in range(num_trips)
        ]

        # Obtener configuración del vehículo
        battery_capacity = 50.0
        safety_margin_percent = 10.0
        soc_current = 50.0
        try:
            config_entry: Optional[ConfigEntry[Any]] = None
            entry_id = getattr(self, "_entry_id", None)
            if entry_id:
                config_entry = self.hass.config_entries.async_get_entry(entry_id)
            else:
                config_entry = self.hass.config_entries.async_get_entry(self.vehicle_id)

            if config_entry is not None and config_entry.data is not None:
                battery_capacity = config_entry.data.get("battery_capacity_kwh", 50.0)
                safety_margin_percent = config_entry.data.get(
                    "safety_margin_percent", 10.0
                )
        except Exception:
            pass
        soc_current = await self.async_get_vehicle_soc(self.vehicle_id)

        # Generar perfil de potencia para cada viaje
        for idx, trip in enumerate(all_trips):
            vehicle_config = {
                "battery_capacity_kwh": battery_capacity,
                "charging_power_kw": charging_power_kw,
                "soc_current": soc_current,
                "safety_margin_percent": safety_margin_percent,
            }
            energia_info = await self.async_calcular_energia_necesaria(
                trip, vehicle_config
            )
            energia_kwh = energia_info["energia_necesaria_kwh"]
            horas_carga = energia_info["horas_carga_necesarias"]

            if energia_kwh <= 0:
                continue

            # Convertir a watts
            charging_power_watts = charging_power_kw * 1000

            # Determinar las horas de carga necesarias
            horas_necesarias = int(horas_carga) + (1 if horas_carga % 1 > 0 else 0)

            # Obtener deadline del viaje
            trip_time = self._get_trip_time(trip)
            if not trip_time:
                continue

            # Calcular posición en el perfil (desde ahora)
            delta = trip_time - now
            horas_hasta_viaje = int(delta.total_seconds() / 3600)

            if horas_hasta_viaje < 0:
                continue

            # Determinar horas de carga: las últimas horas antes del deadline
            hora_inicio_carga = max(0, horas_hasta_viaje - horas_necesarias)

            # Distribuir la carga en las horas disponibles
            # hora_inicio_carga ya es >= 0 por max(0, ...), y range usa min(..., profile_length)
            for h in range(
                int(hora_inicio_carga), min(int(horas_hasta_viaje), profile_length)
            ):
                power_profiles[idx][h] = charging_power_watts

        # Generar calendario con múltiples índices de carga diferible
        schedule = []
        now_dt = dt_util.now()  # Timezone-aware datetime from Home Assistant

        for day in range(planning_horizon_days):
            for hour in range(24):
                # Calcular timestamp con timezone
                timestamp = now_dt + timedelta(days=day, hours=hour)
                profile_idx = day * 24 + hour

                # Crear entrada con todos los índices de carga diferible
                entry = {"date": timestamp.isoformat()}

                # Añadir potencia para cada índice de viaje
                for trip_idx in range(num_trips):
                    power = (
                        power_profiles[trip_idx][profile_idx]
                        if profile_idx < len(power_profiles[trip_idx])
                        else 0.0
                    )
                    entry[f"p_deferrable{trip_idx}"] = f"{power:.1f}"

                # Si no hay viajes, asegurar que hay al menos p_deferrable0
                if num_trips == 0:
                    entry["p_deferrable0"] = "0.0"

                schedule.append(entry)

        return schedule

    async def publish_deferrable_loads(
        self, trips: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Publishes all active trips as deferrable loads to EMHASS.

        Args:
            trips: Optional list of trips to publish. If None, gets all
                   active trips from storage.
        """
        from ..emhass import EMHASSAdapter

        # Get all active trips if not provided
        if trips is None:
            await self._load_trips()
            trips = []
            for trip in self._recurring_trips.values():
                if trip.get("activo", True):
                    trips.append(trip)
            for trip in self._punctual_trips.values():
                if trip.get("estado") == "pendiente":
                    trips.append(trip)

        # Publish through EMHASS adapter
        adapter = getattr(self, "_emhass_adapter", None)
        if adapter and isinstance(adapter, EMHASSAdapter):
            try:
                await adapter.async_publish_all_deferrable_loads(trips)
            except Exception:  # pragma: no cover
                _LOGGER.exception("Error publishing deferrable loads to EMHASS")
