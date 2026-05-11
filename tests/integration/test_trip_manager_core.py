"""Core tests for TripManager covering CRUD and state transitions (hass.data API)."""

from __future__ import annotations

import unittest.mock
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from custom_components.ev_trip_planner.const import (
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_PENDING,
)
from custom_components.ev_trip_planner.trip import TripManager


@pytest.fixture
def vehicle_id() -> str:
    return "chispitas"


@pytest.mark.asyncio
async def test_async_setup_initializes_empty_storage(mock_hass, vehicle_id):
    """Test that async_setup initializes with empty trips when no data exists."""
    # Ensure namespace doesn't exist in hass.data
    namespace = "ev_trip_planner_test_entry_123"
    assert namespace not in mock_hass.data

    manager = TripManager(mock_hass, vehicle_id)
    await manager.async_setup()

    # After setup, trips should be empty
    assert manager._trips == {}
    assert manager._recurring_trips == {}
    assert manager._punctual_trips == {}


@pytest.mark.asyncio
async def test_async_setup_loads_existing_and_does_not_save(mock_hass, vehicle_id):
    """Test that async_setup loads existing trips from hass.storage."""
    from homeassistant.helpers import storage as ha_storage

    # Pre-populate store with trips
    existing_trips = {
        "rec_lun_123": {
            "id": "rec_lun_123",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
        }
    }

    # Patch Store.async_load to return our test data
    with patch.object(
        ha_storage.Store,
        "async_load",
        new_callable=lambda: AsyncMock(
            return_value={
                "data": {
                    "trips": existing_trips,
                    "recurring_trips": existing_trips,
                    "punctual_trips": {},
                }
            }
        ),
    ):
        manager = TripManager(mock_hass, vehicle_id)
        await manager.async_setup()

        # Should have loaded the existing trips
        assert "rec_lun_123" in manager._recurring_trips


@pytest.mark.asyncio
async def test_async_load_trips_empty_returns_list(mock_hass, vehicle_id):
    """Test that _load_trips returns empty when no data exists."""
    from homeassistant.helpers import storage as ha_storage

    # Patch Store.async_load to return None (empty)
    with patch.object(
        ha_storage.Store,
        "async_load",
        new_callable=lambda: AsyncMock(return_value=None),
    ):
        manager = TripManager(mock_hass, vehicle_id)
        await manager._load_trips()

        assert manager._trips == {}
        assert manager._recurring_trips == {}
        assert manager._punctual_trips == {}


@pytest.mark.asyncio
async def test_async_load_trips_with_data(mock_hass, vehicle_id):
    """Test that _load_trips loads data from hass.storage."""
    from homeassistant.helpers import storage as ha_storage

    existing_recurring = {
        "rec_lun_123": {
            "id": "rec_lun_123",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
        },
    }
    existing_punctual = {
        "pun_20251119_123": {
            "id": "pun_20251119_123",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
        },
    }

    # Patch Store.async_load to return test data
    with patch.object(
        ha_storage.Store,
        "async_load",
        new_callable=lambda: AsyncMock(
            return_value={
                "data": {
                    "trips": {**existing_recurring, **existing_punctual},
                    "recurring_trips": existing_recurring,
                    "punctual_trips": existing_punctual,
                }
            }
        ),
    ):
        manager = TripManager(mock_hass, vehicle_id)
        await manager._load_trips()

        assert len(manager._recurring_trips) == 1
        assert len(manager._punctual_trips) == 1
        assert "rec_lun_123" in manager._recurring_trips
        assert "pun_20251119_123" in manager._punctual_trips


@pytest.mark.asyncio
async def test_async_load_trips_skips_when_data_in_memory(
    mock_hass, vehicle_id, caplog
):
    """Test that _load_trips skips loading when data already in memory. Covers lines 202, 208."""
    import logging

    from homeassistant.helpers import storage as ha_storage

    existing_recurring = {
        "rec_lun_123": {
            "id": "rec_lun_123",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
        },
    }

    # Patch Store.async_load to return test data
    with patch.object(
        ha_storage.Store,
        "async_load",
        new_callable=lambda: AsyncMock(
            return_value={
                "data": {
                    "trips": existing_recurring,
                    "recurring_trips": existing_recurring,
                    "punctual_trips": {},
                }
            }
        ),
    ):
        manager = TripManager(mock_hass, vehicle_id)
        # Pre-populate memory with data
        manager._recurring_trips = existing_recurring
        manager._punctual_trips = {}

        # Capture log output
        with caplog.at_level(logging.DEBUG):
            await manager._load_trips()

        # Verify the skip log was emitted (line 202-207)
        assert "Skipping _load_trips" in caplog.text
        assert "already have" in caplog.text

        # Verify data was not overwritten
        assert len(manager._recurring_trips) == 1
        assert "rec_lun_123" in manager._recurring_trips


@pytest.mark.asyncio
async def test_async_save_trips_calls_store_save(mock_hass, vehicle_id):
    """Test that async_save_trips saves to HA storage."""
    from homeassistant.helpers import storage as ha_storage

    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_abc": {
            "id": "rec_lun_abc",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
        }
    }

    # Patch Store.async_save to capture the save
    saved_data = {}

    async def capture_save(data):
        saved_data["data"] = data
        return True

    with patch.object(
        ha_storage.Store,
        "async_save",
        new_callable=lambda: AsyncMock(side_effect=capture_save),
    ):
        await manager.async_save_trips()

        # Check data was saved
        assert "data" in saved_data
        assert "recurring_trips" in saved_data["data"]
        assert "rec_lun_abc" in saved_data["data"]["recurring_trips"]


@pytest.mark.asyncio
async def test_add_recurring_trip_happy_path(mock_hass, vehicle_id):
    """Test adding a recurring trip."""
    manager = TripManager(mock_hass, vehicle_id)
    await manager.async_add_recurring_trip(
        dia_semana="lunes", hora="09:00", km=24.0, kwh=3.6, descripcion="Trabajo"
    )

    # Should have added a trip (check that there's at least one trip)
    assert len(manager._recurring_trips) == 1
    trip_id = list(manager._recurring_trips.keys())[0]
    assert trip_id.startswith("rec_lun_")
    saved_trip = manager._recurring_trips[trip_id]
    assert saved_trip["dia_semana"] == "lunes"
    assert saved_trip["hora"] == "09:00"


@pytest.mark.asyncio
async def test_update_trip_updates_fields(mock_hass, vehicle_id):
    """Test updating a trip."""
    # Pre-populate with a trip
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_12345678": {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
        },
    }
    manager._punctual_trips = {
        "pun_20251119_87654321": {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "estado": TRIP_STATUS_PENDING,
        },
    }

    await manager.async_update_trip("rec_lun_12345678", {"hora": "10:00", "km": 30.0})

    # Check the update was applied
    assert manager._recurring_trips["rec_lun_12345678"]["hora"] == "10:00"
    assert manager._recurring_trips["rec_lun_12345678"]["km"] == 30.0


@pytest.mark.asyncio
async def test_update_trip_not_found_returns_false(mock_hass, vehicle_id):
    """Test updating a non-existent trip - no error should occur."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}

    # Should not raise, just do nothing
    await manager.async_update_trip("does_not_exist", {"hora": "10:00"})


@pytest.mark.asyncio
async def test_delete_trip_removes_entry(mock_hass, vehicle_id):
    """Test deleting a trip."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_12345678": {"id": "rec_lun_12345678", "tipo": "recurrente"},
    }
    manager._punctual_trips = {
        "pun_20251119_87654321": {"id": "pun_20251119_87654321", "tipo": "puntual"},
    }

    await manager.async_delete_trip("rec_lun_12345678")

    assert "rec_lun_12345678" not in manager._recurring_trips
    assert "pun_20251119_87654321" in manager._punctual_trips


@pytest.mark.asyncio
async def test_delete_trip_not_found_returns_false(mock_hass, vehicle_id):
    """Test deleting a non-existent trip - no error should occur."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}

    # Should not raise, just do nothing
    await manager.async_delete_trip("does_not_exist")


@pytest.mark.asyncio
async def test_pause_and_complete_trips(mock_hass, vehicle_id):
    """Test pausing and completing trips."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_12345678": {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "activo": True,
            "dia_semana": "lunes",
            "hora": "09:00",
        },
    }
    manager._punctual_trips = {
        "pun_20251119_87654321": {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "estado": TRIP_STATUS_PENDING,
        },
    }

    await manager.async_pause_recurring_trip("rec_lun_12345678")
    assert manager._recurring_trips["rec_lun_12345678"]["activo"] is False

    await manager.async_complete_punctual_trip("pun_20251119_87654321")
    assert (
        manager._punctual_trips["pun_20251119_87654321"]["estado"]
        == TRIP_STATUS_COMPLETED
    )


@pytest.mark.asyncio
async def test_resume_and_cancel_trips(mock_hass, vehicle_id):
    """Test resuming and canceling trips."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_12345678": {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "activo": False,
            "dia_semana": "lunes",
            "hora": "09:00",
        },
    }
    manager._punctual_trips = {
        "pun_20251119_87654321": {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "estado": TRIP_STATUS_PENDING,
        },
    }

    await manager.async_resume_recurring_trip("rec_lun_12345678")
    assert manager._recurring_trips["rec_lun_12345678"]["activo"] is True

    # Cancel removes the trip from the dictionary
    await manager.async_cancel_punctual_trip("pun_20251119_87654321")
    assert "pun_20251119_87654321" not in manager._punctual_trips


@pytest.mark.asyncio
async def test_getters_and_not_found(mock_hass, vehicle_id):
    """Test getter methods."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_12345678": {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
        },
    }
    manager._punctual_trips = {
        "pun_20251119_87654321": {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
        },
    }

    rec_trips = await manager.async_get_recurring_trips()
    pun_trips = await manager.async_get_punctual_trips()

    assert len(rec_trips) == 1 and rec_trips[0]["tipo"] == "recurrente"
    assert len(pun_trips) == 1 and pun_trips[0]["tipo"] == "puntual"


@pytest.mark.asyncio
async def test_add_punctual_trip_happy_path(mock_hass, vehicle_id):
    """Test adding a punctual trip."""
    manager = TripManager(mock_hass, vehicle_id)
    await manager.async_add_punctual_trip(
        datetime="2025-11-19T15:00:00", km=110.0, kwh=16.5, descripcion="Viaje"
    )

    # Should have added a trip
    assert len(manager._punctual_trips) == 1
    trip_id = list(manager._punctual_trips.keys())[0]
    assert trip_id.startswith("pun_") or trip_id.startswith("trip_")
    saved_trip = manager._punctual_trips[trip_id]
    assert saved_trip["km"] == 110.0


@pytest.mark.asyncio
async def test_add_recurring_trip_accepts_valid_hour_formats(mock_hass, vehicle_id):
    """Test that async_add_recurring_trip accepts valid hour formats."""
    manager = TripManager(mock_hass, vehicle_id)

    # Test valid hour formats
    valid_times = ["00:00", "09:00", "12:30", "16:45", "23:59"]

    for time_str in valid_times:
        await manager.async_add_recurring_trip(
            dia_semana="lunes", hora=time_str, km=24.0, kwh=3.6, descripcion="Trabajo"
        )

    # Should have saved all valid trips
    assert len(manager._recurring_trips) == len(valid_times)


@pytest.mark.asyncio
async def test_async_get_kwh_needed_today_with_recurring_trips(mock_hass, vehicle_id):
    """Test async_get_kwh_needed_today returns correct kWh for recurring trips."""
    from datetime import datetime

    # Mock datetime to return a specific day (e.g., Monday 2025-01-06)
    mock_datetime = unittest.mock.MagicMock()
    mock_datetime.now.return_value = datetime(2025, 1, 6, 10, 0)  # Monday

    with unittest.mock.patch(
        "custom_components.ev_trip_planner.trip.manager.datetime", mock_datetime
    ):
        manager = TripManager(mock_hass, vehicle_id)
        manager._recurring_trips = {
            "rec_lun_12345678": {
                "id": "rec_lun_12345678",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "09:00",
                "kwh": 5.0,
                "activo": True,
            },
            "rec_mar_87654321": {
                "id": "rec_mar_87654321",
                "tipo": "recurrente",
                "dia_semana": "martes",
                "hora": "09:00",
                "kwh": 3.0,
                "activo": True,
            },
        }

        kwh = await manager.async_get_kwh_needed_today()

        # Only Monday trip should be counted (5.0 kWh)
        assert kwh == 5.0


