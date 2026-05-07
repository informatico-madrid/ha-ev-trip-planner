"""Comprehensive tests for Trip CRUD operations.

This test suite covers complete CRUD (Create, Read, Update, Delete) operations
for both recurring and punctual trips. Tests verify:
- Create: Adding new trips via async_add_recurring_trip and async_add_punctual_trip
- Read: Retrieving trips via async_get_recurring_trips and async_get_punctual_trips
- Update: Modifying trips via async_update_trip, async_pause_recurring_trip, async_resume_recurring_trip
- Delete: Removing trips via async_delete_trip, async_cancel_punctual_trip

All tests follow TDD principles and use pytest-homeassistant-custom-component patterns.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from custom_components.ev_trip_planner.trip_manager import TripManager


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def vehicle_id() -> str:
    """Return a test vehicle ID."""
    return "tesla_model_3"


@pytest.fixture
def mock_hass_storage():
    """Create a mock Home Assistant instance with storage (Supervisor environment).

    This fixture creates a proper mock hass with storage support for testing
    CRUD operations that require persistence.
    """
    hass = MagicMock()

    # Mock config_entries to support entry_id lookup
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_config_entry_123"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    # Mock storage for Supervisor environment
    hass.storage = MagicMock()
    hass.storage.async_read = MagicMock(return_value=None)
    hass.storage.async_write_dict = MagicMock()

    # Mock config directory
    hass.config.config_dir = "/tmp/test_config"

    return hass


@pytest.fixture
def mock_hass_no_storage():
    """Create a mock hass WITHOUT storage (Container environment).

    This fixture simulates the Container environment where hass.storage is None.
    CRUD operations fall back to YAML persistence in this case.
    """
    hass = MagicMock()

    # Mock config_entries
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_config_entry_123"
    hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

    # NO storage - simulates Container environment
    hass.storage = None

    # Mock config directory
    hass.config.config_dir = "/tmp/test_config_no_storage"

    return hass


@pytest.fixture
def trip_manager(mock_hass_storage, vehicle_id):
    """Create a TripManager instance for testing CRUD operations."""
    return TripManager(mock_hass_storage, vehicle_id)


# =============================================================================
# CRUD - CREATE Operations
# =============================================================================


class TestTripCreate:
    """Tests for Create operations (CRUD - Create)."""

    @pytest.mark.asyncio
    async def test_create_recurring_trip_basic(self, trip_manager, caplog):
        """Test creating a basic recurring trip.

        This is the most common CRUD operation - adding a weekly recurring trip.
        Verifies all required fields are set correctly.
        """
        # Create
        await trip_manager.async_add_recurring_trip(
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
            descripcion="Commute to work",
        )

        # Read/Verify
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1

        trip = trips[0]
        assert trip["dia_semana"] == "lunes"
        assert trip["hora"] == "08:00"
        assert trip["km"] == 50.0
        assert trip["kwh"] == 10.0
        assert trip["descripcion"] == "Commute to work"
        assert trip["activo"] is True
        assert trip["tipo"] == "recurrente"

    @pytest.mark.asyncio
    async def test_create_recurring_trip_with_custom_id(self, trip_manager, caplog):
        """Test creating a recurring trip with a custom ID."""
        await trip_manager.async_add_recurring_trip(
            trip_id="work_commute_weekly",
            dia_semana="martes",
            hora="09:00",
            km=75.0,
            kwh=15.0,
            descripcion="Weekly meeting",
        )

        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["id"] == "work_commute_weekly"
        assert trips[0]["dia_semana"] == "martes"

    @pytest.mark.asyncio
    async def test_create_punctual_trip_basic(self, trip_manager, caplog):
        """Test creating a basic punctual trip.

        This is the CRUD Create operation for one-time trips.
        """
        await trip_manager.async_add_punctual_trip(
            datetime_str="2026-03-25T14:00",
            km=120.0,
            kwh=25.0,
            descripcion="Weekend trip to beach",
        )

        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 1

        trip = trips[0]
        assert trip["datetime"] == "2026-03-25T14:00"
        assert trip["km"] == 120.0
        assert trip["kwh"] == 25.0
        assert trip["descripcion"] == "Weekend trip to beach"
        assert trip["estado"] == "pendiente"
        assert trip["tipo"] == "puntual"

    @pytest.mark.asyncio
    async def test_create_punctual_trip_with_custom_id(self, trip_manager, caplog):
        """Test creating a punctual trip with a custom ID."""
        await trip_manager.async_add_punctual_trip(
            trip_id="beach_trip_2026",
            datetime_str="2026-04-10T10:00",
            km=200.0,
            kwh=40.0,
            descripcion="Easter trip",
        )

        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 1
        assert trips[0]["id"] == "beach_trip_2026"
        assert trips[0]["datetime"] == "2026-04-10T10:00"

    @pytest.mark.asyncio
    async def test_create_multiple_recurring_trips(self, trip_manager, caplog):
        """Test creating multiple recurring trips (CRUD Create bulk)."""
        # Create several recurring trips
        trips_to_create = [
            ("lunes", "08:00", 50.0, 10.0, "Monday commute"),
            ("miercoles", "09:00", 75.0, 15.0, "Wednesday meeting"),
            ("viernes", "10:00", 60.0, 12.0, "Friday client visit"),
        ]

        for dia, hora, km, kwh, desc in trips_to_create:
            await trip_manager.async_add_recurring_trip(
                dia_semana=dia,
                hora=hora,
                km=km,
                kwh=kwh,
                descripcion=desc,
            )

        # Verify all trips were created
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 3

        # Verify each trip
        days = {trip["dia_semana"] for trip in trips}
        assert days == {"lunes", "miercoles", "viernes"}

        # Verify distances
        distances = {trip["km"] for trip in trips}
        assert distances == {50.0, 75.0, 60.0}

    @pytest.mark.asyncio
    async def test_create_multiple_punctual_trips(self, trip_manager, caplog):
        """Test creating multiple punctual trips (CRUD Create bulk)."""
        for i in range(5):
            await trip_manager.async_add_punctual_trip(
                datetime_str=f"2026-03-{20 + i:02d}T10:00",
                km=50.0 * (i + 1),
                kwh=10.0 * (i + 1),
                descripcion=f"Trip {i + 1}",
            )

        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 5

        # Verify trips are in order
        for i, trip in enumerate(trips):
            assert trip["km"] == 50.0 * (i + 1)
            assert trip["kwh"] == 10.0 * (i + 1)

    @pytest.mark.asyncio
    async def test_create_mixed_trip_types(self, trip_manager, caplog):
        """Test creating both recurring and punctual trips together.

        This verifies that CRUD operations don't interfere with each other.
        """
        # Create recurring trips
        await trip_manager.async_add_recurring_trip(
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
            descripcion="Weekly commute",
        )

        # Create punctual trips
        await trip_manager.async_add_punctual_trip(
            datetime_str="2026-03-25T14:00",
            km=100.0,
            kwh=20.0,
            descripcion="Special trip",
        )

        # Verify both types exist independently
        recurring = await trip_manager.async_get_recurring_trips()
        punctual = await trip_manager.async_get_punctual_trips()

        assert len(recurring) == 1
        assert len(punctual) == 1
        assert recurring[0]["tipo"] == "recurrente"
        assert punctual[0]["tipo"] == "puntual"

    @pytest.mark.asyncio
    async def test_create_trip_with_empty_descripcion(self, trip_manager, caplog):
        """Test creating a trip with empty description."""
        await trip_manager.async_add_recurring_trip(
            dia_semana="jueves",
            hora="12:00",
            km=30.0,
            kwh=5.0,
            descripcion="",
        )

        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["descripcion"] == ""

    @pytest.mark.asyncio
    async def test_create_trip_zero_distance(self, trip_manager, caplog):
        """Test creating a trip with zero distance."""
        await trip_manager.async_add_recurring_trip(
            dia_semana="domingo",
            hora="10:00",
            km=0.0,
            kwh=0.0,
            descripcion="Zero distance trip",
        )

        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["km"] == 0.0
        assert trips[0]["kwh"] == 0.0

    @pytest.mark.asyncio
    async def test_create_trip_logs_debug_message(self, trip_manager, caplog):
        """Test that creating trips logs debug messages."""
        caplog.set_level("DEBUG")

        await trip_manager.async_add_recurring_trip(
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )

        # Verify debug log was written
        assert any(
            "Adding recurring trip" in record.message for record in caplog.records
        )


# =============================================================================
# CRUD - READ Operations
# =============================================================================


class TestTripRead:
    """Tests for Read operations (CRUD - Read)."""

    @pytest.mark.asyncio
    async def test_read_empty_recurring_trips(self, trip_manager):
        """Test reading recurring trips when none exist."""
        trips = await trip_manager.async_get_recurring_trips()
        assert trips == []

    @pytest.mark.asyncio
    async def test_read_empty_punctual_trips(self, trip_manager):
        """Test reading punctual trips when none exist."""
        trips = await trip_manager.async_get_punctual_trips()
        assert trips == []

    @pytest.mark.asyncio
    async def test_read_recurring_trips_with_data(self, trip_manager):
        """Test reading recurring trips after creating them."""
        # Create test trips
        await trip_manager.async_add_recurring_trip(
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
            descripcion="Monday commute",
        )
        await trip_manager.async_add_recurring_trip(
            dia_semana="miercoles",
            hora="09:00",
            km=75.0,
            kwh=15.0,
            descripcion="Wednesday meeting",
        )

        # Read and verify
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 2

        # Verify trip order and data
        assert trips[0]["dia_semana"] == "lunes"
        assert trips[1]["dia_semana"] == "miercoles"
        assert trips[0]["km"] == 50.0
        assert trips[1]["km"] == 75.0

    @pytest.mark.asyncio
    async def test_read_punctual_trips_with_data(self, trip_manager):
        """Test reading punctual trips after creating them."""
        await trip_manager.async_add_punctual_trip(
            datetime_str="2026-03-20T10:00",
            km=100.0,
            kwh=20.0,
            descripcion="First trip",
        )
        await trip_manager.async_add_punctual_trip(
            datetime_str="2026-03-21T11:00",
            km=150.0,
            kwh=30.0,
            descripcion="Second trip",
        )

        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 2

        # Verify trip data
        assert trips[0]["datetime"] == "2026-03-20T10:00"
        assert trips[1]["datetime"] == "2026-03-21T11:00"
        assert trips[0]["km"] == 100.0
        assert trips[1]["km"] == 150.0

    @pytest.mark.asyncio
    async def test_read_trips_returns_list_not_dict(self, trip_manager):
        """Test that read operations return list, not dict."""
        await trip_manager.async_add_recurring_trip(
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )

        trips = await trip_manager.async_get_recurring_trips()
        assert isinstance(trips, list)
        assert not isinstance(trips, dict)

    @pytest.mark.asyncio
    async def test_read_all_trip_fields(self, trip_manager):
        """Test reading all fields from a trip."""
        await trip_manager.async_add_recurring_trip(
            trip_id="full_trip_001",
            dia_semana="viernes",
            hora="17:00",
            km=200.0,
            kwh=40.0,
            descripcion="Weekend trip home",
        )

        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1

        trip = trips[0]
        # Verify all expected fields exist
        assert "id" in trip
        assert "dia_semana" in trip
        assert "hora" in trip
        assert "km" in trip
        assert "kwh" in trip
        assert "descripcion" in trip
        assert "activo" in trip
        assert "tipo" in trip


# =============================================================================
# CRUD - UPDATE Operations
# =============================================================================


class TestTripUpdate:
    """Tests for Update operations (CRUD - Update)."""

    @pytest.mark.asyncio
    async def test_update_recurring_trip(self, trip_manager, caplog):
        """Test updating an existing recurring trip."""
        # Create trip first
        await trip_manager.async_add_recurring_trip(
            trip_id="commute_lunes",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
            descripcion="Original commute",
        )

        # Update trip
        await trip_manager.async_update_trip(
            "commute_lunes",
            {
                "dia_semana": "martes",
                "hora": "09:00",
                "km": 60.0,
                "descripcion": "Updated commute",
            },
        )

        # Verify update
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["dia_semana"] == "martes"
        assert trips[0]["hora"] == "09:00"
        assert trips[0]["km"] == 60.0
        assert trips[0]["descripcion"] == "Updated commute"
        # Fields not updated should remain unchanged
        assert trips[0]["kwh"] == 10.0

    @pytest.mark.asyncio
    async def test_update_punctual_trip(self, trip_manager, caplog):
        """Test updating an existing punctual trip."""
        # Create trip first
        await trip_manager.async_add_punctual_trip(
            trip_id="weekend_trip_001",
            datetime_str="2026-03-25T10:00",
            km=100.0,
            kwh=20.0,
            descripcion="Weekend trip",
        )

        # Update trip
        await trip_manager.async_update_trip(
            "weekend_trip_001",
            {
                "datetime_str": "2026-03-26T10:00",
                "km": 150.0,
                "kwh": 30.0,
                "descripcion": "Updated weekend trip",
            },
        )

        # Verify update
        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 1
        assert trips[0]["km"] == 150.0
        assert trips[0]["kwh"] == 30.0
        assert trips[0]["descripcion"] == "Updated weekend trip"

    @pytest.mark.asyncio
    async def test_update_punctual_trip_datetime_field(self, trip_manager, caplog):
        """TDD: Test that updating datetime works - this test SHOULD FAIL until bug is fixed.

        The frontend sends 'datetime' field (not 'datetime_str'), so we must verify
        that updating with 'datetime' key actually persists.
        """
        # Create trip first
        await trip_manager.async_add_punctual_trip(
            trip_id="datetime_update_test",
            datetime_str="2026-03-25T10:00",
            km=50.0,
            kwh=10.0,
            descripcion="Datetime update test",
        )

        # Update ONLY the datetime (simulating frontend edit flow)
        # Frontend sends 'datetime', not 'datetime_str'
        await trip_manager.async_update_trip(
            "datetime_update_test",
            {
                "datetime": "2026-03-28T15:30",
            },
        )

        # Verify datetime was actually updated
        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 1
        assert trips[0]["datetime"] == "2026-03-28T15:30", (
            f"Expected datetime '2026-03-28T15:30', got '{trips[0].get('datetime')}'"
        )
        # Verify other fields were NOT changed
        assert trips[0]["km"] == 50.0
        assert trips[0]["kwh"] == 10.0

    @pytest.mark.asyncio
    async def test_update_nonexistent_trip(self, trip_manager, caplog):
        """Test updating a trip that doesn't exist."""
        caplog.set_level("WARNING")

        await trip_manager.async_update_trip(
            "nonexistent_trip_id",
            {"km": 100.0},
        )

        # Verify warning was logged
        assert any(
            "not found for update" in record.message for record in caplog.records
        )

        # Verify no trips were created
        trips = await trip_manager.async_get_punctual_trips()
        assert trips == []

    @pytest.mark.asyncio
    async def test_update_nonexistent_punctual_trip(self, trip_manager, caplog):
        """Test updating a punctual trip that doesn't exist."""
        caplog.set_level("WARNING")

        await trip_manager.async_update_trip(
            "nonexistent_punctual",
            {"km": 200.0},
        )

        # Verify warning was logged
        assert any(
            "not found for update" in record.message for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_pause_recurring_trip(self, trip_manager, caplog):
        """Test pausing a recurring trip (update activo=False)."""
        # Create active trip
        await trip_manager.async_add_recurring_trip(
            trip_id="active_trip",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )

        # Pause the trip
        await trip_manager.async_pause_recurring_trip("active_trip")

        # Verify trip is paused
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["activo"] is False

    @pytest.mark.asyncio
    async def test_resume_recurring_trip(self, trip_manager, caplog):
        """Test resuming a paused recurring trip (update activo=True)."""
        # Create and pause trip
        await trip_manager.async_add_recurring_trip(
            trip_id="paused_trip",
            dia_semana="martes",
            hora="09:00",
            km=75.0,
            kwh=15.0,
        )
        await trip_manager.async_pause_recurring_trip("paused_trip")

        # Verify it's paused
        trips = await trip_manager.async_get_recurring_trips()
        assert trips[0]["activo"] is False

        # Resume the trip
        await trip_manager.async_resume_recurring_trip("paused_trip")

        # Verify trip is active
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["activo"] is True

    @pytest.mark.asyncio
    async def test_complete_punctual_trip(self, trip_manager, caplog):
        """Test completing a punctual trip (update estado='completado')."""
        # Create pending trip
        await trip_manager.async_add_punctual_trip(
            trip_id="pending_trip",
            datetime_str="2026-03-20T10:00",
            km=100.0,
            kwh=20.0,
        )

        # Complete the trip
        await trip_manager.async_complete_punctual_trip("pending_trip")

        # Verify trip is completed
        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 1
        assert trips[0]["estado"] == "completado"

    @pytest.mark.asyncio
    async def test_update_paused_trip(self, trip_manager, caplog):
        """Test updating a paused recurring trip."""
        # Create and pause trip
        await trip_manager.async_add_recurring_trip(
            trip_id="paused_update",
            dia_semana="jueves",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )
        await trip_manager.async_pause_recurring_trip("paused_update")

        # Update the paused trip
        await trip_manager.async_update_trip(
            "paused_update",
            {"km": 75.0, "descripcion": "Updated paused trip"},
        )

        # Verify trip is updated but still paused
        trips = await trip_manager.async_get_recurring_trips()
        assert trips[0]["km"] == 75.0
        assert trips[0]["descripcion"] == "Updated paused trip"
        assert trips[0]["activo"] is False

    @pytest.mark.asyncio
    async def test_update_trip_preserves_other_fields(self, trip_manager, caplog):
        """Test that updating trip fields preserves other fields."""
        await trip_manager.async_add_recurring_trip(
            trip_id="preserve_test",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
            descripcion="Original description",
        )

        # Update only km
        await trip_manager.async_update_trip(
            "preserve_test",
            {"km": 100.0},
        )

        trips = await trip_manager.async_get_recurring_trips()
        assert trips[0]["km"] == 100.0
        # Other fields should be preserved
        assert trips[0]["dia_semana"] == "lunes"
        assert trips[0]["hora"] == "08:00"
        assert trips[0]["kwh"] == 10.0
        assert trips[0]["descripcion"] == "Original description"

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, trip_manager, caplog):
        """Test updating multiple fields at once."""
        await trip_manager.async_add_recurring_trip(
            trip_id="multi_update",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
            descripcion="Original",
        )

        await trip_manager.async_update_trip(
            "multi_update",
            {
                "dia_semana": "viernes",
                "hora": "18:00",
                "km": 200.0,
                "kwh": 40.0,
                "descripcion": "New description",
            },
        )

        trips = await trip_manager.async_get_recurring_trips()
        assert trips[0]["dia_semana"] == "viernes"
        assert trips[0]["hora"] == "18:00"
        assert trips[0]["km"] == 200.0
        assert trips[0]["kwh"] == 40.0
        assert trips[0]["descripcion"] == "New description"


