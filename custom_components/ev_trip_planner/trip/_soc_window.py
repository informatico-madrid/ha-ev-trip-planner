"""SOC window calculations — charging-window math.

Migrated from _soc_window_mixin.py. Plain class (no inheritance).
Uses dataclasses to keep method arity within SOLID limits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from homeassistant.util import dt as dt_util

from ..calculations import (
    DEFAULT_T_BASE,
    BatteryCapacity,
    calculate_deficit_propagation,
    calculate_dynamic_soc_limit,
)
from .state import TripManagerState

_LOGGER = logging.getLogger(__name__)

_DURACION_VIAJE_HORAS = 6


@dataclass(frozen=True)
class VentanaCargaParams:
    """Parameters for calcular_ventana_carga / calcular_ventana_carga_multitrip."""

    trips: List[Dict[str, Any]]
    soc_actual: float
    hora_regreso: Optional[datetime]
    charging_power_kw: float
    safety_margin_percent: float = 10.0


@dataclass(frozen=True)
class SOCInicioParams:
    """Parameters for calcular_soc_inicio_trips."""

    trips: List[Dict[str, Any]]
    soc_inicial: float
    hora_regreso: Optional[datetime]
    charging_power_kw: float
    battery_capacity_kwh: float = 50.0
    safety_margin_percent: float = 10.0


@dataclass(frozen=True)
class SOCWindowCalculator:
    """Parameters for calcular_hitos_soc."""

    trips: List[Dict[str, Any]]
    soc_inicial: float
    charging_power_kw: float
    battery_capacity_kwh: float = 50.0
    safety_margin_percent: float = 10.0
    soh_sensor_entity_id: Optional[str] = None
    t_base: float = DEFAULT_T_BASE


def _parse_hora_regreso(value: Optional[datetime | str]) -> Optional[datetime]:
    """Normalize hora_regreso to a tz-aware datetime, or None."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    else:
        parsed = value
    if parsed is not None and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class SOCWindow:
    """Charging-window calculations and SOC milestones."""

    def __init__(self, state: TripManagerState) -> None:
        """Initialize with shared state."""
        self._state = state

    # ── Public API ───────────────────────────────────────────────

    async def calcular_ventana_carga(
        self, params: VentanaCargaParams
    ) -> Dict[str, Any]:
        """Calcula la ventana de carga disponible para un viaje."""
        state = self._state
        parsed = _parse_hora_regreso(params.hora_regreso)

        next_trip = None
        if parsed is not None:
            next_trip = await state._navigator.async_get_next_trip_after(parsed)

        if parsed is not None and next_trip is None:
            return {
                "ventana_horas": 0,
                "kwh_necesarios": 0,
                "horas_carga_necesarias": 0,
                "inicio_ventana": None,
                "fin_ventana": None,
                "es_suficiente": True,
            }

        trip_departure_time = (
            self._state._soc._get_trip_time(params.trips[0]) if params.trips else None
        )
        if trip_departure_time is None and params.trips:
            dt_str = params.trips[0].get("datetime")
            if dt_str:
                trip_departure_time = self._state._soc._parse_trip_datetime(
                    dt_str, allow_none=True
                )

        if parsed is not None:
            inicio_ventana = parsed
        elif trip_departure_time is not None:
            inicio_ventana = trip_departure_time - timedelta(
                hours=_DURACION_VIAJE_HORAS
            )
        else:
            return {
                "ventana_horas": 0.0,
                "kwh_necesarios": 0.0,
                "horas_carga_necesarias": 0.0,
                "inicio_ventana": None,
                "fin_ventana": None,
                "es_suficiente": True,
            }

        fin_ventana = (
            trip_departure_time
            if trip_departure_time
            else dt_util.now() + timedelta(hours=_DURACION_VIAJE_HORAS)
        )
        delta = fin_ventana - inicio_ventana
        ventana_horas = max(0.0, delta.total_seconds() / 3600)

        vehicle_config = {
            "battery_capacity_kwh": 50.0,
            "charging_power_kw": params.charging_power_kw,
            "soc_current": params.soc_actual,
            "safety_margin_percent": params.safety_margin_percent,
        }
        # Get trip from params.trips[0] for single-call usage
        trip = params.trips[0] if params.trips else {}
        energia_info = await state._soc.async_calcular_energia_necesaria(
            trip, vehicle_config
        )
        kwh_necesarios = energia_info["energia_necesaria_kwh"]

        horas_carga_necesarias = (
            kwh_necesarios / params.charging_power_kw
            if params.charging_power_kw > 0
            else 0.0
        )
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
        self, params: VentanaCargaParams
    ) -> List[Dict[str, Any]]:
        """Calcula ventanas de carga para múltiples viajes en cadena."""
        if not params.trips:
            return []
        state = self._state
        parsed = _parse_hora_regreso(params.hora_regreso)

        sorted_trips: List[tuple[datetime, Dict[str, Any]]] = []
        for trip in params.trips:
            trip_time = self._state._soc._get_trip_time(trip)
            if trip_time:
                sorted_trips.append((trip_time, trip))
        sorted_trips.sort(key=lambda x: x[0])

        results: List[Dict[str, Any]] = []
        previous_arrival: Optional[datetime] = None

        for idx, (trip_departure_time, trip) in enumerate(sorted_trips):
            if idx == 0:
                window_start = (
                    parsed
                    if parsed is not None
                    else trip_departure_time - timedelta(hours=_DURACION_VIAJE_HORAS)
                )
            else:
                assert previous_arrival is not None
                window_start = previous_arrival

            trip_arrival = trip_departure_time + timedelta(hours=_DURACION_VIAJE_HORAS)
            delta = trip_arrival - window_start
            ventana_horas = max(0.0, delta.total_seconds() / 3600)

            vehicle_config = {
                "battery_capacity_kwh": 50.0,
                "charging_power_kw": params.charging_power_kw,
                "soc_current": params.soc_actual,
                "safety_margin_percent": params.safety_margin_percent,
            }
            energia_info = await state._soc.async_calcular_energia_necesaria(
                trip, vehicle_config
            )
            kwh_necesarios = energia_info["energia_necesaria_kwh"]

            horas_carga = (
                kwh_necesarios / params.charging_power_kw
                if params.charging_power_kw > 0
                else 0.0
            )
            es_suficiente = ventana_horas >= horas_carga

            results.append(
                {
                    "ventana_horas": round(ventana_horas, 2),
                    "kwh_necesarios": round(kwh_necesarios, 3),
                    "horas_carga_necesarias": round(horas_carga, 2),
                    "inicio_ventana": window_start,
                    "fin_ventana": trip_departure_time,
                    "es_suficiente": es_suficiente,
                    "trip": trip,
                }
            )
            previous_arrival = trip_arrival

        return results

    async def calcular_soc_inicio_trips(
        self, params: SOCInicioParams
    ) -> List[Dict[str, Any]]:
        """Calcula el SOC al inicio de cada viaje en cadena."""
        if not params.trips:
            return []

        ventanas = await self.calcular_ventana_carga_multitrip(
            VentanaCargaParams(
                trips=params.trips,
                soc_actual=params.soc_inicial,
                hora_regreso=params.hora_regreso,
                charging_power_kw=params.charging_power_kw,
                safety_margin_percent=params.safety_margin_percent,
            )
        )

        results: List[Dict[str, Any]] = []
        soc_actual = params.soc_inicial

        for ventana in ventanas:
            trip = ventana["trip"]
            kwh_necesarios = ventana["kwh_necesarios"]
            ventana_horas = ventana["ventana_horas"]

            soc_inicio = soc_actual
            if params.charging_power_kw > 0 and ventana_horas > 0:
                kwh_disponibles = params.charging_power_kw * ventana_horas
                kwh_a_cargar = min(kwh_necesarios, kwh_disponibles)
            else:
                kwh_a_cargar = 0.0

            soc_llegada = soc_actual
            if params.battery_capacity_kwh > 0:
                soc_llegada = min(
                    100.0,
                    soc_actual + (kwh_a_cargar / params.battery_capacity_kwh * 100),
                )

            results.append(
                {
                    "soc_inicio": round(soc_inicio, 2),
                    "trip": trip,
                    "arrival_soc": round(soc_llegada, 2),
                }
            )
            soc_actual = soc_llegada

        return results

    async def calcular_hitos_soc(
        self, params: SOCWindowCalculator
    ) -> List[Dict[str, Any]]:
        """Calcula los hitos SOC para múltiples viajes con propagación hacia atrás."""
        state = self._state
        if not params.trips:
            return []

        battery_cap = BatteryCapacity(
            nominal_capacity_kwh=params.battery_capacity_kwh,
            soh_sensor_entity_id=params.soh_sensor_entity_id,
        )
        real_capacity_kwh = battery_cap.get_capacity(state.hass)

        soc_inicio_info = await self.calcular_soc_inicio_trips(
            SOCInicioParams(
                trips=params.trips,
                soc_inicial=params.soc_inicial,
                hora_regreso=None,
                charging_power_kw=params.charging_power_kw,
                battery_capacity_kwh=params.battery_capacity_kwh,
                safety_margin_percent=params.safety_margin_percent,
            )
        )

        tasa_carga_soc = state._soc._calcular_tasa_carga_soc(
            params.charging_power_kw, params.battery_capacity_kwh
        )

        ventanas = await self.calcular_ventana_carga_multitrip(
            VentanaCargaParams(
                trips=params.trips,
                soc_actual=params.soc_inicial,
                hora_regreso=None,
                charging_power_kw=params.charging_power_kw,
                safety_margin_percent=params.safety_margin_percent,
            )
        )

        t_base = params.t_base
        soc_caps: Optional[List[float]] = [100.0] * len(params.trips)
        results: List[Dict[str, Any]] = []

        if params.trips:
            precomputed_trip_times = [
                state._soc._get_trip_time(trip) for trip in params.trips
            ]
            now_dt = datetime.now(timezone.utc)
            for i, trip in enumerate(params.trips):
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
                soc_caps[i] = calculate_dynamic_soc_limit(
                    t_hours, params.soc_inicial, real_capacity_kwh, t_base=t_base
                )

            precomputed_soc_targets = [
                state._soc._calcular_soc_objetivo_base(trip, real_capacity_kwh)
                for trip in params.trips
            ]
            results = calculate_deficit_propagation(
                trips=params.trips,
                soc_data=soc_inicio_info,
                windows=ventanas,
                tasa_carga_soc=tasa_carga_soc,
                battery_capacity_kwh=real_capacity_kwh,
                reference_dt=datetime.now(timezone.utc),
                trip_times=precomputed_trip_times,
                soc_targets=precomputed_soc_targets,
                soc_caps=soc_caps,
            )

        return results
