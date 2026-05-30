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


def calculate_hours_deficit_propagation(
    windows: List[Dict[str, Any]],
    def_total_hours: List[float] | None = None,
) -> List[Dict[str, Any]]:
    """Propagate charging-hour deficits backwards through the trip chain.

    Business rule (REGLAS_DE_NEGOCIO.md, Section 6):
    - déficit(Ventana_i) = max(0, horas_carga_necesarias - ventana_horas)
    - ALL windows with deficit cascade their unmet hours to earlier windows.
    - Multiple collapsed/insufficient windows accumulate their deficits into
      a single carrier that propagates backward to the first window(s) with
      spare capacity.

    Single-pass backward algorithm (last → first):
    - A deficit_carrier starts at 0 and accumulates deficits from later windows.
    - Each window absorbs from the carrier using spare capacity
      (spare = ventana - original_def_total).
    - Each window with own_deficit > 0 charges only what fits (ceil or 0 for
      zero-timeframe) and adds its own deficit to the carrier.
    - Earlier windows with spare capacity absorb the accumulated carrier.

    For zero-size windows (ventana=0h): the window cannot charge at all, so
    its def_total_hours becomes 0 and its full need is added to the carrier.

    Args:
        windows: List of window dicts from calculate_multi_trip_charging_windows().
            Must contain: ventana_horas, horas_carga_necesarias.
        def_total_hours: Optional list of total charging hours per trip.
            If None, defaults to horas_carga_necesarias from each window.

    Returns:
        List of enriched window dicts with additional keys:
        - deficit_hours_propagated: hours absorbed from carrier (float, 2dp)
        - deficit_hours_to_propagate: remaining carrier after this window (float, 2dp)
        - adjusted_def_total_hours: final charging hours for this window (float, 2dp)
    """
    if not windows:
        return []

    N = len(windows)
    if def_total_hours is None:
        def_total_hours = [w["horas_carga_necesarias"] for w in windows]

    own_deficits = [
        max(0.0, w["horas_carga_necesarias"] - w["ventana_horas"]) for w in windows
    ]

    # Backward pass: process every window last → first.
    # A single carrier accumulates deficits from all insufficient windows
    # and distributes them to earlier windows with spare capacity.
    results: List[Dict[str, Any]] = [{} for _ in range(N)]
    deficit_carrier = 0.0
    for i in range(N - 1, -1, -1):
        ventana = windows[i]["ventana_horas"]
        original = def_total_hours[i]
        spare = max(0.0, ventana - original)

        absorbed = min(deficit_carrier, spare)
        deficit_carrier -= absorbed

        result = windows[i].copy()
        result["deficit_hours_propagated"] = round(absorbed, 2)
        if own_deficits[i] > 0:
            # Insufficient/collapsed: charge only what fits; push rest backward.
            result["adjusted_def_total_hours"] = (
                math.ceil(ventana) if ventana > 0 else 0.0
            )
            deficit_carrier += own_deficits[i]
        else:
            result["adjusted_def_total_hours"] = round(original + absorbed, 2)
        result["deficit_hours_to_propagate"] = round(deficit_carrier, 2)
        results[i] = result

    return results


__all__ = [
    "ChargingDecision",
    "calculate_energy_needed",
    "calculate_hours_deficit_propagation",
    "determine_charging_need",
]
