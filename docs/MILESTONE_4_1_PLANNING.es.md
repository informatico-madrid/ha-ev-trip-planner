# 🚀 Milestone 4.1: Mejoras de Perfil de Carga Inteligente - Plan de Implementación

**Documento de Planificación**  
**Versión**: 1.1  
**Fecha**: 2025-12-14  
**Última Revisión**: 2026-04-09  
**Estado**: 📋 **PLANIFICADO — NO INICIADO**  
**Target**: v0.5.0

> ⚠️ **Este documento es un plan de trabajo futuro. Nada de lo descrito aquí está implementado aún.**  
> El código actual cubre hasta Milestone 4 (perfil de carga binario SOC-aware).  
> Ver [`ROADMAP.md`](../ROADMAP.md) para el estado global del proyecto.

---

## 📋 Resumen Ejecutivo

Milestone 4.1 extiende la funcionalidad de Perfil de Carga Inteligente (Milestone 4) con mejoras basadas en feedback de producción y análisis de casos de uso avanzados. Este milestone se enfoca en **optimización de costes**, **soporte multi-vehículo**, y **experiencia de usuario mejorada**.

**Valor Añadido**: Reducción de costes de carga hasta 30%, soporte para hogares con múltiples EVs, y UI interactiva para monitoreo en tiempo real.

**Punto de partida**: Milestone 4 implementado y en producción — perfil binario de 168 valores (24h × 7d), integración EMHASS con índice dinámico por viaje, SOC-aware, coordinado con `presence_monitor` y `schedule_monitor`.

---

## 🎯 Mejoras Planificadas

### 1. ⚡ Carga Distribuida Inteligente (HIGH PRIORITY)

**Problema Actual**: El perfil de carga actual usa estrategia binaria (0W o máxima potencia) en una sola hora antes del viaje. No optimiza costes de electricidad.

**Solución Propuesta**:
- Distribuir carga en múltiples horas antes del viaje
- Priorizar horas con precio de electricidad más bajo (integración con EMHASS)
- Implementar algoritmo de optimización simple basado en:
  - Precio horario de electricidad (sensor de EMHASS)
  - Horas disponibles hasta el viaje
  - Potencia máxima del cargador

**Algoritmo de Optimización**:
```python
# Pseudocódigo
def optimizar_carga(energia_necesaria_kwh, horas_disponibles, precios_por_hora):
    # 1. Ordenar horas por precio ascendente
    horas_ordenadas = sorted(precios_por_hora.items(), key=lambda x: x[1])
    
    # 2. Asignar carga a horas más baratas primero
    perfil_optimizado = [0] * 168
    energia_restante = energia_necesaria_kwh
    
    for hora, precio in horas_ordenadas:
        if energia_restante <= 0:
            break
        if hora < horas_disponibles:
            # Asignar máxima potencia a hora barata
            energia_hora = min(charging_power_kw, energia_restante)
            perfil_optimizado[hora] = energia_hora * 1000  # Convertir a Watts
            energia_restante -= energia_hora
    
    return perfil_optimizado
```

**Beneficio**: Reducción de costes de carga hasta 30% en tarifas variables.

**Complejidad**: Media  
**Estimación**: 2-3 días de desarrollo  
**Tests Requeridos**: 5-7 tests TDD

---

### 2. 🚗 Soporte para Múltiples Vehículos (HIGH PRIORITY)

**Problema Actual**: El sistema asume un único vehículo por configuración. No hay balanceo de carga entre vehículos.

**Solución Propuesta**:
- Soporte para 2+ vehículos simultáneos
- Balanceo de carga según:
  - Prioridad del vehículo (configurable)
  - Urgencia del viaje (cuánto tiempo hasta el viaje)
  - SOC actual de cada vehículo
- Límite de potencia del hogar (ej: 10 kW total)

**Ejemplo de Uso**:
```yaml
# Configuración de múltiples vehículos
vehicles:
  - vehicle_id: chispitas
    priority: 1  # Alta prioridad
    soc_sensor: sensor.ovms_chispitas_soc
  - vehicle_id: morgan
    priority: 2  # Baja prioridad
    soc_sensor: sensor.morgan_battery_level

# Límite de potencia del hogar
home_max_power_kw: 10.0  # Si ambos cargan, no exceder 10 kW
```

**Beneficio**: Hogares con múltiples EVs pueden cargar eficientemente sin sobrecargar la instalación eléctrica.

**Complejidad**: Alta  
**Estimación**: 4-5 días de desarrollo  
**Tests Requeridos**: 8-10 tests TDD

