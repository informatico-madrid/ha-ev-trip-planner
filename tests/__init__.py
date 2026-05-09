"""Layer 1 test doubles - shared constants, factories, and fakes."""

from typing import Any, Dict, List, Optional

# =============================================================================
# CONSTANTS
# =============================================================================

TEST_VEHICLE_ID = "coche1"
TEST_ENTRY_ID = "test_entry_id_abc123"

TEST_CONFIG = {
    "vehicle_name": "Coche 1",
    "vehicle_id": TEST_VEHICLE_ID,
    "soc_sensor": "sensor.coche1_soc",
    "battery_capacity_kwh": 60.0,
    "charging_power_kw": 7.4,
}

TEST_TRIPS = {
    "recurring": [
        {
            "id": "rec_lun_abc123",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "08:00",
            "km": 50.0,
            "kwh": 7.5,
            "descripcion": "Trabajo",
            "activo": True,
        },
    ],
    "punctual": [
        {
            "id": "pun_20260501_xyz789",
            "tipo": "puntual",
            "datetime": "2026-05-01T10:00:00",
            "km": 120.0,
            "kwh": 18.0,
            "descripcion": "Viaje largo",
            "estado": "pendiente",
        },
    ],
}

TEST_COORDINATOR_DATA = {
    "recurring_trips": {},
    "punctual_trips": {},
    "kwh_today": 0.0,
    "next_trip": None,
    "soc": 80.0,
}


# =============================================================================
# LAYER 1: FAKE CLASSES
# =============================================================================


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


# =============================================================================
# RE-EXPORTS: Factory functions (moved to tests.helpers.factories)
# =============================================================================

from tests.helpers.factories import (  # noqa: E402
    create_mock_coordinator,
    create_mock_ev_config_entry,
    create_mock_trip_manager,
    setup_mock_ev_config_entry,
)
