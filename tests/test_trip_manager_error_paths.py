"""Additional error path coverage tests for trip_manager.py."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.trip_manager import TripManager


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


class TestTripManagerAsyncCreateTripSensor:
    """Tests for async_create_trip_sensor error paths."""

    @pytest.mark.asyncio
    async def test_async_create_trip_sensor_entity_registry_error(self, mock_hass_with_storage):
        """async_create_trip_sensor handles entity registry error gracefully."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        # Add a trip first
        trip_manager._punctual_trips["trip_1"] = {
            "id": "trip_1",
            "tipo": "punctual",
            "datetime": "2025-01-15T18:00",
            "km": 30.0,
            "kwh": 5.0,
            "descripcion": "Test trip",
            "estado": "pendiente",
        }

        # Mock entity_registry to raise on async_get_or_create
        with patch(
            "homeassistant.helpers.entity_registry.EntityRegistry.async_get_or_create",
            side_effect=Exception("Registry error"),
        ):
            # Should not raise - exception is caught and logged
            await trip_manager.async_create_trip_sensor("trip_1", trip_manager._punctual_trips["trip_1"])


class TestTripManagerAsyncRemoveTripSensor:
    """Tests for async_remove_trip_sensor error paths."""

    @pytest.mark.asyncio
    async def test_async_remove_trip_sensor_registry_error(self, mock_hass_with_storage):
        """async_remove_trip_sensor handles registry error gracefully."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        # Mock registry.async_get to raise
        with patch(
            "homeassistant.helpers.entity_registry.EntityRegistry.async_get",
            side_effect=Exception("Registry error"),
        ):
            # Should not raise - exception is caught and logged
            await trip_manager.async_remove_trip_sensor("trip_1")


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
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        # Mock the sensor creation and EMHASS to avoid side effects
        with patch.object(trip_manager, "async_create_trip_sensor", new_callable=AsyncMock):
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
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        with patch.object(trip_manager, "async_create_trip_sensor", new_callable=AsyncMock):
            with patch.object(trip_manager, "_async_publish_new_trip_to_emhass", new_callable=AsyncMock):
                await trip_manager.async_add_recurring_trip(
                    trip_id="custom_recurring_1",
                    dia_semana="monday",
                    hora="08:00",
                    km=30,
                    kwh=5,
                )

        assert "custom_recurring_1" in trip_manager._recurring_trips


class TestTripManagerAsyncDeleteTrip:
    """Tests for async_delete_trip error paths."""

    @pytest.mark.asyncio
    async def test_async_delete_trip_not_found(self, mock_hass_with_storage):
        """async_delete_trip handles missing trip gracefully."""
        trip_manager = TripManager(mock_hass_with_storage, "test_vehicle")
        await trip_manager.async_setup()

        # Try to delete a trip that doesn't exist
        with patch.object(trip_manager, "async_save_trips", new_callable=AsyncMock):
            with patch.object(trip_manager, "async_remove_trip_sensor", new_callable=AsyncMock):
                with patch.object(trip_manager, "_async_remove_trip_from_emhass", new_callable=AsyncMock):
                    await trip_manager.async_delete_trip("nonexistent_trip")

        # No error should be raised - just returns early


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
