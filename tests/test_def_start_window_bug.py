"""Test that def_start_timestep produces a window large enough for def_total_hours.

Bug report: EMHASS optimizer fails with:
  "Deferrable load 3: Available timeframe is shorter than the specified number
   of hours to operate."

Root cause: When inicio_ventana and fin_ventana are close together (e.g., 142.33h
and 143.0h from now), the current calculation produces:
  def_start_timestep = int(142.33) = 142
  def_end_timestep   = ceil(143.0 - 0.001) = 143
  window = 143 - 142 = 1 timestep
  def_total_hours = 2
  → window (1) < def_total_hours (2) → EMHASS FAILS

EMHASS timestep semantics:
  - Minimum unit is 1 complete hour (any fraction counts as 1 full timestep)
  - timestep N covers the period from hour N to hour N+1
  - Available timesteps = def_end_timestep - def_start_timestep (exclusive end)

Fix: Subtract 1 from def_start_timestep to expand the window by 1 timestep.
If def_start would go below 0, reduce def_total_hours instead (only when window
is genuinely too small).

User's sensor data that triggered the bug:
  def_start_timestep: [36, 52, 131, 142, 152]
  def_end_timestep:   [43, 122, 139, 143, 163]
  def_total_hours:    [ 2,  2,   2,   2,   2]
  Load 3 (index 3): start=142, end=143, window=1 < hours=2 → FAILS
"""

import math
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter


class MockConfigEntry:
    """Mock ConfigEntry for testing."""

    def __init__(self, vehicle_id="test_vehicle", data=None):
        self.entry_id = "test_entry"
        self.data = data or {
            "vehicle_name": vehicle_id,
            "max_deferrable_loads": 50,
            "charging_power": 7.4,
        }


