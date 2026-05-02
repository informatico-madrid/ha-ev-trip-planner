"""
Integration tests: Dynamic SOC Capping in EMHASS production path.

These tests call the actual production entry point
(EMHASSAdapter.async_publish_all_deferrable_loads()) to verify that
dynamic SOC capping parameters (t_base, BatteryCapacity/real capacity,
SOC caps) actually affect the power profile output.

TDD NOTE: These tests MUST FAIL initially because the production path
currently uses nominal capacity (self._battery_capacity_kwh) and ignores
self._t_base. Once T059-T064 wire the production path, these tests will pass.

Each test verifies a specific wiring target:
  T056 — T_BASE changes charging hours
  T057 — SOC caps reduce kWh targets
  T058 — Real capacity (SOH) scales power profile
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.util import dt as dt_util

from custom_components.ev_trip_planner.calculations import BatteryCapacity
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _MockConfigEntry:
    """Minimal ConfigEntry replacement matching the test_charging_window pattern."""

    def __init__(
        self,
        vehicle_id: str = "test_vehicle",
        t_base: float = 24.0,
        battery_capacity: float = 60.0,
        charging_power: float = 7.4,
        soh_sensor: str | None = None,
        soh_sensor_entity_id: str | None = None,
        safety_margin: float = 0.0,
    ):
        self.entry_id = f"test_entry_{vehicle_id}"
        self.data: dict = {
            "vehicle_name": vehicle_id,
            "max_deferrable_loads": 50,
            "charging_power": charging_power,
            "battery_capacity": battery_capacity,
            "safety_margin_percent": safety_margin,
        }
        self.options: dict = {
            "t_base": t_base,
        }
        # These keys are read from entry_data in __init__
        self.data["t_base"] = t_base
        self.data["soh_sensor"] = soh_sensor_entity_id or soh_sensor


def _make_mock_hass(
    soc_sensor: str = "sensor.test_soc",
    soh_sensor_entity_id: str | None = None,
    soc_state: float = 40.0,
    soh_state: float | None = None,
) -> MagicMock:
    """Build a mock hass with state lookups for soc_sensor and optional SOH sensor."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = timezone.utc
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    # Mock loop for Store API
    mock_loop = MagicMock()
    mock_loop.create_future = MagicMock(return_value=None)
    hass.loop = mock_loop

    # Mock Store
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value={})
    mock_store.async_save = AsyncMock()

    # Mock states.get
    def states_get(entity_id: str):
        if entity_id == soc_sensor:
            return MagicMock(state=str(soc_state))
        if entity_id == soh_sensor_entity_id and soh_state is not None:
            return MagicMock(state=str(soh_state))
        return None

    hass.states.get = states_get

    return hass, mock_store


def _make_trips(num_commutes: int = 4, kwh: float = 6.0, hours_offset: int = 1):
    """Create a list of trip dicts for testing."""
    now = datetime.now(timezone.utc)
    trips = []
    for i in range(num_commutes):
        deadline = now + timedelta(hours=hours_offset + i)
        trips.append({
            "id": f"trip_{i}",
            "kwh": kwh,
            "datetime": deadline.isoformat(),
            "descripcion": f"Commute {i+1}",
        })
    return trips


def _count_nonzero(profile):
    """Count positive values in a power profile."""
    if not profile:
        return 0
    return sum(1 for v in profile if v > 0)


