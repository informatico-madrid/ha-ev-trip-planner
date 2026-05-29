"""Tests for handler factory closures in _handler_factories.py.

These tests verify that handler factory functions exist and produce
async handler functions. Each factory produces a closure that closes
over hass/entry to create a service handler.
"""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_hass():
    """Return a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.services = MagicMock()
    return hass


class TestHandlerFactoryImports:
    """Verify that handler factory functions are importable and callable."""

    def test_make_add_recurring_handler_exists_and_callable(self) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_add_recurring_handler,
        )

        assert callable(make_add_recurring_handler)

    def test_make_add_punctual_handler_exists_and_callable(self) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_add_punctual_handler,
        )

        assert callable(make_add_punctual_handler)

    def test_make_trip_create_handler_exists_and_callable(self) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_create_handler,
        )

        assert callable(make_trip_create_handler)

    def test_make_trip_update_handler_exists_and_callable(self) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_update_handler,
        )

        assert callable(make_trip_update_handler)

    def test_make_edit_trip_handler_exists_and_callable(self) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_edit_trip_handler,
        )

        assert callable(make_edit_trip_handler)

    def test_make_delete_trip_handler_exists_and_callable(self) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_delete_trip_handler,
        )

        assert callable(make_delete_trip_handler)

    def test_make_pause_recurring_handler_exists_and_callable(self) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_pause_recurring_handler,
        )

        assert callable(make_pause_recurring_handler)

    def test_make_resume_recurring_handler_exists_and_callable(self) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_resume_recurring_handler,
        )

        assert callable(make_resume_recurring_handler)

    def test_make_complete_punctual_handler_exists_and_callable(self) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_complete_punctual_handler,
        )

        assert callable(make_complete_punctual_handler)

    def test_make_cancel_punctual_handler_exists_and_callable(self) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_cancel_punctual_handler,
        )

        assert callable(make_cancel_punctual_handler)

    def test_make_import_weekly_pattern_handler_exists_and_callable(self) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_import_weekly_pattern_handler,
        )

        assert callable(make_import_weekly_pattern_handler)

    def test_make_trip_list_handler_exists_and_callable(self) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_list_handler,
        )

        assert callable(make_trip_list_handler)

    def test_make_trip_get_handler_exists_and_callable(self) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_get_handler,
        )

        assert callable(make_trip_get_handler)


class TestFactoryReturnsAsyncHandler:
    """Verify that factory functions return async handler coroutines."""

    def test_make_add_recurring_handler_returns_async(
        self, mock_hass: MagicMock
    ) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_add_recurring_handler,
        )

        handler = make_add_recurring_handler(mock_hass)
        assert inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(
            handler
        )

    def test_make_add_punctual_handler_returns_async(
        self, mock_hass: MagicMock
    ) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_add_punctual_handler,
        )

        handler = make_add_punctual_handler(mock_hass)
        assert inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(
            handler
        )

    def test_make_trip_create_handler_returns_async(self, mock_hass: MagicMock) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_create_handler,
        )

        handler = make_trip_create_handler(mock_hass)
        assert inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(
            handler
        )

    def test_make_trip_update_handler_returns_async(self, mock_hass: MagicMock) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_update_handler,
        )

        handler = make_trip_update_handler(mock_hass)
        assert inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(
            handler
        )

    def test_make_edit_trip_handler_returns_async(self, mock_hass: MagicMock) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_edit_trip_handler,
        )

        handler = make_edit_trip_handler(mock_hass)
        assert inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(
            handler
        )

    def test_make_delete_trip_handler_returns_async(self, mock_hass: MagicMock) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_delete_trip_handler,
        )

        handler = make_delete_trip_handler(mock_hass)
        assert inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(
            handler
        )

    def test_make_pause_recurring_handler_returns_async(
        self, mock_hass: MagicMock
    ) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_pause_recurring_handler,
        )

        handler = make_pause_recurring_handler(mock_hass)
        assert inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(
            handler
        )

    def test_make_resume_recurring_handler_returns_async(
        self, mock_hass: MagicMock
    ) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_resume_recurring_handler,
        )

        handler = make_resume_recurring_handler(mock_hass)
        assert inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(
            handler
        )

    def test_make_complete_punctual_handler_returns_async(
        self, mock_hass: MagicMock
    ) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_complete_punctual_handler,
        )

        handler = make_complete_punctual_handler(mock_hass)
        assert inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(
            handler
        )

    def test_make_cancel_punctual_handler_returns_async(
        self, mock_hass: MagicMock
    ) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_cancel_punctual_handler,
        )

        handler = make_cancel_punctual_handler(mock_hass)
        assert inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(
            handler
        )

    def test_make_import_weekly_pattern_handler_returns_async(
        self, mock_hass: MagicMock
    ) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_import_weekly_pattern_handler,
        )

        handler = make_import_weekly_pattern_handler(mock_hass)
        assert inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(
            handler
        )

    def test_make_trip_list_handler_returns_async(self, mock_hass: MagicMock) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_list_handler,
        )

        handler = make_trip_list_handler(mock_hass)
        assert inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(
            handler
        )

    def test_make_trip_get_handler_returns_async(self, mock_hass: MagicMock) -> None:
        from custom_components.ev_trip_planner.services._handler_factories import (
            make_trip_get_handler,
        )

        handler = make_trip_get_handler(mock_hass)
        assert inspect.iscoroutinefunction(handler) or asyncio.iscoroutinefunction(
            handler
        )
