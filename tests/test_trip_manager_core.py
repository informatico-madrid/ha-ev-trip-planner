"""Core tests for TripManager covering CRUD and state transitions (hass.data API)."""

from __future__ import annotations

import unittest.mock
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.const import (
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_PENDING,
)
from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def vehicle_id() -> str:
    return "chispitas"


@pytest.fixture
def mock_hass():
    """Create a mock hass with config_entries, data, and storage."""

    hass = MagicMock()
    # Mock config_entries with async_entries returning list of entries
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"
    # Use a dict for data, and a MagicMock that proxies to the dict
    data_dict = {"vehicle_name": "test_vehicle", "charging_power_kw": 3.6}
    mock_entry.data = MagicMock()
    mock_entry.data.get = MagicMock(side_effect=lambda key, default=None: data_dict.get(key, default))
    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    # Mock hass.data with proper namespace (legacy)
    hass.data = {}
    # Mock async_add_executor_job - required by HA Store API
    hass.async_add_executor_job = AsyncMock(return_value=None)

    # Mock config
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"

    return hass


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
            "hora": "09:00"
        }
    }

    # Patch Store.async_load to return our test data
    with patch.object(ha_storage.Store, 'async_load', new_callable=lambda: AsyncMock(return_value={
        "data": {
            "trips": existing_trips,
            "recurring_trips": existing_trips,
            "punctual_trips": {}
        }
    })):
        manager = TripManager(mock_hass, vehicle_id)
        await manager.async_setup()

        # Should have loaded the existing trips
        assert "rec_lun_123" in manager._recurring_trips


@pytest.mark.asyncio
async def test_async_load_trips_empty_returns_list(mock_hass, vehicle_id):
    """Test that _load_trips returns empty when no data exists."""
    from homeassistant.helpers import storage as ha_storage

    # Patch Store.async_load to return None (empty)
    with patch.object(ha_storage.Store, 'async_load', new_callable=lambda: AsyncMock(return_value=None)):
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
    with patch.object(ha_storage.Store, 'async_load', new_callable=lambda: AsyncMock(return_value={
        "data": {
            "trips": {**existing_recurring, **existing_punctual},
            "recurring_trips": existing_recurring,
            "punctual_trips": existing_punctual
        }
    })):
        manager = TripManager(mock_hass, vehicle_id)
        await manager._load_trips()

        assert len(manager._recurring_trips) == 1
        assert len(manager._punctual_trips) == 1
        assert "rec_lun_123" in manager._recurring_trips
        assert "pun_20251119_123" in manager._punctual_trips


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
            "hora": "09:00"
        }
    }

    # Patch Store.async_save to capture the save
    saved_data = {}
    async def capture_save(data):
        saved_data["data"] = data
        return True

    with patch.object(ha_storage.Store, 'async_save', new_callable=lambda: AsyncMock(side_effect=capture_save)):
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
    assert manager._punctual_trips["pun_20251119_87654321"]["estado"] == TRIP_STATUS_COMPLETED


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
            "hora": "09:00"
        },
    }
    manager._punctual_trips = {
        "pun_20251119_87654321": {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00"
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

    with unittest.mock.patch("custom_components.ev_trip_planner.trip_manager.datetime", mock_datetime):
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

    with unittest.mock.patch("custom_components.ev_trip_planner.trip_manager.datetime", mock_datetime):
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
async def test_async_get_kwh_needed_today_excludes_inactive_trips(mock_hass, vehicle_id):
    """Test that inactive/paused recurring trips are excluded."""
    from datetime import datetime

    mock_datetime = unittest.mock.MagicMock()
    mock_datetime.now.return_value = datetime(2025, 1, 6, 10, 0)

    with unittest.mock.patch("custom_components.ev_trip_planner.trip_manager.datetime", mock_datetime):
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
async def test_async_get_kwh_needed_today_excludes_completed_trips(mock_hass, vehicle_id):
    """Test that completed punctual trips are excluded."""
    from datetime import datetime

    mock_datetime = unittest.mock.MagicMock()
    mock_datetime.now.return_value = datetime(2025, 1, 6, 10, 0)
    mock_datetime.strptime = datetime.strptime

    with unittest.mock.patch("custom_components.ev_trip_planner.trip_manager.datetime", mock_datetime):
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
    with patch("custom_components.ev_trip_planner.trip_manager.datetime") as mock_dt:
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
async def test_async_get_hours_needed_today_with_default_charging_power(mock_hass, vehicle_id):
    """Test async_get_hours_needed_today uses default charging power when not configured."""
    # Return None when no entry found - use default
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=None)

    # Freeze time to Monday 2025-01-06 at 10:00
    frozen_time = datetime(2025, 1, 6, 10, 0)
    with patch("custom_components.ev_trip_planner.trip_manager.datetime") as mock_dt:
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
    with patch("custom_components.ev_trip_planner.trip_manager.datetime") as mock_dt:
        mock_dt.now.return_value = frozen_time
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

    mock_datetime = unittest.mock.MagicMock()
    mock_datetime.now.return_value = datetime(2025, 1, 6, 8, 0)  # Monday 8:00 AM
    mock_datetime.strptime = datetime.strptime

    with unittest.mock.patch("custom_components.ev_trip_planner.trip_manager.datetime", mock_datetime):
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
    with patch("custom_components.ev_trip_planner.trip_manager.datetime") as mock_dt:
        mock_dt.now.return_value = frozen_time
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

    mock_datetime = unittest.mock.MagicMock()
    mock_datetime.now.return_value = datetime(2025, 1, 6, 8, 0)
    mock_datetime.strptime = datetime.strptime

    with unittest.mock.patch("custom_components.ev_trip_planner.trip_manager.datetime", mock_datetime):
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
    from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
    from unittest.mock import MagicMock

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
    """Test _publish_deferrable_loads returns early when no adapter."""
    manager = TripManager(mock_hass, vehicle_id)

    # No adapter set - the method should return early without error
    # This tests line 66 - early return when emhass_adapter is falsy
    await manager._publish_deferrable_loads()

    # Should complete without error (early return)


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
async def test_get_charging_power_returns_default_when_not_configured(mock_hass, vehicle_id):
    """Test get_charging_power returns default when not configured."""
    # Configure entry without charging_power_kw
    mock_entry = MagicMock()
    mock_entry.data = {"vehicle_name": vehicle_id}
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    manager = TripManager(mock_hass, vehicle_id)

    # Call public get_charging_power method
    power = manager.get_charging_power()

    # Should return default charging power
    from custom_components.ev_trip_planner.trip_manager import DEFAULT_CHARGING_POWER
    assert power == DEFAULT_CHARGING_POWER


@pytest.mark.asyncio
async def test_get_charging_power_sensor_not_found(mock_hass, vehicle_id):
    """Test get_charging_power returns default when sensor not found."""
    manager = TripManager(mock_hass, vehicle_id)
    # Don't set any vehicle controller or sensor

    # Try to get charging power - should return default
    power = manager._get_charging_power()

    # Should return default charging power
    from custom_components.ev_trip_planner.trip_manager import DEFAULT_CHARGING_POWER
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
    """Test _publish_deferrable_loads when adapter is set."""
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
    await manager._publish_deferrable_loads()

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
