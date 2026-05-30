"""Tests for ErrorHandler in emhass.error_handler."""

import logging
from unittest.mock import MagicMock

import pytest  # noqa: F401


class TestErrorHandlerExists:
    """Test that ErrorHandler class exists in emhass.error_handler module."""

    def test_error_handler_importable(self):
        """ErrorHandler can be imported from emhass.error_handler."""
        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        assert ErrorHandler is not None


# ---------------------------------------------------------------------------
# Functional return-value tests (kill bool_flip / default_value mutations)
# ---------------------------------------------------------------------------


class TestErrorHandlerReturnValues:
    """Assert return values to kill mutations on 'return False' / 'return None'."""

    @pytest.fixture
    def handler(self):
        """Minimal ErrorHandler with no-op on_error callback."""
        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        return ErrorHandler(hass=MagicMock(), on_error=lambda *a: None)

    def test_handle_missing_id_returns_false(self, handler):
        """handle_missing_id returns False — assert to kill bool_flip mutation."""
        assert handler.handle_missing_id("trip-1", "publish") is False

    def test_handle_deadline_error_returns_false(self, handler):
        """handle_deadline_error returns False — assert to kill bool_flip mutation."""
        assert handler.handle_deadline_error("trip-1", "publish") is False

    def test_handle_index_error_returns_none(self, handler):
        """handle_index_error returns None — assert to kill default_value mutation."""
        assert handler.handle_index_error("trip-1", "release") is None


# ---------------------------------------------------------------------------
# Default parameter value tests — kill mutations on default operation string
#
# Mutations that survive:
#   handle_missing_id  mutmut_1: operation="publish" -> "XXpublishXX"
#   handle_missing_id  mutmut_2: operation="publish" -> "PUBLISH"
#   handle_deadline_error mutmut_1: operation="publish" -> "XXpublishXX"
#   handle_deadline_error mutmut_2: operation="publish" -> "PUBLISH"
#
# Previous tests pass operation explicitly, so the default is never exercised.
# These tests call WITHOUT operation arg and verify the log message uses "publish".
# ---------------------------------------------------------------------------


class TestErrorHandlerDefaultOperation:
    """Kill default-parameter mutations on handle_missing_id / handle_deadline_error.

    Mutants change the default value of `operation` from "publish" to
    "XXpublishXX" or "PUBLISH".  Calling without the argument and checking the
    log message content kills both variants.
    """

    @pytest.fixture
    def handler(self):
        """Minimal ErrorHandler — no on_error callback needed."""
        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        return ErrorHandler(hass=MagicMock())

    def test_handle_missing_id_default_operation_in_log(self, handler, caplog):
        """handle_missing_id() uses default operation='publish' in log message.

        Kills mutmut_1 ("XXpublishXX") and mutmut_2 ("PUBLISH"):
        - original: _LOGGER.error(_LOG_MISSING_ID, "publish") → "Trip missing ID during publish"
        - mutant_1: _LOGGER.error(_LOG_MISSING_ID, "XXpublishXX") → contains "XXpublishXX"
        - mutant_2: _LOGGER.error(_LOG_MISSING_ID, "PUBLISH") → contains "PUBLISH" not "publish"
        """
        with caplog.at_level(
            logging.ERROR,
            logger="custom_components.ev_trip_planner.emhass.error_handler",
        ):
            result = handler.handle_missing_id(
                "trip-1"
            )  # No operation arg — uses default
        assert result is False
        # Verify the default "publish" was used, not "XXpublishXX" or "PUBLISH"
        assert any("publish" in record.message for record in caplog.records), (
            f"Expected 'publish' in log message. Records: {[r.message for r in caplog.records]}"
        )
        assert not any("XXpublishXX" in record.message for record in caplog.records)
        assert not any(
            "PUBLISH" == op for record in caplog.records for op in [record.message]
        )

    def test_handle_deadline_error_default_operation_in_log(self, handler, caplog):
        """handle_deadline_error() uses default operation='publish' in log message.

        Kills mutmut_1 ("XXpublishXX") and mutmut_2 ("PUBLISH"):
        - original: _LOGGER.error(_LOG_DEADLINE_ERROR, trip_id, "publish")
        - mutant_1: _LOGGER.error(_LOG_DEADLINE_ERROR, trip_id, "XXpublishXX")
        - mutant_2: _LOGGER.error(_LOG_DEADLINE_ERROR, trip_id, "PUBLISH")
        """
        with caplog.at_level(
            logging.ERROR,
            logger="custom_components.ev_trip_planner.emhass.error_handler",
        ):
            result = handler.handle_deadline_error(
                "trip-1"
            )  # No operation arg — uses default
        assert result is False
        # Verify the default "publish" was used
        assert any("publish" in record.message for record in caplog.records), (
            f"Expected 'publish' in log message. Records: {[r.message for r in caplog.records]}"
        )
        assert not any("XXpublishXX" in record.message for record in caplog.records)

    def test_handle_missing_id_default_operation_returns_false(self, handler):
        """Calling handle_missing_id without operation arg returns False.

        Verifies the return value is always False regardless of default mutation.
        (Complementary to log check: both must pass to kill the mutant.)
        """
        assert handler.handle_missing_id("trip-xyz") is False

    def test_handle_deadline_error_default_operation_returns_false(self, handler):
        """Calling handle_deadline_error without operation arg returns False.

        Verifies the return value is always False regardless of default mutation.
        """
        assert handler.handle_deadline_error("trip-xyz") is False
