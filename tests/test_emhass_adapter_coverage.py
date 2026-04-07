"""Coverage tests for emhass_adapter.py error paths."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_NOTIFICATION_SERVICE,
    CONF_VEHICLE_NAME,
)


class TestEmhassAdapterAsyncLoadErrorPaths:
    """Tests for emhass_adapter async_load error paths."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock store."""
        store = MagicMock()
        store.async_load = AsyncMock()
        return store

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
            CONF_NOTIFICATION_SERVICE: "notify.test",
        }

    @pytest.mark.asyncio
    async def test_async_load_handles_exception(self, mock_store, emhass_config):
        """async_load catches exception when store raises (lines 127-129)."""
        mock_store.async_load = AsyncMock(side_effect=Exception("Storage error"))

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(None, emhass_config)
            adapter.async_notify_error = AsyncMock()

            await adapter.async_load()

            # Verify error was notified
            adapter.async_notify_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_load_handles_invalid_released_indices(
        self, mock_store, emhass_config
    ):
        """async_load handles invalid released_indices format (lines 101-109)."""
        mock_store.async_load = AsyncMock(
            return_value={
                "index_map": {"trip_1": 0},
                "released_indices": {"0": "not-a-valid-iso-format"},
            }
        )

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(None, emhass_config)
            adapter.async_notify_error = AsyncMock()

            # Should not raise - invalid released_indices are skipped
            await adapter.async_load()

            # Verify index_map was loaded despite invalid released_indices
            assert adapter._index_map == {"trip_1": 0}


class TestEmhassAdapterAsyncSaveErrorPaths:
    """Tests for emhass_adapter async_save error paths."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock store."""
        store = MagicMock()
        store.async_load = AsyncMock(return_value={})
        store.async_save = AsyncMock()
        return store

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
            CONF_NOTIFICATION_SERVICE: "notify.test",
        }

    @pytest.mark.asyncio
    async def test_async_save_handles_save_error(
        self, mock_store, emhass_config
    ):
        """async_save catches exception when store.async_save raises."""
        mock_store.async_save = AsyncMock(side_effect=Exception("Save error"))

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(None, emhass_config)
            adapter._store = mock_store
            adapter._index_map = {"trip_1": 0}
            adapter._released_indices = {}

            # Should not raise - exception is caught
            await adapter.async_save()


class TestEmhassAdapterErrorNotification:
    """Tests for emhass_adapter error notification paths."""

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
            CONF_NOTIFICATION_SERVICE: "notify.test",
        }

    @pytest.mark.asyncio
    async def test_async_notify_error_handles_notification_error(
        self, emhass_config
    ):
        """async_notify_error handles when hass.services.async_call raises."""
        hass = MagicMock()

        async def mock_async_call(*args, **kwargs):
            raise Exception("Notification failed")

        hass.services.async_call = mock_async_call
        hass.bus.async_listen_once = AsyncMock()

        adapter = EMHASSAdapter(hass, emhass_config)

        # Should not raise - exception is caught
        await adapter.async_notify_error(
            error_type="test_error",
            message="Test notification",
        )

    @pytest.mark.asyncio
    async def test_async_notify_error_handles_bus_error(self, emhass_config):
        """async_notify_error handles when bus.async_listen_once raises."""
        hass = MagicMock()

        hass.services.async_call = AsyncMock()
        hass.bus.async_listen_once = AsyncMock(
            side_effect=Exception("Bus error")
        )

        adapter = EMHASSAdapter(hass, emhass_config)

        # Should not raise - exception is caught
        await adapter.async_notify_error(
            error_type="test_error",
            message="Test notification",
        )


class TestEmhassAdapterPublishErrorPaths:
    """Tests for emhass_adapter publish error paths."""

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
            CONF_NOTIFICATION_SERVICE: "notify.test",
        }

    @pytest.mark.asyncio
    async def test_async_publish_deferrable_load_handles_missing_trip_id(
        self, emhass_config
    ):
        """async_publish_deferrable_load returns False when trip has no ID."""
        hass = MagicMock()
        adapter = EMHASSAdapter(hass, emhass_config)

        # Trip without ID should return False
        result = await adapter.async_publish_deferrable_load({"kwh": 15.0})
        assert result is False

    @pytest.mark.asyncio
    async def test_async_publish_deferrable_load_handles_missing_deadline(
        self, emhass_config
    ):
        """async_publish_deferrable_load returns False when trip has no datetime."""
        hass = MagicMock()
        adapter = EMHASSAdapter(hass, emhass_config)
        adapter.async_assign_index_to_trip = AsyncMock(return_value=0)

        # Trip without datetime should return False
        result = await adapter.async_publish_deferrable_load({"id": "trip_1", "kwh": 15.0})
        assert result is False


class TestEmhassAdapterIndexErrorPaths:
    """Tests for emhass_adapter index management error paths."""

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
            CONF_NOTIFICATION_SERVICE: "notify.test",
        }

    @pytest.mark.asyncio
    async def test_async_release_trip_index_handles_missing_trip(
        self, emhass_config
    ):
        """async_release_trip_index handles when trip not in index_map."""
        hass = MagicMock()
        adapter = EMHASSAdapter(hass, emhass_config)
        adapter._index_map = {}  # trip_1 not in map
        adapter._released_indices = {}
        adapter._available_indices = [0]
        adapter.async_save_trips = AsyncMock()

        # Should return False gracefully
        result = await adapter.async_release_trip_index("nonexistent_trip")
        assert result is False


class TestEmhassAdapterOptimizationErrorPaths:
    """Tests for optimization result handling."""

    @pytest.fixture
    def emhass_config(self):
        """Create base EMHASS config."""
        return {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
            CONF_NOTIFICATION_SERVICE: "notify.test",
        }

    def test_get_cached_optimization_results_returns_correct_keys(
        self, emhass_config
    ):
        """get_cached_optimization_results returns expected keys."""
        hass = MagicMock()
        adapter = EMHASSAdapter(hass, emhass_config)

        result = adapter.get_cached_optimization_results()
        assert "emhass_power_profile" in result
        assert "emhass_deferrables_schedule" in result
        assert "emhass_status" in result
