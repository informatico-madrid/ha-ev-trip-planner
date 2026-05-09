"""Layer 1 test doubles — in-memory fakes for storage and publishing."""

from typing import Any, Dict, List, Optional


class FakeTripStorage:
    """In-memory fake storage for tests."""

    def __init__(self, initial_data: Dict[str, Any] = None) -> None:
        # Preserve explicit empty dicts (T048: use `if initial_data is None` not `or {}`)
        self._data = (
            initial_data
            if initial_data is not None
            else {"trips": {}, "recurring_trips": {}, "punctual_trips": {}}
        )

    async def async_load(self) -> Dict[str, Any]:
        return self._data

    async def async_save(self, data: Dict[str, Any]) -> None:
        self._data = data


class FakeEMHASSPublisher:
    """In-memory fake EMHASS publisher for tests."""

    def __init__(self) -> None:
        self.published_trips: List[Dict[str, Any]] = []
        self.removed_trip_ids: List[str] = []
        self.all_published_trips: List[List[Dict[str, Any]]] = []
        self._published_trips: List[Dict[str, Any]] = []
        self._cached_per_trip_params: Dict[str, Dict[str, Any]] = {}
        self._cached_power_profile: Optional[List[float]] = None
        self._cached_deferrables_schedule: Optional[List[Any]] = None

    async def async_publish_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        self.published_trips.append(trip)
        return True

    async def async_remove_deferrable_load(self, trip_id: str) -> bool:
        self.removed_trip_ids.append(trip_id)
        return True

    async def async_publish_all_deferrable_loads(
        self, trips: List[Dict[str, Any]], charging_power_kw: float = None
    ) -> bool:
        self.all_published_trips.append(trips)
        for trip in trips:
            self.published_trips.append(trip)
        return True

    async def async_update_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        return await self.async_publish_deferrable_load(trip)
