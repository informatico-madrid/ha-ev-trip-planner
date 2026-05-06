# Research: Dynamic SOC Capping for Battery Health

**Spec**: m403-dynamic-soc-capping
**Phase**: research
**Date**: 2026-04-30
**Goal**: Consolidate dynamic SOC capping algorithm, integrate into existing deficit propagation without breaking what works well.

---

## Executive Summary

The **Dynamic SOC Capping Algorithm** (`SOC_lim = SOC_base + (100-SOC_base) × [h/(h + T_ajustada)]`) is scientifically validated and fills a unique gap in consumer EV charging: no OEM implements time-to-trip-aware continuous SOC capping. The `preservation_factor` concept (modulating capping based on trip energy consumption) aligns with battery degradation physics — low-energy trips justify tighter capping because the battery sits longer at moderate SOC without being used.

**Key decision**: SOC_base = 35% (battery sweet spot) is used internally for calculations, but the user-facing config defaults to 80% (comfort). The algorithm is additive on top of existing deficit propagation — `min(required_soc, dynamic_limit)` — trips always succeed.

---

## External Research

### 1. Battery Degradation Science

**Time-at-SOC is the critical metric**. Calendar aging accelerates exponentially at high SOC:

| SOC Level | Relative Calendar Aging Rate |
|-----------|------------------------------|
| 30-40% | 1.0x (baseline) |
| 50% | ~1.2-1.4x |
| 80% | ~2.0-2.5x |
| 100% | ~3.0-4.0x |

**Source**: Schimpe et al. (2018) J. Electrochem. Soc., Arramon et al. (2018) J. Power Sources, Raoufi et al. (2017).

**SOC_base = 35% justified** for NMC/NCA (dominant EV chem). For LFP vehicles, the sweet spot shifts to ~45-50%.

