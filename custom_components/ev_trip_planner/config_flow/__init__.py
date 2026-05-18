"""Config flow package — re-exports all 3 public names.

This package shadows ``config_flow.py`` so all existing imports that reference
``custom_components.ev_trip_planner.config_flow`` resolve here.
"""

from __future__ import annotations

from .main import EVTripPlannerFlowHandler
from .options import EVTripPlannerOptionsFlowHandler, async_get_options_flow

# Backward-compat alias
EVTripPlannerConfigFlow = EVTripPlannerFlowHandler

__all__ = [
    "EVTripPlannerFlowHandler",
    "EVTripPlannerOptionsFlowHandler",
    "async_get_options_flow",
    "EVTripPlannerConfigFlow",
]
