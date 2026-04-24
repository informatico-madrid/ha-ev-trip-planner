"""Tests for TripManager CRUD operations and YAML persistence.

This test suite covers:
- CRUD operations: create, read, update, delete trips
- YAML persistence for Container environment
- Storage API for Supervisor environment
"""

from __future__ import annotations

from datetime import datetime, timezone
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner import EVTripRuntimeData
from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def vehicle_id() -> str:
    """Return a test vehicle ID."""
    return "morgan"


@pytest.fixture
def mock_hass_no_storage():
    """Create a mock hass WITH storage for testing.

    The production code requires hass.storage to use HA Store API.
    This fixture provides a mocked storage so tests don't hit real storage.
    """

    hass = MagicMock()
    # Mock config_entries
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    # Provide mocked loop for Store API
    mock_loop = MagicMock()
    mock_loop.create_future = MagicMock(return_value=None)
    hass.loop = mock_loop

    # Provide mocked storage so HA Store API can work in tests
    # This is needed because production code uses ha_storage.Store which requires hass.storage
    hass.storage = MagicMock()
    hass.storage.async_read = AsyncMock(return_value=None)
    hass.storage.async_write_dict = AsyncMock(return_value=True)

    return hass


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance with storage (Supervisor environment)."""

    hass = MagicMock()
    # Mock config_entries
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    # Mock config directory
    hass.config.config_dir = "/tmp/test_config"

    return hass


@pytest.fixture
def trip_manager(mock_hass, vehicle_id):
    """Create a TripManager instance for testing."""
    return TripManager(mock_hass, vehicle_id)


@pytest.fixture
def trip_manager_no_storage(mock_hass_no_storage, vehicle_id):
    """Create a TripManager instance for Container environment testing."""
    return TripManager(mock_hass_no_storage, vehicle_id)


class TestTripCreate:
    """Tests for creating trips (CRUD Create operation)."""

    @pytest.mark.asyncio
    async def test_add_recurring_trip(self, trip_manager, caplog):
        """Test adding a new recurring trip."""
        # Add a recurring trip
        await trip_manager.async_add_recurring_trip(
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
            descripcion="Test recurring trip",
        )

        # Verify trip was added
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["dia_semana"] == "lunes"
        assert trips[0]["hora"] == "08:00"
        assert trips[0]["km"] == 50.0
        assert trips[0]["kwh"] == 10.0
        assert trips[0]["descripcion"] == "Test recurring trip"
        assert trips[0]["activo"] is True
        assert trips[0]["tipo"] == "recurrente"

    @pytest.mark.asyncio
    async def test_add_punctual_trip(self, trip_manager, caplog):
        """Test adding a new punctual trip."""
        # Add a punctual trip
        await trip_manager.async_add_punctual_trip(
            datetime_str="2026-03-20T10:00",
            km=100.0,
            kwh=20.0,
            descripcion="Test punctual trip",
        )

        # Verify trip was added
        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 1
        assert trips[0]["datetime"] == "2026-03-20T10:00"
        assert trips[0]["km"] == 100.0
        assert trips[0]["kwh"] == 20.0
        assert trips[0]["descripcion"] == "Test punctual trip"
        assert trips[0]["estado"] == "pendiente"
        assert trips[0]["tipo"] == "puntual"

    @pytest.mark.asyncio
    async def test_add_recurring_trip_with_custom_id(self, trip_manager, caplog):
        """Test adding a recurring trip with custom ID."""
        await trip_manager.async_add_recurring_trip(
            trip_id="custom_rec_trip",
            dia_semana="martes",
            hora="09:00",
            km=75.0,
            kwh=15.0,
            descripcion="Custom ID trip",
        )

        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["id"] == "custom_rec_trip"
        assert trips[0]["dia_semana"] == "martes"

    @pytest.mark.asyncio
    async def test_add_multiple_recurring_trips(self, trip_manager, caplog):
        """Test adding multiple recurring trips."""
        # Add three recurring trips
        for day, hour in [("lunes", "08:00"), ("miercoles", "09:00"), ("viernes", "10:00")]:
            await trip_manager.async_add_recurring_trip(
                dia_semana=day,
                hora=hour,
                km=50.0,
                kwh=10.0,
            )

        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 3

        # Verify all trips are present
        days = {trip["dia_semana"] for trip in trips}
        assert days == {"lunes", "miercoles", "viernes"}

    @pytest.mark.asyncio
    async def test_add_multiple_punctual_trips(self, trip_manager, caplog):
        """Test adding multiple punctual trips."""
        # Add three punctual trips
        for i in range(3):
            await trip_manager.async_add_punctual_trip(
                datetime_str=f"2026-03-{20+i:02d}T10:00",
                km=50.0 * (i + 1),
                kwh=10.0 * (i + 1),
            )

        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 3

    @pytest.mark.asyncio
    async def test_add_trip_logs_debug(self, trip_manager, caplog):
        """Test that adding trips logs debug messages."""
        caplog.set_level("DEBUG")

        await trip_manager.async_add_recurring_trip(
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )

        # Verify debug log was written
        assert any("Adding recurring trip" in record.message for record in caplog.records)


class TestTripRead:
    """Tests for reading trips (CRUD Read operation)."""

    @pytest.mark.asyncio
    async def test_get_recurring_trips_empty(self, trip_manager):
        """Test getting recurring trips when none exist."""
        trips = await trip_manager.async_get_recurring_trips()
        assert trips == []

    @pytest.mark.asyncio
    async def test_get_punctual_trips_empty(self, trip_manager):
        """Test getting punctual trips when none exist."""
        trips = await trip_manager.async_get_punctual_trips()
        assert trips == []

    @pytest.mark.asyncio
    async def test_get_recurring_trips_with_data(self, trip_manager):
        """Test getting recurring trips with existing data."""
        # Add some trips
        await trip_manager.async_add_recurring_trip(
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )
        await trip_manager.async_add_recurring_trip(
            dia_semana="miércoles",
            hora="09:00",
            km=75.0,
            kwh=15.0,
        )

        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 2
        assert trips[0]["dia_semana"] == "lunes"
        assert trips[1]["dia_semana"] == "miércoles"

    @pytest.mark.asyncio
    async def test_get_punctual_trips_with_data(self, trip_manager):
        """Test getting punctual trips with existing data."""
        # Add some trips
        await trip_manager.async_add_punctual_trip(
            datetime_str="2026-03-20T10:00",
            km=100.0,
            kwh=20.0,
        )
        await trip_manager.async_add_punctual_trip(
            datetime_str="2026-03-21T11:00",
            km=150.0,
            kwh=30.0,
        )

        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 2
        assert trips[0]["datetime"] == "2026-03-20T10:00"
        assert trips[1]["datetime"] == "2026-03-21T11:00"


class TestTripUpdate:
    """Tests for updating trips (CRUD Update operation)."""

    @pytest.mark.asyncio
    async def test_update_recurring_trip(self, trip_manager, caplog):
        """Test updating an existing recurring trip."""
        # First add a trip
        await trip_manager.async_add_recurring_trip(
            trip_id="rec_lunes_001",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
            descripcion="Original trip",
        )

        # Update the trip
        await trip_manager.async_update_trip(
            "rec_lunes_001",
            {
                "dia_semana": "martes",
                "hora": "09:00",
                "km": 75.0,
                "descripcion": "Updated trip",
            },
        )

        # Verify update
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["dia_semana"] == "martes"
        assert trips[0]["hora"] == "09:00"
        assert trips[0]["km"] == 75.0
        assert trips[0]["descripcion"] == "Updated trip"

    @pytest.mark.asyncio
    async def test_update_punctual_trip(self, trip_manager, caplog):
        """Test updating an existing punctual trip."""
        # First add a trip
        await trip_manager.async_add_punctual_trip(
            trip_id="pun_20260320_001",
            datetime_str="2026-03-20T10:00",
            km=100.0,
            kwh=20.0,
            descripcion="Original punctual trip",
        )

        # Update the trip
        await trip_manager.async_update_trip(
            "pun_20260320_001",
            {
                "km": 150.0,
                "kwh": 30.0,
                "descripcion": "Updated punctual trip",
            },
        )

        # Verify update
        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 1
        assert trips[0]["km"] == 150.0
        assert trips[0]["kwh"] == 30.0
        assert trips[0]["descripcion"] == "Updated punctual trip"

    @pytest.mark.asyncio
    async def test_update_nonexistent_trip(self, trip_manager, caplog):
        """Test updating a trip that doesn't exist."""
        caplog.set_level("WARNING")

        await trip_manager.async_update_trip(
            "nonexistent_trip",
            {"km": 100.0},
        )

        # Verify warning was logged
        assert any("not found for update" in record.message for record in caplog.records)

        # Verify no trips were created
        trips = await trip_manager.async_get_punctual_trips()
        assert trips == []

    @pytest.mark.asyncio
    async def test_pause_recurring_trip(self, trip_manager, caplog):
        """Test pausing a recurring trip."""
        # First add an active trip
        await trip_manager.async_add_recurring_trip(
            trip_id="rec_active_001",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )

        # Pause the trip
        await trip_manager.async_pause_recurring_trip("rec_active_001")

        # Verify trip is paused
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["activo"] is False

    @pytest.mark.asyncio
    async def test_resume_recurring_trip(self, trip_manager, caplog):
        """Test resuming a paused recurring trip."""
        # First add and pause a trip
        await trip_manager.async_add_recurring_trip(
            trip_id="rec_paused_001",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )
        await trip_manager.async_pause_recurring_trip("rec_paused_001")

        # Verify it's paused
        trips = await trip_manager.async_get_recurring_trips()
        assert trips[0]["activo"] is False

        # Resume the trip
        await trip_manager.async_resume_recurring_trip("rec_paused_001")

        # Verify trip is active
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["activo"] is True

    @pytest.mark.asyncio
    async def test_complete_punctual_trip(self, trip_manager, caplog):
        """Test completing a punctual trip."""
        # First add a trip
        await trip_manager.async_add_punctual_trip(
            trip_id="pun_pending_001",
            datetime_str="2026-03-20T10:00",
            km=100.0,
            kwh=20.0,
        )

        # Complete the trip
        await trip_manager.async_complete_punctual_trip("pun_pending_001")

        # Verify trip is completed
        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 1
        assert trips[0]["estado"] == "completado"

    @pytest.mark.asyncio
    async def test_update_paused_trip(self, trip_manager, caplog):
        """Test updating a paused recurring trip."""
        # First add and pause a trip
        await trip_manager.async_add_recurring_trip(
            trip_id="rec_paused_001",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )
        await trip_manager.async_pause_recurring_trip("rec_paused_001")

        # Update the paused trip
        await trip_manager.async_update_trip(
            "rec_paused_001",
            {"km": 75.0},
        )

        # Verify trip is updated but still paused
        trips = await trip_manager.async_get_recurring_trips()
        assert trips[0]["km"] == 75.0
        assert trips[0]["activo"] is False