---

### 3. 🌡️ Predicción de Consumo Basada en Clima (MEDIUM PRIORITY)

**Problema Actual**: El cálculo de energía necesaria no considera factores climáticos que afectan al rango.

**Solución Propuesta**:
- Integración con sensor de temperatura exterior
- Ajuste automático del consumo según:
  - Frío extremo (< 5°C): +20% consumo
  - Calor extremo (> 35°C): +10% consumo
  - Temperatura óptima (15-25°C): consumo normal
- Alertas cuando el clima afecta significativamente al rango

**Fórmula de Ajuste**:
```python
def ajustar_consumo_por_clima(kwh_necesarios, temperatura_celsius):
    if temperatura_celsius < 5:
        factor = 1.20  # +20% en frío
    elif temperatura_celsius > 35:
        factor = 1.10  # +10% en calor
    else:
        factor = 1.00  # Sin ajuste
    
    return kwh_necesarios * factor
```

**Beneficio**: Precisión en cálculos de energía necesaria, evitando quedarse sin batería.

**Complejidad**: Baja  
**Estimación**: 1-2 días de desarrollo  
**Tests Requeridos**: 3-4 tests TDD

---

### 4. 📊 UI Mejorada para Perfil de Carga (MEDIUM PRIORITY)

**Problema Actual**: No hay visualización gráfica del perfil de carga. Los usuarios no pueden ver cuándo se cargará el vehículo.

**Solución Propuesta**:
- Gráfico en dashboard mostrando:
  - Próximas 24-48 horas de perfil de carga
  - Horas con carga activa (coloreadas)
  - Precio de electricidad por hora (si disponible)
  - SOC actual y proyectado
- Indicador de "Próxima carga en X horas"
- Botón "Cargar Ahora" forzado (override automático)

**Componentes UI**:
```yaml
# Ejemplo de tarjeta Lovelace
type: custom:mini-graph-card
entities:
  - entity: sensor.chispitas_power_profile
    attribute: power_profile_watts
  - entity: sensor.emhass_electricity_price
name: "Perfil de Carga y Precios"
```

**Beneficio**: Transparencia total para el usuario. Puede ver cuándo y por qué se carga.

**Complejidad**: Media  
**Estimación**: 3-4 días de desarrollo (incluye frontend)  
**Tests Requeridos**: 4-5 tests TDD (backend) + testing manual UI

---

### 5. 🔋 Optimización de Salud de Batería (LOW PRIORITY)

**Problema Actual**: La carga siempre usa máxima potencia, lo cual no es óptimo para la salud de la batería a largo plazo.

**Solución Propuesta**:
- Modo "Salud de Batería" que:
  - Limita carga a 80% SOC para viajes diarios (configurable)
  - Usa carga lenta (3.7 kW) en lugar de rápida (7.4 kW) cuando el tiempo lo permite
  - Programa carga para evitar batería a 100% durante horas

**Ejemplo**:
```yaml
# Configuración de salud de batería
battery_health_mode: true
max_daily_soc: 80  # No cargar más allá de 80% para viajes diarios
prefer_slow_charging: true  # Usar 3.7 kW cuando sea posible
```

**Beneficio**: Extender vida útil de la batería en 15-20% según estudios.

**Complejidad**: Media  
**Estimación**: 2-3 días de desarrollo  
**Tests Requeridos**: 4-5 tests TDD

---

### 6. 🔔 Notificaciones Inteligentes Mejoradas (MEDIUM PRIORITY)

**Problema Actual**: Las notificaciones son básicas. No hay recordatorios proactivos.

**Solución Propuesta**:
- Recordatorio "Conecta el vehículo" X horas antes de carga programada
- Alerta "Carga incompleta" si el vehículo no alcanza SOC objetivo
- Notificación "Viaje en riesgo" si el clima afectará significativamente el rango
- Resumen diario/semanal de ahorro de costes

**Ejemplos**:
```yaml
# Configuración de notificaciones
notifications:
  pre_charge_reminder_hours: 2  # Recordatorio 2h antes
  incomplete_charge_alert: true
  weather_impact_alert: true
  savings_summary: "weekly"  # daily, weekly, monthly
```

**Beneficio**: Usuario siempre informado y puede tomar acción preventiva.

**Complejidad**: Baja  
**Estimación**: 1-2 días de desarrollo  
**Tests Requeridos**: 3-4 tests TDD

---

## 📊 Priorización y Roadmap

### Matriz de Priorización

