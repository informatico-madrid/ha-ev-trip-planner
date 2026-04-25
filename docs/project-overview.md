# Project Overview: HA EV Trip Planner

> Generated: 2026-04-16 | Scan Level: Deep | Mode: Initial Scan

## Executive Summary

**HA EV Trip Planner** is a Home Assistant custom component that enables electric vehicle owners to plan trips, optimize charging schedules, and integrate with EMHASS (Energy Management for Home Assistant) for intelligent energy optimization. The component supports recurring weekly trips (e.g., daily commute) and one-time punctual trips, automatically calculating energy requirements and generating charging profiles.

## Project Identity

| Attribute | Value |
|-----------|-------|
| **Name** | EV Trip Planner for Home Assistant |
| **Domain** | `ev_trip_planner` |
| **Version** | 0.5.20 (integration) / 1.0.2 (package) |
| **License** | MIT |
| **HACS Compatible** | Yes |
| **Minimum HA Version** | 2026.3.3 |
| **Author** | @informatico-madrid |
| **Repository Type** | Monolith |

## Tech Stack Summary

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Backend Language** | Python | 3.11+ / 3.14 | Core integration logic |
| **Frontend Framework** | Lit | 2.8.x | Web Component panel UI |
| **Testing (Unit)** | pytest + Jest | pytest (latest) / Jest 30 | Python unit tests + JS tests |
| **Testing (E2E)** | Playwright | 1.58+ | End-to-end browser tests |
| **Linting** | ruff + pylint + mypy | Latest | Python code quality |
| **Formatting** | black + isort | Latest | Python code formatting |
| **Type Checking** | mypy | Latest (strict) | Static type analysis |
| **Package Manager** | npm + pip | Latest | JS and Python dependencies |
| **Containerization** | Docker | docker-compose | HA test environment |
| **Localization** | JSON (es, en) | - | Spanish + English translations |

## Architecture Type

**Plugin/Extension Architecture** — Home Assistant Custom Component with:

- **DataUpdateCoordinator pattern** — 30-second polling cycle via HA's coordinator framework
- **Config Flow** — Multi-step setup wizard for vehicle configuration
- **Service-based API** — 9+ HA services for trip CRUD and control
- **Sensor entities** — 7+ sensors per vehicle with CoordinatorEntity pattern
- **Native Panel** — Custom sidebar panel using Lit web components
- **Lovelace Dashboard** — Auto-deployed YAML dashboards per vehicle
- **Protocol-based DI** — `TripStorageProtocol` and `EMHASSPublisherProtocol` for testability

## Key Features by Milestone

| Milestone | Status | Features |
|-----------|--------|----------|
| **M2 - Trip Management** | ✅ Complete | Recurring + punctual trips, 7 sensors, dashboard |
| **M3 - EMHASS Integration** | ✅ Complete | Deferrable loads, vehicle control (4 strategies), presence detection, notifications |
| **M4 - Power Profile** | ✅ Complete | Binary charging profile, SOC-aware calculations, time alerts, 168h planning |
| **M4.1 - Enhancements** | 🚧 In Progress | Distributed charging, multi-vehicle, weather prediction, UI improvements |

## Repository Structure

```
ha-ev-trip-planner/
├── custom_components/ev_trip_planner/   # Main integration code
├── tests/                                # Python unit tests
├── tests/e2e/                            # Playwright E2E tests
├── docs/                                 # Project documentation
├── specs/                                # Specification and planning docs
├── scripts/                              # Development scripts
├── automations/                          # HA automation templates
└── design-artifacts/                     # UX/design documentation
```

## Links to Detailed Documentation

- [Architecture](./architecture.md)
- [Source Tree Analysis](./source-tree-analysis.md)
- [API Contracts (Services)](./api-contracts.md)
- [Data Models](./data-models.md)
- [Development Guide](./development-guide.md)