# ---------------------------------------------------------------------------
# T056: T_BASE effect
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_t_base_affects_charging_hours():
    """T056: T_BASE=6h should produce different (fewer) charging hours than T_BASE=48h.

    Setup: 4 commute trips (6kWh each), SOC=40%, charging=7.4kW.
    With T_BASE=6h: aggressive capping → fewer charging hours
    With T_BASE=48h: conservative capping → more charging hours

    The production path currently ignores _t_base, so both produce the same output.
    This test MUST FAIL until T062 wires t_base through the charging decision.
    """
    hass_6, store_6 = _make_mock_hass()
    hass_48, store_48 = _make_mock_hass()

    entry_6 = _MockConfigEntry(t_base=6.0, battery_capacity=60.0, charging_power=7.4)
    entry_48 = _MockConfigEntry(t_base=48.0, battery_capacity=60.0, charging_power=7.4)

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=store_6,
    ):
        adapter_6 = EMHASSAdapter(hass_6, entry_6)
        await adapter_6.async_load()

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=store_48,
    ):
        adapter_48 = EMHASSAdapter(hass_48, entry_48)
        await adapter_48.async_load()

    trips = _make_trips(num_commutes=4, kwh=6.0, hours_offset=1)

    now = datetime.now(timezone.utc)
    hora_regreso = now - timedelta(hours=2)

    for adapter in (adapter_6, adapter_48):
        mock_pm = MagicMock()
        mock_pm.async_get_hora_regreso = AsyncMock(return_value=hora_regreso.replace(tzinfo=timezone.utc))
        adapter._presence_monitor = mock_pm

    async def _run(adapter):
        with (
            patch.object(adapter, "_get_current_soc", new_callable=AsyncMock, return_value=40.0),
            patch.object(adapter, "_get_hora_regreso", new_callable=AsyncMock, return_value=hora_regreso.replace(tzinfo=timezone.utc)),
        ):
            await adapter.async_publish_all_deferrable_loads(trips)
        return list(adapter._cached_power_profile or [])

    profile_6 = await _run(adapter_6)
    profile_48 = await _run(adapter_48)

    non_zero_6 = _count_nonzero(profile_6)
    non_zero_48 = _count_nonzero(profile_48)

    # T_BASE=6h (aggressive) should yield FEWER charging hours than T_BASE=48h (conservative)
    assert non_zero_6 < non_zero_48, (
        f"Expected T_BASE=6h to produce fewer charging hours ({non_zero_6}) than "
        f"T_BASE=48h ({non_zero_48}), but they are equal or reversed. "
        "This indicates _t_base is NOT wired into the production path."
    )


# ---------------------------------------------------------------------------
# T057: SOC caps reduce kWh targets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_soc_caps_applied_to_kwh_calculation():
    """T057: SOC caps from calcular_hitos_soc should reduce kWh charging targets.

    Setup: 4 commute trips (6kWh each), SOC=40%, with T_BASE=24h.
    The dynamic SOC limit algorithm should compute a cap below 100%.
    The resulting power profile should reflect capped kWh, not uncapped.

    The production path never calls calcular_hitos_soc or applies SOC caps,
    so the profile will assume 100% target. This test MUST FAIL until T063 wires
    calculate_deficit_propagation with soc_caps.
    """
    hass, store = _make_mock_hass(soc_state=40.0)
    entry = _MockConfigEntry(t_base=24.0, battery_capacity=60.0, charging_power=7.4)

    with patch("custom_components.ev_trip_planner.emhass_adapter.Store", return_value=store):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

    trips = _make_trips(num_commutes=4, kwh=6.0, hours_offset=1)

    now = datetime.now(timezone.utc)
    hora_regreso = now - timedelta(hours=2)

    mock_pm = MagicMock()
    mock_pm.async_get_hora_regreso = AsyncMock(return_value=hora_regreso.replace(tzinfo=timezone.utc))
    adapter._presence_monitor = mock_pm

    with (
        patch.object(adapter, "_get_current_soc", new_callable=AsyncMock, return_value=40.0),
        patch.object(adapter, "_get_hora_regreso", new_callable=AsyncMock, return_value=hora_regreso.replace(tzinfo=timezone.utc)),
    ):
        await adapter.async_publish_all_deferrable_loads(trips)

    profile = list(adapter._cached_power_profile or [])
    non_zero = _count_nonzero(profile)

    # With SOC caps applied, the max SOC target per trip should be below 100%.
    # The nonZeroHours should be LESS than the uncapped scenario.
    #
    # As a proxy: the total charging hours should not equal what 100% target would produce.
    # 4 trips * 6kWh = 24kWh needed. At SOC 40% with real capacity 60kWh:
    #   Current energy = 24kWh. Need 24kWh to reach 100%.
    #   If capped at ~80%, need only ~12kWh more.
    # With 7.4kW charging, 24kWh/7.4 = 3.24h, 12kWh/7.4 = 1.62h.
    #
    # Since the profile is in 1-hour blocks with overlap handling, the nonZeroHours
    # with caps should be measurably less than without caps.
    #
    # The uncapped (current behavior) produces a certain nonZeroHours value.
    # The capped (correct behavior) should produce fewer hours.
    #
    # For now, we assert nonZero > 0 and document the expected difference.
    assert non_zero > 0, "Power profile should have charging hours"

    # The KEY assertion: the adapter should NOT be charging to 100% for every trip.
    # With capped SOC, the profile should reflect a reduced target.
    # We check that the cached params contain a non-100% SOC target per trip.
    for trip_id, params in adapter._cached_per_trip_params.items():
        soc_target = params.get("soc_target", 100.0)
        assert soc_target < 100.0, (
            f"Trip {trip_id} has soc_target=100%, but dynamic SOC capping "
            "should produce a cap below 100%. This indicates soc_caps are NOT "
            "wired into the production path."
        )