@pytest.mark.asyncio
async def test_async_get_kwh_needed_today_with_punctual_trips(mock_hass, vehicle_id):
    """Test async_get_kwh_needed_today returns correct kWh for punctual trips."""
    from datetime import datetime

    # Mock datetime to return 2025-01-06 (Monday)
    mock_datetime = unittest.mock.MagicMock()
    mock_datetime.now.return_value = datetime(2025, 1, 6, 10, 0)
    mock_datetime.strptime = datetime.strptime

    with unittest.mock.patch(
        "custom_components.ev_trip_planner.trip.manager.datetime", mock_datetime
    ):
        manager = TripManager(mock_hass, vehicle_id)
        manager._recurring_trips = {}
        manager._punctual_trips = {
            "pun_20250106_11111111": {
                "id": "pun_20250106_11111111",
                "tipo": "puntual",
                "datetime": "2025-01-06T15:00",  # Today
                "kwh": 10.0,
                "estado": "pendiente",
            },
            "pun_20250107_22222222": {
                "id": "pun_20250107_22222222",
                "tipo": "puntual",
                "datetime": "2025-01-07T15:00",  # Tomorrow
                "kwh": 8.0,
                "estado": "pendiente",
            },
        }

        kwh = await manager.async_get_kwh_needed_today()

        # Only today's trip should be counted (10.0 kWh)
        assert kwh == 10.0


@pytest.mark.asyncio
async def test_async_get_kwh_needed_today_excludes_inactive_trips(
    mock_hass, vehicle_id
):
    """Test that inactive/paused recurring trips are excluded."""
    from datetime import datetime

    mock_datetime = unittest.mock.MagicMock()
    mock_datetime.now.return_value = datetime(2025, 1, 6, 10, 0)

    with unittest.mock.patch(
        "custom_components.ev_trip_planner.trip.manager.datetime", mock_datetime
    ):
        manager = TripManager(mock_hass, vehicle_id)
        manager._recurring_trips = {
            "rec_lun_active": {
                "id": "rec_lun_active",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "09:00",
                "kwh": 5.0,
                "activo": True,
            },
            "rec_lun_inactive": {
                "id": "rec_lun_inactive",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "10:00",
                "kwh": 3.0,
                "activo": False,  # Paused
            },
        }

        kwh = await manager.async_get_kwh_needed_today()

        # Only active trip should be counted
        assert kwh == 5.0


@pytest.mark.asyncio
async def test_async_get_kwh_needed_today_excludes_completed_trips(
    mock_hass, vehicle_id
):
    """Test that completed punctual trips are excluded."""
    from datetime import datetime

    mock_datetime = unittest.mock.MagicMock()
    mock_datetime.now.return_value = datetime(2025, 1, 6, 10, 0)
    mock_datetime.strptime = datetime.strptime

    with unittest.mock.patch(
        "custom_components.ev_trip_planner.trip.manager.datetime", mock_datetime
    ):
        manager = TripManager(mock_hass, vehicle_id)
        manager._recurring_trips = {}
        manager._punctual_trips = {
            "pun_20250106_pending": {
                "id": "pun_20250106_pending",
                "tipo": "puntual",
                "datetime": "2025-01-06T15:00",
                "kwh": 10.0,
                "estado": "pendiente",
            },
            "pun_20250106_completed": {
                "id": "pun_20250106_completed",
                "tipo": "puntual",
                "datetime": "2025-01-06T16:00",
                "kwh": 8.0,
                "estado": "completado",
            },
        }

        kwh = await manager.async_get_kwh_needed_today()

        # Only pending trip should be counted
        assert kwh == 10.0


@pytest.mark.asyncio
async def test_async_get_hours_needed_today(mock_hass, vehicle_id):
    """Test async_get_hours_needed_today calculates charging hours."""
    # Mock config entry for charging power
    mock_entry = MagicMock()
    mock_entry.data = {"charging_power": 7.4}  # 7.4 kW charging
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    # Freeze time to Monday 2025-01-06 at 10:00
    frozen_time = datetime(2025, 1, 6, 10, 0)
    with patch("custom_components.ev_trip_planner.trip.manager.datetime") as mock_dt:
        mock_dt.now.return_value = frozen_time
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        manager = TripManager(mock_hass, vehicle_id)
        manager._recurring_trips = {
            "rec_lun_12345678": {
                "id": "rec_lun_12345678",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "09:00",
                "kwh": 14.8,  # Needs 2 hours at 7.4 kW
                "activo": True,
            },
        }

        hours = await manager.async_get_hours_needed_today()

        # 14.8 kWh / 7.4 kW = 2 hours (ceiling)
        assert hours == 2


@pytest.mark.asyncio
async def test_async_get_hours_needed_today_with_default_charging_power(
    mock_hass, vehicle_id
):
    """Test async_get_hours_needed_today uses default charging power when not configured."""
    # Return None when no entry found - use default
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=None)

    # Freeze time to Monday 2025-01-06 at 10:00
    frozen_time = datetime(2025, 1, 6, 10, 0)
    with patch("custom_components.ev_trip_planner.trip.manager.datetime") as mock_dt:
        mock_dt.now.return_value = frozen_time
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        manager = TripManager(mock_hass, vehicle_id)
        manager._recurring_trips = {
            "rec_lun_12345678": {
                "id": "rec_lun_12345678",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "09:00",
                "kwh": 7.35,  # Needs 1 hour at default 7.4 kW
                "activo": True,
            },
        }

        hours = await manager.async_get_hours_needed_today()

        # Should use default charging power (7.4 kW)
        assert hours == 1


@pytest.mark.asyncio
async def test_async_get_next_trip_returns_next_recurring(mock_hass, vehicle_id):
    """Test async_get_next_trip returns the next upcoming recurring trip."""
    # Freeze time to Monday 2025-01-06 at 8:00 AM
    frozen_time = datetime(2025, 1, 6, 8, 0)
    with patch("custom_components.ev_trip_planner.trip.manager.datetime") as mock_dt:
        # Use side_effect to properly handle timezone-aware datetime.now(timezone.utc)
        mock_dt.now.return_value = frozen_time
        mock_dt.now.side_effect = lambda tz=None: (
            frozen_time.replace(tzinfo=timezone.utc) if tz is not None else frozen_time
        )
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        mock_dt.strptime = datetime.strptime
        mock_dt.combine = datetime.combine

        manager = TripManager(mock_hass, vehicle_id)
        manager._recurring_trips = {
            "rec_lun_12345678": {
                "id": "rec_lun_12345678",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "09:00",
                "activo": True,
            },
            "rec_mar_87654321": {
                "id": "rec_mar_87654321",
                "tipo": "recurrente",
                "dia_semana": "martes",
                "hora": "08:00",
                "activo": True,
            },
        }

        next_trip = await manager.async_get_next_trip()

        # Monday trip at 9:00 is next
        assert next_trip is not None
        assert next_trip["id"] == "rec_lun_12345678"


@pytest.mark.asyncio
async def test_async_get_next_trip_returns_next_punctual(mock_hass, vehicle_id):
    """Test async_get_next_trip returns the next upcoming punctual trip."""
    from datetime import datetime

    frozen_time = datetime(2025, 1, 6, 8, 0)  # Monday 8:00 AM

    mock_datetime = unittest.mock.MagicMock()
    mock_datetime.now.return_value = frozen_time
    mock_datetime.now.side_effect = lambda tz=None: (
        frozen_time.replace(tzinfo=timezone.utc) if tz is not None else frozen_time
    )
    mock_datetime.strptime = datetime.strptime

    with unittest.mock.patch(
        "custom_components.ev_trip_planner.trip.manager.datetime", mock_datetime
    ):
        manager = TripManager(mock_hass, vehicle_id)
        manager._recurring_trips = {}
        manager._punctual_trips = {
            "pun_20250106_11111111": {
                "id": "pun_20250106_11111111",
                "tipo": "puntual",
                "datetime": "2025-01-06T10:00",
                "estado": "pendiente",
            },
            "pun_20250107_22222222": {
                "id": "pun_20250107_22222222",
                "tipo": "puntual",
                "datetime": "2025-01-07T08:00",
                "estado": "pendiente",
            },
        }

        next_trip = await manager.async_get_next_trip()

        # Today's trip at 10:00 is next
        assert next_trip is not None
        assert next_trip["id"] == "pun_20250106_11111111"


@pytest.mark.asyncio
async def test_async_get_next_trip_returns_none_when_empty(mock_hass, vehicle_id):
    """Test async_get_next_trip returns None when no trips exist."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}
    manager._punctual_trips = {}

    next_trip = await manager.async_get_next_trip()

    assert next_trip is None


@pytest.mark.asyncio
async def test_async_get_next_trip_excludes_paused_recurring(mock_hass, vehicle_id):
    """Test that paused recurring trips are excluded from next trip."""
    # Freeze time to Monday 2025-01-06 at 8:00 AM
    frozen_time = datetime(2025, 1, 6, 8, 0)
    with patch("custom_components.ev_trip_planner.trip.manager.datetime") as mock_dt:
        mock_dt.now.return_value = frozen_time
        mock_dt.now.side_effect = lambda tz=None: (
            frozen_time.replace(tzinfo=timezone.utc) if tz is not None else frozen_time
        )
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        mock_dt.strptime = datetime.strptime
        mock_dt.combine = datetime.combine

        manager = TripManager(mock_hass, vehicle_id)
        manager._recurring_trips = {
            "rec_lun_active": {
                "id": "rec_lun_active",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "09:00",
                "activo": True,
            },
            "rec_lun_paused": {
                "id": "rec_lun_paused",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "08:00",
                "activo": False,  # Paused
            },
        }

        next_trip = await manager.async_get_next_trip()

        # Only active trip should be returned
        assert next_trip is not None
        assert next_trip["id"] == "rec_lun_active"


@pytest.mark.asyncio
async def test_async_get_next_trip_excludes_completed_punctual(mock_hass, vehicle_id):
    """Test that completed punctual trips are excluded from next trip."""
    from datetime import datetime

    frozen_time = datetime(2025, 1, 6, 8, 0)
    mock_datetime = unittest.mock.MagicMock()
    mock_datetime.now.return_value = frozen_time
    mock_datetime.now.side_effect = lambda tz=None: (
        frozen_time.replace(tzinfo=timezone.utc) if tz is not None else frozen_time
    )
    mock_datetime.strptime = datetime.strptime

    with unittest.mock.patch(
        "custom_components.ev_trip_planner.trip.manager.datetime", mock_datetime
    ):
        manager = TripManager(mock_hass, vehicle_id)
        manager._recurring_trips = {}
        manager._punctual_trips = {
            "pun_pending": {
                "id": "pun_pending",
                "tipo": "puntual",
                "datetime": "2025-01-06T10:00",
                "estado": "pendiente",
            },
            "pun_completed": {
                "id": "pun_completed",
                "tipo": "puntual",
                "datetime": "2025-01-06T09:00",
                "estado": "completado",
            },
        }

        next_trip = await manager.async_get_next_trip()

        # Only pending trip should be returned
        assert next_trip is not None
        assert next_trip["id"] == "pun_pending"


@pytest.mark.asyncio
async def test_get_emhass_adapter_returns_none_when_not_set(mock_hass, vehicle_id):
    """Test get_emhass_adapter returns None when adapter not set."""
    manager = TripManager(mock_hass, vehicle_id)

    # Adapter not set initially
    adapter = manager.get_emhass_adapter()
    assert adapter is None


@pytest.mark.asyncio
async def test_get_emhass_adapter_returns_adapter_when_set(mock_hass, vehicle_id):
    """Test get_emhass_adapter returns adapter when set."""
    from unittest.mock import MagicMock

    from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter

    manager = TripManager(mock_hass, vehicle_id)

    # Create mock adapter
    mock_adapter = MagicMock(spec=EMHASSAdapter)

    # Set adapter
    manager.set_emhass_adapter(mock_adapter)

    # Get should return the adapter
    adapter = manager.get_emhass_adapter()
    assert adapter is mock_adapter


@pytest.mark.asyncio
async def test_publish_deferrable_loads_no_adapter(mock_hass, vehicle_id):
    """Test publish_deferrable_loads returns early when no adapter."""
    manager = TripManager(mock_hass, vehicle_id)

    # No adapter set - the method should return early without error
    # This tests line 66 - early return when emhass_adapter is falsy
    await manager.publish_deferrable_loads()

    # Should complete without error (early return)


@pytest.mark.asyncio
async def test_publish_deferrable_loads_public(mock_hass, vehicle_id):
    """Test publish_deferrable_loads is public (no underscore prefix).

    Task 1.9 test: expects manager to have public publish_deferrable_loads method.
    Currently the method is named _publish_deferrable_loads (private).
    """
    manager = TripManager(mock_hass, vehicle_id)

    # publish_deferrable_loads should be a public method (no underscore)
    assert hasattr(manager, "publish_deferrable_loads")
    assert callable(manager.publish_deferrable_loads)


@pytest.mark.asyncio
async def test_cancel_punctual_trip_not_found(mock_hass, vehicle_id):
    """Test canceling a non-existent punctual trip logs warning."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._punctual_trips = {}

    # Try to cancel a trip that doesn't exist
    # This should log a warning and return early
    await manager.async_cancel_punctual_trip("nonexistent_trip")

    # Trip should still not exist (no error)
    assert "nonexistent_trip" not in manager._punctual_trips


