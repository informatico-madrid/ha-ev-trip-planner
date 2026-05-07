"""Tests to exercise sensor CRUD hooks in TripManager.

Targets branches that call into `custom_components.ev_trip_planner.sensor` CRUD
functions (create/update/remove) and the EMHASS sensor variants.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.mark.asyncio
async def test_add_recurring_creates_sensors_and_emhass():
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)

    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.data = {"vehicle_name": "veh"}
    runtime = MagicMock()
    runtime.coordinator = MagicMock()
    entry.runtime_data = runtime

    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    tm = TripManager(hass, "veh", entry_id="entry1")

    # Patch storage I/O to avoid filesystem access
    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        new_callable=lambda: AsyncMock(return_value=None),
    ):
        with patch(
            "homeassistant.helpers.storage.Store.async_save",
            new_callable=lambda: AsyncMock(return_value=None),
        ):
            with patch(
                "custom_components.ev_trip_planner.sensor.async_create_trip_sensor",
                new_callable=lambda: AsyncMock(),
            ) as create_sensor:
                with patch(
                    "custom_components.ev_trip_planner.sensor.async_create_trip_emhass_sensor",
                    new_callable=lambda: AsyncMock(),
                ) as create_emhass:
                    await tm.async_add_recurring_trip(
                        dia_semana="lunes", hora="08:00", km=10, kwh=1
                    )

    assert create_sensor.await_count == 1
    # EMHASS create called because runtime_data.coordinator exists
    assert create_emhass.await_count == 1


@pytest.mark.asyncio
async def test_add_punctual_creates_sensors_and_emhass():
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)

    entry = MagicMock()
    entry.entry_id = "entry2"
    entry.data = {"vehicle_name": "veh"}
    runtime = MagicMock()
    runtime.coordinator = MagicMock()
    entry.runtime_data = runtime

    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    tm = TripManager(hass, "veh", entry_id="entry2")

    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        new_callable=lambda: AsyncMock(return_value=None),
    ):
        with patch(
            "homeassistant.helpers.storage.Store.async_save",
            new_callable=lambda: AsyncMock(return_value=None),
        ):
            with patch(
                "custom_components.ev_trip_planner.sensor.async_create_trip_sensor",
                new_callable=lambda: AsyncMock(),
            ) as create_sensor:
                with patch(
                    "custom_components.ev_trip_planner.sensor.async_create_trip_emhass_sensor",
                    new_callable=lambda: AsyncMock(),
                ) as create_emhass:
                    await tm.async_add_punctual_trip(
                        datetime_str="2026-01-01T09:00", km=5, kwh=0.5
                    )

    assert create_sensor.await_count == 1
    assert create_emhass.await_count == 1


@pytest.mark.asyncio
async def test_delete_trip_removes_sensors_and_emhass():
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)

    entry = MagicMock()
    entry.entry_id = "entry3"
    entry.data = {"vehicle_name": "veh"}
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    tm = TripManager(hass, "veh", entry_id="entry3")
    # Pre-populate a recurring trip
    trip_id = "rec_test_1"
    tm._recurring_trips[trip_id] = {"id": trip_id}

    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        new_callable=lambda: AsyncMock(return_value=None),
    ):
        with patch(
            "homeassistant.helpers.storage.Store.async_save",
            new_callable=lambda: AsyncMock(return_value=None),
        ):
            with patch(
                "custom_components.ev_trip_planner.sensor.async_remove_trip_sensor",
                new_callable=lambda: AsyncMock(),
            ) as rem_sensor:
                with patch(
                    "custom_components.ev_trip_planner.sensor.async_remove_trip_emhass_sensor",
                    new_callable=lambda: AsyncMock(),
                ) as rem_emhass:
                    await tm.async_delete_trip(trip_id)

    assert rem_sensor.await_count == 1
    assert rem_emhass.await_count == 1


@pytest.mark.asyncio
async def test_update_trip_calls_update_sensor():
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=None)

    tm = TripManager(hass, "veh")
    trip_id = "rec_upd"
    tm._recurring_trips[trip_id] = {"id": trip_id, "km": 10}

    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        new_callable=lambda: AsyncMock(return_value=None),
    ):
        with patch(
            "homeassistant.helpers.storage.Store.async_save",
            new_callable=lambda: AsyncMock(return_value=None),
        ):
            with patch(
                "custom_components.ev_trip_planner.sensor.async_update_trip_sensor",
                new_callable=lambda: AsyncMock(),
            ) as up_sensor:
                await tm.async_update_trip(trip_id, {"km": 20})

    assert up_sensor.await_count == 1
