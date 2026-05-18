"""Vehicle control package — Strategy pattern for EV charging.

Extracted from the legacy vehicle_controller.py module as part of the
SOLID decomposition (Spec 3).
"""

from __future__ import annotations

from .controller import (
    MAX_RETRY_ATTEMPTS,
    RETRY_TIME_WINDOW_SECONDS,
    VehicleController,
    create_control_strategy,
)
from .external import ExternalStrategy, ScriptStrategy
from .strategy import (
    HomeAssistantWrapper,
    RetryState,
    ServiceStrategy,
    SwitchStrategy,
    VehicleControlStrategy,
)

__all__ = [
    "ExternalStrategy",
    "HomeAssistantWrapper",
    "MAX_RETRY_ATTEMPTS",
    "RETRY_TIME_WINDOW_SECONDS",
    "RetryState",
    "ScriptStrategy",
    "ServiceStrategy",
    "SwitchStrategy",
    "VehicleController",
    "VehicleControlStrategy",
    "create_control_strategy",
]