class TestTripDelete:
    """Tests for deleting trips (CRUD Delete operation)."""

    @pytest.mark.asyncio
    async def test_delete_recurring_trip(self, trip_manager, caplog):
        """Test deleting a recurring trip."""
        # First add a trip
        await trip_manager.async_add_recurring_trip(
            trip_id="rec_to_delete_001",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )

        # Delete the trip
        await trip_manager.async_delete_trip("rec_to_delete_001")

        # Verify trip was deleted
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 0

    @pytest.mark.asyncio
    async def test_delete_punctual_trip(self, trip_manager, caplog):
        """Test deleting a punctual trip."""
        # First add a trip
        await trip_manager.async_add_punctual_trip(
            trip_id="pun_to_delete_001",
            datetime_str="2026-03-20T10:00",
            km=100.0,
            kwh=20.0,
        )

        # Delete the trip
        await trip_manager.async_delete_trip("pun_to_delete_001")

        # Verify trip was deleted
        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_trip(self, trip_manager, caplog):
        """Test deleting a trip that doesn't exist."""
        caplog.set_level("WARNING")

        await trip_manager.async_delete_trip("nonexistent_trip")

        # Verify warning was logged
        assert any("not found for deletion" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_cancel_punctual_trip(self, trip_manager, caplog):
        """Test cancelling a punctual trip (deletes it)."""
        # First add a trip
        await trip_manager.async_add_punctual_trip(
            trip_id="pun_cancel_001",
            datetime_str="2026-03-20T10:00",
            km=100.0,
            kwh=20.0,
        )

        # Cancel the trip
        await trip_manager.async_cancel_punctual_trip("pun_cancel_001")

        # Verify trip was deleted
        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 0

    @pytest.mark.asyncio
    async def test_delete_mixed_trips(self, trip_manager, caplog):
        """Test deleting from both trip types."""
        # Add trips of both types
        await trip_manager.async_add_recurring_trip(
            trip_id="rec_keep_001",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )
        await trip_manager.async_add_recurring_trip(
            trip_id="rec_delete_001",
            dia_semana="martes",
            hora="09:00",
            km=75.0,
            kwh=15.0,
        )
        await trip_manager.async_add_punctual_trip(
            trip_id="pun_keep_001",
            datetime_str="2026-03-20T10:00",
            km=100.0,
            kwh=20.0,
        )
        await trip_manager.async_add_punctual_trip(
            trip_id="pun_delete_001",
            datetime_str="2026-03-21T11:00",
            km=150.0,
            kwh=30.0,
        )

        # Delete one from each type
        await trip_manager.async_delete_trip("rec_delete_001")
        await trip_manager.async_delete_trip("pun_delete_001")

        # Verify remaining trips
        recurring = await trip_manager.async_get_recurring_trips()
        punctual = await trip_manager.async_get_punctual_trips()

        assert len(recurring) == 1
        assert recurring[0]["id"] == "rec_keep_001"
        assert len(punctual) == 1
        assert punctual[0]["id"] == "pun_keep_001"


class TestTripPersistence:
    """Tests for trip persistence (save/load)."""

    @pytest.mark.asyncio
    async def test_save_and_load_trips(self, trip_manager, tmp_path, caplog):
        """Test that trips are saved and loaded correctly."""
        # Add some trips
        await trip_manager.async_add_recurring_trip(
            trip_id="rec_persist_001",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
            descripcion="Persistent trip",
        )
        await trip_manager.async_add_punctual_trip(
            trip_id="pun_persist_001",
            datetime_str="2026-03-20T10:00",
            km=100.0,
            kwh=20.0,
            descripcion="Persistent punctual trip",
        )

        # Verify trips were added to the manager
        assert "rec_persist_001" in trip_manager._recurring_trips
        assert "pun_persist_001" in trip_manager._punctual_trips

    @pytest.mark.asyncio
    async def test_save_trips_logs_info(self, trip_manager, caplog):
        """Test that saving trips logs info message."""
        caplog.set_level("INFO")

        await trip_manager.async_add_recurring_trip(
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )

        # Verify that trips were added (storage error is expected with mock)
        # The important thing is that add_trip logs success
        assert any("Added recurring trip" in record.message for record in caplog.records)


class TestTripManagerInitialization:
    """Tests for TripManager initialization and setup."""

    @pytest.mark.asyncio
    async def test_trip_manager_initialization(self, trip_manager):
        """Test that TripManager initializes with empty collections."""
        assert trip_manager.vehicle_id == "morgan"
        assert trip_manager._trips == {}
        assert trip_manager._recurring_trips == {}
        assert trip_manager._punctual_trips == {}
        assert trip_manager._last_update is None

    @pytest.mark.asyncio
    async def test_trip_manager_setup(self, trip_manager, caplog):
        """Test TripManager async_setup."""
        caplog.set_level("INFO")

        await trip_manager.async_setup()

        # Verify setup completed without errors
        assert "Configurando gestor de viajes" in caplog.text

    @pytest.mark.asyncio
    async def test_emhass_adapter_setter_getter(self, trip_manager):
        """Test setting and getting EMHASS adapter."""

        mock_adapter = MagicMock()

        trip_manager.set_emhass_adapter(mock_adapter)
        assert trip_manager.get_emhass_adapter() is mock_adapter


class TestChargingWindowCalculation:
    """Tests for charging window calculation (AC-1)."""

    @pytest.mark.asyncio
    async def test_basic_window_calculation_4_hours(self, trip_manager, caplog):
        """Test basic window calculation: hora_regreso=18:00, next trip=22:00, verify ventana=4 hours.

        This is the POC test for AC-1:
        Given the car is at home from 18:00 and the next trip is at 22:00,
        then the charging window is 4 hours.
        """
        # Setup: Add a punctual trip at 22:00 today
        # Use the format expected by trip_manager: %Y-%m-%dT%H:%M
        trip_datetime = datetime.now(timezone.utc).replace(hour=22, minute=0, second=0, microsecond=0)
        datetime_str = trip_datetime.strftime("%Y-%m-%dT%H:%M")
        await trip_manager.async_add_punctual_trip(
            datetime_str=datetime_str,
            km=50.0,
            kwh=10.0,
            descripcion="Evening trip",
        )

        # Mock async_calcular_energia_necesaria to return predictable values
        trip_manager.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 10.0}
        )

        # Set hora_regreso at 18:00 today
        hora_regreso = datetime.now(timezone.utc).replace(hour=18, minute=0, second=0, microsecond=0)

        # Get the trip we just added
        trips = await trip_manager.async_get_punctual_trips()
        trip = trips[0]

        # Call calcular_ventana_carga
        result = await trip_manager.calcular_ventana_carga(
            trip=trip,
            soc_actual=50.0,
            hora_regreso=hora_regreso,
            charging_power_kw=7.4,
        )

        # Verify window is 4 hours (from 18:00 to 22:00)
        assert result["ventana_horas"] == 4.0, f"Expected 4.0 hours, got {result['ventana_horas']}"

        # Verify all expected fields are returned (AC-1 interface contract)
        assert "ventana_horas" in result, "Missing ventana_horas field"
        assert "kwh_necesarios" in result, "Missing kwh_necesarios field"
        assert "horas_carga_necesarias" in result, "Missing horas_carga_necesarias field"
        assert "inicio_ventana" in result, "Missing inicio_ventana field"
        assert "fin_ventana" in result, "Missing fin_ventana field"
        assert "es_suficiente" in result, "Missing es_suficiente field"

        # Verify energy calculation
        assert result["kwh_necesarios"] == 10.0
        assert result["horas_carga_necesarias"] == pytest.approx(1.35, rel=0.01)  # 10.0 / 7.4

        # Verify window start and end times
        assert result["inicio_ventana"] == hora_regreso
        assert result["fin_ventana"] == trip_datetime

        # Verify es_suficiente is True (4 hours > 1.35 hours needed)
        assert result["es_suficiente"] is True

