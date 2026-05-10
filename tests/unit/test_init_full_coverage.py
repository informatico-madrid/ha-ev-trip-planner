"""Tests for __init__ hourly refresh callback, emhass error handling, and trip_manager error paths."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner import EVTripRuntimeData
from custom_components.ev_trip_planner.__init__ import _hourly_refresh_callback
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter
from custom_components.ev_trip_planner.trip_manager import TripManager
from tests.helpers import TEST_ENTRY_ID, TEST_VEHICLE_ID


class TestHourlyRefreshCallbackCoverage:
    """Tests para cubrir líneas 72-76 en __init__.py: _hourly_refresh_callback."""

    @pytest.mark.asyncio
    async def test_hourly_refresh_callback_with_none_trip_manager(self):
        """Test línea 73: _hourly_refresh_callback maneja runtime_data.trip_manager=None.

        Este test cubre la ruta donde runtime_data.trip_manager es None,
        evitando la llamada a publish_deferrable_loads().
        """
        # Setup: runtime_data con trip_manager=None
        mock_coordinator = MagicMock()
        runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=None,  # trip_manager=None para cubrir línea 73
            emhass_adapter=None,
        )

        # Act: Llamar al callback
        now = datetime.now()
        await _hourly_refresh_callback(now, runtime_data)

        # Assert: No se debe levantar excepción
        # La función debe retornar silenciosamente cuando trip_manager es None

    @pytest.mark.asyncio
    async def test_hourly_refresh_callback_handles_exception(self, hass):
        """Test líneas 75-76: _hourly_refresh_callback captura excepción en publish_deferrable_loads.

        Este test cubre la ruta de manejo de excepciones en el bloque try-except.
        """
        # Setup: runtime_data con trip_manager que lanza excepción
        mock_trip_manager = AsyncMock()
        mock_trip_manager.publish_deferrable_loads = AsyncMock(
            side_effect=Exception("Test error")
        )

        mock_coordinator = MagicMock()
        runtime_data = EVTripRuntimeData(
            coordinator=mock_coordinator,
            trip_manager=mock_trip_manager,
            emhass_adapter=None,
        )

        # Act: Llamar al callback
        now = datetime.now()
        await _hourly_refresh_callback(now, runtime_data)

        # Assert: La excepción debe ser capturada y logueada como warning
        # El logging se verifica indirectamente: si no se levanta excepción, el test pasa


class TestAsyncNotifyErrorNotificationFailure:
    """Tests para cubrir líneas 1136-1140 en emhass_adapter.py.

    Estas líneas están en el bloque except Exception dentro de async_notify_error
    cuando el servicio de notificación falla.
    """

    @pytest.mark.asyncio
    async def test_async_notify_error_handles_notification_service_exception(
        self, hass, mock_store
    ):
        """Test líneas 1136-1140: async_notify_error maneja excepción en servicio de notificación.

        Este test cubre la ruta donde await hass.services.async_call() lanza excepción.
        """
        # Setup: Configurar adapter con notification_service
        config = MagicMock()
        config.data = {
            "vehicle_id": TEST_VEHICLE_ID,
            "notification_service": "notify.test_service",
        }
        config.entry_id = TEST_ENTRY_ID

        adapter = EMHASSAdapter(hass, config)

        # Mock del servicio de notificación para lanzar excepción
        with patch.object(
            hass.services, "async_call", side_effect=Exception("Service unavailable")
        ):
            # Act: Llamar async_notify_error
            result = await adapter.async_notify_error(
                error_type="emhass_unavailable",
                message="Test error message",
                trip_id="test_trip_id",
            )

            # Assert: Debe retornar False cuando falla la notificación
            assert result is False


class TestPublishDeferrableLoadsErrorPaths:
    """Tests para cubrir líneas 211-213 y 258-260 en trip_manager.py.

    Estas líneas están en los bloques except Exception dentro de publish_deferrable_loads
    cuando la rotación de viajes recurrentes falla.
    """

    @pytest.mark.asyncio
    async def test_publish_deferrable_loads_handles_daily_trip_rotation_exception(
        self, hass, mock_store
    ):
        """Test líneas 211-213: publish_deferrable_loads maneja excepción al rotar viaje diario.

        Este test cubre la ruta donde calculate_trip_time o la actualización del datetime
        del viaje diario lanza excepción durante la rotación.
        """
        # Setup: Configurar trip_manager con trips recurrentes que causan error
        mock_storage = MagicMock()
        mock_storage.async_load = AsyncMock(
            return_value={
                "trips": {},
                "recurring_trips": {
                    "rec_daily_test": {
                        "id": "rec_daily_test",
                        "tipo": "recurrente",
                        "dia_semana": "daily",
                        "hora": "invalid_time",  # Hora inválida para causar error
                        "km": 50.0,
                        "kwh": 7.5,
                        "activo": True,
                    },
                },
                "punctual_trips": {},
            }
        )

        mock_trip_manager = TripManager(
            hass=hass,
            vehicle_id=TEST_VEHICLE_ID,
            entry_id=TEST_ENTRY_ID,
            storage=mock_storage,
        )

        # Mock del emhass_adapter para evitar llamadas reales
        mock_emhass_adapter = AsyncMock()
        mock_emhass_adapter.async_publish_all_deferrable_loads = AsyncMock()
        mock_trip_manager._emhass_adapter = mock_emhass_adapter

        # Act: Llamar publish_deferrable_loads - debe manejar la excepción sin propagarla
        await mock_trip_manager.publish_deferrable_loads()

        # Assert: El método debe completar sin propagar la excepción
        # La excepción debe ser capturada y logueada como warning

    @pytest.mark.asyncio
    async def test_publish_deferrable_loads_handles_weekly_trip_rotation_exception(
        self, hass, mock_store
    ):
        """Test líneas 258-260: publish_deferrable_loads maneja excepción al rotar viaje semanal.

        Este test cubre la ruta donde calculate_next_recurring_datetime o la actualización
        del datetime del viaje semanal lanza excepción durante la rotación.
        """
        # Setup: Configurar trip_manager con trips recurrentes que causan error
        mock_storage = MagicMock()
        mock_storage.async_load = AsyncMock(
            return_value={
                "trips": {},
                "recurring_trips": {
                    "rec_weekly_test": {
                        "id": "rec_weekly_test",
                        "tipo": "recurrente",
                        "dia_semana": "invalid_day",  # Día inválido para causar error
                        "hora": "08:00",
                        "km": 50.0,
                        "kwh": 7.5,
                        "activo": True,
                    },
                },
                "punctual_trips": {},
            }
        )

        mock_trip_manager = TripManager(
            hass=hass,
            vehicle_id=TEST_VEHICLE_ID,
            entry_id=TEST_ENTRY_ID,
            storage=mock_storage,
        )

        # Mock del emhass_adapter para evitar llamadas reales
        mock_emhass_adapter = AsyncMock()
        mock_emhass_adapter.async_publish_all_deferrable_loads = AsyncMock()
        mock_trip_manager._emhass_adapter = mock_emhass_adapter

        # Act: Llamar publish_deferrable_loads - debe manejar la excepción sin propagarla
        await mock_trip_manager.publish_deferrable_loads()

        # Assert: El método debe completar sin propagar la excepción
        # La excepción debe ser capturada y logueada como warning
