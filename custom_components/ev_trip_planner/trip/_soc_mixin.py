"""SOC calculation mixin for TripManager — extracted from trip_manager.py.

Contains all SOC (State of Charge) calculation methods:
- async_get_vehicle_soc: fetch current SOC from HA sensor
- async_calcular_energia_necesaria: energy needed considering current SOC
- calcular_ventana_carga: available charging window for a single trip
- calcular_ventana_carga_multitrip: charging windows for multiple chained trips
- calcular_soc_inicio_trips: SOC at start of each trip in a chain
- calcular_hitos_soc: SOC milestones with deficit propagation
- Helper methods: _get_charging_power, _calcular_tasa_carga_soc,
  _calcular_soc_objetivo_base, _is_trip_today, _get_trip_time,
  _get_day_index, _parse_trip_datetime

This mixin uses composition: it receives a `TripManagerState` instance
in `__init__` and accesses all shared state through `self._state.xxx`.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util

from ..calculations import (
    BatteryCapacity,
    calculate_charging_rate,
    calculate_day_index,
    calculate_deficit_propagation,
    calculate_dynamic_soc_limit,
    calculate_soc_target,
    calculate_trip_time,
    DEFAULT_T_BASE,
)
from ..const import CONF_CHARGING_POWER, CONF_SOH_SENSOR, DEFAULT_CHARGING_POWER, DOMAIN
from ..utils import (
    calcular_energia_kwh,
    is_trip_today as pure_is_trip_today,
)

from .state import TripManagerState


_LOGGER = logging.getLogger(__name__)


class _SOCMixin:
    """Mixin providing SOC calculation operations for TripManager.

    Uses composition — receives TripManagerState in __init__ and stores it
    as self._state. All shared state access goes through self._state.xxx.
    """

    def __init__(self, state: TripManagerState) -> None:
        """Initialize the SOC mixin with shared state."""
        self._state = state

    # ── Helper Methods ──────────────────────────────────────────

    def _parse_trip_datetime(
        self, trip_datetime: datetime | str, allow_none: bool = False
    ) -> datetime | None:
        """Parse trip datetime, ensuring timezone awareness for both object and string inputs.

        Handles two input types:
        - datetime objects: ensures tzinfo is set to UTC if naive
        - strings: parses via dt_util.parse_datetime, then ensures tz awareness

        Args:
            trip_datetime: A datetime object or ISO-format string representing trip time.
            allow_none: If True, returns None on parse failure instead of current UTC time.

        Returns:
            A timezone-aware datetime object, or None if allow_none is True and parsing fails.
        """
        if isinstance(trip_datetime, datetime):
            dt = trip_datetime
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        else:
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

    def _get_charging_power(self) -> float:
        """Obtiene la potencia de carga desde la configuración."""
        try:
            # Buscar config entry por vehicle_name (vehicle_id es vehicle_name, no entry_id)
            entry: Optional[ConfigEntry[Any]] = None
            for config_entry in self._state.hass.config_entries.async_entries(DOMAIN):
                if config_entry.data.get("vehicle_name") == self._state.vehicle_id:
                    entry = config_entry
                    break

            if entry is not None and entry.data is not None:
                power = entry.data.get(CONF_CHARGING_POWER, DEFAULT_CHARGING_POWER)
                # Ensure we return a valid number
                if isinstance(power, (int, float)) and power > 0:
                    return float(power)
        except Exception:
            pass
        return DEFAULT_CHARGING_POWER

    def _calcular_tasa_carga_soc(
        self, charging_power_kw: float, battery_capacity_kwh: float = 50.0
    ) -> float:
        """Calcula la tasa de carga en % SOC/hora.

        Formula: charging_power_kw / battery_capacity_kwh * 100 = % SOC/hour

        Delegates to pure calculate_charging_rate for testability.

        Args:
            charging_power_kw: Potencia de carga en kW
            battery_capacity_kwh: Capacidad de la bateria en kWh (default 50.0)

        Returns:
            Tasa de carga en % SOC por hora
        """
        return calculate_charging_rate(charging_power_kw, battery_capacity_kwh)

    def _calcular_soc_objetivo_base(
        self,
        trip: Dict[str, Any],
        battery_capacity_kwh: float,
        consumption_kwh_per_km: float = 0.15,
    ) -> float:
        """Calculates the base SOC target percentage for a trip.

        Delegates to pure calculate_soc_target for testability.

        Args:
            trip: Dictionary with trip data (kwh or km, consumo)
            battery_capacity_kwh: Battery capacity in kWh
            consumption_kwh_per_km: Energy consumption in kWh/km (default 0.15)

        Returns:
            Base SOC target percentage for the trip (energy + buffer)
        """
        return calculate_soc_target(trip, battery_capacity_kwh, consumption_kwh_per_km)

    def _is_trip_today(self, trip: Dict[str, Any], today: date) -> bool:
        """Verifica si un viaje ocurre hoy.

        Delegates to pure utils.is_trip_today for testability.
        """
        return pure_is_trip_today(trip, today)

    def _get_trip_time(self, trip: Dict[str, Any]) -> Optional[datetime]:
        """Obtiene la fecha y hora del viaje.

        Delegates to pure calculate_trip_time for the core algorithm.
        Returns timezone-aware datetime for proper comparison with datetime.now(timezone.utc).
        """
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
        """Obtiene el índice del día de la semana.

        Delegates to pure calculate_day_index for the core algorithm.
        """
        return calculate_day_index(day_name)

    # ── SOC Fetching ────────────────────────────────────────────

    async def async_get_vehicle_soc(self, vehicle_id: str) -> float:
        """Obtiene el SOC actual del vehículo desde el sensor configurado."""
        try:
            # Buscar config entry por vehicle_name (vehicle_id es vehicle_name, no entry_id)
            entry = None
            for config_entry in self._state.hass.config_entries.async_entries(DOMAIN):
                if config_entry.data.get("vehicle_name") == vehicle_id:
                    entry = config_entry
                    break

            if entry and entry.data:
                soc_sensor = entry.data.get("soc_sensor")
                if soc_sensor:
                    state = self._state.hass.states.get(soc_sensor)
                    if state and state.state not in ("unknown", "unavailable", "none"):
                        return float(state.state)
                _LOGGER.warning("Sensor SOC no disponible para %s", vehicle_id)
            else:
                _LOGGER.warning("Config entry no encontrada para %s", vehicle_id)
        except Exception as err:
            _LOGGER.error("Error obteniendo SOC: %s", err)
        return 0.0

    # ── Energy Calculation ──────────────────────────────────────

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
        safety_margin_percent = vehicle_config.get("safety_margin_percent", 10.0)

        # Calcular energía del viaje
        if "kwh" in trip:
            energia_viaje = trip.get("kwh", 0.0)
        else:
            distance_km = trip.get("km", 0.0)
            energia_viaje = calcular_energia_kwh(distance_km, consumption_kwh_per_km)

        energia_objetivo = energia_viaje
        energia_actual = (soc_current / 100.0) * battery_capacity
        energia_necesaria = max(0.0, energia_objetivo - energia_actual)
        energia_final = energia_necesaria * (1 + safety_margin_percent / 100)

        if charging_power_kw > 0:
            horas_carga = energia_final / charging_power_kw
        else:
            horas_carga = 0

        # Calcular horas disponibles hasta el deadline
        horas_disponibles = 0.0
        alerta_tiempo_insuficiente = False

        trip_tipo = trip.get("tipo")
        trip_datetime = trip.get("datetime")

        if trip_tipo and trip_datetime:
            trip_time = self._get_trip_time(trip)
            if trip_time:
                now = datetime.now(timezone.utc)
                delta = trip_time - now
                horas_disponibles = delta.total_seconds() / 3600
                if horas_carga > horas_disponibles:
                    alerta_tiempo_insuficiente = True
        elif trip_datetime:
            try:
                trip_time = self._state._parse_trip_datetime(trip_datetime)
                if trip_time is not None:
                    now = dt_util.now()
                    try:
                        delta = trip_time - now
                    except TypeError as err:
                        _LOGGER.error(
                            "Datetime subtraction TypeError: trip_datetime=%s (%s), now=%s (%s): %s",
                            repr(trip_datetime),
                            type(trip_datetime),
                            repr(now),
                            type(now),
                            err,
                        )
                        try:
                            if getattr(trip_time, "tzinfo", None) is None:
                                trip_time = trip_time.replace(tzinfo=timezone.utc)
                            delta = trip_time - now
                        except Exception:
                            delta = None

                    if delta is not None:
                        horas_disponibles = delta.total_seconds() / 3600
                        if horas_carga > horas_disponibles:
                            alerta_tiempo_insuficiente = True
            except (KeyError, ValueError, TypeError):
                pass

        return {
            "energia_necesaria_kwh": round(energia_final, 3),
            "horas_carga_necesarias": round(horas_carga, 2),
            "alerta_tiempo_insuficiente": alerta_tiempo_insuficiente,
            "horas_disponibles": round(horas_disponibles, 2),
            "margen_seguridad_aplicado": safety_margin_percent,
        }

    # ── Charging Window Calculation ─────────────────────────────

    async def calcular_ventana_carga(
        self,
        trip: Dict[str, Any],
        soc_actual: float,
        hora_regreso: Optional[datetime],
        charging_power_kw: float,
        safety_margin_percent: float = 10.0,
    ) -> Dict[str, Any]:
        """Calcula la ventana de carga disponible para un viaje.

        La ventana de carga es el tiempo desde que el coche regresa a casa
        hasta que inicia el siguiente viaje.

        Args:
            trip: Diccionario con datos del viaje (datetime, hora, km, kwh, etc.)
            soc_actual: SOC actual del vehículo en porcentaje (0-100)
            hora_regreso: Fecha y hora real de regreso del vehículo (None si no ha llegado)
            charging_power_kw: Potencia de carga en kW
            safety_margin_percent: Safety margin percentage (default 10.0)

        Returns:
            Diccionario con:
                - ventana_horas: Horas disponibles para cargar
                - kwh_necesarios: Energía necesaria en kWh
                - horas_carga_necesarias: Horas necesarias para cargar
                - inicio_ventana: Fecha y hora de inicio de la ventana
                - fin_ventana: Fecha y hora de fin de la ventana
                - es_suficiente: True si la ventana es suficiente para cargar
        """
        DURACION_VIAJE_HORAS = 6

        parsed_hora_regreso = None
        if hora_regreso is not None:
            if isinstance(hora_regreso, str):
                try:
                    parsed_hora_regreso = datetime.fromisoformat(hora_regreso)
                except (ValueError, TypeError) as err:
                    _LOGGER.warning(
                        "Error parsing hora_regreso '%s': %s", hora_regreso, err
                    )
                    parsed_hora_regreso = None
            else:
                parsed_hora_regreso = hora_regreso
            if parsed_hora_regreso is not None and parsed_hora_regreso.tzinfo is None:
                parsed_hora_regreso = parsed_hora_regreso.replace(tzinfo=timezone.utc)

        if parsed_hora_regreso is not None:
            next_trip = await self._state.async_get_next_trip_after(parsed_hora_regreso)
            if next_trip is None:
                return {
                    "ventana_horas": 0,
                    "kwh_necesarios": 0,
                    "horas_carga_necesarias": 0,
                    "inicio_ventana": None,
                    "fin_ventana": None,
                    "es_suficiente": True,
                }

        trip_departure_time = self._get_trip_time(trip)
        if trip_departure_time is None:
            trip_datetime = trip.get("datetime")
            if trip_datetime:
                trip_departure_time = self._parse_trip_datetime(
                    trip_datetime, allow_none=True
                )

        if parsed_hora_regreso is not None:
            inicio_ventana = parsed_hora_regreso
        elif trip_departure_time is not None:
            inicio_ventana = trip_departure_time - timedelta(hours=DURACION_VIAJE_HORAS)
        else:
            return {
                "ventana_horas": 0.0,
                "kwh_necesarios": 0.0,
                "horas_carga_necesarias": 0.0,
                "inicio_ventana": None,
                "fin_ventana": None,
                "es_suficiente": True,
            }

        if trip_departure_time is not None:
            fin_ventana = trip_departure_time
        else:
            fin_ventana = dt_util.now() + timedelta(hours=DURACION_VIAJE_HORAS)

        delta = fin_ventana - inicio_ventana
        ventana_horas = max(0.0, delta.total_seconds() / 3600)

        vehicle_config = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": charging_power_kw,
            "soc_current": soc_actual,
            "safety_margin_percent": safety_margin_percent,
        }
        energia_info = await self._state.async_calcular_energia_necesaria(trip, vehicle_config)
        kwh_necesarios = energia_info["energia_necesaria_kwh"]

        if charging_power_kw > 0:
            horas_carga_necesarias = kwh_necesarios / charging_power_kw
        else:
            horas_carga_necesarias = 0.0

        es_suficiente = ventana_horas >= horas_carga_necesarias

        return {
            "ventana_horas": round(ventana_horas, 2),
            "kwh_necesarios": round(kwh_necesarios, 3),
            "horas_carga_necesarias": round(horas_carga_necesarias, 2),
            "inicio_ventana": inicio_ventana,
            "fin_ventana": fin_ventana,
            "es_suficiente": es_suficiente,
        }

    async def calcular_ventana_carga_multitrip(
        self,
        trips: List[Dict[str, Any]],
        soc_actual: float,
        hora_regreso: Optional[datetime],
        charging_power_kw: float,
        safety_margin_percent: float = 10.0,
    ) -> List[Dict[str, Any]]:
        """Calcula ventanas de carga para múltiples viajes en cadena.

        Cada viaje obtiene su propia ventana de carga. La ventana del primer
        viaje comienza en hora_regreso. Los viajes subsequentes comienzan
        cuando termina el viaje anterior (departure + 6h).

        Args:
            trips: Lista de diccionarios con datos de viajes
            soc_actual: SOC actual del vehículo en porcentaje (0-100)
            hora_regreso: Fecha y hora real de regreso (None si no ha llegado)
            charging_power_kw: Potencia de carga en kW
            safety_margin_percent: Safety margin percentage (default 10.0)

        Returns:
            Lista de diccionarios, uno por viaje, cada uno conteniendo:
                - ventana_horas: Horas disponibles para cargar
                - kwh_necesarios: Energía necesaria en kWh
                - horas_carga_necesarias: Horas necesarias para cargar
                - inicio_ventana: Fecha y hora de inicio de la ventana
                - fin_ventana: Fecha y hora de fin de la ventana
                - es_suficiente: True si la ventana es suficiente
                - trip: El trip original
        """
        DURACION_VIAJE_HORAS = 6

        if not trips:
            return []

        parsed_hora_regreso = None
        if hora_regreso is not None:
            if isinstance(hora_regreso, str):
                try:
                    parsed_hora_regreso = datetime.fromisoformat(hora_regreso)
                except (ValueError, TypeError) as err:
                    _LOGGER.warning(
                        "Error parsing hora_regreso '%s': %s", hora_regreso, err
                    )
                    parsed_hora_regreso = None
            else:
                parsed_hora_regreso = hora_regreso
            if parsed_hora_regreso is not None and parsed_hora_regreso.tzinfo is None:
                parsed_hora_regreso = parsed_hora_regreso.replace(tzinfo=timezone.utc)

        sorted_trips = []
        for trip in trips:
            trip_time = self._get_trip_time(trip)
            if trip_time:
                sorted_trips.append((trip_time, trip))
        sorted_trips.sort(key=lambda x: x[0])
        trips_with_times = [(trip, trip_time) for trip_time, trip in sorted_trips]

        results = []
        previous_arrival = None

        for idx, (trip, trip_departure_time) in enumerate(trips_with_times):
            if idx == 0:
                if parsed_hora_regreso is not None:
                    window_start = parsed_hora_regreso
                else:
                    window_start = trip_departure_time - timedelta(
                        hours=DURACION_VIAJE_HORAS
                    )
            else:
                assert previous_arrival is not None
                window_start = previous_arrival

            trip_arrival = trip_departure_time + timedelta(hours=DURACION_VIAJE_HORAS)

            delta = trip_arrival - window_start
            ventana_horas = max(0.0, delta.total_seconds() / 3600)

            vehicle_config = {
                "battery_capacity_kwh": 50.0,
                "charging_power_kw": charging_power_kw,
                "soc_current": soc_actual,
                "safety_margin_percent": safety_margin_percent,
            }
            energia_info = await self._state.async_calcular_energia_necesaria(
                trip, vehicle_config
            )
            kwh_necesarios = energia_info["energia_necesaria_kwh"]

            if charging_power_kw > 0:
                horas_carga_necesarias = kwh_necesarios / charging_power_kw
            else:
                horas_carga_necesarias = 0.0

            es_suficiente = ventana_horas >= horas_carga_necesarias

            results.append(
                {
                    "ventana_horas": round(ventana_horas, 2),
                    "kwh_necesarios": round(kwh_necesarios, 3),
                    "horas_carga_necesarias": round(horas_carga_necesarias, 2),
                    "inicio_ventana": window_start,
                    "fin_ventana": trip_departure_time,
                    "es_suficiente": es_suficiente,
                    "trip": trip,
                }
            )

            previous_arrival = trip_arrival

        return results

    # ── SOC Start Calculation ───────────────────────────────────

    async def calcular_soc_inicio_trips(
        self,
        trips: List[Dict[str, Any]],
        soc_inicial: float,
        hora_regreso: Optional[datetime],
        charging_power_kw: float,
        battery_capacity_kwh: float = 50.0,
        safety_margin_percent: float = 10.0,
    ) -> List[Dict[str, Any]]:
        """Calcula el SOC al inicio de cada viaje en cadena.

        Utiliza calcular_ventana_carga_multitrip para obtener las ventanas de carga
        y calcula el SOC de inicio para cada viaje.

        Args:
            trips: Lista de diccionarios con datos de viajes
            soc_inicial: SOC inicial del vehículo al comenzar la cadena (%)
            hora_regreso: Fecha y hora real de regreso (None si no ha llegado)
            charging_power_kw: Potencia de carga en kW
            battery_capacity_kwh: Capacidad de batería en kWh
            safety_margin_percent: Safety margin percentage (default 10.0)

        Returns:
            Lista de diccionarios, uno por viaje, conteniendo:
                - soc_inicio: SOC al inicio del viaje (%)
                - trip: El trip original
                - arrival_soc: SOC al llegar (después de cargar)
        """
        if not trips:
            return []

        ventanas = await self._state.calcular_ventana_carga_multitrip(
            trips=trips,
            soc_actual=soc_inicial,
            hora_regreso=hora_regreso,
            charging_power_kw=charging_power_kw,
            safety_margin_percent=safety_margin_percent,
        )

        results = []
        soc_actual = soc_inicial

        results = []
        soc_actual = soc_inicial

        for idx, ventana in enumerate(ventanas):
            trip = ventana["trip"]
            ventana_horas = ventana["ventana_horas"]
            kwh_necesarios = ventana["kwh_necesarios"]

            soc_inicio = soc_actual

            if charging_power_kw > 0 and ventana_horas > 0:
                kwh_disponibles = charging_power_kw * ventana_horas
                kwh_a_cargar = min(kwh_necesarios, kwh_disponibles)
            else:
                kwh_a_cargar = 0.0

            if battery_capacity_kwh > 0:
                soc_llegada = soc_actual + (kwh_a_cargar / battery_capacity_kwh * 100)
                soc_llegada = min(100.0, soc_llegada)
            else:
                soc_llegada = soc_actual

            results.append(
                {
                    "soc_inicio": round(soc_inicio, 2),
                    "trip": trip,
                    "arrival_soc": round(soc_llegada, 2),
                }
            )

            soc_actual = soc_llegada

        return results

    # ── SOC Milestone Calculation ───────────────────────────────

    async def calcular_hitos_soc(
        self,
        trips: List[Dict[str, Any]],
        soc_inicial: float,
        charging_power_kw: float,
        vehicle_config: Optional[Dict[str, Any]] = None,
        hora_regreso: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        # NOTE: This function is not called from the production path (which uses
        # calculate_dynamic_soc_limit() inline in emhass_adapter.py). It is kept as
        # a reference implementation with 17+ unit tests verifying the algorithm.
        # See T062/T087 review notes and task_review.md for the design decision.
        """Calcula los hitos SOC para múltiples viajes con propagación hacia atrás.

        Implements the deficit detection and propagation algorithm:
        1. Sorts trips by departure time (earliest first)
        2. Iterates in REVERSE order (last trip to first)
        3. Calculates charging capacity: tasa_carga_soc * ventana_horas
        4. If soc_inicio + capacidad_carga < soc_objetivo:
           - deficit = soc_objetivo - (soc_inicio + capacidad_carga)
           - Propagates deficit to previous trip
        5. Stores deficit_acumulado for each trip

        Delegates pure deficit propagation to calculate_deficit_propagation.

        Args:
            trips: Lista de diccionarios con datos de viajes
            soc_inicial: SOC inicial del vehículo al comenzar la cadena (%)
            charging_power_kw: Potencia de carga en kW
            vehicle_config: Diccionario con configuración del vehículo
                - battery_capacity_kwh: Capacidad de batería en kWh (fallback 50.0)
            hora_regreso: Fecha y hora real de regreso (None si no ha llegado)

        Returns:
            Lista de SOCMilestoneResult con soc_objetivo ajustado y deficit_acumulado
        """
        # Extract battery_capacity_kwh and safety_margin_percent from vehicle_config
        battery_capacity_kwh = 50.0
        safety_margin_percent = 10.0
        soh_sensor_entity_id: Optional[str] = None
        if vehicle_config and isinstance(vehicle_config, dict):
            battery_capacity_kwh = vehicle_config.get("battery_capacity_kwh", 50.0)
            safety_margin_percent = vehicle_config.get("safety_margin_percent", 10.0)
            soh_sensor_entity_id = vehicle_config.get(CONF_SOH_SENSOR) or None

        # T051: Create BatteryCapacity instance from config for SOH-aware capacity
        battery_cap = BatteryCapacity(
            nominal_capacity_kwh=battery_capacity_kwh,
            soh_sensor_entity_id=soh_sensor_entity_id,
        )
        # Use real capacity (SOH-adjusted if sensor configured, nominal otherwise)
        real_capacity_kwh = battery_cap.get_capacity(self._state.hass)

        if not trips:
            return []

        # Obtener información SOC inicio para todos los viajes
        soc_inicio_info = await self._state.calcular_soc_inicio_trips(
            trips=trips,
            soc_inicial=soc_inicial,
            hora_regreso=hora_regreso,
            charging_power_kw=charging_power_kw,
            battery_capacity_kwh=battery_capacity_kwh,
            safety_margin_percent=safety_margin_percent,
        )

        # Calcular tasa de carga SOC (%/hora)
        tasa_carga_soc = self._state._calcular_tasa_carga_soc(
            charging_power_kw, battery_capacity_kwh
        )

        # Obtener ventanas de carga
        ventanas = await self._state.calcular_ventana_carga_multitrip(
            trips=trips,
            soc_actual=soc_inicial,
            hora_regreso=hora_regreso,
            charging_power_kw=charging_power_kw,
            safety_margin_percent=safety_margin_percent,
        )

        _LOGGER.debug(
            "Deficit propagation START: %d trips, soc_inicial=%.2f%%, tasa_carga_soc=%.2f%%/h",
            len(trips),
            soc_inicial,
            tasa_carga_soc,
        )

        # Extract t_base from vehicle_config (falls back to DEFAULT_T_BASE)
        t_base = DEFAULT_T_BASE
        if vehicle_config and isinstance(vehicle_config, dict):
            t_base = vehicle_config.get("t_base", DEFAULT_T_BASE)

        # Pre-compute dynamic SOC caps per trip (for degradation-aware capping)
        soc_caps: Optional[List[float]] = None
        results: List[dict[str, Any]] = []
        if trips:
            precomputed_trip_times = [self._state._get_trip_time(trip) for trip in trips]
            now_dt = datetime.now(timezone.utc)
            soc_caps = [100.0] * len(trips)
            for i, trip in enumerate(trips):
                trip_time = precomputed_trip_times[i]
                if trip_time:
                    try:
                        if getattr(trip_time, "tzinfo", None) is None:
                            trip_time = trip_time.replace(tzinfo=timezone.utc)
                        t_hours = (trip_time - now_dt).total_seconds() / 3600.0
                    except Exception:
                        t_hours = 0.0
                else:
                    t_hours = 0.0
                limit = calculate_dynamic_soc_limit(
                    t_hours, soc_inicial, real_capacity_kwh, t_base=t_base
                )
                soc_caps[i] = limit

            # Delegate pure deficit propagation algorithm to calculations.py
            precomputed_soc_targets = [
                self._state._calcular_soc_objetivo_base(trip, real_capacity_kwh)
                for trip in trips
            ]
            results = calculate_deficit_propagation(
                trips=trips,
                soc_data=soc_inicio_info,
                windows=ventanas,
                tasa_carga_soc=tasa_carga_soc,
                battery_capacity_kwh=real_capacity_kwh,
                reference_dt=datetime.now(timezone.utc),
                trip_times=precomputed_trip_times,
                soc_targets=precomputed_soc_targets,
                soc_caps=soc_caps,
            )

        _LOGGER.debug("Deficit propagation COMPLETE for %d trips", len(trips))

        return results

    # ── Daily Energy Calculation ────────────────────────────────

    async def async_get_kwh_needed_today(self) -> float:
        """Calcula la energía necesaria para hoy basado en los viajes."""
        today = datetime.now(timezone.utc).date()
        total_kwh = 0.0
        for trip in self._state.recurring_trips.values():
            if trip["activo"] and self._is_trip_today(trip, today):
                total_kwh += trip["kwh"]
        for trip in self._state.punctual_trips.values():
            if trip["estado"] == "pendiente" and self._is_trip_today(trip, today):
                total_kwh += trip["kwh"]
        return total_kwh

    async def async_get_hours_needed_today(self) -> int:
        """Calcula las horas necesarias para cargar hoy."""
        import math

        kwh_needed = await self.async_get_kwh_needed_today()
        charging_power = self._get_charging_power()
        return math.ceil(kwh_needed / charging_power) if charging_power > 0 else 0
