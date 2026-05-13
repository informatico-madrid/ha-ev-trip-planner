"""Tests for services re-export shim modules.

Covers _lookup.py, handlers.py, presence.py which are thin
re-export shims — tests verify exports are available.
"""

from __future__ import annotations


class TestServicesLookupShim:
    """Test _lookup.py re-exports."""

    def test_get_coordinator_reexported(self) -> None:
        """_lookup should re-export _get_coordinator."""
        from custom_components.ev_trip_planner.services._lookup import (
            _get_coordinator,
        )

        assert _get_coordinator is not None
        assert callable(_get_coordinator)

    def test_lookup_all_exports(self) -> None:
        """_lookup __all__ should match actual exports."""
        from custom_components.ev_trip_planner.services import _lookup

        assert _lookup.__all__ == ["_get_coordinator"]


class TestServicesHandlersShim:
    """Test handlers.py re-export shim."""

    def test_register_services_reexported(self) -> None:
        """handlers should re-export register_services."""
        from custom_components.ev_trip_planner.services.handlers import (
            register_services,
        )

        assert register_services is not None
        assert callable(register_services)

    def test_handlers_all_exports(self) -> None:
        """handlers __all__ should match actual exports."""
        from custom_components.ev_trip_planner.services import handlers

        assert handlers.__all__ == ["register_services"]


class TestServicesPresenceShim:
    """Test presence.py re-export shim."""

    def test_build_presence_config_reexported(self) -> None:
        """presence should re-export build_presence_config."""
        from custom_components.ev_trip_planner.services.presence import (
            build_presence_config,
        )

        assert build_presence_config is not None
        assert callable(build_presence_config)

    def test_presence_all_exports(self) -> None:
        """presence __all__ should match actual exports."""
        from custom_components.ev_trip_planner.services import presence

        assert presence.__all__ == ["build_presence_config"]
