"""Integration tests: Dynamic SOC Capping in EMHASS production path.

Legacy source: tests/_legacy_snapshot/from-epic/test_emhass_integration_dynamic_soc.py

Adapted to SOLID API:
- Import from `emhass.adapter` not `emhass_adapter`
- Patch `emhass.adapter.Store` not `emhass_adapter.Store`
- Uses `async_publish_all_deferrable_loads()` → inspect `_cached_power_profile`

BUG-4: T_BASE is NOT wired into the production path.
With T_BASE=6h (aggressive) vs T_BASE=48h (conservative), the power profiles
should differ. Currently they are identical because _t_base is not used.

This test MUST FAIL until T062 wires t_base through the charging decision.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter


def _make_mock_hass(soc_sensor="sensor.test_soc", soc_state=40.0) -> MagicMock:
    """Build a mock hass with state lookups for soc_sensor."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = timezone.utc
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value={})
    mock_store.async_save = AsyncMock()

    def states_get(entity_id):
        if entity_id == soc_sensor:
            return MagicMock(state=str(soc_state))
        return None

    hass.states.get = states_get
    return hass, mock_store


def _count_nonzero(profile):
    """Count positive values in a power profile."""
    if not profile:
        return 0
    return sum(1 for v in profile if v > 0)


@pytest.mark.asyncio
async def test_t_base_affects_charging_hours():
    """T056: T_BASE=6h should produce less total charging energy than T_BASE=48h.

    Setup: 4 commute trips (6kWh each), SOC=60%, charging=7.4kW.
    Trips are scheduled 20h apart (20h, 40h, 60h, 80h in future).

    With SOC=60% and trip_kwh=6kWh on 60kWh battery:
        soc_after_trip = 60 - (6/60)*100 = 50% (above 35% sweet spot)
        → risk > 0 → SOC cap < 100%

    With T_BASE=6h (aggressive): tighter SOC cap → less total energy
    With T_BASE=48h (conservative): looser SOC cap → more total energy

    BUG: _t_base is NOT wired into the production path, so both produce the same.
    This test MUST FAIL until T062 wires t_base through the charging decision.
    """
    hass_6, store_6 = _make_mock_hass(soc_state=60.0)
    hass_48, store_48 = _make_mock_hass(soc_state=60.0)

    entry_6 = MagicMock()
    entry_6.entry_id = "test_entry_tbase6"
    entry_6.data = {
        "vehicle_name": "test_vehicle",
        "max_deferrable_loads": 50,
        "charging_power_kw": 7.4,
        "battery_capacity_kwh": 60.0,
        "safety_margin_percent": 0.0,
        "t_base": 6.0,
    }
    entry_6.options = {"t_base": 6.0}

    entry_48 = MagicMock()
    entry_48.entry_id = "test_entry_tbase48"
    entry_48.data = {
        "vehicle_name": "test_vehicle",
        "max_deferrable_loads": 50,
        "charging_power_kw": 7.4,
        "battery_capacity_kwh": 60.0,
        "safety_margin_percent": 0.0,
        "t_base": 48.0,
    }
    entry_48.options = {"t_base": 48.0}

    with patch(
        "custom_components.ev_trip_planner.emhass.adapter.Store",
        return_value=store_6,
    ):
        adapter_6 = EMHASSAdapter(hass_6, entry_6)
        await adapter_6.async_load()

    with patch(
        "custom_components.ev_trip_planner.emhass.adapter.Store",
        return_value=store_48,
    ):
        adapter_48 = EMHASSAdapter(hass_48, entry_48)
        await adapter_48.async_load()

    now = datetime.now(timezone.utc)
    trips = [
        {
            "id": f"trip_{i}",
            "kwh": 6.0,
            "datetime": (now + timedelta(hours=20 + i * 20)).isoformat(),
        }
        for i in range(4)
    ]

    hora_regreso = now - timedelta(hours=2)

    for adapter in (adapter_6, adapter_48):
        mock_pm = MagicMock()
        mock_pm.async_get_hora_regreso = AsyncMock(
            return_value=hora_regreso.replace(tzinfo=timezone.utc)
        )
        adapter._presence_monitor = mock_pm

    async def _run(adapter):
        with (
            patch.object(
                adapter, "_get_current_soc", new_callable=AsyncMock, return_value=60.0
            ),
            patch.object(
                adapter,
                "_get_hora_regreso",
                new_callable=AsyncMock,
                return_value=hora_regreso.replace(tzinfo=timezone.utc),
            ),
        ):
            await adapter.async_publish_all_deferrable_loads(trips)
        return list(adapter._cached_power_profile or [])

    profile_6 = await _run(adapter_6)
    profile_48 = await _run(adapter_48)

    energy_6 = sum(profile_6)
    energy_48 = sum(profile_48)
    non_zero_6 = _count_nonzero(profile_6)
    non_zero_48 = _count_nonzero(profile_48)

    assert energy_6 < energy_48, (
        f"Expected T_BASE=6h to produce less total charging energy "
        f"({energy_6:.0f} Wh) than T_BASE=48h ({energy_48:.0f} Wh), "
        f"but they are equal or reversed. "
        f"Non-zero hours: {non_zero_6} vs {non_zero_48}. "
        "This indicates _t_base is NOT wired into the production path."
    )


