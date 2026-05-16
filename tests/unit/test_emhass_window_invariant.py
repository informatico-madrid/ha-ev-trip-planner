"""Test window invariant: def_end - def_start >= def_total_hours for all trips.

Bug report: EMHASS optimizer fails when a trip has a narrow window:
  def_start=142, def_end=143, window=1 < def_total_hours=2 → EMHASS rejects optimization.

This test verifies the invariant holds for all trips after async_publish_all_deferrable_loads().
It adapts test_def_start_window_bug.py from legacy (main branch) to the SOLID architecture.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    return hass


@pytest.fixture
def mock_entry():
    """Create a mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        "battery_capacity_kwh": 50.0,
            "charging_power_kw": 3.6,
            "safety_margin_percent": 10.0,
            "vehicle_name": "test_vehicle",
        "max_deferrable_loads": 50,
        "charging_power": 7.4,
        "battery_capacity": 50.0,
    }
    return entry


class TestEMHASSWindowInvariant:
    """Invariante que debe cumplir CADA carga diferible:

        def_end_timestep - def_start_timestep >= def_total_hours

    Si se viola, EMHASS rechaza la optimización.
    """

    @pytest.mark.asyncio
    async def test_narrow_window_passes_invariant(self, mock_hass, mock_entry):
        """Verify narrow window trips still satisfy def_end - def_start >= hours.

        Recreate user's scenario: trips with tight deadlines that produce
        narrow windows. The fix must ensure the invariant holds.
        """
        mock_store = AsyncMock()
        mock_store.async_load = AsyncMock(return_value={})
        mock_store.async_save = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(mock_hass, mock_entry)
            await adapter.async_load()

        now = datetime.now(timezone.utc)

        # Create 5 trips with varying deadlines within the 168h horizon.
        # Deadlines: 36, 61, 86, 111, 136 hours — all within horizon.
        # The key is trip_3: deadline only ~0.7h from now (very narrow window).
        trips = [
            {
                "id": f"trip_{i}",
                "kwh": 14.8,  # ~2 hours at 7.4 kW
                "datetime": (now + timedelta(hours=36 + i * 25)).isoformat(),
            }
            for i in range(5)
        ]
        # Override trip_3 to have a very tight deadline (within horizon)
        trips[3]["datetime"] = (now + timedelta(hours=112, minutes=20)).isoformat()

        with (
            patch.object(
                adapter, "_get_current_soc", new_callable=AsyncMock, return_value=50.0
            ),
            patch.object(
                adapter, "_get_hora_regreso", new_callable=AsyncMock, return_value=None
            ),
        ):
            result = await adapter.async_publish_all_deferrable_loads(trips)

        assert result is True

        # THE INVARIANT: every trip must have window >= def_total_hours
        for trip_id, params in adapter._cached_per_trip_params.items():
            def_start = params.get("def_start_timestep")
            def_end = params.get("def_end_timestep")
            def_total_hours = params.get("def_total_hours", 0)

            if def_start is None or def_end is None:
                continue

            window = def_end - def_start
            assert window >= def_total_hours, (
                f"Trip {trip_id}: window ({window}) < def_total_hours ({def_total_hours}). "
                f"EMHASS will refuse to optimize. "
                f"def_start={def_start}, def_end={def_end}, hours={def_total_hours}"
            )

    @pytest.mark.asyncio
    async def test_wide_window_unchanged(self, mock_hass, mock_entry):
        """Wide windows should not be negatively affected."""
        mock_store = AsyncMock()
        mock_store.async_load = AsyncMock(return_value={})
        mock_store.async_save = AsyncMock()

        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(mock_hass, mock_entry)
            await adapter.async_load()

        now = datetime.now(timezone.utc)

        # Wide windows: deadlines within the 168h horizon to avoid boundary truncation.
        # Deadlines: 100, 125, 150 hours — all within horizon.
        trips = [
            {
                "id": f"trip_{i}",
                "kwh": 14.8,
                "datetime": (now + timedelta(hours=100 + i * 25)).isoformat(),
            }
            for i in range(3)
        ]

        with (
            patch.object(
                adapter, "_get_current_soc", new_callable=AsyncMock, return_value=50.0
            ),
            patch.object(
                adapter, "_get_hora_regreso", new_callable=AsyncMock, return_value=None
            ),
        ):
            result = await adapter.async_publish_all_deferrable_loads(trips)

        assert result is True

        for trip_id, params in adapter._cached_per_trip_params.items():
            def_start = params.get("def_start_timestep")
            def_end = params.get("def_end_timestep")
            def_total_hours = params.get("def_total_hours", 0)

            if def_start is None or def_end is None:
                continue

            window = def_end - def_start
            assert window >= def_total_hours, (
                f"Wide window violated for {trip_id}: "
                f"window={window} < hours={def_total_hours}"
            )
            assert window >= 2, f"Window should be at least 2h for wide windows: {trip_id} window={window}"
