"""Window transformation pipeline for charging schedule optimization.

Each transform is a pure function: (List[WindowDict], PipelineContext) -> List[WindowDict].
Transforms compose via run_window_pipeline, applied in order:
  1. apply_soc_cap_transform  — limits charging hours per window (SOC health)
  2. apply_deficit_transform  — propagates unmet hours backward (factibilidad)

Invariants every transform MUST preserve:
  - adjusted_def_total_hours <= ventana_horas
  - def_start_timestep / def_end_timestep NOT mutated
  - ventana_horas == 0  =>  horas_carga_necesarias == 0
  - Input windows are not mutated (new dicts returned)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Protocol

from .core import calculate_dynamic_soc_limit

WindowDict = Dict[str, Any]


@dataclass(frozen=True)
class PipelineContext:
    """Immutable context passed to every pipeline transform."""

    charging_power_kw: float
    battery_capacity_kwh: float
    t_base: float  # aggressiveness mando (k in the ramp formula, hours unit)
    now: datetime
    soc_current: float = field(default=50.0)  # used by Componente 2 (post-trip cap)


class WindowTransform(Protocol):
    """Contract for a pipeline step.

    Each step receives the current window list and context, and returns
    a new window list. Transforms must not mutate the input windows.
    """

    def __call__(
        self, windows: List[WindowDict], ctx: PipelineContext
    ) -> List[WindowDict]: ...


def apply_soc_cap_transform(
    windows: List[WindowDict],
    ctx: PipelineContext,
) -> List[WindowDict]:
    """Limit horas_carga_necesarias per window via slack-driven ramp (Componente 1).

    For each window:
        slack = max(0, ventana_horas - horas_carga_necesarias)
        H_allowed = horas_carga_necesarias / (1 + slack / k)
        horas_carga_necesarias = ceil(H_allowed)

    Properties:
    - slack=0  =>  H_allowed == H_req  (factibilidad never broken for tight windows)
    - ventana=0  =>  H_allowed=0
    - Monotone: as ventana narrows, H_allowed climbs back towards H_req
    - Never exceeds original horas_carga_necesarias
    - Smaller k (t_base) = more aggressive cap
    """
    k = ctx.t_base
    result: List[WindowDict] = []
    for w in windows:
        ventana: float = w.get("ventana_horas", 0)
        needs: int = w.get("horas_carga_necesarias", 0)

        if needs <= 0:
            new_w = {**w}
        else:
            # Componente 1: slack-driven ramp (pre-trip health)
            slack = max(0.0, ventana - needs)
            h_c1 = math.ceil(needs / (1.0 + slack / k))

            # Componente 2: post-trip cap via calculate_dynamic_soc_limit
            # Only applies when fin_ventana is available (real window from adapter).
            # Converts SOC-based cap to charging hours and takes the more restrictive.
            fin_ventana = w.get("fin_ventana")
            trip = w.get("trip")
            if fin_ventana is not None and ctx.charging_power_kw > 0:
                t_hours = max(0.0, (fin_ventana - ctx.now).total_seconds() / 3600)
                trip_kwh = (
                    (trip or {}).get("kwh", 0.0) if isinstance(trip, dict) else 0.0
                )
                soc_after = max(
                    0.0, ctx.soc_current - (trip_kwh / ctx.battery_capacity_kwh) * 100
                )
                soc_cap_pct = calculate_dynamic_soc_limit(
                    t_hours, soc_after, ctx.battery_capacity_kwh, t_base=ctx.t_base
                )
                if soc_cap_pct < 100.0 and ctx.soc_current < 100.0:
                    capped_energy = max(
                        0.0,
                        (soc_cap_pct - ctx.soc_current)
                        / 100.0
                        * ctx.battery_capacity_kwh,
                    )
                    h_c2 = math.ceil(capped_energy / ctx.charging_power_kw)
                    h_c1 = min(h_c1, h_c2)

            new_w = {**w, "horas_carga_necesarias": min(h_c1, needs)}

        result.append(new_w)
    return result


def apply_deficit_transform(
    windows: List[WindowDict],
    ctx: PipelineContext,  # noqa: ARG001
) -> List[WindowDict]:
    """Propagate unmet charging hours backwards (factibilidad guarantee).

    Thin wrapper around calculate_hours_deficit_propagation. Uses
    horas_carga_necesarias (already capped by apply_soc_cap_transform) as
    the per-window need, then propagates unmet hours to earlier windows.
    """
    from .deficit import calculate_hours_deficit_propagation

    if not windows:
        return windows

    # Pass def_total_hours=None so the function derives from horas_carga_necesarias
    return calculate_hours_deficit_propagation(windows, def_total_hours=None)


def run_window_pipeline(
    windows: List[WindowDict],
    ctx: PipelineContext,
    transforms: List[WindowTransform] | None = None,
) -> List[WindowDict]:
    """Apply a sequence of transforms to the window list.

    Default order: [apply_soc_cap_transform, apply_deficit_transform]
    The order is significant: SOC cap (health) runs before deficit propagation
    (factibilidad) so the deficit step operates on already-capped needs.
    """
    if transforms is None:
        transforms = [apply_soc_cap_transform, apply_deficit_transform]

    current = windows
    for transform in transforms:
        current = transform(current, ctx)
    return current
