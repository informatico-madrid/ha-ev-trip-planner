# Project Documentation Index

> **Last Updated:** 2026-04-23 | **Scan Level:** Deep | **Mode:** Full Rescan with AI Lab Context
> **Project Type:** HYBRID — Real Home Assistant Utility + AI Development Laboratory

## Project Overview

- **Name:** HA EV Trip Planner
- **Type:** HYBRID — Home Assistant Custom Component (Backend Python + Frontend Lit) + AI Development Laboratory
- **Primary Language:** Python 3.11+ (backend), TypeScript/JavaScript (frontend)
- **Architecture:** Plugin/Extension with DataUpdateCoordinator pattern
- **Domain:** `ev_trip_planner`
- **Version:** 0.5.1
- **Author Context:** Senior Architect (PHP/Clean Architectures specialty) — ZERO lines of human-written code

## Quick Reference

- **Tech Stack:** Python + Home Assistant Framework + Lit Web Components + Playwright
- **Entry Point:** `custom_components/ev_trip_planner/__init__.py::async_setup_entry`
- **Architecture Pattern:** Layered with Coordinator (DataUpdateCoordinator, Strategy, Protocol DI)
- **Test Framework:** pytest (unit) + Playwright (E2E)
- **Coverage Target:** 100%
- **Deployment:** HACS + Docker (Container-based HA)

## Generated Documentation

- [Project Overview](./project-overview.md) — Executive summary, tech stack, features by milestone
- [Architecture](./architecture.md) — Layered architecture, component overview, data flow, design patterns
- [Source Tree Analysis](./source-tree-analysis.md) — Annotated directory tree, critical folders, entry points
- [API Contracts](./api-contracts.md) — 9+ HA services, sensor data contract, trip data structures
- [Data Models](./data-models.md) — Storage schema, trip models, config entry data, entity registry
- [Development Guide](./development-guide.md) — Setup, commands, code style, testing, common tasks
- [AI Development Lab](./ai-development-lab.md) — Full experiment narrative, 6-phase methodology evolution, author context, hybrid project documentation
- [Portfolio](./PORTFOLIO.md) — **START HERE:** Multi-layer narrative for recruiters, contributors, and evaluators

## Existing Documentation

- [README.md](../README.md) — Main project README (Spanish) with installation and usage
- [CONTRIBUTING.md](../CONTRIBUTING.md) — Contribution guidelines
- [CHANGELOG.md](../CHANGELOG.md) — Version changelog
- [ROADMAP.md](../ROADMAP.md) — Project roadmap
- [Custom Component README](../custom_components/ev_trip_planner/README.md) — Component-specific docs
- [Dashboard Docs](./DASHBOARD.md) — Lovelace dashboard documentation
- [Vehicle Control](./VEHICLE_CONTROL.md) — Charging control strategies
- [EMHASS Setup](./emhass-setup.md) — EMHASS integration guide
- [E2E Testing](./TESTING_E2E.md) — Playwright E2E testing guide
- [TDD Methodology](./TDD_METHODOLOGY.md) — Test-driven development approach
- [User Journey BDD](./COMPLETE_USER_JOURNEY_BDD.md) — BDD user journey scenarios
- [Implementation Review](./IMPLEMENTATION_REVIEW.md) — Implementation review notes
- [Power Profile (M4)](./MILESTONE_4_POWER_PROFILE.md) — Milestone 4 power profile feature
- [M4.1 Planning](./MILESTONE_4_1_PLANNING.md) — Milestone 4.1 planning
- [Shell Command Setup](./SHELL_COMMAND_SETUP.md) — Shell command configuration
- [Ralph Methodology](./RALPH_METHODOLOGY.md) — Smart Ralph development methodology
- [Code Guidelines (AI)](./CODEGUIDELINESia.md) — AI-assisted coding guidelines
- [SpecKit Flow Map](./SPECKIT_SDD_FLOW_INTEGRATION_MAP.md) — SpecKit workflow integration
## AI Development Lab

> **Nuevo en 2026-04-23:** Documentación completa del experimento de desarrollo asistido por IA.

