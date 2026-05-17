"""Verify config_flow/ package re-exports all 3 public names.

Tests that the `config_flow` **package** (after SOLID decomposition) exposes
the two flow handler classes and the options flow factory function.

This test MUST fail until the `config_flow/` package directory exists.

Requirement: AC-2.4
"""

from __future__ import annotations


def test_import_flow_handler() -> None:
    """EVTripPlannerFlowHandler is importable from config_flow package."""
    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerFlowHandler,
    )

    assert EVTripPlannerFlowHandler is not None


def test_import_options_flow_handler() -> None:
    """EVTripPlannerOptionsFlowHandler is importable from config_flow package."""
    from custom_components.ev_trip_planner.config_flow import (
        EVTripPlannerOptionsFlowHandler,
    )

    assert EVTripPlannerOptionsFlowHandler is not None


def test_import_async_get_options_flow() -> None:
    """async_get_options_flow is importable from config_flow package."""
    from custom_components.ev_trip_planner.config_flow import (
        async_get_options_flow,
    )

    assert async_get_options_flow is not None
