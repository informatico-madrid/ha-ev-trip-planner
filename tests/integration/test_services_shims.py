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


class TestDashboardBase:
    """Test dashboard/_base.py ABCs and Protocols."""

    def test_dashboard_component_protocol_exists(self) -> None:
        """DashboardComponentProtocol should be importable and abstract."""
        from custom_components.ev_trip_planner.dashboard._base import (
            DashboardComponentProtocol,
        )

        assert DashboardComponentProtocol is not None
        assert hasattr(DashboardComponentProtocol, "component_name")
        assert hasattr(DashboardComponentProtocol, "component_config")

    def test_dashboard_importer_protocol_exists(self) -> None:
        """DashboardImporterProtocol should be importable and abstract."""
        from custom_components.ev_trip_planner.dashboard._base import (
            DashboardImporterProtocol,
        )

        assert DashboardImporterProtocol is not None
        assert hasattr(DashboardImporterProtocol, "validate_config")
        assert hasattr(DashboardImporterProtocol, "import_config")

    def test_dashboard_storage_strategy_exists(self) -> None:
        """DashboardStorageStrategy should be importable and abstract."""
        from custom_components.ev_trip_planner.dashboard._base import (
            DashboardStorageStrategy,
        )

        assert DashboardStorageStrategy is not None
        assert hasattr(DashboardStorageStrategy, "save_config")
        assert hasattr(DashboardStorageStrategy, "load_config")
        assert hasattr(DashboardStorageStrategy, "exists")
        assert hasattr(DashboardStorageStrategy, "delete")

    def test_dashboard_template_strategy_exists(self) -> None:
        """DashboardTemplateStrategy should be importable and abstract."""
        from custom_components.ev_trip_planner.dashboard._base import (
            DashboardTemplateStrategy,
        )

        assert DashboardTemplateStrategy is not None
        assert hasattr(DashboardTemplateStrategy, "get_template_path")
        assert hasattr(DashboardTemplateStrategy, "load_template")
        assert hasattr(DashboardTemplateStrategy, "save_template")

    def test_cannot_instantiate_abstract_protocol(self) -> None:
        """Cannot instantiate abstract protocols directly."""
        from custom_components.ev_trip_planner.dashboard._base import (
            DashboardImporterProtocol,
        )

        # Verify the class is abstract (has unimplemented abstract methods)
        abstract_methods = getattr(DashboardImporterProtocol, "__abstractmethods__", set())
        assert len(abstract_methods) > 0, (
            f"DashboardImporterProtocol should have abstract methods, "
            f"found {len(abstract_methods)}"
        )

    def test_concrete_implementation_works(self) -> None:
        """Concrete implementations of protocols should be instantiable."""
        from custom_components.ev_trip_planner.dashboard._base import (
            DashboardImporterProtocol,
        )

        class TestImporter(DashboardImporterProtocol):
            def validate_config(self, config: dict) -> bool:
                return bool(config)

            def import_config(self, hass, vehicle_id: str, config: dict) -> dict:
                return config

        importer = TestImporter()
        assert importer.validate_config({"key": "val"}) is True
        assert importer.validate_config({}) is False
