"""Charging window calculation functions extracted from calculations_orig.py.

Extracted from the legacy calculations.py god module as part of the
SOLID decomposition (Spec 3). These functions handle pure charging
window calculations for single and multi-trip scenarios.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..const import DEFAULT_SAFETY_MARGIN
from ..utils import calcular_energia_kwh
from . import _helpers


def calculate_energy_needed(
    trip: Dict[str, Any],
    battery_capacity_kwh: float,
    soc_current: float,
    charging_power_kw: float,
    consumption_kwh_per_km: float = 0.15,
    safety_margin_percent: float = DEFAULT_SAFETY_MARGIN,
) -> Dict[str, Any]:
    # qg-accepted: arity=6 is the canonical energy API — all params are domain inputs
    """Calculates energy needed for a trip considering current SOC.

    Pure version of TripManager.async_calcular_energia_necesaria
    that does NOT use datetime.now() or hass.

    Args:
        trip: Dictionary with trip data (kwh or km, datetime, tipo, etc.)
        battery_capacity_kwh: Battery capacity in kWh
        soc_current: Current SOC in percentage (0-100)
        charging_power_kw: Charging power in kW
        consumption_kwh_per_km: Energy consumption in kWh/km (default 0.15)
        safety_margin_percent: Safety margin percentage (default from const)

    Returns:
        Dictionary with:
            - energia_necesaria_kwh: Energy to charge in kWh (includes safety margin)
            - horas_carga_necesarias: Hours needed to charge
            - alerta_tiempo_insuficiente: Always False (no datetime check)
            - horas_disponibles: Always 0.0 (no datetime check)
            - margen_seguridad_aplicado: The safety margin % used
    """
    # Guard: SOC must be a valid float - fallback to 0.0 if sensor unavailable
    if soc_current is None or not isinstance(soc_current, (int, float)):
        soc_current = 0.0

    # Calcular energía del viaje
    if "kwh" in trip:
        energia_viaje = trip.get("kwh", 0.0)
    else:
        distance_km = trip.get("km", 0.0)
        energia_viaje = calcular_energia_kwh(distance_km, consumption_kwh_per_km)

    # Energía mínima de seguridad que debe quedar DESPUÉS del viaje
    # (FIX: H1 - garantiza post-trip safety margin)
    energia_seguridad = (safety_margin_percent / 100.0) * battery_capacity_kwh

    # Energía total necesaria = viaje + margen seguridad post-viaje
    energia_objetivo = energia_viaje + energia_seguridad

    # Energía actual en batería
    energia_actual = (soc_current / 100.0) * battery_capacity_kwh

    # Proactive charging trigger: ensure capacity for trip chains even when
    # current SOC covers the trip target. Without this, future trips in a chain
    # would never trigger charging because current SOC covers each trip
    # individually. When energia_actual >= energia_objetivo, charge a minimum
    # (energia_viaje) to prepare for the next trip in the chain.
    if energia_actual >= energia_objetivo:
        # SOC covers full target but not enough headroom for trip chain.
        # Charge minimum = trip energy (ensures proactive preparation).
        energia_necesaria = energia_viaje
    else:
        # Below target: charge up to target as before
        energia_necesaria = max(0.0, energia_objetivo - energia_actual)

    # Clamp: no cargar más de la capacidad de la batería (FIX: H8)
    energia_necesaria = min(energia_necesaria, battery_capacity_kwh)

    # Safety margin already included in energia_objetivo - no multiplier needed
    energia_final = energia_necesaria

    if charging_power_kw > 0:
        horas_carga = energia_final / charging_power_kw
    else:
        horas_carga = 0

    return {
        "energia_necesaria_kwh": round(energia_final, 3),
        "horas_carga_necesarias": math.ceil(horas_carga) if horas_carga > 0 else 0,
        "alerta_tiempo_insuficiente": False,
        "horas_disponibles": 0.0,
        "margen_seguridad_aplicado": safety_margin_percent,
    }


@dataclass(frozen=True, kw_only=True)
class ChargingWindowPureParams:
    trip_departure_time: Optional[datetime]
    soc_actual: float
    hora_regreso: Optional[datetime]
    charging_power_kw: float
    energia_kwh: float
    duration_hours: float = 6.0


def calculate_charging_window_pure(params: ChargingWindowPureParams) -> Dict[str, Any]:
    """Pure charging window calculation without any async or hass.

    Computes the available charging window between return and departure.

    Args:
        params: Encapsulated charging window parameters.

    Returns:
        Dictionary with:
            - ventana_horas: Hours available for charging
            - kwh_necesarios: Energy needed in kWh
            - horas_carga_necesarias: Hours needed to charge
            - inicio_ventana: Window start datetime
            - fin_ventana: Window end datetime (trip departure)
            - es_suficiente: True if window is sufficient
    """
    trip_departure_time = params.trip_departure_time
    soc_actual = params.soc_actual
    hora_regreso = params.hora_regreso
    charging_power_kw = params.charging_power_kw
    energia_kwh = params.energia_kwh
    duration_hours = params.duration_hours

    # Ensure all datetime inputs are timezone-aware (treat naive as UTC)
    if hora_regreso is not None and getattr(hora_regreso, "tzinfo", None) is None:
        hora_regreso = hora_regreso.replace(tzinfo=timezone.utc)
    if (
        trip_departure_time is not None
        and getattr(trip_departure_time, "tzinfo", None) is None
    ):
        trip_departure_time = trip_departure_time.replace(tzinfo=timezone.utc)

    # Determine window start
    if hora_regreso is not None:
        inicio_ventana = hora_regreso
    elif trip_departure_time is not None:
        inicio_ventana = trip_departure_time - timedelta(hours=duration_hours)
    else:
        return {
            "ventana_horas": 0.0,
            "kwh_necesarios": 0.0,
            "horas_carga_necesarias": 0.0,
            "inicio_ventana": None,
            "fin_ventana": None,
            "es_suficiente": True,
        }

    # Determine window end
    if trip_departure_time is not None:
        fin_ventana = trip_departure_time
    else:
        fin_ventana = inicio_ventana + timedelta(hours=duration_hours)

    # Calculate ventana_horas
    ventana_horas = max(0.0, _helpers.compute_hours_until(fin_ventana, inicio_ventana))

    # kwh_necesarios
    kwh_necesarios = energia_kwh

    # Calculate horas_carga_necesarias
    if charging_power_kw > 0:
        horas_carga_necesarias = kwh_necesarios / charging_power_kw
    else:
        horas_carga_necesarias = 0.0

    # Calculate es_suficiente
    es_suficiente = ventana_horas >= horas_carga_necesarias

    return {
        "ventana_horas": round(ventana_horas, 2),
        "kwh_necesarios": round(kwh_necesarios, 3),
        "horas_carga_necesarias": math.ceil(horas_carga_necesarias)
        if horas_carga_necesarias > 0
        else 0,
        "inicio_ventana": inicio_ventana,
        "fin_ventana": fin_ventana,
        "es_suficiente": es_suficiente,
    }


def _compute_first_trip_window_start(
    trip_departure_time: datetime,
    hora_regreso: datetime | None,
    now: datetime,
) -> datetime:
    """Compute the window start for the first trip in a chain.

    When the car is already home (hora_regreso provided), start charging from
    max(hora_regreso, now) if the trip is in the future. Otherwise use
    hora_regreso directly (past trips keep original behavior). When no
    hora_regreso is provided, the car is assumed to be home and charging
    starts from now.

    Args:
        trip_departure_time: When the trip departs.
        hora_regreso: Physical return timestamp, or None.
        now: Current time (aware).

    Returns:
        The computed window start datetime (tz-aware).
    """
    if hora_regreso is not None:
        aware_departure = _helpers._ensure_aware(trip_departure_time)
        if aware_departure > now:
            return max(_helpers._ensure_aware(hora_regreso), now)
        return hora_regreso
    return now


# CC-11-ACCEPTED: cc=16 is inherent to multi-trip chain logic — each iteration
# must handle: timezone awareness, window-start dispatch (first vs subsequent),
# buffer overflow capping, energy calculation, and sufficiency check. These are
# distinct domain steps with no natural grouping that would reduce cc below 11.
def calculate_multi_trip_charging_windows(
    trips: List[Tuple[datetime, Dict[str, Any]]],
    soc_actual: float,
    hora_regreso: Optional[datetime],
    charging_power_kw: float,
    battery_capacity_kwh: float,
    return_buffer_hours: float = 4.0,
    safety_margin_percent: float = DEFAULT_SAFETY_MARGIN,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Calculate charging windows for multiple chained trips.

    Each trip gets its own window. The first trip's charging window starts at
    max(hora_regreso, now) when hora_regreso is provided, or from now when
    hora_regreso is None. Subsequent trips start after the previous trip's
    departure plus the return buffer (return_buffer_hours).

    For trip N (N > 0):
        window_start = previous_departure + return_buffer_hours
        window_end = this_trip_departure

    Args:
        trips: List of (departure_time, trip_dict) tuples, sorted by time.
        soc_actual: Current SOC percentage
        hora_regreso: Physical return timestamp (may be in the past if car
            is already home). When None, the car is assumed to be home.
        charging_power_kw: Charging power in kW
        battery_capacity_kwh: Battery capacity in kWh
        return_buffer_hours: Gap in hours between when a trip ends and the
            next trip begins
        safety_margin_percent: Safety margin percentage for energy calculations

    Returns:
        List of per-trip charging window dicts with keys:
            ventana_horas, kwh_necesarios, horas_carga_necesarias,
            inicio_ventana, fin_ventana, es_suficiente.
    """
    if not trips:
        return []

    results: list[Dict[str, Any]] = []
    previous_departure: datetime | None = None
    loop_now: datetime | None = None

    for idx, (trip_departure_time, trip) in enumerate(trips):
        # Ensure trip_departure_time is aware
        if (
            isinstance(trip_departure_time, datetime)
            and getattr(trip_departure_time, "tzinfo", None) is None
        ):
            trip_departure_time = _helpers._ensure_aware(trip_departure_time)

        window_start = _compute_window_start(
            WindowStartParams(
                idx=idx,
                trip_departure_time=trip_departure_time,
                hora_regreso=hora_regreso,
                return_buffer_hours=return_buffer_hours,
                loop_now=loop_now,
                prev_departure=previous_departure,
                now=now,
            )
        )

        # Edge case: cap window_start at trip_departure_time if buffer exceeds gap
        if _helpers._ensure_aware(window_start) > _helpers._ensure_aware(
            trip_departure_time
        ):
            window_start = trip_departure_time

        ventana_horas = _compute_window_hours(window_start, trip_departure_time)

        energia_info = calculate_energy_needed(
            trip,
            battery_capacity_kwh,
            soc_actual,
            charging_power_kw,
            safety_margin_percent=safety_margin_percent,
        )
        kwh_necesarios = energia_info["energia_necesaria_kwh"]
        horas_carga_necesarias = (
            kwh_necesarios / charging_power_kw if charging_power_kw > 0 else 0.0
        )
        es_suficiente = ventana_horas >= horas_carga_necesarias

        results.append(
            {
                "ventana_horas": round(ventana_horas, 2),
                "kwh_necesarios": round(kwh_necesarios, 3),
                "horas_carga_necesarias": math.ceil(horas_carga_necesarias)
                if horas_carga_necesarias > 0
                else 0,
                "inicio_ventana": window_start,
                "fin_ventana": trip_departure_time,
                "es_suficiente": es_suficiente,
                "trip": trip,
            }
        )
        previous_departure = trip_departure_time

    return results