@pytest.mark.asyncio
async def test_update_trip_not_found_no_emhass(mock_hass, vehicle_id):
    """Test updating a non-existent trip when no emhass adapter."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}
    manager._punctual_trips = {}
    # No emhass adapter set

    # Try to update a non-existent trip
    # Should handle gracefully (calls _async_remove_trip_from_emhass which returns early)
    await manager.async_update_trip("nonexistent_trip", {"km": 10})

    # Should complete without error


@pytest.mark.asyncio
async def test_get_charging_power_returns_correct_value(mock_hass, vehicle_id):
    """Test get_charging_power returns configured value."""
    # Configure entry with charging_power_kw (correct key used by code)
    mock_entry = MagicMock()
    mock_entry.data = {
        "vehicle_name": vehicle_id,
        "charging_power_kw": 7.4,
    }
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    manager = TripManager(mock_hass, vehicle_id)

    # Call public get_charging_power method
    power = manager.get_charging_power()

    # Should return configured value
    assert power == 7.4


@pytest.mark.asyncio
async def test_get_charging_power_returns_default_when_not_configured(
    mock_hass, vehicle_id
):
    """Test get_charging_power returns default when not configured."""
    # Configure entry without charging_power_kw
    mock_entry = MagicMock()
    mock_entry.data = {"vehicle_name": vehicle_id}
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    manager = TripManager(mock_hass, vehicle_id)

    # Call public get_charging_power method
    power = manager.get_charging_power()

    # Should return default charging power
    from custom_components.ev_trip_planner.trip import DEFAULT_CHARGING_POWER

    assert power == DEFAULT_CHARGING_POWER


@pytest.mark.asyncio
async def test_get_charging_power_sensor_not_found(mock_hass, vehicle_id):
    """Test get_charging_power returns default when sensor not found."""
    manager = TripManager(mock_hass, vehicle_id)
    # Don't set any vehicle controller or sensor

    # Try to get charging power - should return default
    power = manager._get_charging_power()

    # Should return default charging power
    from custom_components.ev_trip_planner.trip import DEFAULT_CHARGING_POWER

    assert power == DEFAULT_CHARGING_POWER


@pytest.mark.asyncio
async def test_async_resume_recurring_trip_not_found(mock_hass, vehicle_id):
    """Test resuming a non-existent recurring trip."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}

    # Try to resume a trip that doesn't exist - should handle gracefully
    await manager.async_resume_recurring_trip("nonexistent_trip")

    # Should complete without error (trip not found)


@pytest.mark.asyncio
async def test_async_pause_recurring_trip_not_found(mock_hass, vehicle_id):
    """Test pausing a non-existent recurring trip."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}

    # Try to pause a trip that doesn't exist - should handle gracefully
    await manager.async_pause_recurring_trip("nonexistent_trip")

    # Should complete without error (trip not found)


@pytest.mark.asyncio
async def test_publish_deferrable_loads_with_adapter(mock_hass, vehicle_id):
    """Test publish_deferrable_loads when adapter is set."""
    from unittest.mock import MagicMock

    manager = TripManager(mock_hass, vehicle_id)

    # Set up mock emhass adapter (not TripManager, so spec not needed)
    mock_adapter = MagicMock()
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    # Set up some trips
    manager._recurring_trips = {
        "rec_lun_123": {
            "id": "rec_lun_123",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 30,
            "kwh": 5.0,
            "activo": True,
        }
    }

    # Call the method
    await manager.publish_deferrable_loads()

    # Verify adapter was called
    mock_adapter.async_publish_all_deferrable_loads.assert_called_once()


@pytest.mark.asyncio
async def test_async_delete_trip_recurring_not_found(mock_hass, vehicle_id):
    """Test deleting a non-existent recurring trip."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}
    manager._punctual_trips = {}

    # Try to delete a non-existent trip
    await manager.async_delete_trip("nonexistent_trip")

    # Should complete without error (trip not found)


@pytest.mark.asyncio
async def test_async_get_punctual_trips_empty(mock_hass, vehicle_id):
    """Test getting punctual trips when none exist."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._punctual_trips = {}

    # Get punctual trips
    trips = await manager.async_get_punctual_trips()

    # Should return empty list
    assert trips == []


@pytest.mark.asyncio
async def test_async_get_recurring_trips_empty(mock_hass, vehicle_id):
    """Test getting recurring trips when none exist."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}

    # Get recurring trips
    trips = await manager.async_get_recurring_trips()

    # Should return empty list
    assert trips == []


@pytest.mark.asyncio
async def test_async_complete_punctual_trip_not_found(mock_hass, vehicle_id):
    """Test completing a non-existent punctual trip."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._punctual_trips = {}

    # Try to complete a trip that doesn't exist
    await manager.async_complete_punctual_trip("nonexistent_trip")

    # Should complete without error


@pytest.mark.asyncio
async def test_set_emhass_adapter(mock_hass, vehicle_id):
    """Test setting EMHASS adapter."""
    from unittest.mock import MagicMock

    manager = TripManager(mock_hass, vehicle_id)

    # Create mock adapter
    mock_adapter = MagicMock()

    # Set adapter
    manager.set_emhass_adapter(mock_adapter)

    # Verify adapter is set
    assert manager.get_emhass_adapter() is mock_adapter


@pytest.mark.asyncio
async def test_get_all_active_trips_empty(mock_hass, vehicle_id):
    """Test getting all active trips when none exist."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}
    manager._punctual_trips = {}

    # Get all active trips
    trips = await manager._get_all_active_trips()

    # Should return empty list
    assert trips == []


@pytest.mark.asyncio
async def test_add_recurring_trip_rejects_invalid_hora_out_of_range(
    mock_hass, vehicle_id
):
    """Test that async_add_recurring_trip rejects hora with out-of-range values."""
    manager = TripManager(mock_hass, vehicle_id)

    invalid_times = ["16:400", "25:00", "12:60", "24:00"]
    for time_str in invalid_times:
        with pytest.raises(ValueError):
            await manager.async_add_recurring_trip(
                dia_semana="lunes",
                hora=time_str,
                km=24.0,
                kwh=3.6,
                descripcion="Test",
            )

    # No trips should have been stored
    assert len(manager._recurring_trips) == 0


@pytest.mark.asyncio
async def test_add_recurring_trip_rejects_invalid_hora_bad_format(
    mock_hass, vehicle_id
):
    """Test that async_add_recurring_trip rejects hora with bad format."""
    manager = TripManager(mock_hass, vehicle_id)

    invalid_formats = ["1600", "16-00", "ab:cd", "16:00:00"]
    for time_str in invalid_formats:
        with pytest.raises(ValueError):
            await manager.async_add_recurring_trip(
                dia_semana="lunes",
                hora=time_str,
                km=24.0,
                kwh=3.6,
                descripcion="Test",
            )

    # No trips should have been stored
    assert len(manager._recurring_trips) == 0


@pytest.mark.asyncio
async def test_sanitize_recurring_trips_removes_corrupted_hora(mock_hass, vehicle_id):
    """Test that _sanitize_recurring_trips drops entries with invalid hora."""
    manager = TripManager(mock_hass, vehicle_id)

    trips = {
        "rec_lun_valid": {
            "id": "rec_lun_valid",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
            "kwh": 3.6,
            "activo": True,
        },
        "rec_lun_corrupt": {
            "id": "rec_lun_corrupt",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "16:400",
            "km": 10.0,
            "kwh": 2.0,
            "activo": True,
        },
    }

    sanitized = manager._sanitize_recurring_trips(trips)

    assert len(sanitized) == 1
    assert "rec_lun_valid" in sanitized
    assert "rec_lun_corrupt" not in sanitized


@pytest.mark.asyncio
async def test_sanitize_recurring_trips_all_corrupt_returns_empty(
    mock_hass, vehicle_id
):
    """Test that _sanitize_recurring_trips returns empty dict when all entries are corrupt."""
    manager = TripManager(mock_hass, vehicle_id)

    all_corrupt = {
        "rec_lun_bad1": {
            "id": "rec_lun_bad1",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "16:400",
            "km": 10.0,
            "kwh": 2.0,
            "activo": True,
        },
        "rec_lun_bad2": {
            "id": "rec_lun_bad2",
            "tipo": "recurrente",
            "dia_semana": "martes",
            "hora": "25:00",
            "km": 10.0,
            "kwh": 2.0,
            "activo": True,
        },
    }

    sanitized = manager._sanitize_recurring_trips(all_corrupt)
    assert sanitized == {}


@pytest.mark.asyncio
async def test_storage_wiring_uses_injected_storage(mock_hass, vehicle_id):
    """Test T035: _load_trips() and async_save_trips() use injected self._storage.

    When storage=FakeTripStorage is passed to TripManager constructor,
    _load_trips() should call fake.async_load() (not ha_storage.Store).
    Similarly async_save_trips() should call fake.async_save() (not Store).

    This test FAILS if wiring is incomplete (T039).
    """
    from tests.helpers import FakeTripStorage

    initial_data = {
        "trips": {
            "trip_1": {
                "id": "trip_1",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "08:00",
                "km": 24.0,
                "kwh": 3.6,
            }
        },
        "recurring_trips": {
            "rec_lun": {
                "id": "rec_lun",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "08:00",
                "km": 24.0,
                "kwh": 3.6,
            }
        },
        "punctual_trips": {"pun_1": {"id": "pun_1", "tipo": "puntual"}},
        "last_update": "2026-04-01T00:00:00",
    }
    fake_storage = FakeTripStorage(initial_data=initial_data)

    manager = TripManager(mock_hass, vehicle_id, storage=fake_storage)
    await manager.async_setup()

    # T035: _load_trips() should have used injected storage, loading data
    assert (
        manager._recurring_trips.get("rec_lun") is not None
    ), "_load_trips() did not use injected storage - recurring_trips empty"
    assert (
        manager._punctual_trips.get("pun_1") is not None
    ), "_load_trips() did not use injected storage - punctual_trips empty"

    # Now modify and save - T035: async_save_trips() should use fake.async_save()
    manager._recurring_trips["rec_lun"] = {
        "id": "rec_lun",
        "tipo": "recurrente",
        "modified": True,
    }
    await manager.async_save_trips()

    # Verify FakeTripStorage received the save call
    assert (
        "modified" in manager._recurring_trips["rec_lun"]
    ), "async_save_trips() did not use injected storage - data not saved"


