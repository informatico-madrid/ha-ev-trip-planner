# Implementation Plan: Panel de Control de Vehículo con CRUD de Viajes

**Branch**: `019-panel-vehicle-crud` | **Date**: 2026-03-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/019-panel-vehicle-crud/spec.md`

## Summary

Este plan implementa las siguientes features para EV Trip Planner:
1. Corregir error "Cannot render - no vehicle_id" en el panel nativo
2. Nombre de dispositivo personalizado con slug basado en el nombre del vehículo
3. Incluir dispositivos assist_satellite en selector de notificaciones del config flow
4. Panel dependiente del vehículo - eliminación automática al eliminar vehículo
5. Panel dependiente del vehículo - actualización automática de sensores
6. Panel muestra todos los sensores del vehículo
7. Panel muestra los viajes en formato legible
8. Panel incluye operaciones CRUD de viajes
9. UI del panel ordenada y bonita

**Enfoque técnico**: Modificar panel.js para corregir el timing de vehicle_id, actualizar config_flow.py para agregar domain "assist_satellite", modificar sensor.py para usar el nombre personalizado del vehículo, y expandir panel.js para mostrar viajes con operaciones CRUD.

## Technical Context

**Language/Version**: Python 3.11+, JavaScript (panel.js)  
**Primary Dependencies**: Home Assistant Core 2026, voluptuous, panel_custom  
**Storage**: YAML files in config_dir/ev_trip_planner/  
**Testing**: pytest, Playwright para verificación E2E  
**Target Platform**: Home Assistant Container (Linux)  
**Project Type**: Home Assistant Custom Component  
**Performance Goals**: N/A (componente de integración)  
**Constraints**: Debe funcionar en Home Assistant Container sin supervisor  
**Scale/Scope**: Múltiples vehículos por instancia de HA

## Constitution Check

| Gate | Status | Notes |
|------|--------|-------|
| Code Style (88 chars, type hints, docstrings) | ✅ PASS | Se seguirá el estándar del proyecto |
| Testing (>80% coverage) | ✅ PASS | pytest disponible |
| Documentation (Conventional Commits) | ✅ PASS | Se seguirá el formato |

## Available Tools for Verification

| Tool | Type | Status | Purpose |
|------|------|--------|---------|
| homeassistant-ops | skill | installed | Operar HA via REST/WebSocket APIs |
| homeassistant-skill | skill | installed | Controlar dispositivos HA |
| homeassistant-config | skill | installed | Crear/modificar YAML de HA |
| homeassistant-dashboard-designer | skill | installed | Diseño de Lovelace dashboards |
| homeassistant-best-practices | skill | installed | Mejores prácticas HA |
| playwright-best-practices | skill | installed | E2E testing con Playwright |
| e2e-testing-patterns | skill | installed | Patrones de testing E2E |
| python-testing-patterns | skill | installed | Testing con pytest |
| python-security-scanner | skill | installed | Seguridad Python |
| mcp--shell--shell_exec | MCP | available | Ejecutar comandos shell |
| mcp--playwright--browser_navigate | MCP | available | Navegación web |
| mcp--playwright--browser_snapshot | MCP | available | Snapshot de página |
| mcp--playwright--browser_click | MCP | available | Click en elementos |

## Project Structure

### Documentation (this feature)

```
specs/019-panel-vehicle-crud/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md       # Phase 1 output
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md            # Phase 2 output
```

### Source Code (repository root)

```
custom_components/ev_trip_planner/
├── __init__.py              # Servicios CRUD de viajes (ya existen)
├── config_flow.py            # Config flow - AGREGAR assist_satellite
├── sensor.py                # Sensores - MODIFICAR device_info para nombre personalizado
├── panel.py                 # Registro de paneles - MODIFICAR cleanup
├── frontend/
│   ├── panel.js             # Panel web - CORREGIR vehicle_id Y AGREGAR viajes+CRUD
│   └── panel.css             # Estilos del panel
├── dashboard/                # Dashboards Lovelace
└── const.py                 # Constantes
```

**Estructura Decision**: Proyecto existente de Home Assistant Custom Component. Se modifican archivos existentes para agregar las nuevas funcionalidades.

## State Verification Plan

### ⚠️ IMPORTANT: Only 3 Verification Types (CLOSED set)

| Verification Type | When to Use | Example Command |
|------------------|-------------|-----------------|
| `[VERIFY:TEST]` | Unit/integration tests (pytest) | `pytest tests/test_panel.py -v` |
| `[VERIFY:API]` | REST API verification (use homeassistant-ops skill) | `curl http://HA/api/states` |
| `[VERIFY:BROWSER]` | Playwright UI automation | Navegar y verificar contenido |

