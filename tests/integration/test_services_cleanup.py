"""Tests for services/cleanup.py — full coverage of cleanup functions."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from custom_components.ev_trip_planner.services import cleanup


class _MockPath:
    """Mock Path that supports chaining via / operator and instance-patching.

    Usage:
        mp = _MockPath(yaml_path_mock)
        path = Path("/config") / "a" / "b"   # returns yaml_path_mock
    """

    def __init__(self, result):
        self._result = result

    def __call__(self, *args, **kwargs):
        """Allow instance to be called when used as patch for Path()."""
        return self

    def __truediv__(self, other):
        return self

    def exists(self):
        return self._result.exists()

    def unlink(self):
        self._result.unlink()

    def read_text(self):
        return self._result.read_text()

    def __fspath__(self):
        return "/tmp/test"


# --- async_cleanup_stale_storage ---


@pytest.mark.asyncio
async def test_cleanup_stale_storage_yaml_no_store_data(tmp_path):
    """YAML exists, Store is empty → YAML should be deleted."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=None)

    yaml_path = MagicMock(spec=Path)
    yaml_path.exists.return_value = True
    yaml_path.__truediv__ = MagicMock(side_effect=lambda x: yaml_path)

    with patch.object(
        cleanup, "ha_storage", Mock(Store=MagicMock(return_value=mock_store))
    ):
        with patch.object(cleanup, "Path", _MockPath(yaml_path)):
            await cleanup.async_cleanup_stale_storage(hass, "test_vehicle")

    yaml_path.unlink.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_stale_storage_yaml_with_store_data(tmp_path):
    """YAML exists, Store has data → skip YAML cleanup."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value={"key": "value"})

    yaml_path = MagicMock(spec=Path)
    yaml_path.exists.return_value = True

    with patch.object(
        cleanup, "ha_storage", Mock(Store=MagicMock(return_value=mock_store))
    ):
        with patch.object(cleanup, "Path", _MockPath(yaml_path)):
            await cleanup.async_cleanup_stale_storage(hass, "test_vehicle")

    yaml_path.unlink.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_stale_storage_yaml_not_exists(tmp_path):
    """YAML does not exist → nothing to clean."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    yaml_path = MagicMock(spec=Path)
    yaml_path.exists.return_value = False

    with patch.object(cleanup, "ha_storage", Mock(Store=MagicMock())):
        with patch.object(cleanup, "Path", _MockPath(yaml_path)):
            await cleanup.async_cleanup_stale_storage(hass, "test_vehicle")

    yaml_path.unlink.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_stale_storage_exception(tmp_path):
    """Exception in cleanup → warning logged, no re-raise."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    yaml_path = MagicMock(spec=Path)
    yaml_path.exists.side_effect = OSError("disk error")

    with patch.object(cleanup, "Path", _MockPath(yaml_path)):
        await cleanup.async_cleanup_stale_storage(hass, "test_vehicle")


# --- async_cleanup_orphaned_emhass_sensors ---


@pytest.mark.asyncio
async def test_cleanup_orphaned_emhass_sensors_success():
    """Normal path: iterates entries, calls registry helpers."""
    hass = type("Hass", (), {})()
    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_1"

    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[mock_entry])

    mock_registry = MagicMock()
    mock_registry.async_entries_for_config_entry = MagicMock(return_value=[MagicMock()])

    with patch.object(
        cleanup,
        "er",
        Mock(
            async_get=MagicMock(return_value=mock_registry),
            async_entries_for_config_entry=mock_registry.async_entries_for_config_entry,
        ),
    ):
        await cleanup.async_cleanup_orphaned_emhass_sensors(hass)

    mock_registry.async_entries_for_config_entry.assert_called()


@pytest.mark.asyncio
async def test_cleanup_orphaned_emhass_sensors_exception():
    """Exception during cleanup → debug logged, no re-raise."""
    hass = type("Hass", (), {})()
    hass.config_entries = MagicMock()

    with patch.object(
        cleanup,
        "er",
        Mock(
            async_get=MagicMock(side_effect=RuntimeError("registry error")),
        ),
    ):
        await cleanup.async_cleanup_orphaned_emhass_sensors(hass)


# --- async_unload_entry_cleanup ---


@pytest.mark.asyncio
async def test_unload_entry_cleanup_no_runtime_data():
    """No runtime_data → skips trip manager and emhass_adapter paths."""
    hass = MagicMock()
    entry = MagicMock()
    entry.runtime_data = None
    entry.entry_id = "entry_1"
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    with patch(
        "custom_components.ev_trip_planner.panel.async_unregister_panel",
        side_effect=ImportError("no panel"),
    ):
        result = await cleanup.async_unload_entry_cleanup(
            hass, entry, "vehicle_1", "Vehicle 1"
        )

    assert result is True
    hass.config_entries.async_unload_platforms.assert_called_once()


@pytest.mark.asyncio
async def test_unload_entry_cleanup_with_trip_manager():
    """Has trip_manager → deletes all trips."""
    hass = MagicMock()
    trip_manager = MagicMock()
    # New composition: lifecycle methods are on _lifecycle sub-object
    trip_manager._lifecycle = MagicMock()
    trip_manager._lifecycle.async_delete_all_trips = AsyncMock()

    runtime_data = MagicMock()
    runtime_data.trip_manager = trip_manager

    entry = MagicMock()
    entry.runtime_data = runtime_data
    entry.entry_id = "entry_1"

    emhass_adapter = MagicMock()
    emhass_adapter._config_entry_listener = None
    emhass_adapter.async_cleanup_vehicle_indices = AsyncMock()
    runtime_data.emhass_adapter = emhass_adapter

    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    with patch(
        "custom_components.ev_trip_planner.panel.async_unregister_panel",
        side_effect=ImportError("no panel"),
    ):
        result = await cleanup.async_unload_entry_cleanup(
            hass, entry, "vehicle_1", "Vehicle 1"
        )

    assert result is True
    trip_manager._lifecycle.async_delete_all_trips.assert_called_once()


@pytest.mark.asyncio
async def test_unload_entry_cleanup_with_emhass_listener():
    """Has emhass_adapter with listener → removes listener and cleans up indices."""
    hass = MagicMock()

    call_count = [0]

    def mock_listener():
        call_count[0] += 1

    emhass_adapter = MagicMock()
    emhass_adapter._config_entry_listener = mock_listener
    emhass_adapter.async_cleanup_vehicle_indices = AsyncMock()

    runtime_data = MagicMock()
    runtime_data.trip_manager = None
    runtime_data.emhass_adapter = emhass_adapter

    entry = MagicMock()
    entry.runtime_data = runtime_data
    entry.entry_id = "entry_1"

    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    with patch(
        "custom_components.ev_trip_planner.panel.async_unregister_panel",
        side_effect=ImportError("no panel"),
    ):
        result = await cleanup.async_unload_entry_cleanup(
            hass, entry, "vehicle_1", "Vehicle 1"
        )

    assert result is True
    assert call_count[0] == 1
    emhass_adapter.async_cleanup_vehicle_indices.assert_called_once()


@pytest.mark.asyncio
async def test_unload_entry_cleanup_entity_registry():
    """Entity registry cleanup path via hass.entity_registry."""
    hass = type("Hass", (), {})()
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    mock_entity_entry = MagicMock()
    mock_entity_entry.entity_id = "sensor.test_vehicle_sensor"

    mock_registry = MagicMock()
    mock_registry.async_remove = MagicMock()
    hass.entity_registry = mock_registry

    entry = MagicMock()
    entry.runtime_data = None
    entry.entry_id = "entry_1"

    with patch(
        "custom_components.ev_trip_planner.services.cleanup.er.async_entries_for_config_entry",
        return_value=[mock_entity_entry],
    ):
        with patch(
            "custom_components.ev_trip_planner.panel.async_unregister_panel",
            side_effect=ImportError("no panel"),
        ):
            await cleanup.async_unload_entry_cleanup(
                hass, entry, "vehicle_1", "Vehicle 1"
            )

    mock_registry.async_remove.assert_called_once_with("sensor.test_vehicle_sensor")


@pytest.mark.asyncio
async def test_unload_entry_cleanup_entity_registry_fallback():
    """Entity registry on hass is None → fallback to er.async_get."""
    hass = type("Hass", (), {})()
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    mock_entity_entry = MagicMock()
    mock_entity_entry.entity_id = "sensor.test_sensor"

    mock_registry = MagicMock()
    mock_registry.async_remove = MagicMock()

    entry = MagicMock()
    entry.runtime_data = None
    entry.entry_id = "entry_1"

    with patch(
        "homeassistant.helpers.entity_registry.async_get", return_value=mock_registry
    ):
        with patch(
            "custom_components.ev_trip_planner.services.cleanup.er.async_entries_for_config_entry",
            return_value=[mock_entity_entry],
        ):
            with patch(
                "custom_components.ev_trip_planner.panel.async_unregister_panel",
                side_effect=ImportError("no panel"),
            ):
                await cleanup.async_unload_entry_cleanup(
                    hass, entry, "vehicle_1", "Vehicle 1"
                )

    mock_registry.async_remove.assert_called_once()


@pytest.mark.asyncio
async def test_unload_entry_cleanup_entity_registry_normal():
    """Entity registry cleanup with normal entity listing."""
    hass = MagicMock()
    entry = MagicMock()
    entry.runtime_data = None
    entry.entry_id = "entry_1"
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    mock_registry = MagicMock()
    mock_registry.async_entries_for_config_entry = MagicMock(
        side_effect=RuntimeError("registry error")
    )
    hass.entity_registry = mock_registry

    with patch(
        "custom_components.ev_trip_planner.panel.async_unregister_panel",
        side_effect=ImportError("no panel"),
    ):
        result = await cleanup.async_unload_entry_cleanup(
            hass, entry, "vehicle_1", "Vehicle 1"
        )

    assert result is True


@pytest.mark.asyncio
async def test_unload_entry_cleanup_panel_error():
    """Panel unregistration fails gracefully."""
    hass = MagicMock()
    entry = MagicMock()
    entry.runtime_data = None
    entry.entry_id = "entry_1"
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    mock_registry = MagicMock()
    mock_registry.async_entries_for_config_entry = MagicMock(return_value=[])
    mock_registry.async_remove = MagicMock()
    hass.entity_registry = mock_registry

    with patch(
        "custom_components.ev_trip_planner.panel.async_unregister_panel",
        side_effect=RuntimeError("panel error"),
    ):
        result = await cleanup.async_unload_entry_cleanup(
            hass, entry, "vehicle_1", "Vehicle 1"
        )

    assert result is True


# --- async_remove_entry_cleanup ---


@pytest.mark.asyncio
async def test_remove_entry_cleanup_with_data(tmp_path):
    """Normal path with entry data containing vehicle_name."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    mock_trip_manager = MagicMock()
    mock_trip_manager._lifecycle = MagicMock()
    mock_trip_manager._lifecycle.async_delete_all_trips = AsyncMock()

    mock_emhass = MagicMock()
    mock_emhass.async_cleanup_vehicle_indices = AsyncMock()
    mock_emhass._config_entry_listener = None

    mock_runtime = MagicMock()
    mock_runtime.trip_manager = mock_trip_manager
    mock_runtime.emhass_adapter = mock_emhass

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_abc"
    mock_entry.data = {"vehicle_name": "Test Vehicle"}
    mock_entry.runtime_data = mock_runtime

    mock_store = MagicMock()
    mock_store.async_remove = AsyncMock()

    yaml_path = MagicMock(spec=Path)
    yaml_path.exists.return_value = False

    with patch.object(
        cleanup, "ha_storage", Mock(Store=MagicMock(return_value=mock_store))
    ):
        with patch.object(cleanup, "Path", _MockPath(yaml_path)):
            await cleanup.async_remove_entry_cleanup(hass, mock_entry)

    mock_trip_manager._lifecycle.async_delete_all_trips.assert_called_once()
    mock_emhass.async_cleanup_vehicle_indices.assert_called_once()
    mock_store.async_remove.assert_called_once()