# ---------------------------------------------------------------------------
# T058: Real capacity (SOH) scales power profile
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_real_capacity_affects_power_profile():
    """T058: BatteryCapacity with SOH should use real_capacity in power calculations.

    Setup: Two adapters with the same trips, one with SOH=100% (real=60kWh)
    and one with SOH=90% (real=54kWh). The SOH=90% adapter should produce
    a power profile that reflects the lower capacity.

    The production path uses self._battery_capacity_kwh (60.0) regardless of SOH,
    so both adapters will produce identical profiles. This test MUST FAIL until
    T059-T061 wire BatteryCapacity.get_capacity() into the production path.
    """
    # Adapter with SOH=100% -> real capacity = 60.0 kWh
    hass_100, store_100 = _make_mock_hass(
        soh_sensor_entity_id="sensor.vehicle_soh",
        soh_state=100.0,
    )
    entry_100 = _MockConfigEntry(
        battery_capacity=60.0,
        charging_power=7.4,
        soh_sensor_entity_id="sensor.vehicle_soh",
    )

    # Adapter with SOH=90% -> real capacity = 54.0 kWh
    hass_90, store_90 = _make_mock_hass(
        soh_sensor_entity_id="sensor.vehicle_soh",
        soh_state=90.0,
    )
    entry_90 = _MockConfigEntry(
        battery_capacity=60.0,
        charging_power=7.4,
        soh_sensor_entity_id="sensor.vehicle_soh",
    )

    with patch("custom_components.ev_trip_planner.emhass_adapter.Store", return_value=store_100):
        adapter_100 = EMHASSAdapter(hass_100, entry_100)
        await adapter_100.async_load()

    with patch("custom_components.ev_trip_planner.emhass_adapter.Store", return_value=store_90):
        adapter_90 = EMHASSAdapter(hass_90, entry_90)
        await adapter_90.async_load()

    trips = _make_trips(num_commutes=2, kwh=6.0, hours_offset=1)

    now = datetime.now(timezone.utc)
    hora_regreso = now - timedelta(hours=2)

    for adapter in (adapter_100, adapter_90):
        mock_pm = MagicMock()
        mock_pm.async_get_hora_regreso = AsyncMock(return_value=hora_regreso.replace(tzinfo=timezone.utc))
        adapter._presence_monitor = mock_pm

    async def _run(adapter):
        with (
            patch.object(adapter, "_get_current_soc", new_callable=AsyncMock, return_value=40.0),
            patch.object(adapter, "_get_hora_regreso", new_callable=AsyncMock, return_value=hora_regreso.replace(tzinfo=timezone.utc)),
        ):
            await adapter.async_publish_all_deferrable_loads(trips)
        return list(adapter._cached_power_profile or [])

    profile_100 = await _run(adapter_100)
    profile_90 = await _run(adapter_90)

    # The adapters use BatteryCapacity.get_capacity() which should return different
    # values based on SOH. The power profile for SOH=90% should differ from SOH=100%.
    #
    # Key difference: SOC propagation uses real_capacity.
    #   With 60kWh: SOC consumed per 6kWh trip = 10%
    #   With 54kWh: SOC consumed per 6kWh trip = 11.1%
    # This affects projected_soc for subsequent trips, which affects charging decisions.
    #
    # We assert the profiles differ.
    assert profile_100 != profile_90, (
        f"Profiles for SOH=100% and SOH=90% are IDENTICAL. "
        f"Both: {profile_100[:5]}... "
        "This indicates BatteryCapacity.get_capacity() is NOT wired into the "
        "production path — both adapters use nominal capacity (60kWh)."
    )