@dataclass(frozen=True, kw_only=True)
class WindowStartParams:
    """Parameters for computing a trip's charging window start.

    Frozen to prevent accidental mutation. The caller tracks `loop_now` as a
    separate local variable in the loop — it is passed in via this object but
    is NOT read back from it (the dataclass is immutable).
    """

    idx: int
    trip_departure_time: datetime
    hora_regreso: datetime | None
    return_buffer_hours: float
    loop_now: datetime | None
    prev_departure: datetime | None
    now: datetime | None


def _compute_window_start(params: WindowStartParams) -> datetime:
    """Compute the window start datetime for a trip in the chain.

    Args:
        params: Named parameters for window start computation.

    Returns:
        The computed window start datetime.
    """
    if params.idx == 0:
        loop_now = params.loop_now
        if loop_now is None:
            loop_now = params.now or datetime.now(timezone.utc)
        window_start = _compute_first_trip_window_start(
            params.trip_departure_time, params.hora_regreso, loop_now
        )
        return window_start
    assert params.prev_departure is not None
    return params.prev_departure + timedelta(hours=params.return_buffer_hours)


def _compute_window_hours(
    window_start: datetime,
    trip_departure_time: datetime,
) -> float:
    """Compute available charging window hours.

    Args:
        window_start: Window start datetime.
        trip_departure_time: Window end (trip departure) datetime.

    Returns:
        Available window hours (non-negative).
    """
    window_start_aware = _helpers._ensure_aware(window_start)
    trip_departure_aware = _helpers._ensure_aware(trip_departure_time)
    return max(
        0.0, _helpers.compute_hours_until(trip_departure_aware, window_start_aware)
    )


