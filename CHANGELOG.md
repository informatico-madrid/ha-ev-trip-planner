# Changelog - EV Trip Planner

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0-dev] - 2025-11-22

### Added
- 4 sensores de cálculo: next_trip, next_deadline, kwh_today, hours_today
- Lógica de expansión de viajes recurrentes para 7 días
- Combinación de viajes recurrentes y puntuales
- Manejo completo de timezone con zoneinfo
- Cobertura de tests: 84% (60/60 tests pasando)

### Changed
- Actualizado ROADMAP.md para reflejar Milestone 2 completado
- Versión en manifest.json: 0.1.0-dev → 0.2.0-dev

### Fixed
- Timezone mismatch en cálculos de viajes
- Issues con async/threadsafe en sensores

## [0.1.0-dev] - 2025-11-18

### Added
- Estructura inicial del proyecto
- Config flow para configuración de vehículos
- Sistema de gestión de viajes (recurrentes y puntuales)
- 3 sensores básicos (trips_list, recurring_count, punctual_count)
- Dashboard Lovelace de ejemplo

### Changed
- Migración de input_text a Storage API

### Fixed
- Issues iniciales de setup y configuración