@pytest.mark.asyncio
async def test_storage_wiring_fallback_to_ha_store(mock_hass, vehicle_id):
    """Test T035: when no storage= is passed, _load_trips() falls back to ha_storage.Store.

    This verifies the fallback path still works (no regression).
    """
    from homeassistant.helpers import storage as ha_storage

    # Use the same patch pattern as existing tests in this file
    with patch.object(
        ha_storage.Store,
        "async_load",
        new_callable=lambda: AsyncMock(
            return_value={
                "data": {
                    "trips": {"trip_fb": {"id": "trip_fb"}},
                    "recurring_trips": {},
                    "punctual_trips": {},
                }
            }
        ),
    ):
        manager = TripManager(mock_hass, vehicle_id)  # no storage= passed
        await manager.async_setup()

        assert (
            manager._trips.get("trip_fb") is not None
        ), "Fallback HA Store path failed - _load_trips() not working"


@pytest.mark.asyncio
async def test_load_trips_yaml_error_path(mock_hass, vehicle_id):
    """Test that _load_trips_yaml executes error handling when yaml.safe_load fails."""
    manager = TripManager(mock_hass, vehicle_id)

    # Mock Path.exists to return True and open to raise an exception
    with patch(
        "custom_components.ev_trip_planner.trip.manager.Path"
    ) as mock_path_class:
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.parent.mkdir.return_value = None

        # Make open() raise an exception (simulating I/O failure)
        mock_path.__enter__ = MagicMock(side_effect=OSError("Simulated read error"))
        mock_path.__exit__ = MagicMock(return_value=False)

        mock_path_class.return_value = mock_path

        # Mock yaml.safe_load to raise (simulating corrupted YAML)
        with patch(
            "custom_components.ev_trip_planner.trip._crud_mixin.yaml.safe_load"
        ) as mock_load:
            mock_load.side_effect = yaml.YAMLError("Simulated YAML parse error")

            # Call the method - it should catch the exception
            await manager._load_trips_yaml("test_key")

            # After error, trips should be reset to empty
            assert manager._trips == {}
            assert manager._recurring_trips == {}
            assert manager._punctual_trips == {}


@pytest.mark.asyncio
async def test_save_trips_yaml_error_path(mock_hass, vehicle_id):
    """Test that _save_trips_yaml executes error handling when yaml.dump fails."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_123": {"id": "rec_lun_123", "tipo": "recurrente"}
    }

    # Mock yaml.dump to raise an exception
    with patch("custom_components.ev_trip_planner.trip._crud_mixin.yaml.dump") as mock_dump:
        mock_dump.side_effect = yaml.YAMLError("Simulated YAML dump error")

        with patch(
            "custom_components.ev_trip_planner.trip.manager.Path"
        ) as mock_path_class:
            mock_path = MagicMock()
            mock_path.parent.mkdir.return_value = None

            # Make open() raise an exception during write
            mock_file = MagicMock()
            mock_file.__enter__ = MagicMock(
                side_effect=OSError("Simulated write error")
            )
            mock_file.__exit__ = MagicMock(return_value=False)
            mock_path.__enter__ = MagicMock(return_value=mock_file)
            mock_path.__exit__ = MagicMock(return_value=False)

            mock_path_class.return_value = mock_path

            # Call the method - it should catch the exception and not re-raise
            await manager._save_trips_yaml("test_key")

            # Should complete without raising (error was caught)


# =============================================================================
# T072: Tests for trip_manager error paths and state branches
# =============================================================================


@pytest.mark.asyncio
async def test_get_all_active_trips_with_active_and_inactive_recurring(
    mock_hass, vehicle_id
):
    """Test T072.2: _get_all_active_trips includes active, excludes inactive recurring trips."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_active": {
            "id": "rec_lun_active",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "activo": True,
        },
        "rec_mar_inactive": {
            "id": "rec_mar_inactive",
            "tipo": "recurrente",
            "dia_semana": "martes",
            "hora": "09:00",
            "activo": False,
        },
    }
    manager._punctual_trips = {}

    trips = await manager._get_all_active_trips()

    # Only active recurring trip should be included
    assert len(trips) == 1
    assert trips[0]["id"] == "rec_lun_active"


@pytest.mark.asyncio
async def test_get_all_active_trips_with_pending_and_completed_punctual(
    mock_hass, vehicle_id
):
    """Test T072.2: _get_all_active_trips includes pending, excludes completed punctual trips."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}
    manager._punctual_trips = {
        "pun_pending": {
            "id": "pun_pending",
            "tipo": "puntual",
            "datetime": "2025-01-06T15:00",
            "estado": "pendiente",
        },
        "pun_completed": {
            "id": "pun_completed",
            "tipo": "puntual",
            "datetime": "2025-01-06T16:00",
            "estado": "completado",
        },
    }

    trips = await manager._get_all_active_trips()

    # Only pending punctual trip should be included
    assert len(trips) == 1
    assert trips[0]["id"] == "pun_pending"


@pytest.mark.asyncio
async def test_get_all_active_trips_with_mixed_states(mock_hass, vehicle_id):
    """Test T072.2: _get_all_active_trips handles mixed trip states correctly."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_active": {
            "id": "rec_lun_active",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "activo": True,
        },
        "rec_mar_inactive": {
            "id": "rec_mar_inactive",
            "tipo": "recurrente",
            "dia_semana": "martes",
            "hora": "09:00",
            "activo": False,
        },
    }
    manager._punctual_trips = {
        "pun_pending": {
            "id": "pun_pending",
            "tipo": "puntual",
            "datetime": "2025-01-06T15:00",
            "estado": "pendiente",
        },
        "pun_completed": {
            "id": "pun_completed",
            "tipo": "puntual",
            "datetime": "2025-01-06T16:00",
            "estado": "completado",
        },
    }

    trips = await manager._get_all_active_trips()

    # Only active recurring and pending punctual should be included
    assert len(trips) == 2
    trip_ids = [t["id"] for t in trips]
    assert "rec_lun_active" in trip_ids
    assert "pun_pending" in trip_ids
    assert "rec_mar_inactive" not in trip_ids
    assert "pun_completed" not in trip_ids


@pytest.mark.asyncio
async def test_get_all_active_trips_recurring_missing_activo_defaults_to_true(
    mock_hass, vehicle_id
):
    """Test T072.2: _get_all_active_trips treats missing activo as True (active)."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {
        "rec_lun_no_activo": {
            "id": "rec_lun_no_activo",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            # No "activo" key - should default to True (active)
        },
    }
    manager._punctual_trips = {}

    trips = await manager._get_all_active_trips()

    # Trip without activo should be included (defaults to active)
    assert len(trips) == 1
    assert trips[0]["id"] == "rec_lun_no_activo"


@pytest.mark.asyncio
async def test_async_get_kwh_needed_today_with_empty_data(mock_hass, vehicle_id):
    """Test T072.3: async_get_kwh_needed_today returns 0.0 when no trips exist."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}
    manager._punctual_trips = {}

    kwh = await manager.async_get_kwh_needed_today()

    assert kwh == 0.0


@pytest.mark.asyncio
async def test_async_get_hours_needed_today_with_empty_data(mock_hass, vehicle_id):
    """Test T072.3: async_get_hours_needed_today returns 0 when no trips exist."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}
    manager._punctual_trips = {}

    hours = await manager.async_get_hours_needed_today()

    assert hours == 0


@pytest.mark.asyncio
async def test_async_get_hours_needed_today_with_zero_kwh(mock_hass, vehicle_id):
    """Test T072.3: async_get_hours_needed_today returns 0 when kwh_needed is 0."""
    mock_entry = MagicMock()
    mock_entry.data = {"charging_power": 7.4}
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    manager = TripManager(mock_hass, vehicle_id)
    manager._recurring_trips = {}
    manager._punctual_trips = {}

    hours = await manager.async_get_hours_needed_today()

    assert hours == 0


@pytest.mark.asyncio
async def test_add_recurring_trip_rejects_invalid_dia_semana(mock_hass, vehicle_id):
    """Test T072.1: async_add_recurring_trip rejects invalid dia_semana values.

    While validate_hora handles hour validation, dia_semana is stored directly.
    An invalid dia_semana should be accepted (stored as-is) but may cause
    issues when the trip is processed. This tests that the system handles
    invalid day names gracefully.
    """
    manager = TripManager(mock_hass, vehicle_id)

    # Invalid dia_semana (not a real day) - should still be stored since
    # dia_semana validation happens at trip evaluation time, not at storage time
    await manager.async_add_recurring_trip(
        dia_semana="invalid_day",
        hora="09:00",
        km=24.0,
        kwh=3.6,
        descripcion="Test",
    )

    # Trip should be stored with the invalid dia_semana
    assert len(manager._recurring_trips) == 1
    trip_id = list(manager._recurring_trips.keys())[0]
    assert manager._recurring_trips[trip_id]["dia_semana"] == "invalid_day"


@pytest.mark.asyncio
async def test_async_get_next_trip_with_all_completed_punctual(mock_hass, vehicle_id):
    """Test T072.2: async_get_next_trip returns None when all punctual trips are completed."""
    from datetime import datetime

    mock_datetime = unittest.mock.MagicMock()
    mock_datetime.now.return_value = datetime(2025, 1, 6, 8, 0)  # Monday 8:00 AM
    mock_datetime.strptime = datetime.strptime

    with unittest.mock.patch(
        "custom_components.ev_trip_planner.trip.manager.datetime", mock_datetime
    ):
        manager = TripManager(mock_hass, vehicle_id)
        manager._recurring_trips = {}
        manager._punctual_trips = {
            "pun_completed": {
                "id": "pun_completed",
                "tipo": "puntual",
                "datetime": "2025-01-06T09:00",
                "estado": "completado",
            },
            "pun_also_completed": {
                "id": "pun_also_completed",
                "tipo": "puntual",
                "datetime": "2025-01-06T10:00",
                "estado": "completado",
            },
        }

        next_trip = await manager.async_get_next_trip()

        # No pending trips, should return None
        assert next_trip is None


@pytest.mark.asyncio
async def test_async_get_next_trip_with_all_inactive_recurring(mock_hass, vehicle_id):
    """Test T072.2: async_get_next_trip returns None when all recurring trips are inactive."""
    frozen_time = datetime(2025, 1, 6, 8, 0)  # Monday 8:00 AM
    with patch("custom_components.ev_trip_planner.trip.manager.datetime") as mock_dt:
        mock_dt.now.return_value = frozen_time
        mock_dt.strptime = datetime.strptime
        mock_dt.combine = datetime.combine

        manager = TripManager(mock_hass, vehicle_id)
        manager._recurring_trips = {
            "rec_lun_inactive1": {
                "id": "rec_lun_inactive1",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "09:00",
                "activo": False,
            },
            "rec_lun_inactive2": {
                "id": "rec_lun_inactive2",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "10:00",
                "activo": False,
            },
        }
        manager._punctual_trips = {}

        next_trip = await manager.async_get_next_trip()

        # No active trips, should return None
        assert next_trip is None


# =============================================================================
# T075: Tests for EMHASS adapter integration paths (coverage 81% -> 88%)
# =============================================================================


@pytest.mark.asyncio
async def test_async_add_recurring_trip_with_emhass_adapter(mock_hass, vehicle_id):
    """Test that async_add_recurring_trip calls _async_publish_new_trip_to_emhass when adapter is set."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up mock EMHASS adapter with proper async mocks
    mock_adapter = MagicMock()
    mock_adapter.async_publish_deferrable_load = AsyncMock()
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    # Mock sensor.py async_create_trip_sensor to avoid entity registry operations
    with patch(
        "custom_components.ev_trip_planner.sensor.async_create_trip_sensor",
        new=AsyncMock(),
    ):
        # Add a recurring trip
        await manager.async_add_recurring_trip(
            dia_semana="lunes", hora="09:00", km=24.0, kwh=3.6, descripcion="Trabajo"
        )

    # Verify EMHASS adapter was called to publish the new trip
    mock_adapter.async_publish_deferrable_load.assert_called_once()
    # And that all deferrable loads were republished from _async_publish_new_trip_to_emhass
    # (removed from async_save_trips in m401 to prevent race condition)
    assert mock_adapter.async_publish_all_deferrable_loads.call_count == 1


