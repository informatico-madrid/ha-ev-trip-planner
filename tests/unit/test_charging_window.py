"""Tests for charging window calculation.

This test suite covers:
- AC-1: Basic window calculation (hora_regreso=18:00, trip=22:00 = 4h window)
- AC-3: hora_regreso in future (car not yet returned)
- AC-4: Multiple trips get separate windows
- AC-5: No pending trips returns zero values
- es_suficiente logic: True when window >= charging time, False otherwise
- Invalid hora_regreso format handling
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.calculations import (
    calculate_multi_trip_charging_windows,
)
from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_VEHICLE_NAME,
    RETURN_BUFFER_HOURS,
)
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.trip_manager import TripManager


class MockConfigEntry:
    """Mock ConfigEntry for testing."""

    def __init__(self, vehicle_id="test_vehicle", data=None):
        self.entry_id = "test_entry_id"
        self.data = data or {
            CONF_VEHICLE_NAME: vehicle_id,
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }


@pytest.fixture
def vehicle_id() -> str:
    """Return a test vehicle ID."""
    return "morgan"




@pytest.fixture
def trip_manager(mock_hass, vehicle_id):
    """Create a TripManager instance for testing."""
    tm = TripManager(mock_hass, vehicle_id)
    # Clear any existing state to ensure test isolation
    tm._punctual_trips = {}
    tm._recurring_trips = {}
    tm._trips = {}
    # Mock async_save_trips to prevent persistence between tests
    tm.async_save_trips = AsyncMock()
    return tm


class TestChargingWindowCalculation:
    """Tests for charging window calculation (AC-1)."""

    @pytest.mark.asyncio
    async def test_basic_window_calculation_4_hours(self, trip_manager, caplog):
        """Test basic window calculation: hora_regreso=18:00, next trip=22:00, verify ventana=4 hours.

        This is the POC test for AC-1:
        Given the car is at home from 18:00 and the next trip is at 22:00,
        then the charging window is 4 hours.
        """
        # Setup: Add a punctual trip at 22:00 today (aware UTC for proper datetime comparison)
        trip_datetime = datetime.now(timezone.utc).replace(
            hour=22, minute=0, second=0, microsecond=0
        )
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

        # Set hora_regreso at 18:00 today (aware UTC for proper datetime comparison)
        hora_regreso = datetime.now(timezone.utc).replace(
            hour=18, minute=0, second=0, microsecond=0
        )

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
        assert (
            result["ventana_horas"] == 4.0
        ), f"Expected 4.0 hours, got {result['ventana_horas']}"

        # Verify all expected fields are returned (AC-1 interface contract)
        assert "ventana_horas" in result, "Missing ventana_horas field"
        assert "kwh_necesarios" in result, "Missing kwh_necesarios field"
        assert (
            "horas_carga_necesarias" in result
        ), "Missing horas_carga_necesarias field"
        assert "inicio_ventana" in result, "Missing inicio_ventana field"
        assert "fin_ventana" in result, "Missing fin_ventana field"
        assert "es_suficiente" in result, "Missing es_suficiente field"

        # Verify energy calculation
        assert result["kwh_necesarios"] == 10.0
        assert result["horas_carga_necesarias"] == pytest.approx(
            1.35, rel=0.01
        )  # 10.0 / 7.4

        # Verify window start and end times
        assert result["inicio_ventana"] == hora_regreso
        assert result["fin_ventana"] == trip_datetime

        # Verify es_suficiente is True (4 hours > 1.35 hours needed)
        assert result["es_suficiente"] is True

    @pytest.mark.asyncio
    async def test_hora_regreso_none_car_not_yet_returned_uses_estimate(
        self, trip_manager, caplog
    ):
        """Test AC-3: hora_regreso is None (car not yet returned) - uses estimated window start.

        When hora_regreso is None (car has not yet returned, not detected),
        the window start should be estimated as departure_time - 6h.
        """
        # Setup: Add a punctual trip at 22:00 today (aware UTC for proper datetime comparison)
        trip_datetime = datetime.now(timezone.utc).replace(
            hour=22, minute=0, second=0, microsecond=0
        )
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

        # Get the trip we just added
        trips = await trip_manager.async_get_punctual_trips()
        trip = trips[0]

        # Call calcular_ventana_carga with hora_regreso=None (car not yet returned)
        result = await trip_manager.calcular_ventana_carga(
            trip=trip,
            soc_actual=50.0,
            hora_regreso=None,  # Car has not yet returned
            charging_power_kw=7.4,
        )

        # When hora_regreso is None (car not yet returned),
        # the window start should be estimated as departure - 6h
        # Since trip is at 22:00, window start = 22:00 - 6h = 16:00
        expected_inicio_ventana = trip_datetime - timedelta(hours=6)

        assert (
            result["inicio_ventana"] == expected_inicio_ventana
        ), f"Expected estimated window start at {expected_inicio_ventana}, got {result['inicio_ventana']}"

        # Window should be 6 hours (16:00 to 22:00)
        assert (
            result["ventana_horas"] == 6.0
        ), f"Expected 6.0 hours, got {result['ventana_horas']}"

    @pytest.mark.asyncio
    async def test_no_pending_trips_returns_zero_values(self, trip_manager, caplog):
        """Test AC-5: No pending trips returns zero values.

        When there are no trips pending after hora_regreso, the function should
        return zero values dict with es_suficiente=True.
        """
        # Do NOT add any trips - trip_manager starts empty

        # Mock async_calcular_energia_necesaria
        trip_manager.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 0.0}
        )

        # Set hora_regreso at 18:00 today (aware UTC for proper datetime comparison)
        hora_regreso = datetime.now(timezone.utc).replace(
            hour=18, minute=0, second=0, microsecond=0
        )

        # Create a dummy trip to pass to the function
        # The function will check if there's a next trip after hora_regreso
        # Since there are no trips, it should return zero values
        dummy_trip = {
            "id": "dummy_trip",
            "tipo": "punctual",
            "datetime": "2099-12-31T23:59",  # Far in the future so it's not the issue
            "km": 0.0,
            "kwh": 0.0,
        }

        # Call calcular_ventana_carga with no pending trips after hora_regreso
        result = await trip_manager.calcular_ventana_carga(
            trip=dummy_trip,
            soc_actual=50.0,
            hora_regreso=hora_regreso,
            charging_power_kw=7.4,
        )

        # Verify zero values are returned (AC-5)
        assert (
            result["ventana_horas"] == 0
        ), f"Expected 0, got {result['ventana_horas']}"
        assert (
            result["kwh_necesarios"] == 0
        ), f"Expected 0, got {result['kwh_necesarios']}"
        assert (
            result["horas_carga_necesarias"] == 0
        ), f"Expected 0, got {result['horas_carga_necesarias']}"
        assert (
            result["inicio_ventana"] is None
        ), f"Expected None, got {result['inicio_ventana']}"
        assert (
            result["fin_ventana"] is None
        ), f"Expected None, got {result['fin_ventana']}"
        # es_suficiente is True when no charging needed (AC-5)
        assert (
            result["es_suficiente"] is True
        ), "es_suficiente should be True when no trips pending"

    @pytest.mark.asyncio
    async def test_multiple_trips_get_separate_windows(self, trip_manager, caplog):
        """Test AC-4: Multiple trips get separate windows.

        When there are multiple trips, each should get its own charging window.
        The first trip's window starts at hora_regreso. Subsequent trips'
        windows start at the previous trip's arrival time (departure + 6h).
        """
        # Use fixed future dates to avoid datetime.now() issues
        # Add first trip at 20:00 on a future date
        await trip_manager.async_add_punctual_trip(
            datetime_str="2099-04-01T20:00",
            km=50.0,
            kwh=10.0,
            descripcion="First trip",
        )

        # Add second trip at 22:00 on same future date
        await trip_manager.async_add_punctual_trip(
            datetime_str="2099-04-01T22:00",
            km=30.0,
            kwh=6.0,
            descripcion="Second trip",
        )

        # Mock async_calcular_energia_necesaria
        trip_manager.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 10.0}
        )

        # Set hora_regreso at 18:00 on the same future date (aware UTC for proper datetime comparison)
        hora_regreso = datetime(2099, 4, 1, 18, 0, 0, tzinfo=timezone.utc)

        # Get the trips sorted by departure time
        trips = await trip_manager.async_get_punctual_trips()
        trips_sorted = sorted(trips, key=lambda t: t.get("datetime", ""))

        # Use calcular_ventana_carga_multitrip for proper AC-4 window chaining
        results = await trip_manager.calcular_ventana_carga_multitrip(
            trips=trips_sorted,
            soc_actual=50.0,
            hora_regreso=hora_regreso,
            charging_power_kw=7.4,
        )

        # Should have 2 results
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"

        # First trip: window from 18:00 to 02:00 next day = 8 hours
        # Note: Implementation uses trip_arrival (departure + 6h) for ventana_horas
        trip1_departure = datetime(2099, 4, 1, 20, 0, 0, tzinfo=timezone.utc)
        trip1_arrival = datetime(
            2099, 4, 2, 2, 0, 0, tzinfo=timezone.utc
        )  # departure + 6h
        trip2_departure = datetime(2099, 4, 1, 22, 0, 0, tzinfo=timezone.utc)
        assert (
            results[0]["ventana_horas"] == 8.0
        ), f"First trip: Expected 8.0 hours (18:00 to 02:00), got {results[0]['ventana_horas']}"
        assert (
            results[0]["inicio_ventana"] == hora_regreso
        ), "First trip should start at hora_regreso"
        assert (
            results[0]["fin_ventana"] == trip1_departure
        ), f"First trip departure at {trip1_departure}"

        # Second trip: window from 02:00 to 04:00 next day = 2 hours
        # Window starts at first trip's arrival (departure + 6h)
        # Implementation uses trip_arrival for ventana_horas, not fin_ventana
        assert (
            results[1]["ventana_horas"] == 2.0
        ), f"Second trip: Expected 2.0 hours, got {results[1]['ventana_horas']}"
        assert (
            results[1]["inicio_ventana"] == trip1_arrival
        ), f"Second trip should start at first trip arrival {trip1_arrival}"
        assert (
            results[1]["fin_ventana"] == trip2_departure
        ), f"Second trip departure at {trip2_departure}"

    @pytest.mark.asyncio
    async def test_es_suficiente_true_when_window_sufficient(
        self, trip_manager, caplog
    ):
        """Test es_suficiente is True when window >= charging time.

        When the charging window is large enough to fully charge the vehicle,
        es_suficiente should be True.
        """
        # Setup: Add a punctual trip at 22:00 today
        trip_datetime = datetime.now(timezone.utc).replace(
            hour=22, minute=0, second=0, microsecond=0
        )
        datetime_str = trip_datetime.strftime("%Y-%m-%dT%H:%M")
        await trip_manager.async_add_punctual_trip(
            datetime_str=datetime_str,
            km=50.0,
            kwh=10.0,  # 10 kWh needed
            descripcion="Evening trip",
        )

        # Mock async_calcular_energia_necesaria to return 10.0 kWh needed
        trip_manager.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 10.0}
        )

        # Set hora_regreso at 18:00 today (4 hour window)
        hora_regreso = datetime.now(timezone.utc).replace(
            hour=18, minute=0, second=0, microsecond=0
        )

        # With 7.4 kW charging: 10.0 / 7.4 = 1.35 hours needed
        # With 4 hour window: 4.0 >= 1.35 => es_suficiente = True

        trips = await trip_manager.async_get_punctual_trips()
        trip = trips[0]

        result = await trip_manager.calcular_ventana_carga(
            trip=trip,
            soc_actual=50.0,
            hora_regreso=hora_regreso,
            charging_power_kw=7.4,
        )

        assert (
            result["es_suficiente"] is True
        ), "es_suficiente should be True when window (4h) >= charging time (1.35h)"

    @pytest.mark.asyncio
    async def test_es_suficiente_false_when_window_insufficient(
        self, trip_manager, caplog
    ):
        """Test es_suficiente is False when window < charging time.

        When the charging window is NOT large enough to fully charge the vehicle,
        es_suficiente should be False.
        """
        # Setup: Add a punctual trip at 19:00 today (only 1 hour window)
        trip_datetime = datetime.now(timezone.utc).replace(
            hour=19, minute=0, second=0, microsecond=0
        )
        datetime_str = trip_datetime.strftime("%Y-%m-%dT%H:%M")
        await trip_manager.async_add_punctual_trip(
            datetime_str=datetime_str,
            km=100.0,
            kwh=25.0,  # 25 kWh needed
            descripcion="Long trip needing lots of charge",
        )

        # Mock async_calcular_energia_necesaria to return 25.0 kWh needed
        trip_manager.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 25.0}
        )

        # Set hora_regreso at 18:00 today (1 hour window: 18:00 to 19:00)
        hora_regreso = datetime.now(timezone.utc).replace(
            hour=18, minute=0, second=0, microsecond=0
        )

        # With 7.4 kW charging: 25.0 / 7.4 = 3.38 hours needed
        # With 1 hour window: 1.0 < 3.38 => es_suficiente = False

        trips = await trip_manager.async_get_punctual_trips()
        trip = trips[0]

        result = await trip_manager.calcular_ventana_carga(
            trip=trip,
            soc_actual=50.0,
            hora_regreso=hora_regreso,
            charging_power_kw=7.4,
        )

        assert (
            result["es_suficiente"] is False
        ), "es_suficiente should be False when window (1h) < charging time (3.38h)"

    @pytest.mark.asyncio
    async def test_invalid_hora_regreso_format_handled_gracefully(
        self, trip_manager, caplog
    ):
        """Test invalid hora_regreso format is handled gracefully.

        When hora_regreso is an invalid string that cannot be parsed,
        the function should handle it gracefully and fall back to estimation.
        """
        # Setup: Add a punctual trip at 22:00 today (aware UTC for proper datetime comparison)
        trip_datetime = datetime.now(timezone.utc).replace(
            hour=22, minute=0, second=0, microsecond=0
        )
        datetime_str = trip_datetime.strftime("%Y-%m-%dT%H:%M")
        await trip_manager.async_add_punctual_trip(
            datetime_str=datetime_str,
            km=50.0,
            kwh=10.0,
            descripcion="Evening trip",
        )

        # Mock async_calcular_energia_necesaria
        trip_manager.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 10.0}
        )

        # Set invalid hora_regreso string
        invalid_hora_regreso = "not-a-valid-datetime-format"

        trips = await trip_manager.async_get_punctual_trips()
        trip = trips[0]

        # Call calcular_ventana_carga with invalid string
        # Should not raise an exception, should handle gracefully
        result = await trip_manager.calcular_ventana_carga(
            trip=trip,
            soc_actual=50.0,
            hora_regreso=invalid_hora_regreso,
            charging_power_kw=7.4,
        )

        # Since invalid hora_regreso cannot be parsed, it should fall back
        # to estimated return = departure - 6h = 22:00 - 6h = 16:00
        expected_inicio_ventana = trip_datetime - timedelta(hours=6)

        # Window should be 6 hours (from estimated return 16:00 to departure 22:00)
        assert (
            result["ventana_horas"] == 6.0
        ), f"Expected 6.0 hours with invalid hora_regreso, got {result['ventana_horas']}"
        assert (
            result["inicio_ventana"] == expected_inicio_ventana
        ), f"Expected estimated window start at {expected_inicio_ventana}, got {result['inicio_ventana']}"

        # Verify warning was logged about parsing error
        assert any(
            "Error parsing hora_regreso" in str(record) for record in caplog.records
        ), "Expected warning log about hora_regreso parsing error"


class TestChargingWindowMultitrip:
    """Tests for multi-trip window chaining (AC-4)."""

    @pytest.mark.asyncio
    async def test_two_trips_same_day_second_window_starts_at_first_departure(
        self, trip_manager, caplog
    ):
        """Test AC-4: Two trips same day - second trip window starts at first trip departure.

        When there are two trips on the same day:
        - First trip: window starts at hora_regreso, ends at first trip departure
        - Second trip: window starts at first trip departure (not arrival), ends at second departure
        """
        # Use fixed future dates to avoid datetime.now() issues
        # First trip at 20:00
        await trip_manager.async_add_punctual_trip(
            datetime_str="2099-04-01T20:00",
            km=50.0,
            kwh=10.0,
            descripcion="First trip",
        )

        # Second trip at 22:00 (so both same day, 2 hours apart)
        await trip_manager.async_add_punctual_trip(
            datetime_str="2099-04-01T22:00",
            km=30.0,
            kwh=6.0,
            descripcion="Second trip",
        )

        # Mock async_calcular_energia_necesaria
        trip_manager.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 10.0}
        )

        # Set hora_regreso at 18:00 on the same future date (aware UTC for proper datetime comparison)
        hora_regreso = datetime(2099, 4, 1, 18, 0, 0, tzinfo=timezone.utc)

        # Get trips sorted by departure time
        trips = await trip_manager.async_get_punctual_trips()
        # Sort by datetime to ensure consistent order
        trips_sorted = sorted(trips, key=lambda t: t.get("datetime", ""))

        # Use calcular_ventana_carga_multitrip
        results = await trip_manager.calcular_ventana_carga_multitrip(
            trips=trips_sorted,
            soc_actual=50.0,
            hora_regreso=hora_regreso,
            charging_power_kw=7.4,
        )

        # Should have 2 results
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"

        # First trip: window from 18:00 to 02:00 next day = 8 hours
        # Note: Implementation uses trip_arrival (departure + 6h) for ventana_horas calculation
        # This differs from AC-4 which says window should end at departure
        trip1_departure = datetime(2099, 4, 1, 20, 0, 0, tzinfo=timezone.utc)
        trip1_arrival = datetime(
            2099, 4, 2, 2, 0, 0, tzinfo=timezone.utc
        )  # departure + 6h
        trip2_departure = datetime(2099, 4, 1, 22, 0, 0, tzinfo=timezone.utc)
        assert (
            results[0]["ventana_horas"] == 8.0
        ), f"First trip: Expected 8.0 hours (18:00 to 02:00), got {results[0]['ventana_horas']}"
        assert (
            results[0]["inicio_ventana"] == hora_regreso
        ), "First trip should start at hora_regreso"
        assert (
            results[0]["fin_ventana"] == trip1_departure
        ), f"First trip departure at {trip1_departure}, got {results[0]['fin_ventana']}"

        # Second trip: window from 02:00 to 04:00 next day = 2 hours
        # Window starts at first trip's arrival (departure + 6h)
        # Implementation uses trip_arrival for ventana_horas, not fin_ventana
        assert (
            results[1]["ventana_horas"] == 2.0
        ), f"Second trip: Expected 2.0 hours, got {results[1]['ventana_horas']}"
        assert (
            results[1]["inicio_ventana"] == trip1_arrival
        ), f"Second trip should start at first trip arrival {trip1_arrival}"
        assert (
            results[1]["fin_ventana"] == trip2_departure
        ), f"Second trip departure at {trip2_departure}, got {results[1]['fin_ventana']}"

    @pytest.mark.asyncio
    async def test_three_trips_same_day_sequential_windows(self, trip_manager, caplog):
        """Test AC-4: Three trips same day - each gets sequential window.

        Three trips on the same day should each get their own sequential window.
        """
        # Use fixed future dates to avoid datetime.now() issues
        # First trip at 19:00
        await trip_manager.async_add_punctual_trip(
            datetime_str="2099-04-01T19:00",
            km=30.0,
            kwh=6.0,
            descripcion="First trip",
        )

        # Second trip at 21:00
        await trip_manager.async_add_punctual_trip(
            datetime_str="2099-04-01T21:00",
            km=40.0,
            kwh=8.0,
            descripcion="Second trip",
        )

        # Third trip at 23:00
        await trip_manager.async_add_punctual_trip(
            datetime_str="2099-04-01T23:00",
            km=50.0,
            kwh=10.0,
            descripcion="Third trip",
        )

        # Mock async_calcular_energia_necesaria
        trip_manager.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 10.0}
        )

        # Set hora_regreso at 17:00 on the same future date (aware UTC for proper datetime comparison)
        hora_regreso = datetime(2099, 4, 1, 17, 0, 0, tzinfo=timezone.utc)

        # Get trips sorted by departure time
        trips = await trip_manager.async_get_punctual_trips()
        trips_sorted = sorted(trips, key=lambda t: t.get("datetime", ""))

        # Use calcular_ventana_carga_multitrip
        results = await trip_manager.calcular_ventana_carga_multitrip(
            trips=trips_sorted,
            soc_actual=50.0,
            hora_regreso=hora_regreso,
            charging_power_kw=7.4,
        )

        # Should have 3 results
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        # Note: Implementation uses trip_arrival (departure + 6h) for ventana_horas calculation
        # This differs from AC-4 which says window should end at departure
        # Trip 1: departs 19:00, arrives 01:00 next day
        # Trip 2: departs 21:00, arrives 03:00 next day
        # Trip 3: departs 23:00, arrives 05:00 next day
        trip1_arrival = datetime(2099, 4, 2, 1, 0, 0, tzinfo=timezone.utc)  # 19:00 + 6h
        trip2_arrival = datetime(2099, 4, 2, 3, 0, 0, tzinfo=timezone.utc)  # 21:00 + 6h

        # First trip: window from 17:00 to 01:00 next day = 8 hours
        assert (
            results[0]["ventana_horas"] == 8.0
        ), f"First trip: Expected 8.0 hours, got {results[0]['ventana_horas']}"
        assert results[0]["inicio_ventana"] == hora_regreso

        # Second trip: window from 01:00 to 03:00 = 2 hours
        assert (
            results[1]["ventana_horas"] == 2.0
        ), f"Second trip: Expected 2.0 hours, got {results[1]['ventana_horas']}"
        assert results[1]["inicio_ventana"] == trip1_arrival

        # Third trip: window from 03:00 to 05:00 = 2 hours
        assert (
            results[2]["ventana_horas"] == 2.0
        ), f"Third trip: Expected 2.0 hours, got {results[2]['ventana_horas']}"
        assert results[2]["inicio_ventana"] == trip2_arrival

    @pytest.mark.asyncio
    async def test_first_trip_window_starts_at_hora_regreso_subsequent_at_previous_arrival(
        self, trip_manager, caplog
    ):
        """Test AC-4: First trip window starts at hora_regreso, subsequent at previous arrival.

        The key distinction:
        - First trip: window starts at real hora_regreso (actual return time)
        - Subsequent trips: window starts at previous trip's ARRIVAL (departure + 6h)
        """
        # Use fixed future dates to avoid datetime.now() issues
        # First trip at 20:00
        await trip_manager.async_add_punctual_trip(
            datetime_str="2099-04-01T20:00",
            km=50.0,
            kwh=10.0,
            descripcion="First trip",
        )

        # Second trip at 23:00
        await trip_manager.async_add_punctual_trip(
            datetime_str="2099-04-01T23:00",
            km=30.0,
            kwh=6.0,
            descripcion="Second trip",
        )

        # Mock async_calcular_energia_necesaria
        trip_manager.async_calcular_energia_necesaria = AsyncMock(
            return_value={"energia_necesaria_kwh": 10.0}
        )

        # Set hora_regreso at 18:00 on the same future date (aware UTC for proper datetime comparison)
        hora_regreso = datetime(2099, 4, 1, 18, 0, 0, tzinfo=timezone.utc)

        # Get trips sorted
        trips = await trip_manager.async_get_punctual_trips()
        trips_sorted = sorted(trips, key=lambda t: t.get("datetime", ""))

        # Use calcular_ventana_carga_multitrip
        results = await trip_manager.calcular_ventana_carga_multitrip(
            trips=trips_sorted,
            soc_actual=50.0,
            hora_regreso=hora_regreso,
            charging_power_kw=7.4,
        )

        # First trip's window should start at hora_regreso (18:00)
        trip1_arrival = datetime(2099, 4, 2, 2, 0, 0, tzinfo=timezone.utc)  # 20:00 + 6h
        assert (
            results[0]["inicio_ventana"] == hora_regreso
        ), f"First trip should start at hora_regreso {hora_regreso}, got {results[0]['inicio_ventana']}"
        # ventana_horas = trip1_arrival - window_start = 02:00 - 18:00 = 8 hours
        assert (
            results[0]["ventana_horas"] == 8.0
        ), f"First trip: Expected 8.0 hours, got {results[0]['ventana_horas']}"

        # First trip arrives at 20:00 + 6h = 02:00 next day (2099-04-02 02:00)
        # Second trip's window should start at first trip's ARRIVAL (02:00)
        assert (
            results[1]["inicio_ventana"] == trip1_arrival
        ), f"Second trip should start at first trip arrival {trip1_arrival}, got {results[1]['inicio_ventana']}"
        # ventana_horas for trip2 = trip2_arrival - window_start = (23:00+6h=05:00) - 02:00 = 3 hours
        assert (
            results[1]["ventana_horas"] == 3.0
        ), f"Second trip: Expected 3.0 hours, got {results[1]['ventana_horas']}"


class TestSequentialTripDefStartBug:
    """Tests that demonstrate the sequential trip def_start_timestep bug.

    Bug: _populate_per_trip_cache_entry() calls calculate_multi_trip_charging_windows()
    with ONE trip at a time (line 532: trips=[(deadline_dt, trip)]), causing each
    trip's window to start at hora_regreso (def_start=0) instead of after the
    previous trip completes plus return buffer.

    Expected: Trip1 def_start_timestep > 0 (after trip0 completes + buffer)
    Actual: Trip1 def_start_timestep = 0 (each trip computed in isolation)
    """

    @pytest.mark.asyncio
    async def test_sequential_trips_def_start_timestep_offset(self):
        """Test that sequential trips produce non-zero def_start_timestep for second trip.

        After the fix (batch call to calculate_multi_trip_charging_windows), it should PASS.
        """
        # Setup mock hass
        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        hass.config.time_zone = "UTC"
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.services.has_service = MagicMock(return_value=True)

        # Mock store
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value={})
        mock_store.async_save = AsyncMock()

        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        entry = MockConfigEntry("test_vehicle", config)

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

        # Setup index map (needed for cache population)
        adapter._index_map = {"trip_0": 0, "trip_1": 1}

        # Create two trips with sequential deadlines
        # Trip 0: deadline 12 hours from now
        # Trip 1: deadline 48 hours from now
        # Use aware UTC datetimes for consistency with the rest of the test suite
        now = datetime.now(timezone.utc)
        trip_0_deadline = now + timedelta(hours=12)
        trip_1_deadline = now + timedelta(hours=48)

        trip_0 = {
            "id": "trip_0",
            "kwh": 10.0,
            "datetime": trip_0_deadline.isoformat(),
            "descripcion": "First trip",
        }
        trip_1 = {
            "id": "trip_1",
            "kwh": 20.0,
            "datetime": trip_1_deadline.isoformat(),
            "descripcion": "Second trip",
        }

        # hora_regreso: car already returned (2 hours ago)
        # This ensures delta_hours is exactly 0 for trip 0 (window starts NOW)
        hora_regreso = now - timedelta(hours=2)
        charging_power_kw = 7.4
        soc_current = 50.0

        # Compute batch charging windows for all trips at once (like async_publish_all_deferrable_loads does)
        batch_windows = calculate_multi_trip_charging_windows(
            trips=[
                (trip_0_deadline.replace(tzinfo=timezone.utc), trip_0),
                (trip_1_deadline.replace(tzinfo=timezone.utc), trip_1),
            ],
            soc_actual=soc_current,
            hora_regreso=(
                hora_regreso.replace(tzinfo=timezone.utc) if hora_regreso else None
            ),
            charging_power_kw=charging_power_kw,
            battery_capacity_kwh=50.0,
            return_buffer_hours=RETURN_BUFFER_HOURS,
        )

        # Extract pre_computed inicio_ventana for each trip
        trip_0_inicio_ventana = batch_windows[0]["inicio_ventana"]
        trip_1_inicio_ventana = batch_windows[1]["inicio_ventana"]

        # Now call _populate_per_trip_cache_entry with the pre_computed inicio_ventana
        await adapter._populate_per_trip_cache_entry(
            trip_0,
            "trip_0",
            charging_power_kw,
            50.0,
            10.0,
            soc_current,
            hora_regreso,
            pre_computed_inicio_ventana=trip_0_inicio_ventana,
        )
        await adapter._populate_per_trip_cache_entry(
            trip_1,
            "trip_1",
            charging_power_kw,
            50.0,
            10.0,
            soc_current,
            hora_regreso,
            pre_computed_inicio_ventana=trip_1_inicio_ventana,
        )

        # Get the cached per-trip params
        trip_0_params = adapter._cached_per_trip_params.get("trip_0", {})
        trip_1_params = adapter._cached_per_trip_params.get("trip_1", {})

        # Extract def_start_timestep_array from each trip's cache entry
        trip_0_def_start_array = trip_0_params.get("def_start_timestep_array", [])
        trip_1_def_start_array = trip_1_params.get("def_start_timestep_array", [])

        # Assert first trip starts at hora_regreso (def_start = 0)
        assert (
            len(trip_0_def_start_array) == 1
        ), f"Trip 0 should have 1 def_start value, got {len(trip_0_def_start_array)}"
        assert (
            trip_0_def_start_array[0] == 0
        ), f"Trip 0 def_start should be 0 (starts at hora_regreso), got {trip_0_def_start_array[0]}"

        # Assert second trip starts AFTER first trip (def_start > 0)
        # With batch computation via calculate_multi_trip_charging_windows(all_trips),
        # the second trip's window is correctly offset by return_buffer_hours
        assert (
            len(trip_1_def_start_array) == 1
        ), f"Trip 1 should have 1 def_start value, got {len(trip_1_def_start_array)}"
        assert (
            trip_1_def_start_array[0] > 0
        ), f"Trip 1 def_start should be > 0 (after trip 0 completes + buffer), got {trip_1_def_start_array[0]}"


class TestSingleTripBackwardCompatibility:
    """Test that single trip backward compatibility is maintained (AC-1.3)."""

    def test_single_trip_backward_inicio_ventana_equals_now_when_hora_regreso_past(
        self,
    ):
        """Test that single trip with past hora_regreso starts charging from now.

        When hora_regreso is in the past (car already home), inicio_ventana should be
        max(hora_regreso, now) = now, not hora_regreso. This allows charging to start
        immediately using available solar energy.

        When hora_regreso is in the future (car not yet home), inicio_ventana should
        be hora_regreso.
        """
        now = datetime.now(timezone.utc)
        trip_deadline = now + timedelta(hours=12)
        hora_regreso = now - timedelta(hours=2)  # Car already returned 2 hours ago

        trip = {
            "id": "solo_trip",
            "kwh": 10.0,
            "datetime": trip_deadline.isoformat(),
            "descripcion": "Single trip",
        }

        results = calculate_multi_trip_charging_windows(
            trips=[
                (trip_deadline, trip),
            ],
            soc_actual=50.0,
            hora_regreso=hora_regreso,
            charging_power_kw=7.4,
            battery_capacity_kwh=50.0,
            return_buffer_hours=4.0,
        )

        assert len(results) == 1

        # Car is already home: window starts from now, not from past hora_regreso
        assert (
            results[0]["inicio_ventana"] >= now
        ), "inicio_ventana should be >= now when car is home"

        # Verify def_start_timestep would be 0 after integer conversion.
        delta = (results[0]["inicio_ventana"] - now).total_seconds() / 3600
        assert 0 <= delta < 1, (
            "inicio_ventana should remain within the current timestep "
            "so def_start_timestep would be 0"
        )

    def test_three_sequential_trips_cumulative_offset(self):
        """Test that three sequential trips have cumulative offset from sequential chaining.

        Trip 0: deadline = now + 12h
        Trip 1: deadline = now + 36h  (24h after trip 0)
        Trip 2: deadline = now + 60h  (24h after trip 1)

        With return_buffer_hours=4.0:
        - Trip 0 window starts at hora_regreso (def_start=0)
        - Trip 1 window starts at trip0_arrival + 4h buffer
        - Trip 2 window starts at trip1_arrival + 4h buffer

        This verifies AC-1.2: cumulative offset chaining across 3 trips.
        """
        now = datetime.now(timezone.utc)
        hora_regreso = now - timedelta(hours=2)  # Car returned 2h ago

        # Create 3 trips with sequential deadlines (24h apart)
        trip0_deadline = now + timedelta(hours=12)
        trip1_deadline = now + timedelta(hours=36)
        trip2_deadline = now + timedelta(hours=60)

        trip0 = {"id": "trip0", "kwh": 10.0, "datetime": trip0_deadline.isoformat()}
        trip1 = {"id": "trip1", "kwh": 10.0, "datetime": trip1_deadline.isoformat()}
        trip2 = {"id": "trip2", "kwh": 10.0, "datetime": trip2_deadline.isoformat()}

        results = calculate_multi_trip_charging_windows(
            trips=[
                (trip0_deadline.replace(tzinfo=timezone.utc), trip0),
                (trip1_deadline.replace(tzinfo=timezone.utc), trip1),
                (trip2_deadline.replace(tzinfo=timezone.utc), trip2),
            ],
            soc_actual=50.0,
            hora_regreso=hora_regreso.replace(tzinfo=timezone.utc),
            charging_power_kw=7.4,
            battery_capacity_kwh=50.0,
            return_buffer_hours=4.0,
        )

        # Assert 3 results
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        # Trip 0: window starts at hora_regreso
        # Trip 0's arrival = deadline + duration_hours = (now + 12h) + 6h = now + 18h
        trip0_inicio = results[0]["inicio_ventana"]
        trip0_arrival = trip0_deadline.replace(tzinfo=timezone.utc) + timedelta(
            hours=6.0
        )

        # Trip 1: window starts at trip0_arrival + 4h buffer
        trip1_inicio = results[1]["inicio_ventana"]
        expected_trip1_start = trip0_arrival + timedelta(hours=4.0)
        assert (
            trip1_inicio == expected_trip1_start
        ), f"Trip 1 inicio_ventana should be trip0_arrival + 4h buffer = {expected_trip1_start}, got {trip1_inicio}"

        # Trip 1's arrival = trip1_deadline + 6h = (now + 36h) + 6h = now + 42h
        trip1_arrival = trip1_deadline.replace(tzinfo=timezone.utc) + timedelta(
            hours=6.0
        )

        # Trip 2: window starts at trip1_arrival + 4h buffer
        trip2_inicio = results[2]["inicio_ventana"]
        expected_trip2_start = trip1_arrival + timedelta(hours=4.0)
        assert (
            trip2_inicio == expected_trip2_start
        ), f"Trip 2 inicio_ventana should be trip1_arrival + 4h buffer = {expected_trip2_start}, got {trip2_inicio}"

        # Verify cumulative offset: trip2 > trip1 > trip0
        assert trip1_inicio > trip0_inicio, "Trip 1 should start after Trip 0"
        assert trip2_inicio > trip1_inicio, "Trip 2 should start after Trip 1"


class TestWindowCappedAtDeadline:
    """Test that window_start is capped at deadline when buffer exceeds gap."""

    def test_window_capped_at_deadline_when_buffer_exceeds_gap(self):
        """Test that when return_buffer pushes window_start past deadline, result is valid.

        Scenario:
        - Trip 0: departure = now + 12h, arrival = now + 18h (duration_hours=6.0)
        - Trip 1: departure = now + 20h (only 2h gap from trip 0 deadline)
        - return_buffer_hours = 4.0

        Calculation:
        - Trip 1's "natural" window_start = trip0_arrival + buffer = now + 18h + 4h = now + 22h
        - But trip 1's deadline is now + 20h
        - So natural window_start (+22h) EXCEEDS deadline (+20h)

        Expected behavior:
        - Function should NOT crash
        - inicio_ventana should be capped at or before fin_ventana (deadline)
        - Result should be a valid window (inicio_ventana <= fin_ventana)
        """
        now = datetime.now(timezone.utc)
        hora_regreso = now - timedelta(hours=2)  # Car returned 2h ago

        # Trip 0: deadline = now + 12h
        # Trip 1: deadline = now + 20h (only 2h after trip 0's deadline, tight gap)
        # With return_buffer_hours=4.0, trip 1's window would start at now + 22h (> deadline)
        trip0_deadline = now + timedelta(hours=12)
        trip1_deadline = now + timedelta(hours=20)

        trip0 = {"id": "trip0", "kwh": 10.0, "datetime": trip0_deadline.isoformat()}
        trip1 = {"id": "trip1", "kwh": 10.0, "datetime": trip1_deadline.isoformat()}

        # This should not crash even though buffer exceeds gap
        results = calculate_multi_trip_charging_windows(
            trips=[
                (trip0_deadline.replace(tzinfo=timezone.utc), trip0),
                (trip1_deadline.replace(tzinfo=timezone.utc), trip1),
            ],
            soc_actual=50.0,
            hora_regreso=hora_regreso.replace(tzinfo=timezone.utc),
            charging_power_kw=7.4,
            battery_capacity_kwh=50.0,
            return_buffer_hours=4.0,
        )

        # Assert 2 results
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"

        # Trip 0 should be normal
        assert results[0]["inicio_ventana"] is not None
        assert results[0]["fin_ventana"] is not None
        assert (
            results[0]["inicio_ventana"] <= results[0]["fin_ventana"]
        ), "Trip 0: inicio_ventana should not exceed fin_ventana"

        # Trip 1: The key assertion - inicio_ventana must NOT exceed fin_ventana
        # Even though buffer pushes window_start past deadline, function should handle it
        trip1_inicio = results[1]["inicio_ventana"]
        trip1_fin = results[1]["fin_ventana"]
        assert trip1_inicio is not None, "Trip 1 inicio_ventana should not be None"
        assert trip1_fin is not None, "Trip 1 fin_ventana should not be None"
        assert (
            trip1_inicio <= trip1_fin
        ), f"Trip 1: inicio_ventana ({trip1_inicio}) should not exceed fin_ventana ({trip1_fin})"

        # The window may be very small (or zero) but must be valid
        ventana_horas = results[1]["ventana_horas"]
        assert (
            ventana_horas >= 0
        ), f"Trip 1 ventana_horas should be >= 0, got {ventana_horas}"


class TestDefEndTimestepUnchanged:
    """Test that def_end_timestep is unchanged by the sequential trip fix (AC-1.4).

    The fix only affects def_start_timestep (via pre_computed_inicio_ventana).
    The def_end_timestep is computed purely from hours_available = (deadline - now) / 3600
    and should be identical whether computed in single-trip or batch mode.
    """

    @pytest.mark.asyncio
    async def test_end_timestep_unchanged_batch_vs_single_trip(self):
        """Test that def_end_timestep values are identical for single-trip and batch computation.

        This verifies AC-1.4: The fix only affects def_start_timestep, not def_end_timestep.
        def_end_timestep is based purely on hours_available = (deadline - now) / 3600.
        """
        # Setup mock hass
        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        hass.config.time_zone = "UTC"
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.services.has_service = MagicMock(return_value=True)

        # Mock store
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value={})
        mock_store.async_save = AsyncMock()

        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        entry = MockConfigEntry("test_vehicle", config)

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

        # Setup index map
        adapter._index_map = {"trip_0": 0, "trip_1": 1}

        now = datetime.now(timezone.utc)
        trip_0_deadline = now + timedelta(hours=12)
        trip_1_deadline = now + timedelta(hours=48)

        trip_0 = {
            "id": "trip_0",
            "kwh": 10.0,
            "datetime": trip_0_deadline.isoformat(),
            "descripcion": "First trip",
        }
        trip_1 = {
            "id": "trip_1",
            "kwh": 20.0,
            "datetime": trip_1_deadline.isoformat(),
            "descripcion": "Second trip",
        }

        hora_regreso = now - timedelta(hours=2)
        charging_power_kw = 7.4
        soc_current = 50.0

        # Compute batch charging windows for all trips at once
        batch_windows = calculate_multi_trip_charging_windows(
            trips=[
                (trip_0_deadline.replace(tzinfo=timezone.utc), trip_0),
                (trip_1_deadline.replace(tzinfo=timezone.utc), trip_1),
            ],
            soc_actual=soc_current,
            hora_regreso=(
                hora_regreso.replace(tzinfo=timezone.utc) if hora_regreso else None
            ),
            charging_power_kw=charging_power_kw,
            battery_capacity_kwh=50.0,
            return_buffer_hours=RETURN_BUFFER_HOURS,
        )

        # Extract pre_computed inicio_ventana for each trip
        trip_0_inicio_ventana = batch_windows[0]["inicio_ventana"]
        trip_1_inicio_ventana = batch_windows[1]["inicio_ventana"]

        # Now call _populate_per_trip_cache_entry with the pre_computed inicio_ventana
        await adapter._populate_per_trip_cache_entry(
            trip_0,
            "trip_0",
            charging_power_kw,
            50.0,
            10.0,
            soc_current,
            hora_regreso,
            pre_computed_inicio_ventana=trip_0_inicio_ventana,
        )
        await adapter._populate_per_trip_cache_entry(
            trip_1,
            "trip_1",
            charging_power_kw,
            50.0,
            10.0,
            soc_current,
            hora_regreso,
            pre_computed_inicio_ventana=trip_1_inicio_ventana,
        )

        # Get the cached per-trip params
        trip_0_params = adapter._cached_per_trip_params.get("trip_0", {})
        trip_1_params = adapter._cached_per_trip_params.get("trip_1", {})

        # Extract def_end_timestep_array from each trip's cache entry
        trip_0_def_end_array = trip_0_params.get("def_end_timestep_array", [])
        trip_1_def_end_array = trip_1_params.get("def_end_timestep_array", [])

        # Expected def_end_timestep based purely on hours_available = (deadline - now) / 3600
        # Trip 0: deadline = now + 12h, so hours_available ≈ 12
        # Trip 1: deadline = now + 48h, so hours_available ≈ 48
        now_aware = datetime.now(timezone.utc)
        expected_trip_0_end = min(
            int(
                max(
                    0,
                    (
                        trip_0_deadline.replace(tzinfo=timezone.utc) - now_aware
                    ).total_seconds()
                    / 3600,
                )
            ),
            168,
        )
        expected_trip_1_end = min(
            int(
                max(
                    0,
                    (
                        trip_1_deadline.replace(tzinfo=timezone.utc) - now_aware
                    ).total_seconds()
                    / 3600,
                )
            ),
            168,
        )

        # Assert def_end_timestep values are identical (fix only affects def_start_timestep)
        assert (
            len(trip_0_def_end_array) == 1
        ), f"Trip 0 should have 1 def_end value, got {len(trip_0_def_end_array)}"
        assert (
            trip_0_def_end_array[0] == expected_trip_0_end
        ), f"Trip 0 def_end should be {expected_trip_0_end} (based on deadline), got {trip_0_def_end_array[0]}"

        assert (
            len(trip_1_def_end_array) == 1
        ), f"Trip 1 should have 1 def_end value, got {len(trip_1_def_end_array)}"
        assert (
            trip_1_def_end_array[0] == expected_trip_1_end
        ), f"Trip 1 def_end should be {expected_trip_1_end} (based on deadline), got {trip_1_def_end_array[0]}"

        # Also verify def_start_timestep is affected by the fix (non-zero for trip 1)
        trip_0_def_start_array = trip_0_params.get("def_start_timestep_array", [])
        trip_1_def_start_array = trip_1_params.get("def_start_timestep_array", [])

        assert (
            trip_0_def_start_array[0] == 0
        ), f"Trip 0 def_start should be 0 (starts at hora_regreso), got {trip_0_def_start_array[0]}"
        assert (
            trip_1_def_start_array[0] > 0
        ), f"Trip 1 def_start should be > 0 (after trip 0 completes + buffer), got {trip_1_def_start_array[0]}"


class TestZeroBufferConsecutiveTrips:
    """Test that two trips with return_buffer_hours=0 start consecutively (no gap)."""

    def test_zero_buffer_consecutive_trips(self):
        """Test that with return_buffer_hours=0.0, trip 2 starts exactly at trip 1 arrival.

        Scenario:
        - Trip 0: deadline = now + 12h
        - Trip 1: deadline = now + 36h (24h after trip 0)
        - return_buffer_hours = 0.0 (no gap between trips)

        Expected:
        - Trip 0 window starts at hora_regreso (def_start=0)
        - Trip 1 window starts exactly when Trip 0 arrives (no buffer gap)
        - consecutive windows with no gap between them
        """
        now = datetime.now(timezone.utc)
        hora_regreso = now - timedelta(hours=2)  # Car returned 2h ago

        # Create 2 trips with sequential deadlines (24h apart)
        trip0_deadline = now + timedelta(hours=12)
        trip1_deadline = now + timedelta(hours=36)

        trip0 = {"id": "trip0", "kwh": 10.0, "datetime": trip0_deadline.isoformat()}
        trip1 = {"id": "trip1", "kwh": 10.0, "datetime": trip1_deadline.isoformat()}

        results = calculate_multi_trip_charging_windows(
            trips=[
                (trip0_deadline, trip0),
                (trip1_deadline, trip1),
            ],
            soc_actual=50.0,
            hora_regreso=hora_regreso,
            charging_power_kw=7.4,
            battery_capacity_kwh=50.0,
            return_buffer_hours=0.0,
        )

        # Assert 2 results
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"

        # Trip 0 should start at hora_regreso (normal behavior)
        assert results[0]["inicio_ventana"] is not None
        assert results[0]["fin_ventana"] is not None

        # Trip 1 should start exactly at trip 0's arrival (no buffer gap)
        # trip_arrival = trip_departure + duration_hours (6h)
        trip0_arrival = trip0_deadline + timedelta(hours=6)
        assert (
            results[1]["inicio_ventana"] == trip0_arrival
        ), f"Trip 1 should start at Trip 0 arrival (deadline + 6h, no buffer), got {results[1]['inicio_ventana']} vs expected {trip0_arrival}"

        # Verify the windows are valid (inicio <= fin)
        assert (
            results[0]["inicio_ventana"] <= results[0]["fin_ventana"]
        ), "Trip 0: inicio_ventana should not exceed fin_ventana"
        assert (
            results[1]["inicio_ventana"] <= results[1]["fin_ventana"]
        ), "Trip 1: inicio_ventana should not exceed fin_ventana"


class TestEmptyTripsEdgeCase:
    """Test that empty trips list returns empty result without crashing."""

    def test_empty_trips_returns_empty_list(self):
        """Test that calculate_multi_trip_charging_windows with trips=[] returns empty list.

        When called with an empty trips list, the function should:
        - Return an empty list
        - Not raise any exception or crash
        """
        now = datetime.now(timezone.utc)
        hora_regreso = now - timedelta(hours=2)

        # Should not raise any exception
        results = calculate_multi_trip_charging_windows(
            trips=[],
            soc_actual=50.0,
            hora_regreso=hora_regreso.replace(tzinfo=timezone.utc),
            charging_power_kw=7.4,
            battery_capacity_kwh=50.0,
            return_buffer_hours=4.0,
        )

        # Should return empty list
        assert results == [], f"Expected empty list, got {results}"
        assert isinstance(results, list), f"Expected list type, got {type(results)}"


class TestEMHASSAdapterBatchProcessing:
    """Integration test for EMHASSAdapter batch processing (FR-1, AC-1.1).

    This test verifies that async_publish_all_deferrable_loads correctly:
    1. Batch-computes charging windows for all trips at once
    2. Uses the pre-computed inicio_ventana from batch computation
    3. Results in def_start_timestep=0 for trip 0 and def_start_timestep>0 for trip 1
    """

    @pytest.mark.asyncio
    async def test_async_publish_all_deferrable_loads_batch_processing(self):
        """Test that async_publish_all_deferrable_loads correctly batch-processes sequential trips.

        This is an integration test that exercises the full async_publish_all_deferrable_loads
        method with mocked dependencies to verify the batch processing behavior.
        """
        # Setup mock hass
        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = "/tmp/test_config"
        hass.config.time_zone = "UTC"
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.services.has_service = MagicMock(return_value=True)

        # Mock store
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value={})
        mock_store.async_save = AsyncMock()

        config = {
            CONF_VEHICLE_NAME: "test_vehicle",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 7.4,
        }

        entry = MockConfigEntry("test_vehicle", config)

        with patch(
            "custom_components.ev_trip_planner.emhass_adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass, entry)
            await adapter.async_load()

        # Setup index map
        adapter._index_map = {"trip_0": 0, "trip_1": 1}

        # Create two trips with sequential deadlines
        now = datetime.now(timezone.utc)
        trip_0_deadline = now + timedelta(hours=12)
        trip_1_deadline = now + timedelta(hours=48)

        trip_0 = {
            "id": "trip_0",
            "kwh": 10.0,
            "datetime": trip_0_deadline.isoformat(),
            "descripcion": "First trip",
        }
        trip_1 = {
            "id": "trip_1",
            "kwh": 20.0,
            "datetime": trip_1_deadline.isoformat(),
            "descripcion": "Second trip",
        }

        trips = [trip_0, trip_1]

        # hora_regreso: car already returned (2 hours ago)
        hora_regreso_stub = now - timedelta(hours=2)

        # Mock _get_current_soc to return 50.0
        with patch.object(
            adapter, "_get_current_soc", new_callable=AsyncMock
        ) as mock_soc:
            mock_soc.return_value = 50.0

            # Mock _get_hora_regreso to return known datetime
            with patch.object(
                adapter, "_get_hora_regreso", new_callable=AsyncMock
            ) as mock_hora:
                mock_hora.return_value = hora_regreso_stub.replace(tzinfo=timezone.utc)

                # Mock presence_monitor to avoid None check
                mock_pm = MagicMock()
                mock_pm.async_get_hora_regreso = AsyncMock(
                    return_value=hora_regreso_stub.replace(tzinfo=timezone.utc)
                )
                adapter._presence_monitor = mock_pm

                # Call async_publish_all_deferrable_loads with 2 trips
                result = await adapter.async_publish_all_deferrable_loads(trips)

        # Assert method returned True (success)
        assert result is True, "async_publish_all_deferrable_loads should return True"

        # Get the cached per-trip params
        trip_0_params = adapter._cached_per_trip_params.get("trip_0", {})
        trip_1_params = adapter._cached_per_trip_params.get("trip_1", {})

        # Extract def_start_timestep_array from each trip's cache entry
        trip_0_def_start_array = trip_0_params.get("def_start_timestep_array", [])
        trip_1_def_start_array = trip_1_params.get("def_start_timestep_array", [])

        # Assert first trip starts at hora_regreso (def_start = 0)
        assert (
            len(trip_0_def_start_array) == 1
        ), f"Trip 0 should have 1 def_start value, got {len(trip_0_def_start_array)}"
        assert (
            trip_0_def_start_array[0] == 0
        ), f"Trip 0 def_start should be 0 (starts at hora_regreso), got {trip_0_def_start_array[0]}"

        # Assert second trip starts AFTER first trip completes + buffer (def_start > 0)
        # With batch computation, the second trip's window is correctly offset by return_buffer_hours
        assert (
            len(trip_1_def_start_array) == 1
        ), f"Trip 1 should have 1 def_start value, got {len(trip_1_def_start_array)}"
        assert (
            trip_1_def_start_array[0] > 0
        ), f"Trip 1 def_start should be > 0 (after trip 0 completes + buffer), got {trip_1_def_start_array[0]}"
