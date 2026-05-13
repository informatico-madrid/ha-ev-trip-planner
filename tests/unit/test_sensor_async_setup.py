"""Tests for sensor/_async_setup.py uncovered code paths.

Covers _format_window_time, async_setup_entry error paths,
async_create_trip_sensor, async_update_trip_sensor,
async_remove_trip_sensor, async_create_trip_emhass_sensor,
async_remove_trip_emhass_sensor.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.sensor._async_setup import (
    _format_window_time,
    async_create_trip_emhass_sensor,
    async_create_trip_sensor,
    async_remove_trip_emhass_sensor,
    async_remove_trip_sensor,
    async_update_trip_sensor,
)


class TestFormatWindowTime:
    """Test _format_window_time edge cases."""

    def test_none_input(self):
        """None input returns None (line 57)."""
        assert _format_window_time(None) is None

    def test_datetime_object(self):
        """Datetime object returns HH:MM (line 60-66)."""
        dt = datetime(2026, 5, 14, 9, 30, 0, tzinfo=timezone.utc)
        assert _format_window_time(dt) == "09:30"

    def test_iso_string(self):
        """ISO string returns HH:MM (line 62-63)."""
        assert _format_window_time("2026-05-14T14:45:00+00:00") == "14:45"

    def test_wrong_type(self):
        """Wrong type (int) returns None (line 64-65)."""
        assert _format_window_time(42) is None

    def test_exception_on_parse(self):
        """Exception on fromisoformat returns None (line 67-68)."""
        assert _format_window_time("not-a-date") is None


class TestAsyncSetupEntryError:
    """Test async_setup_entry error paths."""

    @pytest.mark.asyncio
    async def test_no_trip_manager(self, caplog):
        """No trip_manager returns False (lines 83-89)."""
        from custom_components.ev_trip_planner.sensor import async_setup_entry

        hass = MagicMock()
        entry = MagicMock()
        entry.runtime_data.trip_manager = None
        entry.runtime_data.coordinator = MagicMock()

        with caplog.at_level(
            logging.ERROR,
            logger="custom_components.ev_trip_planner.sensor._async_setup",
        ):
            result = await async_setup_entry(hass, entry, lambda x: None)
            assert result is False
            assert any("No trip_manager found" in r.message for r in caplog.records)


class TestAsyncCreateTripSensor:
    """Test async_create_trip_sensor error paths."""

    @pytest.mark.asyncio
    async def test_no_entry(self, caplog):
        """No entry found returns False (line 237)."""
        hass = MagicMock()
        hass.config_entries.async_get_entry.return_value = None

        result = await async_create_trip_sensor(hass, "nonexistent", {"id": "t1"})
        assert result is False

    @pytest.mark.asyncio
    async def test_no_trip_manager(self, caplog):
        """No trip_manager returns False (lines 245-247)."""
        hass = MagicMock()
        entry = MagicMock()
        entry.runtime_data.trip_manager = None
        hass.config_entries.async_get_entry.return_value = entry

        result = await async_create_trip_sensor(
            hass, "test_entry", {"id": "t1", "tipo": "recurrente"}
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_no_coordinator(self, caplog):
        """No coordinator returns False (lines 249-251)."""
        hass = MagicMock()
        entry = MagicMock()
        entry.runtime_data.trip_manager = MagicMock()
        entry.runtime_data.coordinator = None
        hass.config_entries.async_get_entry.return_value = entry

        result = await async_create_trip_sensor(
            hass, "test_entry", {"id": "t1", "tipo": "recurrente"}
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_no_async_add_entities(self, caplog):
        """No async_add_entities returns False (lines 253-258)."""
        hass = MagicMock()
        entry = MagicMock()
        entry.runtime_data.trip_manager = MagicMock()
        entry.runtime_data.coordinator = MagicMock()
        entry.runtime_data.sensor_async_add_entities = None
        hass.config_entries.async_get_entry.return_value = entry

        result = await async_create_trip_sensor(
            hass, "test_entry", {"id": "t1", "tipo": "recurrente"}
        )
        assert result is False


class TestAsyncUpdateTripSensor:
    """Test async_update_trip_sensor paths."""

    @pytest.mark.asyncio
    async def test_no_entry(self, caplog):
        """No entry returns False (line 302)."""
        hass = MagicMock()
        hass.config_entries.async_get_entry.return_value = None

        result = await async_update_trip_sensor(hass, "nonexistent", {"id": "t1"})
        assert result is False

    @pytest.mark.asyncio
    async def test_no_trip_manager(self, caplog):
        """No trip_manager returns False (lines 308-310)."""
        hass = MagicMock()
        entry = MagicMock()
        entry.runtime_data.trip_manager = None
        hass.config_entries.async_get_entry.return_value = entry

        result = await async_update_trip_sensor(hass, "test_entry", {"id": "t1"})
        assert result is False

    @pytest.mark.asyncio
    async def test_entity_not_found_creates_sensor(self, monkeypatch):
        """Entity not found in registry -> creates new sensor."""
        import custom_components.ev_trip_planner.sensor._async_setup as setup_mod

        hass = MagicMock()
        entry = MagicMock()
        entry.runtime_data.trip_manager = MagicMock()
        entry.runtime_data.sensor_async_add_entities = MagicMock(return_value=None)
        entry.runtime_data.coordinator = MagicMock()
        entry.entry_id = "test_entry"
        hass.config_entries.async_get_entry.return_value = entry

        # Patch at source module so production function's __globals__ sees it
        monkeypatch.setattr(
            "custom_components.ev_trip_planner.sensor._async_setup.async_entries_for_config_entry",
            MagicMock(return_value=[]),
        )
        monkeypatch.setattr(
            setup_mod, "async_create_trip_sensor", AsyncMock(return_value=True)
        )

        result = await async_update_trip_sensor(
            hass, "test_entry", {"id": "new_trip", "tipo": "recurrente"}
        )
        assert result is True
        setup_mod.async_create_trip_sensor.assert_called_once()

    @pytest.mark.asyncio
    async def test_entity_found_triggers_coordinator_refresh(self, monkeypatch):
        """Entity found -> coordinator.async_request_refresh called."""
        hass = MagicMock()
        entry = MagicMock()
        entry.runtime_data.trip_manager = MagicMock()
        entry.runtime_data.coordinator = AsyncMock()
        entry.entry_id = "test_entry"
        hass.config_entries.async_get_entry.return_value = entry

        mock_reg_entry = MagicMock()
        mock_reg_entry.unique_id = "trip_new_trip"
        mock_reg_entry.entity_id = "sensor.trip_new_trip"
        hass.states.get.return_value = MagicMock()

        # Patch at source module so production function's __globals__ sees it
        monkeypatch.setattr(
            "custom_components.ev_trip_planner.sensor._async_setup.async_entries_for_config_entry",
            MagicMock(return_value=[mock_reg_entry]),
        )
        result = await async_update_trip_sensor(
            hass, "test_entry", {"id": "new_trip", "tipo": "recurrente"}
        )
        assert result is True
        entry.runtime_data.coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_coordinator_no_refresh(self, monkeypatch):
        """Coordinator not available -> no refresh, still returns True."""
        hass = MagicMock()
        entry = MagicMock()
        entry.runtime_data.trip_manager = MagicMock()
        entry.runtime_data.coordinator = None
        entry.entry_id = "test_entry"
        hass.config_entries.async_get_entry.return_value = entry

        mock_reg_entry = MagicMock()
        mock_reg_entry.unique_id = "trip_new_trip"
        mock_reg_entry.entity_id = "sensor.trip_new_trip"
        hass.states.get.return_value = None

        # Patch at source module so production function's __globals__ sees it
        monkeypatch.setattr(
            "custom_components.ev_trip_planner.sensor._async_setup.async_entries_for_config_entry",
            MagicMock(return_value=[mock_reg_entry]),
        )
        result = await async_update_trip_sensor(
            hass, "test_entry", {"id": "new_trip", "tipo": "recurrente"}
        )
        assert result is True


class TestAsyncRemoveTripSensor:
    """Test async_remove_trip_sensor paths."""

    @pytest.mark.asyncio
    async def test_entity_found_removed(self, monkeypatch):
        """Entity found -> removed from registry, returns True."""
        hass = MagicMock()
        mock_reg_entry = MagicMock()
        mock_reg_entry.unique_id = "trip_target_trip"
        mock_reg_entry.entity_id = "sensor.trip_target_trip"

        mock_registry = MagicMock()
        mock_registry.async_remove = MagicMock()
        hass.entity_registry = mock_registry

        # Patch at source module so production function's __globals__ sees it
        monkeypatch.setattr(
            "custom_components.ev_trip_planner.sensor._async_setup.async_entries_for_config_entry",
            MagicMock(return_value=[mock_reg_entry]),
        )
        result = await async_remove_trip_sensor(hass, "test_entry", "target_trip")
        assert result is True
        mock_registry.async_remove.assert_called_once_with("sensor.trip_target_trip")

    @pytest.mark.asyncio
    async def test_entity_not_found(self, monkeypatch):
        """Entity not found -> returns False."""
        hass = MagicMock()
        mock_registry = MagicMock()
        hass.entity_registry = mock_registry

        # Patch at source module so production function's __globals__ sees it
        monkeypatch.setattr(
            "custom_components.ev_trip_planner.sensor._async_setup.async_entries_for_config_entry",
            MagicMock(return_value=[]),
        )
        result = await async_remove_trip_sensor(hass, "test_entry", "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_unique_id_not_string_skipped(self, monkeypatch):
        """Non-string unique_id -> entry skipped, returns False."""
        hass = MagicMock()
        mock_reg_entry = MagicMock()
        mock_reg_entry.unique_id = 123  # Non-string
        mock_reg_entry.entity_id = "sensor.trip_target_trip"

        mock_registry = MagicMock()
        mock_registry.async_remove = MagicMock()
        hass.entity_registry = mock_registry

        # Patch at source module so production function's __globals__ sees it
        monkeypatch.setattr(
            "custom_components.ev_trip_planner.sensor._async_setup.async_entries_for_config_entry",
            MagicMock(return_value=[mock_reg_entry]),
        )
        result = await async_remove_trip_sensor(hass, "test_entry", "target_trip")
        assert result is False


class TestAsyncCreateTripEmhassSensor:
    """Test async_create_trip_emhass_sensor error paths."""

    @pytest.mark.asyncio
    async def test_no_entry(self, caplog):
        """No entry found returns False (lines 475-477)."""
        hass = MagicMock()
        hass.config_entries.async_get_entry.return_value = None

        result = await async_create_trip_emhass_sensor(
            hass, "nonexistent", MagicMock(), "v1", "t1"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_no_async_add_entities(self, caplog):
        """No async_add_entities returns False (lines 482-487)."""
        hass = MagicMock()
        entry = MagicMock()
        entry.runtime_data.sensor_async_add_entities = None
        hass.config_entries.async_get_entry.return_value = entry

        result = await async_create_trip_emhass_sensor(
            hass, "test_entry", MagicMock(), "v1", "t1"
        )
        assert result is False


class TestAsyncRemoveTripEmhassSensor:
    """Test async_remove_trip_emhass_sensor paths."""

    @pytest.mark.asyncio
    async def test_entity_found_removed(self, monkeypatch):
        """Matching EMHASS entity -> removed, returns True (lines 422-439)."""
        hass = MagicMock()
        mock_reg_entry = MagicMock()
        mock_reg_entry.unique_id = "emhass_trip_v1_t1"
        mock_reg_entry.entity_id = "sensor.emhass_trip_v1_t1"

        mock_registry = MagicMock()
        mock_registry.async_remove = MagicMock()
        hass.entity_registry = mock_registry

        # Patch at source module so production function's __globals__ sees it
        monkeypatch.setattr(
            "custom_components.ev_trip_planner.sensor._async_setup.async_entries_for_config_entry",
            MagicMock(return_value=[mock_reg_entry]),
        )
        result = await async_remove_trip_emhass_sensor(
            hass, "test_entry", "v1", "t1"
        )
        assert result is True
        mock_registry.async_remove.assert_called_once_with(
            "sensor.emhass_trip_v1_t1"
        )

    @pytest.mark.asyncio
    async def test_entity_not_found_no_match(self, monkeypatch):
        """No matching EMHASS entity -> returns False."""
        hass = MagicMock()
        mock_reg_entry = MagicMock()
        mock_reg_entry.unique_id = "trip_v1_t1"  # Not emhass
        mock_reg_entry.entity_id = "sensor.trip_v1_t1"

        mock_registry = MagicMock()
        hass.entity_registry = mock_registry

        # Patch at source module so production function's __globals__ sees it
        monkeypatch.setattr(
            "custom_components.ev_trip_planner.sensor._async_setup.async_entries_for_config_entry",
            MagicMock(return_value=[mock_reg_entry]),
        )
        result = await async_remove_trip_emhass_sensor(
            hass, "test_entry", "v1", "t1"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_empty_registry(self, monkeypatch):
        """Empty registry -> returns False."""
        hass = MagicMock()
        mock_registry = MagicMock()
        hass.entity_registry = mock_registry

        # Patch at source module so production function's __globals__ sees it
        monkeypatch.setattr(
            "custom_components.ev_trip_planner.sensor._async_setup.async_entries_for_config_entry",
            MagicMock(return_value=[]),
        )
        result = await async_remove_trip_emhass_sensor(
            hass, "test_entry", "v1", "t1"
        )
        assert result is False