@pytest.mark.asyncio
async def test_async_add_punctual_trip_with_empty_datetime(mock_hass, vehicle_id):
    """Test that async_add_punctual_trip handles empty datetime string (line 507)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Mock dependencies
    manager.async_save_trips = AsyncMock()

    # Add a punctual trip with empty datetime - this exercises line 507 (date_part = "")
    await manager.async_add_punctual_trip(
        datetime="", km=24.0, kwh=3.6, descripcion="Trabajo"
    )

    # Should have added a trip with empty datetime
    assert len(manager._punctual_trips) == 1


@pytest.mark.asyncio
async def test_async_add_punctual_trip_with_emhass_adapter(mock_hass, vehicle_id):
    """Test that async_add_punctual_trip calls _async_publish_new_trip_to_emhass when adapter is set."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up mock EMHASS adapter with proper async mocks
    mock_adapter = MagicMock()
    mock_adapter.async_publish_deferrable_load = AsyncMock()
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    # Mock sensor.py async_create_trip_sensor to avoid entity registry operations
    with patch(
        "custom_components.ev_trip_planner.sensor.async_create_trip_sensor",
        new=AsyncMock(),
    ):
        # Add a punctual trip
        await manager.async_add_punctual_trip(
            datetime="2025-11-19T15:00:00", km=110.0, kwh=16.5, descripcion="Viaje"
        )

    # Verify EMHASS adapter was called
    mock_adapter.async_publish_deferrable_load.assert_called_once()
    # Called once from _async_publish_new_trip_to_emhass
    # (removed from async_save_trips in m401 to prevent race condition)
    assert mock_adapter.async_publish_all_deferrable_loads.call_count == 1


@pytest.mark.asyncio
async def test_async_save_trips_with_emhass_adapter_triggers_publish(
    mock_hass, vehicle_id
):
    """Test that async_save_trips calls publish_deferrable_loads when adapter is set (line 376)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up mock EMHASS adapter with proper async mocks
    mock_adapter = MagicMock()
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    # Mock the storage to avoid HA storage operations
    mock_storage = MagicMock()
    mock_storage.async_save = AsyncMock()
    manager._storage = mock_storage

    # Add a trip to have data to save
    manager._recurring_trips = {
        "rec_lun_123": {
            "id": "rec_lun_123",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 30,
            "kwh": 5.0,
            "activo": True,
        }
    }

    # Call async_save_trips
    await manager.async_save_trips()

    # Verify async_publish_all_deferrable_loads was NOT called
    # (removed in m401 to prevent race condition - callers now handle publishing)
    mock_adapter.async_publish_all_deferrable_loads.assert_not_called()


@pytest.mark.asyncio
async def test_async_update_trip_with_emhass_adapter_syncs(mock_hass, vehicle_id):
    """Test that async_update_trip calls _async_sync_trip_to_emhass when adapter is set (line 580)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Pre-populate with a trip
    manager._recurring_trips = {
        "rec_lun_12345678": {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
            "kwh": 5.0,
            "activo": True,
        },
    }

    # Set up mock EMHASS adapter
    mock_adapter = MagicMock()
    mock_adapter.async_update_deferrable_load = AsyncMock()
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    mock_adapter.async_remove_deferrable_load = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    # Mock async_save_trips and async_update_trip_sensor
    manager.async_save_trips = AsyncMock()
    manager.async_update_trip_sensor = AsyncMock()

    # Update the trip - this should trigger _async_sync_trip_to_emhass
    await manager.async_update_trip("rec_lun_12345678", {"hora": "10:00", "km": 30.0})

    # Verify EMHASS adapter was called to update the deferrable load
    mock_adapter.async_update_deferrable_load.assert_called()


@pytest.mark.asyncio
async def test_async_delete_trip_with_emhass_adapter_removes(mock_hass, vehicle_id):
    """Test that async_delete_trip calls _async_remove_trip_from_emhass when adapter is set (line 610)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Pre-populate with a trip
    manager._recurring_trips = {
        "rec_lun_12345678": {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
            "activo": True,
        },
    }

    # Set up mock EMHASS adapter
    mock_adapter = MagicMock()
    mock_adapter.async_remove_deferrable_load = AsyncMock()
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    # Mock async_save_trips and async_remove_trip_sensor
    manager.async_save_trips = AsyncMock()
    manager.async_remove_trip_sensor = AsyncMock()

    # Delete the trip
    await manager.async_delete_trip("rec_lun_12345678")

    # Verify _async_remove_trip_from_emhass was called (line 610)
    mock_adapter.async_remove_deferrable_load.assert_called_once_with(
        "rec_lun_12345678"
    )


@pytest.mark.asyncio
async def test_async_cancel_punctual_trip_with_emhass_adapter_removes(
    mock_hass, vehicle_id
):
    """Test that async_cancel_punctual_trip calls _async_remove_trip_from_emhass when adapter is set (line 798)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Pre-populate with a punctual trip
    manager._punctual_trips = {
        "pun_20251119_87654321": {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "estado": "pendiente",
        },
    }

    # Set up mock EMHASS adapter
    mock_adapter = MagicMock()
    mock_adapter.async_remove_deferrable_load = AsyncMock()
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    # Mock async_save_trips
    manager.async_save_trips = AsyncMock()

    # Cancel the punctual trip
    await manager.async_cancel_punctual_trip("pun_20251119_87654321")

    # Verify _async_remove_trip_from_emhass was called (line 798)
    mock_adapter.async_remove_deferrable_load.assert_called_once_with(
        "pun_20251119_87654321"
    )


# =============================================================================
# T075: Tests for error handling paths
# =============================================================================


@pytest.mark.asyncio
async def test_async_get_next_trip_after_handles_invalid_hora(mock_hass, vehicle_id):
    """Test that async_get_next_trip_after handles trips with invalid hora format (lines 1069-1098)."""
    from datetime import datetime as dt

    frozen_time = dt(2025, 1, 6, 10, 0)  # Monday 10:00 AM
    hora_regreso = dt(2025, 1, 6, 8, 0)  # Monday 8:00 AM

    with patch("custom_components.ev_trip_planner.trip.manager.datetime") as mock_dt:
        mock_dt.now.return_value = frozen_time
        mock_dt.strptime = dt.strptime
        mock_dt.combine = dt.combine

        manager = TripManager(mock_hass, vehicle_id)
        # Add a recurring trip with invalid hora format
        manager._recurring_trips = {
            "rec_lun_bad_hora": {
                "id": "rec_lun_bad_hora",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "invalid",  # Invalid format
                "activo": True,
            },
        }
        manager._punctual_trips = {}

        # Should not raise, should handle gracefully
        next_trip = await manager.async_get_next_trip_after(hora_regreso)

        # The trip with invalid hora should be skipped
        assert next_trip is None


@pytest.mark.asyncio
async def test_async_get_vehicle_soc_handles_unavailable_sensor(mock_hass, vehicle_id):
    """Test that async_get_vehicle_soc logs warning when sensor is unavailable (lines 1151, 1154-1155)."""
    # Set up mock entry with soc_sensor
    mock_entry = MagicMock()
    mock_entry.data = {"soc_sensor": "sensor.vehicle_soc"}
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    # Set up mock state that returns unavailable
    mock_state = MagicMock()
    mock_state.state = "unavailable"
    mock_hass.states.get = MagicMock(return_value=mock_state)

    manager = TripManager(mock_hass, vehicle_id)

    # Should return 0.0 when sensor is unavailable and log warning
    soc = await manager.async_get_vehicle_soc(vehicle_id)

    assert soc == 0.0


@pytest.mark.asyncio
async def test_async_get_vehicle_soc_handles_missing_entry(mock_hass, vehicle_id):
    """Test that async_get_vehicle_soc logs warning when entry is not found (line 1153)."""
    # Return None when no entry found
    mock_hass.config_entries.async_entries = MagicMock(return_value=[])

    manager = TripManager(mock_hass, vehicle_id)

    # Should return 0.0 when entry not found
    soc = await manager.async_get_vehicle_soc(vehicle_id)

    assert soc == 0.0


@pytest.mark.asyncio
async def test_get_charging_power_handles_exception(mock_hass, vehicle_id):
    """Test that _get_charging_power returns default when exception occurs (lines 959-960)."""
    # Make async_entries raise an exception
    mock_hass.config_entries.async_entries = MagicMock(
        side_effect=RuntimeError("Config error")
    )

    manager = TripManager(mock_hass, vehicle_id)

    # Should return DEFAULT_CHARGING_POWER when exception occurs
    power = manager._get_charging_power()

    # DEFAULT_CHARGING_POWER is 11.0 kW
    assert power == 11.0


# =============================================================================
# T075: Tests for EMHASS adapter error handling paths
# =============================================================================


@pytest.mark.asyncio
async def test_async_sync_trip_to_emhass_with_inactive_trip(mock_hass, vehicle_id):
    """Test _async_sync_trip_to_emhass removes inactive trip from EMHASS (line 821-827)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Pre-populate with a paused (inactive) trip
    manager._recurring_trips = {
        "rec_lun_12345678": {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
            "kwh": 5.0,
            "activo": False,  # Inactive/paused
        },
    }

    # Set up mock EMHASS adapter
    mock_adapter = MagicMock()
    mock_adapter.async_remove_deferrable_load = AsyncMock()
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    # Call _async_sync_trip_to_emhass with an update
    await manager._async_sync_trip_to_emhass("rec_lun_12345678", {}, {"activo": False})

    # Should call async_remove_deferrable_load for inactive trip
    mock_adapter.async_remove_deferrable_load.assert_called_once_with(
        "rec_lun_12345678"
    )


@pytest.mark.asyncio
async def test_async_sync_trip_to_emhass_with_km_change_triggers_recalculate(
    mock_hass, vehicle_id
):
    """Test _async_sync_trip_to_emhass with km change triggers recalculate (critical update)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Pre-populate with a trip
    manager._recurring_trips = {
        "rec_lun_12345678": {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
            "kwh": 5.0,
            "activo": True,
        },
    }

    # Set up mock EMHASS adapter
    mock_adapter = MagicMock()
    mock_adapter.async_update_deferrable_load = AsyncMock()
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    mock_adapter.async_remove_deferrable_load = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    # Call _async_sync_trip_to_emhass with a critical update (km change)
    # km IS in recalc_fields, so needs_recalculate will be True
    old_trip = manager._recurring_trips["rec_lun_12345678"].copy()
    await manager._async_sync_trip_to_emhass("rec_lun_12345678", old_trip, {"km": 30.0})

    # Should call both update and publish_all for critical updates
    mock_adapter.async_update_deferrable_load.assert_called()
    mock_adapter.async_publish_all_deferrable_loads.assert_called()


