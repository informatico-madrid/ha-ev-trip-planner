"""Test that cleanup.py functions are importable from services.cleanup package."""

from __future__ import annotations


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