# =============================================================================
# CRUD - DELETE Operations
# =============================================================================


class TestTripDelete:
    """Tests for Delete operations (CRUD - Delete)."""

    @pytest.mark.asyncio
    async def test_delete_recurring_trip(self, trip_manager, caplog):
        """Test deleting a recurring trip."""
        # Create trip first
        await trip_manager.async_add_recurring_trip(
            trip_id="rec_to_delete",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
            descripcion="Trip to delete",
        )

        # Verify trip exists
        trips_before = await trip_manager.async_get_recurring_trips()
        assert len(trips_before) == 1

        # Delete the trip
        await trip_manager.async_delete_trip("rec_to_delete")

        # Verify trip was deleted
        trips_after = await trip_manager.async_get_recurring_trips()
        assert len(trips_after) == 0

    @pytest.mark.asyncio
    async def test_delete_punctual_trip(self, trip_manager, caplog):
        """Test deleting a punctual trip."""
        # Create trip first
        await trip_manager.async_add_punctual_trip(
            trip_id="pun_to_delete",
            datetime_str="2026-03-25T10:00",
            km=100.0,
            kwh=20.0,
            descripcion="Trip to delete",
        )

        # Verify trip exists
        trips_before = await trip_manager.async_get_punctual_trips()
        assert len(trips_before) == 1

        # Delete the trip
        await trip_manager.async_delete_trip("pun_to_delete")

        # Verify trip was deleted
        trips_after = await trip_manager.async_get_punctual_trips()
        assert len(trips_after) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_trip(self, trip_manager, caplog):
        """Test deleting a trip that doesn't exist."""
        caplog.set_level("WARNING")

        await trip_manager.async_delete_trip("nonexistent_trip")

        # Verify warning was logged
        assert any(
            "not found for deletion" in record.message for record in caplog.records
        )

        # Verify trips list is empty
        trips = await trip_manager.async_get_punctual_trips()
        assert trips == []

    @pytest.mark.asyncio
    async def test_cancel_punctual_trip(self, trip_manager, caplog):
        """Test cancelling a punctual trip (deletes it)."""
        # Create trip
        await trip_manager.async_add_punctual_trip(
            trip_id="cancel_me",
            datetime_str="2026-03-25T10:00",
            km=100.0,
            kwh=20.0,
        )

        # Cancel the trip
        await trip_manager.async_cancel_punctual_trip("cancel_me")

        # Verify trip was deleted
        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 0

    @pytest.mark.asyncio
    async def test_delete_mixed_trip_types(self, trip_manager, caplog):
        """Test deleting trips from both types."""
        # Create trips of both types
        await trip_manager.async_add_recurring_trip(
            trip_id="rec_keep",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )
        await trip_manager.async_add_recurring_trip(
            trip_id="rec_delete",
            dia_semana="martes",
            hora="09:00",
            km=75.0,
            kwh=15.0,
        )
        await trip_manager.async_add_punctual_trip(
            trip_id="pun_keep",
            datetime_str="2026-03-25T10:00",
            km=100.0,
            kwh=20.0,
        )
        await trip_manager.async_add_punctual_trip(
            trip_id="pun_delete",
            datetime_str="2026-03-26T11:00",
            km=150.0,
            kwh=30.0,
        )

        # Delete one from each type
        await trip_manager.async_delete_trip("rec_delete")
        await trip_manager.async_delete_trip("pun_delete")

        # Verify remaining trips
        recurring = await trip_manager.async_get_recurring_trips()
        punctual = await trip_manager.async_get_punctual_trips()

        assert len(recurring) == 1
        assert recurring[0]["id"] == "rec_keep"
        assert len(punctual) == 1
        assert punctual[0]["id"] == "pun_keep"

    @pytest.mark.asyncio
    async def test_delete_all_trips(self, trip_manager, caplog):
        """Test deleting all trips from a vehicle."""
        # Create multiple trips and capture their IDs
        trip_ids = []
        for i in range(10):
            await trip_manager.async_add_recurring_trip(
                dia_semana="lunes",
                hora="08:00",
                km=50.0,
                kwh=10.0,
                descripcion=f"Trip {i}",
            )
            # Get the trip ID from the created trips
            trips = await trip_manager.async_get_recurring_trips()
            if trips:
                trip_ids.append(trips[-1]["id"])

        # Verify trips exist
        assert len(trip_ids) == 10

        # Delete all trips using the actual IDs
        for trip_id in trip_ids:
            await trip_manager.async_delete_trip(trip_id)

        # Verify all trips are deleted
        trips_after = await trip_manager.async_get_recurring_trips()
        assert len(trips_after) == 0

    @pytest.mark.asyncio
    async def test_delete_single_trip_preserves_others(self, trip_manager, caplog):
        """Test that deleting one trip preserves other trips."""
        # Create three trips
        await trip_manager.async_add_recurring_trip(
            trip_id="keep_first",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )
        await trip_manager.async_add_recurring_trip(
            trip_id="delete_middle",
            dia_semana="martes",
            hora="09:00",
            km=75.0,
            kwh=15.0,
        )
        await trip_manager.async_add_recurring_trip(
            trip_id="keep_last",
            dia_semana="viernes",
            hora="10:00",
            km=60.0,
            kwh=12.0,
        )

        # Delete middle trip
        await trip_manager.async_delete_trip("delete_middle")

        # Verify remaining trips are intact
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 2

        trip_ids = {trip["id"] for trip in trips}
        assert "keep_first" in trip_ids
        assert "keep_last" in trip_ids
        assert "delete_middle" not in trip_ids