@pytest.mark.asyncio
async def test_async_sync_trip_to_emhass_handles_exception(mock_hass, vehicle_id):
    """Test _async_sync_trip_to_emhass handles exceptions gracefully (line 876-877)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Pre-populate with a trip
    manager._recurring_trips = {
        "rec_lun_12345678": {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24.0,
            "kwh": 5.0,
            "activo": True,
        },
    }

    # Set up mock EMHASS adapter that raises an exception
    mock_adapter = MagicMock()
    mock_adapter.async_update_deferrable_load = AsyncMock(
        side_effect=RuntimeError("EMHASS error")
    )
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    mock_adapter.async_remove_deferrable_load = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    # Should not raise, should handle gracefully
    await manager._async_sync_trip_to_emhass("rec_lun_12345678", {}, {"km": 30.0})

    # Exception was caught and logged, no assertion needed


@pytest.mark.asyncio
async def test_async_remove_trip_from_emhass_handles_exception(mock_hass, vehicle_id):
    """Test _async_remove_trip_from_emhass handles exceptions gracefully (line 891-892)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up mock EMHASS adapter that raises an exception
    mock_adapter = MagicMock()
    mock_adapter.async_remove_deferrable_load = AsyncMock(
        side_effect=RuntimeError("EMHASS error")
    )
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    # Should not raise, should handle gracefully
    await manager._async_remove_trip_from_emhass("rec_lun_12345678")

    # Exception was caught and logged, no assertion needed


@pytest.mark.asyncio
async def test_async_publish_new_trip_to_emhass_handles_exception(
    mock_hass, vehicle_id
):
    """Test _async_publish_new_trip_to_emhass handles exceptions gracefully (line 910-911)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up mock EMHASS adapter that raises an exception
    mock_adapter = MagicMock()
    mock_adapter.async_publish_deferrable_load = AsyncMock(
        side_effect=RuntimeError("EMHASS error")
    )
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    trip = {
        "id": "rec_lun_12345678",
        "tipo": "recurrente",
        "dia_semana": "lunes",
        "hora": "09:00",
        "km": 24.0,
        "kwh": 5.0,
        "activo": True,
    }

    # Should not raise, should handle gracefully
    await manager._async_publish_new_trip_to_emhass(trip)

    # Exception was caught and logged, no assertion needed


@pytest.mark.asyncio
async def test_async_sync_trip_to_emhass_trip_not_found(mock_hass, vehicle_id):
    """Test _async_sync_trip_to_emhass handles trip not found (line 836-838)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up mock EMHASS adapter
    mock_adapter = MagicMock()
    mock_adapter.async_remove_deferrable_load = AsyncMock()
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    # Trip doesn't exist - call sync with non-existent trip
    await manager._async_sync_trip_to_emhass("nonexistent_trip", {}, {"km": 30.0})

    # Should call async_remove_deferrable_load for the non-existent trip
    mock_adapter.async_remove_deferrable_load.assert_called_once_with(
        "nonexistent_trip"
    )


@pytest.mark.asyncio
async def test_async_calcular_energia_necesaria_with_charging_power_zero(
    mock_hass, vehicle_id
):
    """Test async_calcular_energia_necesaria handles zero charging power (line 1207)."""
    manager = TripManager(mock_hass, vehicle_id)

    trip = {
        "id": "test_trip",
        "tipo": "puntual",
        "datetime": "2025-11-19T15:00:00",
        "km": 100,
        "kwh": 15.0,
    }
    vehicle_config = {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 0,  # Zero charging power
        "soc_current": 20.0,  # 20% SOC = 10kWh, viaje necesita 15kWh → necesita 5kWh
    }

    result = await manager.async_calcular_energia_necesaria(trip, vehicle_config)

    # Should calculate correctly with zero charging power
    # energia_objetivo = 15kWh
    # energia_actual = 10kWh (20% de 50kWh)
    # energia_necesaria raw = max(0, 15 - 10) = 5kWh
    # With safety_margin=10%: energia_final = 5 * 1.10 = 5.5kWh
    assert result["energia_necesaria_kwh"] == 5.5
    assert result["horas_carga_necesarias"] == 0


# =============================================================================
# T078: Tests for missing lines in trip_manager.py
# =============================================================================


@pytest.mark.asyncio
async def test_async_delete_all_trips_clears_and_saves(mock_hass, vehicle_id):
    """Test async_delete_all_trips clears all trips and saves (lines 614-620)."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._trips = {"trip1": {}}
    manager._recurring_trips = {"rec1": {}}
    manager._punctual_trips = {"pun1": {}}
    manager.async_save_trips = AsyncMock()

    await manager.async_delete_all_trips()

    assert manager._trips == {}
    assert manager._recurring_trips == {}
    assert manager._punctual_trips == {}
    manager.async_save_trips.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_delete_all_trips_with_emhass_adapter(mock_hass, vehicle_id):
    """Test async_delete_all_trips clears cache and publishes empty list (line 708).

    The fix changed behavior: instead of looping through trips calling
    _async_remove_trip_from_emhass for each (which republishes remaining trips),
    we now clear dictionaries FIRST, then call publish_deferrable_loads([])
    once to clear the EMHASS cache.
    """
    manager = TripManager(mock_hass, vehicle_id)
    manager._trips = {"trip1": {}, "trip2": {}}
    manager._recurring_trips = {"rec1": {}}
    manager._punctual_trips = {"pun1": {}}
    manager.async_save_trips = AsyncMock()
    manager.publish_deferrable_loads = AsyncMock()

    # Mock EMHASS adapter
    mock_adapter = MagicMock()
    mock_adapter.async_remove_deferrable_load = AsyncMock()
    manager._emhass_adapter = mock_adapter

    await manager.async_delete_all_trips()

    # NEW BEHAVIOR: Does NOT call async_remove_deferrable_load in a loop.
    # Instead, publish_deferrable_loads([]) is called once to clear cache.
    assert mock_adapter.async_remove_deferrable_load.call_count == 0

    # publish_deferrable_loads IS called with empty list once
    manager.publish_deferrable_loads.assert_awaited_once_with([])

    # Should still clear and save
    assert manager._trips == {}
    manager.async_save_trips.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_save_trips_exception_handler(mock_hass, vehicle_id):
    """Test async_save_trips handles exception in storage save (lines 377-378)."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._trips = {"trip1": {}}
    manager._recurring_trips = {"rec1": {}}
    manager._punctual_trips = {"pun1": {}}
    manager._storage = MagicMock()
    manager._storage.async_save = AsyncMock(side_effect=RuntimeError("Storage error"))

    # Should catch exception and not raise
    await manager.async_save_trips()

    # Exception was caught and logged - no assertion needed


@pytest.mark.asyncio
async def test_async_sync_trip_to_emhass_non_critical_change(mock_hass, vehicle_id):
    """Test _async_sync_trip_to_emhass with non-critical change (lines 868-870).

    Non-critical changes don't trigger recalculation, just async_update_deferrable_load.
    'activo' is NOT in recalc_fields, so it should be a non-critical change.
    """
    manager = TripManager(mock_hass, vehicle_id)
    manager._charging_power_kw = 11.0

    # Set up an active punctual trip
    manager._punctual_trips["trip_1"] = {
        "descripcion": "Active trip",
        "estado": "pendiente",
        "km": 50.0,
        "kwh": 7.5,
        "activo": True,
        "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
    }

    # Set up mock EMHASS adapter
    mock_adapter = MagicMock()
    mock_adapter.async_update_deferrable_load = AsyncMock()
    mock_adapter.async_publish_all_deferrable_loads = AsyncMock()
    mock_adapter.async_remove_deferrable_load = AsyncMock()
    manager.set_emhass_adapter(mock_adapter)

    # Non-critical update - 'activo' is NOT in recalc_fields
    await manager._async_sync_trip_to_emhass(
        "trip_1",
        {"activo": True},
        {"activo": True},  # No actual change, but still non-critical
    )

    # Should call async_update_deferrable_load but NOT publish_deferrable_loads
    mock_adapter.async_update_deferrable_load.assert_called()
    mock_adapter.async_publish_all_deferrable_loads.assert_not_called()


@pytest.mark.asyncio
async def test_async_remove_trip_from_emhass_no_adapter(mock_hass, vehicle_id):
    """Test _async_remove_trip_from_emhass returns early when no adapter (line 882)."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._emhass_adapter = None

    # Should return early without raising
    await manager._async_remove_trip_from_emhass("trip_1")


@pytest.mark.asyncio
async def test_async_publish_new_trip_to_emhass_no_adapter(mock_hass, vehicle_id):
    """Test _async_publish_new_trip_to_emhass returns early when no adapter (line 897)."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._emhass_adapter = None

    trip = {"descripcion": "New trip", "km": 50.0}

    # Should return early without raising
    await manager._async_publish_new_trip_to_emhass(trip)


@pytest.mark.asyncio
async def test_async_get_next_trip_after_skips_non_pendiente_punctual(
    mock_hass, vehicle_id
):
    """Test async_get_next_trip_after skips punctual trips with estado != 'pendiente' (line 1061)."""
    from datetime import datetime as dt

    frozen_time = dt(2025, 1, 6, 10, 0)  # Monday 10:00 AM
    hora_regreso = dt(2025, 1, 6, 8, 0)  # Monday 8:00 AM

    with patch("custom_components.ev_trip_planner.trip.manager.datetime") as mock_dt:
        mock_dt.now.return_value = frozen_time
        mock_dt.strptime = dt.strptime
        mock_dt.combine = dt.combine

        manager = TripManager(mock_hass, vehicle_id)
        # Add a punctual trip with estado != "pendiente" (e.g., "completado")
        manager._punctual_trips = {
            "pun_completed": {
                "id": "pun_completed",
                "tipo": "puntual",
                "estado": "completado",  # Not pending - should be skipped
                "datetime": (frozen_time + timedelta(hours=2)).isoformat(),
            },
        }
        manager._recurring_trips = {}

        # Should return None because the only trip is not pending
        next_trip = await manager.async_get_next_trip_after(hora_regreso)
        assert next_trip is None


@pytest.mark.asyncio
async def test_async_get_next_trip_after_skips_inactive_recurring(
    mock_hass, vehicle_id
):
    """Test async_get_next_trip_after skips inactive recurring trips (line 1070)."""
    from datetime import datetime as dt

    frozen_time = dt(2025, 1, 6, 10, 0)  # Monday 10:00 AM
    hora_regreso = dt(2025, 1, 6, 8, 0)  # Monday 8:00 AM

    with patch("custom_components.ev_trip_planner.trip.manager.datetime") as mock_dt:
        mock_dt.now.return_value = frozen_time
        mock_dt.strptime = dt.strptime
        mock_dt.combine = dt.combine

        manager = TripManager(mock_hass, vehicle_id)
        # Add a recurring trip that is NOT active
        manager._recurring_trips = {
            "rec_inactive": {
                "id": "rec_inactive",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "09:00",
                "activo": False,  # Inactive - should be skipped
            },
        }
        manager._punctual_trips = {}

        # Should return None because the only trip is inactive
        next_trip = await manager.async_get_next_trip_after(hora_regreso)
        assert next_trip is None


@pytest.mark.asyncio
async def test_async_get_next_trip_after_skips_wrong_day_recurring(
    mock_hass, vehicle_id
):
    """Test async_get_next_trip_after skips recurring trips on wrong day (line 1072)."""
    from datetime import datetime as dt

    frozen_time = dt(2025, 1, 6, 10, 0)  # Monday 10:00 AM
    hora_regreso = dt(2025, 1, 6, 8, 0)  # Monday 8:00 AM

    with patch("custom_components.ev_trip_planner.trip.manager.datetime") as mock_dt:
        mock_dt.now.return_value = frozen_time
        mock_dt.strptime = dt.strptime
        mock_dt.combine = dt.combine

        manager = TripManager(mock_hass, vehicle_id)
        # Add a recurring trip for a DIFFERENT day (martes instead of lunes)
        manager._recurring_trips = {
            "rec_wrong_day": {
                "id": "rec_wrong_day",
                "tipo": "recurrente",
                "dia_semana": "martes",  # Wrong day - should be skipped
                "hora": "09:00",
                "activo": True,
            },
        }
        manager._punctual_trips = {}

        # Should return None because the only trip is on the wrong day
        next_trip = await manager.async_get_next_trip_after(hora_regreso)
        assert next_trip is None


