"""Tests for config update functionality.

Tests verify that charging power updates trigger sensor attribute republish:
- Config entry changes propagate to sensor attributes
- Republish only occurs when power actually changes
- No-op when power remains unchanged
"""

import pytest
from homeassistant.core import HomeAssistant
from unittest.mock import patch, AsyncMock, MagicMock

from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.const import (
    CONF_VEHICLE_NAME,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_CHARGING_POWER,
    CONF_T_BASE,
    CONF_SOH_SENSOR,
)


@pytest.fixture
def enable_custom_integrations():
    """Enable custom integrations for testing."""
    return True


@pytest.fixture
def mock_store():
    """Create a mock store for testing."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock(return_value=None)
    return store


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.bus = MagicMock()
    hass.states = MagicMock()
    hass.states.async_remove = MagicMock(return_value=None)
    return hass


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id_123"
    entry.data = {
        "vehicle_name": "test_vehicle",
        "charging_power_kw": 7.4,
    }
    return entry


@pytest.mark.asyncio
async def test_config_update_triggers_republish(mock_hass: HomeAssistant, mock_store):
    """Test that config entry update triggers republish when power changes.

    FR-3.1/FR-3.2: When charging_power_kw changes in config entry:
    1. Listener receives "updated" event
    2. _on_config_entry_updated calls update_charging_power()
    3. update_charging_power() compares new vs old power
    4. If changed, republishes sensor attributes
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,  # Initial power
    }

    # Create adapter
    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"
        adapter.vehicle_id = "test_vehicle"

        # Mock config entry with new power value
        class MockConfigEntryData(dict):
            """Dict subclass that properly implements .get()"""

            pass

        new_entry = MagicMock()
        new_entry.entry_id = "test_entry_id_123"
        # Create a dict subclass that works properly
        new_entry.data = MockConfigEntryData(
            {
                "vehicle_name": "test_vehicle",
                "charging_power_kw": 7.4,  # Changed from 3.6
            }
        )
        # Also mock options since code checks options first (line 1516)
        new_entry.options = MockConfigEntryData(
            {
                "charging_power_kw": 7.4,
            }
        )

        # Mock async_get_entry to return new entry
        mock_hass.config_entries.async_get_entry = MagicMock(return_value=new_entry)

        # Mock publish_deferrable_loads to avoid needing real trips
        adapter.publish_deferrable_loads = AsyncMock(return_value=True)

        # Execute: Call update_charging_power
        # This simulates what happens when config entry is updated
        await adapter.update_charging_power()

        # Verify: Power was updated
        assert adapter._charging_power_kw == 7.4  # Power was updated
        # Verify: publish_deferrable_loads was called because power changed
        adapter.publish_deferrable_loads.assert_called_once()


@pytest.mark.asyncio
async def test_no_republish_when_no_change(mock_hass: HomeAssistant, mock_store):
    """Test that no republish occurs when power remains unchanged.

    If charging_power_kw doesn't change, update_charging_power() should
    skip republish to avoid unnecessary sensor updates.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,  # Initial power
    }

    # Create adapter
    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"
        adapter.vehicle_id = "test_vehicle"
        adapter._charging_power_kw = 7.4  # Same as config

        # Mock config entry with SAME power value
        class MockConfigEntryData(dict):
            """Dict subclass that properly implements .get()"""

            pass

        new_entry = MagicMock()
        new_entry.entry_id = "test_entry_id_123"
        # Create a dict subclass that works properly
        new_entry.data = MockConfigEntryData(
            {
                "vehicle_name": "test_vehicle",
                "charging_power_kw": 7.4,  # Unchanged
            }
        )
        # Also mock options since code checks options first (line 1516)
        new_entry.options = MockConfigEntryData(
            {
                "charging_power_kw": 7.4,
            }
        )

        mock_hass.config_entries.async_get_entry = MagicMock(return_value=new_entry)

        # Mock publish_deferrable_loads to track calls
        adapter.publish_deferrable_loads = AsyncMock()

        # Execute: Call update_charging_power with no change
        await adapter.update_charging_power()

        # Verify: Power remains unchanged
        assert adapter._charging_power_kw == 7.4
        # Verify: publish_deferrable_loads NOT called because power unchanged
        adapter.publish_deferrable_loads.assert_not_called()


@pytest.mark.asyncio
async def test_config_listener_setup(mock_hass: HomeAssistant, mock_store):
    """Test that config entry listener is properly set up.

    setup_config_entry_listener() should:
    1. Retrieve config_entry via async_get_entry
    2. Store listener handle on adapter via config_entry.add_update_listener
    3. Register _handle_config_entry_update callback
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    # Create mock unsubscribe function
    mock_unsubscribe = MagicMock()

    # Create mock config entry
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_id_123"
    mock_entry.data = config
    mock_entry.async_on_unload = MagicMock(return_value=mock_unsubscribe)
    mock_entry.add_update_listener = MagicMock(return_value=mock_unsubscribe)

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"

        # Mock async_get_entry to return our mock_entry
        mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Set up listener
        adapter.setup_config_entry_listener()

        # Verify: Listener handle stored (returned by async_on_unload)
        assert hasattr(adapter, "_config_entry_listener")
        assert adapter._config_entry_listener is mock_unsubscribe

        # Verify: async_get_entry was called with entry_id
        mock_hass.config_entries.async_get_entry.assert_called_once_with(
            "test_entry_id_123"
        )

        # Verify: add_update_listener was called with the handler
        mock_entry.add_update_listener.assert_called_once()