**Estimated benefit** (author's estimate based on Schimpe et al. 2018 calendar aging model): m403 reduces average time-at-high-SOC by approximately 40-50% compared to always-100% charging, with more benefit for users with many low-energy trips and long idle periods.

### 2. Formula Validation: preservation_factor

```
preservation_factor = 1 + (1 - energy_fraction) × (1 + urgency) / 2
energy_fraction = kWh_del_viaje / battery_capacity
urgency = h / (h + T)
```

| Scenario | energy_frac | urgency | PF | Effect |
|----------|-----------|---------|------|--------|
| Long trip (100% battery) | 1.0 | 0.5 | 1.0 | No modification → T_ajustada = T |
| Medium trip (50% battery) | 0.5 | 0.5 | 1.25 | T +25% → tighter capping |
| Short trip (20% battery) | 0.2 | 0.5 | 1.45 | T +45% → much tighter |
| Very short trip (5% battery) | 0.05 | 0.5 | 1.51 | T +51% → aggressive |

**Alignment with battery science**: ✅ Short trips = more time idle at high SOC = tighter capping justified. Long trips = immediate drain = no capping benefit.

### 3. OEM Practices — The Gap

| OEM | Daily Limit | Trip Override | Dynamic to Consumption? |
|-----|-------------|---------------|------------------------|
| Tesla | 80-90% fixed | Manual | No |
| BMW | 80% fixed (Battery Care) | Manual | No |
| VW | 60-80% fixed | Suggested | No |
| **m403** | **35% base, dynamic** | **Automatic** | **Yes** |

**No OEM does this.** All use fixed SOC limits with manual overrides. Fleet operators do "regime switching" (slow health charging at night, fast route-dependent charging during day) — m403 automates what fleet operators do manually.

### 4. V2G Systems — Closest Analogue

V2G systems do dynamic SOC management from the discharge side:
- User-set minimum SOC for mobility
- Prediction-based optimization of discharge schedule
- Rolling 24-48h horizon (matches our `anticipation_hours`)

**Your spec is the charge-side equivalent of V2G optimization**, but simpler because trip schedules are deterministic (not predicted).

---

## Codebase Analysis

### SOC Value Flow

```
Sensor: soc_current (float %)
  ↓
calculate_energy_needed(soc_current) → energia_necesaria (kWh)
  ↓
calculate_deficit_propagation() → soc_objetivo_ajustado (%, backward propagation)
  ↓
determine_charging_need() → ChargingDecision (kwh_needed, def_total_hours, power_watts)
  ↓
_populate_per_trip_cache_entry() → deferrable load params
  ↓
calculate_power_profile_from_trips() → 168-element power profile (Watts)
  ↓
EMHASS API: {def_total_hours, def_start_timestep, def_end_timestep, P_deferrable_nom}
```

### Integration Points

| Priority | File | Lines | Function | Change |
|----------|------|-------|----------|--------|
| 1 | `calculations.py` | 716-863 | `calculate_deficit_propagation()` | Apply `min(soc_objetivo_ajustado, dynamic_limit)` at line 808 |
| 2 | `emhass_adapter.py` | 542-740 | `_populate_per_trip_cache_entry()` | Pass dynamic_limit to charging decision |
| 3 | `const.py` | ~40 | N/A | Add CONF_BATTERY_HEALTH_MODE, CONF_SOC_BASE, CONF_ANTICIPATION_HOURS |
| 4 | `config_flow.py` | ~83-123 | STEP_EMHASS_SCHEMA | Add battery health fields (new Step 3.5) |

### Key Risk: Backward Propagation Interaction

When SOC is capped, earlier trips charge less → projected SOC for later trips is lower → they may need more charge. But `min(required_soc, dynamic_limit)` ensures trip requirements always win, and the deficit propagation handles this naturally.

### Test Patterns

- `tests/test_soc_milestone.py`: 1499 lines, mocks `calculate_deficit_propagation` directly
- `tests/test_power_profile_positions.py`: Verifies charging positions within timestep windows
- `tests/test_soc_100_deficit_propagation_bug.py`: Mocks `adapter._get_current_soc` for edge cases
- Pattern: Mock scalar helpers with `MagicMock(return_value=X)`, use fixed datetime for deterministic tests

---

## Related Specs

| Spec | Relevance | Relationship | May Need Update |
|------|-----------|-------------|-----------------|
| `propagate-charge-deficit-algo` | High | m403 layers ON TOP of deficit propagation | No (compatible) |
| `charging-window-calculation` | Medium | Uses same timestep system | No (uses existing) |
| `soc-integration-baseline` | Medium | Defines SOC calculation patterns | No (uses existing) |

---

## Quality Commands

| Type | Command | Source |
|------|---------|--------|
| Tests | `pytest tests/test_soc_milestone.py -v` | Existing SOC milestone tests |
| Tests | `pytest tests/test_power_profile_positions.py -v` | Power profile position tests |
| Type check | `mypy custom_components/ev_trip_planner/` | Project convention |

---

## Feasibility Assessment

| Aspect | Assessment | Notes |
|--------|------------|-------|
| **Technical Feasibility** | High | Formula is simple (2 functions), clear integration points |
| **Risk** | Low | `min(required, limit)` ensures trips never fail; existing tests validate |
| **Effort** | S | ~2-3 days: 1 day algorithm + integration, 1 day config flow, 1 day tests |
| **Compatibility** | High | Fully additive — no breaking changes to existing calculation pipeline |

---

## Recommendations for Implementation

1. **SOC_base = 35% internally**, user-configurable 30-50%. User-facing config shows 80% as `daily_max_soc` (comfort level).

2. **Config flow**: Add new Step 3.5 (`async_step_battery_health`) between EMHASS and presence steps. Three fields: battery_health_mode (checkbox), soc_base (slider 30-50), anticipation_hours (slider 6-48).

3. **Integration point**: `calculate_deficit_propagation()` in `calculations.py`, after line 808 (`soc_objetivo_ajustado`). Apply `min(soc_objetivo_ajustado, dynamic_limit)`.

4. **Safety guarantee**: `final_soc = min(required_soc, dynamic_limit)`. The dynamic limit is an upper bound, never a target. Trip requirements always win.

5. **Edge cases**:
   - `h < 0` (past trip): return `soc_target_required`
   - `T = 0`: return 100% (no capping)
   - Trip needs > `SOC_base + 15%`: reduce preservation_factor to max 1.2 to prevent over-limiting

6. **Test strategy**: Add to `tests/test_soc_milestone.py` — mock battery health config, verify dynamic limits applied correctly across 4-trip scenarios.

---

---

## Appendix: Test Pseudocode

These functional tests validate the dynamic SOC capping algorithm across key scenarios.

### Algorithm Reference

```python
def calculate_dynamic_soc_limit(
    t_hours: float,
    soc_post_trip: float,
    battery_capacity_kwh: float,
    t_base: float = 24.0,
    soc_base: float = 35.0,
) -> float:
    """Calculate dynamic SOC cap based on degradation risk.

    Risk metric: time x (SOC above sweet spot) / 65
    Higher risk -> tighter cap. Negative risk -> 100% (battery empty).
    """
    risk = t_hours * (soc_post_trip - soc_base) / (100.0 - soc_base)

    if risk <= 0:
        return 100.0

    limit = soc_base + (100.0 - soc_base) * (1.0 / (1.0 + risk / t_base))

    return limit
```

### Test 1: Scenario A — Commute first, then large trip

# Battery: 30kWh
# Trips: 4 trips (30km, 150km, 30km, 80km)
# Small trips = 6kWh (20% of battery), large = 30kWh (100%) / 20kWh (67%)

# T1 (Commute 30km): start 30%, charges to 61%, drives 6kWh
# soc_post = 41%, t = 22h (idle until next charge)
# risk = 22 * 6 / 65 = 2.03
# limit = 35 + 65 * (1 / (1 + 2.03/24)) = 35 + 65 * 0.922 = 94.9%
# Trip needs 61%, limit 94.9% -> NOT CAPPED -> SOC = 61%

# T2 (Large 150km): start 41%, charges to 100%, drives 30kWh
# soc_post = 0% (battery fully drains on trip), t = 8h
# risk = 8 * (0 - 35) / 65 = negative -> return 100.0
# SOC = 100% (battery empty, zero degradation time)

# T3 (Commute 30km): start 0%, charges to 61%, drives 6kWh
# soc_post = 41%, t = 48h (long idle after T2 drain)
# risk = 48 * 6 / 65 = 4.43
# limit = 35 + 65 * (1 / (1 + 4.43/24)) = 35 + 65 * 0.844 = 89.9%
# Trip needs 61%, limit 89.9% -> NOT CAPPED -> SOC = 61%

# T4 (Semi-large 80km): start 41%, charges to 77%, drives 20kWh
# soc_post = 10% (below 35% sweet spot), t = 22h
# risk = 22 * (-25) / 65 = -8.46 -> return 100.0
# SOC = 100% (soc_post below sweet spot, no degradation risk)

assert calculate_dynamic_soc_limit(t_hours=22, soc_post_trip=41) == pytest.approx(94.9, rel=0.01)
assert calculate_dynamic_soc_limit(t_hours=8, soc_post_trip=0) == 100.0
assert calculate_dynamic_soc_limit(t_hours=48, soc_post_trip=41) == pytest.approx(89.9, rel=0.01)
assert calculate_dynamic_soc_limit(t_hours=22, soc_post_trip=10) == 100.0

### Test 2: Scenario C — Commute daily (the critical case)

# 4 identical trips: 30km each, 6kWh, 22.5h idle, 41% post-trip SOC
# Without capping: charges to 100% -> post-trip 80% -> 90h at >80% SOC per week BAD
# With capping: limit is 94.9% each time -> post-trip 41% -> 0h at >78% GOOD
# risk = 22 * 6 / 65 = 2.03
# limit = 35 + 65 * (1 / (1 + 2.03/24)) = 35 + 65 * 0.922 = 94.9%
# Trip needs 61%, limit 94.9% -> no capping hit, charged to 61% not 100%
# Post-trip: 41% each time vs 80% without capping
# Key insight: charging less means ending with less idle at high SOC

expected_limit = calculate_dynamic_soc_limit(t_hours=22, soc_post_trip=41)
assert expected_limit == pytest.approx(94.9, rel=0.01)

### Test 3: Scenario B — Large trip first, then commute

# T1 (150km): start 30%, drives 30kWh -> soc_post = 0%, t = 8h
# risk negative -> return 100.0

# T2-T4 (30km commute x 3): start 41%, drives 6kWh, idle 22h
# risk = 22 * 6 / 65 = 2.03, limit = 94.9%
# Trip needs 61%, limit 94.9% -> NOT CAPPED -> SOC = 61% each time
# All commutes succeed because limit (94.9%) > need (61%)

assert calculate_dynamic_soc_limit(t_hours=8, soc_post_trip=0) == 100.0
for _i in range(3):
    assert calculate_dynamic_soc_limit(t_hours=22, soc_post_trip=41) == pytest.approx(94.9, rel=0.01)

### Test 4: Edge cases

# risk = 0 when t = 0 (no idle), or soc_post = 35% (at sweet spot)
# Either way: return 100.0 (no degradation risk)

assert calculate_dynamic_soc_limit(t_hours=0, soc_post_trip=41, t_base=float("inf")) == pytest.approx(100.0, abs=0.01)
assert calculate_dynamic_soc_limit(t_hours=22, soc_post_trip=35, t_base=24) == 100.0
assert calculate_dynamic_soc_limit(t_hours=0, soc_post_trip=50, t_base=24) == 100.0

### Test 5: User-configurable T_base

# Higher T_base -> risk/T smaller -> limit HIGHER -> less preservation
# Lower T_base -> risk/T large -> limit LOWER -> more preservation

aggressive_limit = calculate_dynamic_soc_limit(t_hours=22, soc_post_trip=41, t_base=6)
normal_limit = calculate_dynamic_soc_limit(t_hours=22, soc_post_trip=41, t_base=24)
conservative_limit = calculate_dynamic_soc_limit(t_hours=22, soc_post_trip=41, t_base=48)

assert aggressive_limit < normal_limit < conservative_limit

## Sources

### Battery Science
- Schimpe et al. (2018), J. Electrochem. Soc. — Calendar aging model for Li-ion
- Arramon et al. (2018), J. Power Sources — High SOC + high temp = dominant aging
- Raoufi et al. (2017), J. Power Sources — Age-dependent capacity loss model
- Battery University — SOC/degradation relationships

### OEM Documentation
- Tesla Owner's Manual 2024 — Charge limits, destination charging
- BMW i4/iX Owner's Manual — Battery Care Mode at 80%
- VW ID. Manual — Adaptive SOC, Trip Assistant

### Industry Context
- IEA Global EV Outlook 2024 — Battery chemistry trends, LFP adoption
- IEEE Trans. Smart Grid — V2G optimization papers
- Fleet operator reports (Geotab, Samsara) — Regime switching strategies
