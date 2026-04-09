# 🗺️ Roadmap & Milestones - EV Trip Planner

## 📊 Estado del Proyecto

**Versión actual**: 0.4.2-dev  
**Fase de desarrollo**: Milestone 4.1 planificado — pendiente de inicio  
**Target Release**: v1.0.0 (Q2 2026)  
**Tests**: 793 Python (pytest) + 10 E2E (Playwright) pasando  

---

## ✅ Historial de Milestones Completados

### Milestone 0: Fundación del Proyecto (Nov 18, 2025)
- Estructura de repositorio y skeleton del custom component
- Config flow inicial, licencia MIT, metadata HACS
- Constantes y dominio configurados

### Milestone 1: Infraestructura Core (Nov 18, 2025)
- Sistema de gestión de viajes recurrentes y puntuales
- Servicios CRUD: `add_recurring_trip`, `add_punctual_trip`, `edit_trip`, `delete_trip`
- 3 sensores básicos: `trips_list`, `recurring_count`, `punctual_count`
- Dashboard Lovelace base
- 83% de cobertura de tests (29 tests)

### Milestone 2: Cálculos de Viaje (Nov 22, 2025)
- Sensores de cálculo: `next_trip`, `next_deadline`, `kwh_today`, `hours_today`
- Expansión de viajes recurrentes a 7 días
- Combinación de viajes recurrentes + puntuales
- Manejo completo de timezone
- 84% de cobertura (60 tests)

### Milestone 3: Integración EMHASS y Control Inteligente (Dic 8, 2025)
- `emhass_adapter.py`: publicación dinámica de cargas diferibles, pool de índices 0-49, persistencia entre reinicios
- `vehicle_controller.py`: 4 estrategias de control (Switch, Service, Script, External)
- `schedule_monitor.py`: monitorización de schedules EMHASS en tiempo real
- `presence_monitor.py`: detección de presencia por sensor y coordenadas, lógica de seguridad
- Config flow extendido con pasos EMHASS y detección de presencia
- 3 nuevos sensores: `active_trips`, `presence_status`, `charging_readiness`
- Servicio de migración desde sliders: `ev_trip_planner.import_from_sliders`
- 156 tests con 93.6% de paso

### Milestone 3.1: Mejoras UX — Claridad de Configuración (Dic 8, 2025)
- Filtros de entidad en config flow (SOC→%, Plugged→binary_sensor)
- Textos de ayuda y descripciones en todos los campos
- Traducciones completas al español
- "External EMHASS" renombrado a "Notifications Only"

### Milestone 3.2: Opciones de Configuración Avanzada (Dic 8, 2025)
- Capacidad de batería dinámica via sensor (con soporte SOH para degradación)
- Perfiles de consumo por tipo de viaje (urbano / carretera / mixto)
- Auto-limpieza de viajes puntuales pasados (configurable)
- Nuevo sensor: `last_cleanup`

### Milestone 4: Perfil de Carga Inteligente (Mar 18, 2026 — v0.4.0-dev)
- Perfil de carga binario: array de 168 valores (24h × 7d), 0W o máxima potencia
- Cálculo SOC-aware con margen de seguridad del 40%
- Sensor `emhass_perfil_diferible_{vehicle_id}` con atributo `power_profile_watts`
- Distribución de carga justo antes de cada viaje
- Alertas de tiempo insuficiente
- Config flow simplificado a 4 pasos
- Dashboard Lovelace con auto-import al completar configuración
- Lógica de reintentos: 3 intentos en ventana de 5 minutos
- 398 tests pasando, 85%+ cobertura

### Refactorización SOLID (Abr 2026 — rama feat/solid-refactor-coverage)
- `protocols.py`: interfaces explícitas (Protocol) para desacoplamiento
- `definitions.py`: entidades centralizadas, eliminación de duplicados
- `coordinator.py`: refactorizado para cumplir SOLID, sin acoplamiento directo
- `diagnostics.py`: soporte de diagnósticos para calidad HACS
- Cobertura de tests elevada a >80% para todos los módulos
- 793 tests Python + 10 E2E Playwright pasando

---

## 🚧 Próximo: Milestone 4.1 — Optimización Avanzada de Carga

**Estado**: 📋 PLANIFICADO — no comenzado  
**Detalle técnico completo**: [`docs/MILESTONE_4_1_PLANNING.md`](docs/MILESTONE_4_1_PLANNING.md)  

### Funcionalidades previstas

- **⚡ Carga Distribuida**: Distribuir energía en múltiples horas según precio de la red (en lugar de perfil binario)
- **🚗 Soporte Multi-Vehículo**: 2+ vehículos con balanceo de potencia en línea compartida
- **🌡️ Ajuste por Temperatura**: Corrección de consumo según previsión meteorológica
- **📊 UI de Perfil**: Gráfico de perfil de carga en el dashboard

