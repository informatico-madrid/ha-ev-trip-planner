"""Tests for YamlTripStorage (TripStorageProtocol implementation)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestYamlTripStorageAsyncLoad:
    """Tests for YamlTripStorage.async_load()."""

    @pytest.fixture
    def mock_hass(self):
        """Mock hass with config."""
        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = Path("/tmp/test_config")
        return hass

    @pytest.mark.asyncio
    async def test_async_load_with_data_wraps_dict(self, mock_hass):
        """Test async_load when Store returns data wrapped in 'data' key."""
        from custom_components.ev_trip_planner.yaml_trip_storage import (
            YamlTripStorage,
        )

        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(
            return_value={
                "data": {
                    "trips": {"trip_1": {"id": "trip_1"}},
                    "recurring_trips": {"rec_lun": {"id": "rec_lun"}},
                    "punctual_trips": {},
                }
            }
        )

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            storage = YamlTripStorage(mock_hass, "test_vehicle")
            result = await storage.async_load()

        assert result == {
            "trips": {"trip_1": {"id": "trip_1"}},
            "recurring_trips": {"rec_lun": {"id": "rec_lun"}},
            "punctual_trips": {},
        }

    @pytest.mark.asyncio
    async def test_async_load_without_data_wraps_dict(self, mock_hass):
        """Test async_load when Store returns None (no data stored)."""
        from custom_components.ev_trip_planner.yaml_trip_storage import (
            YamlTripStorage,
        )

        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value=None)

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            storage = YamlTripStorage(mock_hass, "test_vehicle")
            result = await storage.async_load()

        assert result == {}

    @pytest.mark.asyncio
    async def test_async_load_with_flat_dict(self, mock_hass):
        """Test async_load when Store returns flat dict (no 'data' wrapper)."""
        from custom_components.ev_trip_planner.yaml_trip_storage import (
            YamlTripStorage,
        )

        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(
            return_value={
                "trips": {"trip_1": {"id": "trip_1"}},
                "recurring_trips": {},
                "punctual_trips": {},
            }
        )

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            storage = YamlTripStorage(mock_hass, "test_vehicle")
            result = await storage.async_load()

        assert result == {
            "trips": {"trip_1": {"id": "trip_1"}},
            "recurring_trips": {},
            "punctual_trips": {},
        }

    @pytest.mark.asyncio
    async def test_async_load_coerces_non_dict_to_empty(self, mock_hass):
        """Test async_load coerces non-dict stored_data to {} (protocol compliance)."""
        from custom_components.ev_trip_planner.yaml_trip_storage import (
            YamlTripStorage,
        )

        mock_store = MagicMock()
        # Store returns a string (corrupted data) instead of dict
        mock_store.async_load = AsyncMock(return_value="corrupted string")

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            storage = YamlTripStorage(mock_hass, "test_vehicle")
            result = await storage.async_load()

        assert result == {}


class TestYamlTripStorageAsyncSave:
    """Tests for YamlTripStorage.async_save()."""

    @pytest.fixture
    def mock_hass(self):
        """Mock hass with config."""
        hass = MagicMock()
        hass.config = MagicMock()
        hass.config.config_dir = Path("/tmp/test_config")
        return hass

    @pytest.mark.asyncio
    async def test_async_save_calls_store_with_correct_data(self, mock_hass):
        """Test async_save calls Store.async_save with properly structured data."""
        from custom_components.ev_trip_planner.yaml_trip_storage import (
            YamlTripStorage,
        )

        mock_store = MagicMock()
        mock_store.async_save = AsyncMock()

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            storage = YamlTripStorage(mock_hass, "test_vehicle")
            await storage.async_save(
                {
                    "trips": {"trip_1": {"id": "trip_1"}},
                    "recurring_trips": {"rec_lun": {"id": "rec_lun"}},
                    "punctual_trips": {},
                    "last_update": "2026-04-01T00:00:00",
                }
            )

        mock_store.async_save.assert_called_once()
        call_args = mock_store.async_save.call_args[0][0]
        assert call_args["trips"] == {"trip_1": {"id": "trip_1"}}
        assert call_args["recurring_trips"] == {"rec_lun": {"id": "rec_lun"}}
        assert call_args["punctual_trips"] == {}
        assert "last_update" in call_args

    @pytest.mark.asyncio
    async def test_async_save_includes_timestamp(self, mock_hass):
        """Test async_save includes ISO timestamp in saved data."""
        from custom_components.ev_trip_planner.yaml_trip_storage import (
            YamlTripStorage,
        )

        mock_store = MagicMock()
        mock_store.async_save = AsyncMock()

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            storage = YamlTripStorage(mock_hass, "test_vehicle")
            await storage.async_save(
                {"trips": {}, "recurring_trips": {}, "punctual_trips": {}}
            )

        call_args = mock_store.async_save.call_args[0][0]
        assert "last_update" in call_args
        # Verify it's an ISO format timestamp
        assert "T" in call_args["last_update"]