| Mejora | Impacto Usuario | Complejidad Técnica | ROI Costes | Prioridad | Versión Target |
|--------|----------------|-------------------|------------|-----------|----------------|
| Carga Distribuida Inteligente | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **HIGH** | v0.5.0 |
| Múltiples Vehículos | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **HIGH** | v0.5.0 |
| Predicción Climática | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | MEDIUM | v0.5.1 |
| UI Mejorada | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | MEDIUM | v0.5.1 |
| Salud de Batería | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | LOW | v0.5.2 |
| Notificaciones | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | MEDIUM | v0.5.1 |

---

## 🧪 Estrategia de Testing (TDD)

### Fase 1: Tests de Carga Distribuida (HIGH PRIORITY)

```python
# tests/test_power_profile_optimization.py

async def test_carga_distribuida_prioriza_horas_baratas(hass):
    """Test que carga se asigna a horas con precio más bajo."""
    # Arrange: Viaje en 6 horas, necesita 3 horas de carga
    # Precios: [0.15, 0.12, 0.10, 0.20, 0.18, 0.14] €/kWh
    
    # Act: Generar perfil optimizado
    
    # Assert: Carga asignada a horas 1, 2, 5 (precios más bajos)
    assert perfil[1] == 7400  # Hora barata
    assert perfil[2] == 7400  # Hora barata
    assert perfil[0] == 0     # Hora cara, no usar

async def test_carga_distribuida_respetando_horas_disponibles(hass):
    """Test que no se programa carga después del viaje."""
    # Arrange: Viaje en 3 horas, necesita 5 horas de carga
    
    # Act: Generar perfil
    
    # Assert: Alerta de tiempo insuficiente, perfil vacío
    assert alerta == True
    assert all(p == 0 for p in perfil[3:])  # No carga después de viaje
```

### Fase 2: Tests de Múltiples Vehículos (HIGH PRIORITY)

```python
# tests/test_multi_vehicle.py

async def test_dos_vehiculos_sin_exceder_limite_casa(hass):
    """Test que dos vehículos no exceden límite de potencia del hogar."""
    # Arrange: Casa límite 10 kW, ambos necesitan 7.4 kW
    
    # Act: Generar perfiles con balanceo
    
    # Assert: Uno carga a 7.4 kW, otro espera o carga a 2.6 kW
    assert total_power <= 10000  # 10 kW límite

async def test_prioridad_vehiculo_afecta_orden_carga(hass):
    """Test que vehículo con prioridad 1 carga primero."""
    # Arrange: Dos vehículos, misma necesidad, diferentes prioridades
    
    # Act: Generar perfiles
    
    # Assert: Vehículo prio 1 tiene más horas de carga asignadas
    assert horas_carga_prio1 > horas_carga_prio2
```

### Fase 3: Tests de Clima (MEDIUM PRIORITY)

```python
# tests/test_climate_adjustment.py

async def test_ajuste_consumo_frio_extremo(hass):
    """Test que frío extremo aumenta consumo en 20%."""
    # Arrange: Viaje de 10 kWh, temperatura 0°C
    
    # Act: Calcular con ajuste climático
    
    # Assert: 12 kWh necesarios (10 * 1.20)
    assert energia_necesaria == 12.0

async def test_ajuste_consumo_temperatura_optima(hass):
    """Test que temperatura óptima no ajusta consumo."""
    # Arrange: Viaje de 10 kWh, temperatura 20°C
    
    # Act: Calcular con ajuste climático
    
    # Assert: 10 kWh necesarios (sin ajuste)
    assert energia_necesaria == 10.0
```

---

## 📅 Timeline Estimado

### Sprint 1: Carga Distribuida Inteligente (2 semanas)
- **Semana 1**: Implementación core + tests TDD
- **Semana 2**: Integración con EMHASS + validación en producción

### Sprint 2: Múltiples Vehículos (3 semanas)
- **Semana 1**: Diseño de arquitectura + tests TDD
- **Semana 2**: Implementación de balanceo + tests de integración
- **Semana 3**: Validación con 2+ vehículos reales

### Sprint 3: UI Mejorada + Notificaciones (2 semanas)
- **Semana 1**: Backend para UI + endpoints
- **Semana 2**: Dashboard Lovelace + notificaciones

### Sprint 4: Clima + Salud Batería (2 semanas)
- **Semana 1**: Integración climática + tests
- **Semana 2**: Modo salud batería + optimización

**Total Estimado**: 9 semanas (2-3 meses) para Milestone 4.1 completo

---

## 🔧 Requisitos Técnicos

### Dependencias Nuevas
```python
# requirements.txt (opcional)
# - numpy (para cálculos de optimización)
# - pandas (para análisis de precios)
```

