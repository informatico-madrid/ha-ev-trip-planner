"""Unit test for SOC cap aggregation slot calculation (math.ceil vs round).

BUG HISTORY:
  In emhass_adapter.py, the SOC cap aggregation used `int(round(...))` to calculate
  how many charging slots to keep. When `kwh_needed < charging_power_kw` (e.g., 5 kWh
  needed with 11 kW charger), `round(5000/11000) = round(0.45) = 0`, zeroing ALL
  power profile slots. This made the EMHASS sensor show no data.

  Fix: `math.ceil(expected_capped_wh / slot_size)` — EMHASS works in complete hours,
  any fraction (0.01+) counts as 1 full hour.

  This test would have caught the bug BEFORE the E2E test, because it directly tests
  the aggregation logic with the exact scenario: kwh_needed < charging_power_kw.

E2E REFERENCE:
  emhass-sensor-updates.spec.ts:614 "race-condition-regression-rapid-successive-creation"
  was the E2E test that exposed this bug in production.
"""

import math
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_VEHICLE_NAME,
)
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter


class MockConfigEntry:
    """Mock ConfigEntry for testing."""

    def __init__(self, vehicle_id="test_vehicle", data=None):
        self.entry_id = "test_entry_id"
        self.data = data or {
            CONF_VEHICLE_NAME: vehicle_id,
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 11.0,
        }


class MockRuntimeData:
    """Mock runtime_data for ConfigEntry."""

    def __init__(self, coordinator=None, trip_manager=None):
        self.coordinator = coordinator
        self.trip_manager = trip_manager




