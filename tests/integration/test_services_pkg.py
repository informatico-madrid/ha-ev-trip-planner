"""Tests for services package __init__.py (register_services).

Covers the register_services function that registers all HA services,
and the re-export shim modules (_lookup.py, presence.py, handlers.py).
"""

from __future__ import annotations

from unittest.mock import MagicMock


class TestRegisterServices:
    """Test register_services in services/__init__.py."""

    def test_register_services(self) -> None:
        """register_services should register all expected HA services."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()

        from custom_components.ev_trip_planner.services import register_services

        register_services(hass)

        # Should have registered all service names
        calls = hass.services.async_register.call_count
        # Expected services: add_recurring, add_punctual, edit_trip,
        # trip_update, trip_create, delete_trip, pause_recurring,
        # resume_recurring, complete_punctual, cancel_punctual,
        # import_from_weekly_pattern, trip_list, trip_get = 13
        assert calls == 13

    def test_register_services_add_recurring_trip(self) -> None:
        """First registered service should be add_recurring_trip."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()

        from custom_components.ev_trip_planner.services import register_services

        register_services(hass)
        first_call = hass.services.async_register.call_args_list[0]
        assert first_call[0][1] == "add_recurring_trip"