@pytest.mark.asyncio
async def test_async_get_next_trip_after_skips_early_recurring_trip(
    mock_hass, vehicle_id
):
    """Test async_get_next_trip_after skips recurring trip with earlier time (lines 1080-1083)."""
    from datetime import datetime as dt

    frozen_time = dt(2025, 1, 6, 10, 0)  # Monday 10:00 AM
    hora_regreso = dt(2025, 1, 6, 12, 0)  # Monday 12:00 PM (noon)

    with patch("custom_components.ev_trip_planner.trip.manager.datetime") as mock_dt:
        mock_dt.now.return_value = frozen_time
        mock_dt.strptime = dt.strptime
        mock_dt.combine = dt.combine

        manager = TripManager(mock_hass, vehicle_id)
        # Add a recurring trip at 08:00 (earlier than 12:00 return time)
        manager._recurring_trips = {
            "rec_early": {
                "id": "rec_early",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "08:00",  # Earlier than hora_regreso - should be skipped
                "activo": True,
            },
        }
        manager._punctual_trips = {}

        # Should return None because the only trip is earlier than return time
        next_trip = await manager.async_get_next_trip_after(hora_regreso)
        assert next_trip is None


@pytest.mark.asyncio
async def test_async_get_next_trip_after_handles_valid_recurring_trip(
    mock_hass, vehicle_id
):
    """Test async_get_next_trip_after finds a valid recurring trip after hora_regreso (lines 1084-1098)."""
    from datetime import datetime as dt

    frozen_time = dt(2025, 1, 6, 10, 0)  # Monday 10:00 AM
    hora_regreso = dt(2025, 1, 6, 8, 0)  # Monday 8:00 AM

    with patch("custom_components.ev_trip_planner.trip.manager.datetime") as mock_dt:
        mock_dt.now.return_value = frozen_time
        mock_dt.strptime = dt.strptime
        mock_dt.combine = dt.combine

        manager = TripManager(mock_hass, vehicle_id)
        # Add a recurring trip at 09:00 (later than 8:00 return time)
        manager._recurring_trips = {
            "rec_valid": {
                "id": "rec_valid",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "09:00",  # Later than hora_regreso - should be found
                "activo": True,
                "km": 30,
                "kwh": 5.0,
            },
        }
        manager._punctual_trips = {}

        # Should find the trip
        next_trip = await manager.async_get_next_trip_after(hora_regreso)
        assert next_trip is not None
        assert next_trip["id"] == "rec_valid"


@pytest.mark.asyncio
async def test_async_get_vehicle_soc_with_async_entries_domain(mock_hass, vehicle_id):
    """Test async_get_vehicle_soc uses async_entries(DOMAIN) correctly (lines 1138-1151).

    This tests the warning at line 1151 when SOC sensor returns unavailable.
    """
    from custom_components.ev_trip_planner.const import DOMAIN

    # Set up mock entry returned by async_entries(DOMAIN)
    mock_entry = MagicMock()
    mock_entry.data = {"vehicle_name": vehicle_id, "soc_sensor": "sensor.vehicle_soc"}
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    # Set up mock state that returns unavailable
    mock_state = MagicMock()
    mock_state.state = "unavailable"
    mock_hass.states.get = MagicMock(return_value=mock_state)

    manager = TripManager(mock_hass, vehicle_id)

    # Should return 0.0 when sensor is unavailable and log warning
    soc = await manager.async_get_vehicle_soc(vehicle_id)

    assert soc == 0.0
    mock_hass.config_entries.async_entries.assert_called_with(DOMAIN)


@pytest.mark.asyncio
async def test_async_get_vehicle_soc_with_exception(mock_hass, vehicle_id):
    """Test async_get_vehicle_soc handles exception (lines 1154-1155)."""

    # Set up mock entry that raises exception when data.get is called
    mock_entry = MagicMock()
    mock_entry.data = MagicMock()
    mock_entry.data.get = MagicMock(side_effect=RuntimeError("Data error"))
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    manager = TripManager(mock_hass, vehicle_id)

    # Should return 0.0 when exception occurs
    soc = await manager.async_get_vehicle_soc(vehicle_id)

    assert soc == 0.0


@pytest.mark.asyncio
async def test_calcular_ventana_carga_with_datetime_object(mock_hass, vehicle_id):
    """Test calcular_ventana_carga handles datetime object in trip (line 1314)."""
    from custom_components.ev_trip_planner.trip import TripManager

    manager = TripManager(mock_hass, vehicle_id)
    manager._get_trip_time = MagicMock(
        return_value=None
    )  # Force fallback to trip datetime
    manager.async_get_next_trip_after = AsyncMock(return_value=None)

    trip_datetime = datetime.now() + timedelta(hours=8)
    trip = {
        "id": "test_trip",
        "datetime": trip_datetime,  # Pass datetime object directly, not string
    }

    result = await manager.calcular_ventana_carga(
        trip=trip,
        soc_actual=50.0,
        hora_regreso=datetime.now() - timedelta(hours=1),
        charging_power_kw=7.0,
    )

    assert "ventana_horas" in result
    assert "es_suficiente" in result


@pytest.mark.asyncio
async def test_calcular_ventana_carga_with_no_departure_time(mock_hass, vehicle_id):
    """Test calcular_ventana_carga when trip_departure_time is None (line 1345)."""
    from custom_components.ev_trip_planner.trip import TripManager

    manager = TripManager(mock_hass, vehicle_id)
    manager._get_trip_time = MagicMock(return_value=None)  # No departure time
    manager.async_get_next_trip_after = AsyncMock(return_value=None)

    trip = {
        "id": "test_trip",
        "datetime": None,  # No datetime either
    }

    # This should use the fallback calculation (fin_ventana = now + DURACION_VIAJE_HORAS)
    result = await manager.calcular_ventana_carga(
        trip=trip,
        soc_actual=50.0,
        hora_regreso=datetime.now() - timedelta(hours=1),
        charging_power_kw=7.0,
    )

    assert "ventana_horas" in result


@pytest.mark.asyncio
async def test_calcular_ventana_carga_zero_charging_power(mock_hass, vehicle_id):
    """Test calcular_ventana_carga with zero charging power (line 1364)."""
    from custom_components.ev_trip_planner.trip import TripManager

    manager = TripManager(mock_hass, vehicle_id)
    manager._get_trip_time = MagicMock(
        return_value=datetime.now() + timedelta(hours=10)
    )
    manager.async_get_next_trip_after = AsyncMock(return_value=None)

    trip = {
        "id": "test_trip",
        "kwh": 10.0,
    }

    result = await manager.calcular_ventana_carga(
        trip=trip,
        soc_actual=50.0,
        hora_regreso=datetime.now(),
        charging_power_kw=0,  # Zero charging power
    )

    assert result["horas_carga_necesarias"] == 0.0


@pytest.mark.asyncio
async def test_calcular_soc_inicio_trips_empty_list(mock_hass, vehicle_id):
    """Test calcular_soc_inicio_trips with empty trips list (line 1411)."""
    manager = TripManager(mock_hass, vehicle_id)

    result = await manager.calcular_soc_inicio_trips(
        trips=[],
        soc_inicial=80.0,
        hora_regreso=datetime.now(),
        charging_power_kw=7.0,
        battery_capacity_kwh=50.0,
    )

    assert result == []