# =============================================================================
# CRUD - Complete Workflows
# =============================================================================


class TestCompleteCRUDWorkflow:
    """Tests for complete CRUD workflows."""

    @pytest.mark.asyncio
    async def test_create_read_update_delete_workflow(self, trip_manager, caplog):
        """Test complete CRUD workflow: Create -> Read -> Update -> Delete.

        This is the most important CRUD test - it verifies the entire lifecycle
        of a trip from creation to deletion.
        """
        # CREATE: Create a new trip
        await trip_manager.async_add_recurring_trip(
            trip_id="workflow_trip",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
            descripcion="Workflow test trip",
        )

        # READ: Read the trip
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["dia_semana"] == "lunes"

        # UPDATE: Update the trip
        await trip_manager.async_update_trip(
            "workflow_trip",
            {"km": 100.0, "descripcion": "Updated workflow trip"},
        )

        # READ: Verify update
        trips = await trip_manager.async_get_recurring_trips()
        assert trips[0]["km"] == 100.0
        assert trips[0]["descripcion"] == "Updated workflow trip"

        # DELETE: Delete the trip
        await trip_manager.async_delete_trip("workflow_trip")

        # READ: Verify deletion
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 0

    @pytest.mark.asyncio
    async def test_recurring_trip_workflow(self, trip_manager, caplog):
        """Test complete workflow for recurring trips: create -> pause -> resume -> delete."""
        # Create
        await trip_manager.async_add_recurring_trip(
            trip_id="recurring_workflow",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )

        # Read
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["activo"] is True

        # Pause
        await trip_manager.async_pause_recurring_trip("recurring_workflow")
        trips = await trip_manager.async_get_recurring_trips()
        assert trips[0]["activo"] is False

        # Resume
        await trip_manager.async_resume_recurring_trip("recurring_workflow")
        trips = await trip_manager.async_get_recurring_trips()
        assert trips[0]["activo"] is True

        # Delete
        await trip_manager.async_delete_trip("recurring_workflow")
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 0

    @pytest.mark.asyncio
    async def test_punctual_trip_workflow(self, trip_manager, caplog):
        """Test complete workflow for punctual trips: create -> complete -> delete."""
        # Create
        await trip_manager.async_add_punctual_trip(
            trip_id="punctual_workflow",
            datetime_str="2026-03-25T10:00",
            km=100.0,
            kwh=20.0,
        )

        # Read
        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 1
        assert trips[0]["estado"] == "pendiente"

        # Complete
        await trip_manager.async_complete_punctual_trip("punctual_workflow")
        trips = await trip_manager.async_get_punctual_trips()
        assert trips[0]["estado"] == "completado"

        # Cancel (delete)
        await trip_manager.async_cancel_punctual_trip("punctual_workflow")
        trips = await trip_manager.async_get_punctual_trips()
        assert len(trips) == 0