@pytest.mark.asyncio
async def test_remove_entry_cleanup_no_data(tmp_path):
    """Entry with None data → derives vehicle_id from entry_id."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_abc"
    mock_entry.data = None

    mock_store = MagicMock()
    mock_store.async_remove = AsyncMock()

    yaml_path = MagicMock(spec=Path)
    yaml_path.exists.return_value = False

    with patch.object(
        cleanup, "ha_storage", Mock(Store=MagicMock(return_value=mock_store))
    ):
        with patch.object(cleanup, "Path", _MockPath(yaml_path)):
            await cleanup.async_remove_entry_cleanup(hass, mock_entry)

    mock_store.async_remove.assert_called_once()


@pytest.mark.asyncio
async def test_remove_entry_cleanup_yaml_cleanup(tmp_path):
    """YAML fallback file exists → should be deleted."""
    # Use a plain object to avoid MagicMock auto-attributes
    hass = type("Hass", (), {})()
    hass.config = type("Config", (), {"config_dir": str(tmp_path)})()

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_abc"
    mock_entry.data = {"vehicle_name": "Test Vehicle"}
    mock_entry.runtime_data = None

    mock_store = MagicMock()
    mock_store.async_remove = AsyncMock()

    yaml_path = MagicMock()
    yaml_path.exists.return_value = True

    with patch.object(
        cleanup, "ha_storage", Mock(Store=MagicMock(return_value=mock_store))
    ):
        with patch.object(cleanup, "Path", _MockPath(yaml_path)):
            await cleanup.async_remove_entry_cleanup(hass, mock_entry)

    yaml_path.unlink.assert_called_once()


@pytest.mark.asyncio
async def test_remove_entry_cleanup_storage_error(tmp_path):
    """Storage removal fails → warning logged, no re-raise."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_abc"
    mock_entry.data = {"vehicle_name": "Test Vehicle"}
    mock_entry.runtime_data = None

    mock_store = MagicMock()
    mock_store.async_remove = AsyncMock(side_effect=RuntimeError("storage gone"))

    yaml_path = MagicMock(spec=Path)
    yaml_path.exists.return_value = False

    with patch.object(
        cleanup, "ha_storage", Mock(Store=MagicMock(return_value=mock_store))
    ):
        with patch.object(cleanup, "Path", _MockPath(yaml_path)):
            await cleanup.async_remove_entry_cleanup(hass, mock_entry)


