"""Tests for remaining uncovered lines to achieve 100% coverage.

Targets:
- __init__.py:154-157 - Exception handler in hourly_refresh callback
- trip_manager.py:258-260 - except Exception in weekly trip rotation
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.ev_trip_planner.trip_manager import TripManager


class TestCalculateNextRecurringDatetimeExceptionPath:
    """Tests for trip_manager.py lines 258-260: except Exception in weekly trip rotation."""

    @pytest.mark.asyncio
    async def test_weekly_trip_exception_in_calculate_next_recurring_datetime(self):
        """Test that an exception in calculate_next_recurring_datetime triggers the except block.

        This covers trip_manager.py lines 258-260 where the except block catches
        exceptions raised during the weekly trip rotation.
        """

        # Create mock trip manager
        mock_hass = MagicMock()
        mock_storage = MagicMock()
        mock_storage.async_load = AsyncMock(return_value=None)
        mock_storage.async_save = AsyncMock(return_value=None)

        tm = TripManager(
            hass=mock_hass,
            vehicle_id="test_vehicle",
            entry_id="test_entry",
            presence_config={},
            storage=mock_storage,
        )

        # Mock _get_all_active_trips to return a valid recurring trip
        with patch.object(
            tm,
            "_get_all_active_trips",
            return_value=[
                {
                    "id": "rec_monday_123",
                    "tipo": "recurring",
                    "dia_semana": "lunes",
                    "hora": "18:00",
                    "km": 30.0,
                    "kwh": 5.0,
                    "descripcion": "Test trip",
                    "activo": True,
                    "datetime": datetime.now().isoformat(),
                }
            ],
        ):
            # Mock emhass adapter - MUST be AsyncMock!
            mock_adapter = AsyncMock()
            tm.set_emhass_adapter(mock_adapter)

            # Mock calculate_next_recurring_datetime to raise an exception
            with patch(
                "custom_components.ev_trip_planner.trip_manager.calculate_next_recurring_datetime",
                side_effect=Exception("Simulated calculation error"),
            ):
                # This should trigger the except block in publish_deferrable_loads
                # because calculate_next_recurring_datetime raises an exception
                await tm.publish_deferrable_loads()

                # The warning should have been logged (lines 260-265 executed)

    @pytest.mark.asyncio
    async def test_weekly_trip_exception_in_day_index_calculation(self):
        """Test that an exception in calculate_day_index triggers the except block.

        This covers trip_manager.py lines 258-260 where the except block catches
        exceptions raised during the weekly trip rotation.
        """
        # Create mock trip manager
        mock_hass = MagicMock()
        mock_storage = MagicMock()
        mock_storage.async_load = AsyncMock(return_value=None)
        mock_storage.async_save = AsyncMock(return_value=None)

        tm = TripManager(
            hass=mock_hass,
            vehicle_id="test_vehicle",
            entry_id="test_entry",
            presence_config={},
            storage=mock_storage,
        )

        # Mock _get_all_active_trips to return a valid recurring trip
        with patch.object(
            tm,
            "_get_all_active_trips",
            return_value=[
                {
                    "id": "rec_monday_456",
                    "tipo": "recurring",
                    "dia_semana": "lunes",
                    "hora": "18:00",
                    "km": 30.0,
                    "kwh": 5.0,
                    "descripcion": "Test trip",
                    "activo": True,
                    "datetime": datetime.now().isoformat(),
                }
            ],
        ):
            # Mock emhass adapter - MUST be AsyncMock!
            mock_adapter = AsyncMock()
            tm.set_emhass_adapter(mock_adapter)

            # Mock calculate_day_index to raise an exception
            with patch(
                "custom_components.ev_trip_planner.trip_manager.calculate_day_index",
                side_effect=Exception("Simulated day_index error"),
            ):
                # This should trigger the except block in publish_deferrable_loads
                await tm.publish_deferrable_loads()


class TestCalculateNextRecurringDatetimeNonePath:
    """Tests for trip_manager.py lines 251-257: calculate_next_recurring_datetime returns None path."""

    @pytest.mark.asyncio
    async def test_weekly_trip_with_invalid_hora_triggers_none_path(self):
        """Test that a recurring trip with invalid 'hora' format triggers the None path.

        This covers trip_manager.py lines 251-257 where calculate_next_recurring_datetime
        returns None because time_str cannot be parsed.
        """
        # Create mock trip manager
        mock_hass = MagicMock()
        mock_storage = MagicMock()
        mock_storage.async_load = AsyncMock(return_value=None)
        mock_storage.async_save = AsyncMock(return_value=None)

        tm = TripManager(
            hass=mock_hass,
            vehicle_id="test_vehicle",
            entry_id="test_entry",
            presence_config={},
            storage=mock_storage,
        )

        # Mock _get_all_active_trips to return our trip with invalid hora
        with patch.object(
            tm,
            "_get_all_active_trips",
            return_value=[
                {
                    "id": "rec_monday_123",
                    "tipo": "recurring",
                    "dia_semana": "lunes",
                    "hora": "invalid_time",  # Invalid - will cause calculate_next_recurring_datetime to return None
                    "km": 30.0,
                    "kwh": 5.0,
                    "descripcion": "Test trip",
                    "activo": True,
                    "datetime": datetime.now().isoformat(),
                }
            ],
        ):
            # Mock emhass adapter to avoid actual publishing - MUST be AsyncMock!
            mock_adapter = AsyncMock()
            tm.set_emhass_adapter(mock_adapter)

            # This should trigger the None path in publish_deferrable_loads
            # because calculate_next_recurring_datetime("1", "invalid_time", ...) returns None
            await tm.publish_deferrable_loads()

    @pytest.mark.asyncio
    async def test_weekly_trip_with_none_hora_triggers_none_path(self):
        """Test that a recurring trip with None 'hora' triggers the None path.

        This covers trip_manager.py lines 251-257 where calculate_next_recurring_datetime
        returns None because time_str is None.
        """
        # Create mock trip manager
        mock_hass = MagicMock()
        mock_storage = MagicMock()
        mock_storage.async_load = AsyncMock(return_value=None)
        mock_storage.async_save = AsyncMock(return_value=None)

        tm = TripManager(
            hass=mock_hass,
            vehicle_id="test_vehicle",
            entry_id="test_entry",
            presence_config={},
            storage=mock_storage,
        )

        # Mock _get_all_active_trips to return our trip with None hora
        with patch.object(
            tm,
            "_get_all_active_trips",
            return_value=[
                {
                    "id": "rec_monday_456",
                    "tipo": "recurring",
                    "dia_semana": "lunes",
                    "hora": None,  # None - will cause calculate_next_recurring_datetime to return None
                    "km": 30.0,
                    "kwh": 5.0,
                    "descripcion": "Test trip",
                    "activo": True,
                    "datetime": datetime.now().isoformat(),
                }
            ],
        ):
            # Mock emhass adapter to avoid actual publishing - MUST be AsyncMock!
            mock_adapter = AsyncMock()
            tm.set_emhass_adapter(mock_adapter)

            # This should trigger the None path because calculate_next_recurring_datetime("1", None, ...) returns None
            await tm.publish_deferrable_loads()


class TestHourlyRefreshExceptionHandler:
    """Tests for __init__.py lines 72-76: Exception handler in _hourly_refresh_callback."""

    @pytest.mark.asyncio
    async def test_hourly_refresh_callback_exception_is_caught(self):
        """Test that exceptions in _hourly_refresh_callback are caught and logged.

        This covers __init__.py lines 75-76 where the exception handler
        catches exceptions from publish_deferrable_loads().
        """
        from custom_components.ev_trip_planner import (
            _hourly_refresh_callback,
            EVTripRuntimeData,
        )
        from custom_components.ev_trip_planner.trip_manager import TripManager
        from datetime import datetime

        # Create mock trip manager that raises exception
        mock_trip_manager = AsyncMock(spec=TripManager)
        mock_trip_manager.publish_deferrable_loads = AsyncMock(
            side_effect=Exception("Test exception")
        )

        # Create runtime data with the mock trip manager
        runtime_data = EVTripRuntimeData(
            coordinator=None,
            trip_manager=mock_trip_manager,
            emhass_adapter=None,
        )

        # Import logging to capture warning
        import logging

        # Execute the callback
        with patch.object(
            logging.getLogger("custom_components.ev_trip_planner"), "warning"
        ) as mock_warning:
            now = datetime.now()
            await _hourly_refresh_callback(now, runtime_data)

            # Verify the exception was caught and logged
            mock_warning.assert_called_once()
            assert "Hourly profile refresh failed" in str(mock_warning.call_args)
            assert "Test exception" in str(mock_warning.call_args)

    @pytest.mark.asyncio
    async def test_hourly_refresh_callback_handles_none_trip_manager(self):
        """Test that _hourly_refresh_callback handles runtime_data.trip_manager=None.

        This covers __init__.py line 73 where trip_manager is None.
        """
        from custom_components.ev_trip_planner import (
            _hourly_refresh_callback,
            EVTripRuntimeData,
        )
        from datetime import datetime

        # Create runtime data with trip_manager=None
        runtime_data = EVTripRuntimeData(
            coordinator=None,
            trip_manager=None,
            emhass_adapter=None,
        )

        # Execute the callback - should not raise any exception
        now = datetime.now()
        await _hourly_refresh_callback(now, runtime_data)

        # If we reach here without exception, the test passed

    @pytest.mark.asyncio
    async def test_hourly_refresh_callback_success_path(self):
        """Test that _hourly_refresh_callback succeeds when publish_deferrable_loads succeeds.

        This covers the happy path in __init__.py lines 72-74.
        """
        from custom_components.ev_trip_planner import (
            _hourly_refresh_callback,
            EVTripRuntimeData,
        )
        from custom_components.ev_trip_planner.trip_manager import TripManager
        from datetime import datetime

        # Create mock trip manager that succeeds
        mock_trip_manager = AsyncMock(spec=TripManager)
        mock_trip_manager.publish_deferrable_loads = AsyncMock(return_value=None)

        # Create runtime data with the mock trip manager
        runtime_data = EVTripRuntimeData(
            coordinator=None,
            trip_manager=mock_trip_manager,
            emhass_adapter=None,
        )

        # Execute the callback
        now = datetime.now()
        await _hourly_refresh_callback(now, runtime_data)

        # Verify success
        assert mock_trip_manager.publish_deferrable_loads.called
