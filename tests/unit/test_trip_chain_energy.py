"""Regression: carry one battery through trips and preserve its return reserve."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.ev_trip_planner.calculations.window_pipeline import (
    PipelineContext,
    run_window_pipeline,
)
from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter
from custom_components.ev_trip_planner.emhass.time_grid import project_trip
from custom_components.ev_trip_planner.sensor.entity_emhass_deferrable import (
    EmhassDeferrableLoadSensor,
)

UTC = timezone.utc
MADRID = ZoneInfo("Europe/Madrid")
REFERENCE = datetime(2026, 10, 9, 10, tzinfo=UTC)


@pytest.fixture
def adapter(request):
    """Production-shaped configuration, with no HA services or storage writes."""
    patcher = pytest.MonkeyPatch()
    request.addfinalizer(patcher.undo)
    patcher.setattr(dt_util, "DEFAULT_TIME_ZONE", MADRID)
    patcher.setattr(dt_util, "now", lambda: REFERENCE.astimezone(MADRID))
    hass = MagicMock()
    hass.config.time_zone = "Europe/Madrid"
    hass.states.get.side_effect = lambda entity: SimpleNamespace(
        state="84" if entity == "sensor.soh" else "57"
    )
    entry = SimpleNamespace(
        entry_id="chain_test",
        data={
            "vehicle_name": "test",
            "battery_capacity_kwh": 28,
            "charging_power_kw": 3.4,
            "safety_margin_percent": 10,
            "soc_sensor": "sensor.soc",
            "kwh_per_km": 0.18,
        },
        options={"soh_sensor": "sensor.soh", "t_base": 6},
    )
    result = EMHASSAdapter(hass, entry)
    result._index_map = {"friday": 0, "monday": 1, "wednesday": 2, "saturday": 3}
    return result


def window(start, end, kwh, trip_id="trip"):
    """A window already resolved on the published hourly grid."""
    return {
        "trip": {"id": trip_id, "kwh": kwh},
        "ventana_horas": end - start,
        "horas_carga_necesarias": 1,
        "inicio_ventana": REFERENCE + timedelta(hours=start),
        "fin_ventana": REFERENCE + timedelta(hours=end),
        "def_start_timestep": start,
        "def_end_timestep": end,
        "planning_reference": REFERENCE.isoformat(),
    }


def context(**kwargs):
    """Small battery with exact power for independently checkable balances."""
    return PipelineContext(
        **{
            "charging_power_kw": 4,
            "battery_capacity_kwh": 20,
            "soc_current": 0,
            "t_base": 6,
            "now": REFERENCE,
            **kwargs,
        }
    )


@pytest.mark.parametrize(
    "past_departure",
    [
        "2026-10-23T18:00",
        "2026-10-23T16:00:00+00:00",
        "2026-10-27T10:00:00+00:00",
    ],
)
@pytest.mark.asyncio
async def test_expired_pending_trip_does_not_empty_current_soc(
    adapter, monkeypatch, past_departure
):
    """A past pending trip must not turn a measured 78% into a fictitious 0%."""
    now = datetime(2026, 10, 27, 10, tzinfo=UTC)
    monkeypatch.setattr(dt_util, "now", lambda: now.astimezone(MADRID))
    adapter.hass.states.get.side_effect = lambda entity: SimpleNamespace(
        state="82" if entity == "sensor.soh" else "78"
    )
    trips = [
        {
            "id": "expired",
            "tipo": "puntual",
            "estado": "pendiente",
            "datetime": past_departure,
            "kwh": 18,
        },
        {
            "id": "wednesday",
            "tipo": "recurrente",
            "dia_semana": "3",
            "hora": "07:30",
            "kwh": 26,
        },
    ]
    before = deepcopy(trips)

    await adapter.async_publish_all_deferrable_loads(trips)
    snapshot = adapter.get_cached_optimization_results()
    params = snapshot["per_trip_emhass_params"]

    assert "expired" not in params
    assert params["wednesday"]["soc_start"] == pytest.approx(78)
    assert params["wednesday"]["def_total_hours"] == 2
    assert params["wednesday"]["capacity_shortfall_kwh"] > 0
    coordinator = MagicMock()
    coordinator.data = snapshot
    attrs = EmhassDeferrableLoadSensor(coordinator, "test").extra_state_attributes
    assert attrs["trip_id_array"] == ["wednesday"]
    assert attrs["def_total_hours_array"] == [2]
    assert attrs["number_of_deferrable_loads"] == 1
    assert trips == before


@pytest.mark.asyncio
async def test_pending_trip_expires_at_its_exact_departure(adapter, monkeypatch):
    """A future trip with no full slot remains visible, then leaves the plan."""
    now = datetime(2026, 10, 27, 10, tzinfo=UTC)
    monkeypatch.setattr(dt_util, "now", lambda: now.astimezone(MADRID))
    trip = {
        "id": "soon",
        "tipo": "punctual",
        "estado": "pendiente",
        "datetime": "2026-10-27T11:15:00+01:00",
        "kwh": 18,
    }
    before = deepcopy(trip)
    await adapter.async_publish_all_deferrable_loads([trip])
    assert "soon" in adapter.get_cached_optimization_results()["per_trip_emhass_params"]

    now += timedelta(minutes=15)
    await adapter.async_publish_all_deferrable_loads([trip])
    snapshot = adapter.get_cached_optimization_results()
    assert snapshot["per_trip_emhass_params"] == {}
    assert snapshot["emhass_power_profile"] == []
    assert snapshot["emhass_deferrables_schedule"] == []
    assert trip == before


@pytest.mark.asyncio
async def test_monday_charges_from_empty_saturday_and_preserves_ten_percent(adapter):
    trips = [
        {
            "id": "friday",
            "tipo": "recurrente",
            "dia_semana": "5",
            "hora": "12:35",
            "kwh": 5,
        },
        {
            "id": "monday",
            "tipo": "recurrente",
            "dia_semana": "1",
            "hora": "13:30",
            "kwh": 8,
        },
        {
            "id": "wednesday",
            "tipo": "recurrente",
            "dia_semana": "3",
            "hora": "10:38",
            "kwh": 24,
        },
        {
            "id": "saturday",
            "tipo": "recurrente",
            "dia_semana": "6",
            "hora": "08:00",
            "kwh": 24,
        },
    ]
    original = deepcopy(trips)
    await adapter.async_publish_all_deferrable_loads(trips)
    snapshot = adapter.get_cached_optimization_results()
    params = snapshot["per_trip_emhass_params"]
    assert params["monday"]["def_total_hours"] == 4
    assert params["saturday"]["soc_after_trip"] == 0
    assert params["monday"]["soc_after_trip"] >= 10
    assert params["monday"]["energy_unserved_kwh"] == 0
    assert params["saturday"]["energy_unserved_kwh"] > 0
    # Availability remains Saturday's return -> Monday's departure, not t_base.
    assert params["monday"]["window_start"] == "2026-10-10T10:00:00+00:00"
    assert params["monday"]["def_start_timestep"] == 24
    assert params["monday"]["def_end_timestep"] == 73
    row = params["monday"]["p_deferrable_matrix"][0]
    assert [i for i, watts in enumerate(row) if watts > 0] == [69, 70, 71, 72]
    # These are the actual arrays consumed by both the panel and EMHASS payload.
    coordinator = MagicMock()
    coordinator.data = snapshot
    coordinator.vehicle_id = "test"
    attrs = EmhassDeferrableLoadSensor(coordinator, "test").extra_state_attributes
    monday = attrs["trip_id_array"].index("monday")
    assert attrs["def_start_timestep_array"][monday] == 24
    assert attrs["def_end_timestep_array"][monday] == 73
    assert attrs["def_total_hours_array"][monday] == 4
    assert trips == original


def test_one_trip_already_covered_does_not_charge_its_consumption_again():
    result = run_window_pipeline([window(0, 10, 5)], context(soc_current=60))[0]
    assert result["adjusted_def_total_hours"] == 0
    assert result["soc_after_trip"] == pytest.approx(35)
    assert result["energy_unserved_kwh"] == 0


def test_charge_is_carried_back_when_next_trip_has_no_charge_window():
    windows = [window(0, 10, 8, "first"), window(10, 10, 5, "second")]
    before = deepcopy(windows)
    result = run_window_pipeline(windows, context())
    assert [r["adjusted_def_total_hours"] for r in result] == [4, 0]
    assert result[0]["soc_after_trip"] == pytest.approx(40)
    assert result[1]["soc_after_trip"] == pytest.approx(15)
    assert all(r["energy_unserved_kwh"] == 0 for r in result)
    assert windows == before


def test_capacity_conflict_is_visible_and_never_schedules_unstorable_energy():
    result = run_window_pipeline(
        [window(0, 10, 8), window(10, 10, 8)], context(battery_capacity_kwh=10)
    )
    assert result[0]["soc_departure"] == 100
    assert result[0]["capacity_shortfall_kwh"] > 0
    assert result[1]["energy_unserved_kwh"] > 0
    assert all(0 <= r["soc_after_trip"] <= 100 for r in result)


def test_short_window_reports_original_demand_and_uses_only_available_slots():
    result = run_window_pipeline(
        [window(0, 2, 8)], context(battery_capacity_kwh=10, charging_power_kw=2)
    )[0]
    assert result["adjusted_def_total_hours"] == 2
    assert result["energy_unserved_kwh"] == pytest.approx(5)
    assert not result["es_suficiente"]


def test_rounding_surplus_is_carried_forward_instead_of_charging_twice():
    result = run_window_pipeline([window(0, 10, 3), window(14, 20, 3)], context())
    assert [r["adjusted_def_total_hours"] for r in result] == [2, 0]
    assert result[1]["soc_after_trip"] >= 10


def test_available_window_is_independent_of_the_suggested_charging_position():
    result = run_window_pipeline([window(0, 50, 8)], context())[0]
    assert result["adjusted_def_total_hours"] == 3
    assert result["def_start_timestep"] == 0
    assert result["def_end_timestep"] == 50
    assert result["suggested_charging_start_timestep"] == 47
    assert result["soc_after_trip"] >= 10


def test_explicit_zero_and_configured_distance_consumption():
    windows = [window(0, 10, 0)]
    windows[0]["trip"]["km"] = 100
    assert (
        run_window_pipeline(windows, context(soc_current=10))[0][
            "adjusted_def_total_hours"
        ]
        == 0
    )
    del windows[0]["trip"]["kwh"]
    result = run_window_pipeline(windows, context(consumption_kwh_per_km=0.18))[0]
    assert result["trip_energy_kwh"] == 18
    assert result["adjusted_def_total_hours"] == 5


def test_standby_cannot_erode_a_reserve_that_was_exactly_covered():
    result = run_window_pipeline(
        [window(0, 10, 3)], context(soc_current=25, standby_soc_per_hour=0.02)
    )[0]
    assert result["adjusted_def_total_hours"] == 1
    assert result["soc_after_trip"] >= 10


def test_grid_projection_preserves_energy_shortfalls_from_the_chain():
    params = {
        "window_start": REFERENCE.isoformat(),
        "deadline": (REFERENCE + timedelta(hours=3)).isoformat(),
        "def_total_hours": 2,
        "configured_power_watts": 3400,
        "energy_unserved_kwh": 2.832,
    }
    result = project_trip(params, REFERENCE, 168, REFERENCE)
    assert result["unserved_energy_kwh"] == pytest.approx(2.832)


@pytest.mark.asyncio
async def test_battery_arrival_invalidates_soh_cache_and_republishes_plan(adapter):
    schedule = SimpleNamespace(publish_deferrable_loads=AsyncMock())
    coordinator = SimpleNamespace(async_refresh_trips=AsyncMock())
    adapter._entry.runtime_data = SimpleNamespace(
        trip_manager=SimpleNamespace(_schedule=schedule), coordinator=coordinator
    )
    adapter._load_publisher._battery_cap._soh_cached_at = REFERENCE
    event = SimpleNamespace(
        data={"old_state": None, "new_state": SimpleNamespace(state="84")}
    )
    await adapter._handle_battery_state_change(event)
    assert adapter._load_publisher._battery_cap._soh_cached_at is None
    schedule.publish_deferrable_loads.assert_awaited_once()
    coordinator.async_refresh_trips.assert_awaited_once()


@pytest.mark.asyncio
async def test_battery_attributes_only_or_unavailable_do_not_replan(adapter):
    schedule = SimpleNamespace(publish_deferrable_loads=AsyncMock())
    adapter._entry.runtime_data = SimpleNamespace(
        trip_manager=SimpleNamespace(_schedule=schedule), coordinator=AsyncMock()
    )
    for state in ("84", "unavailable", "nan"):
        event = SimpleNamespace(
            data={
                "old_state": SimpleNamespace(state="84"),
                "new_state": SimpleNamespace(state=state),
            }
        )
        await adapter._handle_battery_state_change(event)
    schedule.publish_deferrable_loads.assert_not_awaited()


def test_battery_listener_is_registered_for_configured_soc_and_soh_and_unloaded(
    adapter,
):
    entry = MagicMock()
    entry.data = adapter._entry.data
    entry.options = adapter._entry.options
    adapter.hass.config_entries.async_get_entry.return_value = entry
    with patch(
        "custom_components.ev_trip_planner.emhass.adapter.async_track_state_change_event"
    ) as track:
        adapter.setup_config_entry_listener()
    track.assert_called_once_with(
        adapter.hass, ["sensor.soc", "sensor.soh"], adapter._handle_battery_state_change
    )
    entry.async_on_unload.assert_any_call(track.return_value)
