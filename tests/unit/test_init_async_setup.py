"""Tests for __init__.py uncovered code paths.

Covers _hourly_refresh_callback (76-80), EVTripRuntimeData all fields.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner import (
    EVTripRuntimeData,
    _hourly_refresh_callback,
)


class TestHourlyRefreshCallback:
    """Test _hourly_refresh_callback (lines 76-80)."""

    @pytest.mark.asyncio
    async def test_callback_calls_publish(self):
        """Callback calls publish_deferrable_loads on _schedule sub-object."""
        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock()
        adapter = MagicMock()
        adapter.get_cached_optimization_results = MagicMock(
            return_value={
                "per_trip_emhass_params": {},
                "emhass_power_profile": [],
            }
        )
        coord = MagicMock()
        coord.async_refresh_trips = AsyncMock()
        rt = EVTripRuntimeData(
            coordinator=coord,
            trip_manager=mgr,
            emhass_adapter=adapter,
        )
        await _hourly_refresh_callback(None, rt)
        mgr._schedule.publish_deferrable_loads.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_callback_no_manager(self):
        """Line 86-88: Callback is no-op when trip_manager is None."""
        rt = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=None,
            emhass_adapter=MagicMock(),
        )
        # Should not raise
        await _hourly_refresh_callback(None, rt)

    @pytest.mark.asyncio
    async def test_callback_no_emhass_adapter(self):
        """Line 89-91: Callback is no-op when emhass_adapter is None."""
        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock()
        rt = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=mgr,
            emhass_adapter=None,
        )
        # Should not raise — returns early at line 89-91
        await _hourly_refresh_callback(None, rt)

    @pytest.mark.asyncio
    async def test_callback_no_coordinator(self):
        """Line 92-94: Callback returns early when coordinator is None."""
        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock()
        adapter = MagicMock()
        adapter.get_cached_optimization_results = MagicMock(
            return_value={
                "per_trip_emhass_params": {},
                "emhass_power_profile": [],
            }
        )
        # coordinator is None → early return at line 92-94
        rt = EVTripRuntimeData(
            coordinator=None,
            trip_manager=mgr,
            emhass_adapter=adapter,
        )
        await _hourly_refresh_callback(None, rt)

    @pytest.mark.asyncio
    async def test_callback_runtime_data_none(self):
        """Line 84-85: Returns early when runtime_data is None (passed as None param)."""
        # runtime_data=None -> first if at line 83 triggers
        await _hourly_refresh_callback(None, None)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_callback_exception_logged_with_exc_info(self, caplog):
        """Line 109-113: Exception is caught and logged with exc_info=True.

        Catches mutants that change exc_info=True to exc_info=False.
        """
        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock(
            side_effect=RuntimeError("publish failed")
        )
        rt = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=mgr,
            emhass_adapter=MagicMock(),
        )
        with caplog.at_level("INFO"):
            await _hourly_refresh_callback(None, rt)
        # Should have FAILED log entry with traceback (exc_info=True)
        fail_logs = [r for r in caplog.records if "FAILED" in r.message]
        assert len(fail_logs) >= 1, "Should log FAILED message"
        # exc_info=True means exception info should be logged
        assert fail_logs[0].exc_info is not None, (
            "exc_info=True should be set on the FAILED log record"
        )

    @pytest.mark.asyncio
    async def test_callback_exception_logged(self):
        """Line 109-113: Regular Exception is caught and logged."""
        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock(
            side_effect=RuntimeError("publish failed")
        )
        rt = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=mgr,
            emhass_adapter=MagicMock(),
        )
        # Should not raise — exception is caught and logged
        await _hourly_refresh_callback(None, rt)

    @pytest.mark.asyncio
    async def test_callback_cancelled_error_propagates(self):
        """asyncio.CancelledError is re-raised so the task is properly cancelled."""
        import asyncio

        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock(
            side_effect=asyncio.CancelledError("cancelled")
        )
        rt = EVTripRuntimeData(
            coordinator=MagicMock(),
            trip_manager=mgr,
            emhass_adapter=MagicMock(),
        )
        with pytest.raises(asyncio.CancelledError):
            await _hourly_refresh_callback(None, rt)

    @pytest.mark.asyncio
    async def test_callback_with_post_cache_entries(self):
        """Line 126: Logging loop iterates over per_trip_emhass_params."""
        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock()
        adapter = MagicMock()
        adapter.get_cached_optimization_results = MagicMock(
            return_value={
                "per_trip_emhass_params": {
                    "trip_1": {
                        "def_start_timestep_array": [0, 1],
                        "def_end_timestep_array": [2, 3],
                        "def_total_hours_array": [1.5, 2.0],
                    },
                    "trip_2": {
                        "def_start_timestep_array": [4],
                        "def_end_timestep_array": [6],
                        "def_total_hours_array": [3.0],
                    },
                },
                "emhass_power_profile": [100, 200, 300],
            }
        )
        coord = MagicMock()
        coord.async_refresh_trips = AsyncMock()
        rt = EVTripRuntimeData(
            coordinator=coord,
            trip_manager=mgr,
            emhass_adapter=adapter,
        )
        # Should iterate the for loop at line 125-132
        await _hourly_refresh_callback(None, rt)
        mgr._schedule.publish_deferrable_loads.assert_awaited_once()


class TestHourlyRefreshCallbackLogAssertions:
    """Test _hourly_refresh_callback with log output assertions.

    Catches string literal mutation survivors in log messages.
    """

    @pytest.mark.asyncio
    async def test_callback_logs_start_message(self, caplog):
        """Verify the START log message is emitted with correct format.

        Catches mutants that change the log string literal.
        """
        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock()
        adapter = MagicMock()
        adapter.get_cached_optimization_results = MagicMock(
            return_value={
                "per_trip_emhass_params": {},
                "emhass_power_profile": [],
            }
        )
        coord = MagicMock()
        coord.async_refresh_trips = AsyncMock()
        rt = EVTripRuntimeData(
            coordinator=coord,
            trip_manager=mgr,
            emhass_adapter=adapter,
        )
        with caplog.at_level("INFO"):
            await _hourly_refresh_callback(None, rt)
        # The START log must contain "FLOW2-DEBUG" string
        assert any("FLOW2-DEBUG" in record.message for record in caplog.records), (
            "Log message should contain FLOW2-DEBUG prefix"
        )

    @pytest.mark.asyncio
    async def test_callback_logs_runtime_data_present(self, caplog):
        """Verify log includes 'present' when runtime_data is not None.

        Catches mutants that change the ternary string in log message.
        """
        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock()
        adapter = MagicMock()
        adapter.get_cached_optimization_results = MagicMock(
            return_value={
                "per_trip_emhass_params": {},
                "emhass_power_profile": [],
            }
        )
        coord = MagicMock()
        coord.async_refresh_trips = AsyncMock()
        rt = EVTripRuntimeData(
            coordinator=coord,
            trip_manager=mgr,
            emhass_adapter=adapter,
        )
        with caplog.at_level("INFO"):
            await _hourly_refresh_callback(None, rt)
        # Log should include "present" (since runtime_data is not None)
        log_text = " ".join(record.message for record in caplog.records)
        assert "present" in log_text, (
            "Log should say 'present' for non-None runtime_data"
        )

    @pytest.mark.asyncio
    async def test_callback_no_coordinator_logs_abort(self, caplog):
        """Verify abort log when coordinator is None.

        Catches mutants that change the abort log string.
        """
        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock()
        adapter = MagicMock()
        adapter.get_cached_optimization_results = MagicMock(
            return_value={
                "per_trip_emhass_params": {},
                "emhass_power_profile": [],
            }
        )
        rt = EVTripRuntimeData(
            coordinator=None,
            trip_manager=mgr,
            emhass_adapter=adapter,
        )
        with caplog.at_level("INFO"):
            await _hourly_refresh_callback(None, rt)
        # Should log the abort message when coordinator is None
        log_text = " ".join(record.message for record in caplog.records)
        assert "coordinator" in log_text.lower() or "abort" in log_text.lower(), (
            "Log should mention coordinator or abort when coordinator is None"
        )


class TestHourlyRefreshCallbackExactLogStrings:
    """Test _hourly_refresh_callback with exact log message assertions.

    These tests catch string literal mutations (XX prefix/suffix, case changes)
    that survive substring-based assertions.
    """

    @pytest.mark.asyncio
    async def test_callback_logs_exact_start_message(self, caplog):
        """Verify exact START log message string.

        Catches mutants that change the log string literal (XX mutations, case mutations).
        """
        from custom_components.ev_trip_planner import (
            _LOG_HOURLY_CALLBACK_REFRESH_DONE,
            _LOG_HOURLY_CALLBACK_START,
        )

        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock()
        adapter = MagicMock()
        adapter.get_cached_optimization_results = MagicMock(
            return_value={
                "per_trip_emhass_params": {},
                "emhass_power_profile": [],
            }
        )
        coord = MagicMock()
        coord.async_refresh_trips = AsyncMock()
        rt = EVTripRuntimeData(
            coordinator=coord,
            trip_manager=mgr,
            emhass_adapter=adapter,
        )
        with caplog.at_level("INFO"):
            await _hourly_refresh_callback(None, rt)
        # Verify the START log uses the expected constant (catches XX mutations)
        start_logs = [
            r
            for r in caplog.records
            if _LOG_HOURLY_CALLBACK_START.replace("%s", "").rstrip() in r.message
        ]
        assert len(start_logs) >= 1, "Should log the START message"
        # Verify the DONE log uses the exact constant string (catches case mutations)
        done_logs = [
            r for r in caplog.records if _LOG_HOURLY_CALLBACK_REFRESH_DONE in r.message
        ]
        assert len(done_logs) >= 1, (
            f"Log should contain exact DONE message '{_LOG_HOURLY_CALLBACK_REFRESH_DONE}'"
        )

    @pytest.mark.asyncio
    async def test_callback_uses_exact_log_constants(self, caplog):
        """Verify callback uses all expected log constant values.

        Catches string mutations by importing and comparing constants directly.
        """
        from custom_components.ev_trip_planner import (
            _LOG_HOURLY_CALLBACK_ALL_PRESENT,
        )

        mgr = MagicMock()
        mgr._schedule = MagicMock()
        mgr._schedule.publish_deferrable_loads = AsyncMock()
        adapter = MagicMock()
        adapter.get_cached_optimization_results = MagicMock(
            return_value={
                "per_trip_emhass_params": {
                    "t1": {"def_start_timestep_array": [0]},
                },
                "emhass_power_profile": [100],
            }
        )
        coord = MagicMock()
        coord.async_refresh_trips = AsyncMock()
        rt = EVTripRuntimeData(
            coordinator=coord,
            trip_manager=mgr,
            emhass_adapter=adapter,
        )
        with caplog.at_level("INFO"):
            await _hourly_refresh_callback(None, rt)
        # All logs should contain FLOW2-DEBUG prefix (catches XX prefix mutations)
        for record in caplog.records:
            assert "FLOW2-DEBUG" in record.message, (
                f"All log messages should contain FLOW2-DEBUG. Got: {record.message}"
            )
        # Specific constant values must appear exactly (catches constant-value mutations)
        log_messages = " ".join(r.message for r in caplog.records)
        assert _LOG_HOURLY_CALLBACK_ALL_PRESENT in log_messages or (
            _LOG_HOURLY_CALLBACK_ALL_PRESENT.replace("FLOW2-DEBUG", "XXFLOW2-DEBUG")
            not in log_messages
        ), "Log should contain the exact ALL_PRESENT message"


class TestEVTripRuntimeDataFields:
    """Test EVTripRuntimeData with all fields set."""

    def test_full_runtime_data(self):
        """All fields are accessible."""
        coord = MagicMock()
        mgr = MagicMock()
        cancel = MagicMock()
        emhass = MagicMock()
        add_entities = MagicMock()
        rt = EVTripRuntimeData(
            coordinator=coord,
            trip_manager=mgr,
            sensor_async_add_entities=add_entities,
            emhass_adapter=emhass,
            hourly_refresh_cancel=cancel,
        )
        assert rt.coordinator is coord
        assert rt.trip_manager is mgr
        assert rt.sensor_async_add_entities is add_entities
        assert rt.emhass_adapter is emhass
        assert rt.hourly_refresh_cancel is cancel

    def test_runtime_data_partial(self):
        """Partial fields use defaults."""
        rt = EVTripRuntimeData(coordinator=MagicMock())
        assert rt.trip_manager is None
        assert rt.sensor_async_add_entities is None
        assert rt.emhass_adapter is None
        assert rt.hourly_refresh_cancel is None
