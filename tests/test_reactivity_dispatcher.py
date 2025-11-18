"""Reactive updates via dispatcher for EV Trip Planner."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.const import SIGNAL_TRIPS_UPDATED


@pytest.mark.asyncio
async def test_trip_manager_dispatches_signal_on_save():
    """TripManager should emit dispatcher signal after saving trips."""
    from custom_components.ev_trip_planner.trip_manager import TripManager

    hass = MagicMock()

    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=[])
    mock_store.async_save = AsyncMock()

    with patch(
        "custom_components.ev_trip_planner.trip_manager.Store", return_value=mock_store
    ), patch(
        "custom_components.ev_trip_planner.trip_manager.async_dispatcher_send"
    ) as send:
        mgr = TripManager(hass, vehicle_id="Chispitas Test")
        # Add a recurring trip (this calls _async_save_trips internally)
        await mgr.async_add_recurring_trip(
            dia_semana="lunes", hora="09:00", km=10, kwh=1.5, descripcion="Test"
        )

        # Dispatcher called with vehicle-scoped signal
        send.assert_called()
        args, kwargs = send.call_args
        assert args[0] is hass
        assert args[1] == f"{SIGNAL_TRIPS_UPDATED}_Chispitas Test"


@pytest.mark.asyncio
async def test_sensor_subscribes_and_schedules_update_on_signal():
    """Sensor subscribes to dispatcher and schedules update on signal."""
    from custom_components.ev_trip_planner.sensor import RecurringTripsCountSensor

    hass = MagicMock()

    # Mock TripManager returning one recurring trip
    mgr = MagicMock()
    mgr.async_get_all_trips = AsyncMock(
        return_value=[{"id": "rec_lun_1", "tipo": "recurrente", "dia_semana": "lunes"}]
    )

    # Capture dispatcher subscription and invoke callback immediately
    callbacks = []

    def fake_connect(hass_, signal, cb):
        callbacks.append(cb)
        # Return an unregister function
        return lambda: None

    with patch(
        "custom_components.ev_trip_planner.sensor.async_dispatcher_connect",
        side_effect=fake_connect,
    ):
        s = RecurringTripsCountSensor(hass, vehicle_id="Chispitas Test", trip_manager=mgr)
        # Simulate entity added to hass
        await s.async_added_to_hass()
        # Trigger dispatcher callback
        assert callbacks, "No dispatcher callback registered"
        # Patch schedule update to observe it being called
        with patch.object(s, "async_schedule_update_ha_state") as sched:
            await callbacks[0]()
            sched.assert_called_once_with(True)

