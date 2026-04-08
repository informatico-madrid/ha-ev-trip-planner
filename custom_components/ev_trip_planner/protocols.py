"""Protocols for TripManager dependency injection."""

from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class TripStorageProtocol(Protocol):
    """Storage interface for trip data."""

    async def async_load(self) -> Dict[str, Any]: ...

    async def async_save(self, data: Dict[str, Any]) -> None: ...


@runtime_checkable
class EMHASSPublisherProtocol(Protocol):
    """EMHASS publishing interface."""

    async def async_publish_deferrable_load(self, trip: Dict[str, Any]) -> bool: ...

    async def async_remove_deferrable_load(self, trip_id: str) -> bool: ...