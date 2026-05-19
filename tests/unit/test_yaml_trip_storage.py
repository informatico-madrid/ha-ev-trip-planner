"""Tests for YamlTripStorage (TripStorageProtocol implementation)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.yaml_trip_storage import YamlTripStorage


class TestYamlTripStorageInit:
    """Tests for YamlTripStorage.__init__() — kill attribute assignment mutants."""

    def test_init_sets_hass_attribute(self, mock_hass):
        """Test __init__ sets self._hass to the provided hass instance."""
        storage = YamlTripStorage(mock_hass, "test_vehicle")
        assert storage._hass is mock_hass

    def test_init_sets_vehicle_id(self, mock_hass):
        """Test __init__ sets self._vehicle_id to the provided vehicle_id."""
        storage = YamlTripStorage(mock_hass, "my_ev")
        assert storage._vehicle_id == "my_ev"

    def test_init_creates_store_with_domain_prefix(self, mock_hass):
        """Test __init__ creates Store with DOMAIN vehicle_id key prefix."""
        with patch(
            "homeassistant.helpers.storage.Store", return_value=MagicMock()
        ) as MockStore:
            YamlTripStorage(mock_hass, "vehicle_42")
            # Verify Store was called with correct key
            call_args = MockStore.call_args
            assert call_args[1]["key"] == f"ev_trip_planner_vehicle_42"

    def test_init_store_version_is_one(self, mock_hass):
        """Test __init__ creates Store with version=1."""
        with patch(
            "homeassistant.helpers.storage.Store", return_value=MagicMock()
        ) as MockStore:
            YamlTripStorage(mock_hass, "vehicle_1")
            call_args = MockStore.call_args
            assert call_args[1]["version"] == 1


class TestYamlTripStorageAsyncLoad:
    """Tests for YamlTripStorage.async_load()."""

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

    @pytest.mark.asyncio
    async def test_async_save_with_empty_input(self, mock_hass):
        """Test async_save handles empty input dict — keys exist as empty defaults."""
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
            # Empty input — all .get() calls return default {}
            await storage.async_save({})

        call_args = mock_store.async_save.call_args[0][0]
        # Mutations to data.get() keys would return {} instead of the actual key
        # This test asserts the keys exist with expected types
        assert call_args["trips"] == {}
        assert call_args["recurring_trips"] == {}
        assert call_args["punctual_trips"] == {}
        assert isinstance(call_args["last_update"], str)

    @pytest.mark.asyncio
    async def test_async_save_exact_key_values(self, mock_hass):
        """Test async_save preserves exact input values in save_data dict."""
        from custom_components.ev_trip_planner.yaml_trip_storage import (
            YamlTripStorage,
        )

        mock_store = MagicMock()
        mock_store.async_save = AsyncMock()

        test_trips = {"t1": {"dest": "beach"}}
        test_recurring = {"r1": {"weekdays": [1, 2]}}
        test_punctual = {"p1": {"time": "08:00"}}

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            storage = YamlTripStorage(mock_hass, "test_vehicle")
            await storage.async_save(
                {
                    "trips": test_trips,
                    "recurring_trips": test_recurring,
                    "punctual_trips": test_punctual,
                }
            )

        call_args = mock_store.async_save.call_args[0][0]
        assert call_args["trips"] is test_trips
        assert call_args["recurring_trips"] is test_recurring
        assert call_args["punctual_trips"] is test_punctual
        assert call_args["last_update"] is not None

    @pytest.mark.asyncio
    async def test_async_save_missing_keys_defaults_empty(self, mock_hass):
        """Test async_save when input is missing trip keys — defaults to empty dict."""
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
            # Input missing all expected keys
            await storage.async_save({"other_key": "value"})

        call_args = mock_store.async_save.call_args[0][0]
        # The .get() calls with missing keys should return empty dicts
        assert call_args["trips"] == {}
        assert call_args["recurring_trips"] == {}
        assert call_args["punctual_trips"] == {}


class TestYamlTripStorageAsyncLoadEdgeCases:
    """Edge-case tests for async_load — kill .get() key mutation survivors."""

    @pytest.mark.asyncio
    async def test_async_load_dict_without_data_key(self, mock_hass):
        """Test async_load when stored_data is a dict but lacks 'data' key."""
        mock_store = MagicMock()
        # Dict with no 'data' key — falls through to line 46
        mock_store.async_load = AsyncMock(
            return_value={"trips": {"x": 1}, "other": 2}
        )

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            storage = YamlTripStorage(mock_hass, "test_vehicle")
            result = await storage.async_load()

        # Should return the flat dict (line 47 path)
        assert result == {"trips": {"x": 1}, "other": 2}

    @pytest.mark.asyncio
    async def test_async_load_returns_exact_stored_data(self, mock_hass):
        """Test async_load returns the exact 'data' value, not a copy."""
        mock_store = MagicMock()
        stored_data = {"data": {"key": "val"}}
        mock_store.async_load = AsyncMock(return_value=stored_data)

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            storage = YamlTripStorage(mock_hass, "test_vehicle")
            result = await storage.async_load()

        # Mutations to .get("data", {}) default value would return None/{} instead
        assert result == {"key": "val"}
        assert result is stored_data["data"]

    @pytest.mark.asyncio
    async def test_async_load_data_key_is_none(self, mock_hass):
        """Test async_load when 'data' key exists but value is None."""
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value={"data": None})

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            storage = YamlTripStorage(mock_hass, "test_vehicle")
            result = await storage.async_load()

        # Line 44: isinstance(None, dict) is False → falls to line 46
        # The value None is returned from .get(), but isinstance check fails
        assert result == None  # noqa: E711

    @pytest.mark.asyncio
    async def test_async_load_data_key_present_but_not_dict(self, mock_hass):
        """Test async_load when 'data' key exists but value is not a dict."""
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value={"data": "not a dict"})

        with patch(
            "homeassistant.helpers.storage.Store",
            return_value=mock_store,
        ):
            storage = YamlTripStorage(mock_hass, "test_vehicle")
            result = await storage.async_load()

        # Line 44: isinstance("not a dict", dict) is False → falls to line 46
        assert result == "not a dict"
