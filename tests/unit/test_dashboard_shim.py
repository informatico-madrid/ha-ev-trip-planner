"""Verify dashboard.py transitional shim re-exports all public + private names.

Tests that names required by existing test imports (via ~80 lazy imports)
still resolve through the dashboard package shim.

Names tested:
  Private helpers (needed by tests that patch dashboard._load_dashboard_template etc.):
    - _load_dashboard_template
    - _save_lovelace_dashboard
    - _save_dashboard_yaml_fallback
    - _validate_dashboard_config
    - _verify_storage_permissions
    - _call_async_executor_sync
    - _await_executor_result
    - _check_path_exists
    - _create_directory
    - _read_file_content
    - _write_file_content
    - DashboardConfig (type alias)

  Public names:
    - import_dashboard
    - is_lovelace_available

  Exception hierarchy:
    - DashboardError (base)
    - DashboardNotFoundError
    - DashboardStorageError
    - DashboardValidationError

    - DashboardImportResult (dataclass-like)

This test MUST fail until dashboard.py is converted to a transitional shim
that re-exports all these names for backward-compatible test imports.

Requirement: AC-2.4, AC-2.5 (import compatibility preserved)
Design: §3.4 + §4.6 (dashboard shim re-exports)
"""

from __future__ import annotations

import importlib

import pytest  # noqa: F401

# All names that existing test imports reach into
ALL_DASHBOARD_NAMES: tuple[str, ...] = (
    # Private helpers (~80 import sites in tests)
    "_load_dashboard_template",
    "_save_lovelace_dashboard",
    "_save_dashboard_yaml_fallback",
    "_validate_dashboard_config",
    "_verify_storage_permissions",
    "_call_async_executor_sync",
    "_await_executor_result",
    "_check_path_exists",
    "_create_directory",
    "_read_file_content",
    "_write_file_content",
    "DashboardConfig",
    # Public API
    "import_dashboard",
    "is_lovelace_available",
    # Exception hierarchy
    "DashboardError",
    "DashboardNotFoundError",
    "DashboardStorageError",
    "DashboardValidationError",
    # Data class
    "DashboardImportResult",
)


@pytest.fixture(params=ALL_DASHBOARD_NAMES)
def dashboard_name(request):
    """Parameterize each dashboard name."""
    return request.param


def test_dashboard_resolves_as_package():
    """Test that `dashboard` resolves as a package (directory), not just a .py file.

    After SOLID decomposition, `dashboard/` is a package directory.
    The sibling `dashboard.py` becomes a transitional shim loaded via importlib
    from `dashboard/__init__.py`.
    """
    import custom_components.ev_trip_planner.dashboard as dashboard_mod

    assert hasattr(dashboard_mod, "__path__"), (
        "dashboard must resolve as a package (have __path__)"
    )


@pytest.mark.parametrize("name", ALL_DASHBOARD_NAMES)
def test_name_imports_from_dashboard(name):
    """Test that each name can be imported from the dashboard package.

    This is the core RED test — it fails until the shim properly re-exports
    the name from the sibling dashboard.py module file.
    """
    mod = importlib.import_module("custom_components.ev_trip_planner.dashboard")
    assert hasattr(mod, name), (
        f"dashboard package must export '{name}' for backward-compatible test imports"
    )


@pytest.mark.parametrize(
    "name,expected_kind",
    [
        # Private helpers — functions
        ("_load_dashboard_template", "callable"),
        ("_save_lovelace_dashboard", "callable"),
        ("_save_dashboard_yaml_fallback", "callable"),
        ("_validate_dashboard_config", "callable"),
        ("_check_path_exists", "callable"),
        ("_create_directory", "callable"),
        ("_read_file_content", "callable"),
        ("_write_file_content", "callable"),
        # Public functions
        ("import_dashboard", "callable"),
        ("is_lovelace_available", "callable"),
        # Exception classes
        ("DashboardError", "class"),
        ("DashboardNotFoundError", "class"),
        ("DashboardStorageError", "class"),
        ("DashboardValidationError", "class"),
        # Data class
        ("DashboardImportResult", "class"),
        # Type alias / function
        ("DashboardConfig", "alias_or_callable"),
    ],
)
def test_name_kind(name, expected_kind):
    """Test that each name has the expected Python kind (callable, class, etc).

    Ensures the re-exported name is the correct type, not a stub or wrong object.
    """
    mod = importlib.import_module("custom_components.ev_trip_planner.dashboard")
    obj = getattr(mod, name)

    if expected_kind == "callable":
        assert callable(obj), f"'{name}' must be callable, got {type(obj).__name__}"

    elif expected_kind == "class":
        assert isinstance(obj, type), (
            f"'{name}' must be a class, got {type(obj).__name__}"
        )

    elif expected_kind == "alias_or_callable":
        assert callable(obj) or hasattr(obj, "__origin__"), (
            f"'{name}' must be callable or a type alias, got {type(obj).__name__}"
        )
