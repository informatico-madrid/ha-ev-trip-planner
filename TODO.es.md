# TODO / BACKLOG — EV Trip Planner

> **Última actualización**: 2026-04-09  
> **Versión actual**: 0.4.1-dev (rama `feat/solid-refactor-coverage`)  
> Este fichero refleja el estado real del proyecto. Para el plan detallado de cada milestone, ver los docs en `docs/`.

---

## ✅ Completado

### Milestone 0 — Fundación del Proyecto
- Estructura de repositorio, config flow inicial, HACS metadata, licencia MIT

### Milestone 1 — Infraestructura Core
- Trip manager (recurrentes + puntuales), servicios CRUD, sensores básicos, dashboard base
- TDD aplicado: 83% cobertura, 29 tests

### Milestone 2 — Cálculos de Viaje
- Sensores: `next_trip`, `next_deadline`, `kwh_today`, `hours_today`
- Expansión de viajes recurrentes (7 días), manejo de timezone, combinación recurrentes + puntuales

### Milestone 3 — Integración EMHASS & Control Inteligente (v0.3.0-dev, dic 2025)
- `emhass_adapter.py`: asignación dinámica de índices por viaje (pool 0-49), persistencia en HA Storage
- `vehicle_controller.py`: patrón estrategia (Switch / Service / Script / External)
- `schedule_monitor.py`: monitorización de schedules EMHASS en tiempo real
- `presence_monitor.py`: detección por sensor o coordenadas (Haversine), lógica de seguridad pre-acción
- 156 tests, 93.6% passing

### Milestone 3.1 — Mejoras UX de Configuración (v0.3.1-dev, dic 2025)
- Filtros de entidades en config flow (SOC→battery class, Plugged→binary_sensor...)
- Textos de ayuda con ejemplos concretos en todos los campos
- Traducciones completas al español

### Milestone 3.2 — Configuración Avanzada (v0.4.0-dev, mar 2026)
- Capacidad de batería dinámica (sensor directo / SOH% + nominal / manual)
- Perfiles de consumo por tipo de viaje (urbano / autopista / mixto)
- Auto-limpieza de viajes puntuales pasados (configurable)
- Config flow completo de 5 pasos
- 398 tests, 85%+ cobertura

### Milestone 4 — Perfil de Carga Inteligente (completado, mar 2026)
- Sensor `sensor.{vehicle}_power_profile`: array 168 valores (24h × 7d) en Watts
- Atributo `deferrables_schedule` con timestamps ISO 8601
- Estrategia binaria SOC-aware: 0W = sin carga, valor positivo = potencia de carga
- Dashboard auto-import (full + simple) al completar config flow
- Retry logic: 3 intentos en ventana de 5 minutos

### Refactorización SOLID (rama actual, abr 2026)
- `protocols.py`: interfaces formales para desacoplar dependencias
- `definitions.py`: entidades y tipos centralizados
- `coordinator.py`: desacoplado mediante inyección de dependencias
- `diagnostics.py`: soporte de diagnóstico para HACS quality scale
- Objetivo: cobertura >80% en todos los módulos post-refactor

---

## 🔄 En Curso

- [ ] Alcanzar cobertura >80% en todos los módulos tras la refactorización SOLID
- [ ] Corregir tests que fallaban por cambio de interfaces tras refactor
- [ ] Revisar y consolidar documentación (ROADMAP, README, docs/)

---

## 📌 Backlog — Milestone 4.1 (no iniciado)

> Plan detallado en [`docs/MILESTONE_4_1_PLANNING.md`](docs/MILESTONE_4_1_PLANNING.md)

- [ ] **Carga distribuida inteligente** (HIGH): distribuir carga en horas baratas (integración precios EMHASS)
- [ ] **Soporte multi-vehículo** (HIGH): balanceo con límite de potencia del hogar configurable
- [ ] **Ajuste climático** (MEDIUM): ajustar kWh por temperatura exterior (+20% frío, +10% calor)
- [ ] **UI de perfil de carga** (MEDIUM): gráfico Lovelace con horas activas y precio por hora
- [ ] **Notificaciones proactivas** (MEDIUM): recordatorio pre-carga, alerta carga incompleta, resumen semanal
- [ ] **Modo salud de batería** (LOW): límite SOC diario configurable, preferencia carga lenta

---

## 🔮 Futuro (post v1.0)

- [ ] Normalización de input (días con/sin tilde, slugs de vehículo)
- [ ] Origen-destino por dirección / coordenadas (geocoding API)
- [ ] Interfaz conversacional / voz (HA Assist)
- [ ] Integración con calendario HA (mostrar viajes como eventos)
- [ ] Estadísticas e historial de consumo
- [ ] Soporte para otros optimizadores (no solo EMHASS)
- [ ] Gestión de flota multi-usuario

---

## ⚠️ Limitaciones Conocidas (activas)

| Limitación | Impacto | Workaround |
|---|---|---|
| Configuración EMHASS manual requerida | Menos plug-and-play | El README incluye snippet de configuración |
| Horizonte de planificación fijo (7 días por defecto) | No se adapta dinámicamente | El usuario puede ajustarlo en config |
| Máximo 50 índices simultáneos (pool EMHASS) | Límite práctico de viajes activos | Suficiente para uso doméstico |
| Control multi-vehículo sin balanceo de potencia | Puede sobrecargar instalación | Pendiente en M4.1 |

---

## ☠️ Obsoleto / Ya no aplica

- **Migración desde sliders** (`import_from_sliders`): La migración es opcional y solo relevante para usuarios con configuración pre-M3. Usuarios nuevos usan directamente el config flow.
- **Validación manual 48h**: Superada por la suite de 793 tests automáticos + CI/CD.
- **Selección de tipo de vehículo (híbrido/eléctrico)**: Eliminado del config flow en v0.4.1-dev por irrelevante.

---

## 🔧 Notas de Proceso (uso interno)

### Agente Goose — Truncación de Output

**Síntoma**: Al usar `RALPH_AGENT=claude`, el log solo muestra la respuesta final (`TASK_COMPLETE`), no el razonamiento completo.

**Causa**: El modelo vLLM (qwen3-5-35b-a3b-nvfp4) trunca la respuesta. El prompt completo se envía correctamente pero el output queda limitado por el tokenizador.

**Workaround**: Usar Claude para tareas complejas donde el razonamiento importa. Goose es adecuado para tareas simples donde solo importa el resultado final.
