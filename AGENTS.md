# AGENTS.md

This file provides guidance to agents when working with code in this repository.

**Build/Lint/Test Commands**:
- Lint: `black custom_components/ev_trip_planner/`, `isort custom_components/ev_trip_planner/`, `pylint custom_components/ev_trip_planner/`, `mypy custom_components/ev_trip_planner/`
- Test: `pytest tests/ -v --cov=custom_components/ev_trip_planner`

**Code Style**:
- Line length: 88 characters
- Type hints: Required for all public functions
- Docstrings: Google style, required for all public functions
- Imports: Standard lib → Third party → HA → Local (use isort)
- Async: Always use `async`/`await`, no blocking calls