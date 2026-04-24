"""Pure calculation functions extracted from trip_manager.py for testability.

These functions contain no async, no hass, and no self — they are
100% synchronous and can be tested with simple @pytest.mark.parametrize
without any mocks.

All datetime-sensitive functions take an explicit reference_dt parameter
instead of using datetime.now(), enabling deterministic testing.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .const import DEFAULT_SAFETY_MARGIN, DEFAULT_SOC_BUFFER_PERCENT
from .utils import calcular_energia_kwh

# Public API: list of exported functions
__all__ = [
    "calculate_day_index",
    "calculate_trip_time",
    "calculate_charging_rate",
    "calculate_soc_target",
    "determine_charging_need",
    "calculate_energy_needed",
    "calculate_charging_window_pure",
    "calculate_multi_trip_charging_windows",
    "calculate_soc_at_trip_starts",
    "calculate_deficit_propagation",
    "calculate_power_profile_from_trips",
    "calculate_deferrable_parameters",
    "generate_deferrable_schedule_from_trips",
]

_LOGGER = logging.getLogger(__name__)


def _ensure_aware(dt: datetime) -> datetime:
    """Convert naive datetime to aware (UTC) if needed."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

# Days of week in Spanish (lowercase) — mirrors trip_manager.DAYS_OF_WEEK
DAYS_OF_WEEK = (
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
)


# =============================================================================
# PURE: Day index calculation
# =============================================================================


def calculate_day_index(day_name: str) -> int:
    """Obtiene el índice del día de la semana (0=lunes, 6=domingo).

    Args:
        day_name: Nombre del día en español (case-insensitive) o dígito 0-6.

    Returns:
        Índice del día de la semana (0=lunes).
    """
    day_lower = day_name.lower().strip()

    # Handle numeric day values (0-6)
    if day_lower.isdigit():
        day_index = int(day_lower)
        if 0 <= day_index < len(DAYS_OF_WEEK):
            return day_index
        return 0  # Monday on invalid index

    # Try direct match first
    try:
        return DAYS_OF_WEEK.index(day_lower)
    except ValueError:
        pass

    # If still not found, default to Monday (index 0)
    return 0


# =============================================================================
# PURE: Trip time calculation
# =============================================================================


def calculate_trip_time(
    trip_tipo: str,
    hora: Optional[str],
    dia_semana: Optional[str],
    datetime_str: Optional[str],
    reference_dt: datetime,
) -> Optional[datetime]:
    """Calculates the datetime of a trip given a reference time.

    Pure version of TripManager._get_trip_time that accepts reference_dt
    instead of using datetime.now().

    Args:
        trip_tipo: TRIP_TYPE_RECURRING or TRIP_TYPE_PUNCTUAL
        hora: Departure time as "HH:MM" string (for recurring trips)
        dia_semana: Day of week name (for recurring trips)
        datetime_str: ISO datetime string (for punctual trips)
        reference_dt: Reference datetime for computing the next occurrence

    Returns:
        Calculated trip datetime, or None if insufficient data.
    """
    from .const import TRIP_TYPE_PUNCTUAL, TRIP_TYPE_RECURRING

    if trip_tipo == TRIP_TYPE_RECURRING:
        if not hora:
            return None
        now = reference_dt
        today = now.date()
        day_of_week = now.weekday()
        target_day = calculate_day_index(dia_semana or "lunes")
        days_ahead = (target_day - day_of_week) % 7
        try:
            hour = int(hora.split(":")[0])
        except (ValueError, IndexError):
            hour = 0
        if days_ahead == 0 and now.hour > hour:
            days_ahead = 7
        return datetime.combine(
            today + timedelta(days=days_ahead),
            datetime.strptime(hora, "%H:%M").time(),
        ).replace(tzinfo=timezone.utc)
    elif trip_tipo == TRIP_TYPE_PUNCTUAL:
        if not datetime_str:
            return None
        # Handle both with and without seconds (isoformat produces HH:MM:SS)
        try:
            # Try without seconds first (original format)
            return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return None


# =============================================================================
# PURE: SOC calculations
# =============================================================================


def calculate_charging_rate(
    charging_power_kw: float, battery_capacity_kwh: float = 50.0
) -> float:
    """Calcula la tasa de carga en % SOC/hora.

    Formula: charging_power_kw / battery_capacity_kwh * 100 = % SOC/hour

    Args:
        charging_power_kw: Potencia de carga en kW
        battery_capacity_kwh: Capacidad de la bateria en kWh (default 50.0)

    Returns:
        Tasa de carga en % SOC por hora
    """
    if battery_capacity_kwh <= 0:
        return 0.0
    return (charging_power_kw / battery_capacity_kwh) * 100


