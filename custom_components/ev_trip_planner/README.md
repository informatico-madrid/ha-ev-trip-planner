# EV Trip Planner Integration

Este componente gestiona planes de viaje para vehículos eléctricos con optimización de carga basada en EMHASS.

## Estructura de archivos

- **config_flow.py**: Flujo de configuración para añadir vehículos
- **const.py**: Constantes y definiciones de tipos
- **emhass_adapter.py**: Adaptador para integración con EMHASS
- **__init__.py**: Punto de entrada principal del componente
- **presence_monitor.py**: Monitorea presencia del vehículo
- **schedule_monitor.py**: Gestiona horarios de recarga
- **sensor.py**: Entidades de sensores para el tablero
- **trip_manager.py**: Lógica central de gestión de viajes
- **vehicle_controller.py**: Control de estado del vehículo

## Dependencias clave
- EMHASS (para planificación energética)
- Home Assistant 2026 (requiere Python 3.13+)
- Spanish localization (via strings.json)

Nota: Todos los archivos cumplen con las reglas de tipado estricto y manejo de errores de Home Assistant 2026.