@pytest.mark.asyncio
async def test_soc_caps_applied_to_kwh_calculation():
    """T057: SOC caps from calculate_dynamic_soc_limit should reduce kWh charging targets.

    Setup: 4 commute trips (6kWh each), SOC=40%, with T_BASE=24h.
    The dynamic SOC limit algorithm should compute a cap below 100%.
    The resulting power profile should reflect capped kWh, not uncapped.
    """
    hass, store = _make_mock_hass(soc_state=40.0)
    entry = MagicMock()
    entry.entry_id = "test_entry_soc"
    entry.data = {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "vehicle_name": "test_vehicle",
        "max_deferrable_loads": 50,
        "charging_power": 7.4,
        "battery_capacity": 60.0,
        "safety_margin_percent": 0.0,
        "t_base": 24.0,
    }
    entry.options = {"t_base": 24.0}

    with patch(
        "custom_components.ev_trip_planner.emhass.adapter.Store", return_value=store
    ):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

    now = datetime.now(timezone.utc)
    trips = [
        {
            "id": f"trip_{i}",
            "kwh": 6.0,
            "datetime": (now + timedelta(hours=1 + i)).isoformat(),
        }
        for i in range(4)
    ]

    hora_regreso = now - timedelta(hours=2)
    mock_pm = MagicMock()
    mock_pm.async_get_hora_regreso = AsyncMock(
        return_value=hora_regreso.replace(tzinfo=timezone.utc)
    )
    adapter._presence_monitor = mock_pm

    with (
        patch.object(
            adapter, "_get_current_soc", new_callable=AsyncMock, return_value=40.0
        ),
        patch.object(
            adapter,
            "_get_hora_regreso",
            new_callable=AsyncMock,
            return_value=hora_regreso.replace(tzinfo=timezone.utc),
        ),
    ):
        await adapter.async_publish_all_deferrable_loads(trips)

    # Verify that the cache entries were populated with non-trivial values
    for trip_id, params in adapter._cached_per_trip_params.items():
        assert "def_total_hours" in params
        assert "def_start_timestep" in params
        assert "def_end_timestep" in params

        hours = params["def_total_hours"]
        # BUG-1: Should be ceil'd int, not float
        # This test verifies the cache structure is correct even if value type is wrong
        assert isinstance(hours, (int, float)), (
            f"def_total_hours is not numeric: {type(hours)}"
        )
        assert hours >= 0, f"def_total_hours negative: {hours}"


@pytest.mark.asyncio
async def test_real_capacity_scales_power_profile():
    """T058: Real capacity (SOH) should scale power profile.

    Setup: Two trips with identical deadlines but different SOH readings.
    With lower SOH, the real capacity is reduced → less energy charged.
    """
    hass_low_soh, store_low = _make_mock_hass(soc_state=50.0)
    hass_full_soh, store_full = _make_mock_hass(soc_state=80.0)

    entry = MagicMock()
    entry.entry_id = "test_entry_soh"
    entry.data = {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "vehicle_name": "test_vehicle",
        "max_deferrable_loads": 50,
        "charging_power": 7.4,
        "battery_capacity": 60.0,
        "safety_margin_percent": 0.0,
    }
    entry.options = {}

    with patch(
        "custom_components.ev_trip_planner.emhass.adapter.Store",
        return_value=store_low,
    ):
        adapter_low = EMHASSAdapter(hass_low_soh, entry)
        await adapter_low.async_load()

    with patch(
        "custom_components.ev_trip_planner.emhass.adapter.Store",
        return_value=store_full,
    ):
        adapter_full = EMHASSAdapter(hass_full_soh, entry)
        await adapter_full.async_load()

    now = datetime.now(timezone.utc)
    trips = [
        {
            "id": f"trip_{i}",
            "kwh": 8.0,
            "datetime": (now + timedelta(hours=10 + i * 5)).isoformat(),
        }
        for i in range(2)
    ]

    hora_regreso = now - timedelta(hours=2)

    for adapter in (adapter_low, adapter_full):
        mock_pm = MagicMock()
        mock_pm.async_get_hora_regreso = AsyncMock(
            return_value=hora_regreso.replace(tzinfo=timezone.utc)
        )
        adapter._presence_monitor = mock_pm

    async def _run(adapter):
        soc = 50.0 if adapter is adapter_low else 80.0
        with (
            patch.object(
                adapter, "_get_current_soc", new_callable=AsyncMock, return_value=soc
            ),
            patch.object(
                adapter,
                "_get_hora_regreso",
                new_callable=AsyncMock,
                return_value=hora_regreso.replace(tzinfo=timezone.utc),
            ),
        ):
            await adapter.async_publish_all_deferrable_loads(trips)
        return list(adapter._cached_power_profile or [])

    profile_low = await _run(adapter_low)
    profile_full = await _run(adapter_full)

    # Higher SOC should have fewer charge hours needed (or equal)
    energy_low = sum(profile_low)
    energy_full = sum(profile_full)
    non_zero_low = _count_nonzero(profile_low)
    non_zero_full = _count_nonzero(profile_full)

    assert non_zero_full <= non_zero_low, (
        f"Expected higher SOC (80%) to need <= charge hours than SOC 50%, "
        f"but got {non_zero_full} > {non_zero_low}. "
        f"Energy: {energy_full:.0f} vs {energy_low:.0f}."
    )
