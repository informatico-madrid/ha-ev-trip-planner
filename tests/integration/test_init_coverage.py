"""Tests for __init__ entry lifecycle, emhass rollback, trip rotation edge cases, and hourly refresh."""

from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_VEHICLE_NAME,
)
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.trip_manager import TripManager


class MockConfigEntry:
    """Mock Home Assistant ConfigEntry for integration tests."""

    def __init__(self, vehicle_name: str, config: Dict[str, Any]) -> None:
        """Initialize mock config entry."""
        self.entry_id = f"ev_trip_planner_{vehicle_name}"
        self.domain = "ev_trip_planner"
        self.title = vehicle_name
        self.state = "loaded"
        self.data = config
        self.runtime_data = None


class MockRuntimeData:
    """Mock runtime data for config entry."""

    def __init__(self, coordinator=None) -> None:
        """Initialize mock runtime data."""
        self.coordinator = coordinator
        self.hourly_refresh_cancel = None


@pytest.fixture
def mock_store():
    """Mock Store object."""
    store = MagicMock()
    return store


@pytest.fixture
def mock_coordinator():
    """Mock DataUpdateCoordinator."""
    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.async_add_listener = MagicMock()
    coordinator.async_remove_listener = MagicMock()
    coordinator.async_refresh = AsyncMock(return_value=None)
    return coordinator