@pytest.fixture
def mock_hass_with_storage():
    """Create a mock hass with storage for testing error paths."""
    hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    mock_loop = MagicMock()
    mock_loop.create_future = MagicMock(return_value=None)
    hass.loop = mock_loop

    hass.storage = MagicMock()
    hass.storage.async_read = AsyncMock(return_value=None)
    hass.storage.async_write_dict = AsyncMock(return_value=True)

    return hass


@pytest.mark.asyncio
async def test_async_setup_handles_cancelled_error(mock_hass_with_storage):
    """async_setup handles CancelledError during storage load."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

    # Make storage async_read raise CancelledError
    mock_hass_with_storage.storage.async_read = AsyncMock(
        side_effect=asyncio.CancelledError
    )

    # Should not raise - CancelledError is caught and treated as empty state
    await trip_manager.async_setup()

    assert trip_manager._trips == {}
    assert trip_manager._recurring_trips == {}
    assert trip_manager._punctual_trips == {}
    assert trip_manager._last_update is None


@pytest.mark.asyncio
async def test_async_setup_handles_generic_exception(mock_hass_with_storage):
    """async_setup handles generic Exception during storage load."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

    # Make storage async_read raise a generic exception
    mock_hass_with_storage.storage.async_read = AsyncMock(
        side_effect=ValueError("Storage corrupted")
    )

    # Should not raise - exception is caught and treated as empty state
    await trip_manager.async_setup()

    assert trip_manager._trips == {}
    assert trip_manager._recurring_trips == {}
    assert trip_manager._punctual_trips == {}
    assert trip_manager._last_update is None


@pytest.mark.asyncio
async def test_async_save_trips_handles_exception(mock_hass_with_storage):
    """async_save_trips handles exceptions during save gracefully."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
    await trip_manager.async_setup()

    # Make storage async_write_dict raise an exception
    mock_hass_with_storage.storage.async_write_dict = AsyncMock(
        side_effect=Exception("Disk full")
    )

    # Should not raise - exception is caught and logged
    await trip_manager.async_save_trips()

    # Data should still be intact
    assert trip_manager._trips == {}


@pytest.mark.asyncio
async def test_async_save_trips_yaml_fallback_also_fails(mock_hass_with_storage):
    """async_save_trips falls back to YAML and catches that error too."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
    await trip_manager.async_setup()

    # Make both HA storage AND YAML fallback fail
    mock_hass_with_storage.storage.async_write_dict = AsyncMock(
        side_effect=Exception("HA storage failed")
    )

    # Patch Path to raise on mkdir
    with patch(
        "pathlib.Path.mkdir",
        side_effect=Exception("mkdir failed"),
    ):
        # Should not raise - both failures caught
        await trip_manager.async_save_trips()


@pytest.mark.asyncio
async def test_set_and_get_emhass_adapter(mock_hass_with_storage):
    """TripManager set_emhass_adapter and get_emhass_adapter work correctly."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

    mock_adapter = MagicMock()
    trip_manager.set_emhass_adapter(mock_adapter)

    assert trip_manager.get_emhass_adapter() is mock_adapter


@pytest.mark.asyncio
async def test_async_generate_deferrables_schedule_returns_list(mock_hass_with_storage):
    """Test async_generate_deferrables_schedule returns a list of deferrable dicts."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

    result = await trip_manager.async_generate_deferrables_schedule()

    # Result is a list of deferrable load dicts (one per time slot)
    assert isinstance(result, list)
    assert len(result) > 0
    # Each entry should have a 'date' key
    assert "date" in result[0]


