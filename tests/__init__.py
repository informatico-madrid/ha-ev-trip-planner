"""Layer 1 test doubles - shared constants, factories, and fakes."""

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

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
# LAYER 1: FACTORY FUNCTIONS
# =============================================================================


def create_mock_trip_manager(hass=None, vehicle_id: str = TEST_VEHICLE_ID) -> MagicMock:
    """Create a spec'd MagicMock for TripManager.

    AC-D1.2: Must use MagicMock(spec=TripManager) with async methods
    configured individually - NOT AsyncMock without spec.

    T048: Includes all async stubs (async_get_kwh_needed_today,
    async_get_hours_needed_today, async_get_next_trip) with defaults.
    """
    from custom_components.ev_trip_planner.trip_manager import TripManager

    mock = MagicMock(spec=TripManager)
    mock.async_setup = AsyncMock(return_value=None)
    mock.async_get_recurring_trips = AsyncMock(return_value=TEST_TRIPS["recurring"])
    mock.async_get_punctual_trips = AsyncMock(return_value=TEST_TRIPS["punctual"])
    mock.get_all_trips = MagicMock(return_value=TEST_TRIPS)
    mock.async_add_recurring_trip = AsyncMock(return_value=None)
    mock.async_add_punctual_trip = AsyncMock(return_value=None)
    mock.async_save_trips = AsyncMock(return_value=None)
    mock.async_delete_trip = AsyncMock(return_value=None)
    mock.publish_deferrable_loads = AsyncMock(return_value=None)
    # T048: async stubs for deterministic datetime-based calculations
    mock.async_get_kwh_needed_today = AsyncMock(return_value=0.0)
    mock.async_get_hours_needed_today = AsyncMock(return_value=0.0)
    mock.async_get_next_trip = AsyncMock(return_value=None)
    # T048: seed attributes required by tests
    mock.hass = hass
    mock.vehicle_id = vehicle_id
    mock._emhass_adapter = None
    mock._trips = {}
    mock._recurring_trips = {}
    mock._punctual_trips = {}
    return mock


def create_mock_coordinator(hass=None, entry=None, trip_manager=None) -> MagicMock:
    """Create a spec'd MagicMock for TripPlannerCoordinator."""
    from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator

    mock = MagicMock(spec=TripPlannerCoordinator)
    mock.data = dict(TEST_COORDINATOR_DATA)
    mock.hass = hass
    mock._trip_manager = trip_manager or create_mock_trip_manager(hass)
    mock.async_config_entry_first_refresh = AsyncMock(return_value=None)
    return mock


def create_mock_ev_config_entry(
    hass=None, data: Dict[str, Any] = None, entry_id: str = TEST_ENTRY_ID
):
    """Create a MockConfigEntry for testing."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    config_entry = MockConfigEntry(
        entry_id=entry_id,
        domain="ev_trip_planner",
        data=data if data is not None else TEST_CONFIG,
        version=1,
    )
    if hass:
        config_entry.add_to_hass(hass)
    return config_entry


async def setup_mock_ev_config_entry(hass, config_entry=None, trip_manager=None):
    """Set up full mock integration entry with HA boundary patches INSIDE.

    AC-D1.5: Patches at HA boundary go inside this factory function,
    NOT in conftest.py Layer 3 directly.
    """
    from unittest.mock import patch

    config_entry = config_entry or create_mock_ev_config_entry(hass)
    manager = trip_manager or create_mock_trip_manager(hass)

    with patch(
        "custom_components.ev_trip_planner.TripManager",
        return_value=manager,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    return config_entry, manager