def calculate_soc_target(
    trip: Dict[str, Any],
    battery_capacity_kwh: float,
    consumption_kwh_per_km: float = 0.15,
    soc_buffer_percent: float = DEFAULT_SOC_BUFFER_PERCENT,
) -> float:
    """Calculates the base SOC target percentage for a trip.

    Pure version of TripManager._calcular_soc_objetivo_base.

    Args:
        trip: Dictionary with trip data (kwh or km, consumo)
        battery_capacity_kwh: Battery capacity in kWh
        consumption_kwh_per_km: Energy consumption in kWh/km (default 0.15)
        soc_buffer_percent: Buffer to add to target SOC (default from const)

    Returns:
        Base SOC target percentage for the trip (energy + buffer)
    """
    # Calculate energy needed for trip
    if "kwh" in trip and trip["kwh"]:
        energia_kwh = trip["kwh"]
    else:
        distance_km = trip.get("km", 0.0)
        energia_kwh = calcular_energia_kwh(distance_km, consumption_kwh_per_km)

    # Convert to SOC percentage
    if battery_capacity_kwh > 0:
        energia_soc = (energia_kwh / battery_capacity_kwh) * 100
    else:
        energia_soc = 0.0

    # Add buffer
    soc_objetivo_base = energia_soc + soc_buffer_percent
    return soc_objetivo_base


@dataclass(frozen=True)
class ChargingDecision:
    """Immutable charging decision for a single trip.
    
    Encapsulates the decision logic for whether and how much to charge,
    extracted from EMHASSAdapter._populate_per_trip_cache_entry for SOLID SRP.
    """
    trip_id: str
    kwh_needed: float          # Energy to charge (0 = no charge needed)
    def_total_hours: int        # Hours of charging needed
    power_watts: float          # Charging power (0 = no charge)
    needs_charging: bool        # Whether charging is needed


def determine_charging_need(
    trip: Dict[str, Any],
    soc_current: float,
    battery_capacity_kwh: float,
    charging_power_kw: float,
    safety_margin_percent: float = DEFAULT_SAFETY_MARGIN,
) -> ChargingDecision:
    """Pure function: determine if and how much to charge for a trip.
    
    Uses calculate_energy_needed() internally (which guarantees post-trip safety margin).
    
    Args:
        trip: Dictionary with trip data (kwh or km, datetime, tipo, etc.)
        soc_current: Current SOC in percentage (0-100)
        battery_capacity_kwh: Battery capacity in kWh
        charging_power_kw: Charging power in kW
        safety_margin_percent: Safety margin percentage (default from const)
    
    Returns:
        ChargingDecision with kwh_needed=0 if SOC is sufficient.
    """
    trip_id = trip.get("id", "unknown")
    
    energia_info = calculate_energy_needed(
        trip, battery_capacity_kwh, soc_current, charging_power_kw,
        safety_margin_percent=safety_margin_percent,
    )
    kwh_needed = energia_info["energia_necesaria_kwh"]
    
    needs_charging = kwh_needed > 0
    
    if needs_charging:
        total_hours = int(math.ceil(kwh_needed / charging_power_kw)) if charging_power_kw > 0 else 0
        power_watts = charging_power_kw * 1000
    else:
        total_hours = 0
        power_watts = 0.0
    
    return ChargingDecision(
        trip_id=trip_id,
        kwh_needed=kwh_needed,
        def_total_hours=total_hours,
        power_watts=power_watts,
        needs_charging=needs_charging,
    )


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

    # Energía a cargar = lo que falta para llegar al objetivo
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


# =============================================================================
# PURE: Charging window calculation
# =============================================================================


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
    if trip_departure_time is not None and getattr(trip_departure_time, "tzinfo", None) is None:
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


# =============================================================================
# PURE: Multi-trip charging windows
# =============================================================================