def build_deferrable_matrix_row(
    horizon_hours: int,
    charging_power_kw: float,
    hours_needed: float,
    end_timestep: int,
) -> list[float]:
    """Build a single-row p_deferrable_matrix with charging slots at END of window.

    The charging slots are placed at the END of the window (just before trip
    departure), not spread across the entire window. This follows the rule:
    "La carga efectiva se compacta al final de la ventana".

    Args:
        horizon_hours: Total number of slots (e.g., 168 for 7 days).
        charging_power_kw: Charging power in kW.
        hours_needed: Number of charging hours needed.
        end_timestep: Window end (trip departure) as timestep index.

    Returns:
        List of floats with power_watts in the last 'hours_needed' slots,
        zeros elsewhere.
    """
    row = [0.0] * horizon_hours
    if hours_needed <= 0:
        return row

    # Calculate the actual charging window: last 'hours_needed' slots before departure
    # Use ceil to ensure we fill the correct number of slots (handles float precision)
    hours_ceil = math.ceil(hours_needed)
    charging_start = max(0, end_timestep - hours_ceil)
    charging_end = min(end_timestep, horizon_hours)
    power_watts = _helpers.kw_to_watts(charging_power_kw)

    for t in range(charging_start, charging_end):
        if 0 <= t < horizon_hours:
            row[t] = power_watts

    return row