- [**AI Development Lab**](./ai-development-lab.md) — Resumen del experimento, trayectoria evolutiva, arquitectura del laboratorio
- [**Gaps y Problemas**](../doc/gaps/gaps.md) — 5 problemas heredados de Vive Coding con hipótesis verificables
- [**Ralph Methodology**](./RALPH_METHODOLOGY.md) — Smart Ralph fork con Phase 5: Agentic Verification Loop

### Para Recruiters y Evaluadores

1. [**Portfolio**](./PORTFOLIO.md) — Vista rápida en 2 minutos
2. [**AI Development Lab**](./ai-development-lab.md) — Laboratorio completo
3. [**Executive Summary**](../doc/gaps/EXECUTIVE_SUMMARY.md) — Gestión de deuda técnica
4. [**Ralph Methodology**](./RALPH_METHODOLOGY.md) — Metodología técnica

### Trayectoria Metodológica

| Fase | Período | Metodología | Artifacts Clave |
|------|---------|-------------|----------------|
| 1 | 2024-Q1 | Vive Coding Puro | Specs con prefijos numéricos, deuda técnica |
| 2 | 2024-Q2 | Ingeniería de Prompts | Prompts estructurados, primeras plantillas |
| 3 | 2024-Q3 | Fine-Tuning | Skills de dominio especializadas |
| 4 | 2024-Q4 | Speckit | Specs formales con checklists |
| 5 | 2025-Q1 - 2026-Q1 | Smart Ralph Fork | Phase 5 Verification, specs descriptivas |
| 6 | 2026-Q1 - Actual | BMad + Ralph | Orquestación multi-agente, sprint planning |

## Getting Started

### For Development

1. Clone the repository
2. Set up Python venv: `python -m venv .venv && source .venv/bin/activate`
3. Install deps: `pip install -r requirements_dev.txt && npm install`
4. Start HA test env: `docker compose up -d`
5. Run tests: `make test`
6. Run all checks: `make check`

### For Understanding the Architecture

1. Read [Project Overview](./project-overview.md) for the big picture
2. Read [Architecture](./architecture.md) for component relationships
3. Read [Data Models](./data-models.md) for data structures
4. Read [API Contracts](./api-contracts.md) for service interfaces

### For Adding Features

1. Read [Development Guide](./development-guide.md) for setup and conventions
2. Follow the TDD approach: write tests first in `tests/`
3. Pure calculations go in `calculations.py`, async orchestration in `trip_manager.py`
4. Use Protocol-based DI for testability

## Component Inventory

| Component | File | LOC | Purpose |
|-----------|------|-----|---------|
| TripManager | `trip_manager.py` | 1998 | Core trip CRUD + EMHASS sync |
| EMHASSAdapter | `emhass_adapter.py` | 1828 | EMHASS integration + power profiles |
| Dashboard | `dashboard.py` | 1261 | Lovelace auto-deploy |
| Calculations | `calculations.py` | 1122 | Pure calculation functions |
| Config Flow | `config_flow.py` | 949 | Multi-step setup wizard |
| Sensors | `sensor.py` | 908 | Sensor entities |
| Services | `services.py` | 1537 | HA service handlers |
| Presence Monitor | `presence_monitor.py` | 769 | GPS + sensor presence |
| Vehicle Controller | `vehicle_controller.py` | 509 | Charging control strategies |
| Utils | `utils.py` | 324 | Utility functions |
| Schedule Monitor | `schedule_monitor.py` | 323 | EMHASS schedule monitoring |
| Panel | `panel.py` | 244 | Native sidebar panel |
| Coordinator | `coordinator.py` | 155 | DataUpdateCoordinator |
| Init | `__init__.py` | 162 | Integration lifecycle |
| Definitions | `definitions.py` | 85 | Sensor entity descriptions |
| Const | `const.py` | 95 | Constants and config keys |
| Protocols | `protocols.py` | 26 | DI protocol interfaces |
| Diagnostics | `diagnostics.py` | 69 | HA diagnostics support |
| YAML Trip Storage | `yaml_trip_storage.py` | 68 | YAML storage fallback |

## Testing Inventory

| Category | Files | Framework |
|----------|-------|-----------|
| Python Unit Tests | **85** files in `tests/` | pytest |
| E2E Tests | **8** specs in `tests/e2e/` | Playwright |
| JS Tests | `tests/panel.test.js` | Jest |
| Test Fixtures | `tests/fixtures/` | JSON data |