### Prerequisitos antes de empezar M4.1
- [ ] Completar validación en producción de M3 (3E.1: 48h sin errores)
- [ ] Confirmar cobertura >80% en todos los módulos post-refactor SOLID
- [ ] Definir formato de API para optimizador externo de precios

---

## ⚠️ Limitaciones Conocidas (Activas)

Estas limitaciones están documentadas y son decisiones de diseño deliberadas para v1.0:

1. **Un índice EMHASS por viaje**: El usuario debe configurar manualmente el snippet EMHASS para cada índice potencial hasta `max_deferrable_loads`. No hay auto-discovery porque EMHASS no lo soporta.
2. **Configuración EMHASS manual**: No es plug-and-play; requiere añadir configuración a `configuration.yaml`.
3. **Un solo optimizador**: Solo EMHASS soportado. La arquitectura usa `emhass_adapter.py` como adaptador, preparado para añadir otros (Tibber, etc.) en v1.2.
4. **Horizonte de planificación fijo**: 7 días por defecto, configurable pero estático. No se adapta dinámicamente al horizonte de EMHASS.

---

## 🔮 Versiones Futuras (Post v1.0)

### v1.0: Consolidación
- Validación en producción completa (3E.1)
- HACS quality scale: bronce → plata
- Documentación de usuario completa

### v1.1: Multi-Vehículo
- Soporte para 2+ vehículos
- Gestión de línea de carga compartida
- Priorización y resolución de conflictos

### v1.2: Optimizadores Adicionales
- Integración nativa con Tibber y otros optimizadores de precio
- Reglas de optimización personalizadas
- Tarifas dinámicas sin EMHASS

### v1.3: Aprendizaje Inteligente
- Aprendizaje de consumo real desde histórico
- Predicción basada en meteorología y tráfico
- Tracking de degradación de batería

### v1.4: Planificación de Rutas
- Integración con Google Maps / OpenStreetMap Nominatim
- Cálculo automático de distancia desde dirección
- Planificación multi-parada

### v1.5: Gestión de Flota
- Soporte multi-usuario
- Permisos y roles
- Dashboard centralizado

---

## 🎯 Casos de Uso — Priorización

### P0 — Must Have (v1.0)
- ✅ Vehículo único con control de carga automático
- ✅ Vehículo único con solo notificaciones (sin control)
- ✅ Viajes recurrentes semanales
- ✅ Viajes puntuales
- ✅ Cálculos de energía y deadline

### P1 — Should Have (v1.1)
- ⏳ Multi-vehículo con línea compartida
- ⏳ Dashboard con gráficos de perfil

### P2 — Nice to Have (v1.2+)
- ⏳ PHEV con lógica híbrida
- ⏳ Optimización de precio dinámica (sin EMHASS)
- ⏳ Comandos de voz / HA Assist

### P3 — Futuro (v2.0+)
- ⏳ Gestión de flota
- ⏳ Planificación de rutas con mapas
- ⏳ Soporte multi-usuario

---

## 🚗 Integraciones de Vehículo

### Probadas por el equipo
- [x] OVMS (Nissan Leaf) — implementación de referencia
- [x] V2C EVSE (Dacia Spring) — implementación de referencia

### Pendientes de prueba (ayuda comunidad)
- [ ] Tesla
- [ ] Renault ZOE
- [ ] Hyundai/Kia
- [ ] BMW i3
- [ ] VW ID series
- [ ] EVSE genérico (enchufes inteligentes)

---

## 📚 Estructura de Documentación

```
docs/
├── MILESTONE_4_1_PLANNING.md         # Plan detallado Milestone 4.1 (no comenzado)
├── MILESTONE_4_POWER_PROFILE.md      # Especificación perfil de carga M4 (completado)
├── TDD_METHODOLOGY.md                # Metodología TDD aplicada al proyecto
├── TESTING_E2E.md                    # Guía de tests E2E con Playwright
├── IMPROVEMENTS_POST_MILESTONE3.md   # UX improvements implementados en M3.1/M3.2
└── configuration_examples.yaml       # Ejemplos completos de configuración YAML
```

---

## 🤝 Cómo Contribuir

**Alta prioridad**:
- Testing con diferentes integraciones de VE (ver lista pendiente arriba)
- Feedback UX sobre el dashboard
- Traducciones a otros idiomas
- Reportes de bugs

**Media prioridad**:
- Ejemplos de automaciones adicionales
- Optimizaciones de rendimiento

**Baja prioridad** (esperar a v1.0):
- Features avanzadas
- Integraciones nuevas de optimizador

---

**Última actualización**: Abril 2026  
**Revisión del estado**: Tras merge de feat/solid-refactor-coverage  

---

📬 **Issues y discusiones**:
- [GitHub Issues](https://github.com/informatico-madrid/ha-ev-trip-planner/issues)
- [GitHub Discussions](https://github.com/informatico-madrid/ha-ev-trip-planner/discussions)
