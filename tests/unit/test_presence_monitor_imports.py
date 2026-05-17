"""Test that presence_monitor package re-exports PresenceMonitor."""

from __future__ import annotations


def test_presence_monitor_package_re_exports():
    """PresenceMonitor must be importable from the presence_monitor package.

    The presence_monitor/ package (with __init__.py) must re-export the
    PresenceMonitor class so that existing import paths continue to work
    after the god-class split.
    """
    from custom_components.ev_trip_planner.presence_monitor import PresenceMonitor

    assert PresenceMonitor is not None
    # Verify it comes from a package (__init__.py), not a module file
    import custom_components.ev_trip_planner.presence_monitor as pm_mod

    assert hasattr(pm_mod, "__path__"), (
        "presence_monitor must be a package (directory with __init__.py), "
        "not a single .py module file"
    )