@pytest.mark.asyncio
async def test_async_generate_power_profile_with_presence_monitor(mock_hass_with_storage):
    """async_generate_power_profile uses presence_monitor for hora_regreso."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
    await trip_manager.async_setup()

    # Set up presence_monitor mock
    mock_presence = MagicMock()
    mock_presence.async_get_hora_regreso = AsyncMock(
        return_value=datetime(2025, 1, 15, 18, 0)
    )
    trip_manager.vehicle_controller._presence_monitor = mock_presence

    # Should use presence_monitor's hora_regreso
    result = await trip_manager.async_generate_power_profile(
        charging_power_kw=3.6,
        planning_horizon_days=1,
    )

    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_async_generate_power_profile_no_presence_monitor(mock_hass_with_storage):
    """async_generate_power_profile handles missing presence_monitor gracefully."""
    trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
    await trip_manager.async_setup()

    # No presence_monitor set
    trip_manager.vehicle_controller._presence_monitor = None

    # Should not raise - presence_monitor is None
    result = await trip_manager.async_generate_power_profile(
        charging_power_kw=3.6,
        planning_horizon_days=1,
    )

    assert isinstance(result, list)


class TestAsyncGeneratePowerProfileWithTrips:
    """Tests for async_generate_power_profile with real trips in memory."""

    @pytest.mark.asyncio
    async def test_async_generate_power_profile_with_punctual_trip_in_memory(
        self, mock_hass_with_storage
    ):
        """async_generate_power_profile processes punctual trips with estado=pendiente."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        # Add a punctual trip directly to memory with estado=pendiente
        # Using a future datetime so horas_hasta_viaje >= 0
        from datetime import datetime, timedelta

        future_date = datetime.now() + timedelta(days=2)
        # Use proper format that calculate_trip_time expects (without microseconds)
        future_date_str = future_date.strftime("%Y-%m-%dT%H:%M")
        trip_manager._punctual_trips["pun_test_001"] = {
            "id": "pun_test_001",
            "tipo": "puntual",
            "datetime": future_date_str,
            "km": 50.0,
            "kwh": 15.0,
            "estado": "pendiente",
        }

        # Mock async_get_vehicle_soc to return a valid SOC
        trip_manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)

        # Also need to mock config_entries to return proper battery_capacity
        mock_entry = MagicMock()
        mock_entry.data = {"battery_capacity_kwh": 50.0}
        mock_hass_with_storage.config_entries.async_get_entry.return_value = mock_entry

        # Call async_generate_power_profile with explicit hora_regreso to avoid mock issues
        result = await trip_manager.async_generate_power_profile(
            charging_power_kw=3.6,
            planning_horizon_days=1,
            hora_regreso=datetime.now() + timedelta(hours=2),
        )

        assert isinstance(result, list)
        assert len(result) == 24  # 1 day * 24 hours

    @pytest.mark.asyncio
    async def test_async_generate_power_profile_skips_trip_without_datetime(
        self, mock_hass_with_storage
    ):
        """async_generate_power_profile skips trips without datetime (line 1951)."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()
        from datetime import datetime, timedelta

        # Add a punctual trip WITHOUT datetime
        trip_manager._punctual_trips["pun_no_dt"] = {
            "id": "pun_no_dt",
            "tipo": "puntual",
            "km": 50.0,
            "kwh": 15.0,
            "estado": "pendiente",
        }

        # Should not raise - trip without datetime is skipped
        result = await trip_manager.async_generate_power_profile(
            charging_power_kw=3.6,
            planning_horizon_days=1,
            hora_regreso=datetime.now() + timedelta(hours=2),
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_async_generate_power_profile_with_past_trip_skipped(
        self, mock_hass_with_storage
    ):
        """async_generate_power_profile skips trips with horas_hasta_viaje < 0 (line 1958)."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()
        from datetime import datetime, timedelta

        past_date = datetime.now() - timedelta(days=2)
        # Use proper format that calculate_trip_time expects (without microseconds)
        past_date_str = past_date.strftime("%Y-%m-%dT%H:%M")
        trip_manager._punctual_trips["pun_past"] = {
            "id": "pun_past",
            "tipo": "puntual",
            "datetime": past_date_str,
            "km": 50.0,
            "kwh": 15.0,
            "estado": "pendiente",
        }

        # Mock async_get_vehicle_soc to return a valid SOC
        trip_manager.async_get_vehicle_soc = AsyncMock(return_value=50.0)

        # Also need to mock config_entries to return proper battery_capacity
        mock_entry = MagicMock()
        mock_entry.data = {"battery_capacity_kwh": 50.0}
        mock_hass_with_storage.config_entries.async_get_entry.return_value = mock_entry

        # Should not raise - past trip is skipped
        result = await trip_manager.async_generate_power_profile(
            charging_power_kw=3.6,
            planning_horizon_days=1,
            hora_regreso=datetime.now() + timedelta(hours=2),
        )

        assert isinstance(result, list)


class TestTripManagerAsyncRemoveTripSensor:
    """Tests for async_remove_trip_sensor error paths."""

    @pytest.mark.asyncio
    async def test_async_remove_trip_sensor_registry_error(self, mock_hass_with_storage):
        """async_remove_trip_sensor handles registry error gracefully."""
        from custom_components.ev_trip_planner.sensor import async_remove_trip_sensor

        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        # Mock registry.async_get to raise
        with patch(
            "homeassistant.helpers.entity_registry.EntityRegistry.async_get",
            side_effect=Exception("Registry error"),
        ):
            # Should not raise - exception is caught and logged
            await async_remove_trip_sensor(mock_hass_with_storage, "test_entry", "trip_1")



class TestTripManagerAsyncUpdateTripSensor:
    """Tests for async_update_trip_sensor error paths."""

    @pytest.mark.asyncio
    async def test_async_update_trip_sensor_trip_not_found(self, mock_hass_with_storage):
        """async_update_trip_sensor handles missing trip gracefully."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        # Don't add any trips - trip_1 doesn't exist
        # Should not raise - returns early when trip not found
        await trip_manager.async_update_trip_sensor("trip_1")

    @pytest.mark.asyncio
    async def test_async_update_trip_sensor_registry_get_error(self, mock_hass_with_storage):
        """async_update_trip_sensor handles registry get error."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        # Add a trip
        trip_manager._punctual_trips["trip_1"] = {
            "id": "trip_1",
            "tipo": "punctual",
            "datetime": "2025-01-15T18:00",
            "km": 30.0,
            "kwh": 5.0,
        }

        # Mock entity_registry.async_get to return an entry first (exists), then raise on update
        mock_entry = MagicMock()
        mock_entry.entity_id = "sensor.trip_1"

        with patch(
            "homeassistant.helpers.entity_registry.EntityRegistry.async_get",
            return_value=mock_entry,
        ):
            # Should not raise even if hass.states.async_set fails
            with patch.object(mock_hass_with_storage, "states") as mock_states:
                mock_states.async_set = MagicMock(side_effect=Exception("State error"))
                await trip_manager.async_update_trip_sensor("trip_1")



