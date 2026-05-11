"""Config flow — transitional shim.

This module is a thin re-export layer that preserves the public API while
all implementation lives in the ``config_flow/`` package.

Existing imports such as
``from custom_components.ev_trip_planner.config_flow import EVTripPlannerFlowHandler``
continue to work because the ``config_flow/`` package (directory) shadows
this ``config_flow.py`` file in Python's import resolution.
"""

from __future__ import annotations

from .config_flow import (
    EVTripPlannerFlowHandler,
    EVTripPlannerOptionsFlowHandler,
    async_get_options_flow,
)

# Alias for backward compatibility with tests
EVTripPlannerConfigFlow = EVTripPlannerFlowHandler

__all__ = [
    "EVTripPlannerFlowHandler",
    "EVTripPlannerOptionsFlowHandler",
    "async_get_options_flow",
    "EVTripPlannerConfigFlow",
]
