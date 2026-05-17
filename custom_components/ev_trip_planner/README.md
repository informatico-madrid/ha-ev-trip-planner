# EV Trip Planner Integration

Este componente gestiona planes de viaje para vehículos eléctricos con optimización de carga basada en EMHASS.

## Estructura de archivos (Post-SOLID Refactoring)

El componente ha sido refactorizado de 9 god-class modules (12,400+ LOC) a 9 SOLID-compliant packages:

### Paquetes principales

- **`emhass/`**: Adaptador para integración con EMHASS (Facade + Composition)
  - `adapter.py` — Adaptador principal
  - `index_manager.py` — Gestión de pool de índices (0-49)
  - `load_publisher.py` — Publicación de cargas deferrables
  - `error_handler.py` — Manejo de errores

- **`trip/`**: Lógica central de gestión de viajes (Facade + Mixins)
  - `manager.py` — Manager principal
  - `_crud_mixin.py` — Operaciones CRUD
  - `_soc_mixin.py` — Cálculos SOC
  - `_power_profile_mixin.py` — Generación de perfiles de potencia
  - `_schedule_mixin.py` — Programación de cargas deferrables

- **`calculations/`**: Funciones puras de cálculo (Functional Decomposition)
  - `windows.py` — Cálculo de ventanas de carga
  - `soc.py` — Cálculos SOC
  - `deferrable.py` — Lógica de horas deferrables
  - `battery.py` — Capacidad de batería (SOH-aware)

- **`services/`**: Handlers de servicios (Module Facade)
  - `_handler_factories.py` — Factorías de handlers
  - `handlers.py` — Handlers de servicios
  - `cleanup.py` — Operaciones de limpieza

- **`dashboard/`**: Carga de templates (Facade + Builder)
  - `template_manager.py` — Carga de templates
  - `_paths.py` — Resolución de paths

- **`vehicle/`**: Control de estado del vehículo (Strategy Pattern)
  - `strategies.py` — Estrategias: Switch, Service, Script, External

- **`sensor/`**: Entidades de sensores
  - `entities.py` — Entidades de sensores para el tablero

- **`config_flow/`**: Flujo de configuración para añadir vehículos
  - `steps.py` — Pasos del flujo de configuración

- **`presence_monitor/`**: Monitoreo de presencia del vehículo
  - `schedule_monitor.py` — Gestión de horarios de recarga

### Archivos de entrada (No refactorizados)

- **`__init__.py`**: Punto de entrada principal del componente
- **`const.py`**: Constantes y definiciones de tipos
- **`coordinator.py`**: Coordinador de datos
- **`definitions.py`**: Definiciones de entidades
- **`diagnostics.py`**: Soporte de diagnósticos HA
- **`panel.py`**: Panel de UI personalizado
- **`utils.py`**: Utilidades
- **`yaml_trip_storage.py`**: Almacenamiento YAML opcional

## Dependencias clave
- EMHASS (para planificación energética)
- Home Assistant 2026 (requiere Python 3.13+)
- Spanish localization (via strings.json)

## Métricas de calidad post-refactor

| Métrica | Antes | Después |
|---------|-------|----------|
| SOLID Compliance | 3/5 FAIL | 5/5 PASS |
| God Classes | 4 | 0 |
| Mutation Kill Rate | 48.9% | 62.5% |
| Pyright Errors | 1 | 0 |

Para más detalles sobre la arquitectura, ver [`docs/architecture.md`](docs/architecture.md).