@pytest.mark.asyncio
async def test_remove_entry_cleanup_listener_exception(tmp_path):
    """Emhass adapter listener raises exception during cleanup."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_abc"
    mock_entry.data = {"vehicle_name": "Test Vehicle"}
    mock_entry.runtime_data = None

    mock_emhass = MagicMock()
    mock_emhass._config_entry_listener = Mock(
        side_effect=RuntimeError("listener error")
    )

    mock_runtime = MagicMock()
    mock_runtime.trip_manager = None
    mock_runtime.emhass_adapter = mock_emhass
    mock_entry.runtime_data = mock_runtime

    mock_store = MagicMock()
    mock_store.async_remove = AsyncMock()

    yaml_path = MagicMock(spec=Path)
    yaml_path.exists.return_value = False

    with patch.object(
        cleanup, "ha_storage", Mock(Store=MagicMock(return_value=mock_store))
    ):
        with patch.object(cleanup, "Path", _MockPath(yaml_path)):
            await cleanup.async_remove_entry_cleanup(hass, mock_entry)


@pytest.mark.asyncio
async def test_remove_entry_cleanup_trips_delete_error(tmp_path):
    """Trip deletion raises → error logged, no re-raise."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    mock_trip_manager = MagicMock()
    mock_trip_manager._lifecycle = MagicMock()
    mock_trip_manager._lifecycle.async_delete_all_trips = AsyncMock(
        side_effect=RuntimeError("delete failed")
    )

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_abc"
    mock_entry.data = {"vehicle_name": "Test Vehicle"}

    mock_runtime = MagicMock()
    mock_runtime.trip_manager = mock_trip_manager
    mock_runtime.emhass_adapter = None
    mock_entry.runtime_data = mock_runtime

    mock_store = MagicMock()
    mock_store.async_remove = AsyncMock()

    yaml_path = MagicMock(spec=Path)
    yaml_path.exists.return_value = False

    with patch.object(
        cleanup, "ha_storage", Mock(Store=MagicMock(return_value=mock_store))
    ):
        with patch.object(cleanup, "Path", _MockPath(yaml_path)):
            await cleanup.async_remove_entry_cleanup(hass, mock_entry)


