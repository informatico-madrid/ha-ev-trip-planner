"""Core types and calculation functions extracted from calculations_orig.py.

This module is the first stage of SOLID decomposition of the legacy
calculations.py module. It holds the core types, constants, and pure
calculation functions that have no dependencies on other sub-modules.

More sub-modules will be created as the decomposition progresses.
"""

from __future__ import annotations

import unicodedata

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from custom_components.ev_trip_planner.const import (
    DEFAULT_SOC_BASE,
    DEFAULT_SOC_BUFFER_PERCENT,
    DEFAULT_T_BASE,
)
from custom_components.ev_trip_planner.utils import calcular_energia_kwh

SOH_CACHE_TTL_SECONDS = 300  # 5 minutes


def compute_safe_delta(
    trip_time: datetime,
    now: datetime,
) -> Optional[timedelta]:
    """Compute (trip_time - now) with timezone-safety fallback.

    If direct subtraction raises TypeError (naive vs aware), attempts to
    attach UTC timezone to the trip_time and retries. Returns None if
    both attempts fail.
    """
    try:
        return trip_time - now
    except TypeError:
        try:
            if getattr(trip_time, "tzinfo", None) is None:
                trip_time = trip_time.replace(tzinfo=timezone.utc)
            return trip_time - now
        except (AttributeError, TypeError):
            return None


