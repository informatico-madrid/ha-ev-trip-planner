"""Plan one battery through chronological trips on an already resolved grid."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..utils import calcular_energia_kwh


@dataclass(frozen=True)
class EnergyChainContext:
    """Energy and reserve policy shared by every trip in a plan."""

    capacity_kwh: float
    charging_power_kw: float
    soc_current: float
    safety_margin_percent: float
    consumption_kwh_per_km: float
    charging_efficiency: float
    now: datetime
    standby_soc_per_hour: float = 0.0


def _trip_energy(trip: dict[str, Any], consumption: float) -> float:
    """Preserve explicit kWh, including zero; use configured consumption otherwise."""
    energy = (
        float(trip["kwh"])
        if "kwh" in trip
        else calcular_energia_kwh(float(trip.get("km", 0)), consumption)
    )
    if not math.isfinite(energy) or energy < 0:
        raise ValueError("Trip energy must be finite and non-negative")
    return energy


def _departure_targets(
    energies: list[float],
    slots: list[int],
    windows: list[dict[str, Any]],
    ctx: EnergyChainContext,
) -> list[float]:
    """Carry future demand backward only where the next window cannot supply it.

    A target can exceed capacity: retain that shortfall rather than pretending
    earlier charging can store more energy than the battery holds.
    """
    reserve = ctx.capacity_kwh * ctx.safety_margin_percent / 100
    slot_energy = ctx.charging_power_kw * ctx.charging_efficiency
    targets = [0.0] * len(energies)
    following = 0.0
    for i in range(len(energies) - 1, -1, -1):
        next_charge = slots[i + 1] * slot_energy if i + 1 < len(slots) else 0
        idle = 0.0
        if i + 1 < len(windows):
            gap = (
                max(
                    0,
                    windows[i + 1]["fin_ventana"].timestamp()
                    - windows[i]["fin_ventana"].timestamp(),
                )
                / 3600
            )
            idle = gap * ctx.standby_soc_per_hour / 100 * ctx.capacity_kwh
        carry = max(reserve, following + idle - next_charge)
        targets[i] = energies[i] + carry
        following = min(ctx.capacity_kwh, targets[i])
    return targets


def plan_energy_chain(
    windows: list[dict[str, Any]], ctx: EnergyChainContext
) -> list[dict[str, Any]]:
    """Allocate charge, then simulate each consumption against the carried energy.

    Windows are chronological and contain integer full-slot boundaries. Power is
    nominal grid power; efficiency converts it into stored battery energy. Health
    policy must not narrow physical availability. The latest-slot suggestion is
    separate, leaving the optimizer free to use the full available window.
    The battery is bounded physically and all unmet departure demand is reported.
    """
    if not windows:
        return []
    if ctx.capacity_kwh <= 0 or not 0 < ctx.charging_efficiency <= 1:
        raise ValueError("Capacity and charging efficiency must be positive")
    if ctx.charging_power_kw < 0 or not 0 <= ctx.safety_margin_percent <= 100:
        raise ValueError("Invalid charging power or safety margin")

    energies = [_trip_energy(w["trip"], ctx.consumption_kwh_per_km) for w in windows]
    slots = [
        max(0, int(w["def_end_timestep"]) - int(w["def_start_timestep"]))
        for w in windows
    ]
    targets = _departure_targets(energies, slots, windows, ctx)
    stored = ctx.capacity_kwh * max(0, min(100, ctx.soc_current)) / 100
    slot_energy = ctx.charging_power_kw * ctx.charging_efficiency
    reserve = ctx.capacity_kwh * ctx.safety_margin_percent / 100
    results = []
    chain_feasible = True
    previous_departure = ctx.now
    for w, consumption, available_slots, target in zip(
        windows, energies, slots, targets
    ):
        start_energy = stored
        elapsed = (
            max(0, w["fin_ventana"].timestamp() - previous_departure.timestamp()) / 3600
        )
        idle_rate = ctx.standby_soc_per_hour / 100 * ctx.capacity_kwh
        minimum_start = max(0, stored - elapsed * idle_rate)
        charge_needed = max(0.0, min(ctx.capacity_kwh, target) - minimum_start)
        required_hours = (
            math.ceil(max(0, charge_needed / slot_energy - 1e-9))
            if slot_energy > 0
            else 0
        )
        hours = min(required_hours, available_slots)
        stored = max(0, stored - max(0, elapsed - hours) * idle_rate)
        charged = min(ctx.capacity_kwh - stored, hours * slot_energy)
        departure_energy = stored + charged
        capacity_shortfall = max(0.0, target - ctx.capacity_kwh)
        charging_shortfall = max(0.0, min(ctx.capacity_kwh, target) - departure_energy)
        unserved = capacity_shortfall + charging_shortfall
        stored = max(0.0, departure_energy - consumption)
        feasible = unserved < 1e-6
        chain_feasible = chain_feasible and feasible
        # A suggested position, never a replacement for the physical window start.
        suggested_start = max(
            int(w["def_start_timestep"]),
            int(w["def_end_timestep"]) - hours,
        )
        results.append(
            {
                **w,
                "chain_energy_planned": True,
                "trip_energy_kwh": consumption,
                "kwh_necesarios": round(charge_needed, 6),
                "horas_carga_necesarias": required_hours,
                "adjusted_def_total_hours": hours,
                "suggested_charging_start_timestep": suggested_start,
                "soc_start": start_energy / ctx.capacity_kwh * 100,
                "soc_departure": departure_energy / ctx.capacity_kwh * 100,
                "soc_after_trip": stored / ctx.capacity_kwh * 100,
                "charged_energy_kwh": round(charged, 6),
                "energy_unserved_kwh": round(unserved, 6),
                "capacity_shortfall_kwh": round(capacity_shortfall, 6),
                "charging_shortfall_kwh": round(charging_shortfall, 6),
                "trip_shortfall_kwh": round(max(0, consumption - departure_energy), 6),
                "reserve_shortfall_kwh": round(max(0, reserve - stored), 6),
                "es_suficiente": feasible,
                "chain_feasible": chain_feasible,
                "charging_efficiency": ctx.charging_efficiency,
                "battery_capacity_kwh": ctx.capacity_kwh,
                "safety_margin_percent": ctx.safety_margin_percent,
            }
        )
        previous_departure = w["fin_ventana"]
    return results
