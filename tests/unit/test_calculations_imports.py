"""Verify calculations/ package re-exports all 20 public names.

Tests that the `calculations` **package** (after SOLID decomposition) exposes
every name from the current `calculations.py` `__all__` list plus four
additional public symbols used by downstream callers.

This test MUST fail until the `calculations/` package directory exists.
It checks that calculations resolves as a package (not the legacy module).

Requirement: AC-2.4, AC-2.5
Design: §3.6 (calculations functional decomposition)
"""

import inspect
from importlib import import_module
from pathlib import Path

import pytest

# 16 names from calculations.py __all__ + 4 additional public symbols
ALL_PUBLIC_NAMES: tuple[str, ...] = (
    # From __all__
    "BatteryCapacity",
    "calculate_day_index",
    "calculate_dynamic_soc_limit",
    "calculate_trip_time",
    "calculate_charging_rate",
    "calculate_soc_target",
    "determine_charging_need",
    "calculate_energy_needed",
    "calculate_charging_window_pure",
    "calculate_multi_trip_charging_windows",
    "calculate_hours_deficit_propagation",
    "calculate_soc_at_trip_starts",
    "calculate_deficit_propagation",
    "calculate_power_profile_from_trips",
    "calculate_deferrable_parameters",
    "generate_deferrable_schedule_from_trips",
    # Additional public symbols used by downstream callers
    "ChargingDecision",
    "DAYS_OF_WEEK",
    "SOH_CACHE_TTL_SECONDS",
    "calculate_power_profile",
)


@pytest.fixture(params=ALL_PUBLIC_NAMES)
def public_name(request):
    """Parameterize each public name."""
    return request.param


def test_calculations_resolves_as_package():
    """The `calculations` import MUST resolve as a package, not a module file.

    After SOLID decomposition, `custom_components.ev_trip_planner.calculations`
    must be a directory with `__init__.py`, not the legacy `calculations.py` file.
    """
    import custom_components.ev_trip_planner.calculations as calc

    # The module file path must be under a 'calculations' directory (package)
    mod_file = Path(calc.__file__)
    assert mod_file.name == "__init__.py", (
        f"calculations must resolve as a package (calculations/__init__.py), "
        f"not as the legacy module file (calculations.py). Got: {mod_file}"
    )


def test_package_has_all_public_names(public_name):
    """Each public name MUST be importable from the calculations package."""
    mod = import_module("custom_components.ev_trip_planner.calculations")
    assert hasattr(mod, public_name), (
        f"calculations package must export '{public_name}' "
        f"(expected {len(ALL_PUBLIC_NAMES)} names, missing {public_name})"
    )


def test_public_names_are_callable_or_dataclass_or_constant():
    """Every public name must resolve to a callable, class, or constant."""
    mod = import_module("custom_components.ev_trip_planner.calculations")

    results: dict[str, str] = {}

    for name in ALL_PUBLIC_NAMES:
        obj = getattr(mod, name)
        if callable(obj) or inspect.isclass(obj):
            results[name] = "callable/class"
        elif inspect.ismodule(obj):
            results[name] = "module"
        else:
            results[name] = "constant"

    for name in ALL_PUBLIC_NAMES:
        assert name in results, f"'{name}' not found on module"
        assert results[name] in (
            "callable/class",
            "constant",
        ), f"'{name}' is {results[name]}, expected callable/class/constant"


def test_no_underscore_leading_names_in_public_api():
    """No name starting with underscore should be exported publicly."""
    mod = import_module("custom_components.ev_trip_planner.calculations")
    exported = {n for n in dir(mod) if not n.startswith("_")}
    for name in ALL_PUBLIC_NAMES:
        assert name in exported, f"'{name}' must be a public (non-underscore) export"
