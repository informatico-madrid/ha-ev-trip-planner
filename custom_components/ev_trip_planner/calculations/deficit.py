"""Deficit and scheduling calculation functions extracted from calculations_orig.py.

Extracted from the legacy calculations.py god module as part of the
SOLID decomposition (Spec 3). These functions handle charging decisions
and charging-hour deficit propagation.
"""

from __future__ import annotations  # pragma: no mutate  # EQ-042

import math
from dataclasses import dataclass
from typing import Any, Dict, List

from ..const import DEFAULT_SAFETY_MARGIN
from . import _helpers
from .windows import calculate_energy_needed

# =============================================================================
# CHARGING DECISION
# =============================================================================


@dataclass
class ChargingDecision:
    """Immutable charging decision for a single trip.

    Encapsulates the decision logic for whether and how much to charge,
    extracted from EMHASSAdapter._populate_per_trip_cache_entry for SOLID SRP.
    """

    trip_id: str
    kwh_needed: float  # Energy to charge (0 = no charge needed)
    def_total_hours: int  # Hours of charging needed
    power_watts: float  # Charging power (0 = no charge)
    needs_charging: bool  # Whether charging is needed


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
        trip,
        battery_capacity_kwh,
        soc_current,
        charging_power_kw,
        safety_margin_percent=safety_margin_percent,
    )
    kwh_needed = energia_info["energia_necesaria_kwh"]

    needs_charging = kwh_needed > 0

    if needs_charging:
        total_hours = (  # pragma: no mutate  # EQ-043
            int(math.ceil(kwh_needed / charging_power_kw))
            if charging_power_kw > 0
            else 0
        )
        power_watts = _helpers.kw_to_watts(charging_power_kw)
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


# =============================================================================
# PURE: Hours deficit propagation
# =============================================================================


# qg-accepted: complexity=11 is inherent to deficit propagation algorithm
def calculate_hours_deficit_propagation(
    windows: List[Dict[str, Any]],
    def_total_hours: List[float] | None = None,
) -> List[Dict[str, Any]]:
    """Propagate charging-hour deficits backwards through the trip chain.

    Business rule (REGLAS_DE_NEGOCIO.md, Section 6):
    - déficit(Ventana_i) = max(0, energía_necesaria - capacidad_disponible)
    - If déficit(Ventana_i) > 0: déficit(Ventana_{i-1}) += déficit(Ventana_i)
    - Propagates recursively to the first window.
    - If the first window also has deficit, absorb what's possible and accept
      the remaining.

    Implements a two-pass algorithm:
    1. Forward pass: accumulate each trip's own deficit + deficits from later
       trips into an accumulated deficit carrier.
    2. Backward pass: absorb from the carrier starting at the last trip and
       working toward the first. The first trip (least spare capacity) is
       last to absorb, giving later trips with spare capacity a chance first.

    For zero-size windows (ventana=0h): the trip cannot charge, so its
    def_total_hours is set to 0 and its deficit cascades to the previous
    window which absorbs and INCREASES its def_total_hours.

    Args:
        windows: List of window dicts from calculate_multi_trip_charging_windows().
            Must contain: ventana_horas, horas_carga_necesarias.
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

    # ========================================================================
    # Step 1: Forward pass — compute each window's own deficit.
    # deficit = max(0, horas_necesarias - ventana_horas)
    # For zero-size windows: the trip cannot charge, so deficit = full need.
    # ========================================================================
    own_deficits: List[float] = []
    for i in range(N):
        ventana = windows[i]["ventana_horas"]
        horas_carga = windows[i]["horas_carga_necesarias"]
        own_deficits.append(max(0.0, horas_carga - ventana))

    # Find the deficit origin: first trip with deficit (window collapsed)
    deficit_origin = None
    for i in range(N):
        if own_deficits[i] > 0:
            deficit_origin = i
            break

    if deficit_origin is None:
        # No deficits anywhere — no cascade needed.
        results = [{} for _ in range(N)]
        for i in range(N):
            result = windows[i].copy()
            result["deficit_hours_propagated"] = 0.0
            result["deficit_hours_to_propagate"] = 0.0
            result["adjusted_def_total_hours"] = round(def_total_hours[i], 2)
            results[i] = result
        return results

    # The deficit carrier is the own deficit at the origin.
    # Trips AFTER the origin don't absorb or propagate — the deficit
    # originates at the window trip and cascades backward only.
    deficit_carrier: float = own_deficits[deficit_origin]

    # ========================================================================
    # Step 2: Backward pass — process from last to first.
    #
    # Trips after deficit_origin: pass through unchanged (absorb=0, carry=0).
    #   They have normal windows and normal needs — no deficit involvement.
    #
    # Deficit origin: def_total_hours=0 (zero window, cannot charge).
    #   Its deficit is passed to earlier trips for absorption.
    #
    # Trips before deficit_origin: absorb deficit using spare capacity.
    #   Each absorbing trip INCREASES its def_total_hours.
    # ========================================================================
    results = [{} for _ in range(N)]

    for i in range(N - 1, -1, -1):
        ventana = windows[i]["ventana_horas"]
        original_def_total = def_total_hours[i]

        if i > deficit_origin:
            # Trips after the origin: no deficit involvement.
            result = windows[i].copy()
            result["deficit_hours_propagated"] = 0.0
            result["deficit_hours_to_propagate"] = 0.0
            result["adjusted_def_total_hours"] = round(original_def_total, 2)
            results[i] = result
            continue

        # i <= deficit_origin: participate in cascade.
        spare = max(0.0, ventana - original_def_total)
        absorbed = min(deficit_carrier, spare)
        deficit_carrier -= absorbed

        result = windows[i].copy()
        result["deficit_hours_propagated"] = round(absorbed, 2)
        result["deficit_hours_to_propagate"] = round(deficit_carrier, 2)

        if i == deficit_origin:
            # Origin trip may have a partial window — charge what's possible.
            # ventana_horas=0 means no time to charge, so adjusted=0.
            # Any positive window ceils to at least 1h.
            ventana = windows[i]["ventana_horas"]
            result["adjusted_def_total_hours"] = (
                math.ceil(ventana) if ventana > 0 else 0.0
            )
        else:
            # Earlier trips absorb deficit → def_total INCREASES.
            result["adjusted_def_total_hours"] = round(original_def_total + absorbed, 2)
        results[i] = result

    return results


__all__ = [
    "ChargingDecision",
    "calculate_energy_needed",
    "calculate_hours_deficit_propagation",
    "determine_charging_need",
]
