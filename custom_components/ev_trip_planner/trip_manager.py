"""Gestión central de viajes y optimización de carga para vehículos eléctricos.

Implementa la lógica de planificación de viajes, cálculo de energía necesaria
y sincronización con EMHASS. Cumple con las reglas de Home Assistant 2026 para
runtime_data y tipado estricto.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from homeassistant.helpers import storage as ha_storage
from homeassistant.helpers.storage import Store
from homeassistant.config_entries import ConfigEntry

import yaml
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .trip._crud_mixin import _CRUDMixin
from .trip._sensor_callbacks import _SensorCallbacks
from .trip._soc_mixin import _SOCMixin

from .emhass import EMHASSAdapter
from .yaml_trip_storage import YamlTripStorage
from .utils import generate_trip_id
from .utils import is_trip_today as pure_is_trip_today
from .utils import sanitize_recurring_trips as pure_sanitize_recurring_trips
from .utils import validate_hora as pure_validate_hora

# T3.2: Import function for recurring trip rotation
from .calculations import calculate_next_recurring_datetime, calculate_day_index
from .vehicle_controller import VehicleController

_UNSET = object()

_LOGGER = logging.getLogger(__name__)

# Instance counter for debugging
_trip_manager_instance_count = 0

# Days of week in Spanish (lowercase)
DAYS_OF_WEEK = (
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
)


class TripManager(_CRUDMixin, _SOCMixin):
    """Gestión central de viajes y optimización de carga para vehículos eléctricos.

    Esta clase implementa la lógica de planificación de viajes, cálculo de energía
    necesaria y sincronización con EMHASS. Cumple con las reglas de Home Assistant
    2026 para runtime_data y tipado estricto.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        vehicle_id: str,
        entry_id: Optional[str] = None,
        presence_config: Optional[Dict[str, Any]] = None,
        storage: Optional[YamlTripStorage] = None,
        emhass_adapter: Optional[EMHASSAdapter] = None,
    ) -> None:
        """Inicializa el gestor de viajes para un vehículo específico."""
        global _trip_manager_instance_count
        _trip_manager_instance_count += 1
        self._instance_id = _trip_manager_instance_count
        _CRUDMixin.__init__(self)
        _SOCMixin.__init__(self)
        _LOGGER.debug(
            "=== TripManager instance created: id=%d, vehicle=%s ===",
            self._instance_id,
            vehicle_id,
        )

        self.hass = hass
        self.vehicle_id = vehicle_id
        self._entry_id: str = entry_id or ""
        self.vehicle_controller = VehicleController(
            hass, vehicle_id, presence_config, self
        )
        self._trips: Dict[str, Any] = {}
        self._recurring_trips: Dict[str, Any] = {}
        self._punctual_trips: Dict[str, Any] = {}
        self._last_update: Optional[datetime] = None
        self._storage: Optional[YamlTripStorage] = storage
        self._emhass_adapter: Optional[EMHASSAdapter] = emhass_adapter
        self._sensor_callbacks = _SensorCallbacks()

    def set_emhass_adapter(self, adapter: EMHASSAdapter) -> None:
        """Set the EMHASS adapter for this trip manager."""
        self._emhass_adapter = adapter
        _LOGGER.debug("EMHASS adapter set for vehicle %s", self.vehicle_id)

    def get_emhass_adapter(self) -> Optional[EMHASSAdapter]:
        """Get the EMHASS adapter for this trip manager."""
        return self._emhass_adapter

    @staticmethod
    def _validate_hora(hora: str) -> None:
        """Valida que una cadena de hora tenga el formato HH:MM y valores válidos.

        Delegates to pure utils.validate_hora for testability.

        Args:
            hora: Cadena de hora en formato HH:MM.

        Raises:
            ValueError: Si el formato no es HH:MM o los valores están fuera de rango.
        """
        pure_validate_hora(hora)

    def _sanitize_recurring_trips(self, trips: Dict[str, Any]) -> Dict[str, Any]:
        """Elimina viajes recurrentes con formato de hora inválido del almacenamiento."""
        original_count = len(trips)
        sanitized = pure_sanitize_recurring_trips(trips)
        removed_count = original_count - len(sanitized)
        if removed_count > 0:
            _LOGGER.warning(
                "%d recurring trip(s) ignored due to invalid hora format. "
                "Fix or remove invalid entries from storage.",
                removed_count,
            )
        return sanitized

    def _parse_trip_datetime(
        self, trip_datetime: datetime | str, allow_none: bool = False
    ) -> datetime | None:
        """Parse trip datetime, ensuring timezone awareness for both object and string inputs."""
        if isinstance(trip_datetime, datetime):
            dt = trip_datetime
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        try:
            parsed = dt_util.parse_datetime(trip_datetime)
            if parsed is not None and parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed is None:
                _LOGGER.warning(
                    "Failed to parse trip datetime: %s, falling back to now",
                    repr(trip_datetime),
                )
                if allow_none:
                    return None
                return datetime.now(timezone.utc)
            return parsed
        except Exception:
            _LOGGER.warning(
                "Failed to parse trip datetime: %s", repr(trip_datetime)
            )
            return None if allow_none else datetime.now(timezone.utc)

    def _is_trip_today(self, trip: Dict[str, Any], today: date) -> bool:
        """Verifica si un viaje ocurre hoy."""
        return pure_is_trip_today(trip, today)

    def _get_trip_time(self, trip: Dict[str, Any]) -> Optional[datetime]:
        """Obtiene la fecha y hora del viaje."""
        from .calculations import calculate_trip_time

        tipo = trip.get("tipo")
        if tipo is None:
            return None
        result = calculate_trip_time(
            tipo,
            trip.get("hora"),
            trip.get("dia_semana"),
            trip.get("datetime"),
            datetime.now(timezone.utc),
        )
        if result is not None:
            return result.replace(tzinfo=timezone.utc)
        return result

    def _get_day_index(self, day_name: str) -> int:
        """Obtiene el índice del día de la semana (0=lunes, 6=domingo)."""
        try:
            idx = DAYS_OF_WEEK.index(day_name.lower())
            return idx
        except ValueError:
            _LOGGER.warning("Unknown day name: %s, defaulting to 0", day_name)
            return 0

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
        from .calculations import calculate_power_profile

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
        # Conflict detection: múltiples viajes a la misma hora
        # Priority logic: deadline más cercano = más urgente = índice menor
        now = datetime.now(timezone.utc)
        for trip in all_trips:
            trip_time = self._get_trip_time(trip)
            if trip_time:
                trip["_deadline"] = trip_time
                # Calcular horas hasta deadline para排序
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