def calculate_multi_trip_charging_windows(
    trips: List[Tuple[datetime, Dict[str, Any]]],
    soc_actual: float,
    hora_regreso: Optional[datetime],
    charging_power_kw: float,
    battery_capacity_kwh: float,
    duration_hours: float = 6.0,
    return_buffer_hours: float = 4.0,
    safety_margin_percent: float = DEFAULT_SAFETY_MARGIN,
) -> List[Dict[str, Any]]:
    """Calculate charging windows for multiple chained trips.

    Each trip gets its own window. The first trip starts at hora_regreso.
    Subsequent trips start after the previous trip ends plus a buffer gap.

    Args:
        trips: List of (departure_time, trip_dict) tuples, sorted by time.
        soc_actual: Current SOC percentage
        hora_regreso: Return time for the first trip
        charging_power_kw: Charging power in kW
        battery_capacity_kwh: Battery capacity in kWh
        duration_hours: Duration of each trip in hours (how long car is away)
        return_buffer_hours: Gap in hours between when a trip ends and the next trip begins
        safety_margin_percent: Safety margin percentage for energy calculations

    Returns:
        List of charging window dicts (one per trip).
    """
    if not trips:
        return []

    results = []
    previous_arrival: datetime | None = None

    for idx, (trip_departure_time, trip) in enumerate(trips):
        # Ensure trip_departure_time is aware
        if isinstance(trip_departure_time, datetime) and getattr(trip_departure_time, "tzinfo", None) is None:
            trip_departure_time = _ensure_aware(trip_departure_time)
        # Determine window start
        window_start: datetime | None
        if idx == 0:
            if hora_regreso is not None:
                window_start = hora_regreso
            else:
                # trip_departure_time must not be None here
                assert trip_departure_time is not None
                window_start = trip_departure_time - timedelta(hours=duration_hours)
        else:
            window_start = previous_arrival

        # Edge case: cap window_start at trip_departure_time if buffer exceeds gap
        # This handles the case where return_buffer pushes window_start past the deadline
        assert trip_departure_time is not None
        if window_start is not None and _ensure_aware(window_start) > _ensure_aware(trip_departure_time):
            window_start = trip_departure_time

        # Calculate arrival for this trip (departure + duration)
        assert trip_departure_time is not None
        trip_arrival = trip_departure_time + timedelta(hours=duration_hours)

        # Calculate ventana_horas
        # Ensure window_start is not None for the calculation
        assert window_start is not None
        window_start_aware = _ensure_aware(window_start)
        trip_arrival_aware = _ensure_aware(trip_arrival)
        delta = trip_arrival_aware - window_start_aware
        ventana_horas = max(0.0, delta.total_seconds() / 3600)

        # Calculate energy needed
        energia_info = calculate_energy_needed(
            trip, battery_capacity_kwh, soc_actual, charging_power_kw,
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

        results.append({
            "ventana_horas": round(ventana_horas, 2),
            "kwh_necesarios": round(kwh_necesarios, 3),
            "horas_carga_necesarias": round(horas_carga_necesarias, 2),
            "inicio_ventana": window_start,
            "fin_ventana": trip_departure_time,
            "es_suficiente": es_suficiente,
            "trip": trip,
        })

        # Update previous_arrival for next iteration (trip arrival + buffer gap)
        previous_arrival = _ensure_aware(trip_arrival) + timedelta(hours=return_buffer_hours)

    return results


def calculate_hours_deficit_propagation(
    windows: List[Dict[str, Any]],
    battery_capacity_kwh: float,
    def_total_hours: List[float] | None = None,
) -> List[Dict[str, Any]]:
    """Walk backward from last trip to first, propagating unmet charging hours to earlier trips with spare capacity.

    For each trip (last to first):
    1. Calculate own deficit: hours needed minus hours available in window
    2. Calculate spare capacity: available hours minus assigned def_total_hours
    3. Absorb deficit from carrier using available spare
    4. Propagate remaining deficit forward to previous trip

    Args:
        windows: List of window dicts from calculate_multi_trip_charging_windows().
            Must contain: ventana_horas, horas_carga_necesarias.
        battery_capacity_kwh: Battery capacity (for reference, not used in calculation).
        def_total_hours: Optional list of total charging hours per trip.
            If None, defaults to horas_carga_necesarias from each window.

    Returns:
        List of enriched window dicts with additional keys:
        - deficit_hours_propagated: hours absorbed from next trip (float, 2dp)
        - deficit_hours_to_propagate: remaining deficit (float, 2dp)
        - adjusted_def_total_hours: original def_total_hours + absorbed (float, 2dp)
    """
    if not windows:
        return []

    N = len(windows)
    defaults = [w["horas_carga_necesarias"] for w in windows]
    if def_total_hours is None:
        def_total_hours = defaults

    results: List[Dict[str, Any]] = []
    deficit_carrier: float = 0.0

    for i in range(N - 1, -1, -1):
        ventana = windows[i]["ventana_horas"]
        horas_carga = windows[i]["horas_carga_necesarias"]
        original_def_total = def_total_hours[i]
        spare = max(0.0, ventana - original_def_total)

        # How much can this trip absorb from the deficit carrier?
        absorbed = min(deficit_carrier, spare)
        deficit_carrier -= absorbed

        # Own deficit: does this trip need more than its window allows?
        own_deficit = max(0.0, horas_carga - ventana)
        deficit_carrier += own_deficit

        # Build result
        result = dict(windows[i])
        result["deficit_hours_propagated"] = round(absorbed, 2)
        result["deficit_hours_to_propagate"] = round(deficit_carrier, 2)
        result["adjusted_def_total_hours"] = round(original_def_total + absorbed, 2)
        results.append(result)

    return results


# =============================================================================
# PURE: SOC at start of trips
# =============================================================================


def calculate_soc_at_trip_starts(
    trips: List[Dict[str, Any]],
    soc_inicial: float,
    windows: List[Dict[str, Any]],
    charging_power_kw: float,
    battery_capacity_kwh: float,
) -> List[Dict[str, Any]]:
    """Calculate SOC at the start of each trip in a chain.

    Args:
        trips: List of trip dicts (in departure time order)
        soc_inicial: Initial SOC at start of chain
        windows: List of charging windows (from calculate_multi_trip_charging_windows)
        charging_power_kw: Charging power in kW
        battery_capacity_kwh: Battery capacity in kWh

    Returns:
        List of dicts with soc_inicio, trip, arrival_soc for each trip.
    """
    if not trips or not windows:
        return []

    results = []
    soc_actual = soc_inicial

    for idx, ventana in enumerate(windows):
        trip = ventana.get("trip", trips[idx]) if idx < len(trips) else trips[-1]
        ventana_horas = ventana["ventana_horas"]
        kwh_necesarios = ventana["kwh_necesarios"]

        # SOC at start of this trip
        soc_inicio = soc_actual

        # Calculate energy that can be charged in window
        if charging_power_kw > 0 and ventana_horas > 0:
            kwh_disponibles = charging_power_kw * ventana_horas
            kwh_a_cargar = min(kwh_necesarios, kwh_disponibles)
        else:
            kwh_a_cargar = 0.0

        # Calculate SOC after charging (at arrival)
        if battery_capacity_kwh > 0:
            soc_llegada = soc_actual + (kwh_a_cargar / battery_capacity_kwh * 100)
            soc_llegada = min(100.0, soc_llegada)  # Cap at 100%
        else:
            soc_llegada = soc_actual

        results.append({
            "soc_inicio": round(soc_inicio, 2),
            "trip": trip,
            "arrival_soc": round(soc_llegada, 2),
        })

        # Update SOC for next trip
        soc_actual = soc_llegada

    return results


# =============================================================================
# PURE: Deficit propagation (core of calcular_hitos_soc)
# =============================================================================


def calculate_deficit_propagation(
    trips: List[Dict[str, Any]],
    soc_data: List[Dict[str, Any]],
    windows: List[Dict[str, Any]],
    tasa_carga_soc: float,
    battery_capacity_kwh: float,
    reference_dt: datetime,
    trip_times: Optional[List[Optional[datetime]]] = None,
    soc_targets: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    """Calculate SOC milestones with backward deficit propagation.

    This is the pure core of calcular_hitos_soc. It implements the
    deficit detection and propagation algorithm:
    1. Sorts trips by departure time (earliest first)
    2. Iterates in REVERSE order (last trip to first)
    3. For each trip: if soc_inicio + capacidad_carga < soc_objetivo,
       the deficit is propagated to the previous trip
    4. Returns adjusted SOC targets and accumulated deficits

    Args:
        trips: List of trip dicts (unsorted or sorted by caller)
        soc_data: List of soc_inicio data dicts (one per trip, in departure order)
        windows: List of charging windows (one per trip, in departure order)
        tasa_carga_soc: Charging rate in % SOC/hour
        battery_capacity_kwh: Battery capacity in kWh
        reference_dt: Reference datetime for trip time calculations

    Returns:
        List of SOCMilestoneResult dicts with soc_objetivo adjusted and
        deficit_acumulado for each trip.
    """
    if not trips or not soc_data or not windows:
        return []

    # Sort trips by departure time and create bidirectional index mapping
    sorted_trips_with_times: List[Tuple[datetime, int, Dict[str, Any]]] = []
    for idx, trip in enumerate(trips):
        if trip_times and idx < len(trip_times) and trip_times[idx] is not None:
            # Use pre-computed trip times (from caller, e.g. mocked in tests)
            trip_time = trip_times[idx]
        else:
            # Compute trip time from trip data
            trip_tipo: Optional[str] = trip.get("tipo")
            hora: Optional[str] = trip.get("hora")
            dia_semana: Optional[str] = trip.get("dia_semana")
            datetime_str: Optional[str] = trip.get("datetime")
            # trip_tipo must be a valid string for calculate_trip_time
            assert trip_tipo is not None
            trip_time = calculate_trip_time(trip_tipo, hora, dia_semana, datetime_str, reference_dt)
        if trip_time:
            sorted_trips_with_times.append((trip_time, idx, trip))

    if not sorted_trips_with_times:
        return []

    sorted_trips_with_times.sort(key=lambda x: x[0])  # Sort by time ascending

    # Map original indices to ordered positions and vice versa
    idx_to_ordered: Dict[int, int] = {}
    ordered_to_idx: Dict[int, int] = {}
    for ordered_idx, (_, original_idx, _) in enumerate(sorted_trips_with_times):
        idx_to_ordered[original_idx] = ordered_idx
        ordered_to_idx[ordered_idx] = original_idx

    # Initialize deficit_acumulado for each trip
    # Deficit propagates to the previous trip (in temporal order)
    deficits = [0.0] * len(trips)

    # ITERATE IN REVERSE ORDER (last trip to first)
    for ordered_idx in range(len(trips) - 1, -1, -1):
        _orig_idx = ordered_to_idx.get(ordered_idx)
        if _orig_idx is None:
            continue
        original_idx = _orig_idx

        # Get data in ordered position
        soc_data_item = soc_data[ordered_idx]
        ventana = windows[ordered_idx]
        trip = trips[ordered_idx]

        soc_inicio = soc_data_item["soc_inicio"]
        ventana_horas = ventana["ventana_horas"]

        # Calculate base soc_objetivo for this trip
        # Use provided soc_targets if available (allows caller to pre-compute with mocks)
        if soc_targets and original_idx < len(soc_targets):
            soc_objetivo = soc_targets[original_idx]
        else:
            soc_objetivo = calculate_soc_target(trip, battery_capacity_kwh)

        # Add propagated deficit
        soc_objetivo_ajustado = soc_objetivo + deficits[original_idx]

        # Calculate available charging capacity
        capacidad_carga = tasa_carga_soc * ventana_horas

        # Check for deficit
        if soc_inicio + capacidad_carga < soc_objetivo_ajustado:
            deficit = soc_objetivo_ajustado - (soc_inicio + capacidad_carga)

            # Propagate deficit to previous trip (in temporal order)
            if ordered_idx > 0:
                prev_original_idx = ordered_to_idx.get(ordered_idx - 1)
                if prev_original_idx is not None:
                    deficits[prev_original_idx] += deficit

            # Accumulate deficit for this trip
            deficits[original_idx] += deficit

    # Build final results
    results: List[Dict[str, Any]] = []
    for ordered_idx in range(len(trips)):
        _orig_idx = ordered_to_idx.get(ordered_idx)
        if _orig_idx is None:
            continue
        original_idx = _orig_idx

        trip = trips[original_idx]
        soc_data_item = soc_data[ordered_idx]
        ventana = windows[ordered_idx]

        # Use provided soc_targets if available (allows caller to pre-compute with mocks)
        if soc_targets and original_idx < len(soc_targets):
            soc_objetivo = soc_targets[original_idx]
        else:
            soc_objetivo = calculate_soc_target(trip, battery_capacity_kwh)
        soc_objetivo_ajustado = soc_objetivo + deficits[original_idx]

        soc_inicio = soc_data_item["soc_inicio"]
        kwh_necesarios = (soc_objetivo_ajustado - soc_inicio) * battery_capacity_kwh / 100

        results.append({
            "trip_id": trip.get("id", f"trip_{original_idx}"),
            "soc_objetivo": round(soc_objetivo_ajustado, 2),
            "kwh_necesarios": round(max(0.0, kwh_necesarios), 3),
            "deficit_acumulado": round(deficits[original_idx], 2),
            "ventana_carga": {
                "ventana_horas": ventana["ventana_horas"],
                "kwh_necesarios": ventana["kwh_necesarios"],
                "horas_carga_necesarias": ventana["horas_carga_necesarias"],
                "inicio_ventana": ventana["inicio_ventana"],
                "fin_ventana": ventana["fin_ventana"],
                "es_suficiente": ventana["es_suficiente"],
            },
        })

    return results


# =============================================================================
# PURE: Power profile calculation (core of async_generate_power_profile)
# =============================================================================


def calculate_next_recurring_datetime(day: int | str, time_str: str, reference_dt: Optional[datetime] = None) -> Optional[datetime]:
    """Calculate the next occurrence of a recurring trip.

    Args:
        day: Day of week (0=Sunday, 6=Saturday) - JavaScript getDay() format.
             Can be int or string (will be converted to int).
        time_str: Time in HH:MM format.
        reference_dt: Reference datetime for calculation (default datetime.now()).

    Returns:
        datetime of next occurrence, or None if inputs are invalid.
    """
    if reference_dt is None:
        reference_dt = datetime.now()

    if day is None or time_str is None:
        return None

    # Convert day to int if it's a string (E2E tests pass day as string)
    try:
        day = int(day)
    except (ValueError, TypeError):
        return None

    try:
        hour, minute = map(int, time_str.split(':'))
    except (ValueError, AttributeError):
        return None

    # Create candidate datetime for today
    candidate = reference_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # Get current day of week (0=Sunday to match JavaScript getDay())
    # isoweekday() returns 1=Monday, 7=Sunday, so we convert
    current_day = reference_dt.isoweekday() % 7

    # Calculate days ahead
    days_ahead = (day - current_day) % 7

    # If the time for today has passed, move to next week
    if days_ahead == 0 and candidate < reference_dt:
        days_ahead = 7

    # Add days to reach the target day
    return candidate + timedelta(days=days_ahead)


def calculate_power_profile_from_trips(
    trips: List[Dict[str, Any]],
    power_kw: float,
    horizon: int = 168,
    reference_dt: Optional[datetime] = None,
    soc_current: Optional[float] = None,
    battery_capacity_kwh: Optional[float] = None,
    safety_margin_percent: float = DEFAULT_SAFETY_MARGIN,
) -> List[float]:
    """Calculate power profile from trips (pure version).

    Each trip creates a charging window before its deadline.
    Power is distributed across the hours leading up to the deadline.

    Args:
        trips: List of trip dicts with 'datetime' and 'kwh' or 'km' keys.
               Recurring trips use 'day' (0=Sunday, 6=Saturday) and 'time' (HH:MM).
               Trips without datetime or day/time are skipped.
        power_kw: Charging power in kilowatts.
        horizon: Number of hours in the profile (default 168 = 1 week).
        reference_dt: Reference datetime for computing positions (default datetime.now()).

    Returns:
        List of power values in watts (one per hour, 0 = no charging).
    """
    logger = logging.getLogger(__name__)

    if reference_dt is None:
        reference_dt = datetime.now(timezone.utc)

    power_profile = [0.0] * horizon
    now = _ensure_aware(reference_dt)
    charging_power_watts = power_kw * 1000

    logger.warning("DEBUG calculate_power_profile: trips=%d, power_kw=%.2f", len(trips), power_kw)
    logger.warning("DEBUG calculate_power_profile: now=%s", now.isoformat())

    for trip in trips:
        logger.warning("DEBUG calculate_power_profile: Processing trip id=%s, trip=%s", trip.get("id"), trip)

        # Get deadline
        deadline = trip.get("datetime")

        # Handle recurring trips (day + time instead of datetime)
        # Support both English (day/time) and Spanish (dia_semana/hora) field names
        if not deadline:
            # Try English field names first, then Spanish
            day = trip.get("day") or trip.get("dia_semana")
            time_str = trip.get("time") or trip.get("hora")
            if day is not None and time_str is not None:
                deadline_dt = calculate_next_recurring_datetime(day, time_str, now)
                if deadline_dt is None:
                    logger.warning("DEBUG calculate_power_profile: trip %s has invalid day/time, skipping", trip.get("id"))
                    continue
                logger.warning("DEBUG calculate_power_profile: trip %s is recurring (day=%s, time=%s), calculated deadline=%s",
                              trip.get("id"), day, time_str, deadline_dt.isoformat())
            else:
                logger.warning("DEBUG calculate_power_profile: trip %s has no datetime or day/time fields, skipping", trip.get("id"))
                continue
        else:
            # Parse deadline for punctual trips
            if isinstance(deadline, str):
                try:
                    deadline_dt = datetime.fromisoformat(deadline)
                except ValueError:
                    logger.warning("DEBUG calculate_power_profile: trip %s has invalid datetime, skipping", trip.get("id"))
                    continue
            else:
                deadline_dt = deadline

            # Ensure deadline_dt is timezone-aware for datetime arithmetic
            deadline_dt = _ensure_aware(deadline_dt)

        logger.warning("DEBUG calculate_power_profile: trip %s deadline=%s, now=%s, deadline_dt=%s", trip.get("id"), deadline, now, deadline_dt)

        # T1.2: Determine charging need considering SOC (backward compat)
        if soc_current is not None and battery_capacity_kwh is not None:
            decision = determine_charging_need(
                trip, soc_current, battery_capacity_kwh,
                power_kw, safety_margin_percent,
            )
            kwh = decision.kwh_needed
            logger.warning(
                "DEBUG calculate_power_profile: trip %s kwh=%.2f (SOC-aware)",
                trip.get("id"), kwh,
            )
        else:
            # Backward compat: use trip kwh directly (no SOC available)
            if "kwh" in trip:
                kwh = float(trip.get("kwh", 0))
            else:
                distance_km = float(trip.get("km", 0))
                kwh = calcular_energia_kwh(distance_km, 0.15)

            logger.warning("DEBUG calculate_power_profile: trip %s kwh=%.2f (no SOC)", trip.get("id"), kwh)

        if kwh <= 0:
            logger.warning("DEBUG calculate_power_profile: trip %s kwh <= 0, skipping", trip.get("id"))
            continue

        # Calculate hours needed to charge
        total_hours = kwh / power_kw if power_kw > 0 else 0
        horas_necesarias = int(total_hours) + (1 if total_hours % 1 > 0 else 0)
        if horas_necesarias == 0:
            horas_necesarias = 1

        logger.warning("DEBUG calculate_power_profile: trip %s total_hours=%.2f, horas_necesarias=%d", trip.get("id"), total_hours, horas_necesarias)

        # Calculate position in profile
        delta = deadline_dt - now
        horas_hasta_viaje = int(delta.total_seconds() / 3600)

        logger.warning("DEBUG calculate_power_profile: trip %s delta_seconds=%d, horas_hasta_viaje=%d, now=%s, deadline=%s",
                      trip.get("id"), delta.total_seconds(), horas_hasta_viaje, now, deadline_dt)

        if horas_hasta_viaje < 0:
            logger.warning("DEBUG calculate_power_profile: trip %s is in the past, skipping", trip.get("id"))
            continue

        # Set charging hours (last hours before deadline)
        hora_inicio_carga = max(0, horas_hasta_viaje - horas_necesarias)
        hora_fin = min(horas_hasta_viaje, horizon)

        logger.warning("DEBUG calculate_power_profile: trip %s charging_window=[%d, %d), horizon=%d",
                      trip.get("id"), hora_inicio_carga, hora_fin, horizon)

        for h in range(int(hora_inicio_carga), int(hora_fin)):
            if 0 <= h < horizon:
                power_profile[h] = charging_power_watts
                logger.warning("DEBUG calculate_power_profile: trip %s setting power_profile[%d]=%d (total non_zero=%d)",
                              trip.get("id"), h, charging_power_watts, sum(1 for x in power_profile if x > 0))

    logger.warning("DEBUG calculate_power_profile: final profile non_zero=%d", sum(1 for x in power_profile if x > 0))
    return power_profile


def calculate_power_profile(
    all_trips: List[Dict[str, Any]],
    battery_capacity_kwh: float,
    soc_current: float,
    charging_power_kw: float,
    hora_regreso: Optional[datetime],
    planning_horizon_days: int,
    reference_dt: datetime,
    safety_margin_percent: float = DEFAULT_SAFETY_MARGIN,
) -> List[float]:
    """Calculate power profile for EMHASS from trip list.

    This is the pure core of async_generate_power_profile. It:
    1. Sorts trips by deadline (earliest first)
    2. For each trip, calculates the charging window
    3. Distributes charging power across the available window hours

    Args:
        all_trips: List of trip dicts with 'tipo', 'hora', 'dia_semana',
                   'datetime', 'kwh' or 'km', 'activo', 'estado'
        battery_capacity_kwh: Battery capacity in kWh
        soc_current: Current SOC in percentage
        charging_power_kw: Charging power in kW
        hora_regreso: Return time (start of first charging window)
        planning_horizon_days: Number of days in the profile
        reference_dt: Reference datetime for computing relative positions
        safety_margin_percent: Safety margin percentage for energy calculations

    Returns:
        List of power values in watts (one per hour, 0 = no charging).
    """
    profile_length = planning_horizon_days * 24
    power_profile = [0.0] * profile_length

    # Normalize all datetime inputs to UTC-aware
    if getattr(reference_dt, "tzinfo", None) is None:
        reference_dt = reference_dt.replace(tzinfo=timezone.utc)
    if hora_regreso is not None and getattr(hora_regreso, "tzinfo", None) is None:
        hora_regreso = hora_regreso.replace(tzinfo=timezone.utc)

    if not all_trips:
        return power_profile

    # Assign deadlines and sort by urgency
    trips_with_deadlines: List[Tuple[datetime, int, Dict[str, Any]]] = []
    for idx, trip in enumerate(all_trips):
        trip_tipo: Optional[str] = trip.get("tipo")
        hora: Optional[str] = trip.get("hora")
        dia_semana: Optional[str] = trip.get("dia_semana")
        datetime_str: Optional[str] = trip.get("datetime")
        # trip_tipo must be a valid string for calculate_trip_time
        assert trip_tipo is not None
        trip_time = calculate_trip_time(trip_tipo, hora, dia_semana, datetime_str, reference_dt)
        if trip_time:
            trips_with_deadlines.append((trip_time, idx, trip))

    if not trips_with_deadlines:
        return power_profile

    # Sort by deadline ascending (earliest = highest priority)
    trips_with_deadlines.sort(key=lambda x: x[0])

    # Assign priority index
    for ordered_idx, (_, original_idx, trip) in enumerate(trips_with_deadlines):
        trip["_trip_index"] = ordered_idx

    # Charging power in watts
    charging_power_watts = charging_power_kw * 1000

    # Duration for estimating return time
    DURACION_VIAJE_HORAS = 6.0

    for trip_departure_time, _, trip in trips_with_deadlines:
        # Calculate energy needed
        energia_info = calculate_energy_needed(
            trip, battery_capacity_kwh, soc_current, charging_power_kw,
            safety_margin_percent=safety_margin_percent,
        )
        energia_kwh = energia_info["energia_necesaria_kwh"]

        if energia_kwh <= 0:
            continue

        # Calculate charging window
        ventana_info = calculate_charging_window_pure(
            trip_departure_time=trip_departure_time,
            soc_actual=soc_current,
            hora_regreso=hora_regreso,
            charging_power_kw=charging_power_kw,
            energia_kwh=energia_kwh,
            duration_hours=DURACION_VIAJE_HORAS,
        )

        if not ventana_info.get("es_suficiente", False):
            continue

        inicio_ventana = ventana_info["inicio_ventana"]
        fin_ventana = ventana_info["fin_ventana"]

        # Calculate position in profile
        delta_inicio = inicio_ventana - reference_dt
        horas_desde_ahora = int(delta_inicio.total_seconds() / 3600)

        if horas_desde_ahora < 0:
            hora_inicio_carga = 0
        else:
            hora_inicio_carga = horas_desde_ahora

        horas_necesarias = ventana_info.get("horas_carga_necesarias", 0)
        if horas_necesarias == 0:
            horas_necesarias = 1

        # End of window relative to reference
        delta_fin = fin_ventana - reference_dt
        horas_hasta_fin = int(delta_fin.total_seconds() / 3600)

        if horas_hasta_fin < 0:
            continue  # Window already ended

        # Distribute charging across available hours
        for h in range(
            int(hora_inicio_carga),
            min(int(hora_inicio_carga + horas_necesarias), horas_hasta_fin, profile_length),
        ):
            if 0 <= h < profile_length:
                power_profile[h] = charging_power_watts

    return power_profile


# =============================================================================
# PURE: Generate deferrable schedule from trips
# =============================================================================


def generate_deferrable_schedule_from_trips(
    trips: List[Dict[str, Any]],
    power_kw: float,
    reference_dt: datetime | None = None,
) -> List[Dict[str, Any]]:
    """Generate deferrable load schedule from trips (pure function version).

    This is the pure version of EMHASSAdapter._generate_schedule_from_trips.
    It generates a 24-hour schedule with charging windows before each trip's
    deadline.

    Format:
        [{"date": "2026-03-17T14:00:00+01:00", "p_deferrable0": "0.0"}, ...]

    Args:
        trips: List of trip dictionaries (must contain 'datetime' and 'kwh')
        power_kw: Charging power in kW
        reference_dt: Reference datetime for calculations (defaults to datetime.now()).
            For deterministic tests, pass a fixed datetime.

    Returns:
        List of schedule dictionaries with 'date' and 'p_deferrable{N}' keys.
        Returns empty list if trips is empty.
    """
    if not trips:
        return []

    # Normalize reference_dt to UTC-aware
    if reference_dt is not None and getattr(reference_dt, "tzinfo", None) is None:
        reference_dt = reference_dt.replace(tzinfo=timezone.utc)
    now = reference_dt if reference_dt is not None else datetime.now(timezone.utc)
    schedule: List[Dict[str, Any]] = []

    # Generate schedule for next 24 hours
    for hour_offset in range(24):
        # Calculate the scheduled time
        schedule_time = now.replace(minute=0, second=0, microsecond=0)
        schedule_time = schedule_time.replace(hour=(now.hour + hour_offset) % 24)

        # Add days if needed (when crossing midnight)
        days_to_add = (now.hour + hour_offset) // 24
        if days_to_add > 0:
            schedule_time = schedule_time + timedelta(days=days_to_add)

        schedule_entry: Dict[str, Any] = {
            "date": schedule_time.isoformat(),
        }

        # Add power values for each trip
        for idx, trip in enumerate(trips):
            power_key = f"p_deferrable{idx}"

            # Get energy requirement
            kwh = float(trip.get("kwh", 0))
            if kwh <= 0:
                schedule_entry[power_key] = "0.0"
                continue

            # Get deadline (datetime)
            deadline = trip.get("datetime")
            if not deadline:
                schedule_entry[power_key] = "0.0"
                continue

            # Parse deadline
            if isinstance(deadline, str):
                try:
                    deadline_dt = datetime.fromisoformat(deadline)
                    if getattr(deadline_dt, "tzinfo", None) is None:
                        deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    schedule_entry[power_key] = "0.0"
                    continue
            else:
                deadline_dt = deadline
                if getattr(deadline_dt, "tzinfo", None) is None:
                    deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)

            # Calculate hours until trip
            delta = deadline_dt - now
            horas_hasta_viaje = int(delta.total_seconds() / 3600)

            if horas_hasta_viaje < 0:
                schedule_entry[power_key] = "0.0"
                continue

            # Calculate charging parameters
            power_watts = power_kw * 1000
            total_hours = kwh / power_kw if power_kw > 0 else 0

            # Hours needed (ceiling of total_hours)
            horas_necesarias = int(total_hours) + (1 if total_hours % 1 > 0 else 0)
            hora_inicio_carga = max(0, horas_hasta_viaje - horas_necesarias)

            # Check if current hour is within charging window
            if hora_inicio_carga <= hour_offset < horas_hasta_viaje:
                schedule_entry[power_key] = str(int(power_watts))
            else:
                schedule_entry[power_key] = "0.0"

        schedule.append(schedule_entry)

    return schedule


# =============================================================================
# PURE: Deferrable load parameters (extracted from EMHASSAdapter)
# =============================================================================


def calculate_deferrable_parameters(
    trip: Dict[str, Any],
    power_kw: float,
    reference_dt: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Calculate deferrable load parameters from trip data.

    Pure function version extracted from EMHASSAdapter.calculate_deferrable_parameters.

    Args:
        trip: Trip dictionary with kwh, datetime (deadline), etc.
        power_kw: Charging power in kW

    Returns:
        Dictionary with calculated deferrable parameters:
        - total_energy_kwh: Energy needed in kWh
        - power_watts: Charging power in watts
        - total_hours: Hours needed to charge
        - end_timestep: End timestep for EMHASS (1-168, or 24 if no deadline)
        - start_timestep: Start timestep for EMHASS (always 0)
        - is_semi_continuous: Always False
        - minimum_power: Always 0.0
        - operating_hours: Always 0
        - startup_penalty: Always 0.0
        - is_single_constant: Always True

        Returns empty dict if kwh <= 0 or kwh is missing.
    """
    try:
        kwh_value = trip.get("kwh")
        if kwh_value is None:
            return {}
        kwh = float(kwh_value)
        if kwh <= 0:
            return {}

        deadline = trip.get("datetime")

        # Calculate hours needed to charge
        total_hours = kwh / power_kw if power_kw > 0 else 0.0

        # Power in watts (positive value = charging)
        power_watts = power_kw * 1000

        # Calculate available time until deadline
        if deadline:
            now = reference_dt if reference_dt is not None else datetime.now()
            if isinstance(deadline, str):
                deadline_dt = datetime.fromisoformat(deadline)
            else:
                deadline_dt = deadline

            hours_available = (deadline_dt - now).total_seconds() / 3600
            end_timestep = max(1, min(int(hours_available), 168))  # Max 7 days
        else:
            # Default to 24 hours if no deadline
            end_timestep = 24

        return {
            "total_energy_kwh": round(kwh, 3),
            "power_watts": round(power_watts, 0),
            "total_hours": round(total_hours, 2),
            "end_timestep": end_timestep,
            "start_timestep": 0,
            "is_semi_continuous": False,
            "minimum_power": 0.0,
            "operating_hours": 0,
            "startup_penalty": 0.0,
            "is_single_constant": True,
        }

    except Exception as err:
        _LOGGER.error("Error calculating deferrable parameters: %s", err)
        return {}
