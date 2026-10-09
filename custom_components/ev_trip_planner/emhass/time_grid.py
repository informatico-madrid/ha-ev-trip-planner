"""Absolute deadlines projected onto EMHASS's hourly, UTC-rounded time grid."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from ..calculations.windows import build_deferrable_matrix_row

STEP_SECONDS = 3600


def as_utc(value: datetime) -> datetime:
    """Normalize internal calculation dates; legacy naive dates mean UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def planning_reference(now: datetime) -> datetime:
    """Match EMHASS ``nearest``: round the UTC grid, not a local clock offset.

    Pandas rounds the forecast index in UTC using ties-to-even. Its forecast
    origin removes microseconds before rounding. The integration currently
    publishes hourly profiles, so the grid interval is one hour.
    """
    timestamp = as_utc(now).replace(microsecond=0).timestamp()
    return datetime.fromtimestamp(
        round(timestamp / STEP_SECONDS) * STEP_SECONDS, timezone.utc
    )


def window_slots(
    start: datetime,
    deadline: datetime,
    reference: datetime,
    horizon: int,
    now: datetime | None = None,
) -> tuple[int, int]:
    """Keep only full slots inside the available window and before departure.

    EMHASS's end index is exclusive: slot ``end - 1`` ends at ``end``. Rounding
    a departure up would explicitly permit charging after the vehicle leaves.
    """
    origin = as_utc(reference)
    first = math.ceil((as_utc(start) - origin).total_seconds() / STEP_SECONDS)
    end = math.floor((as_utc(deadline) - origin).total_seconds() / STEP_SECONDS)
    end = max(0, min(horizon, end))
    first = max(0, min(end, first))
    # Preserve the integration's current-slot availability rule: a vehicle
    # already available may use slot 0 when the rounded grid is in the past.
    if now is not None and as_utc(start) <= as_utc(now) and origin <= as_utc(now):
        first = 0
    return first, end


def project_trip(
    params: dict[str, Any],
    reference: datetime,
    horizon: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Rebase a cached calculation without mutating it or extending its deadline."""
    projected = params.copy()
    start_value = params.get("window_start")
    deadline_value = params.get("deadline")
    if not start_value or not deadline_value:
        return projected
    start = datetime.fromisoformat(start_value)
    deadline = datetime.fromisoformat(deadline_value)
    first, end = window_slots(start, deadline, reference, horizon, now)
    requested = math.ceil(max(0.0, float(params.get("def_total_hours", 0))))
    hours = min(requested, max(0, end - first))
    nominal = float(params.get("configured_power_watts", params.get("power_watts", 0)))
    # EMHASS interprets end=0 as "no end constraint". A window with no complete
    # slot MUST also have zero hours and zero nominal power, never an active load.
    projected.update(
        def_start_timestep=first,
        def_end_timestep=end,
        def_total_hours=hours,
        total_hours=hours,
        power_watts=nominal if hours else 0.0,
        kwh_needed=hours * nominal / 1000,
        unserved_energy_kwh=float(params.get("energy_unserved_kwh", 0))
        + max(0, requested - hours)
        * nominal
        / 1000
        * float(params.get("charging_efficiency", 1.0)),
        planning_reference=reference.isoformat(),
        p_deferrable_matrix=[
            build_deferrable_matrix_row(horizon, nominal / 1000, hours, end)
        ],
    )
    return projected


def plan_snapshot(
    params_by_id: dict[str, Any],
    reference: datetime,
    horizon: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a consistent current-grid profile, schedule and per-trip snapshot."""
    params = {
        trip_id: project_trip(value, reference, horizon, now)
        for trip_id, value in params_by_id.items()
    }
    profile = [0.0] * horizon
    schedule = []
    for value in params.values():
        if not value.get("activo", False):
            continue
        for row in value.get("p_deferrable_matrix", []):
            for step, watts in enumerate(row[:horizon]):
                profile[step] = max(profile[step], watts)
        schedule.append(
            {
                "index": value.get("emhass_index", 0),
                "kwh": value.get("kwh_needed", 0),
                "start_timestep": value.get("def_start_timestep", 0),
                "end_timestep": value.get("def_end_timestep", 0),
            }
        )
    return {
        "per_trip_emhass_params": params,
        "emhass_power_profile": profile,
        "emhass_deferrables_schedule": schedule,
        "emhass_planning_reference": reference.isoformat(),
    }
