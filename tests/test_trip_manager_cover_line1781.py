"""Small test to cover direct config_entry.data.get branch in TripManager.

This ensures the exact line that assigns `battery_capacity` from
`config_entry.data.get(...)` is executed (coverage line 1781).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.mark.asyncio
async def test_generate_power_profile_uses_entry_id_lookup() -> None:
    """When TripManager is instantiated with `entry_id`, use it for lookup."""

    hass = MagicMock()

    entry_data = {"vehicle_name": "My Car", "battery_capacity_kwh": 63.0}
    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_1"
    mock_entry.data = MagicMock()
    mock_entry.data.get = MagicMock(
        side_effect=lambda key, default=None: entry_data.get(key, default)
    )

    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(
        side_effect=lambda x: mock_entry if x == "entry_1" else None
    )

    hass.async_add_executor_job = AsyncMock(return_value=None)
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp"

    tm = TripManager(hass, "my_car", entry_id="entry_1")
    tm.async_get_vehicle_soc = AsyncMock(return_value=80.0)

    captured = {}

    def fake_calculate_power_profile(**kwargs):
        captured.update(kwargs)
        return [0.0]

    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        new_callable=lambda: AsyncMock(return_value=None),
    ):
        with patch(
            "custom_components.ev_trip_planner.calculations.calculate_power_profile",
            side_effect=fake_calculate_power_profile,
        ):
            await tm.async_generate_power_profile()

    assert captured.get("battery_capacity_kwh") == 63.0


@pytest.mark.asyncio
async def test_generate_power_profile_skips_entries_with_no_data() -> None:
    """Ensure entries without `.data` are skipped (hits `continue`)."""

    hass = MagicMock()

    # First entry lacks .data -> should be skipped
    mock_entry_no_data = MagicMock()
    mock_entry_no_data.entry_id = "entry_none"
    mock_entry_no_data.data = None

    # Second entry has the battery capacity we expect to pick up
    entry_data = {"vehicle_name": "My Car", "battery_capacity_kwh": 64.0}
    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_2"
    mock_entry.data = MagicMock()
    mock_entry.data.get = MagicMock(
        side_effect=lambda key, default=None: entry_data.get(key, default)
    )

    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(
        return_value=[mock_entry_no_data, mock_entry]
    )
    hass.config_entries.async_get_entry = MagicMock(return_value=None)

    hass.async_add_executor_job = AsyncMock(return_value=None)
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp"

    tm = TripManager(hass, "my_car")
    tm.async_get_vehicle_soc = AsyncMock(return_value=80.0)

    captured = {}

    def fake_calculate_power_profile(**kwargs):
        captured.update(kwargs)
        return [0.0]

    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        new_callable=lambda: AsyncMock(return_value=None),
    ):
        with patch(
            "custom_components.ev_trip_planner.calculations.calculate_power_profile",
            side_effect=fake_calculate_power_profile,
        ):
            await tm.async_generate_power_profile()

    assert captured.get("battery_capacity_kwh") == 64.0
