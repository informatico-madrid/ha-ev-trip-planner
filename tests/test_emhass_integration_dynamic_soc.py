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

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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
        trips.append(
            {
                "id": f"trip_{i}",
                "kwh": kwh,
                "datetime": deadline.isoformat(),
                "descripcion": f"Commute {i + 1}",
            }
        )
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
    """T056: T_BASE=6h should produce less total charging energy than T_BASE=48h.

    Setup: 4 commute trips (6kWh each), SOC=40%, charging=7.4kW.
    Trips are scheduled 20h apart (20h, 40h, 60h, 80h in future) so that
    t_hours values produce meaningful SOC cap differences between T_BASE=6h
    and T_BASE=48h.

    With T_BASE=6h (aggressive): tight SOC caps → less total energy
    With T_BASE=48h (conservative): loose SOC caps → more total energy

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

    # Trips 20h, 40h, 60h, 80h in the future
    # With SOC=40%, t_hours=20: risk=1.54, cap_6h=83.2%, cap_48h=98.3%
    # Significant energy difference between the two caps
    now = datetime.now(timezone.utc)
    trips = [
        {
            "id": f"trip_{i}",
            "kwh": 6.0,
            "datetime": (now + timedelta(hours=20 + i * 20)).isoformat(),
            "descripcion": f"Commute {i + 1}",
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
        return list(adapter._cached_power_profile or [])

    profile_6 = await _run(adapter_6)
    profile_48 = await _run(adapter_48)

    # Energy-based assertion: T_BASE=6h should deliver LESS total energy
    # than T_BASE=48h because aggressive SOC caps reduce power density
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


# ---------------------------------------------------------------------------
# T057: SOC caps reduce kWh targets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_soc_caps_applied_to_kwh_calculation():
    """T057: SOC caps from calculate_dynamic_soc_limit should reduce kWh charging targets.

    Setup: 4 commute trips (6kWh each), SOC=40%, with T_BASE=24h.
    The dynamic SOC limit algorithm should compute a cap below 100%.
    The resulting power profile should reflect capped kWh, not uncapped.

    This test verifies BOTH:
    1. soc_target < 100% is stored in cache
    2. kwh_needed is proportionally reduced by the SOC cap ratio
    """
    hass, store = _make_mock_hass(soc_state=40.0)
    entry = _MockConfigEntry(t_base=24.0, battery_capacity=60.0, charging_power=7.4)

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store", return_value=store
    ):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

    trips = _make_trips(num_commutes=4, kwh=6.0, hours_offset=1)

    now = datetime.now(timezone.utc)
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

    profile = list(adapter._cached_power_profile or [])
    non_zero = _count_nonzero(profile)

    assert non_zero > 0, "Power profile should have charging hours"

    # KEY ASSERTION 1: soc_target < 100% is stored in cache per trip
    for trip_id, params in adapter._cached_per_trip_params.items():
        soc_target = params.get("soc_target", 100.0)
        assert soc_target < 100.0, (
            f"Trip {trip_id} has soc_target=100%, but dynamic SOC capping "
            "should produce a cap below 100%. This indicates soc_caps are NOT "
            "wired into the production path."
        )

    # KEY ASSERTION 2: total energy in profile is LESS than uncapped scenario
    # With capped SOC (e.g., cap=85%), total energy should be < uncapped energy
    total_energy = sum(profile)
    # 4 trips × 6kWh = 24kWh. With SOC cap < 100%, energy should be reduced.
    # At SOC 40%, real capacity 60kWh: each trip needs 6kWh.
    # Uncapped: 24kWh total → ~24000 Wh. With cap ~85%: ~20400 Wh.
    # The profile is in 1-hour blocks, so total should be < 24000 if cap is applied.
    assert total_energy < 24000, (
        f"Total profile energy ({total_energy:.0f} Wh) should be less than uncapped "
        f"(~24000 Wh) when SOC cap is applied. Cap may not be affecting power profile."
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

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store", return_value=store_100
    ):
        adapter_100 = EMHASSAdapter(hass_100, entry_100)
        await adapter_100.async_load()

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store", return_value=store_90
    ):
        adapter_90 = EMHASSAdapter(hass_90, entry_90)
        await adapter_90.async_load()

    trips = _make_trips(num_commutes=2, kwh=6.0, hours_offset=1)

    now = datetime.now(timezone.utc)
    hora_regreso = now - timedelta(hours=2)

    for adapter in (adapter_100, adapter_90):
        mock_pm = MagicMock()
        mock_pm.async_get_hora_regreso = AsyncMock(
            return_value=hora_regreso.replace(tzinfo=timezone.utc)
        )
        adapter._presence_monitor = mock_pm

    async def _run(adapter):
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


# ---------------------------------------------------------------------------
# T090: No charging needed branch (total_hours == 0)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_charging_needed_power_watts_zero():
    """T090: Verify power_watts is 0.0 when total_hours == 0 (no charging needed).

    A trip with kwh=0 needs no charging. The proactive charging logic in
    determine_charging_need returns total_hours=0 and power_watts=0.0 in that case.
    This test verifies that branch in _populate_per_trip_cache_entry.
    """
    hass, store = _make_mock_hass(soc_state=50.0)
    entry = _MockConfigEntry(battery_capacity=60.0, charging_power=7.4)

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store", return_value=store
    ):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

    # Create a trip with 0kWh — no energy needed
    now = datetime.now(timezone.utc)
    trips = [
        {
            "id": "trip_zero",
            "kwh": 0.0,
            "datetime": (now + timedelta(hours=24)).isoformat(),
            "descripcion": "Zero energy trip",
        }
    ]

    hora_regreso = now - timedelta(hours=2)

    mock_pm = MagicMock()
    mock_pm.async_get_hora_regreso = AsyncMock(
        return_value=hora_regreso.replace(tzinfo=timezone.utc)
    )
    adapter._presence_monitor = mock_pm

    with (
        patch.object(
            adapter, "_get_current_soc", new_callable=AsyncMock, return_value=50.0
        ),
        patch.object(
            adapter,
            "_get_hora_regreso",
            new_callable=AsyncMock,
            return_value=hora_regreso.replace(tzinfo=timezone.utc),
        ),
    ):
        await adapter.async_publish_all_deferrable_loads(trips)

    # Verify the per-trip cache entry has power_watts = 0.0
    params = adapter._cached_per_trip_params.get("trip_zero", {})
    assert params.get("power_watts") == 0.0, (
        f"Expected power_watts=0.0 for kwh=0 trip, got {params.get('power_watts')}. "
        "The total_hours == 0 branch (power_watts = 0.0) is not working."
    )
    assert params.get("kwh_needed") == 0.0, (
        f"Expected kwh_needed=0.0 for kwh=0 trip, got {params.get('kwh_needed')}."
    )


# ---------------------------------------------------------------------------
# T109: Stale cache cleanup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stale_cache_cleanup():
    """T109: Verify stale cache entries are cleaned up when trips are removed.

    When async_publish_all_deferrable_loads() is called with a subset of
    previously published trips, the stale cache entries for removed trips
    should be deleted from _cached_per_trip_params.
    """
    hass, store = _make_mock_hass(soc_state=50.0)
    entry = _MockConfigEntry(battery_capacity=60.0, charging_power=7.4)

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store", return_value=store
    ):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

    now = datetime.now(timezone.utc)
    hora_regreso = now - timedelta(hours=2)
    mock_pm = MagicMock()
    mock_pm.async_get_hora_regreso = AsyncMock(
        return_value=hora_regreso.replace(tzinfo=timezone.utc)
    )
    adapter._presence_monitor = mock_pm

    # Step 1: Publish with 3 trips — all 3 should be in cache
    trips_3 = [
        {
            "id": f"trip_{i}",
            "kwh": 5.0,
            "datetime": (now + timedelta(hours=24)).isoformat(),
            "descripcion": f"Trip {i}",
        }
        for i in range(3)
    ]

    with (
        patch.object(
            adapter, "_get_current_soc", new_callable=AsyncMock, return_value=50.0
        ),
        patch.object(
            adapter,
            "_get_hora_regreso",
            new_callable=AsyncMock,
            return_value=hora_regreso.replace(tzinfo=timezone.utc),
        ),
    ):
        await adapter.async_publish_all_deferrable_loads(trips_3)

    assert len(adapter._cached_per_trip_params) == 3, (
        f"Expected 3 cache entries after first publish, got {len(adapter._cached_per_trip_params)}"
    )

    # Step 2: Publish with only 1 trip — stale cache for 2 trips should be cleaned up
    trips_1 = [
        {
            "id": "trip_0",
            "kwh": 5.0,
            "datetime": (now + timedelta(hours=24)).isoformat(),
            "descripcion": "Trip 0",
        }
    ]

    with (
        patch.object(
            adapter, "_get_current_soc", new_callable=AsyncMock, return_value=50.0
        ),
        patch.object(
            adapter,
            "_get_hora_regreso",
            new_callable=AsyncMock,
            return_value=hora_regreso.replace(tzinfo=timezone.utc),
        ),
    ):
        await adapter.async_publish_all_deferrable_loads(trips_1)

    # Only 1 cache entry should remain — stale entries cleaned up
    assert len(adapter._cached_per_trip_params) == 1, (
        f"Expected 1 cache entry after removing 2 trips, got {len(adapter._cached_per_trip_params)}. "
        f"Stale cache cleanup is not working. Keys: {list(adapter._cached_per_trip_params.keys())}"
    )
    assert "trip_0" in adapter._cached_per_trip_params, (
        f"trip_0 should still be in cache. Keys: {list(adapter._cached_per_trip_params.keys())}"
    )
    assert "trip_1" not in adapter._cached_per_trip_params, (
        "trip_1 should have been cleaned from stale cache"
    )
    assert "trip_2" not in adapter._cached_per_trip_params, (
        "trip_2 should have been cleaned from stale cache"
    )


# ---------------------------------------------------------------------------
# T109 fallback path: trip without ID in fallback list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_path_skips_trip_without_id():
    """T115: Verify the fallback path skips trips without ID — line 1132 coverage.

    Mock _calculate_deadline_from_trip to return None for all trips, ensuring
    trip_deadlines is empty and the code enters the fallback path.
    The fallback iterates [(None, None, trip) for trip in trips] and skips
    trips without 'id' via `continue` at line 1132.
    """
    hass, store = _make_mock_hass(soc_state=50.0)
    entry = _MockConfigEntry(battery_capacity=60.0, charging_power=7.4)

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store", return_value=store
    ):
        adapter = EMHASSAdapter(hass, entry)
        await adapter.async_load()

    hora_regreso = datetime(2026, 5, 2, 18, 0, 0, tzinfo=timezone.utc)
    mock_pm = MagicMock()
    mock_pm.async_get_hora_regreso = AsyncMock(return_value=hora_regreso)
    adapter._presence_monitor = mock_pm

    # Mock _calculate_deadline_from_trip to return None → trip_deadlines stays empty
    # Include one trip without 'id' key to hit line 1132 `continue`
    trips_with_no_id = [
        {"id": "trip_1", "kwh": 5.0, "datetime": "2026-05-03T10:00:00+00:00"},
        {
            "kwh": 5.0,
            "datetime": "2026-05-03T12:00:00+00:00",
        },  # No 'id' → hits line 1132
    ]

    with (
        patch.object(adapter, "_calculate_deadline_from_trip", return_value=None),
        patch.object(
            adapter, "_get_current_soc", new_callable=AsyncMock, return_value=50.0
        ),
        patch.object(
            adapter,
            "_get_hora_regreso",
            new_callable=AsyncMock,
            return_value=hora_regreso,
        ),
    ):
        await adapter.async_publish_all_deferrable_loads(trips_with_no_id)

    # The trip without 'id' is skipped at line 1132, but trip_1 is still processed
    # Verify no crash — fallback path executed correctly
    assert len(adapter._cached_per_trip_params) == 1