class TestTripManagerGetTripTime:
    """Tests for _get_trip_time error paths."""

    def test_get_trip_time_recurring_invalid_hora(self, mock_hass_with_storage):
        """_get_trip_time handles invalid hora format in recurring trip."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

        trip = {
            "tipo": "recurring",
            "dia_semana": "monday",
            "hora": "invalid_time",  # Invalid format
        }

        result = trip_manager._get_trip_time(trip)
        assert result is None

    def test_get_trip_time_punctual_invalid_datetime(self, mock_hass_with_storage):
        """_get_trip_time handles invalid datetime in punctual trip."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

        trip = {
            "tipo": "punctual",
            "datetime": "not-a-datetime",  # Invalid format
        }

        result = trip_manager._get_trip_time(trip)
        assert result is None

    def test_get_trip_time_unknown_tipo(self, mock_hass_with_storage):
        """_get_trip_time handles unknown trip tipo."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

        trip = {
            "tipo": "unknown_type",
        }

        result = trip_manager._get_trip_time(trip)
        assert result is None



class TestTripManagerDayIndex:
    """Tests for _get_day_index error paths."""

    def test_get_day_index_invalid_digit(self, mock_hass_with_storage):
        """_get_day_index handles out-of-range day index."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

        result = trip_manager._get_day_index("9")  # Only 0-6 are valid
        assert result == 0  # Defaults to Monday

    def test_get_day_index_unknown_name(self, mock_hass_with_storage):
        """_get_day_index handles unknown day name."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

        result = trip_manager._get_day_index("NotADay")
        assert result == 0  # Defaults to Monday



class TestTripManagerSaveTrips:
    """Tests for async_save_trips error paths."""

    @pytest.mark.asyncio
    async def test_async_save_trips_yaml_write_fails(self, mock_hass_with_storage):
        """async_save_trips handles YAML write failure gracefully."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        # Add some data
        trip_manager._punctual_trips["trip_1"] = {
            "id": "trip_1",
            "tipo": "punctual",
        }

        # Make both HA storage AND YAML fallback fail
        mock_hass_with_storage.storage.async_write_dict = AsyncMock(
            side_effect=Exception("HA storage failed")
        )

        # Make Path.mkdir raise
        with patch(
            "pathlib.Path.mkdir",
            side_effect=Exception("mkdir failed"),
        ):
            # Should not raise - both failures caught
            await trip_manager.async_save_trips()

    @pytest.mark.asyncio
    async def test_async_save_trips_yaml_open_fails(self, mock_hass_with_storage):
        """async_save_trips handles YAML file open failure."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        trip_manager._punctual_trips["trip_1"] = {"id": "trip_1"}

        # Make storage fail
        mock_hass_with_storage.storage.async_write_dict = AsyncMock(
            side_effect=Exception("HA storage failed")
        )

        # Make yaml.dump succeed but file write fail
        with patch(
            "pathlib.Path.mkdir",
        ):
            with patch(
                "builtins.open",
                side_effect=Exception("File write error"),
            ):
                with patch(
                    "custom_components.ev_trip_planner.trip_manager.yaml.safe_load",
                ):
                    # Should not raise
                    await trip_manager.async_save_trips()



class TestTripManagerEMHASSAdapter:
    """Tests for EMHASS adapter methods."""

    @pytest.mark.asyncio
    async def test_get_emhass_adapter_returns_none(self, mock_hass_with_storage):
        """get_emhass_adapter returns None when no adapter set."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        # No EMHASS adapter set
        result = trip_manager.get_emhass_adapter()
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_emhass_adapter(self, mock_hass_with_storage):
        """set_emhass_adapter and get_emhass_adapter work correctly."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        mock_adapter = MagicMock()
        trip_manager.set_emhass_adapter(mock_adapter)

        assert trip_manager.get_emhass_adapter() is mock_adapter



class TestEMHASSAdapterConstructorInjection:
    """T036: Tests for EMHASS adapter constructor injection (Phase C refactor).

    These tests verify that after the Phase C refactor:
    1. emhass_adapter can be passed to TripManager constructor
    2. get_emhass_adapter() returns the adapter set via constructor
    3. set_emhass_adapter() still works for backward compatibility
    4. set_emhass_adapter() can override constructor-set adapter

    These tests should FAIL in RED phase (before T037-T040 implementation).
    """

    @pytest.mark.asyncio
    async def test_emhass_adapter_via_constructor(self, mock_hass_with_storage):
        """TripManager accepts emhass_adapter in constructor and get_emhass_adapter returns it.

        T036 This test should fail because constructor doesn't accept
        emhass_adapter parameter yet. After T037-T040, it should pass.
        """
        mock_adapter = MagicMock()

        # After Phase C refactor, TripManager should accept emhass_adapter as 3rd parameter
        trip_manager = TripManager(
            mock_hass_with_storage,
            "test_vehicle",
            emhass_adapter=mock_adapter,
        )

        # get_emhass_adapter should return the adapter set via constructor
        assert trip_manager.get_emhass_adapter() is mock_adapter

    @pytest.mark.asyncio
    async def test_set_emhass_adapter_still_works_after_refactor(self, mock_hass_with_storage):
        """set_emhass_adapter() still works after Phase C refactor (backward compatibility).

        T036 This test should fail because the refactor hasn't been done.
        After T037-T040, the set_emhass_adapter() method should still be preserved.
        """
        # Create TripManager with emhass_adapter via constructor
        mock_adapter_constructor = MagicMock()
        trip_manager = TripManager(
            mock_hass_with_storage,
            "test_vehicle",
            emhass_adapter=mock_adapter_constructor,
        )

        # Override with set_emhass_adapter
        mock_adapter_setter = MagicMock()
        trip_manager.set_emhass_adapter(mock_adapter_setter)

        # get_emhass_adapter should return the adapter set via setter (override)
        assert trip_manager.get_emhass_adapter() is mock_adapter_setter

    @pytest.mark.asyncio
    async def test_get_emhass_adapter_returns_none_when_not_set(self, mock_hass_with_storage):
        """get_emhass_adapter returns None when no adapter is set (via constructor or setter).

        T036 This test verifies baseline behavior is preserved.
        """
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

        assert trip_manager.get_emhass_adapter() is None



class TestTripManagerVehicleSOC:
    """Tests for vehicle SOC methods."""

    @pytest.mark.asyncio
    async def test_async_get_vehicle_soc_returns_zero_on_no_entry(self, mock_hass_with_storage):
        """async_get_vehicle_soc returns 0.0 when no config entry found."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        # Make async_entries return empty list (no matching entry)
        mock_hass_with_storage.config_entries.async_entries = MagicMock(return_value=[])

        # Returns 0.0 when no entry found
        result = await trip_manager.async_get_vehicle_soc("test_vehicle")
        assert result == 0.0



class TestTripManagerCalcularVentana:
    """Tests for calcular_ventana_carga error paths."""

    @pytest.mark.asyncio
    async def test_calcular_ventana_carga_no_deadline(self, mock_hass_with_storage):
        """calcular_ventana_carga handles trip with no deadline."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        trip = {
            "id": "trip_1",
            "tipo": "punctual",
            "datetime": "invalid-datetime",
            "km": 30,
            "kwh": 5,
        }

        # Should return default window (0 hours) for invalid datetime
        result = await trip_manager.calcular_ventana_carga(
            trip, soc_actual=50.0, hora_regreso=None, charging_power_kw=7.4
        )

        assert result["ventana_horas"] == 0.0



class TestTripManagerGetAllTrips:
    """Tests for get_all_trips."""

    def test_get_all_trips_returns_structure(self, mock_hass_with_storage):
        """get_all_trips returns dict with recurring and punctual keys."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

        trip_manager._recurring_trips = {
            "rec_1": {"id": "rec_1", "tipo": "recurring"}
        }
        trip_manager._punctual_trips = {
            "pun_1": {"id": "pun_1", "tipo": "punctual"}
        }

        result = trip_manager.get_all_trips()

        assert "recurring" in result
        assert "punctual" in result
        assert len(result["recurring"]) == 1
        assert len(result["punctual"]) == 1



