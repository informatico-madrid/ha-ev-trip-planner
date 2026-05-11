"""Tests for TripManager EMHASS integration, sensor CRUD hooks, and config entry lookup.

Consolidated from:
- test_trip_manager_datetime_tz.py
- test_trip_manager_emhass.py
- test_trip_manager_entry_lookup.py
- test_trip_manager_sensor_hooks.py
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from custom_components.ev_trip_planner.const import (
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_PENDING,
)
from custom_components.ev_trip_planner.trip import TripManager

# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def vehicle_id() -> str:
    return "test_vehicle"




@pytest.fixture
def mock_emhass_adapter():
    """Create a mock EMHASS adapter."""
    adapter = Mock()
    adapter.async_update_deferrable_load = AsyncMock()
    adapter.async_remove_deferrable_load = AsyncMock()
    adapter.async_publish_deferrable_load = AsyncMock()
    adapter.async_publish_all_deferrable_loads = AsyncMock(return_value=True)
    adapter.async_get_deferrable_params = AsyncMock(
        return_value={
            "treat_as_deferrable": 1,
            "optimization_cost_fun": "cost",
        }
    )
    adapter.get_all_assigned_indices = Mock(return_value={})
    adapter.vehicle_id = "test_vehicle"
    return adapter


# ── EMHASS Charging Power ────────────────────────────────────────────────

class TestTripManagerEMHASSMethods:
    """Tests for TripManager EMHASS-related methods."""

    @pytest.mark.asyncio
    async def test_get_charging_power_returns_configured_value(
        self, mock_hass_with_charging_power, vehicle_id
    ):
        """Test _get_charging_power returns configured value."""
        manager = TripManager(mock_hass_with_charging_power, vehicle_id)

        result = manager._get_charging_power()

        assert result == 11.0

    @pytest.mark.asyncio
    async def test_get_charging_power_returns_default_when_not_set(
        self, mock_hass, vehicle_id
    ):
        """Test _get_charging_power returns default when charging_power not configured."""
        manager = TripManager(mock_hass, vehicle_id)

        result = manager._get_charging_power()

        # Should return default 11.0 kW
        assert result == 11.0


# ── Active Trips ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_all_active_trips_returns_active_and_pending_trips(
        self, mock_hass, vehicle_id
    ):
        """Test _get_all_active_trips returns active trips including pending punctual trips."""
        manager = TripManager(mock_hass, vehicle_id)

        # Add a punctual trip
        manager._punctual_trips["trip_1"] = {
            "descripcion": "Test trip",
            "estado": TRIP_STATUS_PENDING,
            "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
            "km": 50.0,
            "kwh": 7.5,
        }

        # Add a recurring trip
        manager._recurring_trips["recurring_1"] = {
            "descripcion": "Daily commute",
            "activo": True,
            "hora": "08:00",
            "km": 30.0,
            "kwh": 4.5,
        }

        active_trips = await manager._get_all_active_trips()

        assert len(active_trips) == 2

    @pytest.mark.asyncio
    async def test_get_all_active_trips_returns_empty_list_when_no_trips(
        self, mock_hass, vehicle_id
    ):
        """Test _get_all_active_trips returns empty list when no trips exist."""
        manager = TripManager(mock_hass, vehicle_id)

        active_trips = await manager._get_all_active_trips()

        assert active_trips == []

    @pytest.mark.asyncio
    async def test_get_all_active_trips_excludes_inactive_recurring_trips(
        self, mock_hass, vehicle_id
    ):
        """Test _get_all_active_trips excludes inactive recurring trips."""
        manager = TripManager(mock_hass, vehicle_id)

        # Add active recurring trip
        manager._recurring_trips["active"] = {
            "descripcion": "Active trip",
            "activo": True,
            "hora": "08:00",
        }

        # Add inactive recurring trip
        manager._recurring_trips["inactive"] = {
            "descripcion": "Inactive trip",
            "activo": False,
            "hora": "09:00",
        }

        active_trips = await manager._get_all_active_trips()

        # Should only include active trip
        assert len(active_trips) == 1
        assert active_trips[0]["descripcion"] == "Active trip"

    @pytest.mark.asyncio
    async def test_get_all_active_trips_excludes_completed_punctual_trips(
        self, mock_hass, vehicle_id
    ):
        """Test _get_all_active_trips excludes completed punctual trips."""
        manager = TripManager(mock_hass, vehicle_id)

        # Add pending punctual trip
        manager._punctual_trips["pending"] = {
            "descripcion": "Pending trip",
            "estado": TRIP_STATUS_PENDING,
        }

        # Add completed punctual trip
        manager._punctual_trips["completed"] = {
            "descripcion": "Completed trip",
            "estado": TRIP_STATUS_COMPLETED,
        }

        active_trips = await manager._get_all_active_trips()

        # Should only include pending trip
        assert len(active_trips) == 1
        assert active_trips[0]["descripcion"] == "Pending trip"


# ── EMHASS Trip Sync ─────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_sync_trip_to_emhass_does_nothing_without_adapter(
        self, mock_hass, vehicle_id
    ):
        """Test sync_trip_to_emhass is a no-op without EMHASS adapter."""
        manager = TripManager(mock_hass, vehicle_id)

        # No adapter set
        manager._emhass_adapter = None

        # Should not raise - method signature is (trip_id, old_trip, updates)
        await manager._async_sync_trip_to_emhass("trip_1", {}, {"descripcion": "test"})

    @pytest.mark.asyncio
    async def test_sync_trip_to_emhass_removes_inactive_trip(
        self, mock_hass, vehicle_id, mock_emhass_adapter
    ):
        """Test sync_trip_to_emhass removes inactive trip from EMHASS."""
        manager = TripManager(mock_hass, vehicle_id)
        manager._emhass_adapter = mock_emhass_adapter

        # Set up inactive recurring trip
        manager._recurring_trips["trip_1"] = {
            "descripcion": "Inactive trip",
            "activo": False,
        }

        await manager._async_sync_trip_to_emhass(
            "trip_1", {"activo": False}, {"descripcion": "test"}
        )

        mock_emhass_adapter.async_remove_deferrable_load.assert_called_once_with(
            "trip_1"
        )

    @pytest.mark.asyncio
    async def test_sync_trip_to_emhass_updates_active_trip(
        self, mock_hass, vehicle_id, mock_emhass_adapter
    ):
        """Test sync_trip_to_emhass updates active trip via EMHASS adapter."""
        manager = TripManager(mock_hass, vehicle_id)
        manager._emhass_adapter = mock_emhass_adapter
        manager._charging_power_kw = 11.0

        # Set up active punctual trip
        manager._punctual_trips["trip_1"] = {
            "descripcion": "Active trip",
            "estado": TRIP_STATUS_PENDING,
            "km": 50.0,
            "kwh": 7.5,
            "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
        }

        # Non-critical update (just description)
        await manager._async_sync_trip_to_emhass(
            "trip_1",
            {"descripcion": "Active trip"},
            {"descripcion": "Updated description"},
        )

        mock_emhass_adapter.async_update_deferrable_load.assert_called()

    @pytest.mark.asyncio
    async def test_sync_trip_to_emhass_recalculates_on_critical_field_change(
        self, mock_hass, vehicle_id, mock_emhass_adapter
    ):
        """Test sync_trip_to_emhass recalculates when critical fields like km change."""
        manager = TripManager(mock_hass, vehicle_id)
        manager._emhass_adapter = mock_emhass_adapter
        manager._charging_power_kw = 11.0

        # Set up active punctual trip
        manager._punctual_trips["trip_1"] = {
            "descripcion": "Active trip",
            "estado": TRIP_STATUS_PENDING,
            "km": 50.0,
            "kwh": 7.5,
            "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
        }

        # Critical update (km changes)
        await manager._async_sync_trip_to_emhass("trip_1", {"km": 50.0}, {"km": 100.0})

        # Should call publish to recalculate
        mock_emhass_adapter.async_publish_all_deferrable_loads.assert_called()


# ── EMHASS Trip Remove/Publish ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_remove_trip_from_emhass_calls_adapter_and_publish(
        self, mock_hass, vehicle_id, mock_emhass_adapter
    ):
        """Test _async_remove_trip_from_emhass removes trip and republishes."""
        manager = TripManager(mock_hass, vehicle_id)
        manager._emhass_adapter = mock_emhass_adapter
        manager._charging_power_kw = 7.4

        # Add a trip
        manager._punctual_trips["trip_1"] = {
            "descripcion": "Test",
            "estado": TRIP_STATUS_PENDING,
            "km": 50.0,
        }

        await manager._async_remove_trip_from_emhass("trip_1")

        mock_emhass_adapter.async_remove_deferrable_load.assert_called_once_with(
            "trip_1"
        )
        mock_emhass_adapter.async_publish_all_deferrable_loads.assert_called()

    @pytest.mark.asyncio
    async def test_publish_new_trip_to_emhass_calls_adapter_publish(
        self, mock_hass, vehicle_id, mock_emhass_adapter
    ):
        """Test _async_publish_new_trip_to_emhass publishes trip via adapter."""
        manager = TripManager(mock_hass, vehicle_id)
        manager._emhass_adapter = mock_emhass_adapter
        manager._charging_power_kw = 11.0

        trip = {
            "descripcion": "New trip",
            "km": 50.0,
            "kwh": 7.5,
        }

        await manager._async_publish_new_trip_to_emhass(trip)

        # Should call async_publish_deferrable_load
        mock_emhass_adapter.async_publish_deferrable_load.assert_called()
        mock_emhass_adapter.async_publish_all_deferrable_loads.assert_called()


# ── Helper Methods ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_day_index_returns_zero_for_monday(self, mock_hass, vehicle_id):
        """Test _get_day_index returns correct value for Monday (lunes)."""
        manager = TripManager(mock_hass, vehicle_id)

        result = manager._get_day_index("lunes")

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_day_index_returns_six_for_sunday(self, mock_hass, vehicle_id):
        """Test _get_day_index returns correct value for Sunday (domingo)."""
        manager = TripManager(mock_hass, vehicle_id)

        result = manager._get_day_index("domingo")

        assert result == 6

    @pytest.mark.asyncio
    async def test_get_day_index_defaults_to_monday_for_invalid_day(
        self, mock_hass, vehicle_id
    ):
        """Test _get_day_index defaults to Monday for invalid day string."""
        manager = TripManager(mock_hass, vehicle_id)

        # Invalid day defaults to Monday (index 0 in DAYS_OF_WEEK)
        result = manager._get_day_index("invalid_day")
        assert result == 0  # Monday (index 0)


# ── Config Entry Battery Capacity Lookup ──────────────────────────────────

@pytest.mark.asyncio
async def test_async_generate_power_profile_uses_config_entry_battery_capacity() -> None:
    """The power profile calculation should use the config entry's battery capacity.

    This test sets up a `ConfigEntry` whose `entry_id` is different from the
    vehicle slug. It then instantiates `TripManager` WITHOUT passing the
    `entry_id` (the buggy code calls async_get_entry(self.vehicle_id)), and
    asserts that the battery capacity is taken from the config entry.
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

    # We expect the test to pass when the bug is fixed:
    # battery_capacity_kwh should be 62.0 (from config entry) not 50.0 (fallback)
    assert captured.get("battery_capacity_kwh") == 62.0