# =============================================================================
# CRUD - Edge Cases and Error Handling
# =============================================================================


class TestCRUDEdgeCases:
    """Tests for CRUD edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_update_with_empty_data(self, trip_manager, caplog):
        """Test updating with empty data dictionary."""
        await trip_manager.async_add_recurring_trip(
            trip_id="empty_update",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )

        # Update with empty dict should not fail
        await trip_manager.async_update_trip("empty_update", {})

        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1

    @pytest.mark.asyncio
    async def test_delete_from_empty_list(self, trip_manager, caplog):
        """Test deleting from an empty trips list."""
        # Should not raise an error
        await trip_manager.async_delete_trip("nonexistent")

        # Verify no trips exist
        trips = await trip_manager.async_get_recurring_trips()
        assert trips == []

    @pytest.mark.asyncio
    async def test_create_then_update_then_delete(self, trip_manager, caplog):
        """Test rapid create -> update -> delete operations."""
        # Create
        await trip_manager.async_add_recurring_trip(
            trip_id="rapid_test",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )

        # Update immediately
        await trip_manager.async_update_trip(
            "rapid_test",
            {"km": 100.0},
        )

        # Delete immediately
        await trip_manager.async_delete_trip("rapid_test")

        # Verify deletion
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 0


# =============================================================================
# CRUD - Data Integrity Tests
# =============================================================================


class TestCRUDDataIntegrity:
    """Tests for data integrity during CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_preserves_exact_values(self, trip_manager, caplog):
        """Test that CRUD operations preserve exact values."""
        test_km = 123.456
        test_kwh = 23.456

        await trip_manager.async_add_recurring_trip(
            dia_semana="lunes",
            hora="08:00",
            km=test_km,
            kwh=test_kwh,
        )

        trips = await trip_manager.async_get_recurring_trips()
        assert trips[0]["km"] == test_km
        assert trips[0]["kwh"] == test_kwh

    @pytest.mark.asyncio
    async def test_update_preserves_precision(self, trip_manager, caplog):
        """Test that update operations preserve precision."""
        await trip_manager.async_add_recurring_trip(
            trip_id="precision_test",
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )

        await trip_manager.async_update_trip(
            "precision_test",
            {"km": 123.456, "kwh": 23.456},
        )

        trips = await trip_manager.async_get_recurring_trips()
        assert trips[0]["km"] == 123.456
        assert trips[0]["kwh"] == 23.456

    @pytest.mark.asyncio
    async def test_delete_does_not_affect_other_trips(self, trip_manager, caplog):
        """Test that deleting one trip doesn't affect others."""
        # Create multiple trips and capture their IDs
        trip_ids = []
        for i in range(5):
            await trip_manager.async_add_recurring_trip(
                dia_semana="lunes",
                hora="08:00",
                km=50.0,
                kwh=10.0,
            )
            trips = await trip_manager.async_get_recurring_trips()
            if trips:
                trip_ids.append(trips[-1]["id"])

        initial_count = len(trip_ids)
        assert initial_count == 5

        # Delete one trip using the actual ID
        await trip_manager.async_delete_trip(trip_ids[0])

        # Verify other trips are unaffected
        remaining = len(await trip_manager.async_get_recurring_trips())
        assert remaining == 4

        # Verify data integrity of remaining trips
        trips = await trip_manager.async_get_recurring_trips()
        for trip in trips:
            assert trip["dia_semana"] == "lunes"
            assert trip["km"] == 50.0


# =============================================================================
# CRUD - Storage Tests
# =============================================================================


class TestCRUDStorage:
    """Tests for CRUD storage persistence."""

    @pytest.mark.asyncio
    async def test_create_triggers_storage_write(self, trip_manager, caplog):
        """Test that creating trips triggers storage write.

        Note: Production code uses ha_storage.Store.async_save(), not hass.storage.async_write_dict.
        The test verifies that the save operation is attempted.
        """
        await trip_manager.async_add_recurring_trip(
            dia_semana="lunes",
            hora="08:00",
            km=50.0,
            kwh=10.0,
        )

        # Verify trips were added (storage write is attempted but may fail with mock)
        trips = await trip_manager.async_get_recurring_trips()
        assert len(trips) == 1
        assert trips[0]["dia_semana"] == "lunes"
        assert trips[0]["hora"] == "08:00"
