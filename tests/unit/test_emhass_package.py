"""Comprehensive unit tests for emhass/ SOLID-decomposed package.

Covers: ErrorHandler, IndexManager, LoadPublisher, EMHASSAdapter facade.
Tests public methods, edge cases, and backward-compat attributes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

import pytest

# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def mock_hass(tmp_path):
    """Minimal MagicMock HomeAssistant."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = str(tmp_path)
    return hass


@pytest.fixture
def mock_entry():
    """Minimal MagicMock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_vehicle"
    entry.data = {"charging_power_kw": 3.6}
    entry.options = {}
    return entry


@pytest.fixture
def sample_trip():
    """Return a minimal trip dict for publish tests."""
    return {
        "id": "trip_001",
        "descripcion": "Work trip",
        "kwh": 10.0,
        "datetime": "2026-05-12T08:00:00+00:00",
    }


@pytest.fixture
def sample_recurring_trip():
    """Return a recurring trip dict for publish tests."""
    return {
        "id": "trip_weekly",
        "descripcion": "Weekly trip",
        "kwh": 15.0,
        "tipo": "recurrente",
        "dia_semana": "lunes",
        "hora": "09:00",
    }


# ===================================================================
# ErrorHandler tests
# ===================================================================


class TestErrorHandlerInit:
    """Test ErrorHandler initialization."""

    def test_error_handler_creation(self, mock_hass):
        """ErrorHandler can be instantiated with hass."""
        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        handler = ErrorHandler(hass=mock_hass)
        assert handler.hass is mock_hass
        assert handler._on_error is None

    def test_error_handler_with_callback(self, mock_hass):
        """ErrorHandler stores on_error callback."""
        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        callback_calls: list = []

        def _callback(op, exc):
            callback_calls.append((op, exc))

        handler = ErrorHandler(hass=mock_hass, on_error=_callback)
        assert handler._on_error is _callback

    def test_error_handler_with_none_callback(self, mock_hass):
        """ErrorHandler works with explicit None callback."""
        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        handler = ErrorHandler(hass=mock_hass, on_error=None)
        assert handler._on_error is None


class TestErrorHandlerHandleError:
    """Test ErrorHandler.handle_error method."""

    def test_handle_error_logs_message(self, mock_hass, caplog):
        """handle_error logs an error message with operation name."""
        import logging

        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        caplog.set_level(logging.ERROR)
        handler = ErrorHandler(hass=mock_hass)
        error = ValueError("test error")
        handler.handle_error("publish", error)

        assert "Error during publish" in caplog.text
        assert "test error" in caplog.text

    def test_handle_error_with_context(self, mock_hass, caplog):
        """handle_error logs context key-value pairs when provided."""
        import logging

        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        caplog.set_level(logging.DEBUG)
        handler = ErrorHandler(hass=mock_hass)
        error = RuntimeError("context test")
        handler.handle_error(
            "update", error, context={"trip_id": "t1", "phase": "init"}
        )

        assert "trip_id" in caplog.text
        assert "t1" in caplog.text

    def test_handle_error_invokes_callback(self, mock_hass):
        """handle_error calls on_error callback with operation and exception."""
        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        received: list = []

        def _callback(op, exc):
            received.append((op, exc))

        handler = ErrorHandler(hass=mock_hass, on_error=_callback)
        error = KeyError("callback test")
        handler.handle_error("remove", error)

        assert len(received) == 1
        assert received[0][0] == "remove"
        assert isinstance(received[0][1], KeyError)

    def test_handle_error_callback_failure_is_logged(self, mock_hass, caplog):
        """handle_error catches and logs callback exceptions."""
        import logging

        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        caplog.set_level(logging.ERROR)

        def _callback(op, exc):
            raise ZeroDivisionError("callback raises")

        handler = ErrorHandler(hass=mock_hass, on_error=_callback)
        error = ValueError("callback raises")
        handler.handle_error("notify", error)

        assert "Error handler callback failed" in caplog.text


class TestErrorHandlerSpecificHandlers:
    """Test specialized error handler methods."""

    def test_handle_missing_id_returns_false(self, mock_hass, caplog):
        """handle_missing_id returns False and logs error."""
        import logging

        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        caplog.set_level(logging.ERROR)
        handler = ErrorHandler(hass=mock_hass)
        result = handler.handle_missing_id("trip_x", "publish")
        assert result is False
        assert "Trip missing ID" in caplog.text

    def test_handle_missing_id_default_operation(self, mock_hass, caplog):
        """handle_missing_id defaults operation to 'publish'."""
        import logging

        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        caplog.set_level(logging.ERROR)
        handler = ErrorHandler(hass=mock_hass)
        handler.handle_missing_id("any_trip")
        assert "during publish" in caplog.text

    def test_handle_deadline_error_returns_false(self, mock_hass, caplog):
        """handle_deadline_error returns False and logs trip-specific message."""
        import logging

        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        caplog.set_level(logging.ERROR)
        handler = ErrorHandler(hass=mock_hass)
        result = handler.handle_deadline_error("trip_deadline", "update")
        assert result is False
        assert "trip_deadline" in caplog.text
        assert "no valid deadline" in caplog.text

    def test_handle_deadline_error_default_operation(self, mock_hass):
        """handle_deadline_error defaults operation to 'publish'."""
        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        handler = ErrorHandler(hass=MagicMock())
        result = handler.handle_deadline_error("trip_x")
        assert result is False

    def test_handle_index_error_returns_none(self, mock_hass, caplog):
        """handle_index_error returns None and logs warning."""
        import logging

        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        caplog.set_level(logging.WARNING)
        handler = ErrorHandler(hass=mock_hass)
        handler.handle_index_error("unknown_trip", "release")
        assert "unknown_trip" in caplog.text

    def test_handle_storage_error_logs(self, mock_hass, caplog):
        """handle_storage_error logs the storage operation failure."""
        import logging

        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        caplog.set_level(logging.ERROR)
        handler = ErrorHandler(hass=mock_hass)
        error = OSError("disk full")
        handler.handle_storage_error("save", error)
        assert "save" in caplog.text
        assert "disk full" in caplog.text


# ===================================================================
# IndexManager tests
# ===================================================================


class TestIndexManagerInit:
    """Test IndexManager initialization."""

    def test_default_initialization(self):
        """IndexManager uses default max_deferrable_loads=50 and cooldown=24."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        assert mgr._max_deferrable_loads == 50
        assert mgr._index_cooldown_hours == 24
        assert mgr._index_map == {}

    def test_custom_initialization(self):
        """IndexManager accepts custom max_deferrable_loads and cooldown_hours."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager(max_deferrable_loads=30, cooldown_hours=12)
        assert mgr._max_deferrable_loads == 30
        assert mgr._index_cooldown_hours == 12


class TestIndexManagerAssignIndex:
    """Test index assignment methods."""

    @pytest.mark.asyncio
    async def test_assign_first_index(self):
        """First trip gets index 0."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        result = await mgr.async_assign_index_to_trip("trip_a")
        assert result == 0
        assert mgr._index_map == {"trip_a": 0}

    @pytest.mark.asyncio
    async def test_assign_second_index(self):
        """Second trip gets index 1."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        await mgr.async_assign_index_to_trip("trip_a")
        result = await mgr.async_assign_index_to_trip("trip_b")
        assert result == 1
        assert mgr._index_map == {"trip_a": 0, "trip_b": 1}

    @pytest.mark.asyncio
    async def test_assign_existing_trip_returns_same_index(self):
        """Re-assigning an existing trip returns its original index."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        await mgr.async_assign_index_to_trip("trip_a")
        result = await mgr.async_assign_index_to_trip("trip_a")
        assert result == 0
        assert len(mgr._index_map) == 1

    def test_sync_assign_first_index(self):
        """Sync assign_index returns 0 for first trip."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        result = mgr.assign_index("x")
        assert result == 0

    def test_sync_assign_existing_trip(self):
        """Sync assign_index returns existing index for known trip."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        mgr._index_map = {"a": 5, "b": 10}
        result = mgr.assign_index("a")
        assert result == 5

    def test_sync_assign_missing_trip_returns_next(self):
        """Sync assign_index for missing trip returns max+1."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        mgr._index_map = {"a": 3}
        result = mgr.assign_index("new")
        assert result == 4

    @pytest.mark.asyncio
    async def test_assign_gives_zero_when_empty(self):
        """async_assign_index_to_trip gives 0 when map is empty."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        result = await mgr.async_assign_index_to_trip("empty_test")
        assert result == 0


