"""Tests for ErrorHandler in emhass.error_handler."""

import pytest  # noqa: F401


class TestErrorHandlerExists:
    """Test that ErrorHandler class exists in emhass.error_handler module."""

    def test_error_handler_importable(self):
        """ErrorHandler can be imported from emhass.error_handler."""
        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        assert ErrorHandler is not None
