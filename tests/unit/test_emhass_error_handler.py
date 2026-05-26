"""Tests for ErrorHandler in emhass.error_handler."""

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