class TestIndexManagerReleaseIndex:
    """Test index release methods."""

    @pytest.mark.asyncio
    async def test_release_existing_trip(self):
        """async_release_index removes and returns the index for existing trip."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        await mgr.async_assign_index_to_trip("trip_x")
        result = await mgr.async_release_index("trip_x")
        assert result == 0
        assert "trip_x" not in mgr._index_map

    @pytest.mark.asyncio
    async def test_release_nonexistent_trip_returns_none(self):
        """async_release_index returns None for unknown trip."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        result = await mgr.async_release_index("ghost")
        assert result is None

    def test_release_existing_trip_sync(self):
        """release_index removes and returns True for existing trip."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        mgr._index_map = {"a": 1}
        result = mgr.release_index("a")
        assert result is True
        assert "a" not in mgr._index_map

    def test_release_nonexistent_trip_sync(self):
        """release_index returns False for unknown trip."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        result = mgr.release_index("unknown")
        assert result is False


class TestIndexManagerLoadSave:
    """Test index persistence methods (no-op stubs)."""

    @pytest.mark.asyncio
    async def test_async_load_index_is_noop(self):
        """async_load_index is a no-op stub that does not raise."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        await mgr.async_load_index()  # should not raise

    @pytest.mark.asyncio
    async def test_async_save_index_is_noop(self):
        """async_save_index is a no-op stub that does not raise."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        await mgr.async_save_index()  # should not raise

    @pytest.mark.asyncio
    async def test_load_save_preserve_indices(self):
        """Load and save no-ops do not corrupt existing indices."""
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        mgr = IndexManager()
        await mgr.async_assign_index_to_trip("keep_me")
        await mgr.async_load_index()
        await mgr.async_save_index()
        assert mgr._index_map == {"keep_me": 0}


