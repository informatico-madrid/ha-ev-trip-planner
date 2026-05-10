"""Transitional shim — import everything from the calculations/ package.

The legacy calculations.py module file has been decomposed into the
calculations/ package (with sub-modules for each functional area).
This shim preserves the old import path so that existing callers
that `from custom_components.ev_trip_planner.calculations import X`
continue to work without changes.

Note: the calculations/ package directory takes precedence over this
module file during import resolution. This file is retained as documentation
of the transitional shim intent.
"""

from __future__ import annotations
