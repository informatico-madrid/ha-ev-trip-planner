"""Tests for trip_manager.py edge cases and error handling."""

from __future__ import annotations

from datetime import datetime, timedelta, date
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager, generate_trip_id, TRIP_TYPE_RECURRING, TRIP_TYPE_PUNCTUAL


# =============================================================================
# TripManager - error handling and edge cases
# =============================================================================


class TestTripManagerEdgeCases:
    """Tests for TripManager edge cases."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        return hass

    @pytest.fixture
    def trip_manager(self, mock_hass):
        """Create TripManager instance with mocked dependencies."""
        from custom_components.ev_trip_planner.trip_manager import TripManager
        mgr = TripManager(mock_hass, "test_vehicle")
        # _recurring_trips and _punctual_trips are dicts, not lists
        mgr._recurring_trips = {}
        mgr._punctual_trips = {}
        return mgr

    def test_is_trip_today_recurring(self, trip_manager):
        """Test _is_trip_today correctly identifies recurring trip."""
        # Monday trip
        trip = {
            "tipo": "recurrente",
            "dia_semana": "lunes",
        }

        # Mock today to be Monday (weekday() = 0)
        mock_today = Mock()
        mock_today.weekday = Mock(return_value=0)

        result = trip_manager._is_trip_today(trip, mock_today)
        assert result is True

    def test_is_trip_today_recurring_wrong_day(self, trip_manager):
        """Test _is_trip_today returns False for wrong day."""
        trip = {
            "tipo": "recurrente",
            "dia_semana": "lunes",
        }

        # Mock today to be Tuesday (weekday() = 1)
        mock_today = Mock()
        mock_today.weekday = Mock(return_value=1)

        result = trip_manager._is_trip_today(trip, mock_today)
        assert result is False

    def test_is_trip_today_punctual(self, trip_manager):
        """Test _is_trip_today correctly identifies punctual trip."""
        trip = {
            "tipo": "puntual",
            "datetime": "2026-04-15T10:00",
        }

        mock_today = date(2026, 4, 15)

        result = trip_manager._is_trip_today(trip, mock_today)
        assert result is True

    def test_is_trip_today_unknown_type(self, trip_manager):
        """Test _is_trip_today returns False for unknown trip type."""
        trip = {
            "tipo": "unknown_type",
        }

        mock_today = Mock()

        result = trip_manager._is_trip_today(trip, mock_today)
        assert result is False

    def test_get_day_index_with_numeric_string(self, trip_manager):
        """Test _get_day_index handles numeric day strings."""
        # Test valid numeric index
        result = trip_manager._get_day_index("2")
        assert result == 2

    def test_get_day_index_with_numeric_out_of_range(self, trip_manager):
        """Test _get_day_index handles out of range numeric index."""
        # Test out of range index (should default to 0)
        result = trip_manager._get_day_index("9")
        assert result == 0  # Defaults to Monday

    def test_get_day_index_case_insensitive(self, trip_manager):
        """Test _get_day_index is case insensitive."""
        result = trip_manager._get_day_index("LUNES")
        assert result == 0

        result = trip_manager._get_day_index("MiErCoLeS")
        assert result == 2


# =============================================================================
# TripManager - trip time calculations
# =============================================================================


class TestTripTimeCalculations:
    """Tests for trip time calculation methods."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        return hass

    @pytest.fixture
    def trip_manager(self, mock_hass):
        """Create TripManager instance."""
        from custom_components.ev_trip_planner.trip_manager import TripManager
        mgr = TripManager(mock_hass, "test_vehicle")
        mgr._recurring_trips = {}
        mgr._punctual_trips = {}
        return mgr

    def test_get_trip_time_recurring(self, trip_manager):
        """Test _get_trip_time for recurring trip."""
        trip = {
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:30",
        }

        result = trip_manager._get_trip_time(trip)

        assert result is not None
        assert result.minute == 30
        assert result.hour == 9

    def test_get_trip_time_punctual(self, trip_manager):
        """Test _get_trip_time for punctual trip."""
        trip = {
            "tipo": "puntual",
            "datetime": "2026-04-15T14:30",
        }

        result = trip_manager._get_trip_time(trip)

        assert result is not None
        assert result.minute == 30
        assert result.hour == 14

    def test_get_trip_time_unknown_type(self, trip_manager):
        """Test _get_trip_time returns None for unknown type."""
        trip = {
            "tipo": "unknown",
        }

        result = trip_manager._get_trip_time(trip)
        assert result is None


# =============================================================================
# TripManager - async_delete_all_trips
# =============================================================================


