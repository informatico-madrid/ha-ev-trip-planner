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

    def test_register_services_trip_list_response(self) -> None:
        """trip_list should support response (returns data)."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()

        from custom_components.ev_trip_planner.services import register_services

        register_services(hass)
        calls = hass.services.async_register.call_args_list
        # Find trip_list call (11th, 0-indexed)
        trip_list_call = calls[11]
        assert trip_list_call[0][1] == "trip_list"
        # Should have supports_response
        assert trip_list_call[1].get("supports_response") is not None

    def test_register_services_trip_get_response(self) -> None:
        """trip_get should support response (returns data)."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()

        from custom_components.ev_trip_planner.services import register_services

        register_services(hass)
        calls = hass.services.async_register.call_args_list
        # trip_get is the last call (12th, 0-indexed)
        trip_get_call = calls[12]
        assert trip_get_call[0][1] == "trip_get"


class TestServicesLookupShim:
    """Test services/_lookup.py re-export shim."""

    def test_lookup_exports_get_coordinator(self) -> None:
        """_lookup.py should re-export _get_coordinator."""
        from custom_components.ev_trip_planner.services._lookup import (
            _get_coordinator,
        )

        assert _get_coordinator is not None

    def test_lookup_all_exports(self) -> None:
        """__all__ should list _get_coordinator."""
        from custom_components.ev_trip_planner.services._lookup import __all__

        assert "_get_coordinator" in __all__


class TestServicesPresenceShim:
    """Test services/presence.py re-export shim."""

    def test_presence_exports_build_config(self) -> None:
        """presence.py should re-export build_presence_config."""
        from custom_components.ev_trip_planner.services.presence import (
            build_presence_config,
        )

        assert build_presence_config is not None

    def test_presence_all_exports(self) -> None:
        """__all__ should list build_presence_config."""
        from custom_components.ev_trip_planner.services.presence import __all__

        assert "build_presence_config" in __all__


class TestServicesHandlersShim:
    """Test services/handlers.py re-export shim."""

    def test_handlers_exports_register_services(self) -> None:
        """handlers.py should re-export register_services."""
        from custom_components.ev_trip_planner.services.handlers import (
            register_services,
        )

        assert callable(register_services)

    def test_handlers_all_exports(self) -> None:
        """__all__ should list register_services."""
        from custom_components.ev_trip_planner.services.handlers import __all__

        assert "register_services" in __all__