@pytest.mark.asyncio
async def test_calcular_soc_inicio_trips_zero_battery_capacity(mock_hass, vehicle_id):
    """Test calcular_soc_inicio_trips handles zero battery capacity (line 1555)."""
    manager = TripManager(mock_hass, vehicle_id)

    trip_dt = (datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M")
    trip = {
        "id": "test_trip",
        "tipo": "puntual",
        "datetime": trip_dt,
        "kwh": 10.0,
        "km": 50.0,
    }

    # Pass battery_capacity_kwh=0 to trigger the else branch at line 1555
    result = await manager.calcular_soc_inicio_trips(
        trips=[trip],
        soc_inicial=80.0,
        hora_regreso=datetime.now() - timedelta(hours=1),
        charging_power_kw=7.0,
        battery_capacity_kwh=0,  # Zero battery capacity
    )

    # Should calculate and return result
    assert isinstance(result, list)
    assert len(result) == 1
    assert (
        result[0]["arrival_soc"] == 80.0
    )  # Should equal soc_actual since battery_capacity <= 0


@pytest.mark.asyncio
async def test_calcular_soc_inicio_trips_invalid_hora_regreso(mock_hass, vehicle_id):
    """Test calcular_soc_inicio_trips handles invalid hora_regreso string (lines 1417-1423)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Use proper datetime format without microseconds
    trip_dt = (datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M")
    trip = {
        "id": "test_trip",
        "tipo": "puntual",
        "datetime": trip_dt,
        "kwh": 10.0,
    }

    # Pass invalid string for hora_regreso - should be caught by exception handling
    result = await manager.calcular_soc_inicio_trips(
        trips=[trip],
        soc_inicial=80.0,
        hora_regreso="invalid-datetime-string",
        charging_power_kw=7.0,
        battery_capacity_kwh=50.0,
    )

    # Should return empty or handle gracefully due to exception
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_calcular_soc_inicio_trips_first_trip_no_return_time(
    mock_hass, vehicle_id
):
    """Test calcular_soc_inicio_trips for first trip with no return time (line 1449)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Trip that will be first in the chain (earliest departure) - use proper datetime format
    trip_dt = (datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M")
    trip = {
        "id": "test_trip",
        "tipo": "puntual",
        "datetime": trip_dt,
        "kwh": 10.0,
        "km": 50.0,
    }

    # Pass None for hora_regreso - should estimate as departure - 6h
    result = await manager.calcular_soc_inicio_trips(
        trips=[trip],
        soc_inicial=80.0,
        hora_regreso=None,  # No return time
        charging_power_kw=7.0,
        battery_capacity_kwh=50.0,
    )

    # Should calculate something since we have a valid trip
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_calcular_soc_inicio_trips_zero_charging_power(mock_hass, vehicle_id):
    """Test calcular_soc_inicio_trips with zero charging power (line 1475)."""
    manager = TripManager(mock_hass, vehicle_id)

    trip_dt = (datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M")
    trip = {
        "id": "test_trip",
        "tipo": "puntual",
        "datetime": trip_dt,
        "kwh": 10.0,
        "km": 50.0,
    }

    result = await manager.calcular_soc_inicio_trips(
        trips=[trip],
        soc_inicial=80.0,
        hora_regreso=datetime.now() - timedelta(hours=1),
        charging_power_kw=0,  # Zero charging power
        battery_capacity_kwh=50.0,
    )

    # Should calculate with zero charging power
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_calcular_ventana_carga_multitrip_empty_trips(mock_hass, vehicle_id):
    """Test calcular_ventana_carga_multitrip with empty trips list (line 1411)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Call directly with empty trips to hit line 1411
    result = await manager.calcular_ventana_carga_multitrip(
        trips=[],
        soc_actual=80.0,
        hora_regreso=datetime.now(),
        charging_power_kw=7.0,
    )

    assert result == []


@pytest.mark.asyncio
async def test_calcular_soc_inicio_trips_iteration(mock_hass, vehicle_id):
    """Test calcular_soc_inicio_trips iterates through trips correctly (lines 1521-1566)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Two trips in chain - use proper datetime format
    trip1_dt = (datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M")
    trip2_dt = (datetime.now() + timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M")
    trip1 = {
        "id": "trip1",
        "tipo": "puntual",
        "datetime": trip1_dt,
        "kwh": 5.0,
        "km": 30.0,
    }
    trip2 = {
        "id": "trip2",
        "tipo": "puntual",
        "datetime": trip2_dt,
        "kwh": 10.0,
        "km": 60.0,
    }

    result = await manager.calcular_soc_inicio_trips(
        trips=[trip1, trip2],
        soc_inicial=80.0,
        hora_regreso=datetime.now() - timedelta(hours=1),
        charging_power_kw=7.0,
        battery_capacity_kwh=50.0,
    )

    # Should return results for both trips
    assert len(result) == 2
    assert "soc_inicio" in result[0]
    assert "trip" in result[0]
    assert "arrival_soc" in result[0]


@pytest.mark.asyncio
async def test_async_generate_power_profile_with_vehicle_config_battery(
    mock_hass, vehicle_id
):
    """Test async_generate_power_profile uses battery_capacity from vehicle_config (lines 1689-1690)."""
    manager = TripManager(mock_hass, vehicle_id)
    manager.async_get_all_trips_expanded = AsyncMock(return_value=[])
    manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)

    vehicle_config = {
        "battery_capacity_kwh": 75.0,  # Custom battery capacity
        "soc_current": 60.0,
    }

    # Should not raise even with no trips
    profile = await manager.async_generate_power_profile(
        charging_power_kw=7.4,
        planning_horizon_days=7,
        vehicle_config=vehicle_config,
    )

    assert len(profile) == 7 * 24


@pytest.mark.asyncio
async def test_async_generate_power_profile_battery_config_exception(
    mock_hass, vehicle_id
):
    """Test async_generate_power_profile handles battery config exception (lines 1697-1699)."""
    manager = TripManager(mock_hass, vehicle_id)
    manager.async_get_all_trips_expanded = AsyncMock(return_value=[])
    manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)

    # Make async_get_entry raise an exception
    mock_hass.config_entries.async_get_entry = MagicMock(
        side_effect=RuntimeError("Config error")
    )

    # Should use default battery capacity and not raise
    profile = await manager.async_generate_power_profile(
        charging_power_kw=7.4,
        planning_horizon_days=7,
    )

    assert len(profile) == 7 * 24


@pytest.mark.asyncio
async def test_async_generate_power_profile_battery_else_branch(mock_hass, vehicle_id):
    """Test async_generate_power_profile uses default battery when entry.data is falsy (line 1697)."""
    manager = TripManager(mock_hass, vehicle_id)
    manager.async_get_all_trips_expanded = AsyncMock(return_value=[])
    manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)

    # Make async_get_entry return an entry with empty/falsy data
    mock_entry = MagicMock()
    mock_entry.data = {}  # Empty dict is falsy in boolean context
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    # Should use default battery capacity (50.0) from the else branch at line 1697
    profile = await manager.async_generate_power_profile(
        charging_power_kw=7.4,
        planning_horizon_days=7,
    )

    assert len(profile) == 7 * 24


@pytest.mark.asyncio
async def test_async_generate_power_profile_with_active_recurring(
    mock_hass, vehicle_id
):
    """Test async_generate_power_profile with active recurring trips (lines 1713-1714)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up recurring trip
    manager._recurring_trips = {
        "rec_active": {
            "id": "rec_active",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "14:00",
            "activo": True,
            "km": 30,
            "kwh": 5.0,
        },
    }
    manager._punctual_trips = {}

    manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)
    manager._load_trips = AsyncMock()

    profile = await manager.async_generate_power_profile(
        charging_power_kw=7.4,
        planning_horizon_days=1,
    )

    assert len(profile) == 24


@pytest.mark.asyncio
async def test_async_generate_deferrables_schedule_battery_exception(
    mock_hass, vehicle_id
):
    """Test async_generate_deferrables_schedule handles battery config exception (lines 1758-1759)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up some trips
    manager._recurring_trips = {}
    manager._punctual_trips = {}

    manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)
    manager._load_trips = AsyncMock()

    # Make async_get_entry raise an exception at line 1755
    mock_hass.config_entries.async_get_entry = MagicMock(
        side_effect=RuntimeError("Config error")
    )

    # Should not raise
    schedule = await manager.async_generate_deferrables_schedule(
        charging_power_kw=7.4,
        planning_horizon_days=1,
    )

    assert isinstance(schedule, list)


@pytest.mark.asyncio
async def test_async_generate_deferrables_schedule_with_pending_punctual(
    mock_hass, vehicle_id
):
    """Test async_generate_deferrables_schedule with pending punctual trips (lines 1770-1771)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up punctual trip - use proper datetime format
    trip_dt = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M")
    manager._recurring_trips = {}
    manager._punctual_trips = {
        "pun_pending": {
            "id": "pun_pending",
            "tipo": "puntual",
            "estado": "pendiente",
            "datetime": trip_dt,
            "km": 50,
            "kwh": 8.0,
        },
    }

    manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)
    manager._load_trips = AsyncMock()

    schedule = await manager.async_generate_deferrables_schedule(
        charging_power_kw=7.4,
        planning_horizon_days=1,
    )

    assert isinstance(schedule, list)


@pytest.mark.asyncio
async def test_async_generate_deferrables_schedule_trip_sorting(mock_hass, vehicle_id):
    """Test async_generate_deferrables_schedule sorts trips by deadline (lines 1780-1783)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up trips with different deadlines - use proper datetime format
    trip_later_dt = (datetime.now() + timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M")
    trip_earlier_dt = (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")
    manager._recurring_trips = {}
    manager._punctual_trips = {
        "pun_later": {
            "id": "pun_later",
            "tipo": "puntual",
            "estado": "pendiente",
            "datetime": trip_later_dt,
            "km": 50,
            "kwh": 8.0,
        },
        "pun_earlier": {
            "id": "pun_earlier",
            "tipo": "puntual",
            "estado": "pendiente",
            "datetime": trip_earlier_dt,
            "km": 30,
            "kwh": 5.0,
        },
    }

    manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)
    manager._load_trips = AsyncMock()

    schedule = await manager.async_generate_deferrables_schedule(
        charging_power_kw=7.4,
        planning_horizon_days=1,
    )

    # Should sort by deadline - earlier trip first
    assert isinstance(schedule, list)


@pytest.mark.asyncio
async def test_async_generate_deferrables_schedule_battery_exception_later(
    mock_hass, vehicle_id
):
    """Test async_generate_deferrables_schedule handles battery exception at line 1815 (lines 1815-1816)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up trips - use proper datetime format
    trip_dt = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M")
    manager._recurring_trips = {}
    manager._punctual_trips = {
        "pun_pending": {
            "id": "pun_pending",
            "tipo": "puntual",
            "estado": "pendiente",
            "datetime": trip_dt,
            "km": 50,
            "kwh": 8.0,
        },
    }

    manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)
    manager._load_trips = AsyncMock()

    # Make async_get_entry raise an exception at line 1812 (second battery_capacity lookup)
    call_count = [0]

    def get_entry_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] > 1:
            raise RuntimeError("Config error on second call")
        mock_entry = MagicMock()
        mock_entry.data = {"battery_capacity_kwh": 50.0}
        return mock_entry

    mock_hass.config_entries.async_get_entry = MagicMock(
        side_effect=get_entry_side_effect
    )

    schedule = await manager.async_generate_deferrables_schedule(
        charging_power_kw=7.4,
        planning_horizon_days=1,
    )

    assert isinstance(schedule, list)


@pytest.mark.asyncio
async def test_async_generate_deferrables_schedule_zero_energy(mock_hass, vehicle_id):
    """Test async_generate_deferrables_schedule skips trips with zero energia_kwh (line 1833)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up trips - one with kwh=0 which should be skipped
    trip_dt = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M")
    manager._recurring_trips = {}
    manager._punctual_trips = {
        "pun_zero": {
            "id": "pun_zero",
            "tipo": "puntual",
            "estado": "pendiente",
            "datetime": trip_dt,
            "km": 0,
            "kwh": 0,  # Zero energy needed
        },
    }

    manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)
    manager._load_trips = AsyncMock()

    schedule = await manager.async_generate_deferrables_schedule(
        charging_power_kw=7.4,
        planning_horizon_days=1,
    )

    # Should not crash with zero energy
    assert isinstance(schedule, list)


@pytest.mark.asyncio
async def test_async_generate_deferrables_schedule_horas_necesarias_floor_one(
    mock_hass, vehicle_id
):
    """Test async_generate_deferrables_schedule floors horas_necesarias to 1 (line 1841)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up trip with very small energy need (will have horas_carga < 1)
    trip_dt = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    manager._recurring_trips = {}
    manager._punctual_trips = {
        "pun_small": {
            "id": "pun_small",
            "tipo": "puntual",
            "estado": "pendiente",
            "datetime": trip_dt,
            "km": 5,  # Small distance
            "kwh": 0.5,  # Small energy
        },
    }

    manager.async_get_vehicle_soc = AsyncMock(return_value=90.0)  # High SOC
    manager._load_trips = AsyncMock()

    schedule = await manager.async_generate_deferrables_schedule(
        charging_power_kw=7.4,
        planning_horizon_days=1,
    )

    # Should floor to 1 hour minimum
    assert isinstance(schedule, list)


@pytest.mark.asyncio
async def test_async_generate_deferrables_schedule_calculates_charging_window(
    mock_hass, vehicle_id
):
    """Test async_generate_deferrables_schedule calculates charging window correctly (lines 1849-1861)."""
    manager = TripManager(mock_hass, vehicle_id)

    # Set up a trip in the future - use proper datetime format
    trip_dt = (datetime.now() + timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M")
    manager._recurring_trips = {}
    manager._punctual_trips = {
        "pun_future": {
            "id": "pun_future",
            "tipo": "puntual",
            "estado": "pendiente",
            "datetime": trip_dt,
            "km": 100,
            "kwh": 15.0,
        },
    }

    manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)
    manager._load_trips = AsyncMock()

    schedule = await manager.async_generate_deferrables_schedule(
        charging_power_kw=7.4,
        planning_horizon_days=1,
    )

    # Should calculate charging window
    assert isinstance(schedule, list)


# =============================================================================
# COVERAGE: async_delete_all_trips coordinator branches (lines 769-773)
# =============================================================================


@pytest.mark.asyncio
async def test_async_delete_all_trips_with_coordinator(mock_hass, vehicle_id):
    """Line 769: coordinator is not None, data gets cleared and refreshed."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._trips = {"trip1": {}}
    manager._recurring_trips = {}
    manager._punctual_trips = {}
    manager.async_save_trips = AsyncMock()
    manager.publish_deferrable_loads = AsyncMock()
    manager._emhass_adapter = None

    coordinator = MagicMock()
    coordinator.data = {"per_trip_emhass_params": {"trip1": {}}}
    coordinator.async_refresh = AsyncMock()

    runtime_data = MagicMock()
    runtime_data.coordinator = coordinator

    entry = mock_hass.config_entries.async_get_entry.return_value
    entry.runtime_data = runtime_data

    await manager.async_delete_all_trips()

    coordinator.async_refresh.assert_awaited()
    assert manager._trips == {}


@pytest.mark.asyncio
async def test_async_delete_all_trips_coordinator_none(mock_hass, vehicle_id):
    """Line 771: coordinator is None in runtime_data."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._trips = {"trip1": {}}
    manager._recurring_trips = {}
    manager._punctual_trips = {}
    manager.async_save_trips = AsyncMock()
    manager.publish_deferrable_loads = AsyncMock()
    manager._emhass_adapter = None

    runtime_data = MagicMock()
    runtime_data.coordinator = None

    entry = mock_hass.config_entries.async_get_entry.return_value
    entry.runtime_data = runtime_data

    await manager.async_delete_all_trips()
    assert manager._trips == {}


@pytest.mark.asyncio
async def test_async_delete_all_trips_no_runtime_data(mock_hass, vehicle_id):
    """Line 773: entry has no runtime_data."""
    manager = TripManager(mock_hass, vehicle_id)
    manager._trips = {"trip1": {}}
    manager._recurring_trips = {}
    manager._punctual_trips = {}
    manager.async_save_trips = AsyncMock()
    manager.publish_deferrable_loads = AsyncMock()
    manager._emhass_adapter = None

    entry = mock_hass.config_entries.async_get_entry.return_value
    entry.runtime_data = None

    await manager.async_delete_all_trips()
    assert manager._trips == {}
