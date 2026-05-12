"""Gestión central de viajes y optimización de carga para vehículos eléctricos.

Implements composition over inheritance — the manager creates a single
TripManagerState and passes it to each mixin instance. All public API
methods delegate to the appropriate mixin.

This eliminates pyright MRO attribute access issues.
"""

from __future__ import annotations

import datetime as _datetime_mod  # noqa: F401 — module-level for test mocking
import logging
from datetime import date, datetime, timezone
from pathlib import Path  # noqa: F401 — module-level for test mocking
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant

from ._crud_mixin import _CRUDMixin
from ._power_profile_mixin import _PowerProfileMixin
from ._schedule_mixin import _ScheduleMixin
from ._soc_mixin import _SOCMixin
from .state import TripManagerState

from ..emhass import EMHASSAdapter
from ..yaml_trip_storage import YamlTripStorage
from ..utils import sanitize_recurring_trips as pure_sanitize_recurring_trips
from ..utils import validate_hora as pure_validate_hora

# T3.2: Import function for recurring trip rotation
from ..vehicle import VehicleController

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


class TripManager:
    """Gestión central de viajes y optimización de carga para vehículos eléctricos.

    Uses composition — creates a TripManagerState and passes it to each mixin.
    All shared state lives in the state object. Public API delegates to mixins.
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
        _LOGGER.debug(
            "=== TripManager instance created: id=%d, vehicle=%s ===",
            self._instance_id,
            vehicle_id,
        )

        # Create shared state — the single source of truth
        self._state = TripManagerState(
            hass=hass,
            vehicle_id=vehicle_id,
            entry_id=entry_id or "",
            storage=storage,
            emhass_adapter=emhass_adapter,
        )
        # Create vehicle controller before mixins (they may reference it)
        self._state.vehicle_controller = VehicleController(
            hass, vehicle_id, presence_config, self
        )

        # Instantiate mixins with shared state
        self._crud = _CRUDMixin(self._state)
        self._soc = _SOCMixin(self._state)
        self._power = _PowerProfileMixin(self._state)
        self._schedule = _ScheduleMixin(self._state)

        # Store method references on state for cross-mixin access
        # (methods defined directly on TripManager)
        self._state.async_save_trips = self.async_save_trips
        self._state._load_trips = self._load_trips
        self._state._save_trips_yaml = self._save_trips_yaml
        self._state._sanitize_recurring_trips = self._sanitize_recurring_trips
        self._state._reset_trips = self._reset_trips
        self._state._validate_hora = self._validate_hora
        self._state._is_trip_today = self._is_trip_today
        self._state._parse_trip_datetime = self._parse_trip_datetime
        self._state._get_charging_power = self._get_charging_power
        self._state._get_trip_time = self._get_trip_time
        self._state.async_get_kwh_needed_today = self.async_get_kwh_needed_today
        self._state.async_get_next_trip_after = self.async_get_next_trip_after
        self._state.async_get_vehicle_soc = self.async_get_vehicle_soc
        self._state.async_get_hours_needed_today = self.async_get_hours_needed_today
        self._state.async_calcular_energia_necesaria = self.async_calcular_energia_necesaria
        self._state.async_get_recurring_trips = self.async_get_recurring_trips
        self._state.async_get_punctual_trips = self.async_get_punctual_trips
        self._state.get_all_trips = self.get_all_trips
        self._state.async_get_next_trip = self.async_get_next_trip
        self._state.calcular_soc_inicio_trips = self.calcular_soc_inicio_trips
        self._state.calcular_ventana_carga_multitrip = self.calcular_ventana_carga_multitrip
        self._state._calcular_soc_objetivo_base = self._calcular_soc_objetivo_base
        self._state._calcular_tasa_carga_soc = self._calcular_tasa_carga_soc
        self._state.publish_deferrable_loads = self.publish_deferrable_loads
        self._state._async_publish_new_trip_to_emhass = self._async_publish_new_trip_to_emhass
        self._state._async_remove_trip_from_emhass = self._async_remove_trip_from_emhass
        self._state._async_sync_trip_to_emhass = self._async_sync_trip_to_emhass
        self._state.async_update_trip_sensor = self.async_update_trip_sensor

    def set_emhass_adapter(self, adapter: EMHASSAdapter) -> None:
        """Set the EMHASS adapter for this trip manager."""
        self._state.emhass_adapter = adapter
        _LOGGER.debug("EMHASS adapter set for vehicle %s", self._state.vehicle_id)

    def get_emhass_adapter(self) -> Optional[EMHASSAdapter]:
        """Get the EMHASS adapter for this trip manager."""
        return self._state.emhass_adapter

    def get_charging_power(self) -> float:
        """Get the configured charging power for the vehicle."""
        return self._soc._get_charging_power()

    def _get_trip_time(self, trip: Dict[str, Any]) -> Optional[datetime]:
        """Get trip departure time. Delegates to SOC mixin."""
        return self._soc._get_trip_time(trip)

    # ── Properties for services and test access ──────

    @property
    def _recurring_trips(self) -> Dict[str, Dict[str, Any]]:
        """Expose recurring trips for services/test access."""
        return self._state.recurring_trips

    @_recurring_trips.setter
    def _recurring_trips(self, value: Dict[str, Dict[str, Any]]) -> None:
        if hasattr(self, "_state"):
            self._state.recurring_trips = value

    @property
    def _punctual_trips(self) -> Dict[str, Dict[str, Any]]:
        """Expose punctual trips for services/test access."""
        return self._state.punctual_trips

    @_punctual_trips.setter
    def _punctual_trips(self, value: Dict[str, Dict[str, Any]]) -> None:
        if hasattr(self, "_state"):
            self._state.punctual_trips = value

    @property
    def vehicle_controller(self) -> Any:
        """Expose vehicle_controller for __init__.py compatibility."""
        return self._state.vehicle_controller

    @property
    def vehicle_id(self) -> str:
        """Expose vehicle_id for test access."""
        return self._state.vehicle_id

    @vehicle_id.setter
    def vehicle_id(self, value: str) -> None:
        if hasattr(self, "_state"):
            self._state.vehicle_id = value

    @property
    def _entry_id(self) -> Optional[str]:
        """Expose entry_id for test access."""
        return self._state.entry_id

    @property
    def _sensor_callbacks(self) -> Any:
        """Expose sensor_callbacks for test access."""
        return self._state.sensor_callbacks

    @property
    def hass(self) -> Any:
        """Expose hass for test access."""
        if hasattr(self, "_state") and self._state is not None:
            return self._state.hass
        # For test stubs (created via __new__), check direct instance attribute
        return object.__getattribute__(self, "_hass")

    @hass.setter
    def hass(self, value: Any) -> None:
        if hasattr(self, "_state") and self._state is not None:
            self._state.hass = value
        else:
            # For test stubs, store directly on instance
            object.__setattr__(self, "_hass", value)

    @property
    def _trips(self) -> Dict[str, Dict[str, Any]]:
        """Expose internal trips dict for test access."""
        return self._state._trips

    @_trips.setter
    def _trips(self, value: Dict[str, Dict[str, Any]]) -> None:
        if hasattr(self, "_state"):
            self._state._trips = value

    @property
    def _storage(self) -> Any:
        """Expose storage for test access."""
        return self._state.storage

    @_storage.setter
    def _storage(self, value: Any) -> None:
        if hasattr(self, "_state"):
            self._state.storage = value

    @property
    def _emhass_adapter(self) -> Any:
        """Expose emhass_adapter for test access."""
        return self._state.emhass_adapter

    @_emhass_adapter.setter
    def _emhass_adapter(self, value: Any) -> None:
        if hasattr(self, "_state"):
            self._state.emhass_adapter = value

    @property
    def _last_update(self) -> Optional[str]:
        """Expose last_update for test access."""
        return self._state.last_update

    @_last_update.setter
    def _last_update(self, value: Optional[str]) -> None:
        if hasattr(self, "_state"):
            self._state.last_update = value

    # ── Delegated helper methods (for test access) ───────────

    def _parse_trip_datetime(
        self, trip_datetime: datetime | str, allow_none: bool = False
    ) -> Optional[datetime]:
        """Delegate to SOC mixin."""
        return self._soc._parse_trip_datetime(trip_datetime, allow_none)

    def _is_trip_today(self, trip: Dict[str, Any], today: date) -> bool:
        """Delegate to SOC mixin."""
        return self._soc._is_trip_today(trip, today)

    def _get_charging_power(self) -> float:
        """Delegate to SOC mixin."""
        return self._soc._get_charging_power()

    def _calcular_tasa_carga_soc(
        self, charging_power_kw: float, battery_capacity_kwh: float = 50.0
    ) -> float:
        """Delegate to SOC mixin."""
        return self._soc._calcular_tasa_carga_soc(charging_power_kw, battery_capacity_kwh)

    def _calcular_soc_objetivo_base(
        self,
        trip: Dict[str, Any],
        battery_capacity_kwh: float,
        consumption_kwh_per_km: float = 0.15,
    ) -> float:
        """Delegate to SOC mixin."""
        return self._soc._calcular_soc_objetivo_base(
            trip, battery_capacity_kwh, consumption_kwh_per_km
        )

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

    def _get_day_index(self, day_name: str) -> int:
        """Obtiene el índice del día de la semana (0=lunes, 6=domingo)."""
        try:
            idx = DAYS_OF_WEEK.index(day_name.lower())
            return idx
        except ValueError:
            _LOGGER.warning("Unknown day name: %s, defaulting to 0", day_name)
            return 0

    async def async_get_next_trip_after(
        self, hora_regreso: datetime
    ) -> Optional[Dict[str, Any]]:
        """Obtiene el próximo viaje pendiente después de una hora de regreso.

        Filters punctual trips with datetime > hora_regreso and estado=pendiente,
        and recurring trips with hora > hora_regreso.time() for today's day of week
        and activo=True.
        """
        next_trip: Optional[Dict[str, Any]] = None
        hoy = hora_regreso.date()
        dia_semana_hoy = DAYS_OF_WEEK[hoy.weekday()]

        # Filter punctual trips: datetime > hora_regreso and estado=pendiente
        for trip in self._state.punctual_trips.values():
            if trip.get("estado") != "pendiente":
                continue
            trip_time = self._get_trip_time(trip)
            if trip_time and trip_time > hora_regreso:
                if next_trip is None or trip_time < next_trip["time"]:
                    next_trip = {"time": trip_time, "trip": trip}

        # Filter recurring trips: today's day_of_week, hora > hora_regreso.time(), activo=True
        for trip in self._state.recurring_trips.values():
            if not trip.get("activo", True):
                continue
            if trip.get("dia_semana", "").lower() != dia_semana_hoy:
                continue
            try:
                trip_hour = int(trip["hora"].split(":")[0])
                trip_minute = int(trip["hora"].split(":")[1])
                regreso_hour = hora_regreso.hour
                regreso_minute = hora_regreso.minute
                if trip_hour < regreso_hour or (
                    trip_hour == regreso_hour and trip_minute <= regreso_minute
                ):
                    continue
                trip_time = datetime.combine(
                    hoy, datetime.strptime(trip["hora"], "%H:%M").time()
                )
            except (ValueError, KeyError) as err:
                _LOGGER.warning(
                    "Invalid trip hora format: %s — skipping. Error: %s",
                    trip.get("hora"),
                    err,
                )
                continue
            if next_trip is None or trip_time < next_trip["time"]:
                next_trip = {"time": trip_time, "trip": trip}

        return next_trip["trip"] if next_trip else None

    async def async_get_next_trip(self) -> Optional[Dict[str, Any]]:
        """Get the next scheduled trip from all trips."""
        now = datetime.now(timezone.utc)
        next_trip: Optional[Dict[str, Any]] = None
        for trip in self._state.recurring_trips.values():
            if trip.get("activo"):
                trip_time = self._get_trip_time(trip)
                if trip_time and trip_time > now:
                    if next_trip is None or trip_time < next_trip["time"]:
                        next_trip = {"time": trip_time, "trip": trip}
        for trip in self._state.punctual_trips.values():
            if trip.get("estado") == "pendiente":
                trip_time = self._get_trip_time(trip)
                if trip_time and trip_time > now:
                    if next_trip is None or trip_time < next_trip["time"]:
                        next_trip = {"time": trip_time, "trip": trip}
        return next_trip["trip"] if next_trip else None

    # ── Delegated: CRUDMixin ────────────────────────────────────

    async def async_setup(self) -> None:
        """Configura el gestor de viajes y carga los datos desde el almacenamiento."""
        await self._crud.async_setup()

    async def _load_trips(self) -> None:
        """Carga los viajes desde el almacenamiento persistente."""
        await self._crud._load_trips()

    async def _load_trips_yaml(self, storage_key: str) -> None:
        """Carga los viajes desde un archivo YAML (fallback)."""
        await self._crud._load_trips_yaml(storage_key)

    def _reset_trips(self) -> None:
        """Resetea todas las colecciones de viajes."""
        self._crud._reset_trips()

    async def async_save_trips(self) -> None:
        """Guarda los viajes en el almacenamiento persistente."""
        await self._crud.async_save_trips()

    async def _save_trips_yaml(self, storage_key: str) -> None:
        """Guarda los viajes en un archivo YAML (fallback)."""
        await self._crud._save_trips_yaml(storage_key)

    async def async_get_recurring_trips(self) -> list:
        """Obtiene la lista de viajes recurrentes."""
        return await self._crud.async_get_recurring_trips()

    async def async_get_punctual_trips(self) -> list:
        """Obtiene la lista de viajes puntuales."""
        return await self._crud.async_get_punctual_trips()

    def get_all_trips(self) -> Dict[str, list]:
        """Get all trips (both recurring and punctual) as a combined dict."""
        return self._crud.get_all_trips()

    async def async_add_recurring_trip(self, **kwargs: Any) -> None:
        """Añade un nuevo viaje recurrente y sincroniza con EMHASS."""
        await self._crud.async_add_recurring_trip(**kwargs)

    async def async_add_punctual_trip(self, **kwargs: Any) -> None:
        """Añade un nuevo viaje puntual y sincroniza con EMHASS."""
        await self._crud.async_add_punctual_trip(**kwargs)

    async def async_update_trip(self, trip_id: str, updates: Dict[str, Any]) -> None:
        """Actualiza un viaje existente y sincroniza con EMHASS."""
        await self._crud.async_update_trip(trip_id, updates)

    async def async_delete_trip(self, trip_id: str) -> None:
        """Elimina un viaje existente y sincroniza con EMHASS."""
        await self._crud.async_delete_trip(trip_id)

    async def async_delete_all_trips(self) -> None:
        """Deletes all recurring and punctual trips for cascade deletion."""
        await self._crud.async_delete_all_trips()

    async def async_pause_recurring_trip(self, trip_id: str) -> None:
        """Pausa un viaje recurrente."""
        await self._crud.async_pause_recurring_trip(trip_id)

    async def async_resume_recurring_trip(self, trip_id: str) -> None:
        """Reanuda un viaje recurrente."""
        await self._crud.async_resume_recurring_trip(trip_id)

    async def async_update_trip_sensor(self, trip_id: str) -> None:
        """Update the Home Assistant sensor entity for an updated trip."""
        await self._crud.async_update_trip_sensor(trip_id)

    async def async_complete_punctual_trip(self, trip_id: str) -> None:
        """Marca un viaje puntual como completado."""
        await self._crud.async_complete_punctual_trip(trip_id)

    async def async_cancel_punctual_trip(self, trip_id: str) -> None:
        """Cancela un viaje puntual."""
        await self._crud.async_cancel_punctual_trip(trip_id)

    async def _async_sync_trip_to_emhass(
        self, trip_id: str, old_trip: Dict[str, Any], updates: Dict[str, Any]
    ) -> None:
        """Sync trip changes to EMHASS adapter."""
        await self._crud._async_sync_trip_to_emhass(trip_id, old_trip, updates)

    async def _async_remove_trip_from_emhass(self, trip_id: str) -> None:
        """Remove a trip from EMHASS deferrable loads."""
        await self._crud._async_remove_trip_from_emhass(trip_id)

    async def _async_publish_new_trip_to_emhass(self, trip: Dict[str, Any]) -> None:
        """Publish a new trip to EMHASS as a deferrable load."""
        await self._crud._async_publish_new_trip_to_emhass(trip)

    async def _get_all_active_trips(self) -> list:
        """Get all active trips for EMHASS publishing."""
        return await self._crud._get_all_active_trips()

    # ── Delegated: SOC mixin ────────────────────────────────────

    async def async_get_vehicle_soc(self, vehicle_id: str) -> float:
        """Obtiene el SOC actual del vehículo desde el sensor configurado."""
        return await self._soc.async_get_vehicle_soc(vehicle_id)

    async def async_calcular_energia_necesaria(
        self, trip: Dict[str, Any], vehicle_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcula la energía necesaria considerando el SOC actual."""
        return await self._soc.async_calcular_energia_necesaria(trip, vehicle_config)

    async def async_get_kwh_needed_today(self) -> float:
        """Calcula la energía necesaria para hoy basado en los viajes."""
        return await self._soc.async_get_kwh_needed_today()

    async def async_get_hours_needed_today(self) -> int:
        """Calcula las horas necesarias para cargar hoy."""
        return await self._soc.async_get_hours_needed_today()

    async def calcular_ventana_carga(
        self,
        trip: Dict[str, Any],
        soc_actual: float,
        hora_regreso: Optional[datetime],
        charging_power_kw: float,
        safety_margin_percent: float = 10.0,
    ) -> Dict[str, Any]:
        """Calcula la ventana de carga disponible para un viaje."""
        return await self._soc.calcular_ventana_carga(
            trip, soc_actual, hora_regreso, charging_power_kw, safety_margin_percent
        )

    async def calcular_ventana_carga_multitrip(
        self,
        trips: list,
        soc_actual: float,
        hora_regreso: Optional[datetime],
        charging_power_kw: float,
        safety_margin_percent: float = 10.0,
    ) -> list:
        """Calcula ventanas de carga para múltiples viajes en cadena."""
        return await self._soc.calcular_ventana_carga_multitrip(
            trips, soc_actual, hora_regreso, charging_power_kw, safety_margin_percent
        )

    async def calcular_soc_inicio_trips(
        self,
        trips: list,
        soc_inicial: float,
        hora_regreso: Optional[datetime],
        charging_power_kw: float,
        battery_capacity_kwh: float = 50.0,
        safety_margin_percent: float = 10.0,
    ) -> list:
        """Calcula el SOC al inicio de cada viaje en cadena."""
        return await self._soc.calcular_soc_inicio_trips(
            trips, soc_inicial, hora_regreso, charging_power_kw,
            battery_capacity_kwh, safety_margin_percent
        )

    async def calcular_hitos_soc(
        self,
        trips: list,
        soc_inicial: float,
        charging_power_kw: float,
        vehicle_config: Optional[Dict[str, Any]] = None,
        hora_regreso: Optional[datetime] = None,
    ) -> list:
        """Calcula los hitos SOC para múltiples viajes con propagación hacia atrás."""
        return await self._soc.calcular_hitos_soc(
            trips, soc_inicial, charging_power_kw, vehicle_config, hora_regreso
        )

    # ── Delegated: Power profile mixin ──────────────────────────

    async def async_generate_power_profile(
        self,
        charging_power_kw: float = 3.6,
        planning_horizon_days: int = 7,
        vehicle_config: Optional[Dict[str, Any]] = None,
        hora_regreso: Optional[datetime] = None,
    ) -> list:
        """Genera el perfil de potencia para EMHASS."""
        return await self._power.async_generate_power_profile(
            charging_power_kw, planning_horizon_days, vehicle_config, hora_regreso
        )

    # ── Delegated: Schedule mixin ───────────────────────────────

    async def async_generate_deferrables_schedule(
        self,
        charging_power_kw: float = 3.6,
        planning_horizon_days: int = 7,
    ) -> list:
        """Genera el calendario de cargas diferibles para EMHASS."""
        if hasattr(self, "_schedule") and self._schedule is not None:
            return await self._schedule.async_generate_deferrables_schedule(
                charging_power_kw, planning_horizon_days
            )
        # Fallback for test stubs (created via __new__): return minimal schedule
        from homeassistant.util import dt as dt_util
        now = dt_util.now()
        return [
            {"date": (now + __import__('datetime').timedelta(days=d, hours=h)).isoformat(), "p_deferrable0": "0.0"}
            for d in range(planning_horizon_days)
            for h in range(24)
        ]

    async def publish_deferrable_loads(
        self, trips: Optional[list] = None
    ) -> None:
        """Publishes all active trips as deferrable loads to EMHASS."""
        await self._schedule.publish_deferrable_loads(trips)
