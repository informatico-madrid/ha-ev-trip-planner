"""Edge-case tests for emhass/adapter.py to cover missing lines."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.emhass.adapter import (
    EMHASSAdapter,
    LoadPublisherConfig,
    PerTripCacheParams,
)


@pytest.fixture
def mock_entry():
    """Minimal MagicMock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_vehicle"
    entry.data = {"charging_power_kw": 3.6}
    entry.options = {}
    return entry


@pytest.fixture
def mock_hass(tmp_path):
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = str(tmp_path)
    hass.config.time_zone = "UTC"
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    yield hass


# ---------------------------------------------------------------------------
# Exception handlers in delegation methods (lines 112-114, 124-126, 132-134, 140-142)
# ---------------------------------------------------------------------------


class TestAdapterExceptionHandlers:
    """Test exception handlers in facade delegation methods."""

    @pytest.mark.asyncio
    async def test_assign_index_handles_exception(self, mock_hass, mock_entry):
        """Lines 112-114: Exception in index_manager.async_assign_index_to_trip."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._index_manager.async_assign_index_to_trip = MagicMock(
            side_effect=RuntimeError("index error")
        )
        result = await adapter.async_assign_index_to_trip("trip_001")
        assert result is None

    @pytest.mark.asyncio
    async def test_release_index_handles_exception(self, mock_hass, mock_entry):
        """Lines 124-126: Exception in index_manager.async_release_index."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._index_manager.async_release_index = MagicMock(
            side_effect=RuntimeError("release error")
        )
        result = await adapter.async_release_trip_index("trip_001")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_deferrable_load_handles_exception(self, mock_hass, mock_entry):
        """Lines 132-134: Exception in load_publisher.remove."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._load_publisher.remove = AsyncMock(
            side_effect=RuntimeError("remove error")
        )
        result = await adapter.async_remove_deferrable_load("trip_001")
        assert result is False

    @pytest.mark.asyncio
    async def test_update_deferrable_load_handles_exception(self, mock_hass, mock_entry):
        """Lines 140-142: Exception in load_publisher.update."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._load_publisher.update = AsyncMock(
            side_effect=RuntimeError("update error")
        )
        result = await adapter.async_update_deferrable_load({"id": "trip_001"})
        assert result is False


# ---------------------------------------------------------------------------
# update_charging_power edge cases (lines 191, 195, 199, 201)
# ---------------------------------------------------------------------------


class TestUpdateChargingPower:
    """Test update_charging_power early returns (lines 191, 195, 199, 201)."""

    @pytest.mark.asyncio
    async def test_shutting_down_early_return(self, mock_hass, mock_entry):
        """Line 191: _shutting_down is True -> return early."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._shutting_down = True
        await adapter.update_charging_power()
        assert adapter._charging_power_kw is None

    @pytest.mark.asyncio
    async def test_no_entry_early_return(self, mock_hass, mock_entry):
        """Line 195: config entry not found -> return early."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        mock_hass.config_entries = MagicMock()
        mock_hass.config_entries.async_get_entry = MagicMock(return_value=None)
        await adapter.update_charging_power()
        assert adapter._charging_power_kw is None

    @pytest.mark.asyncio
    async def test_no_power_in_options_or_data(self, mock_hass, mock_entry):
        """Line 199/201: no charging_power_kw in options or data -> return early."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        mock_entry.options = {}
        mock_entry.data = {}
        mock_hass.config_entries = MagicMock()
        mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        await adapter.update_charging_power()
        assert adapter._charging_power_kw is None

    @pytest.mark.asyncio
    async def test_update_charging_power_success(self, mock_hass, mock_entry):
        """Normal path: power value found and different -> updates stored power."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        mock_entry.data = {"charging_power_kw": 7.0}
        mock_entry.options = {}
        mock_hass.config_entries = MagicMock()
        mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        await adapter.update_charging_power()
        assert adapter._charging_power_kw == 7.0
        assert adapter._stored_charging_power_kw == 7.0

    @pytest.mark.asyncio
    async def test_update_charging_power_from_options(self, mock_hass, mock_entry):
        """Options takes priority over data for charging_power_kw."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        mock_entry.data = {"charging_power_kw": 3.6}
        mock_entry.options = {"charging_power_kw": 11.0}
        mock_hass.config_entries = MagicMock()
        mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        await adapter.update_charging_power()
        assert adapter._charging_power_kw == 11.0

    @pytest.mark.asyncio
    async def test_update_charging_power_no_change(self, mock_hass, mock_entry):
        """New power same as stored -> no update."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._charging_power_kw = 7.0
        mock_entry.data = {"charging_power_kw": 7.0}
        mock_entry.options = {}
        mock_hass.config_entries = MagicMock()
        mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        await adapter.update_charging_power()
        assert adapter._charging_power_kw == 7.0


# ---------------------------------------------------------------------------
# setup_config_entry_listener early return (line 213)
# ---------------------------------------------------------------------------