### Cambios en Config Flow
- Nuevo paso: "Múltiples Vehículos" (si detecta >1 config entry)
- Nuevo campo: `home_max_power_kw` (opcional)
- Nuevo campo: `battery_health_mode` (checkbox)

### Cambios en Base de Datos
- Nuevo atributo en `vehicle_config`: `priority` (int, default: 1)
- Nuevo atributo en `vehicle_config`: `max_soc_daily` (float, default: 100.0)

---

## 📈 Métricas de Éxito

### KPIs a Medir
1. **Reducción de Costes**: % ahorro en factura eléctrica mensual
2. **Satisfacción Usuario**: Encuesta de satisfacción (1-5)
3. **Precisión SOC**: % de veces que el vehículo alcanza SOC objetivo
4. **Uso de UI**: % de usuarios que usan dashboard de perfil de carga
5. **Stability**: % de alertas falsas / errores

### Objetivos
- **Costes**: Reducir coste de carga en 25% promedio
- **Satisfacción**: 4.5/5 o superior en encuesta
- **Precisión**: 95% de viajes con SOC objetivo alcanzado
- **UI**: 70% de usuarios activos usan dashboard
- **Stability**: < 1% errores críticos

---

## 📝 Notas de Implementación

### Consideraciones de Seguridad
- **Validación de límites**: Siempre respetar `home_max_power_kw`
- **Fallback**: Si optimización falla, usar estrategia binaria actual (Milestone 4)
- **Override manual**: Usuario siempre puede forzar carga manualmente

### Compatibilidad Hacia Atrás
- Todas las mejoras son **opcionales**
- Configuración existente funciona sin cambios
- Nuevos campos tienen valores por defecto sensibles

### Performance
- Cálculos de optimización: < 100ms por vehículo
- Actualización de perfiles: Cada 15 minutos o cuando cambia SOC
- Cache de precios: 1 hora (configurable)

---

## 📚 Documentación Relacionada

- [`MILESTONE_4_POWER_PROFILE.md`](MILESTONE_4_POWER_PROFILE.md) — Implementación base de Milestone 4 (perfil binario)
- [`TDD_METHODOLOGY.md`](TDD_METHODOLOGY.md) — Metodología de testing TDD aplicada en el proyecto
- [`../ROADMAP.md`](../ROADMAP.md) — Estado global del proyecto y priorización de milestones

> 📌 Nota: `MILESTONE_3_IMPLEMENTATION_PLAN.md`, `MILESTONE_3_ARCHITECTURE_ANALYSIS.md` y `MILESTONE_3_REFINEMENT.md`
> existieron durante el desarrollo de M3 pero no están presentes en esta rama. El CHANGELOG documenta su contenido.

---

## ✅ Checklist de Implementación

### Pre-Desarrollo
- [ ] Validar requisitos con usuarios piloto
- [ ] Crear issues en GitHub para cada mejora
- [ ] Actualizar ROADMAP.md con estado de Milestone 4.1
- [ ] Configurar entorno de testing para múltiples vehículos

### Desarrollo
- [ ] **Sprint 1**: Carga Distribuida Inteligente
  - [ ] Tests TDD (5-7 tests)
  - [ ] Implementación core
  - [ ] Integración EMHASS
  - [ ] Validación en producción (1 vehículo)
  
- [ ] **Sprint 2**: Múltiples Vehículos
  - [ ] Tests TDD (8-10 tests)
  - [ ] Arquitectura de balanceo
  - [ ] Límites de potencia
  - [ ] Validación en producción (2+ vehículos)

- [ ] **Sprint 3**: UI + Notificaciones
  - [ ] Tests TDD (7-9 tests)
  - [ ] Backend para UI
  - [ ] Dashboard Lovelace
  - [ ] Sistema de notificaciones

- [ ] **Sprint 4**: Clima + Salud Batería
  - [ ] Tests TDD (7-9 tests)
  - [ ] Integración climática
  - [ ] Modo salud batería
  - [ ] Validación completa

### Post-Desarrollo
- [ ] Actualizar CHANGELOG.md con entrada v0.5.0
- [ ] Actualizar ROADMAP.md marcando M4.1 completado
- [ ] Crear release en GitHub
- [ ] Encuesta de satisfacción a usuarios

---

**Documento Version**: 1.1  
**Last Updated**: 2026-04-09  
**Status**: 📋 PLANIFICADO — NO INICIADO  
**Next Review**: Inicio de Sprint 1 (Carga Distribuida)