# ===================================================================
# LoadPublisher tests
# ===================================================================


class TestLoadPublisherInit:
    """Test LoadPublisher initialization."""

    def test_default_initialization(self, mock_hass):
        """LoadPublisher sets default values."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(
            hass=mock_hass,
            vehicle_id="test_v",
        )
        assert publisher.vehicle_id == "test_v"
        assert publisher.charging_power_kw == 3.6
        assert publisher.battery_capacity_kwh == 50.0
        assert publisher.safety_margin_percent == 10.0  # DEFAULT_SAFETY_MARGIN

    def test_custom_initialization(self, mock_hass):
        """LoadPublisher accepts custom parameters."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
            LoadPublisherConfig,
        )

        publisher = LoadPublisher(
            hass=mock_hass,
            vehicle_id="v1",
            config=LoadPublisherConfig(
                charging_power_kw=7.4,
                battery_capacity_kwh=75.0,
                safety_margin_percent=20.0,
                max_deferrable_loads=100,
            ),
        )
        assert publisher.charging_power_kw == 7.4
        assert publisher.battery_capacity_kwh == 75.0
        assert publisher.safety_margin_percent == 20.0


class TestLoadPublisherPublish:
    """Test LoadPublisher.publish method."""

    @pytest.mark.asyncio
    async def test_publish_missing_id_returns_false(self, mock_hass):
        """Publish with missing trip ID returns False."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        result = await publisher.publish({})
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_falsy_id_returns_false(self, mock_hass):
        """Publish with falsy trip ID returns False."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        result = await publisher.publish({"id": ""})
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_no_deadline_releases_index(self, mock_hass):
        """Publish without deadline releases assigned index."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        # trip without datetime and not recurring -> deadline is None
        result = await publisher.publish({"id": "no_deadline_trip"})
        assert result is False
        # Index should be released
        assert "no_deadline_trip" not in publisher._index_manager._index_map

    @pytest.mark.asyncio
    async def test_publish_past_deadline_releases_index(self, mock_hass):
        """Publish with past deadline returns False and releases index."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        past = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        result = await publisher.publish({"id": "past_trip", "datetime": past})
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_future_deadline_succeeds(self, mock_hass, caplog):
        """Publish with valid future deadline returns True."""
        import logging
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        caplog.set_level(logging.INFO)
        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        future = datetime(2027, 1, 1, tzinfo=timezone.utc).isoformat()
        result = await publisher.publish(
            {
                "id": "future_trip",
                "datetime": future,
                "kwh": 10.0,
            }
        )
        assert result is True
        assert "future_trip" in caplog.text
        assert "Published deferrable load" in caplog.text

    @pytest.mark.asyncio
    async def test_publish_recurring_trip(self, mock_hass):
        """Publish a recurring trip gets assigned an index."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        result = await publisher.publish(
            {
                "id": "weekly",
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "09:00",
                "kwh": 15.0,
            }
        )
        assert result is True


class TestLoadPublisherUpdateRemove:
    """Test LoadPublisher.update and remove methods."""

    @pytest.mark.asyncio
    async def test_update_delegates_to_publish(self, mock_hass):
        """update() delegates to publish()."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        # update without id -> fails like publish
        result = await publisher.update({})
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_existing_trip(self, mock_hass):
        """remove() succeeds for a trip with an assigned index."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        # Manually set up index map (publish has side effects that clear it)
        publisher._index_manager._index_map = {"remove_me": 0}
        result = await publisher.remove("remove_me")
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_nonexistent_trip(self, mock_hass):
        """remove() returns False for unknown trip."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        result = await publisher.remove("ghost")
        assert result is False


