"""Type definitions extracted from trip_manager.py.

This module holds type definitions used across the trip package.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from custom_components.ev_trip_planner.emhass import EMHASSAdapter
    from custom_components.ev_trip_planner.yaml_trip_storage import YamlTripStorage


class TripManagerProtocol(Protocol):
    """Protocol defining the TripManager facade contract.

    Extension point for OCP compliance — other components depend on
    this protocol rather than the concrete TripManager class.
    """

    pass


@dataclass(frozen=True)
class TripManagerConfig:
    """Configuration passed to TripManager to reduce __init__ arity."""

    entry_id: str | None = None
    presence_config: dict[str, Any] | None = None
    storage: YamlTripStorage | None = None
    emhass_adapter: EMHASSAdapter | None = None