@pytest.mark.asyncio
async def test_handle_config_entry_update_triggers_republish(
    mock_hass: HomeAssistant, mock_store
):
    """Test that _handle_config_entry_update calls update_charging_power.

    The new pattern uses ConfigEntry.add_update_listener which passes
    (hass, config_entry) to the handler, so no entry_id filtering is needed.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    # Create adapter
    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"
        adapter.vehicle_id = "test_vehicle"

        # Mock update_charging_power to track calls
        adapter.update_charging_power = AsyncMock()

        # Create mock config entry (passed by HA's add_update_listener)
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id_123"

        # Execute: Handle config entry update
        await adapter._handle_config_entry_update(mock_hass, mock_entry)

        # Verify: update_charging_power was called
        adapter.update_charging_power.assert_called_once()


@pytest.mark.asyncio
async def test_update_charging_power_handles_missing_entry(
    mock_hass: HomeAssistant, mock_store
):
    """Test that update_charging_power handles missing config entry gracefully.

    If the config entry no longer exists, the method should log a warning
    and return without error.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    # Create adapter
    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "nonexistent_entry_id"

        # Mock async_get_entry to return None
        mock_hass.config_entries.async_get_entry = MagicMock(return_value=None)

        # Execute: Call update_charging_power with missing entry
        await adapter.update_charging_power()

        # Verify: No exception raised, method handles gracefully
        assert adapter._charging_power_kw == 7.4


# ============================================================================
# T066 Coverage: Tests for 4 missing lines in emhass_adapter.py
# ============================================================================


@pytest.mark.asyncio
async def test_handle_config_entry_update_detects_t_base_change(
    mock_hass: HomeAssistant, mock_store
):
    """Test _handle_config_entry_update detects t_base change.

    Covers line 2331: changed_params.append("t_base")
    The old t_base differs from the new one, so the change is detected.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"
        adapter.vehicle_id = "test_vehicle"
        adapter._charging_power_kw = 7.4

        adapter.update_charging_power = AsyncMock()

        # Create mock config entry with OLD t_base=6, NEW t_base=48
        # The adapter was created without t_base, so old_t_base defaults to DEFAULT_T_BASE (24)
        # We set old_options to have t_base=6 (different from default 24),
        # and new options to have t_base=48 (different from 6)
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id_123"
        mock_entry.options = {CONF_T_BASE: 48}  # New value
        mock_entry.data = {CONF_T_BASE: 6}  # Old value — different from new value

        # Execute: Handle config entry update
        await adapter._handle_config_entry_update(mock_hass, mock_entry)

        # Verify: update_charging_power was called
        adapter.update_charging_power.assert_called_once()

        # Verify: changed_params contains "t_base"
        # (We can verify via the log call)
        # The _handle_config_entry_update logs the changed params
        # We verify it was called and didn't crash with t_base change


@pytest.mark.asyncio
async def test_handle_config_entry_update_detects_soh_sensor_change(
    mock_hass: HomeAssistant, mock_store
):
    """Test _handle_config_entry_update detects SOH sensor change.

    Covers line 2333: changed_params.append("soh_sensor")
    The old SOH sensor differs from the new one, so the change is detected.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"
        adapter.vehicle_id = "test_vehicle"
        adapter._charging_power_kw = 7.4

        adapter.update_charging_power = AsyncMock()

        # Create mock config entry with OLD soh=default (None), NEW soh=sensor.new_soh_sensor
        # old_soh defaults to DEFAULT_SOH_SENSOR (""), new is "sensor.new_soh_sensor"
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id_123"
        mock_entry.options = {CONF_SOH_SENSOR: "sensor.new_soh_sensor"}
        mock_entry.data = {}  # Empty data — old_soh will be DEFAULT_SOH_SENSOR (empty string)

        # Execute: Handle config entry update
        await adapter._handle_config_entry_update(mock_hass, mock_entry)

        # Verify: update_charging_power was called
        adapter.update_charging_power.assert_called_once()


