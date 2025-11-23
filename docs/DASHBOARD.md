# Dashboard de EV Trip Planner

Este archivo describe el dashboard completo para visualizar y gestionar los viajes de EV Trip Planner.

> **Estado:** Dashboard completado en Fase 1D - listo para usar cuando se integren los sensores en HA.

## Archivo de dashboard

- **Ubicación:** `custom_components/ev_trip_planner/dashboard/dashboard.yaml`
- **Contenido:**
  - 📊 **Estado general**: Resumen de viajes totales y contadores
  - 📅 **Grid semanal**: Vista organizada por días (lun-dom) de viajes recurrentes con hora, km y kWh
  - 🎯 **Viajes puntuales**: Lista ordenada por fecha con iconos de estado (⏳/✅/❌)
  - 🚗 **Estado del vehículo**: Placeholder para cálculos de Fase 2 (próximo viaje, kWh necesarios)
  - 📈 **Contadores detallados**: Tarjeta de entidades con iconos

## Características del dashboard

### Grid semanal
- Agrupa viajes recurrentes por día de la semana
- Muestra hora, distancia y energía necesaria
- Indica visualmente viajes pausados
- Borde de color primario para destacar

### Lista de puntuales
- Ordenados cronológicamente por fecha/hora
- Iconos de estado: ⏳ pendiente, ✅ completado, ❌ cancelado
- Formato de fecha legible (dd/mm/yyyy hh:mm)
- Borde de color acento

### Estilos
- Uso de `card-mod` para bordes coloridos
- Iconos consistentes (mdi)
- Placeholders claros para funcionalidad futura

## Importación en Lovelace

1. Ir a **Interfaz de Usuario** → **Editor de panel** → Menu (⋮) → **Editar panel**
2. Añadir vista nueva o editar existente
3. Copiar contenido de `dashboard/dashboard.yaml`
4. Ajustar `entity_id` según tu vehículo:
   - `sensor.chispitas_trips_list` → `sensor.{tu_vehiculo}_trips_list`
   - etc.

## Entity IDs esperados

Los sensores se registran con patrón `{entry_id}_*`:
- `sensor.{vehicle}_trips_list` (valor: total, atributo: `trips`)
- `sensor.{vehicle}_recurring_trips_count`
- `sensor.{vehicle}_punctual_trips_count`

## Notas técnicas

- Template Jinja2 para filtrado y formato
- Compatible con `card-mod` (opcional, mejora visual)
- Diseñado para español pero fácilmente traducible
- Preparado para Fase 2 (cálculos automáticos)
