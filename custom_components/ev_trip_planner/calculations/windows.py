"""Charging window calculation functions extracted from calculations_orig.py.

Extracted from the legacy calculations.py god module as part of the
SOLID decomposition (Spec 3). These functions handle pure charging
window calculations for single and multi-trip scenarios.
"""

from __future__ import annotations

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
        "horas_carga_necesarias": round(horas_carga, 2),
        "alerta_tiempo_insuficiente": False,
        "horas_disponibles": 0.0,
        "margen_seguridad_aplicado": safety_margin_percent,
    }


def calculate_charging_window_pure(
    trip_departure_time: Optional[datetime],
    soc_actual: float,
    hora_regreso: Optional[datetime],
    charging_power_kw: float,
    energia_kwh: float,
    duration_hours: float = 6.0,
) -> Dict[str, Any]:
    """Pure charging window calculation without any async or hass.

    Computes the available charging window between return and departure.

    Args:
        trip_departure_time: When the trip departs (end of charging window)
        soc_actual: Current SOC percentage
        hora_regreso: When the vehicle returns (start of charging window)
        charging_power_kw: Charging power in kW
        energia_kwh: Energy needed for the trip in kWh
        duration_hours: Default trip duration in hours (default 6.0)

    Returns:
        Dictionary with:
            - ventana_horas: Hours available for charging
            - kwh_necesarios: Energy needed in kWh
            - horas_carga_necesarias: Hours needed to charge
            - inicio_ventana: Window start datetime
            - fin_ventana: Window end datetime (trip departure)
            - es_suficiente: True if window is sufficient
    """
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
    delta = fin_ventana - inicio_ventana
    ventana_horas = max(0.0, delta.total_seconds() / 3600)

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
        "horas_carga_necesarias": round(horas_carga_necesarias, 2),
        "inicio_ventana": inicio_ventana,
        "fin_ventana": fin_ventana,
        "es_suficiente": es_suficiente,
    }


def calculate_multi_trip_charging_windows(
    trips: List[Tuple[datetime, Dict[str, Any]]],
    soc_actual: float,
    hora_regreso: Optional[datetime],
    charging_power_kw: float,
    battery_capacity_kwh: float,
    duration_hours: float = 6.0,
    return_buffer_hours: float = 4.0,
    safety_margin_percent: float = DEFAULT_SAFETY_MARGIN,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Calculate charging windows for multiple chained trips.

    Each trip gets its own window. The first trip's charging window starts at
    max(hora_regreso, now) when hora_regreso is provided, or from now when
    hora_regreso is None. Subsequent trips start after the previous trip's
    departure plus the trip duration constant (duration_hours).

    For trip N (N > 0):
        window_start = previous_departure + duration_hours
        window_end = this_trip_departure

    Args:
        trips: List of (departure_time, trip_dict) tuples, sorted by time.
        soc_actual: Current SOC percentage
        hora_regreso: Physical return timestamp (may be in the past if car
            is already home). When None, the car is assumed to be home.
        charging_power_kw: Charging power in kW
        battery_capacity_kwh: Battery capacity in kWh
        duration_hours: Duration of each trip in hours (how long car is away)
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

    results = []
    previous_departure: datetime | None = None

    for idx, (trip_departure_time, trip) in enumerate(trips):
        # Ensure trip_departure_time is aware
        if (
            isinstance(trip_departure_time, datetime)
            and getattr(trip_departure_time, "tzinfo", None) is None
        ):
            trip_departure_time = _helpers._ensure_aware(trip_departure_time)
        # Determine window start
        window_start: datetime | None
        if idx == 0:
            now = now if now is not None else datetime.now(timezone.utc)
            if hora_regreso is not None:
                # Car is already home, start charging from now not from past hora_regreso
                # Only apply when trip is in the future (past trips keep original behavior)
                aware_departure = _helpers._ensure_aware(trip_departure_time)
                if aware_departure > now:
                    window_start = max(_helpers._ensure_aware(hora_regreso), now)
                else:
                    window_start = hora_regreso
            else:
                # trip_departure_time must not be None here
                assert trip_departure_time is not None
                # Car is assumed to be home (no return event detected).
                # Charging starts from now, not from departure - duration.
                window_start = now
        else:
            # Subsequent trips: window starts at previous departure + duration
            assert previous_departure is not None
            window_start = previous_departure + timedelta(hours=duration_hours)

        # Edge case: cap window_start at trip_departure_time if buffer exceeds gap
        # This handles the case where return_buffer pushes window_start past the deadline
        assert (
            trip_departure_time is not None
        )  # Enforced upstream by calculate_charging_window_pure
        if window_start is not None and _helpers._ensure_aware(
            window_start
        ) > _helpers._ensure_aware(trip_departure_time):
            window_start = trip_departure_time

        # Calculate ventana_horas
        # The charging window ends at trip departure (fin_ventana), not arrival.
        assert window_start is not None
        window_start_aware = _helpers._ensure_aware(window_start)
        trip_departure_aware = _helpers._ensure_aware(trip_departure_time)
        delta = trip_departure_aware - window_start_aware
        ventana_horas = max(0.0, delta.total_seconds() / 3600)

        # Calculate energy needed
        energia_info = calculate_energy_needed(
            trip,
            battery_capacity_kwh,
            soc_actual,
            charging_power_kw,
            safety_margin_percent=safety_margin_percent,
        )
        kwh_necesarios = energia_info["energia_necesaria_kwh"]

        # Calculate horas_carga_necesarias
        if charging_power_kw > 0:
            horas_carga_necesarias = kwh_necesarios / charging_power_kw
        else:
            horas_carga_necesarias = 0.0

        # Calculate es_suficiente
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

        # Update previous_departure for next iteration
        previous_departure = trip_departure_time

    return results
