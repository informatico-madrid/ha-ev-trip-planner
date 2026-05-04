"""Targeted tests for the TripManager config-entry lookup branches added in fix.

Covers:
- Lookup using `self._entry_id` when provided.
- Fallback when `async_entries` raises (defaults to 50.0 battery capacity).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.mark.asyncio
async def test_entry_id_lookup_used_in_generate_power_profile() -> None:
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)

    entry = MagicMock()
    entry.entry_id = "entry_xyz"
    entry.data = {"vehicle_name": "veh", "battery_capacity_kwh": 70.0}

    # async_get_entry should be called with the entry_id
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    tm = TripManager(hass, "veh", entry_id="entry_xyz")
    tm.async_get_vehicle_soc = AsyncMock(return_value=80.0)

    captured = {}

    def fake_calc(**kwargs):
        captured.update(kwargs)
        return [0.0]

    with patch(
        "custom_components.ev_trip_planner.calculations.calculate_power_profile",
        side_effect=fake_calc,
    ):
        await tm.async_generate_power_profile()

    # verify battery_capacity from entry was used
    assert captured.get("battery_capacity_kwh") == 70.0


@pytest.mark.asyncio
async def test_async_entries_exception_uses_default_battery() -> None:
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)

    hass.config_entries = MagicMock()
    # No entry found by async_get_entry
    hass.config_entries.async_get_entry = MagicMock(return_value=None)

    # async_entries raises
    def raise_exc(*args, **kwargs):
        raise RuntimeError("boom")

    hass.config_entries.async_entries = MagicMock(side_effect=raise_exc)

    tm = TripManager(hass, "veh")
    tm.async_get_vehicle_soc = AsyncMock(return_value=80.0)

    captured = {}

    def fake_calc(**kwargs):
        captured.update(kwargs)
        return [0.0]

    with patch(
        "custom_components.ev_trip_planner.calculations.calculate_power_profile",
        side_effect=fake_calc,
    ):
        await tm.async_generate_power_profile()

    # Should have used default 50.0 when async_entries failed
    assert captured.get("battery_capacity_kwh") == 50.0

    @pytest.mark.asyncio
    async def _test_generate_power_profile_finds_entry_via_async_entries() -> None:
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(return_value=None)

        entry = MagicMock()
        entry.entry_id = "entry_e"
        entry.data = {"vehicle_name": "My Car", "battery_capacity_kwh": 55.0}

        hass.config_entries = MagicMock()
        # async_get_entry returns None for missing _entry_id
        hass.config_entries.async_get_entry = MagicMock(return_value=None)
        # async_entries returns the entry that matches by vehicle_name slug
        hass.config_entries.async_entries = MagicMock(return_value=[entry])

        vehicle_slug = "my_car"
        tm = TripManager(hass, vehicle_slug)
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

        assert captured.get("battery_capacity_kwh") == 55.0

    @pytest.mark.asyncio
    async def _test_generate_deferrables_schedule_uses_entry_from_async_entries():
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(return_value=None)

        entry = MagicMock()
        entry.entry_id = "entry_d"
        entry.data = {"vehicle_name": "veh", "battery_capacity_kwh": 42.0}

        hass.config_entries = MagicMock()
        hass.config_entries.async_get_entry = MagicMock(return_value=None)
        hass.config_entries.async_entries = MagicMock(return_value=[entry])

        tm = TripManager(hass, "veh")

        # Add one recurring trip so the schedule flow calls async_calcular_energia_necesaria
        now = __import__("datetime").datetime.now()
        tm._recurring_trips = {"r1": {"id": "r1", "activo": True, "hora": "08:00"}}

        tm._get_trip_time = lambda trip: now + __import__("datetime").timedelta(hours=2)
        tm.async_get_vehicle_soc = AsyncMock(return_value=20.0)

        captured_vehicle_config = {}

        async def fake_async_calcular_energia_necesaria(trip, vehicle_config):
            captured_vehicle_config.update(vehicle_config)
            return {"energia_necesaria_kwh": 1.0, "horas_carga_necesarias": 1.0}

        tm.async_calcular_energia_necesaria = AsyncMock(
            side_effect=fake_async_calcular_energia_necesaria
        )

        with patch(
            "homeassistant.helpers.storage.Store.async_load",
            new_callable=lambda: AsyncMock(return_value=None),
        ):
            with patch(
                "homeassistant.helpers.storage.Store.async_save",
                new_callable=lambda: AsyncMock(return_value=None),
            ):
                await tm.async_generate_deferrables_schedule()

        assert captured_vehicle_config.get("battery_capacity_kwh") == 42.0
