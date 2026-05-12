"""Verify that the services/ package re-exports all public names from services.py.

Tests that the `services` package (after SOLID decomposition) exposes
every public name from the original `services.py` module.

This test MUST pass — the services/ package is the transitional re-export layer
that preserves the original public API while enabling future decomposition.

Requirement: AC-2.4, AC-2.5
Design: §3.7 (services module decomposition)
"""

from importlib import import_module
from pathlib import Path

# All public names from services.py (non-underscore-prefixed)
ALL_PUBLIC_NAMES: tuple[str, ...] = (
    "PLATFORMS",
    "CoordinatorType",
    "register_services",
    "create_dashboard_input_helpers",
    "async_cleanup_stale_storage",
    "async_cleanup_orphaned_emhass_sensors",
    "build_presence_config",
    "async_register_static_paths",
    "async_register_panel_for_entry",
    "async_import_dashboard_for_entry",
    "async_unload_entry_cleanup",
    "async_remove_entry_cleanup",
)


def test_services_resolves_as_package():
    """The `services` import MUST resolve as a package, not a module file.

    After SOLID decomposition, `custom_components.ev_trip_planner.services`
    must be a directory with `__init__.py`, not the legacy `services.py` file.
    """
    import custom_components.ev_trip_planner.services as svc

    # The module file path must be under a 'services' directory (package)
    mod_file = Path(svc.__file__)
    assert mod_file.name == "__init__.py", (
        f"services must resolve as a package (services/__init__.py), "
        f"not as the legacy module file (services.py). Got: {mod_file}"
    )


def test_services_has_all_public_names():
    """Every public name MUST be importable from the services package."""
    mod = import_module("custom_components.ev_trip_planner.services")

    for name in ALL_PUBLIC_NAMES:
        assert hasattr(mod, name), (
            f"services package must export '{name}' "
            f"(expected {len(ALL_PUBLIC_NAMES)} names, missing {name})"
        )


def test_register_services_is_callable():
    """register_services must be callable (it's a function)."""
    mod = import_module("custom_components.ev_trip_planner.services")
    assert callable(mod.register_services), "register_services must be callable"


def test_build_presence_config_is_callable():
    """build_presence_config must be callable (it's a function)."""
    mod = import_module("custom_components.ev_trip_planner.services")
    assert callable(mod.build_presence_config), "build_presence_config must be callable"


def test_platforms_is_list():
    """PLATFORMS must be a list of Platform enum values."""
    mod = import_module("custom_components.ev_trip_planner.services")
    assert isinstance(mod.PLATFORMS, list), (
        f"PLATFORMS must be a list, got {type(mod.PLATFORMS)}"
    )