### Existence Check

- **Componente desplegado**: Verificar que ev_trip_planner aparece en /api/components
- **Entidades creadas**: Verificar sensores con `sensor.ev_trip_planner_{vehicle_id}_*`
- **Dispositivo creado**: Verificar en /api/devices que existe con nombre "EV Trip Planner {nombre}"
- **Panel registrado**: Verificar en frontend registries

### Effect Check

- **Panel sin error**: Navegar a /ev-trip-planner-{vehicle_id} y verificar que NO aparece "Cannot render - no vehicle_id"
- **Dispositivo con nombre correcto**: Verificar que el nombre del dispositivo es "EV Trip Planner {nombre}"
- **Selector assist_satellite**: En config flow step notifications, verificar que aparecen entidades assist_satellite
- **Panel eliminado al borrar vehículo**: Eliminar vehículo y verificar que panel ya no existe
- **Viajes mostrados**: En panel, verificar que aparecen viajes programados
- **CRUD funcional**: Crear/editar/eliminar viaje desde panel y verificar cambios

## Complexity Tracking

No hay violaciones de constitución que requieran justificación adicional.

---

## Phase 0: Research

### Research Findings

**Hallazgo 1: Error "Cannot render - no vehicle_id"**
- **Ubicación**: `custom_components/ev_trip_planner/frontend/panel.js`
- **Causa**: El panel intenta obtener vehicle_id de la URL en connectedCallback y hass setter, pero hay timing issue - el config se pasa después
- **Solución**: Asegurar que el config con vehicle_id esté disponible antes del render, o leer vehicle_id de la URL de forma más robusta

**Hallazgo 2: Dispositivo con nombre incorrecto**
- **Ubicación**: `custom_components/ev_trip_planner/sensor.py` - método `device_info`
- **Causa**: Usa `self.trip_manager.vehicle_id` (slug interno) en lugar del nombre personalizado
- **Solución**: Modificar device_info para usar el nombre del vehículo guardado en la configuración

**Hallazgo 3: assist_satellite no aparece en selector**
- **Ubicación**: `custom_components/ev_trip_planner/config_flow.py` - STEP_NOTIFICATIONS_SCHEMA
- **Causa**: Usa `domain="notify"` pero assist_satellite es un dominio diferente
- **Solución**: Agregar dominio "assist_satellite" al selector o usar múltiples dominios

**Hallazgo 4: Panel no se elimina al borrar vehículo**
- **Ubicación**: `custom_components/ev_trip_planner/__init__.py` - async_unload_entry
- **Causa**: Llama a async_unregister_panel pero el cleanup puede no ser completo
- **Solución**: Verificar que la eliminación del panel ocurre correctamente

### Deployment Methods

1. **Para error vehicle_id**: Modificar panel.js para leer vehicle_id de window.location.pathname ANTES de esperar hass
2. **Para nombre dispositivo**: Extraer vehicle_name de entry.data y pasar al sensor
3. **Para assist_satellite**: Modificar EntitySelector para incluir domain=["notify", "assist_satellite"]
4. **Para panel CRUD**: Expandir panel.js con formulario y lista de viajes usando servicios HA existentes