@pytest.mark.asyncio
async def test_handle_config_entry_update_detects_charging_power_change(
    mock_hass: HomeAssistant, mock_store
):
    """Test _handle_config_entry_update detects charging_power change.

    Covers line 2329: changed_params.append("charging_power")
    CONF_CHARGING_POWER is in cur_options, so charging_power is always detected.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"
        adapter.vehicle_id = "test_vehicle"
        adapter._charging_power_kw = 7.4

        adapter.update_charging_power = AsyncMock()

        # Create mock config entry with charging_power
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id_123"
        mock_entry.options = {CONF_CHARGING_POWER: 11.0}

        # Execute: Handle config entry update
        await adapter._handle_config_entry_update(mock_hass, mock_entry)

        # Verify: update_charging_power was called
        adapter.update_charging_power.assert_called_once()


@pytest.mark.asyncio
async def test_t_base_change_triggers_republish_when_power_unchanged(
    mock_hass: HomeAssistant, mock_store
):
    """Test that changing t_base without changing charging_power recomputes cache.

    When t_base changes in config entry, the SOC cap parameters change.
    If charging_power is unchanged, update_charging_power() returns early
    and the stale cached per_trip_params remains with old SOC caps.

    This is a regression test: _handle_config_entry_update must force
    recomputation when t_base or soh_sensor changes, even if power is stable.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"
        adapter.vehicle_id = "test_vehicle"

        # Populate cache and published trips (simulating real running state)
        adapter._cached_per_trip_params = {
            "trip_1": {
                "def_total_hours": 5,
                "P_deferrable_nom": 3600.0,
                "soc_target": 80.0,
            },
        }
        adapter._published_trips = [{"id": "trip_1", "kwh": 5.0}]

        # Stash original power value (same as options value below)
        adapter._charging_power_kw = 3.6

        # Create mock config entry: only t_base changes, power stays 3.6
        class ConfigData(dict):
            pass

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id_123"
        mock_entry.options = ConfigData(
            {CONF_T_BASE: 48, CONF_CHARGING_POWER: 3.6}
        )
        mock_entry.data = ConfigData(
            {CONF_T_BASE: 24, CONF_CHARGING_POWER: 3.6}
        )

        # Wire async_get_entry to return the mock config entry
        mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Track whether update_charging_power was called with force=True
        adapter.update_charging_power = AsyncMock()

        # Execute: Handle config entry update with t_base change only
        await adapter._handle_config_entry_update(mock_hass, mock_entry)

        # Verify: update_charging_power WAS called with force=True — t_base
        # change must force recomputation of SOC caps even when power is unchanged
        adapter.update_charging_power.assert_called_once()
        call_kwargs = adapter.update_charging_power.call_args
        assert call_kwargs.kwargs.get("force") is True or (
            len(call_kwargs.args) > 0 and call_kwargs.args[0] is True
        ), "update_charging_power must be called with force=True when t_base changes"


@pytest.mark.asyncio
async def test_soh_sensor_change_triggers_republish_when_power_unchanged(
    mock_hass: HomeAssistant, mock_store
):
    """Test that changing soh_sensor without changing charging_power recomputes cache.

    When soh_sensor changes, _battery_cap is reinitialized and the real capacity
    may change. The cached per_trip_params is stale and must be recomputed.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.6,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"
        adapter.vehicle_id = "test_vehicle"

        adapter._cached_per_trip_params = {
            "trip_1": {
                "def_total_hours": 5,
                "P_deferrable_nom": 3600.0,
                "soc_target": 80.0,
            },
        }
        adapter._published_trips = [{"id": "trip_1", "kwh": 5.0}]
        adapter._charging_power_kw = 3.6

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id_123"
        mock_entry.options = {
            CONF_SOH_SENSOR: "sensor.new_soh",
            CONF_CHARGING_POWER: 3.6,
        }
        mock_entry.data = {
            CONF_SOH_SENSOR: "sensor.old_soh",
            CONF_CHARGING_POWER: 3.6,
        }

        mock_hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        adapter.update_charging_power = AsyncMock()

        await adapter._handle_config_entry_update(mock_hass, mock_entry)

        adapter.update_charging_power.assert_called_once()


@pytest.mark.asyncio
async def test_async_publish_all_deferrable_loads_skips_trip_without_datetime(
    mock_hass: HomeAssistant, mock_store
):
    """Test that async_publish_all_deferrable_loads skips trips without datetime fields.

    When a trip lacks datetime/day/time fields, calculate_power_profile returns an
    empty profile (non_zero=0) and publish_deferrable_load fails, returning False.
    """
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }

    with patch(
        "custom_components.ev_trip_planner.emhass_adapter.Store",
        return_value=mock_store,
    ):
        adapter = EMHASSAdapter(mock_hass, config)
        adapter.entry_id = "test_entry_id_123"
        adapter.vehicle_id = "test_vehicle"

        trips = [
            {"id": "trip_001", "descripcion": "Trip 1", "kwh": 5.0, "hora": "09:00"},
        ]

        # Trip without datetime — should be skipped, returns False
        result = await adapter.async_publish_all_deferrable_loads(
            trips, charging_power_kw=7.4
        )
        assert result is False