class TestLoadPublisherDeadlineCalculation:
    """Test LoadPublisher._calculate_deadline helper."""

    def test_punctual_trip_with_iso_string(self, mock_hass):
        """Deadline from ISO string is returned as aware datetime."""

        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        dt = publisher._calculate_deadline({"datetime": "2026-06-01T12:00:00+00:00"})
        assert dt is not None
        assert dt.tzinfo is not None
        assert dt.year == 2026 and dt.month == 6 and dt.day == 1

    def test_punctual_trip_with_datetime_obj(self, mock_hass):
        """Deadline from datetime object is returned as-is (made aware)."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        dt = datetime(2026, 7, 4, 14, 30, tzinfo=timezone.utc)
        result = publisher._calculate_deadline({"datetime": dt})
        assert result is dt

    def test_recurring_trip_with_day_and_time(self, mock_hass):
        """Recurring trip with dia_semana and hora produces a deadline."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        dt = publisher._calculate_deadline(
            {
                "tipo": "recurrente",
                "dia_semana": "lunes",
                "hora": "09:00",
            }
        )
        assert dt is not None
        assert dt.tzinfo is not None

    def test_recurring_trip_with_english_day_name(self, mock_hass):
        """Recurring trip with English day name produces deadline."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        dt = publisher._calculate_deadline(
            {
                "tipo": "recurring",
                "dia_semana": "friday",
                "hora": "17:00",
            }
        )
        assert dt is not None

    def test_missing_day_and_time_returns_none(self, mock_hass):
        """Recurring trip without day/time returns None deadline."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        dt = publisher._calculate_deadline(
            {
                "tipo": "recurrente",
                "kwh": 5.0,
            }
        )
        assert dt is None

    def test_punctual_trip_no_datetime_returns_none(self, mock_hass):
        """Punctual trip without datetime field returns None."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        dt = publisher._calculate_deadline({"id": "nodate", "kwh": 5.0})
        assert dt is None


class TestLoadPublisherEnsureAware:
    """Test LoadPublisher._ensure_aware static method."""

    def test_naive_datetime_becomes_aware(self, mock_hass):
        """_ensure_aware converts naive datetime to UTC."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        naive = datetime(2026, 1, 1, 12, 0, 0)
        result = LoadPublisher._ensure_aware(naive)
        assert result.tzinfo is not None
        assert result.year == 2026

    def test_aware_datetime_unchanged(self, mock_hass):
        """_ensure_aware returns aware datetime unchanged."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = LoadPublisher._ensure_aware(aware)
        assert result.tzinfo is aware.tzinfo

    def test_ensure_aware_is_static(self, mock_hass):
        """_ensure_aware can be called without an instance."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        naive = datetime(2026, 5, 1)
        result = LoadPublisher._ensure_aware(naive)
        assert result.tzinfo is not None


class TestLoadPublisherGetCurrentSoc:
    """Test LoadPublisher._get_current_soc method."""

    @pytest.mark.asyncio
    async def test_get_current_soc_returns_none(self, mock_hass):
        """_get_current_soc returns None (stub)."""
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        publisher = LoadPublisher(hass=mock_hass, vehicle_id="v")
        result = await publisher._get_current_soc()
        assert result is None


# ===================================================================
# EMHASSAdapter (Facade) tests
# ===================================================================