@pytest.mark.asyncio
async def test_remove_entry_cleanup_emhass_cleanup_error(tmp_path):
    """EMHASS index cleanup raises → error logged, no re-raise."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    mock_emhass = MagicMock()
    mock_emhass.async_cleanup_vehicle_indices = AsyncMock(
        side_effect=RuntimeError("index cleanup failed")
    )
    mock_emhass._config_entry_listener = None

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_abc"
    mock_entry.data = {"vehicle_name": "Test Vehicle"}

    mock_runtime = MagicMock()
    mock_runtime.trip_manager = None
    mock_runtime.emhass_adapter = mock_emhass
    mock_entry.runtime_data = mock_runtime

    mock_store = MagicMock()
    mock_store.async_remove = AsyncMock()

    yaml_path = MagicMock(spec=Path)
    yaml_path.exists.return_value = False

    with patch.object(
        cleanup, "ha_storage", Mock(Store=MagicMock(return_value=mock_store))
    ):
        with patch.object(cleanup, "Path", _MockPath(yaml_path)):
            await cleanup.async_remove_entry_cleanup(hass, mock_entry)


@pytest.mark.asyncio
async def test_remove_entry_cleanup_yaml_error(tmp_path):
    """YAML cleanup raises → warning logged, no re-raise."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_abc"
    mock_entry.data = {"vehicle_name": "Test Vehicle"}
    mock_entry.runtime_data = None

    mock_store = MagicMock()
    mock_store.async_remove = AsyncMock()

    yaml_path = MagicMock(spec=Path)
    yaml_path.exists.return_value = True
    yaml_path.unlink.side_effect = OSError("permission denied")

    with patch.object(
        cleanup, "ha_storage", Mock(Store=MagicMock(return_value=mock_store))
    ):
        with patch.object(cleanup, "Path", _MockPath(yaml_path)):
            await cleanup.async_remove_entry_cleanup(hass, mock_entry)


