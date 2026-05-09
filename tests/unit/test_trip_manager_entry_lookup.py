"""Test that detects incorrect config entry lookup in TripManager.

This test reproduces the bug where TripManager calls
`hass.config_entries.async_get_entry(self.vehicle_id)` instead of
using the config entry id, causing the code to fall back to the
default battery capacity (50.0) when `TripManager` was instantiated
without `entry_id`.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.mark.asyncio
async def test_async_generate_power_profile_respects_config_entry_battery_capacity() -> (
    None
):
    """The power profile calculation should use the config entry's battery capacity.

    This test sets up a `ConfigEntry` whose `entry_id` is different from the
    vehicle slug. It then instantiates `TripManager` WITHOUT passing the
    `entry_id` (the buggy code calls async_get_entry(self.vehicle_id)), and
    asserts that the battery capacity is taken from the config entry. The
    current buggy behavior will make this assertion fail because the code
    looks up the wrong key and falls back to 50.0 kWh.
    """

    # Prepare a fake Home Assistant object
    hass = MagicMock()

    # Create a fake ConfigEntry with a battery capacity different from 50
    entry_data = {
        "vehicle_name": "My Car",
        "battery_capacity_kwh": 62.0,
    }
    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_1"
    # Provide a .data that supports .get(key, default)
    mock_entry.data = MagicMock()
    mock_entry.data.get = MagicMock(
        side_effect=lambda key, default=None: entry_data.get(key, default)
    )

    # Make async_entries return the entry so TripManager can find it by vehicle_name
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    hass.config_entries.async_get_entry = MagicMock(
        side_effect=lambda x: mock_entry if x == "entry_1" else None
    )

    # Minimal hass pieces used by TripManager
    hass.async_add_executor_job = AsyncMock(return_value=None)
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp"

    # Instantiate TripManager with vehicle_id equal to the slug of "My Car"
    vehicle_slug = "my_car"
    tm = TripManager(hass, vehicle_slug)

    # Ensure async_get_vehicle_soc returns a deterministic value
    tm.async_get_vehicle_soc = AsyncMock(return_value=80.0)

    # Patch the calculate_power_profile function to capture the battery_capacity_kwh argument
    captured: dict = {}

    def fake_calculate_power_profile(**kwargs):
        captured.update(kwargs)
        # Return a trivial profile
        return [0.0]

    # Patch Store.async_load to avoid HA storage filesystem interaction in this unit test
    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        new_callable=lambda: AsyncMock(return_value=None),
    ):
        with patch(
            "custom_components.ev_trip_planner.calculations.calculate_power_profile",
            side_effect=fake_calculate_power_profile,
        ):
            await tm.async_generate_power_profile()

    # We expect the test to fail with the current buggy code because
    # battery_capacity_kwh will be 50.0 (fallback) instead of 62.0
    assert captured.get("battery_capacity_kwh") == 62.0
