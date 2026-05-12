"""Power profile calculation functions extracted from calculations_orig.py.

Extracted from the legacy calculations.py god module as part of the
SOLID decomposition (Spec 3). These functions handle pure power
profile calculations for EMHASS integration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .deficit import (
    calculate_next_recurring_datetime,
    determine_charging_need,
)

from ..const import DEFAULT_SAFETY_MARGIN
from ..utils import calcular_energia_kwh
from ._helpers import _ensure_aware
from .core import calculate_trip_time
from .windows import calculate_charging_window_pure, calculate_energy_needed


def calculate_power_profile_from_trips(
    trips: List[Dict[str, Any]],
    power_kw: float,
    horizon: int = 168,
    reference_dt: Optional[datetime] = None,
    soc_current: Optional[float] = None,
    battery_capacity_kwh: Optional[float] = None,
    safety_margin_percent: float = DEFAULT_SAFETY_MARGIN,
    tz: Optional[Any] = None,
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
        tz: Optional timezone for interpreting recurring trip times as local.
            Passed to calculate_next_recurring_datetime.

    Returns:
        List of power values in watts (one per hour, 0 = no charging).
    """
    logger = logging.getLogger(__name__)

    if reference_dt is None:
        reference_dt = datetime.now(timezone.utc)

    power_profile = [0.0] * horizon
    now = _ensure_aware(reference_dt)
    charging_power_watts = power_kw * 1000

    logger.debug(
        "DEBUG calculate_power_profile: trips=%d, power_kw=%.2f", len(trips), power_kw
    )
    logger.debug("DEBUG calculate_power_profile: now=%s", now.isoformat())

    for trip in trips:
        logger.debug(
            "DEBUG calculate_power_profile: Processing trip id=%s, trip=%s",
            trip.get("id"),
            trip,
        )

        # Get deadline
        deadline = trip.get("datetime")

        # Handle recurring trips (day + time instead of datetime)
        # Support both English (day/time) and Spanish (dia_semana/hora) field names
        if not deadline:
            # Try English field names first, then Spanish
            day = trip.get("day")
            if day is None:
                day = trip.get("dia_semana")
            time_str = trip.get("time")
            if time_str is None:
                time_str = trip.get("hora")
            if day is not None and time_str is not None:
                deadline_dt = calculate_next_recurring_datetime(
                    day, time_str, now, tz=tz
                )
                if deadline_dt is None:
                    logger.debug(
                        "DEBUG calculate_power_profile: trip %s has invalid day/time, skipping",
                        trip.get("id"),
                    )
                    continue
                logger.debug(
                    "DEBUG calculate_power_profile: trip %s is recurring (day=%s, time=%s), calculated deadline=%s",
                    trip.get("id"),
                    day,
                    time_str,
                    deadline_dt.isoformat(),
                )
            else:
                logger.debug(
                    "DEBUG calculate_power_profile: trip %s has no datetime or day/time fields, skipping",
                    trip.get("id"),
                )
                continue
        else:
            # Parse deadline for punctual trips
            if isinstance(deadline, str):
                try:
                    deadline_dt = datetime.fromisoformat(deadline)
                except ValueError:
                    logger.debug(
                        "DEBUG calculate_power_profile: trip %s has invalid datetime, skipping",
                        trip.get("id"),
                    )
                    continue
            else:
                deadline_dt = deadline

            # Ensure deadline_dt is timezone-aware for datetime arithmetic
            deadline_dt = _ensure_aware(deadline_dt)

        logger.debug(
            "DEBUG calculate_power_profile: trip %s deadline=%s, now=%s, deadline_dt=%s",
            trip.get("id"),
            deadline,
            now,
            deadline_dt,
        )

        # T1.2: Determine charging need considering SOC (backward compat)
        if soc_current is not None and battery_capacity_kwh is not None:
            decision = determine_charging_need(
                trip,
                soc_current,
                battery_capacity_kwh,
                power_kw,
                safety_margin_percent,
            )
            kwh = decision.kwh_needed
            logger.debug(
                "DEBUG calculate_power_profile: trip %s kwh=%.2f (SOC-aware)",
                trip.get("id"),
                kwh,
            )
        else:
            # Backward compat: use trip kwh directly (no SOC available)
            if "kwh" in trip:
                kwh = float(trip.get("kwh", 0))
            else:
                distance_km = float(trip.get("km", 0))
                kwh = calcular_energia_kwh(distance_km, 0.15)

            logger.debug(
                "DEBUG calculate_power_profile: trip %s kwh=%.2f (no SOC)",
                trip.get("id"),
                kwh,
            )

        if kwh <= 0:
            logger.debug(
                "DEBUG calculate_power_profile: trip %s kwh <= 0, skipping",
                trip.get("id"),
            )
            continue

        # Calculate hours needed to charge
        total_hours = kwh / power_kw if power_kw > 0 else 0
        horas_necesarias = int(total_hours) + (1 if total_hours % 1 > 0 else 0)
        if horas_necesarias == 0:
            horas_necesarias = 1

        logger.debug(
            "DEBUG calculate_power_profile: trip %s total_hours=%.2f, horas_necesarias=%d",
            trip.get("id"),
            total_hours,
            horas_necesarias,
        )

        # Calculate position in profile
        delta = deadline_dt - now
        horas_hasta_viaje = int(delta.total_seconds() / 3600)

        logger.debug(
            "DEBUG calculate_power_profile: trip %s delta_seconds=%d, horas_hasta_viaje=%d, now=%s, deadline=%s",
            trip.get("id"),
            delta.total_seconds(),
            horas_hasta_viaje,
            now,
            deadline_dt,
        )

        if horas_hasta_viaje < 0:
            logger.debug(
                "DEBUG calculate_power_profile: trip %s is in the past, skipping",
                trip.get("id"),
            )
            continue

        # Set charging hours (last hours before deadline)
        hora_inicio_carga = max(0, horas_hasta_viaje - horas_necesarias)
        hora_fin = min(horas_hasta_viaje, horizon)

        logger.debug(
            "DEBUG calculate_power_profile: trip %s charging_window=[%d, %d), horizon=%d",
            trip.get("id"),
            hora_inicio_carga,
            hora_fin,
            horizon,
        )

        for h in range(int(hora_inicio_carga), int(hora_fin)):
            if 0 <= h < horizon:
                power_profile[h] = charging_power_watts
                logger.debug(
                    "DEBUG calculate_power_profile: trip %s setting power_profile[%d]=%d (total non_zero=%d)",
                    trip.get("id"),
                    h,
                    charging_power_watts,
                    sum(1 for x in power_profile if x > 0),
                )

    logger.debug(
        "DEBUG calculate_power_profile: final profile non_zero=%d",
        sum(1 for x in power_profile if x > 0),
    )
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
    trips_with_deadlines: List[tuple] = []
    for idx, trip in enumerate(all_trips):
        trip_tipo: Optional[str] = trip.get("tipo")
        hora: Optional[str] = trip.get("hora")
        dia_semana: Optional[str] = trip.get("dia_semana")
        datetime_str: Optional[str] = trip.get("datetime")
        # trip_tipo must be a valid string for calculate_trip_time
        assert trip_tipo is not None
        trip_time = calculate_trip_time(
            trip_tipo, hora, dia_semana, datetime_str, reference_dt
        )
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
            trip,
            battery_capacity_kwh,
            soc_current,
            charging_power_kw,
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
            min(
                int(hora_inicio_carga + horas_necesarias),
                horas_hasta_fin,
                profile_length,
            ),
        ):
            if 0 <= h < profile_length:
                power_profile[h] = charging_power_watts

    return power_profile
