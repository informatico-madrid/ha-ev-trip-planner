# AI Context - EV Trip Planner

Documentation for AI agents working on this codebase.

## Structure

- `_ai/` - AI-dense documentation (complex, technical, context-heavy)
- `docs/` - Human-readable documentation (concise, explanatory)
- `plans/` - Active development plans and proposals
- `specs/` - Implemented specifications

## AI Documents

| Document | Purpose |
|----------|---------|
| `ai-development-lab.md` | AI development methodology and workflow |
| `TDD_METHODOLOGY.md` | Test-driven development approach |
| `TESTING_E2E.md` | End-to-end testing framework |
| `CODEGUIDELINESia.md` | Coding standards for AI generation |
| `IMPLEMENTATION_REVIEW.md` | Comprehensive implementation analysis |
| `RALPH_METHODOLOGY.md` | Smart Ralph AI-assisted workflow |
| `SPECKIT_SDD_FLOW_INTEGRATION_MAP.md` | Speckit integration architecture |
| `charging-planning-functional-analysis.md` | SOC-aware charging analysis |
| `PORTFOLIO.md` | AI orchestration portfolio |

## Quick Reference

- **Version**: 0.5.20
- **Platform**: Home Assistant custom component
- **Key Features**: Trip planning, EMHASS integration, smart charging
- **Config Flow**: 5-step wizard
- **Vehicle Control Types**: Switch, Service, Script, External

## Critical Paths

- `custom_components/ev_trip_planner/__init__.py` - Entry point
- `custom_components/ev_trip_planner/services.py` - Service handlers (1592 lines)
- `custom_components/ev_trip_planner/emhass_adapter.py` - EMHASS integration
- `custom_components/ev_trip_planner/trip_manager.py` - Trip management
- `custom_components/ev_trip_planner/vehicle_controller.py` - Vehicle control

## Known Gaps

- `schedule_monitor.py` exists but NOT connected (never imported)
- SOH (State of Health) not implemented in UI
- Vehicle controller not fully tested end-to-end