@pytest.fixture
def mock_store():
    """Create a mock store."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock(return_value=None)
    return store


# =============================================================================
# TEST 1: Pure unit test — math.ceil vs round for slot calculation
# =============================================================================


class TestSlotCalculationCeilVsRound:
    """Pure unit tests for the slot calculation logic.

    These tests verify the mathematical property that math.ceil is correct
    for EMHASS slot calculation (any fraction = 1 full hour).
    """

    def test_ceil_vs_round_when_energy_less_than_one_slot(self):
        """When energy < 1 slot, round gives 0 (BUG), ceil gives 1 (CORRECT).

        This is the EXACT scenario that caused the E2E test failure:
        kwh_needed=5.0, charging_power_kw=11.0 → 5000/11000 = 0.45
        """
        expected_capped_wh = 5000.0  # 5 kWh
        slot_size = 11000.0  # 11 kW * 1000

        # BUG: round(0.45) = 0, zeroing all slots
        buggy_slots = int(round(expected_capped_wh / slot_size))
        assert buggy_slots == 0, "BUG CONFIRMED: round gives 0 slots"

        # FIX: ceil(0.45) = 1, preserving at least 1 slot
        fixed_slots = math.ceil(expected_capped_wh / slot_size)
        assert fixed_slots == 1, "FIX CONFIRMED: ceil gives 1 slot"

    def test_ceil_gives_correct_slots_for_various_fractions(self):
        """Verify math.ceil gives correct slots for various energy/slot ratios."""
        slot_size = 11000.0  # 11 kW

        cases = [
            # (expected_wh, expected_ceil_slots, buggy_round_slots)
            (100.0, 1, 0),     # 0.009 → round=0, ceil=1
            (1000.0, 1, 0),    # 0.09 → round=0, ceil=1
            (5000.0, 1, 0),    # 0.45 → round=0, ceil=1
            (5500.0, 1, 1),    # 0.50 → round=0 or 1 (bankers), ceil=1
            (8000.0, 1, 1),    # 0.73 → round=1, ceil=1
            (11000.0, 1, 1),   # 1.00 → round=1, ceil=1
            (16500.0, 2, 1),   # 1.50 → round=2 (bankers) or 1, ceil=2
            (22000.0, 2, 2),   # 2.00 → round=2, ceil=2
            (33000.0, 3, 3),   # 3.00 → round=3, ceil=3
        ]

        for expected_wh, expected_ceil, _ in cases:
            result = math.ceil(expected_wh / slot_size)
            assert result == expected_ceil, (
                f"math.ceil({expected_wh}/{slot_size}) = {result}, expected {expected_ceil}"
            )

    def test_round_zeros_slots_for_all_sub_slot_energy(self):
        """Demonstrate that round() zeros ALL sub-slot energy values.

        This is why the bug was so severe: ANY energy need below 1 full slot
        resulted in a completely zeroed power profile.
        """
        slot_size = 11000.0

        # All these energy values represent REAL charging needs
        # that should result in at least 1 hour of charging
        sub_slot_energies = [100, 500, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]

        zero_count = 0
        for energy_wh in sub_slot_energies:
            round_slots = int(round(energy_wh / slot_size))
            ceil_slots = math.ceil(energy_wh / slot_size)
            if round_slots == 0:
                zero_count += 1
            # ceil should ALWAYS give at least 1 for positive energy
            assert ceil_slots >= 1, (
                f"math.ceil({energy_wh}/{slot_size}) = {ceil_slots}, should be >= 1"
            )

        # round gives 0 for most sub-slot values
        assert zero_count > 0, "round() should zero some sub-slot energy values"


# =============================================================================
# TEST 2: Integration test — aggregation with pre-populated cache
# =============================================================================


@pytest.mark.asyncio
async def test_soc_cap_aggregation_preserves_slots_when_kwh_needed_less_than_charger_power(
    mock_hass, mock_store
):
    """Test that SOC cap aggregation preserves at least 1 slot when kwh_needed < charger power.

    SCENARIO (matches the E2E failure):
    - charging_power_kw = 11.0 (slot_size = 11000 W)
    - kwh_needed = 5.0 kWh (expected_capped_wh = 5000)
    - Per-trip profile has 1 slot at 11000 W
    - Aggregation should keep at least 1 slot (not zero all)

    With the BUG (round): target_slots = int(round(5000/11000)) = 0 → all zeros
    With the FIX (ceil): target_slots = math.ceil(5000/11000) = 1 → keeps 1 slot

    STRATEGY: Pre-populate _cached_per_trip_params and mock both
    async_publish_deferrable_load (to succeed without overwriting cache) and
    _populate_per_trip_cache_entry (no-op). This isolates the aggregation logic.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 11.0,  # 11 kW charger — key to trigger the bug
    }

    entry = MockConfigEntry("test_vehicle", config)
    entry.runtime_data = MockRuntimeData()

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, entry)
        await adapter.async_load()

        # Pre-populate per-trip cache with the EXACT scenario from the E2E failure:
        # kwh_needed = 5.0 kWh (less than 11 kW charger = less than 1 full slot)
        # power_profile has 1 slot at position 21 with 11000 W
        trip_id = "trip_001"
        adapter._cached_per_trip_params[trip_id] = {
            "kwh_needed": 5.0,  # 5 kWh — less than 11 kW slot
            "power_profile_watts": [0.0] * 21 + [11000.0] + [0.0] * 146,
            "def_total_hours": 1.0,
            "P_deferrable_nom": 11000.0,
            "def_start_timestep": 20,
            "def_end_timestep": 22,
        }

        # Trip matching the cached params
        trips = [{"id": trip_id, "kwh": 5.0}]

        # Mock async_publish_deferrable_load to succeed without clearing cache
        # (it normally fails for trips without datetime and rolls back)
        with patch.object(
            adapter, "async_publish_deferrable_load", new_callable=AsyncMock, return_value=True
        ):
            # Mock _populate_per_trip_cache_entry to NOT overwrite our pre-populated cache
            with patch.object(
                adapter, "_populate_per_trip_cache_entry", new_callable=AsyncMock
            ):
                with patch.object(adapter, "_get_current_soc", return_value=80.0):
                    with patch.object(adapter, "_get_hora_regreso", return_value=None):
                        await adapter.async_publish_all_deferrable_loads(
                            trips, charging_power_kw=11.0
                        )

        # THE CRITICAL ASSERTION: power_profile must have at least 1 non-zero slot
        assert adapter._cached_power_profile is not None, (
            "BUG: _cached_power_profile is None after aggregation"
        )

        non_zero_count = sum(1 for v in adapter._cached_power_profile if v > 0)
        assert non_zero_count >= 1, (
            f"BUG: _cached_power_profile has all zeros after SOC cap aggregation. "
            f"This means round() zeroed all slots when kwh_needed (5 kWh) < "
            f"charging_power_kw (11 kW). "
            f"Expected at least 1 non-zero slot. "
            f"Profile length: {len(adapter._cached_power_profile)}, "
            f"non_zero: {non_zero_count}"
        )

        # Additional verification: the non-zero slot should be at position 21
        assert adapter._cached_power_profile[21] > 0, (
            f"Expected slot 21 to be non-zero (11000), got {adapter._cached_power_profile[21]}"
        )

        print(
            f"SUCCESS: SOC cap aggregation preserved {non_zero_count} slot(s) "
            f"when kwh_needed=5.0 < charging_power_kw=11.0"
        )


