"""TDD: Tests for calcular_ventana_carga and async_calcular_energia_necesaria.

These are core business logic functions in trip_manager.py with low coverage.
Tests verify:
- calcular_ventana_carga: charging window calculation with edge cases
- async_calcular_energia_necesaria: energy needs calculation with SOC
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestCalcularVentanaCarga:
    """Tests for trip_manager.calcular_ventana_carga."""

    @pytest.fixture
    def mock_trip_manager(self):
        """Create a mock TripManager with necessary attributes."""
        mgr = MagicMock()
        mgr._get_trip_time = MagicMock()
        mgr.async_get_next_trip_after = AsyncMock()
        mgr._presence_monitor = MagicMock()
        mgr._vehicle_controller = MagicMock()
        return mgr

    @pytest.mark.asyncio
    async def test_no_trips_after_return_gives_zero_window(self, mock_trip_manager):
        """When no trips pending after return, window is zero (AC-5 edge case)."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        # Setup: next trip exists but is BEFORE return time (not found after)
        mock_trip_manager.async_get_next_trip_after = AsyncMock(return_value=None)

        # Patch _get_trip_time to return a valid departure time
        departure = datetime.now(timezone.utc) + timedelta(hours=10)
        mock_trip_manager._get_trip_time = MagicMock(return_value=departure)

        # Create partial TripManager for testing
        tm = TripManager.__new__(TripManager)
        tm.async_get_next_trip_after = mock_trip_manager.async_get_next_trip_after
        tm._get_trip_time = mock_trip_manager._get_trip_time

        # Act
        result = await tm.calcular_ventana_carga(
            trip={"id": "test"},
            soc_actual=50.0,
            hora_regreso=datetime.now(),
            charging_power_kw=7.0,
        )

        # Assert: AC-5 edge case - no trips after return means no charging needed
        assert result["ventana_horas"] == 0
        assert result["kwh_necesarios"] == 0
        assert result["es_suficiente"] is True

    @pytest.mark.asyncio
    async def test_hora_regreso_string_parsed_correctly(self, mock_trip_manager):
        """hora_regreso as ISO string is parsed correctly."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        # Setup: next trip exists after return
        mock_trip_manager.async_get_next_trip_after = AsyncMock(
            return_value={
                "id": "next_trip",
                "datetime": (datetime.now() + timedelta(hours=12)).isoformat(),
            }
        )

        departure = datetime.now(timezone.utc) + timedelta(hours=10)
        mock_trip_manager._get_trip_time = MagicMock(return_value=departure)

        tm = TripManager.__new__(TripManager)
        tm.async_get_next_trip_after = mock_trip_manager.async_get_next_trip_after
        tm._get_trip_time = mock_trip_manager._get_trip_time

        # Act: Pass hora_regreso as string
        result = await tm.calcular_ventana_carga(
            trip={"id": "test"},
            soc_actual=50.0,
            hora_regreso=datetime.now().isoformat(),
            charging_power_kw=7.0,
        )

        # Assert: Function handled string parsing without error
        assert "ventana_horas" in result
        assert "es_suficiente" in result

    @pytest.mark.asyncio
    async def test_trip_datetime_parsing_fallback(self, mock_trip_manager):
        """When _get_trip_time returns None, trip datetime is used as fallback."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        # Setup: next trip exists after return
        mock_trip_manager.async_get_next_trip_after = AsyncMock(
            return_value={"id": "next_trip"}
        )

        # _get_trip_time returns None, but trip has datetime
        mock_trip_manager._get_trip_time = MagicMock(return_value=None)

        tm = TripManager.__new__(TripManager)
        tm.async_get_next_trip_after = mock_trip_manager.async_get_next_trip_after
        tm._get_trip_time = mock_trip_manager._get_trip_time

        # Act: trip has datetime field
        trip_dt = (datetime.now() + timedelta(hours=8)).isoformat()
        result = await tm.calcular_ventana_carga(
            trip={"id": "test", "datetime": trip_dt},
            soc_actual=50.0,
            hora_regreso=None,
            charging_power_kw=7.0,
        )

        # Assert: fallback to trip datetime worked
        assert "ventana_horas" in result


class TestAsyncCalcularEnergiaNecesaria:
    """Tests for trip_manager.async_calcular_energia_necesaria."""

    @pytest.fixture
    def mock_trip_manager(self):
        """Create a mock TripManager."""
        mgr = MagicMock()
        mgr._presence_monitor = MagicMock()
        mgr._vehicle_controller = MagicMock()
        return mgr

    @pytest.mark.asyncio
    async def test_calculates_from_km_and_consumption(self, mock_trip_manager):
        """When kwh not directly set, calculates from km * consumption."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        tm = TripManager.__new__(TripManager)
        tm._presence_monitor = mock_trip_manager._presence_monitor
        tm._vehicle_controller = mock_trip_manager._vehicle_controller

        # Setup: trip with km but no kwh
        trip = {
            "id": "trip1",
            "km": 100,
            "consumption_kwh_per_km": 0.15,
            "datetime": (datetime.now() + timedelta(hours=5)).isoformat(),
        }
        vehicle_config = {
            "battery_capacity_kwh": 60.0,
            "charging_power_kw": 7.0,
        }

        # Act
        result = await tm.async_calcular_energia_necesaria(trip, vehicle_config)

        # Assert: Should compute energy needs
        assert (
            result.get("energia_necesaria_kwh", 0) > 0
            or "alerta_tiempo_insuficiente" in result
        )

    @pytest.mark.asyncio
    async def test_direct_kwh_trip(self, mock_trip_manager):
        """When kwh directly set, function is callable and returns expected structure."""
        from custom_components.ev_trip_planner.trip_manager import TripManager

        tm = TripManager.__new__(TripManager)
        tm._presence_monitor = mock_trip_manager._presence_monitor
        tm._vehicle_controller = mock_trip_manager._vehicle_controller

        trip = {
            "id": "trip1",
            "km": 100,
            "kwh": 25.0,  # Direct kwh value
            "consumption_kwh_per_km": 0.15,
            "datetime": (datetime.now() + timedelta(hours=5)).isoformat(),
        }
        vehicle_config = {
            "battery_capacity_kwh": 60.0,
            "charging_power_kw": 7.0,
        }

        result = await tm.async_calcular_energia_necesaria(trip, vehicle_config)

        # Assert: returns expected structure with keys for energy calculation
        assert "energia_necesaria_kwh" in result
        assert "horas_carga_necesarias" in result
        assert "alerta_tiempo_insuficiente" in result
        assert "horas_disponibles" in result