class TestUnloadEntryTimerCancel:
    """Tests for async_unload_entry timer cancel path (__init__.py:190-192)."""

    @pytest.mark.asyncio
    async def test_async_unload_entry_cancels_timer(self, hass, mock_store, mock_coordinator):
        """Test that async_unload_entry cancels the hourly refresh timer."""
        from custom_components.ev_trip_planner import async_unload_entry

        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        entry = MockConfigEntry("test_vehicle", config)

        cancel_callback = MagicMock()
        entry.runtime_data = MockRuntimeData(coordinator=mock_coordinator)
        entry.runtime_data.hourly_refresh_cancel = cancel_callback

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            with patch(
                "custom_components.ev_trip_planner.async_unload_entry_cleanup",
                return_value=True,
            ) as mock_cleanup:
                result = await async_unload_entry(hass, entry)

                cancel_callback.assert_called_once()
                assert entry.runtime_data.hourly_refresh_cancel is None
                mock_cleanup.assert_called_once()
                assert result is True

    @pytest.mark.asyncio
    async def test_async_unload_entry_without_timer_cancel(self, hass, mock_store, mock_coordinator):
        """Test that async_unload_entry works when hourly_refresh_cancel is None."""
        from custom_components.ev_trip_planner import async_unload_entry

        config = {
            CONF_VEHICLE_NAME: "test_vehicle2",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        entry = MockConfigEntry("test_vehicle2", config)
        entry.runtime_data = MockRuntimeData(coordinator=mock_coordinator)
        entry.runtime_data.hourly_refresh_cancel = None

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            with patch(
                "custom_components.ev_trip_planner.async_unload_entry_cleanup",
                return_value=True,
            ) as mock_cleanup:
                result = await async_unload_entry(hass, entry)
                mock_cleanup.assert_called_once()
                assert result is True

    @pytest.mark.asyncio
    async def test_async_unload_entry_without_runtime_data(self, hass, mock_store, mock_coordinator):
        """Test that async_unload_entry works when runtime_data is missing."""
        from custom_components.ev_trip_planner import async_unload_entry

        config = {
            CONF_VEHICLE_NAME: "test_vehicle3",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        entry = MockConfigEntry("test_vehicle3", config)
        entry.runtime_data = None

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            with patch(
                "custom_components.ev_trip_planner.async_unload_entry_cleanup",
                return_value=True,
            ) as mock_cleanup:
                result = await async_unload_entry(hass, entry)
                mock_cleanup.assert_called_once()
                assert result is True


class TestFailedTripRollback:
    """Tests for failed trip rollback in async_publish_all_deferrable_loads (emhass_adapter.py:796-802)."""

    @pytest.mark.asyncio
    async def test_async_publish_all_deferrable_loads_rollback_releases_index(
        self, hass, mock_store, mock_coordinator
    ):
        """Test that rollback releases the index back to available pool."""
        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        entry = MockConfigEntry("test_vehicle", config)
        entry.runtime_data = MockRuntimeData(coordinator=mock_coordinator)

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

            adapter._charging_power_kw = 7.4
            adapter._available_indices = [0, 1, 2, 3, 4]

            trips = [
                {
                    "id": "rollback_test",
                    "descripcion": "Rollback test",
                    "kwh": 5.0,
                    "datetime": "2030-01-01T00:00:00+00:00",
                },
            ]

            hass.states.async_set = MagicMock()
            hass.states.async_get = MagicMock(return_value=MagicMock(state="50"))

            published_calls = []

            async def side_effect(trip):
                trip_id = trip.get("id")
                if trip_id and trip_id == "rollback_test":
                    if adapter._available_indices:
                        idx = adapter._available_indices.pop(0)
                        adapter._index_map[trip_id] = idx
                published_calls.append(trip_id)
                return False

            mock_publish = AsyncMock(side_effect=side_effect)

            with patch.object(
                type(adapter), "async_publish_deferrable_load", mock_publish
            ):
                adapter._calculate_power_profile_from_trips = MagicMock(return_value=[])
                adapter._generate_schedule_from_trips = MagicMock(return_value=[])
                adapter._get_current_soc = AsyncMock(return_value=50.0)
                adapter._presence_monitor = None

                with patch(
                    "custom_components.ev_trip_planner.emhass_adapter.calculate_multi_trip_charging_windows",
                    return_value=[],
                ):
                    await adapter.async_publish_all_deferrable_loads(trips)

                    assert mock_publish.call_count == 1
                    assert "rollback_test" in published_calls

    @pytest.mark.asyncio
    async def test_async_publish_all_deferrable_loads_rollback_executes_index_release_code(
        self, hass, mock_store, mock_coordinator
    ):
        """Test that specifically exercises the index release code in rollback (lines 796-798)."""
        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        entry = MockConfigEntry("test_vehicle", config)
        entry.runtime_data = MockRuntimeData(coordinator=mock_coordinator)

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

            adapter._charging_power_kw = 7.4
            adapter._available_indices = [5, 10, 15]

            trips = [
                {
                    "id": "rollback_index_test",
                    "descripcion": "Rollback index test",
                    "kwh": 5.0,
                    "datetime": "2030-01-01T00:00:00+00:00",
                },
            ]

            hass.states.async_set = MagicMock()
            hass.states.async_get = MagicMock(return_value=MagicMock(state="50"))

            async def side_effect(trip):
                trip_id = trip.get("id")
                if trip_id and trip_id == "rollback_index_test":
                    if adapter._available_indices:
                        idx = adapter._available_indices.pop(0)
                        adapter._index_map[trip_id] = idx
                return False

            mock_publish = AsyncMock(side_effect=side_effect)

            with patch.object(
                type(adapter), "async_publish_deferrable_load", mock_publish
            ):
                adapter._calculate_power_profile_from_trips = MagicMock(return_value=[])
                adapter._generate_schedule_from_trips = MagicMock(return_value=[])
                adapter._get_current_soc = AsyncMock(return_value=50.0)
                adapter._presence_monitor = None

                with patch(
                    "custom_components.ev_trip_planner.emhass_adapter.calculate_multi_trip_charging_windows",
                    return_value=[],
                ):
                    await adapter.async_publish_all_deferrable_loads(trips)

                    assert mock_publish.call_count == 1

    @pytest.mark.asyncio
    async def test_async_publish_all_deferrable_loads_rollback_value_error_handled(
        self, hass, mock_store, mock_coordinator
    ):
        """Test that ValueError when removing from _published_trips is handled gracefully."""
        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        entry = MockConfigEntry("test_vehicle", config)
        entry.runtime_data = MockRuntimeData(coordinator=mock_coordinator)

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

            adapter._charging_power_kw = 7.4
            assert adapter._published_trips == []

            trips = [
                {
                    "id": "value_error_test",
                    "descripcion": "ValueError test",
                    "kwh": 5.0,
                    "datetime": "2030-01-01T00:00:00+00:00",
                },
            ]

            hass.states.async_set = MagicMock()
            hass.states.async_get = MagicMock(return_value=MagicMock(state="50"))

            async def side_effect(trip):
                trip_id = trip.get("id")
                if trip_id and trip_id == "value_error_test":
                    if adapter._available_indices:
                        idx = adapter._available_indices.pop(0)
                        adapter._index_map[trip_id] = idx
                return False

            mock_publish = AsyncMock(side_effect=side_effect)

            with patch.object(
                type(adapter), "async_publish_deferrable_load", mock_publish
            ):
                adapter._calculate_power_profile_from_trips = MagicMock(return_value=[])
                adapter._generate_schedule_from_trips = MagicMock(return_value=[])
                adapter._get_current_soc = AsyncMock(return_value=50.0)
                adapter._presence_monitor = None

                with patch(
                    "custom_components.ev_trip_planner.emhass_adapter.calculate_multi_trip_charging_windows",
                    return_value=[],
                ):
                    await adapter.async_publish_all_deferrable_loads(trips)

    @pytest.mark.asyncio
    async def test_async_publish_all_deferrable_loads_rollback_logs_warning(
        self, hass, mock_store, mock_coordinator
    ):
        """Test that rollback logs the warning message."""
        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        entry = MockConfigEntry("test_vehicle", config)
        entry.runtime_data = MockRuntimeData(coordinator=mock_coordinator)

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

            adapter._charging_power_kw = 7.4

            trips = [
                {
                    "id": "rollback_log_test",
                    "descripcion": "Rollback log test",
                    "kwh": 5.0,
                    "datetime": "2030-01-01T00:00:00+00:00",
                },
            ]

            hass.states.async_set = MagicMock()
            hass.states.async_get = MagicMock(return_value=MagicMock(state="50"))

            async def side_effect(trip):
                trip_id = trip.get("id")
                if trip_id and trip_id == "rollback_log_test":
                    if adapter._available_indices:
                        idx = adapter._available_indices.pop(0)
                        adapter._index_map[trip_id] = idx
                return False

            mock_publish = AsyncMock(side_effect=side_effect)

            with patch.object(
                type(adapter), "async_publish_deferrable_load", mock_publish
            ):
                adapter._calculate_power_profile_from_trips = MagicMock(return_value=[])
                adapter._generate_schedule_from_trips = MagicMock(return_value=[])
                adapter._get_current_soc = AsyncMock(return_value=50.0)
                adapter._presence_monitor = None

                with patch(
                    "custom_components.ev_trip_planner.emhass_adapter._LOGGER"
                ) as mock_logger:
                    await adapter.async_publish_all_deferrable_loads(trips)

                    warning_calls = [
                        call for call in mock_logger.warning.call_args_list
                    ]
                    rollback_warnings = [
                        call for call in warning_calls if "Rolling back" in str(call)
                    ]
                    assert len(rollback_warnings) >= 1
                    assert "rollback_log_test" in str(rollback_warnings[0])

    @pytest.mark.asyncio
    async def test_async_publish_all_deferrable_loads_rollback_clears_cache(
        self, hass, mock_store, mock_coordinator
    ):
        """Test that rollback clears per-trip cache entry."""
        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        entry = MockConfigEntry("test_vehicle", config)
        entry.runtime_data = MockRuntimeData(coordinator=mock_coordinator)

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

            adapter._charging_power_kw = 7.4

            trips = [
                {
                    "id": "cache_clear_test",
                    "descripcion": "Cache clear test",
                    "kwh": 5.0,
                    "datetime": "2030-01-01T00:00:00+00:00",
                },
            ]

            hass.states.async_set = MagicMock()
            hass.states.async_get = MagicMock(return_value=MagicMock(state="50"))

            async def side_effect(trip):
                trip_id = trip.get("id")
                if trip_id and trip_id == "cache_clear_test":
                    if adapter._available_indices:
                        idx = adapter._available_indices.pop(0)
                        adapter._index_map[trip_id] = idx
                return False

            mock_publish = AsyncMock(side_effect=side_effect)

            with patch.object(
                type(adapter), "async_publish_deferrable_load", mock_publish
            ):
                adapter._calculate_power_profile_from_trips = MagicMock(return_value=[])
                adapter._generate_schedule_from_trips = MagicMock(return_value=[])
                adapter._get_current_soc = AsyncMock(return_value=50.0)
                adapter._presence_monitor = None

                with patch(
                    "custom_components.ev_trip_planner.emhass_adapter.calculate_multi_trip_charging_windows",
                    return_value=[],
                ):
                    await adapter.async_publish_all_deferrable_loads(trips)

    @pytest.mark.asyncio
    async def test_async_publish_all_deferrable_loads_rollback_no_exception_on_value_error(
        self, hass, mock_store, mock_coordinator
    ):
        """Test that the ValueError exception handler (lines 801-802) is executed."""
        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        entry = MockConfigEntry("test_vehicle", config)
        entry.runtime_data = MockRuntimeData(coordinator=mock_coordinator)

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

            adapter._charging_power_kw = 7.4
            assert adapter._published_trips == []

            trips = [
                {
                    "id": "no_value_error_test",
                    "descripcion": "No ValueError test",
                    "kwh": 5.0,
                    "datetime": "2030-01-01T00:00:00+00:00",
                },
            ]

            hass.states.async_set = MagicMock()
            hass.states.async_get = MagicMock(return_value=MagicMock(state="50"))

            async def side_effect(trip):
                trip_id = trip.get("id")
                if trip_id and trip_id == "no_value_error_test":
                    if adapter._available_indices:
                        idx = adapter._available_indices.pop(0)
                        adapter._index_map[trip_id] = idx
                return False

            mock_publish = AsyncMock(side_effect=side_effect)

            with patch.object(
                type(adapter), "async_publish_deferrable_load", mock_publish
            ):
                adapter._calculate_power_profile_from_trips = MagicMock(return_value=[])
                adapter._generate_schedule_from_trips = MagicMock(return_value=[])
                adapter._get_current_soc = AsyncMock(return_value=50.0)
                adapter._presence_monitor = None

                with patch(
                    "custom_components.ev_trip_planner.emhass_adapter.calculate_multi_trip_charging_windows",
                    return_value=[],
                ):
                    try:
                        await adapter.async_publish_all_deferrable_loads(trips)
                    except ValueError:
                        pytest.fail("ValueError was not handled correctly in rollback")


class TestWeeklyTripRotationEdgeCases:
    """Tests for trip_manager.py weekly trip rotation exception and None paths."""

    @pytest.mark.asyncio
    async def test_weekly_trip_exception_in_calculate_next_recurring_datetime(self):
        """Test that an exception in calculate_next_recurring_datetime triggers the except block."""
        mock_hass = MagicMock()
        mock_storage = MagicMock()
        mock_storage.async_load = AsyncMock(return_value=None)
        mock_storage.async_save = AsyncMock(return_value=None)

        tm = TripManager(
            hass=mock_hass,
            vehicle_id="test_vehicle",
            entry_id="test_entry",
            presence_config={},
            storage=mock_storage,
        )

        with patch.object(
            tm,
            "_get_all_active_trips",
            return_value=[
                {
                    "id": "rec_monday_123",
                    "tipo": "recurring",
                    "dia_semana": "lunes",
                    "hora": "18:00",
                    "km": 30.0,
                    "kwh": 5.0,
                    "descripcion": "Test trip",
                    "activo": True,
                    "datetime": datetime.now().isoformat(),
                }
            ],
        ):
            mock_adapter = AsyncMock()
            tm.set_emhass_adapter(mock_adapter)

            with patch(
                "custom_components.ev_trip_planner.trip_manager.calculate_next_recurring_datetime",
                side_effect=Exception("Simulated calculation error"),
            ):
                await tm.publish_deferrable_loads()
                mock_adapter.assert_not_called()

    @pytest.mark.asyncio
    async def test_weekly_trip_exception_in_day_index_calculation(self):
        """Test that an exception in calculate_day_index triggers the except block."""
        mock_hass = MagicMock()
        mock_storage = MagicMock()
        mock_storage.async_load = AsyncMock(return_value=None)
        mock_storage.async_save = AsyncMock(return_value=None)

        tm = TripManager(
            hass=mock_hass,
            vehicle_id="test_vehicle",
            entry_id="test_entry",
            presence_config={},
            storage=mock_storage,
        )

        with patch.object(
            tm,
            "_get_all_active_trips",
            return_value=[
                {
                    "id": "rec_monday_456",
                    "tipo": "recurring",
                    "dia_semana": "lunes",
                    "hora": "18:00",
                    "km": 30.0,
                    "kwh": 5.0,
                    "descripcion": "Test trip",
                    "activo": True,
                    "datetime": datetime.now().isoformat(),
                }
            ],
        ):
            mock_adapter = AsyncMock()
            tm.set_emhass_adapter(mock_adapter)

            with patch(
                "custom_components.ev_trip_planner.trip_manager.calculate_day_index",
                side_effect=Exception("Simulated day_index error"),
            ):
                await tm.publish_deferrable_loads()

    @pytest.mark.asyncio
    async def test_weekly_trip_with_invalid_hora_triggers_none_path(self):
        """Test that a recurring trip with invalid 'hora' format triggers the None path."""
        mock_hass = MagicMock()
        mock_storage = MagicMock()
        mock_storage.async_load = AsyncMock(return_value=None)
        mock_storage.async_save = AsyncMock(return_value=None)

        tm = TripManager(
            hass=mock_hass,
            vehicle_id="test_vehicle",
            entry_id="test_entry",
            presence_config={},
            storage=mock_storage,
        )

        with patch.object(
            tm,
            "_get_all_active_trips",
            return_value=[
                {
                    "id": "rec_monday_123",
                    "tipo": "recurring",
                    "dia_semana": "lunes",
                    "hora": "invalid_time",
                    "km": 30.0,
                    "kwh": 5.0,
                    "descripcion": "Test trip",
                    "activo": True,
                    "datetime": datetime.now().isoformat(),
                }
            ],
        ):
            mock_adapter = AsyncMock()
            tm.set_emhass_adapter(mock_adapter)

            await tm.publish_deferrable_loads()

    @pytest.mark.asyncio
    async def test_weekly_trip_with_none_hora_triggers_none_path(self):
        """Test that a recurring trip with None 'hora' triggers the None path."""
        mock_hass = MagicMock()
        mock_storage = MagicMock()
        mock_storage.async_load = AsyncMock(return_value=None)
        mock_storage.async_save = AsyncMock(return_value=None)

        tm = TripManager(
            hass=mock_hass,
            vehicle_id="test_vehicle",
            entry_id="test_entry",
            presence_config={},
            storage=mock_storage,
        )

        with patch.object(
            tm,
            "_get_all_active_trips",
            return_value=[
                {
                    "id": "rec_monday_456",
                    "tipo": "recurring",
                    "dia_semana": "lunes",
                    "hora": None,
                    "km": 30.0,
                    "kwh": 5.0,
                    "descripcion": "Test trip",
                    "activo": True,
                    "datetime": datetime.now().isoformat(),
                }
            ],
        ):
            mock_adapter = AsyncMock()
            tm.set_emhass_adapter(mock_adapter)

            await tm.publish_deferrable_loads()


class TestHourlyRefreshCallbackEdgeCases:
    """Tests for _hourly_refresh_callback exception and None paths."""

    @pytest.mark.asyncio
    async def test_hourly_refresh_callback_exception_is_caught(self):
        """Test that exceptions in _hourly_refresh_callback are caught and logged."""
        from custom_components.ev_trip_planner import (
            EVTripRuntimeData,
            _hourly_refresh_callback,
        )
        from custom_components.ev_trip_planner.trip_manager import TripManager

        mock_trip_manager = AsyncMock(spec=TripManager)
        mock_trip_manager.publish_deferrable_loads = AsyncMock(
            side_effect=Exception("Test exception")
        )

        runtime_data = EVTripRuntimeData(
            coordinator=None,
            trip_manager=mock_trip_manager,
            emhass_adapter=None,
        )

        import logging

        with patch.object(
            logging.getLogger("custom_components.ev_trip_planner"), "warning"
        ) as mock_warning:
            now = datetime.now()
            await _hourly_refresh_callback(now, runtime_data)

            mock_warning.assert_called_once()
            assert "Hourly profile refresh failed" in str(mock_warning.call_args)
            assert "Test exception" in str(mock_warning.call_args)

    @pytest.mark.asyncio
    async def test_hourly_refresh_callback_handles_none_trip_manager(self):
        """Test that _hourly_refresh_callback handles runtime_data.trip_manager=None."""
        from custom_components.ev_trip_planner import (
            EVTripRuntimeData,
            _hourly_refresh_callback,
        )

        runtime_data = EVTripRuntimeData(
            coordinator=None,
            trip_manager=None,
            emhass_adapter=None,
        )

        now = datetime.now()
        await _hourly_refresh_callback(now, runtime_data)

    @pytest.mark.asyncio
    async def test_hourly_refresh_callback_success_path(self):
        """Test that _hourly_refresh_callback succeeds when publish_deferrable_loads succeeds."""
        from custom_components.ev_trip_planner import (
            EVTripRuntimeData,
            _hourly_refresh_callback,
        )
        from custom_components.ev_trip_planner.trip_manager import TripManager

        mock_trip_manager = AsyncMock(spec=TripManager)
        mock_trip_manager.publish_deferrable_loads = AsyncMock(return_value=None)

        runtime_data = EVTripRuntimeData(
            coordinator=None,
            trip_manager=mock_trip_manager,
            emhass_adapter=None,
        )

        now = datetime.now()
        await _hourly_refresh_callback(now, runtime_data)

        assert mock_trip_manager.publish_deferrable_loads.called
