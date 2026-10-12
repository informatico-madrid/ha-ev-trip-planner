"""Anticipate future trip energy without losing the single-battery balance."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.ev_trip_planner.calculations.energy_chain import (
    EnergyChainContext,
    plan_energy_chain,
)
from custom_components.ev_trip_planner.calculations.window_pipeline import (
    PipelineContext,
    run_window_pipeline,
)
from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter
from custom_components.ev_trip_planner.sensor.entity_emhass_deferrable import (
    EmhassDeferrableLoadSensor,
)

REFERENCE = datetime(2026, 10, 12, 8, tzinfo=timezone.utc)


def windows_for(energies):
    """Monday -> Tuesday 08:30, Wednesday 07:30, Thursday 07:30 in Madrid."""
    return [
        {
            "trip": {"id": f"trip{i}", "kwh": energy},
            "inicio_ventana": REFERENCE + timedelta(hours=start),
            "fin_ventana": REFERENCE + timedelta(hours=end),
            "ventana_horas": end - start,
            "def_start_timestep": int(start + 0.5),
            "def_end_timestep": int(end),
            "planning_reference": REFERENCE.isoformat(),
        }
        for i, (energy, (start, end)) in enumerate(
            zip(energies, [(0, 22.5), (26.5, 45.5), (49.5, 69.5)])
        )
    ]


def context(**overrides):
    """Production battery convention: SOH 83%, SOC 43%, 3.4 kW, 85% efficiency."""
    return PipelineContext(
        **{
            "battery_capacity_kwh": 23.24,
            "charging_power_kw": 3.4,
            "charging_efficiency": 0.85,
            "soc_current": 43,
            "safety_margin_percent": 10,
            "consumption_kwh_per_km": 0.18,
            "standby_soc_per_hour": 0.02,
            "t_base": 15,
            "now": REFERENCE,
            **overrides,
        }
    )


@pytest.fixture
def adapter(request):
    """Exercise the real publication path without services or storage writes."""
    patcher = pytest.MonkeyPatch()
    request.addfinalizer(patcher.undo)
    patcher.setattr(dt_util, "DEFAULT_TIME_ZONE", ZoneInfo("Europe/Madrid"))
    patcher.setattr(
        dt_util, "now", lambda: REFERENCE.astimezone(dt_util.DEFAULT_TIME_ZONE)
    )
    hass = MagicMock()
    hass.config.time_zone = "Europe/Madrid"
    hass.states.get.side_effect = lambda entity: SimpleNamespace(
        state="83" if entity == "sensor.soh" else "43"
    )
    entry = SimpleNamespace(
        entry_id="anticipation_test",
        data={
            "vehicle_name": "test",
            "battery_capacity_kwh": 28,
            "charging_power_kw": 3.4,
            "safety_margin_percent": 10,
            "soc_sensor": "sensor.soc",
            "kwh_per_km": 0.18,
            "planning_horizon_days": 7,
        },
        options={"soh_sensor": "sensor.soh", "t_base": 15},
    )
    result = EMHASSAdapter(hass, entry)
    result._index_map = {f"trip{i}": i for i in range(3)}
    return result


@pytest.mark.parametrize("t_base, expected_hours", [(6, 1), (15, 2), (24, 2), (48, 3)])
def test_chispitas_can_anticipate_tuesday_with_effective_t_base(t_base, expected_hours):
    windows = windows_for([6, 26, 26])
    before = deepcopy(windows)
    results = run_window_pipeline(windows, context(t_base=t_base))
    assert results[0]["adjusted_def_total_hours"] == expected_hours
    assert results[0]["soc_departure"] > 43
    assert results[1]["soc_start"] == pytest.approx(results[0]["soc_after_trip"])
    assert results[1]["capacity_shortfall_kwh"] == pytest.approx(5.084)
    assert results[2]["capacity_shortfall_kwh"] == pytest.approx(5.084)
    assert not results[-1]["chain_feasible"]
    assert windows == before


def test_anticipation_moves_energy_earlier_instead_of_requesting_it_again():
    results = run_window_pipeline(windows_for([6, 18, 18]), context())
    assert [r["adjusted_def_total_hours"] for r in results] == [2, 4, 6]
    assert sum(r["charged_energy_kwh"] for r in results) == pytest.approx(12 * 2.89)
    initial = 23.24 * 0.43
    standby = sum(
        (duration - r["adjusted_def_total_hours"]) * 23.24 * 0.0002
        for duration, r in zip([22.5, 23, 24], results)
    )
    final = initial + 12 * 2.89 - 42 - standby
    assert results[-1]["soc_after_trip"] == pytest.approx(final / 23.24 * 100)
    assert all(r["soc_after_trip"] >= 10 for r in results)
    assert all(r["energy_unserved_kwh"] == 0 for r in results)


def test_covered_single_trip_and_covered_whole_chain_request_no_extra_energy():
    single = run_window_pipeline(windows_for([6]), context())
    covered = run_window_pipeline(windows_for([2, 2, 2]), context(soc_current=80))
    assert single[0]["adjusted_def_total_hours"] == 0
    assert [r["adjusted_def_total_hours"] for r in covered] == [0, 0, 0]


def test_optional_rounding_cannot_exceed_battery_or_future_demand():
    results = run_window_pipeline(
        windows_for([1, 1]),
        context(
            battery_capacity_kwh=10,
            charging_power_kw=4,
            charging_efficiency=1,
            standby_soc_per_hour=0,
            soc_current=80,
            t_base=48,
        ),
    )
    assert [r["adjusted_def_total_hours"] for r in results] == [0, 0]
    assert all(r["soc_departure"] <= 100 for r in results)


def test_insufficient_future_demand_does_not_justify_an_extra_full_slot():
    results = run_window_pipeline(
        windows_for([1, 3]),
        context(
            battery_capacity_kwh=10,
            charging_power_kw=4,
            charging_efficiency=1,
            standby_soc_per_hour=0,
            soc_current=40,
            t_base=48,
        ),
    )
    assert [r["adjusted_def_total_hours"] for r in results] == [0, 1]
    assert results[0]["soc_departure"] == 40


def test_health_cap_uses_projected_charging_and_does_not_discharge_high_soc():
    windows = windows_for([1, 100])
    windows[0].update(
        ventana_horas=10,
        def_end_timestep=10,
        fin_ventana=REFERENCE + timedelta(hours=10),
    )
    results = run_window_pipeline(
        windows,
        context(
            battery_capacity_kwh=100,
            charging_power_kw=1,
            charging_efficiency=1,
            standby_soc_per_hour=0,
            soc_current=90,
            t_base=48,
        ),
    )
    # Filling the available headroom would leave 99% after the first trip.
    # The post-trip health cap forbids that optional charge, not the trip.
    assert results[0]["adjusted_def_total_hours"] == 0
    assert results[0]["soc_departure"] == 90
    assert results[0]["soc_after_trip"] == 89
    assert results[1]["adjusted_def_total_hours"] > 0
    assert results[1]["capacity_shortfall_kwh"] == 10


def test_zero_charging_power_preserves_demand_and_reports_shortfalls():
    results = run_window_pipeline(windows_for([6, 18]), context(charging_power_kw=0))
    assert [r["adjusted_def_total_hours"] for r in results] == [0, 0]
    assert results[-1]["energy_unserved_kwh"] > 0
    assert not results[-1]["chain_feasible"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"capacity_kwh": 0},
        {"charging_efficiency": 0},
        {"charging_efficiency": 1.1},
        {"charging_power_kw": -1},
        {"safety_margin_percent": 101},
    ],
)
def test_invalid_energy_context_is_rejected_and_empty_plan_is_safe(overrides):
    ctx = EnergyChainContext(
        **{
            "capacity_kwh": 23.24,
            "charging_power_kw": 3.4,
            "soc_current": 43,
            "safety_margin_percent": 10,
            "consumption_kwh_per_km": 0.18,
            "charging_efficiency": 0.85,
            "now": REFERENCE,
            **overrides,
        }
    )
    assert plan_energy_chain([], ctx) == []
    with pytest.raises(ValueError):
        plan_energy_chain(windows_for([6, 18]), ctx)


def test_explicit_zero_stays_zero_and_invalid_consumption_is_not_hidden():
    windows = windows_for([0, 18])
    windows[0]["trip"]["km"] = 100
    results = run_window_pipeline(windows, context())
    assert results[0]["trip_energy_kwh"] == 0
    assert results[0]["soc_after_trip"] == results[0]["soc_departure"]
    windows[0]["trip"]["kwh"] = -1
    with pytest.raises(ValueError, match="Trip energy"):
        run_window_pipeline(windows, context())


def test_resolved_slots_still_work_without_the_optional_window_duration():
    windows = windows_for([6, 18, 18])
    for window in windows:
        del window["ventana_horas"]
    results = run_window_pipeline(windows, context())
    assert [r["adjusted_def_total_hours"] for r in results] == [2, 4, 6]
    assert all(r["soc_after_trip"] >= 10 for r in results)


@pytest.mark.parametrize("t_base", [6, 15, 48])
def test_t_base_never_reduces_mandatory_charge_or_physical_windows(t_base):
    windows = windows_for([6, 18, 18])
    results = run_window_pipeline(windows, context(soc_current=0, t_base=t_base))
    assert results[0]["adjusted_def_total_hours"] >= 3
    assert all(r["soc_after_trip"] >= 10 for r in results)
    assert all(r["energy_unserved_kwh"] == 0 for r in results)
    assert [(r["def_start_timestep"], r["def_end_timestep"]) for r in results] == [
        (w["def_start_timestep"], w["def_end_timestep"]) for w in windows
    ]


@pytest.mark.parametrize("t_base", [0, -1, float("nan"), float("inf")])
def test_invalid_t_base_fails_explicitly(t_base):
    with pytest.raises(ValueError, match="t_base"):
        run_window_pipeline(windows_for([6, 18]), context(t_base=t_base))


@pytest.mark.asyncio
async def test_published_arrays_and_matrix_include_anticipation_and_surplus(adapter):
    trips = [
        {
            "id": f"trip{i}",
            "tipo": "recurrente",
            "dia_semana": str(i + 2),
            "hora": "08:30" if i == 0 else "07:30",
            "kwh": energy,
        }
        for i, energy in enumerate([6, 18, 18])
    ]
    before = deepcopy(trips)
    await adapter.async_publish_all_deferrable_loads(trips)
    coordinator = MagicMock()
    coordinator.data = adapter.get_cached_optimization_results()
    coordinator.vehicle_id = "test"
    attrs = EmhassDeferrableLoadSensor(coordinator, "test").extra_state_attributes
    assert attrs["def_total_hours_array"] == [2, 4, 6]
    assert attrs["p_deferrable_nom_array"] == [3400, 3400, 3400]
    assert attrs["def_start_timestep_array"] == [0, 27, 50]
    assert attrs["def_end_timestep_array"] == [22, 45, 69]
    assert [
        sum(watts > 0 for watts in row) for row in attrs["p_deferrable_matrix"]
    ] == [2, 4, 6]
    expected_soc = 43 + (2 * 3.4 * 0.85 / 23.24) * 100 - (22.5 - 2) * 0.02
    assert attrs["soc_departure_array"][0] == pytest.approx(expected_soc)
    assert all(soc >= 10 for soc in attrs["soc_after_trip_array"])
    assert trips == before