class TestDeleteAllTrips:
    """Tests for delete_all_trips method."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        return hass

    @pytest.fixture
    def trip_manager(self, mock_hass):
        """Create TripManager instance."""
        from custom_components.ev_trip_planner.trip_manager import TripManager
        mgr = TripManager(mock_hass, "test_vehicle")
        return mgr

    @pytest.mark.asyncio
    async def test_async_delete_all_trips_deletes_both_lists(self, trip_manager):
        """Test delete_all_trips clears both recurring and punctual trips."""
        # Add some trips (stored as dict)
        trip_manager._recurring_trips = {
            "r1": {"id": "r1", "tipo": "recurrente"},
            "r2": {"id": "r2", "tipo": "recurrente"},
        }
        trip_manager._punctual_trips = {
            "p1": {"id": "p1", "tipo": "puntual"},
        }

        await trip_manager.async_delete_all_trips()

        assert len(trip_manager._recurring_trips) == 0
        assert len(trip_manager._punctual_trips) == 0


# =============================================================================
# TripManager - get trip methods
# =============================================================================


class TestGetTripMethods:
    """Tests for get trip methods."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        return hass

    @pytest.fixture
    def trip_manager(self, mock_hass):
        """Create TripManager instance."""
        from custom_components.ev_trip_planner.trip_manager import TripManager
        mgr = TripManager(mock_hass, "test_vehicle")
        mgr._recurring_trips = {
            "r1": {"id": "r1", "tipo": "recurrente", "activo": True},
            "r2": {"id": "r2", "tipo": "recurrente", "activo": False},
        }
        mgr._punctual_trips = {
            "p1": {"id": "p1", "tipo": "puntual"},
        }
        return mgr

    @pytest.mark.asyncio
    async def test_async_get_recurring_trips_returns_all(self, trip_manager):
        """Test async_get_recurring_trips returns all trips (filtering happens elsewhere)."""
        trips = await trip_manager.async_get_recurring_trips()

        # Returns all trips (2 total: one active, one inactive)
        assert len(trips) == 2

    @pytest.mark.asyncio
    async def test_async_get_punctual_trips_returns_all(self, trip_manager):
        """Test async_get_punctual_trips returns all trips."""
        trips = await trip_manager.async_get_punctual_trips()

        assert len(trips) == 1
        assert trips[0]["id"] == "p1"

    def test_get_all_trips_returns_both(self, trip_manager):
        """Test get_all_trips returns both recurring and punctual."""
        result = trip_manager.get_all_trips()

        assert "recurring" in result
        assert "punctual" in result
        assert len(result["recurring"]) == 2
        assert len(result["punctual"]) == 1


# =============================================================================
# TripManager - pause/resume trips
# =============================================================================


class TestPauseResumeTrips:
    """Tests for pause and resume trip methods."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        return hass

    @pytest.fixture
    def trip_manager(self, mock_hass):
        """Create TripManager instance."""
        from custom_components.ev_trip_planner.trip_manager import TripManager
        mgr = TripManager(mock_hass, "test_vehicle")
        mgr._recurring_trips = {
            "r1": {"id": "r1", "tipo": "recurrente", "activo": True},
        }
        mgr._punctual_trips = {}
        return mgr

    @pytest.mark.asyncio
    async def test_async_pause_recurring_trip(self, trip_manager):
        """Test pausing a recurring trip."""
        await trip_manager.async_pause_recurring_trip("r1")

        assert trip_manager._recurring_trips["r1"]["activo"] is False

    @pytest.mark.asyncio
    async def test_async_pause_nonexistent_trip(self, trip_manager):
        """Test pausing a nonexistent trip doesn't raise."""
        await trip_manager.async_pause_recurring_trip("nonexistent")
        # Should not raise - just logs warning

    @pytest.mark.asyncio
    async def test_async_resume_recurring_trip(self, trip_manager):
        """Test resuming a recurring trip."""
        # First pause it
        trip_manager._recurring_trips["r1"]["activo"] = False

        await trip_manager.async_resume_recurring_trip("r1")

        assert trip_manager._recurring_trips["r1"]["activo"] is True

    @pytest.mark.asyncio
    async def test_async_resume_nonexistent_trip(self, trip_manager):
        """Test resuming a nonexistent trip doesn't raise."""
        await trip_manager.async_resume_recurring_trip("nonexistent")
        # Should not raise - just logs warning


# =============================================================================
# TripManager - SOC calculations
# =============================================================================


class TestSOCCalculations:
    """Tests for SOC calculation methods."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
        return hass

    @pytest.fixture
    def trip_manager(self, mock_hass):
        """Create TripManager instance."""
        from custom_components.ev_trip_planner.trip_manager import TripManager
        mgr = TripManager(mock_hass, "test_vehicle")
        return mgr

    @pytest.mark.asyncio
    async def test_async_get_kwh_needed_today_with_no_trips(self, trip_manager):
        """Test kwh needed returns 0 when no trips today."""
        result = await trip_manager.async_get_kwh_needed_today()
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_async_get_hours_needed_today_with_no_trips(self, trip_manager):
        """Test hours needed returns 0 when no trips today."""
        result = await trip_manager.async_get_hours_needed_today()
        assert result == 0


# =============================================================================
# Helper functions
# =============================================================================


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_generate_trip_id_recurring(self):
        """Test generate_trip_id for recurring trips."""
        trip_id = generate_trip_id(TRIP_TYPE_RECURRING, "lunes")
        assert trip_id.startswith("rec_")

    def test_generate_trip_id_punctual(self):
        """Test generate_trip_id for punctual trips."""
        trip_id = generate_trip_id(TRIP_TYPE_PUNCTUAL, "martes")
        assert trip_id.startswith("punt_") or trip_id.startswith("trip_")
