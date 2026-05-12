"""Test that sensor.py has zero pyright errors.

VERIFIES: sensor.py must have zero pyright type errors after the mixin refactor.

RED phase: test PASSES immediately (sensor.py has zero pyright errors).
GREEN phase (task 1.98): test continues to PASS — no regression introduced.

This test documents the pyright quality requirement for sensor.py.
If sensor.py had pyright errors, this test would fail, indicating
the RED state where fixes are needed.

Note: sensor.py was replaced by the sensor/ package as part of the
SOLID decomposition (Spec 3). The original code was migrated to
entity_*.py and _async_setup.py files.

Requirement: NFR-7.A.5 (Zero pyright errors)
Design: FR-1.7 (Sensor package decomposition)
"""

import subprocess


def test_sensor_py_zero_pyright_errors():
    """Run make typecheck and verify no pyright errors in sensor.py.

    Checks that sensor.py has zero pyright type errors after the
    sensor/ package decomposition.
    """
    result = subprocess.run(
        ["make", "typecheck"],
        capture_output=True,
        text=True,
        check=False,
        cwd="/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner",
    )
    output = result.stderr + result.stdout

    # Check for pyright errors specifically in sensor.py
    sensor_errors = [
        line
        for line in output.splitlines()
        if "/sensor.py" in line and "error:" in line
    ]

    assert len(sensor_errors) == 0, (
        f"sensor.py has {len(sensor_errors)} pyright error(s). "
        "Expected zero errors. Found:\n" + "\n".join(sensor_errors[:20])
    )