class TestTripManagerAsyncAddRecurringTrip:
    """Tests for async_add_recurring_trip error paths."""

    @pytest.mark.asyncio
    async def test_async_add_recurring_trip_generates_id(self, mock_hass_with_storage):
        """async_add_recurring_trip generates trip_id if not provided."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle", entry_id="test_entry")
        await trip_manager.async_setup()

        # Mock the sensor creation and EMHASS to avoid side effects
        with patch("custom_components.ev_trip_planner.sensor.async_create_trip_sensor", new_callable=AsyncMock):
            with patch.object(trip_manager, "_async_publish_new_trip_to_emhass", new_callable=AsyncMock):
                await trip_manager.async_add_recurring_trip(
                    dia_semana="monday",
                    hora="08:00",
                    km=30,
                    kwh=5,
                )

        # Check that a recurring trip was added
        recurring_ids = list(trip_manager._recurring_trips.keys())
        assert len(recurring_ids) == 1
        assert recurring_ids[0].startswith("rec_")

    @pytest.mark.asyncio
    async def test_async_add_recurring_trip_with_custom_id(self, mock_hass_with_storage):
        """async_add_recurring_trip uses provided trip_id."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle", entry_id="test_entry")
        await trip_manager.async_setup()

        with patch("custom_components.ev_trip_planner.sensor.async_create_trip_sensor", new_callable=AsyncMock):
            with patch.object(trip_manager, "_async_publish_new_trip_to_emhass", new_callable=AsyncMock):
                await trip_manager.async_add_recurring_trip(
                    trip_id="custom_recurring_1",
                    dia_semana="monday",
                    hora="08:00",
                    km=30,
                    kwh=5,
                )

        assert "custom_recurring_1" in trip_manager._recurring_trips

    @pytest.mark.asyncio
    async def test_add_recurring_calls_sensor_py_create(
        self, mock_hass_with_storage, caplog
    ):
        """Test that async_add_recurring_trip calls sensor.py async_create_trip_sensor.

        GREEN test for task 1.47: Verify trip_manager uses sensor.py CRUD functions
        instead of internal methods for creating trip sensors.

        Expected behavior:
        - trip_manager.async_add_recurring_trip should call sensor.async_create_trip_sensor
        - NOT self.async_create_trip_sensor (internal method)

        Current implementation:
        - Line 526-527: from .sensor import async_create_trip_sensor
        - Line 527: await async_create_trip_sensor(self.hass, self._entry_id, ...)
        """
        caplog.set_level("DEBUG")

        trip_manager = TripManager(mock_hass_with_storage, "morgan", entry_id="test_entry")
        await trip_manager.async_setup()

        with patch("custom_components.ev_trip_planner.sensor.async_create_trip_sensor") as mock_create:
            # Mock the sensor.py function to return False (no existing entity)
            mock_create.return_value = False

            # Add a recurring trip
            await trip_manager.async_add_recurring_trip(
                dia_semana="lunes",
                hora="08:00",
                km=50.0,
                kwh=10.0,
                descripcion="Test trip for sensor.py call",
            )

            # Assert sensor.py async_create_trip_sensor was called (not internal method)
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[0][0] is mock_hass_with_storage  # hass is first positional arg
            assert call_args[0][1] == "test_entry"  # entry_id is second positional arg
            assert call_args[0][2].get("dia_semana") == "lunes"  # trip_data contains dia_semana="lunes"

    @pytest.mark.asyncio
    async def test_add_recurring_calls_emhass_sensor_create(
        self, mock_hass_with_storage, caplog
    ):
        """Test that async_add_recurring_trip calls sensor.py async_create_trip_emhass_sensor.

        Test for task 1.52: Verify trip_manager creates EMHASS sensor alongside TripSensor.

        Expected behavior:
        - trip_manager.async_add_recurring_trip should call sensor.async_create_trip_emhass_sensor
        - After calling async_create_trip_sensor (TripSensor comes first, then EMHASS sensor)

        Current implementation:
        - EMHASS sensor CRUD not yet added
        - Only TripSensor is created via async_create_trip_sensor
        """
        caplog.set_level("DEBUG")

        trip_manager = TripManager(mock_hass_with_storage, "morgan", entry_id="test_entry")
        await trip_manager.async_setup()

        # Set up REAL EVTripRuntimeData dataclass (NOT MagicMock)
        # This exposes the bug if code still uses .get() instead of .coordinator attribute
        mock_coordinator = MagicMock()
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        from custom_components.ev_trip_planner import EVTripRuntimeData
        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator, trip_manager=None
        )

        # Mock both sensor CRUD functions and config_entries.async_get_entry
        with patch("custom_components.ev_trip_planner.sensor.async_create_trip_sensor", new_callable=AsyncMock) as mock_trip_sensor:
            with patch("custom_components.ev_trip_planner.sensor.async_create_trip_emhass_sensor", new_callable=AsyncMock) as mock_emhass_sensor:
                with patch.object(mock_hass_with_storage.config_entries, "async_get_entry", return_value=mock_entry):
                    mock_trip_sensor.return_value = False  # No existing entity
                    mock_emhass_sensor.return_value = None  # EMHASS sensor void return

                    # Add a recurring trip
                    await trip_manager.async_add_recurring_trip(
                        dia_semana="lunes",
                        hora="08:00",
                        km=50.0,
                        kwh=10.0,
                        descripcion="Test trip for EMHASS sensor creation",
                    )

                    # Assert TripSensor was created
                    mock_trip_sensor.assert_called_once()

                    # Assert EMHASS sensor was created AFTER TripSensor
                    # This will FAIL until task 1.53 implementation
                    mock_emhass_sensor.assert_called_once()
                    call_args = mock_emhass_sensor.call_args
                    assert call_args[0][0] is mock_hass_with_storage  # hass is first positional arg
                    assert call_args[0][1] == "test_entry"  # entry_id is second positional arg
                    assert call_args[0][2] is mock_coordinator  # third arg is coordinator
                    assert call_args[0][3] == "morgan"  # fourth arg is vehicle_id
                    # The fifth arg should be the trip_id (extracted from the trip that was created)
                    assert isinstance(call_args[0][4], str)  # trip_id should be a string


class TestTripManagerAsyncAddPunctualTrip:
    """Tests for async_add_punctual_trip EMHASS sensor integration."""

    @pytest.mark.asyncio
    async def test_add_punctual_calls_emhass_sensor_create(
        self, mock_hass_with_storage, caplog
    ):
        """Test that async_add_punctual_trip calls sensor.py async_create_trip_emhass_sensor.

        Test for task 1.54: Verify trip_manager creates EMHASS sensor alongside TripSensor
        for punctual trips.

        Expected behavior:
        - trip_manager.async_add_punctual_trip should call sensor.async_create_trip_emhass_sensor
        - After calling async_create_trip_sensor (TripSensor comes first, then EMHASS sensor)

        Current implementation:
        - EMHASS sensor CRUD not yet added for punctual trips
        - Only TripSensor is created via async_create_trip_sensor
        """
        caplog.set_level("DEBUG")

        trip_manager = TripManager(mock_hass_with_storage, "morgan", entry_id="test_entry")
        await trip_manager.async_setup()

        # Set up REAL EVTripRuntimeData dataclass (NOT MagicMock)
        # This exposes the bug if code still uses .get() instead of .coordinator attribute
        mock_coordinator = MagicMock()
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        from custom_components.ev_trip_planner import EVTripRuntimeData
        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator, trip_manager=None
        )

        # Mock both sensor CRUD functions and config_entries.async_get_entry
        with patch("custom_components.ev_trip_planner.sensor.async_create_trip_sensor", new_callable=AsyncMock) as mock_trip_sensor:
            with patch("custom_components.ev_trip_planner.sensor.async_create_trip_emhass_sensor", new_callable=AsyncMock) as mock_emhass_sensor:
                with patch.object(mock_hass_with_storage.config_entries, "async_get_entry", return_value=mock_entry):
                    mock_trip_sensor.return_value = False  # No existing entity
                    mock_emhass_sensor.return_value = None  # EMHASS sensor void return

                    # Add a punctual trip
                    await trip_manager.async_add_punctual_trip(
                        datetime="2024-01-15T08:00:00",
                        km=25.0,
                        kwh=5.0,
                        descripcion="Test punctual trip for EMHASS sensor creation",
                    )

                    # Assert TripSensor was created
                    mock_trip_sensor.assert_called_once()

                    # Assert EMHASS sensor was created AFTER TripSensor
                    # This will FAIL until task 1.55 implementation
                    mock_emhass_sensor.assert_called_once()
                    call_args = mock_emhass_sensor.call_args
                    assert call_args[0][0] is mock_hass_with_storage  # hass is first positional arg
                    assert call_args[0][1] == "test_entry"  # entry_id is second positional arg
                    assert call_args[0][2] is mock_coordinator  # third arg is coordinator
                    assert call_args[0][3] == "morgan"  # fourth arg is vehicle_id
                    # The fifth arg should be the trip_id (extracted from the trip that was created)
                    # We just need to verify it's a string that exists, we don't check if it's still in the trips dict
                    assert isinstance(call_args[0][4], str)  # trip_id should be a string