@pytest.mark.asyncio
async def test_remove_entry_cleanup_no_emhass_no_trips(tmp_path):
    """No emhass adapter, no trip manager → minimal path."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_abc"
    mock_entry.data = {"vehicle_name": "Test Vehicle"}

    mock_runtime = MagicMock()
    mock_runtime.trip_manager = None
    mock_runtime.emhass_adapter = None
    mock_entry.runtime_data = mock_runtime

    mock_store = MagicMock()
    mock_store.async_remove = AsyncMock()

    yaml_path = MagicMock(spec=Path)
    yaml_path.exists.return_value = False

    with patch.object(
        cleanup, "ha_storage", Mock(Store=MagicMock(return_value=mock_store))
    ):
        with patch.object(cleanup, "Path", _MockPath(yaml_path)):
            await cleanup.async_remove_entry_cleanup(hass, mock_entry)

    mock_store.async_remove.assert_called_once()


@pytest.mark.asyncio
async def test_remove_entry_cleanup_listener_removed_in_finally(tmp_path):
    """Listener is set to None even after exception."""
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_abc"
    mock_entry.data = {"vehicle_name": "Test Vehicle"}

    mock_emhass = MagicMock()
    mock_emhass._config_entry_listener = Mock(
        side_effect=RuntimeError("listener error")
    )

    mock_runtime = MagicMock()
    mock_runtime.trip_manager = None
    mock_runtime.emhass_adapter = mock_emhass
    mock_entry.runtime_data = mock_runtime

    mock_store = MagicMock()
    mock_store.async_remove = AsyncMock()

    yaml_path = MagicMock(spec=Path)
    yaml_path.exists.return_value = False

    with patch.object(
        cleanup, "ha_storage", Mock(Store=MagicMock(return_value=mock_store))
    ):
        with patch.object(cleanup, "Path", _MockPath(yaml_path)):
            await cleanup.async_remove_entry_cleanup(hass, mock_entry)

    # Listener should be set to None even after exception
    assert mock_emhass._config_entry_listener is None


@pytest.mark.asyncio
async def test_unload_entry_cleanup_entity_registry_exception():
    """Entity registry cleanup exception is caught and logged (lines 177-178)."""
    hass = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_xyz"
    mock_entry.runtime_data = None

    with patch.object(
        cleanup.er, "async_entries_for_config_entry",
        side_effect=RuntimeError("registry error"),
    ):
        with patch(
            "custom_components.ev_trip_planner.panel.async_unregister_panel",
            side_effect=ImportError("no panel"),
        ):
            result = await cleanup.async_unload_entry_cleanup(
                hass, mock_entry, "vehicle_2", "Vehicle 2"
            )

    assert result is True