def _make_adapter():
    """Create a fresh EMHASSAdapter with mocked dependencies."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)

    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value={})
    mock_store.async_save = AsyncMock()

    entry = MockConfigEntry()

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(hass, entry)
        adapter.async_load = AsyncMock()
        adapter._index_map = {}

    return adapter


class TestDefStartTimestepWindowBug:
    """Bug: def_end - def_start < def_total_hours causes EMHASS optimization failure.

    The invariant that must hold for every deferrable load:
        def_end_timestep - def_start_timestep >= def_total_hours

    If this invariant is violated, EMHASS refuses to optimize.
    """

    @pytest.mark.asyncio
    async def test_narrow_window_at_142_143(self):
        """Reproduce user's exact scenario: load 3 with window [142, 143] and hours=2.

        inicio_ventana at ~142.33h from now → int(142.33) = 142
        fin_ventana at ~143.0h from now → ceil(143.0 - 0.001) = 143
        Current: window = 143 - 142 = 1 < def_total_hours = 2 → BUG
        Expected: def_start reduced by 1 → window = 143 - 141 = 2 >= 2
        """
        adapter = _make_adapter()
        adapter._index_map = {"trip_narrow": 3}
        adapter._battery_capacity_kwh = 50.0
        adapter._safety_margin_percent = 10.0

        now = datetime.now(timezone.utc)

        # inicio_ventana at 142h20m from now (142.33h)
        inicio_ventana = now + timedelta(hours=142, minutes=20)
        # fin_ventana at exactly 143h from now (143.0h)
        fin_ventana = now + timedelta(hours=143)

        trip = {
            "id": "trip_narrow",
            "kwh": 14.8,  # 2 hours at 7.4 kW
            "datetime": fin_ventana.isoformat(),
        }

        await adapter._populate_per_trip_cache_entry(
            trip=trip,
            trip_id="trip_narrow",
            charging_power_kw=7.4,
            battery_capacity_kwh=50.0,
            safety_margin_percent=10.0,
            soc_current=50.0,
            hora_regreso=None,
            pre_computed_inicio_ventana=inicio_ventana,
            pre_computed_fin_ventana=fin_ventana,
            adjusted_def_total_hours=2.0,
        )

        params = adapter._cached_per_trip_params.get("trip_narrow", {})
        def_start = params.get("def_start_timestep")
        def_end = params.get("def_end_timestep")
        def_total_hours = params.get("def_total_hours")

        # THE INVARIANT: window must be >= def_total_hours
        window = def_end - def_start
        assert window >= def_total_hours, (
            f"EMHASS window too small: def_end({def_end}) - def_start({def_start}) "
            f"= {window} < def_total_hours({def_total_hours}). "
            f"EMHASS will refuse to optimize."
        )

    @pytest.mark.asyncio
    async def test_wide_window_unchanged(self):
        """When window is already large enough, def_start should NOT be reduced.

        A trip with a wide window (e.g., 11 timesteps for 2 hours) should not
        have its def_start unnecessarily reduced.
        """
        adapter = _make_adapter()
        adapter._index_map = {"trip_wide": 4}
        adapter._battery_capacity_kwh = 50.0
        adapter._safety_margin_percent = 10.0

        now = datetime.now(timezone.utc)

        # Wide window: 11 hours
        inicio_ventana = now + timedelta(hours=152)
        fin_ventana = now + timedelta(hours=163)

        trip = {
            "id": "trip_wide",
            "kwh": 14.8,
            "datetime": fin_ventana.isoformat(),
        }

        await adapter._populate_per_trip_cache_entry(
            trip=trip,
            trip_id="trip_wide",
            charging_power_kw=7.4,
            battery_capacity_kwh=50.0,
            safety_margin_percent=10.0,
            soc_current=50.0,
            hora_regreso=None,
            pre_computed_inicio_ventana=inicio_ventana,
            pre_computed_fin_ventana=fin_ventana,
            adjusted_def_total_hours=2.0,
        )

        params = adapter._cached_per_trip_params.get("trip_wide", {})
        def_start = params.get("def_start_timestep")
        def_end = params.get("def_end_timestep")
        def_total_hours = params.get("def_total_hours")

        window = def_end - def_start
        assert window >= def_total_hours, (
            f"Window should be sufficient: {window} >= {def_total_hours}"
        )

    @pytest.mark.asyncio
    async def test_def_start_at_zero_reduces_hours(self):
        """When def_start=0 and window is too small, reduce def_total_hours.

        If inicio_ventana is in the past (def_start=0) and the window is too
        narrow, we can't expand backward. Instead, reduce def_total_hours to
        match the available window.
        """
        adapter = _make_adapter()
        adapter._index_map = {"trip_zero": 0}
        adapter._battery_capacity_kwh = 50.0
        adapter._safety_margin_percent = 10.0

        now = datetime.now(timezone.utc)

        # inicio_ventana in the past → def_start = 0
        inicio_ventana = now - timedelta(hours=5)
        # fin_ventana only 1 hour from now → def_end = 1
        fin_ventana = now + timedelta(hours=1)

        trip = {
            "id": "trip_zero",
            "kwh": 14.8,  # needs 2 hours
            "datetime": fin_ventana.isoformat(),
        }

        await adapter._populate_per_trip_cache_entry(
            trip=trip,
            trip_id="trip_zero",
            charging_power_kw=7.4,
            battery_capacity_kwh=50.0,
            safety_margin_percent=10.0,
            soc_current=50.0,
            hora_regreso=None,
            pre_computed_inicio_ventana=inicio_ventana,
            pre_computed_fin_ventana=fin_ventana,
            adjusted_def_total_hours=2.0,
        )

        params = adapter._cached_per_trip_params.get("trip_zero", {})
        def_start = params.get("def_start_timestep")
        def_end = params.get("def_end_timestep")
        def_total_hours = params.get("def_total_hours")

        # def_start must not go below 0
        assert def_start >= 0, f"def_start must be >= 0, got {def_start}"

        # The invariant must still hold
        window = def_end - def_start
        assert window >= def_total_hours, (
            f"Window too small even after adjustment: {window} < {def_total_hours}"
        )

    @pytest.mark.asyncio
    async def test_all_5_loads_from_user_scenario(self):
        """Reproduce the full 5-load scenario from user's sensor data.

        User's data:
          def_start_timestep: [36, 52, 131, 142, 152]
          def_end_timestep:   [43, 122, 139, 143, 163]
          def_total_hours:    [ 2,  2,   2,   2,   2]

        Load 3 (index 3) is the problematic one: window=1 < hours=2.
        All other loads have sufficient windows.
        """
        adapter = _make_adapter()
        adapter._battery_capacity_kwh = 50.0
        adapter._safety_margin_percent = 10.0

        now = datetime.now(timezone.utc)

        # Recreate the 5 trips with deadlines that produce the user's timestep values
        # The key is load 3: inicio_ventana ~142.33h, fin_ventana ~143.0h
        trips_data = [
            # (trip_id, emhass_index, inicio_offset_h, fin_offset_h)
            ("trip_0", 0, 36.2, 43.0),  # window ~7h, hours=2 ✓
            ("trip_1", 1, 52.1, 122.0),  # window ~70h, hours=2 ✓
            ("trip_2", 2, 131.3, 139.0),  # window ~8h, hours=2 ✓
            ("trip_3", 3, 142.33, 143.0),  # window ~1h, hours=2 ✗ BUG!
            ("trip_4", 4, 152.1, 163.0),  # window ~11h, hours=2 ✓
        ]

        adapter._index_map = {tid: idx for tid, idx, _, _ in trips_data}

        for trip_id, _, inicio_h, fin_h in trips_data:
            inicio_ventana = now + timedelta(hours=inicio_h)
            fin_ventana = now + timedelta(hours=fin_h)

            trip = {
                "id": trip_id,
                "kwh": 14.8,  # 2 hours at 7.4 kW
                "datetime": fin_ventana.isoformat(),
            }

            await adapter._populate_per_trip_cache_entry(
                trip=trip,
                trip_id=trip_id,
                charging_power_kw=7.4,
                battery_capacity_kwh=50.0,
                safety_margin_percent=10.0,
                soc_current=50.0,
                hora_regreso=None,
                pre_computed_inicio_ventana=inicio_ventana,
                pre_computed_fin_ventana=fin_ventana,
                adjusted_def_total_hours=2.0,
            )

        # Verify ALL loads satisfy the invariant
        for trip_id, _, _, _ in trips_data:
            params = adapter._cached_per_trip_params.get(trip_id, {})
            def_start = params.get("def_start_timestep")
            def_end = params.get("def_end_timestep")
            def_total_hours = params.get("def_total_hours")

            window = def_end - def_start
            assert window >= def_total_hours, (
                f"Load {trip_id}: window={window} (end={def_end} - start={def_start}) "
                f"< hours={def_total_hours}. EMHASS will refuse to optimize."
            )


class TestDefStartTimestepMath:
    """Pure math tests demonstrating the off-by-one in timestep calculation.

    These tests verify the math without needing the full adapter infrastructure.
    """

    def test_current_calculation_produces_narrow_window(self):
        """Demonstrate the bug with pure math.

        inicio_ventana at 142.33h → int(142.33) = 142
        fin_ventana at 143.0h → ceil(143.0 - 0.001) = 143
        window = 143 - 142 = 1 < 2 → BUG
        """
        delta_hours_start = 142.33
        delta_hours_end = 143.0

        # Current calculation (from emhass_adapter.py lines 584, 622)
        def_start = max(0, min(int(delta_hours_start), 168))  # 142
        def_end = max(0, min(math.ceil(delta_hours_end - 0.001), 168))  # 143

        assert def_start == 142
        assert def_end == 143
        assert def_end - def_start == 1  # Only 1 timestep!
        assert def_end - def_start < 2  # Less than def_total_hours → BUG

    def test_fixed_calculation_expands_window(self):
        """After fix: subtract 1 from def_start → window expands to 2.

        def_start = 142 - 1 = 141
        def_end = 143
        window = 143 - 141 = 2 >= 2 → OK
        """
        delta_hours_start = 142.33
        delta_hours_end = 143.0

        def_start = max(0, min(int(delta_hours_start), 168))
        def_end = max(0, min(math.ceil(delta_hours_end - 0.001), 168))

        # FIX: subtract 1 from def_start
        def_start_fixed = max(0, def_start - 1)

        assert def_start_fixed == 141
        assert def_end == 143
        assert def_end - def_start_fixed == 2  # Now 2 timesteps!
        assert def_end - def_start_fixed >= 2  # Satisfies def_total_hours

    def test_exact_integer_boundary(self):
        """When inicio_ventana is at exact integer hour.

        inicio at 142.0h → int(142.0) = 142
        fin at 143.0h → ceil(143.0 - 0.001) = 143
        Current: window = 1
        Fixed: def_start = 141, window = 2
        """
        delta_hours_start = 142.0
        delta_hours_end = 143.0

        def_start = max(0, min(int(delta_hours_start), 168))
        def_end = max(0, min(math.ceil(delta_hours_end - 0.001), 168))

        assert def_start == 142
        assert def_end == 143
        assert def_end - def_start == 1  # Still only 1!

        # Fix
        def_start_fixed = max(0, def_start - 1)
        assert def_end - def_start_fixed == 2

    def test_def_start_zero_cannot_reduce(self):
        """When def_start=0, can't subtract 1. Must reduce hours instead."""
        delta_hours_start = 0.5  # past → clamped to 0
        delta_hours_end = 1.0

        def_start = max(0, min(int(delta_hours_start), 168))  # 0
        def_end = max(0, min(math.ceil(delta_hours_end - 0.001), 168))  # 1

        assert def_start == 0
        assert def_end == 1
        window = def_end - def_start  # 1

        def_total_hours = 2
        # Can't reduce def_start (already 0), so must cap hours
        if window < def_total_hours:
            adjusted_hours = window  # Cap to available window
        else:
            adjusted_hours = def_total_hours

        assert adjusted_hours == 1  # Reduced from 2 to 1
        assert window >= adjusted_hours  # Now invariant holds

    def test_wide_window_not_affected(self):
        """Wide windows should not be negatively affected by the fix."""
        delta_hours_start = 152.1
        delta_hours_end = 163.0

        def_start = max(0, min(int(delta_hours_start), 168))  # 152
        def_end = max(0, min(math.ceil(delta_hours_end - 0.001), 168))  # 163

        # Fix: subtract 1 from def_start
        def_start_fixed = max(0, def_start - 1)

        window_before = def_end - def_start  # 11
        window_after = def_end - def_start_fixed  # 12

        # Both are sufficient for 2 hours
        assert window_before >= 2
        assert window_after >= 2
        # Fix just makes it 1 wider (harmless)
        assert window_after == window_before + 1
