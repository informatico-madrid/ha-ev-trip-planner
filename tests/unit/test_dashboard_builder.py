"""Tests for DashboardBuilder in dashboard/builder.py.

RED phase: DashboardBuilder does not exist yet. Tests assert it should.
"""

from __future__ import annotations

import pytest  # noqa: F401


def test_dashboard_builder_import():
    """DashboardBuilder is importable from dashboard.builder."""
    from custom_components.ev_trip_planner.dashboard.builder import (
        DashboardBuilder,
    )

    assert DashboardBuilder is not None


def test_dashboard_builder_with_title():
    """with_title sets the dashboard title and returns self."""
    from custom_components.ev_trip_planner.dashboard.builder import (
        DashboardBuilder,
    )

    builder = DashboardBuilder()
    result = builder.with_title("EV Trip Planner")
    assert result is builder


def test_dashboard_builder_add_status_view():
    """add_status_view adds a status view card and returns self."""
    from custom_components.ev_trip_planner.dashboard.builder import (
        DashboardBuilder,
    )

    builder = DashboardBuilder()
    result = builder.add_status_view()
    assert result is builder


def test_dashboard_builder_add_trip_list_view():
    """add_trip_list_view adds a trip list view and returns self."""
    from custom_components.ev_trip_planner.dashboard.builder import (
        DashboardBuilder,
    )

    builder = DashboardBuilder()
    result = builder.add_trip_list_view()
    assert result is builder


def test_dashboard_builder_build_produces_valid_config():
    """build() returns a dict with title, views, and proper structure."""
    from custom_components.ev_trip_planner.dashboard.builder import (
        DashboardBuilder,
    )

    config = (
        DashboardBuilder()
        .with_title("EV Trip Planner")
        .add_status_view()
        .add_trip_list_view()
        .build()
    )

    assert isinstance(config, dict)
    assert config["title"] == "EV Trip Planner"
    assert isinstance(config["views"], list)
    assert len(config["views"]) == 2

    status_view = config["views"][0]
    assert isinstance(status_view, dict)
    assert "path" in status_view
    assert "title" in status_view
    assert "cards" in status_view

    trip_view = config["views"][1]
    assert isinstance(trip_view, dict)
    assert "path" in trip_view
    assert "title" in trip_view
    assert "cards" in trip_view
