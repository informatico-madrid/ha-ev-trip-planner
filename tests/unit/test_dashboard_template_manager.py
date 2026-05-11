"""Test that dashboard.template_manager module exists with template I/O functions.

VERIFIES: After dashboard.py split, template I/O functions are importable
from `custom_components.ev_trip_planner.dashboard.template_manager`.

Expected functions (moved from dashboard.py private helpers):
  - load_template       (_load_dashboard_template)
  - save_lovelace_dashboard (_save_lovelace_dashboard)
  - save_yaml_fallback  (_save_dashboard_yaml_fallback)
  - validate_config     (_validate_dashboard_config)
  - verify_storage_permissions (_verify_storage_permissions)
"""

import pytest  # noqa: F401


def test_load_template_importable():
    """load_template must be importable from dashboard.template_manager."""
    from custom_components.ev_trip_planner.dashboard.template_manager import (
        load_template,
    )

    assert callable(load_template)


def test_save_lovelace_dashboard_importable():
    """save_lovelace_dashboard must be importable from dashboard.template_manager."""
    from custom_components.ev_trip_planner.dashboard.template_manager import (
        save_lovelace_dashboard,
    )

    assert callable(save_lovelace_dashboard)


def test_save_yaml_fallback_importable():
    """save_yaml_fallback must be importable from dashboard.template_manager."""
    from custom_components.ev_trip_planner.dashboard.template_manager import (
        save_yaml_fallback,
    )

    assert callable(save_yaml_fallback)


def test_validate_config_importable():
    """validate_config must be importable from dashboard.template_manager."""
    from custom_components.ev_trip_planner.dashboard.template_manager import (
        validate_config,
    )

    assert callable(validate_config)


def test_verify_storage_permissions_importable():
    """verify_storage_permissions must be importable from dashboard.template_manager."""
    from custom_components.ev_trip_planner.dashboard.template_manager import (
        verify_storage_permissions,
    )

    assert callable(verify_storage_permissions)


def test_all_five_functions_exist():
    """All 5 template I/O functions must be importable in a single import."""
    from custom_components.ev_trip_planner.dashboard.template_manager import (
        load_template,
        save_lovelace_dashboard,
        save_yaml_fallback,
        validate_config,
        verify_storage_permissions,
    )

    assert all(
        callable(fn)
        for fn in [
            load_template,
            save_lovelace_dashboard,
            save_yaml_fallback,
            validate_config,
            verify_storage_permissions,
        ]
    )