# ── Timezone-Aware Datetime Handling ──────────────────────────────────────

@pytest.mark.asyncio
async def test_async_calcular_energia_necesaria_handles_tz_aware_datetime(
    monkeypatch,
) -> None:
    """Calling async_calcular_energia_necesaria with a tz-aware datetime object
    must not raise a TypeError due to naive/aware subtraction.
    """
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])

    tm = TripManager(hass, "veh_test")

    # Trip with tz-aware datetime object (not a string)
    # Use a fixed future datetime to ensure hours_available > 0 deterministically
    trip_future_datetime = datetime(2027, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
    trip = {"tipo": None, "datetime": trip_future_datetime}

    vehicle_config = {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "soc_current": 50.0,
    }

    # Mock dt_util.now() to a fixed earlier aware datetime for deterministic results.
    # This prevents flakiness when the test runs after the trip's original time.
    from custom_components.ev_trip_planner import trip_manager

    fixed_now = datetime(2026, 12, 1, 8, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(trip_manager.dt_util, "now", lambda: fixed_now)

    # Should complete without raising and return the expected keys
    res = await tm.async_calcular_energia_necesaria(trip, vehicle_config)
    assert isinstance(res, dict)
    assert "energia_necesaria_kwh" in res
    assert "horas_disponibles" in res
    # CRITICAL: assert the trip is viable (hours available > 0)
    # Without this, a past-datetime trip could pass the test while having 0 hours available
    assert res["horas_disponibles"] > 0


@pytest.mark.asyncio
async def test_async_calcular_energia_necesaria_handles_naive_datetime_object(
    monkeypatch,
) -> None:
    """Test that async_calcular_energia_necesaria handles naive datetime objects."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])

    tm = TripManager(hass, "veh_test")

    # Trip with naive datetime object
    trip_naive_datetime = datetime(2027, 6, 15, 10, 0, 0)
    trip = {"tipo": None, "datetime": trip_naive_datetime}

    vehicle_config = {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "soc_current": 50.0,
    }

    # Mock dt_util.now() to a fixed earlier aware datetime for deterministic results.
    from custom_components.ev_trip_planner import trip_manager

    fixed_now = datetime(2026, 12, 1, 8, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(trip_manager.dt_util, "now", lambda: fixed_now)

    # Should complete without raising and return the expected keys
    res = await tm.async_calcular_energia_necesaria(trip, vehicle_config)
    assert isinstance(res, dict)
    assert "energia_necesaria_kwh" in res
    assert "horas_disponibles" in res
    assert res["horas_disponibles"] > 0


@pytest.mark.asyncio
async def test_async_calcular_energia_necesaria_handles_strptime_naive_datetime(
    monkeypatch,
) -> None:
    """Test that async_calcular_energia_necesaria handles string datetime via strptime."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])

    tm = TripManager(hass, "veh_test")

    # Trip with string datetime - goes through parse_datetime path
    # Use a fixed future string datetime to ensure deterministic viability
    trip = {"tipo": None, "datetime": "2027-06-15T10:00"}

    vehicle_config = {
        "battery_capacity_kwh": 50.0,
        "charging_power_kw": 3.6,
        "soc_current": 50.0,
    }

    # Mock dt_util.now() to a fixed earlier aware datetime for deterministic results
    from custom_components.ev_trip_planner import trip_manager

    fixed_now = datetime(2026, 12, 1, 8, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(trip_manager.dt_util, "now", lambda: fixed_now)

    # Should complete without raising and return the expected keys
    res = await tm.async_calcular_energia_necesaria(trip, vehicle_config)
    assert isinstance(res, dict)
    assert "energia_necesaria_kwh" in res
    assert "horas_disponibles" in res
    assert res["horas_disponibles"] > 0


# ── Sensor CRUD Hooks ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_recurring_trip_creates_sensor_and_emhass_sensor():
    """Test that adding a recurring trip creates both trip and EMHASS sensors."""
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
async def test_add_punctual_trip_creates_sensor_and_emhass_sensor():
    """Test that adding a punctual trip creates both trip and EMHASS sensors."""
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
async def test_delete_trip_removes_sensor_and_emhass_sensor():
    """Test that deleting a trip removes both trip and EMHASS sensors."""
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
    """Test that updating a trip calls the sensor update function."""
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
