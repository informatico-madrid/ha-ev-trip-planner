"""Regression: a local 12:35 departure must never permit a later full slot."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.ev_trip_planner.calculations.core import calculate_trip_time
from custom_components.ev_trip_planner.emhass.adapter import (
    EMHASSAdapter,
    PerTripCacheParams,
)
from custom_components.ev_trip_planner.emhass.load_publisher import LoadPublisher
from custom_components.ev_trip_planner.emhass.time_grid import (
    planning_reference,
    window_slots,
)

MADRID = ZoneInfo("Europe/Madrid")


def make_adapter():
    """Build an isolated adapter; no Home Assistant server or real services."""
    hass = MagicMock()
    hass.config.time_zone = "Europe/Madrid"
    hass.states.get.return_value = SimpleNamespace(state="51", attributes={})
    entry = SimpleNamespace(
        entry_id="test",
        data={
            "vehicle_name": "test",
            "battery_capacity_kwh": 28,
            "charging_power_kw": 3.4,
            "safety_margin_percent": 10,
            "soc_sensor": "sensor.test_soc",
        },
        options={},
    )
    return EMHASSAdapter(hass, entry)


@pytest.mark.asyncio
async def test_friday_1235_window_excludes_hour_12_to_13(monkeypatch):
    now = datetime(2026, 10, 9, 8, 5, 28, tzinfo=MADRID)
    departure = datetime(2026, 10, 9, 12, 35, tzinfo=MADRID)
    monkeypatch.setattr(dt_util, "DEFAULT_TIME_ZONE", MADRID)
    monkeypatch.setattr(dt_util, "now", lambda: now)
    adapter = make_adapter()
    adapter._index_map = {"friday": 0}
    trip = {
        "id": "friday",
        "tipo": "recurrente",
        "dia_semana": "5",
        "hora": "12:35",
        "kwh": 5,
    }
    await adapter._populate_per_trip_cache_entry(
        PerTripCacheParams(trip, "friday", 3.4, 28, 10, 51),
        pre_computed_inicio_ventana=now,
        pre_computed_fin_ventana=departure,
    )
    params = adapter._cached_per_trip_params["friday"]
    # EMHASS nearest-hour grid starts at 08:00 here. End is exclusive.
    assert params["def_end_timestep"] == 4
    assert params["p_deferrable_matrix"][0][4] == 0
    assert params["deadline"] == departure.astimezone(timezone.utc).isoformat()


@pytest.mark.asyncio
async def test_cached_window_rebases_when_optimizer_grid_advances(monkeypatch):
    now = datetime(2026, 10, 9, 8, 5, 28, tzinfo=MADRID)
    departure = datetime(2026, 10, 9, 12, 35, tzinfo=MADRID)
    monkeypatch.setattr(dt_util, "DEFAULT_TIME_ZONE", MADRID)
    adapter = make_adapter()
    adapter._index_map = {"friday": 0}
    trip = {
        "id": "friday",
        "tipo": "recurrente",
        "dia_semana": "5",
        "hora": "12:35",
        "kwh": 5,
    }
    with patch.object(dt_util, "now", return_value=now):
        await adapter._populate_per_trip_cache_entry(
            PerTripCacheParams(trip, "friday", 3.4, 28, 10, 51),
            pre_computed_inicio_ventana=now,
            pre_computed_fin_ventana=departure,
        )
    with patch.object(dt_util, "now", return_value=now.replace(minute=31)):
        snapshot = adapter.get_cached_optimization_results()
    params = snapshot["per_trip_emhass_params"]["friday"]
    reference = datetime.fromisoformat(snapshot["emhass_planning_reference"])
    assert reference.astimezone(MADRID).hour == 9
    assert params["def_end_timestep"] == 3
    assert reference + timedelta(hours=params["def_end_timestep"]) <= departure
    assert snapshot["emhass_power_profile"][3] == 0
    # Reading a new projection does not modify the published calculation cache.
    assert adapter._cached_per_trip_params["friday"]["def_end_timestep"] == 4


@pytest.mark.asyncio
async def test_no_complete_slot_means_no_unconstrained_emhass_load(monkeypatch):
    now = datetime(2026, 10, 9, 8, 5, tzinfo=MADRID)
    departure = datetime(2026, 10, 9, 12, 35, tzinfo=MADRID)
    monkeypatch.setattr(dt_util, "DEFAULT_TIME_ZONE", MADRID)
    adapter = make_adapter()
    adapter._index_map = {"friday": 0}
    trip = {
        "id": "friday",
        "tipo": "recurrente",
        "dia_semana": "5",
        "hora": "12:35",
        "kwh": 5,
    }
    with patch.object(dt_util, "now", return_value=now):
        await adapter._populate_per_trip_cache_entry(
            PerTripCacheParams(trip, "friday", 3.4, 28, 10, 31),
            pre_computed_inicio_ventana=now,
            pre_computed_fin_ventana=departure,
        )
    with patch.object(dt_util, "now", return_value=now.replace(hour=12, minute=5)):
        snapshot = adapter.get_cached_optimization_results()
    params = snapshot["per_trip_emhass_params"]["friday"]
    assert params["def_end_timestep"] == 0
    assert params["def_total_hours"] == 0
    assert params["power_watts"] == 0
    assert not any(params["p_deferrable_matrix"][0])
    assert params["unserved_energy_kwh"] > 0


@pytest.mark.parametrize("month,day,offset", [(10, 9, 2), (12, 11, 1)])
def test_punctual_naive_datetime_is_local_ha_time(monkeypatch, month, day, offset):
    monkeypatch.setattr(dt_util, "DEFAULT_TIME_ZONE", MADRID)
    publisher = object.__new__(LoadPublisher)
    departure = publisher._calculate_deadline(
        {"tipo": "puntual", "datetime": f"2026-{month:02}-{day:02}T12:35"}
    )
    assert departure.astimezone(MADRID).hour == 12
    assert departure.astimezone(MADRID).minute == 35
    assert departure.astimezone(timezone.utc).hour == 12 - offset


def test_explicit_utc_offset_is_preserved_for_punctual_trips(monkeypatch):
    monkeypatch.setattr(dt_util, "DEFAULT_TIME_ZONE", MADRID)
    publisher = object.__new__(LoadPublisher)
    departure = publisher._calculate_deadline(
        {"tipo": "puntual", "datetime": "2026-10-09T10:35:00+00:00"}
    )
    assert departure == datetime(2026, 10, 9, 10, 35, tzinfo=timezone.utc)


def test_recurring_trip_rolls_next_week_after_minutes_passed_in_same_hour():
    now = datetime(2026, 10, 9, 12, 36, tzinfo=MADRID)
    departure = calculate_trip_time("recurrente", "12:35", "5", None, now, MADRID)
    assert departure.astimezone(MADRID).date().isoformat() == "2026-10-16"


def test_pure_punctual_calculation_honors_supplied_timezone():
    now = datetime(2026, 10, 9, 8, tzinfo=MADRID)
    departure = calculate_trip_time(
        "puntual", None, None, "2026-10-09T12:35", now, MADRID
    )
    assert departure == datetime(2026, 10, 9, 10, 35, tzinfo=timezone.utc)


def test_elapsed_slot_count_accounts_for_autumn_dst_change():
    reference = datetime(2026, 10, 24, 12, tzinfo=MADRID)
    departure = datetime(2026, 10, 25, 12, tzinfo=MADRID)
    first, end = window_slots(reference, departure, reference, 168)
    assert first == 0
    assert end == 25
    assert reference.astimezone(timezone.utc) + timedelta(hours=end) == departure


@pytest.mark.parametrize("minute,expected_hour", [(5, 8), (29, 8), (31, 9), (55, 9)])
def test_reference_matches_nearest_hour_forecast_grid(minute, expected_hour):
    now = datetime(2026, 10, 9, 8, minute, tzinfo=MADRID)
    assert planning_reference(now).astimezone(MADRID).hour == expected_hour
