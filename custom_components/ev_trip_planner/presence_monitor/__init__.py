"""Presence monitor package — transitional re-export shim.

Re-exports all public names from the legacy presence_monitor.py module.

During the SOLID decomposition, the legacy presence_monitor.py module file
is replaced by a presence_monitor/ package directory. This __init__.py
re-exports every public name so that existing import paths continue to work
without changes.
"""

from __future__ import annotations

from ..presence_monitor_orig import (
    HOME_DISTANCE_THRESHOLD_METERS,
    PresenceMonitor,
    SOC_CHANGE_DEBOUNCE_PERCENT,
)

__all__ = [
    "PresenceMonitor",
    "HOME_DISTANCE_THRESHOLD_METERS",
    "SOC_CHANGE_DEBOUNCE_PERCENT",
]