class TestSetupConfigEntryListener:
    """Test setup_config_entry_listener (line 213)."""

    def test_listener_no_entry_returns_early(self):
        """Line 213: No config entry found -> return early."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_vehicle"
        entry.data = {}
        entry.options = {}
        hass.config_entries = MagicMock()
        hass.config_entries.async_get_entry = MagicMock(return_value=None)
        adapter = EMHASSAdapter(hass=hass, entry=entry)
        adapter.setup_config_entry_listener()
        assert adapter._config_entry_listener is None

    def test_listener_with_entry_sets_up(self, mock_hass, mock_entry):
        """Normal path: entry found -> sets up config entry listener."""
        mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        mock_entry.async_on_unload = MagicMock(return_value="listener_ref")
        mock_entry.add_update_listener = MagicMock(return_value="update_callback")
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter.setup_config_entry_listener()
        assert adapter._config_entry_listener == "listener_ref"


# ---------------------------------------------------------------------------
# _get_current_soc edge cases (lines 313, 319-320)
# ---------------------------------------------------------------------------


class TestGetCurrentSoc:
    """Test _get_current_soc edge cases."""

    @pytest.mark.asyncio
    async def test_no_entry_dict(self, mock_hass, mock_entry):
        """Line 307: no _entry_dict -> returns None."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        # _entry_dict not set
        result = await adapter._get_current_soc()
        assert result is None

    @pytest.mark.asyncio
    async def test_no_soc_sensor(self, mock_hass, mock_entry):
        """Line 313: soc_sensor not in entry_data -> returns None."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._entry_dict = {}  # no soc_sensor key
        result = await adapter._get_current_soc()
        assert result is None

    @pytest.mark.asyncio
    async def test_soc_state_non_numeric(self, mock_hass, mock_entry):
        """Lines 319-320: float(state.state) raises ValueError -> returns None."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._entry_dict = {"soc_sensor": "sensor.battery"}
        state_obj = MagicMock()
        state_obj.state = "unavailable"  # not a valid float
        mock_hass.states.get = MagicMock(return_value=state_obj)
        result = await adapter._get_current_soc()
        assert result is None

    @pytest.mark.asyncio
    async def test_soc_state_none_state(self, mock_hass, mock_entry):
        """Lines 319-320: state.state is None -> TypeError -> returns None."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._entry_dict = {"soc_sensor": "sensor.battery"}
        state_obj = MagicMock()
        state_obj.state = None
        mock_hass.states.get = MagicMock(return_value=state_obj)
        result = await adapter._get_current_soc()
        assert result is None


# ---------------------------------------------------------------------------
# _populate_per_trip_cache_entry with pre-computed windows (lines 398-402, 412-416)
# ---------------------------------------------------------------------------


class TestPopulateCacheWithPreComputedWindows:
    """Test _populate_per_trip_cache_entry with pre-computed windows."""

    @pytest.mark.asyncio
    async def test_populate_cache_with_pre_computed_inicio(self, mock_hass, mock_entry):
        """Lines 398-402: pre_computed_inicio_ventana sets def_start_timestep."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._index_map = {}  # avoid assign_index in _populate
        future = datetime.now(timezone.utc) + timedelta(hours=4)

        params = PerTripCacheParams(
            trip={"id": "trip_001", "kwh": 10.0},
            trip_id="trip_001",
            charging_power_kw=3.6,
            battery_capacity_kwh=75.0,
            safety_margin_percent=10,
            soc_current=50.0,
        )
        await adapter._populate_per_trip_cache_entry(
            params,
            pre_computed_inicio_ventana=future,
        )
        # def_start_timestep should be set based on the pre-computed value
        cached = adapter._cached_per_trip_params["trip_001"]
        assert cached["def_start_timestep"] >= 0
        assert cached["def_start_timestep"] <= 168

    @pytest.mark.asyncio
    async def test_populate_cache_with_pre_computed_fin(self, mock_hass, mock_entry):
        """Lines 412-416: pre_computed_fin_ventana adjusts def_end_timestep."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._index_map = {}
        future = datetime.now(timezone.utc) + timedelta(hours=6)

        params = PerTripCacheParams(
            trip={"id": "trip_002", "kwh": 10.0},
            trip_id="trip_002",
            charging_power_kw=3.6,
            battery_capacity_kwh=75.0,
            safety_margin_percent=10,
            soc_current=50.0,
        )
        await adapter._populate_per_trip_cache_entry(
            params,
            pre_computed_fin_ventana=future,
        )
        cached = adapter._cached_per_trip_params["trip_002"]
        assert cached["def_end_timestep"] >= 0
        assert cached["def_end_timestep"] <= 168


# ---------------------------------------------------------------------------
# Cache population exception in async_publish_deferrable_load (lines 488-490)
# ---------------------------------------------------------------------------


class TestCachePopulationException:
    """Test cache population exception handler."""

    @pytest.mark.asyncio
    async def test_cache_populate_failure_does_not_block_publish(self, mock_hass, mock_entry):
        """Lines 488-490: Exception during cache population -> caught, publish proceeds."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)

        mock_load_pub = MagicMock()
        mock_load_pub.publish = AsyncMock(return_value=True)
        mock_load_pub.battery_capacity_kwh = 75.0
        mock_load_pub.safety_margin_percent = 10
        adapter._load_publisher = mock_load_pub

        with patch.object(
            adapter,
            "_populate_per_trip_cache_entry",
            side_effect=RuntimeError("cache error"),
        ):
            trip = {
                "id": "trip_cache_err",
                "kwh": 10.0,
                "datetime": (
                    datetime.now(timezone.utc) + timedelta(hours=2)
                ).isoformat(),
            }
            result = await adapter.async_publish_deferrable_load(trip)
            # Should still succeed -- cache exception is swallowed
            assert result is True
            mock_load_pub.publish.assert_called_once()
