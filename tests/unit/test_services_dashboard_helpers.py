"""Test that dashboard_helpers.py functions are importable from services.dashboard_helpers package."""

from __future__ import annotations


def test_async_register_panel_for_entry_importable() -> None:
    from custom_components.ev_trip_planner.services.dashboard_helpers import (
        async_register_panel_for_entry,
    )

    assert callable(async_register_panel_for_entry)


def test_async_register_static_paths_importable() -> None:
    from custom_components.ev_trip_planner.services.dashboard_helpers import (
        async_register_static_paths,
    )

    assert callable(async_register_static_paths)