@pytest.mark.asyncio
async def test_soc_cap_aggregation_with_very_small_kwh_needed(mock_hass, mock_store):
    """Test aggregation when kwh_needed is very small (0.1 kWh).

    Even 0.1 kWh should result in 1 charging hour because EMHASS works in
    complete hours. This is the most extreme case of the bug.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 11.0,
    }

    entry = MockConfigEntry("test_vehicle", config)
    entry.runtime_data = MockRuntimeData()

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, entry)
        await adapter.async_load()

        # Extreme case: 0.1 kWh needed with 11 kW charger
        # round(100/11000) = round(0.009) = 0 → BUG
        # ceil(100/11000) = ceil(0.009) = 1 → CORRECT
        trip_id = "trip_tiny"
        adapter._cached_per_trip_params[trip_id] = {
            "kwh_needed": 0.1,
            "power_profile_watts": [0.0] * 10 + [11000.0] + [0.0] * 157,
            "def_total_hours": 1.0,
            "P_deferrable_nom": 11000.0,
            "def_start_timestep": 10,
            "def_end_timestep": 12,
        }

        trips = [{"id": trip_id, "kwh": 0.1}]

        # Mock async_publish_deferrable_load to succeed without clearing cache
        with patch.object(
            adapter, "async_publish_deferrable_load", new_callable=AsyncMock, return_value=True
        ):
            with patch.object(
                adapter, "_populate_per_trip_cache_entry", new_callable=AsyncMock
            ):
                with patch.object(adapter, "_get_current_soc", return_value=95.0):
                    with patch.object(adapter, "_get_hora_regreso", return_value=None):
                        await adapter.async_publish_all_deferrable_loads(
                            trips, charging_power_kw=11.0
                        )

        non_zero_count = sum(1 for v in adapter._cached_power_profile if v > 0)
        assert non_zero_count >= 1, (
            f"BUG: Even 0.1 kWh should produce 1 charging slot. "
            f"Got {non_zero_count} non-zero slots. "
            f"math.ceil(100/11000) should be 1, not 0."
        )

        print(f"SUCCESS: 0.1 kWh → {non_zero_count} charging slot(s) preserved")


# =============================================================================
# TEST 3: Full integration test — through the real publish flow
# =============================================================================


@pytest.mark.asyncio
async def test_full_publish_flow_with_high_soc_and_11kw_charger(
    mock_hass, mock_store
):
    """Full integration test through async_publish_all_deferrable_loads.

    This test goes through the REAL code path (no mocking _populate_per_trip_cache_entry)
    to verify that the SOC cap aggregation works correctly end-to-end.

    SCENARIO:
    - 11 kW charger
    - SOC = 80% (high, so kwh_needed is small)
    - Trip needs 5 kWh
    - Expected: power_profile has at least 1 non-zero slot
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 11.0,
    }

    entry = MockConfigEntry("test_vehicle", config)
    entry.runtime_data = MockRuntimeData()

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, entry)
        await adapter.async_load()

        # Use high SOC (80%) so kwh_needed is small relative to 11 kW charger
        with patch.object(adapter, "_get_current_soc", return_value=80.0):
            with patch.object(adapter, "_get_hora_regreso", return_value=None):
                trips = [
                    {
                        "id": "trip_integration",
                        "kwh": 5.0,
                        "hora": "09:00",
                        "dias_semana": ["monday"],
                        "datetime": (
                            datetime.now() + timedelta(days=1)
                        ).isoformat(),
                    },
                ]

                await adapter.async_publish_all_deferrable_loads(
                    trips, charging_power_kw=11.0
                )

        # Verify power_profile exists and has non-zero values
        assert adapter._cached_power_profile is not None, (
            "BUG: _cached_power_profile is None"
        )

        non_zero_count = sum(1 for v in adapter._cached_power_profile if v > 0)
        assert non_zero_count >= 1, (
            f"BUG: Full integration flow produced all-zero power_profile. "
            f"With 11 kW charger and 5 kWh trip, at least 1 slot should be non-zero. "
            f"Non-zero count: {non_zero_count}"
        )

        print(
            f"SUCCESS: Full flow with 11 kW charger produced {non_zero_count} "
            f"non-zero slot(s)"
        )
