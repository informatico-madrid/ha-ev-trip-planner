"""Protocols for TripManager dependency injection."""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class TripStorageProtocol(Protocol):
    """Storage interface for trip data."""

    async def async_load(self) -> Dict[str, Any]:
        """Load trip data from storage."""
        ...

    async def async_save(self, data: Dict[str, Any]) -> None:
        """Save trip data to storage."""
        ...


@runtime_checkable
class EMHASSPublisherProtocol(Protocol):
    """EMHASS publishing interface."""

    async def async_publish_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """Publish a deferrable load for a single trip."""
        ...

    async def async_remove_deferrable_load(self, trip_id: str) -> bool:
        """Remove a deferrable load by trip ID."""
        ...

    async def async_publish_all_deferrable_loads(
        self, trips: List[Dict[str, Any]], charging_power_kw: Optional[float] = None
    ) -> bool:
        """Publish all deferrable loads for the given trips."""
        ...

    async def async_update_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """Update an existing deferrable load."""
        ...

    # Internal state access (for trip_manager -> emhass_adapter coupling)
    _published_trips: List[Dict[str, Any]]
    _cached_per_trip_params: Dict[str, Dict[str, Any]]
    _cached_power_profile: Optional[List[float]]
    _cached_deferrables_schedule: Optional[List[Any]]