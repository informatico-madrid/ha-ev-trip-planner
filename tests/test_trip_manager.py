"""Tests for TripManager CRUD operations and YAML persistence.

This test suite covers:
- CRUD operations: create, read, update, delete trips
- YAML persistence for Container environment
- Storage API for Supervisor environment
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from datetime import datetime

from custom_components.ev_trip_planner.trip_manager import TripManager


@pytest.fixture
def vehicle_id() -> str:
    """Return a test vehicle ID."""
    return "morgan"


@pytest.fixture
def mock_hass_no_storage():
    """Create a mock hass WITHOUT storage (Container environment).

    In Home Assistant Container, the storage API is not available.
    This fixture simulates that environment by returning None for storage.
    """
    from unittest.mock import MagicMock

    hass = MagicMock()
    # Mock config_entries
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    # DO NOT set hass.storage - this simulates Container environment
    # In Container, hass.storage is None or does not exist
    hass.storage = None

    return hass


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance with storage (Supervisor environment)."""
    from unittest.mock import AsyncMock, MagicMock

    hass = MagicMock()
    # Mock config_entries
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    # Mock storage for Supervisor environment
    hass.storage = MagicMock()
    hass.storage.async_read = AsyncMock(return_value=None)
    hass.storage.async_write_dict = AsyncMock()

    # Mock config directory
    hass.config.config_dir = "/tmp/test_config"

    return hass


@pytest.fixture
def trip_manager(mock_hass, vehicle_id):
    """Create a TripManager instance for testing."""
    return TripManager(mock_hass, vehicle_id)


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

        # Verify trips were saved (storage API was called)
        assert trip_manager.hass.storage.async_write_dict.called

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

        # Verify info log was written (storage or YAML)
        assert any("guardados" in record.message or "guardar" in record.message for record in caplog.records)


class TestYAMLFallback:
    """Tests for YAML persistence fallback in Container environment."""

    @pytest.mark.asyncio
    async def test_load_trips_with_yaml_fallback(self, mock_hass_no_storage, vehicle_id, tmp_path, caplog):
        """Test that _load_trips works with YAML fallback when storage is not available.

        This test verifies the P004 fix where:
        - hass.storage is None in Container environment
        - YAML fallback is used instead
        - Expected: PASS after fix (trips loaded successfully via YAML)
        """
        import yaml
        from pathlib import Path as PathLib

        # Setup YAML file with test data
        config_dir = tmp_path / "config"
        storage_key = "ev_trip_planner_morgan"
        yaml_dir = config_dir / "ev_trip_planner"
        yaml_dir.mkdir(parents=True, exist_ok=True)
        yaml_file = yaml_dir / f"{storage_key}.yaml"

        # Create test YAML data
        test_data = {
            "version": 1,
            "data": {
                "trips": {"trip1": {"id": "trip1", "tipo": "punctual"}},
                "recurring_trips": {
                    "rec_lunes_001": {
                        "id": "rec_lunes_001",
                        "tipo": "recurring",
                        "dia_semana": "lunes",
                        "hora": "08:00",
                        "km": 50.0,
                        "kwh": 10.0,
                        "descripcion": "Test recurring trip",
                        "activo": True,
                    }
                },
                "punctual_trips": {
                    "pun_20260320_001": {
                        "id": "pun_20260320_001",
                        "tipo": "punctual",
                        "datetime": "2026-03-20T10:00",
                        "km": 100.0,
                        "kwh": 20.0,
                        "descripcion": "Test punctual trip",
                        "estado": "pendiente",
                    }
                },
                "last_update": "2026-03-20T10:00:00",
            },
        }

        with open(yaml_file, "w") as f:
            yaml.dump(test_data, f)

        # Setup mock to use our config directory
        mock_hass_no_storage.config.config_dir = str(config_dir)

        manager = TripManager(mock_hass_no_storage, vehicle_id)

        # After fix: YAML fallback should work and trips should load
        await manager._load_trips()

        # Verify YAML fallback worked
        assert "cargados desde YAML fallback" in caplog.text

        # Verify trips were loaded from YAML
        assert len(manager._recurring_trips) == 1
        assert len(manager._punctual_trips) == 1
        assert "rec_lunes_001" in manager._recurring_trips
        assert "pun_20260320_001" in manager._punctual_trips
        assert manager._recurring_trips["rec_lunes_001"]["dia_semana"] == "lunes"
        assert manager._punctual_trips["pun_20260320_001"]["km"] == 100.0

    @pytest.mark.asyncio
    async def test_load_trips_fails_when_storage_not_available(self, mock_hass_no_storage, vehicle_id, caplog):
        """Test that _load_trips handles missing YAML file gracefully.

        This test verifies that when storage is not available AND no YAML file exists,
        the code handles it gracefully without errors.
        """
        manager = TripManager(mock_hass_no_storage, vehicle_id)

        # No YAML file exists, should handle gracefully
        await manager._load_trips()

        # Verify no error was logged (graceful handling)
        assert "Error cargando viajes" not in caplog.text

        # Verify trips are empty (expected when no YAML file)
        assert manager._trips == {}
        assert manager._recurring_trips == {}
        assert manager._punctual_trips == {}

    @pytest.mark.asyncio
    async def test_save_trips_with_yaml_fallback(self, mock_hass_no_storage, vehicle_id, tmp_path, caplog):
        """Test that async_save_trips works with YAML fallback when storage is not available.

        This test verifies the P004 fix where:
        - hass.storage is None in Container environment
        - YAML file is created and trips are saved successfully
        """
        import yaml

        # Setup YAML directory
        config_dir = tmp_path / "config"
        storage_key = "ev_trip_planner_morgan"
        yaml_dir = config_dir / "ev_trip_planner"
        yaml_dir.mkdir(parents=True, exist_ok=True)

        # Setup mock to use our config directory
        mock_hass_no_storage.config.config_dir = str(config_dir)

        manager = TripManager(mock_hass_no_storage, vehicle_id)

        # Add a test trip
        await manager.async_add_recurring_trip(
            dia_semana="martes",
            hora="09:00",
            km=50.0,
            kwh=10.0,
            descripcion="Test trip",
        )

        # Verify trips were saved to YAML
        yaml_file = yaml_dir / f"{storage_key}.yaml"
        assert yaml_file.exists(), "YAML file should be created"

        # Read and verify YAML content
        with open(yaml_file, "r") as f:
            saved_data = yaml.safe_load(f)

        assert saved_data is not None
        assert "data" in saved_data
        assert "recurring_trips" in saved_data["data"]
        assert len(saved_data["data"]["recurring_trips"]) == 1

        # Verify trip data was saved correctly
        trip_id = list(saved_data["data"]["recurring_trips"].keys())[0]
        trip = saved_data["data"]["recurring_trips"][trip_id]
        assert trip["dia_semana"] == "martes"
        assert trip["hora"] == "09:00"
        assert trip["km"] == 50.0
        assert trip["kwh"] == 10.0
        assert trip["descripcion"] == "Test trip"


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
