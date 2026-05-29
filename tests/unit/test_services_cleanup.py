"""Test that cleanup.py functions are importable from services.cleanup package."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from custom_components.ev_trip_planner.services import cleanup


def test_async_cleanup_stale_storage_importable() -> None:
    from custom_components.ev_trip_planner.services.cleanup import (
        async_cleanup_stale_storage,
    )

    assert callable(async_cleanup_stale_storage)


def test_async_cleanup_orphaned_emhass_sensors_importable() -> None:
    from custom_components.ev_trip_planner.services.cleanup import (
        async_cleanup_orphaned_emhass_sensors,
    )

    assert callable(async_cleanup_orphaned_emhass_sensors)


def test_async_unload_entry_cleanup_importable() -> None:
    from custom_components.ev_trip_planner.services.cleanup import (
        async_unload_entry_cleanup,
    )

    assert callable(async_unload_entry_cleanup)


def test_async_remove_entry_cleanup_importable() -> None:
    from custom_components.ev_trip_planner.services.cleanup import (
        async_remove_entry_cleanup,
    )

    assert callable(async_remove_entry_cleanup)


# --- async_cleanup_stale_storage — assertions on Store key ---


@pytest.mark.asyncio
async def test_cleanup_stale_storage_uses_correct_store_key(tmp_path):
    """Kill mutations: cleanup_key → None changes Store constructor key argument."""

    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value=None)
    mock_store_instance = MagicMock()
    mock_store_instance.async_load = AsyncMock(return_value=None)
    mock_store_class = MagicMock(return_value=mock_store_instance)

    def mock_path(*args, **kwargs):
        p = MagicMock(spec=Path)
        p.exists.return_value = True
        return p

    with patch.object(cleanup, "Path", mock_path):
        with patch.object(
            cleanup, "ha_storage", Mock(Store=mock_store_class)
        ):
            await cleanup.async_cleanup_stale_storage(hass, "test_vehicle")

    # Verify Store was called with the correct key
    call_kwargs = mock_store_class.call_args[1]
    assert call_kwargs["key"] == "ev_trip_planner_test_vehicle"


# --- async_remove_entry_cleanup — assertions on Store key ---


@pytest.mark.asyncio
async def test_remove_entry_cleanup_uses_correct_store_key(tmp_path):
    """Kill mutations: storage_key → None changes Store constructor."""

    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_abc"
    mock_entry.data = {"vehicle_name": "Test Vehicle"}
    mock_entry.runtime_data = None

    mock_store_instance = MagicMock()
    mock_store_instance.async_remove = AsyncMock()
    mock_store_class = MagicMock(return_value=mock_store_instance)

    def mock_path(*args, **kwargs):
        p = MagicMock(spec=Path)
        p.exists.return_value = False
        return p

    with patch.object(cleanup, "Path", mock_path):
        with patch.object(
            cleanup, "ha_storage", Mock(Store=mock_store_class)
        ):
            await cleanup.async_remove_entry_cleanup(hass, mock_entry)

    # Verify Store was called with the correct key
    call_kwargs = mock_store_class.call_args[1]
    assert call_kwargs["key"] == "ev_trip_planner_test_vehicle"