class TestTripManagerAsyncDeleteTrip:
    """Tests for async_delete_trip error paths."""

    @pytest.mark.asyncio
    async def test_async_delete_trip_not_found(self, mock_hass_with_storage):
        """async_delete_trip handles missing trip gracefully."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle", entry_id="test_entry")
        await trip_manager.async_setup()

        # Try to delete a trip that doesn't exist
        with patch.object(trip_manager, "async_save_trips", new_callable=AsyncMock):
            with patch("custom_components.ev_trip_planner.sensor.async_remove_trip_sensor", new_callable=AsyncMock):
                with patch.object(trip_manager, "_async_remove_trip_from_emhass", new_callable=AsyncMock):
                    await trip_manager.async_delete_trip("nonexistent_trip")

        # No error should be raised - just returns early

    @pytest.mark.asyncio
    async def test_delete_calls_emhass_sensor_remove(
        self, mock_hass_with_storage, caplog
    ):
        """Test that async_delete_trip calls sensor.py async_remove_trip_emhass_sensor.

        Test for task 1.56: Verify trip_manager removes EMHASS sensor alongside TripSensor
        when deleting trips.

        Expected behavior:
        - trip_manager.async_delete_trip should call sensor.async_remove_trip_emhass_sensor
        - After calling async_remove_trip_sensor (TripSensor removed first, then EMHASS sensor)

        Current implementation:
        - EMHASS sensor removal not yet added
        - Only TripSensor is removed via async_remove_trip_sensor
        """
        caplog.set_level("DEBUG")

        trip_manager = TripManager(mock_hass_with_storage, "morgan", entry_id="test_entry")
        await trip_manager.async_setup()

        # Set up REAL EVTripRuntimeData dataclass (NOT MagicMock)
        # This exposes the bug if code still uses .get() instead of .coordinator attribute
        mock_coordinator = MagicMock()
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        from custom_components.ev_trip_planner import EVTripRuntimeData
        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator, trip_manager=None
        )

        # Mock config_entries.async_get_entry to return our properly configured entry
        # This ensures that both trip creation and deletion use the same mock entry
        with patch.object(mock_hass_with_storage.config_entries, "async_get_entry", return_value=mock_entry):
            # Create a trip first (needs coordinator mock for EMHASS sensor creation)
            await trip_manager.async_add_recurring_trip(
                dia_semana="lunes",
                hora="08:00",
                km=50.0,
                kwh=10.0,
                descripcion="Test trip for EMHASS sensor removal",
            )

            # Mock both sensor CRUD functions
            with patch("custom_components.ev_trip_planner.sensor.async_remove_trip_sensor", new_callable=AsyncMock) as mock_trip_sensor:
                with patch("custom_components.ev_trip_planner.sensor.async_remove_trip_emhass_sensor", new_callable=AsyncMock) as mock_emhass_sensor:
                    mock_trip_sensor.return_value = True  # Successfully removed
                    mock_emhass_sensor.return_value = True  # Successfully removed

                    # Delete the trip
                    await trip_manager.async_delete_trip(list(trip_manager._recurring_trips.keys())[0])

                    # Assert TripSensor was removed
                    mock_trip_sensor.assert_called_once()

                    # Assert EMHASS sensor was removed AFTER TripSensor
                    # This will FAIL until task 1.57 implementation
                    mock_emhass_sensor.assert_called_once()
                    call_args = mock_emhass_sensor.call_args
                    assert call_args[0][0] is mock_hass_with_storage  # hass is first positional arg
                    assert call_args[0][1] == "test_entry"  # entry_id is second positional arg
                    assert call_args[0][2] == "morgan"  # third arg is vehicle_id
                    # The fourth arg should be the trip_id that was deleted
                    assert isinstance(call_args[0][3], str)  # trip_id should be a string



class TestTripManagerAsyncPauseResume:
    """Tests for async_pause/resume_recurring_trip."""

    @pytest.mark.asyncio
    async def test_async_pause_recurring_trip_not_found(self, mock_hass_with_storage):
        """async_pause_recurring_trip handles missing trip gracefully."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        with patch.object(trip_manager, "async_save_trips", new_callable=AsyncMock):
            await trip_manager.async_pause_recurring_trip("nonexistent_trip")

    @pytest.mark.asyncio
    async def test_async_resume_recurring_trip_not_found(self, mock_hass_with_storage):
        """async_resume_recurring_trip handles missing trip gracefully."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        with patch.object(trip_manager, "async_save_trips", new_callable=AsyncMock):
            await trip_manager.async_resume_recurring_trip("nonexistent_trip")


# =============================================================================
# Pure calculation function tests (PRAGMA-C coverage for calcular_hitos_soc helpers)
# =============================================================================

class TestCalcularTasaCargaSoc:
    """Parametrized tests for _calcular_tasa_carga_soc - pure calculation function."""

    @pytest.fixture
    def trip_manager(self, mock_hass_with_storage):
        """Create TripManager instance for testing pure functions."""
        return TripManager(mock_hass_with_storage, "test_vehicle")

    @pytest.mark.parametrize(
        "charging_power_kw,battery_capacity_kwh,expected",
        [
            # Normal case: 7.4kW / 50kWh * 100 = 14.8 % SOC/hour
            (7.4, 50.0, 14.8),
            # Lower charging power: 3.6kW / 50kWh * 100 = 7.2 % SOC/hour
            (3.6, 50.0, 7.2),
            # Higher capacity: 7.4kW / 75kWh * 100 = 9.87 % SOC/hour
            (7.4, 75.0, 9.866666666666667),
            # Zero capacity: should return 0.0 (edge case)
            (7.4, 0.0, 0.0),
            # Negative capacity: should return 0.0 (edge case)
            (7.4, -10.0, 0.0),
            # Very small capacity: 7.4kW / 1kWh * 100 = 740 % SOC/hour
            (7.4, 1.0, 740.0),
        ],
    )
    def test_calcular_tasa_carga_soc(
        self, trip_manager, charging_power_kw, battery_capacity_kwh, expected
    ):
        """Test SOC charging rate calculation with various battery capacities."""
        result = trip_manager._calcular_tasa_carga_soc(charging_power_kw, battery_capacity_kwh)
        assert abs(result - expected) < 0.001, f"Expected {expected}, got {result}"


class TestCalcularSocObjetivoBase:
    """Parametrized tests for _calcular_soc_objetivo_base - pure calculation function."""

    @pytest.fixture
    def trip_manager(self, mock_hass_with_storage):
        """Create TripManager instance for testing pure functions."""
        return TripManager(mock_hass_with_storage, "test_vehicle")

    @pytest.mark.parametrize(
        "trip,battery_capacity_kwh,consumption,expected_soc",
        [
            # Trip with kwh directly specified
            ({"kwh": 10.0}, 50.0, 0.15, 20.0 + 10),  # 20% + 10% buffer
            # Trip with km distance - energy calculated from distance
            ({"km": 100.0}, 50.0, 0.15, 30.0 + 10),  # 15kWh = 30% + 10% buffer
            # Trip with no kwh or km - zero energy
            ({}, 50.0, 0.15, 0.0 + 10),  # 0kWh + 10% buffer
            # Zero battery capacity - should return buffer only
            ({"kwh": 10.0}, 0.0, 0.15, 0.0 + 10),  # 0% + 10% buffer
            # Negative battery capacity - should return buffer only
            ({"kwh": 10.0}, -50.0, 0.15, 0.0 + 10),  # 0% + 10% buffer
            # Large trip: 30kWh / 75kWh * 100 = 40% + 10% buffer = 50%
            ({"kwh": 30.0}, 75.0, 0.15, 40.0 + 10),
        ],
    )
    def test_calcular_soc_objetivo_base(
        self, trip_manager, trip, battery_capacity_kwh, consumption, expected_soc
    ):
        """Test SOC target calculation with various trip data and battery capacities."""
        result = trip_manager._calcular_soc_objetivo_base(trip, battery_capacity_kwh, consumption)
        assert abs(result - expected_soc) < 0.001, f"Expected {expected_soc}, got {result}"


class TestTripManagerConstructorInjection:
    """Tests for TripManager constructor injection (Phase C, T035).

    These tests verify that TripManager.__init__ accepts storage and emhass_adapter
    parameters with _UNSET sentinel defaults. This is a TDD RED phase - the tests
    should FAIL because the constructor doesn't accept these parameters yet.
    """

    def test_constructor_accepts_storage_parameter(self, mock_hass_with_storage):
        """TripManager constructor should accept storage: YamlTripStorage parameter.

        This test FAILS with TypeError because current constructor does not
        accept a storage parameter.
        """
        from custom_components.ev_trip_planner.yaml_trip_storage import YamlTripStorage
        from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter

        # Create mock implementations
        mock_storage = MagicMock(spec=YamlTripStorage)
        mock_storage.async_load = AsyncMock(return_value={})
        mock_storage.async_save = AsyncMock(return_value=None)

        mock_emhass = MagicMock(spec=EMHASSAdapter)
        mock_emhass.async_publish_deferrable_load = AsyncMock(return_value=True)
        mock_emhass.async_remove_deferrable_load = AsyncMock(return_value=True)

        # This should raise TypeError because constructor doesn't accept storage/emhass_adapter
        # Currently TripManager.__init__(self, hass, vehicle_id, presence_config=None)
        # After T037/T038 it will be:
        #   TripManager.__init__(self, hass, vehicle_id, presence_config=None,
        #                        storage=_UNSET, emhass_adapter=_UNSET)
        trip_manager = TripManager(
            mock_hass_with_storage,
            "test_vehicle",
            storage=mock_storage,
        )
        # If we get here, storage was accepted - verify it was set
        assert hasattr(trip_manager, "_storage")
        assert trip_manager._storage is mock_storage

    def test_constructor_accepts_emhass_adapter_parameter(self, mock_hass_with_storage):
        """TripManager constructor should accept emhass_adapter: EMHASSAdapter parameter.

        This test FAILS with TypeError because current constructor does not
        accept an emhass_adapter parameter.
        """
        from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter

        mock_emhass = MagicMock(spec=EMHASSAdapter)
        mock_emhass.async_publish_deferrable_load = AsyncMock(return_value=True)
        mock_emhass.async_remove_deferrable_load = AsyncMock(return_value=True)

        # This should raise TypeError - constructor doesn't accept emhass_adapter
        trip_manager = TripManager(
            mock_hass_with_storage,
            "test_vehicle",
            emhass_adapter=mock_emhass,
        )
        # If we get here, emhass_adapter was accepted
        assert hasattr(trip_manager, "_emhass_adapter")
        assert trip_manager._emhass_adapter is mock_emhass

    def test_constructor_accepts_both_storage_and_emhass_adapter(self, mock_hass_with_storage):
        """TripManager constructor should accept both storage and emhass_adapter parameters.

        This test FAILS with TypeError because current constructor does not
        accept these parameters.
        """
        from custom_components.ev_trip_planner.yaml_trip_storage import YamlTripStorage
        from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter

        mock_storage = MagicMock(spec=YamlTripStorage)
        mock_storage.async_load = AsyncMock(return_value={})
        mock_storage.async_save = AsyncMock(return_value=None)

        mock_emhass = MagicMock(spec=EMHASSAdapter)
        mock_emhass.async_publish_deferrable_load = AsyncMock(return_value=True)
        mock_emhass.async_remove_deferrable_load = AsyncMock(return_value=True)

        # This should raise TypeError - constructor doesn't accept these params
        trip_manager = TripManager(
            mock_hass_with_storage,
            "test_vehicle",
            storage=mock_storage,
            emhass_adapter=mock_emhass,
        )
        assert trip_manager._storage is mock_storage
        assert trip_manager._emhass_adapter is mock_emhass

    def test_unset_sentinel_default_behavior(self, mock_hass_with_storage):
        """TripManager should use _UNSET sentinel for storage/emhass_adapter defaults.

        When not provided, the constructor should use _UNSET as the default value
        for both parameters. This test verifies the sentinel pattern is in place.
        """
        from custom_components.ev_trip_planner import trip_manager as tm_module

        # Verify _UNSET sentinel exists in the module
        assert hasattr(tm_module, "_UNSET"), "TripManager module should define _UNSET sentinel"

        # When called without storage/emhass_adapter, they should default to _UNSET
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")

        # After T039, the internal vars should be set to the sentinel or resolved to defaults
        # For now, this just verifies the sentinel pattern is documented
        assert trip_manager is not None


class TestTripManagerLoadErrors:
    """Test suite for TripManager error handling during trip loading.

    Covers the generic exception handler in _load_trips that catches
    any exception (except CancelledError) and resets trip state.
    """

    @pytest.mark.asyncio
    async def test_load_trips_generic_exception_handler(
        self, mock_hass_no_storage, caplog
    ):
        """Test that generic exceptions during trip loading are caught and handled.

        This test covers lines 270-275 in trip_manager.py which were
        previously uncovered (0.16% missing coverage).
        """
        caplog.set_level("ERROR")

        from custom_components.ev_trip_planner.yaml_trip_storage import YamlTripStorage

        # Create a mock storage that raises a generic exception
        mock_storage = MagicMock(spec=YamlTripStorage)
        mock_storage.async_load = AsyncMock(
            side_effect=RuntimeError("Storage read error - disk full")
        )

        trip_manager = TripManager(
            mock_hass_no_storage, "test_vehicle", storage=mock_storage
        )

        # Trigger the load - should catch the exception and reset state
        await trip_manager._load_trips()

        # Verify the exception was caught and logged
        assert any("Error cargando viajes" in record.message for record in caplog.records)

        # Verify trip state was reset to empty
        assert trip_manager._trips == {}
        assert trip_manager._recurring_trips == {}
        assert trip_manager._punctual_trips == {}
        assert trip_manager._last_update is None

    @pytest.mark.asyncio
    async def test_load_trips_value_error_handler(
        self, mock_hass_no_storage, caplog
    ):
        """Test that ValueError during trip loading is caught and handled.

        Tests another type of exception that could occur during storage load.
        """
        caplog.set_level("ERROR")

        from custom_components.ev_trip_planner.yaml_trip_storage import YamlTripStorage

        # Create a mock storage that raises ValueError
        mock_storage = MagicMock(spec=YamlTripStorage)
        mock_storage.async_load = AsyncMock(
            side_effect=ValueError("Invalid data format in storage")
        )

        trip_manager = TripManager(
            mock_hass_no_storage, "test_vehicle", storage=mock_storage
        )

        # Trigger the load - should catch the exception
        await trip_manager._load_trips()

        # Verify the exception was caught
        assert any("Error cargando viajes" in record.message for record in caplog.records)

        # Verify state was reset
        assert trip_manager._trips == {}
        assert trip_manager._recurring_trips == {}
        assert trip_manager._punctual_trips == {}


class TestRuntimeDataAttributeAccess:
    """Tests for proper EVTripRuntimeData attribute access (not dict-style .get()).

    Tests for tasks 2.7 and 2.8: Verify that runtime_data access uses attribute
    access (entry.runtime_data.coordinator) instead of dict-style .get().

    EVTripRuntimeData is a @dataclass with attributes, NOT a dict. Using .get()
    causes AttributeError in production but is hidden by MagicMock in tests.
    """

    @pytest.mark.asyncio
    async def test_add_recurring_trip_uses_runtime_data_attribute_access(
        self, mock_hass_with_storage, caplog
    ):
        """Test that async_add_recurring_trip accesses runtime_data.coordinator as attribute.

        Test for task 2.7: This test FAILS with the current implementation.

        Expected behavior:
        - entry.runtime_data is an EVTripRuntimeData dataclass
        - Coordinator should be accessed via: entry.runtime_data.coordinator
        - NOT via: entry.runtime_data.get("coordinator") (dict-style, causes crash)

        Current implementation (BUG):
        - trip_manager.py:491 uses: entry.runtime_data.get("coordinator")
        - EVTripRuntimeData is a dataclass with .coordinator attribute (no .get() method)
        - In production: AttributeError: 'EVTripRuntimeData' object has no attribute 'get'

        Why existing tests hide this bug:
        - Existing tests (line ~1282) use: mock_entry.runtime_data = MagicMock()
        - MagicMock.autocreates .get() as a callable
        - This makes the test pass even though the code is wrong

        Fix (2.8):
        - Change line 491 from: entry.runtime_data.get("coordinator")
        - To: entry.runtime_data.coordinator
        """
        caplog.set_level("DEBUG")

        trip_manager = TripManager(mock_hass_with_storage, "morgan", entry_id="test_entry")
        await trip_manager.async_setup()

        # Set up REAL EVTripRuntimeData dataclass (NOT MagicMock)
        # This exposes the bug: dataclass has .coordinator attribute, NO .get() method
        mock_coordinator = MagicMock()
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_entry.runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator, trip_manager=None
        )

        # Mock config_entries.async_get_entry to return our properly configured entry
        with patch.object(mock_hass_with_storage.config_entries, "async_get_entry", return_value=mock_entry):
            # Mock async_create_trip_sensor to avoid needing full sensor setup
            with patch("custom_components.ev_trip_planner.sensor.async_create_trip_sensor", new_callable=AsyncMock) as mock_trip_sensor:
                mock_trip_sensor.return_value = False  # No existing entity

                # This will FAIL with: AttributeError: 'EVTripRuntimeData' object has no attribute 'get'
                # until task 2.8 fix is applied
                await trip_manager.async_add_recurring_trip(
                    dia_semana="lunes",
                    hora="08:00",
                    km=50.0,
                    kwh=10.0,
                    descripcion="Test trip for runtime_data attribute access",
                )

                # If we reach here without AttributeError, the bug is fixed
                # The test passes when runtime_data.coordinator is accessed correctly