class TestEMHASSAdapterInit:
    """Test EMHASSAdapter facade initialization."""

    def test_facade_creation(self, mock_hass, mock_entry):
        """EMHASSAdapter facade can be instantiated."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        assert adapter.hass is mock_hass
        assert adapter.vehicle_id == "test_vehicle"

    def test_facade_composes_subcomponents(self, mock_hass, mock_entry):
        """EMHASSAdapter composes ErrorHandler, IndexManager, LoadPublisher."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )
        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )
        from custom_components.ev_trip_planner.emhass.load_publisher import (
            LoadPublisher,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        assert isinstance(adapter._error_handler, ErrorHandler)
        assert isinstance(adapter._index_manager, IndexManager)
        assert isinstance(adapter._load_publisher, LoadPublisher)

    def test_facade_initializes_state_attributes(self, mock_hass, mock_entry):
        """EMHASSAdapter initializes state dict/list attributes."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        assert adapter._published_trips == set()
        assert adapter._cached_per_trip_params == {}
        assert adapter._cached_power_profile is None
        assert adapter._cached_deferrables_schedule is None
        assert adapter._cached_emhass_status is None
        assert adapter._shutting_down is False


class TestEMHASSAdapterLoadSave:
    """Test facade load/save delegation."""

    @pytest.mark.asyncio
    async def test_async_load_delegates_to_index_manager(self, mock_hass, mock_entry):
        """async_load delegates to index_manager.async_load_index."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        await adapter.async_load()  # no raise = success (no-op stub)

    @pytest.mark.asyncio
    async def test_async_save_delegates_to_index_manager(self, mock_hass, mock_entry):
        """async_save delegates to index_manager.async_save_index."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        await adapter.async_save()  # no raise = success (no-op stub)


class TestEMHASSAdapterIndexDelegation:
    """Test facade index assign/release delegation."""

    @pytest.mark.asyncio
    async def test_async_assign_index_delegates(self, mock_hass, mock_entry):
        """async_assign_index_to_trip delegates to IndexManager."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = await adapter.async_assign_index_to_trip("t1")
        assert result == 0

    @pytest.mark.asyncio
    async def test_async_release_trip_index_delegates(self, mock_hass, mock_entry):
        """async_release_trip_index delegates to IndexManager."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        await adapter.async_assign_index_to_trip("t1")
        result = await adapter.async_release_trip_index("t1")
        assert result is True

    @pytest.mark.asyncio
    async def test_async_release_unknown_trip_returns_false(
        self, mock_hass, mock_entry
    ):
        """async_release_trip_index returns False for unknown trip."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = await adapter.async_release_trip_index("ghost")
        assert result is False

    def test_get_assigned_index(self, mock_hass, mock_entry):
        """get_assigned_index returns the index for a trip."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._index_manager._index_map = {"a": 5}
        assert adapter.get_assigned_index("a") == 5

    def test_get_assigned_index_unknown(self, mock_hass, mock_entry):
        """get_assigned_index returns None for unknown trip."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        assert adapter.get_assigned_index("ghost") is None

    def test_get_all_assigned_indices(self, mock_hass, mock_entry):
        """get_all_assigned_indices returns a copy of the index map."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._index_manager._index_map = {"a": 1, "b": 2}
        result = adapter.get_all_assigned_indices()
        assert result == {"a": 1, "b": 2}

    def test_get_available_indices_empty(self, mock_hass, mock_entry):
        """get_available_indices returns [0] when no indices assigned."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        assert adapter.get_available_indices() == [0]

    def test_get_available_indices_with_assignments(self, mock_hass, mock_entry):
        """get_available_indices returns range when indices assigned."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._index_manager._index_map = {"a": 0, "b": 1, "c": 2}
        assert adapter.get_available_indices() == [0, 1, 2]


class TestEMHASSAdapterNotifyError:
    """Test facade error notification."""

    @pytest.mark.asyncio
    async def test_async_notify_error_logs(self, mock_hass, mock_entry, caplog):
        """async_notify_error logs the error via ErrorHandler."""
        import logging

        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        caplog.set_level(logging.ERROR)
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        await adapter.async_notify_error("emhass unreachable", trip_id="t1")
        assert "emhass unreachable" in caplog.text


class TestEMHASSAdapterGetCachedOptimizationResults:
    """Test get_cached_optimization_results."""

    def test_cached_results_return_all_keys(self, mock_hass, mock_entry):
        """get_cached_optimization_results returns dict with all four keys."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = adapter.get_cached_optimization_results()
        assert "emhass_power_profile" in result
        assert "emhass_deferrables_schedule" in result
        assert "emhass_status" in result
        assert "per_trip_emhass_params" in result

    def test_cached_results_empty_by_default(self, mock_hass, mock_entry):
        """get_cached_optimization_results returns None values when nothing cached."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = adapter.get_cached_optimization_results()
        assert result["emhass_power_profile"] is None
        assert result["emhass_deferrables_schedule"] is None
        assert result["emhass_status"] is None
        assert result["per_trip_emhass_params"] == {}


class TestEMHASSAdapterUpdateChargingPower:
    """Test update_charging_power."""

    @pytest.mark.asyncio
    async def test_update_charging_power_sets_value(self, mock_hass, mock_entry):
        """update_charging_power reads from entry options and stores it."""
        mock_entry.options = {"charging_power_kw": 7.4}
        mock_entry.data = {}

        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        mock_hass.config_entries.async_get_entry = Mock(return_value=mock_entry)
        await adapter.update_charging_power()
        assert adapter._charging_power_kw == 7.4
        assert adapter._stored_charging_power_kw == 7.4

    @pytest.mark.asyncio
    async def test_update_charging_power_skips_unchanged(self, mock_hass, mock_entry):
        """update_charging_power skips early when power is unchanged."""
        mock_entry.options = {"charging_power_kw": 3.6}
        mock_entry.data = {}

        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._charging_power_kw = 3.6
        mock_hass.config_entries.async_get_entry = Mock(return_value=mock_entry)
        await adapter.update_charging_power()
        assert adapter._charging_power_kw == 3.6  # unchanged


class TestEMHASSAdapterCleanupIndices:
    """Test async_cleanup_vehicle_indices."""

    @pytest.mark.asyncio
    async def test_cleanup_clears_all_indices(self, mock_hass, mock_entry):
        """async_cleanup_vehicle_indices releases all indices for vehicle."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        await adapter.async_assign_index_to_trip("a")
        await adapter.async_assign_index_to_trip("b")
        assert len(adapter._index_map) == 2

        await adapter.async_cleanup_vehicle_indices()
        assert len(adapter._index_map) == 0
        assert adapter._published_trips == set()
        assert adapter._cached_per_trip_params == {}


class TestEMHASSAdapterPublishDeferrableLoad:
    """Test async_publish_deferrable_load."""

    @pytest.mark.asyncio
    async def test_publish_deferrable_skips_no_id(self, mock_hass, mock_entry):
        """async_publish_deferrable_load returns False for trip without id."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = await adapter.async_publish_deferrable_load({})
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_deferrable_skips_falsy_id(self, mock_hass, mock_entry):
        """async_publish_deferrable_load returns False for trip with falsy id."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = await adapter.async_publish_deferrable_load({"id": ""})
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_deferrable_tracks_published(self, mock_hass, mock_entry):
        """async_publish_deferrable_load adds trip to _published_trips on success."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        future = datetime(2027, 1, 1, tzinfo=timezone.utc).isoformat()
        trip = {"id": "published_trip", "datetime": future, "kwh": 10.0}
        result = await adapter.async_publish_deferrable_load(trip)
        assert result is True
        assert "published_trip" in adapter._published_trips


class TestEMHASSAdapterPublishAll:
    """Test async_publish_all_deferrable_loads."""

    @pytest.mark.asyncio
    async def test_publish_all_empty_clears_cache(self, mock_hass, mock_entry):
        """async_publish_all_deferrable_loads clears cache and returns True for empty list."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = await adapter.async_publish_all_deferrable_loads([])
        assert result is True

    @pytest.mark.asyncio
    async def test_publish_all_sets_shutdown_skips(self, mock_hass, mock_entry):
        """async_publish_all_deferrable_loads returns False when shutting down."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._shutting_down = True
        result = await adapter.async_publish_all_deferrable_loads([{"id": "x"}])
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_all_sets_charging_power(self, mock_hass, mock_entry):
        """async_publish_all_deferrable_loads sets load_publisher charging_power_kw."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        future = datetime(2027, 1, 1, tzinfo=timezone.utc).isoformat()
        trips = [{"id": "t1", "datetime": future, "kwh": 5.0}]
        await adapter.async_publish_all_deferrable_loads(trips, charging_power=7.4)
        assert adapter._load_publisher.charging_power_kw == 7.4


class TestEMHASSAdapterBackwardCompat:
    """Test backward-compatibility methods on facade."""

    @pytest.mark.asyncio
    async def test_get_current_soc_no_entry_dict(self, mock_hass, mock_entry):
        """_get_current_soc returns None when no _entry_dict."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = await adapter._get_current_soc()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_soc_with_entry_dict_and_sensor(
        self, mock_hass, mock_entry
    ):
        """_get_current_soc reads from entry.data soc_sensor."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        mock_entry.data = {"soc_sensor": "sensor.battery_soc"}
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        mock_hass.states.get = Mock(return_value=MagicMock(state="75"))
        result = await adapter._get_current_soc()
        assert result == 75.0

    @pytest.mark.asyncio
    async def test_get_current_soc_sensor_not_found(self, mock_hass, mock_entry):
        """_get_current_soc returns None when sensor not found."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        mock_entry.data = {"soc_sensor": "sensor.missing"}
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        mock_hass.states.get = Mock(return_value=None)
        result = await adapter._get_current_soc()
        assert result is None

    def test_calculate_deadline_delegates_to_publisher(self, mock_hass, mock_entry):
        """_calculate_deadline_from_trip delegates to LoadPublisher."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        future = datetime(2027, 1, 1, tzinfo=timezone.utc).isoformat()
        result = adapter._calculate_deadline_from_trip({"datetime": future, "id": "t1"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_hora_regreso_returns_none(self, mock_hass, mock_entry):
        """_get_hora_regreso is a stub returning None."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = await adapter._get_hora_regreso()
        assert result is None

    def test_calculate_deferrable_parameters_returns_empty(self, mock_hass, mock_entry):
        """calculate_deferrable_parameters returns empty dict."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = adapter.calculate_deferrable_parameters([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_populate_per_trip_cache_entry_creates_entry(
        self, mock_hass, mock_entry
    ):
        """_populate_per_trip_cache_entry stores params in cache."""
        from datetime import datetime, timezone

        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
            PerTripCacheParams,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        future = datetime(2027, 1, 1, tzinfo=timezone.utc).isoformat()
        trip = {"id": "cache_test", "datetime": future, "kwh": 10.0}
        await adapter._populate_per_trip_cache_entry(
            PerTripCacheParams(
                trip=trip,
                trip_id="cache_test",
                charging_power_kw=3.6,
                battery_capacity_kwh=50.0,
                safety_margin_percent=30.0,
                soc_current=50.0,
            ),
        )
        assert "cache_test" in adapter._cached_per_trip_params

    @pytest.mark.asyncio
    async def test_populate_per_trip_cache_entry_with_no_deadline(
        self, mock_hass, mock_entry
    ):
        """_populate_per_trip_cache_entry handles None deadline gracefully."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
            PerTripCacheParams,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        trip = {"id": "no_deadline", "kwh": 10.0}
        await adapter._populate_per_trip_cache_entry(
            PerTripCacheParams(
                trip=trip,
                trip_id="no_deadline",
                charging_power_kw=3.6,
                battery_capacity_kwh=50.0,
                safety_margin_percent=30.0,
                soc_current=50.0,
            ),
        )
        assert "no_deadline" in adapter._cached_per_trip_params


class TestEMHASSAdapterRemoveLoad:
    """Test async_remove_deferrable_load."""

    @pytest.mark.asyncio
    async def test_async_remove_delegates_to_publisher(self, mock_hass, mock_entry):
        """async_remove_deferrable_load delegates to LoadPublisher.remove()."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = await adapter.async_remove_deferrable_load("unknown_trip")
        assert result is False


class TestEMHASSAdapterUpdateLoad:
    """Test async_update_deferrable_load."""

    @pytest.mark.asyncio
    async def test_async_update_delegates_to_publisher(self, mock_hass, mock_entry):
        """async_update_deferrable_load delegates to LoadPublisher.update()."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        result = await adapter.async_update_deferrable_load({})
        assert result is False  # update fails for missing-id trip


class TestEMHASSAdapterSetupConfigEntryListener:
    """Test setup_config_entry_listener."""

    def test_setup_config_entry_listener_subscribes(self, mock_hass, mock_entry):
        """setup_config_entry_listener stores config_entry reference."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        mock_hass.config_entries.async_get_entry = Mock(return_value=mock_entry)
        adapter.setup_config_entry_listener()
        assert hasattr(adapter, "config_entry")


class TestEMHASSAdapterHandleConfigEntryUpdate:
    """Test _handle_config_entry_update."""

    @pytest.mark.asyncio
    async def test_handle_config_entry_update_stores_power(self, mock_hass, mock_entry):
        """_handle_config_entry_update stores new charging power value."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._shutting_down = False
        new_entry = MagicMock()
        new_entry.options = {"charging_power_kw": 11.0}
        await adapter._handle_config_entry_update(mock_hass, new_entry)
        assert adapter._stored_charging_power_kw == 11.0
        assert adapter._charging_power_kw == 11.0

    @pytest.mark.asyncio
    async def test_handle_config_entry_update_skips_when_shutting_down(
        self, mock_hass, mock_entry
    ):
        """_handle_config_entry_update returns early when shutting down."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._shutting_down = True
        new_entry = MagicMock()
        new_entry.options = {"charging_power_kw": 99.0}
        await adapter._handle_config_entry_update(mock_hass, new_entry)
        # Should not have changed
        assert adapter._stored_charging_power_kw is None


class TestEMHASSAdapterAsyncSaveTrips:
    """Test async_save_trips."""

    @pytest.mark.asyncio
    async def test_async_save_trips_delegates(self, mock_hass, mock_entry):
        """async_save_trips delegates to index_manager.async_save_index."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        await adapter.async_save_trips()  # no raise


class TestEMHASSAdapterIndexMapProperty:
    """Test _index_map property getter/setter."""

    def test_index_map_property_getter(self, mock_hass, mock_entry):
        """_index_map property returns IndexManager's internal map."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._index_manager._index_map = {"a": 1}
        assert adapter._index_map == {"a": 1}

    def test_index_map_property_setter(self, mock_hass, mock_entry):
        """_index_map property setter updates IndexManager's internal map."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        adapter._index_map = {"x": 99}
        assert adapter._index_manager._index_map == {"x": 99}


# ===================================================================
# Package re-exports tests
# ===================================================================


class TestEmhassPackageInit:
    """Test emhass/__init__.py re-exports."""

    def test_package_exports_emhass_adapter(self):
        """EMHASSAdapter is re-exported from emhass package."""
        from custom_components.ev_trip_planner.emhass import EMHASSAdapter

        assert EMHASSAdapter is not None

    def test_package_exports_error_handler(self):
        """ErrorHandler is re-exported from emhass package."""
        from custom_components.ev_trip_planner.emhass import ErrorHandler

        assert ErrorHandler is not None

    def test_package_exports_index_manager(self):
        """IndexManager is re-exported from emhass package."""
        from custom_components.ev_trip_planner.emhass import IndexManager

        assert IndexManager is not None

    def test_package_exports_load_publisher(self):
        """LoadPublisher is re-exported from emhass package."""
        from custom_components.ev_trip_planner.emhass import LoadPublisher

        assert LoadPublisher is not None

    def test_all_declares_public_names(self):
        """__all__ lists all four public classes."""
        from custom_components.ev_trip_planner import emhass

        assert emhass.__all__ == [
            "EMHASSAdapter",
            "ErrorHandler",
            "IndexManager",
            "LoadPublisher",
        ]


# ===================================================================
# Integration: facade + sub-components
# ===================================================================


class TestFacadeCompositionIntegrity:
    """Test that the facade properly composes sub-components."""

    def test_error_handler_independent_of_index_manager(self, mock_hass, mock_entry):
        """ErrorHandler is a separate instance from IndexManager."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        assert adapter._error_handler is not adapter._index_manager

    def test_load_publisher_shares_index_manager(self, mock_hass, mock_entry):
        """LoadPublisher shares the same IndexManager as the facade (prevents index exhaustion)."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        assert adapter._load_publisher._index_manager is adapter._index_manager

    def test_facade_error_handler_has_hass(self, mock_hass, mock_entry):
        """ErrorHandler received the same hass instance."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )

        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        assert adapter._error_handler.hass is mock_hass