@dataclass
class BatteryCapacity:
    """Abstraction for real battery capacity with SOH-aware fallback.

    Wraps nominal capacity and optional SOH sensor lookup to compute
    the effective (degraded) capacity used everywhere in the system.

    Attributes:
        nominal_capacity_kwh: Battery's rated (nominal) capacity in kWh.
        soh_sensor_entity_id: Optional HA sensor entity for SOH (%).
    """

    nominal_capacity_kwh: float
    soh_sensor_entity_id: Optional[str] = None
    _soh_value: Optional[float] = None
    _soh_cached_at: Optional[datetime] = None
    SOH_CACHE_TTL_SECONDS: int = SOH_CACHE_TTL_SECONDS  # type: ignore[misc]

    def _compute_capacity(self) -> float:
        """Compute real capacity from nominal + cached SOH value."""
        if self._soh_value is not None:
            return self.nominal_capacity_kwh * self._soh_value / 100.0
        return self.nominal_capacity_kwh  # fallback to nominal

    def get_capacity(self, hass: Any | None = None) -> float:
        """Get current real battery capacity, refreshing SOH cache if stale.

        If SOH sensor is configured and cache is stale (>5 min), re-read the
        sensor. If the sensor is unavailable, keep the last valid cached value
        (hysteresis — do not oscillate capacity when sensor is noisy).
        """
        if not hass or not self.soh_sensor_entity_id:
            return self._compute_capacity()

        # Re-read if cache is stale OR never initialized
        should_read = (
            self._soh_cached_at is None
            or (datetime.now() - self._soh_cached_at).total_seconds()
            > self.SOH_CACHE_TTL_SECONDS
        )
        if should_read:
            new_val = self._read_soh(hass)
            if new_val is not None:
                self._soh_value = new_val
                self._soh_cached_at = datetime.now()
            # If new_val is None, keep old cached value (hysteresis)

        return self._compute_capacity()

    get_capacity_kwh = get_capacity  # Alias for clarity

    def _read_soh(self, hass: Any) -> Optional[float]:
        """Read current SOH sensor value. Returns None if unavailable."""
        state = hass.states.get(self.soh_sensor_entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            val = float(state.state)
            return max(10.0, min(100.0, val))  # clamp to valid range
        except (ValueError, TypeError):
            return None


def calculate_dynamic_soc_limit(
    t_hours: float,
    soc_post_trip: float,
    battery_capacity_kwh: float,
    t_base: float = DEFAULT_T_BASE,
) -> float:
    """Compute degradation-aware SOC upper bound.

    Uses idle time and projected post-trip SOC to calculate a continuous
    upper bound for charging. Larger idle times at high SOC produce
    tighter caps to reduce battery degradation.

    Formula:
        risk = t_hours * (soc_post_trip - 35) / 65
        If risk <= 0: return 100.0 (battery drained below sweet spot)
        limit = 35 + 65 * (1 / (1 + risk / t_base))

    Args:
        t_hours: Hours until next trip.
        soc_post_trip: Expected SOC after the trip completes.
        battery_capacity_kwh: Battery capacity (not used in formula,
            kept for API consistency).
        t_base: User-configurable base window in hours (6-48, default 24).

    Returns:
        SOC limit clamped to [35.0, 100.0].
    """
    # Negative risk means battery was drained below the 35% sweet spot
    # — no degradation risk, allow full charge
    risk = t_hours * (soc_post_trip - DEFAULT_SOC_BASE) / 65.0
    if risk <= 0:
        return 100.0

    limit = DEFAULT_SOC_BASE + 65.0 * (1.0 / (1.0 + risk / t_base))
    return max(35.0, min(100.0, limit))


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


def _strip_accents(s: str) -> str:
    """Remove diacritical marks: 'miércoles' → 'miercoles'."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def calculate_day_index(day_name: str) -> int:
    """Obtiene el índice del día de la semana (0=lunes, 6=domingo).

    Args:
        day_name: Nombre del día en español (case-insensitive) o dígito 0-6.
                  Los dígitos se interpretan en formato JavaScript getDay()
                  (0=domingo, 1=lunes, ..., 6=sábado) y se convierten al
                  formato interno Monday=0.

    Returns:
        Índice del día de la semana (0=lunes).
    """
    day_lower = day_name.lower().strip()
    day_norm = _strip_accents(day_lower)

    # Handle numeric day values (0-6)
    # BUG FIX: Frontend stores dia_semana as JS getDay() format (Sunday=0).
    # Convert to Monday=0 format: Monday=0, ..., Saturday=5, Sunday=6.
    # Formula: (js_day - 1) % 7
    #   JS 0 (Sunday)    → (0-1)%7 = 6 → domingo ✓
    #   JS 1 (Monday)    → (1-1)%7 = 0 → lunes ✓
    #   JS 5 (Friday)    → (5-1)%7 = 4 → viernes ✓
    #   JS 6 (Saturday)  → (6-1)%7 = 5 → sabado ✓
    if day_lower.isdigit():
        js_day = int(day_lower)
        if 0 <= js_day <= 6:
            return (js_day - 1) % 7
        return 0  # Monday on invalid index

    # Try direct match first
    try:
        return DAYS_OF_WEEK.index(day_norm)
    except ValueError:
        pass

    # If still not found, default to Monday (index 0)
    return 0


# =============================================================================
# PURE: Trip time calculation
# =============================================================================


# CC-N-ACCEPTED: cc=13 — inherently requires branching for 2 trip types ×
# (with/without timezone) × 2 datetime format variants. Extracting would
# split a single coherent dispatch logic into 5+ helpers with unclear names.
def calculate_trip_time(
    trip_tipo: str,
    hora: Optional[str],
    dia_semana: Optional[str],
    datetime_str: Optional[str],
    reference_dt: datetime,
    tz: Optional[Any] = None,
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
        tz: Optional timezone for interpreting hora as local time.
            If provided, hora is treated as local time and converted to UTC.
            If None (default), hora is treated as UTC (backward compat).

    Returns:
        Calculated trip datetime, or None if insufficient data.
    """
    from ..const import TRIP_TYPE_PUNCTUAL, TRIP_TYPE_RECURRING

    if trip_tipo == TRIP_TYPE_RECURRING:
        if not hora:
            return None
        now = reference_dt
        target_day = calculate_day_index(dia_semana or "lunes")
        local_time = datetime.strptime(hora, "%H:%M").time()
        hour = local_time.hour

        if tz is not None:
            # BUG FIX: hora is local time, convert to UTC
            # Normalize reference_dt to aware (UTC) if naive to avoid TypeError
            aware_now = (
                now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
            )
            local_now = aware_now.astimezone(tz)
            today = local_now.date()
            day_of_week = local_now.weekday()
            days_ahead = (target_day - day_of_week) % 7
            if days_ahead == 0 and local_now.hour > hour:
                days_ahead = 7
            # Create deadline in local timezone, then convert to UTC
            local_dt = datetime.combine(
                today + timedelta(days=days_ahead),
                local_time,
                tzinfo=tz,
            )
            return local_dt.astimezone(timezone.utc)
        else:
            # Backward compat: treat hora as UTC
            today = now.date()
            day_of_week = now.weekday()
            days_ahead = (target_day - day_of_week) % 7
            if days_ahead == 0 and now.hour > hour:
                days_ahead = 7
            return datetime.combine(
                today + timedelta(days=days_ahead),
                local_time,
            ).replace(tzinfo=timezone.utc)
    elif trip_tipo == TRIP_TYPE_PUNCTUAL:
        if not datetime_str:
            return None
        # Handle both with and without seconds (isoformat produces HH:MM:SS)
        try:
            # Try without seconds first (original format)
            return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=timezone.utc
            )
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
