"""RED test: sensor/ package must re-export HA platform entities.

This test asserts that the sensor/ package exists and re-exports the
same public API as the legacy sensor.py module file, ensuring backward-
compatible imports for downstream consumers (__init__.py, coordinator.py,
services.py, config_flow.py).
"""

from __future__ import annotations

import importlib
import sys


def _clear_sensor_modules() -> None:
    """Remove any cached sensor module refs so re-imports work."""
    to_del = [
        k
        for k in sys.modules
        if k.startswith("custom_components.ev_trip_planner.sensor")
    ]
    for k in to_del:
        del sys.modules[k]


def test_sensor_package_resolves_as_package_not_module() -> None:
    """Verify sensor resolves as a package directory, not sensor.py shim."""
    _clear_sensor_modules()
    mod = importlib.import_module("custom_components.ev_trip_planner.sensor")
    assert hasattr(mod, "__path__"), (
        "sensor must resolve as a package (directory with __init__.py), "
        "not as the legacy sensor.py module file"
    )


def test_async_setup_entry_importable() -> None:
    """async_setup_entry is importable from sensor package."""
    _clear_sensor_modules()
    mod = importlib.import_module("custom_components.ev_trip_planner.sensor")
    assert hasattr(mod, "async_setup_entry")


def test_trip_planner_sensor_importable() -> None:
    """TripPlannerSensor Entity is importable from sensor package."""
    _clear_sensor_modules()
    mod = importlib.import_module("custom_components.ev_trip_planner.sensor")
    assert hasattr(mod, "TripPlannerSensor")


def test_emhass_deferrable_load_sensor_importable() -> None:
    """EmhassDeferrableLoadSensor Entity is importable from sensor package."""
    _clear_sensor_modules()
    mod = importlib.import_module("custom_components.ev_trip_planner.sensor")
    assert hasattr(mod, "EmhassDeferrableLoadSensor")


def test_trip_sensor_importable() -> None:
    """TripSensor Entity is importable from sensor package."""
    _clear_sensor_modules()
    mod = importlib.import_module("custom_components.ev_trip_planner.sensor")
    assert hasattr(mod, "TripSensor")


def test_trip_emhass_sensor_importable() -> None:
    """TripEmhassSensor Entity is importable from sensor package."""
    _clear_sensor_modules()
    mod = importlib.import_module("custom_components.ev_trip_planner.sensor")
    assert hasattr(mod, "TripEmhassSensor")
