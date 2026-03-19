"""Gestión central de viajes y optimización de carga para vehículos eléctricos.

Implementa la lógica de planificación de viajes, cálculo de energía necesaria
y sincronización con EMHASS. Cumple con las reglas de Home Assistant 2026 para
runtime_data y tipado estricto.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CHARGING_POWER,
    DEFAULT_CHARGING_POWER,
    DOMAIN,
    TRIP_TYPE_PUNCTUAL,
    TRIP_TYPE_RECURRING,
)
from .utils import calcular_energia_kwh, generate_trip_id
from .vehicle_controller import VehicleController
from .emhass_adapter import EMHASSAdapter

_LOGGER = logging.getLogger(__name__)

class TripManager:
    """Gestión central de viajes y optimización de carga para vehículos eléctricos.

    Esta clase implementa la lógica de planificación de viajes, cálculo de energía necesaria
    y sincronización con EMHASS. Cumple con las reglas de Home Assistant 2026 para
    runtime_data y tipado estricto.
    """

    def __init__(self, hass: HomeAssistant, vehicle_id: str) -> None:
        """Inicializa el gestor de viajes para un vehículo específico."""
        self.hass = hass
        self.vehicle_id = vehicle_id
        self.vehicle_controller = VehicleController(hass, vehicle_id)
        self._trips: Dict[str, Any] = {}
        self._recurring_trips: Dict[str, Any] = {}
        self._punctual_trips: Dict[str, Any] = {}
        self._last_update: Optional[datetime] = None
        self._emhass_adapter: Optional[EMHASSAdapter] = None

    def set_emhass_adapter(self, adapter: EMHASSAdapter) -> None:
        """Set the EMHASS adapter for this trip manager."""
        self._emhass_adapter = adapter
        _LOGGER.debug("EMHASS adapter set for vehicle %s", self.vehicle_id)

    def get_emhass_adapter(self) -> Optional[EMHASSAdapter]:
        """Get the EMHASS adapter for this trip manager."""
        return self._emhass_adapter

    async def async_setup(self) -> None:
        """Configura el gestor de viajes y carga los datos desde el almacenamiento."""
        _LOGGER.info("Configurando gestor de viajes para vehículo: %s", self.vehicle_id)
        await self.vehicle_controller.async_setup()
        await self._load_trips()

    async def _load_trips(self) -> None:
        """Carga los viajes desde el almacenamiento persistente."""
        try:
            # FIX: Usar hass.storage para persistencia entre reinicios
            storage_key = f"{DOMAIN}_{self.vehicle_id}"
            stored_data = await self.hass.storage.async_read(storage_key)

            if stored_data and "data" in stored_data:
                data = stored_data["data"]
                self._trips = data.get("trips", {})
                self._recurring_trips = data.get("recurring_trips", {})
                self._punctual_trips = data.get("punctual_trips", {})
                self._last_update = data.get("last_update")
                _LOGGER.info(
                    "Viajes cargados desde storage: %d recurrentes, %d puntuales",
                    len(self._recurring_trips),
                    len(self._punctual_trips),
                )
            else:
                _LOGGER.info("No se encontraron viajes almacenados para %s", self.vehicle_id)
                self._trips = {}
                self._recurring_trips = {}
                self._punctual_trips = {}
                self._last_update = None
        except Exception as err:
            _LOGGER.error("Error cargando viajes: %s", err)
            self._trips = {}
            self._recurring_trips = {}
            self._punctual_trips = {}
            self._last_update = None

    async def async_save_trips(self) -> None:
        """Guarda los viajes en el almacenamiento persistente."""
        try:
            # FIX: Usar hass.storage.async_write_dict para persistencia
            storage_key = f"{DOMAIN}_{self.vehicle_id}"
            await self.hass.storage.async_write_dict(
                storage_key,
                {
                    "version": 1,
                    "data": {
                        "trips": self._trips,
                        "recurring_trips": self._recurring_trips,
                        "punctual_trips": self._punctual_trips,
                        "last_update": datetime.now().isoformat(),
                    },
                },
            )
            _LOGGER.info(
                "Viajes guardados en storage: %d recurrentes, %d puntuales",
                len(self._recurring_trips),
                len(self._punctual_trips),
            )
        except Exception as err:
            _LOGGER.error("Error guardando viajes: %s", err)

    async def async_get_recurring_trips(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de viajes recurrentes."""
        return list(self._recurring_trips.values())

    async def async_get_punctual_trips(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de viajes puntuales."""
        return list(self._punctual_trips.values())

    async def async_add_recurring_trip(self, **kwargs: Any) -> None:
        """Añade un nuevo viaje recurrente y sincroniza con EMHASS."""
        # Generate trip ID using the new format: rec_{day}_{random}
        if "trip_id" in kwargs:
            trip_id = kwargs["trip_id"]
        else:
            day = kwargs.get("dia_semana", "lunes")
            trip_id = generate_trip_id(TRIP_TYPE_RECURRING, day)
        self._recurring_trips[trip_id] = {
            "id": trip_id,
            "tipo": TRIP_TYPE_RECURRING,
            "dia_semana": kwargs["dia_semana"],
            "hora": kwargs["hora"],
            "km": kwargs["km"],
            "kwh": kwargs["kwh"],
            "descripcion": kwargs.get("descripcion", ""),
            "activo": True,
        }
        await self.async_save_trips()

        # T019.3: Publish new trip to EMHASS
        if self._emhass_adapter:
            await self._async_publish_new_trip_to_emhass(self._recurring_trips[trip_id])

    async def async_add_punctual_trip(self, **kwargs: Any) -> None:
        """Añade un nuevo viaje puntual y sincroniza con EMHASS."""
        # Generate trip ID using the new format: pun_{date}_{random}
        if "trip_id" in kwargs:
            trip_id = kwargs["trip_id"]
        else:
            datetime_str = kwargs.get("datetime_str", kwargs.get("datetime", ""))
            # Extract date from datetime string (format: YYYY-MM-DDTHH:MM)
            if datetime_str:
                date_part = datetime_str.split("T")[0].replace("-", "")
            else:
                date_part = ""
            trip_id = generate_trip_id(TRIP_TYPE_PUNCTUAL, date_part)
        self._punctual_trips[trip_id] = {
            "id": trip_id,
            "tipo": TRIP_TYPE_PUNCTUAL,
            "datetime": kwargs.get("datetime_str", kwargs.get("datetime", "")),
            "km": kwargs["km"],
            "kwh": kwargs["kwh"],
            "descripcion": kwargs.get("descripcion", ""),
            "estado": "pendiente",
        }
        await self.async_save_trips()

        # T019.3: Publish new trip to EMHASS
        if self._emhass_adapter:
            await self._async_publish_new_trip_to_emhass(self._punctual_trips[trip_id])

    async def async_update_trip(self, trip_id: str, updates: Dict[str, Any]) -> None:
        """Actualiza un viaje existente y sincroniza con EMHASS.

        Detects trip edits and triggers EMHASS update when:
        - km/kwh changes (affects energy calculation)
        - datetime/hora changes (affects deadline/deferrable window)
        - descripcion changes (informational only)
        - activo/estado changes (affects if trip is published)
        """
        # Get old trip data before update for comparison
        old_trip = None
        if trip_id in self._recurring_trips:
            old_trip = self._recurring_trips[trip_id].copy()
            self._recurring_trips[trip_id].update(updates)
        elif trip_id in self._punctual_trips:
            old_trip = self._punctual_trips[trip_id].copy()
            self._punctual_trips[trip_id].update(updates)

        await self.async_save_trips()

        # T019.3: Detect trip changes and trigger EMHASS update
        if old_trip and self._emhass_adapter:
            await self._async_sync_trip_to_emhass(trip_id, old_trip, updates)

    async def async_delete_trip(self, trip_id: str) -> None:
        """Elimina un viaje existente y sincroniza con EMHASS."""
        if trip_id in self._recurring_trips:
            del self._recurring_trips[trip_id]
        elif trip_id in self._punctual_trips:
            del self._punctual_trips[trip_id]
        await self.async_save_trips()

        # T019.3: Remove from EMHASS when deleted
        if self._emhass_adapter:
            await self._async_remove_trip_from_emhass(trip_id)

    async def async_pause_recurring_trip(self, trip_id: str) -> None:
        """Pausa un viaje recurrente."""
        if trip_id in self._recurring_trips:
            self._recurring_trips[trip_id]["activo"] = False
        await self.async_save_trips()

    async def async_resume_recurring_trip(self, trip_id: str) -> None:
        """Reanuda un viaje recurrente."""
        if trip_id in self._recurring_trips:
            self._recurring_trips[trip_id]["activo"] = True
        await self.async_save_trips()

    async def async_complete_punctual_trip(self, trip_id: str) -> None:
        """Marca un viaje puntual como completado."""
        if trip_id in self._punctual_trips:
            self._punctual_trips[trip_id]["estado"] = "completado"
        await self.async_save_trips()

    async def async_cancel_punctual_trip(self, trip_id: str) -> None:
        """Cancela un viaje puntual."""
        if trip_id in self._punctual_trips:
            del self._punctual_trips[trip_id]
        await self.async_save_trips()
        # T019.3: Remove from EMHASS when cancelled
        if self._emhass_adapter:
            await self._async_remove_trip_from_emhass(trip_id)

    async def _async_sync_trip_to_emhass(
        self,
        trip_id: str,
        old_trip: Dict[str, Any],
        updates: Dict[str, Any],
    ) -> None:
        """Sync trip changes to EMHASS adapter.

        Detects which fields changed and updates the deferrable load accordingly.
        """
        if not self._emhass_adapter:
            return

        try:
            # Determine if this is an active trip (for publishing)
            is_active = True
            if trip_id in self._recurring_trips:
                is_active = self._recurring_trips[trip_id].get("activo", True)
            elif trip_id in self._punctual_trips:
                is_active = self._punctual_trips[trip_id].get("estado") == "pendiente"

            if not is_active:
                # Trip is paused/cancelled - remove from EMHASS
                await self._async_remove_trip_from_emhass(trip_id)
                _LOGGER.info(
                    "Trip %s is inactive, removed from EMHASS deferrable loads",
                    trip_id
                )
                return

            # Get the updated trip
            trip = None
            if trip_id in self._recurring_trips:
                trip = self._recurring_trips[trip_id]
            elif trip_id in self._punctual_trips:
                trip = self._punctual_trips[trip_id]

            if not trip:
                await self._async_remove_trip_from_emhass(trip_id)
                return

            # Determine what changed
            changed_fields = set(updates.keys())

            # Check for critical changes that require recalculation
            recalculate_fields = {"km", "kwh", "datetime", "hora", "dia_semana", "descripcion"}
            needs_recalculate = bool(changed_fields & recalculate_fields)

            if needs_recalculate:
                # T019.3: Recalculate deferrable load parameters
                # Get charging power from config
                charging_power_kw = self._get_charging_power()

                # Update the deferrable load with new parameters
                await self._emhass_adapter.async_update_deferrable_load(trip)

                # Also update all deferrable loads to recalculate schedule
                all_trips = await self._get_all_active_trips()
                await self._emhass_adapter.publish_deferrable_loads(all_trips, charging_power_kw)

                _LOGGER.info(
                    "Trip %s updated in EMHASS (recalculated): changed fields=%s",
                    trip_id,
                    changed_fields
                )
            else:
                # Non-critical changes (just update attributes)
                await self._emhass_adapter.async_update_deferrable_load(trip)
                _LOGGER.debug(
                    "Trip %s updated in EMHASS (attributes only): changed fields=%s",
                    trip_id,
                    changed_fields
                )

        except Exception as err:  # pragma: no cover
            _LOGGER.error(
                "Error syncing trip %s to EMHASS: %s",
                trip_id,
                err
            )

    async def _async_remove_trip_from_emhass(self, trip_id: str) -> None:
        """Remove a trip from EMHASS deferrable loads."""
        if not self._emhass_adapter:
            return

        try:
            await self._emhass_adapter.async_remove_deferrable_load(trip_id)

            # Update all deferrable loads to reflect the removal
            all_trips = await self._get_all_active_trips()
            charging_power_kw = self._get_charging_power()
            await self._emhass_adapter.publish_deferrable_loads(all_trips, charging_power_kw)

            _LOGGER.info("Trip %s removed from EMHASS deferrable loads", trip_id)
        except Exception as err:  # pragma: no cover
            _LOGGER.error(
                "Error removing trip %s from EMHASS: %s",
                trip_id,
                err
            )

    async def _async_publish_new_trip_to_emhass(self, trip: Dict[str, Any]) -> None:
        """Publish a new trip to EMHASS as a deferrable load."""
        if not self._emhass_adapter:
            return

        try:
            # Publish this trip
            await self._emhass_adapter.async_publish_deferrable_load(trip)

            # Also publish all trips to recalculate the schedule
            all_trips = await self._get_all_active_trips()
            charging_power_kw = self._get_charging_power()
            await self._emhass_adapter.publish_deferrable_loads(all_trips, charging_power_kw)

            _LOGGER.info(
                "Published new trip %s to EMHASS deferrable loads",
                trip.get("id")
            )
        except Exception as err:  # pragma: no cover
            _LOGGER.error(
                "Error publishing trip %s to EMHASS: %s",
                trip.get("id"),
                err
            )

    async def _get_all_active_trips(self) -> List[Dict[str, Any]]:
        """Get all active trips for EMHASS publishing."""
        all_trips = []
        for trip in self._recurring_trips.values():
            if trip.get("activo", True):
                all_trips.append(trip)
        for trip in self._punctual_trips.values():
            if trip.get("estado") == "pendiente":
                all_trips.append(trip)
        return all_trips

    async def async_get_kwh_needed_today(self) -> float:
        """Calcula la energía necesaria para hoy basado en los viajes."""
        today = datetime.now().date()
        total_kwh = 0.0
        for trip in self._recurring_trips.values():
            if trip["activo"] and self._is_trip_today(trip, today):
                total_kwh += trip["kwh"]
        for trip in self._punctual_trips.values():
            if trip["estado"] == "pendiente" and self._is_trip_today(trip, today):
                total_kwh += trip["kwh"]
        return total_kwh

    async def async_get_hours_needed_today(self) -> int:
        """Calcula las horas necesarias para cargar hoy."""
        import math
        kwh_needed = await self.async_get_kwh_needed_today()
        charging_power = self._get_charging_power()
        return math.ceil(kwh_needed / charging_power) if charging_power > 0 else 0

    def _get_charging_power(self) -> float:
        """Obtiene la potencia de carga desde la configuración."""
        try:
            entry = self.hass.config_entries.async_get_entry(self.vehicle_id)
            if entry and entry.data:
                power = entry.data.get(CONF_CHARGING_POWER, DEFAULT_CHARGING_POWER)
                # Ensure we return a valid number
                if isinstance(power, (int, float)) and power > 0:
                    return float(power)
        except Exception:
            pass
        return DEFAULT_CHARGING_POWER

    async def async_get_next_trip(self) -> Optional[Dict[str, Any]]:
        """Obtiene el próximo viaje programado."""
        now = datetime.now()
        next_trip = None
        for trip in self._recurring_trips.values():
            if trip["activo"]:
                trip_time = self._get_trip_time(trip)
                if trip_time and trip_time > now:
                    if next_trip is None or trip_time < next_trip["time"]:
                        next_trip = {"time": trip_time, "trip": trip}
        for trip in self._punctual_trips.values():
            if trip["estado"] == "pendiente":
                trip_time = self._get_trip_time(trip)
                if trip_time and trip_time > now:
                    if next_trip is None or trip_time < next_trip["time"]:
                        next_trip = {"time": trip_time, "trip": trip}
        return next_trip["trip"] if next_trip else None

    def _is_trip_today(self, trip: Dict[str, Any], today: datetime.date) -> bool:
        """Verifica si un viaje ocurre hoy."""
        if trip["tipo"] == TRIP_TYPE_RECURRING:
            # Use weekday index to compare (0=lunes, 6=domingo)
            day_map = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
            return day_map[today.weekday()] == trip["dia_semana"].lower()
        elif trip["tipo"] == TRIP_TYPE_PUNCTUAL:
            return datetime.strptime(trip["datetime"], "%Y-%m-%dT%H:%M").date() == today
        return False

    def _get_trip_time(self, trip: Dict[str, Any]) -> Optional[datetime]:
        """Obtiene la fecha y hora del viaje."""
        if trip["tipo"] == TRIP_TYPE_RECURRING:
            now = datetime.now()
            today = now.date()
            day_of_week = now.weekday()
            target_day = self._get_day_index(trip["dia_semana"])
            days_ahead = (target_day - day_of_week) % 7
            if days_ahead == 0 and now.hour > int(trip["hora"].split(":")[0]):
                days_ahead = 7
            return datetime.combine(
                today + timedelta(days=days_ahead),
                datetime.strptime(trip["hora"], "%H:%M").time(),
            )
        elif trip["tipo"] == TRIP_TYPE_PUNCTUAL:
            return datetime.strptime(trip["datetime"], "%Y-%m-%dT%H:%M")
        return None

    def _get_day_index(self, day_name: str) -> int:
        """Obtiene el índice del día de la semana."""
        days = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
        return days.index(day_name.lower())

    async def async_get_vehicle_soc(self, vehicle_id: str) -> float:
        """Obtiene el SOC actual del vehículo desde el sensor configurado."""
        try:
            entry = self.hass.config_entries.async_get_entry(vehicle_id)
            if entry and entry.data:
                soc_sensor = entry.data.get("soc_sensor")
                if soc_sensor:
                    state = self.hass.states.get(soc_sensor)
                    if state and state.state not in ("unknown", "unavailable", "none"):
                        return float(state.state)
                _LOGGER.warning("Sensor SOC no disponible para %s", vehicle_id)
            else:
                _LOGGER.warning("Config entry no encontrada para %s", vehicle_id)
        except Exception as err:
            _LOGGER.error("Error obteniendo SOC: %s", err)
        return 0.0

    async def async_calcular_energia_necesaria(
        self, trip: Dict[str, Any], vehicle_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcula la energía necesaria considerando el SOC actual.

        Args:
            trip: Diccionario con datos del viaje (kwh, km, datetime, etc.)
            vehicle_config: Diccionario con configuración del vehículo
                - battery_capacity_kwh: Capacidad de batería en kWh
                - charging_power_kw: Potencia de carga en kW
                - soc_current: SOC actual del vehículo en %
                - consumption_kwh_per_km: Consumo en kWh/km (opcional)

        Returns:
            Diccionario con:
                - energia_necesaria_kwh: Energía a cargar en kWh
                - horas_carga_necesarias: Horas necesarias para cargar
                - alerta_tiempo_insuficiente: True si no hay tiempo suficiente
                - horas_disponibles: Horas disponibles hasta el deadline

        Raises:
            ValueError: Si la distancia o el consumo son negativos.
        """
        battery_capacity = vehicle_config.get("battery_capacity_kwh", 50.0)
        charging_power_kw = vehicle_config.get("charging_power_kw", 3.6)
        soc_current = vehicle_config.get("soc_current", 100.0)
        consumption_kwh_per_km = vehicle_config.get("consumption_kwh_per_km", 0.15)

        # Calcular energía del viaje
        # Prioridad: usar kwh directo si existe, sino calcular desde km * consumo
        if "kwh" in trip:
            # Backward compatibility: usar valor directo si se proporciona
            energia_viaje = trip.get("kwh", 0.0)
        else:
            # Usar la fórmula: energia = distancia * consumo
            distance_km = trip.get("km", 0.0)
            energia_viaje = calcular_energia_kwh(distance_km, consumption_kwh_per_km)

        # Energía objetivo: energía del viaje + 40% de la batería (margen)
        energia_objetivo = energia_viaje + (battery_capacity * 0.4)

        # Energía actual en batería
        energia_actual = (soc_current / 100.0) * battery_capacity

        # Energía necesaria
        energia_necesaria = max(0.0, energia_objetivo - energia_actual)
        horas_carga = energia_necesaria / charging_power_kw if charging_power_kw > 0 else 0

        # Calcular horas disponibles hasta el deadline
        horas_disponibles = 0.0
        alerta_tiempo_insuficiente = False

        # Get trip type from the trip dict
        trip_tipo = trip.get("tipo")
        trip_datetime = trip.get("datetime")

        if trip_tipo and trip_datetime:
            # Trip has tipo and datetime - use _get_trip_time
            trip_time = self._get_trip_time(trip)
            if trip_time:
                now = datetime.now()
                delta = trip_time - now
                horas_disponibles = delta.total_seconds() / 3600
                if horas_carga > horas_disponibles:
                    alerta_tiempo_insuficiente = True
        elif trip_datetime:
            # Handle case where trip has datetime but tipo not set
            try:
                if isinstance(trip_datetime, datetime):
                    trip_time = trip_datetime
                else:
                    trip_time = datetime.strptime(trip_datetime, "%Y-%m-%dT%H:%M")
                now = dt_util.now()
                delta = trip_time - now
                horas_disponibles = delta.total_seconds() / 3600
                if horas_carga > horas_disponibles:
                    alerta_tiempo_insuficiente = True
            except (KeyError, ValueError, TypeError):
                pass

        return {
            "energia_necesaria_kwh": round(energia_necesaria, 3),
            "horas_carga_necesarias": round(horas_carga, 2),
            "alerta_tiempo_insuficiente": alerta_tiempo_insuficiente,
            "horas_disponibles": round(horas_disponibles, 2),
        }

    async def async_generate_power_profile(
        self,
        charging_power_kw: float = 3.6,
        planning_horizon_days: int = 7,
        vehicle_config: Optional[Dict[str, Any]] = None,
    ) -> List[float]:
        """Genera el perfil de potencia para EMHASS.

        Args:
            charging_power_kw: Potencia de carga en kW
            planning_horizon_days: Días de horizonte de planificación
            vehicle_config: Optional configuration dict with battery_capacity_kwh,
                          charging_power_kw, soc_current

        Returns:
            Lista de valores de potencia en watts (0 = no cargar, positivo = cargar)
        """
        # Cargar viajes
        await self._load_trips()

        # Obtener configuración del vehículo
        # Use provided vehicle_config if available, otherwise get from config entry
        if vehicle_config:
            battery_capacity = vehicle_config.get("battery_capacity_kwh", 50.0)
            soc_current = vehicle_config.get("soc_current")
        else:
            try:
                entry = self.hass.config_entries.async_get_entry(self.vehicle_id)
                if entry and entry.data:
                    battery_capacity = entry.data.get("battery_capacity_kwh", 50.0)
                else:
                    battery_capacity = 50.0
            except Exception:
                battery_capacity = 50.0
            soc_current = None

        # Obtener SOC actual - only fetch if not provided in vehicle_config
        if soc_current is None:
            soc_current = await self.async_get_vehicle_soc(self.vehicle_id)

        # Inicializar perfil de potencia (0 = no cargar)
        profile_length = planning_horizon_days * 24
        power_profile = [0.0] * profile_length

        # Obtener todos los viajes pendientes
        all_trips = []
        for trip in self._recurring_trips.values():
            if trip.get("activo", True):
                all_trips.append(trip)
        for trip in self._punctual_trips.values():
            if trip.get("estado") == "pendiente":
                all_trips.append(trip)

        # Asignar índices a los viajes y aplicar prioridad
        # Urgentes = menor deadline = índice menor (prioridad alta)
        # Ordenar por tiempo de viaje (deadline más temprano = más urgente)
        now = datetime.now()
        for trip in all_trips:
            trip_time = self._get_trip_time(trip)
            if trip_time:
                trip["_deadline"] = trip_time
            else:
                trip["_deadline"] = datetime.max  # Sin deadline conocido = menor prioridad

        # Ordenar trips: primero los más urgentes (deadline más cercano)
        all_trips.sort(key=lambda t: t.get("_deadline", datetime.max))

        # Asignar índice a cada viaje (0, 1, 2, ...)
        for idx, trip in enumerate(all_trips):
            trip["_trip_index"] = idx

        # Procesar cada viaje
        for trip in all_trips:
            # Calcular energía necesaria
            vehicle_config = {
                "battery_capacity_kwh": battery_capacity,
                "charging_power_kw": charging_power_kw,
                "soc_current": soc_current,
            }
            energia_info = await self.async_calcular_energia_necesaria(trip, vehicle_config)
            energia_kwh = energia_info["energia_necesaria_kwh"]
            horas_carga = energia_info["horas_carga_necesarias"]

            if energia_kwh <= 0:
                continue

            # Convertir a watts
            charging_power_watts = charging_power_kw * 1000

            # Determinar las horas de carga
            horas_necesarias = int(horas_carga) + (1 if horas_carga % 1 > 0 else 0)
            if horas_necesarias == 0:
                horas_necesarias = 1

            # Obtener deadline del viaje
            trip_time = self._get_trip_time(trip)
            if not trip_time:
                continue

            # Calcular posición en el perfil (desde ahora)
            delta = trip_time - now
            horas_hasta_viaje = int(delta.total_seconds() / 3600)

            if horas_hasta_viaje < 0:
                continue  # El viaje ya pasó

            # Determinar horas de carga: las últimas horas antes del deadline
            hora_inicio_carga = max(0, horas_hasta_viaje - horas_necesarias)

            # Distribuir la carga en las horas disponibles
            for h in range(hora_inicio_carga, min(horas_hasta_viaje, profile_length)):
                if h >= 0 and h < profile_length:
                    power_profile[h] = charging_power_watts

        return power_profile

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
            entry = self.hass.config_entries.async_get_entry(self.vehicle_id)
            if entry and entry.data:
                entry.data.get("battery_capacity_kwh", 50.0)
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
        now = datetime.now()
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
        power_profiles: List[List[float]] = [[0.0] * profile_length for _ in range(num_trips)]

        # Obtener configuración del vehículo
        battery_capacity = 50.0
        soc_current = 50.0
        try:
            entry = self.hass.config_entries.async_get_entry(self.vehicle_id)
            if entry and entry.data:
                battery_capacity = entry.data.get("battery_capacity_kwh", 50.0)
        except Exception:
            pass
        soc_current = await self.async_get_vehicle_soc(self.vehicle_id)

        # Generar perfil de potencia para cada viaje
        for idx, trip in enumerate(all_trips):
            vehicle_config = {
                "battery_capacity_kwh": battery_capacity,
                "charging_power_kw": charging_power_kw,
                "soc_current": soc_current,
            }
            energia_info = await self.async_calcular_energia_necesaria(trip, vehicle_config)
            energia_kwh = energia_info["energia_necesaria_kwh"]
            horas_carga = energia_info["horas_carga_necesarias"]

            if energia_kwh <= 0:
                continue

            # Convertir a watts
            charging_power_watts = charging_power_kw * 1000

            # Determinar las horas de carga necesarias
            horas_necesarias = int(horas_carga) + (1 if horas_carga % 1 > 0 else 0)
            if horas_necesarias == 0:
                horas_necesarias = 1

            # Obtener deadline del viaje
            trip_time = self._get_trip_time(trip)
            if not trip_time:
                continue

            # Calcular posición en el perfil (desde ahora)
            delta = trip_time - now
            horas_hasta_viaje = int(delta.total_seconds() / 3600)

            if horas_hasta_viaje < 0:
                continue  # El viaje ya pasó

            # Determinar horas de carga: las últimas horas antes del deadline
            hora_inicio_carga = max(0, horas_hasta_viaje - horas_necesarias)

            # Distribuir la carga en las horas disponibles
            for h in range(hora_inicio_carga, min(horas_hasta_viaje, profile_length)):
                if h >= 0 and h < profile_length:
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
