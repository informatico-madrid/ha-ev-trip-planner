"""RED test: sensor/ package must re-export HA platform entities.

This test asserts that the sensor/ package exists and re-exports the
same public API as the legacy sensor.py module file, ensuring backward-
compatible imports for downstream consumers (__init__.py, coordinator.py,
services.py, config_flow.py).

NOTE: sys.modules manipulation (del/pop) must NOT be used here — it creates
duplicate module objects under --import-mode=importlib, breaking monkeypatch
in other tests. All assertions are made against the already-imported module.
"""

from __future__ import annotations

import custom_components.ev_trip_planner.sensor as _sensor_pkg


def test_sensor_package_resolves_as_package_not_module() -> None:
    """Verify sensor resolves as a package directory, not sensor.py shim."""
    assert hasattr(_sensor_pkg, "__path__"), (
        "sensor must resolve as a package (directory with __init__.py), "
        "not as the legacy sensor.py module file"
    )


def test_async_setup_entry_importable() -> None:
    """async_setup_entry is importable from sensor package."""
    assert hasattr(_sensor_pkg, "async_setup_entry")


def test_trip_planner_sensor_importable() -> None:
    """TripPlannerSensor Entity is importable from sensor package."""
    assert hasattr(_sensor_pkg, "TripPlannerSensor")


def test_emhass_deferrable_load_sensor_importable() -> None:
    """EmhassDeferrableLoadSensor Entity is importable from sensor package."""
    assert hasattr(_sensor_pkg, "EmhassDeferrableLoadSensor")


def test_trip_sensor_importable() -> None:
    """TripSensor Entity is importable from sensor package."""
    assert hasattr(_sensor_pkg, "TripSensor")


def test_trip_emhass_sensor_importable() -> None:
    """TripEmhassSensor Entity is importable from sensor package."""
    assert hasattr(_sensor_pkg, "TripEmhassSensor")
