"""Shared state for TripManager — composition-over-inheritance backbone.

All sub-component instances are stored here so they can reference each other.
No Callable fields — methods live on their respective sub-component instances.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from homeassistant.core import HomeAssistant

from ..emhass import EMHASSAdapter
from ..yaml_trip_storage import YamlTripStorage
from ._sensor_callbacks import SensorCallbackRegistry


@dataclass
class TripManagerState:
    """All shared state between TripManager and its sub-components."""

    # ── Core attributes ──────────────────────────────────────────
    hass: HomeAssistant
    vehicle_id: str
    entry_id: Optional[str] = None
    _trips: dict[str, dict[str, Any]] = field(default_factory=dict)
    recurring_trips: dict[str, dict[str, Any]] = field(default_factory=dict)
    punctual_trips: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_update: Optional[str] = None
    storage: Optional[YamlTripStorage] = None
    emhass_adapter: Optional[EMHASSAdapter] = None
    vehicle_controller: Any = None
    sensor_callbacks: SensorCallbackRegistry = field(default_factory=SensorCallbackRegistry)

    # ── Sub-component references ─────────────────────────────────
    # Populated by TripManager.__init__ after all sub-components are created.
    # These enable cross-component method access without Callable hacks.
    _crud: Any = None  # TripCRUD
    _persistence: Any = None  # TripPersistence
    _soc: Any = None  # SOCCalculator
    _power: Any = None  # PowerProfile
    _schedule: Any = None  # TripScheduler
    _navigator: Any = None  # TripNavigator
    _emhass_sync: Any = None  # EMHASSSync
    _lifecycle: Any = None  # TripLifecycle
    _soc_window: Any = None  # SOCWindow
    _soc_helpers: Any = None  # SOCHelpers

    # ── Delegates needed by sub-components ────────────────────────
    # Sub-components call these during operation. They are populated
    # after the sub-component is created (in TripManager.__init__).
    async_save_trips: Any = None  # bound method of TripPersistence.async_save_trips
